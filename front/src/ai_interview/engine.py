from types import SimpleNamespace

from ai_interview.access import (
    cleanup_expired_access_codes,
    find_valid_access_code,
    get_global_setting,
    resolve_llm_proxy_url,
)
from ai_interview.catalog import validate_topic_keys
from ai_interview.debug_service import emit_llm_debug, generate_question, validate_answer
from ai_interview.errors import InterviewConflict, InterviewError, InterviewNotFound
from ai_interview.models import AiInterviewAttempt, AiInterviewSession, AiInterviewTurn
from ai_interview.planner import (
    build_focus,
    build_topic_schedule,
    choose_next_seed,
    question_limit_for_topics,
)
from ai_interview.prompts import SYSTEM_PROMPT, evaluation_prompt
from ai_interview.providers import EVALUATION_SCHEMA, ProviderError, evaluation_temperature, get_provider
from ai_interview.rag import retrieve_context
from ai_interview.rubric import normalize_analysis, normalize_final_result
from ai_interview.state import (
    _attempt_for_access_code,
    _last_session,
    _latest_completed_session,
    _latest_incomplete_session,
    _result_payload,
    _with_history,
    find_owned_session,
    ready_state,
    serialize_session,
    used_code_aborted_state,
    used_code_completed_state,
)
from miminet_model import db
from sqlalchemy import func


def get_interview_state(user):
    cleanup_expired_access_codes()
    session = _latest_incomplete_session(user)
    if session is None:
        return _with_history(user, ready_state())

    return _with_history(user, serialize_session(session, resumed=True))


def start_interview(user, requested_topics, access_code=None):
    setting = get_global_setting()
    access_code = find_valid_access_code(access_code)

    existing_attempt = _attempt_for_access_code(user, access_code)
    if existing_attempt is not None:
        session = _last_session(existing_attempt)
        if session is not None:
            if session.status == "completed":
                return _with_history(user, used_code_completed_state(session))
            if session.status == "aborted":
                return _with_history(user, used_code_aborted_state(session))
            return _with_history(user, serialize_session(session, resumed=True))
        raise InterviewConflict("Попытка уже создана, но сессия не найдена.")

    session = _latest_incomplete_session(user)
    if session is not None:
        return _with_history(user, serialize_session(session, resumed=True))

    topics = validate_topic_keys(requested_topics)
    if not topics:
        raise InterviewError("Выберите хотя бы одну тему собеседования.")

    provider = get_provider(proxy_url=resolve_llm_proxy_url(setting))
    schedule = build_topic_schedule(topics)
    question_limit = question_limit_for_topics(topics)
    focus = build_focus(schedule[0], 1, plan_reason="coverage")
    question, context, calls = generate_question(
        provider, schedule[0], focus, question_limit=question_limit
    )
    focus["difficulty"] = question["difficulty"]

    attempt = AiInterviewAttempt(
        user_id=user.id,
        access_code=access_code,
        status="active",
    )
    db.session.add(attempt)

    session = AiInterviewSession(
        attempt=attempt,
        selected_topics=topics,
        topic_schedule=schedule,
        provider_name=provider.name,
        llm_call_count=calls,
        status="active",
    )
    turn = AiInterviewTurn(
        session=session,
        position=1,
        topic_key=schedule[0],
        focus=focus,
        question=question["question"],
        expected_concepts=question["expected_concepts"],
        generation_rag=context.provenance(),
    )
    db.session.add(session)
    db.session.add(turn)
    db.session.commit()
    return _with_history(user, serialize_session(session))


def _planning_session_with_answer(session, turn, answer, analysis):
    planning_turns = []
    for item in session.turns:
        if item is turn:
            planning_turns.append(
                SimpleNamespace(
                    position=turn.position,
                    topic_key=turn.topic_key,
                    focus=turn.focus,
                    answer=answer,
                    analysis=analysis,
                )
            )
        else:
            planning_turns.append(item)
    return SimpleNamespace(
        selected_topics=session.selected_topics,
        topic_schedule=session.topic_schedule,
        turns=planning_turns,
    )


def _find_owned_turn(user, turn_id):
    return (
        AiInterviewTurn.query.join(AiInterviewSession)
        .join(AiInterviewAttempt)
        .filter(AiInterviewTurn.id == turn_id)
        .filter(AiInterviewAttempt.user_id == user.id)
        .with_for_update()
        .first()
    )


def _current_turn(session):
    return next((turn for turn in session.turns if turn.answer is None), None)


