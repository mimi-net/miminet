import os
import shutil
import uuid

from celery_app import app
from flask import request, flash, redirect, jsonify, make_response, url_for
from flask_login import login_required, current_user
from celery_app import DEFAULT_APP_EXCHANGE, EXCHANGE_TYPE
from miminet_model import db, Simulate, Network, SimulateLog
from celery.result import AsyncResult
from redis import RedisError


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

        task_id = str(uuid.uuid4())
        simlog = SimulateLog(author_id=net.author_id, network=net.network, network_guid=net.guid)
        sim = Simulate(network_id=net.id, packets='', task_guid=task_id)
        db.session.add(sim)
        db.session.add(simlog)
        db.session.flush()
        db.session.refresh(sim)
        db.session.commit()

        app.send_task('tasks.mininet_worker', (net.network,),
                      routing_key=str(uuid.uuid4()),
                      exchange=DEFAULT_APP_EXCHANGE,
                      exchange_type=EXCHANGE_TYPE,
                      task_id=task_id)

        ret = {'simulation_id': sim.id}
        return make_response(jsonify(ret), 201)

    return redirect(url_for('home'))


@login_required
def check_simulation():
    user = current_user
    simulation_id = request.args.get('simulation_id', type=int)
    network_guid = request.args.get('network_guid', type=str)
    if not simulation_id:
        ret = {'message': 'Пропущен параметр simulation_id.'}
        return make_response(jsonify(ret), 400)

    if not network_guid:
        ret = {'message': 'Пропущен параметр network_guid.'}
        return make_response(jsonify(ret), 400)

    sim = Simulate.query.filter(Simulate.id == simulation_id).first()

    if not sim:
        ret = {'message': 'Нет такой симуляции'}
        return make_response(jsonify(ret), 400)

    # Check for a pcaps
    pcap_dir = 'static/pcaps/' + network_guid

    if sim.ready:
        pcaps = []
        if os.path.exists(pcap_dir):
            pcaps = [os.path.splitext(f)[0] for f in os.listdir(pcap_dir) if os.path.isfile(os.path.join(pcap_dir, f))]

        ret = {'message': 'Симуляция завершена', 'packets': sim.packets, 'pcaps': pcaps}
        return make_response(jsonify(ret), 200)

    try:
        task_id = sim.task_guid
        task_result = AsyncResult(task_id)
        if task_result.status != "SUCCESS" and task_result.status != "FAILURE":
            return make_response(jsonify({'message': 'Сеть в процессе симуляции'}), 210)
    except RedisError:
        return make_response(jsonify({'message': 'Ошибка при подключении к backend серверу'}), 400)

    try:
        result = task_result.result
    except Exception:
        return make_response(jsonify({'message': 'Ошибка на стороне ipmininet worker'}), 400)

    packets, binary_pcaps = result

    # Костыль для того, чтобы при одновременной обработке
    # одной и той же сети они не ждали результата при разных task_id,
    # а обращались к готовому
    sim.packets = packets
    sim.ready = True
    db.session.commit()

    if not os.path.exists(pcap_dir):
        os.makedirs(pcap_dir)
    else:
        shutil.rmtree(pcap_dir)
        os.makedirs(pcap_dir)

    pcaps = []
    for pcap, name in binary_pcaps:
        pcaps += name
        with open(pcap_dir + '/' + name + '.pcap', "wb") as file:
            file.write(pcap)

    ret = {'message': 'Симуляция завершена', 'packets': packets, 'pcaps': pcaps}

    return make_response(jsonify(ret), 200)