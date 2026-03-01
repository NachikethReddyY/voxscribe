"""
Global hotkey listener.

Registers system-wide keyboard shortcuts using pynput. Each hotkey
is parsed from a string representation (e.g., "<ctrl>+<shift>+s")
and mapped to a callback function.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyManager:
    """
    Manages global hotkey registration and dispatching.

    Hotkeys are registered as string combos like ``<ctrl>+<shift>+s``
    and mapped to zero-argument callables.
    """

    def __init__(self) -> None:
        self._hotkeys: dict[str, Callable[[], None]] = {}
        self._listener: keyboard.GlobalHotKeys | None = None
        self._thread: threading.Thread | None = None

    def register(self, combo: str, callback: Callable[[], None]) -> None:
        """
        Register a hotkey combination.

        Args:
            combo: Hotkey string, e.g. ``"<ctrl>+<shift>+s"``.
            callback: Function to invoke when the hotkey is pressed.
        """
        self._hotkeys[combo] = callback
        logger.info("Registered hotkey: %s", combo)

    def start(self) -> None:
        """
        Start listening for all registered hotkeys in a background thread.

        The listener runs as a daemon thread so it won't block application
        shutdown.
        """
        if not self._hotkeys:
            logger.warning("No hotkeys registered. Listener not started.")
            return

        if self._listener is not None:
            logger.warning("Hotkey listener already running.")
            return

        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.daemon = True
        self._listener.start()
        logger.info(
            "Global hotkey listener started with %d binding(s).", len(self._hotkeys)
        )

    def stop(self) -> None:
        """Stop the hotkey listener."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            logger.info("Global hotkey listener stopped.")