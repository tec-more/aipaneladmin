"""
BUG-T15-012 复现取证：dry-run 并发槽泄漏（进程内降级无看门狗）

背景：回归中发现 usr:1 的 dry-run 槽位被长期占用（42901 item=concurrency remaining=0），
Redis 未启用 → 进程内 _mem_conc 计数无 TTL/看门狗，泄漏后仅重启可恢复。

复现矩阵（每种模式后紧跟一次探测 dry-run 验证槽位是否释放）：
- P0 控制组：流式完整消费 → 槽位应释放
- P1 非流式整体读取（httpx 非 stream 模式 post）→ 槽位应释放
- P2 流式中途断开（读 1 帧后关闭连接，模拟用户关闭浏览器）→ 槽位应释放（finally 兜底）

运行: .venv/Scripts/python.exe tests/_t15_bug012_repro.py
"""
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from base.common.security import create_access_token

BASE = "http://127.0.0.1:9998"


def make_token() -> str:
    return create_access_token({"typ": "usr", "sub": "1"}, expires_delta=timedelta(hours=2))


GRAPH = {
    "schema_version": 2,
    "nodes": [
        {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
         "data": {"outputs": [{"name": "query", "type": "string"}]}},
        {"id": "e1", "type": "end", "position": {"x": 300, "y": 0},
         "data": {"inputs": [{"name": "answer", "type": "string", "from": "s1.query"}]}},
    ],
    "edges": [{"id": "e1", "source": "s1", "target": "e1",
               "sourceHandle": "out", "targetHandle": "in"}],
    "variables": [],
}


async def probe(cli, headers, wid, tag) -> str:
    """探测槽位：再发起一次 dry-run（流式读尽），返回状态码"""
    async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                          headers=headers, json={"inputs": {"query": "probe"}},
                          timeout=30.0) as resp:
        code = resp.status_code
        if code == 200:
            async for _ in resp.aiter_lines():
                pass
        else:
            body = (await resp.aread()).decode("utf-8", "replace")[:160]
            print(f"    [{tag}] 探测: {code} body={body}", flush=True)
            return f"{code}"
        print(f"    [{tag}] 探测: {code}（槽位空闲）", flush=True)
        return f"{code}"


async def main():
    headers = {"Authorization": f"Bearer {make_token()}"}
    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
        r = await cli.post("/v1/agent/u/workflows", headers=headers,
                           json={"name": "BUG012复现靶场", "graph_json": GRAPH})
        wid = r.json()["data"]["id"]
        try:
            # ---- P0 控制组：流式完整消费
            print("[P0] 流式完整消费 dry-run ...", flush=True)
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "p0"}},
                                  timeout=30.0) as resp:
                assert resp.status_code == 200, f"P0 初次执行被拒: {resp.status_code}"
                async for _ in resp.aiter_lines():
                    pass
            await asyncio.sleep(0.5)
            p0 = await probe(cli, headers, wid, "P0")

            # ---- P1 非流式整体读取（G1-DIS-02 模式）
            print("[P1] 非流式 post 整体读取 dry-run ...", flush=True)
            r1 = await cli.post(f"/v1/agent/u/workflows/{wid}/dry-run",
                                headers=headers, json={"inputs": {"query": "p1"}})
            print(f"    [P1] 初次执行: {r1.status_code}, body_len={len(r1.content)}", flush=True)
            await asyncio.sleep(0.5)
            p1 = await probe(cli, headers, wid, "P1")

            # ---- P2 流式中途断开（读 1 帧即关闭）
            print("[P2] 流式中途断开（读 1 帧后关闭连接）...", flush=True)
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "p2"}},
                                  timeout=30.0) as resp:
                assert resp.status_code == 200
                async for _ in resp.aiter_lines():
                    break  # 读一帧即断开
            # 连接已关闭；等待服务端感知
            await asyncio.sleep(2.0)
            p2 = await probe(cli, headers, wid, "P2")

            # 再等待 65s 验证进程内计数是否有任何自愈（对照 Redis 路径 60s 看门狗语义）
            if p2 == "429":
                print("[P2+] 等待 65s 验证进程内降级是否自愈 ...", flush=True)
                await asyncio.sleep(65)
                p2b = await probe(cli, headers, wid, "P2+65s")
            else:
                p2b = "skip"

            print("\n===== 复现结果矩阵 =====")
            print(f"P0 完整消费后槽位: {'释放' if p0 == '200' else '泄漏(' + p0 + ')'}")
            print(f"P1 非流式读取后槽位: {'释放' if p1 == '200' else '泄漏(' + p1 + ')'}")
            print(f"P2 中途断开后槽位: {'释放' if p2 == '200' else '泄漏(' + p2 + ')'}")
            print(f"P2+65s 自愈验证: {p2b}")
        finally:
            await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=headers)
            print("[清理完成]")


asyncio.run(main())
