from abc import abstractmethod
import json

from flask import jsonify, make_response, request, Response
from flask_login import current_user
from miminet_model import Network, Simulate, db
from typing import Callable, Optional
import uuid
import ipaddress


def get_data(arg: str):
    """Get data from user's request"""
    return request.form.get(arg, type=str)


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

    def configure(self) -> dict[str, object]:
        """Validate every argument and return dict with job's data"""
        random_id: str = uuid.uuid4().hex  # random id for every added job
        configured_args = [arg.configure() for arg in self.__args]

        # insert arguments into label string
        command_label: str = self.__print_cmd

        for i, arg in enumerate(configured_args):
            if arg is None:  # check whether the arguments passed the checks
                raise ArgCheckError(self.__args[i].error_msg)
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

    def __ip_check(self, ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except:
            return False

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
                    raise ArgCheckError("Не указана маска IP-адреса для линка")

            mask_value = int(mask_value)

            if mask_value < 0 or mask_value > 32:
                raise ArgCheckError("Маска подсети для линка указана неверно")

            if not self.__ip_check(ip_value):
                raise ArgCheckError("IP-адрес для линка указан неверно")

            interface["ip"] = ip_value
            interface["netmask"] = mask_value

    def _conf_gw(self):
        default_gw = get_data(f"config_{self._device_type}_default_gw")

        if default_gw:
            if not self.__ip_check(default_gw):
                raise ArgCheckError('Неверно указан IP-адрес для шлюза по умолчанию')
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
