"""
Main application orchestrator.

Bootstraps all components (audio, transcriber, rewriter, hotkeys, overlay,
tray) and wires them together. Processing runs in background threads to
keep the UI responsive.
"""

from __future__ import annotations

import logging
import sys
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from voxscribe.audio import AudioRecorder
from voxscribe.config import AppConfig
from voxscribe.hotkeys import HotkeyManager
from voxscribe.injector import inject_text
from voxscribe.overlay import OverlayWidget
from voxscribe.rewriter import OllamaRewriter
from voxscribe.transcriber import Transcriber
from voxscribe.tray import TrayIcon

logger = logging.getLogger(__name__)


class _Signals(QObject):
    """
    Qt signal bridge.

    Hotkey callbacks run on pynput's listener thread, but UI updates
    must happen on the main Qt thread. These signals cross the boundary.
    """

    show_recording = Signal()
    show_transcribing = Signal()
    show_rewriting = Signal()
    show_done = Signal()
    show_error = Signal(str)
    update_tray_status = Signal(str)
    update_tray_text = Signal(str)


class VoxScribeApp:
    """Top-level application controller."""

    def __init__(self, argv: list[str]) -> None:
        # ── Qt Application ────────────────────────────────────────────
        self._qapp = QApplication(argv)
        self._qapp.setQuitOnLastWindowClosed(False)  # We're a tray app
        self._qapp.setApplicationName("VoxScribe")

        # ── Configuration ─────────────────────────────────────────────
        self._config = AppConfig.load()

        # ── Logging ───────────────────────────────────────────────────
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

        # ── Signals ───────────────────────────────────────────────────
        self._signals = _Signals()

        # ── Core Components ───────────────────────────────────────────
        self._recorder = AudioRecorder(self._config.audio)
        self._transcriber = Transcriber(self._config.whisper)
        self._rewriter = OllamaRewriter(self._config.ollama)

        # ── UI Components ─────────────────────────────────────────────
        self._overlay = OverlayWidget()
        self._tray = TrayIcon(self._qapp, self._config.ollama)

        # ── Wire signals to UI slots ──────────────────────────────────
        self._signals.show_recording.connect(self._overlay.show_recording)
        self._signals.show_transcribing.connect(self._overlay.show_transcribing)
        self._signals.show_rewriting.connect(self._overlay.show_rewriting)
        self._signals.show_done.connect(self._overlay.show_done)
        self._signals.show_error.connect(self._overlay.show_error)
        self._signals.update_tray_status.connect(self._tray.set_status)
        self._signals.update_tray_text.connect(self._tray.set_last_text)

        # ── Hotkeys ───────────────────────────────────────────────────
        self._hotkey_manager = HotkeyManager()

        # State tracking: are we currently in a recording session?
        self._active_mode: str | None = None  # "transcribe" or "smart_write"
        self._processing_lock = threading.Lock()

    def run(self) -> int:
        """Start the application and enter the Qt event loop."""
        logger.info("VoxScribe v%s starting...", "0.1.0")

        # Check Ollama availability
        ollama_ok = self._rewriter.is_available()
        self._tray.set_ollama_status(ollama_ok)

        # Register hotkeys
        self._hotkey_manager.register(
            self._config.hotkeys.transcribe, self._on_transcribe_hotkey
        )
        self._hotkey_manager.register(
            self._config.hotkeys.smart_write, self._on_smart_write_hotkey
        )
        self._hotkey_manager.start()

        # Show tray icon
        self._tray.show()
        self._tray.set_status("Idle")
        self._tray.showMessage(
            "VoxScribe",
            f"Ready. Transcribe: {self._config.hotkeys.transcribe} | "
            f"Smart Write: {self._config.hotkeys.smart_write}",
            TrayIcon.MessageIcon.Information,
            3000,
        )

        logger.info("Application ready. Entering event loop.")
        return self._qapp.exec()

    # ── Hotkey Callbacks ──────────────────────────────────────────────

    def _on_transcribe_hotkey(self) -> None:
        """Toggle recording for plain transcription."""
        self._toggle_recording("transcribe")

    def _on_smart_write_hotkey(self) -> None:
        """Toggle recording for Smart Write (transcribe → rewrite)."""
        self._toggle_recording("smart_write")

    def _toggle_recording(self, mode: str) -> None:
        """
        Start or stop recording depending on the current state.

        First press starts recording; second press stops recording
        and triggers processing.
        """
        if self._recorder.is_recording:
            # Stop recording and process
            logger.info("Hotkey pressed — stopping recording (mode=%s).", mode)
            audio = self._recorder.stop()

            if audio.size == 0:
                self._signals.show_error.emit("No audio captured.")
                return

            # Process in a background thread
            thread = threading.Thread(
                target=self._process_audio, args=(audio, mode), daemon=True
            )
            thread.start()
        else:
            if not self._processing_lock.acquire(blocking=False):
                logger.info("Processing in progress — ignoring hotkey.")
                return
            self._processing_lock.release()

            self._active_mode = mode
            self._recorder.start()
            self._signals.show_recording.emit()
            self._signals.update_tray_status.emit("Recording...")
            logger.info("Hotkey pressed — recording started (mode=%s).", mode)

    def _process_audio(self, audio, mode: str) -> None:
        """
        Run transcription (and optional rewriting) in a background thread.

        All UI updates go through Qt signals to remain thread-safe.
        """
        with self._processing_lock:
            try:
                # ── Step 1: Transcribe ────────────────────────────────
                self._signals.show_transcribing.emit()
                self._signals.update_tray_status.emit("Transcribing...")

                text = self._transcriber.transcribe(audio)

                if not text:
                    self._signals.show_error.emit("No speech detected.")
                    self._signals.update_tray_status.emit("Idle")
                    return

                # ── Step 2: Rewrite (Smart Write mode only) ───────────
                if mode == "smart_write":
                    if self._rewriter.is_available():
                        self._signals.show_rewriting.emit()
                        self._signals.update_tray_status.emit("Rewriting...")
                        text = self._rewriter.rewrite(text)
                    else:
                        logger.warning(
                            "Ollama unavailable — skipping rewrite, using raw transcript."
                        )

                # ── Step 3: Inject ────────────────────────────────────
                pasted = inject_text(text)

                self._signals.update_tray_text.emit(text)

                if pasted:
                    self._signals.show_done.emit()
                else:
                    # Fallback: text is on clipboard, show in tray
                    self._signals.show_done.emit()
                    self._tray.showMessage(
                        "VoxScribe",
                        "Text copied to clipboard (no active text field detected).",
                        TrayIcon.MessageIcon.Information,
                        2500,
                    )

                self._signals.update_tray_status.emit("Idle")

            except Exception as exc:
                logger.exception("Processing failed: %s", exc)
                self._signals.show_error.emit(f"Error: {exc}")
                self._signals.update_tray_status.emit("Error")