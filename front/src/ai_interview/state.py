from ai_interview.access import now_utc
from ai_interview.catalog import public_topics, topic_label
from ai_interview.models import AiInterviewAttempt, AiInterviewSession
from ai_interview.planner import MIN_QUESTIONS, MAX_QUESTIONS, question_limit_for_topics


MAX_ANSWER_CHARS = 1000


def _last_session(attempt):
    sessions = sorted(
        attempt.sessions, key=lambda session: session.created_on or now_utc()
    )
    return sessions[-1] if sessions else None


def _owned_attempts(user):
    return (
        AiInterviewAttempt.query.filter_by(user_id=user.id)
        .order_by(AiInterviewAttempt.created_on.asc(), AiInterviewAttempt.id.asc())
        .all()
    )


def _session_sort_value(session):
    return session.created_on or now_utc()


def _latest_incomplete_session(user):
    sessions = []
    for attempt in _owned_attempts(user):
        sessions.extend(
            session
            for session in attempt.sessions
            if session.status in {"active", "failed-recoverable"}
        )
    if not sessions:
        return None
    return sorted(sessions, key=_session_sort_value)[-1]


def _latest_completed_session(user):
    sessions = []
    for attempt in _owned_attempts(user):
        sessions.extend(
            session for session in attempt.sessions if session.status == "completed"
        )
    if not sessions:
        return None
    return sorted(sessions, key=_session_sort_value)[-1]


def _attempt_for_access_code(user, access_code):
    return (
        AiInterviewAttempt.query.filter_by(
            user_id=user.id,
            access_code_id=access_code.id,
        )
        .order_by(AiInterviewAttempt.created_on.desc(), AiInterviewAttempt.id.desc())
        .first()
    )


def _format_datetime(value):
    if value is None:
        return None
    return value.isoformat()


def _turn_payload(turn, include_answer=False):
    payload = {
        "id": turn.id,
        "position": turn.position,
        "topic": {"key": turn.topic_key, "label": topic_label(turn.topic_key)},
        "question": turn.question,
        "feedback": turn.feedback,
    }
    if include_answer:
        payload["answer"] = turn.answer
        payload["answer_summary"] = turn.answer_summary
    return payload


def _result_payload(session):
    result = dict(session.final_result or {})
    result["questions"] = [
        _turn_payload(turn, include_answer=True) for turn in session.turns
    ]
    result["status_label"] = "Сессия завершена"
    return result


def _session_history_item(session):
    turns = sorted(session.turns, key=lambda turn: turn.position)
    answered_count = len([turn for turn in turns if turn.answer is not None])
    question_count = question_limit_for_topics(session.selected_topics)
    status_labels = {
        "active": "В процессе",
        "failed-recoverable": "Можно продолжить",
        "completed": "Завершено",
    }
    result = session.final_result or {}
    access_code = session.attempt.access_code
    return {
        "guid": session.guid,
        "status": session.status,
        "status_label": status_labels.get(session.status, "Черновик"),
        "created_on": _format_datetime(session.created_on),
        "finished_at": _format_datetime(session.finished_at),
        "answered_count": answered_count,
        "question_count": question_count,
        "grade": result.get("grade"),
        "access_code_label": access_code.label if access_code is not None else None,
        "topics": [
            {"key": topic_key, "label": topic_label(topic_key)}
            for topic_key in session.selected_topics
        ],
    }


def get_interview_history(user):
    sessions = []
    for attempt in _owned_attempts(user):
        sessions.extend(
            session for session in attempt.sessions if session.status != "aborted"
        )
    sessions = sorted(sessions, key=_session_sort_value, reverse=True)
    return [_session_history_item(session) for session in sessions]


def _with_history(user, state):
    state["history"] = get_interview_history(user)
    return state


def serialize_session(session, resumed=False, duplicate=False):
    turns = sorted(session.turns, key=lambda turn: turn.position)
    current_turn = next((turn for turn in turns if turn.answer is None), None)
    question_limit = question_limit_for_topics(session.selected_topics)
    state = {
        "enabled": True,
        "status": session.status,
        "session_guid": session.guid,
        "selected_topics": [
            {"key": topic_key, "label": topic_label(topic_key)}
            for topic_key in session.selected_topics
        ],
        "question_count": question_limit,
        "current_turn": (
            _turn_payload(current_turn) if current_turn is not None else None
        ),
        "answered_turns": [
            _turn_payload(turn, include_answer=True)
            for turn in turns
            if turn.answer is not None
        ],
        "llm_call_count": session.llm_call_count,
        "max_answer_chars": MAX_ANSWER_CHARS,
        "resumed": resumed,
        "duplicate": duplicate,
    }
    if session.status == "completed":
        state["result"] = _result_payload(session)
    return state


def ready_state():
    return {
        "enabled": True,
        "status": "ready",
        "history": [],
        "topics": public_topics(),
        "question_count": None,
        "question_limits": {
            "min": MIN_QUESTIONS,
            "max": MAX_QUESTIONS,
        },
        "max_answer_chars": MAX_ANSWER_CHARS,
    }


def used_code_completed_state(session):
    state = ready_state()
    state["notice"] = {
        "type": "info",
        "code": "access_code_completed",
        "message": (
            "Этот код уже был использован, собеседование по нему завершено. "
            "Результат можно посмотреть в истории попыток."
        ),
        "session_guid": session.guid,
    }
    return state


def used_code_aborted_state(session):
    state = ready_state()
    state["notice"] = {
        "type": "info",
        "code": "access_code_aborted",
        "message": (
            "Этот код уже был использован. Попытка была завершена досрочно "
            "и не сохраняется в истории."
        ),
        "session_guid": session.guid,
    }
    return state


def find_owned_session(user, session_guid):
    return (
        AiInterviewSession.query.join(AiInterviewAttempt)
        .filter(AiInterviewSession.guid == session_guid)
        .filter(AiInterviewAttempt.user_id == user.id)
        .first()
    )
