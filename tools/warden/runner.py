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
from tools.warden.yandex_client import YandexClient


def format_tool_result(
    tool_name: str, arguments: dict[str, Any], result: dict[str, Any]
) -> str:
    payload = {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result,
    }
    return (
        "Tool result:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Continue the review. Return either another tool_call or final_report."
    )


def build_forced_final_report_prompt(
    review_context: dict[str, Any], transcript: list[dict[str, Any]]
) -> str:
    inspected_paths: list[str] = []

    for item in transcript:
        tool_result = item.get("tool_result") or {}
        if not tool_result.get("ok"):
            continue

        data = tool_result.get("data") or {}
        path = data.get("path")
        if isinstance(path, str) and path not in inspected_paths:
            inspected_paths.append(path)

    baseline_files = review_context.get("baseline_files") or []
    mode = review_context.get("mode")
    context_label = (
        "Pull request scoped files"
        if mode == "pull_request"
        else "Recently changed scoped files"
    )
    return (
        "This is the final allowed iteration. Do not call any more tools. "
        "Return final_report now based only on the evidence collected in this "
        f"session. {context_label}: {review_context.get('files', [])}. "
        f"Baseline seed files: {baseline_files}. "
        f"Inspected paths so far: {inspected_paths}. "
        "If the evidence is limited, explicitly say so in the report instead of "
        "claiming that the whole repository has no issues."
    )


def build_iteration_limit_report(
    review_context: dict[str, Any], transcript: list[dict[str, Any]]
) -> str:
    inspected_paths: list[str] = []

    for item in transcript:
        tool_result = item.get("tool_result") or {}
        if not tool_result.get("ok"):
            continue

        data = tool_result.get("data") or {}
        path = data.get("path")
        if isinstance(path, str) and path not in inspected_paths:
            inspected_paths.append(path)

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
        лимит итераций для модели.

        #### Дополнительный контекст
        Итоговый отчёт был сформирован раннером автоматически после исчерпания
        лимита итераций.
        """
    ).strip()


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

    client = YandexClient(
        api_key=api_key,
        folder_id=folder_id,
        model_uri=model_uri,
        config=effective_config,
    )
    tools = ReviewTools(repo_root=repo_root, config=effective_config)
    transcript: list[dict[str, Any]] = []

    final_report = ""

    for iteration in range(1, config.max_iterations):
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

        if action["action"] == "final_report":
            final_report = action["report_markdown"].strip()
            break

        tool_name = action["tool_name"]
        arguments = action["arguments"]

        try:
            tool_result = {"ok": True, "data": tools.execute(tool_name, arguments)}
        except Exception as exc:  # noqa: BLE001
            tool_result = {"ok": False, "error": str(exc)}

        transcript[-1]["tool_result"] = tool_result
        messages.append(
            {"role": "assistant", "text": json.dumps(action, ensure_ascii=False)}
        )
        messages.append(
            {
                "role": "user",
                "text": format_tool_result(tool_name, arguments, tool_result),
            }
        )

    if not final_report:
        messages.append(
            {
                "role": "user",
                "text": build_forced_final_report_prompt(review_context, transcript),
            }
        )
        completion = client.complete(messages)
        action = completion["action"]
        transcript.append(
            {
                "iteration": config.max_iterations,
                "model_action": action,
                "usage": completion["raw_response"].get("usage"),
                "status": (completion["raw_response"].get("alternatives") or [{}])[0]
                .get("status"),
                "forced_final_iteration": True,
            }
        )

        if action["action"] == "final_report":
            final_report = action["report_markdown"].strip()
        else:
            transcript[-1]["rejected"] = "tool_call_on_forced_final_iteration"
            final_report = build_iteration_limit_report(review_context, transcript)

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

    report_path.write_text(f"{header}\n\n{final_report}\n", encoding="utf-8")
    session_payload = {
        "generated_at": generated_at,
        "model_uri": model_uri,
        "review_mode": review_mode,
        "review_context": review_context,
        "effective_scope": {
            "include": list(effective_config.scope.include),
            "exclude": list(effective_config.scope.exclude),
            "force_include": list(effective_config.scope.force_include),
        },
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
