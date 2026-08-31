"""
Cryptographic Utilities and Integrity Module for Program B.
Provides HMAC-SHA256 request signing, Nonce generation, and Windows DPAPI local protection.
"""

import hmac
import hashlib
import json
import time
import uuid
import sys
from typing import Dict, Any, Tuple
from licensing.constants import CLIENT_SECRET_SALT


def calculate_hmac(payload: Dict[str, Any], secret_salt: str = CLIENT_SECRET_SALT) -> str:
    """Calculate HMAC-SHA256 signature for canonical JSON payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hmac.new(secret_salt.encode('utf-8'), canonical, hashlib.sha256).hexdigest()


def verify_hmac(payload: Dict[str, Any], signature: str, secret_salt: str = CLIENT_SECRET_SALT) -> bool:
    """Verify HMAC signature with constant-time comparison."""
    if not signature:
        return False
    expected = calculate_hmac(payload, secret_salt)
    return hmac.compare_digest(expected, signature)


def prepare_signed_payload(data: Dict[str, Any], secret_salt: str = CLIENT_SECRET_SALT) -> Tuple[Dict[str, Any], str]:
    """
    Prepare payload with anti-replay protection (fresh timestamp + UUIDv4 nonce) and compute signature.
    """
    payload = dict(data)
    payload["timestamp"] = int(time.time())
    payload["nonce"] = str(uuid.uuid4())
    signature = calculate_hmac(payload, secret_salt)
    return payload, signature


# --- Windows DPAPI Protection Layer ---

def protect_data_dpapi(data_str: str) -> str:
    """
    Encrypt string using Windows Data Protection API (DPAPI CryptProtectData).
    Returns hex-encoded ciphertext. Falls back to base64 if DPAPI unavailable.
    """
    if not data_str:
        return ""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

            pDataIn = (ctypes.c_byte * len(data_str))(*[ctypes.c_byte(b) for b in data_str.encode('utf-8')])
            blobIn = DATA_BLOB(len(data_str), ctypes.cast(pDataIn, ctypes.POINTER(ctypes.c_byte)))
            blobOut = DATA_BLOB()

            if ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(blobIn), None, None, None, None, 0, ctypes.byref(blobOut)
            ):
                out_bytes = ctypes.string_at(blobOut.pbData, blobOut.cbData)
                ctypes.windll.kernel32.LocalFree(blobOut.pbData)
                return out_bytes.hex()
    except Exception:
        pass
    import base64
    return "B64:" + base64.b64encode(data_str.encode('utf-8')).decode('utf-8')


def unprotect_data_dpapi(hex_str: str) -> str:
    """
    Decrypt string using Windows DPAPI (CryptUnprotectData).
    """
    if not hex_str:
        return ""
    if hex_str.startswith("B64:"):
        import base64
        try:
            return base64.b64decode(hex_str[4:]).decode('utf-8')
        except Exception:
            return ""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

            raw_bytes = bytes.fromhex(hex_str)
            pDataIn = (ctypes.c_byte * len(raw_bytes))(*[ctypes.c_byte(b) for b in raw_bytes])
            blobIn = DATA_BLOB(len(raw_bytes), ctypes.cast(pDataIn, ctypes.POINTER(ctypes.c_byte)))
            blobOut = DATA_BLOB()

            if ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(blobIn), None, None, None, None, 0, ctypes.byref(blobOut)
            ):
                out_bytes = ctypes.string_at(blobOut.pbData, blobOut.cbData)
                ctypes.windll.kernel32.LocalFree(blobOut.pbData)
                return out_bytes.decode('utf-8')
    except Exception:
        pass
    return ""
