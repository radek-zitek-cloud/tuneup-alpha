"""Typer CLI entrypoint for TuneUp Alpha."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import ConfigRepository, load_config
from .models import RecordChange, Zone
from .nsupdate import NsupdateClient, NsupdatePlan
from .tui import run_dashboard

__version__ = "0.2.0"

app = typer.Typer(help="Manage dynamic DNS zones via nsupdate.")
console = Console()


@app.command()
def init(
    config_path: Path | None = typer.Option(None, help="Location to create the config"),
    overwrite: bool = typer.Option(False, help="Overwrite if config already exists"),
) -> None:
    """Generate a starter configuration file."""

    repo = ConfigRepository(config_path)
    path = repo.ensure_sample(overwrite=overwrite)
    console.print(f"Configuration written to [bold]{path}[/bold]")


@app.command()
def version() -> None:
    """Display the version of TuneUp Alpha."""
    console.print(f"TuneUp Alpha version [bold]{__version__}[/bold]")


@app.command()
def show(config_path: Path | None = typer.Option(None)) -> None:
    """Display the configured zones in a table."""

    config = load_config(config_path)
    if not config.zones:
        console.print("No zones configured. Use `tuneup-alpha init` first.")
        raise typer.Exit(code=0)

    table = Table(title="Managed Zones")
    table.add_column("Zone")
    table.add_column("Server")
    table.add_column("Records")
    table.add_column("Key File")

    for zone in config.zones:
        table.add_row(zone.name, zone.server, str(len(zone.records)), str(zone.key_file))

    console.print(table)


@app.command()
def tui(config_path: Path | None = typer.Option(None)) -> None:
    """Launch the Textual dashboard."""

    repo = ConfigRepository(config_path)
    run_dashboard(repo)


@app.command()
def plan(
    zone: str = typer.Argument(..., help="Zone name to render"),
    config_path: Path | None = typer.Option(None),
) -> None:
    """Show the nsupdate script that would recreate every record for a zone."""

    target_zone = _find_zone(zone, config_path)
    plan = _full_zone_plan(target_zone)
    script = plan.render()
    console.print(script)


@app.command()
def apply(
    zone: str = typer.Argument(..., help="Zone name to push"),
    config_path: Path | None = typer.Option(None),
    dry_run: bool = typer.Option(True, help="Preview the script without executing"),
) -> None:
    """Apply the generated plan using nsupdate (defaults to dry-run)."""

    target_zone = _find_zone(zone, config_path)
    plan = _full_zone_plan(target_zone)
    client = NsupdateClient()
    result = client.apply_plan(plan, dry_run=dry_run)
    if dry_run:
        console.print(result)
    else:
        console.print("nsupdate completed successfully.")


def _find_zone(name: str, config_path: Path | None) -> Zone:
    config = load_config(config_path)
    for zone in config.zones:
        if zone.name == name:
            return zone
    console.print(f"Zone '{name}' not found in configuration.")
    raise typer.Exit(code=2)


def _full_zone_plan(zone: Zone) -> NsupdatePlan:
    plan = NsupdatePlan(zone)
    for record in zone.records:
        plan.add_change(RecordChange(action="create", record=record))
    return plan
