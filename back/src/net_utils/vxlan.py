import re

from ipmininet.ipnet import IPNet

from network_schema import Node


def setup_vtep_interfaces(net: IPNet, nodes: list[Node]) -> None:
    """
    Configures VXLAN interfaces on router nodes within the network.

    Args:
        net (IPNet): The network containing all nodes.
        nodes (list[Node]): A list of nodes to configure.
    """
    for node in nodes:
        if node.config.type == "router":
            router = net.get(node.data.id)

            # Configure VXLAN network interfaces (connection_type == 1)
            for iface in node.interface:
                connection_type = iface.vxlan_connection_type
                target_ips = iface.vxlan_vni_to_target_ip

                if target_ips and connection_type == 1:
                    setup_network_interface(router, iface.name, iface.ip, target_ips)

            # Configure VXLAN endpoint interfaces (connection_type == 0)
            for iface in node.interface:
                vni = iface.vxlan_vni
                connection_type = iface.vxlan_connection_type

                if vni is not None and connection_type == 0:
                    setup_endpoint_interface(router, iface.name, vni)


def setup_network_interface(
    router: "Node", intf: str, local_ip: str, target_ips: list[list[str]]
) -> None:
    """
    Sets up a VXLAN network interface on the router.

    Args:
        router (Node): The router node where the interface will be added.
        intf (str): The name of the physical interface.
        local_ip (str): The local IP address for VXLAN.
        target_ips (list[list[str]]): A list containing [vni, target_ip] pairs.
    """
    # Extract unique VNIs from the target IP list
    vxlan_vnis = {elem[0] for elem in target_ips}

    for vni in vxlan_vnis:
        # Generate interface and bridge name

        vxlan_name = re.sub(r"[^a-zA-Z0-9\-_]", "", f"vx{router.name}-{vni}")[-15:]
        bridge_name = re.sub(r"[^a-zA-Z0-9\-_]", "", f"br-{router.name}-{vni}")[-15:]

        vxlan_name = f'"{vxlan_name}"'
        bridge_name = f'"{bridge_name}"'

        # Add VXLAN interface
        router.cmd(
            f"ip link add {vxlan_name} type vxlan id {vni} local {local_ip} "
            f"dstport 4789 dev {intf}"
        )
        router.cmd(f"ip link set {vxlan_name} up")

        # Create and set up bridge
        router.cmd(f"brctl addbr {bridge_name}")
        router.cmd(f"brctl addif {bridge_name} {vxlan_name}")
        router.cmd(f"brctl stp {bridge_name} off")
        router.cmd(f"ip link set {bridge_name} up")
    # Populate forwarding database (FDB) with target MAC addresses and destinations
    for elem in target_ips:
        vni, target_ip = elem
        vxlan_name = re.sub(r"[^a-zA-Z0-9\-_]", "", f"vx{router.name}-{vni}")[-15:]
        vxlan_name = f'"{vxlan_name}"'

        router.cmd(
            f"bridge fdb append 00:00:00:00:00:00 dev {vxlan_name} dst {target_ip}"
        )


def setup_endpoint_interface(router: "Node", intf: str, vni: int) -> None:
    """
    Sets up a VXLAN endpoint interface on the router by attaching it to the bridge.

    Args:
        router (Node): The router node where the endpoint interface will be added.
        intf (str): The name of the physical interface.
        vni (int): The VXLAN Network Identifier.
    """
    bridge_name = re.sub(r"[^a-zA-Z0-9\-_]", "", f"br-{router.name}-{vni}")[-15:]
    bridge_name = f'"{bridge_name}"'

    # Attach physical interface to the bridge and bring it up
    router.cmd(f"brctl addif {bridge_name} {intf}")
    router.cmd(f"ip link set dev {intf} up")


def teardown_vtep_bridges(net: "IPNet", nodes: list["Node"]) -> None:
    """
    Removes all VXLAN bridges and associated interfaces on routers after simulation.

    Args:
        net (IPNet): The network containing all nodes.
        nodes (List[Node]): The list of nodes to be cleaned.
    """
    for node in nodes:
        if node.config.type == "router":
            router = net.get(node.data.id)

            for iface in node.interface:
                connection_type = iface.vxlan_connection_type
                target_ips = iface.vxlan_vni_to_target_ip

                if connection_type == 1 and target_ips:
                    # Retrieve unique VNIs
                    vxlan_vnis = {elem[0] for elem in target_ips}

                    for vni in vxlan_vnis:
                        vxlan_name = re.sub(
                            r"[^a-zA-Z0-9\-_]", "", f"vx{router.name}-{vni}"
                        )[-15:]
                        bridge_name = re.sub(
                            r"[^a-zA-Z0-9\-_]", "", f"br-{router.name}-{vni}"
                        )[-15:]

                        vxlan_name = f'"{vxlan_name}"'
                        bridge_name = f'"{bridge_name}"'

                        router.cmd(f"ip link set {bridge_name} down")
                        router.cmd(f"brctl delbr {bridge_name}")
                        router.cmd(f"ip link set {vxlan_name} down")
                        router.cmd(f"ip link del {vxlan_name}")
