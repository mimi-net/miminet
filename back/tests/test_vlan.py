"""Unit tests for the VLAN configuration helpers in net_utils.vlan.

Exercise setup_vlans / configure_access / configure_trunk / add_bridge /
clean_bridges against recording fakes so both the OVS (vsctl) and the plain
Linux-bridge (cmd) code paths are covered rootless.
"""

from types import SimpleNamespace
from typing import cast

import pytest
from ipmininet.ipnet import IPNet
from ipmininet.ipswitch import IPSwitch

from network_schema import Node
from node_types import NodeType
from src.net_utils import vlan as V


class Recorder:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def cmd(self, line):
        self.calls.append(("cmd", line))

    def vsctl(self, line):
        self.calls.append(("vsctl", line))


class OVSSwitch(Recorder):
    pass


@pytest.fixture
def ovs_class(monkeypatch):
    monkeypatch.setattr(V, "IPOVSSwitch", OVSSwitch)
    return OVSSwitch


def iface(name, vlan, type_connection):
    return SimpleNamespace(name=name, vlan=vlan, type_connection=type_connection)


def switch_node(switch_id, interfaces):
    return SimpleNamespace(
        config=SimpleNamespace(type=NodeType.SWITCH),
        data=SimpleNamespace(id=switch_id),
        interface=interfaces,
    )


def fake_net(get_switch=None):
    return cast(IPNet, SimpleNamespace(get=get_switch))


def fake_switches(switches):
    return cast(IPNet, SimpleNamespace(switches=switches))


def test_setup_vlans_skips_non_switch(ovs_class):
    def unexpected(_switch_id):
        raise AssertionError("net.get must not be called for non-switch nodes")

    V.setup_vlans(fake_net(unexpected), cast("list[Node]", [host_node()]))


def host_node():
    return SimpleNamespace(config=SimpleNamespace(type=NodeType.HOST))


def test_setup_vlans_access_link_ovs(ovs_class):
    sw = OVSSwitch("sw1")
    net = fake_net(lambda _id: sw)
    V.setup_vlans(net, cast("list[Node]", [switch_node("sw1", [iface("eth0", 10, 0)])]))
    lines = [line for kind, line in sw.calls if kind == "vsctl"]
    assert any("add-br br-sw1" in line for line in lines)
    assert any("del-port" in line and "eth0" in line for line in lines)
    assert any("set port eth0 tag=10" in line for line in lines)


def test_setup_vlans_trunk_link_ovs(ovs_class):
    sw = OVSSwitch("sw1")
    net = fake_net(lambda _id: sw)
    V.setup_vlans(
        net, cast("list[Node]", [switch_node("sw1", [iface("eth0", [20, 30], 1)])])
    )
    lines = [line for kind, line in sw.calls if kind == "vsctl"]
    assert any("set port eth0 trunks=20,30" in line for line in lines)


def test_setup_vlans_ignores_untagged(ovs_class):
    sw = OVSSwitch("sw1")
    net = fake_net(lambda _id: sw)
    V.setup_vlans(
        net, cast("list[Node]", [switch_node("sw1", [iface("eth0", None, 0)])])
    )
    tag_calls = [line for kind, line in sw.calls if kind == "vsctl" and " tag=" in line]
    assert tag_calls == []


def test_configure_access_linux_bridge():
    sw = Recorder("sw1")
    V.configure_access(cast(IPSwitch, sw), "eth0", 10)
    assert ("cmd", "ip link set eth0 master br-sw1") in sw.calls
    assert ("cmd", "bridge vlan del dev eth0 vid 1") in sw.calls
    assert ("cmd", "bridge vlan add dev eth0 vid 10 pvid untagged") in sw.calls


def test_configure_trunk_linux_bridge():
    sw = Recorder("sw1")
    V.configure_trunk(cast(IPSwitch, sw), "eth0", [20, 30])
    assert ("cmd", "ip link set eth0 master br-sw1") in sw.calls
    assert ("cmd", "bridge vlan del dev eth0 vid 1") in sw.calls
    assert ("cmd", "bridge vlan add dev eth0 vid 20") in sw.calls
    assert ("cmd", "bridge vlan add dev eth0 vid 30") in sw.calls


def test_add_bridge_linux_bridge(ovs_class):
    sw = Recorder("sw1")
    V.add_bridge(cast(IPSwitch, sw), [iface("eth0", 10, 0)])
    assert ("cmd", "ip link add name br-sw1 type bridge") in sw.calls
    assert ("cmd", "ip link set dev br-sw1 up") in sw.calls
    assert ("cmd", "ip link set dev br-sw1 type bridge vlan_filtering 1") in sw.calls


def test_add_bridge_ovs_only_with_vlan(ovs_class):
    sw = OVSSwitch("sw1")
    V.add_bridge(cast(IPSwitch, sw), [iface("eth0", 10, 0)])
    lines = [line for kind, line in sw.calls if kind == "vsctl"]
    assert any("add-br br-sw1" in line for line in lines)
    assert any("enable-vlan-filtering=true" in line for line in lines)
    cmds = [line for kind, line in sw.calls if kind == "cmd"]
    assert ("cmd", "ip link set dev br-sw1 up") in sw.calls
    assert any("vlan_filtering 1" in line for line in cmds)


def test_add_bridge_ovs_no_vlan_no_bridge(ovs_class):
    sw = OVSSwitch("sw1")
    V.add_bridge(cast(IPSwitch, sw), [iface("eth0", None, 0)])
    lines = [line for kind, line in sw.calls if kind == "vsctl"]
    assert not any("add-br" in line for line in lines)
    assert ("cmd", "ip link set dev br-sw1 up") in sw.calls


def test_clean_bridges_ovs(ovs_class):
    sw = OVSSwitch("sw1")
    V.clean_bridges(fake_switches([sw]))
    assert ("cmd", "ip link set br-sw1 down") in sw.calls
    assert any("del-br br-sw1" in line for _, line in sw.calls)


def test_clean_bridges_linux(ovs_class):
    sw = Recorder("sw1")
    V.clean_bridges(fake_switches([sw]))
    assert ("cmd", "ip link set br-sw1 down") in sw.calls
    assert ("cmd", "brctl delbr br-sw1") in sw.calls


def test_has_vlan_interfaces():
    assert V.has_vlan_interfaces([iface("a", 10, 0)])
    assert not V.has_vlan_interfaces([iface("a", None, 0)])
    assert not V.has_vlan_interfaces([])
