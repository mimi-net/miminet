import datetime as dt
import json
import os
import pathlib
import textwrap
from typing import Any
from zoneinfo import ZoneInfo

from tools.warden.config import with_force_include_paths
from tools.warden.config import RuntimeConfig
from tools.warden.exceptions import ReviewError
from tools.warden.model import build_model_uri
from tools.warden.prompts import build_initial_messages
from tools.warden.prompts import pick_baseline_files
from tools.warden.recent_activity import gather_pull_request_activity
from tools.warden.recent_activity import gather_recent_activity
from tools.warden.agent_tools import ReviewTools


REPOSITORY_TOOLS = {"list_dir", "read_file", "search_text"}
FINALIZATION_TOOLS = {"final_report", "end_review"}


def format_tool_result(
    tool_name: str, arguments: dict[str, Any], result: dict[str, Any]
) -> str:
    payload = {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result,
    }
    continuation = (
        "If there are more findings, submit another final_report. "
        "When every report has been submitted, call end_review."
        if tool_name == "final_report"
        else "Continue the review. Return another tool_call."
    )
    return (
        "Tool result:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        f"{continuation}"
    )


def combine_reports(reports: list[str]) -> str:
    return "\n\n---\n\n".join(report.strip() for report in reports if report.strip())


def collect_inspected_paths(transcript: list[dict[str, Any]]) -> list[str]:
    inspected_paths: list[str] = []

    for item in transcript:
        tool_result = item.get("tool_result") or {}
        if not tool_result.get("ok"):
            continue

        data = tool_result.get("data") or {}
        path = data.get("path")
        if isinstance(path, str) and path not in inspected_paths:
            inspected_paths.append(path)

    return inspected_paths


def build_finalization_phase_prompt(
    review_context: dict[str, Any], transcript: list[dict[str, Any]]
) -> str:
    inspected_paths = collect_inspected_paths(transcript)
    baseline_files = review_context.get("baseline_files") or []
    mode = review_context.get("mode")
    context_label = (
        "Pull request scoped files"
        if mode == "pull_request"
        else "Recently changed scoped files"
    )
    return (
        "Repository inspection is now closed. Do not call list_dir, read_file, "
        "or search_text anymore. From this point on, use final_report to submit "
        "one finding per tool call, then call end_review when all reports are "
        "submitted. Base your reports only on the evidence collected in this "
        f"session. {context_label}: {review_context.get('files', [])}. "
        f"Baseline seed files: {baseline_files}. "
        f"Inspected paths so far: {inspected_paths}. "
        "If there are no reportable findings, submit exactly one final_report "
        "saying so, then call end_review."
    )


def build_iteration_limit_report(
    review_context: dict[str, Any], transcript: list[dict[str, Any]]
) -> str:
    inspected_paths = collect_inspected_paths(transcript)
    analysis_date = dt.datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d:%m:%Y")
    inspected_text = ", ".join(inspected_paths[:10]) or "нет подтверждённых файлов"
    changed_files = review_context.get("files") or []
    changed_text = ", ".join(changed_files[:10]) or "нет"
    changed_label = (
        "Изменения pull request"
        if review_context.get("mode") == "pull_request"
        else "Недавние scoped-изменения"
    )

    return textwrap.dedent(
        f"""
        ### [Notice] Анализ ограничен лимитом итераций
        Анализ был проведён {analysis_date}.

        #### Краткое резюме
        Модель не успела завершить полноценный итоговый отчёт в пределах лимита итераций.

        #### Где обнаружено
        Проверка затрагивала только часть разрешённого scope.

        #### Что именно обнаружено
        Подтверждённый итог по всему репозиторию отсутствует. Просмотренные пути: {inspected_text}.

        #### Почему это может быть проблемой
        При неполном покрытии нельзя надёжно утверждать, что в коде нет ошибок,
        уязвимостей или проблем с производительностью.

        #### Как проверить
        Перезапустить ревью с большим лимитом итераций или сузить scope.
        {changed_label}: {changed_text}.

        #### Возможное направление исправления
        Упростить prompt, уменьшить объём анализа за один запуск или повысить
        лимит итераций для модели. Также можно скорректировать правила
        завершения, если модель не вызывает end_review самостоятельно.

        #### Дополнительный контекст
        Итоговый отчёт был сформирован раннером автоматически после исчерпания
        внутреннего лимита завершения без вызова end_review.
        """
    ).strip()


def extract_report_payload(arguments: dict[str, Any]) -> list[str]:
    report_markdown = arguments.get("report_markdown")
    if isinstance(report_markdown, str) and report_markdown.strip():
        return [report_markdown.strip()]

    reports = arguments.get("reports")
    if isinstance(reports, list):
        return [
            report.strip()
            for report in reports
            if isinstance(report, str) and report.strip()
        ]

    return []


def build_client(
    api_key: str,
    folder_id: str,
    model_uri: str,
    config: RuntimeConfig,
):
    from tools.warden.yandex_client import YandexClient

    return YandexClient(
        api_key=api_key,
        folder_id=folder_id,
        model_uri=model_uri,
        config=config,
    )


def collect_pull_request_scope_paths(file_changes: list[dict[str, str]]) -> list[str]:
    paths: list[str] = []

    for item in file_changes:
        for candidate in (item.get("path"), item.get("old_path")):
            if not isinstance(candidate, str) or candidate in paths:
                continue
            paths.append(candidate)

    return paths


