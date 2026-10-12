"""Regression tests for issue #503: textboxes must not reset the emulation.

A textbox (a canvas comment) is a graph node with ``config.type == "textbox"``.
Back drops such nodes before building the topology, so adding, editing or
removing one cannot change what the emulation produces. The server used to
delete the network's ``Simulate`` rows on any of these edits anyway; now it
keeps them unless an emulated part of the network changed.
"""

import copy
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask

import configurators
import miminet_network
from configurators import HostConfigurator, TextboxConfigurator
from miminet_network import emulation_changed


def _host(node_id: str, x: float = 0, label: str | None = None) -> dict:
    return {
        "classes": ["host"],
        "config": {"type": "host", "label": label or node_id, "default_gw": ""},
        "data": {"id": node_id, "label": label or node_id},
        "interface": [],
        "position": {"x": x, "y": 0},
    }


def _textbox(node_id: str, label: str = "comment") -> dict:
    return {
        "classes": ["textbox"],
        "config": {"type": "textbox", "label": label, "tb_fontsize": 12},
        "data": {"id": node_id, "label": label},
        "interface": [],
        "position": {"x": 10, "y": 10},
    }


EDGE = {
    "data": {
        "id": "edge_1",
        "source": "host_1",
        "target": "host_2",
        "loss_percentage": 0,
        "duplicate_percentage": 0,
    }
}
JOB = {"id": "job_1", "job_id": 1, "host_id": "host_1", "arg_1": "10.0.0.2"}


def _network(nodes: list) -> dict:
    return {"nodes": nodes, "edges": [EDGE], "jobs": [JOB]}


BASE = _network([_host("host_1"), _host("host_2")])


# --- emulation_changed --------------------------------------------------------


@pytest.mark.parametrize(
    "edited",
    [
        pytest.param(
            _network([_host("host_1"), _host("host_2"), _textbox("textbox_1")]),
            id="textbox added",
        ),
        pytest.param(
            _network([_host("host_1"), _textbox("textbox_1", "new"), _host("host_2")]),
            id="textbox added between devices",
        ),
        pytest.param(
            _network([_host("host_1", x=500), _host("host_2")]),
            id="device moved",
        ),
    ],
)
def test_edit_outside_emulation_keeps_simulation(edited):
    assert not emulation_changed(BASE, edited)


def test_textbox_edited_or_removed_keeps_simulation():
    with_textbox = _network([_host("host_1"), _host("host_2"), _textbox("textbox_1")])
    relabelled = _network(
        [_host("host_1"), _host("host_2"), _textbox("textbox_1", "edited")]
    )

    assert not emulation_changed(with_textbox, relabelled)
    assert not emulation_changed(with_textbox, BASE)


@pytest.mark.parametrize(
    "edited",
    [
        pytest.param(
            _network([_host("host_1"), _host("host_2"), _host("host_3")]),
            id="device added",
        ),
        pytest.param(_network([_host("host_1")]), id="device removed"),
        pytest.param(
            _network([_host("host_1", label="renamed"), _host("host_2")]),
            id="device relabelled",
        ),
        pytest.param({**BASE, "edges": []}, id="edge removed"),
        pytest.param({**BASE, "jobs": []}, id="job removed"),
    ],
)
def test_edit_to_emulated_part_resets_simulation(edited):
    assert emulation_changed(BASE, edited)


# --- configurators ------------------------------------------------------------


@pytest.fixture
def sims_store(monkeypatch):
    """Stub the Simulate query, the db session and celery's revoke."""
    sims = [SimpleNamespace(task_guid="task-1"), SimpleNamespace(task_guid="task-2")]

    query = MagicMock()
    query.filter.return_value.all.return_value = sims
    monkeypatch.setattr(configurators, "Simulate", MagicMock(query=query))

    db = MagicMock()
    monkeypatch.setattr(configurators, "db", db)

    celery = MagicMock()
    monkeypatch.setattr(configurators, "app", celery)

    return SimpleNamespace(sims=sims, db=db, celery=celery)


