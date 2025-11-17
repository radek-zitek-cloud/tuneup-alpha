"""Terminal UI for browsing zones and records."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from .config import ConfigError, ConfigRepository
from .models import AppConfig, Record, Zone

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

    def compose(self) -> ComposeResult:
        title = "Add Managed Zone" if self.mode == "add" else "Edit Managed Zone"
        button_label = "Save" if self.mode == "add" else "Update"
        with Vertical(id="zone-form-dialog"):
            yield Static(title, id="modal-title")
            self._error = Static("", id="modal-error")
            yield self._error
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

    def on_input_submitted(self, event: Input.Submitted) -> None:  # pragma: no cover - UI shortcut
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
            index = self._FIELD_IDS.index(current_id) if current_id else None  # type: ignore[arg-type]
        except ValueError:
            index = None

        if index is None:
            target = 0 if delta > 0 else -1
        else:
            target = index + delta

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

    def on_input_submitted(self, event: Input.Submitted) -> None:  # pragma: no cover - UI shortcut
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

        return Record(label=label, type=rtype, value=value, ttl=ttl)

    def _value(self, selector: str) -> str:
        return self.query_one(selector, Input).value.strip()

    def _show_error(self, message: str) -> None:
        if self._error:
            self._error.update(f"[red]{message}[/red]")

    def _focus_relative_input(self, delta: int, *, wrap: bool) -> bool:
        focused = self.app.focused
        current_id = focused.id if isinstance(focused, Input) else None
        try:
            index = self._FIELD_IDS.index(current_id) if current_id else None  # type: ignore[arg-type]
        except ValueError:
            index = None

        if index is None:
            target = 0 if delta > 0 else -1
        else:
            target = index + delta

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
        # Pane focus
        Binding("z", "focus_zones", "Focus zones"),
        Binding("r", "focus_records", "Focus records"),
        # Operations (context-aware based on focused pane)
        Binding("a", "add", "Add"),
        Binding("e", "edit", "Edit"),
        Binding("d", "delete", "Delete"),
        # Other operations
        Binding("l", "refresh", "Reload config"),
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
        if self._table and self._table.row_count:
            self._table.focus()

    def action_refresh(self) -> None:
        self.refresh_zones()

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

        def _on_confirm(confirmed: bool) -> None:
            self._handle_delete(zone, confirmed)

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
            self._table.cursor_coordinate = (selected_index, 0)
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
            self._records_table.cursor_coordinate = (target_row, 0)

    def _format_config(self, zone: Zone) -> str:
        lines = [
            "Zone configuration",
            "",
            f"  Name: {zone.name}",
            f"  Server: {zone.server}",
            f"  Key File: {zone.key_file}",
            f"  Default TTL: {zone.default_ttl}",
            f"  Records: {len(zone.records)}",
        ]
        if zone.notes:
            lines.append(f"  Notes: {zone.notes}")
        lines.append("")
        return "\n".join(lines)

    def _show_empty_details(self) -> None:
        message = "No zones configured yet. Use `tuneup-alpha init` or press 'z+a' to add one."
        if self._records_table:
            self._records_table.clear()
        if self._config_details:
            self._config_details.update(
                message + "\nZone configuration details will appear here once a zone is selected.\n"
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

        def _on_confirm(confirmed: bool) -> None:
            self._handle_record_delete(zone.name, index, confirmed)

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
