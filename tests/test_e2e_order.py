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


class TestE2EOrder(unittest.TestCase):
    """全链路 E2E 测试：菜单/价格/库存查询"""

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
        resp = requests.post(
            f"{API_BASE}/chat",
            json={
                "message": "有哪些奶茶？我想看看价格和有没有货",
                "user_id": "e2e_test_user",
                "chat_id": "e2e_test_chat",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self.assertIn("reply", data)
        reply = data["reply"]

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
