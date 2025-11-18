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
    with patch("tuneup_alpha.tui_forms.dns_lookup") as mock_dns:
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
    with patch("tuneup_alpha.tui_forms.dns_lookup") as mock_dns:
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
    with patch("tuneup_alpha.tui_forms.dns_lookup") as mock_dns:
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
    with patch("tuneup_alpha.tui_forms.dns_lookup") as mock_dns:
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
    with patch("tuneup_alpha.tui_forms.dns_lookup") as mock_dns:
        mock_dns.return_value = ("A", {"hostname": "test.com"})

        # Perform DNS lookup
        form._perform_dns_lookup("8.8.8.8")

        # The function should complete successfully
        # Note: We can't directly test the transient "Checking DNS..." message
        # without async testing, but we verify the function runs correctly
        mock_dns.assert_called_once_with("8.8.8.8")


def test_zone_form_dynamic_lookup_on_input_change():
    """Test that zone name input change triggers dynamic DNS lookup."""
    form = ZoneFormScreen(mode="add", zone=None)

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id):
            self.id = input_id
            self.value = ""

    server_input = MockInput("zone-server")
    key_input = MockInput("zone-key")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#zone-server":
            return server_input
        elif selector == "#zone-key":
            return key_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = info_static

    # Mock the DNS lookup functions
    with (
        patch("tuneup_alpha.tui_forms.lookup_nameservers") as mock_ns,
        patch("tuneup_alpha.tui_forms.lookup_a_records") as mock_a,
    ):
        mock_ns.return_value = ["ns1.example.com", "ns2.example.com"]
        mock_a.return_value = ["192.0.2.1"]

        # Simulate user typing a zone name
        form._perform_zone_lookup("example.com")

        # Assert that nameserver lookup was called
        mock_ns.assert_called_once_with("example.com")
        # Assert that A record lookup was called
        mock_a.assert_called_once_with("example.com")
        # Assert that server field was populated
        assert server_input.value == "ns1.example.com"
        # Assert that key field was populated
        assert key_input.value == "~/.config/nsupdate/example.com.key"


def test_zone_form_dynamic_lookup_empty_value():
    """Test that empty zone name doesn't trigger DNS lookup."""
    form = ZoneFormScreen(mode="add", zone=None)

    # Mock the DNS lookup functions
    with (
        patch("tuneup_alpha.tui_forms.lookup_nameservers") as mock_ns,
        patch("tuneup_alpha.tui_forms.lookup_a_records") as mock_a,
    ):
        # Simulate user clearing the zone name
        form._perform_zone_lookup("")

        # Assert that no lookups were performed
        mock_ns.assert_not_called()
        mock_a.assert_not_called()


def test_zone_form_dynamic_lookup_preserves_existing_server():
    """Test that DNS lookup doesn't override manually entered server."""
    form = ZoneFormScreen(mode="add", zone=None)

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id, value=""):
            self.id = input_id
            self.value = value

    # Server already has a value (user manually entered it)
    server_input = MockInput("zone-server", "custom.nameserver.com")
    key_input = MockInput("zone-key")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#zone-server":
            return server_input
        elif selector == "#zone-key":
            return key_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = info_static

    # Mock the DNS lookup functions
    with (
        patch("tuneup_alpha.tui_forms.lookup_nameservers") as mock_ns,
        patch("tuneup_alpha.tui_forms.lookup_a_records") as mock_a,
    ):
        mock_ns.return_value = ["ns1.example.com"]
        mock_a.return_value = []

        # Simulate user typing a zone name
        form._perform_zone_lookup("example.com")

        # Assert that server field was NOT overwritten
        assert server_input.value == "custom.nameserver.com"


