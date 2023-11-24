#!/bin/sh
# Check if the database file exists
if [ ! -f /app/instance/miminet.db ]; then
   python3 app.py init
fi

# Start the application
exec uwsgi --ini /app/uwsgi.ini
