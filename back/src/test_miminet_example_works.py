import dataclasses
import time

import pytest
import re

from tasks import mininet_worker


@dataclasses.dataclass
class Case:
    json_network: str
    json_answer: str


DEFAULT_JSON_TEST_DIRECTORY = 'test_json/'


def read_files(network_filename: str, answer_filename: str):
    with open(DEFAULT_JSON_TEST_DIRECTORY + network_filename, "r") as file1, open(
            DEFAULT_JSON_TEST_DIRECTORY + answer_filename, "r") as file2:
        return file1.read(), file2.read().rstrip()


FILE_NAMES = [("switch_and_hub_network.json", "switch_and_hub_answer.json"),
              ("router_network.json", "router_answer.json")]

TEST_CASES = [
    Case(network, answer)
    for (network, answer) in [
        read_files(file[0], file[1])
        for file in FILE_NAMES
    ]
]


@pytest.mark.parametrize("test", TEST_CASES)
def test_get_program_info_in_csv(test: Case) -> None:
    animation, pcaps = mininet_worker(test.json_network)
    animation = re.sub(r'"timestamp": "\d+"', r'"timestamp": ""', animation)
    animation = re.sub(r'"id": "\w+"', r'"id": ""', animation)
    assert animation == test.json_answer
