import logging
import os
import time
from ipmininet.ipnet import IPNet
from mininet.log import info
import psutil
import logging_config
from network_topology import MiminetTopology
from network_schema import Network
from net_utils.vlan import setup_vlans, clean_bridges
from net_utils.vxlan import setup_vtep_interfaces, teardown_vtep_bridges
from psutil import Process

logger = logging.getLogger(__name__)
logging_config.configure_logging(logger)


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
        info("[network.stop] called, sleeping 2s before teardown\n")
        # Wait before stop
        time.sleep(2)

        clean_bridges(self)
        teardown_vtep_bridges(self, self.__network_schema.nodes)

        info("[network.stop] calling __clean_services\n")
        self.__clean_services()
        info(
            "[network.stop] calling super().stop() — this will send SIGINT to mimidump\n"
        )
        super().stop()
        info("[network.stop] done\n")

    def __check_files(self):
        """Checking for the existence of pcap files."""
        for link1, link2, *_ in self.__network_topology.interfaces:
            pcap_out_file1 = f"/tmp/capture_{link1}_out.pcapng"
            pcap_out_file2 = f"/tmp/capture_{link2}_out.pcapng"

            if not os.path.exists(pcap_out_file1):
                self.__clear_files()
                logger.error(
                    "Pcap out file isn't found",
                    extra={
                        "task_id": getattr(self, "task_id", None),
                        "interface": link1,
                        "expected_file": pcap_out_file1,
                    },
                )
                raise ValueError(f"No capture for interface '{link1}'.")

            if not os.path.exists(pcap_out_file2):
                self.__clear_files()
                logger.error(
                    "Pcap file isn't found",
                    extra={
                        "task_id": getattr(self, "task_id", None),
                        "interface": link2,
                        "expected_file": pcap_out_file2,
                    },
                )
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
        killed_count = 0
        zombie_count = 0

        for child in children:
            if child.status() == psutil.STATUS_ZOMBIE:
                # in case we already have zombies
                child.wait()
                zombie_count += 1
            elif child.name() not in allowed:
                # finish other processes
                info(f"Killed: {child.name()} {child.pid}")
                child.kill()
                child.wait()
                killed_count += 1
        if zombie_count > 0 or killed_count > 0:
            logger.warning(
                "Cleanup is incomplete",
                extra={"killed_processes": killed_count, "zombies_left": zombie_count},
            )
