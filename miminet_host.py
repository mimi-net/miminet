import json
import uuid
import socket
import traceback

from flask import redirect, url_for, request, flash, make_response, jsonify
from miminet_model import db, Network, Simulate
from flask_login import login_required, current_user


def job_id_generator():
    return uuid.uuid4().hex


@login_required
def delete_job():
    user = current_user
    network_guid = request.form.get('guid', type=str)
    jid = request.form.get('id', type=str)

    if request.method != "POST":
        ret = {'message': 'Неверный запрос'}
        return make_response(jsonify(ret), 400)

    if not network_guid:
        ret = {'message': 'Не указан параметр net_guid'}
        return make_response(jsonify(ret), 400)

    net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id == user.id).first()

    if not net:
        ret = {'message': 'Такая сеть не найдена'}
        return make_response(jsonify(ret), 400)

    jnet = json.loads(net.network)

    jobs = jnet['jobs']
    jj = list(filter(lambda x: x["id"] != jid, jobs))
    jnet['jobs'] = jj

    net.network = json.dumps(jnet)

    # Remove all previous simulations
    sims = Simulate.query.filter(Simulate.network_id == net.id).all()
    for s in sims:
        db.session.delete(s)

    db.session.commit()

    ret = {'message': 'Команда удалена', 'jobs': jnet['jobs']}
    return make_response(jsonify(ret), 200)

@login_required
def save_hub_config():

    user = current_user

    if request.method == "POST":

        network_guid = request.form.get('net_guid', type=str)

        if not network_guid:
            ret = {'message': 'Не указан параметр net_guid'}
            return make_response(jsonify(ret), 400)

        net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

        if not net:
            ret = {'message': 'Такая сеть не найдена'}
            return make_response(jsonify(ret), 400)

        hub_id = request.form.get('hub_id')

        if not hub_id:
            ret = {'message': 'Не указан параметр hub_id'}
            return make_response(jsonify(ret), 400)

        jnet = json.loads(net.network)
        nodes = jnet['nodes']

        nn = list(filter(lambda x: x['data']["id"] == hub_id, nodes))

        if not nn:
            ret = {'message': 'Такого хаба не существует'}
            return make_response(jsonify(ret), 400)

        node = nn[0]
        hub_label = request.form.get('config_hub_name')

        if hub_label:
            node['config']['label'] = hub_label
            node['data']['label'] = node['config']['label']

            net.network = json.dumps(jnet)
            db.session.commit()

        ret = {'message': 'Конфигурация обновлена', 'nodes': nodes}
        return make_response(jsonify(ret), 200)

    ret = {'message': 'Неверный запрос'}
    return make_response(jsonify(ret), 400)

@login_required
def save_switch_config():

    user = current_user

    if request.method != "POST":
        ret = {'message': 'Неверный запрос'}
        return make_response(jsonify(ret), 400)

    network_guid = request.form.get('net_guid', type=str)

    if not network_guid:
        ret = {'message': 'Не указан параметр net_guid'}
        return make_response(jsonify(ret), 400)

    net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

    if not net:
        ret = {'message': 'Такая сеть не найдена'}
        return make_response(jsonify(ret), 400)

    switch_id = request.form.get('switch_id')

    if not switch_id:
        ret = {'message': 'Не указан параметр switch_id'}
        return make_response(jsonify(ret), 400)

    jnet = json.loads(net.network)
    nodes = jnet['nodes']

    nn = list(filter(lambda x: x['data']["id"] == switch_id, nodes))

    if not nn:
        ret = {'message': 'Такого свитча не существует'}
        return make_response(jsonify(ret), 400)

    node = nn[0]
    switch_label = request.form.get('config_switch_name')

    if switch_label:
        node['config']['label'] = switch_label
        node['data']['label'] = node['config']['label']

        net.network = json.dumps(jnet)
        db.session.commit()

    ret = {'message': 'Конфигурация обновлена', 'nodes': nodes}
    return make_response(jsonify(ret), 200)

