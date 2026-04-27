import argparse
import os
import pathlib
import sys

from tools.ai_review.config import load_config
from tools.ai_review.exceptions import ReviewError
from tools.ai_review.paths import repo_root_from_script
from tools.ai_review.runner import run_review


DEFAULT_OUTPUT_DIR = pathlib.Path("tmp/ai-review")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run weekly AI code review via Yandex AI Studio."
    )
    parser.add_argument(
        "--config",
        default="tools/ai_review/review_config.toml",
        help="Path to the AI review configuration file.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where report artifacts will be written.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        return run_from_args(parse_args())
    except ReviewError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def run_from_args(args: argparse.Namespace) -> int:
    repo_root = repo_root_from_script()
    config_path = (repo_root / args.config).resolve()
    output_dir = (repo_root / args.output_dir).resolve()

    if not config_path.exists():
        raise ReviewError(f"config file not found: {config_path}")

    api_key = os.environ.get("YANDEX_API_KEY")
    folder_id = os.environ.get("YANDEX_FOLDER_ID")
    if not api_key:
        raise ReviewError("YANDEX_API_KEY is not set")
    if not folder_id:
        raise ReviewError("YANDEX_FOLDER_ID is not set")

    config = load_config(config_path)
    result = run_review(
        repo_root=repo_root,
        output_dir=output_dir,
        config=config,
        api_key=api_key,
        folder_id=folder_id,
    )
    print(f"Report written to {result['report_path']}")
    print(f"Session written to {result['session_path']}")
    return 0
