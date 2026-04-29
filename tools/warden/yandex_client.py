import json
import urllib.error
import urllib.request
from typing import Any

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

        request = urllib.request.Request(
            API_URL, data=body, headers=headers, method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise ReviewError(
                f"Yandex AI request failed with HTTP {exc.code}: {details}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ReviewError(f"Yandex AI request failed: {exc.reason}") from exc

        data = json.loads(raw)
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
