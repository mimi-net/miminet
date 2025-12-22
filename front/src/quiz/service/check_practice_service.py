import ipaddress
import logging

import quiz.service.check_host_service as chs
from quiz.service.check_network_service import check_network_configuration

logger = logging.getLogger(__name__)


def _log(level, event, extra):
    logger.log(level, event, extra=extra)

def check_in_one_network_with(requirement, answer, device):
    points = 0
    hints = []

    target_id = requirement.get("target")
    points_awarded = requirement.get("points", 1)
    # Log start of in_one_network_with check
    _log(
        logging.DEBUG,
        "in_one_network_with_start",
        {
            "device": device,
            "target": target_id,
            "points_awarded": points_awarded,
        },
    )

    if not target_id:
        hints.append("Целевое устройство не указано.")
        return points, hints

    nodes = answer.get("nodes", [])
    host_node = next((n for n in nodes if n["data"]["id"] == device), None)
    target_node = next((n for n in nodes if n["data"]["id"] == target_id), None)

    if not host_node or not target_node:
        hints.append(f"Не удалось найти одно из устройств: {device}, {target_id}.")
        return points, hints

    def get_networks(node):
        networks = set()
        for interface in node.get("interface", []):
            ip = interface.get("ip")
            mask = interface.get("netmask")

            if ip and mask:
                try:
                    cidr = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
                    networks.add(cidr)
                except Exception:
                    hints.append(f"Некорректный IP или маска: {ip}/{mask}")
        return networks

    host_networks = get_networks(host_node)
    target_networks = get_networks(target_node)

    if not host_networks or not target_networks:
        hints.append("Не удалось определить IP-сети одного из устройств.")
        return points, hints

    for net1 in host_networks:
        for net2 in target_networks:
            if net1.overlaps(net2):
                points = points_awarded
                _log(
                    logging.INFO,
                    "in_one_network_with_success",
                    {
                        "device": device,
                        "target": target_id,
                        "network": str(net1),
                        "awarded": points,
                    },
                )
                return points, hints

    hints.append(f"{device} и {target_id} не находятся в одной сети.")
    # Log failure to be in same network and awarded points (usually 0)
    _log(
        logging.INFO,
        "in_one_network_with_fail",
        {
            "device": device,
            "target": target_id,
            "awarded": points,
            "hints": hints,
        },
    )
    return points, hints


def check_abstract_ip_equal(abstract_equal, answer, device):
    points = 0
    hints = []

    if not abstract_equal:
        return points, hints

    # Log parameters before abstract IP equality check
    _log(
        logging.DEBUG,
        "abstract_ip_equal_start",
        {
            "device": device,
            "to": abstract_equal.get("to"),
            "expected_equal_with": abstract_equal.get("expected_equal_with"),
            "points_awarded": abstract_equal.get("points", 1),
        },
    )

    nodes = answer["nodes"]
    edges = answer["edges"]

    to_node_id = abstract_equal.get("to")
    expected_equal_with = abstract_equal.get("expected_equal_with")
    points_awarded = abstract_equal.get("points", 1)

    device_node = next((n for n in nodes if n["data"]["id"] == device), None)
    to_node = next((n for n in nodes if n["data"]["id"] == to_node_id), None)
    compare_node = next(
        (n for n in nodes if n["data"]["id"] == expected_equal_with), None
    )

    if not device_node or not to_node or not compare_node:
        hints.append(
            f"Не удалось найти одно из устройств: {device}, {to_node_id}, {expected_equal_with}"
        )
        return points, hints

    device_ips_to_to_node = set()
    for intf in device_node.get("interface", []):
        edge_id = intf.get("connect")
        ip = intf.get("ip")
        if not edge_id or not ip:
            continue
        edge = next((e for e in edges if e["data"]["id"] == edge_id), None)
        if not edge:
            continue
        connected = (
            edge["data"]["target"]
            if edge["data"]["source"] == device
            else edge["data"]["source"]
        )
        if connected == to_node_id:
            device_ips_to_to_node.add(ip)

    if not device_ips_to_to_node:
        hints.append(
            f"Устройство {device} не имеет интерфейсов, направленных к {to_node_id}."
        )
        return 0, hints

    compare_ips = {
        intf.get("ip") for intf in compare_node.get("interface", []) if intf.get("ip")
    }

    common_ips = device_ips_to_to_node.intersection(compare_ips)
    if common_ips:
        points = max(points_awarded, 0)
        # Log successful abstract IP equality and awarded points
        _log(
            logging.INFO,
            "abstract_ip_equal_success",
            {
                "device": device,
                "to": to_node_id,
                "compare": expected_equal_with,
                "common_ips": list(common_ips),
                "awarded": points,
            },
        )
    else:
        hints.append(
            f"IP-адреса интерфейсов {device}, направленных к {to_node_id}, не совпадают ни с одним IP-адресом интерфейсов {expected_equal_with}."
        )

        if points_awarded < 0:
            points = points_awarded
    # Log final abstract IP equality result and hints
    _log(
        logging.INFO,
        "abstract_ip_equal_result",
        {
            "device": device,
            "to": to_node_id,
            "compare": expected_equal_with,
            "awarded": points,
            "hints": hints,
        },
    )

    return points, hints


