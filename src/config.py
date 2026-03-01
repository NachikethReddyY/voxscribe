"""
Configuration management for VoxScribe.

Reads from a TOML settings file and provides typed access to all
configuration values with sensible defaults.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w


def _default_settings_path() -> Path:
    """Resolve the settings.toml path relative to the project root."""
    # When running from source: project_root/settings.toml
    # When installed: ~/.config/voxscribe/settings.toml
    local = Path.cwd() / "settings.toml"
    if local.exists():
        return local
    config_dir = Path.home() / ".config" / "voxscribe"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.toml"


@dataclass
class WhisperConfig:
    model_path: str = "base.en"
    device: str = "auto"
    compute_type: str = "int8"
    language: str = "en"


@dataclass
class OllamaConfig:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.1:8b"
    timeout_seconds: int = 60
    system_prompt: str = (
        "You are a writing assistant. Rewrite the following transcribed speech "
        "into clear, well-structured prose. Preserve the original meaning and tone. "
        "Fix grammar, remove filler words, and improve clarity. "
        "Return ONLY the rewritten text."
    )


@dataclass
class HotkeyConfig:
    transcribe: str = "<ctrl>+<shift>+s"
    smart_write: str = "<ctrl>+<shift>+d"


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class AppConfig:
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    _path: Path = field(default_factory=_default_settings_path, repr=False)

    @classmethod
    def load(cls, path: Path | None = None) -> AppConfig:
        """Load configuration from a TOML file, falling back to defaults."""
        resolved_path = path or _default_settings_path()
        config = cls(_path=resolved_path)

        if resolved_path.exists():
            with open(resolved_path, "rb") as f:
                data: dict[str, Any] = tomllib.load(f)

            if "whisper" in data:
                for key, value in data["whisper"].items():
                    if hasattr(config.whisper, key):
                        setattr(config.whisper, key, value)

            if "ollama" in data:
                for key, value in data["ollama"].items():
                    if hasattr(config.ollama, key):
                        setattr(config.ollama, key, value)

            if "hotkeys" in data:
                for key, value in data["hotkeys"].items():
                    if hasattr(config.hotkeys, key):
                        setattr(config.hotkeys, key, value)

            if "audio" in data:
                for key, value in data["audio"].items():
                    if hasattr(config.audio, key):
                        setattr(config.audio, key, value)
        else:
            # Write default config so the user has a template to edit
            config.save()

        return config

    def save(self) -> None:
        """Persist the current configuration to the TOML file."""
        data = {
            "whisper": {
                "model_path": self.whisper.model_path,
                "device": self.whisper.device,
                "compute_type": self.whisper.compute_type,
                "language": self.whisper.language,
            },
            "ollama": {
                "base_url": self.ollama.base_url,
                "model": self.ollama.model,
                "timeout_seconds": self.ollama.timeout_seconds,
                "system_prompt": self.ollama.system_prompt,
            },
            "hotkeys": {
                "transcribe": self.hotkeys.transcribe,
                "smart_write": self.hotkeys.smart_write,
            },
            "audio": {
                "sample_rate": self.audio.sample_rate,
                "channels": self.audio.channels,
            },
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "wb") as f:
            tomli_w.dump(data, f)