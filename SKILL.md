---
name: lv2d-png-to-model
description: 将单张 PNG/JPG 二次元立绘拆成可绑定的分层 PSD，优先检查帽子、衣领、头发、耳朵和脖子的遮挡顺序，并路由到 PSD2Live 或半身自动绑定流程。
metadata:
  display_name: Lv2D-png-to-model
---

# Lv2D PNG to Model

把单张动漫立绘转成可继续制作的分层资产。技能的重点是可追溯的分层和遮挡验收，不把 AI 输出直接当作成品。

## 先判断任务类型

- 帽子、衣领、头发、耳朵、脖子或隐藏面：先读 [遮挡工作流](references/occlusion-workflow.md)，再选拆层工具。
- 半身角色：使用内置 `src/rigkit` 走变体、拆分、网格、构建、预览和 VTS。
- 全身角色：See-through 只负责拆层；绑定和导出走 PSD2Live，不能用 `rigkit.prepare/build` 冒充可靠全身绑定。
- 只需快速面捕或动作预览：AutoLive2d 是预览工具，不是 Cubism/VTS 最终导出器。

## 项目路由

| 需求 | 首选 | 不应声称 |
|---|---|---|
| 动漫语义拆层 | See-through；已安装时可用 tk_seethrough | 深度顺序等于遮挡正确 |
| 缺层自动重跑 | tk_seethrough `auto_fill` | 自动重跑能修复衣领或帽檐几何 |
| 衣领/头发穿插 | PSD2Live `source_split_depth` | 复制图层后无需擦除前层 |
| 零样本遮挡排序 | CObL 仅作研究参考 | CObL 已在动漫拆图中验证 |
| 被遮挡区域补全 | 原 See-through 隐藏面、变体；RevealLayer 为可选实验 | 自动补全可以覆盖正面可见像素 |
| 可变层数生成 | Qwen-Image-Layered 为高资源可选路线 | 20B 模型可在 8 GB 显存直接运行 |

项目版本、许可证、真实参数和限制见 [项目核对](references/project-landscape.md)。

## 标准遮挡流程

```text
原图与授权
  -> See-through 首版拆层
  -> 深度与层序初检
  -> tk AutoFill（仅缺层/低相似度，需授权）
  -> 帽子与头发检查
  -> 衣领后层 / 脖子 / 前层
  -> 隐藏面补全
  -> PSD + Original 底垫
  -> 自动结构检查
  -> 人工动作验收
  -> 案例归档
```

强制顺序：

1. PSD2Live 或 PSD 中的衣领从下到上为 `Collar_Back`、`Neck`、`Collar_Front`。
2. 衣帽兜可使用 `Hood_Neck_Back`、`Neck`、`Hood_Neck_Front`。
3. 帽檐透视、帽墙包覆、后发是否穿帽，必须看原画，不由 AutoFill 决定。
4. 正面可见像素来自原画或 See-through 原层；生成只补原先不可见区域。
5. 保留失败版本，不用新结果静默覆盖旧工程。

## 工具与命令

- 安装和环境：先读 [AI_README.md](AI_README.md)；不要为读取本技能自动安装大型 GPU 依赖。
- 生成 tk_seethrough ComfyUI API 工作流：

```text
python scripts/make_tk_workflow.py --input-name hero.png --out hero-tk.json
```

默认 `auto_fill=false`。只有用户批准额外推理后加 `--auto-fill`。

- 检查 PSD 命名与顺序：

```text
python scripts/occlusion_psd_check.py hero.psd --mode full --require-original --json
```

- 半身流水线入口：`python src/run_pipeline.py <task> ...`。
- 全身 PSD2Live 预检：`python src/integrations/check_fullbody.py --psd <file.psd> --psd2live-root <path>`。

## 验收门

- 读取图片、上传外部服务或启动长时间 GPU 推理前取得用户许可。
- 左右手眼、前后发、帽子、耳朵、脖子、衣领、袖子、双腿、鞋底和配饰均已检查。
- 衣领夹层通过自动顺序检查，并能随转头显示正确脖子。
- 帽檐椭圆、头骨中轴、帽墙包覆和后发穿插通过人工检查。
- 自动检查只负责结构与顺序，不替代九头姿态和动作验收。
- 至少保留一个正样本和一个负样本；新失败案例写入独立目录。

## 详细资料

- [遮挡工作流](references/occlusion-workflow.md)
- [项目核对](references/project-landscape.md)
- [全身制作](references/全身制作.md)
- [自动流水线预案](references/自动流水线预案.md)
- [开源项目调研](references/开源项目调研.md)
- [图层清单](references/图层清单.md)
- [规则与失败分流](references/规则.md)
- [配置](references/配置说明.md)

