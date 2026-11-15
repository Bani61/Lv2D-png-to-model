[SYSTEM INSTRUCTION: You are an AI agent operating this skill. This file is the machine-facing protocol. The human-facing overview lives in README.md; do not confuse the two audiences.]

# Lv2D-png-to-model — Agent Operating Protocol

Display name: `Lv2D-png-to-model`
Internal skill ID: `lv2d-png-to-model`
Version: `1.4.0`

## 0. Read order

1. This file (installation + execution contract).
2. `SKILL.md` (task routing, capability ladder, safety gates).
3. `workflows/skill-routing.md` when the user's request could belong to another Live2D skill.
4. `workflows/psd2live-mcp.md` when the task involves rigging, draw order, keyforms or export.
5. `references/model-defects.md` when the user reports a visual defect.

## 1. Outcome

After installation an agent can:

- inspect a PNG/JPG illustration and prepare Live2D variants;
- decompose or normalize a layered PSD;
- run the bundled `rigkit` half-body pipeline (mesh, deformation, preview, VTS install);
- drive **PSD2Live** through its MCP server to rig, reorder layers, edit keyforms and export `.cmo3` / `.moc3` / `.model3.json` / `.physics3.json`;
- verify results by rendering the model to PNG instead of guessing.

Hard rules inherited from the human README: do not upload character art, do not start See-through / CUDA inference / PSD2Live / Cubism / VTube Studio automatically, do not silently overwrite a previous model version.

## 2. Installation protocol

Run from the package root.

```text
python check_env.py --json
python install.py --yes
python install.py --verify-only --json
```

Success = exit code 0 and `"ok": true` in the JSON.

Optional local CUDA decomposition:

```text
python install.py --yes --with-local-gpu
```

Optional skill copy into an empty host skill directory:

```text
python install.py --yes --install-skill <empty-skill-directory>
```

Never overwrite an existing skill directory.

### Environment facts observed on real machines

- `check_env.py` performs a write probe (`_permission_check`, check_env.py:175). Under a restricted sandbox it can spin at 100% CPU with no output. Run it with write access, or expect the hang.
- PyPI direct access is unreliable from mainland China; `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple` succeeded where the default index reset mid-download.
- A non-ASCII install path (e.g. `F:\半白bani_\dsh-lv2D`) breaks Python argv when a shell passes it through. Install to a pure-ASCII path such as `C:\Users\<user>\.dsh\skills\lv2d-png-to-model`.

## 3. Dependency tree

Required (`requirements.txt`): numpy, opencv-python, Pillow, psd-tools, gradio_client.

Optional GPU (`--with-local-gpu`): torch, torchvision, diffusers, transformers==4.49.0, bitsandbytes, safetensors, accelerate, huggingface_hub.

Optional runtime: onnxruntime.

Not bundled, must exist on the machine: ComfyUI-See-through + weights, PSD2Live portable build, Live2D Cubism Editor + Cubism Core, VTube Studio, ffmpeg.

## 4. Resource decision rules

| Condition | Profile |
| --- | --- |
| no CUDA / no torch | `cloud_only` |
| GPU < 8 GB class | `low_vram_under_8gb` (768 px, 15 steps) |
| 8–10 GB | `cautious_8gb` (1024 px, 20 steps) |
| 10–12 GB | `balanced_10_12gb` |
| ≥ 12 GB | `high_quality_12gb_plus` |

Measured: RTX 5060 Laptop 8 GB with NF4 at 1280/30 entered inference but did not finish in 50 minutes. Prefer HF 1280 or ModelScope 1536 for final full-body decomposition.

## 5. Execution paths

### 5.1 Half-body (`rigkit`)

```text
python src\run_pipeline.py variants <asset-dir> A0-base
python src\run_pipeline.py split <asset-dir> <asset-dir>\layers --pad-top 90
python src\run_pipeline.py estimate <asset-dir>\layers-st <character-dir> --name <name>
python src\run_pipeline.py prepare <character-dir>\character.json
python src\run_pipeline.py build <character-dir>\character.json
python src\run_pipeline.py vts <character-dir>\character.json --install
```

