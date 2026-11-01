# Lv2D-png-to-model

An AI-oriented automation package that decomposes a single anime PNG/JPG illustration, produces layered PSD assets, and guides the workflow toward a bound Live2D model.

## Features

- Checks Python, required packages, CUDA, VRAM, disk space and file permissions.
- Selects a safe profile for low-VRAM, 8 GB, balanced or high-memory systems.
- Provides illustration variants, See-through normalization, half-body rigging, previews and VTube Studio installation.
- Routes full-body PSDs through PSD2Live for `.cmo3`, `.moc3`, `.model3.json` and `.vtube.json` output.
- Installation never uploads artwork or starts long-running inference.

## Quick installation

```text
python check_env.py --json
python install.py --yes
python install.py --verify-only --json
```

Optional local CUDA dependencies:

```text
python install.py --yes --with-local-gpu
```

AI agents should read [AI_README.md](AI_README.md) before installation.

## Invocation

```text
python src/run_pipeline.py doctor
python src/run_pipeline.py split <asset-dir> <layer-output-dir> --pad-top 90
python src/run_pipeline.py build <character.json>
python src/run_pipeline.py vts <character.json> --install
```

Inspect a full-body PSD before opening it in PSD2Live:

```text
python src/integrations/check_fullbody.py --psd <file.psd> --psd2live-root <path>
```

## Resource profiles

- No CUDA: prefer Hugging Face or ModelScope.
- 8 GB VRAM: use `cautious_8gb` with batch size 1, 1024 resolution and 20 steps.
- 12 GB or more: higher resolution and step counts are available.

See [config/pipeline.json](config/pipeline.json).

## Outputs

PNG, layered PSD, `.cmo3`, `.moc3`, `.model3.json`, `.physics3.json`, `.motion3.json`, `.vtube.json` and `.psd2live`.

## License

This project is source-available under a non-commercial license. See [LICENSE](LICENSE). Third-party components retain their original licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

