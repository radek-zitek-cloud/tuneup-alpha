from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from tuneup_alpha.cli import app
from tuneup_alpha.config import ConfigRepository
from tuneup_alpha.models import Record, Zone

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "TuneUp Alpha version" in result.stdout
    assert "0.1.0" in result.stdout


def test_init_command(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    result = runner.invoke(app, ["init", "--config-path", str(config_path)])
    assert result.exit_code == 0
    assert "Configuration written to" in result.stdout
    assert config_path.exists()


def test_init_command_no_overwrite(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    # Create config first time
    runner.invoke(app, ["init", "--config-path", str(config_path)])
    # Try again without overwrite
    result = runner.invoke(app, ["init", "--config-path", str(config_path)])
    assert result.exit_code == 0
    assert "Configuration written to" in result.stdout


def test_init_command_with_overwrite(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("old: data")
    result = runner.invoke(
        app, ["init", "--config-path", str(config_path), "--overwrite"]
    )
    assert result.exit_code == 0
    assert config_path.exists()
    content = config_path.read_text()
    assert "old: data" not in content
    assert "zones:" in content


def test_show_command_empty_config(tmp_path: Path) -> None:
    config_path = tmp_path / "empty.yaml"
    result = runner.invoke(app, ["show", "--config-path", str(config_path)])
    assert result.exit_code == 0
    assert "No zones configured" in result.stdout


def test_show_command_with_zones(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    zone = Zone(
        name="example.com",
        server="ns1.example.com",
        key_file=Path("/etc/nsupdate/example.key"),
    )
    repo.add_zone(zone)

    result = runner.invoke(app, ["show", "--config-path", str(tmp_path / "config.yaml")])
    assert result.exit_code == 0
    assert "example.com" in result.stdout
    assert "ns1.example.com" in result.stdout


def test_plan_command_zone_not_found(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    repo = ConfigRepository(config_path)
    repo.save(repo.load())

    result = runner.invoke(
        app, ["plan", "nonexistent.com", "--config-path", str(config_path)]
    )
    assert result.exit_code == 2
    assert "not found" in result.stdout


def test_plan_command_renders_script(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    zone = Zone(
        name="example.com",
        server="ns1.example.com",
        key_file=Path("/etc/nsupdate/example.key"),
        records=[Record(label="@", type="A", value="1.2.3.4", ttl=300)],
    )
    repo.add_zone(zone)

    result = runner.invoke(
        app, ["plan", "example.com", "--config-path", str(tmp_path / "config.yaml")]
    )
    assert result.exit_code == 0
    assert "server ns1.example.com" in result.stdout
    assert "zone example.com" in result.stdout
    assert "update add" in result.stdout
    assert "send" in result.stdout


def test_apply_command_dry_run(tmp_path: Path) -> None:
    repo = ConfigRepository(tmp_path / "config.yaml")
    zone = Zone(
        name="example.com",
        server="ns1.example.com",
        key_file=Path("/etc/nsupdate/example.key"),
        records=[Record(label="@", type="A", value="1.2.3.4", ttl=300)],
    )
    repo.add_zone(zone)

    result = runner.invoke(
        app,
        [
            "apply",
            "example.com",
            "--config-path",
            str(tmp_path / "config.yaml"),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "server ns1.example.com" in result.stdout


def test_apply_command_zone_not_found(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    repo = ConfigRepository(config_path)
    repo.save(repo.load())

    result = runner.invoke(
        app,
        [
            "apply",
            "nonexistent.com",
            "--config-path",
            str(config_path),
            "--dry-run",
        ],
    )
    assert result.exit_code == 2
    assert "not found" in result.stdout


@patch("tuneup_alpha.cli.run_dashboard")
def test_tui_command(mock_run_dashboard: MagicMock, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    ConfigRepository(config_path).save(ConfigRepository(config_path).load())

    result = runner.invoke(app, ["tui", "--config-path", str(config_path)])
    assert result.exit_code == 0
    mock_run_dashboard.assert_called_once()