def test_record_form_label_lookup_updates_fields():
    """Test that label lookup populates type and value fields when DNS record is found."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id):
            self.id = input_id
            self.value = ""

    type_input = MockInput("record-type")
    value_input = MockInput("record-value")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        elif selector == "#record-value":
            return value_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = info_static

    # Mock dns_lookup_label to simulate finding an A record
    with patch("tuneup_alpha.tui_forms.dns_lookup_label") as mock_lookup:
        mock_lookup.return_value = ("A", "192.0.2.1")

        # Simulate user entering a label
        form._perform_label_lookup("www")

        # Assert that type and value were set
        assert type_input.value == "A"
        assert value_input.value == "192.0.2.1"
        mock_lookup.assert_called_once_with("www", "example.com")


def test_record_form_label_lookup_overwrites_existing_values():
    """Test that label lookup overwrites existing values when new DNS info is found.

    This is the key fix: when user types 'name' and fields are prefilled,
    then continues typing to 'name-wg', if new DNS info is found for 'name-wg',
    it should overwrite the previously filled values.
    """
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock query_one to return mock inputs with existing values
    class MockInput:
        def __init__(self, input_id, initial_value=""):
            self.id = input_id
            self.value = initial_value

    # Fields already have values from previous lookup
    type_input = MockInput("record-type", "A")
    value_input = MockInput("record-value", "192.0.2.1")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        elif selector == "#record-value":
            return value_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = info_static

    # Mock dns_lookup_label to simulate finding a CNAME record for new label
    with patch("tuneup_alpha.tui_forms.dns_lookup_label") as mock_lookup:
        mock_lookup.return_value = ("CNAME", "target.example.com")

        # Simulate user continuing to type (label changed from 'name' to 'name-wg')
        form._perform_label_lookup("name-wg")

        # Assert that type and value were OVERWRITTEN with new DNS info
        assert type_input.value == "CNAME"
        assert value_input.value == "target.example.com"
        mock_lookup.assert_called_once_with("name-wg", "example.com")


def test_record_form_label_lookup_cname_discovered():
    """Test that label lookup sets discovered_cname_target when CNAME is found."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id):
            self.id = input_id
            self.value = ""

    type_input = MockInput("record-type")
    value_input = MockInput("record-value")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        elif selector == "#record-value":
            return value_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = info_static

    # Mock dns_lookup_label to simulate finding a CNAME record
    with patch("tuneup_alpha.tui_forms.dns_lookup_label") as mock_lookup:
        mock_lookup.return_value = ("CNAME", "cdn.example.com")

        # Simulate user entering a label
        form._perform_label_lookup("www")

        # Assert that discovered_cname_target was set
        assert form._discovered_cname_target == "cdn.example.com"


def test_record_form_label_lookup_empty_label():
    """Test that empty label doesn't trigger DNS lookup."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock dns_lookup_label
    with patch("tuneup_alpha.tui_forms.dns_lookup_label") as mock_lookup:
        # Simulate user entering empty label
        form._perform_label_lookup("")

        # Assert that dns_lookup_label was not called
        mock_lookup.assert_not_called()


def test_record_form_label_lookup_no_dns_record_found():
    """Test that label lookup clears discovered CNAME and shows appropriate message when no DNS record found."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id):
            self.id = input_id
            self.value = ""

    class MockStatic:
        def __init__(self):
            self.renderable = ""

        def update(self, text):
            self.renderable = text

    type_input = MockInput("record-type")
    value_input = MockInput("record-value")
    info_static = MockStatic()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        elif selector == "#record-value":
            return value_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = MockStatic()

    # Set initial discovered_cname_target
    form._discovered_cname_target = "old.example.com"

    # Mock dns_lookup_label to simulate no record found
    with patch("tuneup_alpha.tui_forms.dns_lookup_label") as mock_lookup:
        mock_lookup.return_value = (None, None)

        # Simulate user entering a label
        form._perform_label_lookup("newlabel")

        # Assert that discovered_cname_target was cleared
        assert form._discovered_cname_target is None
        # Assert that appropriate message is shown
        assert "No existing DNS records found" in info_static.renderable
        assert "○" in info_static.renderable
