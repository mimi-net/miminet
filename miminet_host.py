import json
import uuid

from flask import render_template, redirect, url_for, request, flash
from miminet_model import db, Network, Simulate
from flask_login import login_required, current_user


def job_id_generator():
    return uuid.uuid4().hex


@login_required
def delete_job():
    user = current_user
    network_guid = request.args.get('guid', type=str)
    jid = request.args.get('id', type=str)

    if not network_guid:
        flash('Пропущен параметр GUID')
        return redirect('home')

    net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id == user.id).first()

    if not net:
        flash('Нет такой сети')
        return redirect('home')

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

    return redirect(url_for('web_network', guid=net.guid))


@login_required
def save_hub_config():

    user = current_user

    if request.method == "POST":

        network_guid = request.form.get('net_guid', type=str)

        if not network_guid:
            flash('Пропущен параметр GUID. И какую сеть мне открыть?!')
            return redirect('home')

        net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

        if not net:
            flash('Нет такой сети')
            return redirect('home')

        hub_id = request.form.get('hub_id')

        if not hub_id:
            flash('Хаб не указан')
            return redirect(url_for('web_network', guid=net.guid))

        jnet = json.loads(net.network)
        nodes = jnet['nodes']

        nn = list(filter(lambda x: x['data']["id"] == hub_id, nodes))

        if not nn:
            flash('Хаба таким id не существует')
            return redirect(url_for('web_network', guid=net.guid))

        node = nn[0]
        hub_label = request.form.get('config_hub_name')

        if hub_label:
            node['config']['label'] = hub_label
            node['data']['label'] = node['config']['label']

            net.network = json.dumps(jnet)
            db.session.commit()

        return redirect(url_for('web_network', guid=net.guid))

    return redirect(url_for('home'))

@login_required
def save_switch_config():

    user = current_user

    if request.method == "POST":

        network_guid = request.form.get('net_guid', type=str)

        if not network_guid:
            flash('Пропущен параметр GUID. И какую сеть мне открыть?!')
            return redirect('home')

        net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

        if not net:
            flash('Нет такой сети')
            return redirect('home')

        switch_id = request.form.get('switch_id')

        if not switch_id:
            flash('Свитч не указан')
            return redirect(url_for('web_network', guid=net.guid))

        jnet = json.loads(net.network)
        nodes = jnet['nodes']

        nn = list(filter(lambda x: x['data']["id"] == switch_id, nodes))

        if not nn:
            flash('Свитча таким id не существует')
            return redirect(url_for('web_network', guid=net.guid))

        node = nn[0]
        switch_label = request.form.get('config_switch_name')

        if switch_label:
            node['config']['label'] = switch_label
            node['data']['label'] = node['config']['label']

            net.network = json.dumps(jnet)
            db.session.commit()

        return redirect(url_for('web_network', guid=net.guid))

    return redirect(url_for('home'))

@login_required
def save_host_config():

    user = current_user

    if request.method == "POST":

        network_guid = request.form.get('net_guid', type=str)

        if not network_guid:
            flash('Пропущен параметр GUID. И какую сеть мне открыть?!')
            return redirect('home')

        net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

        if not net:
            flash('Нет такой сети')
            return redirect('home')

        host_id = request.form.get('host_id')

        if not host_id:
            flash('Хост не указан')
            return redirect(url_for('web_network', guid=net.guid))

        jnet = json.loads(net.network)
        nodes = jnet['nodes']

        nn = list(filter(lambda x: x['data']["id"] == host_id, nodes))

        if not nn:
            flash('Хоста таким id не существует')
            return redirect(url_for('web_network', guid=net.guid))

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

            interface['ip'] = host_ip_value
            interface['netmask'] = host_mask_value

        host_label = request.form.get('config_host_name')

        if host_label:
            node['config']['label'] = host_label
            node['data']['label'] = node['config']['label']

            # Remove all previous simulations
            sims = Simulate.query.filter(Simulate.network_id == net.id).all()
            for s in sims:
                db.session.delete(s)

            net.network = json.dumps(jnet)
            db.session.commit()

        return redirect(url_for('web_network', guid=net.guid))

    return redirect(url_for('home'))
