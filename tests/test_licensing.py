"""
Unit and Integration Tests for Program B Zero-Trust Licensing and Security Module.
"""

import os
import sys
import json
import unittest

# Add kivy to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kivy"))

from licensing.fingerprint import get_machine_code, get_machine_fingerprint
from licensing.crypto import (
    calculate_hmac,
    verify_hmac,
    prepare_signed_payload,
    protect_data_dpapi,
    unprotect_data_dpapi,
)
from licensing.local_cache import (
    get_license_file_path,
    save_cached_license_key,
    load_cached_license_key,
    clear_cached_license_key,
)
from licensing.license_guard import LicenseGuard


class TestLicensing(unittest.TestCase):
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

    def test_machine_code_format(self):
        """Test Machine Code format conforms to MCH-XXXX-XXXX-XXXX-XXXX."""
        code = get_machine_code()
        self.assertTrue(code.startswith("MCH-"))
        parts = code.split("-")
        self.assertEqual(len(parts), 5)
        for part in parts[1:]:
            self.assertEqual(len(part), 4)

    def test_machine_fingerprint_components(self):
        """Test machine fingerprint dictionary contains necessary hardware info."""
        fp = get_machine_fingerprint()
        self.assertIn("fingerprint", fp)
        self.assertIn("machine_code", fp)
        self.assertIn("machine_name", fp)
        self.assertIn("os_info", fp)
        self.assertEqual(len(fp["fingerprint"]), 64)

    def test_dpapi_key_persistence(self):
        """Test local cache DPAPI encryption and loading."""
        test_key = "SKCH-9999-8888-7777-6666"
        self.assertTrue(save_cached_license_key(test_key))
        loaded_key = load_cached_license_key()
        self.assertEqual(test_key, loaded_key)

    def test_clear_cached_key(self):
        """Test clearing cached license key removes file from disk."""
        save_cached_license_key("SKCH-1234-5678-9999-0000")
        self.assertIsNotNone(load_cached_license_key())
        clear_cached_license_key()
        self.assertIsNone(load_cached_license_key())

    def test_payload_signing_integrity(self):
        """Test signed payload generation with HMAC-SHA256."""
        data = {"license_key": "SKCH-TEST-KEY"}
        payload, sig = prepare_signed_payload(data)
        self.assertTrue(verify_hmac(payload, sig))


if __name__ == "__main__":
    unittest.main()
