---
name: lv2d-png-to-model
description: 把单张 PNG/JPG 立绘或分层 PSD 做成可在 VTube Studio 直播的 Live2D 模型：拆层、PSD 结构检查、PSD2Live 自动绑定与导出、通过 MCP 程序化修绘制顺序/关键帧/网格、渲染验证与缺陷排查。
metadata:
  display_name: Lv2D-png-to-model
  version: 1.4.0
---

# Lv2D PNG to Model

把一张立绘，做成一具能直播的皮套。

核心链路：**立绘 → 分层 PSD → 自动绑定 → moc3 → VTube Studio**。本技能的重点是：能力分级清楚、每步可验证、出错能定位到具体图层。

## 先判断任务类型

- 只有一张 PNG/JPG → 先拆层（See-through 或 tk_seethrough），再走绑定。
- 已经有分层 PSD → 直接进绑定。**先跑结构检查**：`python scripts/occlusion_psd_check.py <psd> --mode full --require-original --json`。
- 半身、小角度转头 → 内置 `src/rigkit`。
- 全身、要物理和动作 → **PSD2Live**（见 [PSD2Live MCP](workflows/psd2live-mcp.md)）。
- 只是快速预览 → AutoLive2d 足够，但它不是最终导出器。
- 用户报"动起来怪" → 直接看 [缺陷目录](references/model-defects.md)，通常三分钟能定位。

## 能力分级

按你能用到的工具分层，别越级承诺：

| 层 | 能力 | 需要什么 | 能保证什么 |
| --- | --- | --- | --- |
| L0 | 结构检查、命名规范检查 | Python + psd-tools | 图层齐全、命名正确 |
| L1 | 命令行一次性绑定导出 | PSD2Live.exe | moc3/cmo3/物理/动作，质量看自动绑定 |
| L2 | MCP 程序化修改（绘制顺序、关键帧、网格） | PSD2Live 运行 + 令牌 | 可定向修复单个缺陷，结果可渲染验证 |
| L3 | 引擎内精修 | Cubism Editor 手工 / 5.4+ 外部 API | 任意精修；MCP 路径仅 5.4 alpha+ |
| L4 | 全自动流水线 | L2 + 自动化脚本 | 可复现，但每次仍需人工验收渲染 |

**5.3.x 的 Cubism 没有外部 API**（端口 22033 不通），L3 的自动化路径在本机不可用；这不影响 L1/L2。

## 项目路由

| 需求 | 首选 | 不应声称 |
|---|---|---|
| 动漫语义拆层 | See-through；已安装时可用 tk_seethrough | 深度顺序等于遮挡正确 |
| 缺层自动重跑 | tk_seethrough `auto_fill` | 自动重跑能修复衣领或帽檐几何 |
| 衣领/头发穿插 | PSD2Live `source_split_depth` | 复制图层后无需擦除前层 |
| 零样本遮挡排序 | CObL 仅作研究参考 | CObL 已在动漫拆图中验证 |
| 被遮挡区域补全 | 原 See-through 隐藏面、变体；RevealLayer 为可选实验 | 自动补全可以覆盖正面可见像素 |
| 可变层数生成 | Qwen-Image-Layered 为高资源可选路线 | 20B 模型可在 8 GB 显存直接运行 |

## 标准流程

```text
立绘 / PSD
  -> 结构检查（命名、左右、前后、遮挡）
  -> [需要时] 拆层
  -> PSD2Live 自动绑定（CLI 或 GUI）
  -> 渲染核对（正面 / 转头 / 闭眼 / 张嘴）
  -> 用 MCP 修不达标的具体部位
  -> 重新导出 + 再核对
  -> 发布（model3/textures/physics/motions 全套）
  -> 装进 VTS 并调整运行期参数
```

强制规则：

1. **每次导出后必须渲染看图**，不看图不算完成。
2. **改动前备份上一版模型目录**，改动后保留旧版。
3. 每次只改一类东西（层序 / 关键帧 / 网格），改完立刻验证——否则出问题分不清是谁造成的。
4. 用哈希确认结果真的变了：两次渲染 PNG 的 sha256 相同 = 你的修改没生效。

## 常用命令

```text
# 环境
python check_env.py --json
python install.py --yes
python install.py --verify-only --json

# PSD 结构检查
python scripts/occlusion_psd_check.py hero.psd --mode full --require-original --json

# 一次性绑定导出
PSD2Live.exe --input hero.psd --output out --lang zh --atlas 8192 --mesh-spacing 32

# MCP 驱动（PSD2Live 运行中）
python scripts/psd2live_mcp.py list
python scripts/psd2live_mcp.py inspect --scope objects --query Mouth
python scripts/psd2live_mcp.py render --out check.png --params '{"ParamMouthOpenY":1.0}'

# 冒烟
powershell -File tests/smoke.ps1
```

## 验收门

- 左右手眼、前后发、帽子、耳朵、脖子、衣领、袖子、双腿、鞋底和配饰均已检查。
- 衣领夹层通过自动顺序检查，并能随转头显示正确脖子。
- 帽檐椭圆、头骨中轴、帽墙包覆和后发穿插通过人工检查。
- 自动检查只负责结构与顺序，不替代姿态和动作验收。
- 至少保留一个正样本和一个负样本；新失败案例写入独立目录。
- 渲染核对覆盖四个状态：正面、±20° 转头、闭眼、张嘴。

## 详细资料

- [PSD2Live MCP 玩法](workflows/psd2live-mcp.md) — 程序化绑定、改层序、改关键帧、导出
- [技能选型](workflows/skill-routing.md) — 手上有立绘 / PSD / 已有模型时分别走哪条
- [缺陷目录](references/model-defects.md) — 七个常见缺陷的根因与修法
- [操作速查](references/psd2live-ops.md) — 28 个工具与 180+ 操作的参数形状
- [半身自动绑定](workflows/auto-rig.md)
- [验收与回滚](workflows/verify-rollback.md)
- [遮挡工作流](references/occlusion-workflow.md)
- [项目核对](references/project-landscape.md)
- [全身制作](references/全身制作.md)
- [图层清单](references/图层清单.md)
- [规则与失败分流](references/规则.md)
