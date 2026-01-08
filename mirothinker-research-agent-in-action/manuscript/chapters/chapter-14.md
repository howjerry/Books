# 第 14 章：效能優化與成本控制

> **本章目標**：掌握深度研究代理人的效能優化策略，學會 Token 效率提升、智能快取、成本監控與模型降級等實用技術。

---

## 14.1 效能與成本的平衡藝術

「快、好、省，你只能選兩個。」

這句老話在深度研究代理人的開發中同樣適用。一個能夠進行 600 次以上工具調用的代理人，每次研究可能消耗數萬甚至數十萬 Token。如果不加控制，成本將迅速失控。

### 14.1.1 成本構成分析

```
┌─────────────────────────────────────────────────────────────────┐
│                  深度研究代理人成本構成                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  LLM 調用成本（佔 60-80%）                                 │  │
│  │  ├── 輸入 Token：上下文、提示、歷史                        │  │
│  │  ├── 輸出 Token：生成的回答                                │  │
│  │  └── 模型選擇：不同模型價格差異 10-100 倍                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  搜尋與檢索成本（佔 10-20%）                               │  │
│  │  ├── 搜尋引擎 API 調用                                     │  │
│  │  ├── 網頁爬取與解析                                        │  │
│  │  └── 向量資料庫查詢                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  基礎設施成本（佔 10-20%）                                 │  │
│  │  ├── 計算資源（CPU/GPU）                                   │  │
│  │  ├── 儲存（快取、資料庫）                                  │  │
│  │  └── 網路流量                                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 14.1.2 優化目標矩陣

```python
#!/usr/bin/env python3
"""
效能與成本優化目標定義

不同場景下的優化策略
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


class OptimizationProfile(Enum):
    """優化配置檔"""
    COST_FIRST = "cost_first"           # 成本優先
    SPEED_FIRST = "speed_first"         # 速度優先
    QUALITY_FIRST = "quality_first"     # 品質優先
    BALANCED = "balanced"               # 平衡模式


@dataclass
class OptimizationTarget:
    """
    優化目標

    定義不同場景下的優化權重
    """
    profile: OptimizationProfile
    cost_weight: float      # 成本權重 0-1
    speed_weight: float     # 速度權重 0-1
    quality_weight: float   # 品質權重 0-1

    # 具體限制
    max_cost_per_query: float = 1.0      # 美元
    max_latency_seconds: float = 60.0    # 秒
    min_quality_score: float = 0.7       # 0-1

    @classmethod
    def from_profile(cls, profile: OptimizationProfile) -> "OptimizationTarget":
        """根據配置檔創建目標"""
        configs = {
            OptimizationProfile.COST_FIRST: {
                "cost_weight": 0.6,
                "speed_weight": 0.2,
                "quality_weight": 0.2,
                "max_cost_per_query": 0.1,
                "max_latency_seconds": 120.0,
                "min_quality_score": 0.6
            },
            OptimizationProfile.SPEED_FIRST: {
                "cost_weight": 0.2,
                "speed_weight": 0.6,
                "quality_weight": 0.2,
                "max_cost_per_query": 2.0,
                "max_latency_seconds": 15.0,
                "min_quality_score": 0.6
            },
            OptimizationProfile.QUALITY_FIRST: {
                "cost_weight": 0.2,
                "speed_weight": 0.2,
                "quality_weight": 0.6,
                "max_cost_per_query": 5.0,
                "max_latency_seconds": 300.0,
                "min_quality_score": 0.9
            },
            OptimizationProfile.BALANCED: {
                "cost_weight": 0.34,
                "speed_weight": 0.33,
                "quality_weight": 0.33,
                "max_cost_per_query": 1.0,
                "max_latency_seconds": 60.0,
                "min_quality_score": 0.75
            }
        }

        config = configs[profile]
        return cls(profile=profile, **config)
```

---

## 14.2 Token 效率優化

Token 是 LLM 調用成本的核心。優化 Token 使用效率可以顯著降低成本。

### 14.2.1 Token 消耗分析器

```python
#!/usr/bin/env python3
"""
Token 消耗分析與優化

分析和優化 Token 使用效率
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import tiktoken


@dataclass
class TokenUsage:
    """Token 使用記錄"""
    input_tokens: int
    output_tokens: int
    model: str
    timestamp: datetime = field(default_factory=datetime.now)
    operation: str = "unknown"

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost(self) -> float:
        """計算成本（美元）"""
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "qwen-72b": {"input": 0.001, "output": 0.002},
            "qwen-7b": {"input": 0.0001, "output": 0.0002},
        }

        model_pricing = pricing.get(self.model, {"input": 0.01, "output": 0.03})
        return (
            self.input_tokens * model_pricing["input"] / 1000 +
            self.output_tokens * model_pricing["output"] / 1000
        )


