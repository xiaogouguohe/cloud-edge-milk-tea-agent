import sys
import unittest
import subprocess
import time
import sqlite3
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from order_agent.order_agent import OrderAgent

class TestOrderIntegration(unittest.TestCase):
    """
    全链路集成测试：验证 Agent -> MCP Server -> SQLite DB 的完整流程。
    注意：运行此测试需要联网（调用 DashScope LLM）。
    """

    @classmethod
    def setUpClass(cls):
        """环境准备：初始化数据库并启动 MCP Server"""
        print("\n" + "="*60)
        print("正在准备全链路集成测试环境...")
        print("="*60)

        # 1. 初始化临时测试数据库
        cls.test_db_dir = project_root / "data"
        cls.test_db_dir.mkdir(exist_ok=True)
        cls.db_path = cls.test_db_dir / "milk_tea.db" # 默认读取这个路径
        
        print(f"[1/3] 初始化测试数据库: {cls.db_path}")
        conn = sqlite3.connect(cls.db_path)
        cursor = conn.cursor()
        
        # 创建产品表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) UNIQUE,
                price DECIMAL(10,2),
                stock INT,
                status TINYINT DEFAULT 1
            )
        """)
        
        # 插入确定的测试数据
        test_products = [
            ("集成测试专用奶茶", 99.99, 10),
            ("全链路茉莉", 12.34, 50)
        ]
        for name, price, stock in test_products:
            cursor.execute("INSERT OR REPLACE INTO products (name, price, stock, status) VALUES (?, ?, ?, 1)", 
                         (name, price, stock))
        
        conn.commit()
        conn.close()

        # 2. 启动 MCP Server 进程
        print("[2/3] 启动 MCP Server 进程...")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        # 这种方式最稳妥：直接运行脚本，但在脚本内部处理好路径
        server_script = project_root / "order_mcp_server" / "order_mcp_server.py"
        cls.mcp_process = subprocess.Popen(
            [sys.executable, str(server_script)],
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务启动并检查
        print("等待服务就绪 (5秒)...")
        time.sleep(5)
        
        # 检查进程是否意外退出
        # 注意：poll() 为 None 表示进程仍在运行，这是我们希望看到的
        if cls.mcp_process.poll() is not None:
            stdout, stderr = cls.mcp_process.communicate()
            raise RuntimeError(f"MCP Server 意外退出!\nStdout: {stdout}\nStderr: {stderr}")

        print("[3/3] 环境准备就绪！")

    def test_e2e_menu_query(self):
        """测试全链路菜单查询"""
        print("\n[测试开始] 发起真实全链路请求...")
        
        agent = OrderAgent()
        user_id = "e2e_test_user"
        
        # 模拟真实用户输入
        query = "我想看看你们这儿最贵的奶茶，顺便把菜单发给我"
        print(f"用户输入: '{query}'")
        
        # 调用 Agent (这里会触发真实的 MCP 网络调用)
        result = agent.chat(
            user_input=query,
            user_id=user_id,
            role="base"
        )
        
        output = result.get("output", "")
        print(f"Agent 最终回复:\n{output}")
        
        # 验证逻辑：
        # 1. 验证是否包含我们在数据库中插入的特定产品和价格
        self.assertIn("集成测试专用奶茶", output, "回复中应包含测试数据库中的产品名")
        self.assertIn("99.99", output, "回复中应包含测试数据库中的价格")
        self.assertIn("12.34", output, "回复中应包含测试数据库中的价格")
        
        print("\n✅ 全链路集成测试通过！Agent 成功读取了真实数据库数据。")

    @classmethod
    def tearDownClass(cls):
        """环境清理：关闭 MCP Server"""
        print("\n" + "="*60)
        print("正在清理测试环境...")
        if hasattr(cls, 'mcp_process'):
            cls.mcp_process.terminate()
            cls.mcp_process.wait()
            print("MCP Server 进程已关闭。")
        print("="*60)

if __name__ == "__main__":
    unittest.main()
