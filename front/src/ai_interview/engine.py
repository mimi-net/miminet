from ai_interview.access import (
    cleanup_expired_access_codes,
    find_valid_access_code,
)
from ai_interview.catalog import validate_topic_keys
from ai_interview.errors import InterviewConflict, InterviewError, InterviewNotFound
from ai_interview.models import AiInterviewSession, AiInterviewTurn
from ai_interview.planner import (
    build_followup_focus,
    build_topic_schedule,
    choose_main_question,
    pair_count_for_topics,
)
from ai_interview.prompts import (
    SYSTEM_PROMPT,
    followup_answer_prompt,
    main_answer_prompt,
)
from ai_interview.providers import (
    EVALUATION_SCHEMA,
    MAIN_ANSWER_SCHEMA,
    ProviderError,
    evaluation_temperature,
    get_provider,
)
from ai_interview.rubric import normalize_analysis, normalize_final_result
from ai_interview.state import (
    _latest_completed_session,
    _latest_incomplete_session,
    _result_payload,
    _session_for_access_code,
    _with_history,
    find_owned_session,
    MAX_ANSWER_CHARS,
    prune_interview_history,
    ready_state,
    serialize_session,
    used_code_aborted_state,
    used_code_completed_state,
    used_code_state,
)
from miminet_model import db
from sqlalchemy import func


def get_interview_state(user):
    cleanup_expired_access_codes()
    session = _latest_incomplete_session(user)
    if session is None:
        return _with_history(user, ready_state())
    return _with_history(user, serialize_session(session))


def _new_main_turn(session, topic_key, pair_position):
    question, focus = choose_main_question(topic_key, pair_position)
    return AiInterviewTurn(
        session=session,
        position=(pair_position - 1) * 2 + 1,
        topic_key=topic_key,
        focus=focus,
        question=question["question"],
    )


def start_interview(user, requested_topics, access_code=None):
    access_code = find_valid_access_code(access_code)

    existing_session = _session_for_access_code(user, access_code)
    if existing_session is not None:
        if existing_session.status == "completed":
            return _with_history(user, used_code_completed_state(existing_session))
        if existing_session.status == "aborted":
            return _with_history(user, used_code_aborted_state(existing_session))
        return _with_history(user, serialize_session(existing_session))
    if access_code.is_used:
        return _with_history(user, used_code_state())

    session = _latest_incomplete_session(user)
    if session is not None:
        return _with_history(user, serialize_session(session))

    topics = validate_topic_keys(requested_topics)
    if not topics:
        raise InterviewError("Выберите хотя бы одну тему AI-тестирования.")
    schedule = build_topic_schedule(topics)
    get_provider()

    session = AiInterviewSession(
        user_id=user.id,
        access_code=access_code,
        selected_topics=schedule,
        status="active",
    )
    access_code.is_used = True
    db.session.add(session)
    db.session.add(_new_main_turn(session, schedule[0], 1))
    prune_interview_history(user.id)
    db.session.commit()
    return _with_history(user, serialize_session(session))


def _find_owned_turn(user, turn_id):
    return (
        AiInterviewTurn.query.join(AiInterviewSession)
        .filter(AiInterviewTurn.id == turn_id)
        .filter(AiInterviewSession.user_id == user.id)
        .with_for_update()
        .first()
    )


def _current_turn(session):
    return next((turn for turn in session.turns if turn.answer is None), None)


def validate_answer(answer):
    answer = str(answer or "").strip()
    if not answer:
        raise InterviewError("Ответ не должен быть пустым.")
    if len(answer) > MAX_ANSWER_CHARS:
        raise InterviewError("Ответ не должен быть длиннее 1000 символов.")
    return answer


def _complete(provider, prompt, schema):
    return provider.complete_json(
        SYSTEM_PROMPT,
        prompt,
        evaluation_temperature(),
        schema,
    )


def _record_answer(turn, answer, payload):
    turn.answer = answer
    turn.answered_on = func.now()
    turn.feedback = payload["feedback"]
    turn.analysis = normalize_analysis(payload)


