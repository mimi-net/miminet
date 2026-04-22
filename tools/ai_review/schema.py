from typing import Any

from tools.ai_review.exceptions import ReviewError


def build_json_schema() -> dict[str, Any]:
    return {
        "schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["tool_call", "final_report"]},
                "tool_name": {
                    "type": "string",
                    "enum": ["list_dir", "read_file", "search_text"],
                },
                "arguments": {"type": "object"},
                "reason": {"type": "string"},
                "report_markdown": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
            "allOf": [
                {
                    "if": {"properties": {"action": {"const": "tool_call"}}},
                    "then": {"required": ["tool_name", "arguments"]},
                },
                {
                    "if": {"properties": {"action": {"const": "final_report"}}},
                    "then": {"required": ["report_markdown"]},
                },
            ],
        }
    }


def validate_action(action: dict[str, Any]) -> dict[str, Any]:
    action_type = action.get("action")
    if action_type not in {"tool_call", "final_report"}:
        raise ReviewError("model response does not contain a valid action")

    if action_type == "tool_call":
        if not isinstance(action.get("tool_name"), str):
            raise ReviewError("tool_call action is missing tool_name")
        if not isinstance(action.get("arguments"), dict):
            raise ReviewError("tool_call action is missing arguments object")

    if action_type == "final_report":
        report = action.get("report_markdown")
        if not isinstance(report, str) or not report.strip():
            raise ReviewError("final_report action is missing report_markdown")

    return action