class TokenAnalyzer:
    """
    Token 分析器

    ‹1› 追蹤 Token 使用
    ‹2› 識別優化機會
    """

    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.usage_history: List[TokenUsage] = []

    def count_tokens(self, text: str) -> int:
        """計算文本的 Token 數量"""
        return len(self.encoding.encode(text))

    def record_usage(self, usage: TokenUsage):
        """記錄使用情況"""
        self.usage_history.append(usage)

    def get_statistics(
        self,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """獲取統計數據"""
        history = self.usage_history
        if since:
            history = [u for u in history if u.timestamp >= since]

        if not history:
            return {"total_tokens": 0, "total_cost": 0}

        total_input = sum(u.input_tokens for u in history)
        total_output = sum(u.output_tokens for u in history)
        total_cost = sum(u.cost for u in history)

        # 按模型分組
        by_model = {}
        for usage in history:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0
                }
            by_model[usage.model]["calls"] += 1
            by_model[usage.model]["input_tokens"] += usage.input_tokens
            by_model[usage.model]["output_tokens"] += usage.output_tokens
            by_model[usage.model]["cost"] += usage.cost

        # 按操作分組
        by_operation = {}
        for usage in history:
            if usage.operation not in by_operation:
                by_operation[usage.operation] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0
                }
            by_operation[usage.operation]["calls"] += 1
            by_operation[usage.operation]["tokens"] += usage.total_tokens
            by_operation[usage.operation]["cost"] += usage.cost

        return {
            "total_calls": len(history),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost": total_cost,
            "avg_tokens_per_call": (total_input + total_output) / len(history),
            "avg_cost_per_call": total_cost / len(history),
            "by_model": by_model,
            "by_operation": by_operation
        }

    def identify_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """識別優化機會"""
        opportunities = []
        stats = self.get_statistics()

        # 檢查輸入/輸出比例
        if stats["total_input_tokens"] > 0:
            ratio = stats["total_output_tokens"] / stats["total_input_tokens"]
            if ratio < 0.1:
                opportunities.append({
                    "type": "high_input_ratio",
                    "description": "輸入 Token 遠多於輸出，考慮壓縮上下文",
                    "potential_savings": "20-40%",
                    "priority": "high"
                })

        # 檢查高成本操作
        for op, data in stats.get("by_operation", {}).items():
            if data["cost"] > stats["total_cost"] * 0.3:
                opportunities.append({
                    "type": "high_cost_operation",
                    "description": f"操作 '{op}' 佔總成本 {data['cost']/stats['total_cost']*100:.1f}%",
                    "potential_savings": "10-30%",
                    "priority": "medium"
                })

        # 檢查模型選擇
        for model, data in stats.get("by_model", {}).items():
            if "gpt-4" in model or "opus" in model:
                opportunities.append({
                    "type": "expensive_model",
                    "description": f"使用高價模型 {model}，考慮部分任務降級",
                    "potential_savings": "50-80%",
                    "priority": "high"
                })

        return opportunities


class TokenOptimizer:
    """
    Token 優化器

    ‹3› 壓縮提示
    ‹4› 優化上下文
    """

    def __init__(self, analyzer: TokenAnalyzer):
        self.analyzer = analyzer

    def compress_prompt(
        self,
        prompt: str,
        max_tokens: int
    ) -> str:
        """
        壓縮提示

        ‹3› 在保持語義的前提下減少 Token
        """
        current_tokens = self.analyzer.count_tokens(prompt)

        if current_tokens <= max_tokens:
            return prompt

        # 策略 1：移除多餘空白
        compressed = " ".join(prompt.split())
        if self.analyzer.count_tokens(compressed) <= max_tokens:
            return compressed

        # 策略 2：縮短重複內容
        lines = compressed.split("\n")
        unique_lines = list(dict.fromkeys(lines))  # 保持順序去重
        compressed = "\n".join(unique_lines)
        if self.analyzer.count_tokens(compressed) <= max_tokens:
            return compressed

        # 策略 3：截斷（保留開頭和結尾）
        words = compressed.split()
        while self.analyzer.count_tokens(" ".join(words)) > max_tokens:
            # 從中間移除
            mid = len(words) // 2
            words = words[:mid-1] + ["..."] + words[mid+1:]

        return " ".join(words)

    def summarize_context(
        self,
        context: str,
        target_tokens: int,
        llm_client=None
    ) -> str:
        """
        摘要上下文

        ‹4› 使用 LLM 生成精簡摘要
        """
        current_tokens = self.analyzer.count_tokens(context)

        if current_tokens <= target_tokens:
            return context

        if llm_client is None:
            # 沒有 LLM，使用簡單截斷
            return self.compress_prompt(context, target_tokens)

        # 使用小模型生成摘要
        compression_ratio = target_tokens / current_tokens
        summary_prompt = f"""請將以下內容壓縮到約 {target_tokens} 個 token，保留最重要的資訊：

{context}

請直接輸出摘要，不要添加任何解釋。"""

        # 這裡應該調用 LLM，簡化處理
        return self.compress_prompt(context, target_tokens)

    def optimize_conversation_history(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        keep_recent: int = 3
    ) -> List[Dict[str, str]]:
        """
        優化對話歷史

        保留最近的訊息，壓縮較早的訊息
        """
        if not messages:
            return messages

        # 計算當前 Token 數
        total_tokens = sum(
            self.analyzer.count_tokens(m.get("content", ""))
            for m in messages
        )

        if total_tokens <= max_tokens:
            return messages

        # 保留最近的訊息
        recent = messages[-keep_recent:] if len(messages) > keep_recent else messages
        older = messages[:-keep_recent] if len(messages) > keep_recent else []

        # 壓縮較早的訊息
        if older:
            older_content = "\n".join(m.get("content", "") for m in older)
            older_tokens = self.analyzer.count_tokens(older_content)

            remaining_tokens = max_tokens - sum(
                self.analyzer.count_tokens(m.get("content", ""))
                for m in recent
            )

            if remaining_tokens > 100:
                compressed = self.compress_prompt(older_content, remaining_tokens)
                return [{"role": "system", "content": f"[先前對話摘要]:\n{compressed}"}] + recent
            else:
                return recent

        return recent
