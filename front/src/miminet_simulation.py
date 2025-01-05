import os
import uuid

from celery_app import (
    SEND_NETWORK_EXCHANGE,
    EXCHANGE_TYPE,
    app,
)
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

        simlog = SimulateLog(
            author_id=net.author_id, network=net.network, network_guid=net.guid
        )

        task_guid = uuid.uuid4()
        sim = Simulate(network_id=net.id, packets="", task_guid=str(task_guid))
        db.session.add(sim)
        db.session.add(simlog)
        db.session.commit()

        app.send_task(
            "tasks.mininet_worker",
            (net.network,),
            routing_key=str(uuid.uuid4()),
            exchange=SEND_NETWORK_EXCHANGE,
            exchange_type=EXCHANGE_TYPE,
            task_id=str(task_guid),
            headers={"network_task_name": "tasks.save_simulate_result"},
        )

        ret = {"simulation_id": str(task_guid)}
        return make_response(jsonify(ret), 201)

    return redirect(url_for("home"))


@login_required
def check_simulation():
    task_guid = request.args.get("simulation_id", type=str)
    network_guid = request.args.get("network_guid", type=str)

    if not task_guid:
        ret = {"message": "Пропущен параметр task_guid."}
        return make_response(jsonify(ret), 400)

    if not network_guid:
        ret = {"message": "Пропущен параметр network_guid."}
        return make_response(jsonify(ret), 400)

    sim = Simulate.query.filter(Simulate.task_guid == task_guid).first()

    if not sim:
        ret = {"message": "Нет такой симуляции"}
        return make_response(jsonify(ret), 400)

    if sim.ready:
        pcap_dir = "static/pcaps/" + network_guid
        pcaps = []

        if os.path.exists(pcap_dir):
            pcaps = [
                os.path.splitext(f)[0]
                for f in os.listdir(pcap_dir)
                if os.path.isfile(os.path.join(pcap_dir, f))
            ]

        ret = {"message": "Симуляция завершена", "packets": sim.packets, "pcaps": pcaps}
        return make_response(jsonify(ret), 200)

    ret = {"message": "Сеть в процессе симуляции"}
    return make_response(jsonify(ret), 210)
