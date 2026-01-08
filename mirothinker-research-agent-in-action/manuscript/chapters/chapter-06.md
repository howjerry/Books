# 第 6 章：長短時記憶管理

> **本章目標**：掌握深度研究代理人的記憶架構設計，學會在 256K 上下文視窗中有效管理長短期記憶，實現動態壓縮與智能檢索。

---

## 6.1 問題：當記憶成為瓶頸

想像你正在進行一項深度研究——分析過去十年的 AI 發展趨勢。你的代理人已經：

- 搜尋了 50 個相關網頁
- 閱讀了 20 篇學術論文摘要
- 執行了 30 次工具調用
- 累積了超過 100,000 tokens 的對話歷史

現在，當你問代理人：「根據剛才的研究，2018 年的關鍵突破是什麼？」

代理人卻回答：「抱歉，我沒有看到關於 2018 年的資訊。」

這不是幻覺，而是**記憶丟失**——早期的資訊被後來的內容擠出了有效的上下文視窗。

### 記憶管理的三大挑戰

```
┌─────────────────────────────────────────────────────────────┐
│                    記憶管理挑戰                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 容量限制                                                │
│     ┌───────────────────────────────────────┐              │
│     │ 256K tokens ≈ 200 頁文字              │              │
│     │ 深度研究可能需要 500+ 頁資訊           │              │
│     └───────────────────────────────────────┘              │
│                                                             │
│  2. 檢索效率                                                │
│     ┌───────────────────────────────────────┐              │
│     │ 線性掃描 256K tokens = 高延遲           │              │
│     │ 注意力計算 O(n²) = 成本激增             │              │
│     └───────────────────────────────────────┘              │
│                                                             │
│  3. 資訊衰減                                                │
│     ┌───────────────────────────────────────┐              │
│     │ 早期資訊被稀釋                         │              │
│     │ 關鍵細節被遺忘                         │              │
│     └───────────────────────────────────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### MiroThinker 的解決方案

MiroThinker 採用了一套**分層記憶架構**，模仿人類的記憶系統：

| 記憶層級 | 人類類比 | 特點 | 容量 |
|----------|----------|------|------|
| **工作記憶** | 短期記憶 | 當前對話上下文 | ~8K tokens |
| **情節記憶** | 最近經歷 | 近期研究步驟 | ~32K tokens |
| **語義記憶** | 知識庫 | 壓縮後的核心知識 | 無限（外部存儲） |

本章將帶你實現這套完整的記憶管理系統。

---

## 6.2 記憶架構設計

### 6.2.1 三層記憶模型

MiroThinker 的記憶系統分為三個層級，每層有不同的生命週期和存取模式：

```
┌─────────────────────────────────────────────────────────────┐
│                    三層記憶架構                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              工作記憶（Working Memory）              │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │   │
│  │  │當前問題 │ │最近思考 │ │待處理   │ │臨時變數 │   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │   │
│  │  容量：~8K tokens | 生命週期：單次交互               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓ 溢出                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              情節記憶（Episodic Memory）             │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │ 步驟 1 → 步驟 2 → 步驟 3 → ... → 步驟 N    │   │   │
│  │  │ (搜尋)   (閱讀)   (分析)        (整合)     │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │  容量：~32K tokens | 生命週期：單次任務              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓ 壓縮                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              語義記憶（Semantic Memory）             │   │
│  │  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐       │   │
│  │  │概念 A │──│概念 B │──│概念 C │──│概念 D │       │   │
│  │  └───────┘  └───────┘  └───────┘  └───────┘       │   │
│  │            ＼        ╱                              │   │
│  │              知識圖譜                               │   │
│  │  容量：無限 | 生命週期：永久                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2.2 記憶項目資料結構

讓我們定義記憶項目的基本結構：

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json


class MemoryType(Enum):
    """記憶類型"""
    WORKING = "working"      # 工作記憶
    EPISODIC = "episodic"    # 情節記憶
    SEMANTIC = "semantic"    # 語義記憶


class MemoryPriority(Enum):
    """記憶優先級"""
    CRITICAL = 4    # 關鍵資訊，不可刪除
    HIGH = 3        # 高優先級
    MEDIUM = 2      # 中等優先級
    LOW = 1         # 低優先級


@dataclass
class MemoryItem:
    """
    記憶項目

    ‹1› 每個記憶項目都有唯一識別碼
    ‹2› 包含重要性評分和存取計數
    ‹3› 支援向量嵌入以便語義檢索
    """
    content: str                                    # ‹1› 記憶內容
    memory_type: MemoryType                         # 記憶類型
    created_at: datetime = field(                   # 創建時間
        default_factory=datetime.now
    )
    last_accessed: datetime = field(                # 最後存取時間
        default_factory=datetime.now
    )
    access_count: int = 0                           # ‹2› 存取次數
    importance: float = 0.5                         # 重要性評分 (0-1)
    priority: MemoryPriority = MemoryPriority.MEDIUM
    embedding: Optional[List[float]] = None         # ‹3› 向量嵌入
    metadata: Dict[str, Any] = field(default_factory=dict)

    _id: str = field(default="", init=False)

    def __post_init__(self):
        # 生成唯一 ID
        content_hash = hashlib.md5(
            self.content.encode()
        ).hexdigest()[:12]
        timestamp = self.created_at.strftime("%Y%m%d%H%M%S")
        self._id = f"mem_{timestamp}_{content_hash}"

    @property
    def id(self) -> str:
        return self._id

    @property
    def token_count(self) -> int:
        """估算 token 數量"""
        return len(self.content) // 3

    @property
    def recency_score(self) -> float:
        """計算新鮮度分數（0-1）"""
        age = (datetime.now() - self.last_accessed).total_seconds()
        # 使用指數衰減：1 小時衰減到 0.5
        decay_rate = 0.693 / 3600  # ln(2) / 1 hour
        return min(1.0, max(0.0, 2.718 ** (-decay_rate * age)))

    @property
    def relevance_score(self) -> float:
        """計算綜合相關性分數"""
        # 結合重要性、存取頻率和新鮮度
        frequency_score = min(1.0, self.access_count / 10)
        return (
            self.importance * 0.4 +
            frequency_score * 0.3 +
            self.recency_score * 0.3
        )

    def access(self) -> None:
        """記錄一次存取"""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "importance": self.importance,
            "priority": self.priority.value,
            "token_count": self.token_count,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata
        }
