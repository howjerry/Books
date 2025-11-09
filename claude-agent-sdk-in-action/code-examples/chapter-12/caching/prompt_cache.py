"""
Prompt Caching 管理器

利用 Anthropic 的 Prompt Caching 功能节省成本。
"""

from typing import List, Dict, Optional
from anthropic import Anthropic


class PromptCache:
    """
    Prompt Caching 管理器

    核心功能：
    1. 缓存静态上下文
    2. 自动计算缓存收益
    3. 缓存策略优化
    4. 缓存监控
    """

    # 缓存定价折扣
    CACHE_DISCOUNT = 0.9  # 缓存命中可节省 90% 成本

    def __init__(self, api_key: str):
        """
        初始化缓存管理器

        Args:
            api_key: Anthropic API Key
        """
        self.client = Anthropic(api_key=api_key)
        self.cache_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_savings": 0.0
        }

    def create_cached_message(
        self,
        static_context: str,
        dynamic_query: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096
    ) -> Dict:
        """
        创建带缓存的消息

        Args:
            static_context: 静态上下文（会被缓存）
            dynamic_query: 动态查询（不缓存）
            model: 模型名称
            max_tokens: 最大输出 Token 数

        Returns:
            响应结果和缓存统计
        """
        # 使用 cache_control 标记静态内容
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": static_context,
                    "cache_control": {"type": "ephemeral"}  # 启用缓存
                }
            ],
            messages=[
                {"role": "user", "content": dynamic_query}
            ]
        )

        # 提取缓存统计
        usage = response.usage
        cache_creation_tokens = getattr(usage, 'cache_creation_input_tokens', 0)
        cache_read_tokens = getattr(usage, 'cache_read_input_tokens', 0)

        # 更新统计
        self.cache_stats["total_requests"] += 1
        if cache_read_tokens > 0:
            self.cache_stats["cache_hits"] += 1
        else:
            self.cache_stats["cache_misses"] += 1

        # 计算节省
        if cache_read_tokens > 0:
            # 假设 Sonnet 价格：输入 $3/M tokens
            normal_cost = (cache_read_tokens / 1_000_000) * 3.0
            cached_cost = (cache_read_tokens / 1_000_000) * 0.3  # 缓存读取价格
            savings = normal_cost - cached_cost
            self.cache_stats["total_savings"] += savings

        return {
            "response": response.content[0].text,
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "cache_read_tokens": cache_read_tokens
            },
            "cache_hit": cache_read_tokens > 0,
            "estimated_savings": savings if cache_read_tokens > 0 else 0.0
        }

    def create_multi_turn_conversation(
        self,
        system_prompt: str,
        conversation_history: List[Dict],
        new_message: str,
        model: str = "claude-sonnet-4-20250514"
    ) -> Dict:
        """
        创建多轮对话（缓存系统提示和历史记录）

        Args:
            system_prompt: 系统提示词（缓存）
            conversation_history: 对话历史（缓存）
            new_message: 新消息
            model: 模型名称

        Returns:
            响应结果
        """
        # 构建系统提示（缓存）
        system_messages = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ]

        # 构建消息历史
        messages = conversation_history.copy()

        # 标记最后几条消息为可缓存（假设对话历史较长）
        if len(messages) >= 3:
            # 缓存倒数第 3 条消息
            messages[-3]["cache_control"] = {"type": "ephemeral"}

        # 添加新消息
        messages.append({"role": "user", "content": new_message})

        response = self.client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_messages,
            messages=messages
        )

        return {
            "response": response.content[0].text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_tokens": getattr(response.usage, 'cache_read_input_tokens', 0)
            }
        }

    def analyze_cache_efficiency(
        self,
        static_content_length: int,
        expected_requests: int,
        model: str = "claude-sonnet-4-20250514"
    ) -> Dict:
        """
        分析缓存效率

        Args:
            static_content_length: 静态内容长度（字符数）
            expected_requests: 预期请求次数
            model: 模型名称

        Returns:
            缓存效率分析
        """
        # 粗略估算 Token 数（1 token ≈ 4 字符）
        static_tokens = static_content_length // 4

        # 模型定价（简化）
        pricing = {
            "claude-haiku-3-20250307": {"input": 0.25, "cache_read": 0.03},
            "claude-sonnet-4-20250514": {"input": 3.00, "cache_read": 0.30},
            "claude-opus-4-20250514": {"input": 15.00, "cache_read": 1.50}
        }

        model_pricing = pricing.get(model, pricing["claude-sonnet-4-20250514"])

        # 计算成本
        # 无缓存成本
        no_cache_cost = (static_tokens / 1_000_000) * model_pricing["input"] * expected_requests

        # 有缓存成本
        # 第 1 次：写入缓存（稍贵）
        first_request_cost = (static_tokens / 1_000_000) * (model_pricing["input"] * 1.25)
        # 后续：读取缓存（便宜）
        subsequent_cost = (static_tokens / 1_000_000) * model_pricing["cache_read"] * (expected_requests - 1)
        with_cache_cost = first_request_cost + subsequent_cost

        # 节省
        total_savings = no_cache_cost - with_cache_cost
        savings_percentage = (total_savings / no_cache_cost) * 100

        # 投资回收期（需要多少次请求才能收回成本）
        breakeven_requests = 2  # 通常 2 次请求后就开始节省

        return {
            "static_tokens": static_tokens,
            "expected_requests": expected_requests,
            "cost_without_cache": round(no_cache_cost, 4),
            "cost_with_cache": round(with_cache_cost, 4),
            "total_savings": round(total_savings, 4),
            "savings_percentage": round(savings_percentage, 1),
            "breakeven_requests": breakeven_requests,
            "recommendation": "启用缓存" if savings_percentage > 10 else "不建议缓存（请求次数过少）"
        }

    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息

        Returns:
            缓存统计
        """
        hit_rate = 0.0
        if self.cache_stats["total_requests"] > 0:
            hit_rate = (self.cache_stats["cache_hits"] / self.cache_stats["total_requests"]) * 100

        return {
            "total_requests": self.cache_stats["total_requests"],
            "cache_hits": self.cache_stats["cache_hits"],
            "cache_misses": self.cache_stats["cache_misses"],
            "hit_rate_percentage": round(hit_rate, 1),
            "total_savings_usd": round(self.cache_stats["total_savings"], 2)
        }

    def reset_stats(self):
        """重置统计信息"""
        self.cache_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_savings": 0.0
        }


# 使用示例
def example_usage():
    """
    Prompt Caching 使用示例
    """
    import os

    cache = PromptCache(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # 场景：客服 Agent，FAQ 文档是静态的
    faq_document = """
    # 常见问题解答

    Q: 如何重置密码？
    A: 点击登录页面的"忘记密码"...

    Q: 如何联系客服？
    A: 拨打 400-123-4567...

    [包含 50+ 条 FAQ，约 10,000 tokens]
    """

    # 第 1 次调用（缓存未命中）
    result1 = cache.create_cached_message(
        static_context=faq_document,
        dynamic_query="如何重置密码？"
    )
    print(f"第 1 次调用 - 缓存命中: {result1['cache_hit']}")

    # 第 2 次调用（缓存命中！）
    result2 = cache.create_cached_message(
        static_context=faq_document,
        dynamic_query="客服电话是多少？"
    )
    print(f"第 2 次调用 - 缓存命中: {result2['cache_hit']}")
    print(f"节省成本: ${result2['estimated_savings']:.4f}")

    # 查看统计
    stats = cache.get_cache_stats()
    print(f"\n缓存统计:")
    print(f"  总请求: {stats['total_requests']}")
    print(f"  命中率: {stats['hit_rate_percentage']}%")
    print(f"  总节省: ${stats['total_savings_usd']}")


if __name__ == "__main__":
    example_usage()
