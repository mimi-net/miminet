from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from ai_interview.catalog import public_topics
from ai_interview.engine import (
    abort_interview,
    get_interview_result,
    get_interview_result_by_guid,
    get_interview_state,
    start_interview,
    submit_answer,
)
from ai_interview.errors import InterviewError
from ai_interview.providers import ProviderError, ProviderNotConfigured


ai_interview_routes = Blueprint("ai_interview", __name__)


def _json_error(error, default_status=502):
    status = getattr(error, "status_code", default_status)
    return jsonify({"error": str(error)}), status


@ai_interview_routes.route("/ai-testing", methods=["GET"])
@login_required
def interview_page():
    return render_template(
        "ai_interview/interview.html",
        topics=public_topics(),
        result_guid=None,
    )


@ai_interview_routes.route("/ai-testing/result/<session_guid>", methods=["GET"])
@login_required
def interview_result_page(session_guid):
    return render_template(
        "ai_interview/interview.html",
        topics=public_topics(),
        result_guid=session_guid,
    )


@ai_interview_routes.route("/ai-testing/api/state", methods=["GET"])
@login_required
def interview_state_endpoint():
    try:
        return jsonify(get_interview_state(current_user))
    except InterviewError as error:
        return _json_error(error)


@ai_interview_routes.route("/ai-testing/api/start", methods=["POST"])
@login_required
def start_interview_endpoint():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(
            start_interview(
                current_user,
                payload.get("topics", []),
                payload.get("access_code"),
            )
        )
    except (InterviewError, ProviderNotConfigured) as error:
        return _json_error(error, default_status=503)
    except ProviderError as error:
        return _json_error(error)


@ai_interview_routes.route("/ai-testing/api/answer", methods=["POST"])
@login_required
def answer_interview_endpoint():
    payload = request.get_json(silent=True) or {}
    try:
        turn_id = int(payload.get("turn_id", 0))
    except (TypeError, ValueError):
        turn_id = 0

    try:
        return jsonify(submit_answer(current_user, turn_id, payload.get("answer")))
    except (InterviewError, ProviderNotConfigured) as error:
        return _json_error(error, default_status=503)
    except ProviderError as error:
        return _json_error(error)


@ai_interview_routes.route("/ai-testing/api/abort", methods=["POST"])
@login_required
def abort_interview_endpoint():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(abort_interview(current_user, payload.get("session_guid")))
    except InterviewError as error:
        return _json_error(error)


@ai_interview_routes.route("/ai-testing/api/result", methods=["GET"])
@login_required
def interview_result_endpoint():
    try:
        session_guid = request.args.get("guid")
        if session_guid:
            return jsonify(get_interview_result_by_guid(current_user, session_guid))
        return jsonify(get_interview_result(current_user))
    except InterviewError as error:
        return _json_error(error)
