import json
import os.path

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from miminet_model import Network
from pcap_parser import from_pcap_to_json

test_mimishark_json_file = "static/mimi_shark/test_mimishark_json_file.json"
test_mimishark_pcap_file = "static/mimi_shark/test_mimishark_pcap_file.pcap"


def mimishark_page():
    user = current_user
    network_guid = request.args.get("guid", type=str)
    iface = request.args.get("iface", type=str)

    if not network_guid:
        flash("Пропущен параметр GUID. И какую сеть мне открыть?!")
        return redirect(url_for("home"))

    if not iface:
        flash("Пропущен параметр iface. Для какого интерфейса показать pcap?")
        return redirect(url_for("home"))

    net = Network.query.filter(Network.guid == network_guid).first()

    if not net:
        flash("Нет такой сети")
        return redirect("home")

    # Anonymous? Redirect to share version.
    if user.is_anonymous:
        if not net.share_mode:
            flash("У вас нет доступа к этой сети")
            return redirect(url_for("index"))

    pcap_dir = "static/pcaps/" + network_guid

    if not os.path.exists(pcap_dir):
        flash("Нет PCAP файлов")
        return redirect("home")

    # Do we have a pcap file for a given iface?
    if not os.path.exists(pcap_dir + "/" + iface + ".pcap"):
        flash("Нет PCAP файла для интерфейса " + iface)
        return redirect("home")

    # Do we have a json file?
    if not os.path.exists(pcap_dir + "/" + iface + ".json"):
        from_pcap_to_json(
            pcap_dir + "/" + iface + ".pcap", pcap_dir + "/" + iface + ".json"
        )

    # Get JSON file
    if not os.path.isfile(pcap_dir + "/" + iface + ".json"):
        flash("Нет такого JSON файла с пакетами")
        return redirect(url_for("home"))

    json_pcap_data = ""

    with open(pcap_dir + "/" + iface + ".json", encoding="utf-8-sig") as json_data:
        json_pcap_data = json.load(json_data)

    return render_template(
        "mimishark.html", pcap_data=json_pcap_data, mimishark_nav=1, network=net
    )