```

---

## 14.3 智能快取策略

快取是提升效能和降低成本的最有效手段之一。

### 14.3.1 多層快取系統

```
┌─────────────────────────────────────────────────────────────────┐
│                    多層快取架構                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  請求 ──────────────────────────────────────────────────────▶  │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  L1: 記憶體快取（毫秒級）                                  │  │
│  │  - 最近查詢結果                                            │  │
│  │  - 容量：1000 條                                           │  │
│  │  - TTL：5 分鐘                                             │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │ 未命中                              │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  L2: Redis 快取（毫秒到秒級）                              │  │
│  │  - 共享快取                                                │  │
│  │  - 容量：100,000 條                                        │  │
│  │  - TTL：1 小時                                             │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │ 未命中                              │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  L3: 語義快取（秒級）                                      │  │
│  │  - 向量相似度匹配                                          │  │
│  │  - 相似查詢復用                                            │  │
│  │  - 容量：無限（持久化）                                    │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │ 未命中                              │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  L4: LLM 調用                                              │  │
│  │  - 真正的 API 調用                                         │  │
│  │  - 結果回填到各層快取                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 14.3.2 快取系統實作

```python
#!/usr/bin/env python3
"""
智能快取系統

多層快取 + 語義快取
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import hashlib
import json
import asyncio
from collections import OrderedDict


@dataclass
class CacheEntry:
    """快取條目"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class CacheLayer(ABC):
    """快取層抽象基類"""

    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass


class MemoryCache(CacheLayer):
    """
    L1: 記憶體快取

    ‹1› 最快的快取層
    ‹2› 使用 LRU 策略
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {"hits": 0, "misses": 0}

    async def get(self, key: str) -> Optional[CacheEntry]:
        entry = self._cache.get(key)

        if entry is None:
            self._stats["misses"] += 1
            return None

        if entry.is_expired:
            del self._cache[key]
            self._stats["misses"] += 1
            return None

        # LRU：移到最後
        self._cache.move_to_end(key)
        entry.hit_count += 1
        self._stats["hits"] += 1

        return entry

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)

        entry = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at
        )

        # 如果超過容量，移除最舊的
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = entry

    async def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    @property
    def hit_rate(self) -> float:
        total = self._stats["hits"] + self._stats["misses"]
        return self._stats["hits"] / total if total > 0 else 0


class RedisCache(CacheLayer):
    """
    L2: Redis 快取

    ‹3› 分散式快取
    ‹4› 支援高並發
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 3600,
        prefix: str = "research:"
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.prefix = prefix
        self._client = None

    async def _get_client(self):
        """懶加載 Redis 客戶端"""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(self.redis_url)
            except ImportError:
                # 如果沒有 redis，返回模擬客戶端
                self._client = MockRedisClient()
        return self._client

    def _make_key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[CacheEntry]:
        client = await self._get_client()
        full_key = self._make_key(key)

        try:
            data = await client.get(full_key)
            if data is None:
                return None

            entry_dict = json.loads(data)
            return CacheEntry(
                key=key,
                value=entry_dict["value"],
                created_at=datetime.fromisoformat(entry_dict["created_at"]),
                metadata=entry_dict.get("metadata", {})
            )
        except Exception:
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        client = await self._get_client()
        full_key = self._make_key(key)
        ttl = ttl or self.default_ttl

        entry_dict = {
            "value": value,
            "created_at": datetime.now().isoformat(),
            "metadata": {}
        }

        try:
            await client.setex(full_key, ttl, json.dumps(entry_dict))
        except Exception:
            pass

    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        full_key = self._make_key(key)
        try:
            return await client.delete(full_key) > 0
        except Exception:
            return False


class MockRedisClient:
    """模擬 Redis 客戶端（用於測試）"""

    def __init__(self):
        self._data = {}

    async def get(self, key: str) -> Optional[str]:
        item = self._data.get(key)
        if item and item["expires"] > datetime.now():
            return item["value"]
        return None

    async def setex(self, key: str, ttl: int, value: str):
        self._data[key] = {
            "value": value,
            "expires": datetime.now() + timedelta(seconds=ttl)
        }

    async def delete(self, key: str) -> int:
        if key in self._data:
            del self._data[key]
            return 1
        return 0


class SemanticCache(CacheLayer):
    """
    L3: 語義快取

    ‹5› 基於向量相似度的快取
    ‹6› 相似查詢可以復用結果
    """

    def __init__(
        self,
        embedding_model=None,
        similarity_threshold: float = 0.95
    ):
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        self._entries: List[Tuple[List[float], CacheEntry]] = []

    async def get(self, key: str) -> Optional[CacheEntry]:
        if not self.embedding_model or not self._entries:
            return None

        # 計算查詢的 embedding
        try:
            query_embedding = await self._get_embedding(key)
        except Exception:
            return None

        # 找最相似的條目
        best_match = None
        best_similarity = 0

        for embedding, entry in self._entries:
            similarity = self._cosine_similarity(query_embedding, embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = entry

        if best_similarity >= self.similarity_threshold:
            if best_match:
                best_match.hit_count += 1
                best_match.metadata["similarity"] = best_similarity
            return best_match

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        if not self.embedding_model:
            return

        try:
            embedding = await self._get_embedding(key)
            entry = CacheEntry(key=key, value=value)
            self._entries.append((embedding, entry))
        except Exception:
            pass

    async def delete(self, key: str) -> bool:
        # 語義快取不支援精確刪除
        return False

    async def _get_embedding(self, text: str) -> List[float]:
        """獲取文本的 embedding"""
        if hasattr(self.embedding_model, 'encode'):
            return self.embedding_model.encode(text).tolist()
        elif hasattr(self.embedding_model, 'embed'):
            return await self.embedding_model.embed(text)
        else:
            # 簡單的 hash 作為 fallback
            return [float(ord(c)) for c in text[:100]]

    def _cosine_similarity(
        self,
        a: List[float],
        b: List[float]
    ) -> float:
        """計算餘弦相似度"""
        if len(a) != len(b):
            return 0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0

        return dot_product / (norm_a * norm_b)


class MultiLayerCache:
    """
    多層快取管理器

    整合所有快取層
    """

    def __init__(
        self,
        l1_cache: Optional[MemoryCache] = None,
        l2_cache: Optional[RedisCache] = None,
        l3_cache: Optional[SemanticCache] = None
    ):
        self.l1 = l1_cache or MemoryCache()
        self.l2 = l2_cache
        self.l3 = l3_cache

        self._stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "misses": 0
        }

    async def get(self, key: str) -> Optional[Any]:
        """從快取獲取值"""
        # L1: 記憶體
        entry = await self.l1.get(key)
        if entry:
            self._stats["l1_hits"] += 1
            return entry.value

        # L2: Redis
        if self.l2:
            entry = await self.l2.get(key)
            if entry:
                self._stats["l2_hits"] += 1
                # 回填 L1
                await self.l1.set(key, entry.value)
                return entry.value

        # L3: 語義快取
        if self.l3:
            entry = await self.l3.get(key)
            if entry:
                self._stats["l3_hits"] += 1
                # 回填 L1, L2
                await self.l1.set(key, entry.value)
                if self.l2:
                    await self.l2.set(key, entry.value)
                return entry.value

        self._stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """設置快取值"""
        # 寫入所有層
        await self.l1.set(key, value, ttl)

        if self.l2:
            await self.l2.set(key, value, ttl)

        if self.l3:
            await self.l3.set(key, value, ttl)

    def get_stats(self) -> Dict[str, Any]:
        """獲取快取統計"""
        total = sum(self._stats.values())
        return {
            **self._stats,
            "total_requests": total,
            "overall_hit_rate": (total - self._stats["misses"]) / total if total > 0 else 0,
            "l1_hit_rate": self.l1.hit_rate if isinstance(self.l1, MemoryCache) else 0
        }


def generate_cache_key(
    query: str,
    model: str = "",
    params: Optional[Dict] = None
) -> str:
    """生成快取鍵"""
    key_parts = [query, model]
    if params:
        key_parts.append(json.dumps(params, sort_keys=True))

    key_string = "|".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()[:32]
```

