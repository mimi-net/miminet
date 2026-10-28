"""HTTP-регрессии запуска эмуляции, настроек и удаления сетей на двух БД."""

from datetime import timedelta
import json

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError

from http_test_support import persisted_state as _persisted_state
from http_test_support import simulation_http as simulation_http
from miminet_model import Network, Simulate, SimulateLog, db


@pytest.mark.parametrize(
    "path",
    [
        "/run_simulation",
        "/check_simulation",
        "/delete_network",
        "/network/update_network_config",
    ],
)
@pytest.mark.parametrize(
    "token_kind, status", [("missing", 401), ("invalid", 422), ("expired", 401)]
)
def test_unauthorized_requests_have_no_database_or_queue_effects(
    simulation_http, path, token_kind, status
):
    """Отсутствующий, повреждённый и просроченный JWT не дают менять состояние."""
    before = _persisted_state()
    headers = {}
    if token_kind == "invalid":
        headers = {"Authorization": "Bearer broken-token"}
    elif token_kind == "expired":
        token = create_access_token(identity="1", expires_delta=timedelta(seconds=-1))
        headers = {"Authorization": f"Bearer {token}"}

    response = simulation_http.client.open(
        path, method="GET" if path == "/check_simulation" else "POST", headers=headers
    )

    assert response.status_code == status
    assert _persisted_state() == before
    simulation_http.send_task.assert_not_called()


@pytest.mark.parametrize("guid", [None, "", "missing-network", "other-network"])
def test_run_rejects_missing_or_foreign_network_without_side_effects(
    simulation_http, guid
):
    """Ошибка GUID и чужая сеть не удаляют прошлые результаты и не создают задачу."""
    before = _persisted_state()
    response = simulation_http.client.post(
        "/run_simulation",
        query_string={} if guid is None else {"guid": guid},
        headers=simulation_http.headers,
    )

    assert response.status_code == 400
    assert response.get_json()["simulation_id"] == -1
    assert _persisted_state() == before
    simulation_http.send_task.assert_not_called()


def test_run_replaces_only_owned_results_and_sends_matching_task(simulation_http):
    """Повторный запуск заменяет только свои результаты и связывает БД с задачей Celery."""
    response = simulation_http.client.post(
        "/run_simulation?guid=owner-network", headers=simulation_http.headers
    )

    assert response.status_code == 201
    simulation_id = response.get_json()["simulation_id"]
    db.session.remove()
    own = Simulate.query.filter_by(network_id=10).all()
    assert len(own) == 1
    assert own[0].id == simulation_id
    assert own[0].ready is False
    assert db.session.get(Simulate, 101) is None
    assert db.session.get(Simulate, 202).packets == "other-packets"
    log = SimulateLog.query.one()
    assert (log.author_id, log.network_guid) == (1, "owner-network")
    simulation_http.send_task.assert_called_once()
    args, kwargs = simulation_http.send_task.call_args
    assert args == ("tasks.mininet_worker", (db.session.get(Network, 10).network,))
    assert kwargs["task_id"] == own[0].task_guid
    assert kwargs["headers"] == {"network_task_name": "tasks.save_simulate_result"}


@pytest.mark.parametrize("path", ["/run_simulation", "/delete_network"])
def test_get_does_not_start_simulation_or_delete_network(simulation_http, path):
    """Обычный переход по ссылке не выполняет разрушительную операцию."""
    before = _persisted_state()
    response = simulation_http.client.get(
        path, query_string={"guid": "owner-network"}, headers=simulation_http.headers
    )
    assert response.status_code == (405 if path == "/run_simulation" else 302)
    if path == "/delete_network":
        assert response.headers["Location"] == "/home"
    assert _persisted_state() == before
    simulation_http.send_task.assert_not_called()


@pytest.mark.parametrize("simulation_id", [None, "", "0", "not-a-number", "999999"])
def test_poll_invalid_or_missing_simulation_returns_client_error(
    simulation_http, simulation_id
):
    """Некорректный идентификатор не вызывает 500 и не изменяет данные."""
    before = _persisted_state()
    query = {"network_guid": "owner-network"}
    if simulation_id is not None:
        query["simulation_id"] = simulation_id
    response = simulation_http.client.get(
        "/check_simulation", query_string=query, headers=simulation_http.headers
    )
    assert response.status_code == 400
    assert "packets" not in response.get_json()
    assert _persisted_state() == before


@pytest.mark.parametrize("guid", [None, ""])
def test_poll_requires_network_guid(simulation_http, guid):
    """Нельзя читать результаты без указания сети."""
    query = {"simulation_id": 101}
    if guid is not None:
        query["network_guid"] = guid
    response = simulation_http.client.get(
        "/check_simulation", query_string=query, headers=simulation_http.headers
    )
    assert response.status_code == 400
    assert "packets" not in response.get_json()


