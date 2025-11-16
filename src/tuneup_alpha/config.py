"""Configuration loading and persistence helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import AppConfig, Record, Zone


class ConfigError(RuntimeError):
    """Raised when the configuration file cannot be parsed."""


def default_config_path() -> Path:
    """Return the default config location following the XDG spec."""

    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "tuneup-alpha" / "config.yaml"


class ConfigRepository:
    """Handles reading and writing the TuneUp Alpha configuration file."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path else default_config_path()
        self.path = Path(self.path)

    def load(self) -> AppConfig:
        """Parse configuration from disk or return an empty config."""

        if not self.path.exists():
            return AppConfig()

        try:
            payload: Any = yaml.safe_load(self.path.read_text()) or {}
        except yaml.YAMLError as exc:  # pragma: no cover - yaml error path
            raise ConfigError(f"Failed to parse YAML at {self.path}") from exc

        try:
            return AppConfig.model_validate(payload)
        except ValidationError as exc:
            raise ConfigError(f"Invalid configuration detected: {exc}") from exc

    def save(self, config: AppConfig) -> None:
        """Write configuration data to disk."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = config.model_dump(mode="json")
        yaml_str = yaml.safe_dump(data, sort_keys=False)
        self.path.write_text(yaml_str)

    def ensure_sample(self, overwrite: bool = False) -> Path:
        """Create a sample config file, optionally overwriting an existing one."""

        if self.path.exists() and not overwrite:
            return self.path

        sample = sample_config()
        self.save(sample)
        return self.path


def sample_config() -> AppConfig:
    """Return an AppConfig populated with a default example."""

    return AppConfig(
        zones=[
            Zone(
                name="example.com",
                server="ns1.example.com",
                key_file=Path("/etc/nsupdate/example.com.key"),
                notes="Sandbox zone used for demonstrating TuneUp Alpha.",
                records=[
                    Record(label="@", type="A", value="198.51.100.10", ttl=600),
                    Record(label="www", type="CNAME", value="@", ttl=300),
                ],
            )
        ]
    )


def load_config(path: Path | None = None) -> AppConfig:
    """Helper to read configuration using a single call."""

    repo = ConfigRepository(path)
    return repo.load()
