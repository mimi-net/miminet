. /vagrant/venv/bin/activate
cd /vagrant/src
set -a
. ../.env
set +a
nohup python3 -m celery -A celery_app worker --loglevel=info --concurrency=${celery_concurrency} -Q ${queue_names} > ./celery_log 2>&1 &