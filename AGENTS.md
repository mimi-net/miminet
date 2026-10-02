# Miminet

A Linux-based web emulator of computer networks for educational purposes.
Two independent halves, wired together through RabbitMQ:

- `front/` — the Flask web app (registration/login, network CRUD, admin, quiz, AI).
  Sources live in `front/src`, the entry point is `front/src/app.py`, and the
  processes are started by `front/run_app.sh` (uwsgi + a celery worker).
  `front/src/quiz/` is layered `controller → facade → service → entity`.
- `back/` — the Mininet/OVS emulation celery worker. Sources in `back/src`,
  entry into the logic is `run_miminet` in `back/src/tasks.py`.
- SQLAlchemy + PostgreSQL, RabbitMQ. Broker env vars are lowercase —
  `amqp_urls`, `rpc_urls`, `exchange_name` (see `front/.env`); do not go
  looking for `AMQP_URL`.

Setup and run details: `README.md`, `docs/DEVELOPMENT.md` (no Docker, podman),
`docs/FUNCTIONAL_TESTS.md`, `docs/BACKEND_TESTS.md`, `docs/GIT.md`.

## Lint, format, types

CI (`.github/workflows/linter.yml`) runs all three commands separately against
`back` and `front` — all of them must pass:

```bash
uv run --frozen ty check --no-progress front
uv run --frozen ruff format --check front
uv run --frozen ruff check front
```

- Ruff config lives in the root `pyproject.toml`: line-length 88, double quotes.
- `ty` ignores `unsupported-base` for exactly the three files that use
  `db.Model` (`front/src/miminet_model.py`, `front/src/quiz/entity/entity.py`,
  `front/src/ai_interview/models.py`). A new model file will not pass the check
  until you add it to `[[tool.ty.overrides]]` in the root `pyproject.toml`.
- The root is a uv workspace with no project of its own
  (`[tool.uv.workspace] members = ["back", "front"]`), so the root `.venv`
  holds the dependencies of **both** halves, `mininet` included. The
  `uv sync --project back` from the README is not required.

## Backend tests

The split matters: the dividing line is a direct call to `run_miminet`.
Per-file inventory — `docs/BACKEND_TESTS.md`.

- 6 unit files (`test_jobs`, `test_pkt_parser`, `test_vlan`, `test_network_ready`,
  `test_tasks`, `test_captures`) — no root, no Mininet, ~1 s.
- 2 emulation files (`test_miminet_back.py`, `test_duplication.py`) — need root,
  Mininet, OVS and a built `mimidump`; always finish with `mn -c`.
- **`PYTHONPATH=../src` is mandatory**: `back/tests/pytest.ini` sets
  `pythonpath = src`, but the rootdir is `back/tests`, where no such path
  exists, so without `PYTHONPATH` collection blows up on `test_jobs.py` and
  `test_vlan.py`:

  ```bash
  cd back/tests && PYTHONPATH=../src uv run --frozen --project ../.. pytest test_jobs.py -q
  ```

- Without root on the host: `scripts/back-test.sh build` → `scripts/back-test.sh test`
  (docker/podman, repo mounted read-only, emulation runs in the container's
  netns). `probe` and `collect` live there too.
- Test imports are inconsistent: `from src.tasks import ...` in some files,
  `from node_types import ...` in others. Don't unify them — follow the file
  you are editing.
- A new emulation scenario = the pair `back/tests/test_json/<name>_network.json` +
  `<name>_answer.json`.
- Coverage gate: `coverage report --fail-under=75` over `back/src` (CI merges
  3 shards).

## Frontend tests

The same functionality is covered by **two** suites: Selenium in `front/tests/`
and Playwright in `front/tests/playwright/`. A UI change usually means touching
both (they share `utils/networks.py`; the locators are duplicated).

- Playwright (faster, ~1 min, no Selenium grid), from the repo root:

  ```bash
  uv run playwright install chromium      # once, ~658 MB
  sh front/tests/playwright/run.sh                    # full suite, 4 processes
  sh front/tests/playwright/run.sh test_vlan.py       # single file
  sh front/tests/playwright/run.sh . --headed         # visible browser
  ```

  Never take more than 4 workers — the tests compete for the single
  `selenium`/`password` account and start failing.

- `TEST_TARGET_HOST` defaults to `172.18.0.2`, which is nginx inside the docker
  network; from the host it returns 502. Use `127.0.0.1`/`localhost` there.
  `run.sh` already substitutes `127.0.0.1`; a manual invocation does not.
- Selenium (slow, ~5 min): `sh front/tests/docker/run.sh`, then
  `uv run pytest front/tests`; per-test timeout is 300 s.
- Browser-free unit tests (no grid, no containers) are listed **explicitly** in
  `.github/workflows/front_coverage.yml`. A new one will not reach the coverage
  job until you add it to that list.
- A new E2E test ⇒ add the locator to `front/tests/utils/locators.py` and to
  its copy in `front/tests/playwright/utils/locators.py`.
- Auth tests live outside the test directories: `front/src/auth_tests/`. CI runs
  `cd front/src && python -m pytest .` and requires the `CLIENT_YANDEX` and
  `BOT_TOKEN` secrets — they cannot be run locally without them.

## Environment and gotchas

- `front/.env` is the source of truth for the test stand. `MODE=prod` switches to
  Yandex Cloud PostgreSQL (`docker-compose-prod.yml`); `start_all_containers.sh`
  picks the compose file based on `MODE`.
- Docker networks are configured in `front/.env` via `DOCKER_SUBNET` /
  `RABBITMQ_SUBNET` and the static `NGINX_IP` / `MIMINET_IP` / `POSTGRES_IP`.
  Change a subnet and you must change all three IPs too, or the containers will
  not see each other; afterwards run
  `docker compose down && docker compose up -d`.
- `load_dotenv()` in the code reads `.env` from the current directory: run any
  command that needs `amqp_urls`/`MODE` from `front/` (or the compose dir).
- `front/src/vk_auth.json` and `front/src/miminet_secret.conf` are not in git
  (see `.gitignore`). The first is copied by hand from the team chat; the second
  is what keeps you logged in across docker restarts.
- There are no migrations in the repository: `Migrate(app, db)` is in
  `front/src/app.py`, but the `migrations/` directory is not committed — you need
  `flask db init` before `flask db migrate` (all of it inside the `miminet`
  container).
- `.gitignore` contains `.*`, `*.ini` and `__init__.py`. The `pytest.ini` and
  `__init__.py` files that are already in the repo were force-added — new ones
  will not make it into a commit without `git add -f`.
- The backend cannot be deployed under WSL.
- `back/ovs-init.sh` is the single source of truth for starting OVS (image, local
  harness and CI). A second `ovs-vswitchd` breaks STP/RSTP ("No such RSTP
  object"), so do not duplicate that startup logic.
- The backend worker's celery timeouts are env-configured
  (`CELERY_TASK_SOFT_TIME_LIMIT`, `CELERY_TASK_TIME_LIMIT`,
  `CELERY_MAX_TASKS_PER_CHILD`) — see `back/src/celeryconfig.py`.

## Git and workflow

- Docs and code comments are written in English. `README.md` and `docs/*_TESTS.md`
  are still in Russian — leave them as they are, but write anything new in
  English.
- Branch naming rules — `docs/GIT.md`. Read it before creating a branch.
- Commit messages are in English: `<scope>: <description> (#<issue>)`.
