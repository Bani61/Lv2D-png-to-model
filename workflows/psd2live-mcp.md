# PSD2Live MCP — 程序化绑定与导出

自动绑定出来的模型，十有八九有几处不对：手臂被衣服盖住、闭眼还露眼白、张嘴拉出毛刺。这些在 Cubism 里手点能修，但不可复现、不可验证。

PSD2Live 自带 MCP 服务，可以**用代码改**这些点，改完渲染出图核对。本文是完整玩法。

## 1. 启动

```powershell
Start-Process 'D:\Live2D-Fullbody\tools\PSD2Live-3.6.7\PSD2Live.exe'
Test-NetConnection 127.0.0.1 -Port 23871
```

GUI 一打开，MCP 就跟着启动（无需额外开关），监听 `http://127.0.0.1:23871/mcp`。

- 端口、工具集、令牌都在 **设置 → MCP** 里改；
- 工具集「精简」= 28 个工具（推荐），「完整」= 每个操作一个工具。

## 2. 拿令牌

设置面板上的「显示」按钮给的是**掩码干扰值**，用它一定 401。真令牌在注册表：

```
HKCU\Software\JavaSoft\Prefs\io\github\psd2live\agent
  agent_mcp_bearer_token = /P/U5/Egr/...   ← Java prefs 编码
```

**去掉所有 `/` 就是明文令牌**：

```powershell
$raw = (Get-ItemProperty 'HKCU:\Software\JavaSoft\Prefs\io\github\psd2live\agent').agent_mcp_bearer_token
$token = $raw -replace '/',''
```

然后 `Authorization: Bearer $token`。

## 3. 调用约定（踩过的坑，逐条记）

所有调用都要过三层壳：

```jsonc
// 普通工具
{ "request": { ... } }

// 分组工具还要 op
"tools/call" name="project"      args={ "op": "import_psd", "request": { ... } }
"tools/call" name="view"         args={ "op": "render_model", "request": { ... } }
"tools/call" name="parameter"    args={ "op": "...", "request": { ... } }

// 只有 28 个工具；其余操作走 workspace_call
"tools/call" name="workspace_call" args={ "operation": "rig_edit_structure", "request": { ... } }
```

要点：

1. `layer_mesh_update`、`layer_mesh_structure`、`rig_edit_structure` **不是独立工具**，直接 call 会报 `Tool ... not found`。走 `workspace_call`。
2. 写操作必须带 `state`（形如 `f0cd9790-…:1:1`）和 `project_id`。每次写成功后 state 末段自增；用旧 state 会报 `state_conflict`（含 `expected_state` / `actual_state`）。**每次写前重新 inspect 取 state 最省事。**
3. 任务类操作（`layer_mesh_update`、`project_export_model`）返回 job 对象，看 `data.status == "completed"`，新 state 在 `data.result.state`。
4. `wait_ms` 上限 **30000**，超了报 `arguments.wait_ms: expected 0..30000`。
5. `workspace_inspect` **必须带 `scope`**：`layers` / `objects` / `parameters` / `settings` / `preview` / `generation`。可带 `query`（名称模糊）和 `limit`（≤64）。返回的 `target` 字段才是合法 id（形如 `mesh:ArtMeshHandwearL`）。
6. `project_open` 只吃 `.psd2live` 工程包；PSD 必须走 `project_import_psd`，参数是 `{"path": ..., "state": ...}`（不是 `psd_path`）。
7. 当前工程有未保存改动时，`project_import_psd` 会拒绝：`unsaved_changes`。先 `project` → `save_as` 存一下再导入。

## 4. 典型流程

### 4.1 导入 PSD

```jsonc
"tools/call" name="project"
args={
  "op": "import_psd",
  "request": { "path": "D:\\work\\hero.psd", "state": "<当前 state>" }
}
```

返回 `data.result.project_id` 和 `data.result.state`。之后所有调用都用这两个。

### 4.2 读图层与绘制顺序

```jsonc
name="workspace_inspect", args={"request":{"scope":"objects","query":"Arm","limit":16}}
```

返回示例（名字 → target）：

```
Arm_L  → mesh:ArtMeshHandwearL
Arm_R  → mesh:ArtMeshHandwearR
Topwear_Body → mesh:ArtMeshTopwear
```

