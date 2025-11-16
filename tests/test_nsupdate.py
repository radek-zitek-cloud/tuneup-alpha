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
