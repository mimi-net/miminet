import os
import shutil
import uuid

from celery.result import AsyncResult
from celery_app import DEFAULT_APP_EXCHANGE, EXCHANGE_TYPE, app
from flask import jsonify, make_response, redirect, request, url_for
from flask_login import current_user, login_required
from miminet_model import Network, Simulate, SimulateLog, db


@login_required
def run_simulation():
    user = current_user
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        ret = {
            "simulation_id": 0,
            "message": "Пропущен параметр GUID. И какую сеть мне симулировать?!",
        }
        return make_response(jsonify(ret), 400)

    net = (
        Network.query.filter(Network.guid == network_guid)
        .filter(Network.author_id == user.id)
        .first()
    )

    if not net:
        ret = {"simulation_id": 0, "message": "Нет такой сети"}
        return make_response(jsonify(ret), 400)

    if request.method == "POST":
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()

        # Remove all previous simulations
        for s in sims:
            db.session.delete(s)
            db.session.commit()

        task_id = str(uuid.uuid4())

        simlog = SimulateLog(
            author_id=net.author_id, network=net.network, network_guid=net.guid
        )

        sim = Simulate(network_id=net.id, packets="", task_guid=task_id)
        db.session.add(sim)
        db.session.add(simlog)
        db.session.flush()
        db.session.refresh(sim)
        db.session.commit()

        app.send_task(
            "tasks.mininet_worker",
            (net.network,),
            routing_key=str(uuid.uuid4()),
            exchange=DEFAULT_APP_EXCHANGE,
            exchange_type=EXCHANGE_TYPE,
            task_id=task_id,
        )

        ret = {"simulation_id": task_id}
        return make_response(jsonify(ret), 201)

    return redirect(url_for("home"))


@login_required
def check_simulation():
    task_guid = request.args.get("simulation_id", type=str)
    network_guid = request.args.get("network_guid", type=str)

    if not task_guid:
        ret = {"message": "Пропущен параметр task_id."}
        return make_response(jsonify(ret), 400)

    if not network_guid:
        ret = {"message": "Пропущен параметр network_guid."}
        return make_response(jsonify(ret), 400)

    try:
        task_result = AsyncResult(task_guid)
        if task_result.status != "SUCCESS" and task_result.status != "FAILURE":
            return make_response(jsonify({"message": "Сеть в процессе симуляции"}), 210)
    except Exception:
        return make_response(
            jsonify({"message": "Ошибка при подключении к backend серверу"}), 400
        )

    try:
        result = task_result.result
    except Exception:
        return make_response(
            jsonify({"message": "Ошибка на стороне ipmininet worker"}), 400
        )

    packets, binary_pcaps = result

    # Add result main storage
    sim = Simulate.query.filter(Simulate.task_guid == task_guid).first()
    simlog = (
        SimulateLog.query.filter(SimulateLog.network_guid == network_guid)
        .order_by(SimulateLog.id.desc())
        .first()
    )
    sim.packets = packets
    sim.ready = True
    if simlog:
        if not simlog.ready:
            simlog.ready = True

    db.session.commit()

    # Check for a pcaps
    pcap_dir = "static/pcaps/" + network_guid

    if not os.path.exists(pcap_dir):
        os.makedirs(pcap_dir)
    else:
        shutil.rmtree(pcap_dir)
        os.makedirs(pcap_dir)

    pcaps = []
    for pcap, name in binary_pcaps:
        pcaps += name
        with open(pcap_dir + "/" + name + ".pcap", "wb") as file:
            file.write(pcap)

    ret = {"message": "Симуляция завершена", "packets": packets, "pcaps": pcaps}

    return make_response(jsonify(ret), 200)
