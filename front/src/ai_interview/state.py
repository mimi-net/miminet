from ai_interview.access import now_utc
from ai_interview.access import QUESTION_MODE_BANK_ONLY
from ai_interview.catalog import topic_label
from ai_interview.models import AiInterviewSession
from ai_interview.planner import (
    bank_question_count_for_topics,
    pair_count_for_topics,
    question_position_for_turn,
)
from ai_interview.rubric import MAX_ANSWER_SCORE, score_summary


MAX_ANSWER_CHARS = 1000


def _owned_sessions(user):
    return (
        AiInterviewSession.query.filter_by(user_id=user.id)
        .order_by(AiInterviewSession.created_on.asc(), AiInterviewSession.id.asc())
        .all()
    )


def _session_sort_value(session):
    return session.created_on or now_utc()


def _latest_incomplete_session(user):
    sessions = [
        session
        for session in _owned_sessions(user)
        if session.status in {"active", "failed-recoverable"}
    ]
    if not sessions:
        return None
    return sorted(sessions, key=_session_sort_value)[-1]


def _latest_completed_session(user):
    sessions = [
        session for session in _owned_sessions(user) if session.status == "completed"
    ]
    if not sessions:
        return None
    return sorted(sessions, key=_session_sort_value)[-1]


def _session_for_access_code(user, access_code):
    return (
        AiInterviewSession.query.filter_by(
            user_id=user.id,
            access_code_id=access_code.id,
        )
        .order_by(AiInterviewSession.created_on.desc(), AiInterviewSession.id.desc())
        .first()
    )


def _format_datetime(value):
    if value is None:
        return None
    return value.isoformat()


def _turn_payload(turn, include_answer=False):
    focus = turn.focus
    flow_type = focus["flow_type"]
    payload = {
        "id": turn.id,
        "position": turn.position,
        "flow_type": flow_type,
        "topic_position": focus["topic_position"],
        "question_position": (
            focus["topic_question_position"]
            if flow_type == "bank"
            else question_position_for_turn(focus["pair_position"], flow_type)
        ),
        "topic": {"key": turn.topic_key, "label": topic_label(turn.topic_key)},
        "question": turn.question,
        "feedback": turn.feedback,
    }
    if flow_type != "bank":
        payload["pair_position"] = focus["pair_position"]
        payload["topic_pair_position"] = focus["topic_pair_position"]
    if include_answer:
        payload["answer"] = turn.answer
        payload["answer_score"] = int((turn.analysis or {}).get("answer_score", 0))
        payload["answer_max_score"] = MAX_ANSWER_SCORE
    return payload


def _result_payload(session):
    result = dict(session.final_result or {})
    result.update(score_summary(session.turns))
    result["questions"] = [
        _turn_payload(turn, include_answer=True) for turn in session.turns
    ]
    return result


def _question_count(session):
    if getattr(session, "question_mode", "adaptive") == QUESTION_MODE_BANK_ONLY:
        return bank_question_count_for_topics(session.selected_topics)
    return pair_count_for_topics(session.selected_topics) * 2


def _session_history_item(session):
    turns = sorted(session.turns, key=lambda turn: turn.position)
    answered_questions = len([turn for turn in turns if turn.answer is not None])
    status_labels = {
        "active": "В процессе",
        "failed-recoverable": "Можно продолжить",
        "completed": "Завершено",
    }
    result = session.final_result or {}
    access_code = session.access_code
    return {
        "guid": session.guid,
        "status": session.status,
        "status_label": status_labels.get(session.status, "Черновик"),
        "created_on": _format_datetime(session.created_on),
        "finished_at": _format_datetime(session.finished_at),
        "answered_count": answered_questions,
        "question_count": _question_count(session),
        "grade": result.get("grade"),
        "question_mode": getattr(session, "question_mode", "adaptive"),
        "access_code_label": access_code.label if access_code is not None else None,
        "topics": [
            {"key": topic_key, "label": topic_label(topic_key)}
            for topic_key in session.selected_topics
        ],
    }


def get_interview_history(user):
    sessions = [
        session for session in _owned_sessions(user) if session.status != "aborted"
    ]
    sessions = sorted(sessions, key=_session_sort_value, reverse=True)
    return [_session_history_item(session) for session in sessions]


def _with_history(user, state):
    state["history"] = get_interview_history(user)
    return state


def serialize_session(session, duplicate=False):
    turns = sorted(session.turns, key=lambda turn: turn.position)
    current_turn = next((turn for turn in turns if turn.answer is None), None)
    pair_count = pair_count_for_topics(session.selected_topics)
    state = {
        "status": session.status,
        "session_guid": session.guid,
        "selected_topics": [
            {"key": topic_key, "label": topic_label(topic_key)}
            for topic_key in session.selected_topics
        ],
        "pair_count": pair_count,
        "question_mode": getattr(session, "question_mode", "adaptive"),
        "question_count": _question_count(session),
        "topic_count": len(session.selected_topics),
        "current_turn": (
            _turn_payload(current_turn) if current_turn is not None else None
        ),
        "duplicate": duplicate,
    }
    if session.status == "completed":
        state["result"] = _result_payload(session)
    return state


def ready_state():
    return {
        "status": "ready",
        "history": [],
    }


def attempts_exhausted_state():
    state = ready_state()
    state["notice"] = {
        "type": "info",
        "code": "access_code_attempts_exhausted",
        "message": (
            "Вы использовали все доступные попытки по этому коду. "
            "Результаты можно посмотреть в истории попыток."
        ),
    }
    return state


def find_owned_session(user, session_guid):
    return (
        AiInterviewSession.query.filter(AiInterviewSession.guid == session_guid)
        .filter(AiInterviewSession.user_id == user.id)
        .first()
    )
