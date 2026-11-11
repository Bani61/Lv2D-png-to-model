#!/usr/bin/env python3
"""Check PSD layer ownership and front/back occlusion order."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from psd_tools import PSDImage


ROLES = {
    "original": ("original", "original_underlay"),
    "collar_back": ("collar_back", "hood_neck_back", "hood_back"),
    "neck": ("neck", "neck_skin"),
    "collar_front": ("collar_front", "hood_neck_front", "hood_front"),
    "hair_back": ("hair_back",),
    "hair_bang": ("hair_bang", "front_hair"),
    "hat": ("hat", "headwear", "cap"),
    "ear_left": ("ear_l", "ears_l"),
    "ear_right": ("ear_r", "ears_r"),
}


def normalize(name: str) -> str:
    value = unicodedata.normalize("NFKC", name).strip().lower()
    return re.sub(r"[\s\-./]+", "_", value)


def walk(children: Iterable[Any], group: str | None = None) -> tuple[list[dict], list[dict]]:
    layers: list[dict] = []
    groups: list[dict] = []
    for node in children:
        name = str(node.name)
        if node.is_group():
            path = f"{group}/{name}" if group else name
            before = len(layers)
            groups.append({"name": name, "path": path})
            child_layers, child_groups = walk(node, path)
            layers.extend(child_layers)
            groups.extend(child_groups)
            groups[-len(child_groups) - 1]["leaf_count"] = len(layers) - before
        else:
            image = node.topil()
            alpha = image.getchannel("A").getbbox() if "A" in image.getbands() else image.getbbox()
            layers.append(
                {
                    "name": name,
                    "normalized_name": normalize(name),
                    "group": group,
                    "visible": bool(node.visible),
                    "order": len(layers),
                    "bbox": list(node.bbox or ()),
                    "alpha_bbox": list(alpha) if alpha else None,
                }
            )
    return layers, groups


def find_role(layers: list[dict], role: str) -> tuple[dict | None, list[dict]]:
    aliases = ROLES[role]
    matches = [layer for layer in layers if layer["normalized_name"] in aliases]
    for alias in aliases:
        exact = [layer for layer in matches if layer["normalized_name"] == alias]
        if exact:
            return exact[0], matches
    return (matches[0], matches) if matches else (None, [])


def required_role(
    layers: list[dict],
    role: str,
    errors: list[dict],
    warnings: list[dict],
) -> dict | None:
    layer, matches = find_role(layers, role)
    if layer is None:
        errors.append(
            {
                "code": "missing_required_layer",
                "role": role,
                "accepted_names": list(ROLES[role]),
            }
        )
        return None
    if not any(match["visible"] and match["alpha_bbox"] for match in matches):
        errors.append(
            {
                "code": "invisible_or_empty_required_layer",
                "role": role,
                "layers": [match["name"] for match in matches],
            }
        )
    if len(matches) > 1:
        warnings.append(
            {
                "code": "multiple_role_candidates",
                "role": role,
                "layers": [match["name"] for match in matches],
            }
        )
    return layer


def require_below(roles: list[tuple[str, dict | None]], errors: list[dict]) -> None:
    if any(layer is None for _, layer in roles):
        return
    for (left_role, left), (right_role, right) in zip(roles, roles[1:]):
        assert left is not None and right is not None
        if left["order"] >= right["order"]:
            errors.append(
                {
                    "code": "invalid_draw_order",
                    "left": left["name"],
                    "right": right["name"],
                    "required_relation": f"{left_role} < {right_role}",
                }
            )


def check_expected(layers: list[dict], names: list[str], errors: list[dict]) -> None:
    selected = []
    for name in names:
        norm = normalize(name)
        match = next((layer for layer in layers if layer["normalized_name"] == norm), None)
        if match is None:
            errors.append({"code": "expected_layer_missing", "layer": name})
            return
        selected.append(match)
    for left, right in zip(selected, selected[1:]):
        if left["order"] >= right["order"]:
            errors.append(
                {
                    "code": "expected_order_violation",
                    "left": left["name"],
                    "right": right["name"],
                }
            )


def inspect_psd(
    psd: Path,
    mode: str,
    require_original: bool,
    expected_order: Path | None,
) -> dict[str, Any]:
    doc = PSDImage.open(psd, encoding="utf-8")
    layers, groups = walk(doc)
    errors: list[dict] = []
    warnings: list[dict] = []
    canvas = [int(doc.width), int(doc.height)]

    for group in groups:
        if group.get("leaf_count") == 0:
            warnings.append({"code": "empty_group", "group": group["path"]})

    duplicate_names: dict[str, list[str]] = {}
    for layer in layers:
        duplicate_names.setdefault(layer["normalized_name"], []).append(layer["name"])
        bbox = layer["bbox"]
        if bbox and (bbox[0] < 0 or bbox[1] < 0 or bbox[2] > canvas[0] or bbox[3] > canvas[1]):
            errors.append({"code": "layer_outside_canvas", "layer": layer["name"], "bbox": bbox})
    for name, matches in duplicate_names.items():
        if len(matches) > 1:
            errors.append({"code": "duplicate_layer_name", "normalized": name, "layers": matches})

    original = required_role(layers, "original", errors, warnings) if require_original else find_role(layers, "original")[0]
    if require_original and original is not None:
        if not original["visible"]:
            errors.append({"code": "original_hidden", "layer": original["name"]})
        below = [
            layer["name"]
            for layer in layers
            if layer["visible"] and layer["order"] < original["order"]
        ]
        if below:
            errors.append({"code": "original_not_bottom", "layers_below": below})

    collar_back = collar_front = neck = None
    if mode in {"collar", "hat", "full"}:
        collar_back = required_role(layers, "collar_back", errors, warnings)
        neck = required_role(layers, "neck", errors, warnings)
        collar_front = required_role(layers, "collar_front", errors, warnings)
        require_below(
            [("collar_back", collar_back), ("neck", neck), ("collar_front", collar_front)],
            errors,
        )

    if mode in {"hat", "full"}:
        hair_back = required_role(layers, "hair_back", errors, warnings)
        hair_bang = required_role(layers, "hair_bang", errors, warnings)
        hat = required_role(layers, "hat", errors, warnings)
        required_role(layers, "ear_left", errors, warnings)
        required_role(layers, "ear_right", errors, warnings)
        require_below(
            [("hair_back", hair_back), ("hair_bang", hair_bang), ("hat", hat)],
            errors,
        )

    expected: list[str] = []
    if expected_order:
        payload = json.loads(expected_order.read_text(encoding="utf-8-sig"))
        expected = payload.get("order") if isinstance(payload, dict) else payload
        if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
            raise ValueError("Expected order must be a name array or an object with an order array.")
        check_expected(layers, expected, errors)

    return {
        "schema_version": 1,
        "ok": not errors,
        "psd": str(psd.resolve()),
        "mode": mode,
        "canvas": canvas,
        "order_direction": "bottom_to_top",
        "layer_count": len(layers),
        "layers": layers,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "roles": {
            "original": original["order"] if original else None,
            "collar_back": collar_back["order"] if collar_back else None,
            "neck": neck["order"] if neck else None,
            "collar_front": collar_front["order"] if collar_front else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("psd", type=Path)
    parser.add_argument("--mode", choices=("basic", "collar", "hat", "full"), default="basic")
    parser.add_argument("--require-original", action="store_true")
    parser.add_argument("--expected-order", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    result = inspect_psd(
        args.psd.resolve(),
        args.mode,
        args.require_original,
        args.expected_order.resolve() if args.expected_order else None,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    if args.json:
        print(payload)
    else:
        print(f"PSD valid: {'yes' if result['ok'] else 'no'}")
        print(f"Layers: {result['layer_count']}; order: bottom to top")
        for error in result["errors"]:
            print(f"ERROR [{error['code']}] {error}")
        for warning in result["warnings"]:
            print(f"WARNING [{warning['code']}] {warning}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
