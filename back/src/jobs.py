import re
from typing import Any, Callable

from network_schema import Job

from typing import Any, Callable, Optional, Tuple


def ping_handler(job: Job, job_host: Any) -> None:
    """Execute ping -c 1"""
    arg_ip = job.arg_1
    job_host.cmd(f"ping -c 1 {arg_ip}")


def ping_with_options_handler(job: Job, job_host: Any) -> None:
    """Execute ping with options"""

    arg_opt = job.arg_1
    arg_ip = job.arg_2

    if len(arg_opt) > 0:
        arg_opt = re.sub(r"[^\x00-\x7F]", "", str(arg_opt))
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

    job_host.cmd(
        f"dd if=/dev/urandom bs={arg_size} count=1 | nc -uq1 {arg_ip} {arg_port}"
    )


def sending_tcp_data_handler(job: Job, job_host: Any) -> None:
    """Method for sending TCP data sending"""

    arg_size, arg_ip, arg_port = get_sending_data_argument(job)

    job_host.cmd(
        f"dd if=/dev/urandom bs={arg_size} count=1 | nc -w 30 -q1 {arg_ip} {arg_port}"
    )


def traceroute_handler(job: Job, job_host: Any) -> None:
    """Method for executing traceroute"""

    arg_opt = job.arg_1
    arg_ip = job.arg_2

    if len(arg_opt) > 0:
        arg_opt = re.sub(r"[^\x00-\x7F]", "", str(arg_opt))

    job_host.cmd(f"traceroute -n {arg_opt} {arg_ip}")


def ip_addr_add_handler(job: Job, job_host: Any) -> None:
    """Method for executing ip addr add"""

    arg_ip = job.arg_2
    arg_mask = job.arg_3
    arg_dev = job.arg_1

    if arg_ip is None or arg_dev is None:
        return

    job_host.cmd(f"ip addr add {arg_ip}/{arg_mask} dev {arg_dev}")


def iptables_handler(job: Job, job_host: Any) -> None:
    """Method for adding forwarding rule"""

    arg_dev = job.arg_1

    if not arg_dev:
        return

    job_host.cmd(f"iptables -t nat -A POSTROUTING -o {arg_dev} -j MASQUERADE")


def ip_route_add_handler(job: Job, job_host: Any) -> None:
    """Method for executing ip route add"""
    arg_ip = job.arg_1
    arg_mask = job.arg_2
    arg_router = job.arg_3

    job_host.cmd(f"ip route add {arg_ip}/{arg_mask} via {arg_router}")


def block_tcp_udp_port(job: Job, job_host: Any) -> None:
    """ "Method for executing Block TCP/UDP port"""
    arg_port = job.arg_1

    job_host.cmd(f"iptables -A INPUT -p tcp --dport {arg_port} -j DROP")
    job_host.cmd(f"iptables -A INPUT -p udp --dport {arg_port} -j DROP")


def open_tcp_server_handler(job: Job, job_host: Any) -> None:
    """ "Method for open tcp server"""
    arg_ip = job.arg_1
    arg_port = job.arg_2

    job_host.cmd(
        f"nohup nc -k -d {arg_ip} -l {arg_port} > /tmp/tcpserver 2>&1 < /dev/null &"
    )


def open_udp_server_handler(job: Job, job_host: Any) -> None:
    """ "Method for open udp server"""
    arg_ip = job.arg_1
    arg_port = job.arg_2

    job_host.cmd(
        f"nohup nc -d -u {arg_ip} -l {arg_port} > /tmp/udpserver 2>&1 < /dev/null &"
    )


def arp_handler(job: Job, job_host: Any) -> None:
    """ "Method for executing arp -s"""
    arg_ip = job.arg_1
    arg_mac = job.arg_2

    job_host.cmd(f"arp -s {arg_ip} {arg_mac}")


def subinterface_with_vlan(job: Job, job_host: Any) -> None:
    """Method for adding subinterface with vlan"""
    arg_intf = job.arg_1
    arg_ip = job.arg_2
    arg_mask = job.arg_3
    arg_vlan = job.arg_4
    arg_intf_name = arg_intf[6:]

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

    job_host.cmd(
        f"ip tunnel add {arg_name_int} mode ipip remote {arg_ip_end} local {arg_ip_start}"
    )
    job_host.cmd(f"ifconfig {arg_name_int} {arg_ip_int}")


def add_gre(job: Job, job_host: Any) -> None:
    arg_ip_start = job.arg_1
    arg_ip_end = job.arg_2
    arg_ip_iface = job.arg_3  # New virtual interface (IP)
    arg_name_iface = job.arg_4  # New virtual interface (Name) + TTL value

    job_host.cmd(
        f"ip tunnel add {arg_name_iface} mode gre remote {arg_ip_end} local {arg_ip_start} ttl 255"
    )
    job_host.cmd(f"ip addr add {arg_ip_iface}/24 dev {arg_name_iface}")
    job_host.cmd(f"ip link set {arg_name_iface} up")


