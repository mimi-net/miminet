import json
import logging
import os
import uuid

import urllib.request
import urllib.error
from flask import jsonify, make_response, redirect, request, url_for
from flask_login import current_user, login_required
from miminet_model import Network, db

logger = logging.getLogger(__name__)

YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

SYSTEM_PROMPT = """Ты — генератор учебных сетевых топологий для эмулятора Miminet.
Отвечай ТОЛЬКО валидным JSON, без пояснений, без markdown, без ```json.

КРИТИЧЕСКИЕ ПРАВИЛА ДЛЯ JSON:
1. Каждый edge имеет уникальный id вида edge_XXXXXXXX (8 случайных букв/цифр)
2. Каждый edge соединяет ровно два узла: source и target
3. Каждый узел имеет ровно столько интерфейсов, сколько у него соединений (edges)
4. Поле connect в интерфейсе = id того edge, к которому подключён интерфейс
5. НЕТ изолированных узлов — каждый узел соединён хотя бы с одним другим
6. Между двумя узлами всегда только ОДИН edge (без дублирующихся соединений)

ЗАПРЕЩЁННЫЕ ТОПОЛОГИИ (антипаттерны):
- НЕ соединяй host с host напрямую — между хостами всегда свитч или роутер
- НЕ делай server "транзитным" узлом (host → server → switch) — сервер конечное устройство, подключай его к свитчу или роутеру напрямую  # noqa: E501
- НЕ соединяй host напрямую с роутером если в подсети несколько устройств — используй свитч

ПРАВИЛА ПОЗИЦИОНИРОВАНИЯ (поле position):
- Устройства одной подсети (подключённые к одному свитчу) располагай рядом — в кластере
- Свитч ставь в центр своей группы, хосты/серверы — вокруг него (сверху, снизу, слева)
- Роутеры ставь между группами, не внутри кластера
- Шаг между соседними узлами: 150-200 единиц
- Не ставь все узлы в одну горизонтальную или вертикальную линию

ТИПЫ УСТРОЙСТВ (используй точно такие значения в config.type и classes):
- Хост:      classes:["host"],      config.type:"host"
- Сервер:    classes:["server"],    config.type:"server"
- Свитч L2:  classes:["l2_switch"], config.type:"l2_switch"
- Роутер L3: classes:["l3_router"], config.type:"router"  ← ВАЖНО: type именно "router", не "l3_router"

ПРАВИЛА ДЛЯ ИНТЕРФЕЙСОВ:
- У l2_switch интерфейсы БЕЗ ip и netmask: {"connect":"...","id":"...","name":"..."}
- У host, server, роутера поля ip и netmask ПУСТЫЕ: {"connect":"...","id":"...","name":"...","ip":"","netmask":0}
- default_gw у всех узлов всегда ""

ПРАВИЛА ДЛЯ ОПИСАНИЯ (description):
- Топология УЖЕ создана и устройства соединены — студент только настраивает её
- Описание начинай с конкретного действия: "Назначьте...", "Настройте...", "Обеспечьте..."
- НЕ пиши "создайте", "разделите сеть", "постройте" — сеть уже построена
- НЕ указывай конкретные IP адреса — студент выбирает их сам
- Упомяни конкретные имена устройств из топологии (host_1, router_1 и т.д.)
- В конце укажи что проверить: "Проверьте связность ping с host_1 на host_3"
- ЗАПРЕЩЕНО писать любые команды Linux в описании: ip route add, ip tunnel add, ip addr, ifconfig и т.д.
- Вместо команд пиши действия через интерфейс: "добавьте маршрут на router_1", "настройте шлюз на host_1", "создайте туннель между router_1 и router_2"  # noqa: E501

ПРИМЕРЫ ТОПОЛОГИЙ:

Пример 1 (2 хоста через коммутатор — базовый):
{"title":"Два хоста в одной сети","description":"Назначьте IP-адреса из одной подсети на host_1 и host_2. Проверьте ping с host_1 на host_2.","nodes":[{"classes":["host"],"config":{"label":"host_1","type":"host","default_gw":""},"data":{"id":"host_1","label":"host_1"},"interface":[{"connect":"edge_aa11bb22","id":"host_1_1","name":"host_1_1","ip":"","netmask":0}],"position":{"x":200,"y":200}},{"classes":["host"],"config":{"label":"host_2","type":"host","default_gw":""},"data":{"id":"host_2","label":"host_2"},"interface":[{"connect":"edge_cc33dd44","id":"host_2_1","name":"host_2_1","ip":"","netmask":0}],"position":{"x":200,"y":400}},{"classes":["l2_switch"],"config":{"label":"sw_1","type":"l2_switch","default_gw":""},"data":{"id":"sw_1","label":"sw_1"},"interface":[{"connect":"edge_aa11bb22","id":"sw_1_1","name":"sw_1_1"},{"connect":"edge_cc33dd44","id":"sw_1_2","name":"sw_1_2"}],"position":{"x":500,"y":300}}],"edges":[{"data":{"id":"edge_aa11bb22","source":"host_1","target":"sw_1","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_cc33dd44","source":"host_2","target":"sw_1","loss_percentage":0,"duplicate_percentage":0}}],"jobs":[],"config":{"zoom":2,"pan_x":0,"pan_y":0}}  # noqa: E501

Пример 2 (2 хоста + треугольник из 3 роутеров — асимметричная маршрутизация):
{"title":"Асимметричная маршрутизация через 3 роутера","description":"Назначьте IP-адреса на все интерфейсы. Настройте маршруты так, чтобы пакет с host_1 на host_2 шёл через router_2, а обратный путь — через router_3. Проверьте ping с host_1 на host_2.","nodes":[{"classes":["host"],"config":{"label":"host_1","type":"host","default_gw":""},"data":{"id":"host_1","label":"host_1"},"interface":[{"connect":"edge_h1r1","id":"host_1_1","name":"host_1_1","ip":"","netmask":0}],"position":{"x":150,"y":450}},{"classes":["host"],"config":{"label":"host_2","type":"host","default_gw":""},"data":{"id":"host_2","label":"host_2"},"interface":[{"connect":"edge_h2r3","id":"host_2_1","name":"host_2_1","ip":"","netmask":0}],"position":{"x":850,"y":450}},{"classes":["l3_router"],"config":{"label":"router_1","type":"router","default_gw":""},"data":{"id":"router_1","label":"router_1"},"interface":[{"connect":"edge_h1r1","id":"router_1_1","name":"router_1_1","ip":"","netmask":0},{"connect":"edge_r1r2","id":"router_1_2","name":"router_1_2","ip":"","netmask":0},{"connect":"edge_r1r3","id":"router_1_3","name":"router_1_3","ip":"","netmask":0}],"position":{"x":150,"y":250}},{"classes":["l3_router"],"config":{"label":"router_2","type":"router","default_gw":""},"data":{"id":"router_2","label":"router_2"},"interface":[{"connect":"edge_r1r2","id":"router_2_1","name":"router_2_1","ip":"","netmask":0},{"connect":"edge_r2r3","id":"router_2_2","name":"router_2_2","ip":"","netmask":0}],"position":{"x":500,"y":100}},{"classes":["l3_router"],"config":{"label":"router_3","type":"router","default_gw":""},"data":{"id":"router_3","label":"router_3"},"interface":[{"connect":"edge_r1r3","id":"router_3_1","name":"router_3_1","ip":"","netmask":0},{"connect":"edge_r2r3","id":"router_3_2","name":"router_3_2","ip":"","netmask":0},{"connect":"edge_h2r3","id":"router_3_3","name":"router_3_3","ip":"","netmask":0}],"position":{"x":850,"y":250}}],"edges":[{"data":{"id":"edge_h1r1","source":"host_1","target":"router_1","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_r1r2","source":"router_1","target":"router_2","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_r1r3","source":"router_1","target":"router_3","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_r2r3","source":"router_2","target":"router_3","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_h2r3","source":"host_2","target":"router_3","loss_percentage":0,"duplicate_percentage":0}}],"jobs":[],"config":{"zoom":2,"pan_x":0,"pan_y":0}}  # noqa: E501

Пример 3 (2 хоста + свитч + треугольник роутеров + сервер — изоляция и асимметрия):
{"title":"Два хоста через свитч и роутеры к серверу","description":"Назначьте IP-адреса. Настройте маршруты так, чтобы host_1 и host_2 пинговали server_1, но не видели друг друга напрямую. Настройте разные пути туда и обратно. Проверьте ping с host_1 на server_1 и с host_2 на server_1.","nodes":[{"classes":["host"],"config":{"label":"host_1","type":"host","default_gw":""},"data":{"id":"host_1","label":"host_1"},"interface":[{"connect":"edge_dev_sw","id":"host_1_1","name":"host_1_1","ip":"","netmask":0}],"position":{"x":150,"y":200}},{"classes":["host"],"config":{"label":"host_2","type":"host","default_gw":""},"data":{"id":"host_2","label":"host_2"},"interface":[{"connect":"edge_tst_sw","id":"host_2_1","name":"host_2_1","ip":"","netmask":0}],"position":{"x":150,"y":380}},{"classes":["l2_switch"],"config":{"label":"l2sw_1","type":"l2_switch","default_gw":""},"data":{"id":"l2sw_1","label":"l2sw_1"},"interface":[{"connect":"edge_dev_sw","id":"l2sw_1_1","name":"l2sw_1_1"},{"connect":"edge_tst_sw","id":"l2sw_1_2","name":"l2sw_1_2"},{"connect":"edge_sw_r1","id":"l2sw_1_3","name":"l2sw_1_3"}],"position":{"x":380,"y":290}},{"classes":["l3_router"],"config":{"label":"router_1","type":"router","default_gw":""},"data":{"id":"router_1","label":"router_1"},"interface":[{"connect":"edge_sw_r1","id":"router_1_1","name":"router_1_1","ip":"","netmask":0},{"connect":"edge_r1r2","id":"router_1_2","name":"router_1_2","ip":"","netmask":0},{"connect":"edge_r1r3","id":"router_1_3","name":"router_1_3","ip":"","netmask":0}],"position":{"x":600,"y":290}},{"classes":["l3_router"],"config":{"label":"router_2","type":"router","default_gw":""},"data":{"id":"router_2","label":"router_2"},"interface":[{"connect":"edge_r1r2","id":"router_2_1","name":"router_2_1","ip":"","netmask":0},{"connect":"edge_r2r3","id":"router_2_2","name":"router_2_2","ip":"","netmask":0}],"position":{"x":820,"y":420}},{"classes":["l3_router"],"config":{"label":"router_3","type":"router","default_gw":""},"data":{"id":"router_3","label":"router_3"},"interface":[{"connect":"edge_r1r3","id":"router_3_1","name":"router_3_1","ip":"","netmask":0},{"connect":"edge_r2r3","id":"router_3_2","name":"router_3_2","ip":"","netmask":0},{"connect":"edge_r3_srv","id":"router_3_3","name":"router_3_3","ip":"","netmask":0}],"position":{"x":820,"y":160}},{"classes":["server"],"config":{"label":"server_1","type":"server","default_gw":""},"data":{"id":"server_1","label":"server_1"},"interface":[{"connect":"edge_r3_srv","id":"server_1_1","name":"server_1_1","ip":"","netmask":0}],"position":{"x":1050,"y":160}}],"edges":[{"data":{"id":"edge_dev_sw","source":"host_1","target":"l2sw_1","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_tst_sw","source":"host_2","target":"l2sw_1","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_sw_r1","source":"l2sw_1","target":"router_1","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_r1r2","source":"router_1","target":"router_2","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_r1r3","source":"router_1","target":"router_3","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_r2r3","source":"router_2","target":"router_3","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_r3_srv","source":"router_3","target":"server_1","loss_percentage":0,"duplicate_percentage":0}}],"jobs":[],"config":{"zoom":2,"pan_x":0,"pan_y":0}}  # noqa: E501

Пример 4 (4 хоста через 2 свитча — VLAN изоляция):
{"title":"Четыре хоста через два свитча с VLAN изоляцией","description":"Назначьте IP-адреса хостам. Настройте VLAN на l2sw_1 и l2sw_2 так, чтобы host_1 пинговал host_2, но широковещательные пакеты не приходили на host_3 и host_4. Проверьте ping с host_1 на host_2.","nodes":[{"classes":["host"],"config":{"label":"host_1","type":"host","default_gw":""},"data":{"id":"host_1","label":"host_1"},"interface":[{"connect":"edge_h1sw1","id":"host_1_1","name":"host_1_1","ip":"","netmask":0}],"position":{"x":200,"y":150}},{"classes":["host"],"config":{"label":"host_3","type":"host","default_gw":""},"data":{"id":"host_3","label":"host_3"},"interface":[{"connect":"edge_h3sw1","id":"host_3_1","name":"host_3_1","ip":"","netmask":0}],"position":{"x":200,"y":430}},{"classes":["l2_switch"],"config":{"label":"l2sw_1","type":"l2_switch","default_gw":""},"data":{"id":"l2sw_1","label":"l2sw_1"},"interface":[{"connect":"edge_h1sw1","id":"l2sw_1_1","name":"l2sw_1_1"},{"connect":"edge_h3sw1","id":"l2sw_1_2","name":"l2sw_1_2"},{"connect":"edge_sw1sw2","id":"l2sw_1_3","name":"l2sw_1_3"}],"position":{"x":450,"y":290}},{"classes":["l2_switch"],"config":{"label":"l2sw_2","type":"l2_switch","default_gw":""},"data":{"id":"l2sw_2","label":"l2sw_2"},"interface":[{"connect":"edge_sw1sw2","id":"l2sw_2_1","name":"l2sw_2_1"},{"connect":"edge_h2sw2","id":"l2sw_2_2","name":"l2sw_2_2"},{"connect":"edge_h4sw2","id":"l2sw_2_3","name":"l2sw_2_3"}],"position":{"x":700,"y":290}},{"classes":["host"],"config":{"label":"host_2","type":"host","default_gw":""},"data":{"id":"host_2","label":"host_2"},"interface":[{"connect":"edge_h2sw2","id":"host_2_1","name":"host_2_1","ip":"","netmask":0}],"position":{"x":950,"y":150}},{"classes":["host"],"config":{"label":"host_4","type":"host","default_gw":""},"data":{"id":"host_4","label":"host_4"},"interface":[{"connect":"edge_h4sw2","id":"host_4_1","name":"host_4_1","ip":"","netmask":0}],"position":{"x":950,"y":430}}],"edges":[{"data":{"id":"edge_h1sw1","source":"host_1","target":"l2sw_1","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_h3sw1","source":"host_3","target":"l2sw_1","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_sw1sw2","source":"l2sw_1","target":"l2sw_2","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_h2sw2","source":"host_2","target":"l2sw_2","loss_percentage":0,"duplicate_percentage":0}},{"data":{"id":"edge_h4sw2","source":"host_4","target":"l2sw_2","loss_percentage":0,"duplicate_percentage":0}}],"jobs":[],"config":{"zoom":2,"pan_x":0,"pan_y":0}}"""  # noqa: E501

