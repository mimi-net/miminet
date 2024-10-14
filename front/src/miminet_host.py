import json
import re
import ipaddress

from flask import jsonify, make_response, request, Response
from flask_login import current_user, login_required
from miminet_model import Network, Simulate, db
from configurators import *


# ------ Argument Validators ------
# (you can add your checks here)


def IPv4_check(arg: str) -> bool:
    """Check IP address correctness"""
    try:
        ipaddress.ip_address(arg)
        return True
    except:
        return False


def range_check(arg: str, range: range) -> bool:
    """Check if a number is within a specified range"""
    try:
        return int(arg) in range
    except:
        return False


def digit_check(arg: str) -> bool:
    "Check if the argument is a number"
    try:
        num = int(arg)
        return True
    except:
        return False


def mask_check(arg: str) -> bool:
    """Check subnet mask correctness"""
    try:
        return int(arg) in range(0, 33)
    except:
        return False


def port_check(arg: str) -> bool:
    """Check port correctness"""
    try:
        return int(arg) in range(0, 65536)
    except:
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
    """Check if the Python String is empty or not"""
    return arg != ""


def regex_check(arg: str, regex: str) -> bool:
    """Check if a string matches the given regex"""
    return bool(re.match(regex, arg))


# ------ Error messages ------
class ErrorType:
    ip = "Неверно указан IP-адрес"
    port = "Неверно указан порт"
    mask = "Неверно указана маска подсети"
    options = "Неверно указаны опции"


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
).add_check(emptiness_check).add_check(ascii_check).set_error_msg(
    build_error(ErrorType.options, "ping (с опциями)")
)
host_ping_opt_job.add_param("config_host_ping_with_options_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "ping (с опциями)"))

# send UDP data
host_udp_job = host.create_job(3, "send -s [0] -p udp [1]:[2]")
host_udp_job.add_param("config_host_send_udp_data_size_input_field").add_check(
    port_check
).set_error_msg(build_error(ErrorType.port, "Отправить данные (UDP)"))
host_udp_job.add_param("config_host_send_udp_data_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Отправить данные (UDP)"))
host_udp_job.add_param("config_host_send_udp_data_port_input_field").add_check(
    mask_check
).set_error_msg(build_error(ErrorType.port, "Отправить данные (UDP)"))

# send TCP data
host_tcp_job = host.create_job(4, "send -s [0] -p tcp [1]:[2]")
host_tcp_job.add_param("config_host_send_tcp_data_size_input_field").add_check(
    port_check
).set_error_msg(build_error(ErrorType.port, "Отправить данные (TCP)"))
host_tcp_job.add_param("config_host_send_tcp_data_ip_input_field").add_check(
    IPv4_check
).set_error_msg(build_error(ErrorType.ip, "Отправить данные (TCP)"))
host_tcp_job.add_param("config_host_send_tcp_data_port_input_field").add_check(
    mask_check
).set_error_msg(build_error(ErrorType.port, "Отправить данные (TCP)"))

# traceroute -n (with options)
traceroute_job = host.create_job(5, "traceroute -n [0] [1]")
traceroute_job.add_param(
    "config_host_traceroute_with_options_options_input_field"
).add_check(emptiness_check).add_check(ascii_check).set_error_msg(
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
