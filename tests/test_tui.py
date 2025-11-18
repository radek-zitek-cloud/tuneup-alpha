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


def test_record_form_dns_lookup_updates_type_field():
    """Test that DNS lookup updates type field when DNS info is found.

    This ensures consistent behavior with label lookup - both always update
    fields when new DNS information is discovered.
    """
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

        # Assert that type WAS changed to match the DNS lookup result
        assert type_input.value == "A"


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
    """Test that zone name input change triggers DNS lookup but NOT key file generation."""
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

        # Simulate user typing a zone name (without generating key path)
        form._perform_zone_lookup("example.com", generate_key_path=False)

        # Assert that nameserver lookup was called
        mock_ns.assert_called_once_with("example.com")
        # Assert that A record lookup was called
        mock_a.assert_called_once_with("example.com")
        # Assert that server field was populated
        assert server_input.value == "ns1.example.com"
        # Assert that key field was NOT populated (stays empty)
        assert key_input.value == ""


def test_zone_form_key_path_generated_on_blur():
    """Test that key file path is generated when zone name field loses focus."""
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

        # Simulate zone name field losing focus (with key path generation)
        form._perform_zone_lookup("example.com", generate_key_path=True)

        # Assert that nameserver lookup was called
        mock_ns.assert_called_once_with("example.com")
        # Assert that A record lookup was called
        mock_a.assert_called_once_with("example.com")
        # Assert that server field was populated
        assert server_input.value == "ns1.example.com"
        # Assert that key field WAS populated
        assert key_input.value == "~/.config/nsupdate/example.com.key"


def test_zone_form_key_path_fallback_in_build():
    """Test that key file path is generated as fallback in _build_zone if not set."""
    form = ZoneFormScreen(mode="add", zone=None)

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id, value=""):
            self.id = input_id
            self.value = value

    # Setup inputs with zone name and server, but empty key path
    zone_name_input = MockInput("zone-name", "example.com")
    server_input = MockInput("zone-server", "ns1.example.com")
    key_input = MockInput("zone-key", "")  # Empty key path
    ttl_input = MockInput("zone-ttl", "3600")
    notes_input = MockInput("zone-notes", "Test notes")

    def mock_query_one(selector, input_type=None):
        if selector == "#zone-name":
            return zone_name_input
        elif selector == "#zone-server":
            return server_input
        elif selector == "#zone-key":
            return key_input
        elif selector == "#zone-ttl":
            return ttl_input
        elif selector == "#zone-notes":
            return notes_input
        return None

    form.query_one = mock_query_one

    # Build the zone - this should generate the default key path as a fallback
    zone = form._build_zone()

    # Assert that the zone was built successfully with a generated key path
    assert zone.name == "example.com"
    assert zone.server == "ns1.example.com"
    assert str(zone.key_file) == "~/.config/nsupdate/example.com.key"
    assert zone.default_ttl == 3600
    assert zone.notes == "Test notes"


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


def test_zone_form_key_path_not_generated_during_typing():
    """Integration test: key path should not be generated while user is typing.

    This test simulates the actual flow:
    1. User types incrementally in the zone name field (e.g., "e", "ex", "exa", etc.)
    2. Each keystroke triggers on_input_changed
    3. The key file path should remain empty during typing
    4. Only when the field loses focus should the key path be generated
    """
    form = ZoneFormScreen(mode="add", zone=None)

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id):
            self.id = input_id
            self.value = ""

    zone_name_input = MockInput("zone-name")
    server_input = MockInput("zone-server")
    key_input = MockInput("zone-key")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#zone-name":
            return zone_name_input
        elif selector == "#zone-server":
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
        mock_a.return_value = ["192.0.2.1"]

        # Simulate user typing incrementally
        for partial_domain in ["e", "ex", "exa", "exam", "examp", "exampl", "example"]:
            zone_name_input.value = partial_domain

            # Create a mock event with the current value
            class MockEvent:
                def __init__(self, val):
                    self.input = zone_name_input
                    self.value = val

            event = MockEvent(partial_domain)

            # Simulate on_input_changed being called
            form.on_input_changed(event)

            # Key path should still be empty during typing
            assert key_input.value == "", (
                f"Key path should be empty while typing '{partial_domain}', "
                f"but got '{key_input.value}'"
            )

        # Now simulate the zone name field losing focus
        zone_name_input.value = "example.com"

        class MockBlurEvent:
            def __init__(self):
                self.input = zone_name_input

        blur_event = MockBlurEvent()
        form.on_input_blurred(blur_event)

        # After blur, the key path should be generated
        assert key_input.value == "~/.config/nsupdate/example.com.key", (
            f"Key path should be generated on blur, but got '{key_input.value}'"
        )


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
    label_input = MockInput("record-label")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        elif selector == "#record-value":
            return value_input
        elif selector == "#record-label":
            return label_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = info_static

    # Mock dns_lookup_label to simulate finding an A record
    with patch("tuneup_alpha.tui_forms.dns_lookup_label") as mock_lookup:
        mock_lookup.return_value = ("A", "192.0.2.1")

        # Simulate user entering a label
        form._perform_label_type_lookup("www", None)

        # Assert that type and value were set
        assert type_input.value == "A"
        assert value_input.value == "192.0.2.1"
        mock_lookup.assert_called_once_with("www", "example.com")


