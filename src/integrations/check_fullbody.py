#!/usr/bin/env python3
"""Check a full-body PSD and locate PSD2Live before manual import.

This adapter is read-only. It never starts PSD2Live, Cubism, or inference.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".psd"}


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


_configure_stdio()


def _find_psd2live(root: Path) -> Path | None:
    if root.is_file():
        return root
    candidates = [
        root / "PSD2Live.exe",
        root / "PSD2Live" / "PSD2Live.exe",
        root / "bin" / "PSD2Live.exe",
        root / "gradlew.bat",
        root / "gradlew",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    if root.is_dir():
        for candidate in root.rglob("PSD2Live.exe"):
            return candidate
    return None


def inspect(psd: Path, psd2live_root: Path | None) -> dict[str, Any]:
    problems: list[str] = []
    warnings: list[str] = []
    if not psd.is_file():
        problems.append(f"PSD does not exist: {psd}")
    elif psd.suffix.lower() not in IMAGE_SUFFIXES:
        problems.append("Full-body import requires a layered PSD.")
    elif psd.stat().st_size == 0:
        problems.append("PSD file is empty.")

    root = psd2live_root or (
        Path(os.environ["PSD2LIVE_ROOT"]) if os.environ.get("PSD2LIVE_ROOT") else None
    )
    executable = _find_psd2live(root) if root else None
    if psd2live_root and not executable:
        problems.append(f"PSD2Live was not found under: {psd2live_root}")
    if executable is None:
        warnings.append(
            "PSD2Live was not found. Install its Windows portable release before full-body binding."
        )

    if shutil.which("PSD2Live") is None and executable is None:
        warnings.append("PSD2Live is not on PATH.")

    return {
        "schema_version": 1,
        "ok": not problems,
        "psd": str(psd.resolve()) if psd.exists() else str(psd),
        "psd_size_bytes": psd.stat().st_size if psd.is_file() else None,
        "psd2live_root": str(root.resolve()) if root and root.exists() else str(root) if root else None,
        "psd2live_executable": str(executable.resolve()) if executable else None,
        "problems": problems,
        "warnings": warnings,
        "required_manual_checks": [
            "front/back hair separation",
            "left/right eyes and hands",
            "left/right legs and shoes",
            "ankles and stable soles",
            "jacket or hood ownership",
            "belt, bag and dangling accessories",
            "pants/skirt and crotch ownership",
            "hidden regions needed by arm and leg motion",
        ],
        "next": "Open the PSD in PSD2Live, choose the full preset, and export .cmo3 first.",
        "launched_psd2live": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psd", required=True, type=Path)
    parser.add_argument("--psd2live-root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = inspect(args.psd, args.psd2live_root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Full-body PSD ready: {'yes' if result['ok'] else 'no'}")
        print(f"PSD: {result['psd']}")
        print(f"PSD2Live: {result['psd2live_executable'] or 'not found'}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        for problem in result["problems"]:
            print(f"ERROR: {problem}")
        print(result["next"])
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

