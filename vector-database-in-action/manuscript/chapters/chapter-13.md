# Chapter 13：語意搜尋引擎案例

> 「傳統搜尋讓你找到包含關鍵字的文件，語意搜尋讓你找到回答問題的答案。」

## 學習目標

完成本章後，你將能夠：

- 設計完整的企業級語意搜尋引擎
- 實作多語言、多模態的搜尋功能
- 建構高效的文件處理和索引管道
- 優化搜尋相關性和使用者體驗
- 部署生產級的語意搜尋系統

---

## 13.1 語意搜尋引擎概述

### 13.1.1 傳統搜尋 vs 語意搜尋

```python
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np

class SearchComparison:
    """
    傳統搜尋與語意搜尋比較

    ‹1› 展示兩種搜尋方式的差異
    """

    @staticmethod
    def demonstrate_difference():
        """
        ‹1› 展示差異
        """
        comparison = """
        傳統搜尋（關鍵字匹配）vs 語意搜尋（向量相似度）
        ================================================

        查詢: "如何讓電腦運行更快"

        傳統搜尋結果（TF-IDF/BM25）:
        ──────────────────────────
        1. "電腦運行速度測試方法" ← 包含 "電腦" "運行"
        2. "快速啟動電腦的技巧" ← 包含 "電腦" "快"
        3. "運行 Python 程式更快" ← 包含 "運行" "更快"

        問題：
        - 只匹配字面關鍵字
        - 無法理解「同義詞」
        - 無法理解「問題意圖」

        語意搜尋結果（向量相似度）:
        ────────────────────────
        1. "提升電腦效能的 10 個方法" ← 語意相關：效能提升
        2. "清理系統垃圾加速電腦" ← 語意相關：加速
        3. "升級硬體改善電腦速度" ← 語意相關：改善速度

        優勢：
        - 理解查詢意圖
        - 找到語意相關的內容
        - 處理同義詞和近義詞

        混合搜尋（最佳實踐）:
        ──────────────────
        結合關鍵字匹配和語意相似度
        - 精確匹配：確保相關度
        - 語意擴展：發現更多結果
        """
        print(comparison)


@dataclass
class SearchResult:
    """搜尋結果"""
    doc_id: str
    title: str
    content: str
    score: float
    match_type: str  # keyword, semantic, hybrid


class SemanticSearchDemo:
    """
    語意搜尋示範

    ‹1› 展示語意搜尋的核心概念
    """

    def __init__(self):
        self.documents = []
        self.embeddings = None

    def add_documents(self, documents: List[Dict[str, str]]):
        """添加文件"""
        self.documents = documents
        # 模擬生成嵌入
        np.random.seed(42)
        self.embeddings = np.random.randn(len(documents), 768).astype(np.float32)
        # 正規化
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        self.embeddings = self.embeddings / norms

    def semantic_search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        ‹1› 語意搜尋

        Args:
            query: 查詢文字
            top_k: 返回結果數

        Returns:
            搜尋結果列表
        """
        # 模擬查詢向量（實際應用嵌入模型）
        np.random.seed(hash(query) % 2**32)
        query_vector = np.random.randn(768).astype(np.float32)
        query_vector = query_vector / np.linalg.norm(query_vector)

        # 計算相似度
        similarities = np.dot(self.embeddings, query_vector)

        # 獲取 top-k
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            doc = self.documents[idx]
            results.append(SearchResult(
                doc_id=doc["id"],
                title=doc["title"],
                content=doc["content"][:100] + "...",
                score=float(similarities[idx]),
                match_type="semantic"
            ))

        return results


def demonstrate_semantic_search():
    """
    ‹1› 語意搜尋示範
    """
    print("語意搜尋引擎示範")
    print("=" * 60)

    # 比較說明
    SearchComparison.demonstrate_difference()

    # 實際示範
    print("\n實際搜尋示範:")
    print("-" * 50)

    demo = SemanticSearchDemo()

    # 添加示範文件
    documents = [
        {"id": "1", "title": "機器學習入門", "content": "機器學習是人工智慧的重要分支，讓電腦能夠從數據中學習..."},
        {"id": "2", "title": "深度學習基礎", "content": "深度學習使用多層神經網路來處理複雜的模式識別問題..."},
        {"id": "3", "title": "自然語言處理", "content": "NLP 技術讓電腦能夠理解和生成人類語言..."},
        {"id": "4", "title": "電腦視覺應用", "content": "電腦視覺技術讓機器能夠看到和理解圖像內容..."},
        {"id": "5", "title": "推薦系統原理", "content": "推薦系統根據用戶行為和偏好推薦相關內容..."},
    ]
    demo.add_documents(documents)

    # 執行搜尋
    query = "如何讓機器理解人類語言"
    print(f"查詢: {query}\n")

    results = demo.semantic_search(query, top_k=3)

    for i, result in enumerate(results, 1):
        print(f"{i}. {result.title}")
        print(f"   相似度: {result.score:.4f}")
        print(f"   內容: {result.content}")
        print()


if __name__ == "__main__":
    demonstrate_semantic_search()
```

