from abc import abstractmethod
from ast import Call
from asyncio import Server
import json
from ossaudiodev import control_labels
import re
import socket
import uuid
import ipaddress

from typing import Optional, Callable
from flask import jsonify, make_response, request, Response
from flask_login import current_user, login_required
from miminet_model import Network, Simulate, db


def get_data(arg: str):
    """Get data from user's request"""
    return request.form.get(arg, type=str)


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
    return re.match("^[A-Za-z][A-Za-z0-9_-]{1,14}$", arg)


def MAC_check(arg: str) -> bool:
    """Check MAC-address correctness"""
    return re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", arg.lower())


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
def get_ip_error(cmd: str) -> str:
    return f'Неверно указан IP-адрес для команды "{cmd}"'


def get_port_error(cmd: str) -> str:
    return f'Неверно указан порт для команды "{cmd}"'


def get_mask_error(cmd: str) -> str:
    return f'Неверно указана маска подсети для команды "{cmd}"'


def get_opt_error(cmd: str) -> str:
    return f'Неверно указаны опции для команды "{cmd}"'


# ------ Jobs ------
class JobArgConfigurator:
    """Class with job argument data"""

    def __init__(self, control_id: str):
        """
        Args:
            cotrol_id (str): ID of the element with argument data
        """
        self.__control_id: str = control_id
        self.__validators: list[Callable[[str], bool]] = []
        self.__error_msg: str = "Невозможно добавить команду: ошибка в аргументе"

    def set_error_msg(self, msg: str):
        if not msg:
            raise ValueError("Incorrect error message")

        self.__error_msg = msg
        return self

    @property
    def error_msg(self):
        return self.__error_msg

    def add_check(self, validator: Callable[[str], bool]):
        """Add new check for job param (you can add several checks)
        Args:
            validator (Callable[[str], bool]): function that takes a string and returns True if it passes the check_
        """
        self.__validators.append(validator)

        return self

    def configure(self) -> Optional[str]:
        """Get an element from the request and performs validation

        Returns:
            Optional[str]: None if argument didn't pass checks
        """
        arg = get_data(self.__control_id)

        if all([validate(arg) for validate in self.__validators]):
            return arg
        return None


class JobConfigurator:
    """Job configurator. Contains arguments and check them"""

    def __init__(self, job_id: int, job_sign: str):
        """
        Args:
            job_id (int): ID that is assigned to the job in the select list (see static/config*.html files)
            job_sign (str): inscription that will be displayed above the device after adding a job
        """
        self.__job_id: int = job_id
        self.__print_cmd: str = job_sign
        self.__args: list[JobArgConfigurator] = []

    @property
    def job_id(self):
        return self.__job_id

    def add_param(self, control_id: str) -> JobArgConfigurator:
        """
        Add new parameter to job
        Args:
            cotrol_id (str): ID of the element with argument data
        """
        new_arg = JobArgConfigurator(control_id)
        self.__args.append(new_arg)
        return new_arg

    def configure(self) -> dict[str, str]:
        """Validate every argument and return dict with job's data"""
        random_id: str = uuid.uuid4().hex  # random id for every added job
        configured_args = [arg.configure() for arg in self.__args]

        # check whether the arguments passed the checks
        for i in range(len(configured_args)):
            if configured_args[i] is None:
                # return warning for user with arg error message
                raise ArgCheckError(self.__args[i].error_msg)

        # insert arguments into label string
        command_label: str = self.__print_cmd
        for i, arg in enumerate(configured_args):
            command_label = command_label.replace(f"[{i}]", arg)

        response = {
            "id": random_id,
            "job_id": self.__job_id,
            "print_cmd": command_label,
        }

        # add args to response
        for i, arg in enumerate(configured_args):
            response[f"arg_{i+1}"] = arg

        return response


# ------ Network Device Configurators ------
class ConfigurationError(Exception):
    """Special exception for user's request errors"""

    def __init__(self, message):
        super().__init__(message)


class ArgCheckError(Exception):
    """Special exception for job argument errors"""

    def __init__(self, message):
        super().__init__(message)