@login_required
def save_host_config():

    user = current_user
    ret = {}

    if request.method == "POST":

        network_guid = request.form.get('net_guid', type=str)

        if not network_guid:
            ret.update({'message': 'Не указан параметр net_guid'})
            return make_response(jsonify(ret), 400)

        net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

        if not net:
            ret.update({'message': 'Такая сеть не найдена'})
            return make_response(jsonify(ret), 400)

        host_id = request.form.get('host_id')

        if not host_id:
            ret.update({'message': 'Не указан параметр host_id'})
            return make_response(jsonify(ret), 400)

        jnet = json.loads(net.network)
        nodes = jnet['nodes']

        nn = list(filter(lambda x: x['data']["id"] == host_id, nodes))

        if not nn:
            ret.update({'message': 'Такого хоста не существует'})
            return make_response(jsonify(ret), 400)

        node = nn[0]

        # Add job?
        job_id = int(request.form.get('config_host_job_select_field'))

        if job_id:

            if not jnet.get('jobs'):
                jnet['jobs'] = []

            job_level = len(jnet['jobs'])

            if job_level < 10:

                # ping -c 1 (1 param)
                if job_id == 1:
                    job_1_arg_1 = request.form.get('config_host_ping_c_1_ip')

                    if job_1_arg_1:
                        jnet['jobs'].append({'id': job_id_generator(),
                                            'level': job_level,
                                             'job_id' : job_id,
                                             'host_id': node['data']['id'],
                                             'arg_1': job_1_arg_1,
                                             'print_cmd' : 'ping -c 1 ' + job_1_arg_1})
                    else:
                        ret.update({'warning': 'Не указан IP адрес для команды ping'})

        # Set IP adresses
        iface_ids = request.form.getlist('config_host_iface_ids[]')
        for iface_id in iface_ids:

            # Do we really have that iface?
            if not node['interface']:
                break

            ii = list(filter(lambda x: x['id'] == iface_id, node['interface']))

            if not ii:
                continue

            interface = ii[0]

            host_ip_value = request.form.get('config_host_ip_' + str(iface_id))
            host_mask_value = request.form.get('config_host_mask_' + str(iface_id))

            # If not IP
            if not host_ip_value:
                continue

            if not host_mask_value.isdigit():

                # Check if we have 1.2.3.4/5 ?
                ip_mask = host_ip_value.split('/')
                if len(ip_mask) == 2:
                    host_ip_value = ip_mask[0]
                    host_mask_value = ip_mask[1]
                else:
                    ret.update({'warning': 'Не указана маска для IP адреса'})
                    continue

            host_mask_value = int(host_mask_value)

            if host_mask_value < 0 or host_mask_value > 32:
                ret.update({'warning': 'Маска подсети указана неверно'})
                continue

            try:
                socket.inet_aton(host_ip_value)
                interface['ip'] = host_ip_value
                interface['netmask'] = host_mask_value
            except:
                ret.update({'warning': 'IP адрес указан неверно.'})
                continue

        host_label = request.form.get('config_host_name')

        if host_label:
            node['config']['label'] = host_label
            node['data']['label'] = node['config']['label']

        default_gw = request.form.get('config_host_default_gw')

        if default_gw:

            # Check if default_gw is a valid IP address
            try:
                socket.inet_aton(default_gw)
                node['config']['default_gw'] = default_gw
            except:
                ret.update({'warning': 'IP адрес указан неверно.'})
                return make_response(jsonify(ret), 400)
        else:
            node['config']['default_gw'] = ''

        # Remove all previous simulations
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()
        for s in sims:
            db.session.delete(s)

        net.network = json.dumps(jnet)
        db.session.commit()

        ret.update({'message': 'Конфигурация обновлена', 'nodes' : nodes, 'jobs' : jnet['jobs']})
        return make_response(jsonify(ret), 200)

    ret.update({'message': 'Неверный запрос'})
    return make_response(jsonify(ret), 400)