TECHNOLOGY_HINTS = {
    "vlan": (
        "VLAN",
        "Требует: минимум 1 коммутатор (l2_switch), 3+ хоста разбитых на 2 VLAN. "
        "В описании: настроить VLAN на коммутаторе, разделить хосты по VLAN, проверить изоляцию и/или транк.",
    ),
    "dhcp": (
        "DHCP",
        "Требует: 1 сервер (server) как DHCP-сервер, 2+ хоста. "
        "ВАЖНО: DHCP-сервер выдаёт адреса только хостам в той же подсети (relay не поддерживается). "
        "В описании: настроить DHCP-сервер на server_1 — задать диапазон адресов, маску и шлюз. Хосты должны получить адреса автоматически. "  # noqa: E501
        "НЕ писать про несколько пулов и про DHCP relay — это не поддерживается.",
    ),
    "stp": (
        "STP/RSTP",
        "Требует: 2+ коммутатора (l2_switch) с избыточными связями (кольцо). "
        "В описании: включить STP или RSTP на коммутаторах через интерфейс эмулятора, при необходимости задать приоритет для root bridge. "  # noqa: E501
        "Убедиться что петли устранены. RSTP сходится быстрее (10 сек) чем STP (30 сек).",
    ),
    "nat": (
        "NAT",
        "Требует: 1 роутер (l3_router) на границе между внутренней и внешней сетью, 2+ хоста во внутренней подсети, 1 сервер во внешней. "  # noqa: E501
        "NAT-роутер — это тот который напрямую соединён и с внутренней подсетью хостов и с внешней сетью сервера. "
        "В описании: настроить NAT masquerade на исходящем интерфейсе пограничного роутера через интерфейс эмулятора. "
        "Хосты с приватными адресами должны достигать сервера с публичным адресом.",
    ),
    "routing": (
        "Статические маршруты",
        "Требует: 1+ роутер (l3_router), 2+ подсети, хосты в разных подсетях. "
        "В описании: добавить статические маршруты на роутере через интерфейс эмулятора (указать сеть назначения и шлюз), "  # noqa: E501
        "настроить шлюзы на хостах, проверить ping между подсетями.",
    ),
    "tunnel": (
        "Туннель (IPIP или GRE)",
        "Требует: 2 роутера (l3_router) в разных подсетях. "
        "В описании: создать туннель между двумя роутерами через интерфейс эмулятора (выбрать тип IPIP или GRE, указать локальный и удалённый IP), "  # noqa: E501
        "назначить адреса туннельным интерфейсам, добавить маршруты через туннель, проверить связность.",
    ),
    "vxlan": (
        "VXLAN",
        "Требует: 2+ роутера или хоста, каждый с VXLAN-интерфейсом. "
        "В описании: настроить VXLAN на узлах через интерфейс эмулятора — указать VNI и удалённый VTEP IP, "
        "назначить адреса на VXLAN-интерфейсы, проверить связность между узлами через VXLAN-туннель.",
    ),
    "portforward": (
        "Port Forwarding",
        "Требует: 1 роутер (l3_router) с NAT, 1+ сервер во внутренней сети, 1+ хост во внешней сети. "
        "В описании: настроить проброс порта на роутере через интерфейс эмулятора — указать входящий интерфейс, "
        "внешний порт, внутренний IP и порт сервера. Проверить доступность сервиса с внешнего хоста.",
    ),
}

