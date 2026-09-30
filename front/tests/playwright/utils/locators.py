"""Re-export of the Selenium suite's locators.

A locator carries no driver-specific state -- ``Locator`` holds a CSS selector,
an xpath and a text, and ``By`` never appears in that module -- so the file is
shared rather than duplicated. Keeping one copy means a selector that changes
with the UI is fixed once for both suites.
"""

import importlib.util
import sys
from pathlib import Path

_SOURCE = Path(__file__).resolve().parents[2] / "utils" / "locators.py"

_spec = importlib.util.spec_from_file_location("_selenium_locators", _SOURCE)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
sys.modules["_selenium_locators"] = _module
_spec.loader.exec_module(_module)

Location = _module.Location
Locator = _module.Locator
DeviceLocator = _module.DeviceLocator

__all__ = ["Location", "Locator", "DeviceLocator"]
