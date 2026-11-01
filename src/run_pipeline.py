#!/usr/bin/env python3
"""Run bundled rigkit modules without remembering PYTHONPATH details."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parent
MODULES = {
    "doctor": "rigkit.doctor",
    "variants": "rigkit.variants",
    "split": "rigkit.split",
    "seethrough": "rigkit.seethrough",
    "extras": "rigkit.extras",
    "estimate": "rigkit.estimate",
    "check-art": "rigkit.check_art",
    "prepare": "rigkit.prepare",
    "build": "rigkit.build",
    "preview": "rigkit.preview",
    "vts": "rigkit.vts",
    "render": "rigkit.render",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=sorted(MODULES))
    parser.add_argument("args", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()

    environment = os.environ.copy()
    current = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(SRC_ROOT) if not current else str(SRC_ROOT) + os.pathsep + current
    )
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    command = [sys.executable, "-m", MODULES[parsed.task], *parsed.args]
    completed = subprocess.run(command, cwd=Path.cwd(), env=environment, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

