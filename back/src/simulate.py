import os
import os.path
import random
import string
import time
import subprocess

from ipmininet.ipnet import IPNet
from ipmininet.ipswitch import IPSwitch
from ipmininet.ipovs_switch import IPOVSSwitch
from ipmininet.iptopo import IPTopo
from ipmininet.router.config import RouterConfig
from jobs import Jobs
from network import Job, Network, Node, NodeConfig, NodeInterface
from pkt_parser import create_pkt_animation, is_ipv4_address
from net_utils.vlan import setup_vlans, clean_bridges
from net_utils.vxlan import setup_vtep_interfaces, teardown_vtep_bridges
from mininet.log import setLogLevel, info


class MyTopology(IPTopo):
    """Class representing topology for miminet networks"""

    def __init__(self, *args, **kwargs):
        self.link_pair = []
        self.switch_count = 0
        self.network: Network = kwargs["network"]
        # Minimum suitable time for which the network is configured
        self.__network_configuration_time = 3
        self.__nodes = {}
        self.__id_to_node: dict[str, Node] = {}
        super().__init__(*args, **kwargs)

    def get_network_configuration_time(self) -> int:
        """Get amount of time it takes to properly configure the network (in seconds)."""
        return self.__network_configuration_time

    def __set_network_configuration_time(self, value: int):
        """Set amount of time it takes to properly configure the network (in seconds)."""
        return max(value, self.__network_configuration_time)

    def __handle_node(self, node: Node):
        config: NodeConfig = node.config
        node_type: str = config.type  # network device type
        node_id: str = node.data.id  # network device name(label)

        if node_type == "l2_switch":
            self.__handle_l2_switch(node_id, config)
        elif node_type in ("host", "server"):
            self.__handle_host_or_server(node_id, config)
        elif node_type == "l1_hub":
            self.__handle_l1_hub(node_id)
        elif node_type == "router":
            self.__handle_router(node_id, config)

    def __handle_l2_switch(self, node_id: str, config: NodeConfig):
        assert config.stp in (0, 1, 2), "Incorrect STP mode"
        is_stp_enabled = config.stp == 1  # Check switch mode
        is_rstp_enabled = config.stp == 2

        self.__nodes[node_id] = self.addSwitch(
            node_id,
            cls=IPOVSSwitch,
            stp=is_stp_enabled,
            rstp=is_rstp_enabled,
            cwd="/tmp",
            priority=config.priority,
        )

        # Set emulation delay based on STP mode
        if is_rstp_enabled:
            self.__set_network_configuration_time(5)
        elif is_stp_enabled:
            self.__set_network_configuration_time(33)

    def __handle_host_or_server(self, node_id: str, config: NodeConfig):
        default_gw = config.default_gw
        route = f"via {default_gw}" if default_gw else ""
        self.__nodes[node_id] = self.addHost(node_id, defaultRoute=route)

    def __handle_l1_hub(self, node_id: str):
        self.__nodes[node_id] = self.addSwitch(
            node_id, cls=IPSwitch, stp=False, hub=True
        )

    def __handle_router(self, node_id: str, config: NodeConfig):
        default_gw = config.default_gw
        kwargs = {
            "use_v6": False,
            "config": RouterConfig,
        }

        if default_gw:
            kwargs["routerDefaultRoute"] = f"via {default_gw}"

        self.__nodes[node_id] = self.addRouter(node_id, **kwargs)

    @staticmethod
    def _find_interface(edge_id, interfaces: list[NodeInterface]):
        for interface in interfaces:
            if edge_id == interface.connect:
                return interface.name, interface.ip, interface.netmask

    def build(self, *args, **kwargs):
        interfaces = []
        ifs = []

        # Add hosts and switches
        for node in self.network.nodes:
            self.__id_to_node[node.data.id] = node
            self.__handle_node(node)

        # Add links
        for edge in self.network.edges:
            edge_id = edge.data.id
            edge_source = edge.data.source
            edge_target = edge.data.target

            host_source = self.__nodes[edge_source]
            host_target = self.__nodes[edge_target]

            if not host_source or not host_target:
                continue

            source_node = self.__id_to_node[edge_source]
            (
                interface_name_source,
                interface_name_source_ip,
                interface_name_source_netmask,
            ) = self._find_interface(edge_id, source_node.interface)

            target_node = self.__id_to_node[edge_target]
            (
                interface_name_target,
                interface_name_target_ip,
                interface_name_target_netmask,
            ) = self._find_interface(edge_id, target_node.interface)

            if not interface_name_source or not interface_name_target:
                continue

            self.link_pair.append(
                (
                    interface_name_source,
                    interface_name_target,
                    edge_id,
                    edge_source,
                    edge_target,
                )
            )

            l1, l2 = self.addLink(
                host_source,
                host_target,
                interface_name_1=interface_name_source,
                interface_name_2=interface_name_target,
                delay="15ms",
            )

            if (
                is_ipv4_address(interface_name_source_ip)
                and 0 < int(interface_name_source_netmask) <= 32
            ):
                l1[host_source].addParams(
                    ip=(
                        str(interface_name_source_ip)
                        + "/"
                        + str(interface_name_source_netmask)
                    )
                )

            if (
                is_ipv4_address(interface_name_target_ip)
                and 0 < interface_name_target_netmask <= 32
            ):
                l2[host_target].addParams(
                    ip=(
                        str(interface_name_target_ip)
                        + "/"
                        + str(interface_name_target_netmask)
                    )
                )

            interfaces.append(l1[host_source])
            interfaces.append(l2[host_target])

            ifs.append(interface_name_source)
            ifs.append(interface_name_target)

        if interfaces:
            self.addNetworkCapture(
                nodes=[],
                interfaces=[*interfaces],
                base_filename="capture",
                extra_arguments="not igmp",
            )
        super().build(*args, **kwargs)

    def addLink(
        self,
        h_source,
        h_target,
        interface_name_1,
        interface_name_2,
        delay="2ms",
        max_queue_size=None,
    ):
        self.switch_count += 1
        s = "mimiswsw%d" % self.switch_count
        self.addSwitch(s, cls=IPSwitch, stp=False, hub=True)

        opts1 = dict()
        opts2 = dict()

        # switch -> node1
        opts1["params2"] = {"delay": delay, "max_queue_size": max_queue_size}
        # switch -> node2
        opts2["params1"] = {"delay": delay, "max_queue_size": max_queue_size}

        return super().addLink(
            h_source, s, intfName1=interface_name_1, **opts1
        ), super().addLink(s, h_target, intfName2=interface_name_2, **opts2)

    def post_build(self, net: IPNet):
        for node in self.__id_to_node.values():
            config = node.config
            if config.type == "router":
                net[node.data.id].cmd(f"route add default gw {config.default_gw}")

        for h in net.hosts:
            # print ("disable ipv6 on " + h.name)
            h.cmd("sysctl -w net.bridge.bridge-nf-call-arptables=0")
            h.cmd("sysctl -w net.bridge.bridge-nf-call-iptables=0")
            h.cmd("sysctl -w net.bridge.bridge-nf-call-ip6tables=0")
            h.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
            h.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
            h.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")
            h.cmd("sysctl -w net.ipv4.tcp_min_tso_segs=1")
            h.cmd("sysctl -w net.ipv4.conf.all.accept_source_route=1")
            h.cmd("sysctl -w net.ipv4.conf.all.log_martians=1")

        # Enable source route
        for r in net.routers:
            r.cmd("sysctl -w net.bridge.bridge-nf-call-arptables=0")
            r.cmd("sysctl -w net.bridge.bridge-nf-call-iptables=0")
            r.cmd("sysctl -w net.bridge.bridge-nf-call-ip6tables=0")
            r.cmd("sysctl -w net.ipv4.conf.all.accept_source_route=1")
            r.cmd("sysctl -w net.ipv4.conf.all.log_martians=1")
            r.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
            r.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")

        for sw in net.switches:
            # print ("disable ipv6 on " + sw.name)
            sw.cmd("sysctl -w net.bridge.bridge-nf-call-arptables=0")
            sw.cmd("sysctl -w net.bridge.bridge-nf-call-iptables=0")
            sw.cmd("sysctl -w net.bridge.bridge-nf-call-ip6tables=0")
            sw.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
            sw.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
            sw.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

        super().post_build(net)

    def clear_files(self):
        for lp in self.link_pair:
            link1, link2, _, _, _ = lp

            pcap_out_file1 = "/tmp/capture_" + link1 + "_out.pcapng"
            pcap_out_file2 = "/tmp/capture_" + link2 + "_out.pcapng"
            pcap_file1 = "/tmp/capture_" + link1 + ".pcapng"
            pcap_file2 = "/tmp/capture_" + link2 + ".pcapng"

            for filename in (pcap_out_file1, pcap_out_file2, pcap_file1, pcap_file2):
                if os.path.exists(filename):
                    os.remove(filename)

    def check(self):
        for lp in self.link_pair:
            link1, link2, _, _, _ = lp

            pcap_out_file1 = "/tmp/capture_" + link1 + "_out.pcapng"
            pcap_out_file2 = "/tmp/capture_" + link2 + "_out.pcapng"

            if not os.path.exists(pcap_out_file1):
                self.clear_files()
                raise ValueError("No capture for interface: " + link1)

            if not os.path.exists(pcap_out_file2):
                self.clear_files()
                raise ValueError("No capture for interface: " + link2)