```

這個資料結構包含了記憶管理所需的所有資訊：

- **內容與類型**：記憶的實際內容和所屬層級
- **時間追蹤**：創建時間和最後存取時間，用於計算新鮮度
- **存取統計**：存取次數，用於判斷重要性
- **向量嵌入**：支援語義檢索

---

## 6.3 工作記憶管理

工作記憶是代理人的「意識」——當前正在處理的資訊。它需要快速存取、嚴格的容量控制。

### 6.3.1 工作記憶實現

```python
from collections import OrderedDict
from typing import Generator


class WorkingMemory:
    """
    工作記憶管理器

    ‹1› 使用 LRU（最近最少使用）策略管理容量
    ‹2› 支援優先級保護，關鍵資訊不被驅逐
    ‹3› 提供快速的 key-value 存取
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        protected_ratio: float = 0.2  # 保護區佔比
    ):
        self.max_tokens = max_tokens
        self.protected_tokens = int(max_tokens * protected_ratio)
        self._items: OrderedDict[str, MemoryItem] = OrderedDict()
        self._current_tokens = 0

    @property
    def available_tokens(self) -> int:
        """可用 token 數"""
        return self.max_tokens - self._current_tokens

    @property
    def utilization(self) -> float:
        """使用率"""
        return self._current_tokens / self.max_tokens

    def add(
        self,
        content: str,
        importance: float = 0.5,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        **metadata
    ) -> MemoryItem:
        """
        添加記憶項目

        ‹1› 如果超出容量，先驅逐低優先級項目
        ‹2› 關鍵優先級項目進入保護區
        """
        item = MemoryItem(
            content=content,
            memory_type=MemoryType.WORKING,
            importance=importance,
            priority=priority,
            metadata=metadata
        )

        # 檢查是否需要驅逐
        while (
            self._current_tokens + item.token_count > self.max_tokens
            and self._items
        ):
            evicted = self._evict_one()
            if evicted is None:
                # 無法驅逐更多項目
                break

        # 添加新項目
        self._items[item.id] = item
        self._items.move_to_end(item.id)  # LRU: 移到末尾
        self._current_tokens += item.token_count

        return item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """獲取記憶項目（並更新存取記錄）"""
        if item_id not in self._items:
            return None

        item = self._items[item_id]
        item.access()
        self._items.move_to_end(item_id)  # LRU: 移到末尾
        return item

    def search(
        self,
        query: str,
        limit: int = 5
    ) -> List[MemoryItem]:
        """
        搜尋相關記憶

        ‹1› 簡易關鍵字匹配
        ‹2› 按相關性排序
        """
        query_lower = query.lower()
        results = []

        for item in self._items.values():
            # 簡易相關性計算
            content_lower = item.content.lower()
            if query_lower in content_lower:
                score = item.relevance_score
                # 關鍵字匹配加分
                score += 0.3
                results.append((score, item))

        # 按分數排序
        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:limit]]

    def _evict_one(self) -> Optional[MemoryItem]:
        """
        驅逐一個項目

        ‹1› 優先驅逐低優先級項目
        ‹2› 同優先級驅逐最舊的（LRU 頭部）
        ‹3› 保護區內的項目不驅逐
        """
        # 按優先級分組
        candidates = []
        protected_tokens = 0

        for item_id, item in self._items.items():
            if item.priority == MemoryPriority.CRITICAL:
                protected_tokens += item.token_count
                continue
            candidates.append((item.priority.value, item.relevance_score, item_id))

        if not candidates:
            return None

        # 按優先級和相關性排序（最低的在前）
        candidates.sort(key=lambda x: (x[0], x[1]))
        evict_id = candidates[0][2]

        item = self._items.pop(evict_id)
        self._current_tokens -= item.token_count
        return item

    def clear(self, keep_critical: bool = True) -> int:
        """清空工作記憶"""
        if keep_critical:
            to_remove = [
                item_id for item_id, item in self._items.items()
                if item.priority != MemoryPriority.CRITICAL
            ]
            for item_id in to_remove:
                item = self._items.pop(item_id)
                self._current_tokens -= item.token_count
            return len(to_remove)
        else:
            count = len(self._items)
            self._items.clear()
            self._current_tokens = 0
            return count

    def to_prompt(self) -> str:
        """將工作記憶轉換為 prompt 格式"""
        if not self._items:
            return ""

        lines = ["[工作記憶]"]
        for item in self._items.values():
            priority_marker = {
                MemoryPriority.CRITICAL: "🔴",
                MemoryPriority.HIGH: "🟠",
                MemoryPriority.MEDIUM: "🟡",
                MemoryPriority.LOW: "⚪"
            }.get(item.priority, "⚪")
            lines.append(f"{priority_marker} {item.content}")

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        priority_counts = {}
        for item in self._items.values():
            key = item.priority.name
            priority_counts[key] = priority_counts.get(key, 0) + 1

        return {
            "item_count": len(self._items),
            "total_tokens": self._current_tokens,
            "max_tokens": self.max_tokens,
            "utilization": self.utilization,
            "available_tokens": self.available_tokens,
            "priority_distribution": priority_counts
        }
```

### 6.3.2 工作記憶使用範例

```python
# 創建工作記憶
working_memory = WorkingMemory(max_tokens=8000)

# 添加當前任務
working_memory.add(
    content="用戶問題：分析 2024 年 AI 晶片市場趨勢",
    importance=1.0,
    priority=MemoryPriority.CRITICAL,
    source="user_query"
)

# 添加中間思考
working_memory.add(
    content="需要搜尋市場數據、主要廠商資訊、技術趨勢",
    importance=0.8,
    priority=MemoryPriority.HIGH,
    source="agent_thought"
)

# 添加工具結果摘要
working_memory.add(
    content="搜尋結果：NVIDIA 市場份額 80%，AMD 10%，Intel 5%",
    importance=0.9,
    priority=MemoryPriority.HIGH,
    source="tool_result"
)

# 檢視統計
print(working_memory.get_statistics())
# 輸出：
# {
#     'item_count': 3,
#     'total_tokens': 156,
#     'max_tokens': 8000,
#     'utilization': 0.0195,
#     'priority_distribution': {'CRITICAL': 1, 'HIGH': 2}
# }

# 生成 prompt
print(working_memory.to_prompt())
# 輸出：
# [工作記憶]
# 🔴 用戶問題：分析 2024 年 AI 晶片市場趨勢
# 🟠 需要搜尋市場數據、主要廠商資訊、技術趨勢
# 🟠 搜尋結果：NVIDIA 市場份額 80%，AMD 10%，Intel 5%
```

---

## 6.4 情節記憶管理

情節記憶存儲代理人的「經歷」——研究過程中的每個步驟。這是深度研究代理人的核心記憶層。

### 6.4.1 情節記憶實現

```python
from typing import Callable, Iterator
import asyncio


@dataclass
class Episode:
    """
    情節（研究步驟）

    ‹1› 每個情節是一個完整的 ReAct 循環
    ‹2› 包含思考、行動、觀察
    """
    step_number: int
    thought: str
    action: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    summary: Optional[str] = None  # 壓縮後的摘要
    created_at: datetime = field(default_factory=datetime.now)
    importance: float = 0.5

    @property
    def token_count(self) -> int:
        """估算 token 數量"""
        total = len(self.thought) // 3
        if self.action:
            total += len(json.dumps(self.action)) // 3
        if self.observation:
            total += len(self.observation) // 3
        return total

    @property
    def compressed_token_count(self) -> int:
        """壓縮後的 token 數量"""
        if self.summary:
            return len(self.summary) // 3
        return self.token_count

    def compress(self, summary: str) -> None:
        """壓縮情節"""
        self.summary = summary

    def to_prompt(self, use_summary: bool = False) -> str:
        """轉換為 prompt 格式"""
        if use_summary and self.summary:
            return f"[步驟 {self.step_number}] {self.summary}"

        lines = [f"[步驟 {self.step_number}]"]
        lines.append(f"思考：{self.thought}")

        if self.action:
            tool_name = self.action.get("tool_name", "unknown")
            lines.append(f"行動：調用 {tool_name}")

        if self.observation:
            # 截斷過長的觀察
            obs = self.observation
            if len(obs) > 500:
                obs = obs[:500] + "..."
            lines.append(f"觀察：{obs}")

        return "\n".join(lines)


class EpisodicMemory:
    """
    情節記憶管理器

    ‹1› 順序存儲研究步驟
    ‹2› 支援滑動視窗和選擇性壓縮
    ‹3› 提供靈活的檢索機制
    """

    def __init__(
        self,
        max_tokens: int = 32000,
        compression_threshold: float = 0.8,  # 達到 80% 容量時開始壓縮
        window_size: int = 10  # 滑動視窗大小
    ):
        self.max_tokens = max_tokens
        self.compression_threshold = compression_threshold
        self.window_size = window_size
        self._episodes: List[Episode] = []
        self._current_tokens = 0
        self._compressor: Optional[Callable] = None

    def set_compressor(self, compressor: Callable[[str], str]) -> None:
        """設置壓縮器（通常是 LLM 調用）"""
        self._compressor = compressor

    @property
    def episode_count(self) -> int:
        return len(self._episodes)

    @property
    def utilization(self) -> float:
        return self._current_tokens / self.max_tokens

    def add_episode(
        self,
        thought: str,
        action: Optional[Dict[str, Any]] = None,
        observation: Optional[str] = None,
        importance: float = 0.5
    ) -> Episode:
        """
        添加新情節

        ‹1› 自動編號
        ‹2› 檢查是否需要壓縮
        """
        episode = Episode(
            step_number=len(self._episodes) + 1,
            thought=thought,
            action=action,
            observation=observation,
            importance=importance
        )

        self._episodes.append(episode)
        self._current_tokens += episode.token_count

        # 檢查是否需要壓縮
        if self.utilization > self.compression_threshold:
            self._trigger_compression()

        return episode

    def _trigger_compression(self) -> int:
        """
        觸發壓縮

        ‹1› 壓縮最舊的、低重要性的情節
        ‹2› 保留最近的 window_size 個情節不壓縮
        """
        if not self._compressor:
            return 0

        compressed_count = 0
        target_tokens = int(self.max_tokens * 0.6)  # 壓縮到 60%

        # 找出可壓縮的情節（不在滑動視窗內的）
        compressible = self._episodes[:-self.window_size] if len(self._episodes) > self.window_size else []

        for episode in compressible:
            if episode.summary:  # 已壓縮
                continue

            if self._current_tokens <= target_tokens:
                break

            # 生成摘要
            original_content = episode.to_prompt(use_summary=False)
            summary = self._compressor(original_content)

            # 更新 token 計數
            old_tokens = episode.token_count
            episode.compress(summary)
            new_tokens = episode.compressed_token_count

            self._current_tokens -= (old_tokens - new_tokens)
            compressed_count += 1

        return compressed_count

    def get_recent(self, n: int = 5) -> List[Episode]:
        """獲取最近 N 個情節"""
        return self._episodes[-n:]

    def get_by_importance(
        self,
        min_importance: float = 0.7,
        limit: int = 10
    ) -> List[Episode]:
        """按重要性獲取情節"""
        important = [
            ep for ep in self._episodes
            if ep.importance >= min_importance
        ]
        return sorted(
            important,
            key=lambda x: x.importance,
            reverse=True
        )[:limit]

    def search(
        self,
        query: str,
        limit: int = 5
    ) -> List[Episode]:
        """
        搜尋相關情節

        ‹1› 簡易關鍵字匹配
        ‹2› 可擴展為向量檢索
        """
        query_lower = query.lower()
        results = []

        for episode in self._episodes:
            content = episode.to_prompt().lower()
            if query_lower in content:
                # 計算匹配度
                match_count = content.count(query_lower)
                score = match_count * 0.1 + episode.importance
                results.append((score, episode))

        results.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in results[:limit]]

    def to_prompt(
        self,
        use_summary_for_old: bool = True,
        include_all: bool = False
    ) -> str:
        """
        生成 prompt

        ‹1› 舊情節使用摘要
        ‹2› 最近情節保留完整內容
        """
        if not self._episodes:
            return ""

        lines = ["[研究歷程]"]

        # 確定哪些使用摘要
        summary_cutoff = len(self._episodes) - self.window_size

        for i, episode in enumerate(self._episodes):
            use_summary = use_summary_for_old and i < summary_cutoff
            lines.append(episode.to_prompt(use_summary=use_summary))
            lines.append("")  # 空行分隔

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        compressed = sum(1 for ep in self._episodes if ep.summary)

        return {
            "episode_count": len(self._episodes),
            "compressed_count": compressed,
            "compression_rate": compressed / len(self._episodes) if self._episodes else 0,
            "total_tokens": self._current_tokens,
            "max_tokens": self.max_tokens,
            "utilization": self.utilization
        }
```

### 6.4.2 動態壓縮策略

壓縮是情節記憶的關鍵功能。我們需要在保留關鍵資訊的同時減少 token 使用：

```python
from openai import AsyncOpenAI


class EpisodeCompressor:
    """
    情節壓縮器

    ‹1› 使用 LLM 生成摘要
    ‹2› 保留關鍵資訊：發現、決策、結果
    ‹3› 可配置壓縮比例
    """

    COMPRESSION_PROMPT = """請將以下研究步驟壓縮為簡潔摘要。

