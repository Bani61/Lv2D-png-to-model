# Lv2D-png-to-model

把一张立绘做成能在 VTube Studio 里直播的 Live2D 模型。

三个入口，按你手上有什么选：

| 你手上的东西 | 走哪条 | 产出 |
| --- | --- | --- |
| 只有一张 PNG/JPG 立绘 | See-through 拆层 → PSD2Live 绑定 | 分层 PSD + 可动模型 |
| 已经分好层的 PSD | PSD2Live 直接绑定 | `.moc3` / `.cmo3` / 物理 / 动作 |
| 想做半身、要精修绑定 | 内置 `rigkit` 半身流水线 | 网格 + 变形器 + VTS 包 |

当前版本：`1.4.0`。变更见 [CHANGELOG.md](CHANGELOG.md)。

---

## 第一部分 · 给人类

### 它是什么

一个把所有"手工在 Cubism Editor 里拖点"的工作自动化的工具包。核心是 **PSD2Live**：喂给它一个分层 PSD，它自动生成网格、变形器、参数键值、物理摆动，导出能在 VTube Studio 里直接加载的 `.moc3`。

这个仓库包含了三样东西：

1. **环境自检与安装**（`check_env.py` / `install.py`）——按你的显卡自动选档位，不装多余的东西；
2. **半身 rigkit**（`src/rigkit`）——纯代码的半身自动绑定，适合做小角度转头的皮套；
3. **PSD2Live 自动化层**（`scripts/psd2live_mcp.py` + `workflows/`）——通过 MCP 接口程序化地改图层、改绘制顺序、改关键帧、导出，不用手点菜单。

### 30 秒上手（全身，最常用）

```powershell
# 1. 自检
python check_env.py --json

# 2. 装依赖（只装必需项，几百 MB）
python install.py --yes
python install.py --verify-only --json      # 期望 "ok": true

# 3. 把 PSD 直接丢给 PSD2Live 命令行
PSD2Live.exe --input v0.1.psd --output out --lang zh --atlas 8192 --mesh-spacing 32
```

产物：

```
out\v0.1.moc3            ← VTube Studio 用这个
out\v0.1.model3.json     ← 配置清单（Moc / Textures / Motions / Physics）
out\v0.1.physics3.json   ← 头发、挂件摆动
out\v0.1.cmo3            ← 想精修时在 Cubism Editor 打开
out\v0.1.4096\texture_00..0N.png
out\v0.1.idle|nod|shake|blink.motion3.json
out\v0.1.smile|sad|angry|surprised.exp3.json
```

装进 VTS：把整个 `out` 文件夹复制到

```
<Steam>\steamapps\common\VTube Studio\VTube Studio_Data\StreamingAssets\Live2DModels\<模型名>\
```

然后 VTS 里点模型图标加载。**首次加载会弹「为模型进行自动配置？」→ 点「自动配置」→ 再弹「创建 15 个默认 VTS 参数」→ 点「确定」**，这是正常流程，不是报错。

### 几个必须知道的坑

1. **图层名字决定一切。** PSD2Live 靠名字认职责：`Hair_Back`、`Eye_White_L`、`Iris_R`、`Arm_L`、`Topwear_Body`、`张嘴`…… 名字不对或图层隐藏，那个部件就不会生成。最典型：`嘴张开` 图层是隐藏的 → 模型张不开嘴。
2. **默认参数太猛。** 首次自动生成后，VTS 的 `Mouth Open` 上限是 **2.1**、`Eye Open` 是 **1.9**（输入只有 0..1），所以嘴一动就全开、眨眼一跳一跳。改法见下面"调参"。
3. **导出会重置动作。** 每次重新导出，`idle` / `blink` 都会回到默认版本，自己调过的要备份再覆盖回去。
4. **手臂默认被衣服盖住。** 你的 PSD 里 `Arm_L/R` 在 `Topwear_Body` 下面就是会被盖住。要改是改绘制顺序，不是改绑定。
5. **美术本身的问题它救不了。** 比如一个只有 14 px 的嘴，被形变拉大后描边会扯成尖角。得换一张画对的图。

### 调参（VTS 侧）

配置文件：`Live2DModels\<模型名>\<模型名>.vtube.json`

```jsonc
"ParameterSettings": [
  { "Input": "MouthOpen", "OutputRangeLower": 0, "OutputRangeUpper": 0.85 },  // 默认 2.1
  { "Input": "EyeOpenLeft",  "OutputRangeUpper": 1.0 },                       // 默认 1.9
  { "Input": "EyeOpenRight", "OutputRangeUpper": 1.0 }
]
```

**改之前必须先退出 VTS**（它会把自己内存里的设置写回这个文件）。改完再启动。

### 精修（Cubism 侧）

`xxx.cmo3` 可以直接在 Live2D Cubism Editor 里打开，参数和键值都在。注意：

- 打开的是 `.cmo3`，**不要**走"新建 / 导入 PSD"，那样会得到一个只有空壳变形器的工程；
- 文件要和旁边的 `xxx.4096\` 贴图目录待在一起，单独拿出 `.cmo3` 会丢贴图。

### 它做不到什么

- 不能替你画画。分层 PSD 里缺的层、画错的位置，它只会按你给的东西去绑。
- 不能保证绑定质量。8 方向转头超出 ±20° 后，自动绑定的脸会开始变形。
- 不能导出 Cubism 的运行时文件（那步只能在 Editor 里手点，或直接用 PSD2Live 的导出）。

### 需要什么

- Windows 10/11
- Python ≥ 3.10
- 分层 PSD（765×1536 之类的整幅画布，图层名按上面的约定）
- PSD2Live 3.6.x（不随仓库分发）
- 可选：Live2D Cubism Editor（精修）、VTube Studio（直播）

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
├─ README.md                 本文件（人类）
├─ check_env.py              环境自检
├─ install.py                依赖安装
├─ config/pipeline.json      资源档位
├─ src/rigkit/               半身绑定引擎
├─ src/integrations/         全身预检
├─ scripts/
│   ├─ psd2live_mcp.py       ★ PSD2Live MCP 客户端（新增）
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