---

## 14.4 成本監控與預算控制

### 14.4.1 成本追蹤系統

```python
#!/usr/bin/env python3
"""
成本監控與預算控制

追蹤和控制 LLM 調用成本
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import asyncio


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
    limit: float  # 美元
    warning_threshold: float = 0.8  # 80% 時警告
    hard_limit: bool = True  # 是否強制限制


@dataclass
class CostRecord:
    """成本記錄"""
    timestamp: datetime
    operation: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CostTracker:
    """
    成本追蹤器

    ‹1› 記錄所有成本
    ‹2› 監控預算使用
    """

    # 模型定價（每 1K token）
    PRICING = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "qwen-72b": {"input": 0.001, "output": 0.002},
        "qwen-7b": {"input": 0.0001, "output": 0.0002},
    }

    def __init__(self):
        self.records: List[CostRecord] = []
        self.budgets: Dict[BudgetPeriod, Budget] = {}
        self._callbacks: List[Callable] = []

    def set_budget(self, budget: Budget):
        """設置預算"""
        self.budgets[budget.period] = budget

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """計算成本"""
        pricing = self.PRICING.get(model, {"input": 0.01, "output": 0.03})
        return (
            input_tokens * pricing["input"] / 1000 +
            output_tokens * pricing["output"] / 1000
        )

    def record(
        self,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        metadata: Optional[Dict] = None
    ) -> CostRecord:
        """記錄成本"""
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        record = CostRecord(
            timestamp=datetime.now(),
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            metadata=metadata or {}
        )

        self.records.append(record)

        # 檢查預算
        self._check_budgets()

        return record

    def get_cost_summary(
        self,
        period: Optional[BudgetPeriod] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """獲取成本摘要"""
        records = self.records

        if period:
            since = self._get_period_start(period)

        if since:
            records = [r for r in records if r.timestamp >= since]

        if not records:
            return {"total_cost": 0, "total_calls": 0}

        total_cost = sum(r.cost for r in records)
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)

        # 按模型分組
        by_model = {}
        for record in records:
            if record.model not in by_model:
                by_model[record.model] = {"calls": 0, "cost": 0}
            by_model[record.model]["calls"] += 1
            by_model[record.model]["cost"] += record.cost

        # 按操作分組
        by_operation = {}
        for record in records:
            if record.operation not in by_operation:
                by_operation[record.operation] = {"calls": 0, "cost": 0}
            by_operation[record.operation]["calls"] += 1
            by_operation[record.operation]["cost"] += record.cost

        return {
            "total_cost": total_cost,
            "total_calls": len(records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "avg_cost_per_call": total_cost / len(records),
            "by_model": by_model,
            "by_operation": by_operation,
            "period_start": since.isoformat() if since else None
        }

    def _get_period_start(self, period: BudgetPeriod) -> datetime:
        """獲取週期開始時間"""
        now = datetime.now()

        if period == BudgetPeriod.HOURLY:
            return now.replace(minute=0, second=0, microsecond=0)
        elif period == BudgetPeriod.DAILY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == BudgetPeriod.WEEKLY:
            start = now - timedelta(days=now.weekday())
            return start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # MONTHLY
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def _check_budgets(self):
        """檢查預算"""
        for period, budget in self.budgets.items():
            summary = self.get_cost_summary(period=period)
            current_cost = summary["total_cost"]

            usage_ratio = current_cost / budget.limit

            if usage_ratio >= 1.0 and budget.hard_limit:
                self._trigger_budget_exceeded(period, current_cost, budget.limit)
            elif usage_ratio >= budget.warning_threshold:
                self._trigger_budget_warning(period, current_cost, budget.limit)

    def _trigger_budget_warning(
        self,
        period: BudgetPeriod,
        current: float,
        limit: float
    ):
        """觸發預算警告"""
        for callback in self._callbacks:
            callback("warning", period, current, limit)

    def _trigger_budget_exceeded(
        self,
        period: BudgetPeriod,
        current: float,
        limit: float
    ):
        """觸發預算超限"""
        for callback in self._callbacks:
            callback("exceeded", period, current, limit)

    def on_budget_event(self, callback: Callable):
        """註冊預算事件回調"""
        self._callbacks.append(callback)

    def check_can_proceed(
        self,
        estimated_cost: float,
        period: BudgetPeriod = BudgetPeriod.DAILY
    ) -> Tuple[bool, str]:
        """檢查是否可以繼續"""
        if period not in self.budgets:
            return True, "無預算限制"

        budget = self.budgets[period]
        summary = self.get_cost_summary(period=period)
        current_cost = summary["total_cost"]

        if current_cost + estimated_cost > budget.limit:
            if budget.hard_limit:
                return False, f"將超出預算（當前：${current_cost:.4f}，預算：${budget.limit:.2f}）"
            else:
                return True, f"警告：將超出預算限制"

        return True, "預算充足"


class BudgetGuard:
    """
    預算守衛

    ‹3› 在調用前檢查預算
    ‹4› 必要時降級或拒絕
    """

    def __init__(
        self,
        cost_tracker: CostTracker,
        fallback_model: Optional[str] = None
    ):
        self.tracker = cost_tracker
        self.fallback_model = fallback_model

    async def guard(
        self,
        model: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int
    ) -> Tuple[bool, str, Optional[str]]:
        """
        守衛檢查

        Returns:
            (允許, 訊息, 建議模型)
        """
        estimated_cost = self.tracker.calculate_cost(
            model,
            estimated_input_tokens,
            estimated_output_tokens
        )

        can_proceed, message = self.tracker.check_can_proceed(
            estimated_cost,
            BudgetPeriod.DAILY
        )

        if can_proceed:
            return True, message, model

        # 嘗試降級
        if self.fallback_model:
            fallback_cost = self.tracker.calculate_cost(
                self.fallback_model,
                estimated_input_tokens,
                estimated_output_tokens
            )

            can_fallback, fb_message = self.tracker.check_can_proceed(
                fallback_cost,
                BudgetPeriod.DAILY
            )

            if can_fallback:
                return True, f"降級到 {self.fallback_model}", self.fallback_model

        return False, message, None


# 使用 Tuple 的類型提示
from typing import Tuple
```

