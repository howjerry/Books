#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 14 章：效能優化與成本控制
成本優化引擎

這個模組實現了完整的成本優化系統：
1. Token 消耗分析與優化
2. 多層智能快取
3. 成本監控與預算控制
4. 模型選擇與降級

使用方式：
    from cost_optimizer import CostOptimizer, OptimizationProfile

    optimizer = CostOptimizer(profile=OptimizationProfile.BALANCED)
    result = await optimizer.optimize_call(prompt, model="gpt-4")
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from collections import OrderedDict
import hashlib
import json
import asyncio


# =============================================================================
# 優化配置
# =============================================================================

class OptimizationProfile(Enum):
    """優化配置檔"""
    COST_FIRST = "cost_first"
    SPEED_FIRST = "speed_first"
    QUALITY_FIRST = "quality_first"
    BALANCED = "balanced"


@dataclass
class OptimizationTarget:
    """優化目標"""
    profile: OptimizationProfile
    cost_weight: float
    speed_weight: float
    quality_weight: float
    max_cost_per_query: float = 1.0
    max_latency_seconds: float = 60.0
    min_quality_score: float = 0.7

    @classmethod
    def from_profile(cls, profile: OptimizationProfile) -> "OptimizationTarget":
        configs = {
            OptimizationProfile.COST_FIRST: {
                "cost_weight": 0.6, "speed_weight": 0.2, "quality_weight": 0.2,
                "max_cost_per_query": 0.1, "max_latency_seconds": 120.0, "min_quality_score": 0.6
            },
            OptimizationProfile.SPEED_FIRST: {
                "cost_weight": 0.2, "speed_weight": 0.6, "quality_weight": 0.2,
                "max_cost_per_query": 2.0, "max_latency_seconds": 15.0, "min_quality_score": 0.6
            },
            OptimizationProfile.QUALITY_FIRST: {
                "cost_weight": 0.2, "speed_weight": 0.2, "quality_weight": 0.6,
                "max_cost_per_query": 5.0, "max_latency_seconds": 300.0, "min_quality_score": 0.9
            },
            OptimizationProfile.BALANCED: {
                "cost_weight": 0.34, "speed_weight": 0.33, "quality_weight": 0.33,
                "max_cost_per_query": 1.0, "max_latency_seconds": 60.0, "min_quality_score": 0.75
            }
        }
        return cls(profile=profile, **configs[profile])


# =============================================================================
# Token 分析與優化
# =============================================================================

@dataclass
class TokenUsage:
    """Token 使用記錄"""
    input_tokens: int
    output_tokens: int
    model: str
    timestamp: datetime = field(default_factory=datetime.now)
    operation: str = "unknown"

    PRICING = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "qwen-72b": {"input": 0.001, "output": 0.002},
    }

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost(self) -> float:
        pricing = self.PRICING.get(self.model, {"input": 0.01, "output": 0.03})
        return (
            self.input_tokens * pricing["input"] / 1000 +
            self.output_tokens * pricing["output"] / 1000
        )


