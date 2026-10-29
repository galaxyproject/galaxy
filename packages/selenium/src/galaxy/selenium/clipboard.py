"""Observe text the Galaxy client copies to the clipboard during browser tests."""

from collections.abc import Callable
from typing import (
    Any,
    Protocol,
)

from galaxy.util.wait import wait_on

INSTALL_RECORDER_SCRIPT = """
window.__galaxyCopiedText = null;
Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: {
        writeText: (text) => {
            window.__galaxyCopiedText = text;
            return Promise.resolve();
        },
    },
});
"""
READ_RECORDER_SCRIPT = "return window.__galaxyCopiedText;"
# Dropping the own property re-exposes the browser's navigator.clipboard.
REMOVE_RECORDER_SCRIPT = "delete navigator.clipboard;"


class ClipboardCapture(Protocol):
    """Text copied to the clipboard while a capture is active."""

    def wait_for_text(self) -> str:
        """Wait for the page to copy text and return the most recent copy."""
        ...


class RecordedClipboard:
    """Swap ``navigator.clipboard`` for a recorder that keeps whatever the page writes.

    Reading the real system clipboard needs backend-specific permission grants and is
    unreliable headless; the recorder behaves the same under Selenium and Playwright.
    """

    def __init__(self, execute_script: Callable[..., Any], timeout: float):
        self._execute_script = execute_script
        self._timeout = timeout

    def __enter__(self) -> "RecordedClipboard":
        self._execute_script(INSTALL_RECORDER_SCRIPT)
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._execute_script(REMOVE_RECORDER_SCRIPT)

    def wait_for_text(self) -> str:
        text: str = wait_on(
            lambda: self._execute_script(READ_RECORDER_SCRIPT),
            "text to be copied to the clipboard",
            self._timeout,
        )
        return text
