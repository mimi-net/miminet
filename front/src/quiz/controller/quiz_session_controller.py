import json
from flask import request, make_response, jsonify, abort, render_template
from flask_login import login_required, current_user

from quiz.facade.quiz_session_facade import (
    start_session,
    finish_session,
    session_result,
    get_result_by_session_guid,
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
def answer_on_session_exam_question_endpoint():
    return make_response("получено", 200)

@login_required
def get_question_by_session_question_id_endpoint():
    res, is_exam, available_answer, status_code = get_question_by_session_question_id(
        request.args["question_id"]
    )

    logging.info(available_answer)

    if status_code == 404:
        abort(status_code)
    return make_response(
        render_template(
            "quiz/sessionQuestion.html",
            question=res,
            is_exam=is_exam,
            available_answer=available_answer,
        ),
        status_code,
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
    res, status = session_result(request.args["id"])
    if status != 200:
        return make_response("Error", status)

    return make_response(
        render_template("quiz/userSessionResult.html", data=res), status
    )


def get_result_by_session_guid_endpoint():
    res = get_result_by_session_guid(request.args["guid"])

    data=res[0].to_dict()

    return make_response(
        render_template(
            "quiz/sessionResult.html", data=res[0].to_dict(), questions_result=res[1]
        ),
        res[1],
    )
