from types import SimpleNamespace

import pytest
from jsonschema import ValidationError

from ai_interview import access, engine, planner, rubric, state
from ai_interview.catalog import public_topics
from ai_interview.errors import InterviewError
from ai_interview.models import AiInterviewAccessCode
from ai_interview.providers import (
    EVALUATION_SCHEMA,
    MAIN_ANSWER_SCHEMA,
    JsonCompletion,
    OPENROUTER_MODEL,
    ProviderError,
    get_provider,
    validate_payload,
)
from ai_interview.question_bank import questions_for_topic
from miminet_admin import AiInterviewSettingView


def make_turn(flow_type="main", position=1, pair_position=1, answer=None):
    turn = SimpleNamespace(
        id=position,
        position=position,
        topic_key="ethernet_l2",
        focus={
            "flow_type": flow_type,
            "pair_position": pair_position,
            "topic_position": planner.topic_position_for_pair(pair_position),
            "topic_pair_position": planner.topic_pair_position(pair_position),
            "source_question_id": "l2-4",
            "reference_answer": "Кадр отбрасывается.",
            "difficulty": "advanced" if flow_type == "followup" else "mechanism",
        },
        question="Что произойдёт с кадром с неверной контрольной суммой?",
        feedback="",
        answer=answer,
        analysis={"answer_score": 1, "critical_error": False},
    )
    session = SimpleNamespace(
        id=9,
        guid="session-guid",
        status="active",
        created_on=access.now_utc(),
        selected_topics=["ethernet_l2"],
        turns=[turn],
        final_result=None,
    )
    turn.session = session
    session.access_code = None
    return turn


def evaluation_payload(final_result=None, **extra):
    return {
        "feedback": "Короткий фидбек",
        "covered_concepts": ["основной тезис"],
        "missed_concepts": [],
        "misconceptions": [],
        "answer_score": 3,
        "critical_error": False,
        "final_result": final_result,
        **extra,
    }


def final_result_payload():
    return {
        "grade": 5,
        "verdict": "Хорошо",
        "strengths": ["Ethernet"],
        "gaps": [],
        "recommendations": [],
    }


def make_provider(mocker, payload):
    return SimpleNamespace(
        complete_json=mocker.Mock(return_value=JsonCompletion(payload, 1))
    )


def test_question_bank_covers_every_topic():
    assert all(len(questions_for_topic(topic["key"])) >= 2 for topic in public_topics())


def test_topic_schedule_follows_catalog_order():
    topics = [topic["key"] for topic in public_topics()]

    assert planner.build_topic_schedule(list(reversed(topics))) == topics
    assert planner.pair_count_for_topics(topics[:3]) == 6


def test_choose_main_question_excludes_already_used_question():
    questions = questions_for_topic("transport_and_icmp")
    expected_question = questions[-1]

    question, _ = planner.choose_main_question(
        "transport_and_icmp",
        2,
        excluded_ids={item["id"] for item in questions[:-1]},
    )

    assert question["id"] == expected_question["id"]


@pytest.mark.parametrize(
    ("schema", "missing_field"),
    [
        (MAIN_ANSWER_SCHEMA, "followup_question"),
        (EVALUATION_SCHEMA, "covered_concepts"),
    ],
)
def test_llm_payload_schema_requires_fields(schema, missing_field):
    payload = evaluation_payload(
        followup_question="Почему кадр нельзя передать дальше?",
        followup_reference_answer="Проверка FCS не пройдена.",
    )
    del payload[missing_field]

    with pytest.raises(ValidationError):
        validate_payload(payload, schema)


def test_grade_normalization_caps_critical_error():
    turns = [
        {"answer_score": 3, "critical_error": False},
        {"answer_score": 3, "critical_error": True},
    ]

    assert rubric.normalize_grade(turns, candidate_grade=5) == 3


