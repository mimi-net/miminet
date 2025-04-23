from miminet_model import Network
from celery_app import app
import json


# Сейчас тут не приходят netwiork и requiremetns,
# но эндпоинт пришлет их в формате json 
def create_check_task(network, requirements):
    """
    Prepare task and send it for processing.
    """
    # You need to pass into 'prepare_task_network' user's network schema and task requirements
    # I just use test data for example
    res_data = prepare_network(
        json.dumps(TEST_NETWORK_DATA), "*here should be requirements*"
    )

    # send task
    app.send_task(
        "tasks.check_task_network",
        [res_data],
        routing_key="task-checking-routing-key",
        exchange="task-checking-exchange",
        exchange_type="direct",
    )

    # return "OK" code
    return 200


def prepare_network(user_network: Network, task_req: str):
    """
    Prepare task according to requirements:
    - Split task to several separate network schemas,
    - Modify these schemas.

    Args:
        user_network (Network): Network schema developed by user.
        task_req (str): Task requirements (description of what we need to check).

    Returns:
        List[Tuple]: List of tuples (network schema, requirements).
    """

    # ... all task prepare logic should be here ...

    return [(user_network, task_req)]


TEST_NETWORK_DATA = {
    "nodes": [
        {
            "data": {"id": "host_1", "label": "host_1"},
            "position": {"x": 22, "y": 150.5},
            "classes": ["host"],
            "config": {"type": "host", "label": "host_1", "default_gw": ""},
            "interface": [
                {
                    "id": "iface_16775240",
                    "name": "iface_16775240",
                    "connect": "edge_m3qcgwpcn8sunskeewe",
                    "ip": "192.168.1.1",
                    "netmask": 24,
                }
            ],
        },
        {
            "data": {"id": "host_2", "label": "host_2"},
            "position": {"x": 330.5, "y": 343},
            "classes": ["host"],
            "config": {"type": "host", "label": "host_2", "default_gw": ""},
            "interface": [
                {
                    "id": "iface_45420688",
                    "name": "iface_45420688",
                    "connect": "edge_m3qcgwpcn8sunskeewe",
                    "ip": "192.168.1.2",
                    "netmask": 24,
                }
            ],
        },
    ],
    "edges": [
        {
            "data": {
                "id": "edge_m3qcgwpcn8sunskeewe",
                "source": "host_1",
                "target": "host_2",
            }
        }
    ],
    "jobs": [
        {
            "id": "e9853215a9ce47069dad4fd6ba4971e9",
            "job_id": 1,
            "print_cmd": "ping -c 1 192.168.1.2",
            "arg_1": "192.168.1.2",
            "level": 0,
            "host_id": "host_1",
        }
    ],
    "config": {"zoom": 2, "pan_x": 0, "pan_y": 0},
}