### 13.1.2 系統架構

```
                    企業語意搜尋引擎架構
    ┌─────────────────────────────────────────────────────┐
    │                    使用者介面層                      │
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
    │  │ Web UI  │ │  API    │ │ Chatbot │ │  SDK    │  │
    │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
    └───────┼───────────┼───────────┼───────────┼───────┘
            │           │           │           │
    ┌───────┼───────────┼───────────┼───────────┼───────┐
    │       ▼           ▼           ▼           ▼       │
    │                  搜尋服務層                        │
    │  ┌─────────────────────────────────────────────┐  │
    │  │           Query Processing                  │  │
    │  │  • 查詢理解  • 查詢改寫  • 意圖識別          │  │
    │  └─────────────────────┬───────────────────────┘  │
    │                        │                          │
    │  ┌─────────────────────▼───────────────────────┐  │
    │  │              混合搜尋引擎                    │  │
    │  │  • 語意搜尋（向量）                          │  │
    │  │  • 關鍵字搜尋（BM25）                        │  │
    │  │  • 結果融合                                  │  │
    │  └─────────────────────┬───────────────────────┘  │
    │                        │                          │
    │  ┌─────────────────────▼───────────────────────┐  │
    │  │              排序與優化                      │  │
    │  │  • 相關性排序  • 個人化  • 多樣性            │  │
    │  └─────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    │                         ▼                         │
    │                   資料存儲層                      │
    │  ┌─────────┐ ┌──────────┐ ┌─────────┐           │
    │  │ Vector  │ │ Document │ │  Index  │           │
    │  │ Store   │ │ Store    │ │ Store   │           │
    │  └─────────┘ └──────────┘ └─────────┘           │
    └─────────────────────────────────────────────────┘
```

---

## 13.2 文件處理管道

### 13.2.1 文件解析與分塊

```python
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass
import re
from enum import Enum

class DocumentType(Enum):
    """文件類型"""
    TEXT = "text"
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    DOCX = "docx"


@dataclass
class DocumentChunk:
    """文件塊"""
    chunk_id: str
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    start_char: int
    end_char: int
    chunk_index: int


class DocumentProcessor:
    """
    文件處理器

    ‹1› 解析各種格式的文件
    ‹2› 智慧分塊
    ‹3› 元數據提取
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        ‹1› 初始化

        Args:
            chunk_size: 分塊大小（字元數）
            chunk_overlap: 分塊重疊（字元數）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_document(
        self,
        content: str,
        doc_id: str,
        doc_type: DocumentType = DocumentType.TEXT,
        metadata: Dict[str, Any] = None
    ) -> List[DocumentChunk]:
        """
        ‹2› 處理文件

        Args:
            content: 文件內容
            doc_id: 文件 ID
            doc_type: 文件類型
            metadata: 額外元數據

        Returns:
            分塊列表
        """
        # 預處理
        content = self._preprocess(content, doc_type)

        # 分塊
        chunks = self._chunk_text(content, doc_id, metadata or {})

        return chunks

    def _preprocess(self, content: str, doc_type: DocumentType) -> str:
        """
        ‹3› 預處理文件內容
        """
        # 移除多餘空白
        content = re.sub(r'\s+', ' ', content)

        # 根據文件類型處理
        if doc_type == DocumentType.HTML:
            content = self._strip_html_tags(content)
        elif doc_type == DocumentType.MARKDOWN:
            content = self._strip_markdown(content)

        return content.strip()

    def _strip_html_tags(self, content: str) -> str:
        """移除 HTML 標籤"""
        return re.sub(r'<[^>]+>', '', content)

    def _strip_markdown(self, content: str) -> str:
        """移除 Markdown 格式"""
        # 移除標題標記
        content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
        # 移除粗體/斜體
        content = re.sub(r'\*+([^*]+)\*+', r'\1', content)
        # 移除連結
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        return content

    def _chunk_text(
        self,
        content: str,
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        ‹4› 智慧分塊

        優先在句子邊界分塊
        """
        chunks = []

        # 分句
        sentences = self._split_sentences(content)

        current_chunk = []
        current_length = 0
        start_char = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > self.chunk_size and current_chunk:
                # 創建新塊
                chunk_content = ' '.join(current_chunk)
                chunks.append(DocumentChunk(
                    chunk_id=f"{doc_id}_chunk_{len(chunks)}",
                    doc_id=doc_id,
                    content=chunk_content,
                    metadata=metadata.copy(),
                    start_char=start_char,
                    end_char=start_char + len(chunk_content),
                    chunk_index=len(chunks)
                ))

                # 保留重疊部分
                overlap_text = chunk_content[-self.chunk_overlap:] if self.chunk_overlap > 0 else ""
                current_chunk = [overlap_text] if overlap_text else []
                current_length = len(overlap_text)
                start_char = start_char + len(chunk_content) - len(overlap_text)

            current_chunk.append(sentence)
            current_length += sentence_length + 1

        # 處理最後一塊
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            chunks.append(DocumentChunk(
                chunk_id=f"{doc_id}_chunk_{len(chunks)}",
                doc_id=doc_id,
                content=chunk_content,
                metadata=metadata.copy(),
                start_char=start_char,
                end_char=start_char + len(chunk_content),
                chunk_index=len(chunks)
            ))

        return chunks

    def _split_sentences(self, content: str) -> List[str]:
        """分句"""
        # 簡單的句子分割（可使用更複雜的 NLP 工具）
        sentences = re.split(r'(?<=[。！？.!?])\s*', content)
        return [s.strip() for s in sentences if s.strip()]


def demonstrate_document_processing():
    """
    ‹1› 文件處理示範
    """
    print("文件處理管道示範")
    print("=" * 60)

    processor = DocumentProcessor(chunk_size=200, chunk_overlap=30)

    # 示範文件
    document = """
    向量資料庫是一種專門用於儲存和搜尋高維向量的資料庫系統。
    它在人工智慧和機器學習應用中扮演著關鍵角色。

    向量資料庫的主要特點包括：
    1. 高效的相似性搜尋
    2. 支援大規模向量數據
    3. 提供多種索引演算法

    常見的向量資料庫有 FAISS、Milvus、Pinecone 等。
    這些系統被廣泛應用於語意搜尋、推薦系統、圖片搜尋等場景。
    """

    chunks = processor.process_document(
        content=document,
        doc_id="doc_001",
        doc_type=DocumentType.TEXT,
        metadata={"source": "tutorial", "language": "zh"}
    )

    print(f"原始文件長度: {len(document)} 字元")
    print(f"分塊數量: {len(chunks)}")
    print()

    for chunk in chunks:
        print(f"塊 {chunk.chunk_index}:")
        print(f"  ID: {chunk.chunk_id}")
        print(f"  長度: {len(chunk.content)} 字元")
        print(f"  位置: {chunk.start_char}-{chunk.end_char}")
        print(f"  內容: {chunk.content[:50]}...")
        print()


if __name__ == "__main__":
    demonstrate_document_processing()
```

