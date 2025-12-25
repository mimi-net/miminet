"""MSTP (Multiple Spanning Tree Protocol) configuration utilities."""

from ipmininet.ipnet import IPNet  # type: ignore
from ipmininet.ipswitch import IPSwitch  # type: ignore

from mstp_schema import MstInstance
from network_schema import Node, NodeInterface


def _validate_mstp_priority(priority: int, label: str) -> None:
    if not 0 <= priority <= 15:
        raise ValueError(f"{label} priority must be between 0 and 15 (got {priority}).")


def setup_mstp(net: IPNet, nodes: list[Node]) -> None:
    """Configure MSTP on switches with stp=3."""
    for node in nodes:
        if node.config.type == "l2_switch" and node.config.stp == 3:
            switch = net.get(node.data.id)
            configure_mstp_bridge(switch, node)


def configure_mstp_bridge(switch: IPSwitch, node: Node) -> None:
    """Configure MSTP on a switch using Linux bridge + mstpd."""
    config = node.config
    bridge_name = f"br-{switch.name}"

    if config.priority is not None:
        _validate_mstp_priority(config.priority, "CIST")

    if config.mst_instances:
        for mst_instance in config.mst_instances:
            if mst_instance.priority is not None:
                _validate_mstp_priority(
                    mst_instance.priority, f"MST instance {mst_instance.instance_id}"
                )

    switch.cmd(f"ip link add name {bridge_name} type bridge")
    switch.cmd(f"ip link set dev {bridge_name} up")
    switch.cmd(f"ip link set dev {bridge_name} type bridge vlan_filtering 1")

    for iface in node.interface:
        switch.cmd(f"ip link set {iface.name} master {bridge_name}")

    result = switch.cmd("which mstpctl 2>/dev/null || echo 'not found'")

    if "not found" in result:
        print(f"Warning: mstpctl not found, using STP fallback for " f"{switch.name}")
        switch.cmd(f"ip link set {bridge_name} type bridge stp_state 1")
        if config.priority is not None:
            switch.cmd(
                f"ip link set {bridge_name} type bridge priority " f"{config.priority}"
            )
        return

    switch.cmd(f"mstpctl addbridge {bridge_name}")
    switch.cmd(f"mstpctl setforcevers {bridge_name} mstp")

    if config.mst_region:
        switch.cmd(f"mstpctl setmstconfid {bridge_name} 0 " f"{config.mst_region}")

    if config.mst_revision is not None:
        switch.cmd(f"mstpctl setmstconfid {bridge_name} 1 " f"{config.mst_revision}")

    if config.priority is not None:
        switch.cmd(f"mstpctl settreeprio {bridge_name} 0 {config.priority}")

    if config.mst_instances:
        for mst_instance in config.mst_instances:
            configure_mst_instance(switch, bridge_name, mst_instance)

    for iface in node.interface:
        configure_mstp_interface_vlan(switch, bridge_name, iface)


def configure_mst_instance(
    switch: IPSwitch, bridge_name: str, mst_instance: MstInstance
) -> None:
    """Configure a single MST instance with VLAN mappings."""
    instance_id = mst_instance.instance_id
    vlans = mst_instance.vlans
    priority = mst_instance.priority

    switch.cmd(f"mstpctl createtree {bridge_name} {instance_id}")

    if priority is not None:
        _validate_mstp_priority(priority, f"MST instance {instance_id}")
        switch.cmd(f"mstpctl settreeprio {bridge_name} {instance_id} " f"{priority}")

    fid = instance_id

    for vlan in vlans:
        switch.cmd(f"mstpctl setvid2fid {bridge_name} {vlan}:{fid}")

    switch.cmd(f"mstpctl setfid2mstid {bridge_name} " f"{fid}:{instance_id}")


def configure_mstp_interface_vlan(
    switch: IPSwitch, bridge_name: str, iface: NodeInterface
) -> None:
    """Configure VLAN settings on an interface for MSTP."""
    if iface.vlan is None:
        return

    switch.cmd(f"bridge vlan del dev {iface.name} vid 1 2>/dev/null || " f"true")

    if iface.type_connection == 0:
        vlan = iface.vlan
        switch.cmd(f"bridge vlan add dev {iface.name} vid {vlan} pvid " f"untagged")
    elif iface.type_connection == 1:
        vlans = iface.vlan if isinstance(iface.vlan, list) else [iface.vlan]
        for vlan in vlans:
            switch.cmd(f"bridge vlan add dev {iface.name} vid {vlan}")
    else:
        vlans = iface.vlan if isinstance(iface.vlan, list) else [iface.vlan]
        for vlan in vlans:
            switch.cmd(f"bridge vlan add dev {iface.name} vid {vlan}")


def clean_mstp_bridges(net: IPNet, nodes: list[Node]) -> None:
    """Clean up MSTP bridges.

    Args:
        net (IPNet): The network instance.
        nodes (list[Node]): List of network nodes.
    """
    for node in nodes:
        if node.config.type == "l2_switch" and node.config.stp == 3:
            switch = net.get(node.data.id)
            bridge_name = f"br-{switch.name}"

            switch.cmd(f"mstpctl delbridge {bridge_name} 2>/dev/null || true")

            switch.cmd(f"ip link set {bridge_name} down 2>/dev/null || true")
            switch.cmd(f"ip link del {bridge_name} 2>/dev/null || true")


def get_mst_instance_for_vlan(node: Node, vlan_id: int) -> int:
    """Get the MST instance ID for a given VLAN.

    Args:
        node (Node): The node configuration.
        vlan_id (int): The VLAN ID to look up.

    Returns:
        int: MST instance ID (0 = CIST if not mapped).
    """
    if node.config.mst_instances:
        for mst_instance in node.config.mst_instances:
            if vlan_id in mst_instance.vlans:
                return mst_instance.instance_id
    return 0  # Default to CIST (Common and Internal Spanning Tree)
