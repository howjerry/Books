"""
智能模型路由器

根据任务複雜度自动選擇最合适的模型，平衡成本与質量。
"""

from typing import Dict, Optional
from enum import Enum
from anthropic import Anthropic


class TaskComplexity(Enum):
    """任务複雜度枚举"""
    SIMPLE = "simple"          # 簡單任务（FAQ、分类）
    MODERATE = "moderate"      # 中等任务（摘要、翻译）
    COMPLEX = "complex"        # 複雜任务（代码生成、深度分析）


class ModelRouter:
    """
    智能模型路由器

    核心功能：
    1. 分析任务複雜度
    2. 選擇最优模型
    3. 成本预测
    4. 性能監控
    """

    # 模型性能与成本配置
    MODEL_PROFILES = {
        "claude-haiku-3-20250307": {
            "capability": 1.0,
            "cost_multiplier": 1.0,
            "suitable_for": [TaskComplexity.SIMPLE],
            "max_tokens": 200_000,
            "strengths": ["速度快", "成本低", "簡單任务"],
            "pricing": {
                "input": 0.25,   # 每百萬 token
                "output": 1.25
            }
        },
        "claude-sonnet-4-20250514": {
            "capability": 2.5,
            "cost_multiplier": 12.0,
            "suitable_for": [TaskComplexity.SIMPLE, TaskComplexity.MODERATE],
            "max_tokens": 200_000,
            "strengths": ["平衡性能", "通用任务", "適合大部分場景"],
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
            "strengths": ["最高性能", "複雜推理", "關鍵任务"],
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
            default_model: 默認模型
        """
        self.client = Anthropic(api_key=api_key)
        self.default_model = default_model

    def analyze_complexity(self, prompt: str) -> TaskComplexity:
        """
        分析任务複雜度

        Args:
            prompt: 用戶提示词

        Returns:
            任务複雜度
        """
        # 複雜度判断關鍵词
        complex_keywords = [
            "代码", "code", "implement", "设计", "design", "架构", "architecture",
            "優化", "optimize", "重构", "refactor", "分析", "analyze", "推理", "reasoning"
        ]

        moderate_keywords = [
            "總結", "summarize", "翻译", "translate", "改写", "rewrite",
            "解释", "explain", "比较", "compare"
        ]

        simple_keywords = [
            "分类", "classify", "提取", "extract", "FAQ", "查詢", "query"
        ]

        prompt_lower = prompt.lower()

        # 檢查關鍵词
        if any(kw in prompt_lower for kw in complex_keywords):
            return TaskComplexity.COMPLEX
        elif any(kw in prompt_lower for kw in moderate_keywords):
            return TaskComplexity.MODERATE
        elif any(kw in prompt_lower for kw in simple_keywords):
            return TaskComplexity.SIMPLE

        # 基于長度判断
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
        選擇最合适的模型

        Args:
            complexity: 任务複雜度
            budget_mode: 是否啟用預算模式（优先考慮成本）

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
            # 預算模式：選擇最便宜的合适模型
            return min(suitable_models, key=lambda x: x[1]["cost_multiplier"])[0]
        else:
            # 性能模式：選擇性能最好的合适模型
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
            成本预估資訊
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
        路由并呼叫模型

        Args:
            prompt: 用戶提示词
            max_tokens: 最大输出 Token 数
            budget_mode: 是否啟用預算模式
            override_model: 强制使用的模型（跳過路由）

        Returns:
            響應结果和成本資訊
        """
        # 1. 分析複雜度
        complexity = self.analyze_complexity(prompt)

        # 2. 選擇模型
        if override_model:
            model = override_model
        else:
            model = self.select_model(complexity, budget_mode)

        # 3. 预估成本
        estimated_input_tokens = len(prompt) // 4  # 粗略估算
        cost_estimate = self.estimate_cost(model, estimated_input_tokens, max_tokens // 2)

        # 4. 呼叫 API
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        # 5. 實際成本
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
        獲取模型對比資訊

        Returns:
            模型對比表
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
