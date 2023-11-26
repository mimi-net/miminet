import json

from flask import request, abort, make_response, jsonify
from flask_login import login_required, current_user

from quiz.facade.question_facade import create_question
from quiz.service.question_service import get_questions_by_section
from quiz.util.encoder import UUIDEncoder


@login_required
def get_questions_by_section_endpoint():
    res = get_questions_by_section(request.args['id'])
    if res[1] == 404 or res[1] == 405:
        abort(res[1])
    else:
        return make_response(json.dumps([obj.__dict__ for obj in res[0]], cls=UUIDEncoder, default=str), res[1])


@login_required
def create_question_endpoint():
    res = create_question(request.json['id'], request.json, current_user)
    if res[1] == 404 or res[1] == 405:
        abort(res[1])

    ret = {'message': 'Вопрос добавлен', 'id': res[0]}

    return make_response(jsonify(ret), res[1])