---

## 14.5 模型選擇與降級策略

### 14.5.1 智能模型路由

```python
#!/usr/bin/env python3
"""
智能模型路由

根據任務特性選擇最適合的模型
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum


class TaskComplexity(Enum):
    """任務複雜度"""
    SIMPLE = "simple"           # 簡單任務
    MODERATE = "moderate"       # 中等任務
    COMPLEX = "complex"         # 複雜任務
    EXPERT = "expert"           # 專家級任務


@dataclass
class ModelProfile:
    """模型配置檔"""
    name: str
    provider: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    max_context: int
    capabilities: List[str]
    speed_score: float  # 1-10
    quality_score: float  # 1-10

    @property
    def cost_score(self) -> float:
        """成本分數（越低越好）"""
        avg_cost = (self.input_cost_per_1k + self.output_cost_per_1k) / 2
        return 10 - min(avg_cost * 100, 10)


class ModelRouter:
    """
    智能模型路由器

    ‹1› 根據任務選擇模型
    ‹2› 支援降級策略
    """

    # 預設模型配置
    MODELS = {
        "gpt-4o": ModelProfile(
            name="gpt-4o",
            provider="openai",
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
            max_context=128000,
            capabilities=["reasoning", "coding", "analysis", "multimodal"],
            speed_score=8,
            quality_score=9
        ),
        "gpt-4-turbo": ModelProfile(
            name="gpt-4-turbo",
            provider="openai",
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.03,
            max_context=128000,
            capabilities=["reasoning", "coding", "analysis", "multimodal"],
            speed_score=7,
            quality_score=9.5
        ),
        "gpt-3.5-turbo": ModelProfile(
            name="gpt-3.5-turbo",
            provider="openai",
            input_cost_per_1k=0.0005,
            output_cost_per_1k=0.0015,
            max_context=16000,
            capabilities=["basic_reasoning", "coding", "conversation"],
            speed_score=9,
            quality_score=7
        ),
        "claude-3-opus": ModelProfile(
            name="claude-3-opus",
            provider="anthropic",
            input_cost_per_1k=0.015,
            output_cost_per_1k=0.075,
            max_context=200000,
            capabilities=["reasoning", "analysis", "writing", "coding"],
            speed_score=6,
            quality_score=10
        ),
        "claude-3-sonnet": ModelProfile(
            name="claude-3-sonnet",
            provider="anthropic",
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
            max_context=200000,
            capabilities=["reasoning", "analysis", "writing", "coding"],
            speed_score=8,
            quality_score=8.5
        ),
        "claude-3-haiku": ModelProfile(
            name="claude-3-haiku",
            provider="anthropic",
            input_cost_per_1k=0.00025,
            output_cost_per_1k=0.00125,
            max_context=200000,
            capabilities=["basic_reasoning", "conversation", "summarization"],
            speed_score=10,
            quality_score=7
        ),
        "qwen-72b": ModelProfile(
            name="qwen-72b",
            provider="alibaba",
            input_cost_per_1k=0.001,
            output_cost_per_1k=0.002,
            max_context=32000,
            capabilities=["reasoning", "coding", "chinese"],
            speed_score=7,
            quality_score=8
        ),
    }

    # 任務類型對應的能力需求
    TASK_REQUIREMENTS = {
        "summarization": ["summarization", "basic_reasoning"],
        "coding": ["coding"],
        "analysis": ["analysis", "reasoning"],
        "research": ["reasoning", "analysis", "writing"],
        "conversation": ["conversation", "basic_reasoning"],
        "translation": ["writing", "chinese"],
    }

    def __init__(
        self,
        optimization_target: Optional["OptimizationTarget"] = None
    ):
        self.optimization_target = optimization_target
        self._fallback_chain = self._build_fallback_chain()

    def _build_fallback_chain(self) -> Dict[str, List[str]]:
        """建立降級鏈"""
        return {
            "claude-3-opus": ["claude-3-sonnet", "gpt-4-turbo", "gpt-4o"],
            "gpt-4-turbo": ["gpt-4o", "claude-3-sonnet", "gpt-3.5-turbo"],
            "gpt-4o": ["claude-3-sonnet", "gpt-3.5-turbo"],
            "claude-3-sonnet": ["claude-3-haiku", "gpt-3.5-turbo"],
            "gpt-3.5-turbo": ["claude-3-haiku", "qwen-72b"],
            "claude-3-haiku": ["qwen-72b"],
        }

    def select_model(
        self,
        task_type: str,
        complexity: TaskComplexity,
        context_length: int = 0,
        prefer_speed: bool = False,
        prefer_quality: bool = False,
        max_cost_per_1k: Optional[float] = None
    ) -> str:
        """
        選擇最適合的模型

        ‹1› 根據任務需求篩選
        ‹2› 根據優化目標排序
        """
        # 獲取任務需要的能力
        required_capabilities = self.TASK_REQUIREMENTS.get(
            task_type,
            ["basic_reasoning"]
        )

        # 篩選符合要求的模型
        candidates = []
        for name, profile in self.MODELS.items():
            # 檢查能力
            if not any(cap in profile.capabilities for cap in required_capabilities):
                continue

            # 檢查上下文長度
            if context_length > profile.max_context:
                continue

            # 檢查成本限制
            if max_cost_per_1k:
                avg_cost = (profile.input_cost_per_1k + profile.output_cost_per_1k) / 2
                if avg_cost > max_cost_per_1k:
                    continue

            candidates.append(profile)

        if not candidates:
            # 沒有符合的，返回預設
            return "gpt-3.5-turbo"

        # 根據複雜度和偏好排序
        def score_model(profile: ModelProfile) -> float:
            score = 0

            # 複雜度匹配
            if complexity == TaskComplexity.EXPERT:
                score += profile.quality_score * 2
            elif complexity == TaskComplexity.COMPLEX:
                score += profile.quality_score * 1.5
            elif complexity == TaskComplexity.MODERATE:
                score += profile.quality_score + profile.cost_score * 0.5
            else:  # SIMPLE
                score += profile.cost_score * 2

            # 偏好調整
            if prefer_speed:
                score += profile.speed_score
            if prefer_quality:
                score += profile.quality_score

            return score

        candidates.sort(key=score_model, reverse=True)

        return candidates[0].name

    def get_fallback(self, model: str) -> Optional[str]:
        """獲取降級模型"""
        chain = self._fallback_chain.get(model, [])
        return chain[0] if chain else None

    def get_model_info(self, model: str) -> Optional[ModelProfile]:
        """獲取模型資訊"""
        return self.MODELS.get(model)


class AdaptiveModelSelector:
    """
    自適應模型選擇器

    ‹3› 根據歷史表現動態調整
    """

    def __init__(self, router: ModelRouter, tracker: "CostTracker"):
        self.router = router
        self.tracker = tracker
        self._performance_history: Dict[str, List[float]] = {}

    def record_performance(
        self,
        model: str,
        quality_score: float,
        latency: float
    ):
        """記錄模型表現"""
        if model not in self._performance_history:
            self._performance_history[model] = []

        self._performance_history[model].append({
            "quality": quality_score,
            "latency": latency
        })

        # 只保留最近 100 條
        self._performance_history[model] = self._performance_history[model][-100:]

    def select_model(
        self,
        task_type: str,
        complexity: TaskComplexity,
        context_length: int = 0
    ) -> str:
        """智能選擇模型"""
        # 基礎選擇
        base_model = self.router.select_model(
            task_type, complexity, context_length
        )

        # 檢查預算
        can_proceed, _ = self.tracker.check_can_proceed(
            0.1,  # 估計成本
            BudgetPeriod.DAILY
        )

        if not can_proceed:
            # 預算緊張，降級
            fallback = self.router.get_fallback(base_model)
            if fallback:
                return fallback

        # 檢查歷史表現
        if base_model in self._performance_history:
            history = self._performance_history[base_model]
            if len(history) >= 10:
                recent_quality = sum(h["quality"] for h in history[-10:]) / 10
                if recent_quality < 0.6:
                    # 品質不佳，嘗試其他模型
                    fallback = self.router.get_fallback(base_model)
                    if fallback:
                        return fallback

        return base_model
```

