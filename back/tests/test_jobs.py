"""Unit tests for jobs.py validators, option filters and command handlers.

Covers the pure checkers/filters and the handler dispatch against a recording
fake host, so the argument-guard and command-emission paths run rootless.
"""

import pytest

from network_schema import Job
from src import jobs as J


class FakeHost:
    def __init__(self):
        self.name = "host1"
        self.calls = []

    def cmd(self, line):
        self.calls.append(line)
        return ""


def job(job_id, **args):
    return Job(id="job", level=1, job_id=job_id, host_id="host1", print_cmd="", **args)


def test_valid_ip():
    assert J.valid_ip("10.0.0.1")
    assert J.valid_ip("fe80::1")
    assert not J.valid_ip("300.1.1.1")
    assert not J.valid_ip("not-an-ip")
    assert not J.valid_ip("")


def test_valid_mac():
    assert J.valid_mac("00:11:22:33:44:55")
    assert not J.valid_mac("not-a-mac")


def test_valid_port():
    assert J.valid_port(80)
    assert J.valid_port("8080")
    assert J.valid_port(70000)
    assert not J.valid_port("abc")
    assert not J.valid_port(None)


def test_valid_iface():
    assert J.valid_iface("eth0")
    assert J.valid_iface("eth_0")
    assert not J.valid_iface("eth0.1")
    assert not J.valid_iface("Eth0")
    assert not J.valid_iface("eth 0")


def test_net_dev_checker():
    assert J.net_dev_checker("eth0")
    assert J.net_dev_checker("eth_0")
    assert J.net_dev_checker("eth0.1:2-3")
    assert not J.net_dev_checker("Eth0")
    assert not J.net_dev_checker("9eth")


def test_valid_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", lambda s: slept.append(s))
    assert J.valid_sleep(1)
    assert J.valid_sleep("10")
    assert not J.valid_sleep(0)
    assert not J.valid_sleep(51)
    assert not J.valid_sleep("abc")
    assert not J.valid_sleep(None)


def test_udp_tcp_args_checker():
    assert J.udp_tcp_args_checker("10.0.0.1", "1000", "5000")
    assert not J.udp_tcp_args_checker("bad", "1000", "5000")
    assert not J.udp_tcp_args_checker("10.0.0.1", "x", "5000")
    assert not J.udp_tcp_args_checker("10.0.0.1", "1000", None)


def test_ip_addr_add_checker():
    assert J.ip_addr_add_checker("10.0.0.1", "24", "eth0")
    assert not J.ip_addr_add_checker("bad", "24", "eth0")
    assert not J.ip_addr_add_checker("10.0.0.1", "x", "eth0")
    assert not J.ip_addr_add_checker("10.0.0.1", "24", "Eth0")


def test_ip_route_add_checker():
    assert J.ip_route_add_checker("10.0.0.0", "24", "10.0.0.1")
    assert not J.ip_route_add_checker("bad", "24", "10.0.0.1")
    assert not J.ip_route_add_checker("10.0.0.0", "x", "10.0.0.1")
    assert not J.ip_route_add_checker("10.0.0.0", "24", "bad")


def test_subinterface_vlan_checker():
    assert J.subinterface_vlan_checker("eth0", "10.0.0.1", "24", 10, "eth0")
    assert not J.subinterface_vlan_checker("Eth0", "10.0.0.1", "24", 10, "eth0")
    assert not J.subinterface_vlan_checker("eth0", "bad", "24", 10, "eth0")
    assert not J.subinterface_vlan_checker("eth0", "10.0.0.1", "x", 10, "eth0")
    assert not J.subinterface_vlan_checker("eth0", "10.0.0.1", "24", 10, "")


def test_ipip_interface_checker():
    assert J.ipip_interface_checker("10.0.0.1", "10.0.0.2", "10.0.0.3", "tun0")
    assert not J.ipip_interface_checker("bad", "10.0.0.2", "10.0.0.3", "tun0")
    assert not J.ipip_interface_checker("10.0.0.1", "10.0.0.2", "10.0.0.3", "Tun0")


def test_add_gre_checker():
    assert J.add_gre_checker("10.0.0.1", "10.0.0.2", "10.0.0.3", "gre0")
    assert not J.add_gre_checker("bad", "10.0.0.2", "10.0.0.3", "gre0")
    assert not J.add_gre_checker("10.0.0.1", "10.0.0.2", "10.0.0.3", "Gre0")


def test_port_forwarding_checker():
    assert J.port_forwarding_checker("eth0", "8080", "10.0.0.5", "80")
    assert not J.port_forwarding_checker("Eth0", "8080", "10.0.0.5", "80")
    assert not J.port_forwarding_checker("eth0", "abc", "10.0.0.5", "80")
    assert not J.port_forwarding_checker("eth0", "8080", "bad", "80")


def test_filter_arg_for_options_dedupes():
    out = J.filter_arg_for_options("-c 1 -c 1 -b", ["-b"], {"-c": r"\d+"})
    assert out.count("-c") == 1
    assert out == "-c 1 -b "


