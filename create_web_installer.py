#!/usr/bin/env python3
"""CC_ISIS Web Installer Creator

Merges the bootloader, partition table, and application binary produced by
PlatformIO into a single firmware-merged.bin for use with ESP Web Tools,
then updates the version in web-installer/manifest.json.

Usage:
    python create_web_installer.py [version]

    version  Optional version string (e.g. "1.2.0").
             Falls back to the VERSION environment variable, then "0.0.1".

Run this after every successful PlatformIO build:
    pio run -e ccrawford_cc_isis_esp32s3
    python create_web_installer.py 1.2.0
"""

import glob
import json
import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# Project-specific configuration
# ---------------------------------------------------------------------------
ENV_NAME = "ccrawford_cc_isis_esp32s3"
BUILD_DIR = f".pio/build/{ENV_NAME}"
WEB_DIR = "web-installer"
MANIFEST_PATH = os.path.join(WEB_DIR, "manifest.json")

# ESP32-S3 chip identifier used by esptool
CHIP = "esp32s3"

# DIO, not QIO — this is the flash mode byte esptool patches into the bootloader
# image header, which tells the ESP32-S3 ROM how to read the secondary bootloader
# off flash. The ROM requires DIO for this initial load; the secondary bootloader
# then switches to QIO itself. board_build.flash_mode = qio controls the compiled
# code path in the bootloader, which is a separate thing.
FLASH_MODE = "dio"

# Must match board_build.f_flash (80000000L) in CC_ISIS_platformio.ini
FLASH_FREQ = "80m"

# Flash map offsets for ESP32-S3 with Arduino framework.
# NOTE: ESP32-S3 (and S2, C3) place the bootloader at 0x0.
#       Classic ESP32 uses 0x1000 — do NOT change this for S3.
BOOTLOADER_OFFSET  = "0x0"
PARTITION_OFFSET   = "0x8000"
OTA_DATA_OFFSET    = "0xe000"   # otadata partition (huge_app.csv) — needs boot_app0.bin
APP_OFFSET         = "0x10000"  # matches huge_app.csv first partition start

# boot_app0.bin marks app0 as the active OTA slot.  Without it the ESP32-S3
# bootloader sees all-0xFF otadata and refuses to boot.  PlatformIO always
# includes this file via FLASH_EXTRA_IMAGES; we must do the same.
_PIO_PACKAGES = os.path.join(os.path.expanduser("~"), ".platformio", "packages")
BOOT_APP0_BIN = os.path.join(
    _PIO_PACKAGES,
    "framework-arduinoespressif32",
    "tools", "partitions", "boot_app0.bin",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_version() -> str:
    """Determine version: CLI arg > VERSION env var > '0.0.1'."""
    if len(sys.argv) > 1:
        v = sys.argv[1]
    else:
        v = os.environ.get("VERSION", "0.0.1")
    return v.lstrip("v").strip(".")


def find_app_bin() -> str:
    """Return the newest non-merged .bin file in the build directory."""
    pattern = os.path.join(BUILD_DIR, "*.bin")
    candidates = [f for f in glob.glob(pattern) if "_merged" not in f]
    if not candidates:
        sys.exit(
            f"ERROR: No application .bin found in {BUILD_DIR}.\n"
            f"Run 'pio run -e {ENV_NAME}' first."
        )
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


def merge_firmware(app_bin: str, output_path: str) -> None:
    """Run esptool merge-bin to combine all flash regions into one file."""
    bootloader = os.path.join(BUILD_DIR, "bootloader.bin")
    partitions = os.path.join(BUILD_DIR, "partitions.bin")

    for path, name in [
        (bootloader,    "bootloader"),
        (partitions,    "partition table"),
        (BOOT_APP0_BIN, "boot_app0.bin (OTA slot marker)"),
        (app_bin,       "application"),
    ]:
        if not os.path.exists(path):
            sys.exit(f"ERROR: {name} binary not found: {path}")

    print(f"\nMerging firmware for {CHIP.upper()} (flash_mode={FLASH_MODE}, flash_freq={FLASH_FREQ}):")
    print(f"  {BOOTLOADER_OFFSET:8s}  {bootloader}")
    print(f"  {PARTITION_OFFSET:8s}  {partitions}")
    print(f"  {OTA_DATA_OFFSET:8s}  {BOOT_APP0_BIN}")
    print(f"  {APP_OFFSET:8s}  {app_bin}")
    print(f"  -> {output_path}")

    cmd = [
        sys.executable, "-m", "esptool",
        "--chip", CHIP,
        "merge-bin",           # esptool v5+: hyphens preferred over underscores
        "--flash-mode", FLASH_MODE,
        "--flash-freq", FLASH_FREQ,
        "-o", output_path,
        BOOTLOADER_OFFSET, bootloader,
        PARTITION_OFFSET,  partitions,
        OTA_DATA_OFFSET,   BOOT_APP0_BIN,
        APP_OFFSET,        app_bin,
    ]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit("ERROR: esptool merge_bin failed (see output above).")


def update_manifest(version: str) -> None:
    """Write the firmware version into manifest.json."""
    if not os.path.exists(MANIFEST_PATH):
        sys.exit(
            f"ERROR: {MANIFEST_PATH} not found.\n"
            "Ensure the web-installer/ folder exists with manifest.json."
        )
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    manifest["version"] = version

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"Updated {MANIFEST_PATH}  (version -> {version})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    version = get_version()
    app_bin = find_app_bin()
    merged_out = os.path.join(WEB_DIR, "firmware-merged.bin")

    os.makedirs(WEB_DIR, exist_ok=True)

    merge_firmware(app_bin, merged_out)
    update_manifest(version)

    size_mb = os.path.getsize(merged_out) / 1024 / 1024
    print(
        f"\nDone!\n"
        f"  {merged_out}  ({size_mb:.2f} MB)\n"
        f"  {MANIFEST_PATH}  (version {version})\n"
        f"\nCommit the web-installer/ folder and push to serve via GitHub Pages."
    )


if __name__ == "__main__":
    main()
