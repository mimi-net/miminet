import json
from pathlib import Path

from src.tasks import run_miminet


TEST_JSON_DIR = Path("network_examples_json/")


def load_file(filename: str) -> str:
    return (TEST_JSON_DIR / filename).read_text()


def flatten_packets(animation_json: str) -> list[dict]:
    animation = json.loads(animation_json)
    return [packet for group in animation for packet in group]


def packets_by_label_and_path(
    packets: list[dict], label_prefix: str, path: str
) -> list[dict]:
    return [
        pkt
        for pkt in packets
        if pkt.get("data", {}).get("label", "").startswith(label_prefix)
        and pkt.get("config", {}).get("path") == path
    ]


def packets_by_label_path_and_source(
    packets: list[dict], label_prefix: str, path: str, source: str
) -> list[dict]:
    return [
        pkt
        for pkt in packets
        if pkt.get("data", {}).get("label", "").startswith(label_prefix)
        and pkt.get("config", {}).get("path") == path
        and pkt.get("config", {}).get("source") == source
    ]


def test_arp_spoofing_mitm_routes_icmp_through_hacker():
    net_json = load_file("arp_spoofing_mitm_network.json")
    animation_json, _ = run_miminet(net_json)
    packets = flatten_packets(animation_json)

    assert packets_by_label_path_and_source(
        packets, "ARP-response", "edge_arp_hacker_switch", "hacker_1"
    ), "MITM mode should emit a spoofed ARP response from hacker"
    assert packets_by_label_and_path(
        packets, "ICMP echo-request", "edge_arp_hacker_switch"
    ), "MITM mode should route ICMP echo-request through hacker edge"
    assert packets_by_label_and_path(
        packets, "ICMP echo-reply", "edge_arp_hacker_switch"
    ), "MITM mode should route ICMP echo-reply through hacker edge"
    assert packets_by_label_and_path(
        packets, "ICMP echo-reply", "edge_arp_host_switch"
    ), "MITM mode should still deliver echo-reply back to host"


def test_arp_spoofing_reply_only_sends_spoofed_arp_without_mitm_forwarding():
    net_json = load_file("arp_spoofing_reply_only_network.json")
    animation_json, _ = run_miminet(net_json)
    packets = flatten_packets(animation_json)

    assert packets_by_label_path_and_source(
        packets, "ARP-response", "edge_arp_hacker_switch", "hacker_1"
    ), "Reply-only mode should emit a spoofed ARP response from hacker"
    assert packets_by_label_path_and_source(
        packets, "ARP-response", "edge_arp_host_switch", "l2sw1"
    ), "Reply-only mode should deliver ARP responses toward host"
    host_arp_responses = packets_by_label_and_path(
        packets, "ARP-response", "edge_arp_host_switch"
    )
    host_arp_response_labels = {
        pkt.get("data", {}).get("label", "") for pkt in host_arp_responses
    }
    assert (
        len(host_arp_response_labels) >= 2
    ), "Reply-only mode should expose host to both router and hacker ARP responses"
    assert packets_by_label_and_path(
        packets, "ICMP echo-request", "edge_arp_hacker_switch"
    ), "Reply-only mode should attract ICMP echo-request to hacker"
    assert not packets_by_label_and_path(
        packets, "ICMP echo-request", "edge_arp_router_switch"
    ), "Reply-only mode should not forward ICMP echo-request to router"
    assert not packets_by_label_and_path(
        packets, "ICMP echo-reply", "edge_arp_hacker_switch"
    ), "Reply-only mode should not route ICMP echo-reply through hacker"
    assert not packets_by_label_and_path(
        packets, "ICMP echo-reply", "edge_arp_host_switch"
    ), "Reply-only mode should not deliver ICMP echo-reply back to host"
