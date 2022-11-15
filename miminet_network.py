import uuid
import json

from flask_login import login_required, current_user
from flask import render_template, redirect, url_for, request, flash

from miminet_model import db, Network

@login_required
def create_network():

    user = current_user
    u = uuid.uuid4()

    n = Network(author_id=user.id, guid = str(u))
    db.session.add(n)
    db.session.flush()
    db.session.refresh(n)
    db.session.commit()

    return redirect(url_for('web_network', guid=n.guid))


@login_required
def update_network_config():

    network_guid = request.args.get('guid', type=str)

    if not network_guid:
        flash('Пропущен параметр GUID. И какую сеть мне открыть?!')
        return redirect('home')

    net = Network.query.filter(Network.guid == network_guid).first()

    if not net:
        flash('Нет такой сети')
        return redirect('home')

    if request.method == "POST":
        title = request.form.get('network_title').strip()

        if title:
            net.title=title
            db.session.commit()

    return render_template("network.html", network=net)


@login_required
def delete_network():

    user = current_user
    network_guid = request.args.get('guid', type=str)

    if not network_guid:
        flash('Пропущен параметр GUID. И какую сеть мне открыть?!')
        return redirect('home')

    net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

    if not net:
        flash('Нет такой сети')
        return redirect('home')

    if request.method == "POST":
        db.session.delete(net)
        db.session.commit()

    return redirect(url_for('home'))


@login_required
def web_network():

    network_guid = request.args.get('guid', type=str)

    if not network_guid:
        flash('Пропущен параметр GUID. И какую сеть мне открыть?!')
        return redirect('home')

    net = Network.query.filter(Network.guid == network_guid).first()

    if not net:
        flash('Нет такой сети')
        return redirect('home')

    return render_template("network.html", network=net)