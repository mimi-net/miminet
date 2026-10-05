# SYSTEM.md — system shape

How the two halves are deployed, what can reach what, and how the halves talk to
each other. It is a section of the architecture reference, see
[ARCHITECTURE.md](../ARCHITECTURE.md).

## Contents

- [Topology](#topology)
  - [Reachability](#reachability)
  - [nginx configuration](#nginx-configuration)
- [Processes per container](#processes-per-container)
- [Exchanges and queues](#exchanges-and-queues)

---

## Topology

Miminet is two independent halves wired together through RabbitMQ. Neither half
imports the other; they exchange a single JSON document.

```
  browser
     │  HTTP :80
     ▼
  ┌──────────────┐
  │    nginx     │
  └──────────────┘
         │ uwsgi_pass miminet:80
         ▼
  ┌────────────────────────────────────────┐
  │front container (miminet)               │
  │  uwsgi  → front/src/app.py (Flask)     │
  │  celery → front/src/tasks.py           │
  └────────────────────────────────────────┘
       │               │               │
       │ SQLAlchemy    │ AMQP          │ volumes
       ▼               ▼               ▼
 ┌───────────┐   ┌───────────┐   static/pcaps, images, avatar,
 │ postgres  │   │ rabbitmq  │   svg, video, assets, quiz_images
 └───────────┘   └─────┬─────┘
                       │ AMQP
                       ▼
  ┌───────────────────────┐
  │back container(s)      │
  │  celery → back/src    │
  │  mininet + OVS        │
  │  + mimidump           │
  └───────────────────────┘
```

**nginx is a pure reverse proxy in front of the front container.** It forwards
every request to `miminet:80` and opens no database or broker connection of its
own — postgres is reached only by the front container, over SQLAlchemy.

`front/docker-compose.yml` defines `miminet`, `nginx`, `postgres`, `rabbitmq`.
`back/docker-compose.yml` defines a single `celery` service with
`network_mode: host` and `privileged: true` — Mininet and OVS need the host
network namespace and kernel access.

The module map is in [MODULES.md](MODULES.md); the request/response sequences
that cross this topology are in [DATA-FLOW.md](DATA-FLOW.md).

### Reachability

| From | To | How | Network |
|---|---|---|---|
| nginx | miminet | `uwsgi_pass miminet:80` (`front/default.conf.template:17`, `front/default.conf.template:24`) | `miminet_network` |
| miminet | postgres | SQLAlchemy/psycopg2, `POSTGRES_HOST=postgres` | `miminet_network` |
| miminet | rabbitmq | AMQP, `amqp_urls` | `rabbitmq_network` |
| rabbitmq | back | AMQP | host networking |
| back | — | nothing — privileged, host netns, talks to OVS and the kernel | host |

The compose file splits the front stack over two bridges, which is what makes the
table above unambiguous: `miminet` is the **only** container on
`rabbitmq_network`, while `nginx` and `postgres` sit on `miminet_network` only.
So the broker is reachable from the front half through one container, and nginx
is never a peer of it.

The static volumes bind-mount `./src/static/{images,svg,avatar,video,pcaps,assets,quiz_images}`
into the front container, which is why a pcap written by
`save_simulate_result` is immediately servable as `/static/pcaps/…` — no restart,
no upload step.

### nginx configuration

`front/default.conf.template` is mounted into the nginx container's
`templates/` directory, so the image substitutes the `.env` variables into it.
It declares one active server block on port 80 with two locations:

- `location /ai/` — same upstream, but `uwsgi_read_timeout` and
  `uwsgi_send_timeout` raised to 300 s, because AI generation is slow enough to
  outlast the default timeouts.
- `location /` — everything else, default timeouts.

`server_name` is commented out, so the block is the default server for port 80
and catches every `Host`. The separate `QUIZ_DOMAIN` vhost that would proxy to a
`quiz` service is commented out too (`front/default.conf.template:1-9`); the
quiz is served by `miminet` like everything else.

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