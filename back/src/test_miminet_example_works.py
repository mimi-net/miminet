import dataclasses
import re
import json
from pathlib import Path

from mininet.log import setLogLevel, info, error
import pytest
from tasks import simulate

setLogLevel("info")

# Directory with test files
TEST_JSON_DIR = Path("test_json/")

# Suffixes of test files
NETWORK_FILE_SUFFIX = "_network.json"
ANSWER_FILE_SUFFIX = "_answer.json"


def read_files(network_filename: str, answer_filename: str):
    """Read both expected and actual json files."""
    expected_path = TEST_JSON_DIR / network_filename
    answer_path = TEST_JSON_DIR / answer_filename

    with expected_path.open("r") as exp_file, answer_path.open("r") as act_file:
        info(f"Reading files: {network_filename}, {answer_filename}.")
        return exp_file.read(), act_file.read()


def load_test_files(directory: Path):
    """
    Reads all JSON files in the specified directory and pairs test and answer files.

    Args:
        directory (str): The directory containing the test and answer JSON files.

    Returns:
        list of tuples: Each tuple contains the paths to the test and answer JSON files.
    """
    test_dir = Path(directory)

    if not test_dir.is_dir():
        raise FileNotFoundError(f"Directory '{directory}' not found")

    json_files = sorted([file.name for file in test_dir.glob("*.json")])

    network_files, answer_files = [], []
    for test_file in json_files:
        if test_file.endswith(NETWORK_FILE_SUFFIX):
            network_files.append(test_file)
        elif test_file.endswith(ANSWER_FILE_SUFFIX):
            answer_files.append(test_file)
        else:
            raise ValueError(f"Find inappropriate file {test_file} in {test_dir.name}.")

    result_files = list(zip(network_files, answer_files))
    info(f"Find {len(result_files)} in {test_dir.name}.")

    return result_files


def normalize_packet_data(packet_data: str):
    """Apply common regex substitutions to remove volatile parts from the packet data (e.g. label or type).

    Args:
        packet_data (str): Part of packet that should be normalized.
    Returns:
        Normalized part of packet.
    """
    # Common regex patterns that are randomly generated and should be replaced
    subs = [
        (r"(UDP )\d+ > \d+", r"\1PORT > PORT"),
        (r"(TCP .*?)\d+ > \d+", r"\1PORT > PORT"),
        (r"TCP \(SYN\) \d+", r"port"),
        (r"ARP-response\n.+ at ([0-9a-fA-F]{2}[:]){6}", r"mac"),
        (r'"ARP-response.+? at .+?"', r'"ARP-response"'),
    ]

    for pattern, repl in subs:
        packet_data = re.sub(pattern, repl, packet_data)

    packet_data = packet_data.replace("\n", "\\n").strip()
    return packet_data


def extract_important_fields(packets_json) -> list[dict[str, str]]:
    """
    Extracts important (don't change every simulation) fields from packets, excluding packets that match the given regular expression.

    :param packets_json: JSON string with the simulation results.
    """

    # Packets with such patterns is not very informative(or they break tests) and can be skipped
    EXCLUDE_PATTERNS = [r"^ARP", r"RSTP"]

    packets = json.loads(packets_json)
    important_packets = []

    for packet_group in packets:
        for packet in packet_group:
            pkg_data = packet["data"]
            pkg_config = packet["config"]

            pkg_label = pkg_data["label"]
            pkg_type = pkg_config["type"]

            if any(re.match(pattern, pkg_label) for pattern in EXCLUDE_PATTERNS):
                continue  # Skip unimportant packages

            important_packet = {
                "type": normalize_packet_data(pkg_type),
                "label": normalize_packet_data(pkg_label),
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


@dataclasses.dataclass
class Case:
    json_network: str  # Network that we should emulate
    json_answer: str  # Answer that emulation should return


# Generate test cases
TEST_FILES = load_test_files(TEST_JSON_DIR)
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
