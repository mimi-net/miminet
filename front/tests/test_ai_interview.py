from types import SimpleNamespace

import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin
from jsonschema import ValidationError

from ai_interview import access, engine, planner, rubric
from ai_interview.catalog import public_topics
from ai_interview.controller import ai_interview_routes
from ai_interview.models import AiInterviewAccessCode, AiInterviewAttempt
from ai_interview.providers import (
    GENERATION_SCHEMA,
    JsonCompletion,
    ProviderNotConfigured,
    ProxyConfigError,
    get_provider,
    normalize_proxy_url,
    read_env_secret,
    validate_payload,
)
from ai_interview.rag import retrieve_context
from miminet_model import db


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


def make_turn(position=1, answer=None, status="active"):
    turn = SimpleNamespace(
        id=position,
        position=position,
        topic_key="ethernet_l2",
        focus={
            "section_id": "ethernet_frame",
            "section_label": "Структура Ethernet-кадра",
            "plan_reason": "coverage",
        },
        question="Что произойдет с Ethernet-кадром?",
        feedback="",
        answer=answer,
        answer_summary="",
        analysis={"answer_score": 1, "critical_error": False},
        expected_concepts=["frame"],
    )
    session = SimpleNamespace(
        guid="session-guid",
        status=status,
        created_on=access.now_utc(),
        selected_topics=["ethernet_l2"],
        topic_schedule=["ethernet_l2"],
        turns=[turn],
        llm_call_count=1,
        final_result=None,
    )
    attempt = SimpleNamespace(access_code=None)
    turn.session = session
    session.attempt = attempt
    return turn


def test_retrieval_is_topic_constrained_and_bounded():
    context = retrieve_context(
        ["advanced_networking"], "PMTUD large TCP traffic", max_chars=220
    )

    assert context.chunks
    assert all(chunk["topic"] == "advanced_networking" for chunk in context.chunks)
    assert len(context.text) <= 220
    assert "pmtud" in context.text.casefold()


def test_course_chunks_are_normalized_from_course_topic_names():
    context = retrieve_context(
        ["transport_and_icmp"], "ICMP ping Destination Unreachable"
    )

    assert context.chunks
    assert any(
        "icmp" in (chunk.get("source_topic") or "").casefold()
        for chunk in context.chunks
    )
    assert all(chunk["topic"] == "transport_and_icmp" for chunk in context.chunks)


def test_question_limit_scales_with_selected_topics():
    topics = [topic["key"] for topic in public_topics()]

    assert planner.question_limit_for_topics(topics[:1]) == 4
    assert planner.question_limit_for_topics(topics[:2]) == 5
    assert planner.question_limit_for_topics(topics[:3]) == 6
    assert planner.question_limit_for_topics(topics[:4]) == 7
    assert planner.question_limit_for_topics(topics[:5]) == 8


def test_dynamic_planner_covers_unseen_topics_first():
    first = make_turn(answer="Понимаю Ethernet кадр")
    session = first.session
    session.selected_topics = ["ethernet_l2", "network_l3", "transport_and_icmp"]
    session.topic_schedule = ["ethernet_l2", "network_l3", "transport_and_icmp"]

    seed = planner.choose_next_seed(session, 2, rng=planner.random.Random(3))

    assert seed["topic_key"] == "network_l3"
    assert seed["focus"]["plan_reason"] == "coverage"


def test_dynamic_planner_rescues_weak_topic_after_coverage():
    first = make_turn(position=1, answer="Не знаю.")
    first.analysis = {"answer_score": 0, "critical_error": False}
    second = make_turn(position=2, answer="IP нужен для адресации")
    second.topic_key = "network_l3"
    second.focus = {
        "section_id": "ip_addresses",
        "section_label": "IP-адреса",
        "plan_reason": "coverage",
    }
    second.analysis = {"answer_score": 3, "critical_error": False}
    session = first.session
    session.selected_topics = ["ethernet_l2", "network_l3"]
    session.topic_schedule = ["ethernet_l2", "network_l3"]
    session.turns = [first, second]
    first.session = session
    second.session = session

    seed = planner.choose_next_seed(session, 3, rng=planner.random.Random(5))

    assert seed["topic_key"] == "ethernet_l2"
    assert seed["focus"]["plan_reason"] == "rescue"
    assert seed["focus"]["section_id"] != "ethernet_frame"


def test_late_coverage_question_stays_moderate_for_new_topic():
    focus = planner.build_focus(
        "network_l3",
        4,
        rng=planner.random.Random(11),
        plan_reason="coverage",
    )

    assert focus["target_difficulty"] == "mechanism"
    assert focus["question_type"] in {"mechanism", "compare"}
    assert focus["min_reasoning_steps"] == 3


def test_generation_payload_validation_rejects_missing_question():
    with pytest.raises(ValidationError):
        validate_payload(
            {"expected_concepts": ["ARP"], "difficulty": "basic"},
            GENERATION_SCHEMA,
        )


