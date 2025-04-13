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

from network_schema import Network
from emulator import emulate


def run_miminet(network_json: str):
    """Load network from JSON and start emulation safely.

    Args:
        network_json (str): JSON network from queue.

    Returns:
        tuple: Tuple (json emulation results, List[pcap, pcap name]).

    """

    setLogLevel("info")

    if os.name == "posix":
        print("Set default handler to SIGCHLD")
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    jnet = json.loads(network_json)
    network_schema = marshmallow_dataclass.class_schema(Network)()
    network_json = network_schema.load(jnet)

    for _ in range(4):
        try:
            animation, pcaps = emulate(network_json)

            return json.dumps(animation), pcaps
        except Exception as e:
            # Sometimes mininet doesn't work correctly and simulation needs to be redone,
            # Example of mininet error: https://github.com/mininet/mininet/issues/737.
            error(e)
            continue

    return "", []


@app.task(bind=True)
def mininet_worker(self, network_json: str):
    """Celery worker for starting Miminet emulation.

    Args:
        network_json (str): JSON network from queue.

    Returns:
        tuple: Tuple (json emulation results, List[pcap, pcap name])

    """

    animation, pcaps = run_miminet(network_json)

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
