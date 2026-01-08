#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 7 章：搜尋與檢索引擎
RAG 檢索系統實現

這個模組實現了完整的 RAG 系統：
1. 文件分塊
2. 向量索引
3. 相似度檢索

使用方式：
    python rag_retriever.py --demo
"""

import asyncio
import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


# =============================================================================
# 資料結構
# =============================================================================

@dataclass
class DocumentChunk:
    """
    文件片段

    ‹1› 包含原始內容和來源資訊
    ‹2› 支援向量嵌入
    """
    content: str
    source_url: str
    chunk_index: int
    total_chunks: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        url_hash = hashlib.md5(self.source_url.encode()).hexdigest()[:8]
        return f"chunk_{url_hash}_{self.chunk_index}"

    @property
    def token_count(self) -> int:
        return len(self.content) // 3

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "source_url": self.source_url,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "token_count": self.token_count
        }


# =============================================================================
# 文件分塊器
# =============================================================================

class DocumentChunker:
    """
    文件分塊器

    ‹1› 支援多種分塊策略
    ‹2› 保持語義完整性
    ‹3› 處理重疊以避免資訊丟失
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", ".", " "]

    def chunk(
        self,
        text: str,
        source_url: str = "",
        **metadata
    ) -> List[DocumentChunk]:
        """將文件分割成片段"""
        if not text.strip():
            return []

        chunks = []
        current_pos = 0
        chunk_index = 0

        while current_pos < len(text):
            end_pos = current_pos + self.chunk_size

            if end_pos >= len(text):
                chunk_text = text[current_pos:].strip()
                if chunk_text:
                    chunks.append(DocumentChunk(
                        content=chunk_text,
                        source_url=source_url,
                        chunk_index=chunk_index,
                        total_chunks=0,
                        metadata=metadata
                    ))
                break

            # 尋找最佳分割點
            best_split = end_pos
            for separator in self.separators:
                search_start = max(current_pos + self.chunk_size // 2, current_pos)
                sep_pos = text.rfind(separator, search_start, end_pos + 50)
                if sep_pos > current_pos:
                    best_split = sep_pos + len(separator)
                    break

            chunk_text = text[current_pos:best_split].strip()
            if chunk_text:
                chunks.append(DocumentChunk(
                    content=chunk_text,
                    source_url=source_url,
                    chunk_index=chunk_index,
                    total_chunks=0,
                    metadata=metadata
                ))
                chunk_index += 1

            current_pos = best_split - self.chunk_overlap

        # 更新總片段數
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks


# =============================================================================
# 向量索引
# =============================================================================

class VectorIndex:
    """
    向量索引

    ‹1› 高效的相似度搜尋
    ‹2› 支援增量更新
    """

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self._chunks: List[DocumentChunk] = []
        self._embeddings: Optional[np.ndarray] = None

    def add(self, chunk: DocumentChunk) -> None:
        """添加片段"""
        if chunk.embedding is None:
            raise ValueError("片段必須包含嵌入向量")

        self._chunks.append(chunk)

        embedding = np.array(chunk.embedding).reshape(1, -1)
        if self._embeddings is None:
            self._embeddings = embedding
        else:
            self._embeddings = np.vstack([self._embeddings, embedding])

    def add_batch(self, chunks: List[DocumentChunk]) -> None:
        """批次添加片段"""
        for chunk in chunks:
            self.add(chunk)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[Tuple[DocumentChunk, float]]:
        """搜尋最相關的片段"""
        if self._embeddings is None or len(self._chunks) == 0:
            return []

        query = np.array(query_embedding)

        # 計算餘弦相似度
        norms = np.linalg.norm(self._embeddings, axis=1)
        query_norm = np.linalg.norm(query)

        if query_norm == 0:
            return []

        similarities = np.dot(self._embeddings, query) / (norms * query_norm + 1e-8)

        # 獲取 top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= min_score:
                results.append((self._chunks[idx], score))

        return results

    @property
    def size(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        """清空索引"""
        self._chunks = []
        self._embeddings = None


# =============================================================================
# 嵌入器
# =============================================================================

class Embedder:
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

    async def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """批次生成嵌入"""
        tasks = [self.embed(t) for t in texts]
        return await asyncio.gather(*tasks)


class SimpleEmbedder:
    """簡單嵌入器（不需要 API）"""

    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions

    def embed(self, text: str) -> List[float]:
        """生成簡單嵌入"""
        embedding = []

        embedding.append(len(text) / 1000)

        for c in "abcdefghijklmnopqrstuvwxyz":
            embedding.append(text.lower().count(c) / max(len(text), 1))

        embedding.append(sum(c.isdigit() for c in text) / max(len(text), 1))
        embedding.append(sum(c in ".,!?;:" for c in text) / max(len(text), 1))
        embedding.append(text.count(" ") / max(len(text), 1))

        while len(embedding) < self.dimensions:
            embedding.append(0.0)

        embedding = embedding[:self.dimensions]

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [e / norm for e in embedding]

        return embedding

    async def embed_async(self, text: str) -> List[float]:
        return self.embed(text)


# =============================================================================
# RAG 檢索器
# =============================================================================

class RAGRetriever:
    """
    RAG 檢索器

    ‹1› 整合分塊、索引和檢索
    ‹2› 支援多種檢索策略
    ‹3› 提供上下文增強
    """

    def __init__(
        self,
        embedder=None,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.embedder = embedder or SimpleEmbedder()
        self.chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.index = VectorIndex(dimension=128)

    async def add_document(
        self,
        content: str,
        source_url: str = "",
        **metadata
    ) -> int:
        """添加文件到索引"""
        chunks = self.chunker.chunk(content, source_url, **metadata)

        for chunk in chunks:
            if hasattr(self.embedder, 'embed_async'):
                embedding = await self.embedder.embed_async(chunk.content)
            else:
                embedding = self.embedder.embed(chunk.content)
            chunk.embedding = embedding
            self.index.add(chunk)

        return len(chunks)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Tuple[DocumentChunk, float]]:
        """檢索相關片段"""
        if hasattr(self.embedder, 'embed_async'):
            query_embedding = await self.embedder.embed_async(query)
        else:
            query_embedding = self.embedder.embed(query)
        return self.index.search(query_embedding, top_k, min_score)

    async def retrieve_with_context(
        self,
        query: str,
        top_k: int = 5
    ) -> str:
        """檢索並生成上下文"""
        results = await self.retrieve(query, top_k)

        if not results:
            return "未找到相關資訊。"

        context_parts = []
        for chunk, score in results:
            source = chunk.source_url or "未知來源"
            context_parts.append(
                f"[來源: {source}]\n"
                f"[相關度: {score:.2f}]\n"
                f"{chunk.content}"
            )

        return "\n\n---\n\n".join(context_parts)

    @property
    def document_count(self) -> int:
        return self.index.size

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_chunks": self.index.size,
            "chunk_size": self.chunker.chunk_size,
            "chunk_overlap": self.chunker.chunk_overlap
        }


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範 RAG 功能"""
    print("=" * 60)
    print("📚 RAG 檢索系統示範")
    print("=" * 60)

    # 創建 RAG 檢索器
    rag = RAGRetriever(
        embedder=SimpleEmbedder(dimensions=128),
        chunk_size=200,
        chunk_overlap=20
    )

    # 添加示範文件
    documents = [
        {
            "content": """
            NVIDIA 是全球最大的 AI 晶片供應商，市場份額約 80%。
            其 GPU 產品線包括 A100、H100 和最新的 H200。
            CUDA 生態系統擁有超過 400 萬開發者。
            Tensor Core 專為深度學習優化，支援 FP8 精度。
            """,
            "source": "https://example.com/nvidia-analysis"
        },
        {
            "content": """
            AMD 是 NVIDIA 的主要競爭對手，市場份額約 10%。
            MI300 系列是 AMD 的旗艦 AI 加速器。
            ROCm 是 AMD 的 GPU 計算平台，對標 CUDA。
            AMD 在性價比方面有一定優勢。
            """,
            "source": "https://example.com/amd-analysis"
        },
        {
            "content": """
            Intel 正在積極進入 AI 晶片市場。
            Gaudi 系列是 Intel 的 AI 加速器產品線。
            Intel 收購了 Habana Labs 以加強 AI 能力。
            目前市場份額約 5%，但正在快速成長。
            """,
            "source": "https://example.com/intel-analysis"
        }
    ]

    print("\n📥 添加文件...")
    for doc in documents:
        chunks = await rag.add_document(doc["content"], doc["source"])
        print(f"   添加 {chunks} 個片段: {doc['source']}")

    print(f"\n📊 索引統計: {rag.get_statistics()}")

    # 執行檢索
    queries = [
        "NVIDIA 的市場份額是多少？",
        "AMD 的競爭優勢是什麼？",
        "Intel 在 AI 領域的策略"
    ]

    for query in queries:
        print(f"\n🔍 查詢: {query}")
        print("-" * 40)

        results = await rag.retrieve(query, top_k=2)

        for chunk, score in results:
            print(f"[{score:.3f}] {chunk.content[:100]}...")
            print(f"        來源: {chunk.source_url}")

    # 生成上下文
    print("\n" + "=" * 60)
    print("📝 生成研究上下文")
    print("=" * 60)

    context = await rag.retrieve_with_context("AI 晶片市場競爭格局", top_k=3)
    print(context)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="RAG 檢索系統")
    parser.add_argument("--demo", action="store_true", help="執行示範")

    args = parser.parse_args()
    asyncio.run(demo())


if __name__ == "__main__":
    main()
