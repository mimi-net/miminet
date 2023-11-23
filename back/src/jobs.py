import re
import typing

from network import Job


def ping_handler(job: Job, job_host) -> None:
    """Execute ping -c 1"""
    arg1 = job.arg_1
    job_host.cmd("ping -c 1 " + str(arg1))


def ping_with_options_handler(job: Job, job_host) -> None:
    """Execute ping with options"""

    arg_opt = job.arg_1
    arg_ip = job.arg_2

    if len(arg_opt) > 0:
        arg_opt = re.sub(r"[^\x00-\x7F]", "", str(arg_opt))
    job_host.cmd("ping -c 1 " + str(arg_opt) + " " + str(arg_ip))


def get_sending_data_argument(job: Job) -> tuple[str | int, str | int, str | int]:
    """Method for get arguments for sending udp and tcp data"""

    arg_size = job.arg_1
    arg_ip = job.arg_2
    arg_port = job.arg_3

    return arg_size, arg_ip, arg_port


def sending_udp_data_handler(job: Job, job_host) -> None:
    """Method for sending UDP data"""

    arg_size, arg_ip, arg_port = get_sending_data_argument(job)

    job_host.cmd(
        "dd if=/dev/urandom bs="
        + str(arg_size)
        + " count=1 | nc -uq1 "
        + str(arg_ip)
        + " "
        + str(arg_port)
    )


def sending_tcp_data_handler(job: Job, job_host) -> None:
    """Method for sending TCP data sending"""

    arg_size, arg_ip, arg_port = get_sending_data_argument(job)

    job_host.cmd(
        "dd if=/dev/urandom bs="
        + str(arg_size)
        + " count=1 | nc -w 30 -q1 "
        + str(arg_ip)
        + " "
        + str(arg_port)
    )


def traceroute_handler(job: Job, job_host) -> None:
    """Method for executing traceroute"""

    arg_opt = job.arg_1
    arg_ip = job.arg_2

    if len(arg_opt) > 0:
        arg_opt = re.sub(r"[^\x00-\x7F]", "", str(arg_opt))

    job_host.cmd("traceroute -n " + str(arg_opt) + " " + str(arg_ip))


def ip_addr_add_handler(job: Job, job_host) -> None:
    """Method for executing ip addr add"""

    arg_ip = job.arg_2
    arg_mask = job.arg_3
    arg_dev = job.arg_1

    if arg_ip is None or arg_dev is None:
        return

    job_host.cmd(
        "ip addr add " + str(arg_ip) + "/" + str(arg_mask) + " dev " + str(arg_dev)
    )


def iptables_handler(job: Job, job_host) -> None:
    """Method for adding forwarding rule"""

    arg_dev = job.arg_1

    if not arg_dev:
        return

    job_host.cmd("iptables -t nat -A POSTROUTING -o ", arg_dev, "-j MASQUERADE")


def ip_route_add_handler(job: Job, job_host) -> None:
    """Method for executing ip route add"""
    arg_ip = job.arg_1
    arg_mask = job.arg_2
    arg_router = job.arg_3

    job_host.cmd(
        "ip route add " + str(arg_ip) + "/" + str(arg_mask) + " via " + str(arg_router)
    )


def block_tcp_udp_port(job: Job, job_host) -> None:
    """ "Method for executing Block TCP/UDP port"""
    arg_port = job.arg_1

    job_host.cmd("iptables -A INPUT -p tcp --dport " + str(arg_port) + " -j DROP")
    job_host.cmd("iptables -A INPUT -p udp --dport " + str(arg_port) + " -j DROP")


def open_tcp_server_handler(job: Job, job_host) -> None:
    """ "Method for open tcp server"""
    arg_ip = job.arg_1
    arg_port = job.arg_2

    job_host.cmd(
        "nohup nc -k -d "
        + str(arg_ip)
        + " -l "
        + str(arg_port)
        + " > /tmp/tcpserver 2>&1 < /dev/null &"
    )


def open_udp_server_handler(job: Job, job_host) -> None:
    """ "Method for open udp server"""
    arg_ip = job.arg_1
    arg_port = job.arg_2

    job_host.cmd(
        "nohup nc -d -u "
        + str(arg_ip)
        + " -l "
        + str(arg_port)
        + " > /tmp/udpserver 2>&1 < /dev/null &"
    )


def arp_handler(job: Job, job_host):
    """ "Method for executing arp -s"""
    arg_ip = job.arg_1
    arg_mac = job.arg_2

    job_host.cmd("arp -s " + str(arg_ip) + " " + str(arg_mac))


class Jobs:
    """Class for representing various commands for working with miminet network"""

    def __init__(self, job, job_host, **kwargs):
        # Dictionary for storing strategies
        # (At the moment this is used since each command on the application server is encoded by a number)
        self._dct: dict[int, typing.Callable[[Job, typing.Any], None]] = {
            1: ping_handler,
            2: ping_with_options_handler,
            3: sending_udp_data_handler,
            4: sending_tcp_data_handler,
            5: traceroute_handler,
            100: ip_addr_add_handler,
            101: iptables_handler,
            102: ip_route_add_handler,
            103: arp_handler,
            200: open_udp_server_handler,
            201: open_tcp_server_handler,
            202: block_tcp_udp_port,
        }
        self._job: Job = job
        self._job_host = job_host
        self._strategy: typing.Callable[[Job, typing.Any], None] = self._dct[
            self._job.job_id
        ]

    @property
    def strategy(self) -> typing.Callable[[Job, typing.Any], None]:
        """Get current strategy

        Returns:
            JobsStrategy: current strategy
        """

        return self._strategy

    @strategy.setter
    def strategy(self, job_id: int):
        """Change the execution strategy

        Args:
            job_id (int): id for change job strategy

        """
        self._strategy = self._dct[job_id]

    def handler(self) -> None:
        self._strategy(self._job, self._job_host)
