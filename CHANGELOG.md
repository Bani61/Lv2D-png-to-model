# Changelog

## 1.4.0 - 2026-11-15

Runtime-proven release. Everything below was executed end to end on a real
character (blue-hair hoodie, 765×1536 PSD) and verified by rendered images,
not by reading code.

### Changed — licensing

- `LICENSE` is now the **PolyForm Noncommercial License 1.0.0**
  (https://polyformproject.org/licenses/noncommercial/1.0.0), copyright
  holder **Bani61**, carrying the `Required Notice:` line at the top so it
  travels with every copy. `skill_manifest.json` reports the same license.

### Added

- `references/psd2live-ops.md` — PSD2Live 3.6.7 MCP contract: 28 tools, the
  `request` / `op` / `workspace_call` wrapping rules, target id shapes
  (`mesh:ArtMeshHandwearL`, `warp:DeformEyes`), request bodies for
  `rig_edit_structure`, `keyform_apply`, `rig_deform`, the three mesh
  operations and their real limits, state/concurrency rules, error lookup.
- `references/model-defects.md` — nine defect signatures seen in practice
  (model never opens its mouth, torn mouth edges, visible eye-white when
  closed, "one pixel of input = fully open", stuttering blink, arms behind
  the shirt, "parameters lost" on load, red vertical streak, broken large
  head angles). Each entry has symptom, root cause, verification command and
  the fix that actually worked, plus the attempts that did **not**.
- `workflows/psd2live-mcp.md` — operational runbook: start the server, get
  the real bearer token from the Java prefs registry (the value shown in the
  GUI is a mask and returns 401), import → inspect → edit → render → export.
- `workflows/skill-routing.md` — when to use this skill versus
  `live2d-halfbody` or `live2d-pipeline`, and the single deciding question:
  "do you already have a layered PSD?"
- `scripts/psd2live_mcp.py` — dependency-light CLI over the MCP endpoint:
  `list`, `inspect`, `import`, `draw-order`, `keyform`, `render`, `export`,
  with token auto-discovery (argument → env → registry).
- `tests/smoke.ps1` — executable acceptance test (S1–S7) printing
  PASS/FAIL/SKIP, writing `smoke-<stamp>.json`, exiting non-zero only on
  FAIL. Cubism without the 5.4+ integration API reports SKIP, not FAIL.
- `README.en.md` — English counterpart of the human-facing README.
- `SKILL.md` capability tiers L0–L4, so an agent can tell "doable with what
  is installed" from "needs a tool that does not exist here".

### Changed

- `README.md` / `README.en.md` rewritten as a **product manual** for people who
  make VTuber models (not for repo developers): feature table with per-feature
  dependencies and status, system requirements with the five GPU profiles,
  install, quick start, output file reference, workflow, VTS tuning, FAQ,
  layout, license.
- New **known-issues list** (8 items) replaces the previous roadmap phrasing:
  Cubism 5.4 integration not started, closed-eye binding flawed, auto-split
  mouth binds poorly, VTS default ranges too wide, re-export resets motions,
  arms hidden behind the shirt, slow local CUDA on 8 GB, deformation beyond
  ±20° head turn. Each row carries impact, status and a workaround.
- The roadmap wording ("下一个目标") is gone; 5.4 appears only as issue #1 with
  the facts that block it.
- Distribution: from 1.4.0 on every version publishes a built
  `Lv2D-png-to-model-<version>.zip` on GitHub Releases. `README.md` /
  `README.en.md` gained an install section (download → extract → three commands,
  optional `robocopy` into `%USERPROFILE%\.dsh\skills\lv2d-png-to-model`).
- `README.md`/`README.en.md`: the human section is now **开发者必读 / Developer
  notes** — architecture line, three commands, smoke-test state table, binding,
  VTS install, five pitfalls as a symptom→cause→fix table, tuning, render-diff
  verification rule, Cubism caveats, limits, requirements.
- `README.md`/`README.en.md`: new roadmap section **下一个目标：接入 Cubism 5.4**
  — why the API matters, the three verified facts that block it today (alpha
  ended 2026-10-18 23:59 JST and is time-locked; 5.3.00 still latest), a
  6-step adoption checklist, four cautions and a definition of done.
- `README.md` rewritten for humans: three entry points, 30-second start,
  the VTube Studio "auto-configure / 15 default parameters" dialog explained,
  five pitfalls that cost the most time, and an explicit "what this cannot do".
- `AI_README.md` rewritten for agents: reading order, three verified
  environment facts, dependency tiers, three execution paths, mandatory
  render verification, and a two-part completion contract.
- Layer naming is now documented as the single most important input: the
  binding generator maps by name, so a hidden or misnamed `嘴张开` silently
  produces a model that cannot open its mouth.

### Fixed (documented as recipe, reproducible)

- Mouth tearing: the open-mouth art was 14 px wide and got stretched into
  two dark wedges. Cropping a properly drawn open mouth (29×21) to the mouth
  ROI and naming it `mouth_open` removed the artefact entirely.
- Closed-eye eye-white bleed: shrinking the eye-white / iris meshes to 0.12
  on the closed keyform hides it. `keyform_apply` with
  `channels.opacity` silently no-ops — use geometry or `rig_edit_structure`.
- Arms hidden behind the shirt: draw order was 140/150/160
  (Arm_R / Arm_L / Topwear_Body). Moving the arms to 165/166 fixed it without
  touching the PSD.
- "Parameters lost" after import is not a broken file: it is VTube Studio's
  first-load auto-configure wizard.

### Validation

- `tests/smoke.ps1`: 7 PASS / 0 FAIL / 1 SKIP on the reference machine
  (Cubism 5.3.02, no external API).
- Full pipeline reproduced three times with byte-identical renders when
  nothing changed, which is how the ineffective fixes were identified.
- Published models v0.5 → v0.7; v0.7 has clean mouth deformation at
  `ParamMouthOpenY` = 0.5 and 1.0.

## 1.1.0 - 2026-11-11

### Added

- Added an occlusion-first routing workflow for hats, collars, hair, ears and neck layers.
- Added `scripts/make_tk_workflow.py` for tk_seethrough AutoFill workflows with an Original base layer.
- Added `scripts/occlusion_psd_check.py` for PSD layer naming, Original and front/back collar validation.
- Added project research and machine-readable verification records for See-through, tk_seethrough, PSD2Live, CObL, RevealLayer and Qwen-Image-Layered.
- Added six regression tests covering workflow generation and collar ordering.

### Changed

- Clarified that tk_seethrough AutoFill repairs missing or low-similarity layers and is not an occlusion-order judge.
- Updated full-body routing to use PSD2Live `source_split_depth` for front/back layers around a neck mesh.
- Documented verified project versions, licenses, model requirements and limitations.

### Validation

- `quick_validate.py` reports `Skill is valid!`.
- `tests/test_occlusion_tools.py` passes all six tests.
- The current installed skill matches the repository copy byte-for-byte for packaged files.
