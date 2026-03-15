from pathlib import Path
import sys
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import migrate_previews_files as script  # noqa: E402


def test_build_target_rel():
    assert script.build_target_rel("ab123.png") == "a/b/ab123.png"


def test_migrate_files_moves_into_bucket(tmp_path):
    root = tmp_path / "preview"
    root.mkdir()
    (root / "ab123.png").write_bytes(b"1")
    (root / "first_network.jpg").write_bytes(b"sys")

    moved, skipped, errors = script.migrate_files(root, root, dry_run=False)

    assert (moved, skipped, errors) == (1, 1, 0)
    assert (root / "a" / "b" / "ab123.png").exists()
    assert not (root / "ab123.png").exists()


def test_migrate_db_uses_strict_bucket_check_and_updates_only_flat(monkeypatch):
    class Col:
        def __eq__(self, value):
            return type("Expr", (), {"right": type("R", (), {"value": value})()})()

    class Query:
        def __init__(self):
            self.updated = []
            self._id = None

        def with_entities(self, *_):
            return self

        def yield_per(self, _):
            return iter(
                [
                    (1, "ab123.png"),
                    (2, "a/b/already.png"),
                    (3, "legacy/path.png"),
                ]
            )

        def filter(self, expr):
            self._id = expr.right.value
            return self

        def update(self, payload, synchronize_session=False):
            self.updated.append((self._id, payload["preview_uri"]))

    query = Query()
    network = type("Network", (), {"id": Col(), "preview_uri": Col(), "query": query})
    session = Mock()

    monkeypatch.setattr(script, "Network", network)
    monkeypatch.setattr(script, "db", type("Db", (), {"session": session})())

    updated, skipped = script.migrate_db(batch_size=100, dry_run=False)

    assert (updated, skipped) == (1, 2)
    assert query.updated == [(1, "a/b/ab123.png")]
    session.commit.assert_called_once()


def test_migrate_db_rolls_back_on_error(monkeypatch):
    class Col:
        def __eq__(self, value):
            return type("Expr", (), {"right": type("R", (), {"value": value})()})()

    class Query:
        def with_entities(self, *_):
            return self

        def yield_per(self, _):
            return iter([(1, "ab123.png")])

        def filter(self, _):
            return self

        def update(self, payload, synchronize_session=False):
            raise RuntimeError("boom")

    network = type("Network", (), {"id": Col(), "preview_uri": Col(), "query": Query()})
    session = Mock()

    monkeypatch.setattr(script, "Network", network)
    monkeypatch.setattr(script, "db", type("Db", (), {"session": session})())

    with pytest.raises(RuntimeError):
        script.migrate_db(batch_size=100, dry_run=False)

    session.rollback.assert_called_once()