Set `PYTHONPATH` to this package's `src` first.

### 5.2 Full-body (`PSD2Live`)

CLI (no GUI, one shot):

```text
PSD2Live.exe --input model.psd --output out --lang zh --atlas 8192 --mesh-spacing 32
```

MCP (when you need to fix what the automation got wrong):

```text
# 1. start the GUI app; it serves MCP on http://127.0.0.1:23871/mcp
PSD2Live.exe

# 2. token: Settings -> MCP -> 访问令牌, or read it from the registry
#    HKCU\Software\JavaSoft\Prefs\io\github\psd2live\agent
#    agent_mcp_bearer_token -> strip every '/' (Java prefs encoding)

# 3. drive it
python scripts\psd2live_mcp.py list
python scripts\psd2live_mcp.py inspect --scope objects --query Mouth
python scripts\psd2live_mcp.py render --out check.png --params '{"ParamMouthOpenY":1.0}'
```

Full command reference: `workflows/psd2live-mcp.md`.
Operation schema cheatsheet: `references/psd2live-ops.md`.

### 5.3 Verification (mandatory before delivery)

```text
powershell -File tests\smoke.ps1
powershell -File tests\smoke.ps1 -Full -Psd <file.psd>
```

Smoke covers: python, deps, PSD2Live presence, Cubism presence + external API port, environment variables, package integrity. Exit code 0 = no FAIL (SKIP is acceptable). Log lands in `%DSH_LOG_DIR%` or `%TEMP%`.

For model-level verification, always render to PNG and look at it:

```text
python scripts\psd2live_mcp.py render --out face.png --params '{"ParamMouthOpenY":1.0,"ParamEyeLOpen":0}'
```

A change that does not alter the rendered PNG did not happen. Confirm by hash.

## 6. Completion contract

Installation is complete when:

- `check_env.py --json` reports all required dependencies present;
- `src/rigkit` imports succeed;
- `config/pipeline.json` has a valid `active_profile`;
- `skill_manifest.json` validates;
- `tests/smoke.ps1` reports 0 FAIL;
- no inference process was started by the installation itself.

A model delivery is complete when:

- `smoke.ps1` still passes;
- the exported `.moc3` was loaded (or at minimum rendered) and visually checked;
- `model3.json` references resolve (`Moc`, `Textures`, `Physics`, `Motions`, `Expressions`);
- a previous version remains on disk untouched.

## 7. Known failure signatures

Do not re-derive these; they are already diagnosed.

| Symptom | Root cause | Where |
| --- | --- | --- |
| mouth never opens | layer named `嘴张开` was hidden / not named `张嘴` | `references/model-defects.md#1` |
| mouth opens with spikes | the mouth art layer is tiny (≈14 px) or sits far from the mesh | `#2` |
| eyes closed but white/blue sliver remains | eye-white + iris are visible at the closed keyform | `#3` |
| mouth fully open at 20% input | VTS `OutputRangeUpper` = 2.1 | `#4` |
| blink looks like a stutter | blink motion is linear + VTS eye range 1.9 | `#5` |
| arms hidden behind the shirt | PSD draw order puts `Arm_L/R` under `Topwear_Body` | `#6` |
| model loads but "parameters missing" | user opened the PSD through Cubism's import path instead of the `.cmo3` | `#7` |

## 8. Safety gates

- Reading the character art, calling a remote service, or starting long GPU work requires explicit user approval.
- Every write to a model file is preceded by a backup; state the rollback command in the same reply.
- Cubism MCP (`cubism-mcp`) requires Cubism Editor **5.4 alpha or newer** with `外部应用程序集成` enabled. On 5.3.x the port 22033 probe times out — that is expected, record it as BLOCKED rather than FAIL.
- Never claim a rig is "verified" from logs alone. Render, look, then report.
