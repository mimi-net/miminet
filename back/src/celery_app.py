# 'max_retries': 3,
# 'interval_start': 0,
# 'interval_step': 0.2,
# 'interval_max': 0.2,
# 'retry_errors': None,

import os

import celeryconfig
from celery import Celery
from dotenv import load_dotenv
from kombu import Exchange, Queue

load_dotenv()

app = Celery(__name__)

ROUTING_KEY = "1"

QUEUES_NAMES = [""]

if (QUESES_NAMES_ENV := os.getenv("queue_names")) is not None:
    QUEUES_NAMES = QUESES_NAMES_ENV.split(",")

NUMBER_OF_QUEUES_FOR_NODE = len(QUEUES_NAMES)

EXCHANGE_TYPE = "x-consistent-hash"

EXCHANGE_NAME = os.getenv("exchange_name")

DEFAULT_APP_EXCHANGE = Exchange(EXCHANGE_NAME, type=EXCHANGE_TYPE)

QUEUES = (
    Queue(name, exchange=DEFAULT_APP_EXCHANGE, routing_key=ROUTING_KEY)
    for name in QUEUES_NAMES
)

app.conf.task_default_exchange = DEFAULT_APP_EXCHANGE
app.conf.task_queues = QUEUES
app.config_from_object(celeryconfig)
