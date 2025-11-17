"""DNS lookup utilities for auto-filling form fields."""

from __future__ import annotations

import re
import socket
import subprocess
from typing import Literal

from .logging_config import get_logger

logger = get_logger(__name__)

LookupResult = dict[str, str | None]
DigResult = dict[str, list[str]]


def is_ipv4(value: str) -> bool:
    """Check if a string is a valid IPv4 address.

    Args:
        value: String to check

    Returns:
        True if the string is a valid IPv4 address
    """
    ipv4_pattern = r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$"
    match = re.match(ipv4_pattern, value)
    if not match:
        return False
    # Check each octet is 0-255
    return all(int(octet) <= 255 for octet in match.groups())


def reverse_dns_lookup(ip_address: str) -> LookupResult:
    """Perform reverse DNS lookup to find hostname from IP.

    Args:
        ip_address: IPv4 address to lookup

    Returns:
        Dictionary with 'hostname' key if successful, None if lookup fails
    """
    logger.debug(f"Performing reverse DNS lookup for IP: {ip_address}")
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        # Remove trailing dot if present
        hostname = hostname.rstrip(".")
        logger.debug(f"Reverse DNS lookup successful: {ip_address} -> {hostname}")
        return {"hostname": hostname}
    except (socket.herror, socket.gaierror, OSError) as exc:
        logger.debug(f"Reverse DNS lookup failed for {ip_address}: {exc}")
        return {"hostname": None}


def forward_dns_lookup(hostname: str) -> LookupResult:
    """Perform forward DNS lookup to find IP from hostname.

    Args:
        hostname: Hostname to lookup

    Returns:
        Dictionary with 'ip' key if successful, None if lookup fails
    """
    logger.debug(f"Performing forward DNS lookup for hostname: {hostname}")
    try:
        # Remove trailing dot if present for lookup
        lookup_hostname = hostname.rstrip(".")
        ip_address = socket.gethostbyname(lookup_hostname)
        logger.debug(f"Forward DNS lookup successful: {hostname} -> {ip_address}")
        return {"ip": ip_address}
    except (socket.herror, socket.gaierror, OSError) as exc:
        logger.debug(f"Forward DNS lookup failed for {hostname}: {exc}")
        return {"ip": None}


def dig_lookup(domain: str, record_type: str) -> list[str]:
    """Perform DNS lookup using dig command.

    Args:
        domain: Domain name to lookup
        record_type: DNS record type (A, CNAME, NS, etc.)

    Returns:
        List of values found for the record type
    """
    logger.debug(f"Performing dig lookup for {domain} {record_type}")
    try:
        # Run dig command with short output
        result = subprocess.run(
            ["dig", "+short", domain, record_type],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            logger.debug(f"dig command failed for {domain} {record_type}")
            return []

        # Parse output - each line is a result
        values = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                # Remove trailing dot from hostnames
                values.append(line.rstrip("."))

        logger.debug(f"dig lookup found {len(values)} record(s) for {domain} {record_type}")
        return values
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.debug(f"dig lookup failed for {domain} {record_type}: {exc}")
        return []


def lookup_nameservers(domain: str) -> list[str]:
    """Lookup NS records for a domain using dig.

    Args:
        domain: Domain name to lookup

    Returns:
        List of nameserver hostnames
    """
    return dig_lookup(domain, "NS")


def lookup_a_records(domain: str) -> list[str]:
    """Lookup A records for a domain using dig.

    Args:
        domain: Domain name to lookup

    Returns:
        List of IPv4 addresses
    """
    return dig_lookup(domain, "A")


def lookup_cname_records(domain: str) -> list[str]:
    """Lookup CNAME records for a domain using dig.

    Args:
        domain: Domain name to lookup

    Returns:
        List of CNAME targets
    """
    return dig_lookup(domain, "CNAME")


def dns_lookup_label(label: str, zone_name: str) -> tuple[Literal["A", "CNAME"] | None, str | None]:
    """Lookup DNS information for a label within a zone.

    Args:
        label: Record label (e.g., "www", "@")
        zone_name: Zone name (e.g., "example.com")

    Returns:
        Tuple of (record_type, value) if found, (None, None) otherwise
    """
    if not label or not zone_name:
        return None, None

    # Construct FQDN from label and zone
    fqdn = zone_name if label == "@" else f"{label}.{zone_name}"

    # First try CNAME lookup
    cnames = lookup_cname_records(fqdn)
    if cnames:
        return "CNAME", cnames[0]

    # Then try A record lookup
    a_records = lookup_a_records(fqdn)
    if a_records:
        return "A", a_records[0]

    return None, None


def dns_lookup(value: str) -> tuple[Literal["A", "CNAME"] | None, LookupResult]:
    """Perform DNS lookup and suggest record type and related information.

    Args:
        value: DNS value to lookup (IP address or hostname)

    Returns:
        Tuple of (suggested_record_type, lookup_results)
        - suggested_record_type: "A" if IP address, "CNAME" if hostname, None if unclear
        - lookup_results: Dictionary with lookup information
    """
    if not value or value == "@":
        return None, {}

    # Check if it's an IP address
    if is_ipv4(value):
        # For IP addresses, suggest A record and try reverse DNS
        result = reverse_dns_lookup(value)
        return "A", result
    else:
        # For hostnames, suggest CNAME and try forward DNS
        result = forward_dns_lookup(value)
        # If we got an IP, it's likely meant to be used as CNAME target
        # but the user might want to use the IP for an A record
        return "CNAME", result
