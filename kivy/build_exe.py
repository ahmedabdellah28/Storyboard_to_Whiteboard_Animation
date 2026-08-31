"""
Automated Build Script for Sketch Animation Studio (Windows EXE).
Cleans previous builds, executes PyInstaller with optimizations, and prepares distribution package.
"""

import sys
import os
import shutil
import subprocess
import time
from pathlib import Path

CWD = Path(__file__).resolve().parent


def print_banner(title: str):
    print("\n" + "=" * 65)
    print(f"   {title}")
    print("=" * 65)


def clean_previous_builds():
    print_banner("1. Cleaning Previous Build Artifacts")
    for folder in ["build", "dist"]:
        target = CWD / folder
        if target.exists():
            print(f" Removing old directory: {target} ...")
            try:
                shutil.rmtree(target)
            except Exception as e:
                print(f" [Warning]: Could not completely delete {folder}: {e}")
    print(" ✓ Cleanup complete.")


def check_dependencies():
    print_banner("2. Checking Build Dependencies")
    try:
        import PyInstaller
        print(f" ✓ PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print(" ✗ PyInstaller is not installed in the current environment!")
        print(" Run: pip install pyinstaller")
        sys.exit(1)

    try:
        import cv2
        print(f" ✓ OpenCV version: {cv2.__version__}")
    except ImportError:
        print(" ✗ OpenCV is not installed!")
        sys.exit(1)

    try:
        import kivymd
        print(f" ✓ KivyMD version: {kivymd.__version__}")
    except ImportError:
        print(" ✗ KivyMD is not installed!")
        sys.exit(1)


def run_pyinstaller_build():
    print_banner("3. Building Standalone Executable (PyInstaller)")
    spec_file = CWD / "dlDesktop.spec"
    if not spec_file.exists():
        print(f" ✗ Spec file not found: {spec_file}")
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        str(spec_file),
        "--clean",
        "--noconfirm",
    ]

    print(f" Executing: {' '.join(cmd)}\n")
    start_time = time.time()
    result = subprocess.run(cmd, cwd=str(CWD))
    elapsed = time.time() - start_time

    if result.returncode != 0:
        print(f"\n ✗ Build failed with exit code: {result.returncode}")
        sys.exit(result.returncode)

    print(f"\n ✓ Build succeeded in {elapsed:.1f} seconds.")


def summarize_output():
    print_banner("4. Build Output Summary")
    dist_dir = CWD / "dist" / "Img2Sketch"
    exe_file = dist_dir / "Img2Sketch.exe"

    if exe_file.exists():
        total_size = sum(f.stat().st_size for f in dist_dir.rglob('*') if f.is_file())
        mb_size = total_size / (1024 * 1024)
        print(f" 📦 Application Package : {dist_dir}")
        print(f" 🚀 Main Executable    : {exe_file}")
        print(f" 💾 Total Bundle Size  : {mb_size:.2f} MB")
        print("\n [Next Steps]:")
        print(" 1. Test run: dist\\Img2Sketch\\Img2Sketch.exe")
        print(" 2. Compile installer with Inno Setup using: kivy\\img2sketch.iss")
    else:
        print(f" [Warning]: Expected executable not found at {exe_file}")


def main():
    print_banner("SKETCH ANIMATION STUDIO — EXE BUILD PIPELINE")
    clean_previous_builds()
    check_dependencies()
    run_pyinstaller_build()
    summarize_output()


if __name__ == "__main__":
    main()
