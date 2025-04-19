import os
import shutil

from sqlalchemy.orm.exc import StaleDataError

from celery_app import app
from app import app as flask_app
from miminet_model import Simulate, SimulateLog, db, Network


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


@app.task(queue="task-checking-queue")
def check_task_network(data_list):
    """Check network building task and write results to database.

    Args:
        data_list (List[Tuple]): List of tuples (network schema, requirements).
    """

    for net_schema, req in data_list:
        print(f"schema: {net_schema}, requirements: {req}")
