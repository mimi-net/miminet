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

        # Hybrid approach: polling for STP/RSTP, fixed timers for others
        wait_time_or_none = self.__calculate_conservative_wait_time()

        if wait_time_or_none is None:
            # Use intelligent polling for STP/RSTP
            wait_time = self.__wait_for_network_ready()
            info(f"Network ready after {wait_time:.1f}s (polling)\n")
        else:
            # Use fixed timer for non-STP networks
            wait_time = wait_time_or_none
            info(f"Waiting for network convergence ({wait_time:.1f}s)...\n")
            time.sleep(wait_time)

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

    def __calculate_conservative_wait_time(self):
        """Calculate wait time with hybrid approach.

        Hybrid strategy:
        - STP/RSTP: Use intelligent polling (can detect convergence)
        - DHCP/Other: Use fixed timers (cannot reliably detect readiness)

        This gives us the best of both worlds: speed where possible,
        reliability everywhere.

        Returns:
            None if should use polling, float otherwise
        """
        # Check for STP/RSTP
        has_stp = False
        has_rstp = False

        for node in self.__network_schema.nodes:
            if node.config.type == "l2_switch":
                if node.config.stp == 1:
                    has_stp = True
                elif node.config.stp == 2:
                    has_rstp = True

        # For STP/RSTP: use polling (returns actual wait time)
        if has_stp or has_rstp:
            return None  # Signal to use polling

        # For non-STP: use original network_configuration_time (default 3s)
        # This is the baseline time set by MiminetTopology
        return self.__network_topology.network_configuration_time

    def __wait_for_network_ready(self) -> float:
        """Wait for network to be ready using active polling instead of fixed timers.

        This approach actively monitors network readiness:
        - For STP/RSTP networks: check bridge port states
        - Poll every 0.5s with appropriate timeout based on topology

        Returns actual wait time spent.
        """
        import time

        # Determine maximum timeout based on network type
        has_stp = False
        has_rstp = False
        switch_count = 0
        bridge_names = []

        for node in self.__network_schema.nodes:
            if node.config.type == "l2_switch":
                switch_count += 1
                bridge_names.append(node.data.id)
                if node.config.stp == 1:
                    has_stp = True
                elif node.config.stp == 2:
                    has_rstp = True

        # Set timeout based on protocol and topology
        if has_rstp:
            # RSTP is fast by design
            max_timeout = 10
            min_stable_time = 1.5
            final_delay = 3.0  # Conservative safety margin
        elif has_stp:
            # STP can take longer, but we detect early completion
            has_loops = self.__detect_topology_loops()
            if not has_loops:
                max_timeout = 20  # Tree topology
                min_stable_time = 2.0
                final_delay = 6.0
            else:
                max_timeout = 35  # Loop topology needs more time
                min_stable_time = 3.0
                final_delay = 6.0
        else:
            # Fallback - should not reach here
            return self.__network_topology.network_configuration_time

        start_time = time.time()
        stable_since = None
        poll_interval = 0.5

        info(f"Polling for STP/RSTP convergence (max {max_timeout}s)...\n")

        while True:
            elapsed = time.time() - start_time

            if elapsed > max_timeout:
                info(f"Timeout reached ({max_timeout}s), assuming converged\n")
                break

            # Check if network is ready
            if self.__check_stp_ready(bridge_names):
                if stable_since is None:
                    stable_since = time.time()
                    info(
                        f"Network appears ready after {elapsed:.1f}s, waiting {min_stable_time}s for stability...\n"
                    )

                # Check if stable for required duration
                stable_duration = time.time() - stable_since
                if stable_duration >= min_stable_time:
                    convergence_time = time.time() - start_time
                    info(
                        f"Network stable for {stable_duration:.1f}s, applying final delay of {final_delay}s...\n"
                    )
                    time.sleep(final_delay)
                    return convergence_time + final_delay
            else:
                # Reset stability timer if network not ready
                if stable_since is not None:
                    info("Network state changed, resetting stability timer\n")
                stable_since = None

            time.sleep(poll_interval)

        # Timeout reached - apply final delay and return
        time.sleep(final_delay)
        return time.time() - start_time

    def __check_stp_ready(self, bridge_names: list) -> bool:
        """Check if STP/RSTP has converged by examining bridge states.

        Args:
            bridge_names: List of bridge names to check

        Returns:
            True if all bridges appear converged, False otherwise
        """
        import subprocess

        for bridge in bridge_names:
            try:
                # Get bridge STP info
                result = subprocess.run(
                    ["brctl", "showstp", bridge],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                if result.returncode != 0:
                    continue

                output = result.stdout

                # Check for ports in learning or listening state (not converged)
                if (
                    "state listening" in output.lower()
                    or "state learning" in output.lower()
                ):
                    return False

            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return True

    def __detect_topology_loops(self) -> bool:
        """Detect if network topology contains loops using DFS.

        Returns:
            True if loops detected, False for tree topology
        """
        from typing import Dict, List

        # Build adjacency list from network schema
        graph: Dict[str, List[str]] = {}
        for node in self.__network_schema.nodes:
            if node.config.type == "l2_switch":
                graph[node.data.id] = []

        # Add edges from links
        for link in self.__network_schema.links:
            node1 = link.node1_id
            node2 = link.node2_id

            # Only consider switch-to-switch links
            if node1 in graph and node2 in graph:
                graph[node1].append(node2)
                graph[node2].append(node1)

        if not graph:
            return False

        # DFS to detect cycles
        visited = set()
        rec_stack = set()

        def has_cycle(node, parent):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor == parent:  # Skip edge back to parent
                    continue
                if neighbor not in visited:
                    if has_cycle(neighbor, node):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        # Check from any starting node
        start_node = next(iter(graph.keys()))
        return has_cycle(start_node, None)

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
