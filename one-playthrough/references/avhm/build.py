#!/usr/bin/env python3
"""Package AVHM as a modern .sdkmod file."""

import zipfile
from pathlib import Path

MOD_DIR = Path(__file__).parent
MOD_NAME = "AVHM"  # must exactly match the .sdkmod filename stem (case-sensitive)
OUTPUT = MOD_DIR.parent / "AVHM.sdkmod"

FILES = ["__init__.py", "pyproject.toml"]

with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for f in FILES:
        path = MOD_DIR / f
        if not path.exists():
            print(f"WARNING: {f} not found, skipping")
            continue
        zf.write(path, f"{MOD_NAME}/{f}")
        print(f"  Added: {MOD_NAME}/{f}")

print(f"\nCreated {OUTPUT.name} ({OUTPUT.stat().st_size:,} bytes)")
