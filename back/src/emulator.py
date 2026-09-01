import os
import os.path
import subprocess
import time

import dpkt

from ipmininet.ipnet import IPNet
from jobs import Jobs
from network import MiminetNetwork
from network_schema import Job, Network
from pkt_parser import create_pkt_animation
from mininet.log import setLogLevel, info, error
from net_utils.captures import capture_out_path, capture_paths
from network_topology import MiminetTopology

# Server-start jobs launch background listeners (`nc -k -l`, `nc -d -u -l`,
# dhcpd). Client jobs that follow can race ahead of the bind: the first SYN
# hits a not-yet-listening socket and the kernel answers RST (connection
# refused), which surfaces as a flaky tcp/port-forwarding handshake in the test
# suite. Give these jobs a short grace so the socket is bound before clients
# act. MIMINET_SERVER_SETTLE overrides the window (seconds) for tuning.
SERVER_SETTLE_JOBS = frozenset({200, 201, 203})
SERVER_SETTLE_SECONDS = float(os.environ.get("MIMINET_SERVER_SETTLE", "0.5"))


def emulate(
    network: Network,
) -> tuple[list[list], list[tuple[bytes, str]]]:
    """Run mininet emulation.

    Args:
        network (str): Network schema for emulation.

    Returns:
        tuple: animation list and pcap files.
    """

    setLogLevel("info")

    # Validate job limit
    MAX_JOBS_COUNT = 30
    MAX_TIME_SLEEP = 60
    if len(network.jobs) > MAX_JOBS_COUNT:
        raise ValueError(
            f"Превышен лимит! В сети максимальное количество команд ({MAX_JOBS_COUNT}). "
            f"Текущее количество: {len(network.jobs)}"
        )
    sleep_jobs = [j for j in network.jobs if j.job_id == 7]
    total_time = sum(int(j.arg_1) for j in sleep_jobs)
    if total_time > 60 or total_time < 0:
        raise ValueError(
            f"Превышен лимит! В сети максимальное количество команд sleep {MAX_TIME_SLEEP})."
        )

    if len(network.jobs) == 0:
        return [], []

    net = None
    try:
        topo = MiminetTopology(network)
        net = MiminetNetwork(topo, network)

        net.start()

        # Jobs with high ID have priority over low ones
        ordered_jobs = sorted(
            network.jobs, key=lambda job: job.job_id // 100, reverse=True
        )

        error(
            "[emulator] Job execution order (%d jobs): %s\n"
            % (
                len(ordered_jobs),
                ", ".join(
                    f"[host={j.host_id} job_id={j.job_id} cmd={j.print_cmd!r}]"
                    for j in ordered_jobs
                ),
            )
        )

        for job in ordered_jobs:
            info(
                "[emulator] Executing job: host=%s job_id=%s cmd=%r args=(%r, %r, %r, %r, %r)\n"
                % (
                    job.host_id,
                    job.job_id,
                    job.print_cmd,
                    job.arg_1,
                    job.arg_2,
                    job.arg_3,
                    job.arg_4,
                    job.arg_5,
                )
            )
            t0 = time.monotonic()
            execute_job(job, net)
            elapsed = time.monotonic() - t0
            info(
                "[emulator] Finished job: host=%s job_id=%s elapsed=%.2fs\n"
                % (job.host_id, job.job_id, elapsed)
            )
            if job.job_id in SERVER_SETTLE_JOBS:
                info(
                    "[emulator] server job %s started; settling %.2fs\n"
                    % (job.job_id, SERVER_SETTLE_SECONDS)
                )
                time.sleep(SERVER_SETTLE_SECONDS)

        # Log pcap file sizes AND actual paths used by mimidump before stop().
        # mimidump writes to {intf.node.cwd}/capture_{intf.name}_out.pcapng —
        # for hosts cwd may differ from /tmp (routers use /tmp, plain hosts may use /).
        for link1, link2, edge_id, edge_source, edge_target, *_ in topo.interfaces:
            for iface_name, node_name in [(link1, edge_source), (link2, edge_target)]:
                node = net.get(node_name)
                node_cwd = getattr(node, "cwd", "/tmp")
                actual_path = f"{node_cwd}/capture_{iface_name}_out.pcapng"
                expected_path = f"/tmp/capture_{iface_name}_out.pcapng"
                actual_size = (
                    os.path.getsize(actual_path) if os.path.exists(actual_path) else -1
                )
                expected_size = (
                    os.path.getsize(expected_path)
                    if os.path.exists(expected_path)
                    else -1
                )
                error(
                    "[emulator] pcap before stop: node=%s iface=%s "
                    "node_cwd=%r actual_path=%s(%d bytes) expected_path=%s(%d bytes)\n"
                    % (
                        node_name,
                        iface_name,
                        node_cwd,
                        actual_path,
                        actual_size,
                        expected_path,
                        expected_size,
                    )
                )

        error("[emulator] calling net.stop()\n")
        net.stop()

    except Exception as e:
        error(f"An error occurred during mininet configuration: {str(e)}")
        # Always tear the network down, even on a failed start: skipping
        # net.stop() would leave mimidump processes alive, still writing to the
        # same /tmp/capture_* paths, so the next attempt would read stale data
        # left behind by this one.
        if net is not None:
            try:
                net.stop()
            except Exception as stop_err:
                error(f"Failed to stop network after error: {stop_err}")
        subprocess.call("mn -c", shell=True)

        raise e

    animation, pcaps = create_animation(topo.interfaces)
    # Log pcap sizes after stop to compare with pre-stop sizes
    for link1, link2, *_ in topo.interfaces:
        for fname in [capture_out_path(link1), capture_out_path(link2)]:
            size = os.path.getsize(fname) if os.path.exists(fname) else -1
            error("[emulator] pcap size after stop: %s = %d bytes\n" % (fname, size))
    error("[emulator] Animation groups before grouping: %d\n" % len(animation))
    animation = group_packets_by_time(animation)
    error("[emulator] Animation groups after time-grouping: %d\n" % len(animation))

    return animation, pcaps


