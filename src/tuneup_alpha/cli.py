"""Typer CLI entrypoint for TuneUp Alpha."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import ConfigRepository, load_config
from .dns_state import compare_dns_state, validate_dns_state
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
    show_current: bool = typer.Option(False, "--show-current", help="Show current DNS state"),
) -> None:
    """Show the nsupdate script that would recreate every record for a zone."""

    _initialize_logging(config_path)
    set_correlation_id()
    logger.info(f"Generating plan for zone: {zone}")

    target_zone = _find_zone(zone, config_path)

    # If requested, show current state comparison
    if show_current:
        diff_result = compare_dns_state(target_zone)
        if diff_result.has_changes():
            summary = diff_result.summary()
            console.print("[bold]Current DNS State:[/bold]")
            console.print(
                f"  Changes needed: {summary['create']} create, "
                f"{summary['update']} update, {summary['delete']} delete\n"
            )
        else:
            console.print("[green]Current DNS state matches configuration[/green]\n")

    plan = _full_zone_plan(target_zone)
    script = plan.render()
    console.print(script)
    logger.info(f"Plan generated for zone: {zone}")


@app.command()
def apply(
    zone: str = typer.Argument(..., help="Zone name to push"),
    config_path: Path | None = typer.Option(None),
    dry_run: bool = typer.Option(True, help="Preview the script without executing"),
    force: bool = typer.Option(False, "--force", help="Skip state validation check"),
) -> None:
    """Apply the generated plan using nsupdate (defaults to dry-run)."""

    _initialize_logging(config_path)
    set_correlation_id()
    logger.info(f"Applying changes for zone: {zone} (dry_run={dry_run})")

    target_zone = _find_zone(zone, config_path)

    # Validate current state and show warnings unless --force is used
    if not force and not dry_run:
        diff_result = compare_dns_state(target_zone)
        if diff_result.has_changes():
            summary = diff_result.summary()
            console.print("[yellow]⚠ Warning:[/yellow] Changes will be applied:")
            console.print(
                f"  {summary['create']} record(s) to create, "
                f"{summary['update']} to update, {summary['delete']} to delete"
            )

            # Check for potentially dangerous operations
            if summary["delete"] > 0:
                console.print(
                    f"\n[red]⚠ Warning:[/red] {summary['delete']} record(s) "
                    "will be deleted from DNS"
                )

            confirm = typer.confirm("Do you want to proceed?")
            if not confirm:
                console.print("Operation cancelled.")
                logger.info(f"Apply operation cancelled by user for zone: {zone}")
                raise typer.Exit(code=0)

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


@app.command()
def diff(
    zone: str = typer.Argument(..., help="Zone name to compare"),
    config_path: Path | None = typer.Option(None),
) -> None:
    """Show differences between current DNS state and desired configuration."""

    _initialize_logging(config_path)
    set_correlation_id()
    logger.info(f"Comparing DNS state for zone: {zone}")

    target_zone = _find_zone(zone, config_path)
    diff_result = compare_dns_state(target_zone)

    if not diff_result.has_changes():
        console.print(f"[green]✓[/green] Zone '{zone}' matches desired configuration")
        logger.info(f"Zone '{zone}' is in sync with desired configuration")
        return

    summary = diff_result.summary()
    console.print(f"\n[bold]DNS State Differences for {zone}:[/bold]")
    console.print(f"  [yellow]{summary['create']}[/yellow] record(s) to create")
    console.print(f"  [blue]{summary['update']}[/blue] record(s) to update")
    console.print(f"  [red]{summary['delete']}[/red] record(s) to delete")

    # Show detailed changes
    if diff_result.changes:
        console.print("\n[bold]Detailed Changes:[/bold]")
        for change in diff_result.changes:
            if change.action == "create":
                console.print(
                    f"  [green]+[/green] {change.record.label} {change.record.type} "
                    f"{change.record.value} (TTL: {change.record.ttl})"
                )
            elif change.action == "delete":
                console.print(
                    f"  [red]-[/red] {change.record.label} {change.record.type} "
                    f"{change.record.value}"
                )
            elif change.action == "update":
                console.print(
                    f"  [blue]~[/blue] {change.record.label} {change.record.type} "
                    f"{change.record.value} (TTL: {change.record.ttl})"
                )

    logger.info(f"DNS diff completed for zone: {zone}")


@app.command()
def verify(
    zone: str = typer.Argument(..., help="Zone name to verify"),
    config_path: Path | None = typer.Option(None),
) -> None:
    """Verify that current DNS state matches desired configuration."""

    _initialize_logging(config_path)
    set_correlation_id()
    logger.info(f"Verifying DNS state for zone: {zone}")

    target_zone = _find_zone(zone, config_path)
    is_valid, warnings = validate_dns_state(target_zone)

    if is_valid:
        console.print(f"[green]✓[/green] Zone '{zone}' is valid and matches configuration")
        logger.info(f"Zone '{zone}' validation successful")
        raise typer.Exit(code=0)

    console.print(f"[red]✗[/red] Zone '{zone}' validation failed:")
    for warning in warnings:
        console.print(f"  {warning}")

    logger.warning(f"Zone '{zone}' validation failed with {len(warnings)} issue(s)")
    raise typer.Exit(code=1)


def _full_zone_plan(zone: Zone) -> NsupdatePlan:
    plan = NsupdatePlan(zone)
    for record in zone.records:
        plan.add_change(RecordChange(action="create", record=record))
    return plan
