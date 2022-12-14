import uuid
import json

from flask_login import login_required, current_user
from flask import render_template, redirect, url_for, request, flash, make_response, jsonify

from miminet_model import db, Network, Simulate

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
        title = request.form.get('network_title').strip()

        if title:
            net.title=title
            db.session.commit()

    return redirect(url_for('web_network', guid=net.guid))


@login_required
def delete_network():

    user = current_user
    network_guid = request.args.get('guid', type=str)

    if not network_guid:
        flash('Пропущен параметр GUID. И какую сеть мне удалить?!')
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

    jnet = json.loads(net.network)

    if not 'nodes' in jnet:
        jnet['nodes'] = 'null'

    if not 'edges' in jnet:
        jnet['edges'] = 'null'

    if not 'packets' in jnet:
        jnet['packets'] = 'null'

    # Do we simulte this network now?
    sim = Simulate.query.filter(Simulate.network_id == net.id).first()

    return render_template("network.html", network=net, nodes=jnet['nodes'],
                           edges=jnet['edges'], packets=jnet['packets'],
                           simulating = sim)


@login_required
def post_nodes():

    user = current_user
    network_guid = request.args.get('guid', type=str)

    if not network_guid:
        flash('Пропущен параметр GUID. И какую сеть мне открыть?!')
        return redirect(url_for('home'))

    net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

    if not net:
        flash('Нет такой сети')
        return redirect(url_for('home'))

    if request.method == "POST":
        nodes = request.json
        jnet = json.loads(net.network)
        jnet['nodes'] = nodes
        net.network = json.dumps(jnet)

        # Remove all previous simulations
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()
        for s in sims:
            db.session.delete(s)

        db.session.commit()

    ret = {'message': 'Done', 'code': 'SUCCESS'}
    return make_response(jsonify(ret), 201)


@login_required
def post_edges():

    user = current_user
    network_guid = request.args.get('guid', type=str)

    if not network_guid:
        flash('Пропущен параметр GUID. И какую сеть мне открыть?!')
        return redirect(url_for('home'))

    net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

    if not net:
        flash('Нет такой сети')
        return redirect(url_for('home'))

    if request.method == "POST":
        edges = request.json
        jnet = json.loads(net.network)
        jnet['edges'] = edges
        net.network = json.dumps(jnet)
        db.session.commit()

    ret = {'message': 'Done', 'code': 'SUCCESS'}
    return make_response(jsonify(ret), 201)


@login_required
def post_nodes_edges():

    user = current_user
    network_guid = request.args.get('guid', type=str)

    if not network_guid:
        ret = {'message': 'Пропущен параметр guid'}
        return make_response(jsonify(ret), 400)

    net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

    if not net:
        ret = {'message': 'Нет такой сети'}
        return make_response(jsonify(ret), 400)

    if request.method == "POST":
        nodes = request.json[0]
        edges = request.json[1]

        jnet = json.loads(net.network)
        jnet['edges'] = edges
        jnet['nodes'] = nodes
        net.network = json.dumps(jnet)

        # Remove all previous simulations
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()
        for s in sims:
            db.session.delete(s)

        db.session.commit()

    ret = {'message': 'Done', 'code': 'SUCCESS'}
    return make_response(jsonify(ret), 201)


@login_required
def network_simulate():

    user = current_user
    network_guid = request.args.get('guid', type=str)

    if not network_guid:
        flash('Пропущен параметр GUID. Кого симулировать?!')
        return redirect('home')

    net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

    if not net:
        flash('Нет такой сети')
        return redirect('home')


@login_required
def move_nodes():

    user = current_user
    network_guid = request.args.get('guid', type=str)

    if not network_guid:
        ret = {'message': 'Пропущен параметр GUID. И какую сеть мне открыть?!'}
        return make_response(jsonify(ret), 400)

    net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id==user.id).first()

    if not net:
        ret = {'message': 'Нет такой сети'}
        return make_response(jsonify(ret), 400)

    if request.method == "POST":
        nodes = request.json
        jnet = json.loads(net.network)
        jnet['nodes'] = nodes
        net.network = json.dumps(jnet)
        db.session.commit()

    ret = {'message': 'Done', 'code': 'SUCCESS'}
    return make_response(jsonify(ret), 201)