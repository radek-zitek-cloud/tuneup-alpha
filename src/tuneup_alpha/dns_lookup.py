"""DNS lookup utilities for auto-filling form fields."""

from __future__ import annotations

import re
import socket
from typing import Literal

LookupResult = dict[str, str | None]


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
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        # Remove trailing dot if present
        hostname = hostname.rstrip(".")
        return {"hostname": hostname}
    except (socket.herror, socket.gaierror, OSError):
        return {"hostname": None}


def forward_dns_lookup(hostname: str) -> LookupResult:
    """Perform forward DNS lookup to find IP from hostname.

    Args:
        hostname: Hostname to lookup

    Returns:
        Dictionary with 'ip' key if successful, None if lookup fails
    """
    try:
        # Remove trailing dot if present for lookup
        lookup_hostname = hostname.rstrip(".")
        ip_address = socket.gethostbyname(lookup_hostname)
        return {"ip": ip_address}
    except (socket.herror, socket.gaierror, OSError):
        return {"ip": None}


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
