import datetime as dt
import pathlib
import subprocess
from typing import Any

from tools.warden.config import Scope
from tools.warden.exceptions import ReviewError
from tools.warden.paths import is_allowed_by_scope
from tools.warden.process_env import safe_subprocess_env


def gather_recent_activity(
    repo_root: pathlib.Path, days: int, scope: Scope
) -> dict[str, Any]:
    since = (
        (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).date().isoformat()
    )
    cmd = [
        "git",
        "log",
        f"--since={since}",
        "--date=short",
        "--pretty=format:%h%x09%ad%x09%s",
        "--name-only",
        "--",
        ".",
    ]

    try:
        completed = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
            env=safe_subprocess_env(),
            check=False,
        )
    except FileNotFoundError as exc:
        raise ReviewError("git is required to gather recent changes") from exc

    commits: list[dict[str, Any]] = []
    files: list[str] = []
    current: dict[str, Any] | None = None

    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t", 2)
        if len(parts) == 3:
            current = {
                "sha": parts[0],
                "date": parts[1],
                "subject": parts[2],
                "files": [],
            }
        elif current is not None:
            if not is_allowed_by_scope(line, scope):
                continue
            current["files"].append(line)
            if line not in files:
                files.append(line)
            if current not in commits:
                commits.append(current)

    return {
        "since": since,
        "commits": commits[:20],
        "files": files[:80],
    }
