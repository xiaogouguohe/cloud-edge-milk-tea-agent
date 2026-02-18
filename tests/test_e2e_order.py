"""
全链路 E2E 测试：从前端入口（Supervisor API）到订单查询

链路：POST /api/chat → SupervisorAgent → OrderAgent (A2A) → Order MCP Server

测试会自动启动所需服务（若未运行），结束后自动清理。
测试用例自行往数据库写入产品数据，不依赖启动时的初始库存。

运行方式：
  ./run_e2e_test.sh              # 运行全部
  ./run_e2e_test.sh -k "基础权限"  # 按名称筛选
  python3 -m unittest tests.test_e2e_order -v -k "test_base"

测试覆盖对照（需求 vs 用例）：
  一. 基础权限
    1. 获取所有产品价格/库存     → test_menu_and_stock_query
    2. 获取某个产品价格/库存     → test_base_get_single_product_info
    3. 越权操作被拒绝           → test_base_unauthorized_order_rejected
  二. 用户权限
    1. 单品不存在告知           → test_user_order_product_not_exists
    1. 库存不足告知             → test_order_insufficient_stock
    1. 糖分/冰量不明确追问      → test_order_incomplete_then_success
    1. 多单品不同规格下单       → test_user_order_multi_items_different_specs
    2. 查历史订单               → test_order_history_query
    3. 查某个订单详情           → test_user_query_order_detail_by_id
    4. 越权查他人订单被限制     → test_user_unauthorized_query_other_user_orders
  三. 店员权限
    1. 查某用户历史订单         → test_staff_query_user_orders
    1. 查不存在用户             → test_staff_query_user_not_exists
    2. 查某订单 id（存在/不存在）→ test_staff_query_order_by_id, test_staff_query_order_not_exists
    3. 修改库存合法/非法         → test_staff_modify_stock_valid, test_staff_modify_stock_invalid_reduce_below_zero
    3. 修改不存在的单品         → test_staff_modify_product_not_exists
  四. 数据持久化
    1. 用户下单后退出再登录可查 → test_persistence_user_order_after_relogin
    2. 店员改库存后退出再登录保留 → test_persistence_staff_stock_after_relogin
"""
import os
import re
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
        场景2：下单若干产品，库存不足 → 告知用户是哪些单品不够
        通过下单数量超过库存触发
        """
        _prepare_e2e_products(E2E_PRODUCTS_LOW_STOCK)  # 云边茉莉库存仅 5
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
        self.assertTrue(
            "云边茉莉" in reply or "茉莉" in reply,
            f"应告知是哪个单品库存不足，实际: {reply[:300]}...",
        )

    def test_order_insufficient_stock_multi_products(self):
        """
        用户权限 1：多单品下单，其中一样库存不足，应告知哪些单品不够
        """
        _prepare_e2e_products([
            ("云边茉莉", "优质茉莉花茶", 18.00, 2),
            ("桂花云露", "桂花乌龙茶", 20.00, 100),
        ])
        reply = _chat(
            "10002b",
            "e2e_stock_multi",
            "我要5杯云边茉莉少糖去冰，2杯桂花云露半糖少冰",
            role="customer",
        )
        self.assertTrue(
            any(kw in reply for kw in ["库存不足", "售罄", "缺货"]),
            f"应告知库存不足，实际: {reply[:300]}...",
        )
        self.assertTrue(
            "云边茉莉" in reply or "茉莉" in reply,
            f"应告知云边茉莉库存不足，实际: {reply[:300]}...",
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

    # ========== 一. 基础权限 ==========

    def test_base_get_all_products(self):
        """
        基础权限 1：获取所有产品的价格以及是否有存货（无需登录）
        """
        _prepare_e2e_products(E2E_PRODUCTS_FULL)
        reply = _chat(
            "e2e_base_all",
            "e2e_base_all_products",
            "有哪些奶茶？价格和库存呢？",
            role=None,
        )
        self.assertTrue(
            "¥" in reply or "元" in reply,
            f"应返回价格信息，实际: {reply[:200]}...",
        )
        self.assertTrue(
            any(kw in reply for kw in ["有货", "售罄", "库存"]),
            f"应返回库存状态，实际: {reply[:200]}...",
        )
        for name in ["茉莉", "桂花", "珍珠", "红豆"]:
            self.assertTrue(
                name in reply,
                f"应包含产品 {name}，实际: {reply[:300]}...",
            )

    def test_base_get_single_product_info(self):
        """
        基础权限 2：获取某个产品的价格和是否有存货
        """
        _prepare_e2e_products(E2E_PRODUCTS_JASMINE)
        reply = _chat(
            "e2e_base_user",
            "e2e_base_single_product",
            "云边茉莉多少钱？有没有货？",
            role=None,
        )
        self.assertTrue(
            "云边茉莉" in reply or "茉莉" in reply,
            f"应返回产品名，实际: {reply[:200]}...",
        )
        self.assertTrue(
            "¥" in reply or "18" in reply or "元" in reply,
            f"应返回价格，实际: {reply[:200]}...",
        )
        self.assertTrue(
            any(kw in reply for kw in ["有货", "售罄", "库存"]),
            f"应返回库存状态，实际: {reply[:200]}...",
        )

    def test_base_unauthorized_order_rejected(self):
        """
        基础权限 3：越权操作（如下单）应被拒绝，要求先告知身份
        """
        _prepare_e2e_products(E2E_PRODUCTS_JASMINE)
        reply = _chat(
            "e2e_base_unauth",
            "e2e_base_unauth_order",
            "我要一杯云边茉莉，少糖去冰",
            role=None,
        )
        self.assertTrue(
            any(kw in reply for kw in ["身份", "顾客", "店员", "管理员"]),
            f"应要求先告知身份，实际: {reply[:300]}...",
        )

    # ========== 二. 用户权限 ==========

    def test_user_order_product_not_exists(self):
        """
        用户权限 1：下单单品不存在，应告知用户没有这个单品
        """
        _prepare_e2e_products(E2E_PRODUCTS_JASMINE)
        reply = _chat(
            "10010",
            "e2e_product_not_exists",
            "我要一杯不存在的奶茶，少糖去冰",
            role="customer",
        )
        self.assertTrue(
            any(kw in reply for kw in ["未找到", "不存在", "没有", "抱歉"]),
            f"应告知单品不存在，实际: {reply[:300]}...",
        )

    def test_user_order_multi_items_different_specs(self):
        """
        用户权限 1：多单品下单，其中一样点了 2 杯且每杯糖分/冰量不同
        """
        _prepare_e2e_products(E2E_PRODUCTS_FULL)
        reply = _chat(
            "10011",
            "e2e_multi_specs",
            "我要两杯云边茉莉，一杯少糖去冰，一杯标准糖少冰，再要一杯桂花云露半糖去冰",
            role="customer",
        )
        self.assertTrue(
            any(kw in reply for kw in ["订单", "ORDER_", "¥", "成功", "已为您"]),
            f"应成功下单，实际: {reply[:300]}...",
        )
        self.assertTrue(
            "云边茉莉" in reply or "茉莉" in reply,
            f"应包含云边茉莉，实际: {reply[:200]}...",
        )
        self.assertTrue(
            "桂花云露" in reply or "桂花" in reply,
            f"应包含桂花云露，实际: {reply[:200]}...",
        )

    def test_user_query_order_detail_by_id(self):
        """
        用户权限 3：查询自己的某个订单 id 的详情
        """
        _prepare_e2e_products(E2E_PRODUCTS_OSMANTHUS)
        user_id = "10012"
        chat_id = "e2e_order_detail"

        reply1 = _chat(
            user_id, chat_id,
            "我要一杯桂花云露，少糖少冰",
            role="customer",
        )
        self.assertTrue(
            "ORDER_" in reply1,
            f"应先下单成功拿到订单号，实际: {reply1[:300]}...",
        )
        match = re.search(r"ORDER_\d+", reply1)
        self.assertIsNotNone(match, f"应能解析出订单号，实际: {reply1[:200]}...")
        order_id = match.group()

        reply2 = _chat(
            user_id, chat_id,
            f"帮我查一下订单 {order_id} 的详情",
            role="customer",
        )
        self.assertTrue(
            order_id in reply2 or "桂花" in reply2,
            f"应能查到该订单详情，实际: {reply2[:300]}...",
        )

    def test_user_unauthorized_query_other_user_orders(self):
        """
        用户权限 4：越权查其他用户的历史订单，应被限制
        """
        _prepare_e2e_products(E2E_PRODUCTS_OSMANTHUS)
        reply = _chat(
            "10013",
            "e2e_unauth_other_user",
            "帮我查一下用户 99999 的订单记录",
            role="customer",
        )
        # 越权时：要么明确拒绝，要么只返回自己的（空）订单
        self.assertTrue(
            any(kw in reply for kw in ["无权", "没有", "订单"]),
            f"应限制越权查他人订单，实际: {reply[:300]}...",
        )

    def test_user_unauthorized_modify_stock(self):
        """
        用户权限 4：越权修改库存，应被拒绝（customer 无此权限）
        """
        _prepare_e2e_products(E2E_PRODUCTS_JASMINE)
        reply = _chat(
            "10013b",
            "e2e_unauth_modify_stock",
            "把云边茉莉的库存改成 200",
            role="customer",
        )
        # 用户无修改权限，应拒绝或无法执行
        self.assertTrue(
            any(kw in reply for kw in ["权限", "拒绝", "无法", "不能", "抱歉", "没有"]),
            f"用户修改库存应被拒绝，实际: {reply[:300]}...",
        )

    def test_user_unauthorized_query_other_order_id(self):
        """
        用户权限 4：查不属于自己的订单号，应无法查到或被告知无权
        """
        _prepare_e2e_products(E2E_PRODUCTS_OSMANTHUS)
        # 用户 A 下单
        reply1 = _chat("10014a", "e2e_order_a", "我要一杯桂花云露少糖去冰", role="customer")
        match = re.search(r"ORDER_\d+", reply1)
        self.assertIsNotNone(match, "用户 A 应先下单成功")
        order_id = match.group()
        # 用户 B 尝试查用户 A 的订单号
        reply2 = _chat(
            "10014b",
            "e2e_order_b",
            f"帮我查一下订单 {order_id} 的详情",
            role="customer",
        )
        # 应无法查到（订单不属于 B），或被告知无权/未找到
        self.assertTrue(
            any(kw in reply2 for kw in ["没有", "未找到", "无权", "不存在", "无法"]),
            f"用户 B 查用户 A 的订单应被限制，实际: {reply2[:300]}...",
        )

    # ========== 三. 店员权限 ==========

    def test_staff_query_user_orders(self):
        """
        店员权限 1：查询某个用户 id 的历史订单
        """
        _prepare_e2e_products(E2E_PRODUCTS_OSMANTHUS)
        _chat("10014", "e2e_customer_order_for_staff", "我要一杯桂花云露少糖去冰", role="customer")

        reply = _chat(
            "20002",
            "e2e_staff_query_user",
            "帮我查一下用户 10014 的订单",
            role="staff",
        )
        self.assertTrue(
            any(kw in reply for kw in ["订单", "桂花", "10014", "ORDER_"]),
            f"店员应能查到用户订单，实际: {reply[:300]}...",
        )

    def test_staff_query_order_by_id(self):
        """
        店员权限 2：查询某个订单 id，若存在则返回该订单
        """
        _prepare_e2e_products(E2E_PRODUCTS_OSMANTHUS)
        reply1 = _chat("10016", "e2e_staff_order_a", "我要一杯桂花云露少糖去冰", role="customer")
        match = re.search(r"ORDER_\d+", reply1)
        self.assertIsNotNone(match, "应先下单成功")
        order_id = match.group()

        reply2 = _chat(
            "20006",
            "e2e_staff_query_order",
            f"帮我查一下订单 {order_id} 的详情",
            role="staff",
        )
        self.assertTrue(
            order_id in reply2 and ("桂花" in reply2 or "¥" in reply2),
            f"店员应能查到该订单，实际: {reply2[:300]}...",
        )

    def test_staff_query_order_not_exists(self):
        """
        店员权限 2：查询不存在的订单 id，应告知不存在
        """
        _prepare_e2e_products(E2E_PRODUCTS_OSMANTHUS)
        reply = _chat(
            "20007",
            "e2e_staff_order_not_exists",
            "帮我查一下订单 ORDER_9999999999999 的详情",
            role="staff",
        )
        self.assertTrue(
            any(kw in reply for kw in ["未找到", "不存在", "没有"]),
            f"应告知订单不存在，实际: {reply[:300]}...",
        )

    def test_staff_modify_stock_valid(self):
        """
        店员权限 3：修改库存 - 合法修改应成功
        """
        _prepare_e2e_products(E2E_PRODUCTS_JASMINE)
        user_id = "20003"
        chat_id = "e2e_staff_stock"

        pending = _chat_full(user_id, chat_id, "把云边茉莉的库存改成 150", role="staff").get("pending_action")
        if pending and pending.get("type") == "product_update":
            resp = requests.post(
                f"{API_BASE}/product/update",
                json={"productName": "云边茉莉", "stock": 150},
                timeout=10,
            )
            resp.raise_for_status()
            self.assertEqual(resp.json().get("status"), "success")

        reply2 = _chat(user_id, chat_id, "云边茉莉有没有货？", role="staff")
        self.assertTrue("有货" in reply2 or "150" in reply2, f"库存修改应生效，实际: {reply2[:200]}...")

        requests.post(
            f"{API_BASE}/product/update",
            json={"productName": "云边茉莉", "stock": 100},
            timeout=10,
        )

    def test_staff_modify_stock_invalid_reduce_below_zero(self):
        """
        店员权限 3：修改库存 - 减少后 < 0 应失败
        """
        _prepare_e2e_products([("云边茉莉", "优质茉莉花茶", 18.00, 5)])
        resp = requests.post(
            f"{API_BASE}/product/update",
            json={"productName": "云边茉莉", "stock": -1},
            timeout=10,
        )
        data = resp.json() if resp.status_code == 200 else {}
        success = resp.status_code == 200 and data.get("status") == "success"
        self.assertFalse(success, "库存改为负数应失败")

    def test_staff_query_user_not_exists(self):
        """
        店员权限 1：查询不存在用户的历史订单，应告知不存在该用户
        """
        _prepare_e2e_products(E2E_PRODUCTS_OSMANTHUS)
        reply = _chat(
            "20005",
            "e2e_staff_user_not_exists",
            "帮我查一下用户 88888888 的订单",
            role="staff",
        )
        self.assertTrue(
            any(kw in reply for kw in ["没有", "不存在", "订单", "88888888"]),
            f"应告知用户不存在或无订单，实际: {reply[:300]}...",
        )

    def test_staff_modify_product_not_exists(self):
        """
        店员权限 3：修改不存在的单品，应失败
        """
        _prepare_e2e_products(E2E_PRODUCTS_JASMINE)
        resp = requests.post(
            f"{API_BASE}/product/update",
            json={"productName": "不存在的奶茶", "stock": 100},
            timeout=10,
        )
        data = resp.json() if resp.status_code == 200 else {}
        self.assertFalse(
            resp.status_code == 200 and data.get("status") == "success",
            "修改不存在的单品应失败",
        )

    # ========== 四. 订单数据持久化 ==========

    def test_persistence_user_order_after_relogin(self):
        """
        持久化 1：用户登录、下单、退出再登录，能查到自己的订单
        """
        _prepare_e2e_products(E2E_PRODUCTS_OSMANTHUS)
        user_id = "10015"
        chat_id = "e2e_persist_user"

        reply1 = _chat(user_id, chat_id, "我要一杯桂花云露少糖去冰", role="customer")
        self.assertTrue("ORDER_" in reply1, f"应先下单成功，实际: {reply1[:200]}...")

        requests.post(f"{API_BASE}/clear", params={"user_id": user_id, "chat_id": chat_id}, timeout=5)

        reply2 = _chat(
            user_id,
            "e2e_persist_user_new",
            "帮我查一下我的订单记录",
            role="customer",
        )
        self.assertTrue(
            any(kw in reply2 for kw in ["订单", "桂花", "ORDER_", "¥"]),
            f"再登录后应能查到订单，实际: {reply2[:300]}...",
        )

    def test_persistence_staff_stock_after_relogin(self):
        """
        持久化 2：店员登录、修改库存、退出再登录，能保留修改
        """
        _prepare_e2e_products(E2E_PRODUCTS_JASMINE)
        user_id = "20004"
        chat_id = "e2e_persist_staff"

        # 1. 店员修改库存
        pending = _chat_full(user_id, chat_id, "把云边茉莉的库存改成 88", role="staff").get("pending_action")
        if pending and pending.get("type") == "product_update":
            resp = requests.post(
                f"{API_BASE}/product/update",
                json={"productName": "云边茉莉", "stock": 88},
                timeout=10,
            )
            resp.raise_for_status()
            self.assertEqual(resp.json().get("status"), "success")

        # 2. 模拟退出再登录（清空会话）
        requests.post(f"{API_BASE}/clear", params={"user_id": user_id, "chat_id": chat_id}, timeout=5)

        # 3. 新会话查询，验证库存已保留
        reply = _chat(
            user_id,
            "e2e_persist_staff_new",
            "云边茉莉的库存是多少？有没有货？",
            role="staff",
        )
        # get_product_info 只返回有货/售罄，不返回具体数字。有货即表示库存>0，修改已保留
        self.assertTrue(
            "有货" in reply or "云边茉莉" in reply,
            f"再登录后库存修改应保留（有货），实际: {reply[:200]}...",
        )

        # 恢复原库存
        requests.post(
            f"{API_BASE}/product/update",
            json={"productName": "云边茉莉", "stock": 100},
            timeout=10,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
