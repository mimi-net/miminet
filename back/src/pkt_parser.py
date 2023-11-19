import os
import random
import string

import dpkt
from dpkt.pcap import Reader
from dpkt.utils import inet_to_str


def packet_uuid(
    size: int = 8, chars: str = string.ascii_uppercase + string.digits
) -> str:
    uid = "".join(random.choice(chars) for _ in range(size))
    return "pkt_" + uid


def is_ipv4_address(dotquad: str) -> bool:
    octets = dotquad.split(".")
    return len(octets) == 4 and all(o.isdigit() and 0 <= int(o) < 256 for o in octets)


def ip_packet_type(pkt) -> str:
    if isinstance(pkt.data, dpkt.icmp.ICMP):
        icmp = pkt.data
        match icmp.type, icmp.code:
            case (8, _):
                return "ICMP echo-request"
            case (0, _):
                return "ICMP echo-reply"
            case (5, _):
                return "ICMP redirect"
            case (3, 0):
                return "ICMP destination net unreachable"
            case (3, 1):
                return "ICMP destination host unreachable"
            case (3, 3):
                return "ICMP destination port unreachable"
            case (3, _):
                return "ICMP destination unreachable"
            case (11, _):
                return "ICMP time to live exceeded"
            case _:
                return "ICMP message"

    if isinstance(pkt.data, dpkt.udp.UDP):
        udp = pkt.data
        return "UDP " + str(udp.sport) + " > " + str(udp.dport)

    if isinstance(pkt.data, dpkt.tcp.TCP):
        tcp = pkt.data
        d = {
            dpkt.tcp.TH_FIN: "FIN",
            dpkt.tcp.TH_SYN: "SYN",
            dpkt.tcp.TH_RST: "RST",
            dpkt.tcp.TH_PUSH: "PUSH",
            dpkt.tcp.TH_ACK: "ACK",
            dpkt.tcp.TH_URG: "URG",
        }

        active_flags = filter(lambda t: t[0] & tcp.flags, d.items())
        flags_str = " + ".join(t[1] for t in active_flags)

        return "TCP (" + str(flags_str) + ") " + str(tcp.sport) + " > " + str(tcp.dport)

    return "IP packet"


def arp_packet_type(pkt) -> str:
    if isinstance(pkt.data, dpkt.arp.ARP):
        arp = pkt.data

        match arp.op:
            case 1:
                return "ARP-request"
            case 2:
                return "ARP-response"
            case _:
                return "ARP packet"

    return "Unknown IP packet"


def create_pkt_animation(
    file1: str, file2: str, edge_id: str, e_source: str, e_target: str
):
    if not os.path.exists(file1) or not os.path.exists(file2):
        return None

    with open(file1, "rb") as f1, open(file2, "rb") as f2:
        pcap1 = dpkt.pcap.Reader(f1)
        pcap2 = dpkt.pcap.Reader(f2)
        pkts = packet_parser(pcap1, edge_id, e_source, e_target)
        pkts2 = packet_parser(pcap2, edge_id, e_target, e_source)

    return pkts + pkts2


def packet_parser(pcap1: Reader, edge_id: str, e_source: str, e_target: str):
    pkts = []

    # For each packet in the pcap1 process the contents
    for timestamp, buf in pcap1:
        # Unpack the Ethernet frame (mac flask/dst, ethertype)
        try:
            eth = dpkt.ethernet.Ethernet(buf)
        except dpkt.NeedData:
            continue

        # ARP
        if isinstance(eth.data, dpkt.arp.ARP):
            ts = str(timestamp)
            ts = ts.replace(".", "").ljust(16, "0")

            pkt_type = arp_packet_type(eth)
            pkts.append(
                {
                    "data": {"id": packet_uuid(), "label": pkt_type, "type": "packet"},
                    "config": {
                        "type": pkt_type,
                        "path": edge_id,
                        "source": e_source,
                        "target": e_target,
                    },
                    "timestamp": ts,
                }
            )

        if isinstance(eth.data, dpkt.llc.LLC):
            llc = eth.data

            ts = str(timestamp)
            ts = ts.replace(".", "").ljust(16, "0")

            llc_label = "LLC"

            if llc.dsap == 0x42:
                llc_label = "STP"

            pkts.append(
                {
                    "data": {"id": packet_uuid(), "label": llc_label, "type": "packet"},
                    "config": {
                        "type": llc_label,
                        "path": edge_id,
                        "source": e_source,
                        "target": e_target,
                    },
                    "timestamp": ts,
                }
            )

        # Skip IPv6
        if isinstance(eth.data, dpkt.ip6.IP6):
            continue

        # IP?
        if isinstance(eth.data, dpkt.ip.IP):
            ip = eth.data

            # Skip IGMP
            if isinstance(ip.data, dpkt.igmp.IGMP):
                continue

            ts = str(timestamp)
            ts = ts.replace(".", "").ljust(16, "0")

            pkt_type = ip_packet_type(ip)
            pkt_type = (
                pkt_type + "\n" + inet_to_str(ip.src) + " > " + inet_to_str(ip.dst)
            )

            pkts.append(
                {
                    "data": {"id": packet_uuid(), "label": pkt_type, "type": "packet"},
                    "config": {
                        "type": pkt_type,
                        "path": edge_id,
                        "source": e_source,
                        "target": e_target,
                    },
                    "timestamp": ts,
                }
            )

    return pkts


if __name__ == "__main__":
    create_pkt_animation(
        "/tmp/capture_l2sw1_2.pcapng",
        "/tmp/capture_l2sw2_1.pcapng",
        "edge_123",
        "host1",
        "sw1",
    )
