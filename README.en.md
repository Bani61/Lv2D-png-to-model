# Lv2D-png-to-model

**Turn one illustration into a Live2D model you can stream with in VTube Studio.**

Feed it a single PNG/JPG illustration (or an already-layered PSD) and get a
`.moc3` model that loads directly in VTube Studio — mesh, deformers, parameters,
physics, idle and blink already generated. No manual mesh work in Cubism Editor.

Who it is for: individuals and small teams making VTuber models who would rather
not learn the full Cubism binding workflow.

- Version: **1.4.0**
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Downloads: [Releases](https://github.com/Bani61/Lv2D-png-to-model/releases)

---

## 1. Feature list

| # | Feature | Description | Requires | Status |
| --- | --- | --- | --- | --- |
| 1 | **Full-body auto binding** | layered PSD → `.moc3` / `.cmo3` / physics / motions / expressions | PSD2Live 3.6.x | available |
| 2 | **Half-body auto binding** | bundled rigkit, for small-angle head turns | Python | available |
| 3 | **AI layer splitting** | one illustration → layered PSD | cloud tokens, or CUDA locally | available |
| 4 | **Local CUDA inference** | run splitting on your own GPU, nothing uploaded | NVIDIA GPU + several GB | available (slow, see issue 7) |
| 5 | **Occlusion order audit** | checks hats / hair / collar / ears / neck before binding | Python | available |
| 6 | **ComfyUI workflow** | generates a tk_seethrough workflow to fill missing layers | ComfyUI | available |
| 7 | **Scripted binding fixes** | change draw order, keyforms, materials over MCP, then re-render | PSD2Live 3.6.7+ | available |
| 8 | **Render verification** | render a PNG at chosen parameter values to compare before/after | PSD2Live | available |
| 9 | **VTube Studio install** | copies the output into the VTS model folder | VTube Studio | available |
| 10 | **VTS parameter tuning** | fixes VTS auto-generated ranges that are far too wide | VTube Studio | manual step |
| 11 | **Environment check / install** | Python, deps, GPU, VRAM, disk, write permission | Python ≥ 3.10 | available |
| 12 | **Smoke test** | 7 checks, PASS / FAIL / SKIP | PowerShell | available |
| 13 | **Defect playbook** | 9 defect signatures with cause and fix | — | docs |

> Cloud splitting uploads the artwork to the inference service. Use
> `--with-local-gpu` if that matters.

---

## 2. System requirements

| Item | Minimum | Recommended |
| --- | --- | --- |
| OS | Windows 10 64-bit | Windows 11 |
| Python | 3.10 | 3.11 / 3.12 |
| RAM | 8 GB | 16 GB |
| Disk | 5 GB free | 20 GB free (local CUDA) |
| GPU | integrated (cloud splitting) | NVIDIA, ≥ 8 GB VRAM |
| Other software | PSD2Live 3.6.x | + Cubism Editor, VTube Studio |

**Profiles** (auto-selected from `config/pipeline.json`):

| Profile | Condition | Resolution / steps |
| --- | --- | --- |
| `cloud_only` | no CUDA | cloud |
| `low_vram_under_8gb` | < 8 GB | 768 / 15 |
| `cautious_8gb` | 8–10 GB | 1024 / 20 |
| `balanced_10_12gb` | 10–12 GB | higher |
| `high_quality_12gb_plus` | ≥ 12 GB | highest |

---

## 3. Install

Download `Lv2D-png-to-model-1.4.0.zip` from
[Releases](https://github.com/Bani61/Lv2D-png-to-model/releases), extract, then
inside `Lv2D-png-to-model\`:

```powershell
python check_env.py --json
python install.py --yes
python install.py --verify-only --json                     # expects "ok": true
powershell -ExecutionPolicy Bypass -File tests/smoke.ps1    # no FAIL
```

Optional local CUDA splitting (several GB):

```powershell
python install.py --yes --with-local-gpu
```

No registry writes, no PATH changes; uninstall means deleting the folder.

> Versions before 1.4.0 have no release package.

---

## 4. Quick start (full body, ~10 minutes)

```powershell
PSD2Live.exe --input character.psd --output out --lang zh --atlas 8192 --mesh-spacing 32
```

Copy the whole `out` folder into
`...\VTube Studio_Data\StreamingAssets\Live2DModels\<model-name>\`.

On first load VTube Studio shows **two dialogs — both are normal**:

1. "auto-configure this model?" → **auto-configure**
2. "create 15 VTS parameters from Live2D defaults" → **confirm**

Skipping them still loads the model but leaves hotkeys and tracking partly
unconfigured.

Do not drop the two flags: `--atlas 8192` avoids rectangular seams on the face
(the 4096 default has them) and `--mesh-spacing 32` keeps mouth/eye deformation
from going blocky.

---

## 5. Output files

```
out\character.moc3            ← loaded by VTube Studio
out\character.model3.json     ← manifest
out\character.physics3.json   ← hair / accessory physics
out\character.cdi3.json       ← parameter and part display info
out\character.cmo3            ← open in Cubism Editor for detail work
out\character.4096\texture_00..0N.png
out\character.*.motion3.json  ← idle / nod / shake / blink
out\character.*.exp3.json     ← smile / sad / angry / surprised
```

Open `.cmo3` directly — never through *new / import PSD*, which yields empty
deformers — and keep it next to its `<name>.4096\` texture folder.

---

## 6. Workflow

```
1 prepare layered PSD      names per convention (references/图层清单.md)
2 environment check        python check_env.py --json
3 bind                     PSD2Live.exe --input ... --output ...
4 render verification      mouth open, eyes closed, ±20° head turn
5 install into VTS         copy folder, accept the two setup dialogs
6 tune                     edit Mouth / Eye upper ranges in vtube.json
7 detail work (optional)   open the cmo3 in Cubism Editor
```

Step 4 is mandatory:

```powershell
python scripts/psd2live_mcp.py render --out mouth.png --params ParamMouthOpenY=1.0
python scripts/psd2live_mcp.py render --out eyes.png  --params ParamEyeLOpen=0 ParamEyeROpen=0
```

If the new PNG has the same sha256 as the previous one, the change did nothing.

---

## 7. Parameter tuning (VTube Studio)

`Live2DModels\<model>\<model>.vtube.json`

```jsonc
"ParameterSettings": [
  { "Input": "MouthOpen",    "OutputRangeLower": 0, "OutputRangeUpper": 0.85 }, // default 2.1
  { "Input": "EyeOpenLeft",  "OutputRangeUpper": 1.0 },                        // default 1.9
  { "Input": "EyeOpenRight", "OutputRangeUpper": 1.0 }
]
```

Close VTS first — it writes its in-memory settings back on exit.

---

## 8. Known issues

| # | Issue | Impact | Status | Workaround |
| --- | --- | --- | --- | --- |
| 1 | **Cubism 5.4 integration not started** | cannot script edits inside Cubism (keyforms, mesh, part order remain manual) | **not started** | the external API only exists in 5.4 alpha, which ended 2026-10-18 and is time-locked; 5.3.x cannot open port 22033. Edit through the PSD2Live project or by hand |
| 2 | **Closed-eye binding is flawed** | a thin blue sliver and crisp edges remain under the eyelid; the PSD has no dedicated closed-eye layer, so the lash is only squashed | open | shrink eye-white / iris to 0.12 on the closed keyform (works for some models); a proper closed-eye layer is the real fix |
| 3 | **Auto-split mouth binds poorly** | spiky, torn mouth edges when opening; the split often returns scattered pixels or a very small mouth (14 px) that stretches badly | open | use a properly named, fully drawn mouth layer (`张嘴` / `mouth_open`), 29×21 level; see `references/model-defects.md` |
| 4 | **VTS ranges too wide by default** | mouth slams open, blink stutters | known, manual | edit `OutputRangeUpper` (section 7) |
| 5 | **Re-export resets motions** | tuned idle / blink overwritten | known, manual | back up `.motion3.json`, copy back after export |
| 6 | **Arms hidden behind the shirt** | sleeves invisible | known, manual | move arm layers above the torso in the PSD, or set draw order 165/166 after import |
| 7 | **8 GB local CUDA is very slow** | 1280 resolution / 30 steps did not finish in 50 minutes on an 8 GB card | known | use `cloud_only`, or drop to 768 / 15 steps |
| 8 | **Large head angles deform** | hard cut edges beyond ±20° | known | limit rotation; larger angles need manual keyforms in Cubism |

---

## 9. FAQ

**"Parameters lost" or "auto-configure" on load — is the file broken?**
No. That is VTube Studio's first-load wizard: choose auto-configure, then confirm
the 15 default parameters.

**The model cannot open its mouth / never blinks.**
The mouth or eye layer is hidden or misnamed. Binding is by layer name.

**Can I skip PSD2Live?**
For half-body work yes (bundled rigkit). Full-body binding currently requires it.

**Can it be fully automatic?**
No. Steps 4 and 6 need human judgement; a generated binding is not a verified one.

**Does splitting upload my artwork?**
Cloud splitting does; use `--with-local-gpu` to keep it local.

**Textures are missing after opening the .cmo3.**
Keep the `.cmo3` next to its `<name>.4096\` folder.

---

## 10. Repository layout

```text
check_env.py            environment probe
install.py              dependency installer / verifier
config/pipeline.json    resource profiles
src/rigkit/             half-body binding engine
src/integrations/       full-body PSD pre-check
scripts/                psd2live_mcp.py, make_tk_workflow.py, occlusion_psd_check.py
workflows/              PSD2Live MCP, half-body rig, verify/rollback
references/             model-defects.md, psd2live-ops.md, layer conventions
tests/smoke.ps1         smoke test
```

---

## 11. License

**PolyForm Noncommercial License 1.0.0** — noncommercial use only.
Copyright holder: **Bani61**. Full text: [LICENSE](LICENSE). Third-party components keep their own
licenses — [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). PSD2Live itself is
GPL-3.0 and is not distributed here.

---

**For AI agents**: [AI_README.md](AI_README.md) (install and execution protocol),
[SKILL.md](SKILL.md) (task routing and capability tiers).