def arp_proxy_enable(job: Job, job_host: Any) -> None:
    """Enable ARP proxying on the interface"""
    arg_iface = job.arg_1

    job_host.cmd(f"sysctl -w net.ipv4.conf.{arg_iface}.proxy_arp=1")


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
            100: ip_addr_add_handler,
            101: iptables_handler,
            102: ip_route_add_handler,
            103: arp_handler,
            104: subinterface_with_vlan,
            105: add_ipip_interface,
            106: add_gre,
            107: arp_proxy_enable,
            200: open_udp_server_handler,
            201: open_tcp_server_handler,
            202: block_tcp_udp_port,
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



 



def ping_handler(job: Job, job_host: Any) -> None:
    arg_ip = job.arg_1
    job_host.cmd(f"ping -c 1 {arg_ip}")


def ping_with_options_handler(job: Job, job_host: Any) -> None:
    arg_opt = job.arg_1
    arg_ip = job.arg_2

    if arg_opt:
        arg_opt = re.sub(r"[^\x00-\x7F]", "", str(arg_opt))
    job_host.cmd(f"ping -c 1 {arg_opt} {arg_ip}")


def get_sending_data_argument(job: Job) -> Tuple[str | int, str | int, str | int]:
    arg_size = job.arg_1
    arg_ip = job.arg_2
    arg_port = job.arg_3
    return arg_size, arg_ip, arg_port


def sending_udp_data_handler(job: Job, job_host: Any) -> None:
    arg_size, arg_ip, arg_port = get_sending_data_argument(job)
    job_host.cmd(f"dd if=/dev/urandom bs={arg_size} count=1 | nc -uq1 {arg_ip} {arg_port}")


def sending_tcp_data_handler(job: Job, job_host: Any) -> None:
    arg_size, arg_ip, arg_port = get_sending_data_argument(job)
    job_host.cmd(f"dd if=/dev/urandom bs={arg_size} count=1 | nc -w 30 -q1 {arg_ip} {arg_port}")


def traceroute_handler(job: Job, job_host: Any) -> None:
    arg_opt = job.arg_1
    arg_ip = job.arg_2

    if arg_opt:
        arg_opt = re.sub(r"[^\x00-\x7F]", "", str(arg_opt))
    job_host.cmd(f"traceroute -n {arg_opt} {arg_ip}")


def ip_addr_add_handler(job: Job, job_host: Any) -> None:
    arg_dev = job.arg_1
    arg_ip = job.arg_2
    arg_mask = job.arg_3

    if arg_dev is None or arg_ip is None or arg_mask is None:
        return

    job_host.cmd(f"ip addr add {arg_ip}/{arg_mask} dev {arg_dev}")


def iptables_handler(job: Job, job_host: Any) -> None:
    arg_dev = job.arg_1
    if not arg_dev:
        return
    job_host.cmd(f"iptables -t nat -A POSTROUTING -o {arg_dev} -j MASQUERADE")


def ip_route_add_handler(job: Job, job_host: Any) -> None:
    arg_ip = job.arg_1
    arg_mask = job.arg_2
    arg_router = job.arg_3
    job_host.cmd(f"ip route add {arg_ip}/{arg_mask} via {arg_router}")


def block_tcp_udp_port(job: Job, job_host: Any) -> None:
    arg_port = job.arg_1
    job_host.cmd(f"iptables -A INPUT -p tcp --dport {arg_port} -j DROP")
    job_host.cmd(f"iptables -A INPUT -p udp --dport {arg_port} -j DROP")


def open_tcp_server_handler(job: Job, job_host: Any) -> None:
    arg_ip = job.arg_1
    arg_port = job.arg_2
    job_host.cmd(f"nohup nc -k -d {arg_ip} -l {arg_port} > /tmp/tcpserver 2>&1 < /dev/null &")


def open_udp_server_handler(job: Job, job_host: Any) -> None:
    arg_ip = job.arg_1
    arg_port = job.arg_2
    job_host.cmd(f"nohup nc -d -u {arg_ip} -l {arg_port} > /tmp/udpserver 2>&1 < /dev/null &")


def arp_handler(job: Job, job_host: Any) -> None:
    arg_ip = job.arg_1
    arg_mac = job.arg_2
    job_host.cmd(f"arp -s {arg_ip} {arg_mac}")


def subinterface_with_vlan(job: Job, job_host: Any) -> None:
    arg_intf = job.arg_1
    arg_ip = job.arg_2
    arg_mask = job.arg_3
    arg_vlan = job.arg_4
    arg_intf_name = arg_intf[6:]

    job_host.cmd(f"ip link add link {arg_intf} name {arg_intf_name}.{arg_vlan} type vlan id {arg_vlan}")
    job_host.cmd(f"ip addr add {arg_ip}/{arg_mask} dev {arg_intf_name}.{arg_vlan}")
    job_host.cmd(f"ip link set dev {arg_intf_name}.{arg_vlan} up")


