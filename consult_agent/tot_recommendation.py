"""
基于 Tree of Thoughts (ToT) 的个性化推荐功能
实现多路径探索、评估和回溯的推荐规划
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import dashscope
from dashscope import Generation
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY


class ThoughtNode:
    """思维树节点"""
    
    def __init__(self, 
                 thought: str,
                 products: List[Dict],
                 reasoning: str = "",
                 score: float = 0.0,
                 parent: Optional['ThoughtNode'] = None):
        """
        初始化思维节点
        
        Args:
            thought: 思维内容（推荐路径描述）
            products: 推荐的产品列表
            reasoning: 推理过程
            score: 评分（0-1）
            parent: 父节点
        """
        self.thought = thought
        self.products = products
        self.reasoning = reasoning
        self.score = score
        self.parent = parent
        self.children: List['ThoughtNode'] = []
    
    def add_child(self, child: 'ThoughtNode'):
        """添加子节点"""
        child.parent = self
        self.children.append(child)
    
    def __repr__(self):
        return f"ThoughtNode(thought={self.thought[:30]}..., score={self.score:.2f}, products={len(self.products)})"


class ToTRecommendationEngine:
    """基于 Tree of Thoughts 的推荐引擎"""
    
    def __init__(self, consult_service=None):
        """
        初始化推荐引擎
        
        Args:
            consult_service: 咨询服务实例（用于获取产品信息）
        """
        self.consult_service = consult_service
        self.max_depth = 3  # 最大搜索深度
        self.branching_factor = 3  # 每个节点的分支数
        self.max_nodes = 10  # 最大节点数（防止搜索空间过大）
    
    def get_all_products(self) -> List[Dict]:
        """获取所有可用产品"""
        if self.consult_service:
            return self.consult_service.get_all_products()
        # 如果没有 consult_service，返回默认产品列表
        return [
            {"name": "云边茉莉", "price": 18.0, "description": "清香淡雅，适合喜欢清淡口味的用户"},
            {"name": "桂花云露", "price": 20.0, "description": "花香浓郁，适合喜欢花香的用户"},
            {"name": "云雾观音", "price": 22.0, "description": "茶香醇厚，适合喜欢茶味的用户"},
            {"name": "珍珠奶茶", "price": 16.0, "description": "经典口味，价格实惠"},
            {"name": "红豆奶茶", "price": 17.0, "description": "甜香浓郁，适合喜欢甜食的用户"},
        ]
    
    def generate_thoughts(self, 
                          user_query: str,
                          context: Dict,
                          depth: int) -> List[ThoughtNode]:
        """
        生成思维节点（探索不同的推荐路径）
        
        Args:
            user_query: 用户查询
            context: 上下文信息（用户偏好、预算等）
            depth: 当前深度
            
        Returns:
            思维节点列表
        """
        if depth >= self.max_depth:
            return []
        
        all_products = self.get_all_products()
        
        # 使用 LLM 生成不同的推荐思路
        prompt = f"""你是一个奶茶推荐专家，需要为用户的个性化需求生成不同的推荐思路。

用户需求: {user_query}
可用产品: {', '.join([p['name'] for p in all_products])}
当前搜索深度: {depth}

请生成 {self.branching_factor} 个不同的推荐思路，每个思路应该：
1. 从不同维度考虑（如：价格、口味、健康、库存等）
2. 选择不同的产品组合
3. 给出推荐理由

请以 JSON 格式返回，格式如下：
{{
    "thoughts": [
        {{
            "thought": "推荐思路描述（如：基于价格实惠的推荐）",
            "products": ["产品名称1", "产品名称2"],
            "reasoning": "推荐理由"
        }},
        ...
    ]
}}

只返回 JSON，不要其他文字。"""
        
        try:
            response = Generation.call(
                model=DASHSCOPE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,  # 较高温度，鼓励多样性
                result_format='message'
            )
            
            if response.status_code == 200:
                result_text = response.output.choices[0].message.content.strip()
                # 提取 JSON
                import re
                json_match = re.search(r'\{.*?\}', result_text, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group())
                    thoughts = result_json.get("thoughts", [])
                    
                    nodes = []
                    for thought_data in thoughts[:self.branching_factor]:
                        # 匹配产品名称到实际产品对象
                        product_names = thought_data.get("products", [])
                        matched_products = [
                            p for p in all_products 
                            if p['name'] in product_names
                        ]
                        
                        if matched_products:
                            node = ThoughtNode(
                                thought=thought_data.get("thought", ""),
                                products=matched_products,
                                reasoning=thought_data.get("reasoning", "")
                            )
                            nodes.append(node)
                    
                    return nodes
        except Exception as e:
            print(f"[ToT] 生成思维节点失败: {str(e)}", file=sys.stderr, flush=True)
        
        return []
    
    def evaluate_thought(self, 
                         node: ThoughtNode,
                         user_query: str,
                         context: Dict) -> float:
        """
        评估思维节点的质量（评分 0-1）
        
        Args:
            node: 思维节点
            user_query: 用户查询
            context: 上下文信息
            
        Returns:
            评分（0-1）
        """
        if not node.products:
            return 0.0
        
        # 使用 LLM 评估推荐质量
        products_desc = "\n".join([
            f"- {p['name']}: ¥{p.get('price', 0):.2f}, {p.get('description', '')}"
            for p in node.products
        ])
        
        prompt = f"""你是一个推荐系统评估专家，需要评估推荐质量。

