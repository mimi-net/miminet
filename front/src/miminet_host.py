import json
import re
import ipaddress
import shlex
from typing import List, Dict

from flask import jsonify, make_response, request, Response
from flask_login import current_user, login_required
from miminet_model import Network, Simulate, db
from configurators import (
    HostConfigurator,
    SwitchConfigurator,
    HubConfigurator,
    ServerConfigurator,
    RouterConfigurator,
    EdgeConfigurator,
    get_data,
)


# ------ Argument Validators ------
# (you can add your checks here)


def IPv4_check(arg: str) -> bool:
    """Check IP address correctness"""
    try:
        ipaddress.ip_address(arg)
        return True
    except ValueError:
        return False


def range_check(arg: str, range: range) -> bool:
    """Check if a number is within a specified range"""
    try:
        return int(arg) in range
    except (ValueError, TypeError):
        return False


def digit_check(arg: str) -> bool:
    "Check if the argument is a number"
    try:
        int(arg)
        return True
    except (ValueError, TypeError):
        return False


def mask_check(arg: str) -> bool:
    """Check subnet mask correctness"""
    try:
        return int(arg) in range(0, 33)
    except (ValueError, TypeError):
        return False


def port_check(arg: str) -> bool:
    """Check port correctness"""
    try:
        return int(arg) in range(0, 65536)
    except (ValueError, TypeError):
        return False


def data_size_check(arg: str) -> bool:
    """Check data size correctness"""
    try:
        return int(arg) in range(0, 65536)
    except (ValueError, TypeError):
        return False


def name_check(arg: str) -> bool:
    """Check that the name is in the allowed length from 2 to 15,
    from allowed characters: a-z, A-Z, 0-9, -, _."""
    return bool(re.match("^[A-Za-z][A-Za-z0-9_-]{1,14}$", arg))


def MAC_check(arg: str) -> bool:
    """Check MAC-address correctness"""
    return bool(
        re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", arg.lower())
    )


def ascii_check(arg: str) -> bool:
    """Check whether all characters in a string are ASCII characters"""
    return arg.isascii()


def emptiness_check(arg: str) -> bool:
    """Check if the Python String is empty or equals 0"""
    return bool(arg and str(arg).strip()) and str(arg) != "0"


def time_check(arg: str) -> bool:
    """Check if a string is >=50 or <= 0 or empty"""
    return range_check(arg, range(1, 51))


def regex_check(arg: str, regex: str) -> bool:
    """Check if a string matches the given regex"""
    return bool(re.match(regex, arg))


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


# ------ Error messages ------


class ErrorType:
    ip = "Неверно указан IP-адрес"
    port = "Неверно указан порт"
    mask = "Неверно указана маска подсети"
    options = "Неверно указаны опции"
    data_size = "Неверно указан размер данных"


def build_error(error_type: str, cmd: str) -> str:
    """Returns an error message based on the specified error type and command

    Args:
        cmd (str): command name

    Returns:
        str: Error message with specified type and command name
    """

    return f'{error_type} для команды "{cmd}"'


# --- Network device configurators ---

hub = HubConfigurator()
switch = SwitchConfigurator()
host = HostConfigurator()
router = RouterConfigurator()
server = ServerConfigurator()
edge = EdgeConfigurator()

# --- Jobs ---

# ~ ~ ~ HOST JOBS ~ ~ ~

# ping -c 1 (1 param)
host_ping_job = host.create_job(1, "ping -c 1 [0]")
host_ping_job.add_param("config_host_ping_c_1_ip").add_check(IPv4_check).set_error_msg(
    build_error(ErrorType.ip, "ping")
)

# ping -c 1 (with options)
host_ping_opt_job = host.create_job(2, "ping -c 1 [0] [1]")
host_ping_opt_job.add_param(
    "config_host_ping_with_options_options_input_field"
).add_check(ascii_check).add_filter(ping_options_filter).set_error_msg(
    build_error(ErrorType.options, "ping (с опциями)")
)
host_ping_opt_job.add_param("config_host_ping_with_options_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "ping (с опциями)"))

# send UDP data
host_udp_job = host.create_job(3, "send -s [0] -p udp [1]:[2]")
host_udp_job.add_param("config_host_send_udp_data_size_input_field").add_check(
    data_size_check
).set_error_msg(build_error(ErrorType.data_size, "Отправить данные (UDP)"))
host_udp_job.add_param("config_host_send_udp_data_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Отправить данные (UDP)"))
host_udp_job.add_param("config_host_send_udp_data_port_input_field").add_check(
    port_check
).set_error_msg(build_error(ErrorType.port, "Отправить данные (UDP)"))

