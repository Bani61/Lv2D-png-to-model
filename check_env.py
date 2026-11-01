#!/usr/bin/env python3
"""Read-only environment inspection for Lv2D-png-to-model.

This script intentionally uses only the Python standard library so it can run
before project dependencies are installed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
MIN_PYTHON = (3, 10)


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


_configure_stdio()

REQUIRED_PACKAGES = {
    "numpy": "numpy",
    "opencv-python": "cv2",
    "Pillow": "PIL",
    "psd-tools": "psd_tools",
    "gradio_client": "gradio_client",
}

OPTIONAL_PACKAGES = {
    "torch": "torch",
    "torchvision": "torchvision",
    "diffusers": "diffusers",
    "transformers": "transformers",
    "bitsandbytes": "bitsandbytes",
    "safetensors": "safetensors",
    "accelerate": "accelerate",
    "huggingface_hub": "huggingface_hub",
    "onnxruntime": "onnxruntime",
}

EXTERNAL_TOOLS = {
    "git": "git",
    "ffmpeg": "ffmpeg",
    "nvidia-smi": "nvidia-smi",
    "codex": "codex",
    "psd2live": "PSD2Live",
}


def _package_version(distribution: str) -> str | None:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def _package_status(distribution: str, module: str) -> dict[str, Any]:
    found_module = importlib.util.find_spec(module) is not None
    installed_version = _package_version(distribution)
    return {
        "installed": found_module and installed_version is not None,
        "version": installed_version,
        "module": module,
    }


def _run_text(command: list[str], timeout: int = 8) -> str | None:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _nvidia_smi_gpus() -> list[dict[str, Any]]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return []
    output = _run_text(
        [
            executable,
            "--query-gpu=name,memory.total,memory.free,driver_version",
            "--format=csv,noheader,nounits",
        ]
    )
    if not output:
        return []

    devices: list[dict[str, Any]] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 4:
            continue
        try:
            total_mb = int(float(parts[1]))
            free_mb = int(float(parts[2]))
        except ValueError:
            continue
        devices.append(
            {
                "name": parts[0],
                "total_memory_mb": total_mb,
                "free_memory_mb": free_mb,
                "driver_version": parts[3],
                "source": "nvidia-smi",
            }
        )
    return devices


def _torch_gpu_status() -> dict[str, Any]:
    result: dict[str, Any] = {
        "installed": False,
        "cuda_available": False,
        "version": None,
        "cuda_version": None,
        "devices": [],
    }
    if importlib.util.find_spec("torch") is None:
        return result

    try:
        import torch
    except Exception as exc:  # pragma: no cover - import depends on host DLLs
        result["import_error"] = f"{type(exc).__name__}: {exc}"
        return result

    result["installed"] = True
    result["version"] = getattr(torch, "__version__", None)
    result["cuda_version"] = getattr(getattr(torch, "version", None), "cuda", None)
    try:
        result["cuda_available"] = bool(torch.cuda.is_available())
        if result["cuda_available"]:
            for index in range(torch.cuda.device_count()):
                properties = torch.cuda.get_device_properties(index)
                result["devices"].append(
                    {
                        "index": index,
                        "name": properties.name,
                        "total_memory_mb": int(properties.total_memory / (1024**2)),
                        "source": "torch",
                    }
                )
    except Exception as exc:  # pragma: no cover - driver-specific
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _permission_check() -> dict[str, Any]:
    result = {
        "package_root_writable": False,
        "current_directory_writable": False,
        "zip_create_read_delete": False,
        "errors": [],
    }
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=PACKAGE_ROOT, prefix=".lv2d-write-", delete=False
        ) as handle:
            handle.write("ok")
            temp_name = handle.name
        Path(temp_name).unlink()
        result["package_root_writable"] = True
    except OSError as exc:
        result["errors"].append(f"package root: {exc}")

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=Path.cwd(), prefix=".lv2d-write-", delete=False
        ) as handle:
            handle.write("ok")
            temp_name = handle.name
        Path(temp_name).unlink()
        result["current_directory_writable"] = True
    except OSError as exc:
        result["errors"].append(f"current directory: {exc}")

    try:
        with tempfile.TemporaryDirectory(prefix="lv2d-zip-") as directory:
            archive = Path(directory) / "probe.zip"
            payload = Path(directory) / "payload.txt"
            payload.write_text("lv2d", encoding="utf-8")
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as stream:
                stream.write(payload, arcname="payload.txt")
            with zipfile.ZipFile(archive, "r") as stream:
                if stream.read("payload.txt") != b"lv2d":
                    raise OSError("zip payload mismatch")
            archive.unlink()
        result["zip_create_read_delete"] = True
    except (OSError, zipfile.BadZipFile) as exc:
        result["errors"].append(f"zip probe: {exc}")
    return result


def _recommended_profile(gpu: dict[str, Any]) -> str:
    if not gpu["torch"]["cuda_available"]:
        return "cloud_only"
    devices = gpu["torch"].get("devices", [])
    if not devices:
        return "cloud_only"
    memory_mb = max(int(device["total_memory_mb"]) for device in devices)
    if memory_mb < int(7.5 * 1024):
        return "low_vram_under_8gb"
    if memory_mb < 10 * 1024:
        return "cautious_8gb"
    if memory_mb < 12 * 1024:
        return "balanced_10_12gb"
    return "high_quality_12gb_plus"


def collect_environment() -> dict[str, Any]:
    python_version = sys.version_info
    python_supported = python_version >= MIN_PYTHON
    required = {
        distribution: _package_status(distribution, module)
        for distribution, module in REQUIRED_PACKAGES.items()
    }
    optional = {
        distribution: _package_status(distribution, module)
        for distribution, module in OPTIONAL_PACKAGES.items()
    }
    missing_required = [name for name, status in required.items() if not status["installed"]]

    torch_status = _torch_gpu_status()
    smi_devices = _nvidia_smi_gpus()
    devices = torch_status.get("devices") or smi_devices
    gpu = {
        "detected": bool(devices),
        "local_gpu_runtime_ready": bool(torch_status["cuda_available"] and devices),
        "torch": torch_status,
        "devices": devices,
    }
    recommended_profile = _recommended_profile(gpu)

    try:
        disk = shutil.disk_usage(PACKAGE_ROOT)
        disk_info = {
            "path": str(PACKAGE_ROOT),
            "free_bytes": disk.free,
            "free_gb": round(disk.free / (1024**3), 2),
            "sufficient_for_runtime": disk.free >= 3 * 1024**3,
        }
    except OSError as exc:
        disk_info = {
            "path": str(PACKAGE_ROOT),
            "free_bytes": None,
            "free_gb": None,
            "sufficient_for_runtime": False,
            "error": str(exc),
        }

    tools = {}
    for name, executable in EXTERNAL_TOOLS.items():
        path = shutil.which(executable)
        tools[name] = {"available": bool(path), "path": path}

    permissions = _permission_check()
    warnings: list[str] = []
    if not python_supported:
        warnings.append("Python 3.10 or newer is required.")
    if not permissions["package_root_writable"]:
        warnings.append("Package directory is not writable; installation profiles cannot be stored.")
    if not permissions["zip_create_read_delete"]:
        warnings.append("Python ZIP create/read/delete probe failed.")
    if not disk_info["sufficient_for_runtime"]:
        warnings.append("Less than 3 GB free space; model/cache installation may fail.")
    if not gpu["local_gpu_runtime_ready"]:
        warnings.append("Local CUDA See-through is unavailable; remote/cloud splitting is recommended.")
    if gpu["detected"] and recommended_profile == "cautious_8gb":
        warnings.append("8 GB-class GPU detected; local 1280/30-step inference is slow and should be explicit.")
    if not tools["ffmpeg"]["available"]:
        warnings.append("ffmpeg is optional and only needed for preview videos.")

    status = "ok"
    if not python_supported or not permissions["zip_create_read_delete"] or missing_required:
        status = "needs_install" if python_supported else "unsupported"

    return {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "package_root": str(PACKAGE_ROOT),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "supported": python_supported,
            "minimum": ".".join(map(str, MIN_PYTHON)),
        },
        "core_dependencies": required,
        "optional_dependencies": optional,
        "gpu": gpu,
        "permissions": permissions,
        "external_tools": tools,
        "disk": disk_info,
        "recommended_profile": recommended_profile,
        "summary": {
            "status": status,
            "missing_required": missing_required,
            "warnings": warnings,
            "next_command": "python install.py --yes" if missing_required else "python install.py --verify-only",
        },
    }


def format_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    python_info = report["python"]
    gpu = report["gpu"]
    permissions = report["permissions"]
    disk = report["disk"]
    lines = [
        "Lv2D-png-to-model environment check",
        f"Status: {summary['status']}",
        f"Python: {python_info['version']} ({python_info['executable']})",
        f"Python supported: {'yes' if python_info['supported'] else 'no'}",
        f"GPU detected: {'yes' if gpu['detected'] else 'no'}",
        f"CUDA runtime ready: {'yes' if gpu['local_gpu_runtime_ready'] else 'no'}",
    ]
    for device in gpu.get("devices", []):
        lines.append(
            f"  - {device.get('name', 'unknown')}: {device.get('total_memory_mb', '?')} MiB total"
        )
    lines.extend(
        [
            f"Recommended profile: {report['recommended_profile']}",
            f"Package writable: {'yes' if permissions['package_root_writable'] else 'no'}",
            f"ZIP create/read/delete: {'yes' if permissions['zip_create_read_delete'] else 'no'}",
            f"Free disk: {disk['free_gb']} GB",
            "",
            "Core dependencies:",
        ]
    )
    for name, status in report["core_dependencies"].items():
        marker = "OK" if status["installed"] else "MISSING"
        lines.append(f"  [{marker}] {name} {status['version'] or ''}".rstrip())
    if summary["warnings"]:
        lines.extend(["", "Warnings:"])
        for warning in summary["warnings"]:
            lines.append(f"  - {warning}")
    lines.extend(
        [
            "",
            f"Missing required: {', '.join(summary['missing_required']) or 'none'}",
            f"Next: {summary['next_command']}",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--output", type=Path, help="also write the JSON report to this path")
    args = parser.parse_args()

    report = collect_environment()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text(report))

    return 0 if report["summary"]["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())

