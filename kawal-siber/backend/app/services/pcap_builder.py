"""
pcap_builder.py — Pure Python Synthetic PCAP File Generator.
Crafts standard libpcap files containing Ethernet/IPv4/TCP/UDP/ICMP/HTTP frames
without requiring external C libraries (like Scapy or Npcap).
"""
from __future__ import annotations

import struct
import time
from pathlib import Path
from typing import List, Tuple


def _ip_checksum(header: bytes) -> int:
    """Compute standard 16-bit one's complement Internet checksum."""
    if len(header) % 2 == 1:
        header += b"\x00"
    checksum = 0
    for i in range(0, len(header), 2):
        word = (header[i] << 8) + header[i + 1]
        checksum += word
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
    return (~checksum) & 0xFFFF


def _ip_to_bytes(ip_str: str) -> bytes:
    parts = [int(p) for p in ip_str.split(".")]
    return bytes(parts)


def build_icmp_echo_packet(src_ip: str, dst_ip: str) -> bytes:
    """Construct an Ethernet + IPv4 + ICMP Echo Request frame."""
    eth_dst = b"\x00\x0c\x29\x6d\x11\x22"
    eth_src = b"\x00\x0c\x29\x6d\x33\x44"
    eth_type = b"\x08\x00"  # IPv4
    eth_header = eth_dst + eth_src + eth_type

    # ICMP Echo Request: type=8, code=0, id=1, seq=1, data
    icmp_data = b"KAWAL-SIBER-TEST-PING-PACKET"
    icmp_header_no_cs = struct.pack("!BBHHH", 8, 0, 0, 1, 1) + icmp_data
    icmp_cs = _ip_checksum(icmp_header_no_cs)
    icmp_packet = struct.pack("!BBHHH", 8, 0, icmp_cs, 1, 1) + icmp_data

    # IPv4 Header
    ip_ver_ihl = (4 << 4) | 5
    ip_tos = 0
    ip_len = 20 + len(icmp_packet)
    ip_id = 54321
    ip_flags_offset = 0
    ip_ttl = 64
    ip_proto = 1  # ICMP
    ip_src_b = _ip_to_bytes(src_ip)
    ip_dst_b = _ip_to_bytes(dst_ip)

    ip_hdr_no_cs = struct.pack(
        "!BBHHHBBH4s4s",
        ip_ver_ihl,
        ip_tos,
        ip_len,
        ip_id,
        ip_flags_offset,
        ip_ttl,
        ip_proto,
        0,
        ip_src_b,
        ip_dst_b,
    )
    ip_cs = _ip_checksum(ip_hdr_no_cs)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        ip_ver_ihl,
        ip_tos,
        ip_len,
        ip_id,
        ip_flags_offset,
        ip_ttl,
        ip_proto,
        ip_cs,
        ip_src_b,
        ip_dst_b,
    )

    return eth_header + ip_header + icmp_packet


def build_http_get_packet(
    src_ip: str, dst_ip: str, src_port: int, dst_port: int, uri: str, user_agent: str
) -> bytes:
    """Construct an Ethernet + IPv4 + TCP + HTTP payload frame."""
    eth_dst = b"\x00\x50\x56\xc0\x00\x08"
    eth_src = b"\x00\x50\x56\xc0\x00\x01"
    eth_type = b"\x08\x00"
    eth_header = eth_dst + eth_src + eth_type

    http_payload = (
        f"GET {uri} HTTP/1.1\r\n"
        f"Host: {dst_ip}\r\n"
        f"User-Agent: {user_agent}\r\n"
        f"Accept: */*\r\n\r\n"
    ).encode("utf-8")

    # TCP Header: 20 bytes (no options)
    tcp_seq = 1000
    tcp_ack = 2000
    tcp_offset_res = (5 << 4)  # 5 32-bit words = 20 bytes
    tcp_flags = 0x18  # PSH, ACK
    tcp_window = 8192
    tcp_urgent = 0

    tcp_hdr_no_cs = struct.pack(
        "!HHIIBBHHH",
        src_port,
        dst_port,
        tcp_seq,
        tcp_ack,
        tcp_offset_res,
        tcp_flags,
        tcp_window,
        0,
        tcp_urgent,
    )

    # TCP checksum with pseudo-header
    src_b = _ip_to_bytes(src_ip)
    dst_b = _ip_to_bytes(dst_ip)
    tcp_len = len(tcp_hdr_no_cs) + len(http_payload)
    pseudo_hdr = struct.pack("!4s4sBBH", src_b, dst_b, 0, 6, tcp_len)
    tcp_cs = _ip_checksum(pseudo_hdr + tcp_hdr_no_cs + http_payload)

    tcp_header = struct.pack(
        "!HHIIBBHHH",
        src_port,
        dst_port,
        tcp_seq,
        tcp_ack,
        tcp_offset_res,
        tcp_flags,
        tcp_window,
        tcp_cs,
        tcp_urgent,
    )

    tcp_packet = tcp_header + http_payload

    # IPv4 Header
    ip_len = 20 + len(tcp_packet)
    ip_hdr_no_cs = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        ip_len,
        12345,
        0x4000,
        64,
        6,  # TCP
        0,
        src_b,
        dst_b,
    )
    ip_cs = _ip_checksum(ip_hdr_no_cs)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        ip_len,
        12345,
        0x4000,
        64,
        6,
        ip_cs,
        src_b,
        dst_b,
    )

    return eth_header + ip_header + tcp_packet


