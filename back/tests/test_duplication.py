import json
from pathlib import Path

from src.tasks import run_miminet

TEST_JSON_DIR = Path("network_examples_json/")


# ---------------- Utility functions ---------------- #


def load_file(filename: str) -> str:
    return (TEST_JSON_DIR / filename).read_text()


def set_duplicate_percentage(network_json: str, value: float = 0) -> str:
    network = json.loads(network_json)
    for edge in network.get("edges", []):
        edge_data = edge.get("data", {})
        edge_data["duplicate_percentage"] = value
    return json.dumps(network)


def count_packets(animation_json: str) -> int:
    animation = json.loads(animation_json)
    return sum(len(group) for group in animation)


def assert_duplicate_and_loss_present(animation_json: str) -> None:
    animation = json.loads(animation_json)
    for group in animation:
        for pkt in group:
            cfg = pkt.get("config", {})
            assert (
                "duplicate_percentage" in cfg
            ), "duplicate_percentage missing in packet config"
            assert "loss_percentage" in cfg, "loss_percentage missing in packet config"


# ---------------- Test cases ---------------- #


def test_duplicate_edges_double_packets():
    net_json = load_file("duplication_network.json")
    animation_with_dup, _ = run_miminet(net_json)

    net_zero_dup = set_duplicate_percentage(net_json, 0)
    animation_no_dup, _ = run_miminet(net_zero_dup)

    count_with_dup = count_packets(animation_with_dup)
    count_no_dup = count_packets(animation_no_dup)

    assert (
        count_with_dup > count_no_dup
    ), f"Packets with duplication ({count_with_dup}) should be greater than packets without duplication ({count_no_dup})"


def test_backward_compatibility_no_dup_percentage():
    net_json = load_file("issues_no_dup_backward_compatibility_network.json")
    animation_json, _ = run_miminet(net_json)
    assert_duplicate_and_loss_present(animation_json)


def test_backward_compatibility_no_loss_no_dup_percentage():
    net_json = load_file("issues_no_loss_no_dup_backward_compatibility_network.json")
    animation_json, _ = run_miminet(net_json)
    assert_duplicate_and_loss_present(animation_json)
