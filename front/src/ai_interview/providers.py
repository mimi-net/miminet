import json
import os
from dataclasses import dataclass
from typing import Any

import requests
from jsonschema import ValidationError, validate


EVALUATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "feedback": {"type": "string", "minLength": 1},
        "covered_concepts": {"type": "array", "items": {"type": "string"}},
        "missed_concepts": {"type": "array", "items": {"type": "string"}},
        "misconceptions": {"type": "array", "items": {"type": "string"}},
        "answer_score": {"type": "integer", "minimum": 0, "maximum": 3},
        "critical_error": {"type": "boolean"},
        "final_result": {
            "anyOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "grade": {"type": "integer", "minimum": 2, "maximum": 5},
                        "verdict": {"type": "string", "minLength": 1},
                        "strengths": {"type": "array", "items": {"type": "string"}},
                        "gaps": {"type": "array", "items": {"type": "string"}},
                        "recommendations": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "grade",
                        "verdict",
                        "strengths",
                        "gaps",
                        "recommendations",
                    ],
                },
                {"type": "null"},
            ]
        },
    },
    "required": [
        "feedback",
        "covered_concepts",
        "missed_concepts",
        "misconceptions",
        "answer_score",
        "critical_error",
        "final_result",
    ],
}

MAIN_ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **EVALUATION_SCHEMA["properties"],
        "followup_question": {"type": "string", "minLength": 8},
        "followup_reference_answer": {"type": "string", "minLength": 1},
    },
    "required": [
        *EVALUATION_SCHEMA["required"],
        "followup_question",
        "followup_reference_answer",
    ],
}

PROVIDER_CHECK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ok": {"type": "boolean"},
    },
    "required": ["ok"],
}


@dataclass(frozen=True)
class JsonCompletion:
    payload: dict
    calls: int


class ProviderError(Exception):
    def __init__(self, message, calls=0):
        super().__init__(message)
        self.calls = calls


class ProviderNotConfigured(ProviderError):
    pass


def read_env_secret(name):
    value = os.environ.get(name, "").strip()
    if value:
        return value

    file_path = os.environ.get(f"{name}_FILE", "").strip()
    if not file_path:
        return ""

    try:
        with open(file_path, encoding="utf-8") as secret_file:
            return secret_file.read().strip()
    except OSError as exc:
        raise ProviderNotConfigured(
            f"AI secret file for {name} is not readable."
        ) from exc


def validate_payload(payload, schema):
    validate(instance=payload, schema=schema)
    return payload


def _temperature(env_key, default):
    try:
        return float(os.environ.get(env_key, default))
    except (TypeError, ValueError):
        return default


def evaluation_temperature():
    return _temperature("AI_INTERVIEW_EVALUATION_TEMPERATURE", 0.3)


def retry_limit():
    try:
        return max(0, min(int(os.environ.get("AI_INTERVIEW_LLM_RETRIES", 1)), 2))
    except (TypeError, ValueError):
        return 1


class ChatJsonProvider:
    name = ""
    api_url = ""

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request_body(self, system_prompt, user_prompt, temperature):
        return {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

    def _request(self, system_prompt, user_prompt, temperature):
        with requests.Session() as session:
            session.trust_env = False
            response = session.post(
                self.api_url,
                json=self._request_body(system_prompt, user_prompt, temperature),
                headers=self._headers(),
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
        return payload["choices"][0]["message"]["content"]

    def complete_json(self, system_prompt, user_prompt, temperature, schema):
        last_error = None
        calls = 0
        for _ in range(retry_limit() + 1):
            calls += 1
            try:
                raw = self._request(system_prompt, user_prompt, temperature)
                payload = json.loads(raw)
                return JsonCompletion(validate_payload(payload, schema), calls)
            except (KeyError, TypeError, json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
            except requests.HTTPError as exc:
                status_code = (
                    exc.response.status_code if exc.response is not None else "error"
                )
                raise ProviderError(
                    f"LLM API returned HTTP {status_code}", calls
                ) from exc
            except requests.RequestException as exc:
                raise ProviderError("LLM API is unavailable", calls) from exc

        raise ProviderError(
            f"LLM returned invalid structured output: {last_error}", calls
        )


class OpenRouterProvider(ChatJsonProvider):
    name = "openrouter"
    api_url = "https://openrouter.ai/api/v1/chat/completions"

    def _headers(self):
        headers = super()._headers()
        site_url = os.environ.get("EXTERNAL_BASE_URL")
        if site_url:
            headers["HTTP-Referer"] = site_url
        headers["X-Title"] = "Miminet AI Testing"
        return headers


def get_provider():
    provider_name = os.environ.get("AI_INTERVIEW_PROVIDER", "").casefold()
    if provider_name == "openrouter":
        api_key = read_env_secret("OPENROUTER_API_KEY")
        model = os.environ.get("AI_INTERVIEW_OPENROUTER_MODEL", "")
        if api_key and model:
            return OpenRouterProvider(api_key, model)

    raise ProviderNotConfigured(
        "AI-провайдер не настроен. Преподаватель должен настроить OpenRouter."
    )


def check_provider():
    provider = get_provider()
    completion = provider.complete_json(
        "Return only valid JSON.",
        'Return exactly {"ok": true}.',
        0,
        PROVIDER_CHECK_SCHEMA,
    )
    if completion.payload.get("ok") is not True:
        raise ProviderError("LLM вернула неожиданный ответ.", completion.calls)
    return {"model": provider.model, "calls": completion.calls}
