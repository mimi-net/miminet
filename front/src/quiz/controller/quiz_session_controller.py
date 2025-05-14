import json
from flask import request, make_response, jsonify, abort, render_template
from flask_login import login_required, current_user

from quiz.facade.quiz_session_facade import (
    start_session,
    finish_session,
    session_result,
    get_result_by_session_guid,
    finish_old_sessions,
)
from quiz.service.session_question_service import (
    answer_on_session_question,
    get_question_by_session_question_id,
    handle_exam_answer,
    get_session_question_data,
)

# from quiz.service.network_upload_service import create_check_task


@login_required
def answer_on_session_question_endpoint():
    res = answer_on_session_question(request.args["id"], request.json, current_user)
    if res[1] == 404 or res[1] == 403:
        abort(res[1])
    return make_response(json.dumps(res[0].to_dict(), default=str), res[1])


@login_required
def get_session_question_json():
    session_question_id = request.args.get("question_id")
    data, status = get_session_question_data(session_question_id)
    if status != 200:
        return (
            jsonify({"error": "Not found" if status == 404 else "Missing question_id"}),
            status,
        )

    return jsonify(data)


@login_required
def check_network_task_endpoint():
    session_question_id = request.args["id"]
    answer = request.json
    user = current_user

    result, aux, status = handle_exam_answer(session_question_id, answer, user)

    if status != 200:
        abort(status)

    if aux is None:
        # Теория — сразу отправляем результат
        return make_response("Вопрос проверен", 200)

    # Раскомментировать, когда снова потребуется проверять сразу же!!!

    # requirements, network = result, aux
    # res_code = create_check_task(network, requirements, session_question_id)
    # if res_code == 404 or res_code == 403:
    #     abort(res_code)

    return make_response("Практическая задача отправлена на проверку", 200)


@login_required
def get_question_by_session_question_id_endpoint():
    result = get_question_by_session_question_id(request.args["question_id"])

    if result == 404:
        abort(404)
    (
        res,
        is_exam,
        timer,
        available_answer,
        available_from,
        session_question_id,
        status_code,
    ) = result

    return make_response(
        render_template(
            "quiz/sessionQuestion.html",
            question=res,
            timer=timer,
            is_exam=is_exam,
            available_from=available_from,
            session_question_id=session_question_id,
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
def finish_old_session_endpoint():
    code = finish_old_sessions(current_user)

    if code == 404:
        abort(404)
    return make_response(
        jsonify({"message": "Старые сессии завершены или удалены"}), code
    )


@login_required
def session_result_endpoint():
    res, status = session_result(request.args["id"])
    if status != 200:
        return make_response("Error", status)

    return make_response(
        render_template("quiz/userSessionResult.html", data=res), status
    )


def get_result_by_session_guid_endpoint():
    result, status = get_result_by_session_guid(request.args["guid"])

    if result is None:
        return make_response(
            render_template("quiz/noResult.html", error="no_results"),
            status,
        )

    data = result
    questions_result = data.results

    return make_response(
        render_template(
            "quiz/sessionResult.html",
            data=data.to_dict(),
            questions_result=questions_result,
            error=None,
        ),
        status,
    )
