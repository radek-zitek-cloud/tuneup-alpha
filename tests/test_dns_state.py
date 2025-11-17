"""Tests for DNS state validation module."""

from pathlib import Path
from unittest.mock import patch

from tuneup_alpha.dns_state import (
    DNSStateDiff,
    compare_dns_state,
    query_current_dns_state,
    validate_dns_state,
)
from tuneup_alpha.models import Record, Zone


def _zone() -> Zone:
    """Create a test zone."""
    return Zone(
        name="example.com",
        server="ns1.example.com",
        key_file=Path("/etc/nsupdate/example.com.key"),
        records=[],
    )


def test_dns_state_diff_has_changes_empty() -> None:
    """Test has_changes returns False when there are no changes."""
    diff = DNSStateDiff(
        zone_name="example.com",
        changes=[],
        current_records=[],
        desired_records=[],
    )
    assert not diff.has_changes()


def test_dns_state_diff_has_changes_with_changes() -> None:
    """Test has_changes returns True when there are changes."""
    from tuneup_alpha.models import RecordChange

    record = Record(label="@", type="A", value="1.2.3.4")
    diff = DNSStateDiff(
        zone_name="example.com",
        changes=[RecordChange(action="create", record=record)],
        current_records=[],
        desired_records=[record],
    )
    assert diff.has_changes()


