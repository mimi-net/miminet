from src.net_utils.captures import (
    capture_out_path,
    capture_paths,
    iter_capture_out_files,
)


def test_capture_paths_layout():
    inout, out = capture_paths("host1_0")
    assert inout == "/tmp/capture_host1_0.pcapng"
    assert out == "/tmp/capture_host1_0_out.pcapng"


def test_capture_out_path():
    assert capture_out_path("l2sw1_3") == "/tmp/capture_l2sw1_3_out.pcapng"


def test_iter_capture_out_files_visits_every_endpoint():
    interfaces = [
        ("l1a", "l1b", "edge_1", "s", "t", 0, 0),
        ("l2a", "l2b", "edge_2", "s", "t", 0, 0),
    ]
    got = list(iter_capture_out_files(interfaces))
    assert got == [
        ("l1a", "/tmp/capture_l1a_out.pcapng"),
        ("l1b", "/tmp/capture_l1b_out.pcapng"),
        ("l2a", "/tmp/capture_l2a_out.pcapng"),
        ("l2b", "/tmp/capture_l2b_out.pcapng"),
    ]
