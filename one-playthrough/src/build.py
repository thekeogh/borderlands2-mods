#!/usr/bin/env python3
"""Validate and package a release; archive previous loose versions, never overwrite them."""

from __future__ import annotations

import ast
import re
import runpy
import tempfile
import zipfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
DIST = SOURCE.parent / "dist"
PACKAGE = "one_playthrough"
REQUIRED = ("__init__.py", "core.py", "reflection.py", "activity.py", "observers.py", "diagnostics.py",
            "tuning.py", "version.py", "pyproject.toml")
GUIDES = ("INSTALL.md", "TESTING.md", "INVESTIGATION.md", "VALIDATION.md")


def validate_source(source=SOURCE):
    package = source / PACKAGE
    missing = [str(p) for p in [*(package / f for f in REQUIRED),
                                *(source / "docs" / f for f in GUIDES)] if not p.is_file()]
    if missing:
        raise RuntimeError("Missing required release files: " + ", ".join(missing))
    identity = runpy.run_path(str(package / "version.py"))
    metadata = (package / "pyproject.toml").read_text(encoding="utf-8")
    version = identity["VERSION"]
    if re.search(r'^version\s*=\s*"' + re.escape(version) + r'"\s*$', metadata, re.M) is None:
        raise RuntimeError("pyproject.toml and version.py disagree")
    if identity["AUTHOR"] != "keogh" or 'name = "keogh"' not in metadata:
        raise RuntimeError("Release author must be keogh")
    for module in (package / name for name in REQUIRED if name.endswith(".py")):
        tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
        compile(tree, str(module), "exec")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                if node.module + ".py" not in REQUIRED:
                    raise RuntimeError(f"Unpackaged relative import: {node.module}")
    return version


def archive_previous(dist, current_version):
    for folder in sorted(dist.glob("OnePlaythrough-*")):
        if not folder.is_dir() or folder.name == f"OnePlaythrough-{current_version}":
            continue
        archive = dist / (folder.name + ".zip")
        if archive.exists():
            raise RuntimeError(f"Refusing to overwrite previous release archive: {archive.name}")
        files = sorted(p for p in folder.rglob("*") if p.is_file())
        with tempfile.TemporaryDirectory(dir=dist) as temporary:
            temp = Path(temporary) / archive.name
            with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as out:
                for file in files:
                    out.write(file, file.relative_to(dist))
            with zipfile.ZipFile(temp) as check:
                if check.testzip() is not None:
                    raise RuntimeError("Previous-release archive failed integrity check")
                for file in files:
                    if check.read(str(file.relative_to(dist))) != file.read_bytes():
                        raise RuntimeError("Previous-release archive verification failed")
            temp.replace(archive)
        # Remove only verified archived files; never recursively delete unrelated directories.
        for file in files:
            file.unlink()
        for sub in sorted((p for p in folder.rglob("*") if p.is_dir()), reverse=True):
            sub.rmdir()
        folder.rmdir()


def build(source=SOURCE, dist=DIST):
    version = validate_source(source)
    dist.mkdir(parents=True, exist_ok=True)
    destination = dist / f"OnePlaythrough-{version}"
    if destination.exists():
        raise RuntimeError("Release already exists. Increment version; existing releases are immutable.")
    with tempfile.TemporaryDirectory(prefix="one-playthrough-build-") as temporary:
        staged = Path(temporary) / destination.name
        staged.mkdir()
        sdkmod = staged / (PACKAGE + ".sdkmod")
        with zipfile.ZipFile(sdkmod, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as out:
            for name in REQUIRED:
                out.write(source / PACKAGE / name, f"{PACKAGE}/{name}")
        with zipfile.ZipFile(sdkmod) as check:
            expected = {f"{PACKAGE}/{name}" for name in REQUIRED}
            if set(check.namelist()) != expected or check.testzip() is not None:
                raise RuntimeError("Invalid .sdkmod layout or corrupt member")
        for name in GUIDES:
            (staged / name).write_bytes((source / "docs" / name).read_bytes())
        # Fully stage and verify the new release before touching existing distribution files.
        archive_previous(dist, version)
        destination.mkdir()
        for file in staged.iterdir():
            (destination / file.name).write_bytes(file.read_bytes())
    return destination


if __name__ == "__main__":
    try:
        print(build())
    except Exception as exc:
        raise SystemExit(f"Build failed: {exc}")