def test_start_creates_bank_question_without_llm_completion(mocker):
    access_code = AiInterviewAccessCode(id=11)
    provider = SimpleNamespace(name="mock")
    mocker.patch("ai_interview.engine.find_valid_access_code", return_value=access_code)
    mocker.patch("ai_interview.engine._session_for_access_code", return_value=None)
    mocker.patch("ai_interview.engine._latest_incomplete_session", return_value=None)
    mocker.patch("ai_interview.engine.get_provider", return_value=provider)
    mocker.patch("ai_interview.engine.prune_interview_history")
    mocker.patch("ai_interview.state.get_interview_history", return_value=[])
    add = mocker.patch("ai_interview.engine.db.session.add")
    mocker.patch("ai_interview.engine.db.session.commit")

    state = engine.start_interview(SimpleNamespace(id=17), ["ethernet_l2"], "code")

    assert state["status"] == "active"
    assert state["current_turn"]["flow_type"] == "main"
    assert any(
        getattr(item, "question", None)
        for item in [call.args[0] for call in add.call_args_list]
    )


def test_main_answer_creates_followup_with_one_llm_call(mocker):
    turn = make_turn()
    provider = make_provider(
        mocker,
        evaluation_payload(
            followup_question="Почему повреждённый кадр нельзя передать дальше?",
            followup_reference_answer="Проверка FCS не пройдена.",
        ),
    )
    add = mocker.patch("ai_interview.engine.db.session.add")
    followup = SimpleNamespace()
    mocker.patch("ai_interview.engine.AiInterviewTurn", return_value=followup)

    completion, _ = engine._submit_main_answer(
        turn.session, turn, provider, "Его отбросят."
    )

    assert completion.calls == 1
    assert add.call_args.args[0] is followup
    engine.AiInterviewTurn.assert_called_once()
    assert engine.AiInterviewTurn.call_args.kwargs["focus"]["flow_type"] == "followup"
    assert engine.AiInterviewTurn.call_args.kwargs["position"] == 2


def test_last_followup_finalizes_session(mocker):
    turn = make_turn(flow_type="followup", position=4, pair_position=2)
    provider = make_provider(mocker, evaluation_payload(final_result_payload()))

    engine._submit_followup_answer(turn.session, turn, provider, "FCS не совпадает.")

    assert turn.session.status == "completed"
    assert turn.session.final_result["grade"] in {4, 5}


@pytest.mark.parametrize(
    ("pair_position", "expected_topic"),
    [
        (1, "ethernet_l2"),
        (2, "network_l3"),
    ],
)
def test_followup_creates_expected_next_main_question(
    mocker, pair_position, expected_topic
):
    turn = make_turn(
        flow_type="followup",
        position=pair_position * 2,
        pair_position=pair_position,
    )
    turn.session.selected_topics = ["ethernet_l2", "network_l3"]
    provider = make_provider(mocker, evaluation_payload())
    next_turn = SimpleNamespace()
    mocker.patch("ai_interview.engine._new_main_turn", return_value=next_turn)
    add = mocker.patch("ai_interview.engine.db.session.add")

    engine._submit_followup_answer(turn.session, turn, provider, "FCS не совпадает.")

    engine._new_main_turn.assert_called_once_with(
        turn.session, expected_topic, pair_position + 1
    )
    add.assert_called_once_with(next_turn)


@pytest.mark.parametrize(
    ("status", "existing_answer"),
    [
        ("active", "Коммутатор отбросит кадр."),
        ("completed", None),
    ],
)
def test_submit_answer_does_not_call_provider_for_finished_turn(
    mocker, status, existing_answer
):
    turn = make_turn(answer=existing_answer)
    turn.session.status = status
    if status == "completed":
        turn.session.final_result = {"grade": 4, "verdict": "Хорошо"}
    mocker.patch("ai_interview.engine._find_owned_turn", return_value=turn)
    mocker.patch("ai_interview.state.get_interview_history", return_value=[])
    provider_factory = mocker.patch("ai_interview.engine.get_provider")

    state = engine.submit_answer(SimpleNamespace(id=17), turn.id, "Повторный ответ")

    assert state["duplicate"] is True
    provider_factory.assert_not_called()


