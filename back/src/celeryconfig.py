import os

from dotenv import load_dotenv

load_dotenv()

broker_url = os.getenv("amqp_urls")
result_backend = os.getenv("rpc_urls")

imports = ["tasks"]

broker_connection_retry_on_startup = True


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# A stuck emulation must never pin the prefork worker forever (issue #517):
# kill the task instead and let the pool replace the child. Generous
# defaults — a large emulation is tens of seconds; teardown is capped at 15s.
task_soft_time_limit = _int_env("CELERY_TASK_SOFT_TIME_LIMIT", 270)
task_time_limit = _int_env("CELERY_TASK_TIME_LIMIT", 300)

# Recycle each pool child after N tasks so file descriptors, zombies and
# Mininet kernel state cannot accumulate in a long-lived worker.
worker_max_tasks_per_child = _int_env("CELERY_MAX_TASKS_PER_CHILD", 20)
