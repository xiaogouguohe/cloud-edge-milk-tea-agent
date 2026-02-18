import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from order_agent.order_agent import OrderAgent

class TestOrderAgent(unittest.TestCase):
    """
    订单智能体统一测试用例
    包含：菜单查询、产品详情查询
    """

    def setUp(self):
        """每个测试用例前初始化"""
        self.agent = OrderAgent()
        self.user_id = 12345  # 统一改为数字 ID，确保符合 skills.py 中的 integer 类型定义

    # =================================================================
    # 1. 基础查询功能测试 (Base Skills)
    # =================================================================

    @patch('order_agent.order_agent.OrderAgent._invoke_tool')
    def test_get_menu(self, mock_invoke):
        """测试：获取完整菜单"""
        mock_invoke.return_value = "云边奶茶铺菜单：\n- 云边茉莉: ¥18.00 (有货)\n- 桂花云露: ¥20.00 (有货)"
        
        query = "你们这儿都有什么好喝的？"
        print(f"\n[测试] 菜单查询 - 输入: '{query}'")
        
        result = self.agent.chat(query, self.user_id, role="base")
        
        print(f"Agent 回复: {result['output']}")
        self.assertTrue(mock_invoke.called)
        self.assertEqual(mock_invoke.call_args[0][0], "order-get-menu")
        self.assertIn("茉莉", result['output'])
        print("✅ 菜单查询测试通过")

    @patch('order_agent.order_agent.OrderAgent._invoke_tool')
    def test_get_product_info(self, mock_invoke):
        """测试：获取单个产品详情"""
        mock_invoke.return_value = "产品信息: 云边茉莉\n价格: ¥18.00\n库存状态: 有货"
        
        query = "云边茉莉多少钱？"
        print(f"\n[测试] 产品详情 - 输入: '{query}'")
        
        result = self.agent.chat(query, self.user_id, role="base")
        
        print(f"Agent 回复: {result['output']}")
        self.assertTrue(mock_invoke.called)
        self.assertEqual(mock_invoke.call_args[0][0], "order-get-product-info")
        
        # 验证参数提取
        args = mock_invoke.call_args[0][2]
        self.assertEqual(args.get("productName"), "云边茉莉")
        print(f"✅ 产品详情测试通过 (参数提取: {args})")

    @patch('order_agent.order_agent.OrderAgent._invoke_tool')
    def test_product_out_of_stock(self, mock_invoke):
        """测试：产品无货时的 Agent 回复策略"""
        # 模拟工具返回“售罄”状态
        mock_invoke.return_value = "产品信息: 云边茉莉\n价格: ¥18.00\n库存状态: 售罄"
        
        query = "现在还有云边茉莉吗？"
        print(f"\n[测试] 产品无货场景 - 输入: '{query}'")
        
        result = self.agent.chat(query, self.user_id, role="base")
        
        print(f"Agent 回复: {result['output']}")
        
        # 验证逻辑：
        # 1. 确保触发了工具调用
        self.assertTrue(mock_invoke.called)
        # 2. 确保 Agent 没有“幻觉”说有货，而是正确传达了卖完了的信息
        self.assertTrue(
            any(word in result['output'] for word in ["卖完", "售罄", "抱歉", "没有"]), 
            "Agent 在产品无货时应给出合理的致歉或提示"
        )
        print("✅ 产品无货场景测试通过")

    # =================================================================
    # 2. 顾客功能测试 (Customer Skills)
    # =================================================================

    @patch('order_agent.order_agent.OrderAgent._invoke_tool')
    def test_create_order_success(self, mock_invoke):
        """测试：下单成功流程"""
        # 模拟工具返回成功
        mock_invoke.return_value = "订单创建成功！订单ID: ORDER_20260216001, 总价: ¥36.00"
        
        query = "我要两杯云边茉莉，都要正常冰，半糖"
        print(f"\n[测试] 下单成功 - 输入: '{query}'")
        
        # 注意：下单需要 customer 角色
        result = self.agent.chat(query, self.user_id, role="customer")
        
        print(f"Agent 回复: {result['output']}")
        self.assertTrue(mock_invoke.called)
        self.assertEqual(mock_invoke.call_args[0][0], "order-create-order")
        
        # 验证参数提取是否正确
        args = mock_invoke.call_args[0][2]
        self.assertEqual(len(args['items']), 1)
        self.assertEqual(args['items'][0]['productName'], "云边茉莉")
        self.assertEqual(args['items'][0]['sweetness'], "半糖")
        print(f"✅ 下单成功测试通过 (参数提取: {args})")

    @patch('order_agent.order_agent.OrderAgent._invoke_tool')
    def test_create_order_out_of_stock(self, mock_invoke):
        """测试：下单时库存不足"""
        # 模拟工具返回库存不足的错误
        mock_invoke.return_value = "错误: 产品 '云边茉莉' 库存不足（剩余 1 杯，请求 2 杯）。下单失败。"
        
        query = "帮我订两杯云边茉莉，去冰少糖"
        print(f"\n[测试] 下单库存不足 - 输入: '{query}'")
        
        result = self.agent.chat(query, self.user_id, role="customer")
        
        print(f"Agent 回复: {result['output']}")
        
        # 验证 Agent 是否能正确传达失败信息
        self.assertTrue(mock_invoke.called)
        self.assertTrue(
            any(word in result['output'] for word in ["失败", "不足", "抱歉", "无法"]),
            "Agent 在工具报错库存不足时应给出合理的失败提示"
        )
        print("✅ 下单库存不足测试通过")

    @patch('order_agent.order_agent.OrderAgent._invoke_tool')
    def test_create_order_multi_turn(self, mock_invoke):
        """测试：多轮对话补充参数下单"""
        # 第一轮：只说产品
        query1 = "我想买一杯云边茉莉"
        print(f"\n[测试] 多轮下单 - 第一轮输入: '{query1}'")
        
        result1 = self.agent.chat(query1, self.user_id, role="customer")
        print(f"Agent 回复: {result1['output']}")
        
        # 验证：第一轮不应该触发工具调用，而是应该追问
        self.assertFalse(mock_invoke.called, "参数不全时，不应调用工具")
        self.assertTrue(any(word in result1['output'] for word in ["糖", "冰", "规格", "请问"]), "Agent 应该追问缺失的参数")

        # 第二轮：补充参数
        query2 = "都要正常冰，半糖吧"
        print(f"\n[测试] 多轮下单 - 第二轮输入: '{query2}'")
        
        # 模拟工具返回成功
        mock_invoke.return_value = "订单创建成功！订单ID: ORDER_999"
        
        # 传入第一轮的 history，模拟多轮对话
        result2 = self.agent.chat(query2, self.user_id, role="customer", history=result1['history'])
        
        print(f"Agent 回复: {result2['output']}")
        
        # 验证：第二轮应该结合上下文触发工具调用
        self.assertTrue(mock_invoke.called, "补充参数后应触发工具调用")
        args = mock_invoke.call_args[0][2]
        self.assertEqual(args['items'][0]['productName'], "云边茉莉")
        self.assertEqual(args['items'][0]['sweetness'], "半糖")
        self.assertEqual(args['items'][0]['iceLevel'], "正常冰")
        print(f"✅ 多轮下单测试通过 (成功从历史中找回产品名并下单)")

    # =================================================================
    # 3. 历史订单查询 (order_get_orders_by_user)
    # =================================================================

    @patch('order_agent.order_agent.OrderAgent._invoke_tool')
    def test_get_orders_by_user(self, mock_invoke):
        """测试：查询用户历史订单"""
        mock_invoke.return_value = (
            "用户 12345 的订单列表（共 2 条）:\n\n"
            "订单ID: ORDER_001 | 总价: ¥36.00 | 状态: UNPAID\n"
            "  - 云边茉莉 x2 半糖去冰 ¥36.00\n\n"
            "订单ID: ORDER_002 | 总价: ¥20.00 | 状态: UNPAID\n"
            "  - 桂花云露 x1 少糖少冰 ¥20.00"
        )
        query = "帮我查一下我的订单记录"
        print(f"\n[测试] 历史订单查询 - 输入: '{query}'")

        result = self.agent.chat(query, self.user_id, role="customer")

        print(f"Agent 回复: {result['output']}")
        self.assertTrue(mock_invoke.called)
        self.assertEqual(mock_invoke.call_args[0][0], "order-get-orders-by-user")
        args = mock_invoke.call_args[0][2]
        self.assertEqual(args.get("userId"), self.user_id)
        self.assertIn("订单", result["output"])
        print("✅ 历史订单查询测试通过")

    @patch('order_agent.order_agent.OrderAgent._invoke_tool')
    def test_get_orders_by_user_empty(self, mock_invoke):
        """测试：用户无订单时的回复"""
        mock_invoke.return_value = "用户 12345 当前没有任何订单记录。"
        query = "我的历史订单有哪些？"
        print(f"\n[测试] 无订单场景 - 输入: '{query}'")

        result = self.agent.chat(query, self.user_id, role="customer")

        print(f"Agent 回复: {result['output']}")
        self.assertTrue(mock_invoke.called)
        self.assertTrue(
            any(kw in result["output"] for kw in ["没有", "无", "空", "暂无"]),
            "无订单时应给出合理提示",
        )
        print("✅ 无订单场景测试通过")

if __name__ == "__main__":
    unittest.main()
