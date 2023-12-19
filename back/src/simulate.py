import os
import os.path
import random
import string
import time

from ipmininet.ipnet import IPNet
from ipmininet.ipswitch import IPSwitch
from ipmininet.iptopo import IPTopo
from ipmininet.router.config import RouterConfig
from jobs import Jobs
from network import Job, Network, Node, NodeConfig, NodeData, NodeInterface
from pkt_parser import create_pkt_animation, is_ipv4_address


class MyTopology(IPTopo):
    """Class representing topology for miminet networks"""

    def __init__(self, *args, **kwargs):
        self.link_pair = []
        self.switch_count = 0
        self.network: Network = kwargs["network"]
        self._time_to_wait_before_emulation = kwargs["time_to_wait_before_emulation"]
        self._nodes = {}
        self._id_node_map: dict[str, Node] = {}
        super().__init__(*args, **kwargs)

    @property
    def time_to_wait_before_emulation(self) -> int:
        """Get current strategy

        Returns:
            int: time to wait before emulation
        """

        return self._time_to_wait_before_emulation

    @time_to_wait_before_emulation.setter
    def time_to_wait_before_emulation(self, new_time_wait_before_emulation: int):
        """Change the execution strategy

        Args:
            new_time_wait_before_emulation (int): time wait before emulation

        """
        self._time_to_wait_before_emulation = new_time_wait_before_emulation

    def _node_handler(self, node: Node):
        config: NodeConfig = node.config
        data: NodeData = node.data
        node_id = data.id

        match config.type:
            case "l2_switch":
                stp = config.stp
                self._nodes[node_id] = self.addSwitch(node_id, cls=IPSwitch, stp=stp)
                if stp:
                    self.time_to_wait_before_emulation = 33
            case "host" | "server":
                default_gw = config.default_gw
                if default_gw:
                    self._nodes[node_id] = self.addHost(
                        node_id, defaultRoute="via " + str(default_gw)
                    )
                else:
                    self._nodes[node_id] = self.addHost(node_id, defaultRoute="")
            case "l1_hub":
                self._nodes[node_id] = self.addSwitch(
                    node_id, cls=IPSwitch, stp=False, hub=True
                )
            case "router":
                default_gw = config.default_gw

                if default_gw:
                    self._nodes[node_id] = self.addRouter(
                        node_id,
                        use_v6=False,
                        routerDefaultRoute="via " + str(default_gw),
                        config=RouterConfig,
                    )
                else:
                    self._nodes[node_id] = self.addRouter(
                        node_id, use_v6=False, config=RouterConfig
                    )

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
            self._id_node_map[node.data.id] = node
            self._node_handler(node)

        # Add links
        for edge in self.network.edges:
            edge_id = edge.data.id
            edge_source = edge.data.source
            edge_target = edge.data.target

            host_source = self._nodes[edge_source]
            host_target = self._nodes[edge_target]

            if not host_source or not host_target:
                continue

            source_node = self._id_node_map[edge_source]
            (
                interface_name_source,
                interface_name_source_ip,
                interface_name_source_netmask,
            ) = self._find_interface(edge_id, source_node.interface)

            target_node = self._id_node_map[edge_target]
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
                extra_arguments="-v -c 100 -Qout not igmp",
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
        for node in self._id_node_map.values():
            config = node.config
            if config.type == "router":
                net[node.data.id].cmd(f"route add default gw {config.default_gw}")

        for h in net.hosts:
            # print ("disable ipv6 on " + h.name)
            h.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
            h.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
            h.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")
            h.cmd("sysctl -w net.ipv4.tcp_min_tso_segs=1")
            h.cmd("sysctl -w net.ipv4.conf.all.accept_source_route=1")
            h.cmd("sysctl -w net.ipv4.conf.all.log_martians=1")

        # Enable source route
        for r in net.routers:
            r.cmd("sysctl -w net.ipv4.conf.all.accept_source_route=1")
            r.cmd("sysctl -w net.ipv4.conf.all.log_martians=1")

        for sw in net.switches:
            # print ("disable ipv6 on " + sw.name)
            sw.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
            sw.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
            sw.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

        super().post_build(net)


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

    for lp in topo.link_pair:
        link1, link2, edge_id, edge_source, edge_target = lp

        pcap_file1 = "/tmp/capture_" + link1 + ".pcapng"
        pcap_file2 = "/tmp/capture_" + link2 + ".pcapng"

        if not os.path.exists(pcap_file1):
            raise ValueError("No capture for interface: " + link1)

        if not os.path.exists(pcap_file2):
            raise ValueError("No capture for interface: " + link2)

        with open(pcap_file1, "rb") as file1, open(pcap_file2, "rb") as file2:
            pcap_list.append((file1.read(), link1))
            pcap_list.append((file2.read(), link2))

        pkts = create_pkt_animation(
            pcap_file1, pcap_file2, edge_id, edge_source, edge_target
        )

        animation += pkts
        os.remove(pcap_file1)
        os.remove(pcap_file2)

    return animation, pcap_list


def do_job(job: Job, net: IPNet) -> None:
    """Execute job for network

    Args:
        job (Job): current job instance
        net (IPNet): current ipmininet net

    """

    host_id = job.host_id
    job_host = net.get(host_id)
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

    if len(network.jobs) == 0:
        return [], []

    topo = MyTopology(network=network, time_to_wait_before_emulation=2)
    net = IPNet(topo=topo, use_v6=False, autoSetMacs=True, allocate_IPs=False)

    net.start()
    time.sleep(topo.time_to_wait_before_emulation)

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

    time.sleep(2)
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
    os.system("ps -C nc -o pid=|xargs kill -9")

    # Return animation
    return animation, pcap_list
