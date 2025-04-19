# default retry policy:
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

EXCHANGE_TYPE = "x-consistent-hash"

SEND_NETWORK_EXCHANGE_NAME = os.getenv("exchange_name")

SEND_NETWORK_EXCHANGE = Exchange(SEND_NETWORK_EXCHANGE_NAME, type=EXCHANGE_TYPE)

NETWORK_RESULTS_EXCHANGE = Exchange("network-results-exchange", type="direct")
TASK_CHECKING_EXCHANGE = Exchange("task-checking-exchange", type="direct")

QUEUES = [
    Queue(
        "common-results-queue",
        exchange=NETWORK_RESULTS_EXCHANGE,
        routing_key="result-routing-key",
    ),
    Queue(
        "task-checking-queue",
        exchange=TASK_CHECKING_EXCHANGE,
        routing_key="task-checking-routing-key",
    ),
]

app.conf.task_queues = QUEUES
app.config_from_object(celeryconfig)
app.conf.task_ignore_result = True
app.conf.broker_connection_retry_on_startup = True
