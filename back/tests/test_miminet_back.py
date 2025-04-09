import dataclasses
import re
import json
from pathlib import Path

from mininet.log import setLogLevel, info, error
import pytest
from src.tasks import simulate

setLogLevel("info")

# Directory with test files
TEST_JSON_DIR = Path("test_json/")

# Suffixes of test files
NETWORK_FILE_SUFFIX = "_network.json"
ANSWER_FILE_SUFFIX = "_answer.json"

# Packets that can be skipped (contain not very informative data)
EXCLUDE_PATTERNS = [re.compile(r"^ARP"), re.compile(r"RSTP")]

# Dynamic regex patterns that should be replaced by static patterns
# example: TCP dynamic port
SUBSTITUTIONS = [
    (re.compile(r"(UDP )\d+ > \d+"), r"\1PORT > PORT"),
    (re.compile(r"(TCP .*?)\d+ > \d+"), r"\1PORT > PORT"),
    (re.compile(r"TCP \(SYN\) \d+"), r"port"),
    (re.compile(r"ARP-response\n.+ at ([0-9a-fA-F]{2}[:]){6}"), r"mac"),
    (re.compile(r'"ARP-response.+? at .+?"'), r'"ARP-response"'),
]


def read_files(network_filename: str, answer_filename: str):
    """Read both expected and actual json files."""
    expected_path = TEST_JSON_DIR / network_filename
    answer_path = TEST_JSON_DIR / answer_filename

    with expected_path.open("r") as exp_file, answer_path.open("r") as act_file:
        info(f"Reading files: {network_filename}, {answer_filename}.")
        return exp_file.read(), act_file.read()


def load_test_files(directory: Path):
    """Load test and answer JSON files, pairing them."""

    test_dir = Path(directory)

    if not test_dir.is_dir():
        raise FileNotFoundError(f"Directory '{directory}' not found.")

    network_files = sorted(f.name for f in test_dir.glob(f"*{NETWORK_FILE_SUFFIX}"))
    answer_files = sorted(f.name for f in test_dir.glob(f"*{ANSWER_FILE_SUFFIX}"))

    if len(network_files) != len(answer_files):
        raise ValueError("Mismatch between network and answer JSON files.")

    result_files = list(zip(network_files, answer_files))
    info(f"Found {len(result_files)} test cases in {test_dir.name}.")

    return result_files


def normalize_packet_data(packet_data: str) -> str:
    """Normalize packet data by replacing volatile parts."""
    for pattern, repl in SUBSTITUTIONS:
        packet_data = pattern.sub(repl, packet_data)

    return packet_data.replace("\n", "\\n").strip()


def extract_important_fields(packets_json: str) -> list[dict[str, str]]:
    """Extracts relevant fields from emulation packets, excluding uninformative ones."""

    packets = json.loads(packets_json)
    important_packets = []

    for packet_group in packets:
        for packet in packet_group:
            pkg_label = packet["data"]["label"]
            pkg_type = packet["config"]["type"]

            # Skip uninformative packets
            if any(pattern.match(pkg_label) for pattern in EXCLUDE_PATTERNS):
                continue

            important_packets.append(
                {
                    "type": normalize_packet_data(pkg_type),
                    "label": normalize_packet_data(pkg_label),
                    "source": packet["config"]["source"],
                    "target": packet["config"]["target"],
                    "path": packet["config"]["path"],
                }
            )

    important_packets.sort(key=lambda x: (x["path"], x["source"]))

    info("Extracted important fields from packets.")
    return important_packets


@dataclasses.dataclass
class Case:
    json_network: str  # Network that we should emulate
    json_answer: str  # Answer that emulation should return


# Generate test cases
TEST_FILES = load_test_files(TEST_JSON_DIR)
TEST_CASES = [Case(*read_files(n, a)) for n, a in TEST_FILES]


@pytest.mark.parametrize("test", TEST_CASES)
def test_miminet_work(test: Case, request) -> None:
    """Test network emulation using Mininet."""
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
