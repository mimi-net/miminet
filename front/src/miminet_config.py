import os
import pathlib
from datetime import datetime
from PIL import Image

SECRET_KEY_FILE = os.path.join(pathlib.Path(__file__).parent, "miminet_secret.conf")
SECRET_KEY = ""

if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, "r") as file:
        SECRET_KEY = file.read().rstrip()
else:
    print("There is no SECRET_KEY_FILE, generate random SECRET_KEY")
    SECRET_KEY = os.urandom(16).hex()


SQLITE_DATABASE_NAME = "miminet.db"

current_data = datetime.today().strftime("%Y-%m-%d")
SQLITE_DATABASE_BACKUP_NAME = "backup_" + current_data + ".db"


def make_empty_network():
    return (
        '{"nodes" : [], "edges" : [], "jobs" : [], "config" : {"zoom" : 2, "pan_x": 0 ,'
        ' "pan_y": 0}}'
    )


def make_example_net_switch_and_hub():
    return (
        '{"nodes": [{"classes": ["l2_switch"], "config": {"label": "l2sw1", "type":'
        ' "l2_switch"},"data": {"id": "l2sw1", "label": "l2sw1"},"interface":'
        ' [{"connect": "edge_lecszk09edp01gxyfdw", "id": "l2sw1_1", "name":'
        ' "l2sw1_1"},{"connect": "edge_lecsztzmmr9hg7nabv", "id": "l2sw1_2", "name":'
        ' "l2sw1_2"},{"connect": "edge_lect0ujovtnu3vu4k9j", "id": "l2sw1_3", "name":'
        ' "l2sw1_3"}],"position": {"x": 116.88900151787291, "y":'
        ' 54.29980837569416}},{"classes": ["l1_hub"], "config": {"label": "l1hub1",'
        ' "type": "l1_hub"},"data": {"id": "l1hub1", "label": "l1hub1"},"interface":'
        ' [{"connect": "edge_lecszsmarkkbrnjfxsh", "id": "l1hub1_1", "name":'
        ' "l1hub1_1"},{"connect": "edge_lecsztzmmr9hg7nabv", "id": "l1hub1_2", "name":'
        ' "l1hub1_2"},{"connect": "edge_lecszwkj36zl99wxqto", "id": "l1hub1_3", "name":'
        ' "l1hub1_3"}],"position": {"x": 229.5881438315644, "y":'
        ' 54.99786432300368}},{"classes": ["host"], "config": {"label": "host_1",'
        ' "type": "host", "default_gw": ""},"data": {"id": "host_1", "label":'
        ' "host_1"}, "interface": [{"connect": "edge_lecszk09edp01gxyfdw", "id":'
        ' "iface_57306012", "ip": "10.0.0.1","name": "iface_57306012", "netmask":'
        ' 24}],"position": {"x": 36.223748916284435, "y":'
        ' -10.44814358474117}},{"classes": ["host"], "config": {"label": "host_2",'
        ' "type": "host", "default_gw": ""},"data": {"id": "host_2", "label":'
        ' "host_2"}, "interface": [{"connect": "edge_lecszsmarkkbrnjfxsh", "id":'
        ' "iface_2264405", "ip": "10.0.0.2","name": "iface_2264405", "netmask":'
        ' 24},{"id": "iface_8674634", "name": "iface_8674634", "connect":'
        ' "edge_leodb0i042efyciiaci"}],"position": {"x": 310.2812404364625, "y":'
        ' -23.310532960674266}},{"classes": ["host"], "config": {"label": "host_3",'
        ' "type": "host"},"data": {"id": "host_3", "label": "host_3"},"interface":'
        ' [{"connect": "edge_lecszwkj36zl99wxqto", "id": "iface_6176562", "name":'
        ' "iface_6176562"}],"position": {"x": 305.92699885106083, "y":'
        ' 122.56103491577151}},{"classes": ["host"], "config": {"label": "host_4",'
        ' "type": "host", "default_gw": ""},"data": {"id": "host_4", "label":'
        ' "host_4"}, "interface": [{"connect": "edge_lect0ujovtnu3vu4k9j", "id":'
        ' "iface_6631183", "ip": "10.0.0.4","name": "iface_6631183", "netmask":'
        ' 24}],"position": {"x": 38.67780079395636, "y": 123.65267304098761}}],"edges":'
        ' [{"data": {"id": "edge_lecszk09edp01gxyfdw", "source": "host_1", "target":'
        ' "l2sw1"}},{"data": {"id": "edge_lecszsmarkkbrnjfxsh", "source": "host_2",'
        ' "target": "l1hub1"}},{"data": {"id": "edge_lecsztzmmr9hg7nabv", "source":'
        ' "l2sw1", "target": "l1hub1"}},{"data": {"id": "edge_lecszwkj36zl99wxqto",'
        ' "source": "host_3", "target": "l1hub1"}},{"data": {"id":'
        ' "edge_lect0ujovtnu3vu4k9j", "source": "host_4", "target": "l2sw1"}}], "jobs":'
        ' [{"id": "66b08903e18742998362cde8b43ddae3", "level": 0, "job_id": 1,'
        ' "host_id": "host_1", "arg_1": "10.0.0.2","print_cmd": "ping -c 1'
        ' 10.0.0.2"}],"config": {"zoom": 1.8751240138517626, "pan_x":'
        ' 108.98172306193487, "pan_y": 179.24277602686317},"packets": "","pcap": []}'
    )


def check_image_with_pil(file):
    try:
        Image.open(file)
    except IOError:
        return False
    return True


# def add_examples_network_to_profile(user_id):
#     u = uuid.uuid4()
#
#     n = Network(author_id=user_id, guid=str(u))
#     db.session.add(n)
#     db.session.flush()
#     db.session.refresh(n)
#     db.session.commit()
