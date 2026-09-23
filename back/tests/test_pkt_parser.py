"""Unit tests for pkt_parser packet classification helpers.

Exercise the packet-type classifiers (DHCP/ICMP/TCP/GRE/IPIP/ARP) and the
pcap animation parser with synthetic packets so no emulator or pcap file on
disk is required.
"""

import io
import socket
import struct

import dpkt
import pytest
from dpkt.pcap import Reader, Writer
from dpkt import arp, dhcp, ethernet, icmp, igmp, ip6, tcp, udp
from dpkt.ip import IP

from src.pkt_parser import (
    VXLAN,
    arp_packet_type,
    create_pkt_animation,
    int_to_ip,
    ip_packet_type,
    is_dhcp,
    is_ipv4_address,
    packet_parser,
    packet_uuid,
    udp_packet_type,
)

SRC = socket.inet_aton("10.0.0.1")
DST = socket.inet_aton("10.0.0.2")


def ip_packet(proto: int, payload: bytes) -> IP:
    ip = IP(src=SRC, dst=DST, p=proto)
    ip.data = payload
    return IP(ip.pack())


def eth_frame(payload: bytes, etype: int) -> bytes:
    eth = ethernet.Ethernet()
    eth.src = b"\x00\x11\x22\x33\x44\x55"
    eth.dst = b"\x66\x77\x88\x99\xaa\xbb"
    eth.type = etype
    eth.data = payload
    return eth.pack()


def dhcp_payload(msgtype: int, extra=None) -> bytes:
    hdr = struct.pack(
        "!BBBBIHHIIII",
        1,
        1,
        6,
        0,
        0x01020304,
        0,
        0,
        0,
        0x0A000005,
        0,
        0,
    )
    hdr += b"\x00" * 16 + b"\x00" * 64 + b"\x00" * 128
    opts = b"\x35\x01" + bytes([msgtype])
    if extra:
        for code, value in extra:
            opts += bytes([code, len(value)]) + value
    return hdr + struct.pack("!I", 0x63825363) + opts + b"\xff"


def test_packet_uuid_shape():
    uid = packet_uuid()
    assert uid.startswith("pkt_")
    assert len(uid) == 4 + 8
    uid2 = packet_uuid(size=4, chars="ABC")
    assert len(uid2) == 4 + 4
    assert set(uid2[4:]) <= set("ABC")


def test_is_ipv4_address():
    assert is_ipv4_address("192.168.1.1")
    assert is_ipv4_address("0.0.0.0")
    assert is_ipv4_address("255.255.255.255")
    assert not is_ipv4_address("256.1.1.1")
    assert not is_ipv4_address("1.2.3")
    assert not is_ipv4_address("a.b.c.d")
    assert not is_ipv4_address("1.2.3.4.5")


def test_int_to_ip():
    assert int_to_ip(0x0A000001) == "10.0.0.1"
    assert int_to_ip(0) == "0.0.0.0"
    assert int_to_ip(0xFFFFFFFF) == "255.255.255.255"
    assert int_to_ip(None) == ""


def test_is_dhcp():
    u = udp.UDP(sport=68, dport=67, data=dhcp_payload(dhcp.DHCPDISCOVER))
    assert is_dhcp(u)
    assert not is_dhcp(udp.UDP(sport=68, dport=67, data=b"\x00" * 5))
    assert not is_dhcp(udp.UDP(sport=68, dport=67, data=b""))


@pytest.mark.parametrize(
    ("msgtype", "extra", "expected"),
    [
        (dhcp.DHCPDISCOVER, None, "DHCP Discover"),
        (dhcp.DHCPOFFER, [(1, b"\xff\xff\xff\x00")], "DHCP Offer 10.0.0.5/24"),
        (dhcp.DHCPREQUEST, [(50, b"\x0a\x00\x00\x05")], "DHCP Request 10.0.0.5"),
        (dhcp.DHCPDECLINE, None, "DHCP Decline"),
        (dhcp.DHCPACK, None, "DHCP ACK"),
        (dhcp.DHCPNAK, None, "DHCP NAK"),
        (dhcp.DHCPRELEASE, None, "DHCP Release"),
        (dhcp.DHCPINFORM, None, "DHCP Inform"),
    ],
)
def test_dhcp_message_types(msgtype, extra, expected):
    u = udp.UDP(sport=68, dport=67, data=dhcp_payload(msgtype, extra))
    assert udp_packet_type(u) == expected


