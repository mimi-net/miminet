"""Unit tests for the capture-readiness gate.

The gate consumes ipmininet's ``NetworkCapture.wait_until_capturing`` in strict
mode (mimidump READY signal, or a pcap file that keeps growing past its header).
These tests mirror the strict-mode matrix from ipmininet (mimi-net/ipmininet
PR #30) at the miminet orchestration level, using fakes so they run rootless
and dependency-free.
"""

from types import SimpleNamespace
from unittest import mock

import pytest

from src.net_utils.captures import capture_paths
from src.net_utils.readiness import iter_capture_endpoints
from src.network import MiminetNetwork

# ---------------- Fakes ---------------- #


class FakeNode:
    def __init__(self, intfs):
        self._intfs = intfs

    def intf(self, name):
        return self._intfs.get(name)


class FakeCapture:
    def __init__(self, live, iface):
        self.live = live
        self.calls = []
        self.ongoing_captures = {}
        self.started = []

    def wait_until_capturing(self, iface_name, timeout=0.1, strict=False):
        self.calls.append((iface_name, timeout, strict))
        return self.live

    def start(self, intf):
        self.started.append(intf)


class FakeProc:
    def __init__(self):
        self.killed = False
        self.waited = False

    def poll(self):
        return None

    def kill(self):
        self.killed = True

    def wait(self):
        self.waited = True


def make_intf(captures):
    return {"captures": captures}


def make_net(interfaces, intfs):
    net = MiminetNetwork.__new__(MiminetNetwork)
    setattr(
        net,
        "_MiminetNetwork__network_topology",
        SimpleNamespace(interfaces=interfaces),
    )
    setattr(net, "_MiminetNetwork__network_schema", SimpleNamespace(nodes=[]))
    net.nameToNode = {node: FakeNode(ifs) for node, ifs in intfs.items()}
    return net


def monotonic_clock():
    state = {"t": 0.0}

    def tick():
        state["t"] += 0.1
        return state["t"]

    return tick


def wait_until_ready(net, timeout=1.0, poll=0.1):
    return getattr(net, "_MiminetNetwork__wait_until_ready")(timeout=timeout, poll=poll)


def captures_not_live(net, timeout=0.1):
    return getattr(net, "_MiminetNetwork__captures_not_live")(timeout=timeout)


def restart_captures(net, stale):
    return getattr(net, "_MiminetNetwork__restart_captures")(stale)


# ---------------- iter_capture_endpoints ---------------- #


def test_iter_capture_endpoints_visits_every_endpoint():
    interfaces = [
        ("l1a", "l1b", "edge_1", "host1", "router1", 0, 0),
        ("l2a", "l2b", "edge_2", "host1", "router1", 0, 0),
    ]
    intfs = {
        "host1": {"l1a": make_intf(["c1a"]), "l2a": make_intf(["c2a"])},
        "router1": {"l1b": make_intf(["c1b"]), "l2b": make_intf(["c2b"])},
    }

    def get_intf(node_name, iface_name):
        return intfs.get(node_name, {}).get(iface_name)

    got = list(iter_capture_endpoints(interfaces, get_intf))
    assert [(node, iface) for node, iface, _intf, _caps in got] == [
        ("host1", "l1a"),
        ("router1", "l1b"),
        ("host1", "l2a"),
        ("router1", "l2b"),
    ]
    assert [caps for _node, _iface, _intf, caps in got] == [
        ["c1a"],
        ["c1b"],
        ["c2a"],
        ["c2b"],
    ]


def test_iter_capture_endpoints_skips_missing_interfaces():
    interfaces = [("l1a", "l1b", "edge_1", "host1", "router1", 0, 0)]
    intfs = {"host1": {"l1a": make_intf(["c"])}}

    def get_intf(node_name, iface_name):
        return intfs.get(node_name, {}).get(iface_name)

    got = list(iter_capture_endpoints(interfaces, get_intf))
    assert [(node, iface) for node, iface, _intf, _caps in got] == [("host1", "l1a")]


def test_iter_capture_endpoints_ignores_lookup_errors():
    interfaces = [("l1a", "l1b", "edge_1", "host1", "router1", 0, 0)]

    def get_intf(node_name, iface_name):
        if node_name == "host1":
            raise KeyError(node_name)
        if iface_name == "l1b":
            raise AttributeError(iface_name)
        return None

    assert list(iter_capture_endpoints(interfaces, get_intf)) == []


# ---------------- __captures_not_live strict matrix ---------------- #


@pytest.mark.parametrize(
    ("live", "expected"),
    [
        pytest.param(True, [], id="ready-signal-live"),
        pytest.param(False, [("host1", "l1a")], id="bare-file-not-live"),
        pytest.param(True, [], id="growing-file-live"),
        pytest.param(False, [("host1", "l1a")], id="dead-process-not-live"),
        pytest.param(False, [("host1", "l1a")], id="missing-file-not-live"),
    ],
)
def test_captures_not_live_strict_gate(live, expected):
    interfaces = [("l1a", "l1b", "edge_1", "host1", "router1", 0, 0)]
    capture = FakeCapture(live=live, iface="l1a")
    intfs = {
        "host1": {"l1a": make_intf([capture])},
        "router1": {"l1b": make_intf([])},
    }
    net = make_net(interfaces, intfs)

    assert captures_not_live(net) == expected
    assert capture.calls == [("l1a", 0.1, True)]


