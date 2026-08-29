# DEVELOPMENT.md — Run tests locally without Docker

This document covers running Miminet tests on a rootless Linux host
using **podman** (or docker) and **uv**. The production deployment
with Docker Compose is described in `README.md`.

## Prerequisites

- Linux with podman 6+ (or docker)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- ~4 GB free disk space for container images
- Ports **5432**, **5672**, **4442-4444**, **5000** free

---

## Frontend unit test (no containers, offline)

```bash
MODE=dev POSTGRES_HOST=localhost POSTGRES_DEFAULT_USER=postgres \
  POSTGRES_DEFAULT_PASSWORD=my_postgres POSTGRES_DATABASE_NAME=miminet \
  uv run pytest front/tests/test_config_db.py -v
```
Expected: **7 passed**.

---

## Frontend E2E tests (Selenium)

### 1. Start infrastructure

```bash
podman run -d --replace --rm --network host --name postgres \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=my_postgres \
  -e POSTGRES_DB=miminet docker.io/library/postgres:18 -c fsync=off

podman run -d --replace --rm --network host --name rabbitmq \
  -e RABBITMQ_DEFAULT_USER=user -e RABBITMQ_DEFAULT_PASS=password \
  docker.io/library/rabbitmq:3.13-management
```

Wait for postgres:
```bash
for i in $(seq 1 30); do
  python3 -c "import psycopg2; psycopg2.connect(host='localhost', user='postgres', password='my_postgres', dbname='miminet')" 2>/dev/null && break
  sleep 1
done
```

### 2. Seed database

```bash
MODE=dev POSTGRES_HOST=localhost POSTGRES_DEFAULT_USER=postgres \
  POSTGRES_DEFAULT_PASSWORD=my_postgres POSTGRES_DATABASE_NAME=miminet \
  uv run python front/src/app.py dev
```

### 3. Start Flask dev server

```bash
MODE=dev POSTGRES_HOST=localhost POSTGRES_DEFAULT_USER=postgres \
  POSTGRES_DEFAULT_PASSWORD=my_postgres POSTGRES_DATABASE_NAME=miminet \
  nohup uv run python -c "
import sys; sys.path.insert(0, 'front/src')
from app import app
app.run(host='0.0.0.0', port=5000)
" > .tmp/flask.log 2>&1 &
```

### 4. Start Selenium hub + Chrome node

```bash
podman run -d --replace --rm --network host --name selenium-hub \
  docker.io/selenium/hub:4.37.0

podman run -d --replace --rm --network host --shm-size 2gb --name chrome \
  -e SE_EVENT_BUS_HOST=localhost \
  -e SE_EVENT_BUS_PUBLISH_PORT=4442 \
  -e SE_EVENT_BUS_SUBSCRIBE_PORT=4443 \
  docker.io/selenium/node-chrome:141.0
```

### 5. Run tests

```bash
TEST_TARGET_HOST=localhost TEST_TARGET_PORT=5000 \
  MODE=dev POSTGRES_HOST=localhost POSTGRES_DEFAULT_USER=postgres \
  POSTGRES_DEFAULT_PASSWORD=my_postgres POSTGRES_DATABASE_NAME=miminet \
  uv run pytest front/tests -v --timeout=300
```
Expected: **114 passed** in ~5:30.

### 6. Cleanup

```bash
kill $(lsof -ti:5000) 2>/dev/null
podman stop -t 0 postgres rabbitmq selenium-hub chrome
```

---

## Backend tests (containerized)

Build the image and run the full suite inside an isolated container:

```bash
# Build
podman build -t miminet-back:test -f back/Dockerfile back/

# Probe: verify emulation works in the container's own network namespace
podman run --rm --entrypoint /bin/bash \
  -v $(pwd):/repo:ro -w /repo \
  --cap-add=ALL --device /dev/net/tun \
  miminet-back:test \
  -c "
    bash /repo/back/ovs-init.sh
    mn --topo single,2 --test pingall 2>&1 | tail -5
  "

# Run the full test suite
podman run --rm --entrypoint /bin/bash \
  -v $(pwd):/repo:ro -w /repo \
  --cap-add=ALL --device /dev/net/tun \
  miminet-back:test \
  -c "
    bash /repo/back/ovs-init.sh
    pip3 install -q pytest
    cd /repo/back/tests
    PYTHONPATH=/repo/back/src pytest -v -o log_file=/tmp/back_test.log -p no:cacheprovider --basetemp=/tmp/pytest
    mn -c >/dev/null 2>&1 || true
  "
```

Alternatively, use the helper script (same commands, auto-detects docker/podman):
```bash
scripts/back-test.sh build
scripts/back-test.sh test
```

Expected: **24 passed**.

---

## Required environment variables

| Variable | Default | Rootless dev value |
|----------|---------|--------------------|
| `MODE` | `prod` | `dev` |
| `POSTGRES_HOST` | `172.18.0.4` | `localhost` |
| `TEST_TARGET_HOST` | `172.18.0.2` | `localhost` |
| `TEST_TARGET_PORT` | `80` | `5000` |
| `SELENIUM_HUB_URL` | `http://localhost:4444/wd/hub` | (unchanged) |

## Notes

- Ports < 1024 are unavailable under rootless podman — Flask runs on port 5000.
- The `--network host` flag bypasses the `pasta --map-guest-addr` bug in
  older passt versions shipped with podman 6.1.0.
- Chrome requires `--shm-size 2gb` to avoid tab crashes under rootless podman.
- The `front/src/app.py config.js` route uses an absolute path — no CWD dependency.