DIFFICULTY_HINTS = {
    1: (
        "Лёгкая топология: 1-2 роутера, 2 подсети, минимум хостов. "
        "Для маршрутизации: 1 роутер соединяет 2 подсети через 2 свитча. "
        "Для VLAN: 1-2 свитча, 2 VLAN, 3-4 хоста. "
        "Для STP: 2-3 свитча в кольце. "
        "Для туннелей/VXLAN: 2 роутера, туннель или VXLAN между ними."
    ),
    2: (
        "Средняя топология: ровно 3 роутера, 3+ подсети, коммутаторы для группировки хостов. "
        "Для маршрутизации: 3 роутера, каждый со своей подсетью хостов. "
        "КРИТИЧЕСКИ ВАЖНО: каждый раз выбирай РАЗНУЮ структуру соединения роутеров. "
        "Случайно выбери ОДИН из вариантов: "
        "1) ТРЕУГОЛЬНИК — router_1 соединён с router_2, router_2 с router_3, И router_1 с router_3 (три ребра между роутерами), "  # noqa: E501
        "2) ЦЕПОЧКА — router_1 — router_2 — router_3 (только два ребра), "
        "3) ЗВЕЗДА — router_2 в центре, router_1 и router_3 подключены только к router_2. "
        "Для треугольника в условии обязательно укажи асимметрию маршрутов. "
        "Также варьируй количество хостов в подсетях (1, 2 или 3 хоста на подсеть) и наличие серверов. "
        "Для VLAN: 3 свитча, 3 VLAN, роутер для межVLAN маршрутизации, транковые порты. "
        "Для STP: 3-4 свитча с несколькими кольцами. "
        "Для туннелей/VXLAN: 3-4 роутера, туннель или VXLAN поверх транзитной сети."
    ),
    3: (
        "Сложная топология: 5+ роутеров, 4+ подсети, асимметричная маршрутизация или избыточные пути. "
        "Для маршрутизации: минимум 5 роутеров, каждый со своей подсетью, маршруты на каждом роутере до всех остальных подсетей, "  # noqa: E501
        "добавь асимметрию (трафик туда и обратно идёт разными путями) или избыточность (несколько путей между подсетями). "  # noqa: E501
        "Для VLAN: 4+ свитча, 3+ VLAN, 2 роутера для межVLAN маршрутизации, транки между всеми свитчами. "
        "Для STP: 4-5 свитчей с несколькими кольцами и избыточными связями. "
        "Для туннелей/VXLAN: 5 роутеров в цепочке, туннель между крайними, NAT на пограничных роутерах. "
        "Условие должно требовать нетривиальной настройки — асимметрия путей, проверка конкретного маршрута трассировкой."  # noqa: E501
    ),
}

