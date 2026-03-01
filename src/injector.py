"""
Text injection — paste at cursor with clipboard fallback.

Uses platform-specific keyboard simulation to paste text into the
currently focused application. Falls back to clipboard-only mode
if no editable field is detected.
"""

from __future__ import annotations

import logging
import platform
import time

import pyperclip

logger = logging.getLogger(__name__)

_SYSTEM = platform.system()


def inject_text(text: str) -> bool:
    """
    Attempt to paste text at the current cursor position.

    Strategy:
        1. Save the current clipboard contents.
        2. Copy our text to the clipboard.
        3. Simulate Cmd+V (macOS) or Ctrl+V (Windows/Linux).
        4. Restore the original clipboard after a short delay.

    If simulation fails (e.g., no focused text field), the text remains
    on the clipboard and the function returns False.

    Args:
        text: The string to inject.

    Returns:
        True if the paste simulation was executed, False on fallback.
    """
    if not text:
        logger.warning("inject_text called with empty string.")
        return False

    # Save original clipboard
    try:
        original_clipboard = pyperclip.paste()
    except pyperclip.PyperclipException:
        original_clipboard = None

    # Place our text on the clipboard
    pyperclip.copy(text)
    logger.info("Text copied to clipboard (%d chars).", len(text))

    # Simulate paste keystroke
    pasted = _simulate_paste()

    if pasted:
        # Restore original clipboard after a brief delay to allow the
        # paste event to be processed by the target application.
        time.sleep(0.15)
        if original_clipboard is not None:
            try:
                pyperclip.copy(original_clipboard)
            except pyperclip.PyperclipException:
                pass
        logger.info("Text injected via simulated paste.")
    else:
        # Leave the text on the clipboard as fallback
        logger.info("Paste simulation failed; text remains on clipboard.")

    return pasted


def _simulate_paste() -> bool:
    """
    Simulate a Ctrl+V / Cmd+V keystroke.

    Returns:
        True if the simulation was dispatched without error.
    """
    try:
        from pynput.keyboard import Controller, Key

        keyboard = Controller()

        if _SYSTEM == "Darwin":
            # macOS uses Command key
            keyboard.press(Key.cmd)
            keyboard.press("v")
            keyboard.release("v")
            keyboard.release(Key.cmd)
        else:
            # Windows and Linux use Ctrl key
            keyboard.press(Key.ctrl)
            keyboard.press("v")
            keyboard.release("v")
            keyboard.release(Key.ctrl)

        return True
    except Exception as exc:
        logger.error("Failed to simulate paste keystroke: %s", exc)
        return False


def copy_to_clipboard(text: str) -> None:
    """Explicitly copy text to the system clipboard."""
    pyperclip.copy(text)
    logger.info("Text explicitly copied to clipboard (%d chars).", len(text))