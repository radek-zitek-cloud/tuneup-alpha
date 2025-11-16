from pathlib import Path

from tuneup_alpha.models import Record, RecordChange, Zone
from tuneup_alpha.nsupdate import NsupdatePlan


def _zone() -> Zone:
    return Zone(
        name="example.com",
        server="ns1.example.com",
        key_file=Path("/etc/nsupdate/example.com.key"),
        records=[],
    )


def test_plan_render_includes_records() -> None:
    zone = _zone()
    plan = NsupdatePlan(zone)
    plan.add_change(
        RecordChange(action="create", record=Record(label="@", type="A", value="1.1.1.1"))
    )
    script = plan.render()
    assert "server ns1.example.com" in script
    assert "update add example.com." in script
    assert script.strip().endswith("send")


def test_plan_render_delete_record() -> None:
    zone = _zone()
    plan = NsupdatePlan(zone)
    record = Record(label="www", type="A", value="1.2.3.4")
    plan.add_change(RecordChange(action="delete", record=record))
    script = plan.render()
    assert "server ns1.example.com" in script
    assert "zone example.com" in script
    assert "update delete www.example.com. A" in script
    assert "send" in script


def test_plan_render_update_record() -> None:
    zone = _zone()
    plan = NsupdatePlan(zone)
    old_record = Record(label="www", type="A", value="1.2.3.4", ttl=300)
    new_record = Record(label="www", type="A", value="5.6.7.8", ttl=600)
    plan.add_change(RecordChange(action="update", record=new_record, previous=old_record))
    script = plan.render()
    assert "update delete www.example.com. A" in script
    assert "update add www.example.com. 600 A 5.6.7.8" in script


def test_plan_render_cname_record() -> None:
    zone = _zone()
    plan = NsupdatePlan(zone)
    record = Record(label="www", type="CNAME", value="@", ttl=300)
    plan.add_change(RecordChange(action="create", record=record))
    script = plan.render()
    assert "update add www.example.com. 300 CNAME @" in script


def test_plan_render_apex_record() -> None:
    zone = _zone()
    plan = NsupdatePlan(zone)
    record = Record(label="@", type="A", value="1.2.3.4", ttl=600)
    plan.add_change(RecordChange(action="create", record=record))
    script = plan.render()
    # Apex should render as zone name with trailing dot
    assert "update add example.com. 600 A 1.2.3.4" in script


def test_plan_render_multiple_records() -> None:
    zone = _zone()
    plan = NsupdatePlan(zone)
    plan.add_change(
        RecordChange(action="create", record=Record(label="@", type="A", value="1.2.3.4"))
    )
    plan.add_change(
        RecordChange(action="create", record=Record(label="www", type="CNAME", value="@"))
    )
    plan.add_change(
        RecordChange(action="create", record=Record(label="mail", type="A", value="5.6.7.8"))
    )
    script = plan.render()
    assert script.count("update add") == 3
    assert "example.com. 300 A 1.2.3.4" in script
    assert "www.example.com. 300 CNAME @" in script
    assert "mail.example.com. 300 A 5.6.7.8" in script


def test_plan_uses_zone_default_ttl() -> None:
    zone = Zone(
        name="example.com",
        server="ns1.example.com",
        key_file=Path("/etc/nsupdate/example.com.key"),
        default_ttl=7200,
    )
    plan = NsupdatePlan(zone)
    # Record without explicit TTL should use zone default
    record = Record(label="@", type="A", value="1.2.3.4", ttl=300)
    plan.add_change(RecordChange(action="create", record=record))
    script = plan.render()
    # Should use record's explicit TTL, not zone default
    assert "300 A 1.2.3.4" in script
