import dataclasses
import re
import json

import pytest
from tasks import simulate


@dataclasses.dataclass
class Case:
    json_network: str
    json_answer: str
    pattern_in_network: str = r""
    pattern_len: int = 0
    pattern_for_replace: str = r""
    exclude_regex: str = r""


DEFAULT_JSON_TEST_DIRECTORY = "test_json/"


def read_files(network_filename: str, answer_filename: str):
    with open(DEFAULT_JSON_TEST_DIRECTORY + network_filename, "r") as file1, open(
        DEFAULT_JSON_TEST_DIRECTORY + answer_filename, "r"
    ) as file2:
        return file1.read(), file2.read().rstrip()


FILE_NAMES = [
    ("switch_and_hub_network.json", "switch_and_hub_answer.json"),
    ("first_and_last_ip_address_network.json", "first_and_last_ip_address_answer.json"),
    ("vlan_access_network.json", "vlan_access_answer.json"),
    ("vlan_trunk_network.json", "vlan_trunk_answer.json"),
    ("vlan_with_stp_network.json", "vlan_with_stp_answer.json"),
    ("vlan_with_access_switches_network.json", "vlan_with_access_switches_answer.json"),
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

TEST_CASES = [
    Case(network, answer)
    for (network, answer) in [read_files(file[0], file[1]) for file in FILE_NAMES]
]

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


def extract_important_fields(packets_json, exclude_regex=None):
    """
    Извлекает важные(которые не меняются каждую симуляцию) поля из пакетов, исключая пакеты, соответствующие заданному регулярному выражению.

    :param packets_json: JSON-строка с результатами симуляции.
    :param exclude_regex: Регулярное выражение для исключения пакетов по label и type.
    """
    packets = json.loads(packets_json)
    important_packets = []
    pattern = re.compile(exclude_regex) if exclude_regex else None
    for packet_group in packets:
        for packet in packet_group:
            label = packet["data"]["label"]
            pkg_type = packet["config"]["type"]
            if pattern and pattern.match(label):
                continue
            # Убираем порты которые генерируются динамически
            label = re.sub(r"(UDP )\d+ > \d+", r"\1PORT > PORT", label)
            label = re.sub(r"(TCP .*?)\d+ > \d+", r"\1PORT > PORT", label)
            pkg_type = re.sub(r"(UDP )\d+ > \d+", r"\1PORT > PORT", pkg_type)
            pkg_type = re.sub(r"(TCP .*?)\d+ > \d+", r"\1PORT > PORT", pkg_type)
            important_packet = {
                "type": pkg_type,
                "label": label,
                "path": packet["config"]["path"],
                "source": packet["config"]["source"],
                "target": packet["config"]["target"],
            }
            important_packets.append(important_packet)
    return important_packets


def compare_animations(expected, actual) -> bool:
    expected_packets = json.loads(expected)
    actual_packets = json.loads(actual)
    if len(expected_packets) != len(actual_packets):
        return False
    for expected_group, actual_group in zip(expected_packets, actual_packets):
        sorted_expected = sorted(expected_group, key=lambda x: x["config"]["path"])
        sorted_actual = sorted(actual_group, key=lambda x: x["config"]["path"])
        if sorted_actual != sorted_expected:
            return False
    return True


@pytest.mark.parametrize("test", TEST_CASES)
def test_miminet_work(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)
    animation = re.sub(r'"timestamp": "\d+"', r'"timestamp": ""', animation)
    animation = re.sub(r'"id": "\w+"', r'"id": ""', animation)
    assert compare_animations(animation, test.json_answer)


@pytest.mark.parametrize("test", DINAMYC_PORT_TEST_CASES)
def test_miminet_work_for_dinamyc_port_test_cases(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)
    animation = re.sub(r'"timestamp": "\d+"', r'"timestamp": ""', animation)
    animation = re.sub(r'"id": "\w+"', r'"id": ""', animation)
    port_string = re.search(test.pattern_in_network, animation)
    assert port_string is not None
    port = port_string.group(0)[test.pattern_len :]
    test.json_answer = re.sub(test.pattern_for_replace, port, test.json_answer)
    assert compare_animations(animation, test.json_answer)


@pytest.mark.parametrize("test", DINAMYC_ARP_AND_PORT_TEST_CASES)
def test_miminet_work_for_dinamyc_arp_and_port_test_cases(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)
    animation = re.sub(r'"timestamp": "\d+"', r'"timestamp": ""', animation)
    animation = re.sub(r'"id": "\w+"', r'"id": ""', animation)
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
    animation = re.sub(r'"timestamp": "\d+"', r'"timestamp": ""', animation)
    animation = re.sub(r'"id": "\w+"', r'"id": ""', animation)
    animation = re.sub(
        r'"ARP-response.+? at .+?"', r'"ARP-response"', animation, flags=re.S
    )
    assert compare_animations(animation, test.json_answer)


@pytest.mark.parametrize("test", EXCLUDE_PACKETS_TEST_CASES)
def test_miminet_work_with_excluded_packages(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)

    animation = re.sub(r'"timestamp": "\d+"', r'"timestamp": ""', animation)
    animation = re.sub(r'"id": "\w+"', r'"id": ""', animation)

    expected_animation = re.sub(
        r'"timestamp": "\d+"', r'"timestamp": ""', test.json_answer
    )
    expected_animation = re.sub(r'"id": "\w+"', r'"id": ""', expected_animation)

    exclude_regex = getattr(test, "exclude_regex", None)

    # Извлекаем важные поля, исключая пакеты по регулярному выражению
    actual_packets = extract_important_fields(animation, exclude_regex)
    expected_packets = extract_important_fields(expected_animation, exclude_regex)

    assert actual_packets == expected_packets
