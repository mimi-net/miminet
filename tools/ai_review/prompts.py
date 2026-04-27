import datetime as dt
import os
import pathlib
import textwrap
from typing import Any
from zoneinfo import ZoneInfo

from tools.ai_review.config import RuntimeConfig
from tools.ai_review.config import Scope
from tools.ai_review.paths import is_allowed_by_scope
from tools.ai_review.paths import posix_relative


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


def build_initial_messages(
    repo_root: pathlib.Path,
    config: RuntimeConfig,
    recent_activity: dict[str, Any],
) -> list[dict[str, str]]:
    top_level = gather_top_level(repo_root, config.scope)

    recent_commit_lines = [
        f"- {commit['date']} {commit['sha']}: {commit['subject']}"
        for commit in recent_activity["commits"]
    ] or ["- No commits found in the configured review window."]

    recent_file_lines = [
        f"- {path}"
        for path in recent_activity["files"]
        if is_allowed_by_scope(path, config.scope)
    ] or ["- No changed files found in the configured review window."]

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
        - Start from recent activity, then inspect adjacent high-risk files if needed.
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
        Review window: last {config.review_window_days} days
        Since: {recent_activity["since"]}
        Analysis date: {analysis_date}

        Top-level scope:
        {"\n".join(f"- {entry}" for entry in top_level[:40])}

        Recent commits:
        {"\n".join(recent_commit_lines)}

        Recently changed files:
        {"\n".join(recent_file_lines)}

        Available tools:
        - list_dir(path=".", recursive=false, limit=200)
        - read_file(path, start_line=1, max_lines=200)
        - search_text(pattern, path=".", file_glob="*", case_sensitive=false,
          regex=false, limit=80)

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
