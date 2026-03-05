import dataclasses
import re
import json
import logging
import sys
from pathlib import Path

from mininet.log import setLogLevel, info, warning, error
import pytest
from src.tasks import run_miminet

setLogLevel("info")

# _log is used only for debug-level tracing (no equivalent in mininet)
# and for error output in _log_packet_diff.
_log = logging.getLogger("miminet_test")
_log.setLevel(logging.DEBUG)
if not _log.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    _log.addHandler(_handler)

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


def _fmt_packet(pkt: dict) -> str:
    """Format a single packet dict for human-readable log output."""
    return f"  [{pkt['path']}] {pkt['source']} -> {pkt['target']} | {pkt['label']}"


def _log_packet_diff(
    test_name: str,
    actual: list[dict[str, str]],
    expected: list[dict[str, str]],
) -> None:
    """Log a structured diff between actual and expected packet lists."""
    _log.error("=== DHCP/packet diff for: %s ===", test_name)

    actual_set = set(frozenset(p.items()) for p in actual)
    expected_set = set(frozenset(p.items()) for p in expected)

    missing = [p for p in expected if frozenset(p.items()) not in actual_set]
    extra = [p for p in actual if frozenset(p.items()) not in expected_set]

    if missing:
        _log.error(
            "--- MISSING packets (in expected but NOT in actual) [%d] ---", len(missing)
        )
        for p in missing:
            _log.error(_fmt_packet(p))
    else:
        info("No missing packets.")

    if extra:
        _log.error(
            "+++ EXTRA packets (in actual but NOT in expected) [%d] +++", len(extra)
        )
        for p in extra:
            _log.error(_fmt_packet(p))
    else:
        info("No extra packets.")

    _log.error("--- Full ACTUAL list (%d packets) ---", len(actual))
    for i, p in enumerate(actual):
        _log.error("  [%02d] %s", i, _fmt_packet(p))

    _log.error("--- Full EXPECTED list (%d packets) ---", len(expected))
    for i, p in enumerate(expected):
        _log.error("  [%02d] %s", i, _fmt_packet(p))


def remove_duplicate_packets(
    packets: list[dict[str, str]],
) -> list[dict[str, str]]:
    res = []
    seen = set()
    for pck in packets:
        fs = frozenset(pck.items())
        if fs not in seen:
            seen.add(fs)
            res.append(pck)
    return res


def extract_important_fields(
    packets_json: str, label: str = ""
) -> list[dict[str, str]]:
    """Extracts relevant fields from emulation packets, excluding uninformative ones.

    Args:
        packets_json: JSON string with packets.
        label: Optional label used in debug logging (e.g. "actual" or "expected").
    """

    packets = json.loads(packets_json)
    important_packets = []
    skipped_count = 0

    _log.debug("extract_important_fields(%s): total groups=%d", label, len(packets))

    for group_idx, packet_group in enumerate(packets):
        for pkt_idx, packet in enumerate(packet_group):
            pkg_label = packet["data"]["label"]
            pkg_type = packet["config"]["type"]

            # Skip uninformative packets
            if any(pattern.match(pkg_label) for pattern in EXCLUDE_PATTERNS):
                _log.debug(
                    "  [group=%d pkt=%d] SKIPPED (exclude pattern): %s",
                    group_idx,
                    pkt_idx,
                    pkg_label,
                )
                skipped_count += 1
                continue

            entry = {
                "type": normalize_packet_data(pkg_type),
                "label": normalize_packet_data(pkg_label),
                "source": packet["config"]["source"],
                "target": packet["config"]["target"],
                "path": packet["config"]["path"],
            }
            _log.debug(
                "  [group=%d pkt=%d] KEPT: path=%s src=%s -> tgt=%s | %s",
                group_idx,
                pkt_idx,
                entry["path"],
                entry["source"],
                entry["target"],
                entry["label"],
            )
            important_packets.append(entry)

    _log.debug(
        "extract_important_fields(%s): kept=%d skipped=%d",
        label,
        len(important_packets),
        skipped_count,
    )

    important_packets.sort(key=lambda x: (x["path"], x["source"], x["label"]))

    before_dedup = len(important_packets)
    important_packets = remove_duplicate_packets(important_packets)
    after_dedup = len(important_packets)
    if before_dedup != after_dedup:
        _log.debug(
            "extract_important_fields(%s): removed %d duplicates (%d -> %d)",
            label,
            before_dedup - after_dedup,
            before_dedup,
            after_dedup,
        )

    info("Extracted important fields from packets.")
    return important_packets


@dataclasses.dataclass
class Case:
    json_network: str  # Network that we should emulate
    json_answer: str  # Answer that emulation should return


def _case_name(network_filename: str) -> str:
    """Extract base name from network filename, e.g. 'dhcp_one_host_network.json' -> 'dhcp_one_host'."""
    return network_filename.removesuffix(NETWORK_FILE_SUFFIX)


# Generate test cases
TEST_FILES = load_test_files(TEST_JSON_DIR)
TEST_CASES = [
    pytest.param(Case(*read_files(n, a)), id=_case_name(n)) for n, a in TEST_FILES
]


@pytest.mark.parametrize("test", TEST_CASES)
def test_miminet_work(test: Case, request) -> None:
    """Test network emulation using Mininet."""
    test_name = request.node.name
    info(f"Running test: {test_name}.")
    info(f"=== START test: {test_name} ===")

    # Log the network topology being tested (jobs section is most informative)
    try:
        net_json = json.loads(test.json_network)
        info(
            f"Network jobs ({len(net_json.get('jobs', []))}): "
            + json.dumps(
                [
                    {
                        "host": j.get("host_id"),
                        "job_id": j.get("job_id"),
                        "cmd": j.get("print_cmd"),
                    }
                    for j in net_json.get("jobs", [])
                ],
                indent=2,
            )
        )
        info(
            f"Network nodes ({len(net_json.get('nodes', []))}): "
            + ", ".join(
                f"{n['data']['id']}({n['classes'][0]})"
                for n in net_json.get("nodes", [])
            )
        )
    except Exception as parse_exc:
        warning(f"Could not parse network JSON for logging: {parse_exc}")

    # Emulate network behavior based on the test case
    info(f"Starting emulation for: {test_name}")
    animation, _ = run_miminet(test.json_network)
    info(f"Emulation finished for: {test_name}")

    # Log the raw animation JSON for dhcp tests so we can inspect it in CI
    if "dhcp" in test_name.lower():
        info(f"Raw animation JSON:\n{json.dumps(json.loads(animation), indent=2)}")

    # Extract important packet fields while ignoring excluded packets
    actual_packets = extract_important_fields(animation, label="actual")
    expected_packets = extract_important_fields(test.json_answer, label="expected")

    info(
        f"Comparison: actual={len(actual_packets)} packets, "
        f"expected={len(expected_packets)} packets"
    )

    try:
        assert actual_packets == expected_packets
    except AssertionError as e:
        error(f"Test {test_name} failed: {str(e)}.")
        _log_packet_diff(test_name, actual_packets, expected_packets)
        raise e

    info(f"=== PASS test: {test_name} ===")
    info(f"Finish test {test_name}.")