def test_generation_payload_accepts_reasoning_rubric():
    payload = validate_payload(
        {
            "question": "Почему пакет не попадет в соседнюю подсеть без шлюза?",
            "expected_concepts": ["маска подсети", "шлюз"],
            "expected_reasoning": [
                "хост определяет, что адрес назначения вне своей подсети",
                "для чужой подсети нужен маршрут или шлюз",
            ],
            "common_wrong_answers": ["пакет просто не доставится"],
            "difficulty": "practice",
        },
        GENERATION_SCHEMA,
    )

    assert payload["expected_reasoning"][0].startswith("хост определяет")


def test_grade_normalization_caps_critical_error():
    turns = [
        {"answer_score": 3, "critical_error": False},
        {"answer_score": 3, "critical_error": False},
        {"answer_score": 3, "critical_error": True},
        {"answer_score": 3, "critical_error": False},
    ]

    assert rubric.normalize_grade(turns, candidate_grade=5) == 3


def test_grade_five_requires_strong_reasoning_turn():
    turns = [
        {
            "answer_score": 3,
            "critical_error": False,
            "focus": {"difficulty": "basic"},
        },
        {
            "answer_score": 3,
            "critical_error": False,
            "focus": {"difficulty": "mechanism"},
        },
        {
            "answer_score": 3,
            "critical_error": False,
            "focus": {"difficulty": "mechanism"},
        },
        {
            "answer_score": 3,
            "critical_error": False,
            "focus": {"difficulty": "basic"},
        },
    ]

    assert rubric.normalize_grade(turns, candidate_grade=5) == 4

    turns[-1]["focus"] = {"difficulty": "advanced", "question_type": "packet_trace"}

    assert rubric.normalize_grade(turns, candidate_grade=5) == 5


def test_llm_proxy_env_fallback_is_used(monkeypatch):
    setting = SimpleNamespace(
        llm_proxy_enabled=False,
        llm_proxy_url=None,
        llm_proxy_env_fallback_enabled=True,
    )
    monkeypatch.setenv("AI_INTERVIEW_LLM_SOCKS_PROXY", "socks5h://proxy.local:1080")

    assert access.resolve_llm_proxy_url(setting) == "socks5h://proxy.local:1080"


def test_proxy_url_rejects_unsupported_scheme():
    with pytest.raises(ProxyConfigError):
        normalize_proxy_url("ftp://proxy.local:21")


def test_openrouter_key_can_be_read_from_env_file(monkeypatch, tmp_path):
    secret_file = tmp_path / "openrouter_api_key"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY_FILE", str(secret_file))

    assert read_env_secret("OPENROUTER_API_KEY") == "file-secret"


