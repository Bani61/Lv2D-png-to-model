# PSD2Live 操作速查

对象：PSD2Live 3.6.7，MCP 精简工具集（28 个工具）。

## 工具清单

```
workspace_inspect        workspace_overview       workspace_list_operations
workspace_get_operation  workspace_call           workspace_apply_edits
workspace_preview_edits  rig_deform               keyform_apply
author_axis author_physics author_compile
view                     parameter motion expression hit_area pose
skeleton                 path physics simulation swing source_paint
snapshot                 history job project
```

`workspace_call` 是万能入口：`{"operation":"<name>","request":{...}}`。

## 参数包装规则

| 工具类型 | 调用形状 |
| --- | --- |
| 普通工具（`workspace_inspect`、`keyform_apply`） | `{"request":{...}}` |
| 分组工具（`project`、`view`、`job`、`parameter`…） | `{"op":"<sub>","request":{...}}` |
| 其余操作（`rig_edit_structure`、`layer_mesh_update`…） | `workspace_call` → `{"operation":"<name>","request":{...}}` |

## `project` 的 op

```
import_psd   create   create_artwork   import_layout   import_cmo3
save   save_as   open   export_model   export_target   export_psd
```

- `import_psd` 必填 `path` + `state`（不是 `psd_path`）。
- `open` 只吃 `.psd2live` 工程包。
- 有未保存改动时导入会报 `unsaved_changes`，先 `save_as`。
- 返回是 job；产物在 `data.result`（`project_id`、`state`）。

## `view` 的 op

```
render_model   render_layer   render_poses   render_context
compare_history   sample_motion   check_coverage
```

`render_model` 请求形状：

```jsonc
{
  "viewport": {"mode": "canvas_rect", "left": 0, "top": 0, "width": 765, "height": 1536},
  "target_long_edge": 900,
  "parameters": {"ParamMouthOpenY": 1.0},
  "background": "transparent"
}
```

返回 `image/png` 内容块。

## `workspace_inspect` 的 scope

```
layers / objects / parameters / settings / preview / generation
```

可带 `query`（模糊匹配名称）与 `limit`（≤64）。返回：

```jsonc
{
  "state": "f0cd9790-…:1:3",
  "project_id": "ceaa261b-…",
  "items": [{"name": "Arm_L", "target": "mesh:ArtMeshHandwearL", "parentId": "...", "layerId": "..."}]
}
```

**`target` 才是合法 id 形态**，直接拿 `name` 去调用会失败。

## 常用 target 形态

```
mesh:ArtMeshHandwearL      Arm_L
mesh:ArtMeshHandwearR      Arm_R
mesh:ArtMeshTopwear        Topwear_Body
mesh:ArtMeshBottomwear     Pants_Hip
mesh:ArtMeshEyelashL/R     Eye_Open_L/R
mesh:ArtMeshEyewhiteL/R    Eye_White_L/R
mesh:ArtMeshIridesL/R      Eye_Highlight_L/R
mesh:ArtMeshIridesL2/R2    Iris_L/R
mesh:ArtMeshMouthOpen      张嘴 / mouth_open
mesh:ArtMeshMouth          Mouth_Closed
warp:DeformEyes            双眼
warp:DeformEyeShapeL/R     单眼形状
warp:DeformEyeGazeL/R      眼珠
```

## `rig_edit_structure`

```jsonc
{
  "state": "...", "project_id": "...", "request_id": "<uuid>",
  "edits": [
    {"action":"static","kind":"mesh","id":"ArtMeshHandwearL","draw_order":165},
    {"action":"static","kind":"mesh","id":"ArtMeshLayer5","opacity":0.0}
  ]
}
```

- `id` **不带** `mesh:` 前缀。
- `draw_order` 范围 0..1000，生成时相邻差 10；在空隙里插值（160 与 170 之间用 165）。
- 还能改颜色、混合模式、裁剪、culling；删变形器；改 Part；整理参数文件夹。
- 改之前先 `workspace_inspect` 读现值。

## `keyform_apply`

```jsonc
{
  "state": "...", "project_id": "...", "request_id": "<uuid>",
  "changes": [
    {"op":"set","target":"mesh:ArtMeshEyewhiteL","key":{"ParamEyeLOpen":0.0},"geometry":{"scale":0.12}}
  ]
}
```

- `geometry` 支持 `originX` / `originY` / `angle` / `scale`，只做整体变换。
- `channels.opacity` **静默失效**（`applied:false`），透明度请走 `rig_edit_structure`。
- 成功返回 `changed: [...]` 与新 `state`。

## `rig_deform`

逐点编辑 ArtMesh / Warp。`changes[]` 每项：

```jsonc
{
  "target": "warp:DeformEyes",
  "key": {"ParamEyeLOpen": 0.0},
  "operations": [
    {"type":"translate","delta":[dx, dy],"selection":{"center":[x,y],"radius":r,"falloff":"smooth"}},
    {"type":"scale","factors":[sx, sy],"pivot":[x,y],"selection":{"rect":[l,t,r,b]}}
  ]
}
```

`selection` 还支持 `indices`、`line`、`soft_radius`、`hardness`、`feather`。单位是固定输入边界，x 向右 y 向下。

## `layer_mesh_update` / `layer_mesh_structure` / `layer_mesh_rebuild`

- `layer_mesh_update`：`{"wrap":2.0,"edgeMode":"DOUBLE"}` 可用；`interiorDensity` 有 UI 范围限制，会报 `outside its UI range`。
- `layer_mesh_structure`：小图层会报 `has no interior inside its edge band to rebuild`。
- `layer_mesh_rebuild`：能跑，但对形变类缺陷**没有视觉效果**，别拿它当修复手段。

## 状态与并发

- 写成功后 state 末段自增（`:1:1` → `:1:2`）。
- 用旧 state 报 `state_conflict`，含 `expected_state` / `actual_state`。
- 一次只提交一批同质改动，改完立刻渲染核对。

## 错误速查

| 报错 | 含义 |
| --- | --- |
| `Tool layer_mesh_update not found` | 该操作不是独立工具，走 `workspace_call` |
| `arguments.request: missing path, state` | `import_psd` 缺 `path`（或 `state`） |
| `unsaved_changes` | 先 `save_as` 再导入 |
| `state_conflict` | 重新 inspect 取最新 state |
| `interiorDensity is outside its UI range` | 该参数有 UI 限值，换 wrap/edgeMode |
| `io_error: zip END header not found` | 用 `project_open` 打开了 PSD，改用 `import_psd` |
| 401 | 令牌用了面板上的掩码值，去注册表取真值 |