@login_required
def save_router_config():

    user = current_user
    ret = {}

    if request.method == "POST":

        network_guid = request.form.get('net_guid', type=str)

        if not network_guid:
            ret.update({'message': 'Не указан параметр net_guid'})
            return make_response(jsonify(ret), 400)

        net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id == user.id).first()

        if not net:
            ret.update({'message': 'Такая сеть не найдена'})
            return make_response(jsonify(ret), 400)

        router_id = request.form.get('router_id')

        if not router_id:
            ret.update({'message': 'Не указан параметр host_id'})
            return make_response(jsonify(ret), 400)

        jnet = json.loads(net.network)
        nodes = jnet['nodes']

        nn = list(filter(lambda x: x['data']["id"] == router_id, nodes))

        if not nn:
            ret.update({'message': 'Такого раутера не существует'})
            return make_response(jsonify(ret), 400)

        node = nn[0]

        # Add job?
        if 'config_router_job_select_field' in request.form:

            job_id = int(request.form.get('config_router_job_select_field'))

            if job_id:

                if not jnet.get('jobs'):
                    jnet['jobs'] = []

                job_level = len(jnet['jobs'])
                if job_level < 10:

                    # ping -c 1 (1 param)
                    if job_id == 1:
                        job_1_arg_1 = request.form.get('config_router_ping_c_1_ip')

                        if job_1_arg_1:
                            jnet['jobs'].append({'id': job_id_generator(),
                                                 'level': job_level,
                                                 'job_id' : job_id,
                                                 'host_id': node['data']['id'],
                                                 'arg_1': job_1_arg_1,
                                                 'print_cmd' : 'ping -c 1 ' + job_1_arg_1})
                        else:
                            ret.update({'warning': 'Не указан IP адрес для команды ping'})

                    # add IP/mask
                    if job_id == 100:
                        job_100_arg_1 = request.form.get('config_router_add_ip_mask_iface_select_field')
                        job_100_arg_2 = request.form.get('config_router_add_ip_mask_ip_input_field')

                        if not job_100_arg_1:
                            ret.update({'warning': 'Не указан интерфейс адрес для команды "Добавить IP адрес"'})
                            return make_response(jsonify(ret), 200)

                        if not job_100_arg_2:
                            ret.update({'warning': 'Не указан IP адрес для команды "Добавить IP адрес"'})
                            return make_response(jsonify(ret), 400)

                        if not 'config_router_add_ip_mask_mask_input_field' in request.form:
                            ret.update({'warning': 'Не указана маска для команды "Добавить IP адрес"'})
                            return make_response(jsonify(ret), 200)

                        job_100_arg_3 = int(request.form.get('config_router_add_ip_mask_mask_input_field'))

                        if job_100_arg_3 < 0 or job_100_arg_3 > 32:
                            ret.update({'warning': 'Маска для команды "Добавить IP адрес" указана неверно. Допустимые значения от 0 до 32.'})
                            return make_response(jsonify(ret), 200)

                        try:
                            socket.inet_aton(job_100_arg_2)
                            jnet['jobs'].append({'id': job_id_generator(),
                                                 'level': job_level,
                                                 'job_id' : job_id,
                                                 'host_id': node['data']['id'],
                                                 'arg_1': job_100_arg_1,
                                                 'arg_2': job_100_arg_2,
                                                 'arg_3': job_100_arg_3,
                                                 'print_cmd' : 'ip addess add ' + str(job_100_arg_2) + '/' + str(job_100_arg_3) + ' dev ' + str(job_100_arg_1)})
                        except Exception:
                            ret.update({'warning': 'IP адрес для команды "Добавить IP адрес" указан неверно.'})

                    # add NAT masquerade to the interface
                    if job_id == 101:
                        job_101_arg_1 = request.form.get('config_router_add_nat_masquerade_iface_select_field')

                        if not job_101_arg_1 or job_101_arg_1 == "0":
                            ret.update({'warning': 'Не указан интерфейс для команды "Включить NAT masquerade"'})
                            return make_response(jsonify(ret), 200)

                        jnet['jobs'].append({'id': job_id_generator(),
                                             'level': job_level,
                                             'job_id' : job_id,
                                             'host_id': node['data']['id'],
                                             'arg_1': job_101_arg_1,
                                             'print_cmd' : 'add nat -o ' + str(job_101_arg_1) + ' -j masquerad'})

                    if job_id == 102:
                        job_102_arg_1 = request.form.get('config_router_add_route_ip_input_field')
                        job_102_arg_2 = int(request.form.get('config_router_add_route_mask_input_field'))
                        job_102_arg_3 = request.form.get('config_router_add_route_gw_input_field')

                        if not job_102_arg_1:
                            ret.update({'warning': 'Не указан IP адрес для команды "Добавить маршрут"'})
                            return make_response(jsonify(ret), 200)

                        if job_102_arg_2 < 0 or job_102_arg_2 > 32:
                            ret.update({'warning': 'Маска для команды "Добавить маршрут" указана неверно. Допустимые значения от 0 до 32.'})
                            return make_response(jsonify(ret), 200)

                        if not job_102_arg_3:
                            ret.update({'warning': 'Не указан IP адрес шлюза для команды "Добавить маршрут"'})
                            return make_response(jsonify(ret), 200)

                        try:
                            socket.inet_aton(job_102_arg_1)
                            socket.inet_aton(job_102_arg_3)
                            jnet['jobs'].append({'id': job_id_generator(),
                                                 'level': job_level,
                                                 'job_id': job_id,
                                                 'host_id': node['data']['id'],
                                                 'arg_1': job_102_arg_1,
                                                 'arg_2': job_102_arg_2,
                                                 'arg_3': job_102_arg_3,
                                                 'print_cmd': 'ip route add ' + str(job_102_arg_1) + '/' + str(
                                                     job_102_arg_2) + ' via ' + str(job_102_arg_3)})
                        except Exception:
                            ret.update({'warning': 'IP адрес для команды "Добавить маршрут" указан неверно.'})


        # Set IP adresses
        iface_ids = request.form.getlist('config_router_iface_ids[]')
        for iface_id in iface_ids:

            # Do we really have that iface?
            if not node['interface']:
                break

            ii = list(filter(lambda x: x['id'] == iface_id, node['interface']))

            if not ii:
                continue

            interface = ii[0]

            router_ip_value = request.form.get('config_router_ip_' + str(iface_id))
            router_mask_value = request.form.get('config_router_mask_' + str(iface_id))

            # If not IP
            if not router_ip_value:
                continue

            if not router_mask_value.isdigit():

                # Check if we have 1.2.3.4/5 ?
                ip_mask = router_ip_value.split('/')
                if len(ip_mask) == 2:
                    router_ip_value = ip_mask[0]
                    router_mask_value = ip_mask[1]
                else:
                    ret.update({'warning': 'Не указана маска для IP адреса'})
                    continue

            router_mask_value = int(router_mask_value)

            if router_mask_value < 0 or router_mask_value > 32:
                ret.update({'warning': 'Маска подсети указана неверно'})
                continue

            try:
                socket.inet_aton(router_ip_value)
                interface['ip'] = router_ip_value
                interface['netmask'] = router_mask_value
            except:
                ret.update({'warning': 'IP адрес указан неверно.'})
                continue

        router_label = request.form.get('config_router_name')

        if router_label:
            node['config']['label'] = router_label
            node['data']['label'] = node['config']['label']

        default_gw = request.form.get('config_router_default_gw')

        if default_gw:

            # Check if default_gw is a valid IP address
            try:
                socket.inet_aton(default_gw)
                node['config']['default_gw'] = default_gw
            except:
                ret.update({'warning': 'IP адрес для маршрута по умолчанию указан неверно.'})
        else:
            node['config']['default_gw'] = ''

        # Remove all previous simulations
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()
        for s in sims:
            db.session.delete(s)

        net.network = json.dumps(jnet)
        db.session.commit()

        ret.update({'message': 'Конфигурация обновлена', 'nodes': nodes, 'jobs' : jnet['jobs']})
        return make_response(jsonify(ret), 200)

    ret.update({'message': 'Неверный запрос'})
    return make_response(jsonify(ret), 400)