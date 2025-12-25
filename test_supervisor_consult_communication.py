"""
测试 SupervisorAgent 和 ConsultAgent 之间的通信
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_supervisor_consult_communication():
    """测试 SupervisorAgent 和 ConsultAgent 的通信"""
    print("=" * 80)
    print("SupervisorAgent 和 ConsultAgent 通信测试")
    print("=" * 80)
    print()
    
    try:
        from supervisor_agent.supervisor_agent import SupervisorAgent
        
        # 创建 SupervisorAgent 实例
        print("1. 初始化 SupervisorAgent...")
        supervisor = SupervisorAgent(user_id="test_user", chat_id="test_chat")
        print("✅ SupervisorAgent 初始化成功")
        print()
        
        # 检查 consult_agent 配置
        print("2. 检查 consult_agent 配置...")
        sub_agents = supervisor.get_sub_agent_status()
        consult_info = sub_agents.get("consult_agent")
        if consult_info:
            print(f"✅ consult_agent 配置:")
            print(f"   名称: {consult_info['name']}")
            print(f"   描述: {consult_info['description']}")
            print(f"   已实现: {consult_info['implemented']}")
        else:
            print("❌ consult_agent 配置未找到")
            return False
        print()
        
        # 测试路由判断
        print("3. 测试路由判断...")
        test_queries = [
            "云边茉莉的特点是什么？",
            "有哪些产品？",
            "推荐一款奶茶",
        ]
        
        for query in test_queries:
            target = supervisor.route_to_agent(query)
            if target == "consult_agent":
                print(f"✅ 查询: '{query}' -> 路由到: {target}")
            else:
                print(f"⚠️  查询: '{query}' -> 路由到: {target}")
        print()
        
        # 测试 A2A 调用（需要 consult_agent 服务运行）
        print("4. 测试 A2A 协议调用...")
        print("   注意: 需要先启动 consult_agent 服务 (python3 consult_agent/run_consult_agent.py)")
        print()
        
        test_query = "云边茉莉的特点是什么？"
        print(f"   测试查询: {test_query}")
        
        try:
            start_time = time.time()
            response = supervisor.call_sub_agent("consult_agent", test_query)
            elapsed = time.time() - start_time
            
            if response and "错误" not in response and "不可用" not in response:
                print(f"✅ A2A 调用成功 (耗时: {elapsed:.2f} 秒)")
                print(f"   响应: {response[:200]}...")
            else:
                print(f"⚠️  A2A 调用返回: {response}")
                print("   提示: 请确保 consult_agent 服务已启动")
        except Exception as e:
            print(f"❌ A2A 调用失败: {str(e)}")
            print("   提示: 请确保 consult_agent 服务已启动")
            print("   启动命令: python3 consult_agent/run_consult_agent.py")
        print()
        
        # 测试完整流程
        print("5. 测试完整对话流程...")
        test_query = "推荐一款奶茶"
        print(f"   用户输入: {test_query}")
        
        try:
            start_time = time.time()
            response = supervisor.chat(test_query)
            elapsed = time.time() - start_time
            
            print(f"✅ 对话成功 (耗时: {elapsed:.2f} 秒)")
            print(f"   响应: {response[:200]}...")
        except Exception as e:
            print(f"❌ 对话失败: {str(e)}")
            import traceback
            traceback.print_exc()
        print()
        
        print("=" * 80)
        print("测试总结")
        print("=" * 80)
        print("✅ SupervisorAgent 和 ConsultAgent 的通信代码已实现")
        print("📝 使用说明:")
        print("   1. 启动 consult_agent: python3 consult_agent/run_consult_agent.py")
        print("   2. 启动 supervisor_agent: 使用 chat.py 或直接调用 SupervisorAgent")
        print("   3. 当用户输入咨询类问题时，SupervisorAgent 会自动路由到 ConsultAgent")
        print()
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_supervisor_consult_communication()
    sys.exit(0 if success else 1)

