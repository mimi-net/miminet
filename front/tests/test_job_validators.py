import json

import pytest
from flask import Flask

from miminet_host import host, interface_check, server


@pytest.mark.parametrize("interface", ["eth0", "eth_0", "iface_87480866"])
def test_interface_check_accepts_supported_names(interface):
    assert interface_check(interface)


@pytest.mark.parametrize(
    "interface",
    [
        "",
        "eth0;touch /tmp/pwned;",
        "eth0.1",
        "Eth0",
        "eth 0",
        "a" * 16,
    ],
)
def test_interface_check_rejects_invalid_names(interface):
    assert not interface_check(interface)


def test_dhcp_client_invalid_interface_returns_warning_without_saving_job(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "unit-test"
    network = {
        "nodes": [
            {
                "classes": ["host"],
                "config": {"label": "host_1", "type": "host", "default_gw": ""},
                "data": {"id": "host_1", "label": "host_1"},
                "interface": [],
                "position": {"x": 0, "y": 0},
            }
        ],
        "jobs": [],
    }
    monkeypatch.setattr("configurators.current_user", type("User", (), {"id": 1})())
    monkeypatch.setattr("configurators.Network", type("NetworkModel", (), {}))

    class Query:
        def filter(self, *_args):
            return self

        def first(self):
            return type("SavedNetwork", (), {"network": json.dumps(network)})()

    monkeypatch.setattr("configurators.Network.query", Query(), raising=False)

    def prepare_node():
        host._json_network = network
        host._nodes = network["nodes"]
        host._node = network["nodes"][0]

    monkeypatch.setattr(host, "_conf_prepare_node", prepare_node)
    monkeypatch.setattr(host, "_conf_label_update", lambda: None)
    monkeypatch.setattr(host, "_conf_ip_addresses", lambda: None)
    monkeypatch.setattr(host, "_conf_gw", lambda: None)
    monkeypatch.setattr(host, "_AbstractConfigurator__conf_sims_delete", lambda: None)

    for interface in ("", "eth0;touch /tmp/pwned;"):
        with app.test_request_context(
            "/host/save_config",
            method="POST",
            data={
                "net_guid": "network-guid",
                "host_id": "host_1",
                "config_host_job_select_field": "108",
                "config_host_add_dhclient_interface_select_iface_field": interface,
            },
        ):
            response = host.configure()

        payload = response.get_json()
        assert "warning" in payload
        assert "Не указан или неверно указан интерфейс" in payload["warning"]
        assert payload["jobs"] == []


def test_dhcp_server_invalid_interface_returns_warning_without_saving_job(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "unit-test"
    network = {
        "nodes": [
            {
                "classes": ["server"],
                "config": {"label": "server_1", "type": "server", "default_gw": ""},
                "data": {"id": "server_1", "label": "server_1"},
                "interface": [],
                "position": {"x": 0, "y": 0},
            }
        ],
        "jobs": [],
    }

    def prepare_node():
        server._json_network = network
        server._nodes = network["nodes"]
        server._node = network["nodes"][0]

    monkeypatch.setattr(server, "_conf_prepare_node", prepare_node)
    monkeypatch.setattr(server, "_conf_label_update", lambda: None)
    monkeypatch.setattr(server, "_conf_ip_addresses", lambda: None)
    monkeypatch.setattr(server, "_conf_gw", lambda: None)
    monkeypatch.setattr(server, "_AbstractConfigurator__conf_sims_delete", lambda: None)

    for interface in ("", "eth0;touch /tmp/pwned;"):
        with app.test_request_context(
            "/host/server_save_config",
            method="POST",
            data={
                "net_guid": "network-guid",
                "server_id": "server_1",
                "config_server_job_select_field": "203",
                "config_server_add_dhcp_ip_range_1_input_field": "10.0.0.10",
                "config_server_add_dhcp_ip_range_2_input_field": "10.0.0.20",
                "config_server_add_dhcp_mask_input_field": "24",
                "config_server_add_dhcp_gateway_input_field": "10.0.0.1",
                "config_server_add_dhcp_interface_select_iface_field": interface,
            },
        ):
            response = server.configure()

        payload = response.get_json()
        assert "warning" in payload
        assert "Не указан или неверно указан интерфейс" in payload["warning"]
        assert payload["jobs"] == []