def test_captures_not_live_passes_restart_timeout():
    interfaces = [("l1a", "l1b", "edge_1", "host1", "router1", 0, 0)]
    capture = FakeCapture(live=False, iface="l1a")
    intfs = {
        "host1": {"l1a": make_intf([capture])},
        "router1": {"l1b": make_intf([])},
    }
    net = make_net(interfaces, intfs)

    assert captures_not_live(net, timeout=1.0) == [("host1", "l1a")]
    assert capture.calls == [("l1a", 1.0, True)]


def test_captures_not_live_any_capture_fails():
    interfaces = [("l1a", "l1b", "edge_1", "host1", "router1", 0, 0)]
    good = FakeCapture(live=True, iface="l1a")
    bad = FakeCapture(live=False, iface="l1a")
    intfs = {
        "host1": {"l1a": make_intf([good, bad])},
        "router1": {"l1b": make_intf([])},
    }
    net = make_net(interfaces, intfs)

    assert captures_not_live(net) == [("host1", "l1a")]
    assert good.calls == [("l1a", 0.1, True)]
    assert bad.calls == [("l1a", 0.1, True)]


# ---------------- __restart_captures ---------------- #


def test_restart_captures_kills_removes_restarts():
    interfaces = [("l1a", "l1b", "edge_1", "host1", "router1", 0, 0)]
    capture = FakeCapture(live=False, iface="l1a")
    proc = FakeProc()
    capture.ongoing_captures = {"l1a": proc}
    intf = make_intf([capture])
    intfs = {
        "host1": {"l1a": intf},
        "router1": {"l1b": make_intf([])},
    }
    net = make_net(interfaces, intfs)

    with mock.patch("src.network.os.path.exists", return_value=True), mock.patch(
        "src.network.os.remove"
    ) as remove_mock, mock.patch("src.network.info"):
        restart_captures(net, [("host1", "l1a")])

    assert proc.killed
    assert proc.waited
    assert capture.ongoing_captures == {}
    assert capture.started == [intf]
    assert {call.args[0] for call in remove_mock.call_args_list} == set(
        capture_paths("l1a")
    )


def test_restart_captures_skips_unknown_endpoints():
    interfaces = [("l1a", "l1b", "edge_1", "host1", "router1", 0, 0)]
    capture = FakeCapture(live=False, iface="l1a")
    intfs = {
        "host1": {"l1a": make_intf([capture])},
        "router1": {"l1b": make_intf([])},
    }
    net = make_net(interfaces, intfs)

    with mock.patch("src.network.os.path.exists", return_value=True), mock.patch(
        "src.network.os.remove"
    ) as remove_mock, mock.patch("src.network.info"):
        restart_captures(net, [("ghost", "nope")])

    assert not capture.started
    remove_mock.assert_not_called()


# ---------------- __wait_until_ready orchestration ---------------- #


def test_wait_until_ready_all_live_returns():
    net = MiminetNetwork.__new__(MiminetNetwork)
    with mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__captures_not_live", return_value=[]
    ), mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__unconverged_switches", return_value=[]
    ), mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__unreachable_vtep_targets", return_value=[]
    ), mock.patch(
        "src.network.time.monotonic", return_value=0.0
    ), mock.patch(
        "src.network.time.sleep"
    ), mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__restart_captures"
    ) as restart:
        wait_until_ready(net)

    restart.assert_not_called()


def test_wait_until_ready_timeout_lists_captures():
    net = MiminetNetwork.__new__(MiminetNetwork)
    not_live = [("host1", "l1a"), ("router1", "l1b")]
    with mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__captures_not_live", return_value=not_live
    ), mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__unconverged_switches", return_value=[]
    ), mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__unreachable_vtep_targets", return_value=[]
    ), mock.patch(
        "src.network.time.monotonic", side_effect=monotonic_clock()
    ), mock.patch(
        "src.network.time.sleep"
    ), mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__restart_captures"
    ) as restart:
        with pytest.raises(TimeoutError) as excinfo:
            wait_until_ready(net)

    assert "captures not live: l1a, l1b" in str(excinfo.value)
    restart.assert_not_called()


def test_wait_until_ready_restarts_once_after_grace():
    net = MiminetNetwork.__new__(MiminetNetwork)
    not_live = [("host1", "l1a")]
    with mock.patch.dict(
        "src.network.os.environ", {"MIMINET_CAPTURE_RESTART_GRACE": "0.0"}
    ), mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__captures_not_live", return_value=not_live
    ), mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__unconverged_switches", return_value=[]
    ), mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__unreachable_vtep_targets", return_value=[]
    ), mock.patch(
        "src.network.time.monotonic", side_effect=monotonic_clock()
    ), mock.patch(
        "src.network.time.sleep"
    ), mock.patch.object(
        MiminetNetwork, "_MiminetNetwork__restart_captures"
    ) as restart:
        with pytest.raises(TimeoutError):
            wait_until_ready(net)

    restart.assert_called_once()
    args, _kwargs = restart.call_args
    assert args[0] == not_live
