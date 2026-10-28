# Bootstrap failure diagnostics

## Scope and output

The pending-simulation-log repair failure in `database_bootstrap.init_db` emits
one ERROR event through the existing `miminet_model` logger. Existing logger
names, handlers, return values and exception/rollback policy are preserved.
This slice does not change provisioning, authentication, worker or HTTP logging.

The app currently imports `miminet_auth`, whose `logging.basicConfig(INFO)`
provides a default root stderr handler if the host has not configured one.
The bootstrap logger propagates through that existing hierarchy. No new
handlers are added or root formatters/levels forcibly replaced. Hosting processes
can keep their logging configuration. Repeated failures do not duplicate handlers.

Each event includes, in its plain message as well as structured LogRecord fields:

| Field | Meaning |
| --- | --- |
| `bootstrap_stage` / `stage` | `repair_pending_logs` |
| `bootstrap_mode` / `mode` | `dev` or `prod` |
| `error_type` / `error` | Original exception class, e.g. `IntegrityError` |
| `sqlstate` | Valid five-character PostgreSQL code, otherwise `unknown` |
| `event_time` / `time` | UTC ISO timestamp, including an offset |

Default root formatting adds severity and logger name. Time is included in the
message itself so it remains visible with a simple hosting formatter. There is
no HTTP request/task correlation ID during this standalone startup path; none
is fabricated or taken from user data.

## Traceback and private data

SQLAlchemy exception text can include SQL, parameters and driver detail containing
full row values. Calling ordinary `logger.exception()` here would expose those
values. Instead, `exc_info` carries a synthetic RuntimeError with the original
class name and the original traceback frames; its message says that database
exception details were omitted. Frame locations and source lines remain visible,
but original exception strings, SQLAlchemy statement/parameter rendering and
cause/context chains are not formatted. Local variable values are not captured.

Use the `error`/`error_type` field to identify the original class; the final
RuntimeError in the rendered traceback is the sanitized diagnostic wrapper,
not a newly raised application error. SQLSTATE is kept when safe: the real
PostgreSQL constraint-failure test records `23514`. Nonmatching driver values
are replaced with `unknown` rather than logged verbatim.

This is protection for this selected error event and standard Python formatting,
not a claim that every existing log in the project has been audited/redacted.
Provisioning diagnostics and worker entry-point configuration are separate work.

## Retrieve startup diagnostics

`front/run_app.sh` invokes `python3 app.py "$MODE"` before uWSGI/Celery, so startup
stderr is captured by the container's normal logging stream. From `front/`:

```sh
docker compose logs --since 30m --tail 200 miminet
```

Look for `stage=repair_pending_logs` and retain its following traceback lines.
For a direct Python startup, inspect stderr of that process. uWSGI's separate
runtime log (`front/src/uwsgi.ini`, `./uwsgi.log`) is not a replacement for this
preceding bootstrap process's stderr. No restart or deployment is needed merely
to read existing logs.

## Verification and remaining policy

`test_bootstrap_logging.py` covers update/commit failures, traceback locations,
context/timestamp, safe SQLSTATE, parameter/driver/chain redaction, repeated
failure handler behavior and a successful no-error path. Integration tests cause
a real PostgreSQL CHECK failure in both dev/prod and confirm the private row
value is absent from logs while persisted data remains unchanged.

Startup repair still catches the exception and returns None without an explicit
rollback, as before. Whether startup should fail or continue and where rollback
must occur requires a separate behavior decision and regression tests.
