import os
import os.path
import time
import subprocess

from ipmininet.ipnet import IPNet
from jobs import Jobs
from network_schema import Job, Network
from pkt_parser import create_pkt_animation
from net_utils.vlan import setup_vlans, clean_bridges
from net_utils.vxlan import setup_vtep_interfaces, teardown_vtep_bridges
from mininet.log import setLogLevel, info
from network_topology import MiminetTopology


def create_animation(
    topo: MiminetTopology,
) -> tuple[list[list] | list, list | list[tuple[bytes, str]]]:
    """Functions for create animations

    Args:
        topo (MiminetTopology): topo for creating animation

    Returns:
        tuple: animation list and pcap, pcap_name list

    """

    pcap_list = []
    animation = []

    for link1, link2, edge_id, edge_source, edge_target in topo.iface_pairs:
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

        pkts = create_pkt_animation(
            pcap_out_file1, pcap_out_file2, edge_id, edge_source, edge_target
        )

        animation += pkts

    topo.clear_files()

    return animation, pcap_list


def do_job(job: Job, net: IPNet) -> None:
    """Execute job for network

    Args:
        job (Job): current job instance
        net (IPNet): current ipmininet net

    """

    host_id = job.host_id
    # get host from network by it's ID
    job_host = net.get(host_id)
    # initialize new Job by host and job type
    current_job = Jobs(job, job_host)
    current_job.handler()


def run_mininet(
    network: Network,
) -> tuple[list[list] | list, list | list[tuple[bytes, str]]]:
    """Function for start mininet emulation

    Args:
        network (str): Network for emulation

    Returns:
        tuple: animation list and pcap, pcap_name list
    """

    setLogLevel("info")

    if len(network.jobs) == 0:
        return [], []

    try:
        topo = MiminetTopology(network=network)
        net = IPNet(topo=topo, use_v6=False, autoSetMacs=True, allocate_IPs=False)

        net.start()

        setup_vlans(net, network.nodes)
        setup_vtep_interfaces(net, network.nodes)
        time.sleep(topo.get_network_configuration_time())
        topo.check()

        # Don only 100+ jobs
        for job in network.jobs:
            job_id = job.job_id

            if int(job_id) < 100:
                continue

            try:
                do_job(job, net)
            except Exception:
                continue

        # Do only job_id < 100
        for job in network.jobs:
            job_id = job.job_id

            if int(job_id) >= 100:
                continue

            try:
                do_job(job, net)
            except Exception:
                continue
    except Exception as e:
        print("An error occurred during mininet configuration:", str(e))
        subprocess.call("mn -c", shell=True)

        raise e

    time.sleep(2)

    import psutil

    info("Processes: ")
    current_process = psutil.Process()
    children = current_process.children(recursive=True)

    for child in children:
        info(child.name() + " " + str(child.pid))

        if not (child.name() in ["mimidump", "bash"]):
            child.kill()
            child.wait()

    clean_bridges(net)
    teardown_vtep_bridges(net, network.nodes)

    net.stop()

    animation, pcap_list = create_animation(topo)
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

    # Waitng for shuting down switches and hosts
    time.sleep(2)

    # Shut down running services
    # os.system("ps -C nc -o pid=|xargs kill -9")

    # Return animation
    return animation, pcap_list
