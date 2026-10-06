# QUIZ.md — Practice tasks over the quiz API

How to create a practical task (`"question_type": "practice"`) through the HTTP
API, and what every requirement kind available for grading actually checks.

The document describes **what is**. Architecture and data flow live in
[ARCHITECTURE.md](ARCHITECTURE.md) and `docs/ARCHITECTURE/`; deployment and
tests live in [DEVELOPMENT.md](DEVELOPMENT.md), `README.md` and
`docs/*_TESTS.md`.

The quiz is layered `controller → facade → service → entity`
(`docs/ARCHITECTURE/MODULES.md`). A practice task passes through these files:

| Stage | File |
|---|---|
| HTTP layer | `front/src/quiz/controller/question_controller.py` |
| Task creation | `front/src/quiz/facade/question_facade.py` |
| Schema of the requirements | `front/src/quiz/facade/json_schema_validation.py` |
| Grading | `front/src/quiz/service/check_practice_service.py`, `check_host_service.py`, `check_network_service.py` |
| Scenario expansion | `front/src/quiz/service/network_upload_service.py` |
| Storage | `front/src/quiz/entity/entity.py` (`Question`, `PracticeQuestion`) |

## Contents

- [Creating a practice task](#creating-a-practice-task)
- [The requirements format](#the-requirements-format)
- [Available requirements](#available-requirements)
- [Examples](#examples)
- [Scenario modifications](#scenario-modifications)
- [Scoring and hints](#scoring-and-hints)
- [How a student answer is graded](#how-a-student-answer-is-graded)
- [Response codes](#response-codes)
- [Traps](#traps)
- [Verification](#verification)

---

## Creating a practice task

```
POST /quiz/question/create?id=<section_id>
Content-Type: application/json
Cookie: mimi_session=…                # flask_login cookie, see below
```

Registered at `front/src/app.py:373`, handled by
`question_controller.create_question_endpoint`
(`front/src/quiz/controller/question_controller.py:25`).

The endpoint is `@login_required` from `flask_login`, not `@jwt_required`, so it
needs the **session cookie** issued by the login flow — the cookie is named
`mimi_session` (`front/src/app.py:262`), and a request with the JWT cookies only
is redirected (302) to the login page (`front/src/miminet_auth.py:203`). `?id=`
is optional: with no `id` the section lookup is skipped and the question is
created with `section_id = NULL` (`question_facade.py:27`). With an `id`, the
section must exist, not be soft deleted and belong to the caller — see
[Response codes](#response-codes) for what each case actually returns.

The body is either one object or an array of objects; an array is created
one by one and the response contains the list of created ids
(`question_facade.create_question`, `question_facade.py:165`).

### Body fields

| Field | Required | Meaning |
|---|---|---|
| `text` | yes | Question text (`Question.text`) |
| `question_type` | yes | `"practice"` — stored as `question_type = 0` (`entity.py:184`) |
| `explanation` | no | Text returned to the student after the check (`Question.explanation`). Also written to the unused `PracticeQuestion.explanation` column |
| `description` | no | Description shown on the practice canvas (`PracticeQuestion.description`) |
| `category` | no | `question_category.name`; an unknown name is silently ignored (`question_facade.py:42`) |
| `start_configuration` | yes | `guid` of an existing `network` row — the starting topology |
| `requirements` or `network_scenarios` | yes, one of them | What to check — see [below](#the-requirements-format) |
| `available_host` | no | How many extra `host` nodes the student may drag onto the canvas |
| `available_l2_switch` | no | … extra `l2_switch` nodes |
| `available_l1_hub` | no | … extra `l1_hub` nodes |
| `available_l3_router` | no | … extra `l3_router` nodes |
| `available_server` | no | … extra `server` nodes |
| `images` | no | File names previously returned by the image upload endpoint |

The five `available_*` values drive the palette counters in
`front/src/static/quiz/practice_question_scripts.js`. A missing key is stored as
the empty string (`question_facade.py:96`), and `parseInt("")` is `NaN`, so the
unit stays draggable and the label reads `Доступно: NaN` — pass explicit integers.

### What happens to `start_configuration`

`question_facade.py:98-124`:

1. The network is looked up by `guid`; a miss is a 404 with
   `{"message": "Сеть <guid> не найдена"}`.
2. Its JSON is deep-copied with `packets` and `pcap` removed.
3. A **new** `network` row is committed immediately: new uuid, the caller as
   author, the source title/preview, `description="Task start configuration
   copy"`, `is_task=True`.
4. `PracticeQuestion.start_configuration` points at that copy.

So the student's canvas starts from an immutable copy of the source network, and
each student gets a further copy at session start
(`quiz/util/dto.py:335` `PracticeQuestionDto`). Editing the source network later
does not change the task.

The copy is committed at `question_facade.py:122`, **before** the image check, so
a request that fails later with 400 (a name in `images` that is not on disk)
still leaves an orphan `is_task` network row behind.

### Minimal request

```bash
curl -X POST 'http://localhost:80/quiz/question/create?id=1' \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{
    "text": "Настройте приватный адрес на интерфейсе host_1, подключённом к коммутатору",
    "question_type": "practice",
    "explanation": "Интерфейс host_1 в сторону коммутатора должен иметь адрес из частной сети",
    "description": "Сеть уже собрана, настройте только интерфейс host_1",
    "available_host": 0,
    "available_l2_switch": 0,
    "available_l1_hub": 0,
    "available_l3_router": 0,
    "available_server": 0,
    "start_configuration": "b1f4c0de-0000-4000-8000-000000000001",
    "network_scenarios": [
      {
        "requirements": [
          {"host_1": {"ip_check": {"to": "l2sw1", "points": 5}}}
        ],
        "modifications": []
      }
    ]
  }'
```

```json
201 {"message": "Вопрос создан", "id": 42}
```

### Images

Upload first, then reference the returned file name in `images`:

```
POST /quiz/images/upload        (multipart/form-data, field "file")
POST /quiz/upload              (the blueprint route, same handler)
```

Allowed extensions are `bmp`, `png`, `jpg`, `jpeg`; the file is verified with
PIL and re-saved under a uuid name (`front/src/quiz/controller/image_controller.py:32`).
A name in `images` that is not present in `/app/static/quiz_images` fails the
whole request with 400 and `{"details": {"missing": [...]}}`
(`question_facade.py:140-153`).

---

## The requirements format

`practice_question.requirements` is a **list of scenarios**, and grading iterates
that list (`network_upload_service.get_configured_tasks`,
`network_upload_service.py:70`):

```
PracticeQuestion.requirements          list of scenarios
└── scenario
    ├── requirements                   list of check items  → check_task()
    │   ├── {"host_1":   {<check>: …}}                      per-device checks
    │   ├── {"router_2": {<check>: …}}
    │   └── {"network_config": {…}}                          whole-network checks
    └── modifications                  list of edits to the network copy
```

`check_task` (`check_practice_service.py:330`) walks `requirements` as a list of
single-key objects and dispatches on the key prefix:

| Key | Handler |
|---|---|
| `host…`, `server…`, `router…` | `check_host` (`check_practice_service.py:125`) |
| `network…` (`network_config`) | `check_network_configuration` (`check_network_service.py:48`) |
| anything else | silently ignored — no points, no hints |

The device key must be the node id of the **submitted** network
(`node["data"]["id"]`), and one item may carry several checks for one device:

```json
{"host_1": {"ip_check": {"to": "l2sw1", "points": 2},
            "default_gw": {"points": 1}}}
```

### Two accepted field names — read this before you send anything

`question_facade.py:127-131` accepts either:

| Field | Validated | Shape |
|---|---|---|
| `requirements` | yes, by `validate_requirements` (`json_schema_validation.py:4`); a failure is 400 | list of check items, i.e. the **inner** `requirements` list above |
| `network_scenarios` | no | list of full scenarios (the whole envelope above) |

**The validated form is not the form the grader consumes.** `prepare_task` treats
every element of the stored list as a scenario and reads its nested
`requirements`/`modifications` keys. A flat list of check items passes the JSON
schema, but each element yields `{}` as its per-scenario requirements:
`max_score = 0`, `score = 0`, and `is_correct = (0 == 0) = True` — the task is
always marked correct with zero points and no hints. The schema also rejects the
`modifications` key, so a scenario envelope can never be sent through
`requirements`.

**Always send `network_scenarios`.** `requirements` is only useful as the
authority on which check kinds exist (see
[Available requirements](#available-requirements)); `validate_requirements` can be
run locally against a check-item list to pre-validate a task.

The nested `requirements` must itself be a **list**. `check_task` iterates it and
calls `.items()` on each element; a dict raises `AttributeError` and the request
dies with 500.

---

## Available requirements

Every check carries `points` — an integer ≥ 1, mandatory in the schema — and
awards them only when it passes. `network_config` reuses the single `points`
value for whichever field it enables.

### Per-device checks

Dispatch: `check_practice_service.check_host` → `check_host_service`.

| Check | Fields | Passes when | Reference |
|---|---|---|---|
| `cmd.echo-request` | `echo-request` (target node id, required), `direction` `"one-way"`\|`"two-way"` (default `two-way`), `points`, optional `path`, optional `different_paths` | Echo-request packets from the device reach the target in `answer["packets"]`; with `two-way` the reply must come back | `check_host_service.py:510`, `615` |
| `cmd.path` | `required_path` (list of node ids), `points` | The ICMP hop list from the device to the target equals `required_path`. Only checked when the echo passed | `check_host_service.py:251` |
| `cmd.different_paths` | `points` | Request and reply do **not** traverse the same edges in reverse order | `check_host_service.py:159` |
| `ip_check` | `to` (node id), `points` | The device has an interface **directly linked** to `to` whose IP is private (`ipaddress.is_private`) | `check_practice_service.py:184`, `check_host_service.py:155` |
| `mask_check` | `to` (node id), `subnet_mask` (prefix length), `points` | The netmask on the interface of the direct link device↔`to` equals `subnet_mask` | `check_host_service.py:4` |
| `ip_equal` | `to` (node id), `expected_ip` (IPv4), `points` | The device's **own** interface IP on the link to `to` equals `expected_ip` | `check_practice_service.py:270` |
| `equal_vlan_id` | `targets` (list of node ids), `points` | The device and every target share at least one VLAN. Both sides must hang off an `l2_switch` | `check_host_service.py:58` |
| `no_equal_vlan_id` | `targets` (list of node ids), `points` | No shared VLAN with any target | same, `expected_equal=False` |
| `default_gw` | `points` | The device has **no** default gateway. This is an inverse check: setting one loses the points and hints *"Вы настроили маршрут по умолчанию (…), но по условию задания это не требовалось"* | `check_practice_service.py:239` |

Common rules for all of them:

- The device node must exist in the submitted network, otherwise 0 points plus
  a hint (`check_practice_service.py:133`).
- `ip_check`, `ip_equal` and `mask_check` walk `interface[].connect` → the edge →
  its other endpoint, so they only see interfaces with a **direct** edge to
  `to`. A host behind a switch has no such edge and always fails, with a hint
  such as *"Устройство host_1 не подключено к router_1"*.
- `equal_vlan_id` / `no_equal_vlan_id` collect VLAN tags from the `l2_switch`
  ports (`find_connected_switch`, `check_host_service.py:78`). A hub in the path
  means *"Устройство … не подключено к свитчу"* and 0 points. A port may carry a
  list of VLANs.
- `cmd.echo-request` reads the emulation animation, not the network schema, so
  the packets have to be produced by the emulation itself — see
  [add_ping](#scenario-modifications).

### Whole-network checks

Dispatch: `check_network_configuration` (`check_network_service.py:48`). One
`network_config` object per item; `ip_private` and `vlan_id_above` may be
combined, but both award the same `points` value.

| Field | Passes when |
|---|---|
| `ip_private` (bool) + `points` | Every IP on every interface in the whole network is private |
| `vlan_id_above` (int ≥ 1) + `points` | Every VLAN id in the network is strictly greater than the value (`interface.vlan` may be an int or a list) |

### Implemented but outside the schema

These checks exist in the grader and are reachable **only** through
`network_scenarios`, because `validate_requirements` rejects them
(`additionalProperties: false`, and `cmd` requires `echo-request`):

| Check | Fields | Passes when | Reference |
|---|---|---|---|
| `cmd["no-echo-request"]` | target node id, `points` | No ping/tunnel traffic from the device ever reaches the target — an isolation check | `check_host_service.py:577` |
| `cmd["tunnel-echo-request"]` | target, `tunnel_start`, `tunnel_end`, `points`, optional `different_paths` | Request and reply both traverse an IPIP or GRE tunnel between the two routers, and both use the same tunnel type | `check_host_service.py:299` |
| `cmd["vxlan-echo-request"]` | target, `tunnel_start`, `tunnel_end`, `points`, optional `different_paths` | Both directions traverse a VXLAN tunnel (UDP port 4789) | `check_host_service.py:412` |
| `in_one_network_with` | `target`, `points` | The two devices' interface subnets overlap (`IPv4Network(…).overlaps`) | `check_practice_service.py:8` |
| `abstract_ip_equal` | `to`, `expected_equal_with`, `points` | The device's IPs toward `to` intersect `expected_equal_with`'s IPs. A negative `points` is allowed here and penalises | `check_practice_service.py:58` |

Tunnel interaction rules, all verified against `check_task`:

- `tunnel-echo-request` and `vxlan-echo-request` replace `echo-request`; the
  three are **mutually exclusive**. `check_echo_request` and `check_path` only
  follow *consecutive* `ICMP` packets (`check_host_service.py:526`, `:263`), so
  on tunnelled traffic the hop chain breaks and both report
  *"Запрос не достиг <target>"* even though the ping succeeded.
- The tunnel chain may span intermediate routers: `tunnel_used_correctly` hops
  packet by packet and only requires every hop to be a tunnel packet, so
  `router_1 → router_2 → router_4` counts as a tunnel `router_1 → router_4`.
- Both directions must use the **same** tunnel type; GRE in one direction and IPIP
  in the other scores 0 with no hint about the mismatch.
- `check_vxlan_echo_request.trace_path` matches tunnel packets through
  `("UDP" in ptype and "> 4789 in ptype")` (`check_host_service.py:436`) — the
  second operand is a non-empty **string literal**, not a comparison, so the
  condition is true for *every* UDP packet. The VXLAN tunnel assertion itself is
  correct (`"> 4789" in ptype`, `:459`); only the ICMP hop walk is too lax.

---

## Examples

All examples below use the topology the requirements refer to: `host_1` and
`host_2` behind `l2sw1`, with `host_1` also directly linked to `router_1` (and
`host_2` behind a second router) where a path or an address check needs it.

### IP addressing

```json
{"network_scenarios": [
  {
    "requirements": [
      {"host_1": {
         "ip_equal": {"to": "router_1", "expected_ip": "10.0.0.1", "points": 4},
         "mask_check": {"to": "router_1", "subnet_mask": 24, "points": 3},
         "default_gw": {"points": 2}}},
      {"network_config": {"ip_private": true, "points": 3}}
    ],
    "modifications": []
  }
]}
```

`default_gw` awards its points when the host has *no* gateway configured — it is
the check for "do not set anything you were not asked for".

### VLAN

```json
{"network_scenarios": [
  {
    "requirements": [
      {"host_1": {"equal_vlan_id":   {"targets": ["host_2"], "points": 5}}},
      {"host_2": {"no_equal_vlan_id": {"targets": ["host_1"], "points": 5}}},
      {"network_config": {"vlan_id_above": 100, "points": 2}}
    ],
    "modifications": []
  }
]}
```

The two host checks are complementary: same VLAN for the pair that must talk,
different VLAN for the pair that must not.

### Connectivity through a path

```json
{"network_scenarios": [
  {
    "requirements": [
      {"host_1": {"cmd": {
         "echo-request": "host_2",
         "direction": "two-way",
         "points": 5,
         "path": {"required_path": ["router_1", "router_2"], "points": 6},
         "different_paths": {"points": 4}}}}
    ],
    "modifications": [
      {"add_ping": {"from": "host_1", "to": "host_2"}}
    ]
  }
]}
```

- `required_path` lists the hops **between** the device and the target, both
  endpoints excluded: `check_path` builds the observed list as
  `[device, *targets of every ICMP packet]` and compares its middle slice, so for
  `host_1 → router_1 → router_2 → host_2` the answer is
  `["router_1", "router_2"]`.
- `path` and `different_paths` points are only considered when the echo check
  itself passed (`check_host_service.py:631-651`).
- `add_ping` is mandatory here — see [the trap about stripped jobs](#traps).

### Grading a modified topology

```json
{"network_scenarios": [
  {
    "requirements": [
      {"host_1": {"cmd": {"echo-request": "host_2", "direction": "two-way", "points": 5}}}
    ],
    "modifications": [
      {"add_ping": {"from": "host_1", "to": "host_2"}},
      {"remove_edge": {"from": "router_1", "to": "host_2"}}
    ]
  }
]}
```

The scenario grades the student's network *after* the task's own edits:
`add_ping` produces the traffic (the student's ping jobs are stripped — see
[traps](#traps)) and `remove_edge` deletes a link before the emulation. Pin all
three down consistently: the ping source `from`, the echo target `to`, and the
edge you remove.

If the topology has two independent routes, add
`"different_paths": {"points": 4}` to `cmd` to require the reply to come back
along the other one; on a single-route topology that check can never pass
(*"Путь ICMP Echo Reply полностью совпадает с ICMP Echo Request (в обратную
сторону), а должен быть другим"*).

### Isolation (schema-external check)

`no-echo-request` is rejected by `validate_requirements`, so this scenario only
works through `network_scenarios`.

```json
{"network_scenarios": [
  {
    "requirements": [
      {"host_1": {"cmd": {"no-echo-request": "host_2", "points": 5}}}
    ],
    "modifications": []
  }
]}
```

No traffic is generated, so the check passes trivially unless the student's own
configuration produces a ping that reaches the target.

### Several scenarios, summed scores

```json
{"network_scenarios": [
  {
    "requirements": [{"host_1": {"ip_check": {"to": "router_1", "points": 2}}}],
    "modifications": []
  },
  {
    "requirements": [{"host_1": {"ip_check": {"to": "router_1", "points": 2}}}],
    "modifications": [{"remove_edge": {"from": "host_1", "to": "router_1"}}]
  }
]}
```

Each scenario is graded on its own copy of the student's network and the points
add up, so repeating a check under different `modifications` grades the same
requirement against several topologies. The second scenario above cannot pass:
the edge `ip_check` needs has been removed. A modification applied to a scenario
prefixes that scenario's hints with `Для сети с изменениями […]: `
(`session_question_service.py:321`).

---

## Scenario modifications

Only valid inside a `network_scenarios` envelope, applied to the copy of the
student's network before emulation (`get_configured_tasks`,
`network_upload_service.py:70`). Exactly one key per modification object.

| Modification | Arguments | Effect |
|---|---|---|
| `remove_edge` | `{"id": "<edge id>"}` or `{"from": "<node>", "to": "<node>"}` | Deletes the edge from the graded copy. The pair form matches an edge in either direction |
| `add_ping` | `{"from": "<node>", "to": "<node>"}` | Appends a ping job from `from` to the first IP of `to`'s first interface. Silently skipped if `to` has no interfaces or no IP |

Failures are raised, not validated: an unknown modifier, two keys in one
modification, or a `remove_edge` that matches nothing raises `ValueError` inside
`prepare_task`, which no endpoint catches — the answer request returns 500.
`remove_edge` records what it removed for the hint prefix
(`{"remove_edge": {"id": …, "between": "host_1 ↔ l2sw1"}}`).

---

## Scoring and hints

- `max_score` per scenario = `calculate_max_score`
  (`quiz/util/dto.py:294`): the sum of every **positive** `points` in the nested
  structure. `cmd.points`, `cmd.path.points` and `cmd.different_paths.points`
  therefore all count towards the maximum.
- The session score is the sum over scenarios and clamped to ≥ 0;
  `is_correct = score == max_score` (`session_question_service.py:331`, `:333`).
- Every failed check appends a Russian-language hint that is shown to the
  student. If the score is below the maximum and nothing produced a hint, the
  generic *"По вашему решению не предусмотрены подсказки"* is added
  (`session_question_service.py:402`).
- The student sees `score`, `max_score`, the question `explanation` and the hints
  (`PracticeAnswerResultDto`, `dto.py:278`).

Grading is a pure function of `(requirements, animation)` — no Mininet, no root,
no celery — which is what makes it cheap to test offline.

---

## How a student answer is graded

```
student network copy (network.guid)
   │
   ├─ synchronous  POST /quiz/session/answer?id=<session_question_id>   {"answer": "<network_guid>"}
   │    controller → session_question_service.answer_on_session_question
   │    prepare_task  → one (network, requirements, modifications) per scenario
   │    create_emulation_task  (front/src/tasks.py:131, blocking, 120 s timeout)
   │    check_task    → points + hints, stored on SessionQuestion
   │    200 {"score": …, "max_score": …, "explanation": …, "hints": […]}
   │
   └─ asynchronous  POST /quiz/session/check_network_task?id=<session_question_id>
        200 immediately, then celery `tasks.check_task_network`
        (`front/src/tasks.py:65`) grades and writes the result
        read later through GET /quiz/session/result
```

The answer is always the **student's network guid**, never the schema
(`front/src/static/quiz/session_scripts.js:309`).

---

## Response codes

`POST /quiz/question/create`:

| Code | Body | Cause |
|---|---|---|
| 201 | `{"message": "Вопрос создан", "id": 42}` | Created; `id` is an int, or a list of ints for a batch |
| 400 | `{"message": "Ваши требования не удовлетворяют шаблону.", "details": {"message": "Ошибка валидации: …"}}` | `requirements` failed `validate_requirements` |
| 400 | `{"message": "Некоторые изображения отсутствуют", "details": {"missing": [...]}}` | A name in `images` is not on disk |
| 400 | `{"message": "Нельзя создать вопрос с данными параметрами в данном разделе", "id": …}` | Unknown `question_type`, or every item of a batch failed |
| 403 | `{"message": "Нельзя создать вопрос по чужому разделу", "id": …}` | The section belongs to another user |
| 404 | `{"message": "Сеть <guid> не найдена"}` | `start_configuration` does not resolve |
| 500 | HTML error page | Missing `text`/`question_type`/`start_configuration`, a dict instead of a list in the nested `requirements`, or a commit failure — the facade reads these keys with `[]` outside its `try` |
| 500 | HTML error page | **Missing or soft-deleted section.** The facade returns `(None, 404)`, and the controller tests `"message" in res[0]` before anything else (`question_controller.py:28`) → `TypeError: argument of type 'NoneType' is not iterable`. The intended `{"message": "Не существует данного раздела"}` is unreachable |

`GET /quiz/question/all?id=<section_id>` answers with `QuestionForEditorDto`,
which carries `question_id` and `question_text` only — no `question_type`, no
`start_configuration`, no `requirements` (`dto.py:550`).

---

## Traps

1. **Flat `requirements` is a silent always-correct task.** The schema validates
   it, `prepare_task` finds no nested `requirements`, and grading returns
   0/0 → `is_correct = True` with no hints. Send `network_scenarios`.
2. **The nested `requirements` must be a list.** A dict is a 500
   (`AttributeError` in `check_task`).
3. **Neither field present is a 500.** `question_dict["network_scenarios"]` is
   read with `[]` (`question_facade.py:131`).
4. **The student's own ping jobs are removed before emulation.**
   `clean_schema` drops `job_id` 1, 2, 3, 4, 200, 201 (ping variants and
   TCP/UDP ping/server, `network_upload_service.py:47`). Any connectivity check
   therefore needs an `add_ping` modification, otherwise the answer is graded
   against an empty packet list ("Вы не отправляете пакетов по сети").
5. **`default_gw` is an inverse check** — points for *not* having a gateway.
6. **`ip_check`, `ip_equal` and `mask_check` need a direct edge** between the
   device and `to`; a shared switch is not enough.
7. **`equal_vlan_id` needs an `l2_switch`**, not a hub, on both sides.
8. **Switches and hubs cannot be graded.** `check_task` has no branch for them
   and the schema forbids the keys, so `{"switch_1": …}` is either rejected or
   silently dropped — use `network_config` instead.
9. **Validation never touches `network_scenarios`**, so it is the only way to
    use `no-echo-request`, `tunnel-echo-request`, `vxlan-echo-request`,
    `in_one_network_with` and `abstract_ip_equal` — at the cost of unvalidated
    input.
10. **`available_*` default to `""`**, which the palette script reads as `NaN`.
11. **A batch is partially committed.** Failures are logged
    (`question_facade.py:178`) and only the successful ids are returned.
12. **A commit failure still reports "Вопрос создан"** with HTTP 500 and
    `"id": null` — the controller's fall-through branch (`question_controller.py:47`).
13. **`points` is mandatory in every check**, and `additionalProperties` is
    strict everywhere — a typo in a key name is a 400 with the offending key
    named.
14. **A missing section is a 500, not a 404.** `create_single_question` returns
    `(None, 404)`, but the controller's first branch does
    `"message" in res[0]` on that `None` (`question_controller.py:28`) and dies
    with a `TypeError` before it can answer 404. Omitting `?id=` avoids the
    lookup and quietly stores `section_id = NULL`.
15. **A 400 for a missing image still creates the task network copy**, because
    the copy is committed before the image check (`question_facade.py:122` vs
    `140-153`). Retrying the request creates another copy.

---

## Verification

Every example in this document was executed against the real code, without a
database or Mininet:

- `validate_requirements` accepts all check-item lists shown here and rejects the
  `network_scenarios` envelope, `abstract_ip_equal`, `in_one_network_with`,
  `no-echo-request`, `tunnel-echo-request`, `vxlan-echo-request`, unknown device
  keys, missing `points` and an invalid `direction`;
- `check_task` was run over synthetic networks and animations and produced the
  scores and hints quoted above, including the `0/0` result for the flat
  `requirements` form and the `path` / `default_gw` / `add_ping` semantics;
- `prepare_task` was run to confirm that `clean_schema` drops ping jobs, that
  `add_ping` re-adds one, and the `ValueError` cases of
  [Scenario modifications](#scenario-modifications).

The payload of [Minimal request](#minimal-request) and the `?id=` behaviours were
additionally exercised over HTTP against a running stand: 201 for a valid
section, 403 for a section of another user, 500 for an unknown section, and 201
with a `NULL` `section_id` when `id` is omitted.

Grading has no external dependency, so a new requirement kind can be checked the
same way: call `check_task(requirements, answer)` with a hand-built
`{"nodes": [...], "edges": [...], "packets": [...]}` document.

`create_practice_task.py` in the repository root is a worked example that does
all of it: it builds the payload of a real task, grades a synthetic answer and
two broken ones offline (`--self-test`), and posts the question to a stand
(`--section-id`, `--email`, `--password`).
