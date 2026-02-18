"""
全链路 E2E 测试：从前端入口（Supervisor API）到订单查询

链路：POST /api/chat → SupervisorAgent → OrderAgent (A2A) → Order MCP Server

测试会自动启动所需服务（若未运行），结束后自动清理。

运行方式：
  python3 -m unittest tests.test_e2e_order -v
"""
import os
import sys
import time
import unittest
import subprocess
import signal
import atexit
from pathlib import Path
from typing import Tuple, List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests

API_BASE = "http://localhost:8000/api"

# 服务配置：(health_url, 启动命令, 描述)，使用当前 Python 解释器
def _services():
    exe = sys.executable
    return [
        ("http://localhost:10002/mcp/health", [exe, "order_mcp_server/run_order_mcp_server.py"], "Order MCP Server (10002)"),
        ("http://localhost:10006/a2a/health", [exe, "order_agent/run_order_agent.py"], "Order Agent (10006)"),
        ("http://localhost:8000/api/health", [exe, "-m", "supervisor_agent.api"], "Supervisor API (8000)"),
    ]

# 本测试启动的进程 PID，用于清理
_started_pids: List[int] = []


def _check_services() -> Tuple[bool, str]:
    """检查依赖服务是否已启动"""
    for url, _, name in _services():
        try:
            r = requests.get(url, timeout=2)
            if r.status_code != 200:
                return False, f"{name} 未就绪 (HTTP {r.status_code})"
        except Exception as e:
            return False, f"{name} 未启动: {e}"
    return True, ""


def _start_services() -> bool:
    """启动所有服务，返回是否成功"""
    global _started_pids
    _started_pids = []

    for url, cmd, name in _services():
        # 若已就绪则跳过
        try:
            if requests.get(url, timeout=1).status_code == 200:
                continue
        except Exception:
            pass

        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        _started_pids.append(proc.pid)
        time.sleep(2)  # 给进程一点启动时间
        # 等待当前服务就绪后再启动下一个（依赖顺序）
        for _ in range(20):
            try:
                if requests.get(url, timeout=1).status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)

    # 最终确认所有服务就绪
    for _ in range(20):
        ok, _ = _check_services()
        if ok:
            return True
        time.sleep(1)
    return False


def _stop_services():
    """停止本测试启动的服务"""
    global _started_pids
    for pid in _started_pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
    _started_pids = []


# 注册退出时清理
atexit.register(_stop_services)