class TokenAnalyzer:
    """Token 分析器"""

    def __init__(self):
        self.usage_history: List[TokenUsage] = []

    def count_tokens(self, text: str) -> int:
        """簡化的 token 計算"""
        # 實際應用中應使用 tiktoken
        return len(text) // 4

    def record_usage(self, usage: TokenUsage):
        self.usage_history.append(usage)

    def get_statistics(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        history = self.usage_history
        if since:
            history = [u for u in history if u.timestamp >= since]

        if not history:
            return {"total_tokens": 0, "total_cost": 0}

        total_input = sum(u.input_tokens for u in history)
        total_output = sum(u.output_tokens for u in history)
        total_cost = sum(u.cost for u in history)

        by_model = {}
        for usage in history:
            if usage.model not in by_model:
                by_model[usage.model] = {"calls": 0, "cost": 0}
            by_model[usage.model]["calls"] += 1
            by_model[usage.model]["cost"] += usage.cost

        return {
            "total_calls": len(history),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost": total_cost,
            "avg_cost_per_call": total_cost / len(history) if history else 0,
            "by_model": by_model
        }


class TokenOptimizer:
    """Token 優化器"""

    def __init__(self, analyzer: TokenAnalyzer):
        self.analyzer = analyzer

    def compress_prompt(self, prompt: str, max_tokens: int) -> str:
        """壓縮提示"""
        current_tokens = self.analyzer.count_tokens(prompt)
        if current_tokens <= max_tokens:
            return prompt

        # 移除多餘空白
        compressed = " ".join(prompt.split())
        if self.analyzer.count_tokens(compressed) <= max_tokens:
            return compressed

        # 截斷
        words = compressed.split()
        while self.analyzer.count_tokens(" ".join(words)) > max_tokens and len(words) > 10:
            mid = len(words) // 2
            words = words[:mid-1] + ["..."] + words[mid+1:]

        return " ".join(words)

    def optimize_history(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        keep_recent: int = 3
    ) -> List[Dict[str, str]]:
        """優化對話歷史"""
        if not messages:
            return messages

        total = sum(self.analyzer.count_tokens(m.get("content", "")) for m in messages)
        if total <= max_tokens:
            return messages

        recent = messages[-keep_recent:] if len(messages) > keep_recent else messages
        older = messages[:-keep_recent] if len(messages) > keep_recent else []

        if older:
            older_content = "\n".join(m.get("content", "") for m in older)
            remaining = max_tokens - sum(
                self.analyzer.count_tokens(m.get("content", "")) for m in recent
            )
            if remaining > 100:
                compressed = self.compress_prompt(older_content, remaining)
                return [{"role": "system", "content": f"[摘要]: {compressed}"}] + recent

        return recent


# =============================================================================
# 快取系統
# =============================================================================

@dataclass
class CacheEntry:
    """快取條目"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and datetime.now() > self.expires_at


class MemoryCache:
    """L1 記憶體快取"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {"hits": 0, "misses": 0}

    async def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry is None or entry.is_expired:
            self._stats["misses"] += 1
            if entry and entry.is_expired:
                del self._cache[key]
            return None

        self._cache.move_to_end(key)
        entry.hit_count += 1
        self._stats["hits"] += 1
        return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)

        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(key=key, value=value, expires_at=expires_at)

    @property
    def hit_rate(self) -> float:
        total = self._stats["hits"] + self._stats["misses"]
        return self._stats["hits"] / total if total > 0 else 0


class MultiLayerCache:
    """多層快取管理器"""

    def __init__(self, l1_cache: Optional[MemoryCache] = None):
        self.l1 = l1_cache or MemoryCache()
        self._stats = {"l1_hits": 0, "misses": 0}

    async def get(self, key: str) -> Optional[Any]:
        result = await self.l1.get(key)
        if result is not None:
            self._stats["l1_hits"] += 1
            return result
        self._stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        await self.l1.set(key, value, ttl)

    def get_stats(self) -> Dict[str, Any]:
        total = self._stats["l1_hits"] + self._stats["misses"]
        return {
            **self._stats,
            "hit_rate": self._stats["l1_hits"] / total if total > 0 else 0,
            "l1_hit_rate": self.l1.hit_rate
        }


def generate_cache_key(query: str, model: str = "", params: Optional[Dict] = None) -> str:
    """生成快取鍵"""
    key_parts = [query, model]
    if params:
        key_parts.append(json.dumps(params, sort_keys=True))
    return hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:32]


# =============================================================================
# 成本追蹤與預算
# =============================================================================

class BudgetPeriod(Enum):
    """預算週期"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class Budget:
    """預算配置"""
    period: BudgetPeriod
    limit: float
    warning_threshold: float = 0.8
    hard_limit: bool = True


@dataclass
class CostRecord:
    """成本記錄"""
    timestamp: datetime
    operation: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class CostTracker:
    """成本追蹤器"""

    def __init__(self):
        self.records: List[CostRecord] = []
        self.budgets: Dict[BudgetPeriod, Budget] = {}
        self._callbacks: List[Callable] = []

    def set_budget(self, budget: Budget):
        self.budgets[budget.period] = budget

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = TokenUsage.PRICING.get(model, {"input": 0.01, "output": 0.03})
        return input_tokens * pricing["input"] / 1000 + output_tokens * pricing["output"] / 1000

    def record(self, operation: str, model: str, input_tokens: int, output_tokens: int) -> CostRecord:
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        record = CostRecord(
            timestamp=datetime.now(),
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
        self.records.append(record)
        self._check_budgets()
        return record

    def get_summary(self, period: Optional[BudgetPeriod] = None) -> Dict[str, Any]:
        records = self.records
        if period:
            since = self._get_period_start(period)
            records = [r for r in records if r.timestamp >= since]

        if not records:
            return {"total_cost": 0, "total_calls": 0}

        return {
            "total_cost": sum(r.cost for r in records),
            "total_calls": len(records),
            "avg_cost": sum(r.cost for r in records) / len(records)
        }

    def check_can_proceed(self, estimated_cost: float, period: BudgetPeriod = BudgetPeriod.DAILY) -> Tuple[bool, str]:
        if period not in self.budgets:
            return True, "無預算限制"

        budget = self.budgets[period]
        current = self.get_summary(period)["total_cost"]

        if current + estimated_cost > budget.limit:
            if budget.hard_limit:
                return False, f"將超出預算（${current:.4f}/${budget.limit:.2f}）"
        return True, "OK"

    def _get_period_start(self, period: BudgetPeriod) -> datetime:
        now = datetime.now()
        if period == BudgetPeriod.HOURLY:
            return now.replace(minute=0, second=0, microsecond=0)
        elif period == BudgetPeriod.DAILY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == BudgetPeriod.WEEKLY:
            start = now - timedelta(days=now.weekday())
            return start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def _check_budgets(self):
        for period, budget in self.budgets.items():
            current = self.get_summary(period)["total_cost"]
            if current >= budget.limit * budget.warning_threshold:
                for cb in self._callbacks:
                    cb("warning", period, current, budget.limit)

    def on_budget_event(self, callback: Callable):
        self._callbacks.append(callback)


# =============================================================================
# 模型路由
# =============================================================================

class TaskComplexity(Enum):
    """任務複雜度"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