class AbstractDeviceConfigurator:
    def __init__(self, device_type: str):
        self.__jobs: dict[int, JobConfigurator] = {}
        self._device_type: str = device_type
        self._device_node = None  # current device node in miminet network

    __MAX_JOBS_COUNT: int = 20

    def create_job(self, job_id: int, job_sign: str) -> JobConfigurator:
        """
        Create job for current network device
        Args:
            job_id (int): ID that is assigned to the job in the select list (see static/config*.html files)
            job_sign (str): label that will be displayed above the device after adding a job
        """
        if job_id in self.__jobs.keys():
            raise ValueError("This job already added")

        self.__jobs[job_id] = JobConfigurator(job_id, job_sign)
        return self.__jobs[job_id]

    # [!] I have broken device configuration process into different blocks, they will be below

    def _conf_prepare(self):
        """Prepare variables for configuring"""

        # check request correctness
        if request.method != "POST":
            raise ConfigurationError("Неверный запрос: ожидался POST")

        network_guid = get_data("net_guid")

        if not network_guid:
            raise ConfigurationError("Не указан параметр net_guid")

        # get user's network
        self._cur_network: Network = (
            Network.query.filter(Network.guid == network_guid)
            .filter(Network.author_id == current_user.id)
            .first()
        )

        if not self._cur_network:
            raise ConfigurationError("Сеть не найдена")

        # get element (host, hub, switch, ...)
        element_form_id = f"{self._device_type}_id"
        device_id = get_data(element_form_id)

        if not device_id:
            raise ConfigurationError("Не указан параметр {element_form_id}")

        # json representation
        self._json_network: dict = json.loads(self._cur_network.network)
        self._nodes: list = self._json_network["nodes"]

        # find all matches with device in nodes
        filt_nodes = list(filter(lambda n: n["data"]["id"] == device_id, self._nodes))

        if not filt_nodes:
            raise ConfigurationError(f"Такого '{self._device_type}' не существует")

        # current device's node
        self._device_node = filt_nodes[0]

    def _conf_label_update(self):
        """Update device label(name). Typically used at the end of the configuration"""
        # get label with device name
        label = get_data(f"config_{self._device_type}_name")

        if label:
            self._device_node["config"]["label"] = label
            self._device_node["data"]["label"] = self._device_node["config"]["label"]

    def __conf_sims_delete(self):
        """Delete saved simulations. Typically used at the end of the configuration"""
        # Remove all previous simulations (after configuration update)
        sims = Simulate.query.filter(Simulate.network_id == self._cur_network.id).all()
        for s in sims:
            db.session.delete(s)

        self._cur_network.network = json.dumps(self._json_network)
        db.session.commit()

    def _conf_jobs(self):
        """Configure jobs added to the device"""
        job_id_str = get_data(f"config_{self._device_type}_job_select_field")

        if not job_id_str:
            raise ConfigurationError("Не указан параметр job_id")

        job_id = int(job_id_str)

        if job_id not in self.__jobs.keys():
            return  # if user didn't select job

        job_level = len(
            self._json_network["jobs"]
        )  # level in the device configuration list

        if job_level > self.__MAX_JOBS_COUNT:
            raise ConfigurationError("Превышен лимит на количество задач")

        job = self.__jobs[job_id]
        job_conf_res = job.configure()

        job_conf_res["level"] = job_level
        job_conf_res["host_id"] = self._device_node["data"]["id"]

        self._json_network["jobs"].append(job_conf_res)

    def _conf_ip_addresses(self):
        """Configurate device IP-addresses"""
        # all interfaces
        iface_ids = request.form.getlist(f"config_{self._device_type}_iface_ids[]")
        for iface_id in iface_ids:
            if not self._device_node["interface"]:
                return  # we have nothing to configure

            filtered_ifaces = list(
                filter(lambda x: x["id"] == iface_id, self._device_node["interface"])
            )

            if not filtered_ifaces:
                continue

            interface = filtered_ifaces[0]

            ip_value = get_data(f"config_{self._device_type}_ip_{str(iface_id)}")
            mask_value = get_data(f"config_{self._device_type}_mask_{str(iface_id)}")

            if not ip_value:
                continue

            if not mask_value.isdigit():
                # Check if we have 1.2.3.4/5 ?
                ip_mask = ip_value.split("/")
                if len(ip_mask) == 2:
                    ip_value = ip_mask[0]
                    mask_value = ip_mask[1]
                else:
                    raise ArgCheckError("Не указана маска для IP адреса")

            mask_value = int(mask_value)

            if mask_value < 0 or mask_value > 32:
                raise ArgCheckError("Маска подсети указана неверно")

            if not IPv4_check(ip_value):
                raise ArgCheckError("IP-адрес указан неверно")

            interface["ip"] = ip_value
            interface["netmask"] = mask_value

    def _conf_gw(self):
        default_gw = get_data(f"config_{self._device_type}_default_gw")

        if default_gw:
            if not IPv4_check(default_gw):
                raise ArgCheckError('Неверно указан IP-адрес для "шлюза по умолчанию"')
            self._device_node["config"]["default_gw"] = default_gw
        else:
            self._device_node["config"]["default_gw"] = ""

    @abstractmethod
    def _conf_main() -> dict:
        """Configuration main block in which the entire configuration process takes place"""
        pass

    def configure(self) -> Response:
        """Configure current network device"""
        try:
            res = self._conf_main()  # configuration result
            self.__conf_sims_delete()
            return make_response(jsonify(res), 200)
        except ConfigurationError as e:
            return make_response(jsonify({"message": str(e)}), 400)


