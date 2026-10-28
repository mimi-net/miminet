"""Регрессии сохранения и копирования сетей с настоящими JWT, БД и файлами."""

import copy
import json
from urllib.parse import parse_qs, urlparse
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from http_test_support import persisted_state
from http_test_support import simulation_http as simulation_http
import miminet_network
from miminet_model import Network, Simulate, db


EDIT_ROUTES = ["/post_network_nodes", "/post_nodes_edges", "/move_network_nodes"]


@pytest.fixture
def saved_topology(simulation_http):
    """Есть сохранённая топология, захват пакетов и прежний результат эмуляции."""
    topology = {
        "nodes": [
            {
                "data": {"id": "host-1"},
                "config": {"type": "host", "label": "host-1"},
                "position": {"x": 0, "y": 0},
                "interface": [],
            }
        ],
        "edges": [],
        "jobs": [],
        "pcap": ["old-capture"],
        "config": {"zoom": 2, "pan_x": 0, "pan_y": 0},
    }
    second_host = copy.deepcopy(topology["nodes"][0])
    second_host["data"] = {"id": "host-2"}
    second_host["config"] = {"type": "host", "label": "host-2"}
    second_host["position"] = {"x": 200, "y": 0}
    topology["nodes"].append(second_host)
    db.session.get(Network, 10).network = json.dumps(topology)
    db.session.commit()
    return topology


def _body(path, topology):
    """У старого и объединённого API разные форматы тела запроса."""
    return (
        [topology["nodes"], topology["edges"], topology["jobs"]]
        if path == "/post_nodes_edges"
        else topology["nodes"]
    )


@pytest.mark.parametrize("path", EDIT_ROUTES + ["/network/copy_network"])
def test_network_operations_require_authentication(simulation_http, path):
    """Без JWT нельзя ни сохранить, ни скопировать сеть."""
    before = persisted_state()
    response = simulation_http.client.post(
        path, query_string={"guid": "owner-network"}, json=[]
    )
    assert response.status_code == 401
    assert persisted_state() == before


@pytest.mark.parametrize("path", EDIT_ROUTES)
@pytest.mark.parametrize("guid", [None, "", "missing-network", "other-network"])
def test_edit_cannot_modify_foreign_or_missing_network(simulation_http, path, guid):
    """Неизвестный GUID и GUID другого владельца не меняют ни сеть, ни результаты."""
    before = persisted_state()
    response = simulation_http.client.post(
        path,
        query_string={} if guid is None else {"guid": guid},
        json=[],
        headers=simulation_http.headers,
    )
    assert response.status_code == 400
    assert persisted_state() == before


@pytest.mark.parametrize("path", EDIT_ROUTES)
def test_position_only_save_preserves_emulation(simulation_http, saved_topology, path):
    """Перемещение узла сохраняет результат, захваты и параметры камеры."""
    changed = copy.deepcopy(saved_topology)
    changed["nodes"][0]["position"] = {"x": -150, "y": 500}
    response = simulation_http.client.post(
        path,
        query_string={"guid": "owner-network"},
        json=_body(path, changed),
        headers=simulation_http.headers,
    )
    assert response.status_code == 201
    db.session.remove()
    assert json.loads(db.session.get(Network, 10).network) == changed
    assert db.session.get(Simulate, 101).packets == "owner-packets"
    assert db.session.get(Simulate, 202).packets == "other-packets"
    simulation_http.send_task.assert_not_called()


@pytest.mark.parametrize("path", ["/post_network_nodes", "/post_nodes_edges"])
def test_device_change_invalidates_only_owned_results(
    simulation_http, saved_topology, path
):
    """Изменение эмулируемого устройства сбрасывает только свой результат и pcap."""
    changed = copy.deepcopy(saved_topology)
    changed["nodes"][0]["config"]["default_gw"] = "10.0.0.1"
    response = simulation_http.client.post(
        path,
        query_string={"guid": "owner-network"},
        json=_body(path, changed),
        headers=simulation_http.headers,
    )
    assert response.status_code == 201
    db.session.remove()
    saved = json.loads(db.session.get(Network, 10).network)
    assert saved["nodes"] == changed["nodes"]
    assert saved["pcap"] == []
    assert db.session.get(Simulate, 101) is None
    assert db.session.get(Simulate, 202).packets == "other-packets"


@pytest.mark.parametrize("kind", ["job", "link"])
def test_job_or_link_change_invalidates_saved_emulation(
    simulation_http, saved_topology, kind
):
    """Изменение задания или связи тоже делает сохранённую эмуляцию устаревшей."""
    changed = copy.deepcopy(saved_topology)
    if kind == "job":
        changed["jobs"] = [
            {"id": "job-1", "job_id": 1, "host_id": "host-1", "arg_1": "10.0.0.2"}
        ]
    else:
        changed["edges"] = [
            {"data": {"id": "link-1", "source": "host-1", "target": "host-2"}}
        ]
    response = simulation_http.client.post(
        "/post_nodes_edges?guid=owner-network",
        json=_body("/post_nodes_edges", changed),
        headers=simulation_http.headers,
    )
    assert response.status_code == 201
    db.session.remove()
    assert db.session.get(Simulate, 101) is None
    saved = json.loads(db.session.get(Network, 10).network)
    assert saved["pcap"] == []
    if kind == "link":
        assert saved["edges"][0]["data"]["loss_percentage"] == 0
        assert saved["edges"][0]["data"]["duplicate_percentage"] == 0


