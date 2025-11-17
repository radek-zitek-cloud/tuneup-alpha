from pathlib import Path

import pytest

from tuneup_alpha.config import ConfigError, ConfigRepository, sample_config
from tuneup_alpha.models import AppConfig, Zone


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
    assert len(loaded.zones[0].records) == 3


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    target = tmp_path / "config.yaml"
    target.write_text(": not-valid")
    repo = ConfigRepository(target)
    with pytest.raises(ConfigError):
        repo.load()


def test_add_zone_persists_new_entry(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    zone = Zone(
        name="example.org",
        server="ns1.example.org",
        key_file=tmp_path / "example.key",
    )
    config = repo.add_zone(zone)
    assert any(z.name == "example.org" for z in config.zones)


def test_add_zone_rejects_duplicates(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    zone = Zone(
        name="example.org",
        server="ns1.example.org",
        key_file=tmp_path / "example.key",
    )
    repo.add_zone(zone)
    with pytest.raises(ConfigError):
        repo.add_zone(zone)


def test_delete_zone_removes_entry(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    zone = Zone(
        name="example.org",
        server="ns1.example.org",
        key_file=tmp_path / "example.key",
    )
    repo.add_zone(zone)
    config = repo.delete_zone("example.org")
    assert all(z.name != "example.org" for z in config.zones)


def test_delete_zone_missing_raises(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    with pytest.raises(ConfigError):
        repo.delete_zone("not-there")


def test_update_zone_changes_server(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    zone = Zone(
        name="example.org",
        server="ns1.example.org",
        key_file=tmp_path / "example.key",
    )
    repo.add_zone(zone)
    updated = zone.model_copy(update={"server": "ns2.example.org"})
    config = repo.update_zone("example.org", updated)
    assert config.zones[0].server == "ns2.example.org"


def test_update_zone_rename_conflict(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    repo.add_zone(
        Zone(
            name="example.org",
            server="ns1.example.org",
            key_file=tmp_path / "example.key",
        )
    )
    repo.add_zone(
        Zone(
            name="example.net",
            server="ns1.example.net",
            key_file=tmp_path / "example-net.key",
        )
    )
    with pytest.raises(ConfigError):
        repo.update_zone(
            "example.org",
            Zone(
                name="example.net",
                server="ns2.example.net",
                key_file=tmp_path / "example.key",
            ),
        )


def test_config_with_prefix_key_path(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    config = AppConfig(prefix_key_path="/custom/keys")
    repo.save(config)

    loaded = repo.load()
    assert loaded.prefix_key_path == "/custom/keys"


def test_config_default_prefix_key_path(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    config = AppConfig()
    repo.save(config)

    loaded = repo.load()
    assert loaded.prefix_key_path == "~/.config/nsupdate"
