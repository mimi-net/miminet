from typing import Any

from tools.warden.exceptions import ReviewError


def build_json_schema() -> dict[str, Any]:
    return {
        "schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["tool_call"]},
                "tool_name": {
                    "type": "string",
                    "enum": [
                        "list_dir",
                        "read_file",
                        "search_text",
                        "final_report",
                        "end_review",
                    ],
                },
                "arguments": {"type": "object"},
            },
            "required": ["action", "tool_name", "arguments"],
            "additionalProperties": False,
        }
    }


def validate_action(action: dict[str, Any]) -> dict[str, Any]:
    action_type = action.get("action")
    if action_type != "tool_call":
        raise ReviewError("model response does not contain a valid action")

    tool_name = action.get("tool_name")
    if not isinstance(tool_name, str):
        raise ReviewError("tool_call action is missing tool_name")

    arguments = action.get("arguments")
    if not isinstance(arguments, dict):
        raise ReviewError("tool_call action is missing arguments object")

    if tool_name == "final_report":
        reports = arguments.get("reports")
        report_markdown = arguments.get("report_markdown")

        if isinstance(report_markdown, str) and report_markdown.strip():
            return action

        if isinstance(reports, list) and reports:
            if not all(
                isinstance(report, str) and report.strip() for report in reports
            ):
                raise ReviewError(
                    "final_report reports must contain non-empty strings"
                )
            return action

        raise ReviewError(
            "final_report tool_call requires report_markdown or reports"
        )

    if tool_name == "end_review" and arguments:
        raise ReviewError("end_review tool_call must not contain arguments")

    return action