def create_animation(
    interfaces_info,
) -> tuple[list[list] | list, list | list[tuple[bytes, str]]]:
    """Creates an animation using saved pcap files.

    Args:
        interfaces_info: Interface information stored in the topology.

    Returns:
        tuple: A tuple containing the animation list and a list of packet captures with their names.
    """

    pcap_list = []
    animation = []

    for (
        link1,
        link2,
        edge_id,
        edge_source,
        edge_target,
        loss_percentage,
        duplicate_percentage,
    ) in interfaces_info:
        pcap_file1, pcap_out_file1 = capture_paths(link1)
        pcap_file2, pcap_out_file2 = capture_paths(link2)

        if not os.path.exists(pcap_out_file1):
            raise ValueError("No capture for interface: " + link1)

        if not os.path.exists(pcap_out_file2):
            raise ValueError("No capture for interface: " + link2)

        # Log pcap sizes and packet counts before parsing
        for fname, iface, node_name, direction in [
            (pcap_file1, link1, edge_source, "INOUT"),
            (pcap_out_file1, link1, edge_source, "OUT"),
            (pcap_file2, link2, edge_target, "INOUT"),
            (pcap_out_file2, link2, edge_target, "OUT"),
        ]:
            if not os.path.exists(fname):
                error(
                    "[create_animation] pcap: node=%s iface=%s direction=%s MISSING\n"
                    % (node_name, iface, direction)
                )
                continue
            fsize = os.path.getsize(fname)
            count_pcap = count_pcapng = -1
            try:
                with open(fname, "rb") as _f:
                    count_pcap = sum(1 for _ in dpkt.pcap.Reader(_f))
            except Exception:
                pass
            try:
                with open(fname, "rb") as _f:
                    count_pcapng = sum(1 for _ in dpkt.pcapng.Reader(_f))
            except Exception:
                pass
            error(
                "[create_animation] pcap: node=%s iface=%s direction=%s "
                "file=%s size=%d pcap_count=%d pcapng_count=%d\n"
                % (node_name, iface, direction, fname, fsize, count_pcap, count_pcapng)
            )

        with open(pcap_file1, "rb") as file1, open(pcap_file2, "rb") as file2:
            pcap_list.append((file1.read(), link1))
            pcap_list.append((file2.read(), link2))

        packets = create_pkt_animation(
            pcap_out_file1,
            pcap_out_file2,
            edge_id,
            edge_source,
            edge_target,
            loss_percentage,
            duplicate_percentage,
        )

        animation += packets

    return animation, pcap_list


def group_packets_by_time(packets, time_slice_us: int = 14000):
    """Group packets into animation frames by time intervals.

    Args:
        packets: List of packets.
        time_slice_us (int): Time interval (in microseconds) to group packets.

    Returns:
        list: Grouped animation frames.
    """
    if not packets:
        return []

    animation_packets = sorted(packets, key=lambda k: k.get("timestamp", 0))

    grouped = []
    current_group: list = []
    first_packet_time = int(animation_packets[0]["timestamp"])
    time_limit = first_packet_time + time_slice_us

    for pkt in animation_packets:
        pkt_time = int(pkt["timestamp"])

        if pkt_time > time_limit:
            # Add packet to new group based on its time
            grouped.append(current_group)
            current_group = [pkt]
            time_limit = pkt_time + time_slice_us
        else:
            current_group.append(pkt)

    if current_group:
        grouped.append(current_group)

    return grouped


def execute_job(job: Job, net: IPNet) -> None:
    """Execute network job (ping, nc, ...)."""
    job_host = net.get(job.host_id)

    new_job = Jobs(job, job_host)
    new_job.handler()
