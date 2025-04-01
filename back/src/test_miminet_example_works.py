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


def sanitize_animation(animation: str) -> str:
    """Apply common regex substitutions to remove volatile parts from the emulation output."""
    animation = re.sub(TIMESTAMP_REGEX, r'"timestamp": ""', animation)
    animation = re.sub(ID_REGEX, r'"id": ""', animation)
    info("Animation sanitization completed!")
    return animation


def packet_to_static(x: str):
    """Apply common regex substitutions to remove volatile parts from the packet key (label or type)."""
    x = re.sub(r"(UDP )\d+ > \d+", r"\1PORT > PORT", x)
    x = re.sub(r"(TCP .*?)\d+ > \d+", r"\1PORT > PORT", x)

    # Extract and replace dynamic TCP port values in the expected answer
    tcp_pattern = re.search(r"TCP \(SYN\) \d+", x)
    if tcp_pattern:
        pattern = tcp_pattern.group(0)[len("TCP (SYN) ") :]
        x = re.sub(r"port", pattern, x)

    # Extract and replace dynamic ARP MAC addresses in the expected answer
    arp_pattern = re.search(r"ARP-response\\n.+ at ([0-9a-fA-F]{2}[:]){6}", x)
    if arp_pattern:
        pattern = arp_pattern.group(0)[len("TCP (SYN) ") :]
        x = re.sub(r"mac", pattern, x)

    # Remove dynamic ARP response addresses from the package
    x = re.sub(r'"ARP-response.+? at .+?"', '"ARP-response"', x, flags=re.S)


def extract_important_fields(packets_json, exclude_regex=None) -> list[dict[str, str]]:
    """
    Extracts important (don't change every simulation) fields from packets, excluding packets that match the given regular expression.

    :param packets_json: JSON string with the simulation results.
    :param exclude_regex: Regular expression to exclude packets by label and type.
    """
    packets = json.loads(packets_json)
    important_packets = []
    exclude_pattern = re.compile(exclude_regex) if exclude_regex else None

    for packet_group in packets:
        for packet in packet_group:
            pkg_label = packet["data"]["label"]
            pkg_type = packet["config"]["type"]

            if exclude_pattern and exclude_pattern.match(pkg_label):
                continue  # Skip unimportant packages

            important_packet = {
                "type": packet_to_static(pkg_type),
                "label": packet_to_static(pkg_label),
                "path": packet["config"]["path"],
                "source": packet["config"]["source"],
                "target": packet["config"]["target"],
            }

            important_packets.append(important_packet)

    info("Important fields extracted from packets.")
    return important_packets


def compare_animations(actual_json: str, expected_json: str) -> bool:
    """
    Compare two animation JSON strings, ensuring they contain the same structured packet data.
    """
    if not actual_json:
        raise ValueError(f"actual_json is null, there is no simulation result.")

    try:
        expected_packets = json.loads(expected_json)
        actual_packets = json.loads(actual_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}.")

    info("Comparing JSON animations...")

    if len(expected_packets) != len(actual_packets):
        error(
            f"""Mismatch in packet lengths.
                Expected length: {len(expected_packets)}, actual: {len(actual_packets)}.
                    Actual packets: {actual_packets}."""
        )
        return False

    for group_index, (expected_group, actual_group) in enumerate(
        zip(expected_packets, actual_packets)
    ):
        # Sort in the same order
        sorted_expected = sorted(
            expected_group, key=lambda x: (x["config"]["path"], x["config"]["source"])
        )
        sorted_actual = sorted(
            actual_group, key=lambda x: (x["config"]["path"], x["config"]["source"])
        )

        if sorted_actual != sorted_expected:
            error(
                f"Mismatch in packet data at group {group_index}. Actual packets: {actual_packets}."
            )
            return False

    info("Animations matched successfully!")
    return True


STATIC_TEST_FILES = [
    ("switch_and_hub_network.json", "switch_and_hub_answer.json"),
    ("first_and_last_ip_address_network.json", "first_and_last_ip_address_answer.json"),
    ("vlan_access_network.json", "vlan_access_answer.json"),
    ("vlan_trunk_network.json", "vlan_trunk_answer.json"),
    ("vlan_with_stp_network.json", "vlan_with_stp_answer.json"),
    ("vlan_with_access_switches_network.json", "vlan_with_access_switches_answer.json"),
    ("rstp_simple_network.json", "rstp_simple_answer.json"),
    ("rstp_four_switch_network.json", "rstp_four_switch_answer.json"),
]

DYNAMIC_TEST_FILES = [
    ("tcp_connection_setup_1_network.json", "tcp_connection_setup_1_answer.json"),
    ("router_network.json", "router_answer.json"),
    ("icmp_network_unavailable_network.json", "icmp_network_unavailable_answer.json"),
    ("icmp_host_unreachable_network.json", "icmp_host_unreachable_answer.json"),
    ("vlan_with_vxlan_network.json", "vlan_with_vxlan_answer.json"),
    ("vxlan_with_nat_network.json", "vxlan_with_nat_answer.json"),
    ("vxlan_simple_network.json", "vxlan_simple_answer.json"),
]

# Generate test cases
TEST_CASES = [Case(*read_files(n, a)) for n, a in STATIC_TEST_FILES]
DYNAMIC_TEST_CASES = [Case(*read_files(n, a)) for n, a in DYNAMIC_TEST_FILES]

# @pytest.mark.parametrize("test", TEST_CASES)
# def test_miminet_work(test: Case, request) -> None:
#     info(f"Running test: {request.node.name}.")
#     animation, pcaps = simulate(test.json_network)
#     animation = sanitize_animation(animation)

#     assert compare_animations(animation, test.json_answer)
#     info(f"Finish test {request.node.name}.")


@pytest.mark.parametrize("test", DYNAMIC_TEST_CASES)
def test_miminet_work_for_dynamic_cases(test: Case, request) -> None:
    info(f"Running test: {request.node.name}.")

    # Emulate network behavior based on the test case
    animation, _ = simulate(test.json_network)
    animation = sanitize_animation(animation)

    # Extract important packet fields while ignoring excluded packets
    actual_packets = extract_important_fields(animation, r"^ARP")
    expected_packets = extract_important_fields(test.json_answer, r"^ARP")

    assert actual_packets == expected_packets

    info(f"Finish test {request.node.name}.")
