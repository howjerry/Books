"""
Prompt Caching 管理器

利用 Anthropic 的 Prompt Caching 功能節省成本。
"""

from typing import List, Dict, Optional
from anthropic import Anthropic


class PromptCache:
    """
    Prompt Caching 管理器

    核心功能：
    1. 緩存靜態上下文
    2. 自动計算緩存收益
    3. 緩存策略優化
    4. 緩存監控
    """

    # 緩存定價折扣
    CACHE_DISCOUNT = 0.9  # 緩存命中可節省 90% 成本

    def __init__(self, api_key: str):
        """
        初始化緩存管理器

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
        創建带緩存的消息

        Args:
            static_context: 靜態上下文（會被緩存）
            dynamic_query: 動態查詢（不緩存）
            model: 模型名称
            max_tokens: 最大输出 Token 数

        Returns:
            響應结果和緩存统计
        """
        # 使用 cache_control 标记靜態內容
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": static_context,
                    "cache_control": {"type": "ephemeral"}  # 啟用緩存
                }
            ],
            messages=[
                {"role": "user", "content": dynamic_query}
            ]
        )

        # 提取緩存统计
        usage = response.usage
        cache_creation_tokens = getattr(usage, 'cache_creation_input_tokens', 0)
        cache_read_tokens = getattr(usage, 'cache_read_input_tokens', 0)

        # 更新统计
        self.cache_stats["total_requests"] += 1
        if cache_read_tokens > 0:
            self.cache_stats["cache_hits"] += 1
        else:
            self.cache_stats["cache_misses"] += 1

        # 計算節省
        if cache_read_tokens > 0:
            # 假設 Sonnet 价格：输入 $3/M tokens
            normal_cost = (cache_read_tokens / 1_000_000) * 3.0
            cached_cost = (cache_read_tokens / 1_000_000) * 0.3  # 緩存读取价格
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
        創建多轮對话（緩存系統提示和歷史記錄）

        Args:
            system_prompt: 系統提示词（緩存）
            conversation_history: 對话歷史（緩存）
            new_message: 新消息
            model: 模型名称

        Returns:
            響應结果
        """
        # 构建系統提示（緩存）
        system_messages = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ]

        # 构建消息歷史
        messages = conversation_history.copy()

        # 标记最后几条消息为可緩存（假設對话歷史较长）
        if len(messages) >= 3:
            # 緩存倒数第 3 条消息
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
        分析緩存效率

        Args:
            static_content_length: 靜態內容長度（字符数）
            expected_requests: 預期請求次数
            model: 模型名称

        Returns:
            緩存效率分析
        """
        # 粗略估算 Token 数（1 token ≈ 4 字符）
        static_tokens = static_content_length // 4

        # 模型定價（简化）
        pricing = {
            "claude-haiku-3-20250307": {"input": 0.25, "cache_read": 0.03},
            "claude-sonnet-4-20250514": {"input": 3.00, "cache_read": 0.30},
            "claude-opus-4-20250514": {"input": 15.00, "cache_read": 1.50}
        }

        model_pricing = pricing.get(model, pricing["claude-sonnet-4-20250514"])

        # 計算成本
        # 无緩存成本
        no_cache_cost = (static_tokens / 1_000_000) * model_pricing["input"] * expected_requests

        # 有緩存成本
        # 第 1 次：写入緩存（稍贵）
        first_request_cost = (static_tokens / 1_000_000) * (model_pricing["input"] * 1.25)
        # 後續：读取緩存（便宜）
        subsequent_cost = (static_tokens / 1_000_000) * model_pricing["cache_read"] * (expected_requests - 1)
        with_cache_cost = first_request_cost + subsequent_cost

        # 節省
        total_savings = no_cache_cost - with_cache_cost
        savings_percentage = (total_savings / no_cache_cost) * 100

        # 投資回收期（需要多少次請求才能收回成本）
        breakeven_requests = 2  # 通常 2 次請求后就開始節省

        return {
            "static_tokens": static_tokens,
            "expected_requests": expected_requests,
            "cost_without_cache": round(no_cache_cost, 4),
            "cost_with_cache": round(with_cache_cost, 4),
            "total_savings": round(total_savings, 4),
            "savings_percentage": round(savings_percentage, 1),
            "breakeven_requests": breakeven_requests,
            "recommendation": "啟用緩存" if savings_percentage > 10 else "不建議緩存（請求次数過少）"
        }

    def get_cache_stats(self) -> Dict:
        """
        獲取緩存统计資訊

        Returns:
            緩存统计
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
        """重置统计資訊"""
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

    # 場景：客服 Agent，FAQ 文檔是靜態的
    faq_document = """
    # 常见問題解答

    Q: 如何重置密码？
    A: 点击登录页面的"忘记密码"...

    Q: 如何联系客服？
    A: 拨打 400-123-4567...

    [包含 50+ 条 FAQ，約 10,000 tokens]
    """

    # 第 1 次呼叫（緩存未命中）
    result1 = cache.create_cached_message(
        static_context=faq_document,
        dynamic_query="如何重置密码？"
    )
    print(f"第 1 次呼叫 - 緩存命中: {result1['cache_hit']}")

    # 第 2 次呼叫（緩存命中！）
    result2 = cache.create_cached_message(
        static_context=faq_document,
        dynamic_query="客服电话是多少？"
    )
    print(f"第 2 次呼叫 - 緩存命中: {result2['cache_hit']}")
    print(f"節省成本: ${result2['estimated_savings']:.4f}")

    # 查看统计
    stats = cache.get_cache_stats()
    print(f"\n緩存统计:")
    print(f"  總請求: {stats['total_requests']}")
    print(f"  命中率: {stats['hit_rate_percentage']}%")
    print(f"  總節省: ${stats['total_savings_usd']}")


if __name__ == "__main__":
    example_usage()
