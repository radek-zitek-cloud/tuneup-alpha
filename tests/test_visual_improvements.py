"""Tests for visual improvements to the TUI."""

from pathlib import Path

from tuneup_alpha.config import ConfigRepository
from tuneup_alpha.models import AppConfig, Record, Zone
from tuneup_alpha.tui import ZoneDashboard


def test_app_title_is_dns_zone_dashboard() -> None:
    """Test that the app title is 'DNS Zone Dashboard'."""
    app = ZoneDashboard()
    assert app.TITLE == "DNS Zone Dashboard"


def test_zone_panel_height_is_seven() -> None:
    """Test that the zone panel height is 7 (5 zone lines + heading + frame)."""
    # Read the CSS file to verify the height
    css_path = Path(__file__).parent.parent / "src" / "tuneup_alpha" / "tui.tcss"
    css_content = css_path.read_text()

    # Find the #zones-table height setting
    assert "#zones-table {" in css_content
    assert "height: 7;" in css_content


def test_panels_have_same_default_border_color() -> None:
    """Test that all panels use the same border color by default."""
    css_path = Path(__file__).parent.parent / "src" / "tuneup_alpha" / "tui.tcss"
    css_content = css_path.read_text()

    # All panels should use $panel border by default
    assert "border: solid $panel;" in css_content


def test_focused_panel_has_distinct_border_color() -> None:
    """Test that focused panels have a distinct border color."""
    css_path = Path(__file__).parent.parent / "src" / "tuneup_alpha" / "tui.tcss"
    css_content = css_path.read_text()

    # Focused panel selectors should use $primary border
    assert "#zones-table.focused {" in css_content or "#records-table.focused {" in css_content
    assert "border: solid $primary;" in css_content


def test_title_updates_when_records_panel_focused(tmp_path: Path) -> None:
    """Test that the title includes the zone name when records panel has focus."""
    # Create a test zone
    zone = Zone(
        name="hmlab.cloud",
        server="ns1.hmlab.cloud",
        key_file=tmp_path / "hmlab.cloud.key",
        notes="Test zone",
        default_ttl=3600,
        records=[
            Record(label="@", type="A", value="198.51.100.10", ttl=600),
            Record(label="www", type="CNAME", value="@", ttl=300),
        ],
    )

    # Create a config with the zone
    config = AppConfig(zones=[zone])

    # Save config to temp file
    config_path = tmp_path / "config.yaml"
    config_repo = ConfigRepository(path=config_path)
    config_repo.save(config)

    # Create dashboard with the config
    app = ZoneDashboard(config_repo=config_repo)

    # Simulate mounting
    app._config = config
    app._table = type(
        "MockTable",
        (),
        {
            "row_count": 1,
            "focus": lambda self: None,
            "add_class": lambda self, x: None,
            "remove_class": lambda self, x: None,
        },
    )()
    app._records_table = type(
        "MockTable",
        (),
        {
            "remove_class": lambda self, x: None,
            "add_class": lambda self, x: None,
            "focus": lambda self: None,
        },
    )()

    # Mock cursor to return the first zone
    class MockCoordinate:
        row = 0

    app._table.cursor_coordinate = MockCoordinate()

    # Initially in zones mode
    app._focus_mode = "zones"
    app._update_focus_state()
    assert app.title == "DNS Zone Dashboard"

    # Switch to records mode
    app._focus_mode = "records"
    app._update_focus_state()
    assert app.title == "DNS Zone Dashboard [hmlab.cloud]"

    # Switch back to zones mode
    app._focus_mode = "zones"
    app._update_focus_state()
    assert app.title == "DNS Zone Dashboard"


def test_focus_state_updates_css_classes(tmp_path: Path) -> None:
    """Test that focus state updates CSS classes correctly."""
    # Create a test zone
    zone = Zone(
        name="example.com",
        server="ns1.example.com",
        key_file=tmp_path / "example.key",
        notes="Test zone",
        default_ttl=3600,
        records=[Record(label="@", type="A", value="203.0.113.10", ttl=600)],
    )

    # Create a config with the zone
    config = AppConfig(zones=[zone])
    config_path = tmp_path / "config.yaml"
    config_repo = ConfigRepository(path=config_path)
    config_repo.save(config)

    # Create dashboard with the config
    app = ZoneDashboard(config_repo=config_repo)

    # Mock tables to track CSS class changes
    zones_classes = set()
    records_classes = set()

    class MockZonesTable:
        row_count = 1

        def add_class(self, cls: str) -> None:
            zones_classes.add(cls)

        def remove_class(self, cls: str) -> None:
            zones_classes.discard(cls)

        def focus(self) -> None:
            pass

    class MockRecordsTable:
        def add_class(self, cls: str) -> None:
            records_classes.add(cls)

        def remove_class(self, cls: str) -> None:
            records_classes.discard(cls)

        def focus(self) -> None:
            pass

    class MockCoordinate:
        row = 0

    app._config = config
    app._table = MockZonesTable()
    app._table.cursor_coordinate = MockCoordinate()
    app._records_table = MockRecordsTable()

    # Focus zones panel
    app._focus_mode = "zones"
    app._update_focus_state()
    assert "focused" in zones_classes
    assert "focused" not in records_classes

    # Focus records panel
    zones_classes.clear()
    records_classes.clear()
    app._focus_mode = "records"
    app._update_focus_state()
    assert "focused" not in zones_classes
    assert "focused" in records_classes
