# README.md

## Project Goals

- Remote solution for dynamic DNS zone updates. Using nsupdate, create, delete and modify A and CNAME records in a zone file.
- Terminal UI (TUI) displaying overview of managed zones as well as details of individual zones and details of configuration.
- Ability to specify configuration: add, remove zones, specify nsupdate keys, specify name servers.

## Architecture Principles

- Written in Python.
- Able to run by user in terminal, or run in container (not initial priority).