---

## 14.6 批次處理與並行化

### 14.6.1 批次處理引擎

```python
#!/usr/bin/env python3
"""
批次處理與並行化

提高處理效率，降低成本
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, TypeVar, Generic
import asyncio
from datetime import datetime


T = TypeVar('T')
R = TypeVar('R')


@dataclass
class BatchItem(Generic[T]):
    """批次項目"""
    id: str
    data: T
    submitted_at: datetime = field(default_factory=datetime.now)


@dataclass
class BatchResult(Generic[R]):
    """批次結果"""
    id: str
    result: R
    success: bool
    error: Optional[str] = None
    processing_time: float = 0


class BatchProcessor(Generic[T, R]):
    """
    批次處理器

    ‹1› 累積請求到批次
    ‹2› 統一處理以提高效率
    """

    def __init__(
        self,
        processor: Callable[[List[T]], List[R]],
        batch_size: int = 10,
        max_wait_seconds: float = 1.0
    ):
        """
        初始化批次處理器

        Args:
            processor: 批次處理函數
            batch_size: 批次大小
            max_wait_seconds: 最大等待時間
        """
        self.processor = processor
        self.batch_size = batch_size
        self.max_wait_seconds = max_wait_seconds

        self._queue: List[BatchItem[T]] = []
        self._results: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self._processing = False

    async def submit(self, item_id: str, data: T) -> R:
        """
        提交項目並等待結果

        ‹1› 添加到隊列
        ‹2› 等待批次處理完成
        """
        future = asyncio.Future()

        async with self._lock:
            self._queue.append(BatchItem(id=item_id, data=data))
            self._results[item_id] = future

            # 如果達到批次大小，立即處理
            if len(self._queue) >= self.batch_size:
                asyncio.create_task(self._process_batch())

        # 啟動超時處理
        if not self._processing:
            asyncio.create_task(self._wait_and_process())

        return await future

    async def _wait_and_process(self):
        """等待並處理"""
        await asyncio.sleep(self.max_wait_seconds)
        await self._process_batch()

    async def _process_batch(self):
        """處理批次"""
        async with self._lock:
            if not self._queue or self._processing:
                return

            self._processing = True
            batch = self._queue[:self.batch_size]
            self._queue = self._queue[self.batch_size:]

        try:
            start = datetime.now()

            # 執行批次處理
            data_list = [item.data for item in batch]

            if asyncio.iscoroutinefunction(self.processor):
                results = await self.processor(data_list)
            else:
                results = self.processor(data_list)

            elapsed = (datetime.now() - start).total_seconds()

            # 分發結果
            for i, item in enumerate(batch):
                future = self._results.get(item.id)
                if future and not future.done():
                    if i < len(results):
                        future.set_result(results[i])
                    else:
                        future.set_exception(
                            Exception("結果數量不匹配")
                        )

        except Exception as e:
            # 錯誤處理
            for item in batch:
                future = self._results.get(item.id)
                if future and not future.done():
                    future.set_exception(e)

        finally:
            self._processing = False

            # 如果還有待處理項目，繼續
            if self._queue:
                asyncio.create_task(self._process_batch())


class ParallelExecutor:
    """
    並行執行器

    ‹3› 控制並發度
    ‹4› 處理錯誤和重試
    """

    def __init__(
        self,
        max_concurrency: int = 10,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ):
        self.max_concurrency = max_concurrency
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_all(
        self,
        tasks: List[Callable[[], Any]]
    ) -> List[Any]:
        """
        並行執行所有任務

        ‹3› 限制並發度
        """
        async def run_with_semaphore(task):
            async with self._semaphore:
                return await self._execute_with_retry(task)

        return await asyncio.gather(
            *[run_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )

    async def _execute_with_retry(
        self,
        task: Callable[[], Any]
    ) -> Any:
        """
        帶重試的執行

        ‹4› 指數退避重試
        """
        last_error = None

        for attempt in range(self.retry_count):
            try:
                if asyncio.iscoroutinefunction(task):
                    return await task()
                else:
                    return task()

            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

        raise last_error


class RateLimiter:
    """
    速率限制器

    ‹5› 防止 API 過載
    """

    def __init__(
        self,
        requests_per_second: float = 10,
        requests_per_minute: float = 100
    ):
        self.rps = requests_per_second
        self.rpm = requests_per_minute

        self._second_tokens = requests_per_second
        self._minute_tokens = requests_per_minute
        self._last_refill = datetime.now()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """獲取令牌"""
        async with self._lock:
            self._refill()

            while self._second_tokens < 1 or self._minute_tokens < 1:
                await asyncio.sleep(0.1)
                self._refill()

            self._second_tokens -= 1
            self._minute_tokens -= 1

    def _refill(self):
        """補充令牌"""
        now = datetime.now()
        elapsed = (now - self._last_refill).total_seconds()

        # 補充秒級令牌
        self._second_tokens = min(
            self.rps,
            self._second_tokens + elapsed * self.rps
        )

        # 補充分鐘級令牌
        self._minute_tokens = min(
            self.rpm,
            self._minute_tokens + elapsed * self.rpm / 60
        )

        self._last_refill = now
```

