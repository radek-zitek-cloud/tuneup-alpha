# TuneUp Alpha

TuneUp Alpha is a Python 3.11 toolbox for managing dynamic DNS zones through `nsupdate`. It ships with a Typer-powered CLI, a Textual TUI for live inspection, and a YAML-driven configuration system so you can script repeatable record changes.

## Feature Highlights

- **Dynamic plans** – build and optionally apply `nsupdate` scripts for each managed zone.
- **Config-first workflow** – store zones, records, and key metadata as structured YAML that lives in source control.
- **Interactive dashboard** – launch the Textual TUI to inspect zones, records, and metadata without leaving the terminal.
- **In-app authoring** – press `a`, `e`, or `d` to add/edit/delete the selected zone; hit `Tab` to move into the record editor where the same shortcuts manage records.
- **In-app authoring** – press `a` in the TUI to add a new zone without dropping back to a text editor.
- **Automation ready** – CLI commands expose `plan`/`apply` operations that can be scripted inside CI or cron jobs.

## Project Layout

```text
pyproject.toml          # Build metadata and dependencies
src/tuneup_alpha/       # Application source
  config.py             # YAML repository helpers
  models.py             # Pydantic data models
  nsupdate.py           # Script builder + executor
  tui.py                # Textual-based dashboard
  cli.py                # Typer CLI entry point
tests/                  # Pytest suite
config/sample_config.yaml
```

## Getting Started

### Requirements

- Python 3.11+
- `nsupdate` (bind9-utils) available on your `PATH`

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Initialize Configuration

```bash
tuneup-alpha init
```

This writes `~/.config/tuneup-alpha/config.yaml` if it does not already exist. Use `--config-path` on any command to point to a different location (handy for CI or tests).

### Launch the Dashboard

```bash
tuneup-alpha tui
```

Inside the dashboard press `a` to open the add dialog, `e` to edit the highlighted zone, or `d` to delete the selection (with confirmation). Press `Tab` to switch focus to the record editor for the highlighted zone—while there, the same `a`/`e`/`d` shortcuts let you add, modify, or remove individual DNS records.

### Preview an nsupdate Script

```bash
tuneup-alpha plan example.com
```

### Apply Changes (Dry-Run by Default)

```bash
tuneup-alpha apply example.com --dry-run
```

Remove `--dry-run` once you are satisfied with the generated script.

## Configuration Schema

Each zone captures the authoritative server, the key file `nsupdate` should use, optional notes, and the managed records. Records currently support `A` and `CNAME` types.

```yaml
zones:
  - name: example.com
    server: ns1.example.com
    key_file: /etc/nsupdate/example.com.key
    notes: Sandbox zone managed by TuneUp Alpha.
    records:
      - label: "@"
        type: A
        value: 198.51.100.10
        ttl: 600
      - label: www
        type: CNAME
        value: "@"
        ttl: 300
```

## Development Workflow

### Run Tests

```bash
pytest
```

### Lint / Format (optional)

Add your preferred linters or formatters (e.g., Ruff, Black) and wire them into CI as the project evolves.

### Formatting Guidelines

- Use four-space indentation throughout the repository. Hard tabs are not permitted in committed files to keep diffs predictable across editors.

## Next Steps

- Expand `RecordChange` modeling to compute diffs between desired and live state.
- Add container packaging for deployment on automation hosts.
- Integrate secrets management for distributing nsupdate keys safely.
