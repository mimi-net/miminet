# DATA-FLOW.md — data flow

How data moves between the browser, the two halves and the database. It is a
section of the architecture reference, see
[ARCHITECTURE.md](../ARCHITECTURE.md). The modules named here are described in
[MODULES.md](MODULES.md); the exchanges and queues are in
[SYSTEM.md](SYSTEM.md#exchanges-and-queues).

## Contents

- [The network document — the shared contract](#the-network-document--the-shared-contract)
- [Interactive emulation — asynchronous, poll-based](#interactive-emulation--asynchronous-poll-based)
- [Inside one emulation](#inside-one-emulation)
- [Quiz grading — synchronous](#quiz-grading--synchronous)
- [Packet capture and MimiShark](#packet-capture-and-mimishark)
- [AI network generation](#ai-network-generation)
- [Authentication](#authentication)

---

## The network document — the shared contract

One JSON document is the only thing that crosses the RabbitMQ boundary. It is
stored as text in `Network.network` (`front/src/miminet_model.py:62`) and typed
by the dataclasses in `back/src/network_schema.py`.

```jsonc
{
  "nodes": [{
    "config": { "label": "host_1", "type": "host", "stp": 0, "priority": null, "default_gw": "" },
    "data":   { "id": "host_1", "label": "host_1" },
    "classes": ["host"],
    "interface": [{
      "connect": "edge_abc", "id": "iface_1", "name": "host_1_1",
      "ip": "10.0.0.1", "netmask": 24,
      "vlan": null, "type_connection": null,
      "vxlan_vni": null, "vxlan_connection_type": null, "vxlan_vni_to_target_ip": null
    }],
    "position": { "x": 36.2, "y": -10.4 }
  }],
  "edges": [{ "data": { "id": "edge_abc", "source": "host_1", "target": "l2sw1",
                        "loss_percentage": 0, "duplicate_percentage": 0 } }],
  "jobs": [{ "id": "…", "level": 0, "job_id": 1, "host_id": "host_1",
             "print_cmd": "ping -c 1 10.0.0.2",
             "arg_1": "10.0.0.2", "arg_2": "", "arg_3": "", "arg_4": "", "arg_5": "" }],
  "config": { "zoom": 2, "pan_x": 0, "pan_y": 0 },
  "packets": "",
  "pcap": []
}
```

Ownership by field:

| Field | Written by | Read by |
|---|---|---|
| `nodes`, `edges`, `jobs` | the editor (`front/src/miminet_network.py:397`), device configurators (`configurators.py`) | `network_topology.build`, `jobs.py` |
| `nodes[].position`, `config.zoom/pan_x/pan_y` | `move_nodes`, `update_network_config` | Cytoscape only — never emulated |
| `edges[].data.loss_percentage`, `duplicate_percentage` | the editor, defaulted on save (`front/src/miminet_network.py:402`) | `pkt_parser.packet_parser` |
| `packets` | `tasks.save_simulate_result` from the back result | `web_network` / `check_simulation` |
| `pcap` | derived from the `static/pcaps/<guid>/` directory listing | the editor and MimiShark |

Back tolerates more than front produces: `run_miminet` loads with
`unknown="include"` (`back/src/tasks.py:57`) and filters out nodes whose
`config.type` is not a `NodeType` member (`back/src/tasks.py:19`), so a `textbox`
annotation or a device the worker does not know about is skipped instead of
failing the run.

---

## Interactive emulation — asynchronous, poll-based

The path a student takes when they press *Emulate* in the editor.

```
browser                front (Flask + celery)          rabbitmq        back (celery)
   │                          │                            │               │
   │ POST /post_nodes_edges   │                            │               │
   │  (nodes, edges, jobs)    │                            │               │
   │─────────────────────────▶│ persist Network.network     │               │
   │                          │ drop previous Simulate rows │               │
   │                          │                            │               │
   │ POST /run_simulation     │                            │               │
   │  ?guid=…                 │ insert Simulate + SimulateLog, task_guid=uuid4
   │─────────────────────────▶│ send_task tasks.mininet_worker
   │                          │  args=[network JSON]        │               │
   │                          │  task_id=task_guid          │               │
   │                          │  headers={network_task_name: │
   │                          │            "tasks.save_simulate_result"}
   │◀── 201 {simulation_id} ──│──────── x-consistent-hash ─▶│──────────────▶│
   │                          │                            │               │ run_miminet
   │                          │                            │               │  emulate()
   │                          │                            │               │   ├ pre-cleanup (mn -c)
   │                          │                            │               │   ├ build topology
   │                          │                            │               │   ├ start + readiness gate
   │                          │                            │               │   ├ execute jobs
   │                          │                            │               │   ├ stop
   │                          │                            │               │   └ pcap → animation
   │                          │                            │◀─ result ─────│ send_task
   │                          │◀── network-results-exchange │               │  tasks.save_simulate_result
   │                          │     write static/pcaps/<guid>/<iface>.pcap
   │                          │     Simulate.packets = animation, ready = True
   │                          │     SimulateLog.ready = True
   │                          │                            │               │
   │ GET /check_simulation    │                            │               │
   │  ?simulation_id&network_guid                          │               │
   │─────────────────────────▶│ 210 "in progress" | 200 {packets, pcaps}
   │◀─────────────────────────│                            │               │
   │ miminet_animation.js plays `packets`                  │               │
```

Details that matter:

- **The reply route is carried in a task header.** Front sets
  `headers={"network_task_name": "tasks.save_simulate_result"}`
  (`front/src/miminet_simulation.py:64`). Back reads it back
  (`back/src/tasks.py:136`) and re-publishes the result itself. When the header
  is absent — the quiz path — back just returns the value and nobody listens.
- **Pcaps travel as task arguments, not files.** The result payload is
  `(animation_json, [(bytes, name), …])`; the front task writes each blob to
  `static/pcaps/<guid>/<name>.pcap` (`front/src/tasks.py:49`).
- **A missing row is not an error.** If the network or its `SimulateLog` was
  deleted while the emulation was running, `save_simulate_result` returns
  silently (`front/src/tasks.py:27`, `front/src/tasks.py:32`, `front/src/tasks.py:37`).
- **`Simulate` rows are one-per-network-in-flight.** Starting a simulation
  deletes every previous row for that network
  (`front/src/miminet_simulation.py:38`), so the browser only ever polls the
  newest one. Editing the topology through `post_nodes_edges` clears them too.
- **`check_simulation` answers 210 while running**, which the editor treats as
  "keep polling".

---

## Inside one emulation

`emulate()` (`back/src/emulator.py:91`) is the whole lifecycle:

1. **Limits.** At most 30 jobs, and the sum of `sleep` durations at most 60 s
   (`back/src/emulator.py:106`); a network with zero jobs returns immediately.
2. **Pre-cleanup.** `mn -c`, then kill this worker's own leftover `mimidump` /
   `tcpdump` children and remove `/tmp/capture_*.pcapng`
   (`back/src/emulator.py:36`). A wedged teardown from a previous run would
   otherwise leave the new run with dead captures.
3. **Build and start.** `MiminetTopology(network)` → `MiminetNetwork(topo, network)`
   → `net.start()`. `start()` calls ipmininet's start, then `setup_vlans`,
   `setup_vtep_interfaces`, disables IPv6, and waits for readiness.
4. **Readiness gate** (`back/src/network.py:62`) — polling, not sleeping a fixed
   amount, until all three hold: every interface capture is confirmed live,
   every STP/RSTP switch reports all ports forwarding, every VXLAN underlay
   endpoint is reachable from its local router. A capture that raced interface
   startup is restarted once after `MIMINET_CAPTURE_RESTART_GRACE` seconds.
5. **Jobs**, ordered by `job_id // 100` descending so server jobs bind before
   clients act (`back/src/emulator.py:135`). After a job in
   `SERVER_SETTLE_JOBS` (`200`, `201`, `203`) the emulator sleeps
   `MIMINET_SERVER_SETTLE` seconds so the listener is actually bound
   (`back/src/emulator.py:171`).
6. **Stop**, in a `finally`, and `stop()` is idempotent via a `_stopped` guard
   (`back/src/network.py:40`).
7. **Animation.** For every link endpoint, read the outbound pcapng, parse it in
   both directions, and concatenate (`back/src/emulator.py:239`). Then group
   packets into frames of 14 ms (`back/src/emulator.py:322`).

`run_miminet` wraps all of that in up to four attempts. A network that declares
jobs but produced no meaningful host traffic is retried
(`back/src/tasks.py:69`, `_has_meaningful_packets` at `back/src/tasks.py:83`):
ARP counts as meaningful, STP/RSTP/LLC alone does not, and a lone DHCP Discover
without any server response does not either. After four failures it returns an
empty animation rather than raising.

Each animation packet is a self-describing dict (`back/src/pkt_parser.py:214`):

```jsonc
{
  "data":   { "id": "<uuid>", "label": "ICMP Echo Request", "type": "packet" },
  "config": { "type": "ICMP Echo Request", "path": "<edge_id>",
              "source": "<node label>", "target": "<node label>",
              "loss_percentage": 0, "duplicate_percentage": 0 },
  "timestamp": "1712345678901234"
}
```

`path` is an edge id, so the browser can look the node pair up in the topology
it already has. Loss and duplication are carried per packet rather than applied
at capture time — the animation is a record of what *would* have crossed the
link, so a lab can replay a lossy link without re-running it.

---

## Quiz grading — synchronous

Practice tasks in the quiz need the emulation result *inside* the HTTP request,
so this path blocks instead of polling.

```
browser                front (Flask + celery)          rabbitmq        back
   │ POST /quiz/session/answer                        │               │
   │─────────────────────────▶ controller             │               │
   │                          facade: start_session / handle_exam_answer
   │                          service.session_question_service
   │                          service.network_upload_service
   │                            → insert SessionQuestion + PracticeQuestion
   │                          send_task tasks.perform_task_check ───────▶│
   │                                                           task-checking-queue
   │◀── 200 (answer accepted, grading continues in background) ───────  │
   │                          │                            │               │
   │                          │ celery picks it up         │               │
   │                          │ create_emulation_task() ───┼─ x-consistent-hash ─▶│
   │                          │ AsyncResult.wait(timeout=120) ◀── result ──────│
   │                          │ answer_on_exam_question()  │               │
   │                          │   check_practice_service.check_task()
   │                          │ SessionQuestion.result updated
```

`front/src/tasks.py:131` `create_emulation_task` is the blocking bridge: it
sends `tasks.mininet_worker` **without** the `network_task_name` header, so back
returns the animation in the task result, and the front worker blocks on
`AsyncResult.wait(timeout=120)`. Exceeding the timeout raises.

Grading itself is a pure function of `(requirements, animation)`:
`check_practice_service.check_task` (`front/src/quiz/service/check_practice_service.py:330`)
dispatches to `check_host_service` for per-device assertions and
`check_network_service` for whole-network ones. No Mininet, no root, no worker —
which is why the browser-free front tests can cover it. What a requirement may
contain, and how a task is created over the API, is documented in
[../QUIZ.md](../QUIZ.md).

The same task supports a headless variant: with `session_question_id=None` the
grading writes a result file instead of a database row
(`front/src/quiz/service/session_question_service.py:210`).

---

## Packet capture and MimiShark

`mimidump` writes two files per interface into the node working directory:
`capture_<iface>.pcapng` (bidirectional) and `capture_<iface>_out.pcapng`
(outbound). Only the outbound file feeds the animation; both are returned to
front. `back/src/net_utils/captures.py` is the single place that knows this
layout — never build a capture path inline.

MimiShark is a per-interface packet inspector, reached from any device page via
`/host/mimishark?guid=…&iface=…` (and the `router`/`server`/`hub`/`switch`
variants). It reads `static/pcaps/<guid>/<iface>.pcap`, converts it to JSON on
first view via `pcap_parser.from_pcap_to_json`, caches the JSON next to the pcap,
and renders `mimishark.html`.

---

## AI network generation

`POST /ai/generate-task` (`front/src/ai_generate.py:435`) asks an LLM for a
topology matching the requested technologies and difficulty, then repairs and
validates the answer before it is ever stored: `_fix_topology`
(`front/src/ai_generate.py:316`) patches what the model got structurally wrong,
`_validate_topology` (`front/src/ai_generate.py:348`) returns the list of
problems that remain. Provider calls are abstracted behind `_call_ai`, which
dispatches to the RouterAI or Yandex implementation.

---

## Authentication

`miminet_auth.py` owns four OAuth providers (VK, Google, Yandex, Telegram) and
two session mechanisms that coexist: `flask_login` sessions for HTML pages and
`flask_jwt_extended` access/refresh cookies for the XHR API. JWT error handlers
branch on `is_api_request()` (`front/src/app.py:501`) so a dead token yields JSON
for XHR and a redirect to the login page for a browser navigation.

Cookie scope is derived from `JWT_COOKIE_DOMAIN`, falling back to
`.${BASE_DOMAIN}`; an explicit empty value means host-only cookies, which is what
the IP/localhost test stand needs. `clear_stale_scope_jwt_cookies`
(`front/src/miminet_auth.py:93`) clears cookies left over from an older scope so a
domain change does not lock users out.