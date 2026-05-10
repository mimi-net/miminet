import datetime as dt
import os
import pathlib
import random
import textwrap
from typing import Any
from zoneinfo import ZoneInfo

from tools.warden.config import RuntimeConfig
from tools.warden.config import Scope
from tools.warden.paths import is_allowed_by_scope
from tools.warden.paths import is_probably_binary
from tools.warden.paths import posix_relative


def render_focus(focus: tuple[str, ...]) -> str:
    if not focus:
        return (
            "- Find defects, regressions, fragile areas, security issues, "
            "and missing tests."
        )
    return "\n".join(f"- {item}" for item in focus)


def gather_top_level(repo_root: pathlib.Path, scope: Scope) -> list[str]:
    entries: list[str] = []
    for entry in sorted(repo_root.iterdir()):
        relative = posix_relative(entry, repo_root)
        if not is_allowed_by_scope(relative, scope):
            continue
        suffix = "/" if entry.is_dir() else ""
        entries.append(relative + suffix)
    return entries


def pick_baseline_files(
    repo_root: pathlib.Path,
    config: RuntimeConfig,
    sample_size: int | None = None,
) -> list[str]:
    candidates: list[str] = []

    for entry in sorted(repo_root.rglob("*")):
        if not entry.is_file():
            continue

        relative = posix_relative(entry, repo_root)
        if not is_allowed_by_scope(relative, config.scope):
            continue
        if entry.stat().st_size > config.limits.file_bytes:
            continue
        if is_probably_binary(entry):
            continue

        candidates.append(relative)

    if not candidates:
        return []

    seed = (
        f"{repo_root.name}:"
        f"{os.environ.get('GITHUB_SHA', 'unknown')}:"
        f"{dt.date.today().isoformat()}"
    )
    rng = random.Random(seed)
    requested_size = (
        config.baseline_sample_size if sample_size is None else sample_size
    )
    count = min(requested_size, len(candidates))
    return rng.sample(candidates, count)


