from pathlib import Path

import pytest

from tuneup_alpha.config import ConfigError, ConfigRepository, sample_config
from tuneup_alpha.models import AppConfig


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    config = repo.load()
    assert isinstance(config, AppConfig)
    assert not config.zones


def test_save_and_reload_roundtrip(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    original = sample_config()
    repo.save(original)

    loaded = repo.load()
    assert loaded.zones[0].name == "example.com"
    assert len(loaded.zones[0].records) == 2


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    target = tmp_path / "config.yaml"
    target.write_text(": not-valid")
    repo = ConfigRepository(target)
    with pytest.raises(ConfigError):
        repo.load()
