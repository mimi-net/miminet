# Testing the web backend

## Test boundaries

| Kind | Examples | Dependencies |
| --- | --- | --- |
| Unit and boundary | `test_critical_boundaries.py`, pure helpers in existing files | Python dependencies; no external services |
| HTTP/auth regression | `test_simulation_regressions.py` | Real Flask handlers/methods and JWT; broker transport stubbed |
| ORM integration | Same lifecycle/configuration scenarios on SQLite and PostgreSQL | Temporary SQLite file or a test PostgreSQL instance |
| Editing/copy regression | `test_network_editing.py` | Shared HTTP/DB fixture, actual preview files and constraint failures |
| Startup integration | `test_database_bootstrap_integration.py` | Clean/existing schema and provisioning on real PostgreSQL |
| Fault injection | Duplicate primary key and foreign-key deletion failures | Actual DB constraints, not mocked commit results |
| Logging regression | `test_bootstrap_logging.py`, real PostgreSQL CHECK failures | Traceback/context, no private SQL parameters, no duplicate handlers |
| Browser E2E | `front/tests/`, `front/tests/playwright/` | Running application, browser and supporting services |
| Emulation integration | `back/tests/` | Full Linux, Mininet, OVS and mimidump |

Regression is the purpose of a test, not a separate execution boundary. The HTTP
regressions compare persisted state after requests and failures. They do not
replace full application startup, browser, live Celery or emulation checks.

Simulation polling retains its existing lookup by simulation ID.
Tests characterize authenticated access
without owner or network GUID binding; they do not assert ownership enforcement
for this endpoint. JWT and required parameter checks are still covered.

## Local web environment

From the repository root, install the web workspace package without changing
the lockfile:

```powershell
uv sync --locked --package miminet-front
```

The same command can use a system `uv` on Linux. On Windows, use the installed
`.venv/Scripts/python.exe` directly to avoid syncing the emulator workspace.

## SQLite and PostgreSQL lifecycle tests

`test_simulation_regressions.py` and `test_network_editing.py` run their scenarios
against two DB engines through the shared `http_test_support.py` fixture.
PostgreSQL cases explicitly skip when `MIMINET_TEST_POSTGRES_URL` is absent.
An invalid configured URL fails rather than silently falling back to SQLite.
Use an isolated test database and a role allowed to create schemas. Each case
creates and deletes its own UUID-named schema; production schemas are not used.
SQLite enables foreign-key enforcement and adapts INTEGER primary keys only in
copied test DDL, leaving production models unchanged.

Example disposable local stand (PowerShell, from the repository root):

```powershell
$testPgId = docker run --detach --rm --publish 127.0.0.1::5432 --env POSTGRES_USER=miminet_test --env POSTGRES_PASSWORD=miminet_local_test_only --env POSTGRES_DB=miminet_test postgres:17-alpine
try {
    docker exec $testPgId pg_isready -U miminet_test -d miminet_test
    # Если сервер ещё запускается, повторите проверку готовности перед pytest.
    $testPgBinding = docker port $testPgId 5432/tcp
    $env:MIMINET_TEST_POSTGRES_URL = "postgresql+psycopg2://miminet_test:miminet_local_test_only@$testPgBinding/miminet_test"
    $env:MODE = 'dev'
    $env:SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    .\.venv\Scripts\python.exe -m pytest -q -o addopts= -o log_file=NUL front/tests/test_simulation_regressions.py front/tests/test_network_editing.py front/tests/test_database_bootstrap_integration.py
} finally {
    docker stop $testPgId
    Remove-Item Env:MIMINET_TEST_POSTGRES_URL -ErrorAction SilentlyContinue
}
```

The password above is a disposable local test credential. Docker must already
be available. A missing image can require a download. In the browser-free CI
workflow a PostgreSQL 17 service with a health check supplies the test URL, so
both engine variants run there rather than relying on optional local setup.
Check the pull request's Actions status for remote results.

## Verification checkpoints

PR branch, 2026-10-28: after Docker became available, the thirteen-file
browser-free selection reports **403 passed, no skips** with disposable
PostgreSQL 17.11 and SQLite. Zero temporary `miminet_test_*` schemas remained.
Combined statement/branch coverage is **30.36%** for web source, **56.77%** for
network operations and **96.52%** for bootstrap; the existing 21% gate passes.
This run includes the preserved simulation polling-by-ID contract.
The same selection also reports **403 passed, no skips** on PostgreSQL 18.6,
the version used by the Docker web stand; zero temporary schemas remained.
The adjacent job-validator file previously reported **11 passed**; Ruff
format/lint and ty passed for `front/` at the earlier PR checkpoint.

Earlier snapshot, 2026-10-27, Windows/Python 3.12.10 and PostgreSQL 17.11
(before restoring the existing simulation polling contract):

- 128 HTTP/ORM cases passed: 64 scenarios on each DB engine.
- 92 editing/copy cases passed: 46 scenarios on each engine, with real temporary
  files for preview copying and actual DB failures to check state preservation.
- Six PostgreSQL bootstrap cases passed before and after extraction; two later
  cases verify diagnostics for real repair failures in dev/prod.
- The full thirteen-file browser-free CI selection passed: 403 cases, including
  nine logging unit cases. Additional job-validator file: 11 passed.
- Combined statement/branch coverage: web source 30.36%, network operations 56.77%,
  `database_bootstrap.py` 96.52%, model declarations 100%. Declaration coverage
  alone does not measure ORM/database behavior. The whole-web CI gate is 21%.

The current file list and commands are in `.github/workflows/front_coverage.yml`.
Use `coverage run --branch --source=../src` from `front/tests` and an explicit
data-file path to reproduce that measurement. Native Windows logs use `NUL`;
Linux uses `/dev/null`. This measurement does not include browser or emulator
coverage and does not establish live broker reliability.
