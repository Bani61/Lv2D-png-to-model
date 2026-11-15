# Lv2D-png-to-model

Turn one illustration — or one already-layered PSD — into a Live2D model you can
load in VTube Studio.

Three entry points, pick by what you already have:

| What you have | Path | Output |
| --- | --- | --- |
| A single PNG/JPG illustration | See-through split → PSD2Live binding | layered PSD + working model |
| An already-layered PSD | PSD2Live binding directly | `.moc3` / `.cmo3` / physics / motions |
| A half-body character needing hand-tuned binding | bundled `rigkit` pipeline | mesh + deformers + VTS package |

Current version: `1.4.0`. See [CHANGELOG.md](CHANGELOG.md).
Roadmap: [Next goal: Cubism 5.4 integration](#next-goal-cubism-54-integration).

## Install (packaged downloads start at 1.4.0)

**From 1.4.0 on, every version ships a built zip on
[Releases](https://github.com/Bani61/Lv2D-png-to-model/releases).** No clone, no
git required.

### Steps

1. Download `Lv2D-png-to-model-1.4.0.zip` from Releases;
2. Extract it — you get `Lv2D-png-to-model\`;
3. Inside that directory:

```powershell
python check_env.py --json                  # what is missing, is the GPU enough, can we write files
python install.py --yes                     # required dependencies only
python install.py --verify-only --json      # expects "ok": true
powershell -ExecutionPolicy Bypass -File tests/smoke.ps1   # PASS / FAIL / SKIP
```

### Install as a DSH skill (auto-loaded by agents)

Copy the extracted directory into the DSH skill folder, keeping the name
`lv2d-png-to-model`:

```powershell
robocopy . "$env:USERPROFILE\.dsh\skills\lv2d-png-to-model" /E
```

DSH hot-loads it; no restart. **No registry writes, no PATH changes** — uninstall
means deleting that directory.

### Command-line only

Skip the skill copy and run `python check_env.py` plus the scripts in `scripts/`
from the extracted folder.

> Versions before 1.4.0 have no release asset; they had to be cloned or taken as
> a source zip.


---

## Developer notes

Read this first if you are modifying the skill or running it in production.

### 0. Architecture in one line

```
illustration PNG ──See-through──▶ layered PSD ──PSD2Live──▶ moc3 + cmo3 ──▶ VTube Studio
                                                     ▲
                                                     └── MCP: scripted layer order, keyforms, export
```

**PSD2Live is the core, not an optional extra.** It turns a layered image into a
moving model: mesh, deformers, parameters, physics, motions. This repository
handles the environment, the layer audit, the MCP corrections, render
verification and packaging.

### 1. Three commands to a working setup

```powershell
python check_env.py --json                    # what is missing here
python install.py --yes
python install.py --verify-only --json        # expects "ok": true
powershell -ExecutionPolicy Bypass -File tests/smoke.ps1
```

Smoke test states:

| State | Meaning | Action |
| --- | --- | --- |
| PASS | component works | none |
| SKIP | missing or too old (e.g. Cubism 5.3 has no external API) | decide if you need it |
| FAIL | a required piece is broken | fix it; the script exits 1 |

### 2. Bind a model

```powershell
PSD2Live.exe --input character.psd --output out --lang zh --atlas 8192 --mesh-spacing 32
```

Both flags matter: `--atlas 8192` removes the rectangular seams the default 4096
leaves on faces, and `--mesh-spacing 32` keeps mouth and eye deformation from
going blocky.

### 3. Install into VTube Studio

Copy the whole `out` folder into
`...\VTube Studio_Data\StreamingAssets\Live2DModels\<model-name>\`.

Loading it pops two dialogs — **auto-configure this model?** and **create 15 VTS
parameters from Live2D defaults?** Both are normal. Nothing is broken, no
parameter was lost. Skipping them still loads the model but leaves hotkeys and
tracking partially unconfigured.

### 4. Five pitfalls worth an evening each

| Pitfall | Symptom | Cause | Fix |
| --- | --- | --- | --- |
| Wrong or hidden layer name | model cannot open its mouth / never blinks | binding maps by name | rename to the convention, unhide, re-export |
| VTS amplifies by default | mouth slams open, blink stutters | `Mouth Open` upper 2.1, `Eye Open` 1.9 | edit `vtube.json` (next section) |
| Re-export resets motions | tuned idle/blink gone | export regenerates them | back up the `.motion3.json`, copy back |
| Arms behind the shirt | sleeves invisible | arm draw order below torso | change `draw_order`, not the binding |
| Bad source art | torn / spiky mouth edges | e.g. a 14 px mouth stretched | redraw; mesh edits cannot help |

### 5. Tuning on the VTS side

`Live2DModels\<model>\<model>.vtube.json`

```jsonc
"ParameterSettings": [
  { "Input": "MouthOpen",    "OutputRangeLower": 0, "OutputRangeUpper": 0.85 }, // default 2.1
  { "Input": "EyeOpenLeft",  "OutputRangeUpper": 1.0 },                        // default 1.9
  { "Input": "EyeOpenRight", "OutputRangeUpper": 1.0 }
]
```

**Close VTS before editing** — it writes its in-memory settings back on exit.

### 6. Knowing whether a change actually landed

Render, do not trust exit codes:

```powershell
python scripts/psd2live_mcp.py render --out mouth.png --params ParamMouthOpenY=1.0
python scripts/psd2live_mcp.py render --out eyes.png  --params ParamEyeLOpen=0 ParamEyeROpen=0
```

If the new PNG has the **same sha256**, the edit did nothing. Several plausible
"fixes" in this repository were rejected exactly that way.

### 7. Bringing in Cubism

Open the `.cmo3` directly — never through *new / import PSD*, which produces a
shell project with empty deformers. Keep the `.cmo3` next to its `<name>.4096\`
texture folder, or textures go missing.

### 8. Limits

- **Does not draw.** Missing or misplaced layers are simply bound as given.
- **No binding quality guarantee.** Beyond ±20° head rotation the auto-bound face
  starts to deform.
- **Not a replacement for Cubism detail work.**
- **Cannot connect on 5.3 or older** — the external API starts at 5.4.

### 9. Requirements

Windows 10/11, Python ≥ 3.10, a layered PSD, PSD2Live 3.6.x (not bundled),
optionally Live2D Cubism Editor and VTube Studio.

---

## Next goal: Cubism 5.4 integration

**Status: waiting for a release (BLOCKED, not abandoned).**

### Why

The pipeline can *generate* models but cannot *edit* them inside Cubism — every
keyform or part change means clicking. With the 5.4 external-application API:

| Action | Now | After 5.4 |
| --- | --- | --- |
| read parameters / parts / deformers | inferred from renders | read the structure |
| change ranges, add/remove keys | only via the PSD2Live project | `EditParameter`, `AddParameterKey` |
| edit mesh vertices, reorder parts | not possible | `EditArtMesh`, `MoveObjectOnPartsPalette` |
| batch edits | one class at a time, re-export each time | `cubism_edit_batch` |
| export runtime files | GUI menu | **not in the API** (still manual or PSD2Live) |

### Why it cannot happen yet

1. The integration API exists only in **Cubism 5.4 alpha**; this machine runs
   5.3.02 and `ws://localhost:22033` does not exist.
2. Official notice: **alpha distribution and use ended 2026-10-18 23:59 JST**, and
   the alpha is time-locked — an installer would not run past that date.
3. The official update page still lists **5.3.00** as latest: no 5.4 beta, no
   stable.

Nothing about the plan is missing. What is missing is a runnable version.

### Adoption checklist (once a release exists)

```text
1. install Cubism 5.4+ (can coexist with 5.3)
2. open a model -> File -> external application integration -> enable "use"
   (enable "edit" as well to modify data)
3. verify: Test-NetConnection 127.0.0.1 -Port 22033
4. pip install cubism-mcp   (42 tools, MIT, python >= 3.10)
5. smoke.ps1 S5 must flip from SKIP to PASS
6. first real edit on a COPY of an existing model, never the deliverable
```

### While integrating

1. Every edit locks the Editor and asks for confirmation; the user can cancel and
   Editor rolls back through its history — callers must handle cancellation.
2. The API is alpha-tier; do not hardcode its response shapes.
3. No render feedback — visual verification stays mandatory.
4. Runtime export, physics/motion curves and material blending remain outside the
   API.

### Definition of done

- `tests/smoke.ps1` reports **PASS** for S5 (not SKIP);
- parameter tables read back identically to the project;
- a full loop "change one key → render → expected difference" works;
- cancellation rolls back cleanly and leaves the project intact.

Until then, `SKILL.md` keeps marking L3 as "needs 5.4+" and the smoke test keeps
reporting SKIP rather than FAIL.

---

## For AI agents

**If you are an LLM agent, read [AI_README.md](AI_README.md) first — that is the
installation and execution protocol.** Agent-facing content is layered:

| File | Content | When |
| --- | --- | --- |
| [SKILL.md](SKILL.md) | task routing, capability tiers, safety gates | every task |
| [AI_README.md](AI_README.md) | install protocol, deps, profiles, completion contract | first run / broken env |
| [workflows/](workflows/) | executable procedures: PSD2Live MCP, half-body rig, verify/rollback | while executing |

Key rules: ask before expensive inference or uploads; back up before editing a
model; never call an auto-generated binding "verified" without a rendered image;
keep failed versions instead of silently overwriting.

## Repository layout

```text
SKILL.md              agent entry point
AI_README.md          install and execution protocol
README.md             this file (developer notes + agent index)
README.en.md          English version
CHANGELOG.md
check_env.py          environment probe
install.py            dependency installer / verifier
config/pipeline.json  resource profiles
workflows/            ★ psd2live-mcp.md, ★ skill-routing.md,
                      auto-rig.md, verify-rollback.md
references/           ★ psd2live-ops.md, ★ model-defects.md, occlusion docs
scripts/              ★ psd2live_mcp.py, make_tk_workflow.py,
                      occlusion_psd_check.py
tests/                ★ smoke.ps1, test_occlusion_tools.py
src/                  rigkit builder, run_pipeline, integrations
```

`★` marks files added in 1.4.0.

## License

Source-available under a non-commercial license — [LICENSE](LICENSE).
Third-party components keep their own licenses — [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
PSD2Live itself is GPL-3.0 and is not distributed here.