def render_file_changes(file_changes: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for item in file_changes:
        status = item["status"]
        path = item["path"]
        old_path = item.get("old_path")
        if old_path:
            lines.append(f"- {status} {old_path} -> {path}")
        else:
            lines.append(f"- {status} {path}")
    return lines


def render_patch_sections(patches: list[dict[str, Any]]) -> str:
    sections: list[str] = []

    for patch in patches:
        header = f"### {patch['status']} {patch['path']}"
        if patch.get("old_path"):
            header = f"{header} (from {patch['old_path']})"

        suffix = "\n[diff excerpt truncated]" if patch.get("truncated") else ""
        sections.append(
            f"{header}\n```diff\n{patch['diff']}{suffix}\n```"
        )

    return "\n\n".join(sections)


def build_initial_messages(
    repo_root: pathlib.Path,
    config: RuntimeConfig,
    review_context: dict[str, Any],
) -> list[dict[str, str]]:
    top_level = gather_top_level(repo_root, config.scope)
    review_mode = str(review_context["mode"])
    pull_request_mode = review_mode == "pull_request"
    baseline_scan_mode = review_mode == "repository" and not review_context["files"]
    baseline_files = review_context.get("baseline_files") or []
    auto_scope_paths = review_context.get("auto_scope_paths") or []

    recent_commit_lines = [
        f"- {commit['date']} {commit['sha']}: {commit['subject']}"
        for commit in review_context["commits"]
    ] or ["- No commits found in the current review context."]

    recent_file_lines = [f"- {path}" for path in review_context["files"]] or [
        "- No scoped files found in the current review context."
    ]
    file_change_lines = render_file_changes(review_context.get("file_changes") or [])
    patch_sections = render_patch_sections(review_context.get("patches") or [])

    repo_name = os.environ.get("GITHUB_REPOSITORY", repo_root.name)
    sha = os.environ.get("GITHUB_SHA", "unknown")
    ref_name = os.environ.get("GITHUB_REF_NAME", "unknown")
    analysis_date = dt.datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d:%m:%Y")

    system_prompt = textwrap.dedent(
        f"""
        You are an autonomous weekly code review agent for the repository `{repo_name}`.
        Your job is to inspect the codebase with the available tools and
        produce a maintainer-facing Markdown review.

        Review priorities:
        {render_focus(config.focus)}

        Operating rules:
        - Focus on concrete bugs, regressions, fragile logic, security issues,
          dependency risk, and missing tests.
        - If the review mode is pull request, analyze all changes introduced by
          the pull request, using the changed files and patch excerpts as the
          primary context.
        - In pull request review mode, use `read_file` to inspect the full
          current version of changed files whenever the patch excerpt is not
          enough to judge correctness.
        - In repository review mode, start from recent activity, then inspect
          adjacent high-risk files if needed.
        - If there are no recently changed files in the allowed scope during
          repository review mode, switch to baseline repository scan mode and
          inspect the existing code without relying on file modification recency.
        - In baseline repository scan mode, start by exploring one or more
          allowed directories with `list_dir`, then inspect concrete files with
          `search_text` and `read_file` before forming conclusions.
        - Use tools selectively. Avoid re-reading the same content unless necessary.
        - Prefer `search_text` before reading many files.
        - Shell commands are not available.
        - When you have enough evidence, return `final_report`.

        Final report requirements:
        - Write the report in Russian Markdown.
        - Report only concrete bugs, vulnerabilities, and performance problems.
        - Do not create separate findings for generic advice or style issues.
        - Each confirmed problem must be a separate finding block.
        - Assign exactly one tag to each finding:
          `Alert` for high-impact or exploitable problems,
          `Warning` for medium-impact problems,
          `Notice` for low-impact but actionable problems.
        - Use this exact finding structure:

          ### [Alert|Warning|Notice] <Название>
          Анализ был проведён DD:MM:YYYY.

          #### Краткое резюме
          ...

          #### Где обнаружено
          ...

          #### Что именно обнаружено
          ...

          #### Почему это может быть проблемой
          ...

          #### Как проверить
          ...

          #### Возможное направление исправления
          ...

          #### Дополнительный контекст
          ...

        - Replace DD:MM:YYYY with the provided Analysis date exactly.
        - If there are no material findings, say explicitly that no concrete
          bugs, vulnerabilities, or performance problems were found.
        """
    ).strip()

    user_prompt = textwrap.dedent(
        f"""
        Repository root: {repo_root}
        Current ref: {ref_name}
        Current SHA: {sha}
        Analysis date: {analysis_date}

        {"Review window: last "
         f"{config.review_window_days} days\nSince: {review_context['since']}"
         if review_mode == "repository" else
         "Pull request number: "
         f"{review_context.get('number') or 'unknown'}\n"
         "Pull request title: "
         f"{review_context.get('title') or 'unknown'}\n"
         "Pull request URL: "
         f"{review_context.get('url') or 'unknown'}\n"
         "Base ref: "
         f"{review_context.get('base_ref') or 'unknown'}\n"
         "Base SHA: "
         f"{review_context.get('base_sha') or 'unknown'}\n"
         "Head ref: "
         f"{review_context.get('head_ref') or 'unknown'}\n"
         "Head SHA: "
         f"{review_context.get('head_sha') or 'unknown'}\n"
         "Merge base: "
         f"{review_context.get('merge_base') or 'unknown'}"}

        Top-level scope:
        {"\n".join(f"- {entry}" for entry in top_level[:40])}

        Review mode:
        {"- Pull request review. Analyze the delta introduced by the pull request,"
         " then inspect the full file content or adjacent code when the diff"
         " excerpt is not enough." if pull_request_mode else
         "- Baseline repository scan. Ignore modification dates and inspect the "
         "allowed scope for existing bugs, vulnerabilities, and performance "
         "problems." if baseline_scan_mode else
         "- Recent-change-focused repository review. Start from the files changed "
         "within the review window, then inspect adjacent high-risk code if needed."}

        {"Baseline seed files:\n" + "\n".join(f"- {path}" for path in baseline_files)
         if baseline_scan_mode and baseline_files else ""}

        {"Pull request files automatically added to runtime scope:\n"
         + "\n".join(f"- {path}" for path in auto_scope_paths)
         if pull_request_mode and auto_scope_paths else ""}

        {"Pull request commits:" if pull_request_mode else "Recent commits:"}
        {"\n".join(recent_commit_lines)}

        {"Pull request changed files:" if pull_request_mode else "Recently changed files:"}
        {"\n".join(recent_file_lines)}

        {"Changed file statuses:\n" + "\n".join(file_change_lines)
         if pull_request_mode and file_change_lines else ""}

        {"Patch excerpts:\n" + patch_sections
         if pull_request_mode and patch_sections else ""}

        Available tools:
        - list_dir(path=".", recursive=false, limit=200)
        - read_file(path, start_line=1, max_lines=200)
        - search_text(pattern, path=".", file_glob="*", case_sensitive=false,
          regex=false, limit=80)

        Tool call examples:
        - {{"action":"tool_call","tool_name":"list_dir","arguments":{{"path":"back","recursive":false,"limit":50}}}}
        - {{"action":"tool_call","tool_name":"read_file","arguments":{{"path":"front/src/app.py","start_line":1,"max_lines":120}}}}
        - {{"action":"tool_call","tool_name":"search_text","arguments":{{"pattern":"TODO","path":"back","file_glob":"*.py","case_sensitive":false,"regex":false,"limit":20}}}}
        - Do not add extra keys like `tool` inside `arguments`.

        Output protocol:
        - Return a JSON object matching the provided schema.
        - Use tool_call JSON while investigating.
        - Use final_report JSON when the review is complete.
        """
    ).strip()

    return [
        {"role": "system", "text": system_prompt},
        {"role": "user", "text": user_prompt},
    ]
