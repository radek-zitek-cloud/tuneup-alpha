"""Core data models for TuneUp Alpha."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

RecordType = Literal["A", "CNAME"]
RecordAction = Literal["create", "delete", "update"]


class Record(BaseModel):
    """Single DNS record managed by the application."""

    label: str = Field(
        ...,
        description="Relative record label (use '@' for the zone apex).",
        min_length=1,
    )
    type: RecordType = Field(..., description="DNS record type.")
    value: str = Field(..., description="Target IPv4 or hostname value.")
    ttl: int = Field(300, ge=60, description="Record TTL in seconds.")

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
        # DNS label can contain alphanumeric, hyphens, and underscores
        # Must not start or end with hyphen
        pattern = r"^[a-zA-Z0-9_]([a-zA-Z0-9_-]*[a-zA-Z0-9_])?$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid DNS label '{v}'. Labels must contain only alphanumeric characters, hyphens, and underscores."
            )
        if len(v) > 63:
            raise ValueError(f"DNS label '{v}' exceeds maximum length of 63 characters")
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
        elif record_type == "CNAME":
            # CNAME can be @ or a valid hostname
            if v != "@":
                # Basic hostname validation
                hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.?$"
                if not re.match(hostname_pattern, v):
                    raise ValueError(
                        f"Invalid hostname '{v}' for CNAME record"
                    )

        return v


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


class AppConfig(BaseModel):
    """Complete persisted configuration for TuneUp Alpha."""

    zones: list[Zone] = Field(default_factory=list)
