import json
from typing import Any
from typing import cast

import openai
from openai import OpenAI

from tools.warden.config import RuntimeConfig
from tools.warden.exceptions import ReviewError
from tools.warden.schema import build_json_schema
from tools.warden.schema import validate_action


API_URL = "https://ai.api.cloud.yandex.net/v1"


class YandexClient:
    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model_uri: str,
        config: RuntimeConfig,
    ) -> None:
        self.api_key = api_key
        self.folder_id = folder_id
        self.model_uri = model_uri
        self.config = config
        self.client = OpenAI(
            api_key=api_key,
            base_url=API_URL,
            project=folder_id,
        )

    def complete(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        request_headers: dict[str, str] = {}
        if self.config.disable_data_logging:
            request_headers["x-data-logging-enabled"] = "false"

        instructions = None
        input_messages = messages
        if messages and messages[0]["role"] == "system":
            instructions = messages[0]["text"]
            input_messages = messages[1:]

        response_input = [
            {
                "role": message["role"],
                "content": [{"type": "input_text", "text": message["text"]}],
            }
            for message in input_messages
        ]

        try:
            response = self.client.responses.create(
                model=self.model_uri,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                instructions=instructions,
                input=cast(Any, response_input),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "weekly_review_action",
                        "schema": build_json_schema()["schema"],
                        "strict": True,
                    }
                },
                extra_headers=request_headers or None,
                timeout=120,
            )
        except openai.APIStatusError as exc:
            status_code = exc.status_code if exc.status_code is not None else "?"
            details = exc.response.text if exc.response is not None else str(exc)
            raise ReviewError(
                f"Yandex AI request failed with HTTP {status_code}: {details}"
            ) from exc
        except openai.OpenAIError as exc:
            raise ReviewError(f"Yandex AI request failed: {exc}") from exc

        text = response.output_text
        if not isinstance(text, str) or not text:
            raise ReviewError("Yandex AI response does not contain a text completion")

        try:
            action = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ReviewError(f"model returned invalid JSON: {text}") from exc

        usage = response.usage
        usage_data = usage.model_dump(mode="json") if usage is not None else None
        response_body = {
            "id": getattr(response, "id", None),
            "status": getattr(response, "status", None),
            "usage": usage_data,
            "alternatives": [
                {
                    "status": getattr(response, "status", None),
                    "message": {"text": text},
                }
            ],
        }

        validate_action(action)
        return {
            "action": action,
            "raw_response": response_body,
        }
