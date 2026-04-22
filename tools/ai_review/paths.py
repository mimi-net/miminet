import fnmatch
import pathlib

from tools.ai_review.config import Scope


def repo_root_from_script() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def posix_relative(path: pathlib.Path, root: pathlib.Path) -> str:
    relative = path.relative_to(root).as_posix()
    return relative or "."


def within_path(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        _ = path.relative_to(root)
        return True
    except ValueError:
        return False


def match_glob(relative_path: str, pattern: str) -> bool:
    if fnmatch.fnmatchcase(relative_path, pattern):
        return True

    relative_obj = pathlib.PurePosixPath(relative_path)
    return relative_obj.match(pattern)


def is_allowed_by_scope(relative_path: str, scope: Scope) -> bool:
    if relative_path == ".":
        return True

    if scope.include:
        included = any(
            relative_path == prefix
            or relative_path.startswith(f"{prefix.rstrip('/')}/")
            or prefix.startswith(f"{relative_path.rstrip('/')}/")
            for prefix in scope.include
        )
        if not included:
            return False

    return not any(match_glob(relative_path, pattern) for pattern in scope.exclude)


def is_probably_binary(path: pathlib.Path) -> bool:
    with path.open("rb") as handle:
        chunk = handle.read(4096)
    return b"\x00" in chunk


def sanitize_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return f"{text[:limit]}\n\n[truncated {omitted} chars]"
