#!/usr/bin/env python3
"""
直接调用 MCP 验证库存检查是否生效
用法：确保 Order MCP Server 已启动后运行
  python3 scripts/verify_mcp_stock.py
"""
import requests
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

MCP_URL = "http://localhost:10002"


def main():
    print("=" * 50)
    print("MCP 库存检查验证")
    print("=" * 50)

    # 1. 获取菜单，查看当前库存
    print("\n1. 获取菜单...")
    try:
        r = requests.get(f"{MCP_URL}/mcp/tools", timeout=5)
        r.raise_for_status()
        tools = [t["name"] for t in r.json().get("tools", [])]
        print(f"   工具列表: {tools}")
        if "order-create-order" not in tools:
            print("   ❌ order-create-order 未注册")
            return 1
    except Exception as e:
        print(f"   ❌ MCP 不可达: {e}")
        return 1

    # 2. 直接调用 order-create-order，数量 1000（应超过库存）
    print("\n2. 调用 order-create-order，数量 1000 杯云边茉莉...")
    try:
        r = requests.post(
            f"{MCP_URL}/mcp/tools/order-create-order/invoke",
            json={
                "parameters": {
                    "userId": 99999,
                    "items": [
                        {
                            "productName": "云边茉莉",
                            "sweetness": "少糖",
                            "iceLevel": "去冰",
                            "quantity": 1000,
                        }
                    ],
                }
            },
            timeout=10,
        )
        data = r.json()
        result = data.get("result", "")
        status = data.get("status", "")

        print(f"   HTTP {r.status_code}, status={status}")
        print(f"   result 前 200 字: {result[:200]}...")

        if "库存不足" in result:
            print("\n   ✅ MCP 正确返回库存不足")
            return 0
        elif "ORDER_" in result and "¥" in result:
            print("\n   ❌ MCP 错误地创建了订单（应返回库存不足）")
            return 1
        else:
            print(f"\n   ⚠️ 未预期的返回: {result[:300]}")
            return 1
    except Exception as e:
        print(f"   ❌ 调用失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
