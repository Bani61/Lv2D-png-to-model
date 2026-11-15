# 已知缺陷目录

这张表是从实际项目里一条条踩出来的。遇到症状先查表，别从零推导。

## 1. 模型完全不张嘴

**症状**：`ParamMouthOpenY` 拉到 1.0，嘴一动不动。

**根因**：PSD 里嘴的图层叫 `嘴张开`，而且是隐藏的。PSD2Live 只认 `张嘴`（或 `mouth_open`）这个标签，名字不对 + 不可见 = 不生成张嘴部件。

**验证**：

```powershell
python scripts\psd2live_mcp.py inspect --scope objects --query Mouth
```

看结果里有没有 `ArtMeshMouthOpen`。没有就是没生成。

**修法**：把图层改名 `张嘴`、设为可见，重新导入导出。改完 `xxx.cdi3.json` 里应出现 `"Id": "ArtMeshMouthOpen"`。

## 2. 张嘴时边缘拉出尖角（毛刺）

**症状**：嘴张开时左右两侧冒出深色三角，像被扯坏的布。

**根因（两种情况）**：

1. 嘴的美术图层太小（实测某案例只有 14 px 宽的 O 形嘴），被形变放大数倍后描边被扯成棱角；
2. 图层像素散落在远处（包围盒一直延伸到嘴外 100+ px），形变把那些碎点也一起拉过来。

**判定**：导出的警告里会出现

```
关键模型：ArtMeshMouthOpen 默认形态偏离 PSD：
  期望 Bounds(left=452.99, top=946.70, right=472.45, bottom=952.59)
  实际 Bounds(left=375.87, top=209.80, right=394.89, bottom=217.17)
```

期望值和实际值差得越远，说明美术位置/尺寸越离谱。

**修法**：

1. 用 alpha 包围盒找出该图层的真实像素范围（`layer.bbox` 给的是整幅画布，没用）：

```python
alpha = np.array(layer.topil().convert("RGBA"))[:, :, 3]
ys, xs = np.where(alpha > 8)
```

2. 裁到嘴部 ROI（例如 x 355–425、y 190–240），丢掉远处碎点；
3. 用一张**尺寸合适、画对位置**的嘴形替换（通常是 PSD 里另一张被隐藏的 `嘴张开` 图层），重新导入导出。

**无效的尝试（别重复）**：调网格密度（`interiorDensity`）、`layer_mesh_rebuild`、`wrap`/`edgeMode`、缩放上下唇子网格。这些改完渲染逐字节一致——因为问题不在网格。

## 3. 闭眼后还露眼白/蓝线

**症状**：眼皮合上，眼睛下方仍有一条白或蓝的细弧，有时带尖刺。

**根因**：`Eye_White_L/R`、`Iris_L/R`、`Eye_Highlight_L/R` 的闭眼关键帧和睁眼关键帧完全一样，眼皮合上时眼球还在原处。

**修法**：在闭眼关键帧把这些网格缩到接近 0：

```jsonc
{"op":"set","target":"mesh:ArtMeshEyewhiteL","key":{"ParamEyeLOpen":0.0},"geometry":{"scale":0.12}}
```

**注意**：这条路径不是每次都灵。若改完渲染 sha256 不变，说明当前工程的该网格被上游变形器接管，改用 `rig_deform` 动 `warp:DeformEyes` 的闭眼关键帧。

**尖刺的来源**：先排除睫毛——把 `ArtMeshEyelashL/R` 整层隐藏再渲染，如果尖刺还在，它属于眼白自身的描边。

## 4. 嘴稍微一动就全开

**症状**：说话时嘴直接跳到最大张口，没有中间状态。

**根因**：不在模型，在 VTS 的每模型配置：

```
Live2DModels\<模型名>\<模型名>.vtube.json
  "Mouth Open"  OutputRangeLower 0 → OutputRangeUpper 2.1   ← 输入只有 0..1
```

**修法**：退出 VTS（运行时会覆盖文件），把 `OutputRangeUpper` 改成 0.85（嘴）和 1.0（眼睛），再启动。

## 5. 眨眼一卡一卡

**根因**：`blink.motion3.json` 全部是线性段 + VTS 眼睛输出上限 1.9，导致曲线被硬切。

**修法**：

1. 把 `Eye Open Left/Right` 的 `OutputRangeUpper` 改成 1.0；
2. 把 blink 曲线改成 bezier 缓动（段结构 `[t, v, type, c1x, c1y, c2x, c2y]`，`type=1` 为 bezier）。

另外注意 `idle.motion3.json` 默认会驱动 `ParamAngle*` / `ParamEye*`，和面捕抢参数，表现为抖动。把 idle 改成只驱动 `ParamBreath`。

## 6. 手臂被衣服盖住

**症状**：手和袖子看不见，或者手臂压着衣服。

**根因**：PSD 图层顺序里 `Arm_L/R` 排在 `Topwear_Body` **之前**（越靠前越在底层）。这是原图层的顺序，不是绑定错误。

**修法（三选一）**：

1. 在 PS 里把 Arm 图层拖到 Topwear_Body 之上（最干净，但 psd-tools 无法代劳：改 `group._layers` 不持久）；
2. 导出后改绘制顺序（`rig_edit_structure` 设 `draw_order`，见 `workflows/psd2live-mcp.md#43`）；
3. 接受现状（如果动作幅度小）。

## 7. 「参数丢失」/「模型失效」

**症状**：打开工程弹「参数设置 / 自动生成参数」，生成完模型不动。

**根因**：走的是 Cubism 的**新建 / 导入 PSD** 流程，它只生成网格和空变形器，不生成键值。或者用户把 `.psd`、`.moc3` 当工程打开。

**修法**：`文件 → 打开` 直接打开 `.cmo3`。`.cmo3` 必须和 `xxx.4096\` 贴图目录待在一起。

**另一个容易误判的地方**：VTube Studio 首次加载新模型会弹「为模型进行自动配置？」→「创建 15 个默认参数」。这是**正常流程**，不是错误。

## 8. 脸上有红色竖纹

**症状**：鼻梁处一条红竖线，PSD 原图里没有。

**根因**：绑定/图集生成时的网格瑕疵，不是美术问题（扫描 PSD 全部红像素可证实原图干净）。

**现状**：换用 8192 图集 + 32 网格间距后消失过一次；改 4096×5 图集后也未见。若复现，优先换图集参数试。

## 9. 转头过大时脸变形

**症状**：`ParamAngleX` 超过 ±20° 后五官错位、切边。

**根因**：自动绑定的变形器按小角度设计，超出范围就是拉伸。

**修法**：限制参数范围（`ParamAngleX` 改 −20..20），或在 Cubism 里手工补大角度的变形器。这属于 L3 手工活。
