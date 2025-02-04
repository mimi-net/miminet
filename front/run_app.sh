#!/bin/sh
# Check if the database file exists
if [ ! -f /app/instance/miminet.db ]; then
   python3 app.py init
fi

# Start the application
nohup uwsgi --ini /app/uwsgi.ini &

# Start celery
exec python3 -m celery -A celery_app worker --logfile=/app/error.txt --loglevel=info --concurrency=${celery_concurrency} -Q common-results-queue
