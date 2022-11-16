import json

from flask import render_template, redirect, url_for, request, flash
from miminet_model import db, Network
from flask_login import login_required, current_user


@login_required
def safe_host_config():

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

        for node in nodes:
            if node['data']['id'] == host_id:

                host_label = request.form.get('config_host_name')

                if host_label:
                    print (node)
                    node['data']['label'] = host_label
                    node['config']['label'] = host_label
                    print (node)

                    net.network = json.dumps(jnet)
                    db.session.commit()

    return redirect(url_for('web_network', guid=net.guid))
