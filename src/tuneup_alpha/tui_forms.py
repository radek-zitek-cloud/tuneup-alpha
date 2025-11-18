"""Reusable modal screens for the Textual dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from .dns_lookup import (
    dns_lookup,
    dns_lookup_label,
    dns_lookup_label_with_type,
    lookup_a_records,
    lookup_nameservers,
)
from .models import Record, RecordType, Zone

ZoneFormResult = tuple[str | None, Zone]
RecordFormResult = tuple[int | None, Record, str | None]


class ZoneFormScreen(ModalScreen[ZoneFormResult | None]):
    """Modal dialog that captures the fields required to define or edit a zone."""

    BINDINGS = [
        Binding("tab", "focus_next_field", "Next field", show=False, priority=True),
        Binding("shift+tab", "focus_previous_field", "Previous field", show=False, priority=True),
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    _FIELD_IDS = [
        "zone-name",
        "zone-server",
        "zone-key",
        "zone-ttl",
        "zone-notes",
    ]

    def __init__(
        self,
        mode: Literal["add", "edit"],
        zone: Zone | None = None,
        prefix_key_path: str = "~/.config/nsupdate",
    ) -> None:
        super().__init__()
        self.mode = mode
        self._initial_zone = zone
        self._original_name = zone.name if zone else None
        self._prefix_key_path = prefix_key_path
        self._error: Static | None = None
        self._info: Static | None = None
        self._discovered_ns: list[str] = []
        self._discovered_a_records: list[str] = []

    def compose(self) -> ComposeResult:
        title = "Add Managed Zone" if self.mode == "add" else "Edit Managed Zone"
        button_label = "Save" if self.mode == "add" else "Update"
        with Vertical(id="zone-form-dialog"):
            yield Static(title, id="modal-title")
            self._error = Static("", id="modal-error")
            yield self._error
            self._info = Static("", id="modal-info")
            yield self._info
            yield Static("Zone name (example.com)")
            yield Input(
                id="zone-name",
                placeholder="example.com",
                value=self._initial_zone.name if self._initial_zone else "",
            )
            yield Static("Authoritative server")
            yield Input(
                id="zone-server",
                placeholder="ns1.example.com",
                value=self._initial_zone.server if self._initial_zone else "",
            )
            yield Static("nsupdate key file path")
            yield Input(
                id="zone-key",
                placeholder="/etc/nsupdate/example.key",
                value=str(self._initial_zone.key_file) if self._initial_zone else "",
            )
            yield Static("Default TTL (seconds)")
            yield Input(
                id="zone-ttl",
                placeholder="3600",
                value=str(self._initial_zone.default_ttl) if self._initial_zone else "3600",
            )
            yield Static("Notes (optional)")
            notes_value = (
                self._initial_zone.notes if self._initial_zone and self._initial_zone.notes else ""
            )
            yield Input(
                id="zone-notes",
                placeholder="Purpose, owner, etc.",
                value=notes_value,
            )
            with Horizontal(id="modal-actions"):
                yield Button("Cancel", id="cancel")
                yield Button(button_label, id="save", variant="success")

    def on_mount(self) -> None:
        self.query_one("#zone-name", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "save":
            self._submit()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes to clear error messages and perform zone lookup."""
        if self._error:
            self._error.update("")

        if event.input.id == "zone-name":
            self._perform_zone_lookup(event.value, generate_key_path=False)

    def on_input_blurred(self, event: Input.Blurred) -> None:
        """Handle input blur to perform DNS lookup on zone name field."""
        if event.input.id == "zone-name":
            self._perform_zone_lookup(event.input.value, generate_key_path=True)

    def _perform_zone_lookup(self, domain: str, *, generate_key_path: bool = True) -> None:
        """Perform DNS lookup for zone and update fields with discovered values.

        Args:
            domain: The domain name to lookup
            generate_key_path: Whether to generate the default key file path.
                Should be True when called from blur handler, False when called
                from change handler to avoid updating the path on every keystroke.
        """
        if self._error:
            self._error.update("")
        if self._info:
            self._info.update("")

        if not domain or not domain.strip():
            self._discovered_ns = []
            self._discovered_a_records = []
            return

        if self._original_name and domain.strip() == self._original_name:
            return

        if self._info:
            self._info.update("[yellow]⏳ Looking up DNS records...[/yellow]")

        domain = domain.strip()

        nameservers = lookup_nameservers(domain)
        self._discovered_ns = nameservers

        a_records = lookup_a_records(domain)
        self._discovered_a_records = a_records

        server_input = self.query_one("#zone-server", Input)
        if nameservers and not server_input.value.strip():
            server_input.value = nameservers[0]

        if self.mode == "add" and generate_key_path:
            key_input = self.query_one("#zone-key", Input)
            if not key_input.value.strip():
                key_input.value = f"{self._prefix_key_path}/{domain}.key"

        self._show_zone_lookup_info(nameservers, a_records)

    def _show_zone_lookup_info(self, nameservers: list[str], a_records: list[str]) -> None:
        if not self._info:
            return

        messages = []

        if nameservers:
            ns_list = ", ".join(nameservers[:2])
            if len(nameservers) > 2:
                ns_list += f" (+{len(nameservers) - 2} more)"
            messages.append(f"[green]✓[/green] [cyan]NS: {ns_list}[/cyan]")
        else:
            messages.append("[yellow]○[/yellow] [dim]No NS records found[/dim]")

        if a_records:
            a_list = ", ".join(a_records[:2])
            if len(a_records) > 2:
                a_list += f" (+{len(a_records) - 2} more)"
            messages.append(f"[green]✓[/green] [cyan]A: {a_list}[/cyan]")
            if self.mode == "add":
                messages.append("[dim](A record will be added)[/dim]")

        if messages:
            self._info.update(" | ".join(messages))

    def on_input_submitted(self, _event: Input.Submitted) -> None:  # pragma: no cover - shortcut
        if not self._focus_relative_input(1, wrap=False):
            self._submit()

    def action_focus_next_field(self) -> None:  # pragma: no cover - shortcut
        self._focus_relative_input(1, wrap=True)

    def action_focus_previous_field(self) -> None:  # pragma: no cover - shortcut
        self._focus_relative_input(-1, wrap=True)

    def action_cancel(self) -> None:  # pragma: no cover - shortcut
        self.dismiss(None)

    def _submit(self) -> None:
        try:
            zone = self._build_zone()
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self.dismiss((self._original_name, zone))

    def _build_zone(self) -> Zone:
        name = self._value("#zone-name")
        server = self._value("#zone-server")
        key = self._value("#zone-key")
        ttl_text = self._value("#zone-ttl") or "3600"
        notes = self.query_one("#zone-notes", Input).value.strip()

        if not name:
            raise ValueError("Zone name is required.")
        if not server:
            raise ValueError("Authoritative server is required.")

        # Generate default key file path if not provided (fallback for add mode)
        if not key and self.mode == "add":
            key = f"{self._prefix_key_path}/{name}.key"

        if not key:
            raise ValueError("Key file path is required.")

        try:
            default_ttl = int(ttl_text)
        except ValueError as exc:  # pragma: no cover - user input parsing
            raise ValueError("Default TTL must be an integer.") from exc

        if default_ttl <= 0:
            raise ValueError("Default TTL must be positive.")

        existing_records = self._initial_zone.records if self._initial_zone else []

        if self.mode == "add" and self._discovered_a_records:
            has_apex_a = any(r.label == "@" and r.type == "A" for r in existing_records)
            if not has_apex_a:
                apex_record = Record(
                    label="@",
                    type="A",
                    value=self._discovered_a_records[0],
                    ttl=default_ttl,
                    priority=None,
                    weight=None,
                    port=None,
                )
                existing_records = [apex_record] + existing_records

        return Zone(
            name=name,
            server=server,
            key_file=Path(key),
            notes=notes or None,
            default_ttl=default_ttl,
            records=existing_records,
        )

    def _value(self, selector: str) -> str:
        return self.query_one(selector, Input).value.strip()

    def _show_error(self, message: str) -> None:
        if self._error:
            self._error.update(f"[red]{message}[/red]")

    def _focus_relative_input(self, delta: int, *, wrap: bool) -> bool:
        focused = self.app.focused
        current_id = focused.id if isinstance(focused, Input) else None
        try:
            index = self._FIELD_IDS.index(current_id) if current_id else None
        except ValueError:
            index = None

        target = (0 if delta > 0 else -1) if index is None else index + delta

        if target < 0 or target >= len(self._FIELD_IDS):
            if not wrap:
                return False
            target %= len(self._FIELD_IDS)

        field_id = self._FIELD_IDS[target]
        self.query_one(f"#{field_id}", Input).focus()
        return True


