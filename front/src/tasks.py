import json
import os
import shutil
import uuid
import logging
import logging_config
from sqlalchemy.orm.exc import StaleDataError
from app import app as flask_app
from celery.exceptions import TimeoutError
from celery.result import AsyncResult, allow_join_result
from celery_app import EXCHANGE_TYPE, SEND_NETWORK_EXCHANGE, app
from miminet_model import Network, Simulate, SimulateLog, db
from quiz.service.session_question_service import (
    answer_on_exam_question,
    answer_on_exam_without_session,
)

logger = logging.getLogger(__name__)
logging_config.configure_logging(logger)


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

        simlog = SimulateLog.query.filter(SimulateLog.network_guid == net.guid)

        if not simlog:
            return

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
            simlog.update({"ready": 1})

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
                logger.error(
                    "Check task emulation create failed",
                    extra={"error": str(e), "guid": guid},
                )

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
                logger.error(
                    "Check task emulation create failed",
                    extra={
                        "error": str(e),
                        "session_question_id": session_question_id,
                    },
                )

        with flask_app.app_context():
            answer_on_exam_question(session_question_id, networks_to_check)


def create_emulation_task(net_schema):
    if not net_schema.get("jobs"):
        return []

    net_schema = (
        json.dumps(net_schema) if not isinstance(net_schema, str) else net_schema
    )
    routing_key = str(uuid.uuid4())

    # Log start of sending task to RabbitMQ
    logger.info(
        "Rabbitmq send task start",
        extra={"routing_key": routing_key, "exchange": SEND_NETWORK_EXCHANGE.name},
    )

    try:
        async_obj = app.send_task(
            "tasks.mininet_worker",
            [net_schema],
            routing_key=routing_key,
            exchange=SEND_NETWORK_EXCHANGE,
            exchange_type=EXCHANGE_TYPE,
        )
    except Exception as e:
        # Log broker rejection (incl. disk_free_limit)
        logger.error(
            "Rabbitmq send task failed",
            extra={
                "routing_key": routing_key,
                "exchange": SEND_NETWORK_EXCHANGE.name,
                "error": str(e),
                "hint": "Check RabbitMQ disk_free_limit and broker availability",
            },
        )
        raise

    # Log successful scheduling of task in queue
    logger.info(
        "Rabbitmq send task scheduled",
        extra={"routing_key": routing_key, "task_id": async_obj.id},
    )

    async_res = AsyncResult(id=async_obj.id, app=app)

    try:
        with allow_join_result():
            animation, _ = async_res.wait(timeout=120)

            # Log successful result receipt from worker
            logger.info(
                "Rabbitmq receive result success",
                extra={"routing_key": routing_key, "task_id": async_obj.id},
            )
            return animation
    except TimeoutError:
        # Log timeout while waiting for result
        logger.error(
            "Rabbitmq receive result timeout",
            extra={"routing_key": routing_key, "task_id": async_obj.id},
        )
        # TODO improve error message (add user info)
        raise Exception(f"""Check task failed!\nNetwork Schema: {net_schema}.""")
    except Exception as e:
        # Log any other errors while waiting for result
        logger.error(
            "Rabbitmq receive result failed",
            extra={
                "routing_key": routing_key,
                "task_id": async_obj.id,
                "error": str(e),
            },
        )
        raise
