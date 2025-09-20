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

# test copy func from miminet_host
import re
from typing import List, Dict
import shlex


def filter_arg_for_options(
    arg: str, flags_without_args: List[str], flags_with_args: Dict[str, str]
) -> str:
    """Get from str only whitelist options"""
    parts = shlex.split(re.sub(r"[^A-Za-z0-9._\-]+", " ", arg))

    res = ""

    for idx, token in enumerate(parts):
        if token in res:
            continue

        if token in flags_with_args and idx + 1 < len(parts):
            next_arg = parts[idx + 1]
            if re.fullmatch(flags_with_args[token], next_arg):
                res += f"{token} {next_arg} "

        elif token in flags_without_args:
            res += f"{token} "

    return res


def ping_options_filter(arg: str) -> str:
    """Get only whitelist options from ping options"""
    flags_without_args = ["-b"]
    flags_with_args = {"-c": r"([1-9]|10)", "-t": r"\d+", "-i": r"\d+", "-s": r"\d+"}

    return filter_arg_for_options(arg, flags_without_args, flags_with_args)


def traceroute_options_filter(arg: str) -> str:
    """Get only whitelist options from traceout options"""
    flags_without_args = ["-F", "-n"]
    flags_with_args = {
        "-i": r"\d+",
        "-f": r"\d+",
        "-g": r"\d+",
        "-m": r"\d+",
        "-p": r"\d+",
    }
    return filter_arg_for_options(arg, flags_without_args, flags_with_args)


##############


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

    if len(network.jobs) == 0:
        return [], []

    try:
        topo = MiminetTopology(network)
        net = MiminetNetwork(topo, network)

        net.start()

        # Jobs with high ID have priority over low ones
        ordered_jobs = sorted(network.jobs, key=lambda job: job.job_id, reverse=True)

        for job in ordered_jobs:
            match job.job_id:
                case 2:
                    job.arg_1 = ping_options_filter(job.arg_1)
                    if job.arg_1:
                        execute_job(job, net)
                case 5:
                    job.arg_1 = traceroute_options_filter(job.arg_1)
                    if job.arg_1:
                        execute_job(job, net)
                case _:
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
