"""
Master License Generator (Admin / Developer Tool).
Use this tool to generate secure activation keys for clients based on their Machine ID.

Usage:
  Interactive Mode:
    python tools/license_generator.py

  CLI Argument Mode:
    python tools/license_generator.py MCH-XXXX-XXXX-XXXX-XXXX
"""

import sys
import os

# Ensure kivy modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kivy"))

from licensing.crypto import generate_activation_key, normalize_code, verify_activation_key


def main():
    print("=" * 65)
    print("       SKETCH ANIMATION STUDIO — MASTER LICENSE GENERATOR")
    print("=" * 65)
    print(" This tool generates hardware-bound activation keys for clients.")
    print(" Keep this tool and its cryptographic keys PRIVATE.")
    print("=" * 65)

    if len(sys.argv) > 1:
        machine_code = sys.argv[1]
    else:
        try:
            machine_code = input("\nEnter Client Machine Code (e.g. MCH-XXXX-XXXX-XXXX-XXXX): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return

    if not machine_code:
        print("[Error]: Machine Code cannot be empty.")
        return

    clean_code = normalize_code(machine_code)
    if clean_code.startswith("MCH"):
        clean_code = clean_code[3:]

    if len(clean_code) < 8:
        print("[Warning]: Machine Code seems unusually short. Please ensure full code was copied.")

    key = generate_activation_key(machine_code)

    # Self-test verification
    is_valid = verify_activation_key(machine_code, key)

    print("\n" + "-" * 65)
    print(f" Client Machine Code : {machine_code.upper()}")
    print(f" Generated Key       : {key}")
    print(f" Verification Status : {'VALID' if is_valid else 'ERROR'}")
    print("-" * 65)
    print(f"\n Send this Key to the client:")
    print(f" >>> {key} <<<\n")


if __name__ == "__main__":
    main()
