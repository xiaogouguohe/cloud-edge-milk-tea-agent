"""
全链路 E2E 测试：从前端入口（Supervisor API）到订单查询

链路：POST /api/chat → SupervisorAgent → OrderAgent (A2A) → Order MCP Server

测试会自动启动所需服务（若未运行），结束后自动清理。
测试用例自行往数据库写入产品数据，不依赖启动时的初始库存。

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

# E2E 测试用产品数据：(name, description, price, stock)
E2E_PRODUCTS_FULL = [
    ("云边茉莉", "优质茉莉花茶", 18.00, 100),
    ("桂花云露", "桂花乌龙茶", 20.00, 80),
    ("云雾观音", "铁观音茶", 22.00, 60),
    ("珍珠奶茶", "经典珍珠奶茶", 15.00, 120),
    ("红豆奶茶", "红豆奶茶", 16.00, 100),
]
E2E_PRODUCTS_JASMINE = [("云边茉莉", "优质茉莉花茶", 18.00, 100)]
E2E_PRODUCTS_LOW_STOCK = [("云边茉莉", "优质茉莉花茶", 18.00, 5)]  # 库存不足场景
E2E_PRODUCTS_OSMANTHUS = [("桂花云露", "桂花乌龙茶", 20.00, 80)]


def _get_e2e_db():
    """获取与 MCP Server 相同的数据库连接（供 E2E 写入测试数据）"""
    try:
        from database.db_manager import DatabaseManager
        from database.config import DB_TYPE, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
        if DB_TYPE == "mysql":
            return DatabaseManager(
                db_type="mysql",
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE,
            )
        return DatabaseManager(db_type="sqlite")
    except Exception as e:
        raise RuntimeError(f"E2E 无法连接数据库: {e}") from e


def _prepare_e2e_products(products: list):
    """清空 products 表并插入指定数据，供 E2E 用例使用。先删 order_items/orders 以解除外键约束。"""
    db = _get_e2e_db()
    db.execute("DELETE FROM order_items")
    db.execute("DELETE FROM orders")
    db.execute("DELETE FROM products")
    db.connection.commit()
    cursor = db.connection.cursor()
    for name, desc, price, stock in products:
        if db.db_type == "sqlite":
            cursor.execute(
                "INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
                (name, desc, price, stock),
            )
        else:
            cursor.execute(
                "INSERT INTO products (name, description, price, stock) VALUES (%s, %s, %s, %s)",
                (name, desc, price, stock),
            )
    db.connection.commit()

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
    data = _chat_full(user_id, chat_id, message, role, timeout, retries, verbose)
    return data.get("reply", "")


def _chat_full(user_id: str, chat_id: str, message: str, role: str = None, timeout: int = 45, retries: int = 3, verbose: bool = True) -> dict:
    """发送聊天请求，返回完整响应（含 reply、pending_action 等）"""
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
                if data.get("pending_action"):
                    print(f"  [pending_action] {data['pending_action']}")
                if "session_id" in data:
                    print(f"  [session_id] {data['session_id']}")
            if "系统繁忙" in reply and attempt < retries - 1:
                time.sleep(3)
                continue
            return data
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
        _prepare_e2e_products(E2E_PRODUCTS_FULL)
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
        _prepare_e2e_products(E2E_PRODUCTS_JASMINE)
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
        _prepare_e2e_products(E2E_PRODUCTS_LOW_STOCK)  # 库存仅 5
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
        _prepare_e2e_products(E2E_PRODUCTS_JASMINE)
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

    def test_product_update_staff(self):
        """
        场景：店员修改产品单价/库存
        1. 店员身份请求修改 → 返回 pending_action
        2. 直接调用 POST /api/product/update 执行修改（绕过前端确认）
        3. 查询菜单验证修改生效
        """
        _prepare_e2e_products(E2E_PRODUCTS_JASMINE)
        user_id = "20001"
        chat_id = "e2e_product_update"

        print("\n--- 第一步：店员请求修改产品 ---")
        data = _chat_full(
            user_id, chat_id,
            "把云边茉莉的单价改成20元",
            role="staff",
        )
        reply = data.get("reply", "")
        pending = data.get("pending_action")

        self.assertTrue(
            pending is not None and pending.get("type") == "product_update",
            f"应返回 pending_action，实际: {data}",
        )
        self.assertEqual(pending.get("productName"), "云边茉莉")
        self.assertIn("price", pending.get("proposed", {}))
        self.assertEqual(pending["proposed"]["price"], 20)

        print("\n--- 第二步：直接调用 API 执行修改 ---")
        resp = requests.post(
            f"{API_BASE}/product/update",
            json={"productName": "云边茉莉", "price": 20},
            timeout=10,
        )
        resp.raise_for_status()
        upd = resp.json()
        self.assertEqual(upd.get("status"), "success")

        print("\n--- 第三步：查询菜单验证修改生效 ---")
        verify_data = _chat_full(user_id, chat_id, "云边茉莉多少钱？", role="staff", verbose=True)
        verify_reply = verify_data.get("reply", "")
        self.assertTrue(
            "20" in verify_reply or "¥20" in verify_reply,
            f"修改后价格应为 20，实际: {verify_reply[:200]}...",
        )

        # 恢复原价，避免影响其他测试
        requests.post(
            f"{API_BASE}/product/update",
            json={"productName": "云边茉莉", "price": 18},
            timeout=10,
        )

    def test_order_history_query(self):
        """
        场景4：先下单，再查询历史订单
        """
        _prepare_e2e_products(E2E_PRODUCTS_OSMANTHUS)
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
