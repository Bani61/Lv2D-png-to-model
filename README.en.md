# Lv2D-png-to-model

Turn one illustration — or one already-layered PSD — into a Live2D model you can
actually load in VTube Studio. This package covers the whole path: decompose,
validate layer order, bind (full body through PSD2Live, half body through the
bundled builder), fix the bindings, and prove the result with rendered images.

Current version: **1.4.0**. Human-oriented docs are this file; agent-oriented
docs are [AI_README.md](AI_README.md) and [SKILL.md](SKILL.md). Release history:
[CHANGELOG.md](CHANGELOG.md).

If you are a person looking for "how do I get a working VTuber model", read the
next three sections and stop. If you are an agent, jump to
[AI_README.md](AI_README.md).

## What it can and cannot do

Can:

- split a single PNG/JPG into semantic layers (See-through, ComfyUI or the
  bundled provisional splitter),
- check that layer names, `Original` layer and occlusion order are sane before
  binding,
- bind a **full-body** PSD through PSD2Live and emit `.moc3`, `.cmo3`,
  `.model3.json`, `.physics3.json`, motions and expressions,
- bind a **half-body** character with the bundled `rigkit` builder,
- edit an existing project programmatically through the PSD2Live MCP endpoint
  (draw order, key forms, deformers, render checks, export),
- install the model into VTube Studio and tune the parameter ranges.

Cannot:

- repaint or repair art. A 14 px mouth stays a 14 px mouth.
- guess what a wrongly named or hidden layer was supposed to do.
- replace Cubism Editor for hand-drawn detail work.
- connect to Cubism Editor on 5.3.x — the external API only exists in 5.4+.

## Three entry points

| Situation | Entry |
| --- | --- |
| You have one flat PNG and nothing else | `python src/run_pipeline.py split ...` then bind |
| You already have a layered PSD | go straight to PSD2Live (UI, CLI or MCP) |
| Something is already bound but looks wrong | `references/model-defects.md` + the MCP recipes |

## 30-second start

```text
python check_env.py --json          # what is missing on this machine
python install.py --yes             # install required deps
python install.py --verify-only --json
powershell -ExecutionPolicy Bypass -File tests/smoke.ps1
```

Optional (needs CUDA, several GB):

```text
python install.py --yes --with-local-gpu
```

`check_env.py` writes a probe file inside the package directory. Under a
restricted sandbox it will spin forever — run it with normal file access.

## Full body: the PSD2Live path

```text
PSD2Live.exe --input character.psd --output out --lang zh --atlas 8192 --mesh-spacing 32
```

Or with the GUI, or through MCP (`http://127.0.0.1:23871/mcp`, token from the
Java prefs registry — see `workflows/psd2live-mcp.md`).

Output lands as `<psd-name>.moc3`, `.model3.json`, `.physics3.json`,
`.cmo3`, textures and four motions plus four expressions.

### Installing into VTube Studio

1. Put the whole output folder into
   `...\VTube Studio_Data\StreamingAssets\Live2DModels\<model-name>\`.
2. Start VTS → model list → pick it.
3. VTS asks **"auto-configure this model?"** — say yes, then yes again on
   *"create 15 parameters based on Live2D defaults"*.
   This dialog is normal. It is not a broken file, and nothing has been lost.

## Five things that will cost you an evening

1. **Layer names decide the binding.** The generator maps by name. A hidden or
   misnamed `mouth open` layer silently produces a model that cannot open its
   mouth. Nothing warns you.
2. **VTS amplifies by default.** Its auto-generated `Mouth Open` maps 0..1 to
   0..2.1 and `Eye Open` to 0..1.9, so every eyelid twitch looks like a slam.
   Fix it in `<model>.vtube.json`, **with VTS closed** (it rewrites that file
   on exit):

   ```jsonc
   {
     "ParameterSettings": [
       { "Input": "MouthOpen", "OutputRangeLower": 0.0, "OutputRangeUpper": 0.85 },
       { "Input": "EyeOpenLeft", "OutputRangeLower": 0.0, "OutputRangeUpper": 1.0 },
       { "Input": "EyeOpenRight", "OutputRangeLower": 0.0, "OutputRangeUpper": 1.0 }
     ]
   }
   ```

3. **Re-exporting resets your motions.** Idle and blink go back to generated
   defaults. Keep your tuned `.motion3.json` copies and put them back.
4. **Arms behind the shirt is a layer-order bug, not physics.** In the PSD the
   arm layers can sit below the torso. Either move them in Photoshop, or set
   `draw_order` 165/166 over the torso's 160 after import.
5. **Art problems survive automation.** Torn mouth edges came from a 14 px
   open-mouth drawing being stretched; the fix was a better drawing, not a
   better mesh.

## Checking the result

Bindings are not "done" because the command succeeded. Render and look:

```text
python scripts/psd2live_mcp.py render --out mouth_open.png --params ParamMouthOpenY=1.0
python scripts/psd2live_mcp.py render --out eyes_closed.png --params ParamEyeLOpen=0 ParamEyeROpen=0
python scripts/psd2live_mcp.py render --out angle45.png --params ParamAngleX=45
```

If the render is byte-identical to the previous one, your edit did nothing —
that is how several plausible "fixes" were caught here.

## Repository layout

```text
AI_README.md            agent entry point
SKILL.md                skill definition, capability tiers
README.md               this file
README.en.md            English version
CHANGELOG.md
check_env.py            environment probe
install.py              dependency installer / verifier
config/pipeline.json    resource profiles, active profile
workflows/              ★ psd2live-mcp.md, ★ skill-routing.md
references/             ★ psd2live-ops.md, ★ model-defects.md,
                        occlusion-workflow.md, project-landscape.md, prompts
scripts/                ★ psd2live_mcp.py, make_tk_workflow.py,
                        occlusion_psd_check.py
tests/                  ★ smoke.ps1, test_occlusion_tools.py
src/                    rigkit builder, run_pipeline, integrations
```

`★` marks files added in 1.4.0.

## License

Source-available under a non-commercial license — see [LICENSE](LICENSE).
Third-party components keep their own licenses — see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). PSD2Live is GPL-3.0 and is
installed separately by you.
