import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from ai_generate import _fix_topology, _validate_topology  # noqa: E402


def make_edge(edge_id, source, target):
    return {"data": {"id": edge_id, "source": source, "target": target}}


def make_node(node_id, ifaces, node_type="host"):
    return {
        "classes": [node_type],
        "config": {"label": node_id, "type": node_type, "default_gw": ""},
        "data": {"id": node_id, "label": node_id},
        "interface": ifaces,
        "position": {"x": 0, "y": 0},
    }


def make_iface(connect, node_id, idx):
    return {
        "connect": connect,
        "id": f"{node_id}_{idx}",
        "name": f"{node_id}_{idx}",
        "ip": "",
        "netmask": 0,
    }


class TestValidateTopology:
    def test_valid_topology(self):
        topology = {
            "nodes": [
                make_node("host_1", [make_iface("edge_1", "host_1", 1)]),
                make_node("host_2", [make_iface("edge_1", "host_2", 1)]),
            ],
            "edges": [make_edge("edge_1", "host_1", "host_2")],
        }
        errors = _validate_topology(topology)
        assert errors == []

    def test_no_nodes(self):
        errors = _validate_topology({"nodes": [], "edges": []})
        assert any("узлов" in e for e in errors)

    def test_no_edges(self):
        topology = {
            "nodes": [make_node("host_1", [])],
            "edges": [],
        }
        errors = _validate_topology(topology)
        assert any("рёбер" in e for e in errors)

    def test_isolated_node(self):
        topology = {
            "nodes": [
                make_node("host_1", [make_iface("edge_1", "host_1", 1)]),
                make_node("host_2", [make_iface("edge_1", "host_2", 1)]),
                make_node("host_3", []),
            ],
            "edges": [make_edge("edge_1", "host_1", "host_2")],
        }
        errors = _validate_topology(topology)
        assert any("host_3" in e for e in errors)

    def test_disconnected_graph(self):
        topology = {
            "nodes": [
                make_node("host_1", [make_iface("edge_1", "host_1", 1)]),
                make_node("host_2", [make_iface("edge_1", "host_2", 1)]),
                make_node("host_3", [make_iface("edge_2", "host_3", 1)]),
                make_node("host_4", [make_iface("edge_2", "host_4", 1)]),
            ],
            "edges": [
                make_edge("edge_1", "host_1", "host_2"),
                make_edge("edge_2", "host_3", "host_4"),
            ],
        }
        errors = _validate_topology(topology)
        assert any("несвязный" in e for e in errors)

    def test_wrong_interface_count(self):
        topology = {
            "nodes": [
                make_node(
                    "host_1",
                    [make_iface("edge_1", "host_1", 1), make_iface("edge_2", "host_1", 2)],
                ),
                make_node("host_2", [make_iface("edge_1", "host_2", 1)]),
            ],
            "edges": [make_edge("edge_1", "host_1", "host_2")],
        }
        errors = _validate_topology(topology)
        assert any("host_1" in e and "интерфейс" in e for e in errors)

    def test_invalid_edge_reference(self):
        topology = {
            "nodes": [
                make_node("host_1", [make_iface("edge_NONEXISTENT", "host_1", 1)]),
                make_node("host_2", [make_iface("edge_1", "host_2", 1)]),
            ],
            "edges": [make_edge("edge_1", "host_1", "host_2")],
        }
        errors = _validate_topology(topology)
        assert any("edge_NONEXISTENT" in e for e in errors)


class TestFixTopology:
    def test_fix_wrong_connect(self):
        topology = {
            "nodes": [
                make_node("host_1", [make_iface("edge_WRONG", "host_1", 1)]),
                make_node("host_2", [make_iface("edge_1", "host_2", 1)]),
            ],
            "edges": [make_edge("edge_1", "host_1", "host_2")],
        }
        _fix_topology(topology)
        iface = topology["nodes"][0]["interface"][0]
        assert iface["connect"] == "edge_1"

    def test_fix_does_not_break_valid(self):
        topology = {
            "nodes": [
                make_node("host_1", [make_iface("edge_1", "host_1", 1)]),
                make_node("host_2", [make_iface("edge_1", "host_2", 1)]),
            ],
            "edges": [make_edge("edge_1", "host_1", "host_2")],
        }
        _fix_topology(topology)
        assert topology["nodes"][0]["interface"][0]["connect"] == "edge_1"
        assert topology["nodes"][1]["interface"][0]["connect"] == "edge_1"
