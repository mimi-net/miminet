from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import migrate_avatar_files as script


def test_build_target_rel():
    assert script.build_target_rel("ab123.jpg") == "a/b/ab123.jpg"


def test_is_bucketized_avatar_uri_requires_matching_prefix():
    assert script.is_bucketized_avatar_uri("a/b/ab123.jpg") is True
    assert script.is_bucketized_avatar_uri("x/y/ab123.jpg") is False


def test_migrate_files_moves_into_bucket(tmp_path):
    root = tmp_path / "avatar"
    root.mkdir()
    (root / "ab123.jpg").write_bytes(b"1")
    (root / "empty.jpg").write_bytes(b"sys")

    moved, skipped, errors = script.migrate_files(root, root, dry_run=False)

    assert (moved, skipped, errors) == (1, 1, 0)
    assert (root / "a" / "b" / "ab123.jpg").exists()
    assert not (root / "ab123.jpg").exists()


def test_migrate_db_updates_only_legacy_flat(mocker):
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
                    (1, "ab123.jpg"),
                    (2, "a/b/already.jpg"),
                    (3, "legacy/path.jpg"),
                    (4, "empty.jpg"),
                ]
            )

        def filter(self, expr):
            self._id = expr.right.value
            return self

        def update(self, payload, synchronize_session=False):
            self.updated.append((self._id, payload["avatar_uri"]))

    query = Query()
    user = type("User", (), {"id": Col(), "avatar_uri": Col(), "query": query})
    session = mocker.Mock()

    mocker.patch.object(script, "User", user)
    mocker.patch.object(script, "_db", type("Db", (), {"session": session})())

    updated, skipped = script.migrate_db(batch_size=100, dry_run=False)

    assert (updated, skipped) == (1, 3)
    assert query.updated == [(1, "a/b/ab123.jpg")]
    session.commit.assert_called_once()


def test_migrate_db_rolls_back_on_error(mocker):
    class Col:
        def __eq__(self, value):
            return type("Expr", (), {"right": type("R", (), {"value": value})()})()

    class Query:
        def with_entities(self, *_):
            return self

        def yield_per(self, _):
            return iter([(1, "ab123.jpg")])

        def filter(self, _):
            return self

        def update(self, payload, synchronize_session=False):
            raise RuntimeError("boom")

    user = type("User", (), {"id": Col(), "avatar_uri": Col(), "query": Query()})
    session = mocker.Mock()

    mocker.patch.object(script, "User", user)
    mocker.patch.object(script, "_db", type("Db", (), {"session": session})())

    with pytest.raises(RuntimeError):
        script.migrate_db(batch_size=100, dry_run=False)

    session.rollback.assert_called_once()


def test_parse_args_rejects_non_positive_batch_size(mocker):
    mocker.patch.object(sys, "argv", ["migrate_avatar_images.py", "--batch-size", "0"])

    with pytest.raises(SystemExit):
        script.parse_args()


def test_main_dry_run_skips_db_if_app_deps_missing(tmp_path, mocker):
    root = tmp_path / "avatar"
    root.mkdir()
    (root / "ab123.jpg").write_bytes(b"1")

    mocker.patch.object(sys, "argv", [
        "migrate_avatar_images.py",
        "--dry-run",
        "--avatar-root",
        str(root),
    ])
    mocker.patch.object(script, "get_app", side_effect=ModuleNotFoundError("flask"))

    assert script.main() == 0


def test_main_non_dry_run_skips_db_if_app_deps_missing(tmp_path, mocker):
    root = tmp_path / "avatar"
    root.mkdir()
    (root / "ab123.jpg").write_bytes(b"1")

    mocker.patch.object(sys, "argv", [
        "migrate_avatar_images.py",
        "--avatar-root",
        str(root),
        "--only-db",
    ])
    mocker.patch.object(script, "get_app", side_effect=ModuleNotFoundError("flask"))

    assert script.main() == 0