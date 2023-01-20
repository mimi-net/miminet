import json

from flask import render_template, redirect, url_for, request, flash
from miminet_model import db, Network
from flask_login import login_required, current_user


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

            net.network = json.dumps(jnet)
            db.session.commit()

    return redirect(url_for('web_network', guid=net.guid))