def run_review(
    repo_root: pathlib.Path,
    output_dir: pathlib.Path,
    config: RuntimeConfig,
    api_key: str,
    folder_id: str,
    review_mode: str = "repository",
    base_ref: str | None = None,
    base_sha: str | None = None,
    head_sha: str | None = None,
    pull_request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model_name = os.environ.get("YANDEX_AI_MODEL", config.model_name)
    model_uri = build_model_uri(folder_id, model_name)
    effective_config = config

    if review_mode == "pull_request":
        review_context = gather_pull_request_activity(
            repo_root=repo_root,
            scope=None,
            base_ref=base_ref,
            base_sha=base_sha,
            head_sha=head_sha,
            patch_line_limit=min(config.limits.file_lines, 120),
            metadata=pull_request,
        )
        auto_scope_paths = collect_pull_request_scope_paths(
            review_context.get("file_changes") or []
        )
        effective_config = with_force_include_paths(config, auto_scope_paths)
        review_context["auto_scope_paths"] = auto_scope_paths
    elif review_mode == "repository":
        review_context = gather_recent_activity(
            repo_root, config.review_window_days, config.scope
        )
        if not review_context["files"]:
            review_context["baseline_files"] = pick_baseline_files(
                repo_root, effective_config
            )
    else:
        raise ReviewError(f"unknown review mode: {review_mode}")

    messages = build_initial_messages(repo_root, effective_config, review_context)
    client = build_client(
        api_key=api_key,
        folder_id=folder_id,
        model_uri=model_uri,
        config=effective_config,
    )
    tools = ReviewTools(repo_root=repo_root, config=effective_config)
    transcript: list[dict[str, Any]] = []

    final_reports: list[str] = []
    finalized = False
    total_iteration_limit = config.max_iterations + max(20, config.max_iterations)
    finalization_mode = False
    finalization_notice_sent = False

    for iteration in range(1, total_iteration_limit + 1):
        if iteration > config.max_iterations and not finalization_notice_sent:
            messages.append(
                {
                    "role": "user",
                    "text": build_finalization_phase_prompt(review_context, transcript),
                }
            )
            finalization_mode = True
            finalization_notice_sent = True

        completion = client.complete(messages)
        action = completion["action"]
        transcript.append(
            {
                "iteration": iteration,
                "model_action": action,
                "usage": completion["raw_response"].get("usage"),
                "status": (completion["raw_response"].get("alternatives") or [{}])[
                    0
                ].get("status"),
            }
        )

        tool_name = action["tool_name"]
        arguments = action["arguments"]

        if tool_name in REPOSITORY_TOOLS:
            if finalization_mode:
                tool_result = {
                    "ok": False,
                    "error": (
                        "repository inspection phase is closed; use final_report "
                        "to submit findings and end_review to finish"
                    ),
                }
            else:
                try:
                    tool_result = {"ok": True, "data": tools.execute(tool_name, arguments)}
                except Exception as exc:  # noqa: BLE001
                    tool_result = {"ok": False, "error": str(exc)}
        elif tool_name == "final_report":
            submitted_reports = extract_report_payload(arguments)
            if not submitted_reports:
                tool_result = {
                    "ok": False,
                    "error": (
                        "final_report requires a non-empty report_markdown string "
                        "or a non-empty reports array"
                    ),
                }
            else:
                added = 0
                duplicates = 0
                for report in submitted_reports:
                    if report in final_reports:
                        duplicates += 1
                        continue
                    final_reports.append(report)
                    added += 1
                tool_result = {
                    "ok": True,
                    "data": {
                        "accepted_reports": added,
                        "duplicate_reports": duplicates,
                        "reports_count": len(final_reports),
                    },
                }
        elif tool_name == "end_review":
            if not final_reports:
                tool_result = {
                    "ok": False,
                    "error": (
                        "no reports have been submitted yet; use final_report first, "
                        "even if it only states that no reportable findings were found"
                    ),
                }
            else:
                tool_result = {
                    "ok": True,
                    "data": {
                        "reports_count": len(final_reports),
                    },
                }
                finalized = True
        else:
            tool_result = {
                "ok": False,
                "error": f"unknown tool requested: {tool_name}",
            }

        transcript[-1]["tool_result"] = tool_result

        if finalized:
            break

        messages.append(
            {"role": "assistant", "text": json.dumps(action, ensure_ascii=False)}
        )
        messages.append(
            {
                "role": "user",
                "text": format_tool_result(tool_name, arguments, tool_result),
            }
        )

    if not final_reports:
        final_reports = [build_iteration_limit_report(review_context, transcript)]

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.md"
    session_path = output_dir / "session.json"

    generated_at = (
        dt.datetime.now(ZoneInfo("Europe/Moscow")).replace(microsecond=0).isoformat()
    )
    header = textwrap.dedent(
        f"""
        # {"Pull Request AI Review" if review_mode == "pull_request" else "Weekly AI Review"}

        Generated at: {generated_at}
        Model URI: {model_uri}
        Review mode: {review_mode}
        """
    ).strip()

    final_report = combine_reports(final_reports)
    report_path.write_text(f"{header}\n\n{final_report}\n", encoding="utf-8")
    session_payload = {
        "generated_at": generated_at,
        "model_uri": model_uri,
        "review_mode": review_mode,
        "review_context": review_context,
        "final_reports": final_reports,
        "effective_scope": {
            "include": list(effective_config.scope.include),
            "exclude": list(effective_config.scope.exclude),
            "force_include": list(effective_config.scope.force_include),
        },
        "finalized_with_end_review": finalized,
        "transcript": transcript,
    }
    if review_mode == "repository":
        session_payload["recent_activity"] = review_context
    else:
        session_payload["pull_request"] = review_context
    session_path.write_text(
        json.dumps(
            session_payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "report_path": report_path,
        "session_path": session_path,
    }
