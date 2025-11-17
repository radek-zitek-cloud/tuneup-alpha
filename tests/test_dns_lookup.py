"""Tests for DNS lookup utilities."""

from unittest.mock import patch

from tuneup_alpha.dns_lookup import (
    dns_lookup,
    forward_dns_lookup,
    is_ipv4,
    reverse_dns_lookup,
)


def test_is_ipv4_valid():
    """Test is_ipv4 with valid IPv4 addresses."""
    assert is_ipv4("192.168.1.1") is True
    assert is_ipv4("10.0.0.1") is True
    assert is_ipv4("255.255.255.255") is True
    assert is_ipv4("0.0.0.0") is True


def test_is_ipv4_invalid():
    """Test is_ipv4 with invalid inputs."""
    assert is_ipv4("256.1.1.1") is False  # Octet out of range
    assert is_ipv4("192.168.1") is False  # Missing octet
    assert is_ipv4("192.168.1.1.1") is False  # Too many octets
    assert is_ipv4("example.com") is False  # Hostname
    assert is_ipv4("not-an-ip") is False
    assert is_ipv4("") is False
    assert is_ipv4("abc.def.ghi.jkl") is False


def test_reverse_dns_lookup_success():
    """Test reverse DNS lookup with successful resolution."""
    # Mock the socket.gethostbyaddr function
    with patch("tuneup_alpha.dns_lookup.socket.gethostbyaddr") as mock_lookup:
        mock_lookup.return_value = ("example.com.", [], ["8.8.8.8"])
        result = reverse_dns_lookup("8.8.8.8")
        assert result["hostname"] == "example.com"
        mock_lookup.assert_called_once_with("8.8.8.8")


def test_reverse_dns_lookup_failure():
    """Test reverse DNS lookup with failed resolution."""
    import socket

    with patch("tuneup_alpha.dns_lookup.socket.gethostbyaddr") as mock_lookup:
        mock_lookup.side_effect = socket.herror("Host not found")
        result = reverse_dns_lookup("192.0.2.1")
        assert result["hostname"] is None


def test_forward_dns_lookup_success():
    """Test forward DNS lookup with successful resolution."""
    with patch("tuneup_alpha.dns_lookup.socket.gethostbyname") as mock_lookup:
        mock_lookup.return_value = "93.184.216.34"
        result = forward_dns_lookup("example.com")
        assert result["ip"] == "93.184.216.34"
        mock_lookup.assert_called_once_with("example.com")


def test_forward_dns_lookup_with_trailing_dot():
    """Test forward DNS lookup strips trailing dot."""
    with patch("tuneup_alpha.dns_lookup.socket.gethostbyname") as mock_lookup:
        mock_lookup.return_value = "93.184.216.34"
        result = forward_dns_lookup("example.com.")
        assert result["ip"] == "93.184.216.34"
        # Should strip the trailing dot before lookup
        mock_lookup.assert_called_once_with("example.com")


def test_forward_dns_lookup_failure():
    """Test forward DNS lookup with failed resolution."""
    import socket

    with patch("tuneup_alpha.dns_lookup.socket.gethostbyname") as mock_lookup:
        mock_lookup.side_effect = socket.gaierror("Name or service not known")
        result = forward_dns_lookup("nonexistent.invalid")
        assert result["ip"] is None


def test_dns_lookup_with_ipv4():
    """Test dns_lookup with IPv4 address."""
    with patch("tuneup_alpha.dns_lookup.socket.gethostbyaddr") as mock_lookup:
        mock_lookup.return_value = ("dns.google.", [], ["8.8.8.8"])
        suggested_type, result = dns_lookup("8.8.8.8")
        assert suggested_type == "A"
        assert result["hostname"] == "dns.google"


def test_dns_lookup_with_hostname():
    """Test dns_lookup with hostname."""
    with patch("tuneup_alpha.dns_lookup.socket.gethostbyname") as mock_lookup:
        mock_lookup.return_value = "93.184.216.34"
        suggested_type, result = dns_lookup("example.com")
        assert suggested_type == "CNAME"
        assert result["ip"] == "93.184.216.34"


def test_dns_lookup_with_empty_string():
    """Test dns_lookup with empty string."""
    suggested_type, result = dns_lookup("")
    assert suggested_type is None
    assert result == {}


def test_dns_lookup_with_apex():
    """Test dns_lookup with @ (zone apex)."""
    suggested_type, result = dns_lookup("@")
    assert suggested_type is None
    assert result == {}


def test_dns_lookup_ipv4_no_reverse():
    """Test dns_lookup with IPv4 that has no reverse DNS."""
    import socket

    with patch("tuneup_alpha.dns_lookup.socket.gethostbyaddr") as mock_lookup:
        mock_lookup.side_effect = socket.herror("Host not found")
        suggested_type, result = dns_lookup("192.0.2.1")
        assert suggested_type == "A"
        assert result["hostname"] is None


def test_dns_lookup_hostname_no_forward():
    """Test dns_lookup with hostname that has no forward DNS."""
    import socket

    with patch("tuneup_alpha.dns_lookup.socket.gethostbyname") as mock_lookup:
        mock_lookup.side_effect = socket.gaierror("Name or service not known")
        suggested_type, result = dns_lookup("nonexistent.invalid")
        assert suggested_type == "CNAME"
        assert result["ip"] is None
