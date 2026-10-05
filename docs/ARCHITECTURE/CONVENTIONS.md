# CONVENTIONS.md — conventions

The rules a change has to follow: naming, the `job_id` contract, the database
and environment rules, per-change checklists, and the CI commands. It is a
section of the architecture reference, see
[ARCHITECTURE.md](../ARCHITECTURE.md).

Repository-specific traps that are not rules but gotchas live in
[AGENTS.md](../../AGENTS.md) — read it before working in this repository.

## Contents

- [Naming and layout](#naming-and-layout)
- [Language](#language)
- [The `job_id` registry](#the-job_id-registry)
- [Validation is deliberately duplicated](#validation-is-deliberately-duplicated)
- [Database](#database)
- [Environment and configuration](#environment-and-configuration)
- [Adding things](#adding-things)
- [Lint, types, tests](#lint-types-tests)
- [Testing the UI](#testing-the-ui)

---

## Naming and layout

- Frontend modules outside a package are `miminet_*.py` (`miminet_model`,
  `miminet_auth`, `miminet_network`, `miminet_host`, `miminet_simulation`,
  `miminet_shark`, `miminet_admin`, `miminet_config`, `miminet_util`).
  Non-`miminet_` modules are infrastructure or features: `app`, `tasks`,
  `celery_app`, `celeryconfig`, `configurators`, `pcap_parser`, `ai_generate`.
- Backend modules are unprefixed and singular: `network`, `network_topology`,
  `network_schema`, `jobs`, `emulator`, `pkt_parser`, `node_types`.
- New back helpers go in `back/src/net_utils/`, not into `network.py`.
- Job handlers are `<verb>_<noun>_handler(job, job_host)` in `back/src/jobs.py`.
- Controllers are `<aggregate>_controller.py`, services `<aggregate>_service.py`,
  facades `<aggregate>_facade.py`.
- Template naming (`_`-prefix for macros, snippet vs page) is in
  [TEMPLATES.md](TEMPLATES.md#conventions).

---

## Language

Docs and code comments are English. `README.md` and `docs/*_TESTS.md` are
Russian and stay that way. User-facing strings and Flask-Admin view names are
Russian. Commit messages are English: `<scope>: <description> (#<issue>)`.

---

## The `job_id` registry

A job is identified by an integer `job_id`, and the number is a **contract
between the two halves**. Adding one means touching, in order:

1. `back/src/jobs.py` — the handler, its argument checkers, and the entry in the
   `Jobs._dct` registry (`back/src/jobs.py:582`).
2. `front/src/miminet_host.py` — the validator, the `build_error` message, and the
   mapping from the dialog control to `arg_1..arg_5`.
3. `front/src/configurators.py` — `create_job(job_id, job_sign)` on the device
   configurator that owns it.
4. `front/src/static/config_devices.js` — the dialog markup and its bindings.
5. The E2E fixture that exercises it, in **both** `front/tests/` and
   `front/tests/playwright/`.

The numbering carries semantics the backend depends on:

| Range | Meaning |
|---|---|
| `1`–`7` | Simple commands: ping, ping with options, UDP/TCP send, traceroute, link down, sleep |
| `100`–`110` | Configuration: IP address, iptables, route, ARP, VLAN subinterface, IPIP, GRE, ARP proxy, DHCP client, port forwarding |
| `200`–`203` | Long-running listeners, executed before their clients: UDP server, TCP server, port block, DHCP server |

`emulator` sorts by `job_id // 100` descending, so the `2xx` listeners bind
first. Anything new that binds a socket belongs in `2xx` and in
`SERVER_SETTLE_JOBS` (`back/src/emulator.py:25`).

---

## Validation is deliberately duplicated

Argument validation exists twice: `front/src/miminet_host.py` (to give the user
immediate feedback in the dialog) and `back/src/jobs.py` (to refuse to build a
shell command from untrusted input). Both must be updated together. The backend
copy is the security boundary — a check that only exists on the frontend is not
a check. Note also that `filter_arg_for_options` exists in both
`front/src/miminet_host.py:113` and `back/src/jobs.py:13` for the same reason.

---

## Database

- `db` is a single Flask-SQLAlchemy instance created in `miminet_model.py` with
  an explicit naming convention, so Alembic autogenerate produces stable
  constraint names.
- Declarative models must carry `# type: ignore[name-defined]` and be listed in
  the `[[tool.ty.overrides]]` block of the root `pyproject.toml`, or `ty` fails
  on `unsupported-base`.
- There are **no committed migrations**. `Migrate(app, db)` is wired in
  `app.py:268`, but `migrations/` must be created with `flask db init` first.
- Core tables (`user`, `network`, `simulate`, `simulate_log`) are created by
  `init_db`; the quiz tables by `db.create_all()`; the AI interview tables by
  `create_ai_interview_tables()` (`front/src/app.py:672`).
- `init_db` only probes or auto-creates the database when `MODE` derives it.
  With an explicit `SQLALCHEMY_DATABASE_URI` the caller owns the database and
  nothing is provisioned (`front/src/miminet_model.py:209`).

---

## Environment and configuration

- Broker vars are lowercase: `amqp_urls`, `rpc_urls`, `exchange_name`,
  `queue_names`, `celery_concurrency`. Front and back share `exchange_name`.
- `load_dotenv()` reads `.env` from the **current directory**, so anything that
  needs broker config or `MODE` must run from `front/`.
- `MODE=dev` uses the local PostgreSQL container; `MODE=prod` uses Yandex Cloud
  with `sslmode` and a root certificate. An explicit
  `SQLALCHEMY_DATABASE_URI` overrides both, which is how tests get a throwaway
  database.
- `SECRET_KEY` is read from `miminet_secret.conf` next to the app, or generated
  per process if the file is absent — meaning sessions do not survive a restart
  in that mode.
- Emulation tuning knobs, all optional: `MIMINET_SERVER_SETTLE`,
  `MIMINET_CAPTURE_RESTART_GRACE`, `MIMINET_DISABLE_IPV6`, and on the worker
  `CELERY_TASK_TIME_LIMIT`, `CELERY_TASK_SOFT_TIME_LIMIT`,
  `CELERY_MAX_TASKS_PER_CHILD`.

---

## Adding things

**A new device type**

1. `back/src/node_types.py` — add the `NodeType` member.
2. `back/src/network_topology.py` — add a `__handle_*` branch in
   `MiminetTopology.__handle_node` and a handler that creates the right
   ipmininet class.
3. `front/src/configurators.py` — add an `AbstractDeviceConfigurator` subclass.
4. `front/src/miminet_host.py` — add the `save_*_config` endpoint and register it
   in `app.py`.
5. `front/src/static/config_devices.js` plus a `config_<type>.html` dialog, and
   an entry in `front/src/static/images/` for the palette.
6. Both E2E suites and a backend fixture under `back/tests/test_json/`.

**A new route** — register it in `front/src/app.py`. Add it to
`sitemap()`'s `skip_pages` list if it must not be indexed. Wrap it in
`@jwt_required()` for API endpoints or `@login_required` for pages; note that
HTML pages redirect while JSON endpoints return 401. Add the row to the route →
template map in [TEMPLATES.md](TEMPLATES.md#route--template-map) if it renders a
page.

**A new quiz endpoint** — add it to the matching `quiz/controller/*_controller.py`,
delegate to a facade when more than one entity is involved or a DTO is needed,
otherwise to a service. Never query the ORM from a controller.

---

## Lint, types, tests

The commands below are what CI runs; the workflow files are the source of truth
and they change often.

| Check | Command | Workflow |
|---|---|---|
| Format | `uv run ruff format --check <half>` | `linter.yml:43` |
| Lint | `uv run ruff check <half>` | `linter.yml:47` |
| Types | `uv run ty check <half>` | `linter.yml:39` |
| Front E2E | Selenium (`front/tests`) and Playwright (`front/tests/playwright`) | `full_test.yml` |
| Front unit | browser-free tests, listed explicitly in the workflow | `front_coverage.yml` |
| Back | `PYTHONPATH=../src pytest`, needs root + Mininet + OVS + `mimidump` | `back_test.yml` |
| Auth | needs `CLIENT_YANDEX` and `BOT_TOKEN` secrets | `auth_test.yml` |

Ruff: line length 88, target `py312`, `select = ["E4", "E7", "E9", "F", "W605"]`,
double quotes. `E501` is ignored, so long lines pass but still wrap badly in
review.

A new browser-free frontend test only reaches the coverage job after being listed
by name in `.github/workflows/front_coverage.yml`.

Backend tests split at direct calls to `run_miminet`: below it there is no root,
no Mininet and the suite runs in about a second; above it you need root, Mininet,
OVS and a built `mimidump`, and the run must end with `mn -c`. Without root on
the host, use `scripts/back-test.sh build` then `test`. Full recipes are in
[DEVELOPMENT.md](../DEVELOPMENT.md).

---

## Testing the UI

The same E2E scenarios exist twice — Selenium in `front/tests/` and Playwright
in `front/tests/playwright/`. They share `utils/networks.py`, and `locators.py`
is duplicated verbatim in both `utils/` directories. **A UI change usually means
touching both.** Never run more than 4 Playwright workers: the suites compete for
the single `selenium`/`password` account and start failing.

`TEST_TARGET_HOST` defaults to `172.18.0.2`, which is nginx inside the docker
network and answers 502 from the host. `front/tests/docker/run.sh` substitutes
`127.0.0.1`; a manual `pytest` invocation does not — set it yourself.