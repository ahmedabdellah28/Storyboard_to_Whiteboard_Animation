"""
Background Heartbeat Service for Program B (Sketch Animation Studio).
Periodically checks in with Supabase Edge Functions to ensure license session is active.
"""

import threading
import time
import sys
from typing import Optional, Callable
from licensing.license_client import LicenseClient
from licensing.constants import HEARTBEAT_INTERVAL_SECONDS

_heartbeat_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_current_session_token: Optional[str] = None
_on_revocation_callback: Optional[Callable[[str], None]] = None


def _heartbeat_worker(session_token: str):
    """Background worker loop sending heartbeats."""
    client = LicenseClient(timeout=5.0)
    failed_consecutive_count = 0

    while not _stop_event.is_set():
        # Wait for next heartbeat interval or stop signal
        if _stop_event.wait(timeout=HEARTBEAT_INTERVAL_SECONDS):
            break

        try:
            success, res = client.send_heartbeat(session_token, heartbeat_type="periodic")
            if success:
                failed_consecutive_count = 0
                status = res.get("status")
                if status == "kill":
                    reason = res.get("reason", "License was suspended or revoked by administrator.")
                    print(f"\n[SECURITY ALERT]: Session Terminated: {reason}")
                    if _on_revocation_callback:
                        try:
                            _on_revocation_callback(reason)
                        except Exception:
                            pass
                    sys.exit(1)
            else:
                if res.get("network_error"):
                    failed_consecutive_count += 1
                    if failed_consecutive_count >= 3:
                        print("\n[SECURITY WARNING]: Heartbeat connection lost. Please check internet connection.")
                elif res.get("status") == "kill":
                    print("\n[SECURITY ALERT]: License revoked.")
                    sys.exit(1)
        except Exception:
            pass


def start_heartbeat(session_token: str, on_revocation: Optional[Callable[[str], None]] = None):
    """Start background heartbeat thread."""
    global _heartbeat_thread, _current_session_token, _on_revocation_callback
    stop_heartbeat()

    _current_session_token = session_token
    _on_revocation_callback = on_revocation
    _stop_event.clear()

    _heartbeat_thread = threading.Thread(target=_heartbeat_worker, args=(session_token,), daemon=True)
    _heartbeat_thread.start()


def stop_heartbeat():
    """Stop background heartbeat thread cleanly."""
    global _heartbeat_thread, _current_session_token
    _stop_event.set()
    if _current_session_token:
        try:
            client = LicenseClient(timeout=2.0)
            client.send_heartbeat(_current_session_token, heartbeat_type="shutdown")
        except Exception:
            pass
        _current_session_token = None
