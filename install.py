#!/usr/bin/env python3
"""Install dependencies and choose a safe pipeline profile.

The installer never launches See-through, PSD2Live, Cubism, or VTube Studio.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from check_env import PACKAGE_ROOT, collect_environment


SRC_ROOT = PACKAGE_ROOT / "src"
CONFIG_PATH = PACKAGE_ROOT / "config" / "pipeline.json"
REQUIREMENTS = PACKAGE_ROOT / "requirements.txt"
GPU_REQUIREMENTS = PACKAGE_ROOT / "requirements-local-gpu.txt"
MANIFEST_PATH = PACKAGE_ROOT / "skill_manifest.json"


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


_configure_stdio()


class InstallFailure(RuntimeError):
    def __init__(self, stage: str, message: str, suggestion: str = "") -> None:
        super().__init__(message)
        self.stage = stage
        self.suggestion = suggestion


def _run(command: list[str], stage: str) -> str:
    print(f"[{stage}] {' '.join(command)}", flush=True)
    try:
        completed = subprocess.run(
            command,
            cwd=PACKAGE_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise InstallFailure(stage, str(exc), "Check that the current Python can run pip.") from exc

    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    if completed.returncode != 0:
        raise InstallFailure(
            stage,
            f"command exited with code {completed.returncode}",
            "Fix the package/network error shown above, then rerun install.py.",
        )
    return completed.stdout


def _pip_install(requirement_file: Path, stage: str) -> None:
    if not requirement_file.is_file():
        raise InstallFailure(stage, f"Missing requirements file: {requirement_file}")
    _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--timeout",
            "60",
            "-r",
            str(requirement_file),
        ],
        stage,
    )


def _install_local_gpu(torch_index_url: str) -> None:
    _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--timeout",
            "120",
            "--index-url",
            torch_index_url,
            "torch",
            "torchvision",
        ],
        "install-torch",
    )
    _pip_install(GPU_REQUIREMENTS, "install-local-gpu-support")


def _verify_imports(report: dict[str, Any]) -> dict[str, Any]:
    required_missing = report["summary"]["missing_required"]
    source_imports: dict[str, Any] = {}
    sys.path.insert(0, str(SRC_ROOT))
    try:
        import rigkit.split  # noqa: F401
        import rigkit.build  # noqa: F401
        import rigkit.seethrough  # noqa: F401
        import rigkit.vts  # noqa: F401

        source_imports = {
            "rigkit.split": True,
            "rigkit.build": True,
            "rigkit.seethrough": True,
            "rigkit.vts": True,
        }
    except Exception as exc:
        source_imports = {
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        if str(SRC_ROOT) in sys.path:
            sys.path.remove(str(SRC_ROOT))

    return {
        "ok": not required_missing and all(
            value is True for value in source_imports.values()
        ),
        "missing_required": required_missing,
        "source_imports": source_imports,
    }


def _validate_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        raise InstallFailure("validate-manifest", f"Missing manifest: {MANIFEST_PATH}")
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallFailure("validate-manifest", str(exc)) from exc

    required_keys = {
        "name",
        "version",
        "entry",
        "skill_entry",
        "inputs",
        "outputs",
        "installation",
    }
    missing = sorted(required_keys - set(manifest))
    if missing:
        raise InstallFailure(
            "validate-manifest", f"Manifest is missing keys: {', '.join(missing)}"
        )
    for relative in (
        manifest["entry"],
        manifest["skill_entry"],
        "check_env.py",
        "install.py",
        "src/rigkit/split.py",
    ):
        if not (PACKAGE_ROOT / relative).is_file():
            raise InstallFailure("validate-manifest", f"Manifest entry does not exist: {relative}")
    return manifest


def _write_profile(report: dict[str, Any]) -> dict[str, Any]:
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallFailure("write-profile", str(exc)) from exc

    selected = report["recommended_profile"]
    profiles = config.get("profiles", {})
    if selected not in profiles:
        raise InstallFailure("write-profile", f"Unknown profile: {selected}")

    config["active_profile"] = selected
    config["detected_environment"] = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "gpu_detected": report["gpu"]["detected"],
        "local_gpu_runtime_ready": report["gpu"]["local_gpu_runtime_ready"],
        "torch_version": report["gpu"]["torch"].get("version"),
        "devices": report["gpu"]["devices"],
        "python": report["python"]["version"],
    }

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = CONFIG_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp_path, CONFIG_PATH)
    return config


def _install_skill_copy(target: Path) -> None:
    target = target.expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise InstallFailure(
            "install-skill",
            f"Target is not empty: {target}",
            "Choose a new directory so an existing Skill is never overwritten.",
        )
    target.mkdir(parents=True, exist_ok=True)
    items = [
        "AI_README.md",
        "SKILL.md",
        "skill_manifest.json",
        "requirements.txt",
        "requirements-local-gpu.txt",
        "requirements-optional.txt",
        "check_env.py",
        "install.py",
        "LICENSE",
        "agents",
        "src",
        "references",
        "config",
    ]
    for name in items:
        source = PACKAGE_ROOT / name
        destination = target / name
        if source.is_dir():
            shutil.copytree(source, destination)
        elif source.is_file():
            shutil.copy2(source, destination)
        else:
            raise InstallFailure("install-skill", f"Package item is missing: {source}")
    print(f"Skill copy installed to: {target}")


def _result_payload(
    ok: bool,
    stage: str,
    report: dict[str, Any] | None = None,
    verification: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
    error: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ok": ok,
        "stage": stage,
        "package_root": str(PACKAGE_ROOT),
        "report": report,
        "verification": verification,
        "active_profile": profile.get("active_profile") if profile else None,
        "error": error,
        "next_command": (
            "python install.py --verify-only"
            if ok
            else "python check_env.py --json"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="run non-interactively")
    parser.add_argument("--skip-deps", action="store_true", help="do not run pip")
    parser.add_argument(
        "--with-local-gpu",
        action="store_true",
        help="install the optional CUDA/PyTorch stack; this is a large download",
    )
    parser.add_argument(
        "--torch-index-url",
        default="https://download.pytorch.org/whl/cu128",
        help="PyTorch wheel index used by --with-local-gpu",
    )
    parser.add_argument("--verify-only", action="store_true", help="check without installing")
    parser.add_argument(
        "--install-skill",
        type=Path,
        metavar="TARGET_DIR",
        help="copy this package into an empty Skill directory after installation",
    )
    parser.add_argument("--json", action="store_true", help="print a machine-readable result")
    args = parser.parse_args()

    if not args.yes and not args.verify_only and sys.stdin.isatty():
        answer = input("Install Lv2D-png-to-model dependencies? Type 'yes': ").strip().lower()
        if answer != "yes":
            print("Cancelled.")
            return 1

    stage = "start"
    report: dict[str, Any] = {}
    verification: dict[str, Any] = {}
    profile: dict[str, Any] = {}
    try:
        stage = "check-environment"
        report = collect_environment()
        if not report["python"]["supported"]:
            raise InstallFailure(
                stage,
                f"Python {report['python']['minimum']}+ is required.",
                "Install a supported Python and rerun this script with that interpreter.",
            )

        stage = "validate-manifest"
        manifest = _validate_manifest()

        if not args.verify_only and not args.skip_deps:
            stage = "install-core-dependencies"
            _pip_install(REQUIREMENTS, stage)
            if args.with_local_gpu:
                stage = "install-optional-gpu-dependencies"
                _install_local_gpu(args.torch_index_url)

        stage = "recheck-environment"
        report = collect_environment()
        stage = "verify-install"
        verification = _verify_imports(report)
        if not verification["ok"]:
            raise InstallFailure(
                stage,
                "Dependency or source import verification failed.",
                "Run check_env.py --json, inspect missing_required and source_imports, then retry.",
            )

        stage = "write-profile"
        profile = _write_profile(report)

        if args.install_skill:
            stage = "install-skill"
            _install_skill_copy(args.install_skill)

        payload = _result_payload(True, "complete", report, verification, profile)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(
                "\nInstallation complete.\n"
                f"Skill: {manifest['name']} {manifest['version']}\n"
                f"Active profile: {profile['active_profile']}\n"
                f"Verify: {report['python']['executable']} install.py --verify-only\n"
            )
        return 0
    except InstallFailure as exc:
        payload = _result_payload(
            False,
            exc.stage,
            report or None,
            verification or None,
            profile or None,
            {"message": str(exc), "suggestion": exc.suggestion},
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"INSTALL FAILED at {exc.stage}: {exc}", file=sys.stderr)
            if exc.suggestion:
                print(f"Suggestion: {exc.suggestion}", file=sys.stderr)
        return 1
    except Exception as exc:
        payload = _result_payload(
            False,
            stage,
            report or None,
            verification or None,
            profile or None,
            {
                "message": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=5),
                "suggestion": "Inspect the error above and rerun check_env.py --json.",
            },
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

