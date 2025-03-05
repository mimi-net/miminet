#!/bin/bash

/usr/share/openvswitch/scripts/ovs-ctl start
ovs-vswitchd &

exec python3 -m celery -A celery_app worker --loglevel=info --concurrency=${celery_concurrency} -Q ${queue_names}
