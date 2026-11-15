"""PSD2Live MCP client — token discovery, inspection, keyform edits, render, export.

Requires the `mcp` Python package (pip install mcp) and a running PSD2Live GUI
(its MCP server listens on http://127.0.0.1:23871/mcp by default).

Usage:
  python psd2live_mcp.py list
  python psd2live_mcp.py inspect --scope objects --query Mouth
  python psd2live_mcp.py import --psd model.psd
  python psd2live_mcp.py draw-order --target ArtMeshHandwearL:165 --target ArtMeshHandwearR:166
  python psd2live_mcp.py keyform --target mesh:ArtMeshEyewhiteL --key ParamEyeLOpen=0 --scale 0.12
  python psd2live_mcp.py render --out check.png --params ParamMouthOpenY=1.0
  python psd2live_mcp.py export --out-dir out

Token resolution order:
  1. --token
  2. environment PSD2LIVE_TOKEN
  3. Windows registry HKCU\\Software\\JavaSoft\\Prefs\\io\\github\\psd2live\\agent
     (value agent_mcp_bearer_token; Java prefs encoding, strip every '/')
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
import uuid

DEFAULT_URL = os.environ.get("PSD2LIVE_URL", "http://127.0.0.1:23871/mcp")


# --------------------------------------------------------------------------- token


def registry_token() -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\JavaSoft\Prefs\io\github\psd2live\agent",
        )
        with key:
            raw, _ = winreg.QueryValueEx(key, "agent_mcp_bearer_token")
        return raw.replace("/", "")
    except Exception:
        return None


def resolve_token(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("PSD2LIVE_TOKEN")
    if env:
        return env
    tok = registry_token()
    if tok:
        return tok
    raise SystemExit(
        "无法获取 PSD2Live 令牌：请传 --token、设置 PSD2LIVE_TOKEN，"
        "或在 Windows 注册表 HKCU\\Software\\JavaSoft\\Prefs\\io\\github\\psd2live\\agent 中确认"
        " agent_mcp_bearer_token 存在。设置面板上显示的令牌是掩码值，不可用。"
    )


# --------------------------------------------------------------------------- mcp plumbing


class Client:
    def __init__(self, url: str, token: str, timeout: float = 600.0) -> None:
        self.url = url
        self.headers = {"Authorization": f"Bearer {token}"}
        self.timeout = timeout

    async def __aenter__(self) -> "Client":
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        self._cm = streamablehttp_client(self.url, headers=self.headers, timeout=self.timeout)
        read, write, _ = await self._cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self.session = await self._session_cm.__aenter__()
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc) -> None:
        await self._session_cm.__aexit__(*exc)
        await self._cm.__aexit__(*exc)

    async def call(self, tool: str, args: dict) -> dict:
        res = await self.session.call_tool(tool, args)
        text = "".join(getattr(b, "text", "") for b in (res.content or []))
        if not text:
            return {"ok": False, "error": "empty response"}
        return json.loads(text.splitlines()[0])

    async def call_op(self, operation: str, request: dict) -> dict:
        return await self.call("workspace_call", {"operation": operation, "request": request})

    async def state_of(self) -> tuple[str, str]:
        insp = await self.call("workspace_inspect", {"request": {"scope": "layers", "limit": 1}})
        data = insp.get("data") or {}
        return data.get("state", ""), data.get("project_id", "")

    async def render(self, out: str, params: dict, box: tuple[int, int, int, int] | None, long_edge: int) -> None:
        request: dict = {
            "target_long_edge": long_edge,
            "parameters": params,
            "background": "transparent",
        }
        if box:
            left, top, width, height = box
            request["viewport"] = {"mode": "canvas_rect", "left": left, "top": top, "width": width, "height": height}
        res = await self.session.call_tool("view", {"op": "render_model", "request": request})
        for block in res.content or []:
            if getattr(block, "type", None) == "image":
                with open(out, "wb") as fh:
                    fh.write(base64.b64decode(block.data))
                print("WROTE", out)
                return
        print("NO IMAGE in response")


# --------------------------------------------------------------------------- helpers


def kv_pairs(items: list[str] | None) -> dict:
    out = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"参数格式应为 key=value：{item}")
        k, v = item.split("=", 1)
        out[k] = float(v)
    return out


def parse_targets(items: list[str] | None) -> list[tuple[str, int]]:
    out = []
    for item in items or []:
        if ":" not in item:
            raise SystemExit(f"目标格式应为 Name:order：{item}")
        name, order = item.rsplit(":", 1)
        out.append((name, int(order)))
    return out


# --------------------------------------------------------------------------- commands


async def cmd_list(client: Client, args) -> None:
    res = await client.call("workspace_list_operations", {"request": {"limit": args.limit}})
    for item in (res.get("data") or {}).get("items", []):
        print(f"{item.get('name',''):28s} {item.get('summary','')[:70]}")


async def cmd_inspect(client: Client, args) -> None:
    req = {"scope": args.scope, "limit": args.limit}
    if args.query:
        req["query"] = args.query
    res = await client.call("workspace_inspect", {"request": req})
    data = res.get("data") or {}
    print("state", data.get("state"), "project", data.get("project_id"))
    for item in data.get("items", []):
        print(f"{item.get('name',''):32s} {item.get('target','')}")


async def cmd_import(client: Client, args) -> None:
    state, pid = await client.state_of()
    if args.save_first and pid:
        saved = await client.call("project", {"op": "save_as", "request": {
            "state": state, "project_id": pid, "path": args.save_first,
        }})
        print("SAVE_AS", (saved.get("data") or {}).get("status"))
    res = await client.call("project", {"op": "import_psd", "request": {"path": args.psd, "state": state}})
    data = (res.get("data") or {}).get("result") or {}
    print("IMPORT", json.dumps(data, ensure_ascii=False)[:400])


async def cmd_draw_order(client: Client, args) -> None:
    state, pid = await client.state_of()
    edits = [
        {"action": "static", "kind": "mesh", "id": name, "draw_order": order}
        for name, order in parse_targets(args.target)
    ]
    res = await client.call_op("rig_edit_structure", {
        "state": state, "project_id": pid, "request_id": str(uuid.uuid4()), "edits": edits,
    })
    print(json.dumps(res.get("data") or res.get("error"), ensure_ascii=False)[:400])


async def cmd_keyform(client: Client, args) -> None:
    state, pid = await client.state_of()
    changes = []
    for target in args.target or []:
        changes.append({
            "op": "set",
            "target": target,
            "key": kv_pairs(args.key),
            "geometry": {"scale": args.scale},
        })
    res = await client.call("keyform_apply", {"request": {
        "state": state, "project_id": pid, "request_id": str(uuid.uuid4()), "changes": changes,
    }})
    print(json.dumps(res.get("data") or res.get("error"), ensure_ascii=False)[:400])


async def cmd_render(client: Client, args) -> None:
    box = tuple(int(x) for x in args.box.split(",")) if args.box else None
    await client.render(args.out, kv_pairs(args.params), box, args.long_edge)


async def cmd_export(client: Client, args) -> None:
    state, pid = await client.state_of()
    res = await client.call("project", {"op": "export_model", "request": {
        "state": state, "project_id": pid,
        "request_id": str(uuid.uuid4()), "output_directory": args.out_dir,
    }})
    data = res.get("data") or {}
    print("EXPORT", data.get("status"), data.get("error") or "")


async def amain(args) -> None:
    token = resolve_token(args.token)
    async with Client(args.url, token, timeout=args.timeout) as client:
        handler = {
            "list": cmd_list, "inspect": cmd_inspect, "import": cmd_import,
            "draw-order": cmd_draw_order, "keyform": cmd_keyform,
            "render": cmd_render, "export": cmd_export,
        }[args.command]
        await handler(client, args)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PSD2Live MCP client")
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--token", default=None)
    p.add_argument("--timeout", type=float, default=600.0)
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("list", help="列出所有可用操作")
    s.add_argument("--limit", type=int, default=200)

    s = sub.add_parser("inspect", help="读取工程对象")
    s.add_argument("--scope", default="objects",
                   choices=["layers", "objects", "parameters", "settings", "preview", "generation"])
    s.add_argument("--query", default=None)
    s.add_argument("--limit", type=int, default=32)

    s = sub.add_parser("import", help="导入 PSD")
    s.add_argument("--psd", required=True)
    s.add_argument("--save-first", default=None, help="先 save_as 到此路径，避免 unsaved_changes")

    s = sub.add_parser("draw-order", help="修改绘制顺序")
    s.add_argument("--target", action="append", help="ArtMeshName:order，可重复")

    s = sub.add_parser("keyform", help="在指定关键帧设置整体变换")
    s.add_argument("--target", action="append", help="mesh:ArtMeshXxx，可重复")
    s.add_argument("--key", action="append", required=True, help="ParamName=value，可重复")
    s.add_argument("--scale", type=float, default=1.0)

    s = sub.add_parser("render", help="渲染 PNG")
    s.add_argument("--out", required=True)
    s.add_argument("--params", action="append", help="ParamName=value，可重复")
    s.add_argument("--box", default=None, help="left,top,width,height（画布像素坐标）")
    s.add_argument("--long-edge", type=int, default=900)

    s = sub.add_parser("export", help="导出模型")
    s.add_argument("--out-dir", required=True)

    return p


if __name__ == "__main__":
    asyncio.run(amain(build_parser().parse_args(sys.argv[1:])))
