# SYSTEM.md — system shape

How the two halves are deployed and how they reach each other. It is a section
of the architecture reference, see [ARCHITECTURE.md](../ARCHITECTURE.md).

## Contents

- [Topology](#topology)
- [Processes per container](#processes-per-container)
- [Exchanges and queues](#exchanges-and-queues)

---

## Topology

Miminet is two independent halves wired together through RabbitMQ. Neither half
imports the other; they exchange a single JSON document.

```
  browser
     │  HTTP
     ▼
  ┌──────────────┐        ┌────────────┐
  │    nginx     │───────▶│  postgres  │
  └──────────────┘        └────────────┘
         │                      ▲
         ▼                      │ SQLAlchemy
  ┌────────────────────────────────────────┐
  │ front container                        │
  │   uwsgi  → front/src/app.py (Flask)    │
  │   celery  → front/src/tasks.py         │
  └────────────────────────────────────────┘
         │                      ▲
         │ AMQP                │ SQLAlchemy
         ▼                      │
  ┌────────────┐         ┌─────┴──────────────┐
  │  rabbitmq  │────────▶│ back container(s)  │
  └────────────┘         │  celery → back/src │
                         │  mininet + OVS     │
                         │  + mimidump        │
                         └────────────────────┘
```

`front/docker-compose.yml` defines `miminet`, `nginx`, `postgres`, `rabbitmq`.
`back/docker-compose.yml` defines a single `celery` service with
`network_mode: host` and `privileged: true` — Mininet and OVS need the host
network namespace and kernel access.

The module map is in [MODULES.md](MODULES.md); the request/response sequences
that cross this topology are in [DATA-FLOW.md](DATA-FLOW.md).

---

## Processes per container

| Container | Processes | Started by |
|---|---|---|
| `front` | uwsgi (Flask) + one celery worker on `common-results-queue,task-checking-queue` | `front/run_app.sh:10`, `front/run_app.sh:13` |
| `back` | OVS startup + `mn -c` cleanup + one celery worker on `${queue_names}` | `back/ovs-init.sh`, `back/ENTRYPOINT.sh:18` |

`back/.env` sets `queue_names=queue1,queue2,queue3` with `celery_concurrency=1`,
so a single back container consumes three queues serially. Scaling out means
more containers, each bound to its own queue name.

The back worker is started with guard rails — `--time-limit`,
`--soft-time-limit` and `--max-tasks-per-child` (`back/ENTRYPOINT.sh:21`) — so a
single wedged emulation cannot pin the pool forever.

---

## Exchanges and queues

Three hops, all declared in the two `celery_app.py` files:

| Hop | Exchange | Type | Routing key | Queue | Producer → Consumer |
|---|---|---|---|---|---|
| Request | `$exchange_name` (`default_exchange`) | `x-consistent-hash` | `str(uuid.uuid4())` | one of `$queue_names` | front → back |
| Result | `network-results-exchange` | `direct` | `result-routing-key` | `common-results-queue` | back → front |
| Grading job | `task-checking-exchange` | `direct` | `task-checking-routing-key` | `task-checking-queue` | front → front |

The request exchange is `x-consistent-hash`, and the routing key is a fresh
UUID per request (`front/src/miminet_simulation.py:60`,
`front/src/tasks.py:142`). Consistent hashing over a random key spreads every
emulation uniformly across the bound queues, which is what keeps one back
worker from taking all the load. Back binds every queue with the fixed routing
key `"1"` (`back/src/celery_app.py:18`, `back/src/celery_app.py:35`) — on a
consistent-hash exchange the queue's own key only matters for binding, not for
routing.

Broker environment variables are **lowercase**: `amqp_urls`, `rpc_urls`,
`exchange_name` (front), `queue_names` (back). There is no `AMQP_URL`. Front and
back must agree on `exchange_name`, or neither will see the other's requests.