import json
import os
import uuid

from openai import OpenAI
import urllib.request
import urllib.error
from flask import jsonify, make_response, redirect, request, url_for
from flask_login import current_user, login_required
from miminet_model import Network, db

SYSTEM_PROMPT = """Ты — генератор учебных сетевых топологий для эмулятора Miminet.
Отвечай ТОЛЬКО валидным JSON, без пояснений, без markdown, без ```json.

КРИТИЧЕСКИЕ ПРАВИЛА ДЛЯ JSON:
1. Каждый edge имеет уникальный id вида edge_XXXXXXXX (8 случайных букв/цифр)
2. Каждый edge соединяет ровно два узла: source и target
3. Каждый узел имеет ровно столько интерфейсов, сколько у него соединений (edges)
4. Поле connect в интерфейсе = id того edge, к которому подключён интерфейс
5. НЕТ изолированных узлов — каждый узел соединён хотя бы с одним другим
6. Между двумя узлами всегда только ОДИН edge (без дублирующихся соединений)

ТИПЫ УСТРОЙСТВ (используй точно такие значения в config.type и classes):
- Хост:     classes:["host"],      config.type:"host"
- Сервер:   classes:["server"],    config.type:"server"
- Свитч L2: classes:["l2_switch"], config.type:"l2_switch"
- Роутер L3: classes:["l3_router"], config.type:"router"  ← ВАЖНО: type именно "router", не "l3_router"

ПРАВИЛА ДЛЯ ИНТЕРФЕЙСОВ:
- У l2_switch интерфейсы БЕЗ ip и netmask: {"connect":"...","id":"...","name":"..."}
- У host, server, роутера поля ip и netmask ПУСТЫЕ: {"connect":"...","id":"...","name":"...","ip":"","netmask":0}
- default_gw у всех узлов всегда ""

ПРАВИЛА ДЛЯ ОПИСАНИЯ (description):
- Опиши задачу для студента: что нужно настроить и какой результат проверить
- НЕ указывай конкретные IP адреса — студент выбирает их сам
- Упомяни конкретные имена устройств из топологии (host1, router1 и т.д.)
- Пример хорошего описания: "Разделите сеть на две подсети. Назначьте IP-адреса на всех устройствах. Настройте маршрутизацию так, чтобы host1 мог достичь host3 через router1."
- Пример плохого описания: "Настройте host1: 192.168.1.10/24" — конкретные адреса указывать нельзя

ПРИМЕР ТОПОЛОГИИ (2 хоста через коммутатор):
{"title":"Два хоста в одной сети","description":"Объедините host1 и host2 в одну сеть через коммутатор sw1. Назначьте IP-адреса из одной подсети на оба хоста. Проверьте связность командой ping с host1 на host2.","nodes":[{"classes":["host"],"config":{"label":"host1","type":"host","default_gw":""},"data":{"id":"host1","label":"host1"},"interface":[{"connect":"edge_aa11bb22","id":"host1_1","name":"host1_1","ip":"","netmask":0}],"position":{"x":200,"y":200}},{"classes":["host"],"config":{"label":"host2","type":"host","default_gw":""},"data":{"id":"host2","label":"host2"},"interface":[{"connect":"edge_cc33dd44","id":"host2_1","name":"host2_1","ip":"","netmask":0}],"position":{"x":200,"y":400}},{"classes":["l2_switch"],"config":{"label":"sw1","type":"l2_switch","default_gw":""},"data":{"id":"sw1","label":"sw1"},"interface":[{"connect":"edge_aa11bb22","id":"sw1_1","name":"sw1_1"},{"connect":"edge_cc33dd44","id":"sw1_2","name":"sw1_2"}],"position":{"x":500,"y":300}}],"edges":[{"data":{"id":"edge_aa11bb22","source":"host1","target":"sw1","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_cc33dd44","source":"host2","target":"sw1","loss_percentage":0,"duplicate_percentage":0}}],"jobs":[],"config":{"zoom":2,"pan_x":0,"pan_y":0}}"""

TECHNOLOGY_HINTS = {
    "vlan": (
        "VLAN",
        "Требует: минимум 1 коммутатор (l2_switch), 3+ хоста разбитых на 2 VLAN. "
        "В описании: настроить VLAN на коммутаторе, разделить хосты по VLAN, проверить изоляцию и/или транк."
    ),
    "dhcp": (
        "DHCP",
        "Требует: 1 сервер (server) как DHCP-сервер, 2+ хоста. "
        "В описании: настроить DHCP-сервер на server1, хосты должны получить адреса автоматически."
    ),
    "stp": (
        "STP/RSTP",
        "Требует: 2+ коммутатора (l2_switch) с избыточными связями (кольцо). "
        "В описании: настроить STP/RSTP, убедиться что петли устранены, проверить root bridge."
    ),
    "routing": (
        "Статическая маршрутизация",
        "Требует: 1+ роутер (l3_router), 2+ подсети. "
        "В описании: настроить статические маршруты на роутере и шлюзы на хостах, проверить ping между подсетями."
    ),
    "nat": (
        "NAT",
        "Требует: 1 роутер (l3_router), внутренняя подсеть с хостами и внешняя сеть с сервером. "
        "В описании: настроить NAT на роутере, хосты внутренней сети должны достигать внешнего сервера."
    ),
}

