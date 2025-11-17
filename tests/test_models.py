from pathlib import Path

import pytest
from pydantic import ValidationError

from tuneup_alpha.models import AppConfig, Record, RecordChange, Zone


def test_record_defaults() -> None:
    record = Record(label="@", type="A", value="1.2.3.4")
    assert record.ttl == 300
    assert record.is_apex is True


def test_record_custom_ttl() -> None:
    record = Record(label="www", type="CNAME", value="@", ttl=600)
    assert record.ttl == 600
    assert record.is_apex is False


def test_record_validation_min_ttl() -> None:
    with pytest.raises(ValidationError):
        Record(label="@", type="A", value="1.2.3.4", ttl=30)


def test_record_validation_label_required() -> None:
    with pytest.raises(ValidationError):
        Record(label="", type="A", value="1.2.3.4")  # type: ignore


def test_zone_defaults() -> None:
    zone = Zone(name="example.com", server="ns1.example.com", key_file=Path("/etc/key.key"))
    assert zone.default_ttl == 3600
    assert zone.notes is None
    assert zone.records == []


def test_zone_with_notes() -> None:
    zone = Zone(
        name="example.com",
        server="ns1.example.com",
        key_file=Path("/etc/key.key"),
        notes="Test zone",
    )
    assert zone.notes == "Test zone"


def test_zone_with_records() -> None:
    zone = Zone(
        name="example.com",
        server="ns1.example.com",
        key_file=Path("/etc/key.key"),
        records=[Record(label="@", type="A", value="1.2.3.4")],
    )
    assert len(zone.records) == 1
    assert zone.records[0].label == "@"


def test_record_change_create() -> None:
    record = Record(label="@", type="A", value="1.2.3.4")
    change = RecordChange(action="create", record=record)
    assert change.action == "create"
    assert change.record == record
    assert change.previous is None


def test_record_change_update() -> None:
    old_record = Record(label="@", type="A", value="1.2.3.4")
    new_record = Record(label="@", type="A", value="5.6.7.8")
    change = RecordChange(action="update", record=new_record, previous=old_record)
    assert change.action == "update"
    assert change.record == new_record
    assert change.previous == old_record


def test_record_change_delete() -> None:
    record = Record(label="@", type="A", value="1.2.3.4")
    change = RecordChange(action="delete", record=record)
    assert change.action == "delete"
    assert change.record == record


def test_app_config_empty() -> None:
    config = AppConfig()
    assert config.zones == []


def test_app_config_with_zones() -> None:
    zone = Zone(name="example.com", server="ns1.example.com", key_file=Path("/etc/key.key"))
    config = AppConfig(zones=[zone])
    assert len(config.zones) == 1
    assert config.zones[0].name == "example.com"


def test_record_type_validation() -> None:
    # Valid types
    Record(label="@", type="A", value="1.2.3.4")
    Record(label="www", type="CNAME", value="@")

    # Invalid type should raise validation error
    with pytest.raises(ValidationError):
        Record(label="@", type="MX", value="mail.example.com")  # type: ignore


def test_record_action_validation() -> None:
    record = Record(label="@", type="A", value="1.2.3.4")

    # Valid actions
    RecordChange(action="create", record=record)
    RecordChange(action="delete", record=record)
    RecordChange(action="update", record=record)

    # Invalid action should raise validation error
    with pytest.raises(ValidationError):
        RecordChange(action="invalid", record=record)  # type: ignore


def test_record_ipv4_validation() -> None:
    # Valid IPv4 addresses
    Record(label="@", type="A", value="1.2.3.4")
    Record(label="@", type="A", value="192.168.1.1")
    Record(label="@", type="A", value="255.255.255.255")
    Record(label="@", type="A", value="0.0.0.0")

    # Invalid IPv4 addresses
    with pytest.raises(ValidationError, match="Invalid IPv4 address"):
        Record(label="@", type="A", value="256.1.1.1")

    with pytest.raises(ValidationError, match="Invalid IPv4 address"):
        Record(label="@", type="A", value="1.2.3")

    with pytest.raises(ValidationError, match="Invalid IPv4 address"):
        Record(label="@", type="A", value="not.an.ip.address")


def test_record_label_validation() -> None:
    # Valid labels
    Record(label="@", type="A", value="1.2.3.4")
    Record(label="www", type="A", value="1.2.3.4")
    Record(label="mail-server", type="A", value="1.2.3.4")
    Record(label="test_record", type="A", value="1.2.3.4")
    Record(label="api.v1", type="A", value="1.2.3.4")
    Record(label="svc-01.edge", type="A", value="1.2.3.4")
    Record(label="node@cluster", type="A", value="1.2.3.4")
    Record(label="srv1", type="A", value="1.2.3.4")
    Record(label="srv1.", type="A", value="1.2.3.4")
    Record(label="multi.segment.", type="A", value="1.2.3.4")

    # Invalid labels
    with pytest.raises(ValidationError, match="cannot start or end with a hyphen"):
        Record(label="-invalid", type="A", value="1.2.3.4")

    with pytest.raises(ValidationError, match="cannot start or end with a hyphen"):
        Record(label="invalid-", type="A", value="1.2.3.4")

    with pytest.raises(ValidationError, match="empty segments"):
        Record(label="invalid..label", type="A", value="1.2.3.4")

    # Label too long
    with pytest.raises(ValidationError, match="exceeds maximum length"):
        Record(label="a" * 64, type="A", value="1.2.3.4")

    with pytest.raises(ValidationError, match="start with a dot"):
        Record(label=".invalid", type="A", value="1.2.3.4")

    with pytest.raises(ValidationError, match="start with a dot"):
        Record(label=".", type="A", value="1.2.3.4")


def test_record_cname_validation() -> None:
    # Valid CNAME values
    Record(label="www", type="CNAME", value="@")
    Record(label="www", type="CNAME", value="example.com")
    Record(label="www", type="CNAME", value="example.com.")
    Record(label="www", type="CNAME", value="subdomain.example.com")
    Record(label="www", type="CNAME", value="target.example.")

    # Invalid CNAME values
    with pytest.raises(ValidationError, match="Invalid hostname"):
        Record(label="www", type="CNAME", value="-invalid.com")

    with pytest.raises(ValidationError, match="Invalid hostname"):
        Record(label="www", type="CNAME", value="invalid-.com")

    with pytest.raises(ValidationError, match="Invalid hostname"):
        Record(label="www", type="CNAME", value=".invalid.com")


def test_app_config_default_prefix_key_path() -> None:
    config = AppConfig()
    assert config.prefix_key_path == "/etc/nsupdate"


def test_app_config_custom_prefix_key_path() -> None:
    config = AppConfig(prefix_key_path="/custom/path/keys")
    assert config.prefix_key_path == "/custom/path/keys"


def test_app_config_with_prefix_key_path_and_zones() -> None:
    zone = Zone(name="example.com", server="ns1.example.com", key_file=Path("/etc/key.key"))
    config = AppConfig(zones=[zone], prefix_key_path="/etc/nsupdate")
    assert config.prefix_key_path == "/etc/nsupdate"
    assert len(config.zones) == 1