def test_openrouter_provider_uses_secret_file(monkeypatch, tmp_path):
    secret_file = tmp_path / "openrouter_api_key"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY_FILE", str(secret_file))

    provider = get_provider()

    assert provider.name == "openrouter"
    assert provider.model == OPENROUTER_MODEL
    assert provider.api_key == "file-secret"


def test_delete_access_code_detaches_sessions_before_delete(mocker):
    access_code = SimpleNamespace(id=11)
    query = mocker.patch("ai_interview.access.db.session.query")
    delete = mocker.patch("ai_interview.access.db.session.delete")

    access.delete_access_code(access_code)

    query.return_value.filter_by.assert_called_once_with(access_code_id=11)
    query.return_value.filter_by.return_value.update.assert_called_once_with(
        {"access_code_id": None},
        synchronize_session=False,
    )
    delete.assert_called_once_with(access_code)


def test_used_access_code_does_not_create_session_or_call_provider(mocker):
    access_code = AiInterviewAccessCode(id=11, is_used=True)
    mocker.patch("ai_interview.engine.find_valid_access_code", return_value=access_code)
    mocker.patch("ai_interview.engine._session_for_access_code", return_value=None)
    mocker.patch("ai_interview.state.get_interview_history", return_value=[])
    provider_factory = mocker.patch("ai_interview.engine.get_provider")

    result = engine.start_interview(SimpleNamespace(id=17), ["ethernet_l2"], "code")

    assert result["notice"]["code"] == "access_code_used"
    provider_factory.assert_not_called()


@pytest.mark.parametrize(
    ("statuses", "deleted_ids"),
    [
        (["completed"] * 12, [10, 11]),
        (["completed"] * 10 + ["active"], []),
    ],
)
def test_fifo_history_prunes_only_old_completed_sessions(mocker, statuses, deleted_ids):
    sessions = [
        SimpleNamespace(id=index, status=status)
        for index, status in enumerate(statuses)
    ]
    query = mocker.Mock()
    mocker.patch(
        "ai_interview.state.AiInterviewSession",
        SimpleNamespace(query=query, created_on=mocker.Mock(), id=mocker.Mock()),
    )
    query.filter_by.return_value.order_by.return_value.all.return_value = sessions
    delete = mocker.patch("ai_interview.state.db.session.delete")

    state.prune_interview_history(user_id=17)

    assert [call.args[0].id for call in delete.call_args_list] == deleted_ids


def test_admin_provider_status_escapes_external_message():
    label = AiInterviewSettingView._status_label(
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
    )

    assert "<script>" not in label
    assert "<img" not in label
    assert "&lt;script&gt;" in label
    assert "&lt;img" in label


def test_answer_longer_than_limit_is_rejected():
    with pytest.raises(InterviewError, match="1000"):
        engine.validate_answer("x" * 1001)


@pytest.mark.parametrize(
    ("flow_type", "pair_position", "final_result", "message"),
    [
        ("main", 1, final_result_payload(), "premature"),
        ("followup", 1, final_result_payload(), "premature"),
        ("followup", 2, None, "did not finalize"),
    ],
)
def test_invalid_llm_finalization_is_rejected(
    mocker, flow_type, pair_position, final_result, message
):
    turn = make_turn(
        flow_type=flow_type,
        position=pair_position * 2 if flow_type == "followup" else 1,
        pair_position=pair_position,
    )
    provider = make_provider(mocker, evaluation_payload(final_result))
    submit = (
        engine._submit_main_answer
        if flow_type == "main"
        else engine._submit_followup_answer
    )

    with pytest.raises(ProviderError, match=message):
        submit(turn.session, turn, provider, "FCS не совпадает.")
