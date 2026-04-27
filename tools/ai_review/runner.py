from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import textwrap
from typing import Any
from zoneinfo import ZoneInfo

from tools.ai_review.config import RuntimeConfig
from tools.ai_review.exceptions import ReviewError
from tools.ai_review.model import build_model_uri
from tools.ai_review.prompts import build_initial_messages
from tools.ai_review.recent_activity import gather_recent_activity
from tools.ai_review.agent_tools import ReviewTools
from tools.ai_review.yandex_client import YandexClient


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


def run_review(
    repo_root: pathlib.Path,
    output_dir: pathlib.Path,
    config: RuntimeConfig,
    api_key: str,
    folder_id: str,
) -> dict[str, Any]:
    model_name = os.environ.get("YANDEX_AI_MODEL", config.model_name)
    model_uri = build_model_uri(folder_id, model_name)

    recent_activity = gather_recent_activity(repo_root, config.review_window_days)
    messages = build_initial_messages(repo_root, config, recent_activity)

    client = YandexClient(api_key=api_key, model_uri=model_uri, config=config)
    tools = ReviewTools(repo_root=repo_root, config=config)
    transcript: list[dict[str, Any]] = []

    final_report = ""

    for iteration in range(1, config.max_iterations + 1):
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
        raise ReviewError(
            f"review did not finish in {config.max_iterations} iterations; "
            "increase limits or simplify the prompt"
        )

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
