from abc import abstractmethod
from ast import Call
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


def job_id_generator():
    return uuid.uuid4().hex


class ResultCode:
    OK = 200
    ERROR = 400


def get_data(arg: str):
    """Get data from user's request"""
    return request.form.get(arg, type=str)


def build_response(message: str, code=ResultCode.ERROR) -> Response:
    """Create server response with specified message"""
    return make_response(jsonify({"message": message}), code)


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
    """Class with Job arguments data"""

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
        """Add new check for job param
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
    """Frontend job configurator"""

    def __init__(self, job_id: int, job_sign: str):
        """
        Args:
            job_id (int): ID that is assigned to the job in the select list (see static/config*.html files)
            job_sign (str): inscription that will be displayed above the device after adding a job
        """
        self.__job_id: int = job_id
        self.__print_cmd: str = job_sign
        self.__arg_confs: list[JobArgConfigurator] = []

    @property
    def job_id(self):
        return self.__job_id

    def add_param(self, control_id: str) -> JobArgConfigurator:
        """
        Args:
            cotrol_id (str): ID of the element with argument data
        """
        new_arg = JobArgConfigurator(control_id)
        self.__arg_confs.append(new_arg)
        return new_arg

    def configure(self) -> dict[str, str]:
        """Validate every argument and return dict with response for the user's request"""
        random_id: str = uuid.uuid4().hex  # random id for every added job
        configured_args = [arg.configure() for arg in self.__arg_confs]

        # check whether the arguments passed the checks
        for i in range(len(configured_args)):
            if configured_args[i] is None:
                # return warning for user with arg error message
                raise ArgCheckError(self.__arg_confs[i].error_msg)

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

    def add_job(self, job: JobConfigurator):
        if job.job_id in self.__jobs.keys():
            raise ValueError("This job already added")
        self.__jobs[job.job_id] = job

    def add_jobs(self, *jobs):
        for job in jobs:
            self.add_job(job)

    # [!] I have broken device configuration process into different blocks, they will be below

    def _conf_setup(self):
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
        """Update device label during configuration. Typically used at the end of the configuration"""
        # get label with device name
        label = request.form.get(f"config_{self._device_type}_name")

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
        """Configurate all added jobs"""
        job_id_str = get_data("config_host_job_select_field")

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

        iface_ids = request.form.getlist("config_host_iface_ids[]")
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
        """Configurate current network device"""
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
        self._conf_setup()
        self._conf_label_update()

        return {"message": "Конфигурация обновлена", "nodes": self._nodes}


class SwitchConfigurator(AbstractDeviceConfigurator):
    def __init__(self):
        super().__init__(device_type="switch")

    def _conf_main(self):
        self._conf_setup()
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
        self._conf_setup()
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
    def __init__(self):
        super().__init__()
        self._device_type = "router"


# --- Network device configurators ---

hub = HubConfigurator()
switch = SwitchConfigurator()
host = HostConfigurator()
router = RouterConfigurator()

# --- Jobs ---

# ~ HOST ~
# ping -c 1 (1 param)
host_ping_job = JobConfigurator(1, "ping -c 1 [0]")
host_ping_job.add_param("config_host_ping_c_1_ip").add_check(IPv4_check).set_error_msg(
    get_ip_error("ping")
)

