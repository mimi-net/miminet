import os
import shutil
import uuid
import logging
import json

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

from quiz.service.session_question_service import (
    answer_on_exam_question,
    answer_on_exam_without_session,
)


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
def perform_task_check(session_question_id, data_list):
    """Celery task for checking practice tasks. Write results to database.

    Args:
        session_question_id: Id of the current task in the db
        data_list (List[Tuple]): List of tuples (network schema, requirements).
    """

    networks_to_check = []

    if session_question_id is None:
        for network_json, req_json, modifications_json, guid in data_list:
            try:
                network_json = (
                    json.loads(network_json)
                    if isinstance(network_json, str)
                    else network_json
                )
                req_json = (
                    json.loads(req_json) if isinstance(req_json, str) else req_json
                )
                modifications_json = (
                    json.loads(modifications_json)
                    if isinstance(modifications_json, str)
                    else modifications_json
                )

                animation = create_emulation_task(network_json)
                networks_to_check.append(
                    (network_json, animation, req_json, modifications_json)
                )

            except Exception as e:
                logging.error(f"Ошибка при создании задачи: {e}.")

        answer_on_exam_without_session(networks_to_check, guid)

    else:
        for network_json, req_json, modifications_json in data_list:
            try:
                network_json = (
                    json.loads(network_json)
                    if isinstance(network_json, str)
                    else network_json
                )
                req_json = (
                    json.loads(req_json) if isinstance(req_json, str) else req_json
                )
                modifications_json = (
                    json.loads(modifications_json)
                    if isinstance(modifications_json, str)
                    else modifications_json
                )

                animation = create_emulation_task(network_json)
                networks_to_check.append(
                    (network_json, animation, req_json, modifications_json)
                )

            except Exception as e:
                logging.error(f"Ошибка при создании задачи: {e}.")

        with flask_app.app_context():
            answer_on_exam_question(session_question_id, networks_to_check)


def create_emulation_task(net_schema):
    if not net_schema.get("jobs"):
        return []

    net_schema = (
        json.dumps(net_schema) if not isinstance(net_schema, str) else net_schema
    )

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
            animation, _ = async_res.wait(timeout=120)

            return animation
    except TimeoutError:
        # TODO improve error message (add user info)
        raise Exception(f"""Check task failed!\nNetwork Schema: {net_schema}.""")