class HubConfigurator(AbstractDeviceConfigurator):
    def __init__(self):
        super().__init__(device_type="hub")

    def _conf_main(self):
        self._conf_prepare()
        self._conf_label_update()

        return {"message": "Конфигурация обновлена", "nodes": self._nodes}


class SwitchConfigurator(AbstractDeviceConfigurator):
    def __init__(self):
        super().__init__(device_type="switch")

    def _conf_main(self):
        self._conf_prepare()
        self._conf_label_update()

        # STP setup
        switch_stp = get_data("config_switch_stp")

        self._device_node["config"]["stp"] = 0

        if switch_stp and switch_stp == "on":
            self._device_node["config"]["stp"] = 1

        return {"message": "Конфигурация обновлена", "nodes": self._nodes}


class HostConfigurator(AbstractDeviceConfigurator):
    def __init__(self):
        super().__init__(device_type="host")

    def _conf_main(self):
        self._conf_prepare()
        self._conf_label_update()

        res = {}

        try:  # catch argument check errors
            self._conf_jobs()
            self._conf_ip_addresses()
            self._conf_gw()
        except ArgCheckError as e:
            res.update({"warning": str(e)})

        res.update(
            {
                "message": "Конфигурация обновлена",
                "nodes": self._nodes,
                "jobs": self._json_network["jobs"],
            }
        )

        return res


class RouterConfigurator(HostConfigurator):
    # router has the same configuration method as host
    def __init__(self):
        super().__init__()
        self._device_type = "router"


class ServerConfigurator(HostConfigurator):
    # server has the same configuration method as host
    def __init__(self):
        super().__init__()
        self._device_type = "server"


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
    get_ip_error("ping")
)

# ping -c 1 (with options)
host_ping_opt_job = host.create_job(2, "ping -c 1 [0] [1]")
host_ping_opt_job.add_param(
    "config_host_ping_with_options_options_input_field"
).add_check(emptiness_check).add_check(ascii_check).set_error_msg(
    get_opt_error("ping (с опциями)")
)
host_ping_opt_job.add_param("config_host_ping_with_options_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("ping (с опциями)"))

# send UDP data
host_udp_job = host.create_job(3, "send -s [0] -p udp [1]:[2]")
host_udp_job.add_param("config_host_send_udp_data_size_input_field").add_check(
    port_check
).set_error_msg(get_port_error("Отправить данные (UDP)"))
host_udp_job.add_param("config_host_send_udp_data_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Отправить данные (UDP)"))
host_udp_job.add_param("config_host_send_udp_data_port_input_field").add_check(
    mask_check
).set_error_msg(get_port_error("Отправить данные (UDP)"))

# send TCP data
host_tcp_job = host.create_job(4, "send -s [0] -p tcp [1]:[2]")
host_tcp_job.add_param("config_host_send_tcp_data_size_input_field").add_check(
    port_check
).set_error_msg(get_port_error("Отправить данные (TCP)"))
host_tcp_job.add_param("config_host_send_tcp_data_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Отправить данные (TCP)"))
host_tcp_job.add_param("config_host_send_tcp_data_port_input_field").add_check(
    mask_check
).set_error_msg(get_port_error("Отправить данные (TCP)"))

# traceroute -n (with options)
traceroute_job = host.create_job(5, "traceroute -n [0] [1]")
traceroute_job.add_param(
    "config_host_traceroute_with_options_options_input_field"
).add_check(emptiness_check).add_check(ascii_check).set_error_msg(
    get_opt_error("traceroute -n (с опциями)")
)
traceroute_job.add_param(
    "config_host_traceroute_with_options_ip_input_field"
).add_check(IPv4_check).set_error_msg(get_ip_error("traceroute -n (с опциями)"))

# Add route
add_route_job = host.create_job(102, "ip route add [0]/[1] via [2]")
add_route_job.add_param("config_host_add_route_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Добавить маршрут"))
add_route_job.add_param("config_host_add_route_mask_input_field").add_check(
    mask_check
).set_error_msg(get_mask_error("Добавить маршрут"))
add_route_job.add_param("config_host_add_route_gw_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Добавить маршрут"))

# arp -s ip hw_addr
arp_job = host.create_job(103, "arp -s [0] [1]")
arp_job.add_param("config_host_add_arp_cache_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Добавить запись в ARP-cache"))
arp_job.add_param("config_host_add_arp_cache_mac_input_field").add_check(
    MAC_check
).set_error_msg('MAC-адрес для команды "Добавить запись в ARP-cache" указан неверно')

# ~ ~ ~ ROUTER JOBS ~ ~ ~