### 13.2.2 向量生成管道

```python
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
from concurrent.futures import ThreadPoolExecutor
import hashlib

@dataclass
class EmbeddingResult:
    """嵌入結果"""
    text: str
    embedding: np.ndarray
    model: str
    processing_time_ms: float


class EmbeddingPipeline:
    """
    向量生成管道

    ‹1› 批量生成嵌入向量
    ‹2› 支援多模型
    ‹3› 快取優化
    """

    def __init__(
        self,
        model_name: str = "default",
        dimension: int = 768,
        batch_size: int = 32,
        cache_size: int = 10000
    ):
        """
        ‹1› 初始化

        Args:
            model_name: 嵌入模型名稱
            dimension: 向量維度
            batch_size: 批次大小
            cache_size: 快取大小
        """
        self.model_name = model_name
        self.dimension = dimension
        self.batch_size = batch_size

        # 快取
        self.cache: Dict[str, np.ndarray] = {}
        self.cache_size = cache_size

        # 統計
        self.stats = {
            "total_embeddings": 0,
            "cache_hits": 0,
            "total_time_ms": 0
        }

    def embed_text(self, text: str) -> EmbeddingResult:
        """
        ‹2› 生成單個文字的嵌入
        """
        start_time = time.perf_counter()

        # 檢查快取
        cache_key = self._get_cache_key(text)
        if cache_key in self.cache:
            self.stats["cache_hits"] += 1
            embedding = self.cache[cache_key]
        else:
            # 生成嵌入（模擬）
            embedding = self._generate_embedding(text)
            self._update_cache(cache_key, embedding)

        self.stats["total_embeddings"] += 1
        processing_time = (time.perf_counter() - start_time) * 1000
        self.stats["total_time_ms"] += processing_time

        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model_name,
            processing_time_ms=processing_time
        )

    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        ‹3› 批量生成嵌入

        Args:
            texts: 文字列表

        Returns:
            嵌入結果列表
        """
        start_time = time.perf_counter()

        results = []
        uncached_texts = []
        uncached_indices = []

        # 檢查快取
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self.cache:
                self.stats["cache_hits"] += 1
                results.append((i, self.cache[cache_key]))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # 批量生成未快取的嵌入
        if uncached_texts:
            for batch_start in range(0, len(uncached_texts), self.batch_size):
                batch_texts = uncached_texts[batch_start:batch_start + self.batch_size]
                batch_embeddings = self._generate_batch_embedding(batch_texts)

                for j, (text, embedding) in enumerate(zip(batch_texts, batch_embeddings)):
                    idx = uncached_indices[batch_start + j]
                    results.append((idx, embedding))

                    # 更新快取
                    cache_key = self._get_cache_key(text)
                    self._update_cache(cache_key, embedding)

        # 按原始順序排序
        results.sort(key=lambda x: x[0])

        processing_time = (time.perf_counter() - start_time) * 1000
        self.stats["total_embeddings"] += len(texts)
        self.stats["total_time_ms"] += processing_time

        return [
            EmbeddingResult(
                text=texts[i],
                embedding=emb,
                model=self.model_name,
                processing_time_ms=processing_time / len(texts)
            )
            for i, emb in results
        ]

    def _get_cache_key(self, text: str) -> str:
        """生成快取鍵"""
        return hashlib.md5(f"{self.model_name}:{text}".encode()).hexdigest()

    def _update_cache(self, key: str, embedding: np.ndarray):
        """更新快取"""
        if len(self.cache) >= self.cache_size:
            # 簡單的 FIFO 淘汰
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = embedding

    def _generate_embedding(self, text: str) -> np.ndarray:
        """生成嵌入（模擬）"""
        # 實際應使用嵌入模型
        np.random.seed(hash(text) % 2**32)
        embedding = np.random.randn(self.dimension).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def _generate_batch_embedding(self, texts: List[str]) -> List[np.ndarray]:
        """批量生成嵌入（模擬）"""
        return [self._generate_embedding(text) for text in texts]

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計"""
        total = self.stats["total_embeddings"]
        return {
            "total_embeddings": total,
            "cache_hits": self.stats["cache_hits"],
            "cache_hit_rate": self.stats["cache_hits"] / max(total, 1),
            "avg_time_ms": self.stats["total_time_ms"] / max(total, 1),
            "cache_size": len(self.cache)
        }


def demonstrate_embedding_pipeline():
    """
    ‹1› 向量生成管道示範
    """
    print("向量生成管道示範")
    print("=" * 60)

    pipeline = EmbeddingPipeline(
        model_name="text-embedding-model",
        dimension=768,
        batch_size=16,
        cache_size=1000
    )

    # 單個嵌入
    print("\n單個文字嵌入:")
    print("-" * 40)

    text = "向量資料庫是一種專門用於儲存和搜尋向量的系統"
    result = pipeline.embed_text(text)

    print(f"文字: {text}")
    print(f"向量維度: {len(result.embedding)}")
    print(f"處理時間: {result.processing_time_ms:.2f}ms")

    # 批量嵌入
    print("\n批量嵌入（100 個文字）:")
    print("-" * 40)

    texts = [f"這是第 {i} 個測試文字" for i in range(100)]
    start = time.perf_counter()
    results = pipeline.embed_batch(texts)
    elapsed = (time.perf_counter() - start) * 1000

    print(f"總處理時間: {elapsed:.2f}ms")
    print(f"每個文字平均: {elapsed/len(texts):.3f}ms")

    # 快取測試
    print("\n快取效果測試:")
    print("-" * 40)

    # 重複嵌入部分文字
    repeated_texts = texts[:50] + [f"新文字 {i}" for i in range(50)]
    results = pipeline.embed_batch(repeated_texts)

    stats = pipeline.get_stats()
    print(f"快取命中率: {stats['cache_hit_rate']:.2%}")
    print(f"快取大小: {stats['cache_size']}")


if __name__ == "__main__":
    demonstrate_embedding_pipeline()
```

