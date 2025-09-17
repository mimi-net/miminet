import os
import time
from psutil import Process
from ipmininet.ipnet import IPNet
from mininet.log import info
import psutil

from network_topology import MiminetTopology
from network_schema import Network

from net_utils.vlan import setup_vlans, clean_bridges
from net_utils.vxlan import setup_vtep_interfaces, teardown_vtep_bridges

from mininet.net import Mininet
from mininet.node import Host
from mininet.link import Link


class MiminetNetwork(IPNet):
    def __init__(self, topo: MiminetTopology, network: Network):
        super().__init__(topo=topo, use_v6=False, autoSetMacs=True, allocate_IPs=False)
        self.__network_topology = topo
        self.__network_schema = network

    def start(self):
        # Start network
        super().start()

        # Additional settings
        setup_vlans(self, self.__network_schema.nodes)
        setup_vtep_interfaces(self, self.__network_schema.nodes)

        # Waiting for network setup
        time.sleep(self.__network_topology.network_configuration_time)

        self.__check_files()

    def stop(self):
        # Wait before stop
        time.sleep(2)

        clean_bridges(self)
        teardown_vtep_bridges(self, self.__network_schema.nodes)

        self.__clean_services()
        super().stop()

    def __check_files(self):
        """Checking for the existence of pcap files."""
        for link1, link2, *_ in self.__network_topology.interfaces:
            pcap_out_file1 = f"/tmp/capture_{link1}_out.pcapng"
            pcap_out_file2 = f"/tmp/capture_{link2}_out.pcapng"

            if not os.path.exists(pcap_out_file1):
                self.__clear_files()
                raise ValueError(f"No capture for interface '{link1}'.")

            if not os.path.exists(pcap_out_file2):
                self.__clear_files()
                raise ValueError(f"No capture for interface '{link2}'.")

    def __clear_files(self):
        """Remove pcap files."""
        for link1, link2, *_ in self.__network_topology.interfaces:
            files = [
                f"/tmp/capture_{link1}_out.pcapng",
                f"/tmp/capture_{link2}_out.pcapng",
                f"/tmp/capture_{link1}.pcapng",
                f"/tmp/capture_{link2}.pcapng",
            ]
            for f in files:
                if os.path.exists(f):
                    os.remove(f)

    def __clean_services(self):
        """
        Processes running inside virtual devices don't terminate using default mininet functions.

        This function kill them manually.
        """
        info("Starting processes cleanup... ")
        current_process = Process()
        children = current_process.children(recursive=True)
        allowed = ("mimidump", "bash")

        for child in children:
            if child.status() == psutil.STATUS_ZOMBIE:
                # in case we already have zombies
                child.wait()
            elif child.name() not in allowed:
                # finish other processes
                info(f"Killed: {child.name()} {child.pid}")
                child.kill()
                child.wait()


def setup_arp_proxy_on_subinterface(node, sub_intf):
    """Configure ARP Proxying for a given subinterface"""

    # Enable ARP Proxying on the subinterface
    node.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.proxy_arp=1")

    # Enable IP Forwarding to allow packets to be forwarded between interfaces
    node.cmd(f"sysctl -w net.ipv4.ip_forward=1")

    # Enable forwarding on the specific subinterface
    node.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.forwarding=1")

    # Disable ARP filtering to allow proxy ARP to function properly
    node.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.arp_ignore=0")
    node.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.arp_announce=2")

    # Also enable ARP proxying on the parent interface (for bidirectional forwarding)
    parent_iface = sub_intf.split(".")[
        0
    ]  # Extract parent interface (e.g., eth0 from eth0.10)
    node.cmd(f"sysctl -w net.ipv4.conf.{parent_iface}.proxy_arp=1")
    node.cmd(f"sysctl -w net.ipv4.conf.{parent_iface}.forwarding=1")





