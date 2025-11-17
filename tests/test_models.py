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
        Record(label="@", type="PTR", value="ptr.example.com")  # type: ignore


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
    assert config.prefix_key_path == "~/.config/nsupdate"


def test_app_config_custom_prefix_key_path() -> None:
    config = AppConfig(prefix_key_path="/custom/path/keys")
    assert config.prefix_key_path == "/custom/path/keys"


def test_app_config_with_prefix_key_path_and_zones() -> None:
    zone = Zone(name="example.com", server="ns1.example.com", key_file=Path("/etc/key.key"))
    config = AppConfig(zones=[zone], prefix_key_path="/etc/nsupdate")
    assert config.prefix_key_path == "/etc/nsupdate"
    assert len(config.zones) == 1


# Tests for new record types


def test_record_aaaa_validation() -> None:
    # Valid IPv6 addresses
    Record(label="@", type="AAAA", value="2001:0db8:85a3:0000:0000:8a2e:0370:7334")
    Record(label="@", type="AAAA", value="2001:db8:85a3::8a2e:370:7334")
    Record(label="@", type="AAAA", value="::1")
    Record(label="@", type="AAAA", value="fe80::1")
    Record(label="@", type="AAAA", value="::ffff:192.0.2.1")

    # Invalid IPv6 addresses
    with pytest.raises(ValidationError, match="Invalid IPv6 address"):
        Record(label="@", type="AAAA", value="not.an.ipv6.address")

    with pytest.raises(ValidationError, match="Invalid IPv6 address"):
        Record(label="@", type="AAAA", value="192.168.1.1")


def test_record_mx_validation() -> None:
    # Valid MX records
    Record(label="@", type="MX", value="mail.example.com", priority=10)
    Record(label="@", type="MX", value="mail.example.com.", priority=20)

    # Invalid MX - missing priority
    with pytest.raises(ValidationError, match="MX records require a priority"):
        Record(label="@", type="MX", value="mail.example.com")

    # Invalid MX - bad hostname
    with pytest.raises(ValidationError, match="Invalid mail server hostname"):
        Record(label="@", type="MX", value="-invalid.com", priority=10)


def test_record_txt_validation() -> None:
    # Valid TXT records
    Record(label="@", type="TXT", value="v=spf1 include:_spf.example.com ~all")
    Record(label="_dmarc", type="TXT", value="v=DMARC1; p=reject; rua=mailto:dmarc@example.com")
    Record(
        label="selector._domainkey",
        type="TXT",
        value="v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQ...",
    )

    # Test long TXT value (should work up to 4096 chars)
    long_value = "x" * 1000
    Record(label="@", type="TXT", value=long_value)

    # Invalid - too long
    with pytest.raises(ValidationError, match="TXT record value too long"):
        Record(label="@", type="TXT", value="x" * 5000)


def test_record_srv_validation() -> None:
    # Valid SRV records
    Record(
        label="_http._tcp",
        type="SRV",
        value="server.example.com",
        priority=10,
        weight=60,
        port=80,
    )
    Record(label="_xmpp._tcp", type="SRV", value=".", priority=0, weight=0, port=5269)

    # Invalid SRV - missing priority
    with pytest.raises(ValidationError, match="SRV records require a priority"):
        Record(label="_http._tcp", type="SRV", value="server.example.com", weight=60, port=80)

    # Invalid SRV - missing weight
    with pytest.raises(ValidationError, match="SRV records require a weight"):
        Record(label="_http._tcp", type="SRV", value="server.example.com", priority=10, port=80)

    # Invalid SRV - missing port
    with pytest.raises(ValidationError, match="SRV records require a port"):
        Record(label="_http._tcp", type="SRV", value="server.example.com", priority=10, weight=60)


def test_record_ns_validation() -> None:
    # Valid NS records
    Record(label="@", type="NS", value="ns1.example.com")
    Record(label="subdomain", type="NS", value="ns1.example.com.")

    # Invalid NS - bad hostname
    with pytest.raises(ValidationError, match="Invalid nameserver hostname"):
        Record(label="@", type="NS", value="-invalid.com")


def test_record_caa_validation() -> None:
    # Valid CAA records
    Record(label="@", type="CAA", value="0 issue letsencrypt.org")
    Record(label="@", type="CAA", value="0 issuewild ca.example.com")
    Record(label="@", type="CAA", value="0 iodef mailto:security@example.com")
    Record(label="@", type="CAA", value="128 issue ca.example.com")

    # Invalid CAA - wrong format
    with pytest.raises(ValidationError, match="Invalid CAA record format"):
        Record(label="@", type="CAA", value="0 issue")

    # Invalid CAA - bad flags
    with pytest.raises(ValidationError, match="CAA flags must be numeric"):
        Record(label="@", type="CAA", value="bad issue ca.example.com")

    with pytest.raises(ValidationError, match="CAA flags must be 0-255"):
        Record(label="@", type="CAA", value="256 issue ca.example.com")

    # Invalid CAA - bad tag
    with pytest.raises(ValidationError, match="CAA tag must be"):
        Record(label="@", type="CAA", value="0 badtag ca.example.com")


def test_record_type_validation_updated() -> None:
    # Valid types - including new ones
    Record(label="@", type="A", value="1.2.3.4")
    Record(label="@", type="AAAA", value="2001:db8::1")
    Record(label="www", type="CNAME", value="@")
    Record(label="@", type="MX", value="mail.example.com", priority=10)
    Record(label="@", type="TXT", value="v=spf1 ~all")
    Record(
        label="_http._tcp", type="SRV", value="server.example.com", priority=0, weight=0, port=80
    )
    Record(label="@", type="NS", value="ns1.example.com")
    Record(label="@", type="CAA", value="0 issue ca.example.com")

    # Invalid type should still raise validation error
    with pytest.raises(ValidationError):
        Record(label="@", type="PTR", value="example.com")  # type: ignore
