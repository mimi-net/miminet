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
from werkzeug.wrappers import Response


@login_required
def run_simulation() -> Response:
    """Add new celery task and create record (for emulation result) in database."""
    user = current_user
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        ret = {
            "simulation_id": -1,
            "message": "Пропущен параметр GUID. И какую сеть мне эмулировать?!",
        }
        return make_response(jsonify(ret), 400)

    net = (
        Network.query.filter(Network.guid == network_guid)
        .filter(Network.author_id == user.id)
        .first()
    )

    if not net:
        ret = {"simulation_id": -1, "message": "Нет такой сети."}
        return make_response(jsonify(ret), 400)

    if request.method == "POST":
        # Put new network to database

        # Get saved emulations
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()
        # Remove all previous emulations
        for s in sims:
            db.session.delete(s)
            db.session.commit()

        # Write log
        simlog = SimulateLog(
            author_id=net.author_id, network=net.network, network_guid=net.guid
        )

        # Add new network
        task_guid = uuid.uuid4()
        sim = Simulate(network_id=net.id, packets=None, task_guid=str(task_guid))
        db.session.add(sim)
        db.session.add(simlog)
        db.session.commit()

        # Send emulation task to celery
        app.send_task(
            "tasks.mininet_worker",
            (net.network,),
            routing_key=str(uuid.uuid4()),
            exchange=SEND_NETWORK_EXCHANGE,
            exchange_type=EXCHANGE_TYPE,
            task_id=str(task_guid),
            headers={"network_task_name": "tasks.save_simulate_result"},
        )

        # Return network id to check emulation result
        ret = {"simulation_id": sim.id}
        return make_response(jsonify(ret), 201)

    return redirect(url_for("home"))


@login_required
def check_simulation():
    sim_id = request.args.get("simulation_id", type=int)
    network_guid = request.args.get("network_guid", type=str)

    if not sim_id:
        ret = {"message": "Пропущен параметр simulation_id."}
        return make_response(jsonify(ret), 400)

    if not network_guid:
        ret = {"message": "Пропущен параметр network_guid."}
        return make_response(jsonify(ret), 400)

    sim = Simulate.query.filter(Simulate.id == sim_id).first()
    if not sim:
        ret = {"message": "Нет такой симуляции."}
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
