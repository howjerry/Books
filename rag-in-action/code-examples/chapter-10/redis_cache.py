"""
Chapter 10: RAG 快取策略實作

實作三層快取：查詢快取、Embedding 快取、結果快取
"""

import hashlib
import json
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

import redis


class CacheLayer(Enum):
    """快取層級"""
    QUERY = "query"           # 查詢快取
    EMBEDDING = "embedding"   # Embedding 快取
    RESULT = "result"         # 結果快取


@dataclass
class CachedResult:
    """快取的回答結果"""
    answer: str
    sources: List[str]
    created_at: float
    hit_count: int = 0


class RAGCache:
    """
    RAG 系統多層快取

    架構：
    1. 查詢快取：相同問題直接返回
    2. Embedding 快取：避免重複計算向量
    3. 結果快取：相似問題返回快取
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        query_ttl: int = 3600,        # 查詢快取 1 小時
        embedding_ttl: int = 86400,   # Embedding 快取 24 小時
        result_ttl: int = 1800        # 結果快取 30 分鐘
    ):
        self.redis = redis.from_url(redis_url)
        self.ttls = {
            CacheLayer.QUERY: query_ttl,
            CacheLayer.EMBEDDING: embedding_ttl,
            CacheLayer.RESULT: result_ttl,
        }

    # ═══════════════════════════════════════════════════════════════
    # 查詢快取
    # ═══════════════════════════════════════════════════════════════

    def _query_key(self, query: str) -> str:
        """生成查詢快取鍵"""
        normalized = query.lower().strip()
        hash_val = hashlib.md5(normalized.encode()).hexdigest()[:12]
        return f"rag:query:{hash_val}"

    def get_cached_answer(self, query: str) -> Optional[CachedResult]:
        """
        查詢快取命中

        Args:
            query: 使用者問題

        Returns:
            快取的回答或 None
        """
        key = self._query_key(query)
        data = self.redis.get(key)

        if data:
            result = json.loads(data)
            # 更新命中次數
            result["hit_count"] += 1
            self.redis.setex(
                key,
                self.ttls[CacheLayer.QUERY],
                json.dumps(result)
            )
            return CachedResult(**result)

        return None

    def cache_answer(
        self,
        query: str,
        answer: str,
        sources: List[str]
    ) -> None:
        """
        快取回答

        Args:
            query: 使用者問題
            answer: AI 回答
            sources: 引用來源
        """
        key = self._query_key(query)
        result = CachedResult(
            answer=answer,
            sources=sources,
            created_at=time.time(),
            hit_count=0
        )
        self.redis.setex(
            key,
            self.ttls[CacheLayer.QUERY],
            json.dumps(asdict(result))
        )

    # ═══════════════════════════════════════════════════════════════
    # Embedding 快取
    # ═══════════════════════════════════════════════════════════════

    def _embedding_key(self, text: str) -> str:
        """生成 Embedding 快取鍵"""
        hash_val = hashlib.md5(text.encode()).hexdigest()
        return f"rag:emb:{hash_val}"

    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """取得快取的 Embedding"""
        key = self._embedding_key(text)
        data = self.redis.get(key)

        if data:
            return json.loads(data)
        return None

    def cache_embedding(self, text: str, embedding: List[float]) -> None:
        """快取 Embedding"""
        key = self._embedding_key(text)
        self.redis.setex(
            key,
            self.ttls[CacheLayer.EMBEDDING],
            json.dumps(embedding)
        )

    # ═══════════════════════════════════════════════════════════════
    # 統計與管理
    # ═══════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """取得快取統計"""
        query_keys = len(list(self.redis.scan_iter("rag:query:*")))
        emb_keys = len(list(self.redis.scan_iter("rag:emb:*")))

        return {
            "query_cache_size": query_keys,
            "embedding_cache_size": emb_keys,
            "memory_usage_bytes": self.redis.info("memory")["used_memory"],
        }

    def clear_all(self) -> int:
        """清除所有 RAG 快取"""
        count = 0
        for key in self.redis.scan_iter("rag:*"):
            self.redis.delete(key)
            count += 1
        return count


class CachedRAGService:
    """
    帶快取的 RAG 服務

    整合快取層，減少重複計算
    """

    def __init__(
        self,
        cache: RAGCache,
        embedding_fn,
        retrieval_fn,
        generation_fn
    ):
        self.cache = cache
        self.embed = embedding_fn
        self.retrieve = retrieval_fn
        self.generate = generation_fn

    def answer(self, query: str) -> Dict[str, Any]:
        """
        處理查詢（帶快取）

        流程：
        1. 檢查查詢快取
        2. 檢查 Embedding 快取
        3. 檢索並生成
        4. 快取結果
        """
        # 1. 查詢快取命中？
        cached = self.cache.get_cached_answer(query)
        if cached:
            return {
                "answer": cached.answer,
                "sources": cached.sources,
                "cache_hit": True,
                "cache_type": "query"
            }

        # 2. Embedding 快取命中？
        embedding = self.cache.get_cached_embedding(query)
        if embedding is None:
            embedding = self.embed(query)
            self.cache.cache_embedding(query, embedding)
            emb_cache_hit = False
        else:
            emb_cache_hit = True

        # 3. 檢索
        docs = self.retrieve(embedding)

        # 4. 生成
        answer, sources = self.generate(query, docs)

        # 5. 快取結果
        self.cache.cache_answer(query, answer, sources)

        return {
            "answer": answer,
            "sources": sources,
            "cache_hit": emb_cache_hit,
            "cache_type": "embedding" if emb_cache_hit else "none"
        }
