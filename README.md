# Lv2D-png-to-model

将单张 PNG/JPG 二次元立绘通过 AI 拆层、生成分层 PSD，并引导绑定为 Live2D 模型的自动化技能包。

当前版本：`1.1.0`。版本变更见 [CHANGELOG.md](CHANGELOG.md)。

## 功能

- 自动检查 Python、核心依赖、CUDA、显存、磁盘和文件权限。
- 根据显卡情况选择低显存、8 GB 谨慎、均衡或高质量配置。
- 提供立绘变体、See-through 拆层、PSD 组件整理、半身自动绑定、预览和 VTube Studio 安装代码。
- 全身路线使用 See-through 生成 PSD，再通过 PSD2Live 生成 `.cmo3`、`.moc3`、`.model3.json` 和 `.vtube.json`。
- 提供遮挡专项流程，检查帽子、衣领、头发、耳朵和脖子的前后关系。
- 安装过程不会自动上传立绘，也不会自动启动耗时推理。

## 快速安装

```text
python check_env.py --json
python install.py --yes
python install.py --verify-only --json
```

需要本机 CUDA 拆层时：

```text
python install.py --yes --with-local-gpu
```

AI 代理安装前应优先阅读 [AI_README.md](AI_README.md)。

## 调用方式

进入项目根目录并读取 `skill_manifest.json` 后，可运行：

```text
python src/run_pipeline.py doctor
python src/run_pipeline.py split <素材目录> <图层输出目录> --pad-top 90
python src/run_pipeline.py build <character.json>
python src/run_pipeline.py vts <character.json> --install
```

全身 PSD 在进入 PSD2Live 前运行：

```text
python src/integrations/check_fullbody.py --psd <file.psd> --psd2live-root <path>
```

生成 tk_seethrough 的 ComfyUI API 工作流：

```text
python scripts/make_tk_workflow.py --input-name hero.png --out hero-tk.json
```

检查分层 PSD：

```text
python scripts/occlusion_psd_check.py hero.psd --mode full --require-original --json
```

遮挡项目的版本、许可和能力边界见 [项目核对](references/project-landscape.md)，
执行步骤见 [遮挡工作流](references/occlusion-workflow.md)。

## 资源档位

- 无 CUDA：优先使用 Hugging Face 或 ModelScope 云端拆层。
- 8 GB 显存：使用 `cautious_8gb`，默认批大小 1、1024 分辨率、20 步，并关闭不稳定的 group offload。
- 12 GB 及以上：可使用更高分辨率与步数。

具体参数保存在 [config/pipeline.json](config/pipeline.json)。

## 输出

支持 PNG、分层 PSD、`.cmo3`、`.moc3`、`.model3.json`、`.physics3.json`、`.motion3.json`、`.vtube.json` 和 `.psd2live`。

最终交付前必须检查左右手眼、前后发、双腿、鞋底、脚踝、袖口、衣物和挂件所有权。

## 许可证

本项目采用禁止商用许可证，详见 [LICENSE](LICENSE)。第三方代码和依赖保留各自原许可证，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

