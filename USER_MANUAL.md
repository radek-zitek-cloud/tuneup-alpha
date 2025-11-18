# TuneUp Alpha User Manual

Version 0.2.0

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Basic Concepts](#basic-concepts)
4. [Command-Line Interface (CLI)](#command-line-interface-cli)
5. [Textual User Interface (TUI)](#textual-user-interface-tui)
6. [Configuration Management](#configuration-management)
7. [DNS Record Management](#dns-record-management)
8. [Common Workflows](#common-workflows)
9. [Troubleshooting](#troubleshooting)
10. [Tips and Best Practices](#tips-and-best-practices)
11. [FAQ](#faq)

## Introduction

### What is TuneUp Alpha?

TuneUp Alpha is a powerful Python-based toolbox for managing dynamic DNS zones through `nsupdate`. It provides both a command-line interface (CLI) and an interactive text-based user interface (TUI) to help you manage your DNS records efficiently and safely.

### Key Features

- **Configuration-First Approach**: Store your DNS zones and records in a version-controlled YAML file
- **Safe DNS Updates**: Preview changes before applying them with dry-run mode
- **Interactive Dashboard**: Manage zones and records through an intuitive TUI
- **DNS State Validation**: Compare current DNS state with your desired configuration
- **Smart DNS Lookup**: Automatic DNS lookups help you create records faster
- **Comprehensive Logging**: Track all changes with structured audit logs
- **Automation Ready**: Script DNS updates for CI/CD pipelines

### Who Should Use This?

TuneUp Alpha is ideal for:

- System administrators managing multiple DNS zones
- DevOps engineers automating DNS configuration
- IT teams who want version-controlled DNS records
- Anyone who needs safe, repeatable DNS updates

## Getting Started

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL
- **Python**: Version 3.11 or higher
- **DNS Tools**: `nsupdate` command (from BIND utilities)
- **Access**: DNS server that accepts dynamic updates with TSIG keys

### Installation

#### Step 1: Install System Dependencies

**On Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install bind9-utils python3.11 python3-pip python3-venv
```

**On RHEL/CentOS/Fedora:**

```bash
sudo dnf install bind-utils python3.11 python3-pip
```

**On macOS:**

```bash
brew install bind
```

#### Step 2: Install TuneUp Alpha

Create a virtual environment and install the package:

```bash
# Create a virtual environment
python3.11 -m venv ~/.venv/tuneup-alpha

# Activate the virtual environment
source ~/.venv/tuneup-alpha/bin/activate

# Install TuneUp Alpha
pip install tuneup-alpha
```

Or install from source for development:

```bash
git clone https://github.com/radek-zitek-cloud/tuneup-alpha.git
cd tuneup-alpha
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

#### Step 3: Initialize Configuration

Run the initialization command to create your configuration file:

```bash
tuneup-alpha init
```

This creates a configuration file at `~/.config/tuneup-alpha/config.yaml` with sample content.

#### Step 4: Verify Installation

Check the installation:

```bash
tuneup-alpha version
```

You should see version information displayed.

### First-Time Setup

After installation, follow these steps:

1. **Obtain TSIG Keys**: Get the TSIG key files from your DNS administrator or generate them using `tsig-keygen`
2. **Edit Configuration**: Update `~/.config/tuneup-alpha/config.yaml` with your zones and records
3. **Test Connection**: Use `tuneup-alpha plan <zone>` to verify you can connect to your DNS server
4. **Make Your First Update**: Use `tuneup-alpha apply <zone> --dry-run` to preview changes

## Basic Concepts

### DNS Zones

A **zone** represents a DNS domain (e.g., `example.com`) and includes:

- **name**: The domain name (e.g., `example.com`)
- **server**: The DNS server that accepts dynamic updates
- **key_file**: Path to the TSIG key file for authentication
- **default_ttl**: Default time-to-live for records (optional)
- **notes**: Descriptive notes about the zone (optional)
- **records**: List of DNS records in this zone

### DNS Records

A **record** is a single DNS entry within a zone. Each record has:

- **label**: The hostname (use `@` for the zone apex)
- **type**: The DNS record type (A, AAAA, CNAME, MX, TXT, SRV, NS, CAA)
- **value**: The record data (IP address, hostname, etc.)
- **ttl**: Time-to-live in seconds (optional, defaults to zone's default_ttl)
- **priority**: Mail server priority for MX records
- **weight**: Load balancing weight for SRV records
- **port**: Service port number for SRV records

### Configuration File

TuneUp Alpha uses a YAML configuration file to define your DNS infrastructure. By default, this file is located at:

```text
~/.config/tuneup-alpha/config.yaml
```

You can use a different location with the `--config-path` option:

```bash
tuneup-alpha --config-path /path/to/config.yaml <command>
```

### TSIG Keys

TSIG (Transaction Signature) keys are used to authenticate dynamic DNS updates. These are secret keys shared between you and the DNS server. Never commit key files to version control!

## Command-Line Interface (CLI)

### Available Commands

TuneUp Alpha provides eight main commands:

```bash
tuneup-alpha <command> [options]
```

| Command | Purpose |
|---------|---------|
| `init` | Generate a starter configuration file |
| `version` | Display the version of TuneUp Alpha |
| `show` | Display configured zones in a table |
| `tui` | Launch the interactive dashboard |
| `plan` | Preview the nsupdate script for a zone |
| `apply` | Apply DNS changes to a zone |
| `diff` | Show differences between current and desired state |
| `verify` | Verify current DNS state matches configuration |

### init - Initialize Configuration

Create a new configuration file with sample content:

```bash
tuneup-alpha init
```

**Options:**

- `--config-path PATH`: Specify where to create the config file (default: `~/.config/tuneup-alpha/config.yaml`)

**Example:**

```bash
# Create config in custom location
tuneup-alpha init --config-path /etc/tuneup-alpha/config.yaml
```

### version - Show Version

Display the current version:

```bash
tuneup-alpha version
```

**Output:**

```text
TuneUp Alpha version 0.2.0
```

### show - Display Zones

Show all configured zones in a formatted table:

```bash
tuneup-alpha show
```

**Options:**

- `--config-path PATH`: Use a different configuration file

**Output:**

```text
┌─────────────────┬───────────────────┬────────────┬──────────────────────────┐
│ Zone            │ Server            │ Records    │ Notes                    │
├─────────────────┼───────────────────┼────────────┼──────────────────────────┤
│ example.com     │ ns1.example.com   │ 9          │ Production DNS zone      │
│ staging.com     │ ns1.staging.com   │ 5          │ Staging environment      │
└─────────────────┴───────────────────┴────────────┴──────────────────────────┘
```

### tui - Launch Dashboard

Start the interactive Textual User Interface:

```bash
tuneup-alpha tui
```

**Options:**

- `--config-path PATH`: Use a different configuration file

See [Textual User Interface](#textual-user-interface-tui) section for detailed TUI usage.

### plan - Preview Changes

Generate and display the nsupdate script for a zone without executing it:

```bash
tuneup-alpha plan <zone-name>
```

**Arguments:**

- `<zone-name>`: The name of the zone (e.g., `example.com`)

**Options:**

- `--config-path PATH`: Use a different configuration file
- `--show-current`: Also display current DNS state comparison

**Examples:**

```bash
# Preview changes for example.com
tuneup-alpha plan example.com

# Preview with current DNS state
tuneup-alpha plan example.com --show-current
```

**Output (without --show-current):**

```text
server ns1.example.com
zone example.com
update delete example.com. A
update add example.com. 600 A 198.51.100.10
update delete www.example.com. CNAME
update add www.example.com. 300 CNAME example.com.
send
```

**Output (with --show-current):**

```text
DNS State Comparison for example.com:
  Current:
    @ A 192.0.2.1 (TTL: 300)
    www CNAME example.com. (TTL: 600)
  
  Desired:
    @ A 198.51.100.10 (TTL: 600)
    www CNAME @ (TTL: 300)
  
  Changes: 1 to create, 1 to update, 0 to delete

Generated nsupdate script:
server ns1.example.com
zone example.com
update delete example.com. A
update add example.com. 600 A 198.51.100.10
update delete www.example.com. CNAME
update add www.example.com. 300 CNAME example.com.
send
```

### apply - Apply Changes

Execute the nsupdate script to apply DNS changes:

```bash
tuneup-alpha apply <zone-name> [options]
```

**Arguments:**

- `<zone-name>`: The name of the zone (e.g., `example.com`)

**Options:**

- `--config-path PATH`: Use a different configuration file
- `--dry-run`: Generate script but don't execute (default: true)
- `--no-dry-run`: Actually execute the script
- `--force`: Skip validation and confirmation prompts

**Examples:**

```bash
# Dry run (shows what would happen)
tuneup-alpha apply example.com
tuneup-alpha apply example.com --dry-run

# Apply changes with confirmation
tuneup-alpha apply example.com --no-dry-run

# Apply changes without confirmation (use with caution!)
tuneup-alpha apply example.com --no-dry-run --force
```

**Workflow with --no-dry-run:**

1. Queries current DNS state
2. Shows summary of changes
3. Warns about destructive operations (deletions)
4. Asks for confirmation
5. Executes nsupdate
6. Reports success or failure

**Output Example:**

```text
⚠ Warning: Changes will be applied:
  1 record(s) to create, 1 to update, 0 to delete

Do you want to proceed? [y/N]: y

Executing nsupdate...
✓ Successfully updated zone example.com
```

### diff - Show Differences

Compare current DNS state with your desired configuration:

```bash
tuneup-alpha diff <zone-name>
```

**Arguments:**

- `<zone-name>`: The name of the zone (e.g., `example.com`)

**Options:**

- `--config-path PATH`: Use a different configuration file

**Example:**

```bash
tuneup-alpha diff example.com
```

**Output:**

```text
DNS State Differences for example.com:
  1 record(s) to create
  1 record(s) to update
  1 record(s) to delete

Detailed Changes:
  + mail A 203.0.113.50 (TTL: 300)
  ~ @ A 198.51.100.10 (TTL: 600) [current: 192.0.2.1 (TTL: 300)]
  - old A 198.51.100.100
```

**Legend:**

- `+` = Record to be created (missing in DNS)
- `~` = Record to be updated (different in DNS)
- `-` = Record to be deleted (extra in DNS)

### verify - Verify State

Check if current DNS state matches your configuration:

```bash
tuneup-alpha verify <zone-name>
```

**Arguments:**

- `<zone-name>`: The name of the zone (e.g., `example.com`)

**Options:**

- `--config-path PATH`: Use a different configuration file

**Example:**

```bash
tuneup-alpha verify example.com
```

**Output when valid:**

```text
✓ Zone 'example.com' is valid and matches configuration
```

**Output when invalid:**

```text
✗ Zone 'example.com' validation failed:
  DNS state mismatch: 1 to create, 1 to update, 1 to delete
  Missing: mail A 203.0.113.50
  Changed: @ A (current: 192.0.2.1, expected: 198.51.100.10)
  Extra: old A 198.51.100.100
```

## Textual User Interface (TUI)

### Launching the TUI

Start the interactive dashboard:

```bash
tuneup-alpha tui
```

The TUI provides a visual interface for managing zones and records without editing YAML files directly.

### TUI Layout

The dashboard has two main sections:

```text
┌─────────────────────────────────────────────────────────────┐
│ TuneUp Alpha - DNS Zone Manager                             │
├─────────────────────────┬───────────────────────────────────┤
│ Zones                   │ Records (for selected zone)       │
│                         │                                   │
│ • example.com           │ @ A 198.51.100.10 (TTL: 600)     │
│   staging.com           │ www CNAME @ (TTL: 300)            │
│                         │ mail A 203.0.113.50 (TTL: 300)   │
│                         │                                   │
├─────────────────────────┴───────────────────────────────────┤
│ [z] Focus Zones  [r] Focus Records  [a] Add  [e] Edit       │
│ [d] Delete  [l] Reload  [t] Theme  [q] Quit                 │
└─────────────────────────────────────────────────────────────┘
```

### Keyboard Shortcuts

#### Navigation

| Key | Action |
|-----|--------|
| `z` | Focus the zones pane |
| `r` | Focus the records pane |
| `↑` `↓` | Navigate up/down in the active pane |
| `Tab` | Switch between panes |

#### Actions (work on the focused pane)

| Key | Action |
|-----|--------|
| `a` | Add a new zone or record |
| `e` | Edit the selected zone or record |
| `d` | Delete the selected zone or record |
| `l` | Reload configuration from disk |
| `t` | Cycle through available themes |
| `Esc` | Cancel current form/dialog |
| `q` | Quit the application (saves theme) |

### Managing Zones

#### Adding a Zone

1. Press `z` to focus the zones pane
2. Press `a` to open the Add Zone form
3. Fill in the zone details:
   - **Zone Name**: Enter the domain (e.g., `example.com`)
     - The TUI automatically looks up NS records
     - If found, the nameserver field is pre-filled
     - If A records are found, an apex record is auto-created
   - **DNS Server**: The nameserver to use (auto-filled if discovered)
   - **Key File**: Path to the TSIG key file
   - **Default TTL**: Default TTL for records (optional, default: 3600)
   - **Notes**: Optional description
4. Press `Enter` or click Submit to save
5. Press `Esc` to cancel

**Visual Feedback:**

- `⏳ Checking...`: DNS lookup in progress
- `✓ Found X NS records`: Successfully discovered nameservers
- `○ No NS records found`: No nameservers discovered
- Similar feedback for A records

#### Editing a Zone

1. Press `z` to focus the zones pane
2. Use arrow keys to select the zone
3. Press `e` to open the Edit Zone form
4. Modify the fields as needed
5. Press `Enter` or click Submit to save
6. Press `Esc` to cancel

**Note:** Changing the zone name creates a new zone and deletes the old one.

#### Deleting a Zone

1. Press `z` to focus the zones pane
2. Use arrow keys to select the zone
3. Press `d` to open the delete confirmation
4. Confirm the deletion

**Warning:** This deletes the zone and all its records from the configuration file only. It does NOT delete records from the DNS server.

### Managing Records

#### Adding a Record

1. Press `r` to focus the records pane
2. Press `a` to open the Add Record form
3. Fill in the record details:
   - **Label**: The hostname or `@` for apex
     - The TUI performs automatic DNS lookup for the label
     - If CNAME found: auto-fills type as CNAME and value with target
     - If A record found: auto-fills type as A and value with IP
     - Shows visual feedback (✓, ○, or ⏳)
   - **Type**: DNS record type (A, AAAA, CNAME, MX, TXT, SRV, NS, CAA)
     - Auto-filled based on value if you enter value first
   - **Value**: The record data
     - For IP addresses: auto-detects as A/AAAA record
     - For hostnames: auto-detects as CNAME record
     - Performs reverse/forward DNS lookup for validation
   - **TTL**: Time-to-live in seconds (minimum 60)
   - **Priority**: For MX and SRV records (required)
   - **Weight**: For SRV records (required)
   - **Port**: For SRV records (required)
4. Press `Enter` or click Submit to save
5. Press `Esc` to cancel

**Smart DNS Lookup Features:**

When entering a **label**:

- Automatically queries `label.zone.com`
- Shows discovered record type and value
- Pre-fills form fields based on discovery

When entering a **value**:

- For IP addresses (e.g., `192.0.2.1`):
  - Sets type to `A`
  - Performs reverse DNS lookup
  - Shows hostname if found
- For hostnames (e.g., `www.example.com`):
  - Sets type to `CNAME`
  - Performs forward DNS lookup
  - Shows IP address if found

#### Editing a Record

1. Press `r` to focus the records pane
2. Use arrow keys to select the record
3. Press `e` to open the Edit Record form
4. Modify the fields as needed (DNS lookup also works here)
5. Press `Enter` or click Submit to save
6. Press `Esc` to cancel

#### Deleting a Record

1. Press `r` to focus the records pane
2. Use arrow keys to select the record
3. Press `d` to open the delete confirmation
4. Confirm the deletion

**Warning:** This deletes the record from the configuration file only. It does NOT delete the record from the DNS server.

### Theme Customization

TuneUp Alpha includes 12 built-in themes:

1. `textual-dark` (default)
2. `textual-light`
3. `nord`
4. `gruvbox`
5. `catppuccin-mocha`
6. `textual-ansi`
7. `dracula`
8. `tokyo-night`
9. `monokai`
10. `flexoki`
11. `catppuccin-latte`
12. `solarized-light`

**To change theme:**

- Press `t` repeatedly to cycle through themes
- The selected theme is saved when you quit
- On next launch, your theme is restored

**Manual theme selection:**

Edit your configuration file:

```yaml
theme: nord
zones:
  - name: example.com
    ...
```

### Reloading Configuration

If you edit the configuration file while the TUI is running:

1. Press `l` to reload from disk
2. The TUI refreshes with updated data

**Note:** Unsaved changes in the TUI are lost when reloading.

## Configuration Management

### Configuration File Structure

The configuration file uses YAML format:

```yaml
# Optional: Prefix path for key files
prefix_key_path: /etc/nsupdate

# Optional: Logging configuration
logging:
  enabled: true
  level: INFO
  output: console
  log_file: null
  max_bytes: 10485760
  backup_count: 5
  structured: false

# Optional: TUI theme
theme: nord

# Required: List of zones
zones:
  - name: example.com
    server: ns1.example.com
    key_file: /etc/nsupdate/example.com.key
    default_ttl: 3600
    notes: Production zone
    records:
      - label: "@"
        type: A
        value: 198.51.100.10
        ttl: 600
```

### Configuration Options

#### Global Settings

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prefix_key_path` | string | No | null | Prefix path for relative key file paths |
| `logging` | object | No | (defaults) | Logging configuration (see below) |
| `theme` | string | No | `textual-dark` | TUI color theme |
| `zones` | array | Yes | - | List of DNS zones |

#### Zone Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Domain name (e.g., `example.com`) |
| `server` | string | Yes | - | DNS server hostname or IP |
| `key_file` | string | Yes | - | Path to TSIG key file |
| `default_ttl` | integer | No | 3600 | Default TTL for records |
| `notes` | string | No | empty | Optional description |
| `records` | array | Yes | - | List of DNS records |

#### Record Configuration

**Common fields for all record types:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | string | Yes | Hostname or `@` for apex |
| `type` | string | Yes | Record type: A, AAAA, CNAME, MX, TXT, SRV, NS, CAA |
| `value` | string | Yes | Record data (format depends on type) |
| `ttl` | integer | No | Time-to-live in seconds (minimum 60) |

**Additional fields for MX records:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `priority` | integer | Yes | Mail server priority (lower = higher priority) |

**Additional fields for SRV records:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `priority` | integer | Yes | Service priority |
| `weight` | integer | Yes | Load balancing weight |
| `port` | integer | Yes | Service port number (1-65535) |

#### Logging Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | boolean | true | Enable/disable logging |
| `level` | string | INFO | Log level: DEBUG, INFO, WARNING, ERROR |
| `output` | string | console | Output: console, file, or both |
| `log_file` | string | null | Path to log file (required for file/both) |
| `max_bytes` | integer | 10485760 | Max file size before rotation (bytes) |
| `backup_count` | integer | 5 | Number of rotated files to keep |
| `structured` | boolean | false | Use JSON structured logging |

### Validation Rules

#### Labels

- Must contain only alphanumeric characters, hyphens, underscores, and dots
- Maximum 63 characters
- Cannot start or end with a hyphen
- Use `@` for the zone apex

#### IPv4 Addresses

- Must be in dotted-decimal notation (e.g., `192.0.2.1`)
- Each octet must be 0-255

#### IPv6 Addresses

- Must be valid IPv6 address
- Supports standard and compressed notation
- Example: `2001:db8::1`

#### Hostnames

- Must follow DNS naming conventions
- Can be relative (within zone) or fully-qualified
- Use `@` to reference the zone apex in CNAME values

#### TTL Values

- Minimum: 60 seconds
- Recommended: 300-3600 seconds
- Use lower values for records that change frequently
- Use higher values for stable records

#### Priority, Weight, Port

- Must be non-negative integers
- Port range: 1-65535
- Priority and weight: 0-65535

### Configuration Examples

#### Simple Website

```yaml
zones:
  - name: example.com
    server: ns1.example.com
    key_file: /etc/nsupdate/example.com.key
    records:
      # Apex A record
      - label: "@"
        type: A
        value: 203.0.113.10
      
      # WWW CNAME
      - label: www
        type: CNAME
        value: "@"
```

#### Email Configuration

```yaml
zones:
  - name: example.com
    server: ns1.example.com
    key_file: /etc/nsupdate/example.com.key
    records:
      # Domain apex
      - label: "@"
        type: A
        value: 203.0.113.10
      
      # Mail server
      - label: mail
        type: A
        value: 203.0.113.50
      
      # MX record
      - label: "@"
        type: MX
        value: mail.example.com
        priority: 10
      
      # SPF record
      - label: "@"
        type: TXT
        value: "v=spf1 mx ~all"
```

#### Multi-Environment Setup

```yaml
zones:
  # Production
  - name: example.com
    server: ns1.example.com
    key_file: /etc/nsupdate/production.key
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
  
  # Staging
  - name: staging.example.com
    server: ns1.example.com
    key_file: /etc/nsupdate/staging.key
    notes: Staging environment
    records:
      - label: "@"
        type: A
        value: 198.51.100.10
      - label: www
        type: CNAME
        value: "@"
      - label: api
        type: A
        value: 198.51.100.20
```

## DNS Record Management

### Supported Record Types

#### A Records (IPv4 Address)

Maps a hostname to an IPv4 address.

**Configuration:**

```yaml
- label: "@"
  type: A
  value: 192.0.2.1
  ttl: 600
```

**Use cases:**

- Website hosting
- Server addresses
- Application endpoints

#### AAAA Records (IPv6 Address)

Maps a hostname to an IPv6 address.

**Configuration:**

```yaml
- label: "@"
  type: AAAA
  value: 2001:db8::1
  ttl: 600
```

**Use cases:**

- IPv6 connectivity
- Dual-stack environments
- Modern infrastructure

#### CNAME Records (Canonical Name)

Creates an alias pointing to another hostname.

**Configuration:**

```yaml
- label: www
  type: CNAME
  value: "@"  # or use full hostname: example.com.
  ttl: 300
```

**Important:**

- Cannot be used at zone apex (`@`)
- Cannot coexist with other record types for the same label
- Use `@` in value to point to zone apex

**Use cases:**

- WWW to apex redirection
- Service aliases
- CDN configuration

#### MX Records (Mail Exchange)

Specifies mail servers for the domain.

**Configuration:**

```yaml
- label: "@"
  type: MX
  value: mail.example.com
  priority: 10
  ttl: 3600
```

**Priority:**

- Lower number = higher priority
- Use 10, 20, 30 for multiple servers
- Primary server gets lowest number

**Use cases:**

- Email routing
- Backup mail servers
- Spam filtering services

#### TXT Records (Text)

Stores arbitrary text data, commonly used for verification and policies.

**Configuration:**

```yaml
- label: "@"
  type: TXT
  value: "v=spf1 include:_spf.example.com ~all"
  ttl: 3600
```

**Features:**

- Supports up to 4096 characters
- Automatically quoted
- Long values split into multiple strings

**Common uses:**

- SPF (Sender Policy Framework)
- DKIM (DomainKeys Identified Mail)
- DMARC (Domain-based Message Authentication)
- Domain verification (Google, Microsoft, etc.)
- Site ownership verification

**Examples:**

```yaml
# SPF record
- label: "@"
  type: TXT
  value: "v=spf1 mx include:_spf.google.com ~all"

# DMARC record
- label: _dmarc
  type: TXT
  value: "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"

# Domain verification
- label: "@"
  type: TXT
  value: "google-site-verification=abc123def456"
```

#### SRV Records (Service)

Specifies the location of services.

**Configuration:**

```yaml
- label: _http._tcp
  type: SRV
  value: server.example.com
  priority: 10
  weight: 60
  port: 80
  ttl: 3600
```

**Fields:**

- **priority**: Lower = higher priority
- **weight**: Load distribution (higher = more traffic)
- **port**: Service port number
- **value**: Target hostname

**Use cases:**

- Service discovery
- Load balancing
- VoIP/SIP configuration
- XMPP/Jabber servers

**Example:**

```yaml
# SIP service
- label: _sip._tcp
  type: SRV
  value: sip.example.com
  priority: 10
  weight: 50
  port: 5060

# XMPP service
- label: _xmpp-client._tcp
  type: SRV
  value: xmpp.example.com
  priority: 5
  weight: 0
  port: 5222
```

#### NS Records (Name Server)

Delegates a subdomain to specific nameservers.

**Configuration:**

```yaml
- label: subdomain
  type: NS
  value: ns1.example.com
  ttl: 3600
```

**Use cases:**

- Subdomain delegation
- Separate DNS hosting
- Multi-provider setups

**Example:**

```yaml
# Delegate subdomain to different nameserver
- label: dev
  type: NS
  value: ns1.devops.example.com

- label: dev
  type: NS
  value: ns2.devops.example.com
```

#### CAA Records (Certification Authority Authorization)

Specifies which CAs can issue certificates for your domain.

**Configuration:**

```yaml
- label: "@"
  type: CAA
  value: "0 issue letsencrypt.org"
  ttl: 3600
```

**Format:** `flags tag value`

**Tags:**

- `issue`: Authorize CA to issue certificates
- `issuewild`: Authorize CA to issue wildcard certificates
- `iodef`: Report policy violations to URL

**Use cases:**

- SSL/TLS certificate control
- Security hardening
- Compliance requirements

**Examples:**

```yaml
# Allow Let's Encrypt
- label: "@"
  type: CAA
  value: "0 issue letsencrypt.org"

# Allow Let's Encrypt for wildcards
- label: "@"
  type: CAA
  value: "0 issuewild letsencrypt.org"

# Disallow all issuance
- label: "@"
  type: CAA
  value: "0 issue ;"

# Report violations
- label: "@"
  type: CAA
  value: "0 iodef mailto:security@example.com"
```

## Common Workflows

### Workflow 1: Initial Zone Setup

**Scenario:** You need to set up DNS for a new domain.

**Steps:**

1. **Obtain TSIG key from DNS administrator**

2. **Add zone to configuration:**

   ```bash
   tuneup-alpha tui
   # Press 'z', then 'a' to add zone
   # Fill in: example.com, ns1.provider.com, /path/to/key
   ```

3. **Add basic records:**

   ```bash
   # Still in TUI, press 'r', then 'a' to add records
   # Add @ A record
   # Add www CNAME record
   ```

4. **Preview the changes:**

   ```bash
   tuneup-alpha plan example.com
   ```

5. **Apply with dry-run:**

   ```bash
   tuneup-alpha apply example.com --dry-run
   ```

6. **Apply for real:**

   ```bash
   tuneup-alpha apply example.com --no-dry-run
   ```

7. **Verify the results:**

   ```bash
   tuneup-alpha verify example.com
   ```

### Workflow 2: Adding a New Record

**Scenario:** You need to add a new subdomain to an existing zone.

**Option A: Using TUI**

1. Launch TUI: `tuneup-alpha tui`
2. Press `r` to focus records pane
3. Press `a` to add record
4. Enter label (e.g., `api`) - watch for DNS lookup feedback
5. Enter value (e.g., `203.0.113.20`) - type auto-detected as A
6. Submit the form
7. Exit TUI (saves automatically)
8. Apply: `tuneup-alpha apply example.com --no-dry-run`

**Option B: Editing YAML**

1. Edit config: `vi ~/.config/tuneup-alpha/config.yaml`
2. Add record to appropriate zone:
   ```yaml
   - label: api
     type: A
     value: 203.0.113.20
     ttl: 300
   ```
3. Save and exit
4. Preview: `tuneup-alpha plan example.com`
5. Apply: `tuneup-alpha apply example.com --no-dry-run`
6. Verify: `tuneup-alpha verify example.com`

### Workflow 3: Updating an Existing Record

**Scenario:** You need to change the IP address for a hostname.

**Steps:**

1. **Using TUI:**
   - `tuneup-alpha tui`
   - Navigate to record and press `e`
   - Update the value
   - Submit and exit

2. **Or edit config file directly**

3. **Check what will change:**

   ```bash
   tuneup-alpha diff example.com
   ```

4. **Apply the change:**

   ```bash
   tuneup-alpha apply example.com --no-dry-run
   ```

5. **Verify:**

   ```bash
   tuneup-alpha verify example.com
   ```

### Workflow 4: Removing a Record

**Scenario:** You need to remove a record that's no longer needed.

**Steps:**

1. **Remove from configuration:**

   ```bash
   tuneup-alpha tui
   # Navigate to record, press 'd', confirm deletion
   ```

2. **Check the planned deletion:**

   ```bash
   tuneup-alpha diff example.com
   # Should show the record marked for deletion
   ```

3. **Apply the change:**

   ```bash
   tuneup-alpha apply example.com --no-dry-run
   # Review the warning about deletions
   # Confirm when prompted
   ```

**Important:** The record is removed from DNS when you apply. Make sure you really want to delete it!

### Workflow 5: DNS State Validation

**Scenario:** You want to verify your DNS matches your configuration.

**Steps:**

1. **Quick verification:**

   ```bash
   tuneup-alpha verify example.com
   ```

2. **If verification fails, see details:**

   ```bash
   tuneup-alpha diff example.com
   ```

3. **Decide on action:**
   - If DNS is correct: Update your config file
   - If config is correct: Apply the changes

4. **Apply configuration to DNS:**

   ```bash
   tuneup-alpha apply example.com --no-dry-run
   ```

5. **Re-verify:**

   ```bash
   tuneup-alpha verify example.com
   ```

### Workflow 6: Multi-Zone Management

**Scenario:** You manage multiple zones and want to update them all.

**Steps:**

1. **View all zones:**

   ```bash
   tuneup-alpha show
   ```

2. **Update configurations for each:**

   Edit `~/.config/tuneup-alpha/config.yaml` or use TUI

3. **Plan all zones:**

   ```bash
   for zone in example.com staging.com; do
     echo "=== $zone ==="
     tuneup-alpha plan $zone
   done
   ```

4. **Apply all zones:**

   ```bash
   for zone in example.com staging.com; do
     echo "=== Applying $zone ==="
     tuneup-alpha apply $zone --no-dry-run
   done
   ```

5. **Verify all zones:**

   ```bash
   for zone in example.com staging.com; do
     echo "=== Verifying $zone ==="
     tuneup-alpha verify $zone
   done
   ```

### Workflow 7: Configuration Backup and Restore

**Scenario:** You want to back up your DNS configuration.

**Backup:**

```bash
# Create backup directory
mkdir -p ~/backups/tuneup-alpha

# Copy configuration
cp ~/.config/tuneup-alpha/config.yaml \
   ~/backups/tuneup-alpha/config-$(date +%Y%m%d).yaml

# Or use git
cd ~/.config/tuneup-alpha
git init
git add config.yaml
git commit -m "Initial DNS configuration"
```

**Restore:**

```bash
# From backup file
cp ~/backups/tuneup-alpha/config-20241117.yaml \
   ~/.config/tuneup-alpha/config.yaml

# Or from git
cd ~/.config/tuneup-alpha
git checkout config.yaml
```

### Workflow 8: Emergency Rollback

**Scenario:** You applied changes that broke something and need to rollback quickly.

**Steps:**

1. **Restore previous configuration:**

   ```bash
   cp ~/backups/tuneup-alpha/config-previous.yaml \
      ~/.config/tuneup-alpha/config.yaml
   ```

2. **Apply immediately with force:**

   ```bash
   tuneup-alpha apply example.com --no-dry-run --force
   ```

3. **Verify:**

   ```bash
   tuneup-alpha verify example.com
   ```

**Prevention:** Always back up before major changes!

## Troubleshooting

### Common Issues

#### Issue: "nsupdate: command not found"

**Cause:** BIND utilities are not installed.

**Solution:**

```bash
# Ubuntu/Debian
sudo apt-get install bind9-utils

# RHEL/CentOS/Fedora
sudo dnf install bind-utils

# macOS
brew install bind
```

#### Issue: "Permission denied" when accessing key file

**Cause:** Incorrect file permissions on TSIG key file.

**Solution:**

```bash
# Set appropriate permissions
chmod 600 /path/to/key/file
chown $USER /path/to/key/file
```

#### Issue: "Failed to connect to DNS server"

**Causes:**

- DNS server is down
- Firewall blocking port 53
- Incorrect server address
- Network connectivity issue

**Solutions:**

1. **Test connectivity:**

   ```bash
   ping ns1.example.com
   dig @ns1.example.com example.com
   ```

2. **Check firewall:**

   ```bash
   # Allow DNS traffic
   sudo ufw allow 53/tcp
   sudo ufw allow 53/udp
   ```

3. **Verify server address:**

   ```bash
   tuneup-alpha show
   # Check if server address is correct
   ```

#### Issue: "TSIG authentication failed"

**Causes:**

- Incorrect key file
- Key not authorized on server
- Clock skew between client and server

**Solutions:**

1. **Verify key file:**

   ```bash
   cat /path/to/key/file
   # Should contain a valid TSIG key
   ```

2. **Check time sync:**

   ```bash
   # Ensure system time is correct
   timedatectl status
   ntpdate -q pool.ntp.org
   ```

3. **Contact DNS administrator** to verify key is authorized

#### Issue: "Zone validation failed"

**Cause:** DNS state doesn't match configuration.

**Solution:**

1. **See what's different:**

   ```bash
   tuneup-alpha diff example.com
   ```

2. **Decide which is correct:**
   - If DNS is correct: Update config
   - If config is correct: Apply changes

3. **Apply if needed:**

   ```bash
   tuneup-alpha apply example.com --no-dry-run
   ```

#### Issue: "Invalid configuration file"

**Cause:** YAML syntax error or validation failure.

**Solution:**

1. **Check YAML syntax:**

   ```bash
   # Use a YAML validator
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

2. **Common YAML mistakes:**
   - Inconsistent indentation (use spaces, not tabs)
   - Missing quotes around special characters
   - Incorrect list/dict syntax
   - Typos in field names

3. **Restore from backup if needed**

#### Issue: TUI not displaying correctly

**Causes:**

- Terminal doesn't support required features
- Terminal too small
- Color scheme issues

**Solutions:**

1. **Use a modern terminal:**
   - iTerm2 (macOS)
   - Windows Terminal (Windows)
   - GNOME Terminal, Konsole (Linux)

2. **Resize terminal:**
   - Minimum 80x24 characters
   - Recommended: 120x30 or larger

3. **Try different theme:**

   Press `t` in TUI to cycle themes

#### Issue: DNS lookup not working in TUI

**Cause:** `dig` command not available or network issue.

**Solution:**

1. **Install dig:**

   ```bash
   # Ubuntu/Debian
   sudo apt-get install dnsutils

   # RHEL/CentOS/Fedora
   sudo dnf install bind-utils
   ```

2. **Check network:**

   ```bash
   dig google.com
   ```

3. **Continue without DNS lookup:**
   - The feature is optional
   - Manually enter record details

### Getting Help

#### Enable Debug Logging

For detailed troubleshooting, enable debug logging:

```yaml
logging:
  enabled: true
  level: DEBUG
  output: both
  log_file: /tmp/tuneup-debug.log
```

Then run your command and check the log:

```bash
tail -f /tmp/tuneup-debug.log
```

#### Check Application Version

```bash
tuneup-alpha version
```

#### Review Documentation

- README: General overview and quick start
- ARCHITECTURE: Technical details about components
- LOGGING: Comprehensive logging guide
- This manual: User guide

#### Report Issues

If you encounter a bug:

1. Enable debug logging
2. Reproduce the issue
3. Collect logs and error messages
4. Report on GitHub: https://github.com/radek-zitek-cloud/tuneup-alpha/issues

Include:

- Python version
- Operating system
- TuneUp Alpha version
- Steps to reproduce
- Error messages and logs

## Tips and Best Practices

### Configuration Management

1. **Use Version Control**

   Store your configuration in Git:

   ```bash
   cd ~/.config/tuneup-alpha
   git init
   git add config.yaml
   git commit -m "Initial DNS configuration"
   ```

2. **Keep Key Files Separate**

   Never commit TSIG keys to version control:

   ```bash
   # In .gitignore
   *.key
   *.private
   ```

3. **Document Your Zones**

   Use the notes field:

   ```yaml
   zones:
     - name: example.com
       notes: "Production - contact ops@example.com for changes"
   ```

4. **Use Consistent TTL Values**

   Set sensible defaults:
   - Stable records: 3600 seconds (1 hour)
   - Frequently changing: 300 seconds (5 minutes)
   - Emergency changes: 60 seconds (minimum)

### Safe DNS Updates

1. **Always Preview First**

   ```bash
   tuneup-alpha plan example.com
   ```

2. **Use Dry-Run Mode**

   ```bash
   tuneup-alpha apply example.com --dry-run
   ```

3. **Verify After Changes**

   ```bash
   tuneup-alpha verify example.com
   ```

4. **Back Up Before Major Changes**

   ```bash
   cp ~/.config/tuneup-alpha/config.yaml \
      ~/backups/config-$(date +%Y%m%d-%H%M%S).yaml
   ```

5. **Test in Staging First**

   If possible, test changes in a staging zone before production.

### Performance Tips

1. **Use Appropriate TTL Values**
   - Higher TTL = better caching, slower changes
   - Lower TTL = faster changes, more DNS queries

2. **Batch Multiple Changes**

   Make multiple changes at once rather than many small updates.

3. **Use Local Configuration**

   For CI/CD, use `--config-path` to specify config:

   ```bash
   tuneup-alpha --config-path ./dns-config.yaml apply example.com
   ```

### Security Best Practices

1. **Protect TSIG Keys**

   ```bash
   chmod 600 /path/to/key/file
   chown $USER /path/to/key/file
   ```

2. **Use Separate Keys Per Zone**

   Don't reuse the same key for multiple zones.

3. **Enable Audit Logging**

   ```yaml
   logging:
     enabled: true
     level: INFO
     output: file
     log_file: /var/log/tuneup-alpha/audit.log
     structured: true
   ```

4. **Review Logs Regularly**

   ```bash
   tail -f /var/log/tuneup-alpha/audit.log
   ```

5. **Limit Access to Configuration**

   ```bash
   chmod 600 ~/.config/tuneup-alpha/config.yaml
   ```

### Automation Tips

1. **Use Scripts for Bulk Operations**

   ```bash
   #!/bin/bash
   for zone in $(tuneup-alpha show --format=plain | awk '{print $1}'); do
     tuneup-alpha verify $zone
   done
   ```

2. **Integrate with CI/CD**

   ```yaml
   # GitLab CI example
   deploy-dns:
     script:
       - tuneup-alpha --config-path ./dns.yaml plan example.com
       - tuneup-alpha --config-path ./dns.yaml apply example.com --no-dry-run --force
   ```

3. **Use Make for Common Tasks**

   ```makefile
   .PHONY: plan apply verify
   
   plan:
       tuneup-alpha plan example.com
   
   apply:
       tuneup-alpha apply example.com --no-dry-run
   
   verify:
       tuneup-alpha verify example.com
   ```

### TUI Tips

1. **Learn Keyboard Shortcuts**

   Practice the main shortcuts:
   - `z` / `r` for navigation
   - `a` / `e` / `d` for actions
   - `l` to reload

2. **Use DNS Lookup Effectively**

   When adding records:
   - Enter the label first to auto-discover existing records
   - Enter the value to auto-detect record type

3. **Customize Your Theme**

   Find a theme you like and set it in config:

   ```yaml
   theme: nord
   ```

4. **Reload After External Edits**

   If you edit the config file externally, press `l` in TUI.

## FAQ

### General Questions

**Q: What is TuneUp Alpha?**

A: TuneUp Alpha is a tool for managing DNS zones using nsupdate. It provides both CLI and TUI interfaces for safe, version-controlled DNS management.

**Q: Is it free?**

A: Yes, TuneUp Alpha is open source under the MIT license.

**Q: Does it work on Windows?**

A: Yes, via WSL (Windows Subsystem for Linux).

**Q: Can I manage DNS servers from different providers?**

A: Yes, as long as they support dynamic updates via nsupdate with TSIG authentication.

### Installation and Setup

**Q: Do I need to install BIND?**

A: No, you only need the `nsupdate` client utility (from bind-utils or bind9-utils package).

**Q: Where should I store TSIG keys?**

A: Store them in a secure directory like `/etc/nsupdate/` with permissions 600. Never commit them to version control.

**Q: Can I use relative paths for key files?**

A: Yes, use the `prefix_key_path` configuration option to set a base directory.

### Configuration

**Q: Can I manage multiple zones?**

A: Yes, add multiple zones to your configuration file.

**Q: How do I backup my configuration?**

A: Copy the YAML file to a backup location. Better yet, use Git version control.

**Q: Can I have comments in the configuration file?**

A: Yes, YAML supports comments with `#`.

**Q: What's the difference between `@` and the zone name?**

A: `@` is a shorthand for the zone apex. Both refer to the same thing.

### DNS Records

**Q: Can I create wildcard records?**

A: Yes, use `*` as the label:

```yaml
- label: "*"
  type: A
  value: 192.0.2.1
```

**Q: How do I create multiple A records for the same label?**

A: Add multiple record entries with the same label but different values:

```yaml
- label: www
  type: A
  value: 192.0.2.1
- label: www
  type: A
  value: 192.0.2.2
```

**Q: Can I use CNAMEs at the zone apex?**

A: No, this violates DNS standards. Use A or AAAA records instead.

**Q: What's the minimum TTL I can use?**

A: 60 seconds is the minimum enforced by TuneUp Alpha.

### Operations

**Q: What does dry-run mode do?**

A: It generates the nsupdate script but doesn't execute it, so you can preview changes safely.

**Q: Can I undo changes after applying?**

A: Not automatically. You must restore your previous configuration and apply it again. This is why backups are important!

**Q: Does the TUI save changes automatically?**

A: Yes, changes in the TUI are saved immediately to the configuration file.

**Q: Do I need to restart anything after changing configuration?**

A: No, but if the TUI is running, press `l` to reload from disk.

**Q: Can I schedule automatic DNS updates?**

A: Yes, use cron or systemd timers to run `tuneup-alpha apply` commands.

### Troubleshooting

**Q: Why do I get "TSIG authentication failed"?**

A: Check that:
- The key file is correct
- The key is authorized on the DNS server
- Your system time is synchronized

**Q: Why doesn't my change appear in DNS?**

A: Check:
- Did you run `apply` with `--no-dry-run`?
- Did it succeed? Check for error messages
- DNS caching - wait for TTL to expire
- Use `verify` to check current state

**Q: The TUI looks broken. What should I do?**

A: Try:
- Using a modern terminal emulator
- Resizing your terminal window
- Pressing `t` to change themes
- Running in a different terminal

**Q: How do I see what changed?**

A: Use the `diff` command:

```bash
tuneup-alpha diff example.com
```

### Advanced Usage

**Q: Can I use this in CI/CD pipelines?**

A: Yes! Use `--config-path` to specify config and `--force` to skip prompts:

```bash
tuneup-alpha --config-path ./dns.yaml apply example.com --no-dry-run --force
```

**Q: Can I export metrics?**

A: Not directly, but use structured logging with log analysis tools.

**Q: Is there an API?**

A: No, but you can use the CLI from scripts.

**Q: Can I manage secondary DNS servers?**

A: You typically only need to update the primary server. Secondary servers get updates via zone transfers.

**Q: How do I handle zone delegation?**

A: Use NS records to delegate subdomains:

```yaml
- label: subdomain
  type: NS
  value: ns1.other-provider.com
```

### Logging and Auditing

**Q: Where are logs stored?**

A: Depends on your configuration. By default, logs go to console. Configure `log_file` for file logging.

**Q: What's structured logging?**

A: JSON-formatted logs that are easier to parse and analyze programmatically.

**Q: Can I track who made changes?**

A: Logs include correlation IDs to trace operations, but user tracking requires integration with your access control system.

**Q: How long should I keep logs?**

A: Depends on your compliance requirements. For general use, 30-90 days is reasonable.

---

## Getting More Help

- **GitHub Repository**: https://github.com/radek-zitek-cloud/tuneup-alpha
- **Issue Tracker**: https://github.com/radek-zitek-cloud/tuneup-alpha/issues
- **Documentation**: See README.md, ARCHITECTURE.md, and LOGGING.md

For administrator-specific information, see the [Admin Manual](ADMIN_MANUAL.md).
