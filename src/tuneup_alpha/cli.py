"""Typer CLI entrypoint for TuneUp Alpha."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import ConfigRepository, load_config
from .logging_config import (
    LoggingConfig,
    LogLevel,
    LogOutput,
    get_logger,
    set_correlation_id,
    setup_logging,
)
from .models import RecordChange, Zone
from .nsupdate import NsupdateClient, NsupdatePlan
from .tui import run_dashboard

__version__ = "0.2.0"

app = typer.Typer(help="Manage dynamic DNS zones via nsupdate.")
console = Console()


def _initialize_logging(config_path: Path | None) -> None:
    """Initialize logging based on configuration."""
    try:
        app_config = load_config(config_path)
        if app_config.logging.enabled:
            # Expand log file path if specified
            log_file = None
            if app_config.logging.log_file:
                log_file_str = os.path.expanduser(str(app_config.logging.log_file))
                log_file = Path(log_file_str)

            logging_config = LoggingConfig(
                level=LogLevel(app_config.logging.level),
                output=LogOutput(app_config.logging.output),
                log_file=log_file,
                max_bytes=app_config.logging.max_bytes,
                backup_count=app_config.logging.backup_count,
                structured=app_config.logging.structured,
            )
            setup_logging(logging_config)
    except Exception:
        # If config loading fails, use default logging
        setup_logging()


logger = get_logger(__name__)


@app.command()
def init(
    config_path: Path | None = typer.Option(None, help="Location to create the config"),
    overwrite: bool = typer.Option(False, help="Overwrite if config already exists"),
) -> None:
    """Generate a starter configuration file."""

    _initialize_logging(config_path)
    set_correlation_id()
    logger.info("Initializing configuration")

    repo = ConfigRepository(config_path)
    path = repo.ensure_sample(overwrite=overwrite)
    console.print(f"Configuration written to [bold]{path}[/bold]")
    logger.info(f"Configuration initialized at {path}")


@app.command()
def version() -> None:
    """Display the version of TuneUp Alpha."""
    _initialize_logging(None)
    console.print(f"TuneUp Alpha version [bold]{__version__}[/bold]")
    logger.debug(f"Version command executed: {__version__}")


@app.command()
def show(config_path: Path | None = typer.Option(None)) -> None:
    """Display the configured zones in a table."""

    _initialize_logging(config_path)
    set_correlation_id()
    logger.info("Showing configured zones")

    config = load_config(config_path)
    if not config.zones:
        console.print("No zones configured. Use `tuneup-alpha init` first.")
        logger.info("No zones found in configuration")
        raise typer.Exit(code=0)

    table = Table(title="Managed Zones")
    table.add_column("Zone")
    table.add_column("Server")
    table.add_column("Records")
    table.add_column("Key File")

    for zone in config.zones:
        table.add_row(zone.name, zone.server, str(len(zone.records)), str(zone.key_file))

    console.print(table)
    logger.info(f"Displayed {len(config.zones)} zone(s)")


@app.command()
def tui(config_path: Path | None = typer.Option(None)) -> None:
    """Launch the Textual dashboard."""

    _initialize_logging(config_path)
    set_correlation_id()
    logger.info("Launching TUI dashboard")

    repo = ConfigRepository(config_path)
    run_dashboard(repo)


@app.command()
def plan(
    zone: str = typer.Argument(..., help="Zone name to render"),
    config_path: Path | None = typer.Option(None),
) -> None:
    """Show the nsupdate script that would recreate every record for a zone."""

    _initialize_logging(config_path)
    set_correlation_id()
    logger.info(f"Generating plan for zone: {zone}")

    target_zone = _find_zone(zone, config_path)
    plan = _full_zone_plan(target_zone)
    script = plan.render()
    console.print(script)
    logger.info(f"Plan generated for zone: {zone}")


@app.command()
def apply(
    zone: str = typer.Argument(..., help="Zone name to push"),
    config_path: Path | None = typer.Option(None),
    dry_run: bool = typer.Option(True, help="Preview the script without executing"),
) -> None:
    """Apply the generated plan using nsupdate (defaults to dry-run)."""

    _initialize_logging(config_path)
    set_correlation_id()
    logger.info(f"Applying changes for zone: {zone} (dry_run={dry_run})")

    target_zone = _find_zone(zone, config_path)
    plan = _full_zone_plan(target_zone)
    client = NsupdateClient()
    result = client.apply_plan(plan, dry_run=dry_run)
    if dry_run:
        console.print(result)
        logger.info(f"Dry-run completed for zone: {zone}")
    else:
        console.print("nsupdate completed successfully.")
        logger.info(f"Changes applied successfully for zone: {zone}")


def _find_zone(name: str, config_path: Path | None) -> Zone:
    config = load_config(config_path)
    for zone in config.zones:
        if zone.name == name:
            logger.debug(f"Found zone: {name}")
            return zone
    logger.warning(f"Zone '{name}' not found in configuration")
    console.print(f"Zone '{name}' not found in configuration.")
    raise typer.Exit(code=2)


def _full_zone_plan(zone: Zone) -> NsupdatePlan:
    plan = NsupdatePlan(zone)
    for record in zone.records:
        plan.add_change(RecordChange(action="create", record=record))
    return plan
