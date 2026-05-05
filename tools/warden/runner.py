import datetime as dt
import json
import os
import pathlib
import textwrap
from typing import Any
from zoneinfo import ZoneInfo

from tools.warden.config import RuntimeConfig
from tools.warden.model import build_model_uri
from tools.warden.prompts import build_initial_messages
from tools.warden.prompts import pick_baseline_files
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
    recent_activity: dict[str, Any], transcript: list[dict[str, Any]]
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

    baseline_files = recent_activity.get("baseline_files") or []
    return (
        "This is the final allowed iteration. Do not call any more tools. "
        "Return final_report now based only on the evidence collected in this "
        f"session. Recently changed scoped files: {recent_activity.get('files', [])}. "
        f"Baseline seed files: {baseline_files}. "
        f"Inspected paths so far: {inspected_paths}. "
        "If the evidence is limited, explicitly say so in the report instead of "
        "claiming that the whole repository has no issues."
    )


def build_iteration_limit_report(
    recent_activity: dict[str, Any], transcript: list[dict[str, Any]]
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
    changed_files = recent_activity.get("files") or []
    changed_text = ", ".join(changed_files[:10]) or "нет"

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
        Перезапустить ревью с большим лимитом итераций или сузить scope. Недавние
        scoped-изменения: {changed_text}.

        #### Возможное направление исправления
        Упростить prompt, уменьшить объём анализа за один запуск или повысить
        лимит итераций для модели.

        #### Дополнительный контекст
        Итоговый отчёт был сформирован раннером автоматически после исчерпания
        лимита итераций.
        """
    ).strip()


def run_review(
    repo_root: pathlib.Path,
    output_dir: pathlib.Path,
    config: RuntimeConfig,
    api_key: str,
    folder_id: str,
) -> dict[str, Any]:
    model_name = os.environ.get("YANDEX_AI_MODEL", config.model_name)
    model_uri = build_model_uri(folder_id, model_name)

    recent_activity = gather_recent_activity(
        repo_root, config.review_window_days, config.scope
    )
    if not recent_activity["files"]:
        recent_activity["baseline_files"] = pick_baseline_files(repo_root, config)
    messages = build_initial_messages(repo_root, config, recent_activity)

    client = YandexClient(
        api_key=api_key,
        folder_id=folder_id,
        model_uri=model_uri,
        config=config,
    )
    tools = ReviewTools(repo_root=repo_root, config=config)
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
                "text": build_forced_final_report_prompt(recent_activity, transcript),
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
            final_report = build_iteration_limit_report(recent_activity, transcript)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.md"
    session_path = output_dir / "session.json"

    generated_at = (
        dt.datetime.now(ZoneInfo("Europe/Moscow")).replace(microsecond=0).isoformat()
    )
    header = textwrap.dedent(
        f"""
        # Weekly AI Review

        Generated at: {generated_at}
        Model URI: {model_uri}
        Review window: last {config.review_window_days} days
        """
    ).strip()

    report_path.write_text(f"{header}\n\n{final_report}\n", encoding="utf-8")
    session_path.write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "model_uri": model_uri,
                "recent_activity": recent_activity,
                "transcript": transcript,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "report_path": report_path,
        "session_path": session_path,
    }
