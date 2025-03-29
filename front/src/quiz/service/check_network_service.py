from quiz.service.check_host_service import is_private_ip


def check_network_ip_private(answer):
    nodes = answer["nodes"]

    for node in nodes:
        interfaces = node.get("interface", [])
        for interface in interfaces:
            ip = interface.get("ip")
            if ip:
                is_private = is_private_ip(ip)
                if not is_private:
                    return (
                        False,
                        f"Ip-адрес {ip} не является приватным, хотя по условию все адреса в сети должны быть приватными.",
                    )

    return True, ""


def check_vlan_id_above(answer, vlan_id_threshold):
    for node in answer["nodes"]:
        for interface in node.get("interface", []):
            vlan_id = interface.get("vlan")

            if vlan_id is None:
                continue

            if isinstance(vlan_id, int):
                if vlan_id < vlan_id_threshold:
                    return (
                        False,
                        f"В сети есть VLAN с ID {vlan_id}. Но VLAN ID должны быть больше {vlan_id_threshold}.",
                    )

            elif isinstance(vlan_id, list):
                for vlan in vlan_id:
                    if vlan < vlan_id_threshold:
                        return (
                            False,
                            f"В сети есть VLAN с ID {vlan}. Но VLAN ID должны быть больше {vlan_id_threshold}.",
                        )

    return True, ""


def check_network_configuration(requirement, answer):
    hints = []
    points_for_network = 0
    points = requirement.get("points", 1)

    ip_private = requirement.get("ip_private")
    if ip_private:
        check, hint = check_network_ip_private(answer)
        if check:
            points_for_network += points
        else:
            hints.append(hint)

    vlan_id_above = requirement.get("vlan_id_above")
    if vlan_id_above is not None:
        result, hint = check_vlan_id_above(answer, vlan_id_above)
        if result:
            points_for_network += points
        else:
            hints.append(hint)

    return points_for_network, hints
