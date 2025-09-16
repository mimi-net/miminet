def setup_arp_proxy_on_subinterface(node, sub_intf):


    node.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.proxy_arp=1")

    node.cmd("sysctl -w net.ipv4.ip_forward=1")


    node.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.arp_ignore=0")
    node.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.arp_announce=2")


    parent_iface = sub_intf.split(".")[0]
    node.cmd(f"sysctl -w net.ipv4.conf.{parent_iface}.proxy_arp=1")


    node.cmd(f"ip link set {sub_intf} up")

    print(f"[ARP-PROXY] Enabled on {sub_intf} (parent: {parent_iface})")

def configure_vlan_subinterface(node, vlan_id):
    """
    Create a VLAN subinterface and enable ARP proxying on it.
    Does not assign any IP address — purely for ARP Proxy demonstration.
    """
    parent_intf = f"{node.name}-eth1"
    sub_intf = f"{parent_intf}.{vlan_id}"


    node.cmd(f"ip link add link {parent_intf} name {sub_intf} type vlan id {vlan_id}")
    node.cmd(f"ip link set {sub_intf} up")

    setup_arp_proxy_on_subinterface(node, sub_intf)
    
    
    