# ping -c 1 (with options)
host_ping_opt_job = JobConfigurator(2, "ping -c 1 [0] [1]")
host_ping_opt_job.add_param(
    "config_host_ping_with_options_options_input_field"
).add_check(emptiness_check).add_check(ascii_check).set_error_msg(
    get_opt_error("ping (с опциями)")
)
host_ping_opt_job.add_param("config_host_ping_with_options_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("ping (с опциями)"))

# send UDP data
host_udp_job = JobConfigurator(3, "send -s [0] -p udp [1]:[2]")
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
host_tcp_job = JobConfigurator(4, "send -s [0] -p tcp [1]:[2]")
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
traceroute_job = JobConfigurator(5, "traceroute -n [0] [1]")
traceroute_job.add_param(
    "config_host_traceroute_with_options_options_input_field"
).add_check(emptiness_check).add_check(ascii_check).set_error_msg(
    get_opt_error("traceroute -n (с опциями)")
)
traceroute_job.add_param(
    "config_host_traceroute_with_options_ip_input_field"
).add_check(IPv4_check).set_error_msg(get_ip_error("traceroute -n (с опциями)"))

# Add route
add_route_job = JobConfigurator(102, "ip route add [0]/[1] via [2]")
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
arp_job = JobConfigurator(103, "arp -s [0] [1]")
arp_job.add_param("config_host_add_arp_cache_ip_input_field").add_check(
    IPv4_check
).set_error_msg(get_ip_error("Добавить запись в ARP-cache"))
arp_job.add_param("config_host_add_arp_cache_mac_input_field").add_check(
    MAC_check
).set_error_msg('MAC-адрес для команды "Добавить запись в ARP-cache" указан неверно')

host.add_jobs(
    host_ping_job,
    host_ping_opt_job,
    host_udp_job,
    host_tcp_job,
    traceroute_job,
    add_route_job,
    arp_job,
)

# ~ ROUTER ~

# ping
router_ping_job = JobConfigurator(1, "ping -c 1 [0]")
router_ping_job.add_param("config_router_ping_c_1_ip").add_check(
    IPv4_check
).set_error_msg(get_ip_error("ping"))

# add IP/mask
add_ip_job = JobConfigurator(100, "ip addess add [0]/[1] dev [2]")
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
nat_job = JobConfigurator(101, "add nat -o [0] -j masquerad")
nat_job.add_param("config_router_add_nat_masquerade_iface_select_field").add_check(
    emptiness_check
).set_error_msg('Не указан интерфейс для команды "Включить NAT masquerade"')

# Add route
router_add_route_job = JobConfigurator(102, "ip route add [0]/[1] via [2]")
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
vlan_job = JobConfigurator(104, "subinterface [0]:[1] VLAN [2]")
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
ipip_job = JobConfigurator(105, "ipip: [3] from [0] to [1] \n[3]: [2]")
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
gre_job = JobConfigurator(106, "gre: [3] from [0] to [1] \n[3]: [2]")
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

router.add_jobs(
    router_ping_job,
    add_ip_job,
    nat_job,
    router_add_route_job,
    vlan_job,
    ipip_job,
    gre_job,
)


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
    user = current_user
    ret = {}

    if request.method == "POST":
        network_guid = request.form.get("net_guid", type=str)

        if not network_guid:
            ret.update({"message": "Не указан параметр net_guid"})
            return make_response(jsonify(ret), 400)

        net = (
            Network.query.filter(Network.guid == network_guid)
            .filter(Network.author_id == user.id)
            .first()
        )

        if not net:
            ret.update({"message": "Такая сеть не найдена"})
            return make_response(jsonify(ret), 400)

        router_id = request.form.get("router_id")

        if not router_id:
            ret.update({"message": "Не указан параметр host_id"})
            return make_response(jsonify(ret), 400)

        jnet = json.loads(net.network)
        nodes = jnet["nodes"]

        nn = list(filter(lambda x: x["data"]["id"] == router_id, nodes))

        if not nn:
            ret.update({"message": "Такого раутера не существует"})
            return make_response(jsonify(ret), 400)

        node = nn[0]

        if "config_router_job_select_field" in request.form:
            # If we add new job to configuration
            job_id = int(request.form.get("config_router_job_select_field"))

            if job_id:
                if not jnet.get("jobs"):
                    jnet["jobs"] = []

                job_level = len(jnet["jobs"])
                if job_level < 20:
                    # ping -c 1 (1 param)
                    if job_id == 1:
                        job_1_arg_1 = request.form.get("config_router_ping_c_1_ip")

                        if job_1_arg_1:
                            jnet["jobs"].append(
                                {
                                    "id": job_id_generator(),
                                    "level": job_level,
                                    "job_id": job_id,
                                    "host_id": node["data"]["id"],
                                    "arg_1": job_1_arg_1,
                                    "print_cmd": "ping -c 1 " + job_1_arg_1,
                                }
                            )
                        else:
                            ret.update(
                                {"warning": "Не указан IP адрес для команды ping"}
                            )

                    # add IP/mask
                    if job_id == 100:
                        job_100_arg_1 = request.form.get(
                            "config_router_add_ip_mask_iface_select_field"
                        )
                        job_100_arg_2 = request.form.get(
                            "config_router_add_ip_mask_ip_input_field"
                        )

                        if not job_100_arg_1:
                            ret.update(
                                {
                                    "warning": (
                                        'Не указан интерфейс адрес для команды "Добавить IP'
                                        ' адрес"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if not job_100_arg_2:
                            ret.update(
                                {
                                    "warning": (
                                        'Не указан IP адрес для команды "Добавить IP адрес"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if (
                            "config_router_add_ip_mask_mask_input_field"
                            not in request.form
                        ):
                            ret.update(
                                {
                                    "warning": (
                                        'Не указана маска для команды "Добавить IP адрес"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        job_100_arg_3 = int(
                            request.form.get(
                                "config_router_add_ip_mask_mask_input_field"
                            )
                        )

                        if job_100_arg_3 < 0 or job_100_arg_3 > 32:
                            ret.update(
                                {
                                    "warning": (
                                        'Маска для команды "Добавить IP адрес" указана'
                                        " неверно. Допустимые значения от 0 до 32."
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        try:
                            socket.inet_aton(job_100_arg_2)
                            jnet["jobs"].append(
                                {
                                    "id": job_id_generator(),
                                    "level": job_level,
                                    "job_id": job_id,
                                    "host_id": node["data"]["id"],
                                    "arg_1": job_100_arg_1,
                                    "arg_2": job_100_arg_2,
                                    "arg_3": job_100_arg_3,
                                    "print_cmd": (
                                        "ip addess add "
                                        + str(job_100_arg_2)
                                        + "/"
                                        + str(job_100_arg_3)
                                        + " dev "
                                        + str(job_100_arg_1)
                                    ),
                                }
                            )
                        except Exception:
                            ret.update(
                                {
                                    "warning": (
                                        'IP адрес для команды "Добавить IP адрес" указан'
                                        " неверно."
                                    )
                                }
                            )

                    # add NAT masquerade to the interface
                    if job_id == 101:
                        job_101_arg_1 = request.form.get(
                            "config_router_add_nat_masquerade_iface_select_field"
                        )

                        if not job_101_arg_1 or job_101_arg_1 == "0":
                            ret.update(
                                {
                                    "warning": (
                                        'Не указан интерфейс для команды "Включить NAT'
                                        ' masquerade"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        jnet["jobs"].append(
                            {
                                "id": job_id_generator(),
                                "level": job_level,
                                "job_id": job_id,
                                "host_id": node["data"]["id"],
                                "arg_1": job_101_arg_1,
                                "print_cmd": (
                                    "add nat -o " + str(job_101_arg_1) + " -j masquerad"
                                ),
                            }
                        )

                    # Add route
                    if job_id == 102:
                        job_102_arg_1 = request.form.get(
                            "config_router_add_route_ip_input_field"
                        )
                        job_102_arg_2 = int(
                            request.form.get("config_router_add_route_mask_input_field")
                        )
                        job_102_arg_3 = request.form.get(
                            "config_router_add_route_gw_input_field"
                        )

                        if not job_102_arg_1:
                            ret.update(
                                {
                                    "warning": (
                                        'Не указан IP адрес для команды "Добавить маршрут"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if job_102_arg_2 < 0 or job_102_arg_2 > 32:
                            ret.update(
                                {
                                    "warning": (
                                        'Маска для команды "Добавить маршрут" указана'
                                        " неверно. Допустимые значения от 0 до 32."
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if not job_102_arg_3:
                            ret.update(
                                {
                                    "warning": (
                                        'Не указан IP адрес шлюза для команды "Добавить'
                                        ' маршрут"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        try:
                            socket.inet_aton(job_102_arg_1)
                            socket.inet_aton(job_102_arg_3)
                            jnet["jobs"].append(
                                {
                                    "id": job_id_generator(),
                                    "level": job_level,
                                    "job_id": job_id,
                                    "host_id": node["data"]["id"],
                                    "arg_1": job_102_arg_1,
                                    "arg_2": job_102_arg_2,
                                    "arg_3": job_102_arg_3,
                                    "print_cmd": (
                                        "ip route add "
                                        + str(job_102_arg_1)
                                        + "/"
                                        + str(job_102_arg_2)
                                        + " via "
                                        + str(job_102_arg_3)
                                    ),
                                }
                            )
                        except Exception:
                            ret.update(
                                {
                                    "warning": (
                                        'IP адрес для команды "Добавить маршрут" указан'
                                        " неверно."
                                    )
                                }
                            )

                    if job_id == 104:
                        job_104_arg_1 = request.form.get(
                            "config_router_add_subinterface_iface_select_field"
                        )
                        job_104_arg_2 = request.form.get(
                            "config_router_add_subinterface_ip_input_field"
                        )
                        job_104_arg_3 = request.form.get(
                            "config_router_add_subinterface_mask_input_field"
                        )
                        job_104_arg_4 = request.form.get(
                            "config_router_add_subinterface_vlan_input_field"
                        )

                        try:
                            socket.inet_aton(job_104_arg_2)
                            jnet["jobs"].append(
                                {
                                    "id": job_id_generator(),
                                    "level": job_level,
                                    "job_id": job_id,
                                    "host_id": node["data"]["id"],
                                    "arg_1": job_104_arg_1,
                                    "arg_2": job_104_arg_2,
                                    "arg_3": job_104_arg_3,
                                    "arg_4": job_104_arg_4,
                                    "print_cmd": f"subinterface {job_104_arg_2}:{job_104_arg_3} VLAN {job_104_arg_4}",
                                }
                            )
                        except Exception:
                            ret.update(
                                {
                                    "warning": (
                                        'IP адрес для команды "Добавить сабинтерфейс с VLAN" указан'
                                        "неверно."
                                    )
                                }
                            )

                    # Add ipip-interface
                    if job_id == 105:
                        job_105_arg_1 = request.form.get(
                            "config_router_add_ipip_tunnel_iface_select_ip_field"
                        )
                        job_105_arg_2 = request.form.get(
                            "config_router_add_ipip_tunnel_end_ip_input_field"
                        )
                        job_105_arg_3 = request.form.get(
                            "config_router_add_ipip_tunnel_interface_ip_input_field"
                        )
                        job_105_arg_4 = request.form.get(
                            "config_router_add_ipip_tunnel_interface_name_field"
                        )

                        if not job_105_arg_1 or job_105_arg_1 == "0":
                            ret.update(
                                {
                                    "warning": (
                                        'Не выбран IP адрес начальной точки для команды "Добавить IPIP-интерфейс"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if not job_105_arg_2:
                            ret.update(
                                {
                                    "warning": (
                                        'Не указан IP адрес конечной точки для команды "Добавить IPIP-интерфейс"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if not job_105_arg_3:
                            ret.update(
                                {
                                    "warning": (
                                        'Не указан IP адрес IPIP-интерфейса для команды "Добавить IPIP-интерфейс"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if not job_105_arg_4:
                            ret.update(
                                {
                                    "warning": (
                                        'Не указано название IPIP-интерфейса для команды "Добавить IPIP-интерфейс"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if not bool(
                            re.match("^[A-Za-z][A-Za-z0-9_-]{1,14}$", job_105_arg_4)
                        ):
                            ret.update(
                                {
                                    "warning": (
                                        'Название IPIP-интерфейса для команды "Добавить IPIP-интерфейс" указано неверно. '
                                        "Допустимая длина от 2 до 15, допустимые символы: a-z, A-Z, 0-9, -, _."
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        try:
                            socket.inet_aton(job_105_arg_2)
                            socket.inet_aton(job_105_arg_3)
                            jnet["jobs"].append(
                                {
                                    "id": job_id_generator(),
                                    "level": job_level,
                                    "job_id": job_id,
                                    "host_id": node["data"]["id"],
                                    "arg_1": job_105_arg_1,
                                    "arg_2": job_105_arg_2,
                                    "arg_3": job_105_arg_3,
                                    "arg_4": job_105_arg_4,
                                    "print_cmd": (
                                        f"ipip: {job_105_arg_4} from {job_105_arg_1} to {job_105_arg_2} \n{job_105_arg_4}: {job_105_arg_3}"
                                    ),
                                }
                            )
                        except Exception:
                            ret.update(
                                {
                                    "warning": (
                                        'IP адрес(а) для команды "Добавить IPIP-интерфейс" указан(ы)'
                                        " неверно."
                                    )
                                }
                            )

                    if job_id == 106:
                        # GRE Interface
                        job_106_start_ip = request.form.get(
                            "config_router_add_gre_interface_select_ip_field"
                        )
                        job_106_end_ip = request.form.get(
                            "config_router_add_gre_interface_end_ip_input_field"
                        )
                        job_106_iface_ip = request.form.get(
                            "config_router_add_gre_interface_ip_input_field"
                        )
                        job_106_iface_name = request.form.get(
                            "config_router_add_gre_interface_name_field"
                        )

                        if not job_106_start_ip or job_106_start_ip == "0":
                            ret.update(
                                {
                                    "warning": (
                                        'Не выбран интерфейс начальной точки для команды "Добавить GRE-интерфейс"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if not job_106_end_ip:
                            ret.update(
                                {
                                    "warning": (
                                        'Не указан IP адрес конечной точки для команды "Добавить GRE-интерфейс"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if not job_106_iface_ip:
                            ret.update(
                                {
                                    "warning": (
                                        'Не указан IP адрес для GRE-интерфейса для команды "Добавить GRE-интерфейс"'
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        if not job_106_iface_name:
                            ret.update(
                                {"warning": ("Не указано название для GRE-интерфейса")}
                            )
                            return make_response(jsonify(ret), 200)

                        if not bool(
                            re.match(
                                "^[A-Za-z][A-Za-z0-9_-]{1,14}$", job_106_iface_name
                            )
                        ):
                            ret.update(
                                {
                                    "warning": (
                                        "Название GRE-интерфейса указано неверно. "
                                        "Допустимая длина от 2 до 15, допустимые символы: a-z, A-Z, 0-9, -, _."
                                    )
                                }
                            )
                            return make_response(jsonify(ret), 200)

                        try:
                            socket.inet_aton(job_106_start_ip)
                            socket.inet_aton(job_106_end_ip)
                            jnet["jobs"].append(
                                {
                                    "id": job_id_generator(),
                                    "level": job_level,
                                    "job_id": job_id,
                                    "host_id": node["data"]["id"],
                                    "arg_1": job_106_start_ip,
                                    "arg_2": job_106_end_ip,
                                    "arg_3": job_106_iface_ip,
                                    "arg_4": job_106_iface_name,
                                    "print_cmd": (
                                        f"gre: {job_106_iface_name} from {job_106_start_ip} to {job_106_end_ip} \n{job_106_iface_name}: {job_106_iface_ip}"
                                    ),
                                }
                            )
                        except Exception as e:
                            ret.update(
                                {
                                    "warning": (
                                        "Ошибка при добавлении GRE-интерфейса!"
                                        f"{str(repr(e))}"
                                    )
                                }
                            )

        # Set IP adresses
        iface_ids = request.form.getlist("config_router_iface_ids[]")
        for iface_id in iface_ids:
            # Do we really have that iface?
            if not node["interface"]:
                break

            ii = list(filter(lambda x: x["id"] == iface_id, node["interface"]))

            if not ii:
                continue

            interface = ii[0]

            router_ip_value = request.form.get("config_router_ip_" + str(iface_id))
            router_mask_value = request.form.get("config_router_mask_" + str(iface_id))

            # If not IP
            if not router_ip_value:
                continue

            if not router_mask_value.isdigit():
                # Check if we have 1.2.3.4/5 ?
                ip_mask = router_ip_value.split("/")
                if len(ip_mask) == 2:
                    router_ip_value = ip_mask[0]
                    router_mask_value = ip_mask[1]
                else:
                    ret.update({"warning": "Не указана маска для IP адреса"})
                    continue

            router_mask_value = int(router_mask_value)

            if router_mask_value < 0 or router_mask_value > 32:
                ret.update({"warning": "Маска подсети указана неверно"})
                continue

            try:
                socket.inet_aton(router_ip_value)
                interface["ip"] = router_ip_value
                interface["netmask"] = router_mask_value
            except Exception as e:
                print(e)
                ret.update({"warning": "IP адрес указан неверно."})
                continue

        router_label = request.form.get("config_router_name")

        if router_label:
            node["config"]["label"] = router_label
            node["data"]["label"] = node["config"]["label"]

        default_gw = request.form.get("config_router_default_gw")

        if default_gw:
            # Check if default_gw is a valid IP address
            try:
                #  ip = ipaddress.ip_address(default_gw)
                node["config"]["default_gw"] = default_gw
            except ValueError:
                ret.update(
                    {"warning": "IP адрес маршрута по умолчанию указан неверно."}
                )
                return make_response(jsonify(ret), 200)
        else:
            node["config"]["default_gw"] = ""

        # Remove all previous simulations
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()
        for s in sims:
            db.session.delete(s)

        net.network = json.dumps(jnet)
        db.session.commit()

        ret.update(
            {"message": "Конфигурация обновлена", "nodes": nodes, "jobs": jnet["jobs"]}
        )
        return make_response(jsonify(ret), 200)

    ret.update({"message": "Неверный запрос"})
    return make_response(jsonify(ret), 400)


@login_required
def save_server_config():
    user = current_user
    ret = {}

    if request.method == "POST":
        network_guid = request.form.get("net_guid", type=str)

        if not network_guid:
            ret.update({"message": "Не указан параметр net_guid"})
            return make_response(jsonify(ret), 400)

        net = (
            Network.query.filter(Network.guid == network_guid)
            .filter(Network.author_id == user.id)
            .first()
        )

        if not net:
            ret.update({"message": "Такая сеть не найдена"})
            return make_response(jsonify(ret), 400)

        server_id = request.form.get("server_id")

        if not server_id:
            ret.update({"message": "Не указан параметр server_id"})
            return make_response(jsonify(ret), 400)

        jnet = json.loads(net.network)
        nodes = jnet["nodes"]

        nn = list(filter(lambda x: x["data"]["id"] == server_id, nodes))

        if not nn:
            ret.update({"message": "Такого хоста не существует"})
            return make_response(jsonify(ret), 400)

        node = nn[0]

        # Add job?
        job_id = int(request.form.get("config_server_job_select_field"))

        if job_id:
            if not jnet.get("jobs"):
                jnet["jobs"] = []

            job_level = len(jnet["jobs"])

            if job_level < 20:
                # ping -c 1 (1 param)
                if job_id == 1:
                    job_1_arg_1 = request.form.get("config_server_ping_c_1_ip")

                    if job_1_arg_1:
                        jnet["jobs"].append(
                            {
                                "id": job_id_generator(),
                                "level": job_level,
                                "job_id": job_id,
                                "host_id": node["data"]["id"],
                                "arg_1": job_1_arg_1,
                                "print_cmd": "ping -c 1 " + job_1_arg_1,
                            }
                        )
                    else:
                        ret.update({"warning": "Не указан IP адрес для команды ping"})

                # Start UDP server
                if job_id == 200:
                    job_200_arg_1 = request.form.get(
                        "config_server_start_udp_server_ip_input_field"
                    )
                    job_200_arg_2 = request.form.get(
                        "config_server_start_udp_server_port_input_field"
                    )

                    if not job_200_arg_1:
                        ret.update(
                            {
                                "warning": (
                                    'Не указан IP адрес для команды "Запустисть UDP сервер"'
                                )
                            }
                        )
                        return make_response(jsonify(ret), 200)

                    if not job_200_arg_2:
                        ret.update(
                            {
                                "warning": (
                                    'Не указан порт для команды "Запустисть UDP сервер"'
                                )
                            }
                        )
                        return make_response(jsonify(ret), 200)

                    if int(job_200_arg_2) < 0 or int(job_200_arg_2) > 65535:
                        ret.update(
                            {
                                "warning": (
                                    'Неверно указан порт для команды "Запустить UDP сервер"'
                                )
                            }
                        )
                        return make_response(jsonify(ret), 200)

                    try:
                        socket.inet_aton(job_200_arg_1)
                        jnet["jobs"].append(
                            {
                                "id": job_id_generator(),
                                "level": job_level,
                                "job_id": job_id,
                                "host_id": node["data"]["id"],
                                "arg_1": job_200_arg_1,
                                "arg_2": int(job_200_arg_2),
                                "print_cmd": (
                                    "nc -u "
                                    + str(job_200_arg_1)
                                    + " -l "
                                    + str(job_200_arg_2)
                                ),
                            }
                        )
                    except Exception as e:
                        print(e)
                        ret.update(
                            {
                                "warning": (
                                    'IP адрес для команды "Запустить UDP сервер" указан'
                                    " неверно."
                                )
                            }
                        )

                # Start TCP server
                if job_id == 201:
                    job_201_arg_1 = request.form.get(
                        "config_server_start_tcp_server_ip_input_field"
                    )
                    job_201_arg_2 = request.form.get(
                        "config_server_start_tcp_server_port_input_field"
                    )

                    if not job_201_arg_1:
                        ret.update(
                            {
                                "warning": (
                                    'Не указан IP адрес для команды "Запустисть TCP сервер"'
                                )
                            }
                        )
                        return make_response(jsonify(ret), 200)

                    if not job_201_arg_2:
                        ret.update(
                            {
                                "warning": (
                                    'Не указан порт для команды "Запустисть TCP сервер"'
                                )
                            }
                        )
                        return make_response(jsonify(ret), 200)

                    if int(job_201_arg_2) < 0 or int(job_201_arg_2) > 65535:
                        ret.update(
                            {
                                "warning": (
                                    'Неверно указан порт для команды "Запустить TCP сервер"'
                                )
                            }
                        )
                        return make_response(jsonify(ret), 200)

                    try:
                        socket.inet_aton(job_201_arg_1)
                        jnet["jobs"].append(
                            {
                                "id": job_id_generator(),
                                "level": job_level,
                                "job_id": job_id,
                                "host_id": node["data"]["id"],
                                "arg_1": job_201_arg_1,
                                "arg_2": int(job_201_arg_2),
                                "print_cmd": (
                                    "nc "
                                    + str(job_201_arg_1)
                                    + " -l "
                                    + str(job_201_arg_2)
                                ),
                            }
                        )
                    except Exception as e:
                        print(e)
                        ret.update(
                            {
                                "warning": (
                                    'IP адрес для команды "Запустить TCP сервер" указан'
                                    " неверно."
                                )
                            }
                        )

                # Block TCP/UDP port
                if job_id == 202:
                    job_202_arg_1 = request.form.get(
                        "config_server_block_tcp_udp_port_input_field"
                    )

                    if not job_202_arg_1:
                        ret.update(
                            {
                                "warning": (
                                    'Не указан порт для команды "Блокировать TCP/UDP порт"'
                                )
                            }
                        )
                        return make_response(jsonify(ret), 200)

                    if int(job_202_arg_1) < 0 or int(job_202_arg_1) > 65535:
                        ret.update(
                            {
                                "warning": (
                                    'Неверно указан порт для команды "Блокировать TCP/UDP'
                                    ' порт"'
                                )
                            }
                        )
                        return make_response(jsonify(ret), 200)

                    try:
                        jnet["jobs"].append(
                            {
                                "id": job_id_generator(),
                                "level": job_level,
                                "job_id": job_id,
                                "host_id": node["data"]["id"],
                                "arg_1": job_202_arg_1,
                                "print_cmd": "drop tcp/udp port " + str(job_202_arg_1),
                            }
                        )
                    except Exception as e:
                        print(e)
                        ret.update(
                            {
                                "warning": (
                                    'Ошибка при добавлении job "Блокировать TCP/UDP порт'
                                )
                            }
                        )

        # Set IP adresses
        iface_ids = request.form.getlist("config_server_iface_ids[]")
        for iface_id in iface_ids:
            # Do we really have that iface?
            if not node["interface"]:
                break

            ii = list(filter(lambda x: x["id"] == iface_id, node["interface"]))

            if not ii:
                continue

            interface = ii[0]

            host_ip_value = request.form.get("config_server_ip_" + str(iface_id))
            host_mask_value = request.form.get("config_server_mask_" + str(iface_id))

            # If not IP
            if not host_ip_value:
                continue

            if not host_mask_value.isdigit():
                # Check if we have 1.2.3.4/5 ?
                ip_mask = host_ip_value.split("/")
                if len(ip_mask) == 2:
                    host_ip_value = ip_mask[0]
                    host_mask_value = ip_mask[1]
                else:
                    ret.update({"warning": "Не указана маска для IP адреса"})
                    continue

            host_mask_value = int(host_mask_value)

            if host_mask_value < 0 or host_mask_value > 32:
                ret.update({"warning": "Маска подсети указана неверно"})
                continue

            try:
                socket.inet_aton(host_ip_value)
                interface["ip"] = host_ip_value
                interface["netmask"] = host_mask_value
            except Exception:
                ret.update({"warning": "IP адрес указан неверно."})
                continue

        host_label = request.form.get("config_server_name")

        if host_label:
            node["config"]["label"] = host_label
            node["data"]["label"] = node["config"]["label"]

        default_gw = request.form.get("config_server_default_gw")

        if default_gw:
            # Check if default_gw is a valid IP address
            try:
                # ip = ipaddress.ip_address(default_gw)
                node["config"]["default_gw"] = default_gw
            except ValueError:
                ret.update(
                    {"warning": "IP адрес маршрута по умолчанию указан неверно."}
                )
                return make_response(jsonify(ret), 200)
        else:
            node["config"]["default_gw"] = ""

        # Remove all previous simulations
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()
        for s in sims:
            db.session.delete(s)

        net.network = json.dumps(jnet)
        db.session.commit()

        ret.update(
            {"message": "Конфигурация обновлена", "nodes": nodes, "jobs": jnet["jobs"]}
        )
        return make_response(jsonify(ret), 200)

    ret.update({"message": "Неверный запрос"})
    return make_response(jsonify(ret), 400)


@login_required
def delete_job():
    """
    Called when job is removed for an network element
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
