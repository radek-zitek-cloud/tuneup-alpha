# TuneUp Alpha

[![CI](https://github.com/radek-zitek-cloud/tuneup-alpha/actions/workflows/ci.yml/badge.svg)](https://github.com/radek-zitek-cloud/tuneup-alpha/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

TuneUp Alpha is a Python 3.11 toolbox for managing dynamic DNS zones through `nsupdate`. It ships with a Typer-powered CLI, a Textual TUI for live inspection, and a YAML-driven configuration system so you can script repeatable record changes.

## Feature Highlights

- **Dynamic plans** – build and optionally apply `nsupdate` scripts for each managed zone.
- **DNS state validation** – compare current DNS state with desired configuration, show diffs, and verify zone consistency.
- **Config-first workflow** – store zones, records, and key metadata as structured YAML that lives in source control.
- **Interactive dashboard** – launch the Textual TUI to inspect zones, records, and metadata without leaving the terminal.
- **In-app authoring** – press `z` to focus zones or `r` to focus records, then use `a`/`e`/`d` to add, edit, or delete items in the focused pane.
- **Smart DNS lookup** – when adding or editing records in the TUI, the tool automatically performs DNS lookups to help auto-fill form fields and show related DNS information.
- **Automation ready** – CLI commands expose `plan`/`apply` operations that can be scripted inside CI or cron jobs.

## Project Layout

```text
pyproject.toml          # Build metadata and dependencies
src/tuneup_alpha/       # Application source
  config.py             # YAML repository helpers
  models.py             # Pydantic data models
  nsupdate.py           # Script builder + executor
  dns_lookup.py         # DNS lookup utilities
  dns_state.py          # DNS state validation and comparison
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

Inside the dashboard, press `z` to focus the zones pane or `r` to focus the records pane. Once a pane is focused, use `a` to add, `e` to edit, or `d` to delete items in that pane. Press `Esc` to cancel any dialog, and `l` to reload the configuration from disk.

### Validate DNS State

Check if current DNS state matches your configuration:

```bash
tuneup-alpha verify example.com
```

### View Differences

See what changes are needed to align current DNS with your configuration:

```bash
tuneup-alpha diff example.com
```

### Preview an nsupdate Script

```bash
tuneup-alpha plan example.com
```

You can also show current DNS state comparison:

```bash
tuneup-alpha plan example.com --show-current
```

### Apply Changes (Dry-Run by Default)

```bash
tuneup-alpha apply example.com --dry-run
```

Remove `--dry-run` once you are satisfied with the generated script. When applying changes without dry-run, the tool will:

- Query current DNS state
- Show a summary of changes to be made
- Warn about potentially destructive operations (deletions)
- Ask for confirmation before proceeding

To skip the validation and confirmation, use the `--force` flag:

```bash
tuneup-alpha apply example.com --no-dry-run --force
```

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

Pane navigation:

- `z` - Focus the zones pane
- `r` - Focus the records pane

Context-aware operations (work on the currently focused pane):

- `a` - Add a new zone or record
- `e` - Edit the selected zone or record
- `d` - Delete the selected zone or record

Other controls:

- `l` - Reload configuration from disk
- `t` - Cycle through available themes
- `Esc` - Cancel current form/dialog
- `q` - Quit the application (saves current theme)

#### Smart DNS Lookup

The TUI now includes comprehensive DNS lookup functionality to streamline zone and record management:

##### When Creating or Editing Zones

When you enter a domain name in the zone form, the application automatically:

- **Looks up NS records** using `dig domain.com NS` and prefills the nameserver field with the first discovered nameserver
- **Looks up A records** using `dig domain.com A` and automatically creates an apex (@) A record if one is found
- **Shows visual feedback** indicating the number of NS and A records discovered

##### When Creating or Editing Records

The application provides intelligent DNS lookup in two ways:

1. **When entering a label**:
   - Automatically performs DNS lookup for the label within the zone
   - If a CNAME record is found, prefills the type field with "CNAME" and value field with the target
   - If an A record is found, prefills the type field with "A" and value field with the IP address
   - Displays visual feedback showing what was discovered

2. **When entering a value** (existing functionality):
   - **Enter an IP address** (e.g., `192.0.2.1`):
     - The record type is automatically set to `A`
     - Reverse DNS lookup is performed to show the associated hostname (if available)
   - **Enter a hostname** (e.g., `www.example.com`):
     - The record type is automatically set to `CNAME`
     - Forward DNS lookup is performed to show the associated IP address (if available)

All DNS lookups provide visual cues (✓ for success, ○ for no results, ⏳ while checking) to keep you informed about what the application is discovering in the background.

This feature helps ensure accuracy and saves time when creating DNS records by leveraging existing DNS infrastructure.

#### Theme Customization

The TUI supports multiple color themes that persist across sessions:

- Press `t` while the TUI is running to cycle through available themes
- The selected theme is automatically saved when you quit the application
- On next startup, your preferred theme is restored automatically

Available themes include: `textual-dark`, `textual-light`, `nord`, `gruvbox`, `catppuccin-mocha`, `textual-ansi`, `dracula`, `tokyo-night`, `monokai`, `flexoki`, `catppuccin-latte`, and `solarized-light`.

You can also manually set the theme in your configuration file:

```yaml
theme: nord  # or any other available theme
zones:
  - name: example.com
    ...
```

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

### Example 4: DNS State Validation

Validate that your DNS records match your configuration:

```bash
# Check if DNS state is valid
tuneup-alpha verify mysite.com
```

Output when valid:

```text
✓ Zone 'mysite.com' is valid and matches configuration
```

Output when invalid:

```text
✗ Zone 'mysite.com' validation failed:
  DNS state mismatch: 1 to create, 0 to update, 1 to delete
  Missing: mail A 203.0.113.50
  Extra: old A 198.51.100.100
```

View detailed differences:

```bash
tuneup-alpha diff mysite.com
```

Example output:

```text
DNS State Differences for mysite.com:
  1 record(s) to create
  0 record(s) to update
  1 record(s) to delete

Detailed Changes:
  + mail A 203.0.113.50 (TTL: 300)
  - old A 198.51.100.100
```

### Example 5: Safe Apply with Validation

Apply changes with automatic validation and confirmation:

```bash
tuneup-alpha apply mysite.com --no-dry-run
```

The tool will show:

```text
⚠ Warning: Changes will be applied:
  1 record(s) to create, 0 to update, 1 to delete

⚠ Warning: 1 record(s) will be deleted from DNS
Do you want to proceed? [y/N]:
```

### Example 6: Custom Config Location

Use a custom configuration file location (useful for CI/CD):

```bash
tuneup-alpha --config-path /path/to/config.yaml plan example.com
tuneup-alpha --config-path /path/to/config.yaml apply example.com --no-dry-run
```

## Configuration Schema

Each zone captures the authoritative server, the key file `nsupdate` should use, optional notes, and the managed records. Records support multiple DNS record types including A, AAAA, CNAME, MX, TXT, SRV, NS, and CAA.

```yaml
zones:
  - name: example.com
    server: ns1.example.com
    key_file: /etc/nsupdate/example.com.key
    notes: Sandbox zone managed by TuneUp Alpha.
    default_ttl: 3600
    records:
      # A record (IPv4)
      - label: "@"
        type: A
        value: 198.51.100.10
        ttl: 600
      
      # AAAA record (IPv6)
      - label: "@"
        type: AAAA
        value: 2001:db8::1
        ttl: 600
      
      # CNAME record
      - label: www
        type: CNAME
        value: "@"
        ttl: 300
      
      # MX record
      - label: "@"
        type: MX
        value: mail.example.com
        priority: 10
        ttl: 3600
      
      # TXT record (SPF)
      - label: "@"
        type: TXT
        value: "v=spf1 include:_spf.example.com ~all"
        ttl: 3600
      
      # SRV record
      - label: _http._tcp
        type: SRV
        value: server.example.com
        priority: 10
        weight: 60
        port: 80
        ttl: 3600
      
      # NS record
      - label: subdomain
        type: NS
        value: ns1.example.com
        ttl: 3600
      
      # CAA record
      - label: "@"
        type: CAA
        value: "0 issue letsencrypt.org"
        ttl: 3600

logging:
  enabled: true
  level: INFO
  output: console
  log_file: null
  max_bytes: 10485760
  backup_count: 5
  structured: false
```

### Logging Configuration

TuneUp Alpha includes comprehensive structured logging support to track operations and changes:

**Configuration Options**:

- `enabled`: Enable or disable logging (default: `true`)
- `level`: Log level - `DEBUG`, `INFO`, `WARNING`, or `ERROR` (default: `INFO`)
- `output`: Where to send logs - `console`, `file`, or `both` (default: `console`)
- `log_file`: Path to log file (required if output is `file` or `both`)
- `max_bytes`: Maximum log file size before rotation in bytes (default: `10485760` - 10MB)
- `backup_count`: Number of rotated log files to keep (default: `5`)
- `structured`: Use structured JSON logging format (default: `false`)

**Features**:

- **Log Levels**: Control verbosity with DEBUG, INFO, WARNING, and ERROR levels
- **Multiple Outputs**: Log to console, file, or both simultaneously
- **Log Rotation**: Automatic rotation when log files reach the configured size
- **Structured Logging**: Optional JSON output for easy parsing and analysis
- **Correlation IDs**: Automatic tracking of related operations across the application
- **Audit Trail**: Comprehensive logging of all DNS changes and operations

**Example with File Logging**:

```yaml
logging:
  enabled: true
  level: DEBUG
  output: both
  log_file: /var/log/tuneup-alpha/app.log
  max_bytes: 52428800  # 50MB
  backup_count: 10
  structured: true
```

**Structured Log Format**:

When `structured: true`, logs are output as JSON lines:

```json
{
  "timestamp": "2025-11-17T20:14:10.391434+00:00",
  "level": "INFO",
  "logger": "tuneup_alpha.cli",
  "message": "Showing configured zones",
  "module": "cli",
  "function": "show",
  "line": 90,
  "correlation_id": "c16249aa-70b6-4d29-bff7-cdc7da93026b"
}
```

**Audit Trail**:

All DNS operations are logged with detailed metadata:

- Zone creation, updates, and deletion
- Record changes with full details
- nsupdate execution status (dry-run vs. live)
- Success/failure status of operations

### Record Types

TuneUp Alpha supports the following DNS record types:

**A Records**: Maps a hostname to an IPv4 address

- `label`: The hostname (use `@` for the zone apex)
- `value`: Must be a valid IPv4 address (e.g., `192.168.1.1`)
- `ttl`: Time to live in seconds (minimum 60)

**AAAA Records**: Maps a hostname to an IPv6 address

- `label`: The hostname (use `@` for the zone apex)
- `value`: Must be a valid IPv6 address (e.g., `2001:db8::1`)
- `ttl`: Time to live in seconds (minimum 60)

**CNAME Records**: Creates an alias to another hostname

- `label`: The alias hostname (cannot be `@`)
- `value`: Target hostname or `@` for the zone apex
- `ttl`: Time to live in seconds (minimum 60)

**MX Records**: Mail exchange records for email routing

- `label`: Domain name (usually `@` for the zone apex)
- `value`: Mail server hostname (e.g., `mail.example.com`)
- `priority`: Mail server priority (lower values have higher priority)
- `ttl`: Time to live in seconds (minimum 60)

**TXT Records**: Text records for SPF, DKIM, DMARC, and verification

- `label`: The hostname or `@` for the zone apex
- `value`: Text content (supports up to 4096 characters, automatically quoted)
- `ttl`: Time to live in seconds (minimum 60)
- Supports long values that are automatically split into multiple strings

**SRV Records**: Service location records

- `label`: Service name (e.g., `_http._tcp`)
- `value`: Target hostname
- `priority`: Service priority
- `weight`: Load balancing weight
- `port`: Service port number
- `ttl`: Time to live in seconds (minimum 60)

**NS Records**: Nameserver delegation records

- `label`: Domain or subdomain name
- `value`: Nameserver hostname
- `ttl`: Time to live in seconds (minimum 60)

**CAA Records**: Certificate Authority Authorization

- `label`: Domain name (usually `@` for the zone apex)
- `value`: CAA record in format `flags tag value` (e.g., `0 issue letsencrypt.org`)
- `ttl`: Time to live in seconds (minimum 60)
- Valid tags: `issue`, `issuewild`, `iodef`

### Validation Rules

- **Labels**: Must contain only alphanumeric characters, hyphens, and underscores. Maximum 63 characters. Cannot start or end with a hyphen.
- **IPv4 Addresses**: Must be in dotted-decimal notation with octets in range 0-255
- **IPv6 Addresses**: Must be a valid IPv6 address in standard or compressed notation
- **Hostnames**: Must follow standard DNS naming conventions
- **TTL**: Minimum value is 60 seconds
- **Priority, Weight, Port**: Must be non-negative integers (port range: 1-65535)

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

For a comprehensive roadmap of planned features and improvements, see [TODO.md](TODO.md).

Key upcoming features include:

- DNS state validation and diff functionality
- Enhanced security features and secrets management
- Backup and restore functionality
- Container packaging for deployment

See the [TODO.md](TODO.md) file for the complete list of planned improvements.
