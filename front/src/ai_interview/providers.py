import json
import os
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from jsonschema import ValidationError, validate


DIFFICULTY_ALIASES = {
    "easy": "basic",
    "medium": "mechanism",
    "intermediate": "mechanism",
    "hard": "advanced",
}

GENERATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "question": {"type": "string", "minLength": 8},
        "expected_concepts": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 8,
        },
        "expected_reasoning": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5,
        },
        "common_wrong_answers": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 4,
        },
        "difficulty": {
            "type": "string",
            "enum": ["basic", "mechanism", "practice", "advanced"],
        },
    },
    "required": ["question", "expected_concepts", "difficulty"],
}


EVALUATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "feedback": {"type": "string", "minLength": 1},
        "answer_summary": {"type": "string", "minLength": 1},
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
        "answer_summary",
        "covered_concepts",
        "missed_concepts",
        "misconceptions",
        "answer_score",
        "critical_error",
        "final_result",
    ],
}

PROXY_TEST_URL = "https://api.ipify.org?format=json"
ALLOWED_PROXY_SCHEMES = {"http", "https", "socks5", "socks5h"}

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


class ProxyConfigError(ValueError):
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


def normalize_proxy_url(proxy_url):
    proxy_url = str(proxy_url or "").strip()
    if not proxy_url:
        return ""

    parsed = urlparse(proxy_url)
    if parsed.scheme not in ALLOWED_PROXY_SCHEMES:
        raise ProxyConfigError(
            "Прокси должен начинаться с http://, https://, socks5:// или socks5h://."
        )
    if not parsed.hostname or not parsed.port:
        raise ProxyConfigError("Укажите адрес прокси в формате scheme://host:port.")
    return proxy_url


def masked_proxy_url(proxy_url):
    proxy_url = str(proxy_url or "").strip()
    if not proxy_url:
        return ""

    parsed = urlparse(proxy_url)
    if not parsed.password:
        return proxy_url

    auth = parsed.username or ""
    if auth:
        auth = f"{auth}:***@"
    return parsed._replace(netloc=f"{auth}{parsed.hostname}:{parsed.port}").geturl()


def validate_payload(payload, schema):
    _normalize_question_payload(payload)
    if schema is EVALUATION_SCHEMA:
        _normalize_evaluation_payload(payload)
    validate(instance=payload, schema=schema)
    return payload


def _normalize_evaluation_payload(payload):
    if not isinstance(payload, dict):
        return

    explanation = payload.pop("answer_explanation", None)
    if isinstance(explanation, str) and explanation.strip():
        payload.setdefault("feedback", explanation.strip())
        payload.setdefault("answer_summary", explanation.strip())

    payload.setdefault("covered_concepts", [])
    payload.setdefault("missed_concepts", [])
    payload.setdefault("misconceptions", [])

    final_result = payload.get("final_result")
    if isinstance(final_result, str) and final_result.strip():
        payload["final_result"] = {
            "grade": 2,
            "verdict": final_result.strip(),
            "strengths": [],
            "gaps": [],
            "recommendations": [],
        }


def _normalize_question_payload(payload):
    if not isinstance(payload, dict):
        return

    question = payload.get("question")
    if isinstance(question, dict) and isinstance(question.get("text"), str):
        payload["question"] = question["text"]

    difficulty = payload.get("difficulty")
    if isinstance(difficulty, str):
        payload["difficulty"] = DIFFICULTY_ALIASES.get(
            difficulty.casefold(), difficulty
        )

    for key in ("expected_reasoning", "common_wrong_answers"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            payload[key] = [value.strip()]


def _temperature(env_key, default):
    try:
        return float(os.environ.get(env_key, default))
    except (TypeError, ValueError):
        return default


def generation_temperature():
    return _temperature("AI_INTERVIEW_GENERATION_TEMPERATURE", 0.75)


def evaluation_temperature():
    return _temperature("AI_INTERVIEW_EVALUATION_TEMPERATURE", 0.2)


def retry_limit():
    try:
        return max(0, min(int(os.environ.get("AI_INTERVIEW_LLM_RETRIES", 1)), 2))
    except (TypeError, ValueError):
        return 1


class ChatJsonProvider:
    name = ""
    api_url = ""

    def __init__(self, api_key, model, proxy_url=""):
        self.api_key = api_key
        self.model = model
        self.proxy_url = normalize_proxy_url(proxy_url)

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

    def _session(self):
        session = requests.Session()
        session.trust_env = False

        if self.proxy_url:
            session.proxies.update({"http": self.proxy_url, "https": self.proxy_url})

        return session

    def _request(self, system_prompt, user_prompt, temperature):
        with self._session() as session:
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
        headers["X-Title"] = "Miminet AI Interview"
        return headers


def get_provider(proxy_url=""):
    provider_name = os.environ.get("AI_INTERVIEW_PROVIDER", "").casefold()
    if provider_name == "openrouter":
        api_key = read_env_secret("OPENROUTER_API_KEY")
        model = os.environ.get("AI_INTERVIEW_OPENROUTER_MODEL", "")
        if api_key and model:
            return OpenRouterProvider(api_key, model, proxy_url=proxy_url)

    raise ProviderNotConfigured(
        "AI-провайдер не настроен. Преподаватель должен настроить OpenRouter."
    )


def check_proxy(proxy_url):
    proxy_url = normalize_proxy_url(proxy_url)
    session = requests.Session()
    session.trust_env = False
    session.proxies.update({"http": proxy_url, "https": proxy_url})
    response = session.get(PROXY_TEST_URL, timeout=10)
    response.raise_for_status()
    payload = response.json()
    ip_address = payload.get("ip")
    if not ip_address:
        raise ProviderError("Прокси ответил, но сервис проверки не вернул IP.")
    return {"ip": ip_address}


def check_provider(proxy_url=""):
    provider = get_provider(proxy_url=proxy_url)
    completion = provider.complete_json(
        "Return only valid JSON.",
        'Return exactly {"ok": true}.',
        0,
        PROVIDER_CHECK_SCHEMA,
    )
    if completion.payload.get("ok") is not True:
        raise ProviderError("LLM вернула неожиданный ответ.", completion.calls)
    return {"model": provider.model, "calls": completion.calls}
