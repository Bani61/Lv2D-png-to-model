# Lv2D-png-to-model

把一张立绘做成能在 VTube Studio 里直播的 Live2D 模型。

三个入口，按你手上有什么选：

| 你手上的东西 | 走哪条 | 产出 |
| --- | --- | --- |
| 只有一张 PNG/JPG 立绘 | See-through 拆层 → PSD2Live 绑定 | 分层 PSD + 可动模型 |
| 已经分好层的 PSD | PSD2Live 直接绑定 | `.moc3` / `.cmo3` / 物理 / 动作 |
| 想做半身、要精修绑定 | 内置 `rigkit` 半身流水线 | 网格 + 变形器 + VTS 包 |

当前版本：`1.4.0`。变更见 [CHANGELOG.md](CHANGELOG.md)。
路线图见 [下一个目标：接入 Cubism 5.4](#下一个目标接入-cubism-54)。

---

## 开发者必读

这一节是给你（改这个仓库、或拿它做生产的人）的。按顺序看，不要跳。

### 0. 一句话架构

```
立绘 PNG ──See-through──▶ 分层 PSD ──PSD2Live──▶ moc3 + cmo3 ──▶ VTube Studio
                                        ▲
                                        └── MCP 接口：程序化改层序/键值/导出
```

**PSD2Live 是核心，不是可选件。** 它负责把"分层图"变成"会动的模型"——网格、变形器、参数、物理、动作，全是它生成的。这个仓库负责的是：装环境、检查图层、通过 MCP 修正它做错的地方、渲染验收、打包交付。

### 1. 三步跑通

```powershell
# 第一步：自检（会告诉你缺什么、显卡够不够、能不能写文件）
python check_env.py --json

# 第二步：装依赖（只装必需项；不需要 CUDA 就走 cloud_only 档）
python install.py --yes
python install.py --verify-only --json        # 期望 "ok": true

# 第三步：跑冒烟测试（这一条能提前发现 90% 的环境问题）
powershell -ExecutionPolicy Bypass -File tests/smoke.ps1
```

冒烟测试输出 `PASS / FAIL / SKIP` 三态：

| 状态 | 含义 | 要不要管 |
| --- | --- | --- |
| PASS | 该组件可用 | 不用 |
| SKIP | 组件不存在或版本不够（如 Cubism 5.3 无外部 API） | 看你需不需要那功能 |
| FAIL | 必需项坏了 | 必须修，脚本会退出 1 |

### 2. 绑一个模型

```powershell
PSD2Live.exe --input character.psd --output out --lang zh --atlas 8192 --mesh-spacing 32
```

两个参数不是随便写的：

- `--atlas 8192`：默认 4096 在脸上会出现**矩形接缝**，8192 就没有了；
- `--mesh-spacing 32`：默认 64 的网格太粗，嘴和眼睛的形变会走样。

产物里你要用到的：

```
out\character.moc3            ← VTS 加载这个
out\character.model3.json     ← 配置清单
out\character.physics3.json   ← 物理摆动
out\character.cmo3            ← 想精修时在 Cubism 打开
out\character.4096\texture_00..0N.png
out\character.idle|nod|shake|blink.motion3.json
```

### 3. 装进 VTube Studio

把整个 `out` 目录复制到：

```
<Steam>\steamapps\common\VTube Studio\VTube Studio_Data\StreamingAssets\Live2DModels\<模型名>\
```

VTS 里加载后**会连着弹两个框**：

1. 「为模型进行自动配置？」→ 点「自动配置」
2. 「创建 15 个基于 Live2D 默认参数名和值的 VTS 参数」→ 点「确定」

**这是正常流程，不是文件坏了、不是参数丢失。** 它做的事是把模型的 Live2D 参数映射到 VTS 的内部参数。跳过也能用，但热键和面捕会缺一部分。

### 4. 五个会让你白干一晚的坑

| 坑 | 症状 | 根因 | 怎么修 |
| --- | --- | --- | --- |
| 图层名不对 / 图层被隐藏 | 模型张不开嘴、眼睛不眨 | PSD2Live 按名字认职责 | 改名成约定名 + 取消隐藏，重新导出 |
| VTS 默认参数太猛 | 嘴一张就全开、眨眼一跳一跳 | `Mouth Open` 上限 2.1、`Eye Open` 1.9 | 改 `vtube.json`（见下节） |
| 重新导出覆盖动作 | 调好的 idle/blink 没了 | 导出会重新生成动作 | 备份 `.motion3.json`，导出后覆盖回去 |
| 手臂被衣服盖住 | 袖子看不见 | PSD 里 `Arm_L/R` 的绘制顺序在下 | 改 `draw_order`，不是改绑定 |
| 美术本身有问题 | 嘴边缘有尖角、拉丝 | 比如嘴图只有 14 px | 换一张画对的图，改网格无解 |

### 5. 调参（VTS 侧）

配置文件：`Live2DModels\<模型名>\<模型名>.vtube.json`

```jsonc
"ParameterSettings": [
  { "Input": "MouthOpen",    "OutputRangeLower": 0, "OutputRangeUpper": 0.85 }, // 默认 2.1
  { "Input": "EyeOpenLeft",  "OutputRangeUpper": 1.0 },                        // 默认 1.9
  { "Input": "EyeOpenRight", "OutputRangeUpper": 1.0 }
]
```

**改之前必须先退出 VTS**——它退出时会把自己内存里的设置写回这个文件，你在运行中改的会被覆盖。

### 6. 判断"改完了没有"

改完必须渲染，不能靠"命令返回成功"下结论：

```powershell
python scripts/psd2live_mcp.py render --out mouth.png --params ParamMouthOpenY=1.0
python scripts/psd2live_mcp.py render --out eyes.png  --params ParamEyeLOpen=0 ParamEyeROpen=0
```

如果新渲染图和上一张的 **sha256 完全一样**，说明你那步改动根本没生效——这个仓库里好几个"看起来有道理的修法"就是这么被否掉的。

### 7. 精修（Cubism 侧）

`.cmo3` 可以直接在 Cubism Editor 打开，参数和键值都在。注意两点：

- 打开 `.cmo3`，**不要**走「新建 / 导入 PSD」——那会得到只有空壳变形器的工程；
- `.cmo3` 必须和旁边的 `<名字>.4096\` 贴图目录待在一起，单独拿出来会丢贴图。

### 8. 能力边界

- **不画画**：缺层、画错位置，它只会照着你给的东西绑；
- **不保证绑定质量**：8 方向转头超过 ±20° 后，自动绑定的脸会开始变形；
- **不替代 Cubism 精修**：需要手绘级别的细节时，还是要进 Editor；
- **5.3 及以下连不上**：Cubism 的外部 API 只有 5.4+ 才有。

### 9. 环境要求

- Windows 10/11
- Python ≥ 3.10
- 分层 PSD（整幅画布，图层名按约定）
- PSD2Live 3.6.x（不随仓库分发）
- 可选：Live2D Cubism Editor（精修）、VTube Studio（直播）

---

## 下一个目标：接入 Cubism 5.4

**当前状态：等待版发布（BLOCKED，不是放弃）。**

### 为什么要接

现在这条流水线能"生成"模型，但**改不了 Cubism 里的东西**——改一个键值、挪一个部件，都得靠人工点菜单。接入 5.4 的外部应用程序集成 API 之后，这些变成代码可控：

| 动作 | 现在 | 接入后 |
| --- | --- | --- |
| 读参数 / 部件树 / 变形器树 | 靠渲染图反推 | 直接读结构 |
| 改参数范围、加减键值 | 只能通过 PSD2Live 工程 | `EditParameter` / `AddParameterKey` |
| 改网格顶点、重排部件 | 做不到 | `EditArtMesh` / `MoveObjectOnPartsPalette` |
| 批量改动 | 一次一类、反复导出 | `cubism_edit_batch` |
| 导出运行时文件 | GUI 菜单 | **不在 API 内**（仍要手动或走 PSD2Live） |

### 为什么现在做不了

查证过的三个事实：

1. Cubism 的外部应用程序集成 API 只存在于 **5.4 alpha**，本机是 5.3.02，`ws://localhost:22033` 端口不存在；
2. 官方公告：**alpha 版本的提供与下载已于日本时间 2026 年 10 月 18 日 23:59 结束**，且 alpha 本身带时间锁，超期后即使有安装包也无法运行；
3. 官网更新页目前最新仍是 **5.3.00**，没有 5.4 beta、没有 5.4 正式版。

所以这一项目前无法推进，不是缺技术方案，是缺一个能跑的版本。

### 接入条件（等版发布后照这个顺序做）

```text
① 装 Cubism 5.4+（可与 5.3 并存安装，不影响现有工程）
② 打开模型 → 文件 → 外部应用程序集成的设置 → 勾「使用」
   （要改数据，还要再勾「编辑」）
③ 验证端口：Test-NetConnection 127.0.0.1 -Port 22033
④ pip install cubism-mcp   （42 个工具，MIT，python ≥ 3.10）
⑤ 冒烟测试 S5 应从 SKIP 变 PASS
⑥ 拿现有模型的**副本**做第一次真编辑，不要动成品
```

### 接入时要注意的四件事

1. **每次编辑会锁住 Editor 并弹确认框**，用户可以点取消，Editor 会用历史记录回滚——调用方必须能处理"被取消"这个分支；
2. **API 是 alpha 级**，字段和行为可能变，别把它的返回结构写死；
3. **没有渲染反馈**，改完仍然要靠截图或渲染图核对（这条规则不会因为接了 API 而取消）；
4. **导出运行时文件、物理/动作曲线、材质混合不在 API 范围**——这三块仍然要手动或走 PSD2Live。

### 判断标准

接完算成功，要同时满足：

- `tests/smoke.ps1` 的 S5 为 **PASS**（不是 SKIP）；
- 能读回参数表并与原工程一致；
- 能做一次"改一个键值 → 渲染 → 差值符合预期"的闭环；
- 被用户取消时能正确回滚且不损坏工程。

在此之前，`SKILL.md` 里的 L3 能力（Cubism 程序化编辑）保持"需要 5.4+"的标注，冒烟测试保持 SKIP 而不是 FAIL。

---

## 第二部分 · 给 AI agent

**如果你是 LLM agent，先读 [AI_README.md](AI_README.md)，那是安装与执行协议。** 本仓库对 agent 的内容分三层：

| 文件 | 内容 | 什么时候读 |
| --- | --- | --- |
| [SKILL.md](SKILL.md) | 技能主入口：任务路由、能力分级、安全门 | 每次接手任务 |
| [AI_README.md](AI_README.md) | 安装协议、依赖树、资源档位、完成契约 | 首次安装 / 环境异常 |
| [workflows/](workflows/) | 可执行流程：PSD2Live MCP、半身 rigkit、验证回滚、技能路由 | 执行具体步骤 |

关键约定（摘要）：

- 所有耗时推理、上传、外部服务调用都要先取得用户许可；
- 模型文件改动前先备份，改完必须能回滚；
- 不能把"自动生成的绑定"当成已验证的成品，必须渲染出图核对；
- 失败的版本单独留存，不静默覆盖。

### 目录结构

```
├─ SKILL.md                  技能入口（agent）
├─ AI_README.md              安装与执行协议（agent）
├─ README.md                 本文件（开发者必读 + agent 索引）
├─ check_env.py              环境自检
├─ install.py                依赖安装
├─ config/pipeline.json      资源档位
├─ src/rigkit/               半身绑定引擎
├─ src/integrations/         全身预检
├─ scripts/
│   ├─ psd2live_mcp.py       ★ PSD2Live MCP 客户端
│   ├─ make_tk_workflow.py   ComfyUI 工作流生成
│   └─ occlusion_psd_check.py PSD 结构检查
├─ workflows/
│   ├─ psd2live-mcp.md       ★ 程序化绑定与导出的完整玩法
│   ├─ skill-routing.md      三个技能的选型表
│   ├─ auto-rig.md           半身自动绑定
│   └─ verify-rollback.md    验收与回滚
├─ references/
│   ├─ psd2live-ops.md       ★ 28 个工具 / 180+ 操作的参数速查
│   ├─ model-defects.md      ★ 已知缺陷目录与修法
│   ├─ occlusion-workflow.md 遮挡专项
│   └─ ...
└─ tests/smoke.ps1           冒烟测试（可执行）
```

★ = 1.4.0 新增。

## 许可证

本项目采用禁止商用许可证，详见 [LICENSE](LICENSE)。第三方代码和依赖保留各自原许可证，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。PSD2Live 本体为 GPL-3.0，不随本仓库分发。
