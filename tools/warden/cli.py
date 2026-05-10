import argparse
import json
import os
import pathlib
import sys
from typing import Any

from tools.warden.config import load_config
from tools.warden.exceptions import ReviewError
from tools.warden.paths import repo_root_from_script


DEFAULT_OUTPUT_DIR = pathlib.Path("tmp/ai-review")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run weekly AI code review via Yandex AI Studio."
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "repository", "pull_request"),
        default="auto",
        help="Review mode. Auto switches to pull_request on GitHub PR events.",
    )
    parser.add_argument(
        "--config",
        default="tools/warden/review_config.toml",
        help="Path to the AI review configuration file.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where report artifacts will be written.",
    )
    parser.add_argument(
        "--base-ref",
        help="Base branch or ref for pull request review.",
    )
    parser.add_argument(
        "--base-sha",
        help="Base commit SHA for pull request review.",
    )
    parser.add_argument(
        "--head-sha",
        help="Head commit SHA for pull request review. Defaults to GITHUB_SHA or HEAD.",
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

    review_options = resolve_review_options(args)
    config = load_config(config_path)
    from tools.warden.runner import run_review

    result = run_review(
        repo_root=repo_root,
        output_dir=output_dir,
        config=config,
        api_key=api_key,
        folder_id=folder_id,
        review_mode=review_options["review_mode"],
        base_ref=review_options["base_ref"],
        base_sha=review_options["base_sha"],
        head_sha=review_options["head_sha"],
        pull_request=review_options["pull_request"],
    )
    print(f"Report written to {result['report_path']}")
    print(f"Session written to {result['session_path']}")
    return 0


def load_github_pull_request_metadata() -> dict[str, Any]:
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_name not in {"pull_request", "pull_request_target"} or not event_path:
        return {}

    payload_path = pathlib.Path(event_path)
    if not payload_path.exists():
        return {}

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return {}

    base = pull_request.get("base") or {}
    head = pull_request.get("head") or {}
    return {
        "number": pull_request.get("number"),
        "title": pull_request.get("title"),
        "url": pull_request.get("html_url"),
        "base_ref": base.get("ref"),
        "base_sha": base.get("sha"),
        "head_ref": head.get("ref"),
        "head_sha": head.get("sha"),
    }


def resolve_review_options(args: argparse.Namespace) -> dict[str, Any]:
    pull_request = load_github_pull_request_metadata()
    has_pull_request_context = bool(
        args.base_ref
        or args.base_sha
        or os.environ.get("GITHUB_BASE_REF")
        or pull_request
    )

    review_mode = args.mode
    if review_mode == "auto":
        review_mode = "pull_request" if has_pull_request_context else "repository"

    base_ref = args.base_ref or pull_request.get("base_ref") or os.environ.get(
        "GITHUB_BASE_REF"
    )
    base_sha = args.base_sha or pull_request.get("base_sha")
    head_sha = (
        args.head_sha
        or pull_request.get("head_sha")
        or os.environ.get("GITHUB_SHA")
        or "HEAD"
    )

    if review_mode == "pull_request" and not (base_ref or base_sha):
        raise ReviewError(
            "pull_request review requires --base-ref, --base-sha, or GitHub PR metadata"
        )

    if review_mode == "pull_request":
        return {
            "review_mode": review_mode,
            "base_ref": base_ref,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "pull_request": pull_request,
        }

    return {
        "review_mode": review_mode,
        "base_ref": None,
        "base_sha": None,
        "head_sha": None,
        "pull_request": {},
    }