def test_pending_poll_does_not_return_packets(simulation_http):
    """Сохранённый промежуточный payload не выдаётся как готовый результат."""
    response = simulation_http.client.get(
        "/check_simulation?simulation_id=101&network_guid=owner-network",
        headers=simulation_http.headers,
    )
    assert response.status_code == 210
    assert "packets" not in response.get_json()


@pytest.mark.parametrize("with_captures", [False, True])
def test_ready_poll_returns_saved_packets_and_only_capture_files(
    simulation_http, tmp_path, monkeypatch, with_captures
):
    """Готовый результат сохраняет payload; подкаталоги не выдаются как pcap-файлы."""
    db.session.get(Simulate, 101).ready = True
    db.session.commit()
    monkeypatch.chdir(tmp_path)
    if with_captures:
        captures = tmp_path / "static/pcaps/owner-network"
        captures.mkdir(parents=True)
        (captures / "host_1.pcapng").write_bytes(b"test capture")
        (captures / "nested").mkdir()

    response = simulation_http.client.get(
        "/check_simulation?simulation_id=101&network_guid=owner-network",
        headers=simulation_http.headers,
    )
    assert response.status_code == 200
    assert response.get_json()["packets"] == "owner-packets"
    assert response.get_json()["pcaps"] == (["host_1"] if with_captures else [])


@pytest.mark.parametrize(
    "simulation_id, guid, status, packets",
    [
        (202, "other-network", 200, "other-packets"),
        (202, "owner-network", 200, "other-packets"),
        (101, "other-network", 210, None),
        (101, "../other-network", 210, None),
    ],
)
def test_poll_preserves_lookup_by_id_without_owner_or_network_binding(
    simulation_http, tmp_path, monkeypatch, simulation_id, guid, status, packets
):
    """По просьбе пользователя сохраняем исходный поиск результата только по ID."""
    before = _persisted_state()
    monkeypatch.chdir(tmp_path)
    response = simulation_http.client.get(
        "/check_simulation",
        query_string={"simulation_id": simulation_id, "network_guid": guid},
        headers=simulation_http.headers,
    )
    assert response.status_code == status
    if packets is None:
        assert "packets" not in response.get_json()
    else:
        assert response.get_json()["packets"] == packets
        assert response.get_json()["pcaps"] == []
    assert _persisted_state() == before
    simulation_http.send_task.assert_not_called()


@pytest.mark.parametrize("guid", [None, "", "missing-network", "other-network"])
def test_delete_missing_or_foreign_network_preserves_all_rows(simulation_http, guid):
    """Нельзя удалить чужую сеть, даже зная её GUID."""
    before = _persisted_state()
    response = simulation_http.client.post(
        "/delete_network",
        query_string={} if guid is None else {"guid": guid},
        headers=simulation_http.headers,
    )
    assert response.status_code == 302
    assert _persisted_state() == before


def test_delete_owned_network_removes_only_its_simulations(simulation_http):
    """Удаление своей сети убирает её результаты, не затрагивая другого владельца."""
    response = simulation_http.client.post(
        "/delete_network?guid=owner-network", headers=simulation_http.headers
    )
    assert response.status_code == 302
    db.session.remove()
    assert db.session.get(Network, 10) is None
    assert db.session.get(Simulate, 101) is None
    assert db.session.get(Network, 20) is not None
    assert db.session.get(Simulate, 202).packets == "other-packets"


@pytest.mark.parametrize("guid", [None, "", "missing-network", "other-network"])
def test_update_config_cannot_change_foreign_or_missing_network(simulation_http, guid):
    """Настройки чужой сети не изменяются даже при корректном JWT."""
    before = _persisted_state()
    response = simulation_http.client.post(
        "/network/update_network_config",
        query_string={} if guid is None else {"guid": guid},
        json={"network_title": "changed", "network_description": "changed"},
        headers=simulation_http.headers,
    )
    assert response.status_code == 400
    assert _persisted_state() == before


