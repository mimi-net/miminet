import pathlib
import tomllib
from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    directory_entries: int
    file_lines: int
    file_bytes: int
    search_matches: int


@dataclass(frozen=True)
class Scope:
    include: tuple[str, ...]
    exclude: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeConfig:
    model_name: str
    temperature: float
    max_tokens: int
    max_iterations: int
    review_window_days: int
    disable_data_logging: bool
    focus: tuple[str, ...]
    limits: Limits
    scope: Scope


def load_config(config_path: pathlib.Path) -> RuntimeConfig:
    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))

    limits = raw["limits"]
    scope = raw["scope"]
    return RuntimeConfig(
        model_name=str(raw.get("model_name", "yandexgpt-lite")),
        temperature=float(raw.get("temperature", 0.1)),
        max_tokens=int(raw.get("max_tokens", 3500)),
        max_iterations=int(raw.get("max_iterations", 12)),
        review_window_days=int(raw.get("review_window_days", 7)),
        disable_data_logging=bool(raw.get("disable_data_logging", True)),
        focus=tuple(str(item) for item in raw.get("focus", [])),
        limits=Limits(
            directory_entries=int(limits.get("directory_entries", 200)),
            file_lines=int(limits.get("file_lines", 200)),
            file_bytes=int(limits.get("file_bytes", 200_000)),
            search_matches=int(limits.get("search_matches", 80)),
        ),
        scope=Scope(
            include=tuple(str(item) for item in scope.get("include", [])),
            exclude=tuple(str(item) for item in scope.get("exclude", [])),
        ),
    )
