import json
from typing import Any

import requests

from tools.warden.config import RuntimeConfig
from tools.warden.exceptions import ReviewError
from tools.warden.schema import build_json_schema
from tools.warden.schema import validate_action


API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


class YandexClient:
    def __init__(self, api_key: str, model_uri: str, config: RuntimeConfig) -> None:
        self.api_key = api_key
        self.model_uri = model_uri
        self.config = config

    def complete(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": self.config.temperature,
                "maxTokens": str(self.config.max_tokens),
                "reasoningOptions": {"mode": "DISABLED"},
            },
            "messages": messages,
            "jsonSchema": build_json_schema(),
        }

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}",
        }
        if self.config.disable_data_logging:
            headers["x-data-logging-enabled"] = "false"

        try:
            response = requests.post(
                API_URL,
                data=body,
                headers=headers,
                timeout=120,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "?"
            details = exc.response.text if exc.response is not None else str(exc)
            raise ReviewError(
                f"Yandex AI request failed with HTTP {status_code}: {details}"
            ) from exc
        except requests.RequestException as exc:
            raise ReviewError(f"Yandex AI request failed: {exc}") from exc

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ReviewError("Yandex AI response is not valid JSON") from exc
        alternatives = data.get("alternatives") or []
        if not alternatives:
            raise ReviewError("Yandex AI response does not contain alternatives")

        alternative = alternatives[0]
        message = alternative.get("message") or {}
        text = message.get("text")
        if not isinstance(text, str):
            raise ReviewError("Yandex AI response does not contain a text completion")

        try:
            action = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ReviewError(f"model returned invalid JSON: {text}") from exc

        validate_action(action)
        return {
            "action": action,
            "raw_response": data,
        }
