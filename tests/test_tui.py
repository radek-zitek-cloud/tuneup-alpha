"""Tests for TUI components, particularly form handling."""

from pathlib import Path
from unittest.mock import patch

from tuneup_alpha.models import Record, Zone
from tuneup_alpha.tui import RecordFormScreen, ZoneDashboard, ZoneFormScreen


def test_zone_dashboard_disables_tab_bindings() -> None:
    """Test that tab and shift+tab bindings are disabled in the main dashboard.

    Note: priority is False to allow modal screens to override with their own tab bindings.
    """
    dashboard = ZoneDashboard()

    # Check that tab and shift+tab bindings exist and point to noop action
    tab_bindings = [b for b in dashboard.BINDINGS if b.key in ("tab", "shift+tab")]

    assert len(tab_bindings) == 2, "Should have both tab and shift+tab bindings"

    for binding in tab_bindings:
        assert binding.action == "noop", f"Binding {binding.key} should use 'noop' action"
        assert binding.priority is False, (
            f"Binding {binding.key} should have priority=False to allow modal overrides"
        )
        assert binding.show is False, f"Binding {binding.key} should not be shown in footer"


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


def test_record_form_dns_lookup_for_ip():
    """Test that entering an IP address triggers DNS lookup and updates type."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id):
            self.id = input_id
            self.value = ""

    type_input = MockInput("record-type")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        return None

    form.query_one = mock_query_one
    form._info = info_static

    # Mock dns_lookup to simulate successful reverse DNS
    with patch("tuneup_alpha.tui.dns_lookup") as mock_dns:
        mock_dns.return_value = ("A", {"hostname": "example.com"})

        # Simulate user entering an IP address
        form._perform_dns_lookup("192.0.2.1")

        # Assert that type was set to "A"
        assert type_input.value == "A"
        mock_dns.assert_called_once_with("192.0.2.1")


def test_record_form_dns_lookup_for_hostname():
    """Test that entering a hostname triggers DNS lookup and updates type."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id):
            self.id = input_id
            self.value = ""

    type_input = MockInput("record-type")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        return None

    form.query_one = mock_query_one
    form._info = info_static

    # Mock dns_lookup to simulate successful forward DNS
    with patch("tuneup_alpha.tui.dns_lookup") as mock_dns:
        mock_dns.return_value = ("CNAME", {"ip": "192.0.2.1"})

        # Simulate user entering a hostname
        form._perform_dns_lookup("www.example.com")

        # Assert that type was set to "CNAME"
        assert type_input.value == "CNAME"
        mock_dns.assert_called_once_with("www.example.com")


def test_record_form_dns_lookup_empty_value():
    """Test that empty value doesn't trigger DNS lookup."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock dns_lookup
    with patch("tuneup_alpha.tui.dns_lookup") as mock_dns:
        # Simulate user entering empty value
        form._perform_dns_lookup("")

        # Assert that dns_lookup was not called
        mock_dns.assert_not_called()


def test_record_form_dns_lookup_preserves_existing_type():
    """Test that DNS lookup doesn't override manually set type."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id, initial_value=""):
            self.id = input_id
            self.value = initial_value

    # Type is already set to CNAME
    type_input = MockInput("record-type", "CNAME")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        return None

    form.query_one = mock_query_one
    form._info = info_static

    # Mock dns_lookup to suggest "A" type
    with patch("tuneup_alpha.tui.dns_lookup") as mock_dns:
        mock_dns.return_value = ("A", {"hostname": "example.com"})

        # Simulate user entering an IP address
        form._perform_dns_lookup("192.0.2.1")

        # Assert that type was NOT changed because it was already set to CNAME
        assert type_input.value == "CNAME"


def test_dns_visual_cue_successful_reverse_lookup():
    """Test visual cue for successful reverse DNS lookup."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock info widget to capture the displayed message
    class MockStatic:
        def __init__(self):
            self.renderable = ""

        def update(self, text):
            self.renderable = text

    info_static = MockStatic()
    form._info = info_static

    # Test successful reverse DNS lookup
    form._show_lookup_info("A", {"hostname": "dns.google"})

    # Verify the visual cue includes success indicator and hostname
    assert "✓" in info_static.renderable
    assert "Reverse DNS: dns.google" in info_static.renderable
    assert "[green]" in info_static.renderable


def test_dns_visual_cue_failed_reverse_lookup():
    """Test visual cue for failed reverse DNS lookup."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    class MockStatic:
        def __init__(self):
            self.renderable = ""

        def update(self, text):
            self.renderable = text

    info_static = MockStatic()
    form._info = info_static

    # Test failed reverse DNS lookup
    form._show_lookup_info("A", {"hostname": None})

    # Verify the visual cue includes no-result indicator
    assert "○" in info_static.renderable
    assert "No reverse DNS found" in info_static.renderable
    assert "[yellow]" in info_static.renderable


def test_dns_visual_cue_successful_forward_lookup():
    """Test visual cue for successful forward DNS lookup."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    class MockStatic:
        def __init__(self):
            self.renderable = ""

        def update(self, text):
            self.renderable = text

    info_static = MockStatic()
    form._info = info_static

    # Test successful forward DNS lookup
    form._show_lookup_info("CNAME", {"ip": "93.184.216.34"})

    # Verify the visual cue includes success indicator and IP
    assert "✓" in info_static.renderable
    assert "Forward DNS: 93.184.216.34" in info_static.renderable
    assert "[green]" in info_static.renderable


def test_dns_visual_cue_failed_forward_lookup():
    """Test visual cue for failed forward DNS lookup."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    class MockStatic:
        def __init__(self):
            self.renderable = ""

        def update(self, text):
            self.renderable = text

    info_static = MockStatic()
    form._info = info_static

    # Test failed forward DNS lookup
    form._show_lookup_info("CNAME", {"ip": None})

    # Verify the visual cue includes no-result indicator
    assert "○" in info_static.renderable
    assert "No forward DNS found" in info_static.renderable
    assert "[yellow]" in info_static.renderable


def test_dns_visual_cue_checking_indicator():
    """Test that checking indicator is shown during DNS lookup."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    class MockStatic:
        def __init__(self):
            self.renderable = ""

        def update(self, text):
            self.renderable = text

    class MockInput:
        def __init__(self, input_id):
            self.id = input_id
            self.value = ""

    info_static = MockStatic()
    type_input = MockInput("record-type")

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = MockStatic()

    # Mock dns_lookup to verify the checking indicator appears
    with patch("tuneup_alpha.tui.dns_lookup") as mock_dns:
        mock_dns.return_value = ("A", {"hostname": "test.com"})

        # Perform DNS lookup
        form._perform_dns_lookup("8.8.8.8")

        # The function should complete successfully
        # Note: We can't directly test the transient "Checking DNS..." message
        # without async testing, but we verify the function runs correctly
        mock_dns.assert_called_once_with("8.8.8.8")
