#!/bin/bash
# ENTRYPOINT for the emulation (celery) container.
#
# The container runs privileged with host networking, so Mininet/OVS kernel
# state (bridges, veth pairs) survives container restarts. Clean it once at
# startup, then run the worker with guard rails so one wedged emulation
# (see issue #517) can never pin the pool forever:
#   --time-limit / --soft-time-limit kill a stuck task,
#   --max-tasks-per-child recycles each pool child before fd/zombie/bridge
#   residue can accumulate in a long-lived worker.

bash /app/ovs-init.sh

# Stale kernel state from an unclean shutdown (host netns persists).
mn -c >/dev/null 2>&1 || true
rm -f /tmp/capture_*.pcapng >/dev/null 2>&1 || true

exec python3 -m celery -A celery_app worker --loglevel=info \
  --concurrency=${celery_concurrency} \
  -Q ${queue_names} \
  --time-limit=${CELERY_TASK_TIME_LIMIT:-300} \
  --soft-time-limit=${CELERY_TASK_SOFT_TIME_LIMIT:-270} \
  --max-tasks-per-child=${CELERY_MAX_TASKS_PER_CHILD:-20}