def test_filter_arg_for_options_rejects_nonmatching_value():
    out = J.filter_arg_for_options("-i abc", [], {"-i": r"\d+"})
    assert out == ""


def test_ping_options_filter():
    assert J.ping_options_filter("-c 2") == "-c 2 "
    assert J.ping_options_filter("-b -c 10") == "-b -c 10 "
    assert J.ping_options_filter("-c 20") == ""
    assert J.ping_options_filter("-s 128") == "-s 128 "


def test_traceroute_options_filter():
    assert J.traceroute_options_filter("-F -n") == "-F -n "
    assert J.traceroute_options_filter("-m 5") == "-m 5 "
    assert J.traceroute_options_filter("-g abc") == ""


def test_link_down_handler():
    host = FakeHost()
    J.link_down_handler(job(6, arg_1="eth0"), host)
    assert host.calls == ["ip link set eth0 down"]
    J.link_down_handler(job(6, arg_1="Eth0"), host)
    assert len(host.calls) == 1


def test_sleep_handler(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", lambda s: slept.append(s))
    host = FakeHost()
    J.sleep_handler(job(7, arg_1=2), host)
    assert slept == [2]
    J.sleep_handler(job(7, arg_1="x"), host)
    assert slept == [2]


def test_ping_handler():
    host = FakeHost()
    J.ping_handler(job(1, arg_1="10.0.0.1"), host)
    assert host.calls == ["ping -c 1 10.0.0.1"]
    J.ping_handler(job(1, arg_1="bad"), host)
    assert len(host.calls) == 1


def test_ping_with_options_handler():
    host = FakeHost()
    J.ping_with_options_handler(job(2, arg_1="-c 2", arg_2="10.0.0.1"), host)
    assert host.calls == ["ping -c 1 -c 2  10.0.0.1"]
    host.calls.clear()
    J.ping_with_options_handler(job(2, arg_1="", arg_2="10.0.0.1"), host)
    assert host.calls == ["ping -c 1  10.0.0.1"]
    host.calls.clear()
    J.ping_with_options_handler(job(2, arg_1="-c 2", arg_2="bad"), host)
    assert host.calls == []


def test_sending_udp_data_handler():
    host = FakeHost()
    J.sending_udp_data_handler(
        job(3, arg_1="1000", arg_2="10.0.0.1", arg_3="5000"), host
    )
    assert host.calls == ["dd if=/dev/urandom bs=1000 count=1 | nc -uq1 10.0.0.1 5000"]
    J.sending_udp_data_handler(job(3, arg_1="x", arg_2="10.0.0.1", arg_3="5000"), host)
    assert len(host.calls) == 1


def test_sending_tcp_data_handler():
    host = FakeHost()
    J.sending_tcp_data_handler(
        job(4, arg_1="1000", arg_2="10.0.0.1", arg_3="5000"), host
    )
    assert host.calls == [
        "dd if=/dev/urandom bs=1000 count=1 | nc -w 30 -q1 10.0.0.1 5000"
    ]


def test_traceroute_handler():
    host = FakeHost()
    J.traceroute_handler(job(5, arg_1="-m 5", arg_2="10.0.0.1"), host)
    assert host.calls == ["traceroute -n -m 5  10.0.0.1"]
    host.calls.clear()
    J.traceroute_handler(job(5, arg_1="", arg_2="10.0.0.1"), host)
    assert host.calls == ["traceroute -n  10.0.0.1"]
    host.calls.clear()
    J.traceroute_handler(job(5, arg_1="-m 5", arg_2="bad"), host)
    assert host.calls == []


def test_ip_addr_add_handler():
    host = FakeHost()
    J.ip_addr_add_handler(job(100, arg_1="eth0", arg_2="10.0.0.1", arg_3="24"), host)
    assert host.calls == ["ip addr add 10.0.0.1/24 dev eth0"]
    J.ip_addr_add_handler(job(100, arg_1="Eth0", arg_2="10.0.0.1", arg_3="24"), host)
    assert len(host.calls) == 1


def test_iptables_handler():
    host = FakeHost()
    J.iptables_handler(job(101, arg_1="eth0"), host)
    assert host.calls == ["iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE"]
    J.iptables_handler(job(101, arg_1="Eth0"), host)
    assert len(host.calls) == 1


def test_port_forwarding_tcp_handler():
    host = FakeHost()
    J.port_forwarding_tcp_handler(
        job(109, arg_1="eth0", arg_2="8080", arg_3="10.0.0.5", arg_4="80"), host
    )
    assert host.calls == [
        "iptables -t nat -A PREROUTING -p tcp -i eth0 --dport 8080 -j DNAT --to-destination 10.0.0.5:80"
    ]
    J.port_forwarding_tcp_handler(
        job(109, arg_1="eth0", arg_2="abc", arg_3="10.0.0.5", arg_4="80"), host
    )
    assert len(host.calls) == 1


def test_port_forwarding_udp_handler():
    host = FakeHost()
    J.port_forwarding_udp_handler(
        job(110, arg_1="eth0", arg_2="8080", arg_3="10.0.0.5", arg_4="80"), host
    )
    assert host.calls == [
        "iptables -t nat -A PREROUTING -p udp -i eth0 --dport 8080 -j DNAT --to-destination 10.0.0.5:80"
    ]


def test_ip_route_add_handler():
    host = FakeHost()
    J.ip_route_add_handler(
        job(102, arg_1="10.0.0.0", arg_2="24", arg_3="10.0.0.1"), host
    )
    assert host.calls == ["ip route add 10.0.0.0/24 via 10.0.0.1"]
    J.ip_route_add_handler(job(102, arg_1="bad", arg_2="24", arg_3="10.0.0.1"), host)
    assert len(host.calls) == 1


def test_block_tcp_udp_port():
    host = FakeHost()
    J.block_tcp_udp_port(job(202, arg_1="8080"), host)
    assert host.calls == [
        "iptables -A INPUT -p tcp --dport 8080 -j DROP",
        "iptables -A INPUT -p udp --dport 8080 -j DROP",
    ]
    J.block_tcp_udp_port(job(202, arg_1="abc"), host)
    assert len(host.calls) == 2


def test_open_tcp_server_handler():
    host = FakeHost()
    J.open_tcp_server_handler(job(201, arg_1="10.0.0.1", arg_2="8080"), host)
    assert host.calls == [
        "nohup nc -k -d 10.0.0.1 -l 8080 > /tmp/tcpserver 2>&1 < /dev/null &"
    ]
    J.open_tcp_server_handler(job(201, arg_1="bad", arg_2="8080"), host)
    assert len(host.calls) == 1


def test_open_udp_server_handler():
    host = FakeHost()
    J.open_udp_server_handler(job(200, arg_1="10.0.0.1", arg_2="8080"), host)
    assert host.calls == [
        "nohup nc -d -u 10.0.0.1 -l 8080 > /tmp/udpserver 2>&1 < /dev/null &"
    ]


def test_arp_handler():
    host = FakeHost()
    J.arp_handler(job(103, arg_1="10.0.0.1", arg_2="00:11:22:33:44:55"), host)
    assert host.calls == ["arp -s 10.0.0.1 00:11:22:33:44:55"]
    J.arp_handler(job(103, arg_1="10.0.0.1", arg_2="bad"), host)
    assert len(host.calls) == 1


def test_subinterface_with_vlan():
    host = FakeHost()
    J.subinterface_with_vlan(
        job(104, arg_1="sw001-eth0", arg_2="10.0.0.1", arg_3="24", arg_4=10), host
    )
    assert host.calls == [
        "ip link add link sw001-eth0 name eth0.10 type vlan id 10",
        "ip addr add 10.0.0.1/24 dev eth0.10",
        "ip link set dev eth0.10 up",
    ]
    J.subinterface_with_vlan(
        job(104, arg_1="Eth0", arg_2="10.0.0.1", arg_3="24", arg_4=10), host
    )
    assert len(host.calls) == 3


def test_add_ipip_interface():
    host = FakeHost()
    J.add_ipip_interface(
        job(105, arg_1="10.0.0.1", arg_2="10.0.0.2", arg_3="10.0.0.3", arg_4="tun0"),
        host,
    )
    assert host.calls == [
        "ip tunnel add tun0 mode ipip remote 10.0.0.2 local 10.0.0.1",
        "ifconfig tun0 10.0.0.3",
    ]
    J.add_ipip_interface(
        job(105, arg_1="10.0.0.1", arg_2="10.0.0.2", arg_3="10.0.0.3", arg_4="Tun0"),
        host,
    )
    assert len(host.calls) == 2


def test_add_gre():
    host = FakeHost()
    J.add_gre(
        job(106, arg_1="10.0.0.1", arg_2="10.0.0.2", arg_3="10.0.0.3", arg_4="gre0"),
        host,
    )
    assert host.calls == [
        "ip tunnel add gre0 mode gre remote 10.0.0.2 local 10.0.0.1 ttl 255",
        "ip addr add 10.0.0.3/24 dev gre0",
        "ip link set gre0 up",
    ]
    J.add_gre(
        job(106, arg_1="10.0.0.1", arg_2="10.0.0.2", arg_3="10.0.0.3", arg_4="Gre0"),
        host,
    )
    assert len(host.calls) == 3


def test_arp_proxy_enable():
    host = FakeHost()
    J.arp_proxy_enable(job(107, arg_1="eth0"), host)
    assert host.calls == ["sysctl -w net.ipv4.conf.eth0.proxy_arp=1"]
    J.arp_proxy_enable(job(107, arg_1="Eth0"), host)
    assert len(host.calls) == 1


def test_jobs_dispatch_ping():
    host = FakeHost()
    j = J.Jobs(job(1, arg_1="10.0.0.1"), host)
    assert j.strategy is J.ping_handler
    j.handler()
    assert host.calls == ["ping -c 1 10.0.0.1"]


def test_jobs_strategy_setter():
    host = FakeHost()
    j = J.Jobs(job(1, arg_1="10.0.0.1"), host)
    j.strategy = 100
    assert j.strategy is J.ip_addr_add_handler


def test_jobs_unknown_job_id_raises():
    with pytest.raises(KeyError):
        J.Jobs(job(999), FakeHost())
