# 帽子、衣领与隐藏面工作流

## 目标

在拆层和绑定之间增加一层明确的遮挡门禁，避免出现以下错误：

- 帽檐盖住整张脸或透视与头部俯仰相反。
- 帽墙没有包住头骨，后脑头发从帽顶穿出。
- 后领口盖住脖子，或前领中央把整段脖子遮住。
- 耳朵和侧发在转头时互相穿插或漏底。
- 被遮挡区域没有补画，运动后才露出透明洞。

## 输入

- 原图与透明背景合成。
- See-through 或 tk_seethrough 输出。
- `layers.json`、逐层深度和 PSD。
- 角色自身左右方向的确认记录。
- 用户是否允许上传图片、是否允许最多 5 轮 AutoFill 的授权。

## 1. 选择拆层入口

### 首选：已安装 tk_seethrough

```powershell
python scripts/make_tk_workflow.py `
  --input-name hero.png `
  --filename-prefix hero `
  --resolution 1280 `
  --steps 30 `
  --out hero-tk.json
```

默认不开启 AutoFill。只有用户明确批准后加：

```powershell
python scripts/make_tk_workflow.py `
  --input-name hero.png `
  --auto-fill `
  --out hero-tk-autofill.json
```

生成的工作流把 `SeeThrough_LoadSource.image` 和 `source_filename` 同时接到 `SeeThrough_SavePSD`，因此 PSD 会有可见 `Original` 底垫，并使用源文件名。

提交到 ComfyUI 时把文件内容放进 API 的 `prompt` 字段：

```powershell
$prompt = Get-Content -Raw .\hero-tk.json | ConvertFrom-Json
$body = @{
  prompt = $prompt
  client_id = [guid]::NewGuid().ToString()
} | ConvertTo-Json -Depth 20
$response = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8188/prompt `
  -ContentType application/json `
  -Body $body
```

tk v1.2.9 的 Loader 不接受上游旧脚本里的 `quant_mode`、`cache_tag_embeds` 或 `group_offload` 输入。工作流生成器不会注入这些未声明字段；8 GB 上默认全精度模型的实际耗时尚未验证。

### 回退：上游 ComfyUI-See-through

使用 `SeeThrough_GenerateLayers`、`SeeThrough_GenerateDepth`、`SeeThrough_PostProcess` 和 `SeeThrough_SavePSD`。这条路线没有 AutoFill 和 Original 自动接线，需要人工检查并补底垫。

### 云端

仅在用户同意上传角色图后使用 Hugging Face 或 ModelScope。记录分辨率、种子、服务、时间和原始结果哈希。

## 2. 检查 See-through 原始输出

1. 把 `layers.json` 或 PSD 展开为从下到上的叶层清单。
2. 验证 `headwear`、`hair`、`face`、`ears`、`neck`、`topwear` 等语义没有明显串层。
3. 检查 `depth_median` 只作为初值，尤其不能直接相信复杂衣领、袖子和帽檐。
4. 检查所有层坐标在同一画布内。
5. 将原画可见像素逐个归回图层；不要把整张合成截图当作贴图。

## 3. AutoFill 的成本门

AutoFill 只在以下全部条件满足时开启：

- tk fork 已经在当前 ComfyUI 中加载。
- 第一轮已经完成并保存结果。
- 缺失层不是角色本来没有的尾巴、翅膀或头饰。
- 用户允许最多 5 轮推理及相应时间或额度消耗。

先看第一轮日志中的：

```text
tag: MISSING
tag: sim=<value>
```

`sim < 0.85` 会触发后续轮次。若预期层集中有本来不存在的可选标签，AutoFill 可能反复重跑仍无法达到停止条件。

AutoFill 通过后仍要继续下面的遮挡检查，不能把 All Runs PSD 的最佳相似度当作最终排序。

## 4. 帽子和头发

从下到上建立主链：

```text
Hair_Back
Ear_L / Ear_R
Face_Skin
Hair_Side_L / Hair_Side_R
Hair_Bang
Hat
Collar_Back
Neck
Collar_Front
```

这只是检查主链。若头发从帽口穿出、反戴帽子或耳前发束有特殊交叠，按原画局部证据修改。

检查：

- 帽檐的上下椭圆弧与头部俯仰一致。
- 帽墙从太阳穴连到后脑，包住头骨。
- 帽顶不落在头骨内部。
- 后发从帽口下方连续，不穿过帽檐上表面。
- 耳朵被帽墙和侧发遮住的部分有足够隐藏像素。
- 帽檐与衣领不得由错误深度顺序自动决定。

## 5. 衣领夹层

### PSD 手工方案

从下到上：

```text
Collar_Back
Neck
Collar_Front
```

1. 把完整衣领作为后层。
2. 保持 Neck 在下巴下方完整。
3. 复制完整衣领作为前层。
4. 在前层中央擦除应由脖子显示的领口。
5. 保留压在脖子前面的领尖、翻领、扣子和装饰。
6. 检查后领、肩后和头后没有因前层擦除而一起丢失。

### PSD2Live 方案

1. 启动 PSD2Live，通过 MCP 调用 `workspace_inspect`，读取衣领网格和脖子的原始 ID 及当前 `state`。
2. 调用 `source_split_depth`：

```json
{
  "state": "<current state>",
  "source_id": "<topwear mesh id>",
  "middle_ids": ["<neck mesh id>"],
  "names": ["Collar_Back", "Collar_Front"]
}
```

3. 在返回的前层上用橡皮擦掉中央领口和后领区域。
4. 预览左右转头、低头和抬头。
5. 确认后保存 `.psd2live`，再导出 `.cmo3` 检查。

注意：`source_split_depth` 会取代原源图层；只有撤销能回到原层。不要在没有备份工程时直接应用。

## 6. 隐藏区域

补画顺序：

1. 先使用 See-through 已提供的隐藏面。
2. 再使用同一机位、同一画布的变体补画。
3. 只有在前两者都无法覆盖时，才把 RevealLayer 或 Qwen-Image-Layered 作为实验候选。
4. 正面可见区域的差异必须为零；任何重画都要保留补前和补后对照。

RevealLayer 需要逐物体 bounding box，输出对象层而不是动漫语义层。Qwen 权重约 53.74 GB，当前技能不把它列为 8 GB 可运行方案。

CObL 的训练域是多物体桌面场景。它不能在没有新测试的情况下充当动漫衣领、帽檐和头发的最终顺序裁判。

## 7. PSD 门禁

```powershell
python scripts/occlusion_psd_check.py hero.psd `
  --mode full `
  --require-original `
  --json `
  --report hero-occlusion.json
```

必须满足：

- PSD 可以打开。
- 没有重名叶层。
- 所有层边界在画布内。
- `Original` 在可见层最底部。
- 衣领顺序为后层、脖子、前层。
- 帽子模式下，帽顶位于刘海之上，后发位于帽层之下。
- 自动检查通过后，仍完成 1:1 与 3-4 倍局部人工检查。

## 8. 回退

- AutoFill 无用或超预算：关闭 AutoFill，使用第一轮结果手工修层。
- 帽檐透视失败：回到整顶帽层重画，不在错误轮廓上继续切头发。
- 衣领像素不足：保留全领 PSD 作为失败版本，先补隐藏面或在 PSD2Live 中做前后分层。
- CObL/RevealLayer/Qwen 与现有环境冲突：保留为独立实验环境，不破坏主技能依赖。
- PSD2Live 操作失败：保留 `.psd2live` 工程和导出报告，撤销错误编辑，不覆盖通过版本。