# ping
router_ping_job = router.create_job(1, "ping -c 1 [0]")
router_ping_job.add_param("config_router_ping_c_1_ip").add_check(
    IPv4_check
).set_error_msg(get_ip_error("ping"))

# add IP/mask
add_ip_job = router.create_job(100, "ip addess add [0]/[1] dev [2]")
add_ip_job.add_param("config_router_add_ip_mask_iface_select_field").add_check(
    emptiness_check
).set_error_msg('Не указан интерфейс для команды "Добавить IP-адрес"')
add_ip_job.add_param("config_router_add_ip_mask_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Добавить IP-адрес"))
add_ip_job.add_param("config_router_add_ip_mask_mask_input_field").add_check(
    mask_check
).set_error_msg(get_mask_error("Добавить IP-адрес"))

# add NAT masquerade to the interface
nat_job = router.create_job(101, "add nat -o [0] -j masquerad")
nat_job.add_param("config_router_add_nat_masquerade_iface_select_field").add_check(
    emptiness_check
).set_error_msg('Не указан интерфейс для команды "Включить NAT masquerade"')

# Add route
router_add_route_job = router.create_job(102, "ip route add [0]/[1] via [2]")
router_add_route_job.add_param("config_router_add_route_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Добавить маршрут"))
router_add_route_job.add_param("config_router_add_route_mask_input_field").add_check(
    mask_check
).set_error_msg(get_mask_error("Добавить маршрут"))
router_add_route_job.add_param("config_router_add_route_gw_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Добавить маршрут"))

# Add VLAN
vlan_job = router.create_job(104, "subinterface [0]:[1] VLAN [2]")
vlan_job.add_param("config_router_add_subinterface_iface_select_field").add_check(
    emptiness_check
).set_error_msg('Не выбран линк для команды "Добавить сабинтерфейс с VLAN"')
vlan_job.add_param("config_router_add_subinterface_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Добавить сабинтерфейс с VLAN"))
vlan_job.add_param("config_router_add_subinterface_mask_input_field").add_check(
    mask_check
).set_error_msg(get_mask_error("Добавить сабинтерфейс с VLAN"))
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
).set_error_msg(
    'Не указан IP-адрес конечной точки для команды "Добавить IPIP-интерфейс"'
)
ipip_job.add_param("config_router_add_ipip_tunnel_interface_ip_input_field").add_check(
    IPv4_check
).set_error_msg(
    'Не указан IP адрес IPIP-интерфейса для команды "Добавить IPIP-интерфейс"'
)
ipip_job.add_param("config_router_add_ipip_tunnel_interface_name_field").add_check(
    name_check
).set_error_msg(
    'Не указано название IPIP-интерфейса для команды "Добавить IPIP-интерфейс"'
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
    'Не указан IP-адрес конечной точки для команды "Добавить GRE-интерфейс"'
)
gre_job.add_param("config_router_add_gre_interface_ip_input_field").add_check(
    IPv4_check
).set_error_msg(
    'Не указан IP адрес GRE-интерфейса для команды "Добавить GRE-интерфейс"'
)
gre_job.add_param("config_router_add_gre_interface_name_field").add_check(
    name_check
).set_error_msg(
    'Не указано название GRE-интерфейса для команды "Добавить GRE-интерфейс"'
)

# ~ ~ ~ SERVER JOBS ~ ~ ~

# ping -c 1
server_ping_job = server.create_job(1, "ping -c 1 [0]")
server_ping_job.add_param("config_server_ping_c_1_ip").add_check(
    IPv4_check
).set_error_msg(get_ip_error("ping"))

# start UDP server
start_udp_server = server.create_job(200, "nc -u [0] -l [1]")
start_udp_server.add_param("config_server_start_udp_server_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Запустисть UDP сервер"))
start_udp_server.add_param("config_server_start_udp_server_port_input_field").add_check(
    port_check
).set_error_msg(get_port_error("Запустисть UDP сервер"))

# start TCP server
start_tcp_server = server.create_job(201, "nc [0] -l [1]")
start_tcp_server.add_param("config_server_start_tcp_server_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Запустисть TCP сервер"))
start_tcp_server.add_param("config_server_start_tcp_server_port_input_field").add_check(
    port_check
).set_error_msg(get_port_error("Запустисть TCP сервер"))

# Block TCP/UDP port
block_server_port = server.create_job(202, "drop tcp/udp port [0]")
block_server_port.add_param("config_server_block_tcp_udp_port_input_field").add_check(
    port_check
).set_error_msg(get_port_error("Блокировать TCP/UDP порт"))


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


def build_response(msg: str) -> Response:
    return make_response(jsonify({"message": msg}), 400)


@login_required
def delete_job():
    """
    Called when job is removed for an network device
    """
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
