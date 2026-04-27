import os


def safe_subprocess_env() -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_TERMINAL_PROMPT": "0",
    }
    for key in ("TMPDIR", "RUNNER_TEMP"):
        if os.environ.get(key):
            env[key] = os.environ[key]
    return env
