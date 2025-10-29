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

from net_utils.arp_proxy import configure_vlan_subinterface  


from net_utils.arp_proxy import configure_vlan_subinterface  

from mininet.node import Host
from mininet.link import Link
from net_utils.arp_proxy import configure_vlan_subinterface
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

                
        # Enable ARP Proxy for VLAN subinterfaces dynamically
        for host in self.hosts:
            node_info = self.__network_schema.nodes.get(host.name, {})
            vlan_id = node_info.get("vlan_id")
            if vlan_id is not None:
                self.create_vlan_subinterface(host, parent="eth0", vlan_id=vlan_id)
                info(f"Configured VLAN {vlan_id} on host {host.name}\n")


        

        # Enable ARP Proxy for VLAN subinterfaces dynamically
    
        for host in self.hosts:
            node_info = self.__network_schema.nodes.get(host.name, {})
            vlan_id = node_info.get("vlan_id")
            if vlan_id is not None:
                configure_vlan_subinterface(host, vlan_id=vlan_id)
                info(f"Configured VLAN {vlan_id} on host {host.name}\n")

        # Waiting for network setup
        time.sleep(self.__network_topology.network_configuration_time)

        self.__check_files()
    @staticmethod
    def create_vlan_subinterface(host, parent, vlan_id):
        """Create VLAN subinterface and enable ARP proxy."""
        sub_intf = f"{parent}.{vlan_id}"
        host.cmd(f"ip link add link {parent} name {sub_intf} type vlan id {vlan_id}")
        host.cmd(f"ip link set dev {sub_intf} up")
        host.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.proxy_arp=1")
        return sub_intf    

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

        This function kills them manually.
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
                info(f"Killed: {child.name()} {child.pid}\n")
                child.kill()


