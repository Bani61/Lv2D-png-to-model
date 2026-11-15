# Lv2D-png-to-model

**把一张立绘做成能在 VTube Studio 里直播的 Live2D 模型。**

输入一张 PNG/JPG 立绘（或已经分好层的 PSD），输出可以直接加载进 VTube Studio 的 `.moc3` 模型：网格、变形器、参数、物理摆动、待机与眨眼动作全部生成好，不需要在 Cubism Editor 里手动铺网格。

适用对象：做皮套的个人 / 小团队；不想学 Cubism 全套绑定流程、只想把画好的立绘变成能用的模型的人。

- 当前版本：**1.4.0**
- 更新日志：[CHANGELOG.md](CHANGELOG.md)
- 下载安装包：[Releases](https://github.com/Bani61/Lv2D-png-to-model/releases)

---

## 一、功能列表

| # | 功能 | 说明 | 依赖 | 状态 |
| --- | --- | --- | --- | --- |
| 1 | **整身自动绑定** | 分层 PSD → `.moc3` / `.cmo3` / 物理 / 动作 / 表情 | PSD2Live 3.6.x | 可用 |
| 2 | **半身自动绑定** | 内置 rigkit，适合小角度转头的半身皮套 | Python | 可用 |
| 3 | **AI 拆层** | 单张立绘 → 分层 PSD（头发、眼睛、嘴、身体、衣服等） | 云端：HF / 魔搭令牌<br>本地：CUDA | 可用 |
| 4 | **CUDA 本地推理** | 有 N 卡时可把拆层放在本机跑，不上传画稿 | CUDA 显卡 + 数 GB 依赖 | 可用（慢，见已知问题 7） |
| 5 | **遮挡顺序检查** | 绑定前检查帽子 / 头发 / 衣领 / 耳朵 / 脖子 的前后关系 | Python | 可用 |
| 6 | **ComfyUI 工作流生成** | 生成 tk_seethrough 工作流，用于补缺层 | ComfyUI | 可用 |
| 7 | **程序化修绑定** | 通过 MCP 改绘制顺序、改键值、改变色器、重新渲染验证 | PSD2Live 3.6.7+ | 可用 |
| 8 | **渲染验收** | 指定参数值渲染 PNG，用于对比改动前后 | PSD2Live | 可用 |
| 9 | **VTS 安装** | 一键把产物装进 VTube Studio 模型目录 | VTube Studio | 可用 |
| 10 | **VTS 参数调优** | 修正 VTS 自动生成参数放大过头的问题 | VTube Studio | 需手动改配置 |
| 11 | **环境自检 / 安装** | 检查 Python、依赖、显卡、显存、磁盘、写权限 | Python ≥ 3.10 | 可用 |
| 12 | **冒烟测试** | 7 项自检，输出 PASS / FAIL / SKIP | PowerShell | 可用 |
| 13 | **缺陷手册** | 9 类常见缺陷的症状、根因、修法 | — | 文档 |

> 说明：第 3 项"AI 拆层"走云端时，画稿会被上传到对应服务；在意隐私请用第 4 项本地 CUDA 模式。

---

## 二、系统要求

| 项目 | 最低 | 推荐 |
| --- | --- | --- |
| 操作系统 | Windows 10 64 位 | Windows 11 |
| Python | 3.10 | 3.11 / 3.12 |
| 内存 | 8 GB | 16 GB |
| 磁盘 | 5 GB 可用 | 20 GB 可用（本地 CUDA 模式） |
| 显卡 | 集成显卡（走云端拆层） | NVIDIA，≥ 8 GB 显存 |
| 其他软件 | PSD2Live 3.6.x | + Live2D Cubism Editor（精修）、VTube Studio（直播） |

**显卡档位**（`config/pipeline.json` 自动判定）：

| 档位 | 条件 | 拆层分辨率 / 步数 |
| --- | --- | --- |
| `cloud_only` | 无 CUDA | 云端执行 |
| `low_vram_under_8gb` | 显存 < 8 GB | 768 / 15 |
| `cautious_8gb` | 8–10 GB | 1024 / 20 |
| `balanced_10_12gb` | 10–12 GB | 更高 |
| `high_quality_12gb_plus` | ≥ 12 GB | 最高 |

---

## 三、安装

从 [Releases](https://github.com/Bani61/Lv2D-png-to-model/releases) 下载 `Lv2D-png-to-model-1.4.0.zip`，解压后进入 `Lv2D-png-to-model\` 目录：

```powershell
python check_env.py --json                  # 自检：缺什么、显卡够不够、能不能写文件
python install.py --yes                     # 装必需依赖（几百 MB）
python install.py --verify-only --json      # 期望输出 "ok": true
powershell -ExecutionPolicy Bypass -File tests/smoke.ps1   # 期望：无 FAIL
```

**需要本地 CUDA 拆层**（可选，装数 GB，慢但不上传画稿）：

```powershell
python install.py --yes --with-local-gpu
```

安装过程不写注册表、不改 PATH；卸载等于删目录。

> 1.4.0 之前的版本没有发布包，只能 clone 仓库或下载源码 zip。

---

## 四、快速开始（全身，约 10 分钟）

```powershell
# 1. 绑定（PSD 必须是分层文件，图层名按约定）
PSD2Live.exe --input character.psd --output out --lang zh --atlas 8192 --mesh-spacing 32

# 2. 装进 VTube Studio：整个 out 目录复制到
#    <Steam>\steamapps\common\VTube Studio\VTube Studio_Data\StreamingAssets\Live2DModels\<模型名>\
```

VTS 里加载后**连续弹两个框，都是正常流程**：

1. 「为模型进行自动配置？」→ 点**自动配置**
2. 「创建 15 个基于 Live2D 默认参数名和值的 VTS 参数」→ 点**确定**

跳过也能加载，但热键和面捕会缺一部分。

两个命令行参数不要省：`--atlas 8192`（默认 4096 脸上会有矩形接缝）、`--mesh-spacing 32`（默认 64 网格太粗，嘴和眼睛形变走样）。

---

## 五、输出文件说明

```
out\character.moc3            ← VTube Studio 加载这个
out\character.model3.json     ← 配置清单（模型 / 贴图 / 动作 / 物理）
out\character.physics3.json   ← 头发、挂坠等物理摆动
out\character.cdi3.json       ← 参数与部件显示信息
out\character.cmo3            ← 想精修时在 Cubism Editor 打开
out\character.4096\texture_00..0N.png   ← 图集贴图
out\character.idle|nod|shake|blink.motion3.json
out\character.smile|sad|angry|surprised.exp3.json
```

打开 `.cmo3` 的注意事项：**直接打开文件**，不要走「新建 / 导入 PSD」（那样会得到只有空壳变形器的工程）；`.cmo3` 必须和旁边的 `<名字>.4096\` 贴图目录放在一起。

---

## 六、使用流程

```
① 准备分层 PSD      图层名按约定（见 references/图层清单.md）
② 环境自检           python check_env.py --json
③ 绑定               PSD2Live.exe --input ... --output ...
④ 渲染验收           看张嘴、闭眼、±20° 转头是否正常
⑤ 装进 VTS           复制到 Live2DModels，加载时按自动配置
⑥ 调参               改 vtube.json 的 Mouth/Eye 上限
⑦ 精修（可选）       在 Cubism Editor 打开 cmo3
```

**第 ④ 步不能跳。** 命令返回成功不代表绑定正确，必须看图：

```powershell
python scripts/psd2live_mcp.py render --out mouth.png --params ParamMouthOpenY=1.0
python scripts/psd2live_mcp.py render --out eyes.png  --params ParamEyeLOpen=0 ParamEyeROpen=0
```

如果新图和上一张的 sha256 完全一致，说明那步改动没生效——这是本仓库里否掉过好几种"看起来合理"的修法的办法。

---

## 七、参数调优（VTube Studio 侧）

VTS 首次自动生成的参数**放大过头**，所以会出现"嘴一张就全开""眨眼一跳一跳"。改配置文件：

`Live2DModels\<模型名>\<模型名>.vtube.json`

```jsonc
"ParameterSettings": [
  { "Input": "MouthOpen",    "OutputRangeLower": 0, "OutputRangeUpper": 0.85 }, // 默认 2.1
  { "Input": "EyeOpenLeft",  "OutputRangeUpper": 1.0 },                        // 默认 1.9
  { "Input": "EyeOpenRight", "OutputRangeUpper": 1.0 }
]
```

**改之前必须先退出 VTS**——它退出时会把自己内存里的设置写回该文件，运行中改的会被覆盖。

---

## 八、已知问题清单

> 这些是 1.4.0 已确认存在、尚未解决的问题。列表中"规避"一栏是当前可用的替代做法。

| # | 问题 | 影响 | 状态 | 规避 |
| --- | --- | --- | --- | --- |
| 1 | **Cubism 5.4 适配尚未开始** | 无法程序化修改 Cubism 工程（改键值、改网格、重排部件都还得手点） | **未开始** | Cubism 外部 API 仅 5.4 alpha 提供，官方已于 2026-10-18 停止提供且带时间锁，5.3.x 端口 22033 连不上；暂时用 PSD2Live 工程改，或手动 |
| 2 | **眼部闭合绑定存在问题** | 闭眼后眼下仍露出一条细蓝线 / 边缘毛刺；原因是 PSD 没有专门的闭眼图层，只能压扁眼线 | 待修 | 可尝试在闭眼关键帧把眼白、瞳孔缩到 0.12（对部分模型无效）；彻底解决需在 PSD 增加闭眼专用图层 |
| 3 | **自动拆出的嘴巴绑定存在问题** | 张嘴时嘴边缘出现尖角、拉丝；原因是拆层给出的嘴形美术常是零碎像素或极小图（如 14 px），被形变放大后描边被扯开 | 待修 | 用命名规范的嘴层（`张嘴` / `mouth_open`）并确认画得完整；按 `references/model-defects.md` 换成 29×21 级别的嘴图 |
| 4 | **VTS 默认参数放大过头** | 嘴一开就全开、眨眼一卡一卡 | 已知，需手动 | 改 `vtube.json` 的 `OutputRangeUpper`（见第七节） |
| 5 | **重新导出会重置动作** | 调好的 idle / blink 被覆盖回默认 | 已知，需手动 | 先备份 `.motion3.json`，导出后覆盖回去 |
| 6 | **手臂默认被衣服盖住** | 袖子看不见 | 已知，需手动 | PSD 里把手臂层移到衣服之上，或导入后把绘制顺序改成 165/166 |
| 7 | **8 GB 显存本地 CUDA 很慢** | 1280 分辨率 / 30 步在 8 GB 卡上 50 分钟未完成 | 已知 | 用 `cloud_only` 云端拆层，或降到 768 / 15 步 |
| 8 | **大角度转头会变形** | 超过 ±20° 后脸部出现硬切边 | 已知 | 限制转头幅度；需要更大角度必须在 Cubism 里手动补键 |

---

## 九、常见问题

**Q：加载模型时提示"参数丢失"或"自动配置"，是不是文件坏了？**
不是。那是 VTS 首次加载新模型的配置向导：先点「自动配置」，再点「确定」创建 15 个默认参数。

**Q：模型张不开嘴 / 眼睛不眨？**
PSD 里对应的嘴层或眼层被隐藏，或名字不符合约定。PSD2Live 按图层名识别职责，名字不对就不生成该部件。

**Q：能不能不用 PSD2Live？**
半身可以用内置 rigkit；整身绑定目前只有 PSD2Live 这条路。

**Q：能不能全自动，我只想点一下？**
不行。第 ④ 步（渲染验收）、第 ⑥ 步（调参）需要人判断，自动绑定不等于绑定正确。

**Q：拆层会不会把我的画稿上传？**
走云端拆层会上传到对应的推理服务；在意隐私用 `--with-local-gpu` 本地模式。

**Q：`.cmo3` 打开后贴图全丢了？**
`.cmo3` 必须和同目录的 `<名字>.4096\` 贴图文件夹放在一起，单独移动 `.cmo3` 会丢贴图。

---

## 十、目录结构

```
├─ check_env.py              环境自检
├─ install.py                依赖安装 / 验证
├─ config/pipeline.json      资源档位与当前档位
├─ src/rigkit/               半身绑定引擎
├─ src/integrations/         整身 PSD 预检
├─ scripts/
│   ├─ psd2live_mcp.py       PSD2Live MCP 客户端（程序化修绑定 / 渲染 / 导出）
│   ├─ make_tk_workflow.py   ComfyUI 工作流生成
│   └─ occlusion_psd_check.py PSD 结构与遮挡检查
├─ workflows/                操作流程（PSD2Live MCP、半身绑定、验收回滚）
├─ references/
│   ├─ model-defects.md      缺陷手册（症状 / 根因 / 修法）
│   ├─ psd2live-ops.md       PSD2Live 接口速查
│   ├─ 图层清单.md            图层命名约定
│   └─ ...
└─ tests/smoke.ps1           冒烟测试
```

---

## 十一、许可

本项目采用 **PolyForm Noncommercial License 1.0.0**（禁止商业用途），著作权人 **Bani61**，全文见 [LICENSE](LICENSE)。第三方代码与依赖保留各自原许可证，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。PSD2Live 本体为 GPL-3.0，不随本仓库分发，需自行安装。

---

**给 AI agent 的文档**：[AI_README.md](AI_README.md)（安装与执行协议）、[SKILL.md](SKILL.md)（任务路由与能力分级）。
