import json
import os
import signal

import marshmallow_dataclass

try:
    from celery_app import (
        app,
        SEND_NETWORK_RESPONSE_EXCHANGE,
        SEND_NETWORK_RESPONSE_ROUTING_KEY,
    )
except ImportError:
    app = None
    SEND_NETWORK_RESPONSE_EXCHANGE = None
    SEND_NETWORK_RESPONSE_ROUTING_KEY = None


# --- pytest / no-celery fallback ---
if app is None:
    class _FakeApp:
        def task(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

    app = _FakeApp()


from mininet.log import setLogLevel, error

from src.network_schema import Network
from src.emulator import emulate
from typing import Union

def run_miminet(network_json: Union[str, dict, list]):
    setLogLevel("info")

    if os.name == "posix":
        print("Set default handler to SIGCHLD")
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    # accept both: string JSON OR already parsed dict/list
    if isinstance(network_json, (dict, list)):
        jnet = network_json
    else:
        jnet = json.loads(network_json)

    network_schema = marshmallow_dataclass.class_schema(Network)()
    if isinstance(jnet, dict) and "jobs" in jnet and isinstance(jnet["jobs"], list):
        for job in jnet["jobs"]:
            if isinstance(job, dict):
                for k in ("arg_1", "arg_2", "arg_3"):
                    if k in job and job[k] is not None and not isinstance(job[k], str):
                        job[k] = str(job[k])

    if isinstance(jnet, dict) and "nodes" in jnet and isinstance(jnet["nodes"], list):
        for node in jnet["nodes"]:
            if not isinstance(node, dict):
                continue

            interfaces = node.get("interface")
            if not isinstance(interfaces, list):
                continue

            for iface in interfaces:
                if not isinstance(iface, dict):
                    continue

                if "vlan" in iface and iface["vlan"] is not None and not isinstance(iface["vlan"], int):
                    try:
                        iface["vlan"] = int(iface["vlan"])
                    except (TypeError, ValueError):
                        iface.pop("vlan", None)

    network = network_schema.load(jnet, unknown="include")

    if isinstance(jnet, dict) and "jobs" in jnet and isinstance(jnet["jobs"], list):
        for job in jnet["jobs"]:
            if isinstance(job, dict):
                if "arg_1" in job and not isinstance(job["arg_1"], str):
                    job["arg_1"] = str(job["arg_1"])
                if "arg_3" in job and not isinstance(job["arg_3"], str):
                    job["arg_3"] = str(job["arg_3"])

    network = network_schema.load(jnet, unknown="include")

    for _ in range(4):
        try:
            animation, pcaps = emulate(network)

            animation_str = animation if isinstance(animation, str) else json.dumps(animation)
            return animation_str, pcaps

        except Exception as e:
            error(e)

    raise RuntimeError("Emulation failed after 4 attempts")

@app.task(bind=True)
def mininet_worker(self, network_json: str):
    """Celery worker for starting Miminet emulation.

    Args:
        network_json (str): JSON network from queue.

    Returns:
        tuple: Tuple (json emulation results, List[pcap, pcap name])

    """

    animation, pcaps = run_miminet(network_json)

    # Task that starts emulation process may specify where we should send the result

    if self.request.headers:
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
