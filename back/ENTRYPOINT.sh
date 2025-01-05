#!/bin/bash

exec python3 -m celery -A celery_app worker --loglevel=info --concurrency=${celery_concurrency} -Q ${queue_names}
