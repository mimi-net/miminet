import os
import time

import psutil
from ipmininet.ipnet import IPNet
from mininet.log import info
from net_utils.captures import capture_paths
from net_utils.readiness import iter_capture_endpoints
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
        # Whether the adaptive settle hit its cap instead of breaking early on
        # quiescence. Exposed for the benchmark harness (back/bench/bench.py).
        self.settle_hit_cap: bool = False

    def start(self):
        # Start network
        super().start()

        # Additional settings
        setup_vlans(self, self.__network_schema.nodes)
        setup_vtep_interfaces(self, self.__network_schema.nodes)

        # Stop the IPv6 multicast chatter on this IPv4-only emulation (see
        # __disable_ipv6); needed for the adaptive settle to see genuinely
        # quiet links. On by default; opt out with MIMINET_DISABLE_IPV6=0.
        if os.environ.get("MIMINET_DISABLE_IPV6", "1") == "1":
            self.__disable_ipv6()

        # Wait until the network is actually usable, instead of a fixed sleep:
        # capture files exist, STP/RSTP switches have converged, and the VXLAN
        # underlay is reachable. This makes correctness independent of
        # network_configuration_time (even 0).
        self.__wait_until_ready()

    def __wait_until_ready(self, timeout: float = 90.0, poll: float = 0.5) -> None:
        """Poll until the emulation environment is really ready.

        Deterministic conditions (no fixed sleeps):
          1. Every interface capture is live (mimidump READY via
             NetworkCapture.wait_until_capturing).
          2. STP/RSTP switches report all ports in the forwarding state.
          3. Every VXLAN underlay endpoint is reachable from its local router.

        Raises a descriptive error if the conditions are not met within
        ``timeout`` seconds.
        """
        deadline = time.monotonic() + timeout
        restart_grace = float(os.environ.get("MIMINET_CAPTURE_RESTART_GRACE", "2.0"))
        capture_restarted = False
        while time.monotonic() < deadline:
            captures_not_live = self.__captures_not_live()
            unconverged = self.__unconverged_switches()
            unreachable = self.__unreachable_vtep_targets()
            if not captures_not_live and not unconverged and not unreachable:
                return
            # mimidump can race interface startup: it may start while the
            # interface is still down and block in its internal ifup wait for
            # up to 100s, leaving the capture unattached. The interface is
            # certainly up now, so once the grace window has passed restart the
            # still-not-live captures a single time and keep waiting. A stale
            # file left by a died captor process is treated the same as a
            # missing one — both mean the capture is not attached.
            if (
                captures_not_live
                and not capture_restarted
                and time.monotonic() - (deadline - timeout) > restart_grace
            ):
                self.__restart_captures(self.__captures_not_live(timeout=1.0))
                capture_restarted = True
            info(
                "[network] waiting for readiness: captures_not_live=%s "
                "stp_unconverged=%s vtep_unreachable=%s\n"
                % (captures_not_live, unconverged, unreachable)
            )
            time.sleep(poll)

        details = []
        captures_not_live = self.__captures_not_live()
        if captures_not_live:
            details.append(
                "captures not live: %s"
                % ", ".join(iface for _node, iface in captures_not_live)
            )
        if self.__unconverged_switches():
            details.append("STP/RSTP switches not forwarding")
        if self.__unreachable_vtep_targets():
            details.append("VXLAN underlay unreachable")
        raise TimeoutError(
            "Network did not become ready within %ss: %s"
            % (timeout, ", ".join(details))
        )

    def __captures_not_live(self, timeout: float = 0.1) -> list:
        """Return interface endpoints whose capture is not confirmed live yet.

        Consumes ipmininet's ``NetworkCapture.wait_until_capturing`` in strict
        mode (mimidump READY signal, or a pcap file that keeps growing past its
        header) so jobs start only after the capture is actually attached — not
        just because its output file exists. The default ``timeout`` is a short
        per-poll gate; callers that need a definitive answer (the restart path)
        pass a longer one.
        """
        not_live = []
        for node_name, iface_name, _intf, captures in iter_capture_endpoints(
            self.__network_topology.interfaces,
            lambda node_name, iface_name: self[node_name].intf(iface_name),
        ):
            for capture in captures:
                if not capture.wait_until_capturing(
                    iface_name, timeout=timeout, strict=True
                ):
                    not_live.append((node_name, iface_name))
                    break
        return not_live

    def __restart_captures(self, stale: list) -> None:
        """Restart the packet capture on the given stale interface endpoints.

        mimidump may start while the interface is still down and block in its
        internal ifup wait (up to 100s), never attaching the capture; or the
        captor process may have died leaving a stale file behind. Either way
        the interface is certainly up by the time we get here, so kill any
        lingering process, drop the stale files and start a fresh capture.
        """
        endpoints = {
            (node_name, iface_name): (intf, captures)
            for node_name, iface_name, intf, captures in iter_capture_endpoints(
                self.__network_topology.interfaces,
                lambda node_name, iface_name: self[node_name].intf(iface_name),
            )
        }
        for node_name, iface_name in stale:
            if (node_name, iface_name) not in endpoints:
                continue
            intf, captures = endpoints[(node_name, iface_name)]
            for capture in captures:
                proc = capture.ongoing_captures.get(iface_name)
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait()
                capture.ongoing_captures.pop(iface_name, None)
            for path in capture_paths(iface_name):
                if os.path.exists(path):
                    os.remove(path)
            for capture in captures:
                capture.start(intf=intf)
            info("[network] restarted capture for interface %s\n" % iface_name)

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

    def __disable_ipv6(self) -> None:
        """Disable IPv6 per interface: the emulated kernel stacks emit a
        continuous DAD/MLDv2 multicast flood that keeps every OVS port busy,
        defeating the adaptive settle. Harmless (Miminet is IPv4-only)."""
        for node in list(self.hosts) + list(self.routers):
            node.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1 >/dev/null 2>&1")
        for switch in self.switches:
            switch.cmd(
                "sysctl -w net.ipv6.conf.%s.disable_ipv6=1 >/dev/null 2>&1"
                % switch.name
            )
            for intf in switch.intfNames():
                switch.cmd(
                    "sysctl -w net.ipv6.conf.%s.disable_ipv6=1 >/dev/null 2>&1" % intf
                )

    def __own_observable_interfaces(self, pernic: dict) -> list:
        """Root-netns OVS ports carrying this emulation's traffic (every edge
        crosses a switch bridge port), so concurrent emulations or container
        chatter cannot mask quiescence."""
        names = set()
        for switch in self.switches:
            names.update(switch.intfNames())
            # VLAN mode moves the data ports to a br-{switch} bridge.
            names.add("br-%s" % switch.name)
        return [n for n in names if n in pernic]

    def __settle(self) -> None:
        """Wait for async tail traffic (echo-replies, DHCP ACK, VXLAN/NAT
        propagation) to drain by polling this emulation's own OVS ports; tear
        down once they have been quiet for ~0.3s, capped at 2.0s. A fixed 2.0s
        floor is reliable but dominates simple networks, hence the 1.2s floor.

        Knobs (read at call time): MIMINET_STOP_SLEEP forces the old fixed
        sleep; MIMINET_SETTLE_MIN sets the floor (default 1.2). Sets
        ``self.settle_hit_cap`` so benchmarks can tell early breaks from
        cap-bound ones.
        """
        override = os.environ.get("MIMINET_STOP_SLEEP")
        if override is not None:
            duration = float(override)
            info("[network.settle] fixed override, sleeping %ss\n" % duration)
            time.sleep(duration)
            self.settle_hit_cap = False
            return

        min_s = float(os.environ.get("MIMINET_SETTLE_MIN", "1.2"))
        max_s = 2.0
        poll_s = 0.1
        quiet_polls = 3

        start = time.monotonic()
        deadline = start + max_s
        pernic = psutil.net_io_counters(pernic=True)
        names = self.__own_observable_interfaces(pernic)
        if not names:
            info("[network.settle] no observable interfaces; fixed %ss floor\n" % min_s)
            time.sleep(min_s)
            self.settle_hit_cap = False
            return

        prev = {n: (pernic[n].packets_recv, pernic[n].packets_sent) for n in names}
        quiet = 0
        while time.monotonic() < deadline:
            time.sleep(poll_s)
            now = psutil.net_io_counters(pernic=True)
            active = False
            for n in names:
                c = now.get(n)
                if c is None:
                    continue
                p = prev.get(n)
                if p is not None:
                    if c.packets_recv - p[0] or c.packets_sent - p[1]:
                        active = True
                prev[n] = (c.packets_recv, c.packets_sent)
            if active:
                quiet = 0
            else:
                quiet += 1
                if quiet >= quiet_polls and time.monotonic() - start >= min_s:
                    break

        elapsed = time.monotonic() - start
        self.settle_hit_cap = elapsed >= max_s - 1e-6
        info(
            "[network.settle] settled in %.2fs (cap=%.1fs, hit_cap=%s)\n"
            % (elapsed, max_s, self.settle_hit_cap)
        )

    def stop(self):
        info("[network.stop] called\n")
        # Pre-teardown settle window for async tail traffic (echo-replies,
        # DHCP ACK, ICMP unreachable, VXLAN/NAT propagation).
        self.__settle()

        clean_bridges(self)
        teardown_vtep_bridges(self, self.__network_schema.nodes)

        info("[network.stop] calling __clean_services\n")
        self.__clean_services()
        info(
            "[network.stop] calling super().stop() — this will send SIGINT to mimidump\n"
        )
        super().stop()
        info("[network.stop] done\n")

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