def _chat(user_id: str, chat_id: str, message: str, role: str = None, timeout: int = 45, retries: int = 3, verbose: bool = True) -> str:
    """发送聊天请求，返回 reply。系统繁忙时自动重试"""
    payload = {"message": message, "user_id": user_id, "chat_id": chat_id}
    if role:
        payload["role"] = role
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.post(f"{API_BASE}/chat", json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            reply = data.get("reply", "")
            if verbose:
                print(f"\n  [请求] {message}")
                print(f"  [实际返回] {reply}")
                if "session_id" in data:
                    print(f"  [session_id] {data['session_id']}")
            if "系统繁忙" in reply and attempt < retries - 1:
                time.sleep(3)
                continue
            return reply
        except Exception as e:
            last_err = e
            if verbose:
                print(f"\n  [请求] {message}")
                print(f"  [异常] {e}")
            if attempt < retries - 1:
                time.sleep(2)
    raise last_err


def _verify_mcp_has_order_tools() -> bool:
    """验证 MCP 已注册 order-create-order，避免 404"""
    try:
        r = requests.get("http://localhost:10002/mcp/tools", timeout=5)
        if r.status_code != 200:
            return False
        tools = [t.get("name") for t in r.json().get("tools", [])]
        return "order-create-order" in tools
    except Exception:
        return False


class TestE2EOrder(unittest.TestCase):
    """全链路 E2E 测试：菜单/价格/库存查询、用户下单"""

    @classmethod
    def setUpClass(cls):
        """确保服务已启动（若未运行则自动启动）"""
        ok, err = _check_services()
        if not ok:
            if _start_services():
                cls._we_started = True
            else:
                raise RuntimeError(f"服务启动失败: {err}")
        else:
            cls._we_started = False
        # 验证 MCP 已注册 order-create-order，避免 404
        if not _verify_mcp_has_order_tools():
            raise RuntimeError(
                "MCP 未注册 order-create-order，请重启 Order MCP Server: "
                "python3 order_mcp_server/run_order_mcp_server.py"
            )

    @classmethod
    def tearDownClass(cls):
        """若由本测试启动的服务，则清理"""
        if getattr(cls, "_we_started", False):
            _stop_services()

    def test_menu_and_stock_query(self):
        """
        全链路：查询所有产品的价格和库存
        无需登录，直接查询即可
        """
        msg = "有哪些奶茶？我想看看价格和有没有货"
        resp = requests.post(
            f"{API_BASE}/chat",
            json={
                "message": msg,
                "user_id": "e2e_test_user",
                "chat_id": "e2e_test_chat",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self.assertIn("reply", data)
        reply = data["reply"]
        print(f"\n  [请求] {msg}")
        print(f"  [实际返回] {reply}")

        # 验证：应包含价格、库存状态、产品列表
        self.assertTrue(
            "¥" in reply or "元" in reply,
            f"应能获取价格信息，实际: {reply[:200]}...",
        )
        self.assertTrue(
            any(kw in reply for kw in ["有货", "售罄", "库存"]),
            f"应能获取库存状态，实际: {reply[:200]}...",
        )
        self.assertTrue(
            any(kw in reply for kw in ["茉莉", "桂花", "珍珠", "红豆", "奶茶"]),
            f"应能获取产品列表，实际: {reply[:200]}...",
        )

    def test_order_incomplete_then_success(self):
        """
        场景1：下单若干产品，信息没给完全 → 用户补全 → 成功下单
        """
        user_id = "10001"
        chat_id = "e2e_order_incomplete"
        print("\n--- 第一轮：缺糖度/冰度 ---")
        # 第一轮：只说产品名，缺糖度、冰度
        reply1 = _chat(user_id, chat_id, "我要一杯云边茉莉", role="customer")
        # 应追问缺失信息（糖度或冰度）
        self.assertTrue(
            any(kw in reply1 for kw in ["糖", "甜度", "冰", "冰度", "规格"]),
            f"应追问糖度/冰度，实际: {reply1[:300]}...",
        )
        print("\n--- 第二轮：补全信息 ---")
        # 第二轮：补全信息
        reply2 = _chat(user_id, chat_id, "少糖去冰", role="customer")
        # 应下单成功，包含订单信息
        self.assertTrue(
            any(kw in reply2 for kw in ["订单", "ORDER_", "¥", "成功", "已为您"]),
            f"应下单成功，实际: {reply2[:300]}...",
        )

    def test_order_insufficient_stock(self):
        """
        场景2：下单若干产品，库存不足 → 告知用户
        通过下单数量超过库存（如 1000 杯）触发
        """
        user_id = "10002"
        chat_id = "e2e_order_stock"
        print("\n--- 库存不足场景 ---")
        reply = _chat(
            user_id, chat_id,
            "我要1000杯云边茉莉，少糖去冰",
            role="customer",
        )
        self.assertTrue(
            any(kw in reply for kw in ["库存不足", "库存", "售罄", "缺货"]),
            f"应告知库存不足，实际: {reply[:300]}...",
        )

    def test_order_success(self):
        """
        场景3：下单若干产品，成功 → 告知用户
        """
        user_id = "10003"
        chat_id = "e2e_order_success"
        print("\n--- 下单成功场景 ---")
        reply = _chat(
            user_id, chat_id,
            "我要一杯云边茉莉，少糖去冰",
            role="customer",
        )
        self.assertTrue(
            any(kw in reply for kw in ["订单", "ORDER_", "¥", "成功", "已为您", "总价"]),
            f"应成功下单并告知用户，实际: {reply[:300]}...",
        )

    def test_order_history_query(self):
        """
        场景4：先下单，再查询历史订单
        """
        user_id = "10004"
        chat_id = "e2e_order_history"

        print("\n--- 第一步：下单 ---")
        # 先下单
        reply1 = _chat(
            user_id, chat_id,
            "我要一杯桂花云露，少糖少冰",
            role="customer",
        )
        self.assertTrue(
            any(kw in reply1 for kw in ["订单", "ORDER_", "¥", "成功", "桂花"]),
            f"应先下单成功，实际: {reply1[:300]}...",
        )

        print("\n--- 第二步：查询历史订单 ---")
        # 再查历史订单
        reply2 = _chat(
            user_id, chat_id,
            "帮我查一下我的订单记录",
            role="customer",
        )
        self.assertTrue(
            any(kw in reply2 for kw in ["订单", "桂花", "ORDER_", "¥"]),
            f"应能查到刚下的订单，实际: {reply2[:300]}...",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
