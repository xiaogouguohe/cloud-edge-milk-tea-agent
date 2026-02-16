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
        self.user_id = "test_user_123"

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
    # 后续功能预留位置 (下单、查询历史订单等)
    # =================================================================

if __name__ == "__main__":
    unittest.main()