@dataclass
class ModelProfile:
    """模型配置"""
    name: str
    cost_per_1k: float
    quality_score: float
    speed_score: float
    capabilities: List[str]


class ModelRouter:
    """智能模型路由器"""

    MODELS = {
        "gpt-4o": ModelProfile("gpt-4o", 0.01, 9, 8, ["reasoning", "coding", "analysis"]),
        "gpt-3.5-turbo": ModelProfile("gpt-3.5-turbo", 0.001, 7, 9, ["basic", "conversation"]),
        "claude-3-opus": ModelProfile("claude-3-opus", 0.045, 10, 6, ["reasoning", "analysis", "writing"]),
        "claude-3-sonnet": ModelProfile("claude-3-sonnet", 0.009, 8.5, 8, ["reasoning", "coding"]),
        "claude-3-haiku": ModelProfile("claude-3-haiku", 0.00075, 7, 10, ["basic", "summarization"]),
    }

    FALLBACK_CHAIN = {
        "claude-3-opus": ["claude-3-sonnet", "gpt-4o"],
        "gpt-4o": ["claude-3-sonnet", "gpt-3.5-turbo"],
        "claude-3-sonnet": ["claude-3-haiku", "gpt-3.5-turbo"],
        "gpt-3.5-turbo": ["claude-3-haiku"],
    }

    def select_model(
        self,
        complexity: TaskComplexity,
        prefer_speed: bool = False,
        prefer_quality: bool = False,
        max_cost: Optional[float] = None
    ) -> str:
        candidates = list(self.MODELS.values())

        if max_cost:
            candidates = [m for m in candidates if m.cost_per_1k <= max_cost]

        if not candidates:
            return "gpt-3.5-turbo"

        def score(m: ModelProfile) -> float:
            s = 0
            if complexity == TaskComplexity.EXPERT:
                s += m.quality_score * 2
            elif complexity == TaskComplexity.SIMPLE:
                s += (10 - m.cost_per_1k * 100) * 2
            else:
                s += m.quality_score

            if prefer_speed:
                s += m.speed_score
            if prefer_quality:
                s += m.quality_score
            return s

        candidates.sort(key=score, reverse=True)
        return candidates[0].name

    def get_fallback(self, model: str) -> Optional[str]:
        chain = self.FALLBACK_CHAIN.get(model, [])
        return chain[0] if chain else None


# =============================================================================
# 並行處理
# =============================================================================

class ParallelExecutor:
    """並行執行器"""

    def __init__(self, max_concurrency: int = 10, retry_count: int = 3):
        self.max_concurrency = max_concurrency
        self.retry_count = retry_count
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_all(self, tasks: List[Callable]) -> List[Any]:
        async def run(task):
            async with self._semaphore:
                for attempt in range(self.retry_count):
                    try:
                        if asyncio.iscoroutinefunction(task):
                            return await task()
                        return task()
                    except Exception as e:
                        if attempt == self.retry_count - 1:
                            raise
                        await asyncio.sleep(1 * (2 ** attempt))

        return await asyncio.gather(*[run(t) for t in tasks], return_exceptions=True)


