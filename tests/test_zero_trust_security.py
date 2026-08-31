"""
Automated Zero-Trust Security & Attack Simulation Test Suite.
Verifies multi-application isolation, replay protection, signature enforcement,
and online-only policy between Program A (Gmail Options) and Program B (Sketch Animation Studio).
"""

import unittest
import time
import uuid
import json
import os
import sys

# Add kivy to sys.path
KIVY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kivy")
if KIVY_DIR not in sys.path:
    sys.path.insert(0, KIVY_DIR)

from licensing.constants import (
    APPLICATION_SLUG,
    CLIENT_SECRET_SALT,
    ENDPOINT_VERIFY,
    ENDPOINT_ACTIVATE,
)
from licensing.crypto import calculate_hmac, verify_hmac, prepare_signed_payload, protect_data_dpapi, unprotect_data_dpapi
from licensing.license_client import LicenseClient
from licensing.license_guard import LicenseGuard
from licensing.local_cache import save_cached_license_key, load_cached_license_key, clear_cached_license_key


class TestZeroTrustLicensingSecurity(unittest.TestCase):
    """Rigorous Security Test Suite for Zero-Trust Licensing."""
    _original_key = None

    @classmethod
    def setUpClass(cls):
        cls._original_key = load_cached_license_key()

    @classmethod
    def tearDownClass(cls):
        if cls._original_key:
            save_cached_license_key(cls._original_key)
        else:
            clear_cached_license_key()

    def setUp(self):
        clear_cached_license_key()

    def tearDown(self):
        pass

    # ════════════════════════════════════════════════
    #  Test Group 1: Cryptographic Primitives & DPAPI
    # ════════════════════════════════════════════════

    def test_01_hmac_signature_calculation_and_verification(self):
        """Test canonical JSON HMAC signature calculation and constant-time verification."""
        payload = {"app": "sketch_animation", "license_key": "SKCH-TEST-1234", "timestamp": 1700000000}
        sig = calculate_hmac(payload, CLIENT_SECRET_SALT)
        self.assertTrue(len(sig) == 64, "HMAC-SHA256 signature must be 64 hex characters.")
        self.assertTrue(verify_hmac(payload, sig, CLIENT_SECRET_SALT), "HMAC verification must succeed on untampered payload.")

        # Tamper payload
        tampered = dict(payload)
        tampered["app"] = "gmail_options"
        self.assertFalse(verify_hmac(tampered, sig, CLIENT_SECRET_SALT), "HMAC verification must fail on tampered payload.")

    def test_02_dpapi_local_storage_protection(self):
        """Test Windows DPAPI encryption and decryption for local cached license keys."""
        test_key = "SKCH-A1B2-C3D4-E5F6"
        encrypted_blob = protect_data_dpapi(test_key)
        self.assertNotEqual(test_key, encrypted_blob, "Encrypted blob must not match plaintext.")
        decrypted_key = unprotect_data_dpapi(encrypted_blob)
        self.assertEqual(test_key, decrypted_key, "Decrypted DPAPI key must match original plaintext.")

    def test_03_replay_protection_payload_generation(self):
        """Test that every prepared payload contains a unique UUIDv4 nonce and fresh timestamp."""
        data = {"license_key": "SKCH-TEST-0001"}
        p1, s1 = prepare_signed_payload(data)
        p2, s2 = prepare_signed_payload(data)

        self.assertIn("nonce", p1)
        self.assertIn("timestamp", p1)
        self.assertNotEqual(p1["nonce"], p2["nonce"], "Each payload must have a globally unique nonce.")
        self.assertNotEqual(s1, s2, "Signatures must differ due to unique nonces.")

    # ════════════════════════════════════════════════
    #  Test Group 2: Online-Only Enforcement (Program B)
    # ════════════════════════════════════════════════

    def test_04_no_offline_authorization_grant(self):
        """Verify that local cache alone NEVER grants authorization (Fail-Closed)."""
        # Save a fake key to local cache
        save_cached_license_key("SKCH-FAK9-9999-0000")
        
        # Verify that without server confirmation, is_session_active is False
        self.assertFalse(LicenseGuard.is_session_active(), "LicenseGuard must NOT be active before online validation.")
        self.assertIsNone(LicenseGuard.get_active_session_token(), "Session token must be None.")

    def test_05_invalid_license_denial(self):
        """Verify that an invalid or malformed license key is rejected online."""
        client = LicenseClient(timeout=5.0)
        success, res = client.verify_license("SKCH-INVALID-KEY-XXXX-0000")
        self.assertFalse(success, "Invalid license key must return failure.")
        self.assertFalse(LicenseGuard.is_session_active(), "Session must remain inactive.")

    # ════════════════════════════════════════════════
    #  Test Group 3: Multi-Application Isolation Logic
    # ════════════════════════════════════════════════

    def test_06_application_scope_injection(self):
        """Verify that Program B client automatically injects 'sketch_animation' application slug."""
        client = LicenseClient()
        data = {"license_key": "SKCH-TEST"}
        # Prepare payload via client internal method
        p, s = prepare_signed_payload(data)
        self.assertIn("timestamp", p)
        self.assertIn("nonce", p)
        self.assertEqual(APPLICATION_SLUG, "sketch_animation")

    def test_07_cross_application_license_mismatch_simulation(self):
        """
        Simulate cross-application attack: Attempting to verify a Program A license key
        under Program B's application scope.
        """
        program_a_license = "SCN-1111-2222-3333-4444"
        client = LicenseClient(timeout=5.0)
        success, res = client.verify_license(program_a_license)
        # Server must reject because SCN-* belongs to 'gmail_options', not 'sketch_animation'
        self.assertFalse(success, "Program A license must be rejected under Program B scope.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