def build_tcp_scan_packet(
    src_ip: str, dst_ip: str, src_port: int, dst_port: int, flags: int
) -> bytes:
    """Construct an Ethernet + IPv4 + TCP probe (e.g. XMAS=0x29, NULL=0x00, SYN=0x02)."""
    eth_dst = b"\x00\x11\x22\x33\x44\x55"
    eth_src = b"\x00\x66\x77\x88\x99\xaa"
    eth_type = b"\x08\x00"
    eth_header = eth_dst + eth_src + eth_type

    tcp_seq = 500
    tcp_ack = 0
    tcp_offset_res = (5 << 4)
    tcp_window = 1024
    tcp_urgent = 0

    tcp_hdr_no_cs = struct.pack(
        "!HHIIBBHHH",
        src_port,
        dst_port,
        tcp_seq,
        tcp_ack,
        tcp_offset_res,
        flags,
        tcp_window,
        0,
        tcp_urgent,
    )

    src_b = _ip_to_bytes(src_ip)
    dst_b = _ip_to_bytes(dst_ip)
    pseudo_hdr = struct.pack("!4s4sBBH", src_b, dst_b, 0, 6, 20)
    tcp_cs = _ip_checksum(pseudo_hdr + tcp_hdr_no_cs)

    tcp_header = struct.pack(
        "!HHIIBBHHH",
        src_port,
        dst_port,
        tcp_seq,
        tcp_ack,
        tcp_offset_res,
        flags,
        tcp_window,
        tcp_cs,
        tcp_urgent,
    )

    ip_len = 40
    ip_hdr_no_cs = struct.pack(
        "!BBHHHBBH4s4s", 0x45, 0, ip_len, 5432, 0, 64, 6, 0, src_b, dst_b
    )
    ip_cs = _ip_checksum(ip_hdr_no_cs)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s", 0x45, 0, ip_len, 5432, 0, 64, 6, ip_cs, src_b, dst_b
    )

    return eth_header + ip_header + tcp_header


def write_pcap(filepath: Path, packets: List[bytes]) -> None:
    """
    Write a list of raw Ethernet frames into standard Libpcap format.
    Global Header (24 bytes) + Per-packet Headers (16 bytes each).
    """
    # Libpcap global header:
    # magic_number (0xa1b2c3d4), version_major (2), version_minor (4),
    # thiszone (0), sigfigs (0), snaplen (65535), network (1 = LINKTYPE_ETHERNET)
    global_hdr = struct.pack("!IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)

    with open(filepath, "wb") as f:
        f.write(global_hdr)
        base_time = int(time.time())
        for idx, pkt in enumerate(packets):
            ts_sec = base_time + idx
            ts_usec = 1000 * idx
            incl_len = len(pkt)
            orig_len = len(pkt)
            pkt_hdr = struct.pack("!IIII", ts_sec, ts_usec, incl_len, orig_len)
            f.write(pkt_hdr)
            f.write(pkt)

