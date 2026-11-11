#!/usr/bin/env python3
"""Tests for the skill's occlusion workflow helpers."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from make_tk_workflow import build_workflow  # noqa: E402


class TkWorkflowTests(unittest.TestCase):
    def test_auto_fill_and_original_are_explicit(self) -> None:
        graph = build_workflow("hero.png", auto_fill=True, seed=7)
        generate = graph["4"]["inputs"]
        self.assertTrue(generate["auto_fill"])
        self.assertEqual(generate["min_alpha_coverage"], 0.01)
        self.assertNotIn("group_offload", graph["2"]["inputs"])
        self.assertNotIn("quant_mode", graph["2"]["inputs"])
        save = graph["7"]["inputs"]
        self.assertEqual(save["original_image"], ["1", 0])
        self.assertEqual(save["source_filename"], ["1", 2])

    def test_filter_is_inserted_before_save(self) -> None:
        graph = build_workflow("hero.png", exclude_tags="tail,wings")
        self.assertEqual(graph["7"]["class_type"], "SeeThrough_LayerFilter")
        self.assertEqual(graph["8"]["inputs"]["parts"], ["7", 0])

    def test_include_and_exclude_are_exclusive(self) -> None:
        with self.assertRaises(ValueError):
            build_workflow("hero.png", include_tags="face", exclude_tags="tail")

    def test_resolution_must_match_node_constraint(self) -> None:
        with self.assertRaises(ValueError):
            build_workflow("hero.png", resolution=1000)


class PsdOrderTests(unittest.TestCase):
    def make_psd(self, path: Path, order: list[str]) -> None:
        doc = PSDImage.new("RGBA", (64, 64), color=(0, 0, 0, 0))
        group = doc.create_group(name="Layers")
        for index, name in enumerate(order):
            layer = group.create_pixel_layer(
                Image.new("RGBA", (64, 64), (40 + index * 20, 80, 120, 255)),
                name=name,
            )
            layer.visible = True
        doc.save(path, encoding="utf-8")

    def run_check(self, psd: Path, mode: str) -> dict:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "occlusion_psd_check.py"),
                str(psd),
                "--mode",
                mode,
                "--require-original",
                "--json",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return json.loads(completed.stdout)

    def test_collar_triplet_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            psd = Path(temp) / "collar.psd"
            self.make_psd(
                psd,
                [
                    "Original",
                    "Hair_Back",
                    "Collar_Back",
                    "Neck",
                    "Collar_Front",
                    "Hair_Bang",
                    "Hat",
                ],
            )
            result = self.run_check(psd, "collar")
            self.assertTrue(result["ok"], result["errors"])
            self.assertLess(result["roles"]["collar_back"], result["roles"]["neck"])
            self.assertLess(result["roles"]["neck"], result["roles"]["collar_front"])

    def test_collar_front_below_neck_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            psd = Path(temp) / "bad-collar.psd"
            self.make_psd(
                psd,
                [
                    "Original",
                    "Collar_Back",
                    "Collar_Front",
                    "Neck",
                ],
            )
            result = self.run_check(psd, "collar")
            self.assertFalse(result["ok"])
            self.assertTrue(any(item["code"] == "invalid_draw_order" for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