# send TCP data
host_tcp_job = host.create_job(4, "send -s [0] -p tcp [1]:[2]")
host_tcp_job.add_param("config_host_send_tcp_data_size_input_field").add_check(
    data_size_check
).set_error_msg(build_error(ErrorType.data_size, "Отправить данные (TCP)"))
host_tcp_job.add_param("config_host_send_tcp_data_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Отправить данные (TCP)"))
host_tcp_job.add_param("config_host_send_tcp_data_port_input_field").add_check(
    port_check
).set_error_msg(build_error(ErrorType.port, "Отправить данные (TCP)"))

# traceroute -n (with options)
traceroute_job = host.create_job(5, "traceroute -n [0] [1]")
traceroute_job.add_param(
    "config_host_traceroute_with_options_options_input_field"
).add_check(ascii_check).add_filter(traceroute_options_filter).set_error_msg(
    build_error(ErrorType.options, "traceroute -n (с опциями)")
)
traceroute_job.add_param(
    "config_host_traceroute_with_options_ip_input_field"
).add_check(IPv4_check).set_error_msg(
    build_error(ErrorType.ip, "traceroute -n (с опциями)")
)

# Add route
add_route_job = host.create_job(102, "ip route add [0]/[1] via [2]")
add_route_job.add_param("config_host_add_route_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Добавить маршрут"))
add_route_job.add_param("config_host_add_route_mask_input_field").add_check(
    mask_check
).set_error_msg(build_error(ErrorType.mask, "Добавить маршрут"))
add_route_job.add_param("config_host_add_route_gw_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Добавить маршрут"))

# arp -s ip hw_addr
arp_job = host.create_job(103, "arp -s [0] [1]")
arp_job.add_param("config_host_add_arp_cache_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Добавить запись в ARP-cache"))
arp_job.add_param("config_host_add_arp_cache_mac_input_field").add_check(
    MAC_check
).set_error_msg('MAC-адрес для команды "Добавить запись в ARP-cache" указан неверно')

host_dhclient_job = host.create_job(108, "dhcp client")
host_dhclient_job.add_param(
    "config_host_add_dhclient_interface_select_iface_field"
).add_check(emptiness_check).set_error_msg(
    'Не указан интерфейс для команды "Запросить IP адрес автоматически"'
)

# ~ ~ ~ ROUTER JOBS ~ ~ ~

# ping
router_ping_job = router.create_job(1, "ping -c 1 [0]")
router_ping_job.add_param("config_router_ping_c_1_ip").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "ping"))

# add IP/mask
add_ip_job = router.create_job(100, "ip addess add [0]/[1] dev [2]")
add_ip_job.add_param("config_router_add_ip_mask_iface_select_field").add_check(
    emptiness_check
).set_error_msg('Не указан интерфейс для команды "Добавить IP-адрес"')
add_ip_job.add_param("config_router_add_ip_mask_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Добавить IP-адрес"))
add_ip_job.add_param("config_router_add_ip_mask_mask_input_field").add_check(
    mask_check
).set_error_msg(build_error(ErrorType.mask, "Добавить IP-адрес"))

# add NAT masquerade to the interface
nat_job = router.create_job(101, "add nat -o [0] -j masquerad")
nat_job.add_param("config_router_add_nat_masquerade_iface_select_field").add_check(
    emptiness_check
).set_error_msg('Не указан интерфейс для команды "Включить NAT masquerade"')

# add Port forwarding TCP
port_forwarding_tcp_job = router.create_job(
    109, "port forwarding -p tcp -i [0] from [1] to [2]:[3]"
)
port_forwarding_tcp_job.add_param(
    "config_router_add_port_forwarding_tcp_iface_select_field"
).add_check(emptiness_check).set_error_msg("Добавить Port forwarding для TCP")
port_forwarding_tcp_job.add_param(
    "config_router_add_port_forwarding_tcp_port_input_field"
).add_check(port_check).set_error_msg(
    build_error(ErrorType.port, "Добавить Port forwarding для TCP")
)
port_forwarding_tcp_job.add_param(
    "config_router_add_port_forwarding_tcp_dest_ip_input_field"
).add_check(IPv4_check).set_error_msg(
    build_error(ErrorType.ip, "Добавить Port forwarding для TCP")
)
port_forwarding_tcp_job.add_param(
    "config_router_add_port_forwarding_tcp_dest_port_input_field"
).add_check(port_check).set_error_msg(
    build_error(ErrorType.port, "Добавить Port forwarding для TCP")
)