MASKS_HINT = (
    "ДОПОЛНИТЕЛЬНОЕ ТРЕБОВАНИЕ к описанию: укажи что для point-to-point линков между роутерами "
    "нужно использовать маску /30, а для подсетей с хостами студент должен сам посчитать нужную маску "
    "Не давай готовые маски — пусть студент считает сам."
)


def _user_prompt(technologies: list, difficulty: int, masks: bool = False) -> str:
    tech_lines = []
    for t in technologies:
        if t in TECHNOLOGY_HINTS:
            name, hint = TECHNOLOGY_HINTS[t]
            tech_lines.append(f"- {name}: {hint}")

    if not tech_lines:
        tech_lines = [
            "- Базовая IP-связность: несколько хостов, настройка адресов, проверка ping."
        ]

    tech_block = "\n".join(tech_lines)
    diff_hint = DIFFICULTY_HINTS.get(difficulty, DIFFICULTY_HINTS[1])

    masks_block = f"\n{MASKS_HINT}" if masks else ""

    return f"""Создай учебную сетевую топологию со следующими технологиями:
{tech_block}

Сложность: {difficulty}/3. {diff_hint}{masks_block}

ОБЯЗАТЕЛЬНО:
- Сам подбери нужные устройства (host, server, l2_switch, l3_router) и их количество
- Все устройства соединены, нет изолированных узлов
- В описании: конкретные шаги настройки с именами устройств, что проверить в конце
- Без конкретных IP-адресов в описании

Только JSON, без пояснений."""


