from types import SimpleNamespace

import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin
from jsonschema import ValidationError

from ai_interview import access, engine, planner, rubric, state
from ai_interview.catalog import public_topics
from ai_interview.controller import ai_interview_routes
from ai_interview.models import AiInterviewAccessCode
from ai_interview.providers import (
    EVALUATION_SCHEMA,
    MAIN_ANSWER_SCHEMA,
    JsonCompletion,
    OPENROUTER_MODEL,
    ProviderNotConfigured,
    get_provider,
    read_env_secret,
    validate_payload,
)
from ai_interview.question_bank import load_question_bank, questions_for_topic
from miminet_model import db
from miminet_admin import AiInterviewSettingView


class TestUser(UserMixin):
    id = 17


@pytest.fixture
def api_client():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="ai-interview-test")
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def load_user(user_id):
        return TestUser() if user_id == "17" else None

    app.register_blueprint(ai_interview_routes)
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["_user_id"] = "17"
            session["_fresh"] = True
        yield client


def make_turn(flow_type="main", position=1, pair_position=1, answer=None):
    turn = SimpleNamespace(
        id=position,
        position=position,
        topic_key="ethernet_l2",
        focus={
            "flow_type": flow_type,
            "pair_position": pair_position,
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


def test_question_bank_is_normalized_and_covers_every_topic():
    questions = load_question_bank()
    ids = [question["id"] for question in questions]

    assert len(questions) >= 50
    assert len(ids) == len(set(ids))
    assert all(
        set(question) == {"id", "topic_key", "question", "reference_answer"}
        for question in questions
    )
    assert all(questions_for_topic(topic["key"]) for topic in public_topics())


def test_topic_schedule_follows_catalog_order():
    topics = [topic["key"] for topic in public_topics()]

    assert planner.build_topic_schedule(list(reversed(topics))) == topics
    assert planner.pair_count_for_topics(topics[:3]) == 3


def test_choose_main_question_uses_requested_topic():
    question, focus = planner.choose_main_question(
        "transport_and_icmp",
        2,
        rng=planner.choose_question.__globals__["random"].Random(3),
    )

    assert question["topic_key"] == "transport_and_icmp"
    assert focus["flow_type"] == "main"
    assert focus["pair_position"] == 2
    assert focus["reference_answer"] == question["reference_answer"]


def test_main_answer_schema_requires_followup():
    with pytest.raises(ValidationError):
        validate_payload(evaluation_payload(), MAIN_ANSWER_SCHEMA)


def test_evaluation_schema_does_not_fill_missing_fields():
    payload = evaluation_payload()
    del payload["covered_concepts"]

    with pytest.raises(ValidationError):
        validate_payload(payload, EVALUATION_SCHEMA)


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
    provider = SimpleNamespace(
        complete_json=mocker.Mock(
            return_value=JsonCompletion(
                evaluation_payload(
                    followup_question="Почему повреждённый кадр нельзя передать дальше?",
                    followup_reference_answer="Проверка FCS не пройдена.",
                ),
                1,
            )
        )
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
    turn = make_turn(flow_type="followup", position=2)
    provider = SimpleNamespace(
        complete_json=mocker.Mock(
            return_value=JsonCompletion(
                evaluation_payload(
                    {
                        "grade": 5,
                        "verdict": "Хорошо",
                        "strengths": ["Ethernet"],
                        "gaps": [],
                        "recommendations": [],
                    }
                ),
                1,
            )
        )
    )

    engine._submit_followup_answer(turn.session, turn, provider, "FCS не совпадает.")

    assert turn.session.status == "completed"
    assert turn.session.final_result["grade"] in {4, 5}


def test_nonfinal_followup_creates_main_question_for_next_topic(mocker):
    turn = make_turn(flow_type="followup", position=2)
    turn.session.selected_topics = ["ethernet_l2", "network_l3"]
    provider = SimpleNamespace(
        complete_json=mocker.Mock(return_value=JsonCompletion(evaluation_payload(), 1))
    )
    next_turn = SimpleNamespace()
    mocker.patch("ai_interview.engine._new_main_turn", return_value=next_turn)
    add = mocker.patch("ai_interview.engine.db.session.add")

    engine._submit_followup_answer(turn.session, turn, provider, "FCS не совпадает.")

    engine._new_main_turn.assert_called_once_with(turn.session, "network_l3", 2)
    add.assert_called_once_with(next_turn)


def test_duplicate_answer_returns_state_without_provider_call(mocker):
    turn = make_turn(answer="Коммутатор отбросит кадр.")
    mocker.patch("ai_interview.engine._find_owned_turn", return_value=turn)
    mocker.patch("ai_interview.state.get_interview_history", return_value=[])
    provider_factory = mocker.patch("ai_interview.engine.get_provider")

    state = engine.submit_answer(SimpleNamespace(id=17), turn.id, turn.answer)

    assert state["duplicate"] is True
    provider_factory.assert_not_called()


def test_completed_session_rejects_extra_answer_without_provider_call(mocker):
    turn = make_turn()
    turn.session.status = "completed"
    turn.session.final_result = {"grade": 4, "verdict": "Хорошо"}
    mocker.patch("ai_interview.engine._find_owned_turn", return_value=turn)
    mocker.patch("ai_interview.state.get_interview_history", return_value=[])
    provider_factory = mocker.patch("ai_interview.engine.get_provider")

    state = engine.submit_answer(SimpleNamespace(id=17), turn.id, "Повторный ответ")

    assert state["duplicate"] is True
    provider_factory.assert_not_called()


def test_openrouter_key_can_be_read_from_env_file(monkeypatch, tmp_path):
    secret_file = tmp_path / "openrouter_api_key"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY_FILE", str(secret_file))

    assert read_env_secret("OPENROUTER_API_KEY") == "file-secret"


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
    mocker.patch("ai_interview.access.db.session.delete")

    access.delete_access_code(access_code)

    query.return_value.filter_by.assert_called_once_with(access_code_id=11)
    query.return_value.filter_by.return_value.update.assert_called_once_with(
        {"access_code_id": None},
        synchronize_session=False,
    )
    db.session.delete.assert_called_once_with(access_code)


def test_used_access_code_does_not_create_session_or_call_provider(mocker):
    access_code = AiInterviewAccessCode(id=11, is_used=True)
    mocker.patch("ai_interview.engine.find_valid_access_code", return_value=access_code)
    mocker.patch("ai_interview.engine._session_for_access_code", return_value=None)
    mocker.patch("ai_interview.state.get_interview_history", return_value=[])
    provider_factory = mocker.patch("ai_interview.engine.get_provider")

    result = engine.start_interview(SimpleNamespace(id=17), ["ethernet_l2"], "code")

    assert result["notice"]["code"] == "access_code_used"
    provider_factory.assert_not_called()


def test_fifo_history_deletes_sessions_after_tenth(mocker):
    sessions = [SimpleNamespace(id=index, status="completed") for index in range(12)]
    query = mocker.Mock()
    mocker.patch(
        "ai_interview.state.AiInterviewSession",
        SimpleNamespace(query=query, created_on=mocker.Mock(), id=mocker.Mock()),
    )
    query.filter_by.return_value.order_by.return_value.all.return_value = sessions
    delete = mocker.patch("ai_interview.state.db.session.delete")

    state.prune_interview_history(user_id=17)

    assert [call.args[0].id for call in delete.call_args_list] == [10, 11]


def test_fifo_history_keeps_incomplete_session(mocker):
    sessions = [SimpleNamespace(id=index, status="completed") for index in range(10)]
    sessions.append(SimpleNamespace(id=10, status="active"))
    query = mocker.Mock()
    mocker.patch(
        "ai_interview.state.AiInterviewSession",
        SimpleNamespace(query=query, created_on=mocker.Mock(), id=mocker.Mock()),
    )
    query.filter_by.return_value.order_by.return_value.all.return_value = sessions
    delete = mocker.patch("ai_interview.state.db.session.delete")

    state.prune_interview_history(user_id=17)

    delete.assert_not_called()


def test_admin_provider_status_escapes_external_message():
    label = AiInterviewSettingView._status_label(
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
    )

    assert "<script>" not in label
    assert "<img" not in label
    assert "&lt;script&gt;" in label
    assert "&lt;img" in label


def test_start_api_reports_missing_provider(api_client, mocker):
    mocker.patch(
        "ai_interview.controller.start_interview",
        side_effect=ProviderNotConfigured("provider missing"),
    )

    response = api_client.post(
        "/ai-testing/api/start",
        json={"topics": ["ethernet_l2"], "access_code": "code"},
    )

    assert response.status_code == 503
