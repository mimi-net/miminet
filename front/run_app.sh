#!/bin/sh

# Use default 'prod' if MODE is not set
MODE="${MODE:-prod}"

echo "[!] Running in $MODE mode"
python3 app.py "$MODE"

# Start the application
nohup uwsgi --ini /app/uwsgi.ini &

# Start celery
exec python3 -m celery -A celery_app worker --loglevel=info --concurrency=${celery_concurrency} -Q common-results-queue,task-checking-queue
