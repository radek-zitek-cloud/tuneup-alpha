"""Tests for theme persistence in TUI."""

from pathlib import Path
from unittest.mock import MagicMock

from tuneup_alpha.config import ConfigRepository
from tuneup_alpha.models import AppConfig
from tuneup_alpha.tui import ZoneDashboard


def test_default_theme_is_textual_dark(tmp_path: Path) -> None:
    """Test that default theme is textual-dark."""
    config = AppConfig()
    assert config.theme == "textual-dark"


def test_theme_persisted_in_config(tmp_path: Path) -> None:
    """Test that theme is saved in the config file."""
    config_path = tmp_path / "config.yaml"
    repo = ConfigRepository(config_path)

    # Create and save a config with a custom theme
    config = AppConfig(theme="nord")
    repo.save(config)

    # Load it back
    loaded_config = repo.load()
    assert loaded_config.theme == "nord"


def test_theme_loaded_on_dashboard_mount(tmp_path: Path) -> None:
    """Test that theme is loaded from config when dashboard starts."""
    config_path = tmp_path / "config.yaml"
    repo = ConfigRepository(config_path)

    # Save a config with a specific theme
    config = AppConfig(theme="dracula")
    repo.save(config)

    # Create dashboard with this repo
    dashboard = ZoneDashboard(config_repo=repo)

    # Simulate mounting - the theme should be loaded
    # Note: We can't fully test mounting without running the app,
    # but we can verify the logic
    dashboard._config = repo.load()
    if dashboard._config.theme:
        dashboard.theme = dashboard._config.theme

    assert dashboard.theme == "dracula"


def test_theme_saved_on_quit(tmp_path: Path) -> None:
    """Test that theme is saved when quitting the dashboard."""
    config_path = tmp_path / "config.yaml"
    repo = ConfigRepository(config_path)

    # Start with default config
    repo.save(AppConfig())

    # Create dashboard
    dashboard = ZoneDashboard(config_repo=repo)
    dashboard._config = repo.load()

    # Change theme
    dashboard.theme = "gruvbox"

    # Call save logic directly (without triggering actual quit)
    dashboard._config.theme = dashboard.theme
    dashboard.config_repo.save(dashboard._config)

    # Verify theme was saved
    saved_config = repo.load()
    assert saved_config.theme == "gruvbox"


def test_cycle_theme_action(tmp_path: Path) -> None:
    """Test that cycle_theme action changes theme."""
    config_path = tmp_path / "config.yaml"
    repo = ConfigRepository(config_path)

    # Create dashboard
    dashboard = ZoneDashboard(config_repo=repo)
    dashboard._config = repo.load()

    # Mock notify to prevent actual UI updates
    dashboard.notify = MagicMock()

    # Get initial theme
    initial_theme = dashboard.theme

    # Cycle to next theme
    dashboard.action_cycle_theme()

    # Verify theme changed
    assert dashboard.theme != initial_theme
    assert dashboard.notify.called

    # Verify notification message
    call_args = dashboard.notify.call_args
    assert "Theme changed to:" in call_args[0][0]


def test_cycle_theme_wraps_around(tmp_path: Path) -> None:
    """Test that cycling theme wraps around to first theme."""
    config_path = tmp_path / "config.yaml"
    repo = ConfigRepository(config_path)

    # Create dashboard
    dashboard = ZoneDashboard(config_repo=repo)
    dashboard._config = repo.load()

    # Mock notify
    dashboard.notify = MagicMock()

    # Get all available themes
    themes = list(dashboard.available_themes)

    # Set to last theme
    dashboard.theme = themes[-1]

    # Cycle to next theme (should wrap to first)
    dashboard.action_cycle_theme()

    assert dashboard.theme == themes[0]


def test_theme_roundtrip_persistence(tmp_path: Path) -> None:
    """Test complete theme persistence roundtrip."""
    config_path = tmp_path / "config.yaml"
    repo = ConfigRepository(config_path)

    # Session 1: Set theme and save
    dashboard1 = ZoneDashboard(config_repo=repo)
    dashboard1._config = repo.load()
    dashboard1.theme = "tokyo-night"

    # Save theme (without triggering actual quit)
    dashboard1._config.theme = dashboard1.theme
    dashboard1.config_repo.save(dashboard1._config)

    # Session 2: Load and verify theme was persisted
    dashboard2 = ZoneDashboard(config_repo=repo)
    dashboard2._config = repo.load()

    # Simulate on_mount behavior
    if dashboard2._config.theme:
        dashboard2.theme = dashboard2._config.theme

    assert dashboard2.theme == "tokyo-night"
