"""Terminal UI for browsing zones and records."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Static

from .config import ConfigRepository
from .models import AppConfig, Zone


class ZoneDashboard(App):
    """Simple Textual dashboard listing all configured zones."""

    CSS_PATH = None
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Reload config"),
    ]

    def __init__(self, config_repo: ConfigRepository | None = None) -> None:
        super().__init__()
        self.config_repo = config_repo or ConfigRepository()
        self._config = AppConfig()
        self._table: DataTable | None = None
        self._details: Static | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self._table = DataTable(id="zones-table", zebra_stripes=True)
        self._table.add_columns("Zone", "Server", "Records", "Key File")
        yield self._table
        self._details = Static(id="zone-details")
        yield self._details
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_zones()
        if self._table and self._table.row_count:
            self._table.focus()

    def action_refresh(self) -> None:
        self.refresh_zones()

    def refresh_zones(self) -> None:
        self._config = self.config_repo.load()
        if not self._table:
            return

        self._table.clear()
        for zone in self._config.zones:
            self._table.add_row(
                zone.name,
                zone.server,
                str(len(zone.records)),
                str(zone.key_file),
            )

        if self._table.row_count:
            self._table.cursor_coordinate = (0, 0)
            self._update_details(self._config.zones[0])
        elif self._details:
            self._details.update("No zones configured yet. Use `tuneup-alpha init`.\n")

    def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if not self._table or not self._details:
            return
        if event.row_index >= len(self._config.zones):
            return
        self._update_details(self._config.zones[event.row_index])

    def _update_details(self, zone: Zone) -> None:
        if not self._details:
            return

        rows = [
            f"Name: {zone.name}",
            f"Server: {zone.server}",
            f"Key: {zone.key_file}",
            f"Records: {len(zone.records)}",
        ]

        if zone.notes:
            rows.append(f"Notes: {zone.notes}")
        if zone.records:
            rows.append("")
            rows.append("Managed records:")
            for record in zone.records:
                fqdn = zone.name if record.is_apex else f"{record.label}.{zone.name}"
                rows.append(
                    f"  - {fqdn} {record.type} {record.value} (ttl {record.ttl})"
                )

        self._details.update("\n".join(rows) + "\n")


def run_dashboard(config_repo: ConfigRepository | None = None) -> None:
    """Convenience helper to start the TUI."""

    ZoneDashboard(config_repo=config_repo).run()
