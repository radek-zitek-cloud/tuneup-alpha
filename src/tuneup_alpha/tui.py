"""Terminal UI for browsing zones and records."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from .config import ConfigError, ConfigRepository
from .dns_lookup import dns_lookup, dns_lookup_label, lookup_a_records, lookup_nameservers
from .models import AppConfig, Record, RecordType, Zone

ZoneFormResult = tuple[str | None, Zone]
RecordFormResult = tuple[int | None, Record]


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

    def __init__(self, mode: Literal["add", "edit"], zone: Zone | None = None) -> None:
        super().__init__()
        self.mode = mode
        self._initial_zone = zone
        self._original_name = zone.name if zone else None
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
        """Handle input changes to perform DNS lookup when zone name changes."""
        # Only perform DNS lookup on the zone name field
        if event.input.id == "zone-name":
            self._perform_zone_lookup(event.value)

    def _perform_zone_lookup(self, domain: str) -> None:
        """Perform DNS lookup for zone and update fields with discovered values.

        Args:
            domain: The domain name entered in the zone name field
        """
        # Clear previous messages
        if self._error:
            self._error.update("")
        if self._info:
            self._info.update("")

        # Skip lookup for empty values or when editing existing zone
        if not domain or not domain.strip():
            self._discovered_ns = []
            self._discovered_a_records = []
            return

        # Don't perform lookup if this is the original zone name (editing case)
        if self._original_name and domain.strip() == self._original_name:
            return

        # Show checking indicator
        if self._info:
            self._info.update("[yellow]⏳ Looking up DNS records...[/yellow]")

        domain = domain.strip()

        # Lookup NS records
        nameservers = lookup_nameservers(domain)
        self._discovered_ns = nameservers

        # Lookup A records for the apex
        a_records = lookup_a_records(domain)
        self._discovered_a_records = a_records

        # Auto-fill nameserver field if found and field is empty
        server_input = self.query_one("#zone-server", Input)
        if nameservers and not server_input.value.strip():
            server_input.value = nameservers[0]

        # Show lookup information
        self._show_zone_lookup_info(nameservers, a_records)

    def _show_zone_lookup_info(self, nameservers: list[str], a_records: list[str]) -> None:
        """Display information about zone DNS lookup results.

        Args:
            nameservers: List of discovered nameservers
            a_records: List of discovered A records
        """
        if not self._info:
            return

        messages = []

        if nameservers:
            ns_list = ", ".join(nameservers[:2])  # Show first 2
            if len(nameservers) > 2:
                ns_list += f" (+{len(nameservers) - 2} more)"
            messages.append(f"[green]✓[/green] [cyan]NS: {ns_list}[/cyan]")
        else:
            messages.append("[yellow]○[/yellow] [dim]No NS records found[/dim]")

        if a_records:
            a_list = ", ".join(a_records[:2])  # Show first 2
            if len(a_records) > 2:
                a_list += f" (+{len(a_records) - 2} more)"
            messages.append(f"[green]✓[/green] [cyan]A: {a_list}[/cyan]")
            if self.mode == "add":
                messages.append("[dim](A record will be added)[/dim]")

        if messages:
            self._info.update(" | ".join(messages))

    def on_input_submitted(self, _event: Input.Submitted) -> None:  # pragma: no cover - UI shortcut
        if not self._focus_relative_input(1, wrap=False):
            self._submit()

    def action_focus_next_field(self) -> None:  # pragma: no cover - UI shortcut
        self._focus_relative_input(1, wrap=True)

    def action_focus_previous_field(self) -> None:  # pragma: no cover - UI shortcut
        self._focus_relative_input(-1, wrap=True)

    def action_cancel(self) -> None:  # pragma: no cover - UI shortcut
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
        if not key:
            raise ValueError("Key file path is required.")

        try:
            default_ttl = int(ttl_text)
        except ValueError as exc:  # pragma: no cover - user input parsing
            raise ValueError("Default TTL must be an integer.") from exc

        if default_ttl <= 0:
            raise ValueError("Default TTL must be positive.")

        # Preserve existing records when editing a zone
        existing_records = self._initial_zone.records if self._initial_zone else []

        # Add discovered A records when creating a new zone
        if self.mode == "add" and self._discovered_a_records:
            # Check if apex A record already exists
            has_apex_a = any(r.label == "@" and r.type == "A" for r in existing_records)
            if not has_apex_a:
                # Add the first discovered A record for the apex
                apex_record = Record(
                    label="@",
                    type="A",
                    value=self._discovered_a_records[0],
                    ttl=default_ttl,
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

    _FIELD_IDS = ["record-label", "record-type", "record-value", "record-ttl"]

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
            yield Static("Type (A or CNAME)")
            yield Input(
                id="record-type",
                placeholder="A",
                value=self._initial_record.type if self._initial_record else "A",
            )
            yield Static("Value (IPv4 or hostname)")
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
        """Handle input changes to perform DNS lookup."""
        # Perform DNS lookup on the value field
        if event.input.id == "record-value":
            self._perform_dns_lookup(event.value)
        # Perform DNS lookup on the label field
        elif event.input.id == "record-label":
            self._perform_label_lookup(event.value)

    def _perform_label_lookup(self, label: str) -> None:
        """Perform DNS lookup for a label and update fields with discovered values.

        Args:
            label: The label entered in the label field
        """
        # Clear previous messages
        if self._error:
            self._error.update("")
        if self._info:
            self._info.update("")

        # Skip lookup for empty values
        if not label or not label.strip():
            return

        # Show checking indicator
        if self._info:
            self._info.update("[yellow]⏳ Looking up label...[/yellow]")

        label = label.strip()

        # Perform DNS lookup for the label in this zone
        record_type, value = dns_lookup_label(label, self.zone_name)

        # Update type and value fields if we found something
        if record_type and value:
            type_input = self.query_one("#record-type", Input)
            value_input = self.query_one("#record-value", Input)

            # Only auto-fill if fields are empty or contain default values
            if not type_input.value.strip() or type_input.value.strip().upper() in ("A", ""):
                type_input.value = record_type

            if not value_input.value.strip():
                value_input.value = value

            # Show success message
            if self._info:
                self._info.update(
                    f"[green]✓[/green] [cyan]Found {record_type} record: {value}[/cyan]"
                )
        else:
            # Show no records found message
            if self._info:
                self._info.update("[yellow]○[/yellow] [dim]No existing DNS records found[/dim]")

    def _perform_dns_lookup(self, value: str) -> None:
        """Perform DNS lookup and update type field and info message.

        Args:
            value: The value entered in the value field
        """
        # Clear previous messages
        if self._error:
            self._error.update("")
        if self._info:
            self._info.update("")

        # Skip lookup for empty values
        if not value or not value.strip():
            return

        # Show checking indicator
        if self._info:
            self._info.update("[yellow]⏳ Checking DNS...[/yellow]")

        # Perform DNS lookup
        suggested_type, lookup_result = dns_lookup(value.strip())

        # Update type field if we have a suggestion
        if suggested_type:
            type_input = self.query_one("#record-type", Input)
            # Only auto-fill if the field is empty or contains default value
            current_type = type_input.value.strip().upper()
            if not current_type or current_type in ("A", ""):
                type_input.value = suggested_type

        # Show lookup information
        self._show_lookup_info(suggested_type, lookup_result)

    def _show_lookup_info(
        self, suggested_type: Literal["A", "CNAME"] | None, lookup_result: dict
    ) -> None:
        """Display information about DNS lookup results.

        Args:
            suggested_type: Suggested record type based on the value
            lookup_result: Results from DNS lookup
        """
        if not self._info:
            return

        messages = []

        if suggested_type == "A":
            # User entered an IP address
            hostname = lookup_result.get("hostname")
            if hostname:
                messages.append(f"[green]✓[/green] [cyan]Reverse DNS: {hostname}[/cyan]")
            else:
                messages.append("[yellow]○[/yellow] [dim]No reverse DNS found[/dim]")
        elif suggested_type == "CNAME":
            # User entered a hostname
            ip = lookup_result.get("ip")
            if ip:
                messages.append(f"[green]✓[/green] [cyan]Forward DNS: {ip}[/cyan]")
            else:
                messages.append("[yellow]○[/yellow] [dim]No forward DNS found[/dim]")

        if messages:
            self._info.update(" | ".join(messages))

    def on_input_submitted(self, _event: Input.Submitted) -> None:  # pragma: no cover - UI shortcut
        if not self._focus_relative_input(1, wrap=False):
            self._submit()

    def action_focus_next_field(self) -> None:  # pragma: no cover - UI shortcut
        self._focus_relative_input(1, wrap=True)

    def action_focus_previous_field(self) -> None:  # pragma: no cover - UI shortcut
        self._focus_relative_input(-1, wrap=True)

    def action_cancel(self) -> None:  # pragma: no cover - UI shortcut
        self.dismiss(None)

    def _submit(self) -> None:
        try:
            record = self._build_record()
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self.dismiss((self._record_index, record))

    def _build_record(self) -> Record:
        label = self._value("#record-label")
        rtype = self._value("#record-type").upper() or "A"
        value = self._value("#record-value")
        ttl_text = self._value("#record-ttl") or "300"

        if not label:
            raise ValueError("Record label is required.")
        if rtype not in ("A", "CNAME"):
            raise ValueError("Record type must be A or CNAME.")
        if not value:
            raise ValueError("Record value is required.")
        try:
            ttl = int(ttl_text)
        except ValueError as exc:  # pragma: no cover - user input parsing
            raise ValueError("TTL must be an integer.") from exc
        if ttl <= 0:
            raise ValueError("TTL must be positive.")

        return Record(label=label, type=cast(RecordType, rtype), value=value, ttl=ttl)

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

    def __init__(self, zone_name: str) -> None:
        super().__init__()
        self.zone_name = zone_name

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(f"Delete zone [bold]{self.zone_name}[/bold]?", id="modal-title")
            with Horizontal(id="modal-actions"):
                yield Button("Cancel", id="cancel")
                yield Button("Delete", id="delete", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "delete":
            self.dismiss(True)


class ConfirmRecordDeleteScreen(ModalScreen[bool]):
    """Modal to confirm record deletion."""

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "delete":
            self.dismiss(True)


class ZoneDashboard(App):
    """Simple Textual dashboard listing all configured zones."""

    CSS_PATH = "tui.tcss"
    BINDINGS = [
        # Disable default tab/shift+tab pane switching (use z/r instead)
        Binding("tab", "noop", show=False, priority=True),
        Binding("shift+tab", "noop", show=False, priority=True),
        # Pane focus
        Binding("z", "focus_zones", "Focus zones"),
        Binding("r", "focus_records", "Focus records"),
        # Operations (context-aware based on focused pane)
        Binding("a", "add", "Add"),
        Binding("e", "edit", "Edit"),
        Binding("d", "delete", "Delete"),
        # Other operations
        Binding("l", "refresh", "Reload config"),
        Binding("t", "cycle_theme", "Cycle theme"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, config_repo: ConfigRepository | None = None) -> None:
        super().__init__()
        self.config_repo = config_repo or ConfigRepository()
        self._config = AppConfig()
        self._table: DataTable | None = None
        self._records_table: DataTable | None = None
        self._config_details: Static | None = None
        self._focus_mode: Literal["zones", "records"] = "zones"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self._table = DataTable(id="zones-table", zebra_stripes=True)
        self._table.cursor_type = "row"
        self._table.add_columns("Zone", "Server", "Records", "Key File")
        yield self._table
        self._records_table = DataTable(id="records-table", zebra_stripes=True)
        self._records_table.cursor_type = "row"
        self._records_table.add_columns("Label", "Type", "Value", "TTL")
        yield self._records_table
        self._config_details = Static(id="zone-configuration")
        yield self._config_details
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_zones()
        # Load and apply saved theme
        if self._config.theme:
            self.theme = self._config.theme
        if self._table and self._table.row_count:
            self._table.focus()

    def action_noop(self) -> None:
        """No-op action to disable default tab/shift+tab bindings."""
        pass

    def action_refresh(self) -> None:
        self.refresh_zones()

    def action_cycle_theme(self) -> None:
        """Cycle to the next theme in the list."""
        themes = list(self.available_themes)
        try:
            current_index = themes.index(self.theme)
            next_index = (current_index + 1) % len(themes)
        except ValueError:
            next_index = 0
        self.theme = themes[next_index]
        self.notify(f"Theme changed to: {self.theme}", severity="information")

    async def action_quit(self) -> None:
        """Save theme before quitting."""
        # Save current theme to config
        self._config.theme = self.theme
        self.config_repo.save(self._config)
        # Call the parent quit action
        await super().action_quit()

    def action_focus_zones(self) -> None:
        """Focus the zones pane."""
        if self._table:
            self._focus_mode = "zones"
            self._table.focus()

    def action_focus_records(self) -> None:
        """Focus the records pane."""
        if not self._records_table or not self._config.zones:
            self.notify("Select a zone with records to edit", severity="warning")
            return
        self._focus_mode = "records"
        self._records_table.focus()

    def action_add(self) -> None:
        """Add a zone or record based on which pane has focus."""
        if self._focus_mode == "zones":
            self.action_add_zone()
        elif self._focus_mode == "records":
            self._add_record()

    def action_edit(self) -> None:
        """Edit a zone or record based on which pane has focus."""
        if self._focus_mode == "zones":
            self.action_edit_zone()
        elif self._focus_mode == "records":
            self._edit_record()

    def action_delete(self) -> None:
        """Delete a zone or record based on which pane has focus."""
        if self._focus_mode == "zones":
            self.action_delete_zone()
        elif self._focus_mode == "records":
            self._delete_record()

    def action_add_zone(self) -> None:
        self.push_screen(ZoneFormScreen("add"), self._handle_zone_saved)

    def action_edit_zone(self) -> None:
        zone = self._current_zone()
        if not zone:
            self.notify("No zone selected", severity="warning")
            return
        self.push_screen(ZoneFormScreen("edit", zone), self._handle_zone_saved)

    def action_delete_zone(self) -> None:
        zone = self._current_zone()
        if not zone:
            self.notify("No zone selected", severity="warning")
            return

        def _on_confirm(confirmed: bool | None) -> None:
            self._handle_delete(zone, confirmed or False)

        self.push_screen(ConfirmDeleteScreen(zone.name), _on_confirm)

    def refresh_zones(
        self, select_name: str | None = None, record_index: int | None = None
    ) -> None:
        self._config = self.config_repo.load()
        if not self._table:
            return

        self._table.clear()
        selected_index = 0
        for index, zone in enumerate(self._config.zones):
            self._table.add_row(
                zone.name,
                zone.server,
                str(len(zone.records)),
                str(zone.key_file),
            )
            if select_name and zone.name == select_name:
                selected_index = index

        if self._table.row_count:
            self._table.cursor_coordinate = Coordinate(selected_index, 0)
            self._update_details_for_row(selected_index, record_index)
        else:
            self._show_empty_details()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        table_id = getattr(event.control, "id", "")
        if table_id == "zones-table":
            self._update_details_for_row(event.cursor_row)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table_id = getattr(event.control, "id", "")
        if table_id == "zones-table":
            self._update_details_for_row(event.cursor_row)

    def _update_details(self, zone: Zone, record_index: int | None = None) -> None:
        self._populate_records_table(zone, record_index)
        if self._config_details:
            self._config_details.update(self._format_config(zone))

    def _update_details_for_row(self, row_index: int, record_index: int | None = None) -> None:
        if row_index < 0 or row_index >= len(self._config.zones):
            self._show_empty_details()
            return
        self._update_details(self._config.zones[row_index], record_index)

    def _populate_records_table(self, zone: Zone, record_index: int | None = None) -> None:
        if not self._records_table:
            return
        previous_row = None
        if record_index is None:
            coord = self._records_table.cursor_coordinate
            if coord:
                previous_row = coord.row
        target_row = record_index if record_index is not None else previous_row or 0
        self._records_table.clear()
        for record in zone.records:
            self._records_table.add_row(
                record.label,
                record.type,
                record.value,
                str(record.ttl),
            )
        if self._records_table.row_count:
            target_row = max(0, min(target_row, self._records_table.row_count - 1))
            self._records_table.cursor_coordinate = Coordinate(target_row, 0)

    def _format_config(self, zone: Zone) -> str:
        lines = [
            "Zone configuration",
            f"  Name: {zone.name}",
            f"  Server: {zone.server}",
            f"  Key File: {zone.key_file}",
            f"  Default TTL: {zone.default_ttl}",
            f"  Records: {len(zone.records)}",
        ]
        if zone.notes:
            lines.append(f"  Notes: {zone.notes}")
        return "\n".join(lines)

    def _show_empty_details(self) -> None:
        message = "No zones configured yet. Use `tuneup-alpha init` or press 'z+a' to add one."
        if self._records_table:
            self._records_table.clear()
        if self._config_details:
            self._config_details.update(
                message + "\nZone configuration details will appear here once a zone is selected."
            )
        self._focus_mode = "zones"

    def _handle_zone_saved(self, payload: ZoneFormResult | None) -> None:
        if not payload:
            return
        original_name, zone = payload
        try:
            if original_name:
                self.config_repo.update_zone(original_name, zone)
                self.notify(f"Zone '{zone.name}' updated", severity="information")
            else:
                self.config_repo.add_zone(zone)
                self.notify(f"Zone '{zone.name}' added", severity="information")
        except ConfigError as exc:
            self.notify(str(exc), severity="error")
            return
        self.refresh_zones(select_name=zone.name)

    def _handle_delete(self, zone: Zone, confirmed: bool) -> None:
        if not confirmed:
            return
        try:
            self.config_repo.delete_zone(zone.name)
        except ConfigError as exc:
            self.notify(str(exc), severity="error")
            return
        self.notify(f"Zone '{zone.name}' deleted", severity="information")
        self.refresh_zones()

    def _current_zone(self) -> Zone | None:
        if not self._table:
            return None
        cursor = self._table.cursor_coordinate
        if not cursor:
            return None
        row = cursor.row
        if row is None or row >= len(self._config.zones):
            return None
        return self._config.zones[row]

    def _current_record(self) -> tuple[Zone, Record, int] | None:
        zone = self._current_zone()
        if not zone or not self._records_table:
            return None
        cursor = self._records_table.cursor_coordinate
        if not cursor:
            return None
        row = cursor.row
        if row is None or row >= len(zone.records):
            return None
        return zone, zone.records[row], row

    def _add_record(self) -> None:
        zone = self._current_zone()
        if not zone:
            self.notify("Select a zone before adding records", severity="warning")
            return
        zone_name = zone.name
        self.push_screen(
            RecordFormScreen("add", zone_name),
            lambda payload: self._handle_record_saved(zone_name, payload),
        )

    def _edit_record(self) -> None:
        current = self._current_record()
        if not current:
            self.notify("No record selected", severity="warning")
            return
        zone, record, index = current
        zone_name = zone.name
        self.push_screen(
            RecordFormScreen("edit", zone_name, record=record, record_index=index),
            lambda payload: self._handle_record_saved(zone_name, payload),
        )

    def _delete_record(self) -> None:
        current = self._current_record()
        if not current:
            self.notify("No record selected", severity="warning")
            return
        zone, record, index = current

        def _on_confirm(confirmed: bool | None) -> None:
            self._handle_record_delete(zone.name, index, confirmed or False)

        self.push_screen(
            ConfirmRecordDeleteScreen(zone.name, record.label),
            _on_confirm,
        )

    def _handle_record_saved(self, zone_name: str, payload: RecordFormResult | None) -> None:
        if not payload:
            return
        index, record = payload
        zone = self._get_zone_by_name(zone_name)
        if not zone:
            self.notify(f"Zone '{zone_name}' no longer exists", severity="error")
            return
        updated = zone.model_copy(deep=True)
        records = list(updated.records)
        if index is None:
            records.append(record)
            target_index = len(records) - 1
            action = "added"
        else:
            if index >= len(records):
                self.notify("Record no longer exists", severity="error")
                return
            records[index] = record
            target_index = index
            action = "updated"
        updated.records = records
        try:
            self.config_repo.update_zone(zone_name, updated)
        except ConfigError as exc:
            self.notify(str(exc), severity="error")
            return
        self.notify(f"Record '{record.label}' {action}", severity="information")
        self.refresh_zones(select_name=updated.name, record_index=target_index)
        if self._focus_mode == "records" and self._records_table:
            self._records_table.focus()

    def _handle_record_delete(self, zone_name: str, record_index: int, confirmed: bool) -> None:
        if not confirmed:
            return
        zone = self._get_zone_by_name(zone_name)
        if not zone:
            self.notify(f"Zone '{zone_name}' no longer exists", severity="error")
            return
        if record_index >= len(zone.records):
            self.notify("Record no longer exists", severity="error")
            return
        updated = zone.model_copy(deep=True)
        records = list(updated.records)
        removed = records.pop(record_index)
        updated.records = records
        try:
            self.config_repo.update_zone(zone_name, updated)
        except ConfigError as exc:
            self.notify(str(exc), severity="error")
            return
        target_index = min(record_index, max(0, len(records) - 1)) if records else None
        self.notify(
            f"Record '{removed.label}' deleted",
            severity="information",
        )
        self.refresh_zones(select_name=updated.name, record_index=target_index)
        if self._focus_mode == "records" and self._records_table:
            self._records_table.focus()

    def _get_zone_by_name(self, name: str) -> Zone | None:
        for zone in self.config_repo.load().zones:
            if zone.name == name:
                return zone
        return None


def run_dashboard(config_repo: ConfigRepository | None = None) -> None:
    """Convenience helper to start the TUI."""

    ZoneDashboard(config_repo=config_repo).run()
