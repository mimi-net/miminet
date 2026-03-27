import re
import shlex
import ipaddress
import time
from netaddr import EUI, AddrFormatError
from typing import Any, Callable, List, Dict
from network_schema import Job
from mininet.log import info
from ipmininet.host.config.dnsmasq import Dnsmasq


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
    flags_with_args = {
        "-c": r"([1-9]|10)",
        "-t": r"\d+",
        "-i": r"\d+",
        "-s": r"\d+",
        "-l": r"\d+",
    }

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


def udp_tcp_args_checker(ip, size, port) -> bool:
    """Check all args in tcp and udp data handler on correct"""
    if not valid_ip(ip):
        return False

    try:
        _ = int(size)
        _ = int(port)
    except (ValueError, TypeError):
        return False

    return True


def net_dev_checker(dev) -> bool:
    """Checker for net interface"""
    if not re.match(r"^[a-z][a-z0-9:_\-\.]{,14}$", dev):
        return False
    return True


def ip_addr_add_checker(ip, mask, dev) -> bool:
    """Checker all args in ip addr add job"""

    if not valid_ip(ip):
        return False

    try:
        _ = int(mask)
    except (ValueError, TypeError):
        return False
    if not net_dev_checker(dev):
        return False
    return True


def ip_route_add_checker(ip, mask, router) -> bool:
    """Checker all args in ip route add job"""

    if not valid_ip(ip):
        return False

    try:
        _ = int(mask)
    except (ValueError, TypeError):
        return False

    if not valid_ip(router):
        return False

    return True


def subinterface_vlan_checker(intf, ip, mask, vlan, intf_name) -> bool:
    """Checker for subinterface_vlan args"""

    if not net_dev_checker(intf):
        return False

    if not valid_ip(ip):
        return False

    try:
        _ = int(mask)
        _ = int(vlan)
    except (ValueError, TypeError):
        return False

    if not intf_name:
        return False

    return True


def ipip_interface_checker(ip_start, ip_end, ip_int, name_int) -> bool:
    """Checker args for ipip_interface"""

    if not valid_ip(ip_start) or not valid_ip(ip_end) or not valid_ip(ip_int):
        return False

    if not valid_iface(name_int):
        return False

    return True


def add_gre_checker(ip_start, ip_end, ip_iface, name_iface) -> bool:
    """Checker args for add_gre"""

    if not valid_ip(ip_start) or not valid_ip(ip_iface) or not valid_ip(ip_end):
        return False

    if not valid_iface(name_iface):
        return False

    return True


def port_forwarding_checker(iface, port, dest_addr, dest_port) -> bool:
    """Checker args for port_forwarding_tcp and port_forwarding_udp"""

    return (
        valid_ip(dest_addr)
        and valid_port(port)
        and valid_port(dest_port)
        and valid_iface(iface)
    )


def valid_port(port) -> bool:
    """Check if given arg is port or not"""
    try:
        _ = int(port)
    except (ValueError, TypeError):
        return False

    return True


def valid_ip(ip) -> bool:
    """Check if given arg is ip or not"""

    try:
        ipaddress.ip_address(str(ip))
        return True
    except ValueError:
        return False


def valid_mac(mac) -> bool:
    """Check if given arg is mac or not"""
    try:
        EUI(mac)
    except AddrFormatError:
        return False

    return True


def valid_iface(iface) -> bool:
    """Check if arg have only valid symbols for iface"""
    if not re.match(r"^[a-z][a-z0-9_-]{0,14}$", iface):
        return False
    return True


def valid_sleep(time) -> bool:
    try:
        _ = int(time)
    except (ValueError, TypeError):
        return False
    if int(time) > 50 or int(time) <= 0:
        return False

    return True


def link_down_handler(job: Job, job_host: Any) -> None:
    arg_interface = job.arg_1
    if not net_dev_checker(arg_interface):
        return
    job_host.cmd(f"ip link set {arg_interface} down")


