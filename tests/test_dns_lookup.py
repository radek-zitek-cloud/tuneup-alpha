"""Tests for DNS lookup utilities."""

from unittest.mock import MagicMock, patch

from tuneup_alpha.dns_lookup import (
    dig_lookup,
    dns_lookup,
    dns_lookup_label,
    forward_dns_lookup,
    is_ipv4,
    lookup_a_records,
    lookup_aaaa_records,
    lookup_caa_records,
    lookup_cname_records,
    lookup_mx_records,
    lookup_nameservers,
    lookup_srv_records,
    lookup_txt_records,
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


def test_dig_lookup_success():
    """Test dig_lookup with successful response."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "ns1.example.com.\nns2.example.com.\n"

    with patch("tuneup_alpha.dns_lookup.subprocess.run", return_value=mock_result):
        result = dig_lookup("example.com", "NS")
        assert result == ["ns1.example.com", "ns2.example.com"]


def test_dig_lookup_empty_result():
    """Test dig_lookup with no results."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""

    with patch("tuneup_alpha.dns_lookup.subprocess.run", return_value=mock_result):
        result = dig_lookup("example.com", "NS")
        assert result == []


def test_dig_lookup_failure():
    """Test dig_lookup with failed command."""
    mock_result = MagicMock()
    mock_result.returncode = 1

    with patch("tuneup_alpha.dns_lookup.subprocess.run", return_value=mock_result):
        result = dig_lookup("example.com", "NS")
        assert result == []


def test_dig_lookup_timeout():
    """Test dig_lookup with timeout."""
    import subprocess

    with patch(
        "tuneup_alpha.dns_lookup.subprocess.run",
        side_effect=subprocess.TimeoutExpired("dig", 5),
    ):
        result = dig_lookup("example.com", "NS")
        assert result == []


def test_lookup_nameservers():
    """Test lookup_nameservers function."""
    with patch("tuneup_alpha.dns_lookup.dig_lookup") as mock_dig:
        mock_dig.return_value = ["ns1.example.com", "ns2.example.com"]
        result = lookup_nameservers("example.com")
        assert result == ["ns1.example.com", "ns2.example.com"]
        mock_dig.assert_called_once_with("example.com", "NS")


def test_lookup_a_records():
    """Test lookup_a_records function."""
    with patch("tuneup_alpha.dns_lookup.dig_lookup") as mock_dig:
        mock_dig.return_value = ["192.0.2.1", "192.0.2.2"]
        result = lookup_a_records("example.com")
        assert result == ["192.0.2.1", "192.0.2.2"]
        mock_dig.assert_called_once_with("example.com", "A")


def test_lookup_cname_records():
    """Test lookup_cname_records function."""
    with patch("tuneup_alpha.dns_lookup.dig_lookup") as mock_dig:
        mock_dig.return_value = ["target.example.com"]
        result = lookup_cname_records("www.example.com")
        assert result == ["target.example.com"]
        mock_dig.assert_called_once_with("www.example.com", "CNAME")


def test_dns_lookup_label_with_cname():
    """Test dns_lookup_label finding a CNAME record."""
    with patch("tuneup_alpha.dns_lookup.lookup_cname_records") as mock_cname:
        mock_cname.return_value = ["target.example.com"]
        record_type, value = dns_lookup_label("www", "example.com")
        assert record_type == "CNAME"
        assert value == "target.example.com"
        mock_cname.assert_called_once_with("www.example.com")


def test_dns_lookup_label_with_a_record():
    """Test dns_lookup_label finding an A record."""
    with (
        patch("tuneup_alpha.dns_lookup.lookup_cname_records") as mock_cname,
        patch("tuneup_alpha.dns_lookup.lookup_a_records") as mock_a,
    ):
        mock_cname.return_value = []
        mock_a.return_value = ["192.0.2.1"]
        record_type, value = dns_lookup_label("www", "example.com")
        assert record_type == "A"
        assert value == "192.0.2.1"


def test_dns_lookup_label_apex():
    """Test dns_lookup_label with apex (@) label."""
    with (
        patch("tuneup_alpha.dns_lookup.lookup_cname_records") as mock_cname,
        patch("tuneup_alpha.dns_lookup.lookup_a_records") as mock_a,
    ):
        mock_cname.return_value = []
        mock_a.return_value = ["192.0.2.1"]
        record_type, value = dns_lookup_label("@", "example.com")
        assert record_type == "A"
        assert value == "192.0.2.1"
        # Should lookup the zone apex directly
        mock_a.assert_called_once_with("example.com")


def test_dns_lookup_label_not_found():
    """Test dns_lookup_label when no records are found."""
    with (
        patch("tuneup_alpha.dns_lookup.lookup_cname_records") as mock_cname,
        patch("tuneup_alpha.dns_lookup.lookup_a_records") as mock_a,
    ):
        mock_cname.return_value = []
        mock_a.return_value = []
        record_type, value = dns_lookup_label("www", "example.com")
        assert record_type is None
        assert value is None


def test_dns_lookup_label_empty_inputs():
    """Test dns_lookup_label with empty inputs."""
    record_type, value = dns_lookup_label("", "example.com")
    assert record_type is None
    assert value is None

    record_type, value = dns_lookup_label("www", "")
    assert record_type is None
    assert value is None


def test_is_ipv6_valid():
    """Test is_ipv6 with valid IPv6 addresses."""
    from tuneup_alpha.dns_lookup import is_ipv6

    assert is_ipv6("2001:0db8:85a3:0000:0000:8a2e:0370:7334") is True
    assert is_ipv6("2001:db8:85a3::8a2e:370:7334") is True
    assert is_ipv6("::1") is True
    assert is_ipv6("fe80::1") is True
    assert is_ipv6("::ffff:192.0.2.1") is True


def test_is_ipv6_invalid():
    """Test is_ipv6 with invalid inputs."""
    from tuneup_alpha.dns_lookup import is_ipv6

    assert is_ipv6("192.168.1.1") is False
    assert is_ipv6("example.com") is False
    assert is_ipv6("not-an-ipv6") is False
    assert is_ipv6("") is False


def test_dns_lookup_with_ipv6():
    """Test dns_lookup with IPv6 address."""
    suggested_type, result = dns_lookup("2001:db8::1")
    assert suggested_type == "AAAA"
    assert result == {}


def test_lookup_aaaa_records():
    """Test lookup_aaaa_records function."""
    with patch("tuneup_alpha.dns_lookup.dig_lookup") as mock_dig:
        mock_dig.return_value = ["2001:db8::1", "2001:db8::2"]
        result = lookup_aaaa_records("example.com")
        assert result == ["2001:db8::1", "2001:db8::2"]
        mock_dig.assert_called_once_with("example.com", "AAAA")


def test_lookup_mx_records():
    """Test lookup_mx_records function."""
    with patch("tuneup_alpha.dns_lookup.dig_lookup") as mock_dig:
        mock_dig.return_value = ["10 mail.example.com", "20 mail2.example.com"]
        result = lookup_mx_records("example.com")
        assert result == ["10 mail.example.com", "20 mail2.example.com"]
        mock_dig.assert_called_once_with("example.com", "MX")


def test_lookup_txt_records():
    """Test lookup_txt_records function."""
    with patch("tuneup_alpha.dns_lookup.dig_lookup") as mock_dig:
        mock_dig.return_value = ["v=spf1 include:_spf.example.com ~all"]
        result = lookup_txt_records("example.com")
        assert result == ["v=spf1 include:_spf.example.com ~all"]
        mock_dig.assert_called_once_with("example.com", "TXT")


def test_lookup_srv_records():
    """Test lookup_srv_records function."""
    with patch("tuneup_alpha.dns_lookup.dig_lookup") as mock_dig:
        mock_dig.return_value = ["10 60 80 server.example.com"]
        result = lookup_srv_records("_http._tcp.example.com")
        assert result == ["10 60 80 server.example.com"]
        mock_dig.assert_called_once_with("_http._tcp.example.com", "SRV")


def test_lookup_caa_records():
    """Test lookup_caa_records function."""
    with patch("tuneup_alpha.dns_lookup.dig_lookup") as mock_dig:
        mock_dig.return_value = ["0 issue letsencrypt.org"]
        result = lookup_caa_records("example.com")
        assert result == ["0 issue letsencrypt.org"]
        mock_dig.assert_called_once_with("example.com", "CAA")


def test_dns_lookup_label_with_aaaa_record():
    """Test dns_lookup_label finding an AAAA record."""
    with (
        patch("tuneup_alpha.dns_lookup.lookup_cname_records") as mock_cname,
        patch("tuneup_alpha.dns_lookup.lookup_a_records") as mock_a,
        patch("tuneup_alpha.dns_lookup.lookup_aaaa_records") as mock_aaaa,
    ):
        mock_cname.return_value = []
        mock_a.return_value = []
        mock_aaaa.return_value = ["2001:db8::1"]
        record_type, value = dns_lookup_label("www", "example.com")
        assert record_type == "AAAA"
        assert value == "2001:db8::1"
