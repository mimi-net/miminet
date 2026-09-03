"""Browser-free regression tests for MiminetTester log helpers.

``MiminetTester.get_logs`` runs the Selenium ``GET_LOG`` wire command directly
because the remote WebDriver has no ``get_log`` in Selenium 4 (only
``ChromiumDriver`` does). These tests stub ``execute`` so the wire path and its
filtering are verified without a browser or a running grid. This locks in the
latent-bug fix from #486 where the helper called the non-existent
``self.get_log`` on a remote session.
"""

from selenium.webdriver.remote.command import Command

from conftest import MiminetTester


class _StubLogTester(MiminetTester):
    """MiminetTester whose ``execute`` returns canned browser-log entries."""

    def __init__(self, entries: list):
        self.entries = entries
        self.calls: list = []

    def execute(self, driver_command, params=None):
        self.calls.append((driver_command, params))
        return {"value": self.entries}


def test_get_logs_issues_browser_log_command():
    entries = [{"message": "m", "source": "console-api", "level": "INFO"}]
    tester = _StubLogTester(entries)

    assert tester.get_logs() == entries
    assert tester.calls == [(Command.GET_LOG, {"type": "browser"})]


def test_get_logs_returns_empty_list_when_no_entries():
    tester = _StubLogTester([])

    assert tester.get_logs() == []


def test_get_logs_filters_entries():
    entries = [
        {"message": "keep", "source": "console-api", "level": "INFO"},
        {"message": "drop", "source": "network", "level": "WARNING"},
    ]
    tester = _StubLogTester(entries)

    kept = tester.get_logs(lambda log: log["source"] == "console-api")
    assert kept == [entries[0]]


def test_get_console_messages_returns_only_info_console_entries():
    entries = [
        {"message": "a", "source": "console-api", "level": "INFO"},
        {"message": "b", "source": "console-api", "level": "WARNING"},
        {"message": "c", "source": "network", "level": "INFO"},
    ]
    tester = _StubLogTester(entries)

    assert list(tester.get_console_messages()) == ["a"]
