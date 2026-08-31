"""
Local License Key Store for Program B.
Stores the user's license key locally (DPAPI encrypted) for UX convenience only.
NOTE: NEVER used as an authorization grant (Strict Online-Only Policy).
"""

import os
import json
from typing import Optional
from licensing.crypto import protect_data_dpapi, unprotect_data_dpapi


def get_license_file_path() -> str:
    """Get persistent path for license storage in user profile."""
    home_dir = os.path.expanduser("~")
    app_dir = os.path.join(home_dir, ".image_to_animation")
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "license.config")


def save_cached_license_key(license_key: str) -> bool:
    """Save encrypted license key for auto-login on startup."""
    try:
        clean_key = license_key.strip().upper()
        encrypted_blob = protect_data_dpapi(clean_key)
        path = get_license_file_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"protected_key": encrypted_blob}, f, indent=2)
        return True
    except Exception as e:
        print(f"[Licensing Warning]: Could not persist license key: {e}")
        return False


def load_cached_license_key() -> Optional[str]:
    """Load and decrypt stored license key if present."""
    path = get_license_file_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        blob = data.get("protected_key", "")
        if not blob:
            return None
        decrypted = unprotect_data_dpapi(blob)
        return decrypted.strip().upper() if decrypted else None
    except Exception:
        return None


def clear_cached_license_key():
    """Clear cached key on deactivation or logout."""
    path = get_license_file_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
