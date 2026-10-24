"""
Automated Release Packager for Number Plate Detection System
Builds the standalone Windows executable and packages it into a distributable ZIP.
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

VERSION = "1.0.0"
APP_NAME = "NumberPlateDetectionSystem"
DIST_DIR = Path("dist")
APP_DIR = DIST_DIR / APP_NAME
ZIP_NAME = f"Number-Plate-Detection-System-v{VERSION}-win64.zip"
ZIP_PATH = DIST_DIR / ZIP_NAME

def log(msg):
    print(f"\n[NPDS Packager] {msg}")

def check_prerequisites():
    log("Checking prerequisites...")
    if not Path("models/best.onnx").exists():
        raise FileNotFoundError("Model file 'models/best.onnx' not found!")
    if not Path("npds_data.db").exists():
        log("Notice: npds_data.db will be initialized automatically on first run if missing.")
    log("Prerequisites verified.")

def run_pyinstaller():
    log("Running PyInstaller build using npds.spec...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "npds.spec"]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError("PyInstaller build failed with non-zero exit code.")
    log("PyInstaller compilation completed successfully.")

def copy_additional_assets():
    log("Verifying bundled assets and directories...")
    # Ensure models directory in dist
    dist_models = APP_DIR / "models"
    dist_models.mkdir(exist_ok=True)
    shutil.copy2("models/best.onnx", dist_models / "best.onnx")

    # Ensure database in dist
    if Path("npds_data.db").exists():
        shutil.copy2("npds_data.db", APP_DIR / "npds_data.db")

    # Ensure assets in dist
    dist_assets = APP_DIR / "assets"
    if Path("assets").exists():
        if dist_assets.exists():
            shutil.rmtree(dist_assets)
        shutil.copytree("assets", dist_assets)

    # Add quickstart instructions
    readme_txt = APP_DIR / "RUN_INSTRUCTIONS.txt"
    readme_txt.write_text(
        "Number Plate Detection System (ANPR / ALPR)\n"
        "===========================================\n\n"
        "How to Run:\n"
        "1. Simply double-click 'NumberPlateDetectionSystem.exe'.\n"
        "2. No Python installation or extra drivers required.\n"
        "3. Explore features from the left navigation:\n"
        "   - Dashboard: Real-time system stats\n"
        "   - Live Feed: Webcam or RTSP IP camera feed detection\n"
        "   - Media Scan: Upload test images from the included 'assets/Cars' folder\n"
        "   - Vehicle Database: Manage and search registered/stolen vehicle records\n\n"
        "Developed by Hammad Haider\n"
    )
    log("Assets copied and verified.")

def make_zip_archive():
    log(f"Creating ZIP distribution: {ZIP_PATH} ...")
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in APP_DIR.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(DIST_DIR)
                zf.write(file_path, rel_path)

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    log(f"Distribution package successfully created: {ZIP_PATH} ({size_mb:.1f} MB)")

def main():
    try:
        check_prerequisites()
        run_pyinstaller()
        copy_additional_assets()
        make_zip_archive()
        print("\n" + "=" * 60)
        print("  BUILD COMPLETE!")
        print(f"  Distribution package: {ZIP_PATH.resolve()}")
        print("  Upload this file to GitHub -> Releases to share with recruiters!")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