要求：
1. 保留關鍵發現和結論
2. 保留重要的數據和事實
3. 省略過程細節
4. 控制在 50 字以內

原始內容：
{content}

摘要："""

    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        model: str = "gpt-4o-mini"
    ):
        self.client = client or AsyncOpenAI()
        self.model = model

    async def compress(self, content: str) -> str:
        """壓縮單個情節"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": self.COMPRESSION_PROMPT.format(content=content)
            }],
            max_tokens=100,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    async def batch_compress(
        self,
        contents: List[str],
        concurrency: int = 5
    ) -> List[str]:
        """批次壓縮多個情節"""
        semaphore = asyncio.Semaphore(concurrency)

        async def compress_one(content: str) -> str:
            async with semaphore:
                return await self.compress(content)

        tasks = [compress_one(c) for c in contents]
        return await asyncio.gather(*tasks)


# 使用範例
async def demo_compression():
    compressor = EpisodeCompressor()

    original = """
    [步驟 5]
    思考：根據搜尋結果，我需要深入了解 NVIDIA 的 GPU 架構優勢。
    主要關注 CUDA 生態系統、Tensor Core 技術、以及與競爭對手的對比。

    行動：調用 web_browser

    觀察：NVIDIA 的 GPU 架構優勢主要體現在三個方面：
    1. CUDA 生態系統：超過 400 萬開發者，10+ 年積累
    2. Tensor Core：專為 AI 優化的計算單元，FP8 精度支援
    3. 軟體棧：cuDNN、TensorRT、Triton 推理伺服器
    與 AMD 相比，NVIDIA 的軟體生態更成熟，但 AMD 在性價比上有優勢。
    """

    summary = await compressor.compress(original)
    print(f"原始長度: {len(original)} 字符")
    print(f"摘要長度: {len(summary)} 字符")
    print(f"壓縮比: {len(summary)/len(original)*100:.1f}%")
    print(f"\n摘要: {summary}")

