"""DNS state validation and comparison utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .dns_lookup import dig_lookup
from .logging_config import get_logger
from .models import Record, RecordChange, Zone

logger = get_logger(__name__)

ChangeType = Literal["create", "delete", "update", "no-change"]


@dataclass
class DNSRecordState:
    """Represents a DNS record as it exists in the live DNS system."""

    label: str
    type: str
    value: str
    ttl: int | None = None
    priority: int | None = None
    weight: int | None = None
    port: int | None = None


@dataclass
class DNSStateDiff:
    """Represents the difference between desired and current DNS state."""

    zone_name: str
    changes: list[RecordChange]
    current_records: list[DNSRecordState]
    desired_records: list[Record]

    def has_changes(self) -> bool:
        """Return True if there are any changes needed."""
        return len(self.changes) > 0

    def summary(self) -> dict[str, int]:
        """Return a summary of changes by action type."""
        summary = {"create": 0, "delete": 0, "update": 0}
        for change in self.changes:
            summary[change.action] = summary.get(change.action, 0) + 1
        return summary


def query_current_dns_state(zone: Zone) -> list[DNSRecordState]:
    """Query the current DNS state for all records in a zone.

    Args:
        zone: The zone to query

    Returns:
        List of DNSRecordState objects representing current DNS records
    """
    logger.info(f"Querying current DNS state for zone: {zone.name}")
    current_records: list[DNSRecordState] = []

    # Get all unique labels from desired records to query
    labels_to_query = set()
    for record in zone.records:
        labels_to_query.add(record.label)

    # Also query the apex
    labels_to_query.add("@")

    # For each label, query all relevant record types
    record_types = ["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "NS", "CAA"]

    for label in labels_to_query:
        fqdn = zone.name if label == "@" else f"{label}.{zone.name}"

        for record_type in record_types:
            try:
                results = dig_lookup(fqdn, record_type)
                if results:
                    logger.debug(
                        f"Found {len(results)} {record_type} record(s) for {fqdn}"
                    )
                    for value in results:
                        # Parse the result based on record type
                        current_records.append(
                            _parse_dns_record(label, record_type, value)
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to query {record_type} records for {fqdn}: {e}"
                )

    logger.info(
        f"Found {len(current_records)} current DNS record(s) for zone: {zone.name}"
    )
    return current_records


def compare_dns_state(zone: Zone) -> DNSStateDiff:
    """Compare current DNS state with desired configuration.

    Args:
        zone: The zone with desired configuration

    Returns:
        DNSStateDiff object with comparison results
    """
    logger.info(f"Comparing DNS state for zone: {zone.name}")

    current_records = query_current_dns_state(zone)
    desired_records = zone.records
    changes: list[RecordChange] = []

    # Create sets for easier comparison
    # Use enhanced key that includes priority/weight/port for MX/SRV records
    current_set = {
        _record_key_enhanced(
            r.label, r.type, r.value, r.priority, r.weight, r.port
        ): r
        for r in current_records
    }
    desired_set = {
        _record_key_enhanced(
            r.label, r.type, r.value, r.priority, r.weight, r.port
        ): r
        for r in desired_records
    }

    # Find records to create (in desired but not in current)
    for key, desired_record in desired_set.items():
        if key not in current_set:
            logger.debug(
                f"Record to create: {desired_record.label} {desired_record.type} {desired_record.value}"
            )
            changes.append(RecordChange(action="create", record=desired_record))
        else:
            # Record exists, check if it needs updating (TTL or other fields)
            current_record = current_set[key]
            if _needs_update(current_record, desired_record):
                logger.debug(
                    f"Record to update: {desired_record.label} {desired_record.type} {desired_record.value}"
                )
                # Convert current DNSRecordState to Record for comparison
                previous = _dns_state_to_record(current_record)
                changes.append(
                    RecordChange(
                        action="update", record=desired_record, previous=previous
                    )
                )

    # Find records to delete (in current but not in desired)
    for key, current_record in current_set.items():
        if key not in desired_set:
            logger.debug(
                f"Record to delete: {current_record.label} {current_record.type} {current_record.value}"
            )
            # Convert DNSRecordState to Record for deletion
            record_to_delete = _dns_state_to_record(current_record)
            changes.append(RecordChange(action="delete", record=record_to_delete))

    logger.info(f"Found {len(changes)} change(s) for zone: {zone.name}")
    return DNSStateDiff(
        zone_name=zone.name,
        changes=changes,
        current_records=current_records,
        desired_records=desired_records,
    )


def validate_dns_state(zone: Zone) -> tuple[bool, list[str]]:
    """Validate that current DNS state matches desired configuration.

    Args:
        zone: The zone to validate

    Returns:
        Tuple of (is_valid, list of validation errors/warnings)
    """
    logger.info(f"Validating DNS state for zone: {zone.name}")
    diff = compare_dns_state(zone)

    warnings: list[str] = []
    is_valid = not diff.has_changes()

    if not is_valid:
        summary = diff.summary()
        warnings.append(
            f"DNS state mismatch: {summary['create']} to create, "
            f"{summary['update']} to update, {summary['delete']} to delete"
        )

        for change in diff.changes:
            if change.action == "create":
                warnings.append(
                    f"  Missing: {change.record.label} {change.record.type} {change.record.value}"
                )
            elif change.action == "delete":
                warnings.append(
                    f"  Extra: {change.record.label} {change.record.type} {change.record.value}"
                )
            elif change.action == "update":
                warnings.append(
                    f"  Different: {change.record.label} {change.record.type} {change.record.value}"
                )

    logger.info(f"Validation result for zone {zone.name}: valid={is_valid}")
    return is_valid, warnings


def _record_key(label: str, record_type: str, value: str) -> str:
    """Generate a unique key for a DNS record."""
    return f"{label}:{record_type}:{value}"


def _record_key_enhanced(
    label: str,
    record_type: str,
    value: str,
    priority: int | None = None,
    weight: int | None = None,
    port: int | None = None,
) -> str:
    """Generate a unique key for a DNS record including priority/weight/port.

    Args:
        label: DNS label
        record_type: Record type
        value: Record value
        priority: Priority (for MX/SRV)
        weight: Weight (for SRV)
        port: Port (for SRV)

    Returns:
        Unique key string
    """
    key_parts = [label, record_type, value]

    # Include priority for MX and SRV records
    if priority is not None:
        key_parts.append(f"p{priority}")

    # Include weight for SRV records
    if weight is not None:
        key_parts.append(f"w{weight}")

    # Include port for SRV records
    if port is not None:
        key_parts.append(f"port{port}")

    return ":".join(key_parts)


def _parse_dns_record(label: str, record_type: str, value: str) -> DNSRecordState:
    """Parse a DNS lookup result into a DNSRecordState.

    Args:
        label: The DNS label
        record_type: The record type
        value: The raw value from dig

    Returns:
        DNSRecordState object
    """
    # Parse MX records (format: "priority hostname")
    if record_type == "MX":
        parts = value.split(None, 1)
        if len(parts) == 2:
            priority = int(parts[0])
            hostname = parts[1].rstrip(".")
            return DNSRecordState(
                label=label, type=record_type, value=hostname, priority=priority
            )

    # Parse SRV records (format: "priority weight port target")
    if record_type == "SRV":
        parts = value.split(None, 3)
        if len(parts) == 4:
            priority = int(parts[0])
            weight = int(parts[1])
            port = int(parts[2])
            target = parts[3].rstrip(".")
            return DNSRecordState(
                label=label,
                type=record_type,
                value=target,
                priority=priority,
                weight=weight,
                port=port,
            )

    # Parse CAA records (format: "flags tag value")
    if record_type == "CAA":
        # CAA records from dig come in format: flags tag "value"
        # We need to preserve the full format as the value
        return DNSRecordState(label=label, type=record_type, value=value)

    # Parse TXT records (remove quotes)
    if record_type == "TXT":
        # dig returns TXT records with quotes, remove them
        cleaned_value = value.strip('"')
        return DNSRecordState(label=label, type=record_type, value=cleaned_value)

    # For A, AAAA, CNAME, NS records, just use the value as-is
    return DNSRecordState(label=label, type=record_type, value=value)


def _dns_state_to_record(dns_state: DNSRecordState) -> Record:
    """Convert DNSRecordState to Record model.

    Args:
        dns_state: DNSRecordState object

    Returns:
        Record object
    """
    return Record(
        label=dns_state.label,
        type=dns_state.type,  # type: ignore[arg-type]
        value=dns_state.value,
        ttl=dns_state.ttl or 300,  # Default TTL if not known
        priority=dns_state.priority,
        weight=dns_state.weight,
        port=dns_state.port,
    )


def _needs_update(current: DNSRecordState, desired: Record) -> bool:
    """Check if a record needs updating.

    Args:
        current: Current DNS record state
        desired: Desired record configuration

    Returns:
        True if the record needs updating
    """
    # For now, we only compare based on label, type, and value
    # TTL differences are not considered critical enough to warrant updates
    # unless explicitly different in the config

    # Check if priority differs (for MX/SRV records)
    if current.priority is not None and desired.priority is not None and current.priority != desired.priority:
        return True

    # Check if weight differs (for SRV records)
    if current.weight is not None and desired.weight is not None and current.weight != desired.weight:
        return True

    # Check if port differs (for SRV records)
    return (
        current.port is not None
        and desired.port is not None
        and current.port != desired.port
    )