def sleep_handler(job: Job, job_host: Any) -> None:
    arg_time = job.arg_1
    if not valid_sleep(arg_time):
        return
    time.sleep(int(arg_time))


def ping_handler(job: Job, job_host: Any) -> None:
    """Execute ping -c 1"""
    arg_ip = job.arg_1

    if not valid_ip(arg_ip):
        return

    job_host.cmd(f"ping -c 1 {arg_ip}")


def ping_with_options_handler(job: Job, job_host: Any) -> None:
    """Execute ping with options"""

    arg_opt = job.arg_1
    arg_ip = job.arg_2

    if not valid_ip(arg_ip):
        return

    if len(arg_opt) > 0:
        arg_opt = ping_options_filter(arg_opt)

    job_host.cmd(f"ping -c 1 {arg_opt} {arg_ip}")


def get_sending_data_argument(job: Job) -> tuple[str | int, str | int, str | int]:
    """Method for get arguments for sending udp and tcp data"""

    arg_size = job.arg_1
    arg_ip = job.arg_2
    arg_port = job.arg_3

    return arg_size, arg_ip, arg_port


def sending_udp_data_handler(job: Job, job_host: Any) -> None:
    """Method for sending UDP data"""

    arg_size, arg_ip, arg_port = get_sending_data_argument(job)

    if not udp_tcp_args_checker(arg_ip, arg_size, arg_port):
        return

    job_host.cmd(
        f"dd if=/dev/urandom bs={arg_size} count=1 | nc -uq1 {arg_ip} {arg_port}"
    )


def sending_tcp_data_handler(job: Job, job_host: Any) -> None:
    """Method for sending TCP data sending"""

    arg_size, arg_ip, arg_port = get_sending_data_argument(job)

    if not udp_tcp_args_checker(arg_ip, arg_size, arg_port):
        return

    job_host.cmd(
        f"dd if=/dev/urandom bs={arg_size} count=1 | nc -w 30 -q1 {arg_ip} {arg_port}"
    )


def traceroute_handler(job: Job, job_host: Any) -> None:
    """Method for executing traceroute"""

    arg_opt = job.arg_1
    arg_ip = job.arg_2

    if not valid_ip(arg_ip):
        return

    if len(arg_opt) > 0:
        arg_opt = traceroute_options_filter(arg_opt)

    job_host.cmd(f"traceroute -n {arg_opt} {arg_ip}")


def ip_addr_add_handler(job: Job, job_host: Any) -> None:
    """Method for executing ip addr add"""

    arg_ip = job.arg_2
    arg_mask = job.arg_3
    arg_dev = job.arg_1

    if not ip_addr_add_checker(arg_ip, arg_mask, arg_dev):
        return

    job_host.cmd(f"ip addr add {arg_ip}/{arg_mask} dev {arg_dev}")


def iptables_handler(job: Job, job_host: Any) -> None:
    """Method for adding forwarding rule"""

    arg_dev = job.arg_1

    if not net_dev_checker(arg_dev):
        return

    job_host.cmd(f"iptables -t nat -A POSTROUTING -o {arg_dev} -j MASQUERADE")


def port_forwarding_tcp_handler(job: Job, job_host: Any) -> None:
    """Method for adding tcp port forwarding"""

    arg_iface = job.arg_1
    arg_port = job.arg_2
    arg_dest_addr = job.arg_3
    arg_dest_port = job.arg_4

    if not port_forwarding_checker(arg_iface, arg_port, arg_dest_addr, arg_dest_port):
        return

    job_host.cmd(
        f"iptables -t nat -A PREROUTING -p tcp -i {arg_iface} --dport {arg_port} -j DNAT --to-destination {arg_dest_addr}:{arg_dest_port}"
    )


