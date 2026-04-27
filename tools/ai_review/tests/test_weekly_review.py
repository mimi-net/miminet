from __future__ import annotations

import pathlib
import tempfile
import unittest

from tools.ai_review.config import Limits
from tools.ai_review.config import RuntimeConfig
from tools.ai_review.config import Scope
from tools.ai_review.exceptions import ReviewError
from tools.ai_review.model import build_model_uri
from tools.ai_review.prompts import build_initial_messages
from tools.ai_review.agent_tools import ReviewTools


def make_config() -> RuntimeConfig:
    return RuntimeConfig(
        model_name="yandexgpt-lite",
        temperature=0.1,
        max_tokens=1000,
        max_iterations=4,
        review_window_days=7,
        disable_data_logging=True,
        focus=(),
        limits=Limits(
            directory_entries=20,
            file_lines=20,
            file_bytes=50_000,
            search_matches=20,
        ),
        scope=Scope(
            include=("src", "README.md"),
            exclude=("**/*.png",),
        ),
    )


class ReviewToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = pathlib.Path(self.temp_dir.name)
        (self.repo_root / "src").mkdir()
        (self.repo_root / "src" / "main.py").write_text(
            "def hello():\n    return 'world'\n",
            encoding="utf-8",
        )
        (self.repo_root / "README.md").write_text("# demo\n", encoding="utf-8")
        (self.repo_root / "src" / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        self.tools = ReviewTools(self.repo_root, make_config())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_list_dir_respects_scope(self) -> None:
        result = self.tools.list_dir("src")
        paths = [entry["path"] for entry in result["entries"]]
        self.assertIn("src/main.py", paths)
        self.assertNotIn("src/image.png", paths)

    def test_list_dir_is_not_truncated_at_exact_limit(self) -> None:
        result = self.tools.list_dir("src", limit=1)

        self.assertEqual(len(result["entries"]), 1)
        self.assertFalse(result["truncated"])

    def test_list_dir_marks_real_truncation(self) -> None:
        (self.repo_root / "src" / "other.py").write_text("x = 1\n", encoding="utf-8")
        result = self.tools.list_dir("src", limit=1)

        self.assertEqual(len(result["entries"]), 1)
        self.assertTrue(result["truncated"])

    def test_read_file_returns_numbered_lines(self) -> None:
        result = self.tools.read_file("src/main.py")
        self.assertIn("1 | def hello():", result["content"])

    def test_read_file_blocks_path_escape(self) -> None:
        with self.assertRaises(ReviewError):
            self.tools.read_file("../etc/passwd")

    def test_search_text_returns_matches(self) -> None:
        result = self.tools.search_text("hello", path="src")
        self.assertEqual(result["matches"][0]["path"], "src/main.py")


class ModelUriTest(unittest.TestCase):
    def test_build_model_uri(self) -> None:
        self.assertEqual(
            build_model_uri("folder123", "yandexgpt-lite"),
            "gpt://folder123/yandexgpt-lite",
        )
        self.assertEqual(
            build_model_uri("folder123", "gpt://folder456/yandexgpt/latest"),
            "gpt://folder456/yandexgpt/latest",
        )


class PromptFormatTest(unittest.TestCase):
    def test_initial_prompt_contains_finding_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            (repo_root / "src").mkdir()
            messages = build_initial_messages(
                repo_root,
                make_config(),
                {"since": "2026-04-14", "commits": [], "files": []},
            )

        prompt_text = "\n\n".join(message["text"] for message in messages)
        self.assertIn("[Alert|Warning|Notice] <Название>", prompt_text)
        self.assertIn("Краткое резюме", prompt_text)
        self.assertIn("Где обнаружено", prompt_text)
        self.assertIn("Что именно обнаружено", prompt_text)
        self.assertIn("Почему это может быть проблемой", prompt_text)
        self.assertIn("Как проверить", prompt_text)
        self.assertIn("Возможное направление исправления", prompt_text)
        self.assertIn("Дополнительный контекст", prompt_text)


if __name__ == "__main__":
    unittest.main()
