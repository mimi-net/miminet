from abc import abstractmethod
import json
from celery_app import app
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
            control_id (str): ID of the element with argument data
        """
        self.__control_id: str = control_id
        self.__validators: list[Callable[[str], bool]] = []
        self.__text_filters: list[Callable[[str], str]] = []
        self.__error_msg: str = "Невозможно добавить команду: ошибка в аргументе"

    @property
    def control_id(self) -> str:
        return self.__control_id

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

    def add_filter(self, filter: Callable[[str], str]):
        """Add new filter for argument (you can add several filters)
        Args:
            filter (Callable[[str], str]): function that takes a string and returns string after filter
        """
        self.__text_filters.append(filter)

        return self

    def configure(self, value: Optional[str] = None) -> Optional[str]:
        """Get an element from the request and performs validation

        Args:
            value (Optional[str]): If provided, use this value instead of getting from request

        Returns:
            Optional[str]: None if argument didn't pass checks
        """
        if value is not None:
            arg = value
        else:
            arg = get_data(self.control_id)

        if arg is None:
            return None

        if all([validate(arg) for validate in self.__validators]):
            res = arg
            for filter in self.__text_filters:
                res = filter(res)
            if res:
                return res
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

        # fetch all raw values
        raw_values = []
        for job_arg in self.__args:
            val = get_data(job_arg.control_id)
            raw_values.append(val if val is not None else "")

        # check if we have 1.2.3.4/5
        for i in range(len(raw_values) - 1):
            val = raw_values[i]

            if val and "/" in val:
                try:
                    parts = val.split("/")
                    if len(parts) == 2 and parts[0] and parts[1]:
                        raw_values[i] = parts[0]
                        raw_values[i + 1] = parts[1]
                except Exception:
                    pass

        # configure args using processed raw_values
        configured_args = [
            self.__args[i].configure(value=raw_values[i])
            for i in range(len(self.__args))
        ]

        # insert arguments into label string
        command_label: str = self.__print_cmd

        for i, conf_arg in enumerate(configured_args):
            if conf_arg is None:  # check whether the arguments passed the checks
                raise ArgCheckError(self.__args[i].error_msg)
            command_label = command_label.replace(f"[{i}]", conf_arg)

        response = {
            "id": random_id,
            "job_id": self.__job_id,
            "print_cmd": command_label,
        }

        # add args to response
        for i, conf_arg in enumerate(configured_args):
            response[f"arg_{i+1}"] = conf_arg

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

    __MAX_JOBS_COUNT: int = 30
    __SLEEP_JOB_ID: int = 7
    __MAX_SLEEP_TIME: int = 60

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
            raise ConfigurationError(f"Не указан параметр {element_form_id}")

        # json representation
        self._json_network: dict = json.loads(self._cur_network.network)
        self._nodes: list = self._json_network["nodes"]

        # find all matches with device in nodes
        filt_nodes = list(filter(lambda n: n["data"]["id"] == device_id, self._nodes))

        if not filt_nodes and self._device_type != "edge":
            raise ConfigurationError(f"Такого '{self._device_type}' не существует")

        # current device's node
        if self._device_type != "edge":
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
            app.control.revoke(s.task_guid, terminate=False)
            db.session.delete(s)

        self._cur_network.network = json.dumps(self._json_network)
        db.session.commit()

    def _conf_jobs(self):
        """Configure jobs added to the device"""
        job_id_str = get_data(f"config_{self._device_type}_job_select_field")

        if not job_id_str:
            return

        job_id = int(job_id_str)
        if job_id not in self.__jobs.keys():
            return  # if user didn't select job

        editing_job_id = get_data("editing_job_id")

        jobs_list = self._json_network["jobs"]
        if editing_job_id:
            job_level = len([j for j in jobs_list if j["id"] != editing_job_id])
        else:
            job_level = len(jobs_list)

        if job_level >= self.__MAX_JOBS_COUNT:
            raise ConfigurationError(
                f"Достигнут лимит! В сети максимальное количество команд ({self.__MAX_JOBS_COUNT}). "
                "Для добавления новой команды удалите существующую."
            )

        job = self.__jobs[job_id]
        job_conf_res = job.configure()

        if editing_job_id:
            # Find the index of the job being edited to preserve order
            old_job_index = next(
                (i for i, j in enumerate(jobs_list) if j["id"] == editing_job_id), None
            )

            # Remove the old job
            self._json_network["jobs"] = [
                j for j in jobs_list if j["id"] != editing_job_id
            ]
            # Recalculate level after removal
            job_level = len(self._json_network["jobs"])

        job_conf_res["level"] = job_level
        job_conf_res["host_id"] = self._device_node["data"]["id"]
        sleep_job_list = [
            job
            for job in self._json_network["jobs"]
            if job["job_id"] == self.__SLEEP_JOB_ID
        ]
        current_time = sum(int(j["arg_1"]) for j in sleep_job_list)

        if job_id == self.__SLEEP_JOB_ID:
            new_job_arg = int(job_conf_res["arg_1"])
            if current_time + new_job_arg > 60:
                raise ConfigurationError(
                    f"Превышен лимит по времени для команды sleep ({self.__MAX_SLEEP_TIME} секунд на сеть)"
                )

        if editing_job_id and old_job_index is not None:
            # Insert at the same position where the old job was
            self._json_network["jobs"].insert(old_job_index, job_conf_res)
        else:
            # New job - append to the end
            self._json_network["jobs"].append(job_conf_res)

    def __ip_check(self, ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
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

            # check if split is needed.
            if "/" in ip_value:
                try:
                    parts = ip_value.split("/")
                    if len(parts) == 2:
                        ip_value = parts[0]
                        mask_value = parts[1]
                except Exception:
                    pass

            # then check mask validity
            if not mask_value or not str(mask_value).isdigit():
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
                raise ArgCheckError("Неверно указан IP-адрес для шлюза по умолчанию")
            self._device_node["config"]["default_gw"] = default_gw
        else:
            self._device_node["config"]["default_gw"] = ""

    @abstractmethod
    def _configure(self) -> dict:
        """Configuration main block in which the entire configuration process takes place"""
        pass

    def configure(self) -> Response:
        """Configure current network device"""
        try:
            res = self._configure()  # configuration result
            self.__conf_sims_delete()
            return make_response(jsonify(res), 200)
        except ConfigurationError as e:
            return make_response(jsonify({"message": str(e)}), 400)


class HubConfigurator(AbstractDeviceConfigurator):
    def __init__(self):
        super().__init__(device_type="hub")

    def _configure(self):
        self._conf_prepare()
        self._conf_label_update()

        return {"message": "Конфигурация обновлена", "nodes": self._nodes}


class SwitchConfigurator(AbstractDeviceConfigurator):
    def __init__(self):
        super().__init__(device_type="switch")

    def _configure(self):
        self._conf_prepare()
        self._conf_label_update()
        res = {}
        try:  # catch argument check errors
            self._conf_jobs()
        except ArgCheckError as e:
            res.update({"warning": str(e)})
        # RSTP/STP setup
        switch_stp = get_data("config_rstp_stp")

        self._device_node["config"]["stp"] = 0

        if switch_stp and switch_stp == "1":
            self._device_node["config"]["stp"] = 1
        elif switch_stp and switch_stp == "2":
            self._device_node["config"]["stp"] = 2

        stp_priority = get_data("config_stp_priority")

        if stp_priority:
            self._device_node["config"]["priority"] = int(stp_priority)
        res.update(
            {
                "message": "Конфигурация обновлена",
                "nodes": self._nodes,
                "jobs": self._json_network["jobs"],
            }
        )
        return res


class HostConfigurator(AbstractDeviceConfigurator):
    def __init__(self):
        super().__init__(device_type="host")

    def _configure(self):
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


class EdgeConfigurator(AbstractDeviceConfigurator):
    def __init__(self):
        super().__init__(device_type="edge")

    def _configure(self):
        self._conf_prepare()
        self._update_network_issue()

        return {
            "message": "Конфигурация обновлена",
            "edges": self._json_network["edges"],
            "nodes": self._nodes,
            "jobs": self._json_network["jobs"],
        }

    def _update_network_issue(self):
        loss = int(get_data("edge_loss"))
        duplicate = int(get_data("edge_duplicate"))
        edge_id = get_data("edge_id")

        for edge in self._json_network["edges"]:
            if edge["data"]["id"] == edge_id:
                edge["data"]["loss_percentage"] = loss
                edge["data"]["duplicate_percentage"] = duplicate
                break
        else:
            raise ConfigurationError("Ребро не найдено")
