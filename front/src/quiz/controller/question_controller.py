import json
import uuid

from flask import render_template, request, abort, make_response, jsonify, session
from flask_login import login_required, current_user

from quiz.facade.question_facade import create_question, delete_question
from quiz.service.question_service import get_questions_by_section
from quiz.util.encoder import UUIDEncoder

from miminet_model import Network, db
from quiz.entity.entity import Test


@login_required
def get_questions_by_section_endpoint():
    res = get_questions_by_section(request.args["id"])
    if res[1] == 404 or res[1] == 403:
        abort(res[1])

    return make_response(
        json.dumps([obj.__dict__ for obj in res[0]], cls=UUIDEncoder, default=str),
        res[1],
    )


@login_required
def create_question_endpoint():
    if request.method == "POST":
        section_id = request.args.get("section_id", None)
        res = create_question(section_id, request.json, current_user)
        if res[2] == 404 and "message" in res[1]:
            msg = res[1]["message"]
            ret = {"message": f"{msg}"}
        elif res[2] == 404:
            ret = {"message": "Не существует данного раздела", "section_id": section_id}
        elif res[2] == 403:
            ret = {"message": "Нельзя создать вопрос по чужому разделу", "section_id": section_id}
        elif res[2] == 400 and "missing" in res[1]:
            ret = {"message": "Некоторые изображения отсутствуют", "details": res[1]}
        elif res[2] == 400 and "message" in res[1]:
            ret = {
                "message": "Ваши требования не удовлетворяют шаблону.",
                "details": res[1],
            }
        elif res[2] == 400:
            ret = {
                "message": "Нельзя создать вопрос с данными параметрами в данном разделе",
                "section_id": section_id
            }
        else:
            ret = {"message": "Вопрос создан", "question_ids": res[1], "section_id": res[0]}

        if "launch_id" in session and res[2] == 201: return make_response(res[0])
        return make_response(jsonify(ret), res[2])
    
    elif request.method == "GET":
        network_id = request.args.get("network_id", None)
        if network_id is None:
            network = Network(
                guid=uuid.uuid4(),
                author_id=current_user.id,
                title="Сеть для нового задания",
                description="Создайте сеть, которая будет начальной конфигурацией в данном задании",
                is_task=True,
            )

            db.session.add(network)
            db.session.commit()
        else:
            network = Network.query.filter(
                Network.guid == network_id
            ).first()

            if network.author_id != current_user.id: 
                raise Exception("Используйте созданную вами сеть")

        return make_response(render_template("quiz/createQuestionForm.html", network=network, is_lti=("launch_id" in session), mimishark_nav=1))


@login_required
def delete_question_endpoint():
    question_id = request.args["id"]

    res = delete_question(request.args["id"], current_user)
    if res == 404:
        ret = {"message": "Вопрос не существует", "id": question_id}
    elif res == 403:
        ret = {
            "message": "Попытка удалить чужой вопрос или нет прав",
            "id": question_id,
        }
    elif res == 409:
        ret = {"message": "Попытка удалить удалённый вопрос", "id": question_id}
    else:
        ret = {"message": "Вопрос удалён", "id": question_id}

    return make_response(jsonify(ret), res)