def submit_answer(user, turn_id, answer):
    setting = get_global_setting()

    answer = validate_answer(answer)
    turn = _find_owned_turn(user, turn_id)
    if turn is None:
        raise InterviewNotFound("Вопрос собеседования не найден.")

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
        provider = get_provider(proxy_url=resolve_llm_proxy_url(setting))
    except ProviderError:
        session.status = "failed-recoverable"
        db.session.commit()
        raise
    current_context = retrieve_context(
        [turn.topic_key],
        " ".join([turn.question, answer, " ".join(turn.expected_concepts or [])]),
    )
    next_seed = None
    next_context = None
    question_limit = question_limit_for_topics(session.selected_topics)
    prompt = evaluation_prompt(
        turn,
        answer,
        current_context,
        question_limit,
        is_final=turn.position >= question_limit,
    )
    temperature = evaluation_temperature()
    try:
        completion = provider.complete_json(
            SYSTEM_PROMPT,
            prompt,
            temperature,
            EVALUATION_SCHEMA,
        )
    except ProviderError as error:
        session.status = "failed-recoverable"
        session.llm_call_count += getattr(error, "calls", 0)
        db.session.commit()
        raise
    payload = completion.payload
    try:
        if turn.position < question_limit:
            if payload["final_result"] is not None:
                raise ProviderError("LLM returned premature final result")
        elif payload["final_result"] is None:
            raise ProviderError("LLM did not finalize the last turn")
    except ProviderError:
        session.status = "failed-recoverable"
        session.llm_call_count += completion.calls
        db.session.commit()
        raise

    analysis = normalize_analysis(payload, answer)
    next_seed = None
    next_question = None
    next_calls = 0
    if turn.position < question_limit:
        planning_session = _planning_session_with_answer(
            session, turn, answer, analysis
        )
        next_seed = choose_next_seed(planning_session, turn.position + 1)
        next_topic = next_seed["topic_key"]
        next_focus = next_seed["focus"]
        try:
            next_question, next_context, next_calls = generate_question(
                provider,
                next_topic,
                next_focus,
                question_limit=question_limit,
            )
        except ProviderError as error:
            session.status = "failed-recoverable"
            session.llm_call_count += completion.calls + getattr(error, "calls", 0)
            db.session.commit()
            raise
        if not next_question.get("expected_concepts"):
            next_question["expected_concepts"] = next_focus["concepts"]
        next_focus["difficulty"] = next_question["difficulty"]

    turn.answer = answer
    turn.answered_on = func.now()
    turn.feedback = payload["feedback"]
    turn.answer_summary = payload["answer_summary"]
    turn.analysis = analysis
    turn.evaluation_rag = current_context.provenance()
    session.llm_call_count += completion.calls + next_calls
    session.status = "active"
    emit_llm_debug(
        "evaluation",
        {
            "provider": provider.name,
            "session_id": session.id,
            "turn_id": turn.id,
            "topic_key": turn.topic_key,
            "position": turn.position,
            "temperature": temperature,
            "focus": turn.focus,
            "system_prompt": SYSTEM_PROMPT,
            "prompt": prompt,
            "response": payload,
            "analysis": turn.analysis,
            "current_difficulty": (turn.focus or {}).get("difficulty"),
            "next_difficulty": (
                next_seed["focus"].get("difficulty")
                if next_seed is not None
                else None
            ),
            "rag": {
                "current": current_context.provenance(),
                "next": next_context.provenance() if next_context is not None else None,
            },
        },
    )

    if turn.position < question_limit:
        next_focus = next_seed["focus"]
        emit_llm_debug(
            "difficulty_adaptation",
            {
                "session_id": session.id,
                "turn_id": turn.id,
                "from_position": turn.position,
                "to_position": turn.position + 1,
                "answer_score": turn.analysis["answer_score"],
                "critical_error": turn.analysis["critical_error"],
                "current_difficulty": (turn.focus or {}).get("difficulty"),
                "next_difficulty": next_focus["difficulty"],
                "missed_concepts": turn.analysis["missed_concepts"],
                "misconceptions": turn.analysis["misconceptions"],
                "next_focus": next_focus,
            },
        )
        db.session.add(
            AiInterviewTurn(
                session=session,
                position=turn.position + 1,
                topic_key=next_seed["topic_key"],
                focus=next_focus,
                question=next_question["question"],
                expected_concepts=next_question["expected_concepts"],
                generation_rag=next_context.provenance(),
            )
        )
    else:
        session.status = "completed"
        session.finished_at = func.now()
        session.attempt.status = "completed"
        session.final_result = normalize_final_result(
            session.turns, payload["final_result"]
        )
        emit_llm_debug(
            "finalization",
            {
                "session_id": session.id,
                "turn_id": turn.id,
                "position": turn.position,
                "answer_score": turn.analysis["answer_score"],
                "critical_error": turn.analysis["critical_error"],
                "final_result": session.final_result,
            },
        )

    db.session.commit()
    return _with_history(user, serialize_session(session))


def abort_interview(user, session_guid):
    session_guid = str(session_guid or "").strip()
    if not session_guid:
        raise InterviewError("Сессия собеседования не указана.")

    session = _latest_incomplete_session(user)
    if session is None or session.guid != session_guid:
        raise InterviewNotFound("Сессия собеседования не найдена.")

    session.status = "aborted"
    session.finished_at = func.now()
    session.final_result = None
    session.attempt.status = "completed"
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
        raise InterviewNotFound("Сессия собеседования не найдена.")
    if session.status != "completed":
        raise InterviewConflict("Сессия еще не завершена.")
    return _result_payload(session)