---

## 13.3 混合搜尋引擎

### 13.3.1 語意搜尋與關鍵字搜尋結合

```python
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from collections import Counter
import re
import math

@dataclass
class HybridSearchResult:
    """混合搜尋結果"""
    doc_id: str
    title: str
    content: str
    semantic_score: float
    keyword_score: float
    final_score: float
    match_highlights: List[str]


class BM25Index:
    """
    BM25 關鍵字搜尋索引

    ‹1› 經典的關鍵字搜尋演算法
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        ‹1› 初始化

        Args:
            k1: 詞頻飽和參數
            b: 長度正規化參數
        """
        self.k1 = k1
        self.b = b

        self.documents: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0
        self.inverted_index: Dict[str, List[Tuple[int, int]]] = {}
        self.idf: Dict[str, float] = {}

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        ‹2› 添加文件並建立索引
        """
        self.documents = documents

        # 分詞並建立倒排索引
        for doc_idx, doc in enumerate(documents):
            content = doc.get("content", "") + " " + doc.get("title", "")
            tokens = self._tokenize(content)
            self.doc_lengths.append(len(tokens))

            # 統計詞頻
            term_freqs = Counter(tokens)

            for term, freq in term_freqs.items():
                if term not in self.inverted_index:
                    self.inverted_index[term] = []
                self.inverted_index[term].append((doc_idx, freq))

        # 計算平均文件長度
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)

        # 計算 IDF
        num_docs = len(documents)
        for term, postings in self.inverted_index.items():
            doc_freq = len(postings)
            self.idf[term] = math.log((num_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        ‹3› BM25 搜尋

        Args:
            query: 查詢文字
            top_k: 返回數量

        Returns:
            [(doc_idx, score), ...]
        """
        query_tokens = self._tokenize(query)
        scores = {}

        for term in query_tokens:
            if term not in self.inverted_index:
                continue

            for doc_idx, term_freq in self.inverted_index[term]:
                if doc_idx not in scores:
                    scores[doc_idx] = 0

                # BM25 公式
                doc_length = self.doc_lengths[doc_idx]
                tf = term_freq
                idf = self.idf[term]

                score = idf * (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
                )
                scores[doc_idx] += score

        # 排序並返回 top-k
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        """分詞（簡化版）"""
        # 轉小寫，移除標點，分詞
        text = text.lower()
        tokens = re.findall(r'\w+', text)
        return tokens


class HybridSearchEngine:
    """
    混合搜尋引擎

    ‹1› 結合語意搜尋和關鍵字搜尋
    ‹2› 支援可配置的融合策略
    """

    def __init__(
        self,
        dimension: int = 768,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        """
        ‹1› 初始化

        Args:
            dimension: 向量維度
            semantic_weight: 語意搜尋權重
            keyword_weight: 關鍵字搜尋權重
        """
        self.dimension = dimension
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

        # 索引
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: np.ndarray = None
        self.bm25_index = BM25Index()

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: np.ndarray
    ):
        """
        ‹2› 添加文件和向量
        """
        self.documents = documents

        # 正規化向量
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.embeddings = embeddings / norms

        # 建立 BM25 索引
        self.bm25_index.add_documents(documents)

        print(f"添加了 {len(documents)} 個文件")

    def search(
        self,
        query: str,
        query_embedding: np.ndarray,
        top_k: int = 10,
        semantic_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None
    ) -> List[HybridSearchResult]:
        """
        ‹3› 混合搜尋

        Args:
            query: 查詢文字
            query_embedding: 查詢向量
            top_k: 返回數量
            semantic_weight: 語意搜尋權重（覆蓋默認值）
            keyword_weight: 關鍵字搜尋權重（覆蓋默認值）

        Returns:
            混合搜尋結果
        """
        sw = semantic_weight or self.semantic_weight
        kw = keyword_weight or self.keyword_weight

        # 正規化權重
        total = sw + kw
        sw, kw = sw / total, kw / total

        # 語意搜尋
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        semantic_scores = np.dot(self.embeddings, query_embedding)

        # 關鍵字搜尋
        keyword_results = self.bm25_index.search(query, top_k=len(self.documents))
        keyword_scores = np.zeros(len(self.documents))
        for doc_idx, score in keyword_results:
            keyword_scores[doc_idx] = score

        # 正規化分數
        if semantic_scores.max() > 0:
            semantic_scores = semantic_scores / semantic_scores.max()
        if keyword_scores.max() > 0:
            keyword_scores = keyword_scores / keyword_scores.max()

        # 融合分數
        final_scores = sw * semantic_scores + kw * keyword_scores

        # 獲取 top-k
        top_indices = np.argsort(final_scores)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            doc = self.documents[idx]

            # 生成高亮
            highlights = self._generate_highlights(query, doc.get("content", ""))

            results.append(HybridSearchResult(
                doc_id=doc.get("id", str(idx)),
                title=doc.get("title", ""),
                content=doc.get("content", "")[:200] + "...",
                semantic_score=float(semantic_scores[idx]),
                keyword_score=float(keyword_scores[idx]),
                final_score=float(final_scores[idx]),
                match_highlights=highlights
            ))

        return results

    def _generate_highlights(self, query: str, content: str, context_size: int = 50) -> List[str]:
        """生成高亮片段"""
        highlights = []
        query_terms = set(query.lower().split())

        sentences = content.split('。')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(term in sentence_lower for term in query_terms):
                highlights.append(sentence.strip() + "。")
                if len(highlights) >= 3:
                    break

        return highlights


def demonstrate_hybrid_search():
    """
    ‹1› 混合搜尋示範
    """
    print("混合搜尋引擎示範")
    print("=" * 60)

    # 初始化引擎
    engine = HybridSearchEngine(
        dimension=768,
        semantic_weight=0.7,
        keyword_weight=0.3
    )

    # 準備測試文件
    documents = [
        {
            "id": "1",
            "title": "向量資料庫入門",
            "content": "向量資料庫是一種專門用於儲存和搜尋高維向量的資料庫系統。它在人工智慧應用中扮演關鍵角色。"
        },
        {
            "id": "2",
            "title": "機器學習基礎",
            "content": "機器學習讓電腦能夠從數據中學習，無需明確編程。深度學習是機器學習的重要分支。"
        },
        {
            "id": "3",
            "title": "自然語言處理技術",
            "content": "自然語言處理讓電腦能夠理解和生成人類語言。語意搜尋是 NLP 的重要應用。"
        },
        {
            "id": "4",
            "title": "推薦系統原理",
            "content": "推薦系統根據用戶行為和偏好推薦相關內容。向量相似度是推薦系統的核心技術。"
        },
        {
            "id": "5",
            "title": "FAISS 向量搜尋",
            "content": "FAISS 是 Facebook 開發的高效向量搜尋函式庫。它支援大規模向量的快速相似性搜尋。"
        },
    ]

    # 生成嵌入（模擬）
    np.random.seed(42)
    embeddings = np.random.randn(len(documents), 768).astype(np.float32)

    # 添加文件
    engine.add_documents(documents, embeddings)

    # 執行搜尋
    query = "向量搜尋技術"
    print(f"\n查詢: {query}")
    print("-" * 50)

    # 生成查詢嵌入（模擬）
    np.random.seed(hash(query) % 2**32)
    query_embedding = np.random.randn(768).astype(np.float32)

    results = engine.search(query, query_embedding, top_k=3)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   最終分數: {result.final_score:.4f}")
        print(f"   語意分數: {result.semantic_score:.4f}")
        print(f"   關鍵字分數: {result.keyword_score:.4f}")
        print(f"   內容: {result.content[:80]}...")

    # 不同權重比較
    print("\n\n不同權重比較:")
    print("-" * 50)

    weights = [(0.9, 0.1), (0.7, 0.3), (0.5, 0.5), (0.3, 0.7)]

    for sw, kw in weights:
        results = engine.search(query, query_embedding, top_k=1,
                               semantic_weight=sw, keyword_weight=kw)
        print(f"語意:{sw} 關鍵字:{kw} → 最佳結果: {results[0].title}")


if __name__ == "__main__":
    demonstrate_hybrid_search()
```

