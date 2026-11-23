"""DNS fallback patch to ensure Google API lookups always succeed
even if the local router DNS is degraded or dropping packets.
"""

import socket
import struct
import logging

logger = logging.getLogger("DNSFallback")

_orig_getaddrinfo = socket.getaddrinfo
DNS_SERVERS = ['8.8.8.8', '1.1.1.1', '8.8.4.4']

def _raw_dns_resolve(domain: str, dns_ip: str = '8.8.8.8'):
    ID = 0x5a5a
    flags = 0x0100
    header = struct.pack('!HHHHHH', ID, flags, 1, 0, 0, 0)
    qname = b''.join(bytes([len(p)]) + p.encode('ascii') for p in domain.split('.')) + b'\x00'
    packet = header + qname + struct.pack('!HH', 1, 1) # A record
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2.5)
    try:
        s.sendto(packet, (dns_ip, 53))
        data, _ = s.recvfrom(1024)
    finally:
        s.close()
    
    ans_offset = len(header) + len(qname) + 4
    ips = []
    for i in range(ans_offset, len(data) - 14):
        if data[i:i+2] == b'\x00\x01' and data[i+2:i+4] == b'\x00\x01':
            rdlength = struct.unpack('!H', data[i+8:i+10])[0]
            if rdlength == 4:
                ip = socket.inet_ntoa(data[i+10:i+14])
                ips.append(ip)
    return ips

def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return _orig_getaddrinfo(host, port, family, type, proto, flags)
    except socket.gaierror:
        # Fallback to direct DNS resolution
        for dns in DNS_SERVERS:
            try:
                ips = _raw_dns_resolve(host, dns)
                if ips:
                    results = []
                    for ip in ips:
                        results.append((socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port)))
                    return results
            except Exception:
                continue
        raise

def apply_dns_patch():
    socket.getaddrinfo = _patched_getaddrinfo

apply_dns_patch()
