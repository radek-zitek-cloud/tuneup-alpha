"""Terminal UI for browsing zones and records."""

from __future__ import annotations

from typing import Literal

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Static

from .config import ConfigError, ConfigRepository
from .dns_lookup import lookup_a_records
from .models import AppConfig, Record, Zone
from .tui_forms import (
    ConfirmDeleteScreen,
    ConfirmRecordDeleteScreen,
    RecordFormResult,
    RecordFormScreen,
    ZoneFormResult,
    ZoneFormScreen,
)

__all__ = [
    "ZoneDashboard",
    "run_dashboard",
    "ZoneFormScreen",
    "RecordFormScreen",
    "ConfirmDeleteScreen",
    "ConfirmRecordDeleteScreen",
]


class ZoneDashboard(App):
    """Simple Textual dashboard listing all configured zones."""

    CSS_PATH = "tui.tcss"
    BINDINGS = [
        # Disable default tab/shift+tab pane switching in main app (use z/r instead)
        # Note: Modal screens will override these with their own tab bindings
        Binding("tab", "noop", show=False),
        Binding("shift+tab", "noop", show=False),
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
        if self._config.theme:
            self.theme = self._config.theme
        if self._table and self._table.row_count:
            self._table.focus()

    def action_noop(self) -> None:
        """No-op action to disable default tab/shift+tab bindings."""

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
        self._config.theme = self.theme
        self.config_repo.save(self._config)
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
        self.push_screen(
            ZoneFormScreen("add", prefix_key_path=self._config.prefix_key_path),
            self._handle_zone_saved,
        )

    def action_edit_zone(self) -> None:
        zone = self._current_zone()
        if not zone:
            self.notify("No zone selected", severity="warning")
            return
        self.push_screen(
            ZoneFormScreen("edit", zone, prefix_key_path=self._config.prefix_key_path),
            self._handle_zone_saved,
        )

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
        index, record, cname_target = payload
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

        if record.type == "CNAME" and cname_target and index is None:
            target_label = "@" if cname_target == "@" else cname_target.split(".")[0]
            target_exists = any(r.label == target_label for r in records)
            if not target_exists:
                target_fqdn = zone_name if target_label == "@" else f"{target_label}.{zone_name}"
                a_records = lookup_a_records(target_fqdn)
                if a_records:
                    target_record = Record(
                        label=target_label,
                        type="A",
                        value=a_records[0],
                        ttl=record.ttl,
                        priority=None,
                        weight=None,
                        port=None,
                    )
                    records.append(target_record)
                    self.notify(
                        f"Also added A record for '{target_label}' ({a_records[0]})",
                        severity="information",
                    )

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