用户需求: {user_query}
推荐思路: {node.thought}
推荐理由: {node.reasoning}
推荐产品:
{products_desc}

请从以下维度评估这个推荐：
1. 是否符合用户需求（0-0.4分）
2. 产品选择的合理性（0-0.3分）
3. 推荐理由的说服力（0-0.3分）

请返回一个 0-1 之间的评分，只返回数字，不要其他文字。"""
        
        try:
            response = Generation.call(
                model=DASHSCOPE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 低温度，确保评估一致性
                result_format='message'
            )
            
            if response.status_code == 200:
                result_text = response.output.choices[0].message.content.strip()
                # 提取数字
                import re
                score_match = re.search(r'0?\.\d+|1\.0|0', result_text)
                if score_match:
                    score = float(score_match.group())
                    return min(max(score, 0.0), 1.0)  # 确保在 0-1 范围内
        except Exception as e:
            print(f"[ToT] 评估思维节点失败: {str(e)}", file=sys.stderr, flush=True)
        
        # 默认评分：基于产品数量和质量
        return min(len(node.products) * 0.2, 1.0)
    
    def search(self, 
              user_query: str,
              context: Dict = None) -> Optional[ThoughtNode]:
        """
        使用 Tree of Thoughts 搜索最优推荐
        
        Args:
            user_query: 用户查询
            context: 上下文信息
            
        Returns:
            最优推荐节点
        """
        if context is None:
            context = {}
        
        # 初始化根节点
        root = ThoughtNode(
            thought="初始推荐",
            products=[],
            reasoning="开始搜索"
        )
        
        # 广度优先搜索
        queue = [(root, 0)]  # (node, depth)
        best_node = None
        best_score = 0.0
        node_count = 0
        
        while queue and node_count < self.max_nodes:
            current_node, depth = queue.pop(0)
            node_count += 1
            
            # 如果当前节点有产品，评估它
            if current_node.products:
                score = self.evaluate_thought(current_node, user_query, context)
                current_node.score = score
                
                # 更新最优节点
                if score > best_score:
                    best_score = score
                    best_node = current_node
            
            # 如果还没到最大深度，生成子节点
            if depth < self.max_depth and node_count < self.max_nodes:
                child_nodes = self.generate_thoughts(user_query, context, depth + 1)
                
                for child in child_nodes:
                    current_node.add_child(child)
                    queue.append((child, depth + 1))
        
        # 如果没有找到最优节点，返回根节点的第一个子节点
        if best_node is None and root.children:
            # 评估所有叶子节点，选择最优的
            for child in root.children:
                if child.products:
                    score = self.evaluate_thought(child, user_query, context)
                    child.score = score
                    if score > best_score:
                        best_score = score
                        best_node = child
        
        return best_node if best_node else root
    
    def format_recommendation(self, node: ThoughtNode) -> str:
        """
        格式化推荐结果为用户友好的文本
        
        Args:
            node: 推荐节点
            
        Returns:
            格式化的推荐文本
        """
        if not node.products:
            return "抱歉，暂时没有找到合适的推荐。"
        
        result = f"🎯 推荐思路：{node.thought}\n\n"
        result += f"💡 推荐理由：{node.reasoning}\n\n"
        result += "📦 推荐产品：\n"
        
        total_price = 0.0
        for i, product in enumerate(node.products, 1):
            price = product.get('price', 0)
            total_price += price
            result += f"{i}. {product['name']} - ¥{price:.2f}\n"
            if product.get('description'):
                result += f"   {product['description']}\n"
        
        result += f"\n💰 总价：¥{total_price:.2f}\n"
        result += f"⭐ 推荐评分：{node.score:.2f}/1.0"
        
        return result


def test_tot_recommendation():
    """测试 ToT 推荐功能"""
    from consult_mcp_server.consult_service import ConsultService
    
    consult_service = ConsultService()
    engine = ToTRecommendationEngine(consult_service=consult_service)
    
    # 测试场景1：个性化推荐
    print("\n" + "="*60)
    print("测试场景1：个性化推荐")
    print("="*60)
    user_query = "我想要一杯适合我的奶茶，我喜欢清淡的口味，预算在20元左右"
    
    best_node = engine.search(user_query)
    if best_node:
        recommendation = engine.format_recommendation(best_node)
        print(f"\n用户需求：{user_query}")
        print(f"\n{recommendation}")
    
    # 测试场景2：健康需求推荐
    print("\n" + "="*60)
    print("测试场景2：健康需求推荐")
    print("="*60)
    user_query = "我想要一杯低糖的奶茶，不要太甜"
    
    best_node = engine.search(user_query)
    if best_node:
        recommendation = engine.format_recommendation(best_node)
        print(f"\n用户需求：{user_query}")
        print(f"\n{recommendation}")


if __name__ == "__main__":
    test_tot_recommendation()