def check_host(requirement, answer, device):
    points_for_host = 0
    points = 0
    hints = []

    nodes = answer["nodes"]
    host_node = next((node for node in nodes if node["data"]["id"] == device), None)

    if not host_node:
        hints.append(f"Устройство {device} не найдено в сети.")
        return points_for_host, hints

    # Log start of host check and requirement keys
    _log(
        logging.DEBUG,
        "practice_check_host_start",
        {"device": device, "requirement_keys": list(requirement.keys())},
    )

    # Checking commands (ping in particular)
    cmd = requirement.get("cmd")
    if cmd:
        # Log command check input
        _log(
            logging.DEBUG,
            "practice_cmd_check",
            {"device": device, "cmd": cmd},
        )
        points_for_cmd, cmd_hints = chs.process_host_command(cmd, answer, device)
        points_for_host += points_for_cmd
        hints.extend(cmd_hints)
        # Log command check result and awarded points
        _log(
            logging.INFO,
            "practice_cmd_result",
            {
                "device": device,
                "awarded": points_for_cmd,
                "host_total": points_for_host,
                "hints": cmd_hints,
            },
        )

    # Checking for identical VLANs
    all_vlan_conditions_passed = True
    equal_vlan_hints_all = []

    equal_vlan_targets = []
    equal_vlan_id = requirement.get("equal_vlan_id")
    if equal_vlan_id:
        targets = equal_vlan_id.get("targets", [])
        equal_vlan_targets = targets
        equal_vlan_points = equal_vlan_id.get("points", 1)
        # Log VLAN equality check input
        _log(
            logging.DEBUG,
            "practice_equal_vlan_check",
            {"device": device, "targets": targets, "points": equal_vlan_points},
        )

        equal_vlan_hints_all = []

        for target in targets:
            result, equal_vlan_hints = chs.check_vlan_id(
                answer, device, target, expected_equal=True
            )
            if not result:
                all_vlan_conditions_passed = False
                hints.extend(equal_vlan_hints)
                equal_vlan_hints_all.extend(equal_vlan_hints)

    equal_vlan_awarded = (
        equal_vlan_points if all_vlan_conditions_passed and equal_vlan_id else 0
    )
    if all_vlan_conditions_passed:
        points_for_host += equal_vlan_points
    # Log VLAN equality result and points
    _log(
        logging.INFO,
        "practice_equal_vlan_result",
            {
                "device": device,
                "targets": equal_vlan_targets,
                "awarded": equal_vlan_awarded,
                "host_total": points_for_host,
                "hints": equal_vlan_hints_all if not all_vlan_conditions_passed else [],
            },
        )

    # Checking for different VLANs
    all_vlan_conditions_passed = True
    no_equal_vlan_hints_all = []

    no_equal_vlan_targets = []
    no_equal_vlan_id = requirement.get("no_equal_vlan_id")
    if no_equal_vlan_id:
        targets = no_equal_vlan_id.get("targets", [])
        no_equal_vlan_targets = targets
        no_equal_vlan_points = no_equal_vlan_id.get("points", 1)
        # Log VLAN inequality check input
        _log(
            logging.DEBUG,
            "practice_no_equal_vlan_check",
            {"device": device, "targets": targets, "points": no_equal_vlan_points},
        )

        no_equal_vlan_hints_all = []

        for target in targets:
            result, no_equal_vlan_hints = chs.check_vlan_id(
                answer, device, target, expected_equal=False
            )
            if not result:
                all_vlan_conditions_passed = False
                hints.extend(no_equal_vlan_hints)
                no_equal_vlan_hints_all.extend(no_equal_vlan_hints)

    no_equal_vlan_awarded = (
        no_equal_vlan_points if all_vlan_conditions_passed and no_equal_vlan_id else 0
    )
    if all_vlan_conditions_passed:
        points_for_host += no_equal_vlan_points
    # Log VLAN inequality result and points
    _log(
        logging.INFO,
            "practice_no_equal_vlan_result",
            {
                "device": device,
                "targets": no_equal_vlan_targets,
                "awarded": no_equal_vlan_awarded,
                "host_total": points_for_host,
                "hints": no_equal_vlan_hints_all if not all_vlan_conditions_passed else [],
            },
        )

    # Checking for the privacy of an IP address
    ip_check = requirement.get("ip_check")
    if ip_check:
        points = ip_check.get("points", 1)
        target_node_id = ip_check.get("to")
        # Log IP privacy check input
        _log(
            logging.DEBUG,
            "practice_ip_check",
            {"device": device, "target": target_node_id, "points": points},
        )

        ip_check_hints = []
        before = points_for_host

        target_node = next(
            (node for node in nodes if node["data"]["id"] == target_node_id), None
        )

        if not target_node:
            hints.append(
                f"Целевое устройство {target_node_id} для проверки приватности ip-адреса не найдено в сети."
            )
            ip_check_hints.append(
                f"Целевое устройство {target_node_id} для проверки приватности ip-адреса не найдено в сети."
            )

        for interface in host_node.get("interface", []):
            edge_id = interface.get("connect")

            if not edge_id:
                hints.append(
                    f"Интерфейс на устройстве {device} не подключен к {target_node_id}."
                )
                ip_check_hints.append(
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
                ip_check_hints.append(
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
                    ip_check_hints.append(
                        f"IP-адрес {source_ip} на устройстве {device} не является приватным."
                    )
            else:
                hints.append(
                    f"Устройство {device} не подключено к {target_node_id}. Проверка приватности IP-адреса невозможна."
                )
                ip_check_hints.append(
                    f"Устройство {device} не подключено к {target_node_id}. Проверка приватности IP-адреса невозможна."
                )
        awarded_ip_check = points_for_host - before
        # Log IP privacy check result and points
        _log(
            logging.INFO,
            "practice_ip_check_result",
            {
                "device": device,
                "target": target_node_id,
                "awarded": awarded_ip_check,
                "host_total": points_for_host,
                "hints": ip_check_hints,
            },
        )

    # Checking whether the default gateway is configured
    required_default_gw = requirement.get("default_gw")
    if required_default_gw:
        points = required_default_gw.get("points", 1)
        actual_default_gw = host_node["config"].get("default_gw")
        # Log default gateway absence check input
        _log(
            logging.DEBUG,
            "practice_default_gw_check",
            {
                "device": device,
                "expected_absent": True,
                "actual": actual_default_gw,
                "points": points,
            },
        )

        default_gw_hints = []
        before = points_for_host

        if not actual_default_gw:
            points_for_host += points
        else:
            hints.append(
                f"Вы настроили маршрут по умолчанию ({actual_default_gw}) у {device}, но по условию задания это не требовалось."
            )
            default_gw_hints.append(
                f"Вы настроили маршрут по умолчанию ({actual_default_gw}) у {device}, но по условию задания это не требовалось."
            )
        awarded_default_gw = points_for_host - before
        # Log default gateway check result and points
        _log(
            logging.INFO,
            "practice_default_gw_result",
            {
                "device": device,
                "awarded": awarded_default_gw,
                "host_total": points_for_host,
                "hints": default_gw_hints,
            },
        )

    # Mask check
    mask_check = requirement.get("mask_check")
    if mask_check:
        points = mask_check.get("points", 1)
        target = mask_check.get("to")
        expected_mask = mask_check.get("subnet_mask")
        # Log subnet mask check input
        _log(
            logging.DEBUG,
            "practice_mask_check",
            {
                "device": device,
                "target": target,
                "expected_mask": expected_mask,
                "points": points,
            },
        )

        result, mask_hints = chs.check_subnet_mask(
            answer, device, target, expected_mask
        )

        awarded_mask = 0
        if result:
            points_for_host += points
            awarded_mask = points
        else:
            hints.extend(mask_hints)
        # Log subnet mask check result and points
        _log(
            logging.INFO,
            "practice_mask_check_result",
            {
                "device": device,
                "target": target,
                "awarded": awarded_mask,
                "host_total": points_for_host,
                "hints": mask_hints if not result else [],
            },
        )

    # Check for a specific IP address
    ip_equal = requirement.get("ip_equal")
    if ip_equal:
        points = ip_equal.get("points", 1)
        expected_ip = ip_equal.get("expected_ip")
        target_node_id = ip_equal.get("to")
        # Log specific IP check input
        _log(
            logging.DEBUG,
            "practice_ip_equal_check",
            {
                "device": device,
                "target": target_node_id,
                "expected_ip": expected_ip,
                "points": points,
            },
        )

        found = False
        ip_equal_hints = []

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
                    ip_equal_hints.append(
                        f"IP-адрес интерфейса на устройстве {device}, подключенного к {target_node_id}, должен быть {expected_ip}, но найден {actual_ip}."
                    )

        if not found:
            hints.append(
                f"Не найден интерфейс на устройстве {device}, подключённый к {target_node_id} с IP {expected_ip}."
            )
            ip_equal_hints.append(
                f"Не найден интерфейс на устройстве {device}, подключённый к {target_node_id} с IP {expected_ip}."
            )

        # Log specific IP check result and points
        _log(
            logging.INFO,
            "practice_ip_equal_result",
            {
                "device": device,
                "target": target_node_id,
                "expected_ip": expected_ip,
                "awarded": points if found else 0,
                "host_total": points_for_host,
                "hints": ip_equal_hints,
            },
        )

    # abstract_ip_equal
    abstract_equal = requirement.get("abstract_ip_equal")
    if abstract_equal:
        points, abstract_hints = check_abstract_ip_equal(abstract_equal, answer, device)
        points_for_host += points
        hints.extend(abstract_hints)
        # Log abstract IP equality aggregation result
        _log(
            logging.INFO,
            "practice_abstract_ip_equal_result",
            {
                "device": device,
                "awarded": points,
                "host_total": points_for_host,
                "hints": abstract_hints,
            },
        )

    # Check if two hosts are in the same network
    in_one_network_with = requirement.get("in_one_network_with")
    if in_one_network_with:
        p, net_hints = check_in_one_network_with(in_one_network_with, answer, device)
        points_for_host += p
        hints.extend(net_hints)
        # Log same-network check result and points
        _log(
            logging.INFO,
            "practice_in_one_network_result",
            {
                "device": device,
                "awarded": p,
                "host_total": points_for_host,
                "hints": net_hints,
            },
        )

    # Log host-level summary: points and hints count
    _log(
        logging.INFO,
        "practice_check_host_done",
        {"device": device, "host_total": points_for_host, "hints_count": len(hints)},
    )

    return points_for_host, hints


def check_task(requirements, answer):
    total_points = 0
    hints = []
    # Log task-level start: counts of requirements/nodes/edges
    _log(
        logging.INFO,
        "practice_check_task_start",
        {
            "requirements_count": len(requirements),
            "nodes_count": len(answer.get("nodes", [])),
            "edges_count": len(answer.get("edges", [])),
        },
    )

    for requirement in requirements:
        for device, requirements in requirement.items():
            # Log device requirement keys before processing
            _log(
                logging.DEBUG,
                "practice_check_task_device",
                {"device": device, "requirements_keys": list(requirements.keys())},
            )
            if (
                device.startswith("host")
                or device.startswith("server")
                or device.startswith("router")
            ):
                points, device_hints = check_host(requirements, answer, device)
                total_points += points
                hints.extend(device_hints)
                # Log device result: points and hints
                _log(
                    logging.INFO,
                    "practice_device_result",
                    {
                        "device": device,
                        "awarded": points,
                        "total_points": total_points,
                        "hints": device_hints,
                    },
                )
            elif device.startswith("network"):
                points, network_hints = check_network_configuration(
                    requirements, answer
                )
                total_points += points
                hints.extend(network_hints)
                # Log network result: points and hints
                _log(
                    logging.INFO,
                    "practice_network_result",
                    {
                        "network": device,
                        "awarded": points,
                        "total_points": total_points,
                        "hints": network_hints,
                    },
                )

    # Log task-level summary: total points and hints count
    _log(
        logging.INFO,
        "practice_check_task_done",
        {"total_points": total_points, "hints_count": len(hints)},
    )
    return total_points, hints