YANDEX_MODELS_GRPC = {"yandexgpt", "yandexgpt-lite"}

ROUTERAI_API_URL = "https://routerai.ru/api/v1/chat/completions"


def _call_routerai(
    system: str, user: str, model_id: str, api_key_override: str = ""
) -> str:
    api_key = api_key_override or os.environ.get("ROUTERAI_API_KEY", "")
    payload = json.dumps(
        {
            "model": model_id,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        ROUTERAI_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    return result["choices"][0]["message"]["content"].strip()


def _call_yandex(
    system: str,
    user: str,
    model_id: str,
    api_key_override: str = "",
    folder_override: str = "",
) -> str:
    api_key = api_key_override or os.environ.get("YANDEX_AI_API_KEY", "")
    folder_id = folder_override or os.environ.get("YANDEX_FOLDER_ID", "")

    base_model = model_id.split("/")[0]
    if base_model in YANDEX_MODELS_GRPC:
        payload = json.dumps(
            {
                "modelUri": f"gpt://{folder_id}/{model_id}",
                "completionOptions": {"maxTokens": 4000, "temperature": 0.1},
                "messages": [
                    {"role": "system", "text": system},
                    {"role": "user", "text": user},
                ],
            }
        ).encode()
        req = urllib.request.Request(
            YANDEX_API_URL,
            data=payload,
            headers={
                "Authorization": f"Api-Key {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        return result["result"]["alternatives"][0]["message"]["text"].strip()
    else:
        payload = json.dumps(
            {
                "model": f"gpt://{folder_id}/{model_id}",
                "temperature": 0.1,
                "instructions": system,
                "input": user,
                "max_output_tokens": 8192,
                "reasoning_effort": "none",
            }
        ).encode()
        req = urllib.request.Request(
            "https://ai.api.cloud.yandex.net/v1/responses",
            data=payload,
            headers={
                "Authorization": f"Api-Key {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        if result.get("output_text"):
            return result["output_text"].strip()
        for block in result.get("output", []):
            if block.get("type") == "message":
                for part in block.get("content", []):
                    if part.get("type") == "output_text":
                        return part["text"].strip()
        raise Exception(f"Пустой ответ от модели: {json.dumps(result)[:300]}")


def _call_ai(
    system: str,
    user: str,
    model_id: str,
    api_key_override: str = "",
    yandex_key_override: str = "",
    yandex_folder_override: str = "",
) -> str:
    """Роутинг между провайдерами по model_id."""
    if model_id.startswith("anthropic/"):
        return _call_routerai(system, user, model_id, api_key_override=api_key_override)
    return _call_yandex(
        system,
        user,
        model_id,
        api_key_override=yandex_key_override,
        folder_override=yandex_folder_override,
    )


def _fix_topology(topology: dict) -> None:
    """Автоисправление connect в интерфейсах по графу edges. Правит topology на месте."""
    nodes = topology.get("nodes", [])
    edges = topology.get("edges", [])

    node_to_edges: dict[str, list[str]] = {}
    for edge in edges:
        d = edge.get("data", {})
        eid = d.get("id")
        for side in ("source", "target"):
            nid = d.get(side)
            if nid:
                node_to_edges.setdefault(nid, []).append(eid)

    edge_ids = {e.get("data", {}).get("id") for e in edges}

    for node in nodes:
        nid = node.get("data", {}).get("id")
        valid_edges = node_to_edges.get(nid, [])
        ifaces = node.get("interface", [])

        used = set()
        for iface in ifaces:
            if iface.get("connect") in edge_ids:
                used.add(iface["connect"])

        free = [e for e in valid_edges if e not in used]
        for iface in ifaces:
            if iface.get("connect") not in edge_ids and free:
                iface["connect"] = free.pop(0)


def _validate_topology(topology: dict) -> list[str]:
    """Возвращает список ошибок. Пустой список = топология валидна."""
    errors = []
    nodes = topology.get("nodes", [])
    edges = topology.get("edges", [])

    node_ids = {n.get("data", {}).get("id") for n in nodes}
    edge_ids = {e.get("data", {}).get("id") for e in edges}

    if not nodes:
        errors.append("Нет узлов в топологии")
        return errors
    if not edges:
        errors.append("Нет рёбер в топологии")
        return errors

    connected_nodes = set()
    for edge in edges:
        d = edge.get("data", {})
        src, tgt = d.get("source"), d.get("target")
        if src not in node_ids:
            errors.append(f"Edge {d.get('id')}: source '{src}' не существует")
        if tgt not in node_ids:
            errors.append(f"Edge {d.get('id')}: target '{tgt}' не существует")
        connected_nodes.add(src)
        connected_nodes.add(tgt)

    isolated = node_ids - connected_nodes
    if isolated:
        errors.append(f"Изолированные узлы: {', '.join(isolated)}")

    # Проверка связности через BFS
    adjacency: dict[str, set[str]] = {nid: set() for nid in node_ids}
    for edge in edges:
        d = edge.get("data", {})
        src, tgt = d.get("source"), d.get("target")
        if src in adjacency and tgt in adjacency:
            adjacency[src].add(tgt)
            adjacency[tgt].add(src)

    if node_ids:
        start = next(iter(node_ids))
        visited = {start}
        queue = [start]
        while queue:
            current = queue.pop()
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        unreachable = node_ids - visited
        if unreachable:
            errors.append(
                f"Граф несвязный — недостижимые узлы: {', '.join(unreachable)}"
            )

    # Количество интерфейсов
    node_edge_count: dict[str, int] = {}
    for edge in edges:
        d = edge.get("data", {})
        for side in ("source", "target"):
            nid = d.get(side)
            if nid:
                node_edge_count[nid] = node_edge_count.get(nid, 0) + 1

    for node in nodes:
        nid = node.get("data", {}).get("id", "?")
        ifaces = node.get("interface", [])
        expected = node_edge_count.get(nid, 0)

        if len(ifaces) != expected:
            errors.append(
                f"Узел {nid}: ожидается {expected} интерфейс(ов) (по числу edges), "
                f"но объявлено {len(ifaces)}"
            )

        for iface in ifaces:
            connect = iface.get("connect")
            if connect and connect not in edge_ids:
                errors.append(
                    f"Узел {nid}: интерфейс {iface.get('name')} ссылается на несуществующий edge '{connect}'"
                )

    return errors


@login_required
def generate_ai_task():
    if not current_user.role or current_user.role < 1:
        return make_response(jsonify({"error": "Доступ запрещён"}), 403)

    # Ключи берём из БД (поле ai_keys у текущего пользователя) или из env
    ai_keys = {}
    if current_user.ai_keys:
        try:
            ai_keys = json.loads(current_user.ai_keys)
        except (json.JSONDecodeError, TypeError):
            ai_keys = {}

    user_api_key = ai_keys.get("routerai", "")
    yandex_api_key_override = ai_keys.get("yandex_api_key", "")
    yandex_folder_override = ai_keys.get("yandex_folder_id", "")

    model_id = request.form.get("model", "yandexgpt")

    # Проверяем наличие нужного ключа для выбранной модели
    if model_id.startswith("anthropic/") and not user_api_key:
        return make_response(
            jsonify(
                {
                    "error": "Ключи API не найдены в БД. Инструкция: https://github.com/mimi-net/miminet/pull/438"
                }
            ),
            400,
        )
    if not model_id.startswith("anthropic/") and not (
        yandex_api_key_override or os.environ.get("YANDEX_AI_API_KEY")
    ):
        return make_response(
            jsonify(
                {
                    "error": "Ключи API не найдены в БД. Инструкция: https://github.com/mimi-net/miminet/pull/438"
                }
            ),
            400,
        )
    if not model_id.startswith("anthropic/") and not (
        yandex_folder_override or os.environ.get("YANDEX_FOLDER_ID")
    ):
        return make_response(
            jsonify(
                {
                    "error": "Yandex Folder ID не найден в БД. Инструкция: https://github.com/mimi-net/miminet/pull/438"
                }
            ),
            400,
        )
    allowed_techs = set(TECHNOLOGY_HINTS.keys())
    technologies = [t for t in request.form.getlist("tech") if t in allowed_techs]

    try:
        difficulty = int(request.form.get("difficulty", 1))
        if difficulty not in (1, 2, 3):
            difficulty = 1
    except (ValueError, TypeError):
        difficulty = 1

    masks = request.form.get("masks") == "1"

    logger.info(
        "AI generate: user=%s model=%s techs=%s difficulty=%s masks=%s",
        current_user.id,
        model_id,
        technologies,
        difficulty,
        masks,
    )

    topology = None
    last_error = None
    extra_instruction = ""
    for attempt in range(1, 4):
        user_prompt = _user_prompt(technologies, difficulty, masks=masks)
        if extra_instruction:
            user_prompt += (
                f"\n\nИСПРАВЬ ОШИБКИ из предыдущей попытки:\n{extra_instruction}"
            )
        try:
            raw = _call_ai(
                SYSTEM_PROMPT,
                user_prompt,
                model_id,
                api_key_override=user_api_key,
                yandex_key_override=yandex_api_key_override,
                yandex_folder_override=yandex_folder_override,
            )

            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                raw = raw.rsplit("```", 1)[0].strip()

            candidate = json.loads(raw)
            _fix_topology(candidate)
            validation_errors = _validate_topology(candidate)
            if validation_errors:
                last_error = "Невалидная топология: " + "; ".join(validation_errors)
                extra_instruction = "\n".join(f"- {e}" for e in validation_errors)
                logger.warning(
                    "AI generate attempt %s/3 failed validation: %s",
                    attempt,
                    last_error,
                )
                continue
            topology = candidate
            logger.info("AI generate success on attempt %s/3", attempt)
            break
        except json.JSONDecodeError as e:
            last_error = f"ИИ вернул невалидный JSON: {e}"
            extra_instruction = f"Верни ТОЛЬКО валидный JSON без markdown и пояснений. Ошибка парсинга: {e}"
            logger.warning("AI generate attempt %s/3 JSON error: %s", attempt, e)
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            logger.error("AI generate HTTP error %s: %s", e.code, body)
            return make_response(
                jsonify({"error": f"Yandex API {e.code}: {body}"}), 500
            )
        except Exception as e:
            logger.error("AI generate unexpected error: %s", e, exc_info=True)
            return make_response(jsonify({"error": "Ошибка API"}), 500)

    if topology is None:
        logger.error("AI generate failed after 3 attempts: %s", last_error)
        return make_response(
            jsonify(
                {
                    "error": "Не удалось сгенерировать топологию. Повторите попытку позже."
                }
            ),
            500,
        )

    # Нормализация типов
    for node in topology.get("nodes", []):
        cfg = node.get("config", {})
        if cfg.get("type") == "l3_router":
            cfg["type"] = "router"
        if cfg.get("type") == "router" and "l3_router" in node.get("classes", []):
            node["classes"] = ["l3_router"]

    # Убираем дублирующиеся рёбра
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
    network_json = json.dumps(
        {
            "nodes": topology.get("nodes", []),
            "edges": topology.get("edges", []),
            "jobs": topology.get("jobs", []),
            "config": topology.get("config", {"zoom": 2, "pan_x": 0, "pan_y": 0}),
        }
    )

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