def test_record_form_label_lookup_overwrites_existing_values():
    """Test that label lookup performs type-specific lookup when type is already set.

    When user types 'name' and type field already has "A",
    then continues typing to 'name-wg', the lookup should search for an A record
    for 'name-wg', not overwrite the type.
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
    label_input = MockInput("record-label")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        elif selector == "#record-value":
            return value_input
        elif selector == "#record-label":
            return label_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = info_static

    # Mock dns_lookup_label_with_type to simulate finding an A record for new label
    with patch("tuneup_alpha.tui_forms.dns_lookup_label_with_type") as mock_lookup:
        mock_lookup.return_value = "203.0.2.100"

        # Simulate user continuing to type (label changed from 'name' to 'name-wg')
        form._perform_label_type_lookup("name-wg", None)

        # Assert that value was updated but type stayed the same (type-specific lookup)
        assert type_input.value == "A"  # Type should NOT change
        assert value_input.value == "203.0.2.100"  # Value should update with new A record
        mock_lookup.assert_called_once_with("name-wg", "example.com", "A")


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
    label_input = MockInput("record-label")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-type":
            return type_input
        elif selector == "#record-value":
            return value_input
        elif selector == "#record-label":
            return label_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = info_static

    # Mock dns_lookup_label to simulate finding a CNAME record
    with patch("tuneup_alpha.tui_forms.dns_lookup_label") as mock_lookup:
        mock_lookup.return_value = ("CNAME", "cdn.example.com")

        # Simulate user entering a label
        form._perform_label_type_lookup("www", None)

        # Assert that discovered_cname_target was set
        assert form._discovered_cname_target == "cdn.example.com"


def test_record_form_label_lookup_empty_label():
    """Test that empty label doesn't trigger DNS lookup."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id):
            self.id = input_id
            self.value = ""

    label_input = MockInput("record-label")
    type_input = MockInput("record-type")
    value_input = MockInput("record-value")

    def mock_query_one(selector, input_type=None):
        if selector == "#record-label":
            return label_input
        elif selector == "#record-type":
            return type_input
        elif selector == "#record-value":
            return value_input
        return None

    form.query_one = mock_query_one

    # Mock dns_lookup_label
    with patch("tuneup_alpha.tui_forms.dns_lookup_label") as mock_lookup:
        # Simulate user entering empty label
        form._perform_label_type_lookup("", None)

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

    label_input = MockInput("record-label")
    type_input = MockInput("record-type")
    value_input = MockInput("record-value")
    info_static = MockStatic()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-label":
            return label_input
        elif selector == "#record-type":
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
        form._perform_label_type_lookup("newlabel", None)

        # Assert that discovered_cname_target was cleared
        assert form._discovered_cname_target is None
        # Assert that appropriate message is shown
        assert "No existing DNS records found" in info_static.renderable
        assert "○" in info_static.renderable


def test_record_form_type_change_triggers_lookup():
    """Test that changing the type field triggers a type-specific lookup."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id, initial_value=""):
            self.id = input_id
            self.value = initial_value

    label_input = MockInput("record-label", "www")
    type_input = MockInput("record-type", "A")
    value_input = MockInput("record-value", "192.0.2.1")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-label":
            return label_input
        elif selector == "#record-type":
            return type_input
        elif selector == "#record-value":
            return value_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = info_static

    # Simulate a first lookup for label "www" and type "A"
    form._last_lookup_label = "www"
    form._last_lookup_type = "A"

    # Mock dns_lookup_label_with_type to simulate finding an AAAA record
    with patch("tuneup_alpha.tui_forms.dns_lookup_label_with_type") as mock_lookup:
        mock_lookup.return_value = "2001:db8::1"

        # Simulate user changing type from "A" to "AAAA"
        form._perform_label_type_lookup(None, "AAAA")

        # Assert that type-specific lookup was called with new type
        mock_lookup.assert_called_once_with("www", "example.com", "AAAA")
        # Assert that value was updated
        assert value_input.value == "2001:db8::1"


def test_record_form_label_and_type_change_together():
    """Test that both label and type changing triggers a new lookup."""
    form = RecordFormScreen(mode="add", zone_name="example.com")

    # Mock query_one to return mock inputs
    class MockInput:
        def __init__(self, input_id, initial_value=""):
            self.id = input_id
            self.value = initial_value

    label_input = MockInput("record-label", "mail")
    type_input = MockInput("record-type", "MX")
    value_input = MockInput("record-value", "")
    info_static = type("MockStatic", (), {"update": lambda self, text: None})()

    def mock_query_one(selector, input_type=None):
        if selector == "#record-label":
            return label_input
        elif selector == "#record-type":
            return type_input
        elif selector == "#record-value":
            return value_input
        return None

    form.query_one = mock_query_one
    form._info = info_static
    form._error = info_static

    # Mock dns_lookup_label_with_type to simulate finding an MX record
    with patch("tuneup_alpha.tui_forms.dns_lookup_label_with_type") as mock_lookup:
        mock_lookup.return_value = "10 mail.example.com"

        # Simulate user entering label and type
        form._perform_label_type_lookup("mail", "MX")

        # Assert that type-specific lookup was called
        mock_lookup.assert_called_once_with("mail", "example.com", "MX")
        # Assert that value was updated
        assert value_input.value == "10 mail.example.com"
