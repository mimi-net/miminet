import os
import os.path
import subprocess

from ipmininet.ipnet import IPNet
from jobs import Jobs
from network_schema import Job, Network
from pkt_parser import create_pkt_animation
from mininet.log import setLogLevel, error
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

        for job in ordered_jobs:
            execute_job(job, net)

        net.stop()

    except Exception as e:
        error(f"An error occurred during mininet configuration: {str(e)}")
        subprocess.call("mn -c", shell=True)

        raise e

    animation, pcaps = create_animation(topo.interfaces)
    animation = group_packets_by_time(animation)

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