---

## 13.4 查詢理解與優化

### 13.4.1 查詢改寫

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class QueryRewriteResult:
    """查詢改寫結果"""
    original_query: str
    rewritten_queries: List[str]
    expansions: List[str]
    intent: str


class QueryUnderstanding:
    """
    查詢理解模組

    ‹1› 查詢意圖識別
    ‹2› 查詢改寫和擴展
    ‹3› 拼寫校正
    """

    def __init__(self):
        # 同義詞詞典（簡化版）
        self.synonyms = {
            "資料庫": ["database", "DB", "數據庫"],
            "向量": ["vector", "嵌入", "embedding"],
            "搜尋": ["search", "查詢", "檢索", "搜索"],
            "機器學習": ["ML", "machine learning", "AI", "人工智慧"],
        }

        # 意圖模板
        self.intent_patterns = {
            "definition": ["什麼是", "定義", "解釋"],
            "howto": ["如何", "怎麼", "怎樣", "方法"],
            "comparison": ["比較", "區別", "差異", "vs"],
            "example": ["範例", "例子", "示範", "案例"],
        }

    def understand_query(self, query: str) -> QueryRewriteResult:
        """
        ‹1› 理解並改寫查詢
        """
        # 識別意圖
        intent = self._identify_intent(query)

        # 查詢改寫
        rewritten = self._rewrite_query(query, intent)

        # 查詢擴展
        expansions = self._expand_query(query)

        return QueryRewriteResult(
            original_query=query,
            rewritten_queries=rewritten,
            expansions=expansions,
            intent=intent
        )

    def _identify_intent(self, query: str) -> str:
        """
        ‹2› 識別查詢意圖
        """
        query_lower = query.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    return intent

        return "general"

    def _rewrite_query(self, query: str, intent: str) -> List[str]:
        """
        ‹3› 改寫查詢

        根據意圖生成不同形式的查詢
        """
        rewrites = [query]

        if intent == "definition":
            # 定義類查詢
            subject = query.replace("什麼是", "").replace("的定義", "").strip()
            rewrites.append(f"{subject} 介紹")
            rewrites.append(f"{subject} 概念")

        elif intent == "howto":
            # 方法類查詢
            rewrites.append(query.replace("如何", "方法"))
            rewrites.append(query.replace("如何", "步驟"))

        elif intent == "comparison":
            # 比較類查詢
            rewrites.append(query.replace("比較", "區別"))
            rewrites.append(query.replace("比較", "對比"))

        return rewrites

    def _expand_query(self, query: str) -> List[str]:
        """
        ‹4› 擴展查詢

        添加同義詞
        """
        expansions = []

        for term, synonyms in self.synonyms.items():
            if term in query:
                for syn in synonyms:
                    expanded = query.replace(term, syn)
                    if expanded not in expansions:
                        expansions.append(expanded)

        return expansions[:5]  # 限制數量