def packet_uuid(size=8, chars: str = string.ascii_uppercase + string.digits) -> str:
    """Function for generate packet uid

    Args:
        size (int): uid size
        chars (str): available symbols

    Returns:
        str: packer uid

    """

    uid = "".join(random.choice(chars) for _ in range(size))
    return "pkt_" + uid


def create_animation(
    topo: MyTopology,
) -> tuple[list[list] | list, list | list[tuple[bytes, str]]]:
    """Functions for create animations

    Args:
        topo (MyTopology): topo for creating animation

    Returns:
        tuple: animation list and pcap, pcap_name list

    """

    pcap_list = []
    animation = []

    for link1, link2, edge_id, edge_source, edge_target in topo.link_pair:
        pcap_out_file1 = "/tmp/capture_" + link1 + "_out.pcapng"
        pcap_out_file2 = "/tmp/capture_" + link2 + "_out.pcapng"

        pcap_file1 = "/tmp/capture_" + link1 + ".pcapng"
        pcap_file2 = "/tmp/capture_" + link2 + ".pcapng"

        if not os.path.exists(pcap_out_file1):
            raise ValueError("No capture for interface: " + link1)

        if not os.path.exists(pcap_out_file2):
            raise ValueError("No capture for interface: " + link2)

        with open(pcap_file1, "rb") as file1, open(pcap_file2, "rb") as file2:
            pcap_list.append((file1.read(), link1))
            pcap_list.append((file2.read(), link2))

        pkts = create_pkt_animation(
            pcap_out_file1, pcap_out_file2, edge_id, edge_source, edge_target
        )

        animation += pkts

    topo.clear_files()

    return animation, pcap_list


