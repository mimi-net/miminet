# MODULES.md — module map

What each module owns and which modules it is allowed to depend on. It is a
section of the architecture reference, see [ARCHITECTURE.md](../ARCHITECTURE.md).

## Contents

- [front/src — flat feature slices](#frontsrc--flat-feature-slices)
- [front/src/quiz — layered package](#frontsrcquiz--layered-package)
- [front/src/ai_interview — engine-centric package](#frontsrcai_interview--engine-centric-package)
- [back/src — emulation worker](#backsrc--emulation-worker)
- [Templates and static assets](#templates-and-static-assets)
- [Tests, scripts, infrastructure](#tests-scripts-infrastructure)

---

## front/src — flat feature slices

Outside `quiz/` and `ai_interview/` the frontend is a **flat set of modules,
one per feature**, all importable as top-level names because uwsgi runs with
`front/src` as the working directory and on `sys.path`. There is no package
nesting and no enforced layering — dependency direction follows the table below.

| Module | Responsibility | Depends on |
|---|---|---|
| `app.py` | Flask instance, config, extension wiring, all `add_url_rule` calls, Flask-Admin registration, `sitemap.xml`, `/config.js`, JWT error handlers, `__main__` bootstrap | everything |
| `celery_app.py`, `celeryconfig.py` | Celery app, queue/exchange declarations, broker URLs | — |
| `tasks.py` | Front celery tasks: `save_simulate_result`, `perform_task_check` | `app`, `celery_app`, `miminet_model`, `quiz.service.session_question_service` |
| `miminet_config.py` | `SECRET_KEY` load-or-generate, `make_empty_network()` factory, Pillow image probe | — |
| `miminet_model.py` | The `db` instance; `User`, `Network`, `Simulate`, `SimulateLog`; `init_db()` provisioning and schema creation | `miminet_config` |
| `miminet_auth.py` | VK/Google/Yandex/Telegram login and callbacks, `LoginManager`, JWT cookie issuance and stale-cookie cleanup, profile pages, animation filter preferences | `miminet_model`, `miminet_config` |
| `miminet_network.py` | Network CRUD, editor page rendering (`web_network`, `web_network_shared`), preview images, node/edge persistence, emulation queue statistics | `miminet_model`, `miminet_config` |
| `miminet_host.py` | Job argument validators (`IPv4_check`, `port_check`, …), option filters, error message catalog, the seven device-config endpoints and `delete_job` | `configurators`, `miminet_model` |
| `configurators.py` | The object model behind the device dialogs: `JobConfigurator`/`JobArgConfigurator` validation pipeline and the `AbstractConfigurator` → node/device/edge hierarchy | — |
| `miminet_simulation.py` | `run_simulation` (enqueue emulation) and `check_simulation` (poll result) | `celery_app`, `miminet_model` |
| `miminet_shark.py` | MimiShark pcap viewer page | `miminet_model`, `pcap_parser` |
| `pcap_parser.py` | pcap → JSON for MimiShark (frame tree for Wireshark-like display) | — |
| `miminet_admin.py` | Flask-Admin `ModelView` subclasses for quiz entities and AI interview settings, statistics dashboard, check-task builder | `miminet_model`, `quiz.*`, `ai_interview.models` |
| `ai_generate.py` | `/ai/generate-task`: LLM-generated network topologies with topology repair and validation | `miminet_model`, `miminet_auth` |
| `auth_tests/` | Yandex/Telegram authorization tests. Not part of the app; run by a dedicated CI workflow | — |
| `miminet_util.py` | Empty placeholder, kept for future shared helpers | — |

Note the deliberate separation between `miminet_host.py` (validators, error
messages and thin HTTP endpoints) and `configurators.py` (the pipeline that
actually applies a device configuration). Configurator instances are module-level
singletons created at import time (`front/src/miminet_host.py:189`), and the
device endpoints are one-line delegations to them
(`front/src/miminet_host.py:507`-`front/src/miminet_host.py:539`). The job
definitions follow immediately after, as declarative chains of
`create_job(...).add_param(...).add_check(...).set_error_msg(...)`
(`front/src/miminet_host.py:202`) — that chain *is* the front half of the
`job_id` contract. `delete_job` (`front/src/miminet_host.py:543`) is the one
endpoint in the group that does its own work.

---

## front/src/quiz — layered package

The quiz subsystem is the one place with an enforced layering. Dependencies
flow strictly in one direction:

```
controller  ──▶  facade  ──▶  service  ──▶  entity
    └──────────────────────────────▲
                util (dto, encoder)
```

| Layer | Directory | Owns | May import |
|---|---|---|---|
| controller | `quiz/controller/` | HTTP only: parse the request, delegate, return JSON or render a template. No business rules, no ORM queries. | `facade`, `service`, `util`, `miminet_model` |
| facade | `quiz/facade/` | Orchestration across entities and presentation shaping: session start/finish, result assembly, JSON-schema validation of LLM answers | `service`, `entity`, `util`, `miminet_model` |
| service | `quiz/service/` | Single-entity CRUD and grading logic. Returns ORM objects, never DTOs. | `entity`, `miminet_model` |
| entity | `quiz/entity/entity.py` | SQLAlchemy models and the custom column types | `miminet_model` |
| util | `quiz/util/` | `dto.py` (read models shared by facades and templates) and `encoder.py` | `entity`, `miminet_model` |

Controllers, one per aggregate: `question_controller.py`,
`section_controller.py`, `test_controller.py`, `quiz_session_controller.py`,
`image_controller.py` (the last one registers a `Blueprint`).

Services split by concern rather than by entity name alone: besides the CRUD
services (`test_service`, `section_service`, `question_service`) there are three
grading services — `check_host_service.py` (per-device assertions: subnet masks,
VLAN IDs, required paths, echo requests), `check_network_service.py`
(whole-network assertions), and `check_practice_service.py` (the dispatcher
that walks a task's requirement list). `network_upload_service.py` turns a
user-submitted network plus requirements into a check payload.

`entity.py` defines reusable mixins — `IdMixin` (GUID primary key),
`SoftDeleteMixin`, `TimeMixin`, `CreatedByMixin` — and the `GUID` and `Json`
`TypeDecorator` column types.

---

## front/src/ai_interview — engine-centric package

The AI interview feature is organized around an engine rather than around
layers. `controller.py` is the only Flask-facing file (a `Blueprint` named
`ai_interview`); everything else is reached through it.

| Module | Responsibility |
|---|---|
| `controller.py` | Blueprint, page routes, JSON API routes, error → status mapping |
| `engine.py` | Orchestration: start / submit / abort, turn creation, answer recording |
| `planner.py` | Topic schedule, question selection, focus construction |
| `prompts.py` | Prompt text and JSON schemas per turn type |
| `providers.py` | LLM transport, retry/temperature settings, `jsonschema` validation, `get_provider()` |
| `rubric.py` | Score normalization and summary |
| `state.py` | Read model: session history, serialized state payloads |
| `access.py` | Access codes: create, validate, expire, cleanup |
| `catalog.py` | Public topic catalog and key validation |
| `question_bank.py` | Bank-mode question selection |
| `models.py` | `AiInterviewSetting`, `AiInterviewAccessCode`, `AiInterviewSession`, `AiInterviewTurn` |
| `errors.py` | `InterviewError` hierarchy |

Provider configuration is read from the environment through
`providers.read_env_secret`; the feature degrades to `ProviderNotConfigured`
rather than crashing when no key is present.

---

## back/src — emulation worker

| Module | Responsibility |
|---|---|
| `tasks.py` | `mininet_worker` celery task; `run_miminet` — the entry point for all logic; JSON → dataclass load; retry loop; result dispatch |
| `network_schema.py` | The dataclasses that *are* the wire contract: `Network`, `Node`, `NodeConfig`, `NodeInterface`, `NodeData`, `NodePosition`, `Edge`, `EdgeData`, `Job`, `NetworkConfig` |
| `node_types.py` | `NodeType` enum — the closed set of emulatable device types |
| `emulator.py` | `emulate()`: job limits, pre-run cleanup, network lifecycle, job ordering and execution, pcap → animation |
| `network_topology.py` | `MiminetTopology(IPTopo)` — turns the schema into ipmininet nodes and links |
| `network.py` | `MiminetNetwork(IPNet)` — `start()`, the readiness gate, the adaptive settle loop, idempotent `stop()` |
| `jobs.py` | The `job_id` → handler registry, every handler, and the argument checkers that guard them |
| `pkt_parser.py` | pcap → animation packet dicts, with `dpkt.VXLAN` added for tunnel decoding |
| `net_utils/captures.py` | The single place that knows the mimidump capture file layout |
| `net_utils/readiness.py` | Iterate capture endpoints for readiness probing |
| `net_utils/vlan.py` | 802.1Q access/trunk setup and bridge cleanup |
| `net_utils/vxlan.py` | VTEP interfaces, endpoint setup, teardown |
| `celery_app.py`, `celeryconfig.py` | Celery app and queue bindings |

`back/src` uses **bare imports** (`from jobs import Jobs`, `from network_schema
import Network`) because the worker runs with `back/src` on `sys.path`.
`front/src` uses the same bare style for its siblings (`from miminet_model
import Network`). Both halves are inconsistent with their own package imports
(`quiz.*`, `ai_interview.*`) — follow the file you are editing.

---

## Templates and static assets

What each template and asset file is for is covered here; **how they are
composed** — blocks, `extends`/`include`, the route → template map — is in
[TEMPLATES.md](TEMPLATES.md).

| Path | Contents |
|---|---|
| `front/src/templates/` | Jinja2 templates, one per page, plus subdirectories mirroring the feature (`quiz/`, `auth/`, `admin/`, `ai_interview/`) |
| `front/src/templates/base.html` | The single page shell: GTM, meta/OG blocks, navbar, network modals, vendor script tags |
| `front/src/templates/config.js` | A **template**, not a static file — rendered by the `/config.js` route with `EXTERNAL_BASE_URL` interpolated |
| `front/src/static/assets/` | Theme and vendor CSS/JS (Bootstrap, nouislider, rellax, parallax) |
| `front/src/static/js/` | Vendored libraries: jQuery, jQuery UI, Cytoscape (+ canvas and edgehandles plugins), Ace, lodash |
| `front/src/static/*.js` | First-party application scripts, one per concern: `netfront.js` (editor), `netfront_f.js`, `miminet_animation.js` (packet playback), `config_devices.js`, `config_vlan.js`, `config_vxlan.js`, `config_stp.js`, `icons.js`, `jwt_auth.js`, `shark_script.js` |
| `front/src/static/config_*.html` | Device dialog markup, injected by `config_devices.js` |
| `front/src/static/quiz/` | Quiz page scripts, split by page: `quiz_scripts.js`, `session_scripts.js`, `practice_question_scripts.js`, `text_question_scripts.js`, `drop_node.js` |
| `front/src/static/ai_interview/interview.js` | AI interview client |
| `front/src/static/pcaps/<network_guid>/` | Written at runtime by `save_simulate_result`; served as static files |
| `front/src/static/images/preview/<a>/<b>/<hash>.png` | Network preview images, sharded by the first two hex characters of the hash |

---

## Tests, scripts, infrastructure

How to *run* these is in [DEVELOPMENT.md](../DEVELOPMENT.md) and
`docs/*_TESTS.md`; the CI commands are in
[CONVENTIONS.md](CONVENTIONS.md#lint-types-tests).

| Path | Responsibility |
|---|---|
| `front/tests/` | Selenium E2E suite plus browser-free unit tests |
| `front/tests/playwright/` | Playwright port of the same E2E scenarios |
| `front/tests/utils/` | Shared `locators.py`, `networks.py`, `checkers.py` — duplicated verbatim under `playwright/utils/` |
| `front/src/auth_tests/` | Auth tests that need real Yandex/Telegram secrets; CI-only |
| `back/tests/` | Backend suite, split by whether it needs root and Mininet |
| `back/tests/test_json/` | Network/answer fixture pairs — one per scenario |
| `back/bench/` | Benchmark harness plus example topologies |
| `scripts/back-test.sh` | Containerized backend test runner (docker/podman auto-detect) |
| `scripts/bench-emulation.sh` | Benchmark driver |
| `scripts/fetch-example-networks.py` | Seeds the published example networks |
| `scripts/lib-back-env.sh` | Shared env sourcing for the back scripts |
| `start_all_containers.sh` | Starts the front stack, choosing the compose file from `MODE` |
| `ansible/` | Deployment playbooks and systemd unit for a back node |
| `rabbitmq/`, `front/rabbitmq/` | Broker configuration, enabled plugins, metrics collector |
| `.github/workflows/` | `linter.yml`, `full_test.yml`, `back_test.yml`, `front_coverage.yml`, `auth_test.yml`, `dependency_review.yml` |