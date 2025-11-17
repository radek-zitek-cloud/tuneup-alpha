"""Core data models for TuneUp Alpha."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

RecordType = Literal["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "NS", "CAA"]
RecordAction = Literal["create", "delete", "update"]


class Record(BaseModel):
    """Single DNS record managed by the application."""

    label: str = Field(
        ...,
        description="Relative record label (use '@' for the zone apex).",
        min_length=1,
    )
    type: RecordType = Field(..., description="DNS record type.")
    value: str = Field(..., description="Target IPv4, IPv6, hostname, or text value.")
    ttl: int = Field(300, ge=60, description="Record TTL in seconds.")
    # Optional fields for specific record types
    priority: int | None = Field(None, ge=0, description="Priority for MX and SRV records.")
    weight: int | None = Field(None, ge=0, description="Weight for SRV records.")
    port: int | None = Field(None, ge=1, le=65535, description="Port for SRV records.")

    @property
    def is_apex(self) -> bool:
        """True when the record applies to the zone apex."""

        return self.label == "@"

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        """Validate DNS label format."""

        if v == "@":
            return v

        if v.startswith("."):
            raise ValueError("DNS labels cannot start with a dot")

        trimmed_value = v[:-1] if v.endswith(".") else v
        if not trimmed_value:
            raise ValueError("DNS labels must contain at least one character")

        label_pattern = re.compile(r"^[A-Za-z0-9@_-]+$")

        for part in trimmed_value.split("."):
            if not part:
                raise ValueError("DNS labels cannot contain empty segments (consecutive dots)")
            if part.startswith("-") or part.endswith("-"):
                raise ValueError("DNS label segments cannot start or end with a hyphen")
            if len(part) > 63:
                raise ValueError(
                    f"DNS label segment '{part}' exceeds maximum length of 63 characters"
                )
            if not label_pattern.match(part):
                raise ValueError(
                    f"Invalid DNS label '{v}'. Labels may contain letters, digits, hyphens, dots, underscores, and '@'."
                )

        return v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str, info) -> str:
        """Validate record value based on type."""
        if "type" not in info.data:
            return v

        record_type = info.data["type"]

        if record_type == "A":
            # Validate IPv4 address format
            ipv4_pattern = r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$"
            match = re.match(ipv4_pattern, v)
            if not match:
                raise ValueError(f"Invalid IPv4 address '{v}'")
            # Check each octet is 0-255
            for octet in match.groups():
                if int(octet) > 255:
                    raise ValueError(f"Invalid IPv4 address '{v}' - octet out of range")
        elif record_type == "AAAA":
            # Validate IPv6 address format
            # Basic IPv6 validation - accepts full and compressed forms
            ipv6_pattern = r"^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$"
            if not re.match(ipv6_pattern, v):
                raise ValueError(f"Invalid IPv6 address '{v}'")
        elif record_type == "CNAME":
            # CNAME can be @ or a valid hostname
            if v != "@":
                # Basic hostname validation
                hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.?$"
                if not re.match(hostname_pattern, v):
                    raise ValueError(f"Invalid hostname '{v}' for CNAME record")
        elif record_type == "MX":
            # MX value is a mail server hostname
            if v != "@":
                hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.?$"
                if not re.match(hostname_pattern, v):
                    raise ValueError(f"Invalid mail server hostname '{v}' for MX record")
        elif record_type == "NS":
            # NS value is a nameserver hostname
            if v != "@":
                hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.?$"
                if not re.match(hostname_pattern, v):
                    raise ValueError(f"Invalid nameserver hostname '{v}' for NS record")
        elif record_type == "SRV":
            # SRV value is a target hostname
            if v != "@" and v != ".":
                hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.?$"
                if not re.match(hostname_pattern, v):
                    raise ValueError(f"Invalid target hostname '{v}' for SRV record")
        elif record_type == "TXT":
            # TXT records can contain any text, but check for reasonable length
            # DNS TXT records have a limit of 255 characters per string, but multiple strings can be used
            if len(v) > 4096:  # Reasonable upper limit for total TXT record length
                raise ValueError(
                    f"TXT record value too long ({len(v)} characters). Maximum is 4096."
                )
        elif record_type == "CAA":
            # CAA format: flags tag value (e.g., "0 issue ca.example.com")
            # The value field should contain: flags tag value (space-separated)
            parts = v.split(None, 2)
            if len(parts) != 3:
                raise ValueError(
                    f"Invalid CAA record format '{v}'. Expected: 'flags tag value' (e.g., '0 issue ca.example.com')"
                )
            flags, tag, value = parts
            # Validate flags (should be 0-255)
            try:
                flag_int = int(flags)
            except ValueError as exc:
                raise ValueError(f"CAA flags must be numeric, got '{flags}'") from exc

            if flag_int < 0 or flag_int > 255:
                raise ValueError(f"CAA flags must be 0-255, got {flags}")

            # Validate tag (issue, issuewild, iodef)
            if tag not in ("issue", "issuewild", "iodef"):
                raise ValueError(f"CAA tag must be 'issue', 'issuewild', or 'iodef', got '{tag}'")

        return v

    @model_validator(mode="after")
    def validate_required_fields(self) -> Record:
        """Validate that required fields are present for specific record types."""
        if self.type == "MX" and self.priority is None:
            raise ValueError("MX records require a priority value")
        if self.type == "SRV":
            if self.priority is None:
                raise ValueError("SRV records require a priority value")
            if self.weight is None:
                raise ValueError("SRV records require a weight value")
            if self.port is None:
                raise ValueError("SRV records require a port value")
        return self


class Zone(BaseModel):
    """Represents a DNS zone managed through nsupdate."""

    name: str = Field(..., description="FQDN of the zone (example.com).")
    server: str = Field(..., description="Authoritative name server to target.")
    key_file: Path = Field(..., description="Path to the nsupdate key file.")
    notes: str | None = Field(default=None, description="Human friendly metadata about the zone.")
    default_ttl: int = Field(3600, ge=60, description="Default TTL when not set.")
    records: list[Record] = Field(default_factory=list)


class RecordChange(BaseModel):
    """Represents a desired modification for a record within a zone."""

    action: RecordAction
    record: Record
    previous: Record | None = None


class LoggingConfig(BaseModel):
    """Logging configuration."""

    enabled: bool = Field(default=True, description="Enable logging")
    level: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    output: str = Field(default="console", description="Log output (console, file, both)")
    log_file: Path | None = Field(
        default=None, description="Path to log file (required if output is file or both)"
    )
    max_bytes: int = Field(
        default=10 * 1024 * 1024, description="Maximum log file size before rotation"
    )
    backup_count: int = Field(default=5, description="Number of backup log files to keep")
    structured: bool = Field(default=False, description="Use structured JSON logging")


class AppConfig(BaseModel):
    """Complete persisted configuration for TuneUp Alpha."""

    zones: list[Zone] = Field(default_factory=list)
    theme: str = Field(default="textual-dark", description="UI theme name")
    prefix_key_path: str = Field(
        default="~/.config/nsupdate", description="Default path prefix for nsupdate key files"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
