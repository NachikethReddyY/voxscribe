"""
System tray icon and menu.

Provides the persistent tray/menu-bar presence for VoxScribe, with
menu entries for settings, status, and quit.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

    from voxscribe.config import OllamaConfig

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


class TrayIcon(QSystemTrayIcon):
    """System tray icon with context menu for VoxScribe."""

    def __init__(self, app: QApplication, ollama_config: OllamaConfig) -> None:
        icon_path = _ASSETS_DIR / "icon.png"
        if icon_path.exists():
            icon = QIcon(str(icon_path))
        else:
            # Fallback: use a built-in icon so the tray entry is visible
            from PySide6.QtWidgets import QStyle

            icon = app.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)
            logger.warning("Icon not found at %s; using fallback.", icon_path)

        super().__init__(icon, app)
        self._app = app
        self._ollama_config = ollama_config
        self._last_text: str = ""

        # ── Context Menu ──────────────────────────────────────────────
        menu = QMenu()

        self._status_action = QAction("VoxScribe — Idle")
        self._status_action.setEnabled(False)
        menu.addAction(self._status_action)

        menu.addSeparator()

        self._preview_action = QAction("No recent text")
        self._preview_action.setEnabled(False)
        self._preview_action.triggered.connect(self._copy_last_text)
        menu.addAction(self._preview_action)

        menu.addSeparator()

        self._ollama_status = QAction("Ollama: checking...")
        self._ollama_status.setEnabled(False)
        menu.addAction(self._ollama_status)

        menu.addSeparator()

        quit_action = QAction("Quit VoxScribe")
        quit_action.triggered.connect(app.quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.setToolTip("VoxScribe — Speech to Text")

    def set_status(self, status: str) -> None:
        self._status_action.setText(f"VoxScribe — {status}")

    def set_ollama_status(self, available: bool) -> None:
        status = "Ollama: ✅ Connected" if available else "Ollama: ❌ Not detected"
        self._ollama_status.setText(status)

    def set_last_text(self, text: str) -> None:
        """Update the tray menu preview with the most recent output."""
        self._last_text = text
        preview = text[:80] + "..." if len(text) > 80 else text
        self._preview_action.setText(preview)
        self._preview_action.setEnabled(True)

    def _copy_last_text(self) -> None:
        """Copy the last result to clipboard when the user clicks the preview."""
        if self._last_text:
            from voxscribe.injector import copy_to_clipboard

            copy_to_clipboard(self._last_text)
            self.showMessage(
                "VoxScribe", "Text copied to clipboard.", QSystemTrayIcon.MessageIcon.Information, 2000
            )