def demonstrate_query_understanding():
    """
    ‹1› 查詢理解示範
    """
    print("查詢理解示範")
    print("=" * 60)

    qu = QueryUnderstanding()

    queries = [
        "什麼是向量資料庫",
        "如何使用 FAISS 進行搜尋",
        "向量資料庫和傳統資料庫的比較",
        "機器學習入門範例",
    ]

    for query in queries:
        print(f"\n原始查詢: {query}")
        print("-" * 40)

        result = qu.understand_query(query)

        print(f"識別意圖: {result.intent}")
        print(f"改寫查詢:")
        for r in result.rewritten_queries:
            print(f"  - {r}")
        if result.expansions:
            print(f"擴展查詢:")
            for e in result.expansions:
                print(f"  - {e}")


if __name__ == "__main__":
    demonstrate_query_understanding()
```

---

## 13.5 完整系統實作

### 13.5.1 企業級語意搜尋引擎

```python
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
from datetime import datetime

@dataclass
class SearchConfig:
    """搜尋配置"""
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    top_k: int = 10
    min_score: float = 0.3
    enable_reranking: bool = True
    enable_query_expansion: bool = True


@dataclass
class SearchResponse:
    """搜尋響應"""
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    search_time_ms: float
    query_understanding: Dict[str, Any]


