import quiz.service.check_host_service as chs

from quiz.service.check_network_service import check_network_configuration


def check_host(requirement, answer, device):
    points_for_host = 0
    points = 0
    hints = []

    nodes = answer["nodes"]
    host_node = next((node for node in nodes if node["data"]["id"] == device), None)

    if not host_node:
        hints.append(f"Устройство {device} не найдено в сети.")
        return points_for_host, hints

    # Checking commands (ping in particular)
    cmd = requirement.get("cmd")
    if cmd:
        points_for_cmd, cmd_hints = chs.process_host_command(cmd, answer, device)
        points_for_host += points_for_cmd
        hints.extend(cmd_hints)

    # Checking for identical VLANs
    all_vlan_conditions_passed = True

    equal_vlan_id = requirement.get("equal_vlan_id")
    if equal_vlan_id:
        targets = equal_vlan_id.get("targets", [])
        points = equal_vlan_id.get("points", 1)

        for target in targets:
            result, equal_vlan_hints = chs.check_vlan_id(
                answer, device, target, expected_equal=True
            )
            if not result:
                all_vlan_conditions_passed = False
                hints.extend(equal_vlan_hints)

    if all_vlan_conditions_passed:
        points_for_host += points
        points = 0

    # Checking for different VLANs
    all_vlan_conditions_passed = True

    no_equal_vlan_id = requirement.get("no_equal_vlan_id")
    if no_equal_vlan_id:
        targets = no_equal_vlan_id.get("targets", [])
        points = no_equal_vlan_id.get("points", 1)

        for target in targets:
            result, no_equal_vlan_hints = chs.check_vlan_id(
                answer, device, target, expected_equal=False
            )
            if not result:
                all_vlan_conditions_passed = False
                hints.extend(no_equal_vlan_hints)

    if all_vlan_conditions_passed:
        points_for_host += points

    # Checking for the privacy of an IP address
    ip_check = requirement.get("ip_check")
    if ip_check:
        points = ip_check.get("points", 1)
        target_node_id = ip_check.get("to")

        target_node = next(
            (node for node in nodes if node["data"]["id"] == target_node_id), None
        )

        if not target_node:
            hints.append(
                f"Целевое устройство {target_node_id} для проверки приватности ip-адреса не найдено в сети."
            )

        for interface in host_node.get("interface", []):
            edge_id = interface.get("connect")

            if not edge_id:
                hints.append(
                    f"Интерфейс на устройстве {device} не подключен к {target_node_id}."
                )
                continue

            connected_edge = next(
                (edge for edge in answer["edges"] if edge["data"]["id"] == edge_id),
                None,
            )

            if not connected_edge:
                hints.append(
                    f"Соединение для интерфейса на устройстве {device} не найдено."
                )
                continue

            connected_node_id = (
                connected_edge["data"]["target"]
                if connected_edge["data"]["source"] == device
                else connected_edge["data"]["source"]
            )

            if connected_node_id == target_node_id:
                source_ip = interface.get("ip")
                if source_ip and chs.is_private_ip(source_ip):
                    points_for_host += points
                    break
                else:
                    hints.append(
                        f"IP-адрес {source_ip} на устройстве {device} не является приватным."
                    )
            else:
                hints.append(
                    f"Устройство {device} не подключено к {target_node_id}. Проверка приватности IP-адреса невозможна."
                )

    # Checking whether the default gateway is configured
    required_default_gw = requirement.get("default_gw")
    if required_default_gw:
        points = required_default_gw.get("points", 1)
        actual_default_gw = host_node["config"].get("default_gw")

        if not actual_default_gw:
            points_for_host += points
        else:
            hints.append(
                f"Вы настроили маршрут по умолчанию ({actual_default_gw}) у {device}, но по условию задания это не требовалось."
            )

    # Mask check
    mask_check = requirement.get("mask_check")
    if mask_check:
        points = mask_check.get("points", 1)
        target = mask_check.get("to")
        expected_mask = mask_check.get("subnet_mask")

        result, mask_hints = chs.check_subnet_mask(
            answer, device, target, expected_mask
        )

        if result:
            points_for_host += points
        else:
            hints.extend(mask_hints)

        ip_equal = requirement.get("ip_equal")

    # Check for a specific IP address
    ip_equal = requirement.get("ip_equal")
    if ip_equal:
        points = ip_equal.get("points", 1)
        expected_ip = ip_equal.get("expected_ip")
        target_node_id = ip_equal.get("to")

        found = False

        for interface in host_node.get("interface", []):
            edge_id = interface.get("connect")
            if not edge_id:
                continue

            connected_edge = next(
                (edge for edge in answer["edges"] if edge["data"]["id"] == edge_id),
                None,
            )

            if not connected_edge:
                continue

            connected_node_id = (
                connected_edge["data"]["target"]
                if connected_edge["data"]["source"] == device
                else connected_edge["data"]["source"]
            )

            if connected_node_id == target_node_id:
                actual_ip = interface.get("ip")
                if actual_ip == expected_ip:
                    points_for_host += points
                    found = True
                    break
                else:
                    hints.append(
                        f"IP-адрес интерфейса на устройстве {device}, подключенного к {target_node_id}, должен быть {expected_ip}, но найден {actual_ip}."
                    )

        if not found:
            hints.append(
                f"Не найден интерфейс на устройстве {device}, подключённый к {target_node_id} с IP {expected_ip}."
            )

    return points_for_host, hints


def check_task(task_dict, answer):
    total_points = 0
    hints = []

    for requirement in task_dict:
        for device, requirements in requirement.items():
            if (
                device.startswith("host")
                or device.startswith("server")
                or device.startswith("router")
            ):
                points, device_hints = check_host(requirements, answer, device)
                total_points += points
                hints.extend(device_hints)
            elif device.startswith("network"):
                points, network_hints = check_network_configuration(
                    requirements, answer
                )
                total_points += points
                hints.extend(network_hints)

    return total_points, hints
