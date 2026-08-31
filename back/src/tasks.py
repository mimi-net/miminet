import json
import os
import signal

from marshmallow import Schema
import marshmallow_dataclass

from node_types import NodeType
from celery_app import (
    SEND_NETWORK_RESPONSE_EXCHANGE,
    SEND_NETWORK_RESPONSE_ROUTING_KEY,
    app,
)
from emulator import emulate
from mininet.log import error, setLogLevel
from network_schema import Network

_network_schema: Schema | None = None


def _filter_unknown_nodes(data: dict) -> dict:
    allowed = set(NodeType)
    data["nodes"] = [
        node
        for node in data.get("nodes", [])
        if node.get("config", {}).get("type") in allowed
    ]
    return data


def get_network_schema() -> Schema:
    global _network_schema
    if _network_schema is None:
        _network_schema = marshmallow_dataclass.class_schema(Network)()
    return _network_schema


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

    jnet = _filter_unknown_nodes(json.loads(network_json))
    schema = get_network_schema()
    network_schema: Network = schema.load(jnet, unknown="include")

    for _ in range(4):
        try:
            animation, pcaps = emulate(network_schema)

            # A network that defines jobs must show evidence of captured host
            # traffic. Retry when the animation is empty or carries only
            # STP/RSTP/LLC control frames — that means the capture never caught
            # any host packet (cold start). If ARP was captured but no IP
            # follows, the result is plausible (e.g. link_down / no-client
            # tests) and is returned as-is.
            if network_schema.jobs and not _has_meaningful_packets(animation):
                error("Animation without captured host traffic; retrying.")
                continue

            return json.dumps(animation), pcaps
        except Exception as e:
            # Sometimes mininet doesn't work correctly and simulation needs to be redone,
            # Example of mininet error: https://github.com/mininet/mininet/issues/737.
            error(e)
            continue

    return "[]", []


def _has_meaningful_packets(animation) -> bool:
    """Return True if the animation shows evidence of captured host traffic.

    A warm capture always picks up at least the ARP exchange, so ARP counts as
    meaningful too: animations carrying only STP/RSTP/LLC control frames mean
    the capture started too late to see any host packet and must be retried.

    DHCP is protocol-aware: a client's Discover alone (without a server Offer,
    Request or ACK) means the DHCP server was not ready when the client ran, so
    the capture is not meaningful and must be retried.
    """
    if not animation:
        return False

    dhcp_seen = False
    dhcp_answered = False

    for group in animation:
        for packet in group:
            pkt_type = packet.get("config", {}).get("type", "")

            if pkt_type.startswith("DHCP"):
                dhcp_seen = True
                if not pkt_type.startswith("DHCP Discover"):
                    dhcp_answered = True
                continue

            if pkt_type.startswith("ARP"):
                return True
            if not pkt_type.startswith(("STP", "RSTP", "LLC", "Unknown")):
                return True

    if dhcp_seen:
        return dhcp_answered
    return False


@app.task(bind=True)
def mininet_worker(self, network_json: str):
    """Celery worker for starting Miminet emulation.

    Args:
        network_json (str): JSON network from queue.

    Returns:
        tuple: Tuple (json emulation results, List[pcap, pcap name])

    """

    animation, pcaps = run_miminet(network_json)

    # Task that starts emulation proccess may specify where we should send the result

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
