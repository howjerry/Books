#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 6 章：長短時記憶管理
統一記憶管理系統完整實現

這個模組實現了完整的三層記憶架構，包含：
1. 工作記憶（Working Memory）- 當前任務上下文
2. 情節記憶（Episodic Memory）- 研究步驟歷程
3. 語義記憶（Semantic Memory）- 持久化知識庫

使用方式：
    python memory_manager.py --demo
    python memory_manager.py --test
"""

import asyncio
import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 載入環境變數
load_dotenv()


# =============================================================================
# 基礎資料結構
# =============================================================================

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
    content: str
    memory_type: MemoryType
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: float = 0.5
    priority: MemoryPriority = MemoryPriority.MEDIUM
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _id: str = field(default="", init=False)

    def __post_init__(self):
        content_hash = hashlib.md5(self.content.encode()).hexdigest()[:12]
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
        decay_rate = 0.693 / 3600  # ln(2) / 1 hour
        return min(1.0, max(0.0, np.exp(-decay_rate * age)))

    @property
    def relevance_score(self) -> float:
        """計算綜合相關性分數"""
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


# =============================================================================
# 工作記憶
# =============================================================================

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
        protected_ratio: float = 0.2
    ):
        self.max_tokens = max_tokens
        self.protected_tokens = int(max_tokens * protected_ratio)
        self._items: OrderedDict[str, MemoryItem] = OrderedDict()
        self._current_tokens = 0

    @property
    def available_tokens(self) -> int:
        return self.max_tokens - self._current_tokens

    @property
    def utilization(self) -> float:
        return self._current_tokens / self.max_tokens if self.max_tokens > 0 else 0

    def add(
        self,
        content: str,
        importance: float = 0.5,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        **metadata
    ) -> MemoryItem:
        """添加記憶項目"""
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
                break

        self._items[item.id] = item
        self._items.move_to_end(item.id)
        self._current_tokens += item.token_count

        return item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """獲取記憶項目"""
        if item_id not in self._items:
            return None

        item = self._items[item_id]
        item.access()
        self._items.move_to_end(item_id)
        return item

    def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        """搜尋相關記憶"""
        query_lower = query.lower()
        results = []

        for item in self._items.values():
            content_lower = item.content.lower()
            if query_lower in content_lower:
                score = item.relevance_score + 0.3
                results.append((score, item))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:limit]]

    def _evict_one(self) -> Optional[MemoryItem]:
        """驅逐一個項目"""
        candidates = []

        for item_id, item in self._items.items():
            if item.priority == MemoryPriority.CRITICAL:
                continue
            candidates.append((item.priority.value, item.relevance_score, item_id))

        if not candidates:
            return None

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

    def __iter__(self) -> Iterator[MemoryItem]:
        return iter(self._items.values())

    def __len__(self) -> int:
        return len(self._items)


# =============================================================================
# 情節記憶
# =============================================================================

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
    summary: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    importance: float = 0.5

    @property
    def token_count(self) -> int:
        total = len(self.thought) // 3
        if self.action:
            total += len(json.dumps(self.action)) // 3
        if self.observation:
            total += len(self.observation) // 3
        return total

    @property
    def compressed_token_count(self) -> int:
        if self.summary:
            return len(self.summary) // 3
        return self.token_count

    def compress(self, summary: str) -> None:
        self.summary = summary

    def to_prompt(self, use_summary: bool = False) -> str:
        if use_summary and self.summary:
            return f"[步驟 {self.step_number}] {self.summary}"

        lines = [f"[步驟 {self.step_number}]"]
        lines.append(f"思考：{self.thought}")

        if self.action:
            tool_name = self.action.get("tool_name", "unknown")
            lines.append(f"行動：調用 {tool_name}")

        if self.observation:
            obs = self.observation
            if len(obs) > 500:
                obs = obs[:500] + "..."
            lines.append(f"觀察：{obs}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "observation": self.observation,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
            "importance": self.importance,
            "token_count": self.token_count
        }


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
        compression_threshold: float = 0.8,
        window_size: int = 10
    ):
        self.max_tokens = max_tokens
        self.compression_threshold = compression_threshold
        self.window_size = window_size
        self._episodes: List[Episode] = []
        self._current_tokens = 0
        self._compressor: Optional[Callable] = None

    def set_compressor(self, compressor: Callable[[str], str]) -> None:
        """設置壓縮器"""
        self._compressor = compressor

    @property
    def episode_count(self) -> int:
        return len(self._episodes)

    @property
    def utilization(self) -> float:
        return self._current_tokens / self.max_tokens if self.max_tokens > 0 else 0

    def add_episode(
        self,
        thought: str,
        action: Optional[Dict[str, Any]] = None,
        observation: Optional[str] = None,
        importance: float = 0.5
    ) -> Episode:
        """添加新情節"""
        episode = Episode(
            step_number=len(self._episodes) + 1,
            thought=thought,
            action=action,
            observation=observation,
            importance=importance
        )

        self._episodes.append(episode)
        self._current_tokens += episode.token_count

        if self.utilization > self.compression_threshold:
            self._trigger_compression()

        return episode

    def _trigger_compression(self) -> int:
        """觸發壓縮"""
        if not self._compressor:
            return 0

        compressed_count = 0
        target_tokens = int(self.max_tokens * 0.6)

        compressible = self._episodes[:-self.window_size] if len(self._episodes) > self.window_size else []

        for episode in compressible:
            if episode.summary:
                continue

            if self._current_tokens <= target_tokens:
                break

            original_content = episode.to_prompt(use_summary=False)
            summary = self._compressor(original_content)

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
        important = [ep for ep in self._episodes if ep.importance >= min_importance]
        return sorted(important, key=lambda x: x.importance, reverse=True)[:limit]

    def search(self, query: str, limit: int = 5) -> List[Episode]:
        """搜尋相關情節"""
        query_lower = query.lower()
        results = []

        for episode in self._episodes:
            content = episode.to_prompt().lower()
            if query_lower in content:
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
        """生成 prompt"""
        if not self._episodes:
            return ""

        lines = ["[研究歷程]"]
        summary_cutoff = len(self._episodes) - self.window_size

        for i, episode in enumerate(self._episodes):
            use_summary = use_summary_for_old and i < summary_cutoff
            lines.append(episode.to_prompt(use_summary=use_summary))
            lines.append("")

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

    def __iter__(self) -> Iterator[Episode]:
        return iter(self._episodes)

    def __len__(self) -> int:
        return len(self._episodes)


# =============================================================================
# 語義記憶
# =============================================================================

@dataclass
class KnowledgeChunk:
    """知識片段"""
    content: str
    embedding: List[float]
    source_episodes: List[int]
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _id: str = field(default="", init=False)

    def __post_init__(self):
        content_hash = hashlib.md5(self.content.encode()).hexdigest()[:12]
        self._id = f"know_{content_hash}"

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "source_episodes": self.source_episodes,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


class SemanticMemory:
    """
    語義記憶管理器

    ‹1› 使用向量相似度進行語義檢索
    ‹2› 支援知識整合（去重、合併）
    """

    def __init__(
        self,
        embedding_dim: int = 1536,
        similarity_threshold: float = 0.85
    ):
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold
        self._chunks: Dict[str, KnowledgeChunk] = {}
        self._embeddings: Optional[np.ndarray] = None
        self._chunk_ids: List[str] = []
        self._embedder: Optional[Callable] = None

    def set_embedder(self, embedder: Callable[[str], List[float]]) -> None:
        """設置嵌入函數"""
        self._embedder = embedder

    def add_knowledge(
        self,
        content: str,
        embedding: Optional[List[float]] = None,
        source_episodes: Optional[List[int]] = None,
        **metadata
    ) -> Optional[KnowledgeChunk]:
        """添加知識片段"""
        if embedding is None:
            if self._embedder is None:
                raise ValueError("未設置嵌入函數")
            embedding = self._embedder(content)

        # 檢查重複
        if self._chunks:
            similar_id, similarity = self._find_similar(embedding)
            if similarity > self.similarity_threshold:
                self._merge_knowledge(similar_id, content, source_episodes or [])
                return self._chunks[similar_id]

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

    def _find_similar(self, embedding: List[float]) -> Tuple[Optional[str], float]:
        """找到最相似的知識片段"""
        if self._embeddings is None or len(self._chunk_ids) == 0:
            return None, 0.0

        query = np.array(embedding)
        norms = np.linalg.norm(self._embeddings, axis=1)
        query_norm = np.linalg.norm(query)

        if query_norm == 0:
            return None, 0.0

        similarities = np.dot(self._embeddings, query) / (norms * query_norm + 1e-8)
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
        chunk.source_episodes.extend(source_episodes)
        chunk.source_episodes = list(set(chunk.source_episodes))

        if new_content not in chunk.content:
            chunk.metadata["merged_contents"] = chunk.metadata.get("merged_contents", [])
            chunk.metadata["merged_contents"].append(new_content)

    def search(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.5
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """語義搜尋"""
        if self._embedder is None:
            raise ValueError("未設置嵌入函數")

        if not self._chunks:
            return []

        query_embedding = self._embedder(query)
        query_vec = np.array(query_embedding)

        norms = np.linalg.norm(self._embeddings, axis=1)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        similarities = np.dot(self._embeddings, query_vec) / (norms * query_norm + 1e-8)

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

    def to_prompt(self, query: Optional[str] = None, limit: int = 5) -> str:
        """生成 prompt"""
        if not self._chunks:
            return ""

        lines = ["[知識庫]"]

        if query and self._embedder:
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
            "total_sources": sum(len(c.source_episodes) for c in self._chunks.values()),
            "embedding_dim": self.embedding_dim
        }

    def __len__(self) -> int:
        return len(self._chunks)


# =============================================================================
# 輔助組件
# =============================================================================

class EpisodeCompressor:
    """情節壓縮器"""

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

    def compress_sync(self, content: str) -> str:
        """同步壓縮"""
        return asyncio.get_event_loop().run_until_complete(self.compress(content))


class EmbeddingGenerator:
    """嵌入生成器"""

    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        model: str = "text-embedding-3-small"
    ):
        self.client = client or AsyncOpenAI()
        self.model = model
        self._cache: Dict[str, List[float]] = {}

    async def embed(self, text: str) -> List[float]:
        """生成嵌入"""
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )

        embedding = response.data[0].embedding
        self._cache[cache_key] = embedding
        return embedding

    def embed_sync(self, text: str) -> List[float]:
        """同步生成嵌入"""
        return asyncio.get_event_loop().run_until_complete(self.embed(text))


# =============================================================================
# 統一記憶管理器
# =============================================================================

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

        self.working = WorkingMemory(max_tokens=working_memory_tokens)
        self.episodic = EpisodicMemory(max_tokens=episodic_memory_tokens)
        self.semantic = SemanticMemory()

        self._compressor = EpisodeCompressor(client=self.client, model=model)
        self._embedder = EmbeddingGenerator(client=self.client)

        self.episodic.set_compressor(self._compressor.compress_sync)
        self.semantic.set_embedder(self._embedder.embed_sync)

    async def process_step(
        self,
        thought: str,
        action: Optional[Dict[str, Any]] = None,
        observation: Optional[str] = None,
        importance: float = 0.5
    ) -> Episode:
        """處理研究步驟"""
        episode = self.episodic.add_episode(
            thought=thought,
            action=action,
            observation=observation,
            importance=importance
        )

        self.working.add(
            content=f"步驟 {episode.step_number}: {thought[:100]}...",
            importance=importance,
            priority=MemoryPriority.MEDIUM if importance < 0.7 else MemoryPriority.HIGH,
            source="episode",
            step_number=episode.step_number
        )

        if importance >= 0.8 and observation:
            await self._extract_knowledge(episode)

        return episode

    async def _extract_knowledge(self, episode: Episode) -> None:
        """從情節中提取知識"""
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
        """統一查詢介面"""
        results = []
        current_tokens = 0

        if include_working:
            working_prompt = self.working.to_prompt()
            working_tokens = len(working_prompt) // 3
            if current_tokens + working_tokens <= max_tokens:
                results.append(working_prompt)
                current_tokens += working_tokens

        if include_semantic and self.semantic._embedder:
            try:
                semantic_results = self.semantic.search(query, limit=5)
                for chunk, similarity in semantic_results:
                    chunk_tokens = len(chunk.content) // 3
                    if current_tokens + chunk_tokens > max_tokens:
                        break
                    results.append(f"[知識] {chunk.content}")
                    current_tokens += chunk_tokens
            except Exception:
                pass

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


# =============================================================================
# 示範與測試
# =============================================================================

def demo_memory_system():
    """示範記憶系統"""
    print("=" * 60)
    print("🧠 記憶管理系統示範")
    print("=" * 60)

    # 1. 工作記憶示範
    print("\n📍 1. 工作記憶示範")
    print("-" * 40)

    working = WorkingMemory(max_tokens=1000)

    working.add(
        content="研究問題：分析 2024 年 AI 晶片市場",
        importance=1.0,
        priority=MemoryPriority.CRITICAL
    )

    working.add(
        content="需要搜尋市場數據和主要廠商資訊",
        importance=0.8,
        priority=MemoryPriority.HIGH
    )

    working.add(
        content="NVIDIA 市場份額約 80%",
        importance=0.9,
        priority=MemoryPriority.HIGH
    )

    print(working.to_prompt())
    print(f"\n統計: {working.get_statistics()}")

    # 2. 情節記憶示範
    print("\n📍 2. 情節記憶示範")
    print("-" * 40)

    episodic = EpisodicMemory(max_tokens=5000)

    episodic.add_episode(
        thought="需要了解 AI 晶片市場的整體規模",
        action={"tool_name": "web_search", "query": "AI chip market size 2024"},
        observation="市場規模約 500 億美元，年增長 30%",
        importance=0.8
    )

    episodic.add_episode(
        thought="已獲得市場規模，接下來分析主要競爭者",
        action={"tool_name": "web_search", "query": "NVIDIA AMD Intel AI chip"},
        observation="NVIDIA 80%，AMD 10%，Intel 5%",
        importance=0.9
    )

    print(episodic.to_prompt())
    print(f"\n統計: {episodic.get_statistics()}")

    # 3. 語義記憶示範（使用模擬嵌入）
    print("\n📍 3. 語義記憶示範")
    print("-" * 40)

    semantic = SemanticMemory(embedding_dim=4)

    # 使用簡單的模擬嵌入函數
    def simple_embedder(text: str) -> List[float]:
        # 簡單的模擬嵌入：基於文字長度和首字母
        return [
            len(text) / 100,
            ord(text[0]) / 255 if text else 0,
            text.count(" ") / 10,
            len(set(text)) / 50
        ]

    semantic.set_embedder(simple_embedder)

    semantic.add_knowledge(
        content="NVIDIA 在 AI 晶片市場佔據 80% 份額",
        source_episodes=[1, 2]
    )

    semantic.add_knowledge(
        content="AMD 正在積極追趕，目前市場份額約 10%",
        source_episodes=[2]
    )

    print(semantic.to_prompt())
    print(f"\n統計: {semantic.get_statistics()}")

    # 4. 綜合統計
    print("\n📍 4. 綜合統計")
    print("-" * 40)
    print(f"工作記憶: {len(working)} 項，使用率 {working.utilization*100:.1f}%")
    print(f"情節記憶: {len(episodic)} 項，使用率 {episodic.utilization*100:.1f}%")
    print(f"語義記憶: {len(semantic)} 項")


def main():
    """主程式入口"""
    import argparse

    parser = argparse.ArgumentParser(description="記憶管理系統 - 第 6 章範例")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("--test", action="store_true", help="執行測試")

    args = parser.parse_args()

    if args.demo or not args.test:
        demo_memory_system()


if __name__ == "__main__":
    main()
