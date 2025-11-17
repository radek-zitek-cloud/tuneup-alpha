# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-11-17

### Added

#### Smart DNS Lookup Features
- Automatic DNS lookup when creating or editing zones
  - Auto-fills nameserver field from NS records
  - Auto-creates apex (@) A record if discovered
  - Shows visual feedback for discovered NS and A records
- Intelligent DNS lookup when creating or editing records
  - Auto-lookup when entering a label (detects existing CNAME or A records)
  - Auto-lookup when entering a value (IP address or hostname)
  - Auto-fills record type and value fields based on lookup results
  - Visual feedback with status indicators (✓ success, ○ no results, ⏳ checking)
- DNS lookup utilities module (`dns_lookup.py`)
  - IPv4 address validation
  - Reverse DNS lookup (IP → hostname)
  - Forward DNS lookup (hostname → IP)
  - Dig-based DNS record lookups (NS, A, CNAME)
  - Label-based DNS lookup within zones

#### Theme Support
- Multiple built-in color themes (textual-dark, textual-light, nord, gruvbox, catppuccin-mocha, dracula, tokyo-night, monokai, flexoki, catppuccin-latte, solarized-light)
- Press `t` to cycle through available themes
- Theme persistence across sessions
- Theme saved automatically on quit

#### TUI Improvements
- Disabled tab and shift+tab navigation in main dashboard (prevents confusion)
- Enabled tab navigation in form dialogs for better usability
- Custom TCSS stylesheet for improved visual design
- Confirmation dialogs for delete operations
- Real-time visual feedback for DNS operations
- Better keyboard navigation and focus management

#### Development & Testing
- Comprehensive test suite (94 tests total)
  - Tests for DNS lookup functionality
  - Tests for theme persistence
  - Tests for TUI form handling
  - Tests for tab navigation
- GitHub Actions CI/CD pipeline
  - Tests on Python 3.11 and 3.12
  - Ruff linting and formatting checks
  - mypy type checking
  - Code coverage reporting
- Dependabot for automated dependency updates
- Makefile for common development tasks
- EditorConfig for consistent code style

#### Documentation
- Comprehensive README with usage examples
- Architecture documentation (ARCHITECTURE.md)
- Contributing guidelines (CONTRIBUTING.md)
- Improvements summary (IMPROVEMENTS.md)
- MIT License

### Changed
- Enhanced README with detailed DNS lookup documentation
- Improved form field validation and error messages
- Updated architecture documentation to reflect DNS lookup integration

### Fixed
- Linting and formatting issues in test files
- Tab navigation conflicts in TUI
- Record preservation when editing zones

## [0.1.0] - 2025-01-01

### Added
- Initial release of TuneUp Alpha
- Dynamic DNS zone management
- Typer-powered CLI
- Textual TUI for live inspection
- YAML-driven configuration system
- Support for A and CNAME DNS record types
- Configuration management via YAML
- nsupdate integration for DNS updates
- Zone and record CRUD operations
- Dry-run mode for safe testing

[Unreleased]: https://github.com/radek-zitek-cloud/tuneup-alpha/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/radek-zitek-cloud/tuneup-alpha/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/radek-zitek-cloud/tuneup-alpha/releases/tag/v0.1.0
