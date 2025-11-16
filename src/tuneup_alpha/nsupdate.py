"""Helpers for producing and executing nsupdate command scripts."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Iterable

from .models import Record, RecordChange, Zone


class NsupdateError(RuntimeError):
    """Raised when nsupdate exits with an error."""


@dataclass
class NsupdatePlan:
    """Sequence of changes that can be rendered into an nsupdate script."""

    zone: Zone
    changes: list[RecordChange]

    def __init__(self, zone: Zone, changes: Iterable[RecordChange] | None = None) -> None:
        self.zone = zone
        self.changes = list(changes or [])

    def add_change(self, change: RecordChange) -> None:
        self.changes.append(change)

    def render(self) -> str:
        lines = [f"server {self.zone.server}", f"zone {self.zone.name}"]
        for change in self.changes:
            lines.extend(_render_change(self.zone, change))
        lines.append("send")
        return "\n".join(lines) + "\n"


class NsupdateClient:
    """Runs nsupdate with a generated plan."""

    def __init__(self, executable: str = "nsupdate") -> None:
        self.executable = executable

    def apply_plan(self, plan: NsupdatePlan, dry_run: bool = False) -> str:
        script = plan.render()

        if dry_run:
            return script

        cmd = [self.executable, "-k", str(plan.zone.key_file)]
        try:
            completed = subprocess.run(  # noqa: S603,S607
                cmd,
                input=script.encode(),
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover - error path
            raise NsupdateError(exc.stderr.decode() or str(exc)) from exc

        return completed.stdout.decode()


def _render_change(zone: Zone, change: RecordChange) -> list[str]:
    """Translate a RecordChange into nsupdate script lines."""

    lines: list[str] = []
    if change.action in ("delete", "update"):
        target = change.previous or change.record
        lines.append(_delete_line(zone, target))
    if change.action in ("create", "update"):
        lines.append(_add_line(zone, change.record))
    return lines


def _delete_line(zone: Zone, record: Record) -> str:
    fqdn = _fqdn(zone, record)
    return f"update delete {fqdn} {record.type}"


def _add_line(zone: Zone, record: Record) -> str:
    fqdn = _fqdn(zone, record)
    ttl = record.ttl or zone.default_ttl
    return f"update add {fqdn} {ttl} {record.type} {record.value}"


def _fqdn(zone: Zone, record: Record) -> str:
    if record.is_apex:
        return zone.name.rstrip(".") + "."
    return f"{record.label}.{zone.name}".rstrip(".") + "."