class RecordFormScreen(ModalScreen[RecordFormResult | None]):
    """Modal dialog for adding or editing a DNS record."""

    BINDINGS = [
        Binding("tab", "focus_next_field", "Next field", show=False, priority=True),
        Binding("shift+tab", "focus_previous_field", "Previous field", show=False, priority=True),
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    _FIELD_IDS = [
        "record-label",
        "record-type",
        "record-value",
        "record-ttl",
        "record-priority",
        "record-weight",
        "record-port",
    ]

    def __init__(
        self,
        mode: Literal["add", "edit"],
        zone_name: str,
        record: Record | None = None,
        record_index: int | None = None,
    ) -> None:
        super().__init__()
        self.mode = mode
        self.zone_name = zone_name
        self._initial_record = record
        self._record_index = record_index
        self._error: Static | None = None
        self._info: Static | None = None
        self._discovered_cname_target: str | None = None
        # Track last lookup to avoid redundant lookups
        self._last_lookup_label: str | None = None
        self._last_lookup_type: str | None = None

    def compose(self) -> ComposeResult:
        title = (
            f"Add record to {self.zone_name}"
            if self.mode == "add"
            else f"Edit record in {self.zone_name}"
        )
        button_label = "Add" if self.mode == "add" else "Update"
        with Vertical(id="record-form-dialog"):
            yield Static(title, id="modal-title")
            self._error = Static("", id="modal-error")
            yield self._error
            self._info = Static("", id="modal-info")
            yield self._info
            yield Static("Label (use @ for apex)")
            yield Input(
                id="record-label",
                placeholder="@ or www",
                value=self._initial_record.label if self._initial_record else "",
            )
            yield Static("Type (A, AAAA, CNAME, MX, TXT, SRV, NS, CAA)")
            yield Input(
                id="record-type",
                placeholder="A",
                value=self._initial_record.type if self._initial_record else "A",
            )
            yield Static("Value (IPv4, IPv6, hostname, or text)")
            yield Input(
                id="record-value",
                placeholder="198.51.100.10",
                value=self._initial_record.value if self._initial_record else "",
            )
            yield Static("TTL (seconds)")
            yield Input(
                id="record-ttl",
                placeholder="300",
                value=str(self._initial_record.ttl) if self._initial_record else "300",
            )
            yield Static("Priority (for MX and SRV records, optional)")
            yield Input(
                id="record-priority",
                placeholder="10",
                value=str(self._initial_record.priority)
                if self._initial_record and self._initial_record.priority is not None
                else "",
            )
            yield Static("Weight (for SRV records, optional)")
            yield Input(
                id="record-weight",
                placeholder="0",
                value=str(self._initial_record.weight)
                if self._initial_record and self._initial_record.weight is not None
                else "",
            )
            yield Static("Port (for SRV records, optional)")
            yield Input(
                id="record-port",
                placeholder="80",
                value=str(self._initial_record.port)
                if self._initial_record and self._initial_record.port is not None
                else "",
            )
            with Horizontal(id="modal-actions"):
                yield Button("Cancel", id="cancel")
                yield Button(button_label, id="save", variant="success")

    def on_mount(self) -> None:
        self.query_one("#record-label", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "save":
            self._submit()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "record-value":
            self._perform_dns_lookup(event.value)
        elif event.input.id == "record-label":
            self._perform_label_type_lookup(event.value, None)
        elif event.input.id == "record-type":
            self._perform_label_type_lookup(None, event.value)

    def _perform_label_type_lookup(self, label: str | None, record_type: str | None) -> None:
        """Perform DNS lookup when label or type changes.

        Args:
            label: New label value if label changed, None if only type changed
            record_type: New record type if type changed, None if only label changed
        """
        if self._error:
            self._error.update("")
        if self._info:
            self._info.update("")

        # Get current values from form
        label_input = self.query_one("#record-label", Input)
        type_input = self.query_one("#record-type", Input)
        value_input = self.query_one("#record-value", Input)

        current_label = (label if label is not None else label_input.value).strip()
        current_type = (
            (record_type if record_type is not None else type_input.value).strip().upper()
        )

        if not current_label:
            return

        # Check if we need to perform a new lookup
        # Only lookup if the combination of label and type has changed
        if self._last_lookup_label == current_label and self._last_lookup_type == current_type:
            return

        # Clear discovered CNAME target when performing a new lookup
        self._discovered_cname_target = None

        # Update tracking to prevent redundant lookups.
        # Note: Tracking is updated before lookup execution to avoid repeated
        # attempts for the same label/type combination, even if the lookup fails.
        # This prevents excessive DNS queries when records don't exist.
        self._last_lookup_label = current_label
        self._last_lookup_type = current_type

        if self._info:
            self._info.update("[yellow]⏳ Looking up DNS record...[/yellow]")

        # If we have a specific type, do a type-specific lookup
        if current_type and current_type in ("A", "AAAA", "CNAME", "MX", "TXT", "SRV", "NS", "CAA"):
            value = dns_lookup_label_with_type(current_label, self.zone_name, current_type)

            if value:
                # Update value field with found result
                value_input.value = value

                if current_type == "CNAME":
                    self._discovered_cname_target = value

                if self._info:
                    self._info.update(
                        f"[green]✓[/green] [cyan]Found {current_type} record: {value}[/cyan]"
                    )
            else:
                if self._info:
                    self._info.update(
                        f"[yellow]○[/yellow] [dim]No {current_type} record found for {current_label}[/dim]"
                    )
        else:
            # Fall back to automatic type detection for unknown or empty types
            detected_type, value = dns_lookup_label(current_label, self.zone_name)

            if detected_type and value:
                # Update both type and value fields
                type_input.value = detected_type
                value_input.value = value

                if detected_type == "CNAME":
                    self._discovered_cname_target = value

                if self._info:
                    self._info.update(
                        f"[green]✓[/green] [cyan]Found {detected_type} record: {value}[/cyan]"
                    )
            else:
                if self._info:
                    self._info.update("[yellow]○[/yellow] [dim]No existing DNS records found[/dim]")

    def _perform_dns_lookup(self, value: str) -> None:
        if self._error:
            self._error.update("")
        if self._info:
            self._info.update("")

        if not value or not value.strip():
            return

        if self._info:
            self._info.update("[yellow]⏳ Checking DNS...[/yellow]")

        suggested_type, lookup_result = dns_lookup(value.strip())

        if suggested_type:
            type_input = self.query_one("#record-type", Input)
            # Always update type field when new DNS info is found (consistent with label lookup)
            type_input.value = suggested_type

        self._show_lookup_info(suggested_type, lookup_result)

    def _show_lookup_info(
        self, suggested_type: Literal["A", "AAAA", "CNAME"] | None, lookup_result: dict
    ) -> None:
        if not self._info:
            return

        messages = []

        if suggested_type == "A":
            hostname = lookup_result.get("hostname")
            if hostname:
                messages.append(f"[green]✓[/green] [cyan]Reverse DNS: {hostname}[/cyan]")
            else:
                messages.append("[yellow]○[/yellow] [dim]No reverse DNS found[/dim]")
        elif suggested_type == "AAAA":
            messages.append("[green]✓[/green] [cyan]IPv6 address detected[/cyan]")
        elif suggested_type == "CNAME":
            ip = lookup_result.get("ip")
            if ip:
                messages.append(f"[green]✓[/green] [cyan]Forward DNS: {ip}[/cyan]")
            else:
                messages.append("[yellow]○[/yellow] [dim]No forward DNS found[/dim]")

        if messages:
            self._info.update(" | ".join(messages))

    def on_input_submitted(self, _event: Input.Submitted) -> None:  # pragma: no cover - shortcut
        if not self._focus_relative_input(1, wrap=False):
            self._submit()

    def action_focus_next_field(self) -> None:  # pragma: no cover - shortcut
        self._focus_relative_input(1, wrap=True)

    def action_focus_previous_field(self) -> None:  # pragma: no cover - shortcut
        self._focus_relative_input(-1, wrap=True)

    def action_cancel(self) -> None:  # pragma: no cover - shortcut
        self.dismiss(None)

    def _submit(self) -> None:
        try:
            record = self._build_record()
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self.dismiss((self._record_index, record, self._discovered_cname_target))

    def _build_record(self) -> Record:
        label = self._value("#record-label")
        rtype = self._value("#record-type").upper() or "A"
        value = self._value("#record-value")
        ttl_text = self._value("#record-ttl") or "300"
        priority_text = self._value("#record-priority")
        weight_text = self._value("#record-weight")
        port_text = self._value("#record-port")

        if not label:
            raise ValueError("Record label is required.")
        if rtype not in ("A", "AAAA", "CNAME", "MX", "TXT", "SRV", "NS", "CAA"):
            raise ValueError("Record type must be one of: A, AAAA, CNAME, MX, TXT, SRV, NS, CAA.")
        if not value:
            raise ValueError("Record value is required.")

        try:
            ttl = int(ttl_text)
        except ValueError as exc:  # pragma: no cover - user input parsing
            raise ValueError("TTL must be an integer.") from exc
        if ttl <= 0:
            raise ValueError("TTL must be positive.")

        # Parse optional fields
        priority = None
        weight = None
        port = None

        if priority_text:
            try:
                priority = int(priority_text)
            except ValueError as exc:
                raise ValueError("Priority must be an integer.") from exc

        if weight_text:
            try:
                weight = int(weight_text)
            except ValueError as exc:
                raise ValueError("Weight must be an integer.") from exc

        if port_text:
            try:
                port = int(port_text)
            except ValueError as exc:
                raise ValueError("Port must be an integer.") from exc

        return Record(
            label=label,
            type=cast(RecordType, rtype),
            value=value,
            ttl=ttl,
            priority=priority,
            weight=weight,
            port=port,
        )

    def _value(self, selector: str) -> str:
        return self.query_one(selector, Input).value.strip()

    def _show_error(self, message: str) -> None:
        if self._error:
            self._error.update(f"[red]{message}[/red]")

    def _focus_relative_input(self, delta: int, *, wrap: bool) -> bool:
        focused = self.app.focused
        current_id = focused.id if isinstance(focused, Input) else None
        try:
            index = self._FIELD_IDS.index(current_id) if current_id else None
        except ValueError:
            index = None

        target = (0 if delta > 0 else -1) if index is None else index + delta

        if target < 0 or target >= len(self._FIELD_IDS):
            if not wrap:
                return False
            target %= len(self._FIELD_IDS)

        field_id = self._FIELD_IDS[target]
        self.query_one(f"#{field_id}", Input).focus()
        return True


class ConfirmDeleteScreen(ModalScreen[bool]):
    """Modal dialog asking the user to confirm zone removal."""

    BINDINGS = [
        Binding("tab", "focus_next_button", "Next button", show=False, priority=True),
        Binding("shift+tab", "focus_previous_button", "Previous button", show=False, priority=True),
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(self, zone_name: str) -> None:
        super().__init__()
        self.zone_name = zone_name

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(f"Delete zone [bold]{self.zone_name}[/bold]?", id="modal-title")
            with Horizontal(id="modal-actions"):
                yield Button("Cancel", id="cancel")
                yield Button("Delete", id="delete", variant="error")

    def on_mount(self) -> None:
        self.query_one("#cancel", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "delete":
            self.dismiss(True)

    def action_focus_next_button(self) -> None:  # pragma: no cover - shortcut
        focused = self.app.focused
        if focused and focused.id == "cancel":
            self.query_one("#delete", Button).focus()
        else:
            self.query_one("#cancel", Button).focus()

    def action_focus_previous_button(self) -> None:  # pragma: no cover - shortcut
        focused = self.app.focused
        if focused and focused.id == "delete":
            self.query_one("#cancel", Button).focus()
        else:
            self.query_one("#delete", Button).focus()

    def action_cancel(self) -> None:  # pragma: no cover - shortcut
        self.dismiss(False)


class ConfirmRecordDeleteScreen(ModalScreen[bool]):
    """Modal to confirm record deletion."""

    BINDINGS = [
        Binding("tab", "focus_next_button", "Next button", show=False, priority=True),
        Binding("shift+tab", "focus_previous_button", "Previous button", show=False, priority=True),
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(self, zone_name: str, record_label: str) -> None:
        super().__init__()
        self.zone_name = zone_name
        self.record_label = record_label

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-record-dialog"):
            yield Static(
                f"Delete record [bold]{self.record_label}[/bold] from {self.zone_name}?",
                id="modal-title",
            )
            with Horizontal(id="modal-actions"):
                yield Button("Cancel", id="cancel")
                yield Button("Delete", id="delete", variant="error")

    def on_mount(self) -> None:
        self.query_one("#cancel", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "delete":
            self.dismiss(True)

    def action_focus_next_button(self) -> None:  # pragma: no cover - shortcut
        focused = self.app.focused
        if focused and focused.id == "cancel":
            self.query_one("#delete", Button).focus()
        else:
            self.query_one("#cancel", Button).focus()

    def action_focus_previous_button(self) -> None:  # pragma: no cover - shortcut
        focused = self.app.focused
        if focused and focused.id == "delete":
            self.query_one("#cancel", Button).focus()
        else:
            self.query_one("#delete", Button).focus()

    def action_cancel(self) -> None:  # pragma: no cover - shortcut
        self.dismiss(False)


__all__ = [
    "ZoneFormResult",
    "RecordFormResult",
    "ZoneFormScreen",
    "RecordFormScreen",
    "ConfirmDeleteScreen",
    "ConfirmRecordDeleteScreen",
]
