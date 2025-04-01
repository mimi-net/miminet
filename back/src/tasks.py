import json
import os
import signal

import marshmallow_dataclass
from celery_app import (
    app,
    SEND_NETWORK_RESPONSE_EXCHANGE,
    SEND_NETWORK_RESPONSE_ROUTING_KEY,
)
from mininet.log import setLogLevel, error

from network import Network
from simulate import run_mininet


def simulate(network: str):
    """Worker for start mininet simulation

    Args:
        network (str): str network from queue

    Returns:
        tuple: Tuple (json emulation results, List[pcap, pcap name])

    """

    setLogLevel("info")

    if os.name == "posix":
        print("Set default handler to SIGCHLD")
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    jnet = json.loads(network)
    network_schema = marshmallow_dataclass.class_schema(Network)()
    network = network_schema.load(jnet)

    for _ in range(4):
        try:
            animation, pcaps = run_mininet(network)

            return json.dumps(animation), pcaps
        except Exception as e:
            # Sometimes mininet doesn't work correctly and simulation needs to be redone,
            # Example of mininet error: https://github.com/mininet/mininet/issues/737.
            error(e)
            continue

    return "", []


@app.task(bind=True)
def mininet_worker(self, network: str):
    """Worker for start mininet simulation

    Args:
        network (str): str network from queue

    Returns:
        tuple: Tuple (json emulation results, List[pcap, pcap name])

    """

    animation, pcaps = simulate(network)

    network_task = self.request.headers["network_task_name"]
    task_id = self.request.id

    app.send_task(
        network_task,
        (
            animation,
            pcaps,
        ),
        routing_key=SEND_NETWORK_RESPONSE_ROUTING_KEY,
        exchange=SEND_NETWORK_RESPONSE_EXCHANGE.name,
        exchange_type=SEND_NETWORK_RESPONSE_EXCHANGE.type,
        task_id=task_id,
    )

    return json.dumps(animation), pcaps
