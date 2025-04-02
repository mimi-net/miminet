import dataclasses
import re
import json
from pathlib import Path

from mininet.log import setLogLevel, info, error
import pytest
from tasks import simulate


setLogLevel("info")

# Test directory
TEST_JSON_DIR = Path("test_json/")

# Common regex patterns
TIMESTAMP_REGEX = r'"timestamp": "\d+"'
ID_REGEX = r'"id": "\w+"'


@dataclasses.dataclass
class Case:
    json_network: str  # Network that we should emulate
    json_answer: str  # Answer that emulation should return


def read_files(network_filename: str, answer_filename: str):
    """Read both expected and actual json files."""
    expected_path = TEST_JSON_DIR / network_filename
    answer_path = TEST_JSON_DIR / answer_filename

    with expected_path.open("r") as exp_file, answer_path.open("r") as act_file:
        info(f"Reading files: {network_filename}, {answer_filename}.")
        return exp_file.read(), act_file.read()


def packet_to_static(x: str):
    """Apply common regex substitutions to remove volatile parts from the packet key (label or type)."""

    # Extract and replace dynamic TCP port values in the expected answer
    x = re.sub(r"(UDP )\d+ > \d+", r"\1PORT > PORT", x)
    x = re.sub(r"(TCP .*?)\d+ > \d+", r"\1PORT > PORT", x)

    x = re.sub(r"TCP \(SYN\) \d+", r"port", x)

    # Extract and replace dynamic ARP MAC addresses in the expected answer
    x = re.sub(r"ARP-response\n.+ at ([0-9a-fA-F]{2}[:]){6}", r"mac", x)

    # Remove dynamic ARP response addresses from the package
    x = re.sub(r'"ARP-response.+? at .+?"', '"ARP-response"', x, flags=re.S)

    x = x.replace("\n", "\\n").strip()

    return x


def extract_important_fields(packets_json) -> list[dict[str, str]]:
    """
    Extracts important (don't change every simulation) fields from packets, excluding packets that match the given regular expression.

    :param packets_json: JSON string with the simulation results.
    """
    packets = json.loads(packets_json)

    important_packets = []
    exclude_pattern = re.compile(r"^ARP") if r"^ARP" else None

    for packet_group in packets:
        for packet in packet_group:
            pkg_data = packet["data"]
            pkg_config = packet["config"]

            pkg_label = pkg_data["label"]
            pkg_type = pkg_config["type"]

            if exclude_pattern and exclude_pattern.match(pkg_label):
                continue  # Skip unimportant packages

            important_packet = {
                "type": packet_to_static(pkg_type),
                "label": packet_to_static(pkg_label),
                "source": pkg_config["source"],
                "target": pkg_config["target"],
                "path": pkg_config["path"],
            }

            important_packets.append(important_packet)

    sorted_important_packets = sorted(
        important_packets, key=lambda x: (x["path"], x["source"])
    )

    info("Important fields extracted from packets.")
    return sorted_important_packets


TEST_FILES = [
    # ("switch_and_hub_network.json", "switch_and_hub_answer.json"),
    # ("first_and_last_ip_address_network.json", "first_and_last_ip_address_answer.json"),
    # ("vlan_access_network.json", "vlan_access_answer.json"),
    # ("vlan_trunk_network.json", "vlan_trunk_answer.json"),
    # ("vlan_with_stp_network.json", "vlan_with_stp_answer.json"),
    # ("vlan_with_access_switches_network.json", "vlan_with_access_switches_answer.json"),
    # ("rstp_simple_network.json", "rstp_simple_answer.json"),
    ("rstp_four_switch_network.json", "rstp_four_switch_answer.json"),
    # ("tcp_connection_setup_1_network.json", "tcp_connection_setup_1_answer.json"),
    # ("router_network.json", "router_answer.json"),
    # ("icmp_network_unavailable_network.json", "icmp_network_unavailable_answer.json"),
    # ("icmp_host_unreachable_network.json", "icmp_host_unreachable_answer.json"),
    # ("vlan_with_vxlan_network.json", "vlan_with_vxlan_answer.json"),
    # ("vxlan_with_nat_network.json", "vxlan_with_nat_answer.json"),
    # ("vxlan_simple_network.json", "vxlan_simple_answer.json"),
]

# Generate test cases
TEST_CASES = [Case(*read_files(n, a)) for n, a in TEST_FILES]


@pytest.mark.parametrize("test", TEST_CASES)
def test_miminet_work(test: Case, request) -> None:
    info(f"Running test: {request.node.name}.")

    # Emulate network behavior based on the test case
    animation, _ = simulate(test.json_network)

    # Extract important packet fields while ignoring excluded packets
    actual_packets = extract_important_fields(animation)
    expected_packets = extract_important_fields(test.json_answer)

    try:
        assert actual_packets == expected_packets
    except AssertionError as e:
        error(f"Test {request.node.name} failed: {str(e)}.")
        raise e

    info(f"Finish test {request.node.name}.")
