# Architecture

## Overview

TuneUp Alpha is structured as a modular Python application with clear separation of concerns:

``` bash
src/tuneup_alpha/
├── __init__.py      # Package exports
├── __main__.py      # Entry point for python -m tuneup_alpha
├── cli.py           # Typer CLI commands
├── config.py        # Configuration loading/saving
├── models.py        # Pydantic data models
├── dns_lookup.py    # DNS lookup utilities
├── dns_state.py     # DNS state validation and comparison
├── nsupdate.py      # nsupdate script generation
├── tui.py           # Textual TUI application
└── tui.tcss         # TUI styling
```

## Component Responsibilities

### models.py

Defines the core data structures using Pydantic:

- `Record`: Represents a single DNS record (A or CNAME)
- `Zone`: Represents a DNS zone with its records
- `RecordChange`: Tracks modifications to records
- `AppConfig`: Top-level configuration container

Includes field validators for:

- DNS label format validation
- IPv4 address validation
- Hostname validation

### config.py

Handles configuration persistence:

- `ConfigRepository`: Manages reading/writing YAML config files
- `load_config()`: Helper to load configuration
- `sample_config()`: Generates default configuration
- Follows XDG Base Directory specification for config location

### nsupdate.py

Generates and executes nsupdate scripts:

- `NsupdatePlan`: Builds a sequence of DNS changes
- `NsupdateClient`: Executes plans using the nsupdate command
- Handles record creation, deletion, and updates
- Renders changes into nsupdate script format

### dns_lookup.py

DNS lookup utilities for auto-filling form fields:

- `is_ipv4()`: Validates IPv4 address format
- `is_ipv6()`: Validates IPv6 address format
- `reverse_dns_lookup()`: Performs reverse DNS lookup (IP → hostname) using socket
- `forward_dns_lookup()`: Performs forward DNS lookup (hostname → IP) using socket
- `dig_lookup()`: Executes dig command to lookup DNS records
- `lookup_nameservers()`: Looks up NS records for a domain using dig
- `lookup_a_records()`: Looks up A records for a domain using dig
- `lookup_aaaa_records()`: Looks up AAAA records for a domain using dig
- `lookup_cname_records()`: Looks up CNAME records for a domain using dig
- `lookup_mx_records()`: Looks up MX records for a domain using dig
- `lookup_txt_records()`: Looks up TXT records for a domain using dig
- `lookup_srv_records()`: Looks up SRV records for a domain using dig
- `lookup_caa_records()`: Looks up CAA records for a domain using dig
- `dns_lookup_label()`: Looks up DNS information for a label within a zone
- `dns_lookup()`: Main lookup function that suggests record type and provides related DNS information
- Gracefully handles lookup failures and network errors

### dns_state.py

DNS state validation and comparison utilities:

- `DNSRecordState`: Represents a DNS record as it exists in the live DNS system
- `DNSStateDiff`: Represents the difference between desired and current DNS state
- `query_current_dns_state()`: Queries current DNS records for all labels in a zone
- `compare_dns_state()`: Compares current DNS state with desired configuration
- `validate_dns_state()`: Validates that current DNS state matches desired configuration
- Returns validation results with detailed warnings and change summaries
- Supports all DNS record types (A, AAAA, CNAME, MX, TXT, SRV, NS, CAA)
- Handles priority, weight, and port fields for MX and SRV records

### cli.py

Typer-based command-line interface with commands:

- `init`: Create initial configuration
- `version`: Display version
- `show`: Display configured zones in a table
- `plan`: Preview nsupdate script for a zone (with optional `--show-current` flag)
- `apply`: Execute nsupdate script (with dry-run support, state validation, and confirmation)
- `diff`: Show differences between current DNS state and desired configuration
- `verify`: Verify that current DNS state matches desired configuration
- `tui`: Launch the interactive dashboard

### tui.py

Textual-based interactive dashboard:

- `ZoneDashboard`: Main application screen
- `ZoneFormScreen`: Modal for adding/editing zones with automatic DNS lookup for nameservers and A records
- `RecordFormScreen`: Modal for adding/editing records with DNS lookup integration for both labels and values
- `ConfirmDeleteScreen`: Confirmation dialogs
- Real-time zone and record management
- Tab navigation between zones and records
- Smart DNS lookup that:
  - Auto-fills nameserver field from NS records when creating zones
  - Auto-creates apex A record if discovered when creating zones
  - Auto-fills record type and value when entering labels
  - Auto-fills record type when entering values
  - Provides visual feedback for all DNS lookups

## Data Flow

### CLI Commands Flow

``` bash
User Command → CLI Parser → ConfigRepository → Models → Business Logic → Output
```

### DNS State Validation Flow

``` bash
User Command → DNS State Module → dig lookup → Parse Results → Compare with Config → Generate Diff → Output
```

### TUI Flow

``` bash
User Input → TUI Event Handler → DNS Lookup (optional) → ConfigRepository → Models → Update UI
```

### Apply Flow (with validation)

``` bash
Configuration → DNS State Validation → User Confirmation → Models → NsupdatePlan → NsupdateClient → nsupdate → DNS Server
```

## Configuration Storage

Configuration is stored as YAML following this structure:

```yaml
zones:
  - name: example.com
    server: ns1.example.com
    key_file: /path/to/key
    default_ttl: 3600
    notes: Optional notes
    records:
      - label: "@"
        type: A
        value: 1.2.3.4
        ttl: 600
```

## Validation Strategy

Validation occurs at multiple levels:

1. **Pydantic Models**: Validate data structure and basic types
2. **Field Validators**: Custom validators for DNS-specific formats
3. **Business Logic**: Additional validation in ConfigRepository methods

## Error Handling

- `ConfigError`: Raised for configuration-related issues
- `NsupdateError`: Raised when nsupdate execution fails
- Pydantic `ValidationError`: Raised for invalid data structures

## Extension Points

The architecture supports extension through:

1. Adding new DNS record types to `RecordType` literal
2. Adding new validators to the `Record` model
3. Extending `ConfigRepository` with new operations
4. Adding new CLI commands to `cli.py`
5. Adding new TUI screens for additional features

## Testing Strategy

Tests are organized by component:

- `test_models.py`: Model validation and behavior
- `test_config_repo.py`: Configuration persistence
- `test_nsupdate.py`: Script generation
- `test_cli.py`: CLI commands
- `test_dns_lookup.py`: DNS lookup functionality
- `test_dns_state.py`: DNS state validation and comparison
- `test_tui.py`: TUI form handling and DNS lookup integration

Coverage focuses on business logic and validation, with TUI testing
being minimal due to the difficulty of testing interactive applications.