def test_dns_state_diff_summary() -> None:
    """Test summary returns correct counts."""
    from tuneup_alpha.models import RecordChange

    record1 = Record(label="@", type="A", value="1.2.3.4")
    record2 = Record(label="www", type="CNAME", value="@")
    record3 = Record(label="old", type="A", value="5.6.7.8")
    record4 = Record(label="change", type="A", value="9.9.9.9")

    diff = DNSStateDiff(
        zone_name="example.com",
        changes=[
            RecordChange(action="create", record=record1),
            RecordChange(action="create", record=record2),
            RecordChange(action="delete", record=record3),
            RecordChange(action="update", record=record4, previous=record3),
        ],
        current_records=[],
        desired_records=[record1, record2, record4],
    )
    summary = diff.summary()
    assert summary["create"] == 2
    assert summary["delete"] == 1
    assert summary["update"] == 1


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_query_current_dns_state_empty(mock_dig: any) -> None:
    """Test querying DNS state with no records."""
    mock_dig.return_value = []

    zone = _zone()
    result = query_current_dns_state(zone)

    assert isinstance(result, list)
    assert len(result) == 0


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_query_current_dns_state_with_a_record(mock_dig: any) -> None:
    """Test querying DNS state with A record."""
    # Mock dig_lookup to return an A record for the apex
    def mock_lookup(domain: str, record_type: str) -> list[str]:
        if domain == "example.com" and record_type == "A":
            return ["1.2.3.4"]
        return []

    mock_dig.side_effect = mock_lookup

    zone = _zone()
    zone.records = [Record(label="@", type="A", value="1.2.3.4")]

    result = query_current_dns_state(zone)

    # Should find at least the A record
    assert len(result) >= 1
    a_records = [r for r in result if r.type == "A" and r.value == "1.2.3.4"]
    assert len(a_records) == 1
    assert a_records[0].label == "@"


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_query_current_dns_state_with_mx_record(mock_dig: any) -> None:
    """Test querying DNS state with MX record."""

    def mock_lookup(domain: str, record_type: str) -> list[str]:
        if domain == "example.com" and record_type == "MX":
            return ["10 mail.example.com"]
        return []

    mock_dig.side_effect = mock_lookup

    zone = _zone()
    zone.records = [
        Record(label="@", type="MX", value="mail.example.com", priority=10)
    ]

    result = query_current_dns_state(zone)

    mx_records = [r for r in result if r.type == "MX"]
    assert len(mx_records) == 1
    assert mx_records[0].value == "mail.example.com"
    assert mx_records[0].priority == 10


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_query_current_dns_state_with_srv_record(mock_dig: any) -> None:
    """Test querying DNS state with SRV record."""

    def mock_lookup(domain: str, record_type: str) -> list[str]:
        if domain == "_http._tcp.example.com" and record_type == "SRV":
            return ["10 60 80 server.example.com"]
        return []

    mock_dig.side_effect = mock_lookup

    zone = _zone()
    zone.records = [
        Record(
            label="_http._tcp",
            type="SRV",
            value="server.example.com",
            priority=10,
            weight=60,
            port=80,
        )
    ]

    result = query_current_dns_state(zone)

    srv_records = [r for r in result if r.type == "SRV"]
    assert len(srv_records) == 1
    assert srv_records[0].value == "server.example.com"
    assert srv_records[0].priority == 10
    assert srv_records[0].weight == 60
    assert srv_records[0].port == 80


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_compare_dns_state_no_changes(mock_dig: any) -> None:
    """Test comparing DNS state when current matches desired."""

    def mock_lookup(domain: str, record_type: str) -> list[str]:
        if domain == "example.com" and record_type == "A":
            return ["1.2.3.4"]
        return []

    mock_dig.side_effect = mock_lookup

    zone = _zone()
    zone.records = [Record(label="@", type="A", value="1.2.3.4")]

    diff = compare_dns_state(zone)

    assert diff.zone_name == "example.com"
    assert not diff.has_changes()


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_compare_dns_state_record_to_create(mock_dig: any) -> None:
    """Test comparing DNS state when a record needs to be created."""
    mock_dig.return_value = []

    zone = _zone()
    zone.records = [Record(label="@", type="A", value="1.2.3.4")]

    diff = compare_dns_state(zone)

    assert diff.has_changes()
    summary = diff.summary()
    assert summary["create"] == 1
    assert summary["delete"] == 0
    assert summary["update"] == 0


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_compare_dns_state_record_to_delete(mock_dig: any) -> None:
    """Test comparing DNS state when a record needs to be deleted."""

    def mock_lookup(domain: str, record_type: str) -> list[str]:
        if domain == "example.com" and record_type == "A":
            return ["1.2.3.4"]
        return []

    mock_dig.side_effect = mock_lookup

    zone = _zone()
    zone.records = []  # No desired records

    diff = compare_dns_state(zone)

    assert diff.has_changes()
    summary = diff.summary()
    assert summary["create"] == 0
    assert summary["delete"] == 1
    assert summary["update"] == 0


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_compare_dns_state_record_to_update(mock_dig: any) -> None:
    """Test comparing DNS state when a record needs to be updated."""

    def mock_lookup(domain: str, record_type: str) -> list[str]:
        if domain == "example.com" and record_type == "MX":
            return ["10 mail.example.com"]
        return []

    mock_dig.side_effect = mock_lookup

    zone = _zone()
    # Desired has different priority
    zone.records = [
        Record(label="@", type="MX", value="mail.example.com", priority=20)
    ]

    diff = compare_dns_state(zone)

    assert diff.has_changes()
    summary = diff.summary()
    # When priority differs, it should show as create + delete (not update)
    # because the value is the same but priority is different
    assert summary["create"] == 1
    assert summary["delete"] == 1


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_validate_dns_state_valid(mock_dig: any) -> None:
    """Test validating DNS state when everything matches."""

    def mock_lookup(domain: str, record_type: str) -> list[str]:
        if domain == "example.com" and record_type == "A":
            return ["1.2.3.4"]
        return []

    mock_dig.side_effect = mock_lookup

    zone = _zone()
    zone.records = [Record(label="@", type="A", value="1.2.3.4")]

    is_valid, warnings = validate_dns_state(zone)

    assert is_valid
    assert len(warnings) == 0


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_validate_dns_state_invalid(mock_dig: any) -> None:
    """Test validating DNS state when there are mismatches."""
    mock_dig.return_value = []

    zone = _zone()
    zone.records = [Record(label="@", type="A", value="1.2.3.4")]

    is_valid, warnings = validate_dns_state(zone)

    assert not is_valid
    assert len(warnings) > 0
    assert "Missing" in warnings[1]


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_compare_dns_state_multiple_records(mock_dig: any) -> None:
    """Test comparing DNS state with multiple records."""

    def mock_lookup(domain: str, record_type: str) -> list[str]:
        if domain == "example.com" and record_type == "A":
            return ["1.2.3.4"]
        if domain == "www.example.com" and record_type == "CNAME":
            return ["example.com"]
        return []

    mock_dig.side_effect = mock_lookup

    zone = _zone()
    zone.records = [
        Record(label="@", type="A", value="1.2.3.4"),
        Record(label="www", type="CNAME", value="example.com"),
        Record(label="new", type="A", value="5.6.7.8"),  # New record
    ]

    diff = compare_dns_state(zone)

    assert diff.has_changes()
    summary = diff.summary()
    assert summary["create"] == 1  # 'new' record
    assert summary["delete"] == 0
    assert summary["update"] == 0


@patch("tuneup_alpha.dns_state.dig_lookup")
def test_query_current_dns_state_with_txt_record(mock_dig: any) -> None:
    """Test querying DNS state with TXT record (quotes should be removed)."""

    def mock_lookup(domain: str, record_type: str) -> list[str]:
        if domain == "example.com" and record_type == "TXT":
            return ['"v=spf1 include:_spf.example.com ~all"']
        return []

    mock_dig.side_effect = mock_lookup

    zone = _zone()
    zone.records = [
        Record(label="@", type="TXT", value="v=spf1 include:_spf.example.com ~all")
    ]

    result = query_current_dns_state(zone)

    txt_records = [r for r in result if r.type == "TXT"]
    assert len(txt_records) == 1
    assert txt_records[0].value == "v=spf1 include:_spf.example.com ~all"