def port_forwarding_udp_handler(job: Job, job_host: Any) -> None:
    """Method for adding udp port forwarding"""

    arg_iface = job.arg_1
    arg_port = job.arg_2
    arg_dest_addr = job.arg_3
    arg_dest_port = job.arg_4

    if not port_forwarding_checker(arg_iface, arg_port, arg_dest_addr, arg_dest_port):
        return

    job_host.cmd(
        f"iptables -t nat -A PREROUTING -p udp -i {arg_iface} --dport {arg_port} -j DNAT --to-destination {arg_dest_addr}:{arg_dest_port}"
    )


def ip_route_add_handler(job: Job, job_host: Any) -> None:
    """Method for executing ip route add"""
    arg_ip = job.arg_1
    arg_mask = job.arg_2
    arg_router = job.arg_3

    if not ip_route_add_checker(arg_ip, arg_mask, arg_router):
        return

    job_host.cmd(f"ip route add {arg_ip}/{arg_mask} via {arg_router}")


def block_tcp_udp_port(job: Job, job_host: Any) -> None:
    """ "Method for executing Block TCP/UDP port"""
    arg_port = job.arg_1

    if not valid_port(arg_port):
        return

    job_host.cmd(f"iptables -A INPUT -p tcp --dport {arg_port} -j DROP")
    job_host.cmd(f"iptables -A INPUT -p udp --dport {arg_port} -j DROP")


def open_tcp_server_handler(job: Job, job_host: Any) -> None:
    """ "Method for open tcp server"""
    arg_ip = job.arg_1
    arg_port = job.arg_2

    if not valid_port(arg_port) or not valid_ip(arg_ip):
        return

    job_host.cmd(
        f"nohup nc -k -d {arg_ip} -l {arg_port} > /tmp/tcpserver 2>&1 < /dev/null &"
    )


def open_udp_server_handler(job: Job, job_host: Any) -> None:
    """ "Method for open udp server"""
    arg_ip = job.arg_1
    arg_port = job.arg_2

    if not valid_ip(arg_ip) or not valid_port(arg_port):
        return

    job_host.cmd(
        f"nohup nc -d -u {arg_ip} -l {arg_port} > /tmp/udpserver 2>&1 < /dev/null &"
    )


def arp_handler(job: Job, job_host: Any) -> None:
    """ "Method for executing arp -s"""
    arg_ip = job.arg_1
    arg_mac = job.arg_2

    if not valid_ip(arg_ip) or not valid_mac(arg_mac):
        return

    job_host.cmd(f"arp -s {arg_ip} {arg_mac}")


def subinterface_with_vlan(job: Job, job_host: Any) -> None:
    """Method for adding subinterface with vlan"""
    arg_intf = job.arg_1
    arg_ip = job.arg_2
    arg_mask = job.arg_3
    arg_vlan = job.arg_4
    arg_intf_name = arg_intf[6:]

    if not subinterface_vlan_checker(
        arg_intf, arg_ip, arg_mask, arg_vlan, arg_intf_name
    ):
        return

    job_host.cmd(
        f"ip link add link {arg_intf} name {arg_intf_name}.{arg_vlan} type vlan id {arg_vlan}"
    )
    job_host.cmd(f"ip addr add {arg_ip}/{arg_mask} dev {arg_intf_name}.{arg_vlan}")
    job_host.cmd(f"ip link set dev {arg_intf_name}.{arg_vlan} up")


def add_ipip_interface(job: Job, job_host: Any) -> None:
    """Method for adding ipip-interface"""
    arg_ip_start = job.arg_1
    arg_ip_end = job.arg_2
    arg_ip_int = job.arg_3
    arg_name_int = job.arg_4

    if not ipip_interface_checker(arg_ip_start, arg_ip_end, arg_ip_int, arg_name_int):
        return

    job_host.cmd(
        f"ip tunnel add {arg_name_int} mode ipip remote {arg_ip_end} local {arg_ip_start}"
    )
    job_host.cmd(f"ifconfig {arg_name_int} {arg_ip_int}")


