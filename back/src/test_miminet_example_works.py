import dataclasses
import re
import json
from pathlib import Path

import pytest
from tasks import simulate


# Test directory
TEST_JSON_DIR = Path("test_json/")

# Common regex patterns
TIMESTAMP_REGEX = r'"timestamp": "\d+"'
ID_REGEX = r'"id": "\w+"'


@dataclasses.dataclass
class Case:
    json_network: str
    json_answer: str
    pattern_in_network: str = r""
    pattern_len: int = 0
    pattern_for_replace: str = r""
    exclude_regex: str = r""


def read_files(network_filename: str, answer_filename: str):
    """Read both expected and actual json files."""
    expected_path = TEST_JSON_DIR / network_filename
    answer_path = TEST_JSON_DIR / answer_filename

    with expected_path.open("r") as exp_file, answer_path.open("r") as act_file:
        return exp_file.read(), act_file.read()


def sanitize_animation(animation: str) -> str:
    """Apply common regex substitutions to remove volatile parts from the simulation output."""
    animation = re.sub(TIMESTAMP_REGEX, r'"timestamp": ""', animation)
    animation = re.sub(ID_REGEX, r'"id": ""', animation)
    return animation


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

            # Убираем порты которые генерируются динамически
            pkg_label = re.sub(r"(UDP )\d+ > \d+", r"\1PORT > PORT", pkg_label)
            pkg_label = re.sub(r"(TCP .*?)\d+ > \d+", r"\1PORT > PORT", pkg_label)
            pkg_type = re.sub(r"(UDP )\d+ > \d+", r"\1PORT > PORT", pkg_type)
            pkg_type = re.sub(r"(TCP .*?)\d+ > \d+", r"\1PORT > PORT", pkg_type)

            important_packet = {
                "type": pkg_type,
                "label": pkg_label,
                "path": packet["config"]["path"],
                "source": packet["config"]["source"],
                "target": packet["config"]["target"],
            }

            important_packets.append(important_packet)

    return important_packets


def compare_animations(actual_json: str, expected_json: str) -> bool:
    """
    Compare two animation JSON strings, ensuring they contain the same structured packet data.
    """
    assert actual_json, "Simulation failed, no reasonable result was obtained."

    try:
        expected_packets = json.loads(expected_json)
        actual_packets = json.loads(actual_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}.")

    if len(expected_packets) != len(actual_packets):
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
            return False

    return True


FILE_NAMES = [
    ("switch_and_hub_network.json", "switch_and_hub_answer.json"),
    ("first_and_last_ip_address_network.json", "first_and_last_ip_address_answer.json"),
    ("vlan_access_network.json", "vlan_access_answer.json"),
    ("vlan_trunk_network.json", "vlan_trunk_answer.json"),
    ("vlan_with_stp_network.json", "vlan_with_stp_answer.json"),
    ("vlan_with_access_switches_network.json", "vlan_with_access_switches_answer.json"),
    ("rstp_simple_network.json", "rstp_simple_answer.json"),
    ("rstp_four_switch_network.json", "rstp_four_switch_answer.json"),
]

DINAMYC_PORT_FILE_NAMES = [
    (
        "tcp_connection_setup_1_network.json",
        "tcp_connection_setup_1_answer.json",
        r"TCP \(SYN\) \d+",
        len("TCP (SYN) "),
        r"port",
    ),
]

DINAMYC_ARP_FILE_NAMES = [
    (
        "router_network.json",
        "router_answer.json",
        r"ARP-response\\n.+ at ([0-9a-fA-F]{2}[:]){6}",
        len("ARP-response\\n10.0.0.1 at "),
        r"mac",
    ),
]


DINAMYC_ARP_AND_PORT_FILE_NAMES = [
    (
        "icmp_network_unavailable_network.json",
        "icmp_network_unavailable_answer.json",
        r"TCP \(SYN\) \d+",
        len("TCP (SYN) "),
        r"port",
    ),
    (
        "icmp_host_unreachable_network.json",
        "icmp_host_unreachable_answer.json",
        r"TCP \(SYN\) \d+",
        len("TCP (SYN) "),
        r"port",
    ),
]