DIFFICULTY_DEVICE_HINTS = {
    1: "Минимальная топология: ровно столько устройств сколько нужно для выбранных технологий, не больше.",
    2: "Средняя топология: добавь 1-2 лишних хоста для реалистичности, используй коммутаторы для группировки.",
    3: "Сложная топология: максимум устройств, несколько подсетей, цепочки роутеров или несколько коммутаторов с избыточными связями.",
}


def _user_prompt(technologies: list, difficulty: int) -> str:
    if not technologies:
        technologies = ["routing"]

    tech_lines = []
    for t in technologies:
        if t in TECHNOLOGY_HINTS:
            name, hint = TECHNOLOGY_HINTS[t]
            tech_lines.append(f"- {name}: {hint}")

    tech_block = "\n".join(tech_lines)
    diff_hint = DIFFICULTY_DEVICE_HINTS.get(difficulty, DIFFICULTY_DEVICE_HINTS[1])

    return f"""Создай учебную сетевую топологию со следующими технологиями:
{tech_block}

Сложность: {difficulty}/3. {diff_hint}

ОБЯЗАТЕЛЬНО:
- Сам подбери нужные устройства (host, server, l2_switch, l3_router) и их количество
- Все устройства соединены, нет изолированных узлов
- В описании: конкретные шаги настройки с именами устройств, что проверить в конце
- Без конкретных IP-адресов в описании

Только JSON, без пояснений."""


@login_required
def generate_ai_task():
    proxy_url = os.environ.get("AI_PROXY_URL", "http://172.18.0.1:5050/chat")
    allowed_techs = set(TECHNOLOGY_HINTS.keys())
    technologies = [t for t in request.args.getlist("tech") if t in allowed_techs]
    if not technologies:
        technologies = ["routing"]

    try:
        difficulty = int(request.args.get("difficulty", 1))
        if difficulty not in (1, 2, 3):
            difficulty = 1
    except (ValueError, TypeError):
        difficulty = 1

    topology = None
    last_error = None
    for _ in range(3):
        try:
            payload = json.dumps({
                "model": "mistral-small-latest",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _user_prompt(technologies, difficulty)},
                ],
            }).encode()
            req = urllib.request.Request(
                proxy_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=240) as resp:
                result = json.loads(resp.read())
            raw = result["choices"][0]["message"]["content"].strip()

            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                raw = raw.rsplit("```", 1)[0].strip()

            topology = json.loads(raw)
            break
        except json.JSONDecodeError as e:
            last_error = f"ИИ вернул невалидный JSON: {e}"
        except urllib.error.HTTPError as e:
            return make_response(jsonify({"error": f"Proxy HTTP {e.code}: {e.read().decode()}"}), 500)
        except Exception as e:
            return make_response(jsonify({"error": f"Ошибка API: {e}"}), 500)

    if topology is None:
        return make_response(jsonify({"error": last_error}), 500)

    # Нормализация типов — фронтенд ожидает "router", а не "l3_router"
    for node in topology.get("nodes", []):
        cfg = node.get("config", {})
        if cfg.get("type") == "l3_router":
            cfg["type"] = "router"
        if cfg.get("type") == "router" and "l3_router" in node.get("classes", []):
            node["classes"] = ["l3_router"]

    # Убираем дублирующиеся рёбра между одними и теми же узлами
    seen_pairs = set()
    unique_edges = []
    for edge in topology.get("edges", []):
        d = edge.get("data", {})
        pair = frozenset([d.get("source"), d.get("target")])
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            unique_edges.append(edge)
    topology["edges"] = unique_edges

    title = topology.pop("title", "AI-задача")
    description = topology.pop("description", "")
    network_json = json.dumps({
        "nodes": topology.get("nodes", []),
        "edges": topology.get("edges", []),
        "jobs": topology.get("jobs", []),
        "config": topology.get("config", {"zoom": 2, "pan_x": 0, "pan_y": 0}),
    })

    net = Network(
        author_id=current_user.id,
        guid=str(uuid.uuid4()),
        title=title,
        description=description,
        network=network_json,
    )
    db.session.add(net)
    db.session.commit()

    return redirect(url_for("web_network", guid=net.guid))
