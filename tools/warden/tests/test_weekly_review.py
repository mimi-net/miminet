from __future__ import annotations

import argparse
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tools.warden.cli import resolve_review_options
from tools.warden.config import Limits
from tools.warden.config import RuntimeConfig
from tools.warden.config import Scope
from tools.warden.config import with_force_include_paths
from tools.warden.exceptions import ReviewError
from tools.warden.model import build_model_uri
from tools.warden.prompts import build_initial_messages
from tools.warden.prompts import pick_baseline_files
from tools.warden.paths import is_allowed_by_scope
from tools.warden.recent_activity import gather_pull_request_activity
from tools.warden.recent_activity import gather_recent_activity
from tools.warden.schema import build_json_schema
from tools.warden.agent_tools import ReviewTools

try:
    from tools.warden.yandex_client import YandexClient
except ModuleNotFoundError:
    YandexClient = None


def make_config() -> RuntimeConfig:
    return RuntimeConfig(
        model_name="yandexgpt-lite",
        temperature=0.1,
        max_tokens=1000,
        max_iterations=4,
        review_window_days=7,
        baseline_sample_size=2,
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


class ScopeOverrideTest(unittest.TestCase):
    def test_force_include_paths_override_include_and_exclude(self) -> None:
        config = with_force_include_paths(make_config(), ["docs/image.png"])

        self.assertTrue(is_allowed_by_scope("docs", config.scope))
        self.assertTrue(is_allowed_by_scope("docs/image.png", config.scope))


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
                {
                    "mode": "repository",
                    "since": "2026-04-14",
                    "commits": [],
                    "files": [],
                },
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

    def test_initial_prompt_switches_to_baseline_scan_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            (repo_root / "src").mkdir()
            messages = build_initial_messages(
                repo_root,
                make_config(),
                {
                    "mode": "repository",
                    "since": "2026-04-14",
                    "commits": [],
                    "files": [],
                    "baseline_files": ["src/main.py", "README.md"],
                },
            )

        prompt_text = "\n\n".join(message["text"] for message in messages)
        self.assertIn("Baseline repository scan", prompt_text)
        self.assertIn("Ignore modification dates", prompt_text)
        self.assertIn("Baseline seed files", prompt_text)
        self.assertIn("src/main.py", prompt_text)

    def test_initial_prompt_switches_to_pull_request_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            (repo_root / "src").mkdir()
            messages = build_initial_messages(
                repo_root,
                make_config(),
                {
                    "mode": "pull_request",
                    "number": 14,
                    "title": "Add guard for edge case",
                    "url": "https://example.test/pr/14",
                    "base_ref": "main",
                    "base_sha": "base123",
                    "head_ref": "feature/pr",
                    "head_sha": "head456",
                    "merge_base": "merge789",
                    "commits": [
                        {
                            "sha": "abc123",
                            "date": "2026-05-10",
                            "subject": "adjust handler",
                            "files": ["src/main.py"],
                        }
                    ],
                    "files": ["src/main.py"],
                    "file_changes": [{"status": "M", "path": "src/main.py"}],
                    "patches": [
                        {
                            "status": "M",
                            "path": "src/main.py",
                            "diff": "@@ -1 +1 @@\n-print('old')\n+print('new')",
                            "truncated": False,
                        }
                    ],
                },
            )

        prompt_text = "\n\n".join(message["text"] for message in messages)
        self.assertIn("Pull request review", prompt_text)
        self.assertIn("Pull request changed files", prompt_text)
        self.assertIn("Patch excerpts", prompt_text)
        self.assertIn("Add guard for edge case", prompt_text)
        self.assertIn("src/main.py", prompt_text)


class BaselineFilesTest(unittest.TestCase):
    def test_pick_baseline_files_uses_only_allowed_text_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            (repo_root / "src").mkdir()
            (repo_root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
            (repo_root / "src" / "utils.py").write_text("VALUE = 1\n", encoding="utf-8")
            (repo_root / "README.md").write_text("# demo\n", encoding="utf-8")
            (repo_root / "src" / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

            picked = pick_baseline_files(repo_root, make_config(), sample_size=2)

        self.assertEqual(len(picked), 2)
        self.assertTrue(all(path in {"src/main.py", "src/utils.py", "README.md"} for path in picked))
        self.assertTrue(all(not path.endswith(".png") for path in picked))


class RecentActivityTest(unittest.TestCase):
    @mock.patch("tools.warden.recent_activity.subprocess.run")
    def test_gather_recent_activity_filters_files_by_scope(
        self, run: mock.Mock
    ) -> None:
        run.return_value = mock.Mock(
            returncode=0,
            stdout=(
                "abc123\t2026-05-03\twarden change\n"
                "src/main.py\n"
                "tools/warden/runner.py\n"
                "\n"
                "def456\t2026-05-02\treadme change\n"
                "README.md\n"
            ),
            stderr="",
        )

        result = gather_recent_activity(
            pathlib.Path("."),
            days=7,
            scope=make_config().scope,
        )

        self.assertEqual(result["files"], ["src/main.py", "README.md"])
        self.assertEqual(len(result["commits"]), 2)
        self.assertEqual(result["commits"][0]["files"], ["src/main.py"])
        self.assertEqual(result["commits"][1]["files"], ["README.md"])

    @mock.patch("tools.warden.recent_activity.subprocess.run")
    def test_gather_pull_request_activity_collects_scoped_diff_context(
        self, run: mock.Mock
    ) -> None:
        run.side_effect = [
            mock.Mock(returncode=0, stdout="mergebase123\n", stderr=""),
            mock.Mock(
                returncode=0,
                stdout=(
                    "abc123\t2026-05-10\tadjust handler\n"
                    "src/main.py\n"
                    "tools/warden/runner.py\n"
                ),
                stderr="",
            ),
            mock.Mock(
                returncode=0,
                stdout="M\tsrc/main.py\nD\tREADME.md\n",
                stderr="",
            ),
            mock.Mock(
                returncode=0,
                stdout="diff --git a/src/main.py b/src/main.py\n@@ -1 +1 @@\n-old\n+new\n",
                stderr="",
            ),
            mock.Mock(
                returncode=0,
                stdout="diff --git a/README.md b/README.md\n@@ -1 +0,0 @@\n-# demo\n",
                stderr="",
            ),
        ]

        result = gather_pull_request_activity(
            repo_root=pathlib.Path("."),
            scope=make_config().scope,
            base_ref="main",
            base_sha="base123",
            head_sha="head456",
            patch_line_limit=20,
            metadata={
                "number": 14,
                "title": "Adjust handler",
                "url": "https://example.test/pr/14",
                "head_ref": "feature/pr",
            },
        )

        self.assertEqual(result["mode"], "pull_request")
        self.assertEqual(result["merge_base"], "mergebase123")
        self.assertEqual(result["files"], ["src/main.py", "README.md"])
        self.assertEqual(result["file_changes"][0]["path"], "src/main.py")
        self.assertEqual(result["patches"][0]["path"], "src/main.py")
        self.assertIn("+new", result["patches"][0]["diff"])


class CliReviewModeTest(unittest.TestCase):
    def test_resolve_review_options_uses_pull_request_event_metadata(self) -> None:
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as handle:
            json.dump(
                {
                    "pull_request": {
                        "number": 14,
                        "title": "Adjust handler",
                        "html_url": "https://example.test/pr/14",
                        "base": {"ref": "main", "sha": "base123"},
                        "head": {"ref": "feature/pr", "sha": "head456"},
                    }
                },
                handle,
            )
            handle.flush()
            args = argparse.Namespace(
                mode="auto",
                config="tools/warden/review_config.toml",
                output_dir="tmp/ai-review",
                base_ref=None,
                base_sha=None,
                head_sha=None,
            )

            with mock.patch.dict(
                "os.environ",
                {
                    "GITHUB_EVENT_NAME": "pull_request",
                    "GITHUB_EVENT_PATH": handle.name,
                },
                clear=False,
            ):
                options = resolve_review_options(args)

        self.assertEqual(options["review_mode"], "pull_request")
        self.assertEqual(options["base_sha"], "base123")
        self.assertEqual(options["head_sha"], "head456")
        self.assertEqual(options["pull_request"]["title"], "Adjust handler")


class SchemaFormatTest(unittest.TestCase):
    def test_json_schema_uses_required_variants(self) -> None:
        schema = build_json_schema()["schema"]
        variants = schema["oneOf"]

        self.assertEqual(len(variants), 2)
        self.assertEqual(
            variants[0]["required"],
            ["action", "tool_name", "arguments"],
        )
        self.assertEqual(
            variants[1]["required"],
            ["action", "report_markdown"],
        )


@unittest.skipIf(YandexClient is None, "openai is not installed")
class YandexClientTest(unittest.TestCase):
    @mock.patch("tools.warden.yandex_client.OpenAI")
    def test_complete_accepts_openai_response_payload(
        self, openai_client: mock.Mock
    ) -> None:
        response = mock.Mock()
        response.output_text = '{"action":"final_report","report_markdown":"ok"}'
        response.status = "completed"
        response.id = "resp_123"
        response.usage = mock.Mock()
        response.usage.model_dump.return_value = {"total_tokens": 1}
        openai_client.return_value.responses.create.return_value = response

        client = YandexClient(
            api_key="key",
            folder_id="folder",
            model_uri="gpt://folder/yandexgpt-lite",
            config=make_config(),
        )
        result = client.complete([{"role": "user", "text": "test"}])

        self.assertEqual(result["action"]["action"], "final_report")
        self.assertEqual(
            result["raw_response"]["alternatives"][0]["status"],
            "completed",
        )


if __name__ == "__main__":
    unittest.main()
