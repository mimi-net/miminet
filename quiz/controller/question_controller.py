import json

from flask import request, abort, make_response, jsonify, render_template
from flask_login import login_required, current_user

from quiz.facade.question_facade import create_question
from quiz.service.question_service import get_questions_by_section
from quiz.service.section_service import get_section
from quiz.service.test_service import get_test
from quiz.util.encoder import UUIDEncoder


@login_required
def get_questions_by_section_endpoint():
    section_id = request.args['id']
    res = get_questions_by_section(request.args['id'])
    if res[1] == 404 or res[1] == 405:
        abort(res[1])
    else:
        questions = res[0]
        section = get_section(section_id)[0]
        test_name = get_test(section.test_id)[0].name
        return make_response(render_template("quiz/section.html", questions=questions, section_name=section.name, test_name=test_name), res[1])


@login_required
def create_question_endpoint():
    res = create_question(request.json['id'], request.json, current_user)
    if res[1] == 404 or res[1] == 405:
        abort(res[1])

    ret = {'message': 'Вопрос добавлен', 'id': res[0]}

    return make_response(jsonify(ret), res[1])