def add_gre(job: Job, job_host: Any) -> None:
    arg_ip_start = job.arg_1
    arg_ip_end = job.arg_2
    arg_ip_iface = job.arg_3  # New virtual interface (IP)
    arg_name_iface = job.arg_4  # New virtual interface (Name) + TTL value

    if not add_gre_checker(arg_ip_start, arg_ip_end, arg_ip_iface, arg_name_iface):
        return

    job_host.cmd(
        f"ip tunnel add {arg_name_iface} mode gre remote {arg_ip_end} local {arg_ip_start} ttl 255"
    )
    job_host.cmd(f"ip addr add {arg_ip_iface}/24 dev {arg_name_iface}")
    job_host.cmd(f"ip link set {arg_name_iface} up")


def arp_proxy_enable(job: Job, job_host: Any) -> None:
    """Enable ARP proxying on the interface"""
    arg_iface = job.arg_1

    if not valid_iface(arg_iface):
        return

    job_host.cmd(f"sysctl -w net.ipv4.conf.{arg_iface}.proxy_arp=1")


def dhcp_client(job: Job, job_host):
    job_host.cmd(f"ifconfig {job.arg_1} 0")
    job_host.cmd("rm /var/lib/dhcp/dhclient.leases")
    job_host.cmd("echo 'initial-interval 6;' > /tmp/dhclient.conf")
    out = job_host.cmd(
        f"timeout -k 1 5 dhclient -d -v -4 -cf /tmp/dhclient.conf {job.arg_1} && "
        + "ip route show && rm -f /tmp/dhclient.conf"
    )
    info(out)


def dhcp_server(job: Job, job_host):
    ip_range_start = job.arg_1
    ip_range_end = job.arg_2
    mask = job.arg_3
    gw = job.arg_4
    intfs = [job.arg_5]
    daemon = Dnsmasq(
        node=job_host,
        ip_range=f"{ip_range_start},{ip_range_end}",
        mask=mask,
        gw=gw,
        intfs=intfs,
    )
    job_host.build_daemon(daemon)
    job_host.start_daemon(daemon)


class Jobs:
    """Class for representing various commands for working with miminet network"""

    def __init__(self, job: Job, job_host: Any, **kwargs) -> None:
        """
        Args:
            job (Job): What type of Job we should execute.
            job_host (Any): Host for which the job is performed.
        """
        # Dictionary for storing strategies
        # (At the moment this is used since each command on the application server is encoded by a number)
        self._dct: dict[int, Callable[[Job, Any], None]] = {
            1: ping_handler,
            2: ping_with_options_handler,
            3: sending_udp_data_handler,
            4: sending_tcp_data_handler,
            5: traceroute_handler,
            6: link_down_handler,
            7: sleep_handler,
            100: ip_addr_add_handler,
            101: iptables_handler,
            102: ip_route_add_handler,
            103: arp_handler,
            104: subinterface_with_vlan,
            105: add_ipip_interface,
            106: add_gre,
            107: arp_proxy_enable,
            108: dhcp_client,
            109: port_forwarding_tcp_handler,
            110: port_forwarding_udp_handler,
            200: open_udp_server_handler,
            201: open_tcp_server_handler,
            202: block_tcp_udp_port,
            203: dhcp_server,
        }
        self._job: Job = job
        self._job_host = job_host
        self._strategy: Callable[[Job, Any], None] = self._dct[self._job.job_id]

    @property
    def strategy(self) -> Callable[[Job, Any], None]:
        """Get current strategy

        Returns:
            JobsStrategy: current strategy
        """

        return self._strategy

    @strategy.setter
    def strategy(self, job_id: int) -> None:
        """Change the execution strategy

        Args:
            job_id (int): id for change job strategy

        """
        self._strategy = self._dct[job_id]

    def handler(self) -> None:
        self._strategy(self._job, self._job_host)
