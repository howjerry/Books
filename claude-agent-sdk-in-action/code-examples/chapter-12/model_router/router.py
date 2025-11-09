"""
智能模型路由器

根据任务复杂度自动选择最合适的模型，平衡成本与质量。
"""

from typing import Dict, Optional
from enum import Enum
from anthropic import Anthropic


class TaskComplexity(Enum):
    """任务复杂度枚举"""
    SIMPLE = "simple"          # 简单任务（FAQ、分类）
    MODERATE = "moderate"      # 中等任务（摘要、翻译）
    COMPLEX = "complex"        # 复杂任务（代码生成、深度分析）


class ModelRouter:
    """
    智能模型路由器

    核心功能：
    1. 分析任务复杂度
    2. 选择最优模型
    3. 成本预测
    4. 性能监控
    """

    # 模型性能与成本配置
    MODEL_PROFILES = {
        "claude-haiku-3-20250307": {
            "capability": 1.0,
            "cost_multiplier": 1.0,
            "suitable_for": [TaskComplexity.SIMPLE],
            "max_tokens": 200_000,
            "strengths": ["速度快", "成本低", "简单任务"],
            "pricing": {
                "input": 0.25,   # 每百万 token
                "output": 1.25
            }
        },
        "claude-sonnet-4-20250514": {
            "capability": 2.5,
            "cost_multiplier": 12.0,
            "suitable_for": [TaskComplexity.SIMPLE, TaskComplexity.MODERATE],
            "max_tokens": 200_000,
            "strengths": ["平衡性能", "通用任务", "适合大部分场景"],
            "pricing": {
                "input": 3.00,
                "output": 15.00
            }
        },
        "claude-opus-4-20250514": {
            "capability": 3.0,
            "cost_multiplier": 60.0,
            "suitable_for": [TaskComplexity.MODERATE, TaskComplexity.COMPLEX],
            "max_tokens": 200_000,
            "strengths": ["最高性能", "复杂推理", "关键任务"],
            "pricing": {
                "input": 15.00,
                "output": 75.00
            }
        }
    }

    def __init__(self, api_key: str, default_model: str = "claude-sonnet-4-20250514"):
        """
        初始化路由器

        Args:
            api_key: Anthropic API Key
            default_model: 默认模型
        """
        self.client = Anthropic(api_key=api_key)
        self.default_model = default_model

    def analyze_complexity(self, prompt: str) -> TaskComplexity:
        """
        分析任务复杂度

        Args:
            prompt: 用户提示词

        Returns:
            任务复杂度
        """
        # 复杂度判断关键词
        complex_keywords = [
            "代码", "code", "implement", "设计", "design", "架构", "architecture",
            "优化", "optimize", "重构", "refactor", "分析", "analyze", "推理", "reasoning"
        ]

        moderate_keywords = [
            "总结", "summarize", "翻译", "translate", "改写", "rewrite",
            "解释", "explain", "比较", "compare"
        ]

        simple_keywords = [
            "分类", "classify", "提取", "extract", "FAQ", "查询", "query"
        ]

        prompt_lower = prompt.lower()

        # 检查关键词
        if any(kw in prompt_lower for kw in complex_keywords):
            return TaskComplexity.COMPLEX
        elif any(kw in prompt_lower for kw in moderate_keywords):
            return TaskComplexity.MODERATE
        elif any(kw in prompt_lower for kw in simple_keywords):
            return TaskComplexity.SIMPLE

        # 基于长度判断
        if len(prompt) > 2000:
            return TaskComplexity.COMPLEX
        elif len(prompt) > 500:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.SIMPLE

    def select_model(
        self,
        complexity: TaskComplexity,
        budget_mode: bool = False
    ) -> str:
        """
        选择最合适的模型

        Args:
            complexity: 任务复杂度
            budget_mode: 是否启用预算模式（优先考虑成本）

        Returns:
            模型名称
        """
        suitable_models = [
            (name, profile)
            for name, profile in self.MODEL_PROFILES.items()
            if complexity in profile["suitable_for"]
        ]

        if not suitable_models:
            return self.default_model

        if budget_mode:
            # 预算模式：选择最便宜的合适模型
            return min(suitable_models, key=lambda x: x[1]["cost_multiplier"])[0]
        else:
            # 性能模式：选择性能最好的合适模型
            return max(suitable_models, key=lambda x: x[1]["capability"])[0]

    def estimate_cost(
        self,
        model: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int
    ) -> Dict:
        """
        预估成本

        Args:
            model: 模型名称
            estimated_input_tokens: 预估输入 Token 数
            estimated_output_tokens: 预估输出 Token 数

        Returns:
            成本预估信息
        """
        profile = self.MODEL_PROFILES.get(model, self.MODEL_PROFILES[self.default_model])
        pricing = profile["pricing"]

        input_cost = (estimated_input_tokens / 1_000_000) * pricing["input"]
        output_cost = (estimated_output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        return {
            "model": model,
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "input_cost": round(input_cost, 4),
            "output_cost": round(output_cost, 4),
            "total_cost": round(total_cost, 4)
        }

    def route_and_call(
        self,
        prompt: str,
        max_tokens: int = 4096,
        budget_mode: bool = False,
        override_model: Optional[str] = None
    ) -> Dict:
        """
        路由并调用模型

        Args:
            prompt: 用户提示词
            max_tokens: 最大输出 Token 数
            budget_mode: 是否启用预算模式
            override_model: 强制使用的模型（跳过路由）

        Returns:
            响应结果和成本信息
        """
        # 1. 分析复杂度
        complexity = self.analyze_complexity(prompt)

        # 2. 选择模型
        if override_model:
            model = override_model
        else:
            model = self.select_model(complexity, budget_mode)

        # 3. 预估成本
        estimated_input_tokens = len(prompt) // 4  # 粗略估算
        cost_estimate = self.estimate_cost(model, estimated_input_tokens, max_tokens // 2)

        # 4. 调用 API
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        # 5. 实际成本
        actual_cost = self.estimate_cost(
            model,
            response.usage.input_tokens,
            response.usage.output_tokens
        )

        return {
            "response": response.content[0].text,
            "complexity": complexity.value,
            "model_used": model,
            "cost_estimate": cost_estimate,
            "actual_cost": actual_cost,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        }

    def get_model_comparison(self) -> Dict:
        """
        获取模型对比信息

        Returns:
            模型对比表
        """
        comparison = {}

        for model, profile in self.MODEL_PROFILES.items():
            comparison[model] = {
                "capability_score": profile["capability"],
                "cost_multiplier": profile["cost_multiplier"],
                "suitable_for": [c.value for c in profile["suitable_for"]],
                "strengths": profile["strengths"],
                "pricing_input": f"${profile['pricing']['input']}/M tokens",
                "pricing_output": f"${profile['pricing']['output']}/M tokens"
            }

        return comparison
