"""Tests for TUI components, particularly form handling."""

from pathlib import Path

from tuneup_alpha.models import Record, Zone
from tuneup_alpha.tui import ZoneFormScreen


def test_zone_form_preserves_records_on_edit(tmp_path: Path) -> None:
    """Test that editing a zone preserves its existing records."""
    # Create a zone with records
    original_records = [
        Record(label="@", type="A", value="198.51.100.10", ttl=600),
        Record(label="www", type="CNAME", value="@", ttl=300),
    ]
    zone = Zone(
        name="example.com",
        server="ns1.example.com",
        key_file=tmp_path / "example.key",
        notes="Test zone",
        default_ttl=3600,
        records=original_records,
    )

    # Create a form in edit mode
    form = ZoneFormScreen(mode="edit", zone=zone)

    # Build a zone from the form (simulating saving without changes)
    # This would be called by the _submit method
    form._initial_zone = zone
    form._original_name = zone.name

    # Simulate form field values (same as original)
    class MockInput:
        def __init__(self, value):
            self.value = value

    # Mock the query_one method to return form values
    original_query_one = form.query_one

    def mock_query_one(selector, input_type=None):
        if selector == "#zone-name":
            return MockInput(zone.name)
        elif selector == "#zone-server":
            return MockInput(zone.server)
        elif selector == "#zone-key":
            return MockInput(str(zone.key_file))
        elif selector == "#zone-ttl":
            return MockInput(str(zone.default_ttl))
        elif selector == "#zone-notes":
            return MockInput(zone.notes or "")
        return original_query_one(selector, input_type)

    form.query_one = mock_query_one

    # Build the zone
    updated_zone = form._build_zone()

    # Assert that records are preserved
    assert len(updated_zone.records) == 2
    assert updated_zone.records[0].label == "@"
    assert updated_zone.records[1].label == "www"
    assert updated_zone.records == original_records


def test_zone_form_no_records_when_adding() -> None:
    """Test that adding a new zone has no records by default."""
    form = ZoneFormScreen(mode="add", zone=None)

    # Mock query_one to return minimal valid values
    class MockInput:
        def __init__(self, value):
            self.value = value

    def mock_query_one(selector, input_type=None):
        if selector == "#zone-name":
            return MockInput("example.com")
        elif selector == "#zone-server":
            return MockInput("ns1.example.com")
        elif selector == "#zone-key":
            return MockInput("/etc/keys/example.key")
        elif selector == "#zone-ttl":
            return MockInput("3600")
        elif selector == "#zone-notes":
            return MockInput("")
        return None

    form.query_one = mock_query_one

    # Build the zone
    new_zone = form._build_zone()

    # Assert that new zones have no records
    assert len(new_zone.records) == 0
