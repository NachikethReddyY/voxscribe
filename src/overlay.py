"""
Floating overlay widget — recording indicator and progress display.

A frameless, translucent, always-on-top window that appears during
recording and processing, then fades away when complete.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QWidget,
)

logger = logging.getLogger(__name__)


class OverlayWidget(QWidget):
    """
    A floating status overlay displayed during recording and processing.

    Visual states:
        - RECORDING: Pulsing red dot + "Recording..."
        - TRANSCRIBING: Progress bar + "Transcribing..."
        - REWRITING: Progress bar + "Smart Write..."
        - DONE: Brief "Done" flash, then auto-hide.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # ── Window flags ──────────────────────────────────────────────
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # Keeps it out of the taskbar / dock
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 60)

        # ── Opacity animation for fade-in / fade-out ──────────────────
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(200)

        # ── Layout ────────────────────────────────────────────────────
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        self._status_label = QLabel("Ready")
        self._status_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self._status_label.setStyleSheet("color: #FFFFFF;")

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(120)
        self._progress_bar.setRange(0, 0)  # Indeterminate mode
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #555;
                border-radius: 6px;
                background-color: #2B2B2B;
                height: 12px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
            """
        )

        layout.addWidget(self._status_label)
        layout.addWidget(self._progress_bar)

        # Background styling
        self.setStyleSheet(
            """
            OverlayWidget {
                background-color: rgba(30, 30, 30, 220);
                border-radius: 12px;
            }
            """
        )

        # ── Auto-hide timer ──────────────────────────────────────────
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide_overlay)

    def _position_on_screen(self) -> None:
        """Place the overlay at the top-center of the primary screen."""
        from PySide6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + 40  # Slight offset below the top edge
        self.move(x, y)

    def show_overlay(self, status: str, show_progress: bool = False) -> None:
        """Display the overlay with the given status text."""
        self._auto_hide_timer.stop()
        self._status_label.setText(status)
        self._progress_bar.setVisible(show_progress)
        self._position_on_screen()

        if not self.isVisible():
            self.show()

        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.95)
        self._fade_anim.start()

        logger.debug("Overlay shown: '%s'", status)

    def show_recording(self) -> None:
        self.show_overlay("🔴  Recording...", show_progress=False)

    def show_transcribing(self) -> None:
        self.show_overlay("📝  Transcribing...", show_progress=True)

    def show_rewriting(self) -> None:
        self.show_overlay("✨  Smart Write...", show_progress=True)

    def show_done(self, auto_hide_ms: int = 1500) -> None:
        """Flash a 'Done' message and auto-hide after a delay."""
        self.show_overlay("✅  Done!", show_progress=False)
        self._auto_hide_timer.start(auto_hide_ms)

    def show_error(self, message: str, auto_hide_ms: int = 3000) -> None:
        self.show_overlay(f"❌  {message}", show_progress=False)
        self._auto_hide_timer.start(auto_hide_ms)

    def hide_overlay(self) -> None:
        """Fade out and hide the overlay."""
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_out_finished)
        self._fade_anim.start()

    def _on_fade_out_finished(self) -> None:
        if self._opacity_effect.opacity() < 0.05:
            self.hide()
        # Disconnect to avoid stacking connections
        try:
            self._fade_anim.finished.disconnect(self._on_fade_out_finished)
        except RuntimeError:
            pass