---

## 14.7 章節總結

本章深入探討了深度研究代理人的效能優化與成本控制：

### 核心概念

1. **Token 效率優化**
   - Token 消耗分析
   - 提示壓縮
   - 上下文優化

2. **智能快取策略**
   - 多層快取架構
   - 語義快取
   - 快取命中率優化

3. **成本監控與預算控制**
   - 成本追蹤
   - 預算守衛
   - 超限處理

4. **模型選擇與降級**
   - 智能路由
   - 降級鏈
   - 自適應選擇

5. **批次處理與並行化**
   - 批次累積
   - 並發控制
   - 速率限制

### 優化效果預期

| 優化策略 | 成本節省 | 速度提升 |
|----------|----------|----------|
| Token 優化 | 20-40% | - |
| 智能快取 | 30-60% | 2-10x |
| 模型降級 | 50-80% | 可能降低 |
| 批次處理 | 10-30% | 1.5-3x |

### 檢查清單

- [ ] 實施 Token 使用追蹤
- [ ] 建立多層快取系統
- [ ] 設置預算警告和限制
- [ ] 配置模型降級鏈
- [ ] 實現批次處理邏輯

---

## 14.8 全書總結

恭喜你完成了《深度研究代理人實戰》全書的學習！

### 回顧旅程

