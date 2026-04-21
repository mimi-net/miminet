from __future__ import annotations

import fnmatch
import pathlib
import re
from typing import Any

from tools.ai_review.config import RuntimeConfig
from tools.ai_review.exceptions import ReviewError
from tools.ai_review.paths import is_allowed_by_scope
from tools.ai_review.paths import is_probably_binary
from tools.ai_review.paths import posix_relative
from tools.ai_review.paths import within_path


class ReviewTools:
    def __init__(self, repo_root: pathlib.Path, config: RuntimeConfig) -> None:
        self.repo_root = repo_root.resolve()
        self.config = config

    def resolve_path(self, raw_path: str, require_exists: bool = True) -> pathlib.Path:
        target = (self.repo_root / raw_path).resolve()
        if not within_path(target, self.repo_root):
            raise ReviewError(f"path escapes repository root: {raw_path}")

        scope_target = target if target.exists() else target.parent
        relative = posix_relative(scope_target, self.repo_root)

        if not is_allowed_by_scope(relative, self.config.scope):
            raise ReviewError(f"path is outside configured review scope: {raw_path}")

        if require_exists and not target.exists():
            raise ReviewError(f"path does not exist: {raw_path}")

        return target

    def list_dir(
        self,
        path: str = ".",
        recursive: bool = False,
        limit: int | None = None,
    ) -> dict[str, Any]:
        directory = self.resolve_path(path)
        if not directory.is_dir():
            raise ReviewError(f"not a directory: {path}")

        entry_limit = min(
            limit or self.config.limits.directory_entries,
            self.config.limits.directory_entries,
        )
        collected: list[dict[str, str]] = []
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        truncated = False

        for entry in sorted(iterator):
            if len(collected) >= entry_limit:
                truncated = True
                break
            relative = posix_relative(entry, self.repo_root)
            if not is_allowed_by_scope(relative, self.config.scope):
                continue
            collected.append(
                {
                    "path": relative,
                    "type": "dir" if entry.is_dir() else "file",
                }
            )

        return {
            "path": posix_relative(directory, self.repo_root),
            "recursive": recursive,
            "entries": collected,
            "truncated": truncated,
        }

    def read_file(
        self,
        path: str,
        start_line: int = 1,
        max_lines: int | None = None,
    ) -> dict[str, Any]:
        file_path = self.resolve_path(path)
        if not file_path.is_file():
            raise ReviewError(f"not a file: {path}")
        if is_probably_binary(file_path):
            raise ReviewError(f"binary file is not readable by this tool: {path}")
        if file_path.stat().st_size > self.config.limits.file_bytes:
            raise ReviewError(
                "file is larger than configured read limit "
                f"({self.config.limits.file_bytes} bytes): {path}"
            )

        line_limit = min(
            max_lines or self.config.limits.file_lines, self.config.limits.file_lines
        )
        start = max(start_line, 1)
        end = start + line_limit - 1

        rendered_lines: list[str] = []
        with file_path.open("r", encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, start=1):
                if number < start:
                    continue
                if number > end:
                    break
                rendered_lines.append(f"{number:>5} | {line.rstrip()}")

        return {
            "path": posix_relative(file_path, self.repo_root),
            "start_line": start,
            "max_lines": line_limit,
            "content": "\n".join(rendered_lines),
        }

    def search_text(
        self,
        pattern: str,
        path: str = ".",
        file_glob: str = "*",
        case_sensitive: bool = False,
        regex: bool = False,
        limit: int | None = None,
    ) -> dict[str, Any]:
        root = self.resolve_path(path)
        match_limit = min(
            limit or self.config.limits.search_matches,
            self.config.limits.search_matches,
        )

        flags = 0 if case_sensitive else re.IGNORECASE
        compiled = re.compile(pattern, flags) if regex else None
        matches: list[dict[str, Any]] = []
        truncated = False

        if root.is_file():
            candidates = [root]
        else:
            candidates = sorted(item for item in root.rglob("*") if item.is_file())

        for candidate in candidates:
            if len(matches) >= match_limit:
                truncated = True
                break

            relative = posix_relative(candidate, self.repo_root)
            if not (
                is_allowed_by_scope(relative, self.config.scope)
                and fnmatch.fnmatchcase(candidate.name, file_glob)
                and candidate.stat().st_size > self.config.limits.file_bytes
            ) or is_probably_binary(candidate):
                continue

            with candidate.open("r", encoding="utf-8", errors="replace") as handle:
                for line_number, line in enumerate(handle, start=1):
                    haystack = line if case_sensitive else line.lower()
                    needle = pattern if case_sensitive else pattern.lower()
                    found = (
                        bool(compiled.search(line)) if compiled else needle in haystack
                    )
                    if not found:
                        continue
                    matches.append(
                        {
                            "path": relative,
                            "line": line_number,
                            "text": line.rstrip(),
                        }
                    )
                    if len(matches) >= match_limit:
                        truncated = True
                        break

        return {
            "pattern": pattern,
            "path": posix_relative(root, self.repo_root),
            "matches": matches,
            "truncated": truncated,
        }

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "list_dir": self.list_dir,
            "read_file": self.read_file,
            "search_text": self.search_text,
        }
        if tool_name not in handlers:
            raise ReviewError(f"unknown tool requested: {tool_name}")
        return handlers[tool_name](**arguments)
