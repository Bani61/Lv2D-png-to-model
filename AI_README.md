[SYSTEM INSTRUCTION: You are an AI agent tasked with installing this skill. Read this file carefully, run the checks, and install dependencies automatically.]

# Lv2D-png-to-model AI Installation Guide

Display name: `Lv2D-png-to-model`

Internal Skill ID: `lv2d-png-to-model` (the platform requires lowercase skill IDs).

## Outcome

Install this package so an AI agent can:

- inspect a PNG/JPG illustration and prepare Live2D variants;
- decompose or normalize a layered PSD;
- use the bundled `rigkit` half-body pipeline for mesh, deformation, preview and VTube Studio installation;
- route full-body work through PSD2Live for `.cmo3`, `.moc3`, `.model3.json` and `.vtube.json` output.

Do not upload character art. Do not start See-through, CUDA inference, PSD2Live, Cubism or VTube Studio automatically. Installation is allowed; production inference requires a later user-approved action.

For occlusion-sensitive work, read `references/occlusion-workflow.md` and
`references/project-landscape.md` before choosing a model. The verified routing is:

- See-through or tk_seethrough for anime semantic decomposition.
- PSD2Live `source_split_depth` for front/back layers around a neck or hair mesh.
- tk_seethrough `auto_fill` only for missing or low-similarity layers, never for occlusion-order decisions.
- CObL, RevealLayer and Qwen-Image-Layered only as optional research/comparison paths until tested on this workflow.

## Installation Protocol

Run commands from the directory containing this file.

1. Inspect the machine:

```text
python check_env.py --json
```

Parse `summary.status`, `summary.missing_required`, `gpu`, `permissions`, `disk`, and `recommended_profile`.

2. If Python is older than 3.10, stop and request a supported Python.

3. Install required Python dependencies:

```text
python install.py --yes
```

The installer runs `pip install -r requirements.txt`, verifies source imports, and writes the detected profile to `config/pipeline.json`.

4. Install optional local CUDA support only when the user wants local See-through:

```text
python install.py --yes --with-local-gpu
```

This is a large PyTorch/diffusers download. It does not download See-through model weights and does not run inference.

5. Verify:

```text
python install.py --verify-only --json
python check_env.py
```

Success means `install.py` returns exit code 0 and JSON contains `"ok": true`.

6. Optional Skill copy: if the host expects a Skill directory and the user permits a write outside this package, install into a new empty directory:

```text
python install.py --yes --install-skill <empty-skill-directory>
```

Never overwrite an existing Skill directory.

## Dependency Tree

Required, installed by `requirements.txt`:

```text
Python >= 3.10
├─ numpy
├─ opencv-python
├─ Pillow
├─ psd-tools
└─ gradio_client
```

Optional local GPU profile, installed only with `--with-local-gpu`:

```text
CUDA-capable NVIDIA GPU
├─ torch
├─ torchvision
├─ diffusers
├─ transformers==4.49.0
├─ bitsandbytes
├─ safetensors
├─ accelerate
└─ huggingface_hub
```

Optional vision/runtime packages:

```text
requirements-optional.txt
└─ onnxruntime
```

External applications and assets are not bundled:

- ComfyUI-See-through and LayerDiff/Marigold weights.
- PSD2Live Windows portable release.
- Live2D Cubism Editor and Cubism Core.
- VTube Studio.
- ffmpeg, only for preview clips.
- Hugging Face or ModelScope tokens, only if the user chooses remote decomposition.

## Resource Decision Rules

- No CUDA/torch: use the `cloud_only` profile.
- GPU below the 8 GB product class: use `low_vram_under_8gb`; batch size 1, 768 resolution, 15 steps.
- 8-10 GB GPU class: use `cautious_8gb`; batch size 1, 1024 resolution, 20 steps, no group offload by default.
- 10-12 GB GPU: use `balanced_10_12gb`.
- 12 GB or more: use `high_quality_12gb_plus`.

For the known Windows RTX 5060 8 GB setup, local NF4 at 1280/30 entered inference but did not finish after 50 minutes. Prefer Hugging Face 1280 or ModelScope 1536 for final full-body decomposition.

## Source Commands

Set `PYTHONPATH` to this package's `src` directory. On PowerShell:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python src\run_pipeline.py doctor
```

Half-body sequence:

```text
python src\run_pipeline.py variants <asset-dir> A0-base
python src\run_pipeline.py split <asset-dir> <asset-dir>\layers --pad-top 90
python src\run_pipeline.py estimate <asset-dir>\layers-st <character-dir> --name <name>
python src\run_pipeline.py prepare <character-dir>\character.json
python src\run_pipeline.py build <character-dir>\character.json
python src\run_pipeline.py vts <character-dir>\character.json --install
```

Build a tk_seethrough ComfyUI workflow without starting inference:

```text
python scripts\make_tk_workflow.py --input-name hero.png --out hero-tk.json
```

The generator defaults to `auto_fill=false`. Adding `--auto-fill` permits up to
five diffusion runs and must be approved before submission.

Validate a generated PSD:

```text
python scripts\occlusion_psd_check.py hero.psd --mode full --require-original --json
```

Full-body sequence:

1. Prepare a layered PSD with separate left/right legs, feet, hands, head, face, hair and clothing ownership.
2. Run `python src\integrations\check_fullbody.py --psd <file.psd> --psd2live-root <path>`.
3. Open the PSD in PSD2Live and use its full preset.
4. Export `.cmo3` for inspection, then `.moc3`/`.vtube.json` for runtime.
5. Validate hips, knees, ankles, soles, shoulders, wrists, sleeves and skirt/pants layers.

## Completion Contract

The installer is complete when:

- `check_env.py --json` shows all required dependencies installed;
- source imports in `src/rigkit` succeed;
- `config/pipeline.json` has a valid `active_profile`;
- `skill_manifest.json` validates;
- no inference process was started by installation.

Read `SKILL.md` for operating instructions and `references/` for detailed Live2D workflows.

