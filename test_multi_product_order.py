#!/usr/bin/env python3
"""
测试多产品订单功能
验证：
1. 单产品订单（items数组只有1个元素）
2. 多产品订单（items数组有多个元素）
3. 查询订单，验证订单项是否正确
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.db_manager import DatabaseManager
from order_mcp_server.database import OrderDAO
from order_mcp_server.order_service import OrderService

def init_database():
    """初始化数据库和产品数据"""
    db_manager = DatabaseManager(db_type="sqlite")
    # 初始化产品数据
    db_manager._init_products()
    return db_manager


def test_single_product_order():
    """测试单产品订单"""
    print("\n" + "="*60)
    print("测试 1: 单产品订单（items数组只有1个元素）")
    print("="*60)
    
    # 初始化数据库和服务
    db_manager = init_database()
    order_dao = OrderDAO(db_manager=db_manager)
    order_service = OrderService(order_dao)
    
    # 创建单产品订单
    items = [{
        "productName": "云边茉莉",
        "sweetness": "标准糖",
        "iceLevel": "正常冰",
        "quantity": 1,
        "remark": "不要珍珠"
    }]
    
    order = order_service.create_order(
        user_id=789012,
        items=items,
        remark="单产品订单测试"
    )
    
    print(f"\n✅ 订单创建成功:")
    print(f"   订单ID: {order['order_id']}")
    print(f"   用户ID: {order['user_id']}")
    print(f"   订单总价: ¥{order['total_price']:.2f}")
    print(f"   订单项数量: {len(order.get('items', []))}")
    
    # 验证订单项
    items = order.get('items', [])
    assert len(items) == 1, f"期望1个订单项，实际{len(items)}个"
    assert items[0]['product_name'] == "云边茉莉", f"产品名称不匹配: {items[0]['product_name']}"
    assert items[0]['quantity'] == 1, f"数量不匹配: {items[0]['quantity']}"
    
    print(f"\n✅ 订单项验证通过:")
    for i, item in enumerate(items, 1):
        print(f"   订单项 {i}: {item['product_name']} x{item['quantity']} = ¥{item['item_price']:.2f}")
    
    return order['order_id']


def test_multi_product_order():
    """测试多产品订单"""
    print("\n" + "="*60)
    print("测试 2: 多产品订单（items数组有多个元素）")
    print("="*60)
    
    # 初始化数据库和服务（使用同一个数据库实例）
    db_manager = init_database()
    order_dao = OrderDAO(db_manager=db_manager)
    order_service = OrderService(order_dao)
    
    # 创建多产品订单
    items = [
        {
            "productName": "云边茉莉",
            "sweetness": "少糖",
            "iceLevel": "正常冰",
            "quantity": 1,
            "remark": "不要珍珠"
        },
        {
            "productName": "桂花云露",
            "sweetness": "半糖",
            "iceLevel": "去冰",
            "quantity": 2,
            "remark": ""
        },
        {
            "productName": "云雾观音",
            "sweetness": "标准糖",
            "iceLevel": "热",
            "quantity": 1,
            "remark": "加珍珠"
        }
    ]
    
    order = order_service.create_order(
        user_id=789012,
        items=items,
        remark="多产品订单测试"
    )
    
    print(f"\n✅ 订单创建成功:")
    print(f"   订单ID: {order['order_id']}")
    print(f"   用户ID: {order['user_id']}")
    print(f"   订单总价: ¥{order['total_price']:.2f}")
    print(f"   订单项数量: {len(order.get('items', []))}")
    
    # 验证订单项
    items = order.get('items', [])
    assert len(items) == 3, f"期望3个订单项，实际{len(items)}个"
    
    expected_products = ["云边茉莉", "桂花云露", "云雾观音"]
    actual_products = [item['product_name'] for item in items]
    assert set(actual_products) == set(expected_products), f"产品列表不匹配: {actual_products}"
    
    # 验证总价计算
    calculated_total = sum(item['item_price'] for item in items)
    assert abs(order['total_price'] - calculated_total) < 0.01, \
        f"总价计算错误: 订单总价={order['total_price']}, 计算总价={calculated_total}"
    
    print(f"\n✅ 订单项验证通过:")
    for i, item in enumerate(items, 1):
        print(f"   订单项 {i}: {item['product_name']} x{item['quantity']} = ¥{item['item_price']:.2f}")
        print(f"           甜度: {item['sweetness']}, 冰量: {item['ice_level']}")
        if item.get('remark'):
            print(f"           备注: {item['remark']}")
    
    print(f"\n✅ 总价验证通过: ¥{order['total_price']:.2f} = 各项小计之和")
    
    return order['order_id']


def test_query_order(order_id: str):
    """测试查询订单"""
    print("\n" + "="*60)
    print(f"测试 3: 查询订单 {order_id}")
    print("="*60)
    
    # 初始化数据库和服务（使用同一个数据库实例）
    db_manager = init_database()
    order_dao = OrderDAO(db_manager=db_manager)
    order_service = OrderService(order_dao)
    
    # 查询订单
    order = order_service.get_order(order_id)
    
    if not order:
        print(f"❌ 订单不存在: {order_id}")
        return
    
    print(f"\n✅ 订单查询成功:")
    print(f"   订单ID: {order['order_id']}")
    print(f"   用户ID: {order['user_id']}")
    print(f"   订单总价: ¥{order['total_price']:.2f}")
    print(f"   订单项数量: {len(order.get('items', []))}")
    
    # 验证订单项是否正确加载
    items = order.get('items', [])
    assert len(items) > 0, "订单项为空"
    
    print(f"\n✅ 订单项详情:")
    for i, item in enumerate(items, 1):
        print(f"   订单项 {i}: {item['product_name']} x{item['quantity']} = ¥{item['item_price']:.2f}")
    
    # 格式化输出
    formatted = order_service.format_order_response(order)
    print(f"\n✅ 格式化输出:")
    print(formatted)


def test_query_orders_by_user():
    """测试查询用户的所有订单"""
    print("\n" + "="*60)
    print("测试 4: 查询用户的所有订单")
    print("="*60)
    
    # 初始化数据库和服务（使用同一个数据库实例）
    db_manager = init_database()
    order_dao = OrderDAO(db_manager=db_manager)
    order_service = OrderService(order_dao)
    
    # 查询用户的所有订单
    orders = order_service.get_orders_by_user(789012)
    
    print(f"\n✅ 查询成功，用户 789012 共有 {len(orders)} 个订单:")
    
    for i, order in enumerate(orders, 1):
        items = order.get('items', [])
        print(f"\n   订单 {i}: {order['order_id']}")
        print(f"     总价: ¥{order['total_price']:.2f}")
        print(f"     订单项数量: {len(items)}")
        for j, item in enumerate(items, 1):
            print(f"       项 {j}: {item['product_name']} x{item['quantity']} = ¥{item['item_price']:.2f}")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("多产品订单功能验证测试")
    print("="*60)
    
    try:
        # 测试1: 单产品订单
        order_id_1 = test_single_product_order()
        
        # 测试2: 多产品订单
        order_id_2 = test_multi_product_order()
        
        # 测试3: 查询订单
        test_query_order(order_id_2)
        
        # 测试4: 查询用户的所有订单
        test_query_orders_by_user()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)
        print("\n验证结果:")
        print("  ✅ 单产品订单：items数组只有1个元素，功能正常")
        print("  ✅ 多产品订单：items数组有多个元素，功能正常")
        print("  ✅ 订单查询：订单项正确加载")
        print("  ✅ 总价计算：订单总价 = 所有订单项总价之和")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

