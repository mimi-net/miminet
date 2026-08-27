import os
import time

import psutil
from ipmininet.ipnet import IPNet
from mininet.log import info
from net_utils.captures import capture_paths, iter_capture_out_files
from net_utils.vlan import clean_bridges, has_vlan_interfaces, setup_vlans
from net_utils.vxlan import (
    iter_vtep_network_interfaces,
    setup_vtep_interfaces,
    teardown_vtep_bridges,
)
from network_schema import Network
from network_topology import MiminetTopology, stp_enabled
from node_types import NodeType
from psutil import Process


class MiminetNetwork(IPNet):
    def __init__(self, topo: MiminetTopology, network: Network):
        super().__init__(topo=topo, use_v6=False, autoSetMacs=True, allocate_IPs=False)
        self.__network_topology = topo
        self.__network_schema = network
        # Last observed (port, role, state) snapshot per STP/RSTP switch, used
        # to detect that the spanning-tree state machine has actually settled.
        self.__stp_snapshots: dict = {}
        # Diagnostic: last raw rstp/stp show output per switch (see __stp_settled).
        self.__stp_diag: dict = {}

    def start(self):
        # Start network
        super().start()

        # Additional settings
        setup_vlans(self, self.__network_schema.nodes)
        setup_vtep_interfaces(self, self.__network_schema.nodes)

        # Wait until the network is actually usable, instead of a fixed sleep:
        # capture files exist, STP/RSTP switches have converged, and the VXLAN
        # underlay is reachable. This makes correctness independent of
        # network_configuration_time (even 0).
        self.__wait_until_ready()

        self.__check_files()

    def __wait_until_ready(self, timeout: float = 90.0, poll: float = 0.5) -> None:
        """Poll until the emulation environment is really ready.

        Deterministic conditions (no fixed sleeps):
          1. Every interface capture file exists (mimidump has started).
          2. STP/RSTP switches report all ports in the forwarding state.
          3. Every VXLAN underlay endpoint is reachable from its local router.

        Raises a descriptive error if the conditions are not met within
        ``timeout`` seconds.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            missing_captures = self.__missing_capture_files()
            unconverged = self.__unconverged_switches()
            unreachable = self.__unreachable_vtep_targets()
            if not missing_captures and not unconverged and not unreachable:
                return
            info(
                "[network] waiting for readiness: captures_missing=%s "
                "stp_unconverged=%s vtep_unreachable=%s\n"
                % (missing_captures, unconverged, unreachable)
            )
            time.sleep(poll)

        details = []
        if self.__missing_capture_files():
            details.append("capture files missing")
        if self.__unconverged_switches():
            details.append("STP/RSTP switches not forwarding")
        if self.__unreachable_vtep_targets():
            details.append("VXLAN underlay unreachable")
        raise TimeoutError(
            "Network did not become ready within %ss: %s"
            % (timeout, ", ".join(details))
        )

    def __missing_capture_files(self) -> list:
        return [
            path
            for _, path in iter_capture_out_files(self.__network_topology.interfaces)
            if not os.path.exists(path)
        ]

    def __unconverged_switches(self) -> list:
        """Return switches whose STP/RSTP state machine has not settled yet."""
        unconverged = []
        for node in self.__network_schema.nodes:
            if node.config.type != NodeType.SWITCH or not stp_enabled(node.config):
                continue
            # In VLAN mode the data ports are moved to the br-{name} bridge,
            # which has no STP/RSTP enabled — there is nothing to converge
            # there, and the base bridge only carries the LOCAL port.
            if has_vlan_interfaces(node.interface):
                continue
            switch = self[node.data.id]
            if not self.__stp_settled(switch):
                unconverged.append(switch.name)
        return unconverged

    def __stp_settled(self, switch) -> bool:
        """Return True once the switch's spanning-tree state has converged.

        Uses the authoritative ``ovs-appctl rstp/stp show`` output. A bridge is
        considered ready when, on two consecutive polls, every port has a
        settled (role, state) pair: at least one port is forwarding, nothing is
        still listening/learning, and the only discarding ports are the
        Alternate/Backup ones (a discarding Designated/Root port means the
        state machine is still converging).

        If the state cannot be determined at all (command error, or the
        daemon has no object for the bridge), the switch is treated as ready —
        the emulation retries on meaningless results anyway, so an anomaly
        must not hard-block the whole run.
        """
        protocol = "rstp" if getattr(switch, "rstp", False) else "stp"
        try:
            out = switch.cmd("ovs-appctl %s/show %s" % (protocol, switch))
        except Exception as e:
            self.__stp_diag[switch.name] = "cmd error: %r" % e
            return True  # cannot determine -> do not block
        self.__stp_diag[switch.name] = out
        if "no such" in out.lower() or "server returned an error" in out.lower():
            return True  # daemon anomaly -> do not block

        ports = []
        for line in out.splitlines():
            parts = line.split()
            # "name  Role  State  Cost  Pri.Nbr" — e.g. "l2sw1_3 Designated Discarding 2000 128.1"
            if len(parts) == 5 and parts[1] in (
                "Root",
                "Designated",
                "Alternate",
                "Backup",
                "Disabled",
            ):
                ports.append((parts[0], parts[1], parts[2]))

        if not ports or not any(state == "Forwarding" for _, _, state in ports):
            self.__stp_snapshots.pop(switch.name, None)
            return False
        if any(state in ("Learning", "Listening") for _, _, state in ports):
            self.__stp_snapshots.pop(switch.name, None)
            return False
        # Discarding is only allowed on the blocked Alternate/Backup port.
        for _, role, state in ports:
            if state == "Discarding" and role not in ("Alternate", "Backup"):
                self.__stp_snapshots.pop(switch.name, None)
                return False

        snapshot = tuple(sorted(ports))
        if self.__stp_snapshots.get(switch.name) == snapshot:
            return True
        self.__stp_snapshots[switch.name] = snapshot
        return False

    def __unreachable_vtep_targets(self) -> list:
        """Return VXLAN underlay targets that are not yet reachable."""
        unreachable = []
        for node, _iface, target_ips in iter_vtep_network_interfaces(
            self.__network_schema.nodes
        ):
            router = self[node.data.id]
            for _vni, target_ip in target_ips:
                out = router.cmd(f"ip route get {target_ip}")
                if "unreachable" in out or not out.strip():
                    unreachable.append(f"{router.name}->{target_ip}")
        return unreachable

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
        """Check that every interface capture file exists."""
        for iface, path in iter_capture_out_files(self.__network_topology.interfaces):
            if not os.path.exists(path):
                self.__clear_files()
                raise ValueError(f"No capture for interface '{iface}'.")

    def __clear_files(self):
        """Remove pcap files."""
        for link1, link2, *_ in self.__network_topology.interfaces:
            for iface in (link1, link2):
                for f in capture_paths(iface):
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