def test_udp_packet_type_default():
    u = udp.UDP(sport=5000, dport=5001, data=b"hello")
    assert udp_packet_type(u) == "UDP 5000 > 5001"


@pytest.mark.parametrize(
    ("type_", "code", "expected"),
    [
        (8, 0, "ICMP echo-request"),
        (0, 0, "ICMP echo-reply"),
        (5, 0, "ICMP redirect"),
        (3, 0, "ICMP destination net unreachable"),
        (3, 1, "ICMP destination host unreachable"),
        (3, 3, "ICMP destination port unreachable"),
        (3, 9, "ICMP destination unreachable"),
        (11, 0, "ICMP time to live exceeded"),
        (12, 0, "ICMP message"),
    ],
)
def test_icmp_packet_types(type_, code, expected):
    payload = icmp.ICMP(type=type_, code=code).pack()
    assert ip_packet_type(ip_packet(1, payload)) == expected


def test_tcp_packet_type_flags():
    pkt = tcp.TCP(sport=1234, dport=80)
    pkt.flags = tcp.TH_SYN | tcp.TH_ACK
    assert ip_packet_type(ip_packet(6, pkt.pack())) == "TCP (SYN + ACK) 1234 > 80"


def test_tunnel_packet_types():
    gre = dpkt.gre.GRE()
    assert ip_packet_type(ip_packet(47, gre.pack())) == "GRE tunnel"
    inner = IP(src=SRC, dst=DST)
    assert ip_packet_type(ip_packet(4, inner.pack())) == "IPIP tunnel"


def _arp(op: int):
    a = arp.ARP(op=op, sha=b"\x00\x11\x22\x33\x44\x55", spa=SRC, tpa=DST)
    a.hln = 6
    a.pln = 4
    return ethernet.Ethernet(eth_frame(a.pack(), 0x0806))


def test_arp_packet_types():
    assert arp_packet_type(_arp(1)) == "ARP-request\nWho has 10.0.0.2? Tell 10.0.0.1"
    assert arp_packet_type(_arp(2)) == "ARP-response\n10.0.0.1 at 00:11:22:33:44:55"
    assert arp_packet_type(_arp(9)) == "ARP packet"


def test_arp_packet_type_unknown():
    eth = ethernet.Ethernet()
    eth.type = 0x0800
    assert arp_packet_type(eth) == "Unknown IP packet"


def test_vxlan_vni_property():
    vx = VXLAN()
    vx.vni = 0xABCDEF
    assert vx.vni == 0xABCDEF


def _sample_pcap():
    a = arp.ARP(op=1, sha=b"\x00\x11\x22\x33\x44\x55", spa=SRC, tpa=DST)
    a.hln = 6
    a.pln = 4
    ig = igmp.IGMP()
    i6 = ip6.IP6()
    i6.src = socket.inet_pton(socket.AF_INET6, "2001:db8::1")
    i6.dst = socket.inet_pton(socket.AF_INET6, "2001:db8::2")
    t = tcp.TCP(sport=3333, dport=80)
    frames = [
        eth_frame(a.pack(), 0x0806),
        eth_frame(ip_packet(1, icmp.ICMP(type=8, code=0).pack()), 0x0800),
        eth_frame(ip_packet(2, ig.pack()), 0x0800),
        eth_frame(ip_packet(6, t.pack()), 0x0800),
        eth_frame(i6.pack(), 0x86DD),
        b"\x00\x11\x22",
    ]
    bio = io.BytesIO()
    w = Writer(bio)
    for i, frame in enumerate(frames):
        w.writepkt(frame, ts=1000.0 + i)
    bio.seek(0)
    return bio


def test_packet_parser_synthetic_pcap():
    out = packet_parser(Reader(_sample_pcap()), "edge1", "host1", "host2", 0, 0)
    labels = [o["data"]["label"].split("\n")[0] for o in out]
    assert labels == ["ARP-request", "ICMP echo-request", "TCP (SYN) 3333 > 80"]
    cfg = out[0]["config"]
    assert cfg["path"] == "edge1"
    assert cfg["source"] == "host1"
    assert cfg["target"] == "host2"
    assert cfg["loss_percentage"] == 0
    assert cfg["duplicate_percentage"] == 0
    assert all(o["timestamp"].isdigit() for o in out)


def test_create_pkt_animation_missing_files():
    assert create_pkt_animation("/no/such/1", "/no/such/2", "e", "a", "b") is None
