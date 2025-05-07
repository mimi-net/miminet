import ipaddress


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
    packets = answer.get("packets", [])

    if not packets:
        return False, ["Вы не отправляете пакетов по сети."]

    request_path = []
    reply_path = []
    request_edges = []
    reply_edges = []

    def is_request(pkt_type):
        return (
            "ICMP echo-request" in pkt_type
            or ("UDP" in pkt_type and "> 4789" in pkt_type)
            or "GRE tunnel" in pkt_type
            or "IPIP tunnel" in pkt_type
        )

    def is_reply(pkt_type):
        return (
            "ICMP echo-reply" in pkt_type
            or ("UDP" in pkt_type and "> 4789" in pkt_type)
            or "GRE tunnel" in pkt_type
            or "IPIP tunnel" in pkt_type
        )

    for packet in packets:
        config = packet[0].get("config", {})
        pkt_type = config.get("type", "")
        src = config.get("source")
        tgt = config.get("target")
        edge_id = config.get("path")

        if is_request(pkt_type):
            if not request_path:
                if src == source_device:
                    request_path = [src, tgt]
                    request_edges = [edge_id]
            else:
                if src == request_path[-1]:
                    request_path.append(tgt)
                    request_edges.append(edge_id)

        if is_reply(pkt_type):
            if not reply_path:
                if src == target_device:
                    reply_path = [src, tgt]
                    reply_edges = [edge_id]
            else:
                if src == reply_path[-1]:
                    reply_path.append(tgt)
                    reply_edges.append(edge_id)

    if not request_path:
        hints.append(
            f"Невозможно проверить разность путей: запрос от {source_device} к {target_device} не обнаружен."
        )
    elif request_path[0] != source_device:
        hints.append(
            f"Невозможно проверить разность путей: запрос начинается не с {source_device}."
        )
    elif request_path[-1] != target_device:
        hints.append(
            f"Невозможно проверить разность путей: запрос не достиг {target_device}."
        )

    if not reply_path:
        hints.append(
            f"Невозможно проверить разность путей: ответ от {target_device} к {source_device} не обнаружен."
        )
    elif reply_path[0] != target_device:
        hints.append(
            f"Невозможно проверить разность путей: ответ начинается не с {target_device}."
        )
    elif reply_path[-1] != source_device:
        hints.append(
            f"Невозможно проверить разность путей: ответ не вернулся к {source_device}."
        )

    if hints:
        return False, hints

    if request_edges == reply_edges[::-1]:
        return False, [
            "Путь ICMP Echo Reply полностью совпадает с ICMP Echo Request (в обратную сторону), а должен быть другим."
        ]

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


def check_tunnel_echo_request(
    answer, source_device, target_device, tunnel_start, tunnel_end
):
    packets = answer.get("packets", [])
    hints = []

    if not packets:
        return False, ["Вы не отправляете запросов по сети."]

    def extract_packet_info(pkt):
        cfg = pkt[0]["config"]
        return cfg["type"], cfg["source"], cfg["target"]

    def trace_path(start, end, is_request=True):
        path = [start]
        reached = False
        current = start

        expected_type = "ICMP echo-request" if is_request else "ICMP echo-reply"
        for pkt in packets:
            ptype, src, dst = extract_packet_info(pkt)
            if src != current:
                continue

            if (
                expected_type in ptype
                or "IPIP tunnel" in ptype
                or "GRE tunnel" in ptype
            ):
                path.append(dst)
                current = dst
                if current == end:
                    reached = True
                    break

        return path, reached

    def tunnel_used_correctly(is_request=True):
        tunnel_src = tunnel_start if is_request else tunnel_end
        tunnel_dst = tunnel_end if is_request else tunnel_start

        visited = set()
        current = tunnel_src
        max_hops = 20
        tunnel_type_used = None

        for _ in range(max_hops):
            found = False
            for pkt in packets:
                ptype, src, dst = extract_packet_info(pkt)
                if src == current and dst not in visited:
                    if "IPIP tunnel" in ptype:
                        if tunnel_type_used and tunnel_type_used != "IPIP tunnel":
                            return False, None
                        tunnel_type_used = "IPIP tunnel"
                    elif "GRE tunnel" in ptype:
                        if tunnel_type_used and tunnel_type_used != "GRE tunnel":
                            return False, None
                        tunnel_type_used = "GRE tunnel"
                    else:
                        continue

                    visited.add(src)
                    current = dst
                    found = True
                    if current == tunnel_dst:
                        return True, tunnel_type_used
                    break
            if not found:
                break
        return False, None

    req_path, req_reached = trace_path(source_device, target_device, is_request=True)
    rep_path, rep_reached = trace_path(target_device, source_device, is_request=False)

    req_tunnel, req_type = tunnel_used_correctly(is_request=True)
    rep_tunnel, rep_type = tunnel_used_correctly(is_request=False)

    ok_req = req_reached
    ok_rep = rep_reached
    ok_tun = req_tunnel and rep_tunnel and req_type == rep_type and req_type is not None

    if ok_req and ok_rep and ok_tun:
        return True, []

    if not ok_req:
        if len(req_path) == 1:
            hints.append(f"Запрос от {source_device} не стартовал.")
        else:
            hints.append(
                f"Запрос дошёл только до {req_path[-1]}, а не до {target_device}."
            )
    if not req_tunnel:
        hints.append(f"Запрос не прошёл через туннель {tunnel_start}→{tunnel_end}.")
    if not ok_rep:
        if len(rep_path) == 1:
            hints.append(f"Ответ от {target_device} не стартовал.")
        else:
            hints.append(
                f"Ответ дошёл только до {rep_path[-1]}, а не до {source_device}."
            )
    if not rep_tunnel:
        hints.append(f"Ответ не прошёл через туннель {tunnel_end}→{tunnel_start}.")
    if req_type != rep_type:
        hints.append("Тип туннеля различается для запроса и ответа.")

    return False, hints