class RateLimiter:
    """速率限制器"""

    def __init__(self, requests_per_second: float = 10):
        self.rps = requests_per_second
        self._tokens = requests_per_second
        self._last_refill = datetime.now()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            self._refill()
            while self._tokens < 1:
                await asyncio.sleep(0.1)
                self._refill()
            self._tokens -= 1

    def _refill(self):
        now = datetime.now()
        elapsed = (now - self._last_refill).total_seconds()
        self._tokens = min(self.rps, self._tokens + elapsed * self.rps)
        self._last_refill = now


# =============================================================================
# 整合優化器
# =============================================================================

class CostOptimizer:
    """
    成本優化引擎

    整合所有優化功能
    """

    def __init__(self, profile: OptimizationProfile = OptimizationProfile.BALANCED):
        self.target = OptimizationTarget.from_profile(profile)
        self.analyzer = TokenAnalyzer()
        self.token_optimizer = TokenOptimizer(self.analyzer)
        self.cache = MultiLayerCache()
        self.cost_tracker = CostTracker()
        self.model_router = ModelRouter()
        self.rate_limiter = RateLimiter()
        self.executor = ParallelExecutor()

    async def optimize_call(
        self,
        prompt: str,
        model: str = "gpt-4o",
        use_cache: bool = True,
        allow_fallback: bool = True
    ) -> Dict[str, Any]:
        """優化 LLM 調用"""

        # 1. 檢查快取
        if use_cache:
            cache_key = generate_cache_key(prompt, model)
            cached = await self.cache.get(cache_key)
            if cached:
                return {"result": cached, "from_cache": True, "cost": 0}

        # 2. 優化 prompt
        compressed = self.token_optimizer.compress_prompt(
            prompt, max_tokens=4000
        )

        # 3. 估算成本
        input_tokens = self.analyzer.count_tokens(compressed)
        estimated_cost = self.cost_tracker.calculate_cost(model, input_tokens, 500)

        # 4. 檢查預算
        can_proceed, msg = self.cost_tracker.check_can_proceed(estimated_cost)
        if not can_proceed and allow_fallback:
            fallback = self.model_router.get_fallback(model)
            if fallback:
                model = fallback
                estimated_cost = self.cost_tracker.calculate_cost(model, input_tokens, 500)
                can_proceed, msg = self.cost_tracker.check_can_proceed(estimated_cost)

        if not can_proceed:
            return {"error": msg, "result": None}

        # 5. 速率限制
        await self.rate_limiter.acquire()

        # 6. 模擬 LLM 調用（實際應調用真實 API）
        result = f"[{model}] Response to: {compressed[:50]}..."
        output_tokens = self.analyzer.count_tokens(result)

        # 7. 記錄成本
        self.cost_tracker.record("llm_call", model, input_tokens, output_tokens)

        # 8. 快取結果
        if use_cache:
            await self.cache.set(cache_key, result)

        return {
            "result": result,
            "from_cache": False,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": self.cost_tracker.calculate_cost(model, input_tokens, output_tokens)
        }

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計數據"""
        return {
            "token_stats": self.analyzer.get_statistics(),
            "cache_stats": self.cache.get_stats(),
            "cost_stats": self.cost_tracker.get_summary()
        }


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範成本優化"""
    print("=" * 60)
    print("  成本優化引擎示範")
    print("=" * 60)

    # 創建優化器
    optimizer = CostOptimizer(profile=OptimizationProfile.BALANCED)

    # 設置預算
    optimizer.cost_tracker.set_budget(Budget(
        period=BudgetPeriod.DAILY,
        limit=1.0,
        warning_threshold=0.8
    ))

    # 模擬多次調用
    prompts = [
        "什麼是深度學習？",
        "解釋 Transformer 架構",
        "什麼是深度學習？",  # 重複，應該命中快取
        "比較 CNN 和 RNN 的差異",
    ]

    print("\n執行優化調用：")
    for prompt in prompts:
        result = await optimizer.optimize_call(prompt)
        print(f"\n  提示: {prompt[:30]}...")
        print(f"  快取命中: {result.get('from_cache', False)}")
        print(f"  模型: {result.get('model', 'N/A')}")
        print(f"  成本: ${result.get('cost', 0):.6f}")

    # 獲取統計
    stats = optimizer.get_stats()
    print("\n" + "-" * 40)
    print("統計數據：")
    print(f"  總調用: {stats['token_stats']['total_calls']}")
    print(f"  總成本: ${stats['cost_stats']['total_cost']:.6f}")
    print(f"  快取命中率: {stats['cache_stats']['hit_rate']:.2%}")


if __name__ == "__main__":
    asyncio.run(demo())
