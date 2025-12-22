from ipmininet.ipnet import IPNet  # type: ignore
from ipmininet.node import IPNode  # type: ignore

from network_schema import MstInstance, Node  # type: ignore


def setup_mstp(net: IPNet, nodes: list[Node]) -> None:
    for node in nodes:
        if node.config.type == "l2_switch" and node.config.stp == 3:
            switch = net.get(node.data.id)
            configure_mstp_bridge(switch, node)


def configure_mstp_bridge(switch: IPNode, node: Node) -> None:
    config = node.config
    bridge_name = f"br-{switch.name}"

    switch.cmd(f"ip link add name {bridge_name} type bridge")
    switch.cmd(f"ip link set dev {bridge_name} up")

    switch.cmd(f"ip link set dev {bridge_name} type bridge vlan_filtering 1")

    for iface in node.interface:
        switch.cmd(f"ip link set {iface.name} master {bridge_name}")


    result = switch.cmd("which mstpctl 2>/dev/null || echo 'not found'")

    if "not found" in result:
        # mstpd not installed - use STP as fallback
        print(
            f"Warning: mstpctl not found, using STP fallback for {switch.name}"
        )
        switch.cmd(f"ip link set {bridge_name} type bridge stp_state 1")

        if config.priority is not None:
            switch.cmd(
                f"ip link set {bridge_name} type bridge priority {config.priority}"
            )
        return

    # Enable MSTP using mstpctl
    switch.cmd(f"mstpctl addbridge {bridge_name}")
    switch.cmd(f"mstpctl setforcevers {bridge_name} mstp")

    # Set MST region configuration
    if config.mst_region:
        switch.cmd(
            f"mstpctl setmstconfid {bridge_name} 0 {config.mst_region}"
        )

    if config.mst_revision is not None:
        switch.cmd(
            f"mstpctl setmstconfid {bridge_name} 1 {config.mst_revision}"
        )

    # Set bridge priority for CIST (instance 0)
    if config.priority is not None:
        prio = min(15, max(0, config.priority))
        switch.cmd(f"mstpctl settreeprio {bridge_name} 0 {prio}")

    # Configure MST instances
    if config.mst_instances:
        for mst_instance in config.mst_instances:
            configure_mst_instance(switch, bridge_name, mst_instance)

    # Configure VLANs on interfaces
    for iface in node.interface:
        configure_mstp_interface_vlan(switch, bridge_name, iface)


def configure_mst_instance(
    switch: IPNode, bridge_name: str, mst_instance: MstInstance
) -> None:
    instance_id = mst_instance.instance_id
    vlans = mst_instance.vlans
    priority = mst_instance.priority

    # Create MST instance
    switch.cmd(f"mstpctl createtree {bridge_name} {instance_id}")

    # Set MST instance priority
    if priority is not None:
        prio = min(15, max(0, priority))
        switch.cmd(
            f"mstpctl settreeprio {bridge_name} {instance_id} {prio}"
        )

    # Use instance_id as FID
    fid = instance_id

    for vlan in vlans:
        switch.cmd(
            f"mstpctl setvid2fid {bridge_name} {vlan}:{fid}"
        )

    switch.cmd(
        f"mstpctl setfid2mstid {bridge_name} {fid}:{instance_id}"
    )


def configure_mstp_interface_vlan(
    switch: IPNode, bridge_name: str, iface
) -> None:
    if iface.vlan is None:
        # Trunk with all VLANs allowed
        return

    # Remove default VLAN 1
    switch.cmd(
        f"bridge vlan del dev {iface.name} vid 1 2>/dev/null || true"
    )

    if iface.type_connection == 0:  # Access port
        vlan = iface.vlan
        switch.cmd(
            f"bridge vlan add dev {iface.name} vid {vlan} pvid untagged"
        )

    elif iface.type_connection == 1:  # Trunk port
        vlans = iface.vlan if isinstance(iface.vlan, list) else [iface.vlan]
        for vlan in vlans:
            switch.cmd(
                f"bridge vlan add dev {iface.name} vid {vlan}"
            )

    else:
        vlans = iface.vlan if isinstance(iface.vlan, list) else [iface.vlan]
        for vlan in vlans:
            switch.cmd(
                f"bridge vlan add dev {iface.name} vid {vlan}"
            )


def clean_mstp_bridges(net: IPNet, nodes: list[Node]) -> None:
    for node in nodes:
        if node.config.type == "l2_switch" and node.config.stp == 3:
            switch = net.get(node.data.id)
            bridge_name = f"br-{switch.name}"

            switch.cmd(
                f"mstpctl delbridge {bridge_name} 2>/dev/null || true"
            )
            switch.cmd(
                f"ip link set {bridge_name} down 2>/dev/null || true"
            )
            switch.cmd(
                f"ip link del {bridge_name} 2>/dev/null || true"
            )


def get_mst_instance_for_vlan(node: Node, vlan_id: int) -> int:
    if node.config.mst_instances:
        for mst_instance in node.config.mst_instances:
            if vlan_id in mst_instance.vlans:
                return mst_instance.instance_id
    return 0  # CIST