def _submit_main_answer(session, turn, provider, answer):
    prompt = main_answer_prompt(turn, answer)
    completion = _complete(provider, prompt, MAIN_ANSWER_SCHEMA)
    payload = completion.payload
    if payload["final_result"] is not None:
        raise ProviderError("LLM returned premature final result", completion.calls)

    _record_answer(turn, answer, payload)
    followup_focus = build_followup_focus(turn, payload["followup_reference_answer"])
    db.session.add(
        AiInterviewTurn(
            session=session,
            position=turn.position + 1,
            topic_key=turn.topic_key,
            focus=followup_focus,
            question=payload["followup_question"].strip(),
        )
    )
    return completion, prompt


def _submit_followup_answer(session, turn, provider, answer):
    pair_position = int(turn.focus["pair_position"])
    pair_count = pair_count_for_topics(session.selected_topics)
    is_final = pair_position >= pair_count
    prompt = followup_answer_prompt(turn, answer, is_final)
    completion = _complete(provider, prompt, EVALUATION_SCHEMA)
    payload = completion.payload

    if is_final and payload["final_result"] is None:
        raise ProviderError("LLM did not finalize the last turn", completion.calls)
    if not is_final and payload["final_result"] is not None:
        raise ProviderError("LLM returned premature final result", completion.calls)

    _record_answer(turn, answer, payload)
    if is_final:
        session.status = "completed"
        session.finished_at = func.now()
        session.final_result = normalize_final_result(
            session.turns, payload["final_result"]
        )
    else:
        topic_key = session.selected_topics[pair_position]
        db.session.add(_new_main_turn(session, topic_key, pair_position + 1))
    return completion, prompt


def submit_answer(user, turn_id, answer):
    answer = validate_answer(answer)
    turn = _find_owned_turn(user, turn_id)
    if turn is None:
        raise InterviewNotFound("Вопрос AI-тестирования не найден.")

    session = turn.session
    if session.status == "completed":
        return _with_history(user, serialize_session(session, duplicate=True))
    if session.status not in {"active", "failed-recoverable"}:
        raise InterviewConflict("Эта попытка уже завершена.")
    if turn.answer is not None:
        return _with_history(user, serialize_session(session, duplicate=True))
    if _current_turn(session) != turn:
        raise InterviewConflict("Этот вопрос сейчас не ожидает ответа.")

    try:
        provider = get_provider()
        if turn.focus["flow_type"] == "main":
            _submit_main_answer(session, turn, provider, answer)
        else:
            _submit_followup_answer(session, turn, provider, answer)
    except ProviderError:
        session.status = "failed-recoverable"
        db.session.commit()
        raise

    session.status = "active" if session.status != "completed" else session.status
    prune_interview_history(user.id)
    db.session.commit()
    return _with_history(user, serialize_session(session))


def abort_interview(user, session_guid):
    session_guid = str(session_guid or "").strip()
    if not session_guid:
        raise InterviewError("Сессия AI-тестирования не указана.")

    session = _latest_incomplete_session(user)
    if session is None or session.guid != session_guid:
        raise InterviewNotFound("Сессия AI-тестирования не найдена.")

    session.status = "aborted"
    session.finished_at = func.now()
    session.final_result = None
    prune_interview_history(user.id)
    db.session.commit()

    state = ready_state()
    state["notice"] = {
        "type": "info",
        "code": "attempt_aborted",
        "message": "Попытка завершена досрочно. Код считается использованным.",
    }
    return _with_history(user, state)


def get_interview_result(user):
    session = _latest_completed_session(user)
    if session is None:
        raise InterviewConflict("Сессия еще не завершена.")
    return _result_payload(session)


def get_interview_result_by_guid(user, session_guid):
    session = find_owned_session(user, session_guid)
    if session is None:
        raise InterviewNotFound("Сессия AI-тестирования не найдена.")
    if session.status != "completed":
        raise InterviewConflict("Сессия еще не завершена.")
    return _result_payload(session)
