from typing import List

from ipmininet.ipnet import IPNet
from ipmininet.ipswitch import IPSwitch
from ipmininet.ipovs_switch import IPOVSSwitch
from ipmininet.iptopo import IPTopo
from ipmininet.router.config import RouterConfig
from network_schema import Network, Node, NodeConfig, NodeInterface
from pkt_parser import is_ipv4_address


class MiminetTopology(IPTopo):
    """Class representing topology for miminet networks."""

    def __init__(self, network: Network):
        # List with useful information about every interface
        self.__iface_pairs: list = []
        # Used to generate unique names
        self.__switch_count = 0
        # Minimum suitable time for which the network is configured
        self.__network_configuration_time = 3

        self.__network: Network = network
        self.__nodes: dict = {}
        self.__id_to_node: dict[str, Node] = {}

        super().__init__()

    @property
    def interfaces(self) -> List:
        """Available interfaces in the topology.

        Return: List with useful information about every interface."""
        return self.__iface_pairs.copy()

    @property
    def network_configuration_time(self) -> int:
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

    def __find_interface(
        self, edge_id: str, node_interfaces: list[NodeInterface]
    ) -> NodeInterface:
        # Search for matching interface among all node interfaces
        matches = [iface for iface in node_interfaces if iface.connect == edge_id]

        if len(matches) == 1:
            return matches[0]

        elif len(matches) == 0:
            raise ValueError(f"Can't find {edge_id} in node interfaces.")

        else:
            raise ValueError(
                f"Found {len(matches)} matching interfaces in node (expected 1)."
            )

    def __configure_link(self, link, iface: NodeInterface):
        """Configure IP settings for an link if valid."""
        ip, mask = iface.ip, iface.netmask

        if is_ipv4_address(ip) and 0 < int(mask) <= 32:
            link.addParams(ip=f"{ip}/{mask}")

    def build(self, *args, **kwargs):
        links = []
        interfaces = []

        for node in self.__network.nodes:
            # Caches node by ID for quick lookup later
            self.__id_to_node[node.data.id] = node

            self.__handle_node(node)

        # Add links
        for edge in self.__network.edges:
            edge_id = edge.data.id
            source_id = edge.data.source
            target_id = edge.data.target

            if source_id not in self.__nodes:
                raise ValueError(
                    f"Edge '{edge_id}' references unknown source node '{source_id}'."
                )
            if target_id not in self.__nodes:
                raise ValueError(
                    f"Edge '{edge_id}' references unknown target node '{target_id}'."
                )

            # Mininet host objects (https://mininet.org/api/classmininet_1_1node_1_1Host.html)
            src_host = self.__nodes[source_id]
            trg_host = self.__nodes[target_id]

            # Mininet full node definitions
            src_node = self.__id_to_node[source_id]
            trg_node = self.__id_to_node[target_id]

            src_iface = self.__find_interface(edge_id, src_node.interface)
            trg_iface = self.__find_interface(edge_id, trg_node.interface)

            self.__iface_pairs.append(
                (src_iface.name, trg_iface.name, edge_id, source_id, target_id)
            )

            # Put virtual switch between nodes and return link between them
            link1, link2 = self.addLink(
                src_host,
                trg_host,
                interface_name_1=src_iface.name,
                interface_name_2=trg_iface.name,
                delay="15ms",
            )

            self.__configure_link(link1[src_host], src_iface)
            self.__configure_link(link2[trg_host], trg_iface)

            links.append(link1[src_host])
            links.append(link2[trg_host])

            interfaces.append(src_iface.name)
            interfaces.append(trg_iface.name)

        if links:
            # Set up packet capturing
            self.addNetworkCapture(
                nodes=[],
                interfaces=[*links],
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
        """Connects two hosts through a virtual switch."""
        # Create unique switch name
        self.__switch_count += 1
        switch_name = "mimiswsw%d" % self.__switch_count

        self.addSwitch(switch_name, cls=IPSwitch, stp=False, hub=True)

        # Link options for (src host <-> switch <-> dst host) connections
        link_opts_src = {
            "params2": {
                "delay": delay,
                "max_queue_size": max_queue_size,
            }
        }

        link_opts_dst = {
            "params1": {
                "delay": delay,
                "max_queue_size": max_queue_size,
            }
        }

        # Create links
        link1 = super().addLink(
            h_source, switch_name, intfName1=interface_name_1, **link_opts_src
        )
        link2 = super().addLink(
            switch_name, h_target, intfName2=interface_name_2, **link_opts_dst
        )

        return link1, link2

    def post_build(self, net: IPNet):
        for node in self.__id_to_node.values():
            config = node.config
            if config.type == "router":
                net[node.data.id].cmd(f"route add default gw {config.default_gw}")

        for h in net.hosts:
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
            sw.cmd("sysctl -w net.bridge.bridge-nf-call-arptables=0")
            sw.cmd("sysctl -w net.bridge.bridge-nf-call-iptables=0")
            sw.cmd("sysctl -w net.bridge.bridge-nf-call-ip6tables=0")
            sw.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
            sw.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
            sw.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

        super().post_build(net)
