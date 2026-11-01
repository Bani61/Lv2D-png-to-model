---
name: lv2d-png-to-model
description: 这是一个将单张 PNG/JPG 二次元立绘，通过 AI 自动拆层、生成 PSD，并引导绑定为 Live2D 模型的自动化技能包。支持 8GB 显存环境的自适应环境检查和依赖安装。
metadata:
  display_name: Lv2D-png-to-model
---

# Lv2D PNG to Model

Read [AI_README.md](AI_README.md) before installation. It contains the environment protocol, dependency tree, install commands, resource profiles, and completion contract.

## 调用方式

1. 解压 `Lv2D-png-to-model.zip`，进入包含 `AI_README.md` 的目录。
2. 运行 `python check_env.py --json`，读取 Python、依赖、CUDA、显存、写权限和推荐资源档位。
3. 运行 `python install.py --yes` 安装核心依赖并写入 `config/pipeline.json`。
4. 需要本机拆层时，再运行 `python install.py --yes --with-local-gpu`。
5. 运行 `python install.py --verify-only --json` 完成验证。
6. 读取 `skill_manifest.json` 获取输入输出格式和入口；源码命令使用 `python src/run_pipeline.py <task> ...`。

## Route by target

- For a half-body avatar, use the bundled `src/rigkit` modules for variants, decomposition, mesh estimation, build, preview, and VTube Studio installation.
- For a full-body avatar, use See-through for decomposition and PSD2Live for binding/export. Never claim that `rigkit.prepare/build` produced a reliable full-body rig.
- Use AutoLive2d only for rapid preview or face-tracking experiments; it is not a Cubism/VTube Studio final exporter.
- Use Bunraku as a research reference only until a public implementation and checkpoint are available.

## Required quality gates

- Obtain user consent before uploading illustration data or starting long local GPU inference.
- Verify left/right ownership, layer order, hidden-area completion, arms, hands, legs, feet, soles, clothing, and accessories.
- For full-body work, require independent ownership of hips, knees, ankles, shoes, sleeves and garment panels.
- Inspect nine head poses, body extremes, arm raises, knee bends, foot anchors, hair physics and clothing physics before delivery.
- Preserve old failed versions; never overwrite them silently.

## Detailed references

- [Full-body workflow](references/全身制作.md)
- [Automated full-body plan](references/自动流水线预案.md)
- [Open-source project research](references/开源项目调研.md)
- [Layer checklist](references/图层清单.md)
- [Rules and failure routing](references/规则.md)
- [Configuration](references/配置说明.md)

## Code entry points

- `src/rigkit`: bundled provisional decomposition, half-body rig generation, preview, `.moc3` output and VTS installation.
- `src/run_pipeline.py`: module dispatcher for `rigkit` commands.
- `src/integrations/check_fullbody.py`: full-body PSD checks and PSD2Live discovery.
- `check_env.py` and `install.py`: installation and environment verification.