def test_openrouter_env_value_takes_precedence_over_secret_file(monkeypatch, tmp_path):
    secret_file = tmp_path / "openrouter_api_key"
    secret_file.write_text("file-secret", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY_FILE", str(secret_file))

    assert read_env_secret("OPENROUTER_API_KEY") == "env-secret"


def test_openrouter_provider_uses_secret_file(monkeypatch, tmp_path):
    secret_file = tmp_path / "openrouter_api_key"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    monkeypatch.setenv("AI_INTERVIEW_PROVIDER", "openrouter")
    monkeypatch.setenv("AI_INTERVIEW_OPENROUTER_MODEL", "test-model")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY_FILE", str(secret_file))

    provider = get_provider()

    assert provider.name == "openrouter"
    assert provider.model == "test-model"
    assert provider.api_key == "file-secret"


def test_start_resumes_existing_attempt_before_provider_call(mocker):
    turn = make_turn()
    mocker.patch(
        "ai_interview.engine.get_global_setting",
        return_value=SimpleNamespace(),
    )
    mocker.patch(
        "ai_interview.engine.find_valid_access_code",
        return_value=SimpleNamespace(id=11),
    )
    mocker.patch(
        "ai_interview.engine._attempt_for_access_code",
        return_value=SimpleNamespace(status="active", sessions=[turn.session]),
    )
    mocker.patch(
        "ai_interview.engine._latest_incomplete_session", return_value=turn.session
    )
    mocker.patch("ai_interview.state.get_interview_history", return_value=[])
    provider_factory = mocker.patch("ai_interview.engine.get_provider")

    state = engine.start_interview(SimpleNamespace(id=17), ["ethernet_l2"], "code")

    assert state["resumed"] is True
    assert state["history"] == []
    provider_factory.assert_not_called()


def test_duplicate_answer_returns_state_without_provider_call(mocker):
    turn = make_turn(answer="Коммутатор пересылает кадр.")
    mocker.patch(
        "ai_interview.engine.get_global_setting",
        return_value=SimpleNamespace(),
    )
    mocker.patch("ai_interview.engine._find_owned_turn", return_value=turn)
    mocker.patch("ai_interview.state.get_interview_history", return_value=[])
    provider_factory = mocker.patch("ai_interview.engine.get_provider")

    state = engine.submit_answer(SimpleNamespace(id=17), turn.id, turn.answer)

    assert state["duplicate"] is True
    assert state["history"] == []
    provider_factory.assert_not_called()


def test_completed_attempt_does_not_block_new_attempt(mocker):
    access_code = AiInterviewAccessCode(id=11)
    mocker.patch(
        "ai_interview.engine.get_global_setting",
        return_value=SimpleNamespace(
            llm_proxy_enabled=False,
            llm_proxy_url=None,
            llm_proxy_env_fallback_enabled=False,
        ),
    )
    mocker.patch(
        "ai_interview.engine.find_valid_access_code",
        return_value=access_code,
    )
    mocker.patch("ai_interview.engine._attempt_for_access_code", return_value=None)
    mocker.patch("ai_interview.engine._latest_incomplete_session", return_value=None)
    mocker.patch("ai_interview.state.get_interview_history", return_value=[])
    provider = SimpleNamespace(
        name="mock",
        complete_json=lambda *args, **kwargs: JsonCompletion(
            payload={
                "question": "Что делает ARP?",
                "expected_concepts": ["ARP"],
                "difficulty": "basic",
            },
            calls=1,
        ),
    )
    mocker.patch("ai_interview.engine.get_provider", return_value=provider)
    mocker.patch(
        "ai_interview.debug_service.retrieve_context",
        return_value=SimpleNamespace(
            text="ARP сопоставляет IP и MAC.",
            example_questions=[],
            provenance=lambda: {"chunks": []},
        ),
    )
    mocker.patch("ai_interview.engine.db.session.add")
    mocker.patch("ai_interview.engine.db.session.commit")

    state = engine.start_interview(SimpleNamespace(id=17), ["ethernet_l2"], "code")

    assert state["status"] == "active"
    assert state["resumed"] is False


def test_delete_access_code_detaches_attempts_before_delete(mocker):
    access_code = SimpleNamespace(id=11)
    session_query = mocker.Mock()
    update_query = mocker.Mock()
    query = mocker.patch("ai_interview.access.db.session.query")
    mocker.patch("ai_interview.access.db.session.delete")
    query.return_value = session_query
    session_query.filter_by.return_value = update_query

    access.delete_access_code(access_code)

    query.assert_called_once_with(AiInterviewAttempt)
    session_query.filter_by.assert_called_once_with(access_code_id=11)
    update_query.update.assert_called_once_with(
        {"access_code_id": None},
        synchronize_session=False,
    )
    db.session.delete.assert_called_once_with(access_code)


def test_state_api_returns_disabled_backend_state(api_client, mocker):
    mocker.patch(
        "ai_interview.controller.get_interview_state",
        return_value={"enabled": False, "status": "unavailable", "message": "closed"},
    )

    response = api_client.get("/ai-interview/api/state")

    assert response.status_code == 200
    assert response.get_json()["enabled"] is False


def test_start_api_reports_missing_provider(api_client, mocker):
    mocker.patch(
        "ai_interview.controller.start_interview",
        side_effect=ProviderNotConfigured("provider missing"),
    )

    response = api_client.post(
        "/ai-interview/api/start",
        json={"topics": ["ethernet_l2"], "access_code": "code"},
    )

    assert response.status_code == 503
    assert "provider missing" in response.get_json()["error"]


def test_start_requires_access_code_before_provider_call(mocker):
    mocker.patch(
        "ai_interview.engine.get_global_setting", return_value=SimpleNamespace()
    )
    provider_factory = mocker.patch("ai_interview.engine.get_provider")

    with pytest.raises(engine.InterviewError):
        engine.start_interview(SimpleNamespace(id=17), ["ethernet_l2"], "")

    provider_factory.assert_not_called()


def test_reusing_completed_access_code_returns_notice_without_opening_result(mocker):
    turn = make_turn(status="completed")
    turn.session.status = "completed"
    turn.session.final_result = {"grade": 4, "verdict": "OK"}
    access_code = SimpleNamespace(id=11)
    attempt = SimpleNamespace(status="completed", sessions=[turn.session])
    mocker.patch(
        "ai_interview.engine.get_global_setting", return_value=SimpleNamespace()
    )
    mocker.patch("ai_interview.engine.find_valid_access_code", return_value=access_code)
    mocker.patch("ai_interview.engine._attempt_for_access_code", return_value=attempt)
    mocker.patch("ai_interview.state.get_interview_history", return_value=[])
    provider_factory = mocker.patch("ai_interview.engine.get_provider")

    state = engine.start_interview(SimpleNamespace(id=17), [], "123456")

    assert state["status"] == "ready"
    assert state["notice"]["code"] == "access_code_completed"
    assert "истории попыток" in state["notice"]["message"]
    assert "result" not in state
    provider_factory.assert_not_called()


def test_result_api_can_return_session_by_guid(api_client, mocker):
    mocker.patch(
        "ai_interview.controller.get_interview_result_by_guid",
        return_value={"grade": 5, "questions": []},
    )

    response = api_client.get("/ai-interview/api/result?guid=session-guid")

    assert response.status_code == 200
    assert response.get_json()["grade"] == 5
