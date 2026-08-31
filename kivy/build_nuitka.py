"""
Automated Nuitka Build Script for Storyboard to Whiteboard Animation (Windows Native EXE).
Compiles Python code directly to optimized native C machine code with full Kivy/KivyMD integration.
"""

import sys
import os
import shutil
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Apply patch to Nuitka's debug timing assertion for Python 3.13 stability
try:
    import nuitka.ModuleRegistry
    orig_timing_fn = nuitka.ModuleRegistry.addModuleOptimizationTimeInformation

    def safe_addModuleOptimizationTimeInformation(module_name, pass_number, initial, merge_counts):
        try:
            return orig_timing_fn(module_name, pass_number, initial, merge_counts)
        except AssertionError:
            pass

    nuitka.ModuleRegistry.addModuleOptimizationTimeInformation = safe_addModuleOptimizationTimeInformation
except Exception as e:
    pass

CWD = Path(__file__).resolve().parent


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"   {title}")
    print("=" * 70)


def clean_previous_builds():
    print_banner("1. Cleaning Previous Build Artifacts")
    for folder in ["main.build", "main.dist", "main.onefile-build", "dist"]:
        target = CWD / folder
        if target.exists():
            print(f" Removing old directory: {target} ...")
            try:
                shutil.rmtree(target, ignore_errors=True)
            except Exception as e:
                print(f" [Warning]: Could not delete {folder}: {e}")
    print(" [OK] Cleanup complete.")


def run_nuitka_build():
    print_banner("2. Compiling with Nuitka to Native Windows Binary")

    icon_path = CWD / "data" / "images" / "favicon.ico"

    args = [
        "nuitka",
        "--standalone",
        "--enable-plugin=kivy",
        "--include-package=engine",
        "--include-package=ui",
        "--include-package=licensing",
        "--include-package=kivymd",
        "--include-package-data=kivymd",
        "--include-data-dir=data=data",
        "--include-data-file=main_layout.kv=main_layout.kv",
        "--nofollow-import-to=unittest,doctest,pytest,scipy,matplotlib,pandas,IPython,tkinter,test",
        "--windows-console-mode=disable",
        "--windows-company-name=Ahmed Abdellah",
        "--windows-product-name=Storyboard to Whiteboard Animation",
        "--windows-file-version=3.0.0.0",
        "--windows-product-version=3.0.0.0",
        "--windows-file-description=Storyboard to Whiteboard Animation Studio",
        "--output-dir=dist",
        "--output-filename=StoryboardToWhiteboard.exe",
        "--assume-yes-for-downloads",
        "--jobs=4",
        "main.py"
    ]

    if icon_path.exists():
        args.insert(12, f"--windows-icon-from-ico={icon_path}")

    print(f" Executing Nuitka:\n {' '.join(args)}\n")
    start_time = time.time()

    sys.argv = args
    from nuitka.__main__ import main as nuitka_main
    
    os.chdir(str(CWD))
    try:
        nuitka_main()
    except SystemExit as se:
        if se.code not in (0, None):
            print(f"\n [Error]: Nuitka exited with code: {se.code}")
            sys.exit(se.code)

    elapsed = time.time() - start_time
    print(f"\n [OK] Nuitka compilation succeeded in {elapsed/60:.2f} minutes ({elapsed:.1f}s).")


def summarize_and_finalize():
    print_banner("3. Packaging & Distribution Summary")
    dist_dir = CWD / "dist" / "main.dist"
    final_dir = CWD / "dist" / "Storyboard_to_Whiteboard_Animation"
    
    if dist_dir.exists():
        if final_dir.exists():
            shutil.rmtree(final_dir, ignore_errors=True)
        dist_dir.rename(final_dir)
        dist_dir = final_dir

    exe_file = dist_dir / "StoryboardToWhiteboard.exe"

    if exe_file.exists():
        total_size = sum(f.stat().st_size for f in dist_dir.rglob('*') if f.is_file())
        mb_size = total_size / (1024 * 1024)
        print(f" [+] Application Bundle : {dist_dir}")
        print(f" [+] Main Native Executable : {exe_file}")
        print(f" [+] Total Bundle Size  : {mb_size:.2f} MB")
        print("\n [Distribution Ready]:")
        print(" -> You can zip and send the 'dist\\Storyboard_to_Whiteboard_Animation' folder to ANY Windows PC.")
        print(" -> The application will launch instantly via 'StoryboardToWhiteboard.exe' with zero Python requirements.")
    else:
        print(f" [Warning]: Expected executable not found at {exe_file}")


def main():
    print_banner("STORYBOARD TO WHITEBOARD ANIMATION — NUITKA NATIVE BUILD")
    clean_previous_builds()
    run_nuitka_build()
    summarize_and_finalize()


if __name__ == "__main__":
    main()
