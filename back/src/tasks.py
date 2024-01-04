import json
import typing

import marshmallow_dataclass
from celery import shared_task
from network import Network
from simulate import run_mininet
from mininet.log import setLogLevel

import redis


@shared_task(
    autoretry_for=(redis.exceptions.ConnectionError,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
)
def mininet_worker(
    network: str,
) -> tuple[str, list[typing.Any] | list[tuple[str, bytes]]]:
    """Worker for start mininet simulation

    Args:
        network (str): str network from queue

    Returns:
        tuple: Tuple (json emulation results, List[pcap, pcap name])

    """
    setLogLevel('info')

    jnet = json.loads(network)
    print(network)
    network_schema = marshmallow_dataclass.class_schema(Network)()
    animation = ""
    pcaps = []
    host_ip = {}

    for i in range(3):
        try:
            animation, pcaps, host_ip = run_mininet(network_schema.load(jnet))
        except ValueError:
            continue
        except Exception:
            break
        else:
            break
    return json.dumps(animation), pcaps, host_ip
