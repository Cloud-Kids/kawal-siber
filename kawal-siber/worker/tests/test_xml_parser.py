"""
test_xml_parser.py — Unit tests for safe Nmap XML parsing.
"""
from __future__ import annotations

import pytest

from worker.xml_parser import NmapXMLParseError, parse_nmap_xml

SAMPLE_OPEN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sT -sV ..." start="1700000000" version="7.94" xmloutputversion="1.05">
  <host starttime="1700000001" endtime="1700000005">
    <status state="up" reason="syn-ack"/>
    <address addr="192.168.1.100" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open" reason="syn-ack"/>
        <service name="http" product="nginx" version="1.24.0" extrainfo="Ubuntu"/>
      </port>
    </ports>
  </host>
  <runstats>
    <finished time="1700000005" elapsed="2.45" exit="success"/>
    <hosts up="1" down="0" total="1"/>
  </runstats>
</nmaprun>
"""

SAMPLE_CLOSED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" version="7.94">
  <host>
    <status state="up" reason="syn-ack"/>
    <address addr="10.0.0.5" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="443">
        <state state="closed" reason="conn-refused"/>
      </port>
    </ports>
  </host>
  <runstats>
    <finished elapsed="0.05"/>
  </runstats>
</nmaprun>
"""

SAMPLE_HOST_DOWN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun scanner="nmap" version="7.94">
  <host>
    <status state="down" reason="no-response"/>
    <address addr="10.0.0.99" addrtype="ipv4"/>
  </host>
</nmaprun>
"""


def test_parse_open_port_xml():
    findings = parse_nmap_xml(SAMPLE_OPEN_XML)
    assert findings["target_ip"] == "192.168.1.100"
    assert findings["host_status"] == "up"
    assert findings["duration_ms"] == 2450
    assert findings["scanner_version"] == "7.94"
    assert len(findings["ports"]) == 1

    p = findings["ports"][0]
    assert p["protocol"] == "tcp"
    assert p["port"] == 80
    assert p["state"] == "open"
    assert p["reason"] == "syn-ack"
    assert p["service_name"] == "http"
    assert p["product"] == "nginx"
    assert p["version"] == "1.24.0"
    assert p["extra_info"] == "Ubuntu"


def test_parse_closed_port_xml():
    findings = parse_nmap_xml(SAMPLE_CLOSED_XML)
    assert findings["target_ip"] == "10.0.0.5"
    assert findings["host_status"] == "up"
    assert findings["duration_ms"] == 50
    assert len(findings["ports"]) == 1
    p = findings["ports"][0]
    assert p["port"] == 443
    assert p["state"] == "closed"
    assert p["reason"] == "conn-refused"


def test_parse_host_down_xml():
    findings = parse_nmap_xml(SAMPLE_HOST_DOWN_XML)
    assert findings["target_ip"] == "10.0.0.99"
    assert findings["host_status"] == "down"
    assert len(findings["ports"]) == 0


def test_parse_empty_and_malformed_xml():
    with pytest.raises(NmapXMLParseError):
        parse_nmap_xml("")

    with pytest.raises(NmapXMLParseError):
        parse_nmap_xml("<nmaprun>unclosed tag")

    with pytest.raises(NmapXMLParseError):
        parse_nmap_xml("<wrongroot></wrongroot>")


def test_parse_oversized_xml_rejected():
    small_limit = 50
    with pytest.raises(NmapXMLParseError) as exc_info:
        parse_nmap_xml(SAMPLE_OPEN_XML, max_bytes=small_limit)
    assert "exceeds maximum limit" in str(exc_info.value)

