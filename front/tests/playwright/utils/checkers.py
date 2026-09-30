"""Re-export of the Selenium suite's network comparator.

``TestNetworkComparator`` compares plain dicts read out of the page's JS state
and never touches a driver, so both suites share one implementation.
"""

import importlib.util
import sys
from pathlib import Path

_SOURCE = Path(__file__).resolve().parents[2] / "utils" / "checkers.py"

_spec = importlib.util.spec_from_file_location("_selenium_checkers", _SOURCE)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
sys.modules["_selenium_checkers"] = _module
_spec.loader.exec_module(_module)

TestNetworkComparator = _module.TestNetworkComparator

__all__ = ["TestNetworkComparator"]
