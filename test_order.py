"""
订单功能测试脚本
验证下单功能是否正常工作
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from supervisor_agent import SupervisorAgent

# 尝试导入数据库模块
try:
    from database.db_manager import DatabaseManager
    from database.config import DB_TYPE, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("警告: 数据库模块未找到，将无法验证数据库")


def get_db():
    """获取数据库连接"""
    if not DB_AVAILABLE:
        return None
    
    if DB_TYPE == "mysql":
        return DatabaseManager(
            db_type="mysql",
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
    else:
        return DatabaseManager(db_type="sqlite")


def get_order_count(db):
    """获取订单总数"""
    if not db:
        return 0
    
    if db.db_type == "sqlite":
        query = "SELECT COUNT(*) as count FROM orders"
    else:
        query = "SELECT COUNT(*) as count FROM orders"
    
    result = db.fetch_one(query)
    return result['count'] if result else 0


def get_latest_orders(db, limit=5):
    """获取最新的订单"""
    if not db:
        return []
    
    if db.db_type == "sqlite":
        query = "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?"
    else:
        query = "SELECT * FROM orders ORDER BY created_at DESC LIMIT %s"
    
    return db.fetch_all(query, (limit,))


def format_order(order):
    """格式化订单信息"""
    sweetness_map = {1: "无糖", 2: "微糖", 3: "半糖", 4: "少糖", 5: "标准糖"}
    ice_level_map = {1: "热", 2: "温", 3: "去冰", 4: "少冰", 5: "正常冰"}
    
    created_at = order.get('created_at', '')
    if isinstance(created_at, datetime):
        created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(created_at, str):
        pass
    else:
        created_at = str(created_at)
    
    return f"""订单ID: {order.get('order_id', '')}
用户ID: {order.get('user_id', '')}
产品: {order.get('product_name', '')}
甜度: {sweetness_map.get(order.get('sweetness', 5), '标准糖')}
冰量: {ice_level_map.get(order.get('ice_level', 5), '正常冰')}
数量: {order.get('quantity', 1)}
总价: ¥{order.get('total_price', 0):.2f}
创建时间: {created_at}"""


def test_create_order():
    """测试创建订单功能"""
    print("=" * 80)
    print("订单功能测试 - 创建订单")
    print("=" * 80)
    print()
    
    # 测试用户ID
    test_user_id = "12345678901"
    
    # 1. 验证前查询
    print("步骤1: 验证前查询数据库")
    print("-" * 80)
    db = get_db()
    if db:
        count_before = get_order_count(db)
        latest_before = get_latest_orders(db, 3)
        
        print(f"当前订单总数: {count_before}")
        print(f"最新3条订单:")
        if latest_before:
            for i, order in enumerate(latest_before, 1):
                print(f"\n订单 {i}:")
                print(format_order(order))
        else:
            print("  暂无订单")
        db.close()
    else:
        print("⚠️  数据库不可用，跳过数据库验证")
        count_before = None
        latest_before = []
    
    print()
    print("-" * 80)
    print()
    
    # 2. 执行下单操作
    print("步骤2: 执行下单操作")
    print("-" * 80)
    
    # 创建 SupervisorAgent
    supervisor = SupervisorAgent(user_id=test_user_id, chat_id=f"test_{int(datetime.now().timestamp() * 1000)}")
    
    # 测试下单请求（用户ID在对话中携带）
    test_queries = [
        f"我要下单，云边茉莉，标准糖，正常冰，1杯，用户ID是{test_user_id}",
        f"帮我下单：桂花云露，少糖，少冰，2杯，用户ID是{test_user_id}",
    ]
    
    print(f"测试用户ID: {test_user_id}")
    print()
    
    for i, query in enumerate(test_queries, 1):
        print(f"测试 {i}: {query}")
        print()
        
        try:
            response = supervisor.chat(query)
            print(f"AI 回复:")
            print(response)
            print()
        except Exception as e:
            print(f"❌ 下单失败: {str(e)}")
            print()
    
    print("-" * 80)
    print()
    
    # 3. 验证后查询
    print("步骤3: 验证后查询数据库")
    print("-" * 80)
    
    if db:
        db = get_db()  # 重新连接
        count_after = get_order_count(db)
        latest_after = get_latest_orders(db, 5)
        
        print(f"当前订单总数: {count_after}")
        print(f"最新5条订单:")
        if latest_after:
            for i, order in enumerate(latest_after, 1):
                print(f"\n订单 {i}:")
                print(format_order(order))
        else:
            print("  暂无订单")
        
        print()
        print("-" * 80)
        print()
        
        # 4. 对比结果
        print("步骤4: 对比验证结果")
        print("-" * 80)
        
        if count_before is not None:
            count_diff = count_after - count_before
            print(f"订单数量变化: {count_before} → {count_after} (变化: {count_diff:+d})")
            print()
            
            if count_diff > 0:
                print("✅ 验证成功：订单已成功写入数据库")
                print()
                print("新增的订单:")
                # 显示新增的订单
                new_orders = latest_after[:count_diff]
                for i, order in enumerate(new_orders, 1):
                    print(f"\n新增订单 {i}:")
                    print(format_order(order))
                
                # 验证用户ID是否正确
                print()
                print("验证用户ID:")
                for order in new_orders:
                    order_user_id = str(order.get('user_id', ''))
                    if order_user_id == test_user_id:
                        print(f"  ✅ 订单 {order.get('order_id')} 的用户ID正确: {order_user_id}")
                    else:
                        print(f"  ❌ 订单 {order.get('order_id')} 的用户ID错误: 期望 {test_user_id}, 实际 {order_user_id}")
            elif count_diff == 0:
                print("⚠️  订单数量未变化，可能下单失败或订单已存在")
            else:
                print("⚠️  订单数量减少，可能发生了删除操作")
        else:
            print("无法对比：缺少验证前数据")
        
        db.close()
    else:
        print("⚠️  数据库不可用，无法验证数据库")
        print("但下单请求已发送，请检查服务日志确认是否成功")
    
    print()
    print("=" * 80)
    print("测试完成")
    print("=" * 80)


def test_query_order():
    """测试查询订单功能"""
    print("=" * 80)
    print("订单功能测试 - 查询订单")
    print("=" * 80)
    print()
    
    test_user_id = "12345678901"
    
    # 创建 SupervisorAgent
    supervisor = SupervisorAgent(user_id=test_user_id, chat_id=f"test_{int(datetime.now().timestamp() * 1000)}")
    
    # 测试查询请求
    test_queries = [
        f"查询我的订单，用户ID是{test_user_id}",
        f"帮我查一下订单，用户ID是{test_user_id}",
    ]
    
    print(f"测试用户ID: {test_user_id}")
    print()
    
    for i, query in enumerate(test_queries, 1):
        print(f"测试 {i}: {query}")
        print()
        
        try:
            response = supervisor.chat(query)
            print(f"AI 回复:")
            print(response)
            print()
        except Exception as e:
            print(f"❌ 查询失败: {str(e)}")
            print()
    
    print("=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="订单功能测试脚本")
    parser.add_argument("--test", choices=["create", "query", "all"], default="all",
                       help="测试类型: create(创建订单), query(查询订单), all(全部)")
    
    args = parser.parse_args()
    
    if args.test == "create" or args.test == "all":
        test_create_order()
        print()
    
    if args.test == "query" or args.test == "all":
        test_query_order()