def add_ipip_interface(job: Job, job_host: Any) -> None:
    arg_ip_start = job.arg_1
    arg_ip_end = job.arg_2
    arg_ip_int = job.arg_3
    arg_name_int = job.arg_4

    job_host.cmd(f"ip tunnel add {arg_name_int} mode ipip remote {arg_ip_end} local {arg_ip_start}")
    job_host.cmd(f"ifconfig {arg_name_int} {arg_ip_int}")


def add_gre(job: Job, job_host: Any) -> None:
    arg_ip_start = job.arg_1
    arg_ip_end = job.arg_2
    arg_ip_iface = job.arg_3
    arg_name_iface = job.arg_4

    job_host.cmd(f"ip tunnel add {arg_name_iface} mode gre remote {arg_ip_end} local {arg_ip_start} ttl 255")
    job_host.cmd(f"ip addr add {arg_ip_iface}/24 dev {arg_name_iface}")
    job_host.cmd(f"ip link set {arg_name_iface} up")


def arp_proxy_enable(job: Job, job_host: Any) -> None:
    arg_iface = job.arg_1
    job_host.cmd(f"sysctl -w net.ipv4.conf.{arg_iface}.proxy_arp=1")


# -----------------------
# Jobs class
# -----------------------

class Jobs:
    def __init__(self, job: Job, job_host: Any, **kwargs) -> None:
        self._dct: dict[int, Callable[[Job, Any], None]] = {
            1: ping_handler,
            2: ping_with_options_handler,
            3: sending_udp_data_handler,
            4: sending_tcp_data_handler,
            5: traceroute_handler,
            100: ip_addr_add_handler,
            101: iptables_handler,
            102: ip_route_add_handler,
            103: arp_handler,
            104: subinterface_with_vlan,
            105: add_ipip_interface,
            106: add_gre,
            107: arp_proxy_enable,
            200: open_udp_server_handler,
            201: open_tcp_server_handler,
            202: block_tcp_udp_port,
        }
        self._job: Job = job
        self._job_host = job_host
        self._strategy: Callable[[Job, Any], None] = self._dct[self._job.job_id]

    @property
    def strategy(self) -> Callable[[Job, Any], None]:
        return self._strategy

    @strategy.setter
    def strategy(self, job_id: int) -> None:
        self._strategy = self._dct[job_id]

    def handler(self) -> None:
        self._strategy(self._job, self._job_host)


# -----------------------
# VLAN / ARP helpers
# -----------------------

def create_vlan_subinterface(
    job_host: Any, parent: str, vlan: int, ip: Optional[str] = None, mask: Optional[int] = None
) -> str:
    sub_intf = f"{parent}.{vlan}"
    job_host.cmd(f"ip link del {sub_intf} 2>/dev/null || true")
    job_host.cmd(f"ip link add link {parent} name {sub_intf} type vlan id {vlan}")
    job_host.cmd(f"ip link set dev {sub_intf} up")
    if ip is not None and mask is not None:
        job_host.cmd(f"ip addr add {ip}/{mask} dev {sub_intf}")
    return sub_intf


def enable_arp_proxy(job: Job, job_host: Any) -> None:
    arg_iface = job.arg_1
    sub_intf = arg_iface

    if "." not in arg_iface:
        vlan = int(job.arg_2)
        ip = job.arg_3
        mask = job.arg_4
        sub_intf = create_vlan_subinterface(job_host, arg_iface, vlan, ip, mask)

    job_host.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.proxy_arp=1")
    job_host.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.forwarding=1")
    job_host.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.arp_ignore=0")
    job_host.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.arp_announce=0")

    parent = sub_intf.split(".")[0]
    job_host.cmd(f"sysctl -w net.ipv4.conf.{parent}.proxy_arp=1")
    job_host.cmd(f"sysctl -w net.ipv4.conf.{parent}.forwarding=1")

    print(f"[OK] ARP Proxy enabled on {sub_intf} (parent={parent})")


# -----------------------
# Optional renamed configure_access to avoid mypy redefinition
# -----------------------

def configure_access_vlan(
    switch: IPSwitch, intf: str, vlan: int, ip: Optional[str] = None, mask: Optional[int] = None
) -> None:
    sub_intf = f"{intf}.{vlan}"
    switch.cmd(f"ip link add link {intf} name {sub_intf} type vlan id {vlan}")
    switch.cmd(f"ip link set {sub_intf} up")
    if ip is not None and mask is not None:
        switch.cmd(f"ip addr add {ip}/{mask} dev {sub_intf}")
    switch.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.proxy_arp=1")
    switch.cmd(f"sysctl -w net.ipv4.conf.{sub_intf}.forwarding=1")
