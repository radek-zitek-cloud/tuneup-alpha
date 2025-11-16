"""Configuration loading and persistence helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import AppConfig, Record, Zone


class ConfigError(RuntimeError):
    """Raised when the configuration file cannot be parsed or updated."""


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

    def add_zone(self, zone: Zone, overwrite: bool = False) -> AppConfig:
        """Persist a new zone, optionally overwriting existing entries."""

        config = self.load()
        existing_index = next(
            (index for index, existing in enumerate(config.zones) if existing.name == zone.name),
            None,
        )

        if existing_index is not None and not overwrite:
            raise ConfigError(
                f"Zone '{zone.name}' already exists. Use overwrite=True to replace it."
            )

        if existing_index is None:
            config.zones.append(zone)
        else:
            config.zones[existing_index] = zone

        self.save(config)
        return config

    def delete_zone(self, name: str) -> AppConfig:
        """Remove a zone by name and persist the updated configuration."""

        config = self.load()
        index = next((i for i, zone in enumerate(config.zones) if zone.name == name), None)
        if index is None:
            raise ConfigError(f"Zone '{name}' was not found.")
        del config.zones[index]
        self.save(config)
        return config

    def update_zone(self, original_name: str, updated: Zone) -> AppConfig:
        """Update an existing zone, optionally renaming it, and persist to disk."""

        config = self.load()
        current_index = next(
            (i for i, zone in enumerate(config.zones) if zone.name == original_name),
            None,
        )
        if current_index is None:
            raise ConfigError(f"Zone '{original_name}' was not found.")

        conflict_index = next(
            (i for i, zone in enumerate(config.zones) if zone.name == updated.name),
            None,
        )
        if conflict_index is not None and conflict_index != current_index:
            raise ConfigError(f"Zone '{updated.name}' already exists. Choose a different name.")

        config.zones[current_index] = updated
        self.save(config)
        return config


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
                    Record(label="mail", type="A", value="198.51.100.20", ttl=300),
                ],
            )
        ]
    )


def load_config(path: Path | None = None) -> AppConfig:
    """Helper to read configuration using a single call."""

    repo = ConfigRepository(path)
    return repo.load()