def do_job(job: Job, net: IPNet) -> None:
    """Execute job for network

    Args:
        job (Job): current job instance
        net (IPNet): current ipmininet net

    """

    host_id = job.host_id
    # get host from network by it's ID
    job_host = net.get(host_id)
    # initialize new Job by host and job type
    current_job = Jobs(job, job_host)
    current_job.handler()


def run_mininet(
    network: Network,
) -> tuple[list[list] | list, list | list[tuple[bytes, str]]]:
    """Function for start mininet emulation

    Args:
        network (str): Network for emulation

    Returns:
        tuple: animation list and pcap, pcap_name list
    """

    setLogLevel("info")

    if len(network.jobs) == 0:
        return [], []

    try:
        topo = MyTopology(network=network)
        net = IPNet(topo=topo, use_v6=False, autoSetMacs=True, allocate_IPs=False)

        net.start()

        setup_vlans(net, network.nodes)
        setup_vtep_interfaces(net, network.nodes)
        time.sleep(topo.get_network_configuration_time())
        topo.check()

        # Don only 100+ jobs
        for job in network.jobs:
            job_id = job.job_id

            if int(job_id) < 100:
                continue

            try:
                do_job(job, net)
            except Exception:
                continue

        # Do only job_id < 100
        for job in network.jobs:
            job_id = job.job_id

            if int(job_id) >= 100:
                continue

            try:
                do_job(job, net)
            except Exception:
                continue
    except Exception as e:
        print("An error occurred during mininet configuration:", str(e))
        subprocess.call("mn -c", shell=True)

        raise e

    time.sleep(2)

    import psutil

    info("Processes: ")
    current_process = psutil.Process()
    children = current_process.children(recursive=True)

    for child in children:
        info(child.name() + " " + str(child.pid))

        if not (child.name() in ["mimidump", "bash"]):
            child.kill()
            child.wait()

    clean_bridges(net)
    teardown_vtep_bridges(net, network.nodes)

    net.stop()

    animation, pcap_list = create_animation(topo)
    animation_s = sorted(animation, key=lambda k: k.get("timestamp", 0))

    if animation_s:
        animation = []
        animation_m = []
        first_packet = None
        limit = 0

        # Magic constant.
        # Number of microseconds * 100000
        # Depends on 'opts1["params2"] = {"delay": delay' in addLink function
        pkt_speed = 14000

        for pkt in animation_s:
            if not first_packet:
                first_packet = pkt
                animation_m = [pkt]
                limit = int(first_packet["timestamp"]) + pkt_speed
                continue

            if int(pkt["timestamp"]) > limit:
                animation.append(animation_m)
                first_packet = pkt
                animation_m = [pkt]
                limit = int(first_packet["timestamp"]) + pkt_speed
                continue

            animation_m.append(pkt)

        # Append last packet
        animation.append(animation_m)

    # Waitng for shuting down switches and hosts
    time.sleep(2)

    # Shut down running services
    # os.system("ps -C nc -o pid=|xargs kill -9")

    # Return animation
    return animation, pcap_list
