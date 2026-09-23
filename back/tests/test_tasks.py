"""Unit tests for tasks.py network filtering, schema caching and retry logic.

Covers the pure helpers (_filter_unknown_nodes, _has_meaningful_packets,
get_network_schema caching) and run_miminet's retry/exception paths with the
emulator mocked, so no OVS/emulation environment is needed.
"""

from types import SimpleNamespace


from src import tasks as T


def meaningful_ip() -> list:
    return [[{"config": {"type": "ICMP echo-request"}}]]


def control_only() -> list:
    return [[{"config": {"type": "STP"}}]]


def dhcp_discover_only() -> list:
    return [[{"config": {"type": "DHCP Discover"}}]]


def dhcp_answered() -> list:
    return [[{"config": {"type": "DHCP ACK"}}]]


def test_filter_unknown_nodes_drops_unknown_types():
    data = {
        "nodes": [
            {"config": {"type": "host"}},
            {"config": {"type": "router"}},
            {"config": {"type": "alien"}},
            {"config": {}},
            {},
        ]
    }
    out = T._filter_unknown_nodes(data)
    assert out is data
    assert [n["config"]["type"] for n in out["nodes"]] == ["host", "router"]


def test_filter_unknown_nodes_defaults_missing_nodes():
    out = T._filter_unknown_nodes({"nodes": []})
    assert out["nodes"] == []


def test_get_network_schema_cached():
    T._network_schema = None
    first = T.get_network_schema()
    second = T.get_network_schema()
    assert first is second
    assert first is not None


def test_has_meaningful_packets_empty():
    assert not T._has_meaningful_packets([])


def test_has_meaningful_packets_control_only():
    assert not T._has_meaningful_packets(control_only())


def test_has_meaningful_packets_ip():
    assert T._has_meaningful_packets(meaningful_ip())


def test_has_meaningful_packets_arp():
    assert T._has_meaningful_packets([[{"config": {"type": "ARP-request"}}]])


def test_has_meaningful_packets_dhcp_discover_only():
    assert not T._has_meaningful_packets(dhcp_discover_only())


def test_has_meaningful_packets_dhcp_answered():
    assert T._has_meaningful_packets(dhcp_answered())


def _patch_run(monkeypatch, emulate_results=None, jobs=()):
    fake_schema = SimpleNamespace(
        load=lambda _jnet, **_kwargs: SimpleNamespace(jobs=list(jobs))
    )
    monkeypatch.setattr(T, "get_network_schema", lambda: fake_schema)
    if emulate_results is None:

        def boom(_net):
            raise RuntimeError("emulation failed")

        monkeypatch.setattr(T, "emulate", boom)
    else:
        calls = {"n": 0}

        def fake_emulate(_net):
            result = emulate_results[min(calls["n"], len(emulate_results) - 1)]
            calls["n"] += 1
            return result

        monkeypatch.setattr(T, "emulate", fake_emulate)
        return calls


def test_run_miminet_returns_meaningful(monkeypatch):
    calls = _patch_run(
        monkeypatch, emulate_results=[(meaningful_ip(), ["p1"])], jobs=[1]
    )
    anim, pcaps = T.run_miminet("{}")
    assert pcaps == ["p1"]
    assert calls["n"] == 1


def test_run_miminet_retries_until_meaningful(monkeypatch):
    results = [([], []), (control_only(), []), (meaningful_ip(), ["p3"])]
    calls = _patch_run(monkeypatch, emulate_results=results, jobs=[1])
    anim, pcaps = T.run_miminet("{}")
    assert pcaps == ["p3"]
    assert calls["n"] == 3


def test_run_miminet_exhausts_retries_on_empty(monkeypatch):
    calls = _patch_run(monkeypatch, emulate_results=[([], [])], jobs=[1])
    anim, pcaps = T.run_miminet("{}")
    assert anim == "[]"
    assert pcaps == []
    assert calls["n"] == 4


def test_run_miminet_returns_after_exception_retries(monkeypatch):
    _patch_run(monkeypatch, emulate_results=None, jobs=[1])
    anim, pcaps = T.run_miminet("{}")
    assert anim == "[]"
    assert pcaps == []


def test_run_miminet_no_jobs_skips_retry_check(monkeypatch):
    calls = _patch_run(monkeypatch, emulate_results=[([], [])], jobs=[])
    anim, pcaps = T.run_miminet("{}")
    assert anim == "[]"
    assert pcaps == []
    assert calls["n"] == 1


def test_mininet_worker_no_headers(monkeypatch):
    sent = []
    monkeypatch.setattr(T, "run_miminet", lambda _j: ("[]", []))
    monkeypatch.setattr(T.app, "send_task", lambda *a, **k: sent.append((a, k)) or None)
    result = T.mininet_worker.run("{}")
    assert result == ('"[]"', [])
    assert sent == []


def test_mininet_worker_sends_result(monkeypatch):
    sent = []
    monkeypatch.setattr(T, "run_miminet", lambda _j: ("[]", []))
    monkeypatch.setattr(T.app, "send_task", lambda *a, **k: sent.append((a, k)) or None)
    T.mininet_worker.push_request(
        headers={"network_task_name": "send_result"}, id="task-1"
    )
    try:
        result = T.mininet_worker.run("{}")
    finally:
        T.mininet_worker.pop_request()
    assert result == ('"[]"', [])
    assert len(sent) == 1
    args, kwargs = sent[0]
    assert args[0] == "send_result"
    assert kwargs["task_id"] == "task-1"
    assert kwargs["exchange_type"] is not None
