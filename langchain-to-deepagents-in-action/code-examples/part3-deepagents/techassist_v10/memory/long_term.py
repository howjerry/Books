"""
TechAssist v1.0 - 長期記憶

基於向量的語義記憶存儲
"""

import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict

from ..config import config


@dataclass
class MemoryEntry:
    """記憶條目"""
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    importance: float = 0.5
    access_count: int = 0
    user_id: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class SimpleEmbeddings:
    """簡化的嵌入實現（用於演示）

    生產環境應使用：
    - OpenAI Embeddings
    - Sentence Transformers
    - Cohere Embeddings
    """

    def embed_query(self, text: str) -> list[float]:
        """生成文本的嵌入向量"""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_bytes[:64]]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量生成嵌入"""
        return [self.embed_query(t) for t in texts]


class LongTermMemory:
    """長期記憶：向量化的持久記憶存儲

    生產環境應使用：
    - Qdrant
    - Pinecone
    - Weaviate
    - Chroma
    """

    def __init__(self, embeddings: SimpleEmbeddings | None = None):
        self.embeddings = embeddings or SimpleEmbeddings()
        self.memories: list[MemoryEntry] = []
        self.vectors: list[list[float]] = []

    def add(
        self,
        content: str,
        importance: float = 0.5,
        user_id: str = "",
        metadata: dict | None = None
    ) -> None:
        """添加記憶"""
        entry = MemoryEntry(
            content=content,
            importance=importance,
            user_id=user_id,
            metadata=metadata or {}
        )
        self.memories.append(entry)
        self.vectors.append(self.embeddings.embed_query(content))

    def search(
        self,
        query: str,
        top_k: int | None = None,
        user_id: str | None = None
    ) -> list[tuple[MemoryEntry, float]]:
        """語義搜尋相關記憶"""
        top_k = top_k or config.long_term_top_k

        if not self.memories:
            return []

        query_vector = self.embeddings.embed_query(query)

        # 計算相似度
        scored = []
        for i, (mem, vec) in enumerate(zip(self.memories, self.vectors)):
            # 用戶過濾
            if user_id and mem.user_id and mem.user_id != user_id:
                continue

            # 餘弦相似度
            dot_product = sum(a * b for a, b in zip(query_vector, vec))
            norm_q = sum(a * a for a in query_vector) ** 0.5
            norm_v = sum(b * b for b in vec) ** 0.5
            similarity = dot_product / (norm_q * norm_v) if norm_q * norm_v > 0 else 0

            # 結合相似度和重要性
            final_score = similarity * 0.7 + mem.importance * 0.3
            scored.append((mem, final_score))

        # 排序並更新訪問計數
        scored.sort(key=lambda x: x[1], reverse=True)
        for mem, _ in scored[:top_k]:
            mem.access_count += 1

        return scored[:top_k]

    def get_by_importance(
        self,
        min_importance: float = 0.7,
        limit: int = 10
    ) -> list[MemoryEntry]:
        """獲取高重要性記憶"""
        important = [m for m in self.memories if m.importance >= min_importance]
        important.sort(key=lambda x: x.importance, reverse=True)
        return important[:limit]

    def __len__(self) -> int:
        return len(self.memories)
