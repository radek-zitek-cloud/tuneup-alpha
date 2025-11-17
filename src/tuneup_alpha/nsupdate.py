"""Helpers for producing and executing nsupdate command scripts."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass

from .logging_config import AuditLogger, get_logger
from .models import Record, RecordChange, Zone

logger = get_logger(__name__)
audit_logger = AuditLogger()


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
        logger.debug(f"Rendering nsupdate plan for zone {self.zone.name}")
        lines = [f"server {self.zone.server}", f"zone {self.zone.name}"]
        for change in self.changes:
            lines.extend(_render_change(self.zone, change))
        lines.append("send")
        script = "\n".join(lines) + "\n"
        logger.debug(f"Generated nsupdate script with {len(self.changes)} change(s)")
        return script


class NsupdateClient:
    """Runs nsupdate with a generated plan."""

    def __init__(self, executable: str = "nsupdate") -> None:
        self.executable = executable

    def apply_plan(self, plan: NsupdatePlan, dry_run: bool = False) -> str:
        script = plan.render()

        if dry_run:
            logger.info(f"Dry-run mode: would execute nsupdate for zone {plan.zone.name}")
            audit_logger.log_nsupdate_execution(
                zone_name=plan.zone.name,
                dry_run=True,
                success=True,
                details={"change_count": len(plan.changes)},
            )
            return script

        logger.info(f"Executing nsupdate for zone {plan.zone.name}")
        cmd = [self.executable, "-k", str(plan.zone.key_file)]
        try:
            completed = subprocess.run(  # noqa: S603,S607
                cmd,
                input=script.encode(),
                capture_output=True,
                check=True,
            )
            logger.info(f"nsupdate completed successfully for zone {plan.zone.name}")
            audit_logger.log_nsupdate_execution(
                zone_name=plan.zone.name,
                dry_run=False,
                success=True,
                details={"change_count": len(plan.changes)},
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover - error path
            logger.error(
                f"nsupdate failed for zone {plan.zone.name}: {exc.stderr.decode() or str(exc)}"
            )
            audit_logger.log_nsupdate_execution(
                zone_name=plan.zone.name,
                dry_run=False,
                success=False,
                details={
                    "change_count": len(plan.changes),
                    "error": exc.stderr.decode() or str(exc),
                },
            )
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
    
    # Handle record types with special formatting
    if record.type == "MX":
        # MX records need priority before the value
        priority = record.priority if record.priority is not None else 10
        return f"update add {fqdn} {ttl} {record.type} {priority} {record.value}"
    elif record.type == "SRV":
        # SRV records need priority, weight, and port before the value
        priority = record.priority if record.priority is not None else 0
        weight = record.weight if record.weight is not None else 0
        port = record.port if record.port is not None else 0
        return f"update add {fqdn} {ttl} {record.type} {priority} {weight} {port} {record.value}"
    elif record.type == "TXT":
        # TXT records need to be quoted
        # Handle multi-line or long text by proper quoting
        quoted_value = _quote_txt_value(record.value)
        return f"update add {fqdn} {ttl} {record.type} {quoted_value}"
    elif record.type == "CAA":
        # CAA records: value already contains "flags tag value" format
        return f"update add {fqdn} {ttl} {record.type} {record.value}"
    else:
        # A, AAAA, CNAME, NS records
        return f"update add {fqdn} {ttl} {record.type} {record.value}"


def _fqdn(zone: Zone, record: Record) -> str:
    if record.is_apex:
        return zone.name.rstrip(".") + "."
    return f"{record.label}.{zone.name}".rstrip(".") + "."


def _quote_txt_value(value: str) -> str:
    """Quote TXT record value for nsupdate.
    
    TXT records can be split into multiple strings if longer than 255 characters.
    Each string must be quoted.
    """
    # If the value contains quotes, escape them
    escaped = value.replace('"', '\\"')
    
    # Split into chunks of 255 characters if needed
    if len(escaped) <= 255:
        return f'"{escaped}"'
    
    # Split into multiple quoted strings
    chunks = []
    for i in range(0, len(escaped), 255):
        chunk = escaped[i:i+255]
        chunks.append(f'"{chunk}"')
    
    return " ".join(chunks)
