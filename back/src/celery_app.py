# default retry policy:
# 'max_retries': 3,
# 'interval_start': 0,
# 'interval_step': 0.2,
# 'interval_max': 0.2,
# 'retry_errors': None,

import os
import celeryconfig

from celery import Celery
from kombu import Exchange, Queue

app = Celery(__name__)

ROUTING_KEY = "1"

QUESES_NAMES = os.getenv("queue_names").split(",")

NUMBER_OF_QUEUES_FOR_NODE = len(QUESES_NAMES)

EXCHANGE_TYPE = "x-consistent-hash"

EXCHANGE_NAME = os.getenv("exchange_name")

DEFAULT_APP_EXCHANGE = Exchange(EXCHANGE_NAME, type=EXCHANGE_TYPE)

QUEUES = (Queue(name) for name in QUESES_NAMES)

app.conf.task_default_exchange = "default"
app.conf.task_queues = QUEUES
app.config_from_object(celeryconfig)

with app.connection() as conn:
    # Create queues and exchange
    ch = conn.channel()
    DEFAULT_APP_EXCHANGE.declare(channel=ch)
    for queue in QUEUES:
        queue.declare(channel=ch)
        queue.bind_to(
            channel=ch, exchange=DEFAULT_APP_EXCHANGE, routing_key=ROUTING_KEY
        )