def _save(configurator, json_network: dict) -> SimpleNamespace:
    network = SimpleNamespace(id=1, network="{}")
    configurator._cur_network = network
    configurator._json_network = json_network
    configurator._AbstractConfigurator__conf_sims_delete()
    return network


def test_textbox_configurator_saves_without_deleting_simulations(sims_store):
    json_network = _network([_host("host_1"), _textbox("textbox_1", "edited")])

    network = _save(TextboxConfigurator(), json_network)

    assert json.loads(network.network) == json_network
    sims_store.db.session.commit.assert_called_once()
    sims_store.db.session.delete.assert_not_called()
    sims_store.celery.control.revoke.assert_not_called()


def test_device_configurator_still_deletes_simulations(sims_store):
    json_network = _network([_host("host_1", label="renamed"), _host("host_2")])

    network = _save(HostConfigurator(), json_network)

    assert json.loads(network.network) == json_network
    assert sims_store.db.session.delete.call_count == len(sims_store.sims)
    assert sims_store.celery.control.revoke.call_count == len(sims_store.sims)
    sims_store.db.session.commit.assert_called_once()


# --- graph save endpoints -----------------------------------------------------


@pytest.fixture
def saved_network(monkeypatch):
    """A stored network with a textbox, one simulation and one pcap."""
    stored = _network([_host("host_1"), _host("host_2"), _textbox("textbox_1")])
    stored["pcap"] = ["capture.pcap"]
    net = SimpleNamespace(id=1, network=json.dumps(stored))

    net_query = MagicMock()
    net_query.filter.return_value.filter.return_value.first.return_value = net
    monkeypatch.setattr(miminet_network, "Network", MagicMock(query=net_query))

    sims = [SimpleNamespace(task_guid="task-1")]
    sim_query = MagicMock()
    sim_query.filter.return_value.all.return_value = sims
    monkeypatch.setattr(miminet_network, "Simulate", MagicMock(query=sim_query))

    db = MagicMock()
    monkeypatch.setattr(miminet_network, "db", db)
    monkeypatch.setattr(miminet_network, "get_jwt_identity", lambda: 1)

    return SimpleNamespace(stored=stored, net=net, db=db)


def _post(view, payload):
    app = Flask(__name__)
    with app.test_request_context(
        "/post?guid=network-guid", method="POST", json=payload
    ):
        # Skip @jwt_required(): the identity is stubbed in the fixture.
        return view.__wrapped__()


def test_removing_textbox_keeps_simulation_and_pcaps(saved_network):
    nodes = [_host("host_1"), _host("host_2")]

    response = _post(miminet_network.post_nodes_edges, [nodes, [EDGE], [JOB]])

    assert response.status_code == 201
    saved = json.loads(saved_network.net.network)
    assert saved["nodes"] == nodes
    assert saved["pcap"] == ["capture.pcap"]
    saved_network.db.session.delete.assert_not_called()


def test_removing_device_still_resets_simulation_and_pcaps(saved_network):
    nodes = [_host("host_1"), _textbox("textbox_1")]

    _post(miminet_network.post_nodes_edges, [nodes, [EDGE], [JOB]])

    saved = json.loads(saved_network.net.network)
    assert saved["pcap"] == []
    saved_network.db.session.delete.assert_called_once()


def test_adding_textbox_keeps_simulation(saved_network):
    nodes = copy.deepcopy(saved_network.stored["nodes"]) + [_textbox("textbox_2")]

    response = _post(miminet_network.post_nodes, nodes)

    assert response.status_code == 201
    assert json.loads(saved_network.net.network)["nodes"] == nodes
    saved_network.db.session.delete.assert_not_called()


def test_adding_device_still_resets_simulation(saved_network):
    nodes = copy.deepcopy(saved_network.stored["nodes"]) + [_host("host_3")]

    _post(miminet_network.post_nodes, nodes)

    saved_network.db.session.delete.assert_called_once()