def check_vxlan_echo_request(
    answer, source_device, target_device, tunnel_start, tunnel_end
):
    packets = answer.get("packets", [])
    hints = []

    if not packets:
        return False, ["Вы не отправляете запросов по сети."]

    def extract_packet_info(pkt):
        cfg = pkt[0]["config"]
        return cfg["type"], cfg["source"], cfg["target"]

    def trace_path(start, end, is_request=True):
        path = [start]
        reached = False
        current = start

        expected_type = "ICMP echo-request" if is_request else "ICMP echo-reply"
        for pkt in packets:
            ptype, src, dst = extract_packet_info(pkt)
            if src != current:
                continue

            if expected_type in ptype or ("UDP" in ptype and "> 4789 in ptype"):
                path.append(dst)
                current = dst
                if current == end:
                    reached = True
                    break

        return path, reached

    def tunnel_used_correctly(is_request=True):
        tunnel_src = tunnel_start if is_request else tunnel_end
        tunnel_dst = tunnel_end if is_request else tunnel_start

        visited = set()
        current = tunnel_src
        max_hops = 20
        vxlan_used = False

        for _ in range(max_hops):
            found = False
            for pkt in packets:
                ptype, src, dst = extract_packet_info(pkt)
                if src == current and dst not in visited:
                    if "UDP" in ptype and "> 4789" in ptype:
                        vxlan_used = True
                        visited.add(src)
                        current = dst
                        found = True
                        if current == tunnel_dst:
                            return True, vxlan_used
                        break
            if not found:
                break
        return False, vxlan_used

    req_path, req_reached = trace_path(source_device, target_device, is_request=True)
    rep_path, rep_reached = trace_path(target_device, source_device, is_request=False)

    req_tunnel, req_vxlan = tunnel_used_correctly(is_request=True)
    rep_tunnel, rep_vxlan = tunnel_used_correctly(is_request=False)

    ok_req = req_reached
    ok_rep = rep_reached
    ok_tun = req_tunnel and rep_tunnel and req_vxlan and rep_vxlan

    if ok_req and ok_rep and ok_tun:
        return True, []

    if not ok_req:
        if len(req_path) == 1:
            hints.append(f"Запрос от {source_device} не стартовал.")
        else:
            hints.append(
                f"Запрос дошёл только до {req_path[-1]}, а не до {target_device}."
            )
    if not req_tunnel:
        hints.append(
            f"Запрос не прошёл через VXLAN-туннель {tunnel_start}→{tunnel_end}."
        )
    if not ok_rep:
        if len(rep_path) == 1:
            hints.append(f"Ответ от {target_device} не стартовал.")
        else:
            hints.append(
                f"Ответ дошёл только до {rep_path[-1]}, а не до {source_device}."
            )
    if not rep_tunnel:
        hints.append(
            f"Ответ не прошёл через VXLAN-туннель {tunnel_end}→{tunnel_start}."
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


def check_no_echo_request(answer, source_device, target_device):
    hints = []
    packets = answer.get("packets", [])

    if not packets:
        return True, []

    def has_request_reached():
        current = source_device
        for packet in packets:
            cfg = packet[0].get("config", {})
            ptype = cfg.get("type")
            src = cfg.get("source")
            dst = cfg.get("target")

            is_icmp = "ICMP echo-request" in ptype
            is_ipip = "IPIP tunnel" in ptype
            is_gre = "GRE tunnel" in ptype
            is_vxlan = "UDP" in ptype and "> 4789" in ptype

            if src == source_device and current != source_device:
                current = source_device

            if src == current and (is_icmp or is_ipip or is_gre or is_vxlan):
                current = dst
                if current == target_device:
                    return True
        return False

    if has_request_reached():
        hints.append(
            f"Обнаружен ping от {source_device} к {target_device} (включая туннели), хотя он не должен был проходить"
        )
        return False, hints
    else:
        return True, []


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

        elif command == "no-echo-request":
            points = cmd.get("points", 1)
            check_result, no_echo_hints = check_no_echo_request(answer, device, target)

            if check_result:
                points_for_host += points
            else:
                hints.extend(no_echo_hints)

        elif command == "tunnel-echo-request":
            points = cmd.get("points", 1)
            tunnel_start = cmd.get("tunnel_start")
            tunnel_end = cmd.get("tunnel_end")

            result, tunnel_hints = check_tunnel_echo_request(
                answer, device, target, tunnel_start, tunnel_end
            )

            if result:
                points_for_host += points
            else:
                hints.extend(tunnel_hints)

            different_paths_points = cmd.get("different_paths")
            if different_paths_points and result:
                import logging

                logging.info("Ща проверим")
                path_result, path_hints = check_different_paths(answer, device, target)
                if path_result:
                    points_for_host += different_paths_points.get("points", 1)
                else:
                    hints.extend(path_hints)

        elif command == "vxlan-echo-request":
            points = cmd.get("points", 1)
            tunnel_start = cmd.get("tunnel_start")
            tunnel_end = cmd.get("tunnel_end")

            result, vxlan_hints = check_vxlan_echo_request(
                answer, device, target, tunnel_start, tunnel_end
            )

            if result:
                points_for_host += points
            else:
                hints.extend(vxlan_hints)

            different_paths_points = cmd.get("different_paths")
            if different_paths_points and result:
                path_result, path_hints = check_different_paths(answer, device, target)
                if path_result:
                    points_for_host += different_paths_points.get("points", 1)
                else:
                    hints.extend(path_hints)

    return points_for_host, hints
