from ipmininet.ipnet import IPNet
from ipmininet.ipswitch import IPSwitch
from ipmininet.ipovs_switch import IPOVSSwitch

from network_schema import Node, NodeInterface


def setup_vlans(net: IPNet, nodes: list[Node]) -> None:
    """Function to configure VLANs on the presented network

    Args:
        net (IPNet): network
        nodes (list[Node]): nodes on the network

    """

    for node in nodes:
        if node.config.type == "l2_switch":
            switch = net.get(node.data.id)
            add_bridge(switch, node.interface)

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
        if isinstance(switch, IPOVSSwitch):
            switch.vsctl(f' del-br {f"br-{switch.name}"}')
        else:
            switch.cmd(f'brctl delbr {f"br-{switch.name}"}')


def configure_access(switch: IPSwitch, intf: str, vlan: int) -> None:
    if isinstance(switch, IPOVSSwitch):
        switch.vsctl(f" del-port {switch} {intf}")
        switch.vsctl(f' add-port {f"br-{switch.name}"} {intf}')
        switch.vsctl(f" set port {intf} tag={vlan}")
    else:
        switch.cmd(f'ip link set {intf} master {f"br-{switch.name}"}')
        switch.cmd(f"bridge vlan del dev {intf} vid 1")
        switch.cmd(f"bridge vlan add dev {intf} vid {vlan} pvid untagged")


def configure_trunk(switch: IPSwitch, intf: str, vlans: list[int]) -> None:
    if isinstance(switch, IPOVSSwitch):
        switch.vsctl(f" del-port {switch} {intf}")
        switch.vsctl(f' add-port {f"br-{switch.name}"} {intf}')
        switch.vsctl(f" set port {intf} trunks={','.join(map(str, vlans))}")
    else:
        switch.cmd(f'ip link set {intf} master {f"br-{switch.name}"}')
        switch.cmd(f"bridge vlan del dev {intf} vid 1")

        for vlan in vlans:
            switch.cmd(f"bridge vlan add dev {intf} vid {vlan}")


def add_bridge(switch: IPSwitch, interface: list[NodeInterface]) -> None:
    if isinstance(switch, IPOVSSwitch):
        if any(iface.vlan is not None for iface in interface):
            switch.vsctl(f' add-br {f"br-{switch.name}"}')
            switch.vsctl(
                f' set bridge {f"br-{switch.name}"} other_config:enable-vlan-filtering=true'
            )
    else:
        switch.cmd(f'ip link add name {f"br-{switch.name}"} type bridge')
    switch.cmd(f'ip link set dev {f"br-{switch.name}"} up')
    switch.cmd(f'ip link set dev {f"br-{switch.name}"} type bridge vlan_filtering 1')







from typing import Any, Optional

# Assuming these are your switch types
class IPSwitch:
    name: str
    def cmd(self, command: str) -> None:
        ...

class IPOVSSwitch(IPSwitch):
    def vsctl(self, command: str) -> None:
        ...

def configure_access(switch: IPSwitch, intf: str, vlan: int) -> None:
    """Configure a switch port for a VLAN and enable ARP proxying."""

    if isinstance(switch, IPOVSSwitch):
        switch.vsctl(f"del-port {switch} {intf}")
        switch.vsctl(f"add-port br-{switch.name} {intf}")
        switch.vsctl(f"set port {intf} tag={vlan}")
    else:
        switch.cmd(f"ip link set {intf} master br-{switch.name}")
        switch.cmd(f"bridge vlan del dev {intf} vid 1")
        switch.cmd(f"bridge vlan add dev {intf} vid {vlan} pvid untagged")

    # Enable ARP proxy on base interface
    switch.cmd(f"sysctl -w net.ipv4.conf.{intf}.proxy_arp=1")
    switch.cmd(f"sysctl -w net.ipv4.conf.{intf}.forwarding=1")

    # Create and enable sub-interface
    sub_intf = f"{intf}.{vlan}"
    switch.cmd(f"ip link add link {intf} name {sub_intf} type vlan id {vlan}")
    switch.cmd(f"ip link set {sub_intf} up")
    switch.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.proxy_arp=1")
    switch.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.forwarding=1")

    # Enable ARP proxy on the bridge too
    switch.cmd(f"sysctl -w net.ipv4.conf.br-{switch.name}.proxy_arp=1")
    switch.cmd(f"sysctl -w net.ipv4.conf.br-{switch.name}.forwarding=1")



# Optional: second function renamed to avoid mypy redefinition error
def configure_access_vlan(switch: IPSwitch, intf: str, vlan: int, ip: Optional[str] = None, mask: Optional[int] = None) -> None:
    """Optional variant for VLAN subinterface with optional IP assignment."""
    sub_intf = f"{intf}.{vlan}"
    switch.cmd(f"ip link add link {intf} name {sub_intf} type vlan id {vlan}")
    switch.cmd(f"ip link set {sub_intf} up")
    
    if ip is not None and mask is not None:
        switch.cmd(f"ip addr add {ip}/{mask} dev {sub_intf}")

    # Enable ARP proxy on sub-interface
    switch.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.proxy_arp=1")
    switch.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.forwarding=1")
