import os
import os.path
import subprocess
from psutil import Process

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
        tuple: animation list and pcap, pcap_name list.
    """

    setLogLevel("info")

    if len(network.jobs) == 0:
        return [], []

    try:
        # Build topology using network schema
        topo = MiminetTopology(network=network)
        # Build runnable network using topology and network schema
        net = MiminetNetwork(topo, network)

        net.start()

        # jobs with high ID have priority over low ones
        ordered_jobs = sorted(network.jobs, key=lambda job: job.job_id, reverse=True)

        for job in ordered_jobs:
            execute_job(job, net)

        net.stop()

    except Exception as e:
        error(f"An error occurred during mininet configuration: {str(e)}")
        subprocess.call("mn -c", shell=True)

        raise e

    animation, pcap_list = create_animation(topo.interfaces)
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

    return animation, pcap_list


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
    animation_frames = []

    for link1, link2, edge_id, edge_source, edge_target in interfaces_info:
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
            pcap_out_file1, pcap_out_file2, edge_id, edge_source, edge_target
        )

        animation_frames += packets

    return animation_frames, pcap_list


def execute_job(job: Job, net: IPNet) -> None:
    """Execute network job (ping, nc, ...)."""
    job_host = net.get(job.host_id)

    new_job = Jobs(job, job_host)
    new_job.handler()


def clean_processes():
    """
    Processes running in virtual devices aren't deleted by themselves.

    This function kill them manually.
    """
    info("Starting processes cleanup... ")

    current_process = Process()
    children_processes = current_process.children(recursive=True)

    # Mininet can kill this processes by itself
    good_process_names = ("mimidump", "bash")

    for child in children_processes:
        if child.name() not in good_process_names:
            info(f"Killed: {child.name()} {str(child.pid)}")
            child.kill()
            child.wait()