# add Port forwarding UDP
port_forwarding_udp_job = router.create_job(
    110, "port forwarding -p udp -i [0] from [1] to [2]:[3]"
)
port_forwarding_udp_job.add_param(
    "config_router_add_port_forwarding_udp_iface_select_field"
).add_check(emptiness_check).set_error_msg("Добавить Port forwarding для UDP")
port_forwarding_udp_job.add_param(
    "config_router_add_port_forwarding_udp_port_input_field"
).add_check(port_check).set_error_msg(
    build_error(ErrorType.port, "Добавить Port forwarding для UDP")
)
port_forwarding_udp_job.add_param(
    "config_router_add_port_forwarding_udp_dest_ip_input_field"
).add_check(IPv4_check).set_error_msg(
    build_error(ErrorType.ip, "Добавить Port forwarding для UDP")
)
port_forwarding_udp_job.add_param(
    "config_router_add_port_forwarding_udp_dest_port_input_field"
).add_check(port_check).set_error_msg(
    build_error(ErrorType.port, "Добавить Port forwarding для UDP")
)

# Add route
router_add_route_job = router.create_job(102, "ip route add [0]/[1] via [2]")
router_add_route_job.add_param("config_router_add_route_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Добавить маршрут"))
router_add_route_job.add_param("config_router_add_route_mask_input_field").add_check(
    mask_check
).set_error_msg(build_error(ErrorType.mask, "Добавить маршрут"))
router_add_route_job.add_param("config_router_add_route_gw_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Добавить маршрут"))

# Add VLAN
vlan_job = router.create_job(104, "subinterface [1]:[2] VLAN [3]")
vlan_job.add_param("config_router_add_subinterface_iface_select_field").add_check(
    emptiness_check
).set_error_msg('Не выбран линк для команды "Добавить сабинтерфейс с VLAN"')
vlan_job.add_param("config_router_add_subinterface_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Добавить сабинтерфейс с VLAN"))
vlan_job.add_param("config_router_add_subinterface_mask_input_field").add_check(
    mask_check
).set_error_msg(build_error(ErrorType.mask, "Добавить сабинтерфейс с VLAN"))
vlan_job.add_param("config_router_add_subinterface_vlan_input_field").add_check(
    digit_check
).set_error_msg('Неверный параметр VLAN для команды "Добавить сабинтерфейс с VLAN"')

# IPIP
ipip_job = router.create_job(105, "ipip: [3] from [0] to [1] \n[3]: [2]")
ipip_job.add_param("config_router_add_ipip_tunnel_iface_select_ip_field").add_check(
    emptiness_check
).set_error_msg(
    'Не выбран IP-адрес начальной точки для команды "Добавить IPIP-интерфейс"'
)
ipip_job.add_param("config_router_add_ipip_tunnel_end_ip_input_field").add_check(
    IPv4_check
).set_error_msg("Неверно указан IP-адрес конечной точки для команды ")
ipip_job.add_param("config_router_add_ipip_tunnel_interface_ip_input_field").add_check(
    IPv4_check
).set_error_msg(
    'Неверно указан IP адрес IPIP-интерфейса для команды "Добавить IPIP-интерфейс"'
)
ipip_job.add_param("config_router_add_ipip_tunnel_interface_name_field").add_check(
    name_check
).set_error_msg(
    'Неверно указано название IPIP-интерфейса для команды "Добавить IPIP-интерфейс"'
)

# GRE
gre_job = router.create_job(106, "gre: [3] from [0] to [1] \n[3]: [2]")
gre_job.add_param("config_router_add_gre_interface_select_ip_field").add_check(
    emptiness_check
).set_error_msg(
    'Не выбран IP-адрес начальной точки для команды "Добавить GRE-интерфейс"'
)
gre_job.add_param("config_router_add_gre_interface_end_ip_input_field").add_check(
    IPv4_check
).set_error_msg(
    'Неверно указан IP-адрес конечной точки для команды "Добавить GRE-интерфейс"'
)
gre_job.add_param("config_router_add_gre_interface_ip_input_field").add_check(
    IPv4_check
).set_error_msg(
    'Неверно указан IP адрес GRE-интерфейса для команды "Добавить GRE-интерфейс"'
)
gre_job.add_param("config_router_add_gre_interface_name_field").add_check(
    name_check
).set_error_msg(
    'Неверно указано название GRE-интерфейса для команды "Добавить GRE-интерфейс"'
)

# Add ARP Proxy to the interface
arp_proxy_job = router.create_job(107, "arp proxy: [1]")
arp_proxy_job.add_param("config_router_add_arp_proxy_iface_select_field").add_check(
    emptiness_check
).set_error_msg('Не указан интерфейс для команды "Добавить ARP Proxy-интерфейс"')
arp_proxy_job.add_param("router_connection_host_label_hidden").add_check(
    emptiness_check
).set_error_msg('Не указан интерфейс для команды "Добавить ARP Proxy-интерфейс"')


