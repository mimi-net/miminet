from flask import request, flash, redirect, jsonify, make_response, url_for
from flask_login import login_required, current_user

from miminet_model import db, Simulate, Network

@login_required
def run_simulation():

    user = current_user
    network_guid = request.args.get('guid', type=str)

    if not network_guid:
        ret = {'simulation_id': 0, 'message': 'Пропущен параметр GUID. И какую сеть мне симулировать?!'}
        return make_response(jsonify(ret), 400)

    net = Network.query.filter(Network.guid == network_guid).filter(Network.author_id == user.id).first()

    if not net:
        ret = {'simulation_id': 0, 'message': 'Нет такой сети'}
        return make_response(jsonify(ret), 400)

    if request.method == "POST":
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()

        # Remove all previous simulations
        for s in sims:
            db.session.delete(s)
            db.session.commit()

        sim = Simulate(network_id = net.id, packets = '')
        db.session.add(sim)
        db.session.flush()
        db.session.refresh(sim)
        db.session.commit()

        ret = {'simulation_id': sim.id}
        return make_response(jsonify(ret), 201)

    return redirect(url_for('home'))


@login_required
def check_simulation():
    user = current_user
    simulation_id = request.args.get('simulation_id', type=int)

    if not simulation_id:
        ret = {'message': 'Пропущен параметр simulation_id.'}
        return make_response(jsonify(ret), 400)

    sim = Simulate.query.filter(Simulate.id == simulation_id).first()

    if not sim:
        ret = {'message': 'Нет такой симуляции'}
        return make_response(jsonify(ret), 400)

    if sim.ready:
        ret = {'message': 'Симуляция завершена', 'packets' : sim.packets}
        return make_response(jsonify(ret), 200)

    ret = {'message': 'Сеть в процессе симуляции'}
    return make_response(jsonify(ret), 210)