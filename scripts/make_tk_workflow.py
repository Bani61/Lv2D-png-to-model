#!/usr/bin/env python3
"""Build a ComfyUI API workflow for the tackcrypto1031/tk_seethrough fork.

The generated graph uses only inputs verified in tk_seethrough v1.2.9 at
commit 265d7acbb82bd60198ff17714361426994114149.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LAYERDIFF_MODEL = "layerdifforg/seethroughv0.0.2_layerdiff3d"
DEPTH_MODEL = "layerdifforg/seethroughv0.0.1_marigold"


def _tag_lines(value: str) -> str:
    return "\n".join(item.strip() for item in value.split(",") if item.strip())


def build_workflow(
    input_name: str,
    filename_prefix: str = "seethrough",
    seed: int = 42,
    resolution: int = 1280,
    steps: int = 30,
    enable_head_detail: bool = True,
    auto_fill: bool = False,
    min_alpha_coverage: float = 0.01,
    tblr_split: bool = True,
    use_lama: bool = True,
    include_tags: str = "",
    exclude_tags: str = "",
    layerdiff_model: str = LAYERDIFF_MODEL,
    depth_model: str = DEPTH_MODEL,
) -> dict[str, Any]:
    if include_tags and exclude_tags:
        raise ValueError("include_tags and exclude_tags are mutually exclusive")
    if not input_name.strip():
        raise ValueError("input_name must not be empty")
    if not 512 <= resolution <= 2048 or resolution % 64:
        raise ValueError("resolution must be between 512 and 2048 and divisible by 64")
    if not 1 <= steps <= 100:
        raise ValueError("steps must be between 1 and 100")
    if not 0.001 <= min_alpha_coverage <= 0.1:
        raise ValueError("min_alpha_coverage must be between 0.001 and 0.1")

    workflow: dict[str, Any] = {
        "1": {
            "class_type": "SeeThrough_LoadSource",
            "inputs": {"image": input_name},
        },
        "2": {
            "class_type": "SeeThrough_LoadLayerDiffModel",
            "inputs": {
                "model": layerdiff_model,
                "vae_ckpt": "",
                "unet_ckpt": "",
            },
        },
        "3": {
            "class_type": "SeeThrough_LoadDepthModel",
            "inputs": {"model": depth_model},
        },
        "4": {
            "class_type": "SeeThrough_GenerateLayers_Custom",
            "inputs": {
                "image": ["1", 0],
                "layerdiff_model": ["2", 0],
                "seed": seed,
                "resolution": resolution,
                "num_inference_steps": steps,
                "enable_head_detail": enable_head_detail,
                "auto_fill": auto_fill,
                "min_alpha_coverage": min_alpha_coverage,
            },
        },
        "5": {
            "class_type": "SeeThrough_GenerateDepth",
            "inputs": {
                "layers": ["4", 0],
                "depth_model": ["3", 0],
                "seed": seed,
            },
        },
        "6": {
            "class_type": "SeeThrough_PostProcess",
            "inputs": {
                "layers_depth": ["5", 0],
                "tblr_split": tblr_split,
                "use_lama": use_lama,
            },
        },
    }

    parts_source = ["6", 0]
    filter_tags = include_tags or exclude_tags
    if filter_tags:
        workflow["7"] = {
            "class_type": "SeeThrough_LayerFilter",
            "inputs": {
                "parts": parts_source,
                "mode": "include" if include_tags else "exclude",
                "tags": _tag_lines(filter_tags),
            },
        }
        parts_source = ["7", 0]

    save_id = "8" if filter_tags else "7"
    workflow[save_id] = {
        "class_type": "SeeThrough_SavePSD",
        "inputs": {
            "parts": parts_source,
            "filename_prefix": filename_prefix,
            "original_image": ["1", 0],
            "source_filename": ["1", 2],
        },
    }
    return workflow


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-name", required=True, help="ComfyUI input image filename.")
    parser.add_argument("--filename-prefix", default="seethrough")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--resolution", type=int, default=1280)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--enable-head-detail", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--auto-fill",
        action="store_true",
        help="Allow up to five diffusion runs. Obtain explicit approval first.",
    )
    parser.add_argument("--min-alpha-coverage", type=float, default=0.01)
    parser.add_argument("--no-tblr-split", action="store_true")
    parser.add_argument("--no-lama", action="store_true")
    parser.add_argument("--include-tags", default="", help="Comma-separated tk tag names to keep.")
    parser.add_argument("--exclude-tags", default="", help="Comma-separated tk tag names to remove.")
    parser.add_argument("--layerdiff-model", default=LAYERDIFF_MODEL)
    parser.add_argument("--depth-model", default=DEPTH_MODEL)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    workflow = build_workflow(
        input_name=args.input_name,
        filename_prefix=args.filename_prefix,
        seed=args.seed,
        resolution=args.resolution,
        steps=args.steps,
        enable_head_detail=args.enable_head_detail,
        auto_fill=args.auto_fill,
        min_alpha_coverage=args.min_alpha_coverage,
        tblr_split=not args.no_tblr_split,
        use_lama=not args.no_lama,
        include_tags=args.include_tags,
        exclude_tags=args.exclude_tags,
        layerdiff_model=args.layerdiff_model,
        depth_model=args.depth_model,
    )
    payload = json.dumps(workflow, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
        print(args.out.resolve())
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
