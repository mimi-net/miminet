import datetime as dt
import pathlib
import subprocess
from typing import Any
from zoneinfo import ZoneInfo

from tools.warden.config import Scope
from tools.warden.exceptions import ReviewError
from tools.warden.paths import is_allowed_by_scope
from tools.warden.process_env import safe_subprocess_env


def run_git(
    repo_root: pathlib.Path,
    args: list[str],
    timeout: int = 15,
) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]

    try:
        completed = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_subprocess_env(),
            check=False,
        )
    except FileNotFoundError as exc:
        raise ReviewError("git is required to gather review context") from exc

    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise ReviewError(f"git command failed ({' '.join(cmd)}): {details}")

    return completed


def parse_scoped_commit_log(
    stdout: str, scope: Scope | None
) -> tuple[list[dict[str, Any]], list[str]]:
    commits: list[dict[str, Any]] = []
    files: list[str] = []
    current: dict[str, Any] | None = None

    for raw_line in stdout.splitlines():
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
            continue

        if current is None:
            continue

        if scope is not None and not is_allowed_by_scope(line, scope):
            continue

        current["files"].append(line)
        if line not in files:
            files.append(line)
        if current not in commits:
            commits.append(current)

    return commits, files


def parse_scoped_name_status(
    stdout: str, scope: Scope | None
) -> tuple[list[dict[str, str]], list[str]]:
    file_changes: list[dict[str, str]] = []
    files: list[str] = []

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        status = parts[0]
        if status.startswith(("R", "C")) and len(parts) >= 3:
            old_path = parts[1]
            path = parts[2]
            if scope is not None and not (
                is_allowed_by_scope(path, scope) or is_allowed_by_scope(old_path, scope)
            ):
                continue
            file_changes.append(
                {
                    "status": status,
                    "path": path,
                    "old_path": old_path,
                }
            )
        else:
            path = parts[1]
            if scope is not None and not is_allowed_by_scope(path, scope):
                continue
            file_changes.append(
                {
                    "status": status,
                    "path": path,
                }
            )

        if path not in files:
            files.append(path)

    return file_changes, files


def collect_patch_excerpt(
    repo_root: pathlib.Path,
    range_spec: str,
    file_change: dict[str, str],
    line_limit: int,
) -> dict[str, Any]:
    diff_text = ""
    path_candidates = [file_change["path"]]

    old_path = file_change.get("old_path")
    if old_path and old_path not in path_candidates:
        path_candidates.append(old_path)

    for path in path_candidates:
        completed = run_git(
            repo_root,
            ["diff", "--no-color", "--unified=12", range_spec, "--", path],
            timeout=30,
        )
        if completed.stdout.strip():
            diff_text = completed.stdout
            break

    lines = diff_text.splitlines()
    truncated = len(lines) > line_limit
    excerpt = "\n".join(lines[:line_limit]) if lines else "No textual diff available."

    patch = {
        "status": file_change["status"],
        "path": file_change["path"],
        "diff": excerpt,
        "truncated": truncated,
    }
    if old_path:
        patch["old_path"] = old_path
    return patch


def gather_recent_activity(
    repo_root: pathlib.Path, days: int, scope: Scope
) -> dict[str, Any]:
    since = (
        (dt.datetime.now(ZoneInfo("Europe/Moscow")) - dt.timedelta(days=days))
        .date()
        .isoformat()
    )
    completed = run_git(
        repo_root,
        [
            "log",
            f"--since={since}",
            "--date=short",
            "--pretty=format:%h%x09%ad%x09%s",
            "--name-only",
            "--",
            ".",
        ],
    )
    commits, files = parse_scoped_commit_log(completed.stdout, scope)

    return {
        "mode": "repository",
        "since": since,
        "commits": commits[:20],
        "files": files[:80],
    }


def gather_pull_request_activity(
    repo_root: pathlib.Path,
    scope: Scope | None,
    base_ref: str | None,
    base_sha: str | None,
    head_sha: str | None,
    patch_line_limit: int,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_rev = base_sha or base_ref
    if not base_rev:
        raise ReviewError(
            "pull request review requires a base ref or base sha"
        )

    head_rev = head_sha or "HEAD"
    merge_base = run_git(
        repo_root,
        ["merge-base", base_rev, head_rev],
    ).stdout.strip()
    range_spec = f"{merge_base}..{head_rev}"

    commits_output = run_git(
        repo_root,
        [
            "log",
            "--date=short",
            "--pretty=format:%h%x09%ad%x09%s",
            "--name-only",
            range_spec,
            "--",
            ".",
        ],
        timeout=30,
    )
    commits, _ = parse_scoped_commit_log(commits_output.stdout, scope)

    file_changes_output = run_git(
        repo_root,
        ["diff", "--name-status", range_spec, "--", "."],
        timeout=30,
    )
    file_changes, files = parse_scoped_name_status(file_changes_output.stdout, scope)
    patches = [
        collect_patch_excerpt(repo_root, range_spec, file_change, patch_line_limit)
        for file_change in file_changes[:80]
    ]

    metadata = metadata or {}
    return {
        "mode": "pull_request",
        "number": metadata.get("number"),
        "title": metadata.get("title"),
        "url": metadata.get("url"),
        "base_ref": base_ref,
        "base_sha": base_sha,
        "head_ref": metadata.get("head_ref"),
        "head_sha": head_rev,
        "merge_base": merge_base,
        "commits": commits[:20],
        "files": files[:80],
        "file_changes": file_changes[:80],
        "patches": patches,
    }
