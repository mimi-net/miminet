# Miminet

A Linux-based web emulator of computer networks for educational purposes.
Two independent halves, wired together through RabbitMQ:

- `front/` — the Flask web app (registration/login, network CRUD, admin, quiz, AI).
  Sources live in `front/src`, the entry point is `front/src/app.py`, and the
  processes are started by `front/run_app.sh` (uwsgi + a celery worker).
  `front/src/quiz/` is layered `controller → facade → service → entity`.
- `back/` — the Mininet/OVS emulation celery worker. Sources in `back/src`,
  entry into the logic is `run_miminet` in `back/src/tasks.py`.

Docs: `README.md` (Russian, deployment), `docs/DEVELOPMENT.md` (running tests on
a rootless Linux host, no Docker), `docs/FUNCTIONAL_TESTS.md`,
`docs/BACKEND_TESTS.md` (per-file test inventory), `docs/GIT.md`,
`docs/REQUIREMENTS.md` (specification index, one file per subject in
`docs/REQUIREMENTS/`).

Lint commands, ruff/ty config, CI triggers, test selection, coverage gates and
per-workflow environment setup are all defined in `.github/workflows/*.yml` and
the root `pyproject.toml`. Read them — they are the source of truth and they
change often. Everything below is only what those files cannot tell you.

## Traps

- Broker env vars are lowercase: `amqp_urls`, `rpc_urls`, `exchange_name` (see
  `front/.env`). There is no `AMQP_URL`.
- The root is a uv workspace with no project of its own, so the root `.venv`
  holds both halves, `mininet` included; the README's `uv sync --project back`
  is not needed.
- `ty` ignores `unsupported-base` only for the `db.Model` files listed in the
  root `pyproject.toml`. A new declarative model fails the check until it is
  added to `[[tool.ty.overrides]]` there.
- Local backend tests need `PYTHONPATH=../src`. `back/tests/pytest.ini` sets
  `pythonpath = src`, but the rootdir is `back/tests`, where that path does not
  exist, so collection blows up on `test_jobs.py` and `test_vlan.py`.
- Backend tests split at direct calls to `run_miminet`: below it — no root, no
  Mininet, ~1 s; above it — root, Mininet, OVS and a built `mimidump`, and you
  must finish with `mn -c`. Without root on the host use
  `scripts/back-test.sh build` → `test`.
- Backend test imports are inconsistent (`from src.tasks import ...` in some
  files, `from node_types import ...` in others). Don't unify them — follow the
  file you are editing.
- The same E2E functionality is covered twice: Selenium in `front/tests/` and
  Playwright in `front/tests/playwright/` (they share `utils/networks.py`, and
  the locators are duplicated in both `utils/locators.py` copies). A UI change
  usually means touching both.
- Never take more than 4 Playwright workers — the tests compete for the single
  `selenium`/`password` account and start failing.
- `TEST_TARGET_HOST` defaults to `172.18.0.2`, which is nginx inside the docker
  network and answers 502 from the host. `run.sh` substitutes `127.0.0.1`; a
  manual pytest invocation does not.
- Auth tests live outside the test directories (`front/src/auth_tests/`) and
  need the `CLIENT_YANDEX` and `BOT_TOKEN` secrets — they cannot run locally.
- A new browser-free frontend test only reaches the coverage job after being
  listed explicitly in `.github/workflows/front_coverage.yml`.

## Environment

- `front/.env` is the source of truth for the test stand. `MODE=prod` switches to
  Yandex Cloud PostgreSQL (`docker-compose-prod.yml`);
  `start_all_containers.sh` picks the compose file based on `MODE`.
- Docker networks are configured in `front/.env` via `DOCKER_SUBNET` /
  `RABBITMQ_SUBNET` and the static `NGINX_IP` / `MIMINET_IP` / `POSTGRES_IP`.
  Change a subnet and all three IPs must change too, or the containers will not
  see each other; afterwards run `docker compose down && docker compose up -d`.
- `load_dotenv()` reads `.env` from the current directory: run anything that
  needs `amqp_urls`/`MODE` from `front/` (or the compose dir).
- There are no migrations in the repository: `Migrate(app, db)` is in
  `front/src/app.py`, but `migrations/` is not committed — you need
  `flask db init` before `flask db migrate` (all of it inside the `miminet`
  container).
- `.gitignore` contains `.*`, `*.ini` and `__init__.py`. The `pytest.ini` and
  `__init__.py` files that are in the repo were force-added; new ones need
  `git add -f`.
- `back/ovs-init.sh` is the single source of truth for starting OVS (image,
  local harness and CI). A second `ovs-vswitchd` breaks STP/RSTP ("No such RSTP
  object"), so do not duplicate that startup logic.
- The backend cannot be deployed under WSL.

## Git and workflow

- Docs and code comments are written in English. `README.md` and
  `docs/*_TESTS.md` are still Russian — leave them as they are, but write
  anything new in English.
- Branch naming rules — `docs/GIT.md`. Read it before creating a branch.
- Commit messages are in English: `<scope>: <description> (#<issue>)`.