我們從**交互式縮放**的理論基石出發，探索了如何透過增加模型與環境的交互深度來補足參數規模的不足。通過 MiroThinker 開源專案，我們深入理解了深度研究代理人的架構設計。

**第一部分**建立了理論基礎，讓你理解為什麼 600 次工具調用比單純增加參數更能提升研究品質。

**第二部分**解構了核心架構，從調度器、工具管理、記憶系統到搜尋引擎，每個組件都有其獨特的設計考量。

**第三部分**進入工程實踐，你學會了如何從零建構一個具備自我查證能力的研究代理人，並將其部署到生產環境。

**第四部分**關注品質保證與優化，從基準測試到幻覺處理，再到本章的效能優化，確保你的代理人既可靠又經濟。

### 下一步

建議你：

1. **實踐**：動手建構自己的深度研究代理人
2. **優化**：根據實際使用情況調整配置
3. **貢獻**：參與 MiroThinker 開源社區
4. **分享**：將你的經驗分享給其他開發者

### 最後的話

> 「智能的奇點不在於無限制地擴大參數，而在於強化代理人向外求證、自我修正的發現式智能。」

希望這本書能幫助你在深度研究代理人的道路上走得更遠。AI 的未來不只是更大的模型，更是更智能的交互。

祝你的 AI 之旅順利！
