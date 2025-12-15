"""
MSTP (Multiple Spanning Tree Protocol) configuration utilities.

MSTP allows mapping multiple VLANs to different spanning tree instances,
providing load balancing and redundancy for VLAN traffic.

For MSTP we use Linux bridge with mstpd instead of OVS,
because OVS doesn't support true MSTP with multiple spanning tree instances.
"""

from ipmininet.ipnet import IPNet  # type: ignore
from network_schema import MstInstance, Node  # type: ignore


def setup_mstp(net: IPNet, nodes: list[Node]) -> None:
    """Configure MSTP on switches that have stp=3.

    For MSTP, we create a Linux bridge with mstpd instead of using OVS,
    because mstpd provides full MSTP support with multiple spanning tree
    instances.

    Args:
        net (IPNet): The network instance.
        nodes (list[Node]): List of network nodes.
    """
    for node in nodes:
        if node.config.type == "l2_switch" and node.config.stp == 3:
            switch = net.get(node.data.id)
            configure_mstp_bridge(switch, node)


def configure_mstp_bridge(switch, node: Node) -> None:
    """Configure MSTP on a switch using Linux bridge + mstpd.

    This creates a Linux bridge with MSTP enabled via mstpd,
    which provides full support for multiple spanning tree instances.

    Args:
        switch: The switch instance.
        node (Node): The node configuration.
    """
    config = node.config
    bridge_name = f"br-{switch.name}"

    # Create Linux bridge for MSTP
    switch.cmd(f"ip link add name {bridge_name} type bridge")
    switch.cmd(f"ip link set dev {bridge_name} up")

    # Enable VLAN filtering on the bridge
    switch.cmd(f"ip link set dev {bridge_name} type bridge vlan_filtering 1")

    # Add all interfaces to the bridge
    for iface in node.interface:
        switch.cmd(f"ip link set {iface.name} master {bridge_name}")

    # Check if mstpd/mstpctl is available
    result = switch.cmd("which mstpctl 2>/dev/null || echo 'not found'")

    if "not found" in result:
        # mstpd not installed - use STP as fallback
        print(f"Warning: mstpctl not found, using STP fallback for "
              f"{switch.name}")
        switch.cmd(f"ip link set {bridge_name} type bridge stp_state 1")
        if config.priority is not None:
            # Set bridge priority (0-65535, default 32768)
            switch.cmd(f"ip link set {bridge_name} type bridge priority "
                       f"{config.priority}")
        return

    # Enable MSTP using mstpctl
    switch.cmd(f"mstpctl addbridge {bridge_name}")
    switch.cmd(f"mstpctl setforcevers {bridge_name} mstp")

    # Set MST region configuration
    # setmstconfid <bridge> 0 <region_name> - sets region name
    # setmstconfid <bridge> 1 <revision> - sets revision number
    if config.mst_region:
        switch.cmd(f"mstpctl setmstconfid {bridge_name} 0 "
                   f"{config.mst_region}")

    if config.mst_revision is not None:
        switch.cmd(f"mstpctl setmstconfid {bridge_name} 1 "
                   f"{config.mst_revision}")

    # Set bridge priority for CIST (instance 0)
    # Priority uses 0-15 scale (0 = highest priority, becomes root)
    if config.priority is not None:
        # Convert to 0-15 scale if needed
        prio = min(15, max(0, config.priority))
        switch.cmd(f"mstpctl settreeprio {bridge_name} 0 {prio}")

    # Configure MST instances with VLAN mappings
    if config.mst_instances:
        for mst_instance in config.mst_instances:
            configure_mst_instance(switch, bridge_name, mst_instance)

    # Configure VLAN on interfaces
    for iface in node.interface:
        configure_mstp_interface_vlan(switch, bridge_name, iface)


def configure_mst_instance(switch, bridge_name: str,
                           mst_instance: MstInstance) -> None:
    """Configure a single MST instance with VLAN mappings.

    MSTP VLAN mapping uses two-step process:
    1. setvid2fid: Map VLAN ID to FID (Filtering Database ID)
    2. setfid2mstid: Map FID to MST Instance ID

    Priority uses 0-15 scale (not 0-65535 like STP).

    Args:
        switch: The switch instance.
        bridge_name (str): Name of the bridge.
        mst_instance (MstInstance): MST instance configuration.
    """
    instance_id = mst_instance.instance_id
    vlans = mst_instance.vlans
    priority = mst_instance.priority

    # Create MST instance first (required before mapping VLANs)
    switch.cmd(f"mstpctl createtree {bridge_name} {instance_id}")

    # Set priority for this MST instance (0-15 scale)
    if priority is not None:
        # Ensure priority is in valid range 0-15
        prio = min(15, max(0, priority))
        switch.cmd(f"mstpctl settreeprio {bridge_name} {instance_id} "
                   f"{prio}")

    # Map VLANs to this MST instance using FID (Filtering ID)
    # Use a single FID per MST instance for simplicity
    fid = instance_id  # Use instance_id as FID

    for vlan in vlans:
        # Map VLAN to FID
        switch.cmd(f"mstpctl setvid2fid {bridge_name} {vlan}:{fid}")

    # Map FID to MST instance (one mapping per FID)
    switch.cmd(f"mstpctl setfid2mstid {bridge_name} "
               f"{fid}:{instance_id}")


def configure_mstp_interface_vlan(switch, bridge_name: str, iface) -> None:
    """Configure VLAN settings on an interface for MSTP.

    Args:
        switch: The switch instance.
        bridge_name (str): Name of the bridge.
        iface: The interface configuration.
    """
    if iface.vlan is None:
        # For inter-switch links without VLAN config, allow all VLANs
        # (trunk mode)
        # Keep default VLAN 1 for basic connectivity
        return

    # Remove default VLAN 1 only if specific VLANs are configured
    switch.cmd(f"bridge vlan del dev {iface.name} vid 1 2>/dev/null || "
               f"true")

    if iface.type_connection == 0:  # Access port
        vlan = iface.vlan
        switch.cmd(f"bridge vlan add dev {iface.name} vid {vlan} pvid "
                   f"untagged")
    elif iface.type_connection == 1:  # Trunk port
        vlans = iface.vlan if isinstance(iface.vlan, list) else [iface.vlan]
        for vlan in vlans:
            switch.cmd(f"bridge vlan add dev {iface.name} vid {vlan}")
    else:
        # Default: allow configured VLANs as tagged
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

            # Remove from mstpd if available
            switch.cmd(f"mstpctl delbridge {bridge_name} 2>/dev/null || true")

            # Delete the bridge
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
