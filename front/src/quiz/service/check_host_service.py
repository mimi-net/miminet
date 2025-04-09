import ipaddress
import logging


def check_subnet_mask(answer, device, target, expected_mask):
    nodes = answer["nodes"]
    edges = answer["edges"]
    hints = []
    host_node = next((node for node in nodes if node["data"]["id"] == device), None)

    if not host_node:
        hints.append(
            f"Устройство {device}, для которого требуется проверка сетевой маски, отсутствует в сети."
        )
        return False, hints

    if not host_node.get("interface"):
        hints.append(
            f"Устройство {device} не имеет интерфейсов, для которых можно было бы проверить маску."
        )
        return False, hints

    target_edge = next(
        (
            edge["data"]["id"]
            for edge in edges
            if (edge["data"]["source"] == device and edge["data"]["target"] == target)
            or (edge["data"]["source"] == target and edge["data"]["target"] == device)
        ),
        None,
    )

    if not target_edge:
        hints.append(
            f"Соединение между {device} и {target} отсутствует, проверка маски невозможна."
        )
        return False, hints

    if not any(
        interface.get("connect") == target_edge for interface in host_node["interface"]
    ):
        hints.append(
            f"Интерфейс устройства {device} не подключён к {target}, проверка маски невозможна."
        )
        return False, hints

    for interface in host_node["interface"]:
        edge = interface["connect"]

        if edge == target_edge:
            mask = interface.get("netmask")

            if str(mask) == str(expected_mask):
                return True, []
            else:
                hints.append(
                    f"Подсеть {mask} на интерфейсе устройства {device} не соответствует ожидаемой {expected_mask}."
                )

    return False, hints


def check_vlan_id(answer, device, target, expected_equal):
    nodes = answer["nodes"]
    edges = answer["edges"]
    hints = []

    device_node = next((node for node in nodes if node["data"]["id"] == device), None)
    target_node = next((node for node in nodes if node["data"]["id"] == target), None)

    if not device_node or not target_node:
        if not device_node:
            hints.append(
                f"Устройство {device} отсутствует в сети, проверка VLAN ID невозможна."
            )
        if not target_node:
            hints.append(
                f"Устройство {target} отсутствует в сети, проверка VLAN ID невозможна."
            )

        return False, hints

    def find_connected_switch(node):
        for iface in node.get("interface", []):
            edge_id = iface.get("connect")
            if not edge_id:
                continue

            connected_edge = next(
                (edge for edge in edges if edge["data"]["id"] == edge_id), None
            )
            if not connected_edge:
                continue

            connected_node_id = (
                connected_edge["data"]["target"]
                if connected_edge["data"]["source"] == node["data"]["id"]
                else connected_edge["data"]["source"]
            )

            connected_node = next(
                (n for n in nodes if n["data"]["id"] == connected_node_id), None
            )
            if connected_node and connected_node["config"]["type"] == "l2_switch":
                return connected_node

        return None

    device_switch = find_connected_switch(device_node)
    target_switch = find_connected_switch(target_node)

    if not device_switch or not target_switch:
        if not device_switch:
            hints.append(
                f"Устройство {device} не подключено к свитчу, настройка VLAN невозможна."
            )
        if not target_switch:
            hints.append(
                f"Устройство {target} не подключено к свитчу, настройка VLAN невозможна."
            )
        return False, hints

    def get_vlans_on_switch(switch, node_id):
        vlans = set()
        for iface in switch.get("interface", []):
            if iface.get("connect") and iface["connect"] in [
                iface.get("connect")
                for iface in next(
                    (n["interface"] for n in nodes if n["data"]["id"] == node_id), []
                )
            ]:
                vlan = iface.get("vlan")
                if isinstance(vlan, list):
                    vlans.update(vlan)
                elif vlan is not None:
                    vlans.add(vlan)
        return vlans

    device_vlans = get_vlans_on_switch(device_switch, device)
    target_vlans = get_vlans_on_switch(target_switch, target)

    if expected_equal:
        result = bool(device_vlans & target_vlans)
        if not result:
            hints.append(
                f"Устройства {device} и {target} не имеют общих VLAN. "
                f"Ожидалось, что они будут находиться в одном VLAN."
            )
        return result, hints
    else:
        result = not (device_vlans & target_vlans)
        if not result:
            hints.append(
                f"Устройства {device} и {target} имеют общие VLAN. "
                f"Ожидалось, что они будут находиться в разных VLAN."
            )
        return result, hints


def is_private_ip(ip):
    return ipaddress.ip_address(ip).is_private


