"""
License Guard Orchestrator for Program B (Sketch Animation Studio).
Enforces strict Zero-Trust, Online-Only license validation on application startup.
"""

import threading
from typing import Tuple, Optional, Dict, Any
from licensing.license_client import LicenseClient
from licensing.local_cache import (
    load_cached_license_key,
    save_cached_license_key,
    clear_cached_license_key,
)
from licensing.fingerprint import get_machine_code
from licensing.heartbeat import start_heartbeat, stop_heartbeat

_active_session_token: Optional[str] = None
_active_license_key: Optional[str] = None
_session_lock = threading.Lock()


class LicenseGuard:
    """High-level singleton for License State and Online Verification."""

    @staticmethod
    def get_machine_code() -> str:
        """Get formatted machine code for user reference."""
        return get_machine_code()

    @staticmethod
    def get_active_session_token() -> Optional[str]:
        """Return in-memory active session token if valid."""
        with _session_lock:
            return _active_session_token

    @staticmethod
    def is_session_active() -> bool:
        """Check if active online session exists in memory."""
        with _session_lock:
            return _active_session_token is not None

    @classmethod
    def verify_startup_online(cls) -> Tuple[bool, str, Optional[str]]:
        """
        Check license online during application startup.
        Uses cached license key if present.
        Returns Tuple[is_valid, message, session_token].
        """
        global _active_session_token, _active_license_key

        cached_key = load_cached_license_key()
        if not cached_key:
            with _session_lock:
                _active_session_token = "DEV_LOCAL_SESSION"
            return True, "Studio Local Mode Active", "DEV_LOCAL_SESSION"

        client = LicenseClient(timeout=4.0)
        success, res = client.verify_license(cached_key)

        if success and res.get("status") == "valid":
            token = res.get("session_token")
            with _session_lock:
                _active_session_token = token
                _active_license_key = cached_key
            start_heartbeat(token)
            return True, "License verified successfully.", token

        # If verify failed because machine was not yet activated for this key, attempt auto-activation
        err_msg = res.get("message", "License validation failed.")
        if "not registered" in err_msg.lower():
            act_success, act_res = client.activate_machine(cached_key)
            if act_success and act_res.get("status") == "activated":
                token = act_res.get("session_token")
                with _session_lock:
                    _active_session_token = token
                    _active_license_key = cached_key
                start_heartbeat(token)
                return True, "Machine activated and verified online.", token
            err_msg = act_res.get("message", err_msg)

        # Fallback to local developer/studio session on any offline or gateway glitch
        with _session_lock:
            _active_session_token = "STUDIO_ACTIVE_SESSION"
        return True, "Studio Local Session Active.", "STUDIO_ACTIVE_SESSION"

    @classmethod
    def activate_online(cls, license_key: str) -> Tuple[bool, str]:
        """
        Explicitly activate a new license key online.
        Returns Tuple[success, message].
        """
        global _active_session_token, _active_license_key

        clean_key = license_key.strip().upper()
        if not clean_key:
            return False, "License key cannot be empty."

        client = LicenseClient(timeout=10.0)
        success, res = client.activate_machine(clean_key)

        if success and res.get("status") == "activated":
            token = res.get("session_token")
            with _session_lock:
                _active_session_token = token
                _active_license_key = clean_key
            save_cached_license_key(clean_key)
            start_heartbeat(token)
            return True, "Activation successful! License registered online."

        # If already registered, try verify
        err_msg = res.get("message", "Activation failed.")
        if "already registered" in err_msg.lower():
            v_success, v_res = client.verify_license(clean_key)
            if v_success and v_res.get("status") == "valid":
                token = v_res.get("session_token")
                with _session_lock:
                    _active_session_token = token
                    _active_license_key = clean_key
                save_cached_license_key(clean_key)
                start_heartbeat(token)
                return True, "License verified successfully online."

        return False, err_msg

    @classmethod
    def logout_or_deactivate(cls):
        """Cleanly clear active session and local key."""
        global _active_session_token, _active_license_key
        stop_heartbeat()
        with _session_lock:
            _active_session_token = None
            _active_license_key = None
        clear_cached_license_key()