@pytest.mark.parametrize(
    "path, payload",
    [
        ("/post_network_nodes", None),
        ("/post_network_nodes", {}),
        ("/post_network_nodes", [None]),
        ("/post_network_nodes", [{"config": None}]),
        ("/move_network_nodes", None),
        ("/move_network_nodes", {}),
        ("/post_nodes_edges", []),
        ("/post_nodes_edges", [[], []]),
        ("/post_nodes_edges", [[None], [], []]),
        ("/post_nodes_edges", [[], [None], []]),
        ("/post_nodes_edges", [[], [{"data": None}], []]),
        ("/post_nodes_edges", [[], [], [None]]),
    ],
)
def test_malformed_topology_is_rejected_before_any_write(
    simulation_http, saved_topology, path, payload
):
    """Повреждённая структура возвращает 400, не сохраняется и не удаляет результаты."""
    before = persisted_state()
    response = simulation_http.client.post(
        path,
        query_string={"guid": "owner-network"},
        data=json.dumps(payload),
        content_type="application/json",
        headers=simulation_http.headers,
    )
    assert response.status_code == 400
    assert persisted_state() == before


@pytest.mark.parametrize("path", ["/post_network_nodes", "/post_nodes_edges"])
def test_failed_topology_update_preserves_previous_results(
    simulation_http, saved_topology, path
):
    """Ошибка NOT NULL отменяет и топологию, и удаление прежней эмуляции."""
    changed = copy.deepcopy(saved_topology)
    changed["nodes"] = []

    def break_title(_mapper, _connection, target):
        target.title = None

    before = persisted_state()
    event.listen(Network, "before_update", break_title)
    try:
        with pytest.raises(IntegrityError):
            simulation_http.client.post(
                path,
                query_string={"guid": "owner-network"},
                json=_body(path, changed),
                headers=simulation_http.headers,
            )
    finally:
        event.remove(Network, "before_update", break_title)
    assert persisted_state() == before


@pytest.fixture
def preview_root(tmp_path, monkeypatch):
    """Копируем настоящие байты в каталог теста, не затрагивая файлы проекта."""
    root = tmp_path / "preview"
    root.mkdir()
    monkeypatch.setattr(miminet_network, "PREVIEW_IMAGES_ROOT", str(root))
    (root / "first_network.jpg").write_bytes(b"test-preview")
    return root


@pytest.mark.parametrize("path", ["/post_network_nodes", "/post_nodes_edges"])
def test_empty_topology_is_a_valid_edit(simulation_http, saved_topology, path):
    """Пустой список допустим: удаление всех узлов не должно ошибочно стать 400."""
    cleared = copy.deepcopy(saved_topology)
    cleared["nodes"] = []
    response = simulation_http.client.post(
        path,
        query_string={"guid": "owner-network"},
        json=_body(path, cleared),
        headers=simulation_http.headers,
    )
    assert response.status_code == 201
    db.session.remove()
    saved = json.loads(db.session.get(Network, 10).network)
    assert saved["nodes"] == []
    assert saved["pcap"] == []
    assert db.session.get(Simulate, 101) is None
    assert db.session.get(Simulate, 202) is not None


@pytest.mark.parametrize("guid", [None, "", "missing-network"])
def test_copy_missing_network_does_not_create_rows(simulation_http, preview_root, guid):
    """Пропущенный или неизвестный GUID не создаёт строки и изображения копии."""
    before = persisted_state()
    response = simulation_http.client.post(
        "/network/copy_network",
        query_string={} if guid is None else {"guid": guid},
        headers=simulation_http.headers,
    )
    assert response.status_code == 400
    assert persisted_state() == before
    assert sorted(path.name for path in preview_root.rglob("*") if path.is_file()) == [
        "first_network.jpg"
    ]


@pytest.mark.parametrize("source_guid", ["owner-network", "other-network"])
def test_copy_owned_or_shared_network_is_independent(
    simulation_http, preview_root, source_guid
):
    """Свою или общедоступную сеть можно скопировать без копирования её результатов."""
    source = Network.query.filter_by(guid=source_guid).one()
    source.share_mode = source_guid == "other-network"
    db.session.commit()
    original_document = source.network
    original_title = source.title
    response = simulation_http.client.post(
        "/network/copy_network",
        query_string={"guid": source_guid},
        headers=simulation_http.headers,
    )
    assert response.status_code == 200
    new_guid = parse_qs(urlparse(response.get_json()["new_url"]).query)["guid"][0]
    assert str(uuid.UUID(new_guid)) == new_guid
    assert new_guid != source_guid
    db.session.remove()
    copied = Network.query.filter_by(guid=new_guid).one()
    assert copied.author_id == 1
    assert copied.network == original_document
    assert copied.title == original_title + " - копия"
    assert Simulate.query.filter_by(network_id=copied.id).count() == 0
    assert (preview_root / copied.preview_uri).read_bytes() == b"test-preview"
    assert db.session.get(Simulate, 101).packets == "owner-packets"
    assert db.session.get(Simulate, 202).packets == "other-packets"


def test_copy_cannot_read_private_network(simulation_http, preview_root):
    """Знание GUID не даёт права скопировать чужую закрытую сеть."""
    db.session.get(Network, 20).share_mode = False
    db.session.commit()
    before = persisted_state()
    response = simulation_http.client.post(
        "/network/copy_network?guid=other-network", headers=simulation_http.headers
    )
    assert response.status_code == 400
    assert persisted_state() == before


def test_missing_preview_does_not_create_partial_copy(simulation_http, preview_root):
    """Если исходного изображения нет, в БД не остаётся неполная копия сети."""
    (preview_root / "first_network.jpg").unlink()
    before = persisted_state()
    response = simulation_http.client.post(
        "/network/copy_network?guid=owner-network", headers=simulation_http.headers
    )
    assert response.status_code == 400
    assert persisted_state() == before