class EnterpriseSearchEngine:
    """
    企業級語意搜尋引擎

    ‹1› 完整的搜尋功能
    ‹2› 效能監控
    ‹3› 可配置的搜尋策略
    """

    def __init__(self, config: SearchConfig = None):
        """
        ‹1› 初始化
        """
        self.config = config or SearchConfig()

        # 文件存儲
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.embeddings: Dict[str, np.ndarray] = {}

        # 索引
        self.vector_index: np.ndarray = None
        self.doc_ids: List[str] = []

        # 統計
        self.stats = {
            "total_searches": 0,
            "total_time_ms": 0,
            "avg_results": 0
        }

    def index_documents(self, documents: List[Dict[str, Any]]):
        """
        ‹2› 索引文件
        """
        print(f"索引 {len(documents)} 個文件...")

        for doc in documents:
            doc_id = doc["id"]
            self.documents[doc_id] = doc

            # 生成嵌入（模擬）
            np.random.seed(hash(doc.get("content", "")) % 2**32)
            embedding = np.random.randn(768).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            self.embeddings[doc_id] = embedding

        # 建立向量索引
        self.doc_ids = list(self.embeddings.keys())
        self.vector_index = np.array([self.embeddings[did] for did in self.doc_ids])

        print(f"索引完成，共 {len(self.documents)} 個文件")

    def search(
        self,
        query: str,
        config: Optional[SearchConfig] = None
    ) -> SearchResponse:
        """
        ‹3› 執行搜尋
        """
        start_time = time.perf_counter()
        cfg = config or self.config

        # 查詢理解
        query_understanding = self._understand_query(query)

        # 生成查詢向量
        queries_to_search = [query]
        if cfg.enable_query_expansion and query_understanding.get("expansions"):
            queries_to_search.extend(query_understanding["expansions"][:2])

        # 執行向量搜尋
        all_results = []
        for q in queries_to_search:
            results = self._vector_search(q, cfg.top_k * 2)
            all_results.extend(results)

        # 去重和融合
        merged_results = self._merge_results(all_results)

        # 過濾低分結果
        filtered_results = [r for r in merged_results if r["score"] >= cfg.min_score]

        # 重排序
        if cfg.enable_reranking:
            filtered_results = self._rerank(query, filtered_results)

        # 取 top-k
        final_results = filtered_results[:cfg.top_k]

        # 更新統計
        search_time = (time.perf_counter() - start_time) * 1000
        self._update_stats(search_time, len(final_results))

        return SearchResponse(
            query=query,
            results=final_results,
            total_results=len(filtered_results),
            search_time_ms=search_time,
            query_understanding=query_understanding
        )

    def _understand_query(self, query: str) -> Dict[str, Any]:
        """查詢理解"""
        return {
            "original": query,
            "intent": "general",
            "expansions": [],
            "entities": []
        }

    def _vector_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """向量搜尋"""
        # 生成查詢向量
        np.random.seed(hash(query) % 2**32)
        query_vector = np.random.randn(768).astype(np.float32)
        query_vector = query_vector / np.linalg.norm(query_vector)

        # 計算相似度
        similarities = np.dot(self.vector_index, query_vector)

        # 獲取 top-k
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            doc_id = self.doc_ids[idx]
            doc = self.documents[doc_id]
            results.append({
                "id": doc_id,
                "title": doc.get("title", ""),
                "content": doc.get("content", "")[:300],
                "score": float(similarities[idx]),
                "metadata": doc.get("metadata", {})
            })

        return results

    def _merge_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合併和去重結果"""
        seen = {}
        for r in results:
            doc_id = r["id"]
            if doc_id not in seen or r["score"] > seen[doc_id]["score"]:
                seen[doc_id] = r

        merged = list(seen.values())
        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged

    def _rerank(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """重排序（簡化版）"""
        # 實際應用中可使用 cross-encoder 模型
        return results

    def _update_stats(self, time_ms: float, num_results: int):
        """更新統計"""
        self.stats["total_searches"] += 1
        self.stats["total_time_ms"] += time_ms
        n = self.stats["total_searches"]
        self.stats["avg_results"] = (
            (self.stats["avg_results"] * (n - 1) + num_results) / n
        )

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計"""
        n = self.stats["total_searches"]
        return {
            "total_searches": n,
            "avg_time_ms": self.stats["total_time_ms"] / max(n, 1),
            "avg_results": self.stats["avg_results"]
        }


