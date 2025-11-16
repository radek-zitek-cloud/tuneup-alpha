# Architecture

## Overview

TuneUp Alpha is structured as a modular Python application with clear separation of concerns:

```
src/tuneup_alpha/
├── __init__.py      # Package exports
├── __main__.py      # Entry point for python -m tuneup_alpha
├── cli.py           # Typer CLI commands
├── config.py        # Configuration loading/saving
├── models.py        # Pydantic data models
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

### cli.py
Typer-based command-line interface with commands:
- `init`: Create initial configuration
- `version`: Display version
- `show`: Display configured zones in a table
- `plan`: Preview nsupdate script for a zone
- `apply`: Execute nsupdate script (with dry-run support)
- `tui`: Launch the interactive dashboard

### tui.py
Textual-based interactive dashboard:
- `ZoneDashboard`: Main application screen
- `ZoneFormScreen`: Modal for adding/editing zones
- `RecordFormScreen`: Modal for adding/editing records
- `ConfirmDeleteScreen`: Confirmation dialogs
- Real-time zone and record management
- Tab navigation between zones and records

## Data Flow

### CLI Commands Flow
```
User Command → CLI Parser → ConfigRepository → Models → Business Logic → Output
```

### TUI Flow
```
User Input → TUI Event Handler → ConfigRepository → Models → Update UI
```

### Apply Flow
```
Configuration → Models → NsupdatePlan → NsupdateClient → nsupdate → DNS Server
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

Coverage focuses on business logic and validation, with TUI testing 
being minimal due to the difficulty of testing interactive applications.