绘制顺序：数字越大越靠前。生成时相邻对象差 10，中间有空位可以插入（例如 160 和 170 之间可用 165）。

### 4.3 改绘制顺序（把手臂提到衣服前面）

```jsonc
name="workspace_call"
args={
  "operation": "rig_edit_structure",
  "request": {
    "state": "<state>",
    "project_id": "<pid>",
    "request_id": "<uuid>",
    "edits": [
      {"action":"static","kind":"mesh","id":"ArtMeshHandwearL","draw_order":165},
      {"action":"static","kind":"mesh","id":"ArtMeshHandwearR","draw_order":166}
    ]
  }
}
```

注意 `id` **不带** `mesh:` 前缀（这里和 `workspace_inspect` 的 target 格式不同）。

同一接口还能：改透明度 `"opacity": 0.0`、改混合模式、改裁剪、删变形器。

### 4.4 改关键帧（闭眼时把眼白缩掉）

```jsonc
name="workspace_call"
args={
  "operation": "keyform_apply",
  "request": {
    "state": "<state>", "project_id": "<pid>", "request_id": "<uuid>",
    "changes": [
      {"op":"set","target":"mesh:ArtMeshEyewhiteL","key":{"ParamEyeLOpen":0.0},"geometry":{"scale":0.12}},
      {"op":"set","target":"mesh:ArtMeshEyewhiteR","key":{"ParamEyeROpen":0.0},"geometry":{"scale":0.12}}
    ]
  }
}
```

- `geometry` 只支持整体变换：`originX` / `originY` / `angle` / `scale`，**不能逐顶点**。
- `channels.opacity` 这条路径会**静默失效**（返回 `applied:false`，不报错也不改 state）。要透明度请用 `rig_edit_structure`。
- 逐顶点编辑走 `rig_deform`（`translate` / `scale` / `rotate` + `selection` 的选择区域）。

### 4.5 渲染核对

```jsonc
name="view"
args={
  "op":"render_model",
  "request":{
    "viewport":{"mode":"canvas_rect","left":330,"top":170,"width":120,"height":110},
    "target_long_edge":900,
    "parameters":{"ParamMouthOpenY":1.0},
    "background":"transparent"
  }
}
```

返回 `image/png` 内容块（base64），落盘后用看图工具看一眼。

**判定标准**：改完再渲染，PNG 的 sha256 必须变。没变 = 改动没生效，别继续往下做。

### 4.6 导出

```jsonc
name="project"
args={
  "op":"export_model",
  "request":{
    "state":"<state>","project_id":"<pid>","request_id":"<uuid>",
    "output_directory":"D:\\work\\out"
  }
}
```

产物 20 个文件：`moc3`、`cmo3`、`cdi3`、`physics3`、`can3`、`model3.json`、`psd2live.json`、图集 `*.4096/texture_*.png`、4 个 motion、4 个 exp3。

**导出会重置动作**：`idle` 和 `blink` 回到默认版本。自己调过的要备份后覆盖回去。

## 5. 命名决定绑定

PSD2Live 按图层名判职责。改名字比改结构便宜得多：

| 想要的效果 | 做法 |
| --- | --- |
| 让张嘴能张开 | 把嘴部图层命名为 `张嘴`（或 `mouth_open`）、并设为可见 |
| 让闭眼动作有东西可动 | 提供 `闭眼_L` / `闭眼_R` 图层，否则只能压扁眼线 |
| 让左右手分开 | `Arm_L` / `Arm_R`（`Handwear` 是它的识别词） |
| 让上衣在手臂下面 | 保持 PSD 层序，或导出后改 `draw_order` |

实测：新加图层用**纯 ASCII 名字**（`mouth_open`）能被正确识别；用中文名新建图层会在保存时报 `'charmap' codec` 编码错误（psd-tools 写层名走 macroman）。中文名请沿用 PSD 里已有的图层改名，而不是新建。

## 6. 不要做的事

- 不要在 VTS 运行时改 `vtube.json`（会被覆盖），也不要指望导出的动作保留你的调参。
- 不要用 `layer_mesh_rebuild` 去修"形变难看"——网格密度不是这种缺陷的原因（实测改完渲染逐字节一致）。
- 不要在没有渲染核对的情况下宣称"修好了"。
