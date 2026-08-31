"""
Online Licensing API Client for Program B (Sketch Animation Studio).
Zero-Trust Architecture: Interacts exclusively with Supabase Edge Functions.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple, Optional
from licensing.constants import (
    ENDPOINT_VERIFY,
    ENDPOINT_ACTIVATE,
    ENDPOINT_HEARTBEAT,
    ENDPOINT_CHECK_UPDATE,
    SUPABASE_ANON_KEY,
    APPLICATION_SLUG,
    APP_VERSION,
)
from licensing.crypto import prepare_signed_payload, verify_hmac
from licensing.fingerprint import get_machine_fingerprint


class LicenseClient:
    """Synchronous HTTP Client for Online Licensing Operations."""

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        }

    def _post_signed(self, endpoint: str, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Internal helper to send signed POST request."""
        # Always inject application scope
        data["application_slug"] = APPLICATION_SLUG
        data["app_version"] = APP_VERSION

        payload, signature = prepare_signed_payload(data)
        request_body = {
            "payload": payload,
            "signature": signature,
        }

        json_bytes = json.dumps(request_body).encode('utf-8')
        req = urllib.request.Request(endpoint, data=json_bytes, headers=self.headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status_code = response.status
                res_body = response.read().decode('utf-8')
                res_json = json.loads(res_body)

                res_payload = res_json.get("payload", {})
                res_sig = res_json.get("signature", "")

                # Verify server signature if provided
                if res_sig and not verify_hmac(res_payload, res_sig):
                    return False, {"message": "Server response cryptographic signature verification failed."}

                return True, res_payload

        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode('utf-8')
                err_json = json.loads(err_body)
                return False, {"message": err_json.get("message", f"HTTP Error {e.code}"), "status_code": e.code}
            except Exception:
                return False, {"message": f"Server returned error code {e.code}", "status_code": e.code}
        except urllib.error.URLError as e:
            return False, {"message": f"Network connection failed: {e.reason}", "network_error": True}
        except Exception as e:
            return False, {"message": f"Unexpected error during communication: {e}"}

    def verify_license(self, license_key: str) -> Tuple[bool, Dict[str, Any]]:
        """Verify license key and active machine registration online."""
        fp_info = get_machine_fingerprint()
        data = {
            "license_key": license_key.strip().upper(),
            "fingerprint": fp_info["fingerprint"],
            "components": fp_info.get("components", {}),
        }
        return self._post_signed(ENDPOINT_VERIFY, data)

    def activate_machine(self, license_key: str) -> Tuple[bool, Dict[str, Any]]:
        """Register current machine to license key online."""
        fp_info = get_machine_fingerprint()
        data = {
            "license_key": license_key.strip().upper(),
            "fingerprint": fp_info["fingerprint"],
            "components": fp_info.get("components", {}),
            "machine_name": fp_info.get("machine_name", ""),
            "os_info": fp_info.get("os_info", ""),
        }
        return self._post_signed(ENDPOINT_ACTIVATE, data)

    def send_heartbeat(self, session_token: str, heartbeat_type: str = "periodic") -> Tuple[bool, Dict[str, Any]]:
        """Send periodic heartbeat pulse to server."""
        data = {
            "session_token": session_token,
            "heartbeat_type": heartbeat_type,
        }
        return self._post_signed(ENDPOINT_HEARTBEAT, data)