EXCLUDE_PACKETS_FILE_NAMES = [
    ("vlan_with_vxlan_network.json", "vlan_with_vxlan_answer.json", r"^ARP"),
    ("vxlan_with_nat_network.json", "vxlan_with_nat_answer.json", r"^ARP"),
    ("vxlan_simple_network.json", "vxlan_simple_answer.json", r"^ARP"),
]

TEST_CASES = [Case(*read_files(network, answer)) for network, answer in FILE_NAMES]

DINAMYC_PORT_TEST_CASES = [
    Case(network, answer, pattern, length, replace)
    for (network, answer, pattern, length, replace) in [
        list(read_files(case[0], case[1])) + [case[2], case[3], case[4]]
        for case in DINAMYC_PORT_FILE_NAMES
    ]
]

DINAMYC_ARP_AND_PORT_TEST_CASES = [
    Case(network, answer, pattern, length, replace)
    for (network, answer, pattern, length, replace) in [
        list(read_files(case[0], case[1])) + [case[2], case[3], case[4]]
        for case in DINAMYC_ARP_AND_PORT_FILE_NAMES
    ]
]

DINAMYC_ARP_TEST_CASES = [
    Case(network, answer, pattern, length, replace)
    for (network, answer, pattern, length, replace) in [
        list(read_files(case[0], case[1])) + [case[2], case[3], case[4]]
        for case in DINAMYC_ARP_FILE_NAMES
    ]
]

EXCLUDE_PACKETS_TEST_CASES = [
    Case(json_network=network, json_answer=answer, exclude_regex=exclude)
    for (network, answer, exclude) in [
        (*read_files(case[0], case[1]), case[2]) for case in EXCLUDE_PACKETS_FILE_NAMES
    ]
]


@pytest.mark.parametrize("test", TEST_CASES)
def test_miminet_work(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)
    animation = sanitize_animation(animation)

    assert compare_animations(animation, test.json_answer)


@pytest.mark.parametrize("test", DINAMYC_PORT_TEST_CASES)
def test_miminet_work_for_dinamyc_port_test_cases(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)
    animation = sanitize_animation(animation)

    port_string = re.search(test.pattern_in_network, animation)
    assert port_string is not None
    port = port_string.group(0)[test.pattern_len :]
    test.json_answer = re.sub(test.pattern_for_replace, port, test.json_answer)
    assert compare_animations(animation, test.json_answer)


@pytest.mark.parametrize("test", DINAMYC_ARP_AND_PORT_TEST_CASES)
def test_miminet_work_for_dinamyc_arp_and_port_test_cases(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)
    animation = sanitize_animation(animation)
    animation = re.sub(
        r'"ARP-response.+? at .+?"', r'"ARP-response"', animation, flags=re.S
    )
    port_string = re.search(test.pattern_in_network, animation)
    assert port_string is not None
    port = port_string.group(0)[test.pattern_len :]
    test.json_answer = re.sub(test.pattern_for_replace, port, test.json_answer)
    assert compare_animations(animation, test.json_answer)


@pytest.mark.parametrize("test", DINAMYC_ARP_TEST_CASES)
def test_miminet_work_for_dinamyc_arp_test_cases(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)
    animation = sanitize_animation(animation)
    animation = re.sub(
        r'"ARP-response.+? at .+?"', r'"ARP-response"', animation, flags=re.S
    )
    assert compare_animations(animation, test.json_answer)


@pytest.mark.parametrize("test", EXCLUDE_PACKETS_TEST_CASES)
def test_miminet_work_with_excluded_packages(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)

    animation = sanitize_animation(animation)

    expected_animation = re.sub(
        r'"timestamp": "\d+"', r'"timestamp": ""', test.json_answer
    )
    expected_animation = re.sub(r'"id": "\w+"', r'"id": ""', expected_animation)

    exclude_regex = getattr(test, "exclude_regex", None)

    actual_packets = extract_important_fields(animation, exclude_regex)
    expected_packets = extract_important_fields(expected_animation, exclude_regex)

    assert actual_packets == expected_packets
