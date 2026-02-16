import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from order_agent.order_agent import OrderAgent

class TestOrderAgentMenu(unittest.TestCase):
    """测试订单智能体的菜单查询功能 (使用 patch 模式)"""

    @classmethod
    def setUpClass(cls):
        """测试前初始化 Agent"""
        print("\n" + "="*50)
        print("正在初始化 OrderAgent 测试环境...")
        print("="*50)
        # 注意：Agent 的实例化要在 patch 之前还是之后，取决于 patch 的目标
        # 为了保险，我们在每个测试方法中进行 patch

    @patch('order_agent.order_agent.OrderAgent._invoke_tool')
    def test_get_menu_flow(self, mock_invoke):
        """验证查询菜单的完整流程"""
        
        # 1. 设置 Mock 返回值
        # 模拟 _invoke_tool 被调用后的返回字符串
        mock_invoke.return_value = (
            "云边奶茶铺菜单如下：\n"
            "1. 云边茉莉 - 价格: ¥18.00 - 状态: 有货\n"
            "2. 桂花云露 - 价格: ¥20.00 - 状态: 有货\n"
            "3. 珍珠奶茶 - 价格: ¥15.00 - 状态: 有货\n"
            "支持规格：标准糖/半糖/无糖，正常冰/少冰/去冰"
        )

        # 2. 实例化 Agent
        agent = OrderAgent()
        user_id = "test_user_123"

        test_queries = [
            "你们这儿都有什么好喝的？",
            "查询所有产品"
        ]

        print(f"\n[测试开始] 验证菜单查询功能 (patch 模式)")
        
        for query in test_queries:
            print(f"\n--- 用户输入: '{query}' ---")
            
            # 3. 调用 Agent
            result = agent.chat(
                user_input=query,
                user_id=user_id,
                role="base"
            )
            
            output = result.get("output", "")
            print(f"Agent 回复:\n{output}")
            
            # 4. 断言验证
            # 验证 _invoke_tool 是否被调用
            self.assertTrue(mock_invoke.called, "Agent 应该触发了工具调用")
            
            # 验证调用时的第一个参数（工具名）是否正确
            called_tool_name = mock_invoke.call_args[0][0]
            self.assertEqual(called_tool_name, "order-get-menu")
            
            # 验证回复中是否包含 Mock 数据中的关键词
            self.assertTrue(
                any(word in output for word in ["茉莉", "奶茶", "菜单", "价格"]), 
                f"Agent 回复似乎没有包含菜单信息。回复内容: {output}"
            )
            print("✅ 测试通过：patch 成功拦截并替换了工具调用")

if __name__ == "__main__":
    unittest.main()
