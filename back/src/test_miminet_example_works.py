import dataclasses
import re

import pytest
from tasks import simulate


@dataclasses.dataclass
class Case:
    json_network: str
    json_answer: str
    pattern_in_network: str = r""
    pattern_len: int = 0
    pattern_for_replace: str = r""


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
    # ("multicast_udp_traffic_network.json", "multicast_udp_traffic_answer.json", r'UDP \d+', len('UDP '), r'port'),
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

DINAMYC_ARP_TEST_CASES = [
    Case(network, answer, pattern, length, replace)
    for (network, answer, pattern, length, replace) in [
        list(read_files(case[0], case[1])) + [case[2], case[3], case[4]]
        for case in DINAMYC_ARP_FILE_NAMES
    ]
]


@pytest.mark.parametrize("test", TEST_CASES)
def test_miminet_work(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)
    animation = re.sub(r'"timestamp": "\d+"', r'"timestamp": ""', animation)
    animation = re.sub(r'"id": "\w+"', r'"id": ""', animation)
    assert animation == test.json_answer


@pytest.mark.parametrize("test", DINAMYC_PORT_TEST_CASES)
def test_miminet_work_for_dinamyc_port_test_cases(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)
    animation = re.sub(r'"timestamp": "\d+"', r'"timestamp": ""', animation)
    animation = re.sub(r'"id": "\w+"', r'"id": ""', animation)
    port_string = re.search(test.pattern_in_network, animation)
    assert port_string is not None
    port = port_string.group(0)[test.pattern_len :]
    test.json_answer = re.sub(test.pattern_for_replace, port, test.json_answer)
    assert animation == test.json_answer


@pytest.mark.parametrize("test", DINAMYC_ARP_TEST_CASES)
def test_miminet_work_for_dinamyc_arp_test_cases(test: Case) -> None:
    animation, pcaps = simulate(test.json_network)
    animation = re.sub(r'"timestamp": "\d+"', r'"timestamp": ""', animation)
    animation = re.sub(r'"id": "\w+"', r'"id": ""', animation)
    animation = re.sub(
        r'"ARP-response.+ at ([0-9a-fA-F]{2}[:]){6}"', r'"ARP-response"', animation
    )
    print(animation)
    print(---------xxxxxxxxxxxxxx------------)
    assert animation == test.json_answer
