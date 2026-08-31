"""
Licensing Package for Sketch Animation Studio (Program B).
Zero-Trust, Hardware-locked, Online-Only cryptographic license validation.
"""

from licensing.license_guard import LicenseGuard
from licensing.license_client import LicenseClient
from licensing.fingerprint import get_machine_code, get_machine_fingerprint

__all__ = ["LicenseGuard", "LicenseClient", "get_machine_code", "get_machine_fingerprint"]
