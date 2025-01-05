from ipmininet.ipnet import IPNet
from ipmininet.ipswitch import IPSwitch

from network import Node


def setup_vlans(net: IPNet, nodes: list[Node]) -> None:
    """Function to configure VLANs on the presented network

    Args:
        net (IPNet): network
        nodes (list[Node]): nodes on the network

    """

    for node in nodes:
        if node.config.type == "l2_switch":
            switch = net.get(node.data.id)
            add_bridge(switch)

            for iface in node.interface:
                vlan = iface.vlan
                type_connection = iface.type_connection
                if vlan is not None:
                    if type_connection == 0:  # Access link
                        configure_access(switch, iface.name, vlan)
                    elif type_connection == 1:  # Trunk link
                        configure_trunk(switch, iface.name, sorted(vlan))


def clean_bridges(net: IPNet) -> None:
    """Function to clear bridges that were supplied during VLAN configuration

    Args:
        net (IPNet): network

    """

    for switch in net.switches:
        switch.cmd(f'ip link set {f"br-{switch.name}"} down')
        switch.cmd(f'brctl delbr {f"br-{switch.name}"}')


def configure_access(switch: IPSwitch, intf: str, vlan: int) -> None:
    switch.cmd(f'ip link set {intf} master {f"br-{switch.name}"}')
    switch.cmd(f"bridge vlan del dev {intf} vid 1")
    switch.cmd(f"bridge vlan add dev {intf} vid {vlan} pvid untagged")


def configure_trunk(switch: IPSwitch, intf: str, vlans: list[int]) -> None:
    switch.cmd(f'ip link set {intf} master {f"br-{switch.name}"}')
    switch.cmd(f"bridge vlan del dev {intf} vid 1")

    for vlan in vlans:
        switch.cmd(f"bridge vlan add dev {intf} vid {vlan}")


def add_bridge(switch: IPSwitch) -> None:
    switch.cmd(f'ip link add name {f"br-{switch.name}"} type bridge')
    switch.cmd(f'ip link set dev {f"br-{switch.name}"} up')
    switch.cmd(f'ip link set dev {f"br-{switch.name}"} type bridge vlan_filtering 1')
