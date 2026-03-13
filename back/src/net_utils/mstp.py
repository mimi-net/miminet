"""MSTP (Multiple Spanning Tree Protocol) configuration utilities."""
import shlex
from ipmininet.ipnet import IPNet  # type: ignore
from ipmininet.ipswitch import IPSwitch  # type: ignore

from src.net_utils.mstp_schema import MstInstance
from src.network_schema import Node, NodeInterface


def _validate_mstp_priority(priority: int, label: str) -> None:
    if not 0 <= priority <= 61440 or priority % 4096 != 0:
        raise ValueError(f"{label} priority must be between 0 and 61440 in steps of 4096 (got {priority}).")


def setup_mstp(net: IPNet, nodes: list[Node]) -> None:
    """Configure MSTP bridges for all L2 switches with MSTP enabled."""
    for node in nodes:
        if node.config.type == "l2_switch" and node.config.stp == 3:
            switch = net.get(node.data.id)
            configure_mstp_bridge(switch, node)


def configure_mstp_bridge(switch: IPSwitch, node: Node) -> None:
    """Configure MSTP on a switch using Linux bridge + mstpd."""
    config = node.config
    bridge_name = f"br-{switch.name}"
    bridge_name_q = shlex.quote(bridge_name)

    if config.priority is not None:
        _validate_mstp_priority(config.priority, "CIST")

    if config.mst_instances:
        for mst_instance in config.mst_instances:
            if mst_instance.priority is not None:
                _validate_mstp_priority(
                    mst_instance.priority, f"MST instance {mst_instance.instance_id}"
                )

    switch.cmd(f"ip link add name {bridge_name_q} type bridge")
    switch.cmd(f"ip link set dev {bridge_name_q} type bridge vlan_filtering 1")
    switch.cmd(f"ip link set dev {bridge_name_q} up")

    for iface in node.interface:
        switch.cmd(f"ip link set {shlex.quote(iface.name)} master {bridge_name_q}")

    result = switch.cmd("which mstpctl 2>/dev/null || echo 'not found'")

    if "not found" in result:
        print(f"Warning: mstpctl not found, using STP fallback for {switch.name}")
        switch.cmd(f"ip link set {bridge_name_q} type bridge stp_state 1")
        if config.priority is not None:
            switch.cmd(f"ip link set {bridge_name_q} type bridge priority {config.priority}")
        return

    switch.cmd(f"mstpctl addbridge {bridge_name_q}")
    switch.cmd(f"mstpctl setforcevers {bridge_name_q} mstp")

    if config.mst_region:
        switch.cmd(f"mstpctl setmstconfid {bridge_name_q} 0 {shlex.quote(config.mst_region)}")

    if config.mst_revision is not None:
        switch.cmd(f"mstpctl setmstconfid {bridge_name_q} 1 {config.mst_revision}")

    if config.priority is not None:
        switch.cmd(f"mstpctl settreeprio {bridge_name_q} 0 {config.priority}")

    if config.mst_instances:
        for mst_instance in config.mst_instances:
            configure_mst_instance(switch, bridge_name, mst_instance)

    for iface in node.interface:
        configure_mstp_interface_vlan(switch, bridge_name, iface)


def configure_mst_instance(
    switch: IPSwitch, bridge_name: str, mst_instance: MstInstance
) -> None:
    """Configure a single MST instance with VLAN mappings."""
    bridge_name_q = shlex.quote(bridge_name)
    instance_id = mst_instance.instance_id
    vlans = mst_instance.vlans
    priority = mst_instance.priority

    switch.cmd(f"mstpctl createtree {bridge_name_q} {instance_id}")

    if priority is not None:
        _validate_mstp_priority(priority, f"MST instance {instance_id}")
        switch.cmd(f"mstpctl settreeprio {bridge_name_q} {instance_id} {priority}")

    fid = instance_id

    for vlan in vlans:
        switch.cmd(f"mstpctl setvid2fid {bridge_name_q} {vlan}:{fid}")

    switch.cmd(f"mstpctl setfid2mstid {bridge_name_q} {fid}:{instance_id}")


def configure_mstp_interface_vlan(
    switch: IPSwitch, bridge_name: str, iface: NodeInterface
) -> None:
    """Configure VLAN settings on an interface for MSTP."""
    if iface.vlan is None:
        return

    iface_name_q = shlex.quote(iface.name)
    switch.cmd(f"bridge vlan del dev {iface_name_q} vid 1 2>/dev/null || true")

    if iface.type_connection == 0:
        vlan = iface.vlan
        switch.cmd(f"bridge vlan add dev {iface_name_q} vid {vlan} pvid untagged")
    elif iface.type_connection == 1:
        vlans = iface.vlan if isinstance(iface.vlan, list) else [iface.vlan]
        for vlan in vlans:
            switch.cmd(f"bridge vlan add dev {iface_name_q} vid {vlan}")
    else:
        vlans = iface.vlan if isinstance(iface.vlan, list) else [iface.vlan]
        for vlan in vlans:
            switch.cmd(f"bridge vlan add dev {iface_name_q} vid {vlan}")


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
            bridge_name_q = shlex.quote(bridge_name)

            switch.cmd(f"mstpctl delbridge {bridge_name_q} 2>/dev/null || true")

            switch.cmd(f"ip link set {bridge_name_q} down 2>/dev/null || true")
            switch.cmd(f"ip link del {bridge_name_q} 2>/dev/null || true")


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

