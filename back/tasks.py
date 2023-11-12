import json
import redis

from simulate import run_mininet
from celery import shared_task


@shared_task(autoretry_for=(redis.exceptions.ConnectionError,),
             retry_kwargs={'max_retries': 3, 'countdown': 5})
def mininet_worker(network: str, guid: str):
    animation, pcaps = run_mininet(network, guid)
    return json.dumps(animation), pcaps
