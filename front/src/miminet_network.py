import json
import os
import uuid
import shutil

from flask import (
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from miminet_config import check_image_with_pil
from miminet_model import Network, Simulate, db, SimulateLog
import datetime
from sqlalchemy import not_


@login_required
def create_network():
    user = current_user
    u = uuid.uuid4()

    n = Network(author_id=user.id, guid=str(u))
    db.session.add(n)
    db.session.flush()
    db.session.refresh(n)
    db.session.commit()

    return redirect(url_for("web_network", guid=n.guid))


@login_required
def update_network_config():
    user = current_user
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        ret = {"message": "Пропущен параметр GUID. И какую сеть мне открыть?!"}
        return make_response(jsonify(ret), 400)

    net = (
        Network.query.filter(Network.guid == network_guid)
        .filter(Network.author_id == user.id)
        .first()
    )

    if not net:
        ret = {"message": "Нет такой сети"}
        return make_response(jsonify(ret), 400)

    if request.method != "POST":
        ret = {"message": "Неверный запрос"}
        return make_response(jsonify(ret), 400)

    net_config = request.json
    jnet = json.loads(net.network)

    title = net_config.get("network_title").strip()

    if title:
        net.title = title

    description = net_config.get("network_description").strip()

    if description:
        net.description = description

    zoom = net_config.get("zoom")

    # Default zoom
    if not zoom:
        zoom = 2

    zoom = float(zoom)

    pan_x = net_config.get("pan_x")
    pan_y = net_config.get("pan_y")

    if not pan_x:
        pan_x = 0

    if not pan_y:
        pan_y = 0

    if "config" not in jnet:
        jnet["config"] = {}

    jnet["config"]["zoom"] = zoom
    jnet["config"]["pan_x"] = pan_x
    jnet["config"]["pan_y"] = pan_y

    net.network = json.dumps(jnet)
    db.session.commit()

    ret = {"message": "Done"}
    return make_response(jsonify(ret), 200)


@login_required
def delete_network():
    user = current_user
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        flash("Пропущен параметр GUID. И какую сеть мне удалить?!")
        return redirect("home")

    net = (
        Network.query.filter(Network.guid == network_guid)
        .filter(Network.author_id == user.id)
        .first()
    )

    if not net:
        flash("Нет такой сети")
        return redirect("home")

    if request.method == "POST":
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()

        # Remove all previous simulations
        for s in sims:
            db.session.delete(s)
            db.session.commit()

        db.session.delete(net)
        db.session.commit()

    return redirect(url_for("home"))


def web_network_shared():
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        flash("Пропущен параметр GUID. И какую сеть мне открыть?!")
        return redirect(url_for("home"))

    net = Network.query.filter(Network.guid == network_guid).first()

    if not net:
        flash("Нет такой сети")
        return redirect(url_for("home"))

    if not net.share_mode:
        flash("Сеть закрыта для общего доступа")
        return redirect(url_for("home"))

    jnet = json.loads(net.network)

    # Do we simulated this network already
    sim = (
        Simulate.query.filter(Simulate.network_id == net.id)
        .order_by(Simulate.id.desc())
        .first()
    )
    jnet["packets"] = "null"

    if sim:
        if sim.ready:
            jnet["packets"] = sim.packets

    if "nodes" not in jnet:
        jnet["nodes"] = []

    if "edges" not in jnet:
        jnet["edges"] = []

    if "jobs" not in jnet:
        jnet["jobs"] = []

    if "config" not in jnet:
        jnet["config"] = {"zoom": 2, "pan_x": 0, "pan_y": 0}

    # Check if we have a pcaps. If not, try to check for it.
    if "pcap" not in jnet:
        jnet["pcap"] = []

    pcap_dir = "static/pcaps/" + network_guid

    if os.path.exists(pcap_dir):
        jnet["pcap"] = [
            os.path.splitext(f)[0]
            for f in os.listdir(pcap_dir)
            if os.path.isfile(os.path.join(pcap_dir, f))
        ]
        net.network = json.dumps(jnet)
        db.session.commit()

    json_nodes = json.dumps(jnet["nodes"])

    return render_template(
        "network_shared.html",
        network=net,
        nodes=json_nodes,
        edges=jnet["edges"],
        packets=jnet["packets"],
        jobs=jnet["jobs"],
        network_config=jnet["config"],
        pcaps=jnet["pcap"],
        mimishark_nav=1,
    )


def web_network():
    user = current_user
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        flash("Пропущен параметр GUID. И какую сеть мне открыть?!")
        return redirect(url_for("home"))

    net = Network.query.filter(Network.guid == network_guid).first()

    if not net:
        flash("Нет такой сети")
        return redirect("home")

    # Anonymous? Redirect to share version.
    if user.is_anonymous:
        if net.share_mode:
            return redirect(url_for("web_network_shared", guid=net.guid))
        else:
            return redirect(url_for("login_index"))

    # If author is not user
    if net.author_id != user.id:
        if net.share_mode:
            return redirect(url_for("web_network_shared", guid=net.guid))
        else:
            return redirect(url_for("home"))

    jnet = json.loads(net.network)

    # Do we simulated this network already
    sim = (
        Simulate.query.filter(Simulate.network_id == net.id)
        .order_by(Simulate.id.desc())
        .first()
    )
    jnet["packets"] = "null"

    if sim:
        if sim.ready:
            jnet["packets"] = sim.packets

    if "nodes" not in jnet:
        jnet["nodes"] = []

    if "edges" not in jnet:
        jnet["edges"] = []

    if "jobs" not in jnet:
        jnet["jobs"] = []

    if "config" not in jnet:
        jnet["config"] = {"zoom": 2, "pan_x": 0, "pan_y": 0}

    # Check if we have a pcaps. If not, try to check for it.
    if "pcap" not in jnet:
        jnet["pcap"] = []

    pcap_dir = "static/pcaps/" + network_guid

    if os.path.exists(pcap_dir):
        jnet["pcap"] = [
            os.path.splitext(f)[0]
            for f in os.listdir(pcap_dir)
            if os.path.isfile(os.path.join(pcap_dir, f))
        ]
        net.network = json.dumps(jnet)
        db.session.commit()

    json_nodes = json.dumps(jnet["nodes"])

    return render_template(
        "network.html",
        network=net,
        nodes=json_nodes,
        edges=jnet["edges"],
        packets=jnet["packets"],
        jobs=jnet["jobs"],
        simulating=sim,
        network_config=jnet["config"],
        pcaps=jnet["pcap"],
        mimishark_nav=1,
    )


def generate_image_uri(extension=".png"):
    return os.urandom(16).hex() + extension


# Depricated?
@login_required
def post_nodes():
    user = current_user
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        ret = {"message": "Пропущен параметр guid"}
        return make_response(jsonify(ret), 400)

    net = (
        Network.query.filter(Network.guid == network_guid)
        .filter(Network.author_id == user.id)
        .first()
    )

    if not net:
        ret = {"message": "Нет такой сети"}
        return make_response(jsonify(ret), 400)

    if request.method == "POST":
        nodes = request.json
        jnet = json.loads(net.network)
        jnet["nodes"] = nodes
        net.network = json.dumps(jnet)

        # Remove all previous simulations
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()
        for s in sims:
            db.session.delete(s)

        db.session.commit()

    ret = {"message": "Done", "code": "SUCCESS"}
    return make_response(jsonify(ret), 201)


@login_required
def post_nodes_edges():
    user = current_user
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        ret = {"message": "Пропущен параметр guid"}
        return make_response(jsonify(ret), 400)

    net = (
        Network.query.filter(Network.guid == network_guid)
        .filter(Network.author_id == user.id)
        .first()
    )

    if not net:
        ret = {"message": "Нет такой сети"}
        return make_response(jsonify(ret), 400)

    if request.method == "POST":
        nodes = request.json[0]
        edges = request.json[1]
        jobs = request.json[2]

        for edge in edges:
            edge_data = edge.get("data", {})
            edge_data["loss_percentage"] = edge_data.get("loss_percentage", 0)
            edge_data["duplicate_percentage"] = edge_data.get("duplicate_percentage", 0)

        jnet = json.loads(net.network)
        jnet["edges"] = edges
        jnet["nodes"] = nodes
        jnet["jobs"] = jobs

        # Remove all pcaps
        jnet["pcap"] = []

        net.network = json.dumps(jnet)

        # Remove all previous simulations
        sims = Simulate.query.filter(Simulate.network_id == net.id).all()
        for s in sims:
            db.session.delete(s)

        db.session.commit()

    ret = {"message": "Done", "code": "SUCCESS"}
    return make_response(jsonify(ret), 201)


@login_required
def move_nodes():
    user = current_user
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        ret = {"message": "Пропущен параметр GUID. И какую сеть мне открыть?!"}
        return make_response(jsonify(ret), 400)

    net = (
        Network.query.filter(Network.guid == network_guid)
        .filter(Network.author_id == user.id)
        .first()
    )

    if not net:
        ret = {"message": "Нет такой сети"}
        return make_response(jsonify(ret), 400)

    if request.method == "POST":
        nodes = request.json
        jnet = json.loads(net.network)
        jnet["nodes"] = nodes
        net.network = json.dumps(jnet)
        db.session.commit()

    ret = {"message": "Done", "code": "SUCCESS"}
    return make_response(jsonify(ret), 201)


@login_required
def upload_network_picture():
    user = current_user
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        ret = {"message": "Пропущен параметр GUID. И какую сеть мне открыть?!"}
        return make_response(jsonify(ret), 400)

    net = (
        Network.query.filter(Network.guid == network_guid)
        .filter(Network.author_id == user.id)
        .first()
    )

    if not net:
        ret = {"message": "Нет такой сети"}
        return make_response(jsonify(ret), 400)

    if request.method == "POST":
        picture_blob = request.get_data()

        # Try to save data
        picture_blob_uri = generate_image_uri()

        try:
            open("static/images/preview/" + picture_blob_uri, "wb").write(picture_blob)
        except Exception:
            ret = {"message": "Не могу сохранить PNG"}
            return make_response(jsonify(ret), 400)

        if not check_image_with_pil("static/images/preview/" + picture_blob_uri):
            ret = {"message": "Это не PNG"}
            return make_response(jsonify(ret), 400)

        # Remove old picture
        if (
            net.preview_uri != "first_network.jpg"
            and net.preview_uri != "switch_and_hub.png"
        ):
            if os.path.isfile("static/images/preview" + "/" + net.preview_uri):
                os.unlink("static/images/preview" + "/" + net.preview_uri)

        net.preview_uri = picture_blob_uri
        db.session.commit()
        ret = {"message": "Done"}
        return make_response(jsonify(ret), 200)

    ret = {
        "message": "Неверный запрос",
    }
    return make_response(jsonify(ret), 400)


@login_required
def copy_network():
    user = current_user
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        ret = {"message": "Пропущен параметр GUID. И какую сеть мне открыть?!"}
        return make_response(jsonify(ret), 400)

    net = Network.query.filter(Network.guid == network_guid).first()

    if not net:
        ret = {"message": "Нет такой сети."}
        return make_response(jsonify(ret), 400)

    if request.method == "POST":
        u = uuid.uuid4()
        n = Network(author_id=user.id, guid=str(u))
        n.network = net.network
        n.title = net.title + str(" - копия")

        new_picture_blob_uri = generate_image_uri()
        try:
            shutil.copy2(
                "static/images/preview/" + net.preview_uri,
                "static/images/preview/" + new_picture_blob_uri,
            )
        except Exception:
            ret = {"message": "Не могу сохранить копию PNG"}
            return make_response(jsonify(ret), 400)

        n.preview_uri = new_picture_blob_uri

        db.session.add(n)
        db.session.commit()
        ret = {"message": "Сделана копия.", "new_url": "/web_network?guid=" + str(u)}
        return make_response(jsonify(ret), 200)


@login_required
def get_last_emulation_time():
    """Answer with current last emulation starting time."""
    last_emulation_time = (
        db.session.query(SimulateLog.simulate_start)
        .order_by(SimulateLog.simulate_start.desc())
        .limit(1)
        .scalar()
    )

    if not last_emulation_time:
        return make_response(jsonify({"message": "Никаких эмуляций не найдено."}), 404)

    return make_response(
        jsonify({"time": str(last_emulation_time.isoformat())}),
        200,
    )


@login_required
def get_emulation_queue_size():
    """Answer with current emulation queue size filtered by emulation time."""
    time_filter_req: str = request.args.get("time-filter", type=str).replace(" ", "+")
    time_filter: datetime.datetime = datetime.datetime.fromisoformat(time_filter_req)
    if not time_filter:
        return make_response(
            jsonify({"message": "Пропущен параметр 'time-filter'."}), 400
        )

    emulated_networks_count = (
        SimulateLog.query.filter(not_(SimulateLog.ready))
        .filter(SimulateLog.simulate_start <= time_filter)
        .count()
    )

    return make_response(
        jsonify({"size": emulated_networks_count}),
        200,
    )
