import json

from flask import request, make_response, jsonify, abort
from flask_login import login_required, current_user

from quiz.facade.quiz_session_facade import start_session, finish_session
from quiz.service.session_question_service import answer_on_session_question, get_question_by_session_question_id


@login_required
def answer_on_session_question_endpoint():
    res = answer_on_session_question(request.args['id'], request.json, current_user)
    if res[1] == 404 or res[1] == 405:
        abort(res[1])
    return make_response(json.dumps(res[0].to_dict(), default=str), res[1])


@login_required
def get_question_by_session_question_id_endpoint():
    res = get_question_by_session_question_id(request.args['id'])
    if res[1] == 404:
        abort(res[1])
    return make_response(jsonify(res[0]), res[1])


@login_required
def start_session_endpoint():
    res = start_session(request.args['id'], current_user)
    ret = {'session_question_ids': res[0]}
    return make_response(jsonify(ret), res[1])


@login_required
def finish_session_endpoint():
    res = finish_session(request.args['id'], current_user)
    if res[1] == 404 or res[1] == 405:
        abort(res[1])

    return make_response(jsonify(res[0]), res[1])
