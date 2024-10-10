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

RESULT_QUEUES_NAMES = ["common-results-queue"]

RESULT_ROUTING_KEY = "result-routing-key"

QUEUES = [
    Queue(name, exchange=NETWORK_RESULTS_EXCHANGE, routing_key=RESULT_ROUTING_KEY)
    for name in RESULT_QUEUES_NAMES
]

app.conf.task_queues = QUEUES
app.config_from_object(celeryconfig)
app.conf.task_ignore_result = True
app.conf.broker_connection_retry_on_startup = True
