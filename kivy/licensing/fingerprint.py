"""
Hardware Fingerprint Module.
Extracts unique system identifiers (Registry MachineGuid, CPU, MAC, Username)
to bind the software to a specific machine.
"""

import sys
import os
import platform
import socket
import uuid
import hashlib
from typing import Dict, Any


def _get_windows_machine_guid() -> str:
    """Retrieve Windows MachineGuid from Registry."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        )
        val, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return str(val).strip()
    except Exception:
        pass
    return ""


def _get_linux_machine_id() -> str:
    """Retrieve Linux machine-id from standard sysfs locations."""
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception:
                pass
    return ""


def get_raw_machine_id() -> str:
    """Get unique OS machine ID."""
    if sys.platform.startswith("win"):
        mid = _get_windows_machine_guid()
        if mid:
            return mid
    elif sys.platform.startswith("linux"):
        mid = _get_linux_machine_id()
        if mid:
            return mid
    
    # Fallback to node uuid
    return f"fallback-{uuid.getnode()}"


def get_cpu_info() -> str:
    """Get CPU model / processor identifier."""
    try:
        if sys.platform.startswith("win"):
            return os.environ.get("PROCESSOR_IDENTIFIER", "") or platform.processor() or ""
        elif sys.platform.startswith("linux"):
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if "model name" in line or "Hardware" in line:
                        return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.machine() or "Generic_CPU"


def get_mac_address() -> str:
    """Get primary MAC address string."""
    try:
        mac_num = uuid.getnode()
        mac_hex = f"{mac_num:012x}"
        return ":".join(mac_hex[i:i+2] for i in range(0, 12, 2))
    except Exception:
        return "00:00:00:00:00:00"


_cached_fingerprint = None


def get_machine_fingerprint() -> Dict[str, Any]:
    """
    Generate Machine Fingerprint payload with deterministic hash.
    Cached in memory to avoid repetitive registry reads.
    """
    global _cached_fingerprint
    if _cached_fingerprint is not None:
        return _cached_fingerprint

    mid = get_raw_machine_id()
    cpu = get_cpu_info()
    mac = get_mac_address()

    # Create individual component hashes
    raw_combined = f"{mid}|{cpu}|{mac}".lower()
    fp_hash = hashlib.sha256(raw_combined.encode('utf-8')).hexdigest()

    # Form user-friendly Machine Code (e.g. MCH-A1B2-C3D4-E5F6)
    short_hash = fp_hash[:16].upper()
    machine_code = f"MCH-{short_hash[0:4]}-{short_hash[4:8]}-{short_hash[8:12]}-{short_hash[12:16]}"

    _cached_fingerprint = {
        "machine_code": machine_code,
        "fingerprint": fp_hash,
        "raw_id": mid,
        "cpu": cpu,
        "mac": mac,
        "hostname": socket.gethostname(),
        "machine_name": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "os_info": f"{platform.system()} {platform.release()}"
    }
    return _cached_fingerprint


def get_machine_code() -> str:
    """Return user-facing formatted Machine Code (e.g., MCH-XXXX-XXXX-XXXX-XXXX)."""
    return get_machine_fingerprint()["machine_code"]
