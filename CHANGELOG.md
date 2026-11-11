# Changelog

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