# ~ ~ ~ SWITCH JOBS ~ ~ ~
link_down_job = switch.create_job(6, "link down [1]")
link_down_job.add_param("config_switch_link_down_iface_select_field").add_check(
    emptiness_check
).set_error_msg('Не указан интерфейс для команды "Удалить линк"')
link_down_job.add_param("switch_connection_host_label_hidden").add_check(
    emptiness_check
).set_error_msg('Не указан интерфейс для команды "Удалить линк"')

sleep_job = switch.create_job(7, "sleep [0] seconds")
sleep_job.add_param("config_switch_sleep").add_check(time_check).set_error_msg(
    build_error(ErrorType.options, "sleep")
)


# ~ ~ ~ SERVER JOBS ~ ~ ~

# ping -c 1
server_ping_job = server.create_job(1, "ping -c 1 [0]")
server_ping_job.add_param("config_server_ping_c_1_ip").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "ping"))

# start UDP server
start_udp_server = server.create_job(200, "nc -u [0] -l [1]")
start_udp_server.add_param("config_server_start_udp_server_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Запустисть UDP сервер"))
start_udp_server.add_param("config_server_start_udp_server_port_input_field").add_check(
    port_check
).set_error_msg(build_error(ErrorType.port, "Запустисть UDP сервер"))

# start TCP server
start_tcp_server = server.create_job(201, "nc [0] -l [1]")
start_tcp_server.add_param("config_server_start_tcp_server_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Запустисть TCP сервер"))
start_tcp_server.add_param("config_server_start_tcp_server_port_input_field").add_check(
    port_check
).set_error_msg(build_error(ErrorType.port, "Запустисть TCP сервер"))

# Block TCP/UDP port
block_server_port = server.create_job(202, "drop tcp/udp port [0]")
block_server_port.add_param("config_server_block_tcp_udp_port_input_field").add_check(
    port_check
).set_error_msg(build_error(ErrorType.port, "Блокировать TCP/UDP порт"))

# start DHCP server
start_dhcp_server = server.create_job(203, "dhcp ip range: [0],[1]/[2] gw: [3]")
start_dhcp_server.add_param("config_server_add_dhcp_ip_range_1_input_field").add_check(
    IPv4_check
).set_error_msg('Неверно указан IP адрес диапазона для команды "Запустить DHCP сервер"')
start_dhcp_server.add_param("config_server_add_dhcp_ip_range_2_input_field").add_check(
    IPv4_check
).set_error_msg('Неверно указан IP адрес диапазона для команды "Запустить DHCP сервер"')
start_dhcp_server.add_param("config_server_add_dhcp_mask_input_field").add_check(
    mask_check
).set_error_msg('Неверно указана маска для команды "Запустить DHCP сервер"')
start_dhcp_server.add_param("config_server_add_dhcp_gateway_input_field").add_check(
    IPv4_check
).set_error_msg('Неверно указан IP адрес шлюза для команды "Запустить DHCP сервер"')
start_dhcp_server.add_param(
    "config_server_add_dhcp_interface_select_iface_field"
).add_check(emptiness_check).set_error_msg(
    'Не указан интерфейс для команды "Запустить DHCP сервер"'
)


# ------ request handlers ------


@login_required
def save_hub_config():
    return hub.configure()


@login_required
def save_switch_config():
    return switch.configure()


@login_required
def save_host_config():
    return host.configure()


@login_required
def save_router_config():
    return router.configure()


@login_required
def save_server_config():
    return server.configure()


@login_required
def save_edge_config():
    return edge.configure()


@login_required
def delete_job():
    """
    Called when job is removed for an network device
    """

    def build_response(msg: str) -> Response:
        return make_response(jsonify({"message": msg}), 400)

    user = current_user
    network_guid = get_data("guid")
    job_id = get_data("id")

    if request.method != "POST":
        return build_response("Неверный запрос")

    if not network_guid:
        return build_response("Не указан параметр net_guid")

    cur_network: Network = (
        Network.query.filter(Network.guid == network_guid)
        .filter(Network.author_id == user.id)
        .first()
    )

    if not cur_network:
        return build_response("Такая сеть не найдена")

    json_network: dict = json.loads(cur_network.network)

    # get jobs & remove one
    jobs: list = json_network["jobs"]
    new_jobs: list = list(filter(lambda x: x["id"] != job_id, jobs))
    json_network["jobs"] = new_jobs

    # update network
    cur_network.network = json.dumps(json_network)

    # Remove all previous simulations
    sims = Simulate.query.filter(Simulate.network_id == cur_network.id).all()
    for s in sims:
        db.session.delete(s)

    db.session.commit()

    return {"message": "Команда удалена", "jobs": json_network["jobs"]}
