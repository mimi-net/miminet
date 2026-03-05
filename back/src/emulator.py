import os
import os.path
import subprocess
import time

import dpkt

from ipmininet.ipnet import IPNet
from jobs import Jobs
from network_schema import Job, Network
from pkt_parser import create_pkt_animation
from mininet.log import setLogLevel, info, error
from network_topology import MiminetTopology
from network import MiminetNetwork


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

    try:
        topo = MiminetTopology(network)
        net = MiminetNetwork(topo, network)

        net.start()

        # Jobs with high ID have priority over low ones
        ordered_jobs = sorted(
            network.jobs, key=lambda job: job.job_id // 100, reverse=True
        )

        info(
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
                info(
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

        info("[emulator] calling net.stop()\n")
        net.stop()

    except Exception as e:
        error(f"An error occurred during mininet configuration: {str(e)}")
        subprocess.call("mn -c", shell=True)

        raise e

    animation, pcaps = create_animation(topo.interfaces)
    # Log pcap sizes after stop to compare with pre-stop sizes
    for link1, link2, *_ in topo.interfaces:
        for fname in [
            f"/tmp/capture_{link1}_out.pcapng",
            f"/tmp/capture_{link2}_out.pcapng",
        ]:
            size = os.path.getsize(fname) if os.path.exists(fname) else -1
            info("[emulator] pcap size after stop: %s = %d bytes\n" % (fname, size))
    info("[emulator] Animation groups before grouping: %d\n" % len(animation))
    animation = group_packets_by_time(animation)
    info("[emulator] Animation groups after time-grouping: %d\n" % len(animation))

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
        pcap_out_file1 = "/tmp/capture_" + link1 + "_out.pcapng"
        pcap_out_file2 = "/tmp/capture_" + link2 + "_out.pcapng"

        pcap_file1 = "/tmp/capture_" + link1 + ".pcapng"
        pcap_file2 = "/tmp/capture_" + link2 + ".pcapng"

        if not os.path.exists(pcap_out_file1):
            raise ValueError("No capture for interface: " + link1)

        if not os.path.exists(pcap_out_file2):
            raise ValueError("No capture for interface: " + link2)

        # Log pcap sizes and packet counts before parsing
        for fname, iface, node_name in [
            (pcap_out_file1, link1, edge_source),
            (pcap_out_file2, link2, edge_target),
        ]:
            fsize = os.path.getsize(fname)
            try:
                with open(fname, "rb") as _f:
                    _count = sum(1 for _ in dpkt.pcapng.Reader(_f))
            except Exception as _e:
                _count = -1
            info(
                "[create_animation] pcap: node=%s iface=%s file=%s size=%d pkt_count=%d\n"
                % (node_name, iface, fname, fsize, _count)
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
