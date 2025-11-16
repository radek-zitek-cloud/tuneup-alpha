"""Core data models for TuneUp Alpha."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

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