# 輸出：
# 原始長度: 456 字符
# 摘要長度: 68 字符
# 壓縮比: 14.9%
#
# 摘要: NVIDIA GPU 優勢：CUDA 生態（400萬開發者）、Tensor Core、
#       完整軟體棧。軟體生態領先 AMD，AMD 勝在性價比。
```

---

## 6.5 語義記憶管理

語義記憶是代理人的「知識庫」——壓縮、結構化後的長期知識。它使用向量資料庫實現高效檢索。

### 6.5.1 語義記憶實現

```python
import numpy as np
from typing import Tuple


@dataclass
class KnowledgeChunk:
    """
    知識片段

    ‹1› 從情節記憶壓縮而來
    ‹2› 包含向量嵌入供語義檢索
    ‹3› 記錄來源以便溯源
    """
    content: str
    embedding: List[float]
    source_episodes: List[int]  # 來源情節編號
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    _id: str = field(default="", init=False)

    def __post_init__(self):
        content_hash = hashlib.md5(self.content.encode()).hexdigest()[:12]
        self._id = f"know_{content_hash}"

    @property
    def id(self) -> str:
        return self._id


class SemanticMemory:
    """
    語義記憶管理器

    ‹1› 使用向量相似度進行語義檢索
    ‹2› 支援知識整合（去重、合併）
    ‹3› 可持久化到向量資料庫
    """

    def __init__(
        self,
        embedding_dim: int = 1536,  # OpenAI embedding 維度
        similarity_threshold: float = 0.85  # 去重閾值
    ):
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold
        self._chunks: Dict[str, KnowledgeChunk] = {}
        self._embeddings: Optional[np.ndarray] = None
        self._chunk_ids: List[str] = []
        self._embedder: Optional[Callable] = None

    def set_embedder(
        self,
        embedder: Callable[[str], List[float]]
    ) -> None:
        """設置嵌入函數"""
        self._embedder = embedder

    def add_knowledge(
        self,
        content: str,
        embedding: Optional[List[float]] = None,
        source_episodes: Optional[List[int]] = None,
        **metadata
    ) -> Optional[KnowledgeChunk]:
        """
        添加知識片段

        ‹1› 自動生成嵌入（如果未提供）
        ‹2› 檢查重複（基於語義相似度）
        ‹3› 如果相似，合併而非添加
        """
        # 生成嵌入
        if embedding is None:
            if self._embedder is None:
                raise ValueError("未設置嵌入函數")
            embedding = self._embedder(content)

        # 檢查重複
        if self._chunks:
            similar_id, similarity = self._find_similar(embedding)
            if similarity > self.similarity_threshold:
                # 合併到現有知識
                self._merge_knowledge(similar_id, content, source_episodes or [])
                return self._chunks[similar_id]

        # 添加新知識
        chunk = KnowledgeChunk(
            content=content,
            embedding=embedding,
            source_episodes=source_episodes or [],
            metadata=metadata
        )

        self._chunks[chunk.id] = chunk
        self._update_index(chunk)

        return chunk

    def _update_index(self, chunk: KnowledgeChunk) -> None:
        """更新向量索引"""
        new_embedding = np.array(chunk.embedding).reshape(1, -1)

        if self._embeddings is None:
            self._embeddings = new_embedding
        else:
            self._embeddings = np.vstack([self._embeddings, new_embedding])

        self._chunk_ids.append(chunk.id)

    def _find_similar(
        self,
        embedding: List[float]
    ) -> Tuple[Optional[str], float]:
        """找到最相似的知識片段"""
        if self._embeddings is None or len(self._chunk_ids) == 0:
            return None, 0.0

        query = np.array(embedding)

        # 計算餘弦相似度
        norms = np.linalg.norm(self._embeddings, axis=1)
        query_norm = np.linalg.norm(query)

        if query_norm == 0:
            return None, 0.0

        similarities = np.dot(self._embeddings, query) / (norms * query_norm)

        max_idx = np.argmax(similarities)
        max_similarity = similarities[max_idx]

        return self._chunk_ids[max_idx], float(max_similarity)

    def _merge_knowledge(
        self,
        chunk_id: str,
        new_content: str,
        source_episodes: List[int]
    ) -> None:
        """合併知識到現有片段"""
        chunk = self._chunks[chunk_id]

        # 添加來源
        chunk.source_episodes.extend(source_episodes)
        chunk.source_episodes = list(set(chunk.source_episodes))

        # 可選：更新內容（這裡簡單地附加）
        # 實際應用中可能需要用 LLM 智能合併
        if new_content not in chunk.content:
            chunk.metadata["merged_contents"] = chunk.metadata.get(
                "merged_contents", []
            )
            chunk.metadata["merged_contents"].append(new_content)

    def search(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.5
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """
        語義搜尋

        ‹1› 將查詢轉換為嵌入向量
        ‹2› 計算與所有知識的相似度
        ‹3› 返回最相關的結果
        """
        if self._embedder is None:
            raise ValueError("未設置嵌入函數")

        if not self._chunks:
            return []

        query_embedding = self._embedder(query)
        query_vec = np.array(query_embedding)

        # 計算相似度
        norms = np.linalg.norm(self._embeddings, axis=1)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        similarities = np.dot(self._embeddings, query_vec) / (norms * query_norm)

        # 過濾和排序
        results = []
        for i, sim in enumerate(similarities):
            if sim >= min_similarity:
                chunk_id = self._chunk_ids[i]
                chunk = self._chunks[chunk_id]
                results.append((chunk, float(sim)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_all_knowledge(self) -> List[KnowledgeChunk]:
        """獲取所有知識"""
        return list(self._chunks.values())

    def to_prompt(
        self,
        query: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """
        生成 prompt

        ‹1› 如果有查詢，返回相關知識
        ‹2› 否則返回所有知識摘要
        """
        if not self._chunks:
            return ""

        lines = ["[知識庫]"]

        if query:
            results = self.search(query, limit=limit)
            for chunk, similarity in results:
                lines.append(f"[相關度: {similarity:.2f}] {chunk.content}")
        else:
            for chunk in list(self._chunks.values())[:limit]:
                lines.append(f"• {chunk.content}")

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        return {
            "chunk_count": len(self._chunks),
            "total_sources": sum(
                len(c.source_episodes) for c in self._chunks.values()
            ),
            "embedding_dim": self.embedding_dim
        }
```

### 6.5.2 嵌入生成器

```python
class EmbeddingGenerator:
    """
    嵌入生成器

    ‹1› 使用 OpenAI embedding API
    ‹2› 支援批次處理
    ‹3› 內建快取機制
    """

    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        model: str = "text-embedding-3-small"
    ):
        self.client = client or AsyncOpenAI()
        self.model = model
        self._cache: Dict[str, List[float]] = {}

    async def embed(self, text: str) -> List[float]:
        """生成單個文本的嵌入"""
        # 檢查快取
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )

        embedding = response.data[0].embedding

        # 存入快取
        self._cache[cache_key] = embedding

        return embedding

    async def batch_embed(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """批次生成嵌入"""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # 檢查快取
            to_embed = []
            cached_indices = []
            for j, text in enumerate(batch):
                cache_key = hashlib.md5(text.encode()).hexdigest()
                if cache_key in self._cache:
                    cached_indices.append((j, self._cache[cache_key]))
                else:
                    to_embed.append((j, text))

            # 批次嵌入
            if to_embed:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=[t for _, t in to_embed]
                )

                for k, (j, text) in enumerate(to_embed):
                    embedding = response.data[k].embedding
                    cache_key = hashlib.md5(text.encode()).hexdigest()
                    self._cache[cache_key] = embedding
                    cached_indices.append((j, embedding))

            # 按原始順序排列
            cached_indices.sort(key=lambda x: x[0])
            all_embeddings.extend([emb for _, emb in cached_indices])

        return all_embeddings

    def embed_sync(self, text: str) -> List[float]:
        """同步版本（用於回調）"""
        return asyncio.get_event_loop().run_until_complete(
            self.embed(text)
        )
```

---

## 6.6 整合：統一記憶管理器

現在讓我們將三層記憶整合成一個統一的管理器：

```python
class UnifiedMemoryManager:
    """
    統一記憶管理器

    ‹1› 整合工作、情節、語義三層記憶
    ‹2› 自動處理記憶層級間的轉換
    ‹3› 提供統一的查詢介面
    """

    def __init__(
        self,
        working_memory_tokens: int = 8000,
        episodic_memory_tokens: int = 32000,
        client: Optional[AsyncOpenAI] = None,
        model: str = "gpt-4o-mini"
    ):
        self.client = client or AsyncOpenAI()
        self.model = model

        # 初始化三層記憶
        self.working = WorkingMemory(max_tokens=working_memory_tokens)
        self.episodic = EpisodicMemory(max_tokens=episodic_memory_tokens)
        self.semantic = SemanticMemory()

        # 初始化輔助組件
        self._compressor = EpisodeCompressor(client=self.client, model=model)
        self._embedder = EmbeddingGenerator(client=self.client)

        # 設置回調
        self.episodic.set_compressor(
            lambda content: asyncio.get_event_loop().run_until_complete(
                self._compressor.compress(content)
            )
        )
        self.semantic.set_embedder(self._embedder.embed_sync)

    async def process_step(
        self,
        thought: str,
        action: Optional[Dict[str, Any]] = None,
        observation: Optional[str] = None,
        importance: float = 0.5
    ) -> Episode:
        """
        處理研究步驟

        ‹1› 添加到情節記憶
        ‹2› 更新工作記憶
        ‹3› 必要時提取知識到語義記憶
        """
        # 1. 添加情節
        episode = self.episodic.add_episode(
            thought=thought,
            action=action,
            observation=observation,
            importance=importance
        )

        # 2. 更新工作記憶（只保留最新思考和觀察）
        self.working.add(
            content=f"步驟 {episode.step_number}: {thought[:100]}...",
            importance=importance,
            priority=MemoryPriority.MEDIUM if importance < 0.7 else MemoryPriority.HIGH,
            source="episode",
            step_number=episode.step_number
        )

        # 3. 如果是高重要性步驟，提取到語義記憶
        if importance >= 0.8 and observation:
            await self._extract_knowledge(episode)

        return episode

    async def _extract_knowledge(self, episode: Episode) -> None:
        """從情節中提取知識"""
        # 使用 LLM 提取關鍵知識
        extraction_prompt = f"""從以下研究步驟中提取可重用的知識點。
只提取事實性資訊，不包含過程描述。
每個知識點一行，最多 3 條。

研究步驟：
{episode.to_prompt()}

知識點："""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": extraction_prompt}],
            max_tokens=200,
            temperature=0.3
        )

        knowledge_text = response.choices[0].message.content.strip()

        # 分割知識點並添加
        for line in knowledge_text.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                embedding = await self._embedder.embed(line)
                self.semantic.add_knowledge(
                    content=line,
                    embedding=embedding,
                    source_episodes=[episode.step_number]
                )

    async def query(
        self,
        query: str,
        include_working: bool = True,
        include_episodic: bool = True,
        include_semantic: bool = True,
        max_tokens: int = 4000
    ) -> str:
        """
        統一查詢介面

        ‹1› 搜尋所有記憶層
        ‹2› 整合並排序結果
        ‹3› 控制輸出長度
        """
        results = []
        current_tokens = 0

        # 1. 工作記憶（最高優先級）
        if include_working:
            working_prompt = self.working.to_prompt()
            working_tokens = len(working_prompt) // 3
            if current_tokens + working_tokens <= max_tokens:
                results.append(working_prompt)
                current_tokens += working_tokens

        # 2. 語義記憶（相關知識）
        if include_semantic:
            semantic_results = self.semantic.search(query, limit=5)
            for chunk, similarity in semantic_results:
                chunk_tokens = len(chunk.content) // 3
                if current_tokens + chunk_tokens > max_tokens:
                    break
                results.append(f"[知識] {chunk.content}")
                current_tokens += chunk_tokens

        # 3. 情節記憶（最近步驟）
        if include_episodic:
            recent = self.episodic.get_recent(5)
            for episode in recent:
                ep_content = episode.to_prompt(use_summary=True)
                ep_tokens = len(ep_content) // 3
                if current_tokens + ep_tokens > max_tokens:
                    break
                results.append(ep_content)
                current_tokens += ep_tokens

        return "\n\n".join(results)

    def build_context(
        self,
        current_query: str,
        system_prompt: str = "",
        max_context_tokens: int = 8000
    ) -> List[Dict[str, str]]:
        """
        構建完整的對話上下文

        ‹1› 系統提示詞
        ‹2› 記憶內容
        ‹3› 當前問題
        """
        messages = []

        # 系統提示詞
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # 記憶上下文
        memory_context = asyncio.get_event_loop().run_until_complete(
            self.query(
                current_query,
                max_tokens=max_context_tokens - 1000  # 預留空間
            )
        )

        if memory_context:
            messages.append({
                "role": "system",
                "content": f"以下是相關的研究上下文：\n\n{memory_context}"
            })

        # 當前問題
        messages.append({
            "role": "user",
            "content": current_query
        })

        return messages

    def get_statistics(self) -> Dict[str, Any]:
        """獲取完整統計"""
        return {
            "working_memory": self.working.get_statistics(),
            "episodic_memory": self.episodic.get_statistics(),
            "semantic_memory": self.semantic.get_statistics(),
            "total_tokens": (
                self.working._current_tokens +
                self.episodic._current_tokens
            )
        }
```

---

## 6.7 實戰：記憶增強的研究代理人

讓我們將記憶管理整合到研究代理人中：

```python
class MemoryEnhancedResearchAgent:
    """
    記憶增強研究代理人

    ‹1› 整合統一記憶管理器
    ‹2› 自動處理記憶層級
    ‹3› 支援長程研究任務
    """

    SYSTEM_PROMPT = """你是一個專業的研究助理，具備以下能力：

1. 深度搜尋：能夠從網路獲取最新資訊
2. 批判思考：能夠評估資訊的可靠性
3. 知識整合：能夠將多個來源的資訊整合成有條理的報告

你可以存取以下記憶系統：
- 工作記憶：當前任務的關鍵資訊
- 研究歷程：過去的研究步驟摘要
- 知識庫：已驗證的事實和發現

請基於這些記憶，提供準確、有依據的回答。"""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_iterations: int = 20
    ):
        self.client = AsyncOpenAI()
        self.model = model
        self.max_iterations = max_iterations

        # 初始化記憶管理器
        self.memory = UnifiedMemoryManager(
            client=self.client,
            model=model
        )

        # 初始化工具（使用第 5 章的 ToolManager）
        # self.tools = ToolManager(client=self.client)

    async def research(
        self,
        query: str,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        執行研究任務

        ‹1› 初始化記憶
        ‹2› 執行 ReAct 循環
        ‹3› 整合結果
        """
        # 記錄原始問題（最高優先級）
        self.memory.working.add(
            content=f"研究問題：{query}",
            importance=1.0,
            priority=MemoryPriority.CRITICAL,
            source="user"
        )

        iteration = 0
        final_answer = None

        while iteration < self.max_iterations:
            iteration += 1

            if verbose:
                print(f"\n🔄 迭代 {iteration}/{self.max_iterations}")

            # 構建上下文
            messages = self.memory.build_context(
                current_query=query,
                system_prompt=self.SYSTEM_PROMPT
            )

            # 調用 LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7
            )

            content = response.choices[0].message.content

            # 解析回應（簡化版，實際應使用工具調用）
            if "[最終答案]" in content:
                final_answer = content.split("[最終答案]")[1].strip()
                break

            # 記錄思考過程
            thought = content[:500] if len(content) > 500 else content

            # 模擬工具調用結果
            observation = f"這是步驟 {iteration} 的觀察結果..."

            # 計算重要性
            importance = 0.5
            if any(kw in content.lower() for kw in ["發現", "關鍵", "重要", "結論"]):
                importance = 0.8

            # 記錄到記憶
            await self.memory.process_step(
                thought=thought,
                action={"tool_name": "think", "step": iteration},
                observation=observation,
                importance=importance
            )

            if verbose:
                stats = self.memory.get_statistics()
                print(f"   📊 記憶使用：工作 {stats['working_memory']['utilization']*100:.1f}%，"
                      f"情節 {stats['episodic_memory']['utilization']*100:.1f}%")

        # 整合結果
        return {
            "query": query,
            "answer": final_answer or "未能完成研究",
            "iterations": iteration,
            "memory_stats": self.memory.get_statistics()
        }


# 使用範例
async def demo():
    agent = MemoryEnhancedResearchAgent()

    result = await agent.research(
        "分析 2024 年全球電動車市場的主要趨勢和競爭格局"
    )

    print("\n" + "=" * 60)
    print("📝 研究結果")
    print("=" * 60)
    print(result["answer"])
    print(f"\n📊 總迭代次數: {result['iterations']}")
```

---

## 6.8 效能優化技巧

### 6.8.1 漸進式壓縮

```python
class ProgressiveCompressor:
    """
    漸進式壓縮器

    ‹1› 根據記憶年齡調整壓縮程度
    ‹2› 越舊的記憶壓縮越狠
    """

    COMPRESSION_LEVELS = {
        "light": "保留 80% 細節，壓縮到 100 字",
        "medium": "保留 50% 細節，壓縮到 50 字",
        "heavy": "只保留關鍵結論，壓縮到 20 字"
    }

    def __init__(self, client: AsyncOpenAI):
        self.client = client

    def get_compression_level(self, age_hours: float) -> str:
        """根據年齡決定壓縮級別"""
        if age_hours < 1:
            return "light"
        elif age_hours < 4:
            return "medium"
        else:
            return "heavy"

    async def compress(
        self,
        content: str,
        level: str = "medium"
    ) -> str:
        instruction = self.COMPRESSION_LEVELS[level]

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"請{instruction}：\n\n{content}"
            }],
            max_tokens=150
        )

        return response.choices[0].message.content.strip()
```

### 6.8.2 選擇性檢索

```python
class SelectiveRetriever:
    """
    選擇性檢索器

    ‹1› 根據查詢類型選擇記憶層
    ‹2› 優化檢索效率
    """

    QUERY_PATTERNS = {
        "recent": ["最近", "剛才", "上一步", "之前"],
        "factual": ["什麼是", "定義", "解釋", "是什麼"],
        "historical": ["過程", "如何", "為什麼", "步驟"]
    }

    def classify_query(self, query: str) -> str:
        """分類查詢類型"""
        for query_type, patterns in self.QUERY_PATTERNS.items():
            if any(p in query for p in patterns):
                return query_type
        return "general"

    async def retrieve(
        self,
        query: str,
        memory: UnifiedMemoryManager
    ) -> str:
        query_type = self.classify_query(query)

        if query_type == "recent":
            # 優先檢索情節記憶
            return await memory.query(
                query,
                include_working=True,
                include_episodic=True,
                include_semantic=False
            )

        elif query_type == "factual":
            # 優先檢索語義記憶
            return await memory.query(
                query,
                include_working=False,
                include_episodic=False,
                include_semantic=True
            )

        else:
            # 全面檢索
            return await memory.query(query)
```

### 6.8.3 記憶垃圾回收

```python
class MemoryGarbageCollector:
    """
    記憶垃圾回收器

    ‹1› 定期清理低價值記憶
    ‹2› 合併重複知識
    ‹3› 釋放空間供新記憶使用
    """

    def __init__(
        self,
        min_access_count: int = 0,
        min_importance: float = 0.2,
        max_age_hours: float = 24
    ):
        self.min_access_count = min_access_count
        self.min_importance = min_importance
        self.max_age_hours = max_age_hours

    def collect(self, memory: UnifiedMemoryManager) -> Dict[str, int]:
        """執行垃圾回收"""
        stats = {"working": 0, "episodic": 0, "semantic": 0}

        # 清理工作記憶中的低優先級項目
        items_to_remove = []
        for item_id, item in memory.working._items.items():
            age_hours = (datetime.now() - item.created_at).total_seconds() / 3600
            if (
                item.access_count <= self.min_access_count and
                item.importance < self.min_importance and
                age_hours > 1 and
                item.priority.value < MemoryPriority.HIGH.value
            ):
                items_to_remove.append(item_id)

        for item_id in items_to_remove:
            item = memory.working._items.pop(item_id)
            memory.working._current_tokens -= item.token_count
            stats["working"] += 1

        # 更多清理邏輯...

        return stats
```

---

## 6.9 章節總結

### 核心收穫

1. **三層記憶架構**
   - 工作記憶：當前上下文（~8K tokens）
   - 情節記憶：研究步驟（~32K tokens）
   - 語義記憶：持久知識（無限）

2. **關鍵技術**
   - LRU 驅逐策略
   - 動態壓縮
   - 向量語義檢索
   - 漸進式壓縮

3. **設計原則**
   - 按重要性分配資源
   - 新鮮度與相關性平衡
   - 自動層級轉換

### 檢查清單

- [ ] 實現三層記憶資料結構
- [ ] 建立 LRU 驅逐機制
- [ ] 整合 LLM 壓縮功能
- [ ] 實現向量語義檢索
- [ ] 建立統一查詢介面
- [ ] 測試長程研究任務

### 本章產出物

| 類型 | 內容 |
|------|------|
| **資料結構** | MemoryItem, Episode, KnowledgeChunk |
| **管理器** | WorkingMemory, EpisodicMemory, SemanticMemory |
| **整合器** | UnifiedMemoryManager |
| **輔助工具** | EpisodeCompressor, EmbeddingGenerator |
| **優化器** | ProgressiveCompressor, SelectiveRetriever |

---

## 6.10 下一章預告

**第 7 章：搜尋與檢索引擎**

在下一章中，我們將深入探討：

- 網頁瀏覽與內容擷取
- RAG（檢索增強生成）實現
- 知識圖譜建構
- 多模態資訊檢索

你將學會如何讓代理人從網路獲取資訊，並將其整合到記憶系統中。

---

## 本章程式碼

**GitHub 位置**：`code-examples/chapter-06/`

| 檔案 | 行數 | 說明 |
|------|------|------|
| `memory_manager.py` | ~600 | 統一記憶管理系統 |
| `compressor.py` | ~150 | 情節壓縮器 |
| `embedder.py` | ~100 | 嵌入生成器 |
| `requirements.txt` | - | 依賴清單 |
| `.env.example` | - | 環境變數範例 |
