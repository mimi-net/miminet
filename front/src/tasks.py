import os
import shutil
import uuid

from sqlalchemy.orm.exc import StaleDataError

from celery_app import (
    SEND_NETWORK_EXCHANGE,
    EXCHANGE_TYPE,
    app,
)
from app import app as flask_app
from miminet_model import Simulate, SimulateLog, db, Network
from celery.result import AsyncResult, allow_join_result
from celery.exceptions import TimeoutError


@app.task(bind=True, queue="common-results-queue")
def save_simulate_result(self, animation, pcaps):
    task_guid = self.request.id

    with flask_app.app_context():
        sim = Simulate.query.filter(Simulate.task_guid == task_guid).first()

        # Симуляция уже удалена
        if not sim:
            return

        net = Network.query.filter(Network.id == sim.network_id).first()

        if not net:
            return

        simlog = (
            SimulateLog.query.filter(SimulateLog.network_guid == net.guid)
            .order_by(SimulateLog.id.desc())
            .first()
        )

        pcap_dir = "static/pcaps/" + net.guid

        if not os.path.exists(pcap_dir):
            os.makedirs(pcap_dir)
            print("Created pcap dir", pcap_dir)
        else:
            shutil.rmtree(pcap_dir)
            os.makedirs(pcap_dir)

        for pcap in pcaps:
            name = pcap[1]
            with open(pcap_dir + "/" + name + ".pcap", "wb") as file:
                file.write(pcap[0])

        try:
            sim.packets = animation
            sim.ready = True

            if simlog:
                simlog.ready = True

            db.session.commit()
        except StaleDataError:
            return


@app.task(name="tasks.check_task_network", queue="task-checking-queue")
def perform_task_check(data_list):
    """Check network building task and write results to database.

    Args:
        data_list (List[Tuple]): List of tuples (network schema, requirements).
    """

    for network_json, req_json in data_list:
        print(f"Emulate: {network_json}")
        animation = create_emulation_task(network_json)
        print(animation)

        # ... check logic ...


def create_emulation_task(net_schema):
    async_obj = app.send_task(
        "tasks.mininet_worker",
        [net_schema],
        routing_key=str(uuid.uuid4()),
        exchange=SEND_NETWORK_EXCHANGE,
        exchange_type=EXCHANGE_TYPE,
    )

    async_res = AsyncResult(id=async_obj.id, app=app)

    try:
        with allow_join_result():
            animation, _ = async_res.wait(timeout=60)

            return animation
    except TimeoutError:
        # You need to improve the message, perhaps add information about the user or the network name
        raise Exception(f"""Check task failed!\nNetwork Schema: {net_schema}.""")