@pytest.mark.parametrize("zoom, expected_zoom", [(None, 2), (0, 2), (3.5, 3.5)])
def test_update_config_preserves_topology_results_and_other_users(
    simulation_http, zoom, expected_zoom
):
    """Настройка камеры и описания не должна сбрасывать топологию и результаты."""
    network = db.session.get(Network, 10)
    original = {
        "nodes": [{"data": {"id": "host-1"}}],
        "jobs": [{"job_id": 1}],
        "edges": [],
        "config": {"custom": "keep"},
    }
    network.network = json.dumps(original)
    db.session.commit()
    response = simulation_http.client.post(
        "/network/update_network_config?guid=owner-network",
        json={
            "network_title": "  Учебная сеть  ",
            "network_description": "  Описание  ",
            "zoom": zoom,
            "pan_x": -5,
            "pan_y": 100,
        },
        headers=simulation_http.headers,
    )
    assert response.status_code == 200
    db.session.remove()
    saved = db.session.get(Network, 10)
    assert (saved.title, saved.description) == ("Учебная сеть", "Описание")
    expected: dict[str, object] = dict(original)
    expected["config"] = {
        "custom": "keep",
        "zoom": expected_zoom,
        "pan_x": -5,
        "pan_y": 100,
    }
    assert json.loads(saved.network) == expected
    assert db.session.get(Network, 20).title == "Новая сеть"
    assert db.session.get(Simulate, 101).packets == "owner-packets"
    assert db.session.get(Simulate, 202).packets == "other-packets"
    simulation_http.send_task.assert_not_called()


@pytest.mark.parametrize(
    "payload", [{}, {"network_title": "  ", "network_description": ""}]
)
def test_empty_metadata_fields_preserve_existing_values(simulation_http, payload):
    """Пропущенные или пустые поля не стирают существующее название и описание."""
    network = db.session.get(Network, 10)
    network.title, network.description = "keep-title", "keep-description"
    db.session.commit()
    response = simulation_http.client.post(
        "/network/update_network_config?guid=owner-network",
        json=payload,
        headers=simulation_http.headers,
    )
    assert response.status_code == 200
    db.session.remove()
    saved = db.session.get(Network, 10)
    assert (saved.title, saved.description) == ("keep-title", "keep-description")


@pytest.mark.parametrize("payload", [None, [], "not-an-object"])
def test_config_rejects_non_object_json_without_changing_rows(simulation_http, payload):
    """Вместо 500 неверная структура JSON возвращает 400 без записи данных."""
    before = _persisted_state()
    response = simulation_http.client.post(
        "/network/update_network_config?guid=owner-network",
        data=json.dumps(payload),
        content_type="application/json",
        headers=simulation_http.headers,
    )
    assert response.status_code == 400
    assert _persisted_state() == before


@pytest.mark.parametrize(
    "field, value",
    [
        ("network_title", None),
        ("network_description", 42),
        ("zoom", "bad"),
        ("zoom", float("nan")),
        ("zoom", "inf"),
        ("zoom", -1),
        ("zoom", True),
        ("pan_x", {}),
        ("pan_y", []),
    ],
)
def test_config_rejects_invalid_values_atomically(simulation_http, field, value):
    """Ошибка одного поля не сохраняет даже корректное новое название сети."""
    before = _persisted_state()
    payload = {"network_title": "must-not-persist", "network_description": "valid"}
    payload[field] = value
    response = simulation_http.client.post(
        "/network/update_network_config?guid=owner-network",
        json=payload,
        headers=simulation_http.headers,
    )
    assert response.status_code == 400
    assert _persisted_state() == before


@pytest.mark.parametrize(
    "method, data, content_type, status",
    [
        ("GET", None, None, 400),
        ("POST", "broken-json", "application/json", 400),
        ("POST", "not-json", "text/plain", 415),
    ],
)
def test_invalid_config_request_preserves_database(
    simulation_http, method, data, content_type, status
):
    """Неверный метод, повреждённый JSON и неподходящий Content-Type не меняют БД."""
    before = _persisted_state()
    response = simulation_http.client.open(
        "/network/update_network_config?guid=owner-network",
        method=method,
        data=data,
        content_type=content_type,
        headers=simulation_http.headers,
    )
    assert response.status_code == status
    assert _persisted_state() == before


@pytest.mark.parametrize("operation", ["run", "delete"])
def test_failed_database_write_preserves_previous_results(simulation_http, operation):
    """Настоящая ошибка ограничения БД не должна уничтожить старые результаты."""
    if operation == "run":
        db.session.add(SimulateLog(id=303, author_id=1, network_guid="owner-network"))
        db.session.commit()

        def duplicate_log_id(_mapper, _connection, target):
            target.id = 303

        event.listen(SimulateLog, "before_insert", duplicate_log_id)
    else:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE deletion_blocker (id INTEGER PRIMARY KEY, "
                    "network_id BIGINT NOT NULL REFERENCES network(id))"
                )
            )
            connection.execute(text("INSERT INTO deletion_blocker VALUES (1, 10)"))
    before = _persisted_state()
    try:
        with pytest.raises(IntegrityError):
            simulation_http.client.post(
                "/run_simulation?guid=owner-network"
                if operation == "run"
                else "/delete_network?guid=owner-network",
                headers=simulation_http.headers,
            )
    finally:
        if operation == "run":
            event.remove(SimulateLog, "before_insert", duplicate_log_id)

    assert _persisted_state() == before
    simulation_http.send_task.assert_not_called()
