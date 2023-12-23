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
from kombu import Exchange

load_dotenv()

app = Celery(__name__)

EXCHANGE_TYPE = "x-consistent-hash"

EXCHANGE_NAME = os.getenv("exchange_name")

DEFAULT_APP_EXCHANGE = Exchange(EXCHANGE_NAME, type=EXCHANGE_TYPE)

app.config_from_object(celeryconfig)