def check_different_paths(answer, source_device, target_device):
    hints = []
    packets = answer["packets"]

    request_path = []
    reply_path = []

    for packet in packets:
        packet_type = packet[0]["config"]["type"]
        source = packet[0]["config"]["source"]
        target = packet[0]["config"]["target"]

        if "ICMP echo-request" in packet_type:
            if not request_path and source == source_device:
                request_path = [source, target]
            elif request_path and request_path[-1] == source:
                request_path.append(target)

        elif "ICMP echo-reply" in packet_type:
            if not reply_path and source == target_device:
                reply_path = [source, target]
            elif reply_path and reply_path[-1] == source:
                reply_path.append(target)

    if not request_path or not reply_path:
        hints.append("Не удалось найти полный путь для ICMP Echo Request.")
        return False, hints

    elif not reply_path:
        hints.append("Не удалось найти полный путь для ICMP Echo Reply.")
        return False, hints

    if request_path == reply_path[::-1]:
        hints.append("Пути ICMP Echo Request и Echo Reply совпадают, хотя не должны.")
        return False, hints
    else:
        return True, []


def check_path(answer, device, target, required_path):
    hints = []
    packets = answer["packets"]

    actual_path = []
    actual_path.append(device)

    is_icmp = False

    for packet in packets:
        packet_type = packet[0]["config"]["type"]

        if "ICMP" in packet_type:
            actual_path.append(packet[0]["config"]["target"])
            is_icmp = True

    if not is_icmp:
        hints.append("Вы не отправляете ICMP пакетов по сети.")

    if not (
        actual_path[0] == device
        and actual_path[-1] == device
        and actual_path[len(actual_path) // 2] == target
    ):
        if not (actual_path[0] == device):
            hints.append(
                f"Начало пути не соответствует требуемому по условию устройству {device}."
            )
        if not (actual_path[-1] == device):
            hints.append(
                f"Конец пути не соответствует требуемому по условию устройству {device}."
            )
        if not (actual_path[len(actual_path) // 2] == target):
            hints.append(f"Узел назначения {target} отсутствует в пути.")

        return False, hints

    trimmed_actual_path = actual_path[1 : len(actual_path) // 2]

    if trimmed_actual_path == required_path:
        return True, hints
    else:
        hints.append(
            f"Путь до целевого устройства не совпадает с требуемым. Требуемый:{required_path}. А Ваш: {trimmed_actual_path}."
        )
        return False, hints


def check_echo_request(answer, source_device, target_device, direction="two-way"):
    hints = []
    packets = answer.get("packets", [])

    if not packets:
        return False, ["Вы не отправляете пакетов по сети."]

    request_path = []
    reply_path = []

    for packet in packets:
        config = packet[0]["config"]
        packet_type = config["type"]
        source = config["source"]
        target = config["target"]

        if "ICMP echo-request" in packet_type:
            if source == source_device and (
                not request_path or request_path[-1] != target_device
            ):
                request_path = [source]
                reply_path = []
            if source == request_path[-1] if request_path else False:
                request_path.append(target)
        elif "ICMP echo-reply" in packet_type:
            if not reply_path and source == target_device:
                reply_path = [source]
            if reply_path and source == reply_path[-1]:
                reply_path.append(target)

    if direction == "one-way":
        valid = (
            request_path
            and request_path[0] == source_device
            and request_path[-1] == target_device
        )
    else:
        valid = (
            request_path
            and reply_path
            and request_path[0] == source_device
            and request_path[-1] == target_device
            and reply_path[0] == target_device
            and reply_path[-1] == source_device
        )

    if valid:
        return True, []
    else:
        if not request_path:
            hints.append(f"Запрос от {source_device} к {target_device} не обнаружен.")
        elif request_path[0] != source_device:
            hints.append(f"Запрос начинается не с {source_device}.")
        elif request_path[-1] != target_device:
            hints.append(f"Запрос не достиг {target_device}.")

        if direction == "two-way":
            if not reply_path:
                hints.append(f"Ответ от {target_device} не обнаружен.")
            elif reply_path[0] != target_device:
                hints.append(f"Ответ начинается не с {target_device}.")
            elif reply_path[-1] != source_device:
                hints.append(f"Ответ не вернулся к {source_device}.")

    return False, hints


def process_host_command(cmd, answer, device):
    points_for_host = 0
    hints = []

    for command, target in cmd.items():
        if command == "echo-request":
            points = cmd.get("points", 1)
            check_result, echo_hints = check_echo_request(
                answer, device, target, cmd.get("direction", "two-way")
            )

            if check_result:
                points_for_host += points
            else:
                hints.extend(echo_hints)

            path = cmd.get("path")
            if path and check_result:
                required_path = path.get("required_path")
                path_points = path.get("points", 1)

                path_result, path_hints = check_path(
                    answer, device, target, required_path
                )

                if path_result:
                    points_for_host += path_points
                else:
                    hints.extend(path_hints)

            different_paths_points = cmd.get("different_paths")
            if different_paths_points and check_result:
                path_result, path_hints = check_different_paths(answer, device, target)
                if path_result:
                    points_for_host += different_paths_points.get("points", 1)
                else:
                    hints.extend(path_hints)

    return points_for_host, hints