def demonstrate_enterprise_search():
    """
    ‹1› 企業級搜尋引擎示範
    """
    print("企業級語意搜尋引擎示範")
    print("=" * 60)

    # 初始化引擎
    config = SearchConfig(
        semantic_weight=0.7,
        keyword_weight=0.3,
        top_k=5,
        min_score=0.2,
        enable_reranking=True
    )
    engine = EnterpriseSearchEngine(config)

    # 準備測試文件
    documents = [
        {"id": "1", "title": "向量資料庫入門指南", "content": "向量資料庫是一種專門用於儲存和搜尋高維向量的資料庫系統..."},
        {"id": "2", "title": "FAISS 使用教程", "content": "FAISS 是 Facebook 開發的高效向量搜尋函式庫..."},
        {"id": "3", "title": "語意搜尋技術原理", "content": "語意搜尋通過理解查詢的含義來找到相關文件..."},
        {"id": "4", "title": "機器學習在搜尋中的應用", "content": "現代搜尋引擎大量使用機器學習技術提升搜尋品質..."},
        {"id": "5", "title": "企業知識管理系統", "content": "企業知識管理系統幫助組織儲存和檢索知識資產..."},
        {"id": "6", "title": "自然語言處理基礎", "content": "NLP 技術讓電腦能夠理解和處理人類語言..."},
        {"id": "7", "title": "推薦系統設計", "content": "推薦系統根據用戶行為和偏好推薦相關內容..."},
        {"id": "8", "title": "搜尋相關性優化", "content": "搜尋相關性是衡量搜尋結果品質的關鍵指標..."},
    ]

    # 索引文件
    engine.index_documents(documents)

    # 執行搜尋
    queries = [
        "如何使用向量搜尋",
        "什麼是語意搜尋",
        "企業知識管理",
    ]

    for query in queries:
        print(f"\n查詢: {query}")
        print("-" * 50)

        response = engine.search(query)

        print(f"搜尋耗時: {response.search_time_ms:.2f}ms")
        print(f"結果數量: {response.total_results}")
        print("\n搜尋結果:")

        for i, result in enumerate(response.results[:3], 1):
            print(f"  {i}. {result['title']}")
            print(f"     分數: {result['score']:.4f}")
            print(f"     內容: {result['content'][:60]}...")

    # 統計
    print("\n\n系統統計:")
    print("-" * 30)
    stats = engine.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    demonstrate_enterprise_search()
```

---

## 13.6 本章回顧

### 核心要點

1. **語意搜尋原理**
   - 向量相似度代替關鍵字匹配
   - 理解查詢意圖
   - 找到語意相關的內容

2. **文件處理**
   - 智慧分塊
   - 向量生成管道
   - 批量處理優化

3. **混合搜尋**
   - 語意 + 關鍵字結合
   - 可配置的融合權重
   - 結果重排序

4. **查詢理解**
   - 意圖識別
   - 查詢改寫
   - 查詢擴展

5. **企業級系統**
   - 可配置的搜尋策略
   - 效能監控
   - 擴展性設計

### 最佳實踐

- 使用混合搜尋提高召回和精確度
- 適當的分塊大小（300-500 字元）
- 實施查詢理解提升用戶體驗
- 持續監控和優化搜尋品質

---

## 思考題

1. 如何處理多語言的語意搜尋？需要考慮哪些因素？

2. 在搜尋結果中，如何平衡相關性和多樣性？

3. 如何設計一個能夠從用戶反饋中學習的搜尋系統？

4. 對於非常長的文件，應該如何設計分塊策略？

5. 在企業環境中，如何確保搜尋系統的安全性和權限控制？

---

## 全書總結

恭喜你完成了《向量資料庫實戰》的學習！

在本書中，我們從向量資料庫的基礎概念開始，深入探討了：

- **理論基礎**：向量空間、相似性度量、嵌入技術
- **核心演算法**：HNSW、LSH、IVF、PQ 等索引結構
- **工具實踐**：FAISS、Milvus 的使用方法
- **系統設計**：架構設計、效能優化、監控告警
- **實戰案例**：自動駕駛感知、語意搜尋引擎

向量資料庫技術正在快速發展，它是 AI 應用的關鍵基礎設施。希望本書能幫助你在這個領域建立堅實的基礎，並在實際專案中發揮作用。

繼續學習，持續實踐，祝你在向量資料庫的旅程中取得成功！
