#!/usr/bin/env python3
"""Migrate avatar images to hash-based nested directories.

Supports phased migration:
1) move files from old flat directory to new bucket layout
2) update DB avatar_uri from "file.jpg" to "a/b/file.jpg"
3) rerun safely (idempotent)
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

User = None
_db = None


def get_app():
    from app import app  # noqa: E402

    return app


def ensure_db_models_loaded():
    global User, _db

    if User is not None and _db is not None:
        return

    from miminet_model import User as loaded_user, db as loaded_db  # noqa: E402

    User = loaded_user
    _db = loaded_db


DEFAULT_AVATAR_ROOT = SRC_DIR / "static" / "avatar"
SYSTEM_AVATARS = {"empty.jpg"}


def get_bucket_prefix(file_name: str) -> tuple[str, str]:
    stem = Path(file_name).stem.lower()
    if len(stem) >= 2 and stem[0].isalnum() and stem[1].isalnum():
        return stem[0], stem[1]

    digest = hashlib.sha1(file_name.encode("utf-8")).hexdigest()
    return digest[0], digest[1]


def build_target_rel(file_name: str) -> str:
    file_name = Path(file_name).name
    a, b = get_bucket_prefix(file_name)
    return f"{a}/{b}/{file_name}"


def is_bucketized_avatar_uri(avatar_uri: str) -> bool:
    parts = avatar_uri.split("/")
    if len(parts) != 3:
        return False

    first, second, file_name = parts
    if len(first) != 1 or len(second) != 1:
        return False

    if not first.isalnum() or not second.isalnum():
        return False

    if not file_name:
        return False

    return avatar_uri == build_target_rel(file_name)


def is_legacy_flat_avatar_uri(avatar_uri: str) -> bool:
    return Path(avatar_uri).name == avatar_uri and avatar_uri not in {"", ".", ".."}


def iter_flat_files(source_root: Path):
    for entry in source_root.iterdir():
        if entry.is_file():
            yield entry


def migrate_files(source_root: Path, avatar_root: Path, dry_run: bool) -> tuple[int, int, int]:
    moved = 0
    skipped = 0
    errors = 0

    for entry in iter_flat_files(source_root):
        file_name = entry.name

        if file_name in SYSTEM_AVATARS:
            skipped += 1
            continue

        target_rel = build_target_rel(file_name)
        target_abs = avatar_root / target_rel

        if target_abs.exists():
            print(f"[SKIP_EXISTS] target exists: {target_rel}")
            skipped += 1
            continue

        print(f"[MOVE] {entry} -> {target_abs}")

        if dry_run:
            moved += 1
            continue

        try:
            target_abs.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(entry), str(target_abs))
            moved += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"[ERROR] move failed for {entry}: {exc}")

    return moved, skipped, errors


def migrate_db(batch_size: int, dry_run: bool) -> tuple[int, int]:
    ensure_db_models_loaded()

    updated = 0
    skipped = 0

    query = User.query.with_entities(User.id, User.avatar_uri)

    try:
        for user_id, avatar_uri in query.yield_per(batch_size):
            if not avatar_uri or avatar_uri in SYSTEM_AVATARS:
                skipped += 1
                continue

            if is_bucketized_avatar_uri(avatar_uri):
                skipped += 1
                continue

            if not is_legacy_flat_avatar_uri(avatar_uri):
                print(f"[SKIP] unsupported avatar_uri format for user_id={user_id}: {avatar_uri}")
                skipped += 1
                continue

            new_avatar_uri = build_target_rel(avatar_uri)
            print(f"[DB] user_id={user_id}: {avatar_uri} -> {new_avatar_uri}")
            updated += 1

            if dry_run:
                continue

            User.query.filter(User.id == user_id).update(
                {"avatar_uri": new_avatar_uri}, synchronize_session=False
            )

            if updated % batch_size == 0:
                _db.session.commit()

        if not dry_run:
            _db.session.commit()
    except Exception:
        if not dry_run:
            _db.session.rollback()
        raise

    return updated, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate avatar images to hash buckets")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without changing files/DB")
    parser.add_argument("--batch-size", type=int, default=1000, help="DB commit batch size")
    parser.add_argument(
        "--avatar-root",
        type=Path,
        default=DEFAULT_AVATAR_ROOT,
        help="Target avatar root where files should end up",
    )
    parser.add_argument(
        "--legacy-root",
        type=Path,
        default=None,
        help="Optional source dir with old flat files. Defaults to --avatar-root",
    )
    parser.add_argument("--only-files", action="store_true", help="Migrate files only")
    parser.add_argument("--only-db", action="store_true", help="Migrate DB only")
    args = parser.parse_args()

    if args.only_files and args.only_db:
        parser.error("Use only one of --only-files or --only-db")

    if args.batch_size <= 0:
        parser.error("--batch-size must be > 0")

    return args


def main() -> int:
    args = parse_args()

    avatar_root: Path = args.avatar_root
    legacy_root: Path = args.legacy_root or avatar_root

    if not avatar_root.exists():
        print(f"[ERROR] Avatar root does not exist: {avatar_root}")
        return 1

    if not args.only_db and not legacy_root.exists():
        print(f"[ERROR] Legacy root does not exist: {legacy_root}")
        return 1

    file_moved = file_skipped = file_errors = 0
    db_updated = db_skipped = 0

    run_files = not args.only_db
    run_db = not args.only_files

    if run_files:
        file_moved, file_skipped, file_errors = migrate_files(
            source_root=legacy_root,
            avatar_root=avatar_root,
            dry_run=args.dry_run,
        )

    if run_db:
        try:
            app = get_app()
        except ModuleNotFoundError as exc:
            print(f"[WARN] Cannot run DB migration without app dependencies: {exc}")
            print("[WARN] DB step skipped. Install app dependencies (for example: flask) to enable --only-db/update mode")
        else:
            with app.app_context():
                db_updated, db_skipped = migrate_db(
                    batch_size=args.batch_size,
                    dry_run=args.dry_run,
                )

    print("\n=== Migration summary ===")
    if run_files:
        file_action = "files to move" if args.dry_run else "files moved"
        print(f"{file_action}: {file_moved}")
        print(f"files skipped: {file_skipped}")
        print(f"file errors: {file_errors}")
    if run_db:
        db_action = "db rows to update" if args.dry_run else "db updated"
        print(f"{db_action}: {db_updated}")
        print(f"db skipped: {db_skipped}")

    return 0 if file_errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())