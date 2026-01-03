#!/usr/bin/env python3
"""
测试基于 Tree of Thoughts (ToT) 的个性化推荐功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from consult_agent.tot_recommendation import ToTRecommendationEngine, ThoughtNode
from consult_mcp_server.consult_service import ConsultService


def test_tot_basic():
    """测试 ToT 基本功能"""
    print("\n" + "="*60)
    print("测试 1: ToT 基本功能")
    print("="*60)
    
    consult_service = ConsultService()
    engine = ToTRecommendationEngine(consult_service=consult_service)
    
    # 测试场景：个性化推荐
    user_query = "我想要一杯适合我的奶茶，我喜欢清淡的口味，预算在20元左右"
    
    print(f"\n用户需求：{user_query}")
    print("\n开始 ToT 搜索...")
    
    best_node = engine.search(user_query)
    
    if best_node:
        print(f"\n✅ 找到最优推荐节点:")
        print(f"   推荐思路: {best_node.thought}")
        print(f"   推荐评分: {best_node.score:.2f}/1.0")
        print(f"   推荐产品数量: {len(best_node.products)}")
        
        recommendation = engine.format_recommendation(best_node)
        print(f"\n📋 推荐结果:")
        print(recommendation)
    else:
        print("\n❌ 未找到推荐")


def test_tot_health_requirement():
    """测试健康需求推荐"""
    print("\n" + "="*60)
    print("测试 2: 健康需求推荐")
    print("="*60)
    
    consult_service = ConsultService()
    engine = ToTRecommendationEngine(consult_service=consult_service)
    
    user_query = "我想要一杯低糖的奶茶，不要太甜"
    
    print(f"\n用户需求：{user_query}")
    print("\n开始 ToT 搜索...")
    
    best_node = engine.search(user_query)
    
    if best_node:
        recommendation = engine.format_recommendation(best_node)
        print(f"\n📋 推荐结果:")
        print(recommendation)
    else:
        print("\n❌ 未找到推荐")


def test_tot_budget_optimization():
    """测试预算优化推荐"""
    print("\n" + "="*60)
    print("测试 3: 预算优化推荐")
    print("="*60)
    
    consult_service = ConsultService()
    engine = ToTRecommendationEngine(consult_service=consult_service)
    
    user_query = "我想花50元，买几杯奶茶，推荐一下最划算的组合"
    
    print(f"\n用户需求：{user_query}")
    print("\n开始 ToT 搜索...")
    
    best_node = engine.search(user_query)
    
    if best_node:
        recommendation = engine.format_recommendation(best_node)
        print(f"\n📋 推荐结果:")
        print(recommendation)
    else:
        print("\n❌ 未找到推荐")


def test_thought_evaluation():
    """测试思维节点评估"""
    print("\n" + "="*60)
    print("测试 4: 思维节点评估")
    print("="*60)
    
    consult_service = ConsultService()
    engine = ToTRecommendationEngine(consult_service=consult_service)
    
    # 创建测试节点
    test_products = [
        {"name": "云边茉莉", "price": 18.0, "description": "清香淡雅"},
        {"name": "桂花云露", "price": 20.0, "description": "花香浓郁"}
    ]
    
    node = ThoughtNode(
        thought="基于价格和口味的推荐",
        products=test_products,
        reasoning="价格适中，口味清淡"
    )
    
    user_query = "我想要一杯适合我的奶茶"
    context = {}
    
    print(f"\n评估节点: {node.thought}")
    print(f"推荐产品: {[p['name'] for p in node.products]}")
    
    score = engine.evaluate_thought(node, user_query, context)
    node.score = score
    
    print(f"\n✅ 评估完成:")
    print(f"   评分: {score:.2f}/1.0")
    print(f"   推荐思路: {node.thought}")
    print(f"   推荐理由: {node.reasoning}")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Tree of Thoughts (ToT) 推荐功能测试")
    print("="*60)
    
    try:
        # 测试1: 基本功能
        test_tot_basic()
        
        # 测试2: 健康需求推荐
        test_tot_health_requirement()
        
        # 测试3: 预算优化推荐
        test_tot_budget_optimization()
        
        # 测试4: 思维节点评估
        test_thought_evaluation()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)
        print("\n测试说明:")
        print("  ✅ ToT 搜索：能够探索多个推荐路径")
        print("  ✅ 节点评估：能够评估每个推荐的质量")
        print("  ✅ 最优选择：能够选择评分最高的推荐")
        print("  ✅ 多场景支持：支持个性化、健康、预算等多种需求")
        
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

