from flask import Flask, jsonify, render_template, request
from miminet_model import db, Network, Simulate
from flask_login import login_required, current_user
from pcap_parser import Add_Json
import json

path = "static/mimi_shark/pcap.json"


def ReadJson(path):
    Add_Json()
    with open(path, encoding='utf-8-sig') as json_data:
        data = json.load(json_data)
    return data

def mimishark_page():
    user = current_user
    network_guid = request.args.get('guid', type=str)
    net = Network.query.filter(Network.guid == network_guid).first()
    data = ReadJson(path)
    return render_template('mimishark.html',pcap_data = data, mimishark_nav = 1)