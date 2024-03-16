import json

from flask import request, make_response, jsonify, abort, render_template
from flask_login import login_required, current_user

from quiz.facade.quiz_session_facade import (
    start_session,
    finish_session,
    session_result,
    get_results_by_user,
)
from quiz.service.session_question_service import (
    answer_on_session_question,
    get_question_by_session_question_id,
)


@login_required
def answer_on_session_question_endpoint():
    res = answer_on_session_question(request.args["id"], request.json, current_user)
    if res[1] == 404 or res[1] == 403:
        abort(res[1])
    return make_response(json.dumps(res[0].to_dict(), default=str), res[1])


@login_required
def get_question_by_session_question_id_endpoint():
    res = get_question_by_session_question_id(request.args["question_id"])
    if res[1] == 404:
        abort(res[1])
    return make_response(
        render_template("quiz/sessionQuestion.html", question=res[0]), res[1]
    )


@login_required
def start_session_endpoint():
    res = start_session(request.args["section_id"], current_user)

    if res[2] == 404:
        abort(res[2])
    if res[2] == 403:
        ret = {"message": "Данный раздел уже пройден вами"}
    else:
        ret = {"quiz_session_id": res[0], "session_question_ids": res[1]}
    return make_response(jsonify(ret), res[2])


@login_required
def finish_session_endpoint():
    code = finish_session(request.args["id"], current_user)
    if code == 404 or code == 403:
        abort(code)
    ret = {"message": "Сессия завершена", "id": request.args["id"]}
    return make_response(ret, code)


@login_required
def session_result_endpoint():
    res = session_result(request.args["id"])
    ret = {"time_spent": res[2], "correct_answers": res[0], "answer_count": res[1]}
    return make_response(render_template("quiz/sessionResult.html", data=ret), res[3])


@login_required
def get_results_by_user_endpoint():
    res = get_results_by_user(current_user)
    return make_response(json.dumps([obj.__dict__ for obj in res], default=str), 200)
