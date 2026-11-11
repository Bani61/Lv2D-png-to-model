# 遮挡相关项目核对

核对日期：2026-11-02

本页只记录已经在源码、README、模型元数据或本地文件中核实过的能力和边界。项目更新后先复核 commit，再修改流程。

## 版本与定位

| 项目 | 已核对版本 | 许可 | 在流程中的定位 |
|---|---|---|---|
| [See-through](https://github.com/shitagaki-lab/see-through) | `df019de5129d6c4b406587a14c3501669441a783` | Apache-2.0 | 动漫立绘首版语义拆层和深度估计 |
| [ComfyUI-See-through](https://github.com/jtydhr88/ComfyUI-See-through) | 本地 `98d754bf04f668647919ab750eccb0e0640faa81` | 以仓库说明为准 | 把 See-through 接入 ComfyUI |
| [tk_seethrough](https://github.com/tackcrypto1031/tk_seethrough) | `265d7acbb82bd60198ff17714361426994114149`，v1.2.9 | MIT | 可选的 AutoFill、Original 底垫和 Layer Filter |
| [PSD2Live](https://github.com/tsunehimatoi/psd2live) | 本地 `f70241ff0ba2c50a992540ab4238e25a869aa33e` | 应用 GPL-3.0；部分模块 MIT | PSD 绑定、前后分层和 Cubism/VTS 导出 |
| [CObL](https://github.com/aneeldamaraju/cobl) | `c7ecec5264245b8be7d45c82d02e7a55d3dad075` | MIT | 研究参考，不是已验证的动漫图层裁判 |
| [RevealLayer](https://github.com/360CVGroup/RevealLayer) | `da68ff58889a1799a1e75efd23e72bccebbf7589` | Apache-2.0 | 可选的自然图像遮挡分解实验 |
| [Qwen-Image-Layered](https://github.com/QwenLM/Qwen-Image-Layered) | `54c4fe47e76d745775e03fc66ee38457280ed9ea` | Apache-2.0 | 可选的多 RGBA 层分解，资源门槛很高 |

## See-through

官方研究仓库把任务定义为单图动漫角色图层分解，输出带透明通道的语义层和伪深度，论文声称可生成最多 23 个语义层。ComfyUI 封装在 V3 身体层与头部细节层全部启用时最多输出 24 个标签层。

已核对的 ComfyUI 节点：

- `SeeThrough_LoadLayerDiffModel`
- `SeeThrough_LoadDepthModel`
- `SeeThrough_Decompose`
- `SeeThrough_SavePSD`
- `SeeThrough_PartsToLayers`

官方研究在 1280 全精度下给出的显存需求约为 12-16 GB。8 GB 只能走量化、降低分辨率或 group offload，本项目实测仍不适合高频试错。

边界：

- 语义层不是 Live2D 的最终动作层。
- 深度中位数只给绘制顺序提示，不负责复杂衣领穿插。
- 被完全挡住的区域可能为空或被错误补画。
- 官方明确表示这不是完整的 Image-to-Live2D 流程。

## tk_seethrough

该 fork 在 v1.2.9 新增或保留了以下生产相关能力：

- `SeeThrough_GenerateLayers_Custom`
  - `enable_head_detail`：默认 `true`，关闭时跳过 V3 头部细节推理。
  - `auto_fill`：默认 `false`，最多额外重跑至 5 轮。
  - `min_alpha_coverage`：默认 `0.01`，只在 AutoFill 开启时使用。
- `SeeThrough_LoadSource`：输出 `image`、`mask`、`source_filename`。
- `SeeThrough_SavePSD`：可选输入 `original_image` 和 `source_filename`；可把原图作为可见 `Original` 底垫。
- `SeeThrough_LayerFilter`：`mode` 为 `include` / `exclude`，`tags` 每行一个。
- 开启 AutoFill 时可下载 All Runs PSD，比较每一轮。

AutoFill 算法：

1. 第一轮使用给定 seed。
2. 对预期标签逐个检查 alpha 覆盖率，低于阈值即视为缺失。
3. 有像素的层再与原图可见区域计算 RGB 相似度。
4. 缺失或相似度低于 `0.85` 时，以 `seed + 1` 等继续推理。
5. 每层保留相似度最高的版本，最多运行 5 次。

重要限制：

- 它修复缺层和可见区域相似度，不判断帽子、头发和衣领的空间关系。
- 相似度低不等于遮挡错，相似度高也不能证明隐藏区域正确。
- 没有出现在人物上的可选标签也可能被当成缺失层，导致无意义的重跑。
- 每次额外轮次都可能显著增加耗时和额度消耗。
- 开启 AutoFill 前必须记录预计成本并取得用户许可。
- 当前 v1.2.9 的 Loader 输入只有 `model`、`vae_ckpt` 和 `unet_ckpt`，没有上游脚本里的 `quant_mode`、`cache_tag_embeds` 或 `group_offload` 字段；不要把旧脚本参数直接塞进这个 fork。
- 默认模型标识是全精度 `layerdifforg/seethroughv0.0.2_layerdiff3d`，8 GB 是否能在可接受时间内完成必须实测，不能因为节点自动 CPU offload 就宣称 8 GB 已优化。

## PSD2Live

PSD2Live 的 `source_split_depth` 是实现衣领、头发、配饰穿插的首选入口。它不是简单复制 PSD 图层，而是在模型工程中：

1. 把源 ArtMesh 复制成后层和前层。
2. 把 `middle_ids` 中的脖子或头发等 ArtMesh 放在两者之间。
3. 复制源网格的几何、参数关键形、混合形、路径和权重。
4. 后层继承 Glue、蒙版和模拟目标，方向 Glue 让前层跟随后层。
5. 前端随后用橡皮擦掉前层里应藏到后面的部分。

输入核心字段：

```json
{
  "operation": "source_split_depth",
  "request": {
    "state": "<workspace_inspect 返回的 state>",
    "source_id": "<衣领或帽子所在网格的原始 ID>",
    "middle_ids": ["<脖子或头发网格的原始 ID>"],
    "names": ["Collar_Back", "Collar_Front"]
  }
}
```

`names` 的顺序是后层、前层。中间对象必须是非空、唯一、且不包含源网格的 ID，不带 `mesh:` 前缀。

边界：

- 原图层和网格会被新前后层取代；只有撤销能回到原层。
- 导入的 CMO3 模型使用另一套兼容路径。
- 复制的是现有像素，不会凭模型自动补出被遮挡内容。
- 生成绑定仍需人工检查转头、低头、衣领和肩膀。

## CObL

CObL 的真实论文名称是 **CObL: Toward Zero-Shot Ordinal Layering without User Prompting**，ICCV 2025 Highlight。

公开实现的关键事实：

- 输入一张 RGB 场景图，不需要用户提示物体数量。
- 使用扩散先验和推理时合成约束，并行生成按遮挡排序的物体层。
- 训练集是几千张合成的多物体桌面场景。
- 论文只报告对真实桌面照片的零样本泛化。
- 示例使用 Python 3.10、PyTorch 2.7.1 和 `Guided_Layer_Sampler`。
- 权重通过 `install.sh` 从 Dropbox 下载，仓库本身不包含权重。

不能把 CObL 直接称为“已验证的动漫衣领层级裁判”。它更适合启发“合成回到原图”的约束和候选顺序验证，若用于动漫角色，必须另建帽檐、耳朵、头发和衣领测试集。

另一个名为 `m-kazuki/cobl_diffusion` 的仓库是机器人动态环境轨迹规划，与本项目无关。

## RevealLayer

RevealLayer 是遮挡感知的图像分解研究，官方标题为 **Disentangling Hidden and Visible Layers via Occlusion-Aware Image Decomposition**。

已核对事实：

- 输入 RGB 图和每个前景物体的 bounding box。
- 使用 FLUX.1-dev 和约 0.65 GB 的 RevealLayer 增量权重。
- 输出包含背景和多个 RGBA 前景层，目标是同时保留可见区域并恢复被遮挡内容。
- 官方仓库的 `infer.sh` 含硬编码的多 GPU、路径和环境名，不是即装即用脚本。
- README 提到 `--guidance_scale`，当前源码参数实际为 `--cfg`；以源码 schema 为准。
- 数据处理面向自然场景的多物体层，不提供动漫语义名称。

适用方式：在其他结果缺少耳后、帽下或领后像素时做局部对照实验。不能直接替代 See-through 的语义拆层，也不能预设它在 8 GB 显卡上可运行。

## Qwen-Image-Layered

官方模型是 Qwen-Image 的可编辑 RGBA 图层分解微调版。

已核对事实：

- 支持可变层数和递归拆层。
- 模型约 `20,430,407,232` 个 BF16 参数，权重文件合计约 `53.74 GB`。
- 官方示例推荐 `resolution=640`，也可使用 `1024` bucket。
- 默认参数包括 `true_cfg_scale=4.0`、`50` 步、`layers=4`。
- 输出按层保存 RGBA；官方 PSD 导出把层命名为 `Layer 1..N`。
- 文本提示描述整张图，不应假定它能精确控制每一层的语义。

主要用途是比较空间分解和补全假设，或对有足够显存的机器做独立候选。当前 8 GB 路线不能把它当作默认依赖。

## 路由结论

```text
动漫角色语义拆层
  -> See-through / tk_seethrough

衣领、头发、配饰夹层
  -> PSD2Live source_split_depth

缺层自动重跑
  -> tk_seethrough auto_fill，显式授权且预算允许时

遮挡顺序研究
  -> CObL 只作参考；必须先用动漫案例重新验证

缺失区域补全实验
  -> RevealLayer / Qwen-Image-Layered 可选对照

最终绑定与导出
  -> PSD2Live，随后 Cubism / VTS 验收
```
