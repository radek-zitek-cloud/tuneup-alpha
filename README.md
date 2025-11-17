# TuneUp Alpha

[![CI](https://github.com/radek-zitek-cloud/tuneup-alpha/actions/workflows/ci.yml/badge.svg)](https://github.com/radek-zitek-cloud/tuneup-alpha/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

TuneUp Alpha is a Python 3.11 toolbox for managing dynamic DNS zones through `nsupdate`. It ships with a Typer-powered CLI, a Textual TUI for live inspection, and a YAML-driven configuration system so you can script repeatable record changes.

## Feature Highlights

- **Dynamic plans** – build and optionally apply `nsupdate` scripts for each managed zone.
- **Config-first workflow** – store zones, records, and key metadata as structured YAML that lives in source control.
- **Interactive dashboard** – launch the Textual TUI to inspect zones, records, and metadata without leaving the terminal.
- **In-app authoring** – use prefixed hotkeys (`z+a`/`z+e`/`z+d` for zones, `r+a`/`r+e`/`r+d` for records) to add, edit, or delete zones and records. Hit `Tab` to switch between zones and records view.
- **Automation ready** – CLI commands expose `plan`/`apply` operations that can be scripted inside CI or cron jobs.

## Project Layout

```text
pyproject.toml          # Build metadata and dependencies
src/tuneup_alpha/       # Application source
  config.py             # YAML repository helpers
  models.py             # Pydantic data models
  nsupdate.py           # Script builder + executor
  tui.py                # Textual-based dashboard
  tui.tcss              # TUI styling
  cli.py                # Typer CLI entry point
tests/                  # Pytest suite
config/sample_config.yaml
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed component documentation.

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

Inside the dashboard, use `z` followed by `a` to add a zone, `z+e` to edit the highlighted zone, or `z+d` to delete it (with confirmation). Press `Tab` to switch focus to the records view—while there, use `r+a`/`r+e`/`r+d` to add, modify, or remove individual DNS records. Press `Esc` to cancel any dialog, and `l` to reload the configuration from disk.

### Preview an nsupdate Script

```bash
tuneup-alpha plan example.com
```

### Apply Changes (Dry-Run by Default)

```bash
tuneup-alpha apply example.com --dry-run
```

Remove `--dry-run` once you are satisfied with the generated script.

## Usage Examples

### Example 1: Managing a Simple Zone

1. Initialize configuration:

   ```bash
   tuneup-alpha init
   ```

2. Edit `~/.config/tuneup-alpha/config.yaml` to add your zone:

   ```yaml
   zones:
     - name: mysite.com
       server: ns1.provider.com
       key_file: /path/to/mysite.key
       records:
         - label: "@"
           type: A
           value: 203.0.113.10
         - label: www
           type: CNAME
           value: "@"
   ```

3. Preview the changes:

   ```bash
   tuneup-alpha plan mysite.com
   ```

4. Apply the changes:

   ```bash
   tuneup-alpha apply mysite.com --no-dry-run
   ```

### Example 2: Using the TUI

Launch the interactive dashboard to manage zones visually:

```bash
tuneup-alpha tui
```

Key bindings:

Zone operations (prefix with `z`):
- `z` then `a` - Add a new zone
- `z` then `e` - Edit the selected zone
- `z` then `d` - Delete the selected zone

Record operations (prefix with `r`):
- `r` then `a` - Add a new record
- `r` then `e` - Edit the selected record
- `r` then `d` - Delete the selected record

Other controls:
- `Tab` - Switch between zones and records view
- `l` - Reload configuration from disk
- `Esc` - Cancel current form/dialog
- `q` - Quit the application

### Example 3: Multiple Zones

```yaml
zones:
  - name: production.com
    server: ns1.production.com
    key_file: /etc/keys/production.key
    notes: Production environment
    records:
      - label: "@"
        type: A
        value: 203.0.113.10
      - label: www
        type: CNAME
        value: "@"
      - label: api
        type: A
        value: 203.0.113.20

  - name: staging.com
    server: ns1.staging.com
    key_file: /etc/keys/staging.key
    notes: Staging environment
    records:
      - label: "@"
        type: A
        value: 198.51.100.10
      - label: www
        type: CNAME
        value: "@"
```

### Example 4: Custom Config Location

Use a custom configuration file location (useful for CI/CD):

```bash
tuneup-alpha --config-path /path/to/config.yaml plan example.com
tuneup-alpha --config-path /path/to/config.yaml apply example.com --no-dry-run
```

## Configuration Schema

Each zone captures the authoritative server, the key file `nsupdate` should use, optional notes, and the managed records. Records currently support `A` and `CNAME` types.

```yaml
zones:
  - name: example.com
    server: ns1.example.com
    key_file: /etc/nsupdate/example.com.key
    notes: Sandbox zone managed by TuneUp Alpha.
    default_ttl: 3600
    records:
      - label: "@"
        type: A
        value: 198.51.100.10
        ttl: 600
      - label: www
        type: CNAME
        value: "@"
        ttl: 300
      - label: mail
        type: A
        value: 198.51.100.20
        ttl: 300
```

### Record Types

**A Records**: Maps a hostname to an IPv4 address

- `label`: The hostname (use `@` for the zone apex)
- `value`: Must be a valid IPv4 address (e.g., `192.168.1.1`)
- `ttl`: Time to live in seconds (minimum 60)

**CNAME Records**: Creates an alias to another hostname

- `label`: The alias hostname (cannot be `@`)
- `value`: Target hostname or `@` for the zone apex
- `ttl`: Time to live in seconds (minimum 60)

### Validation Rules

- **Labels**: Must contain only alphanumeric characters, hyphens, and underscores. Maximum 63 characters. Cannot start or end with a hyphen.
- **IPv4 Addresses**: Must be in dotted-decimal notation with octets in range 0-255
- **Hostnames**: Must follow standard DNS naming conventions
- **TTL**: Minimum value is 60 seconds

## Development Workflow

### Run Tests

```bash
pytest
# or use make
make test
```

### Run Tests with Coverage

```bash
pytest --cov=tuneup_alpha --cov-report=term-missing
# or use make
make coverage
```

### Lint / Format

```bash
ruff check .
ruff format .
# or use make
make lint
make format
```

### Run All Checks

```bash
make check  # runs lint + test
```

### Formatting Guidelines

- Use four-space indentation throughout the repository. Hard tabs are not permitted in committed files to keep diffs predictable across editors.

## Next Steps

- Expand `RecordChange` modeling to compute diffs between desired and live state.
- Add container packaging for deployment on automation hosts.
- Integrate secrets management for distributing nsupdate keys safely.
