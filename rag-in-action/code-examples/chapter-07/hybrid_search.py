"""
chapter-07/hybrid_search.py

混合檢索系統

本模組實作 BM25 + Vector Search 的混合檢索引擎，
結合關鍵字精確匹配和語義相似搜尋的優點。

使用方式：
    from hybrid_search import HybridSearchEngine
    engine = HybridSearchEngine()
    results = engine.search(query)

依賴安裝：
    pip install sentence-transformers qdrant-client rank-bm25 jieba rich
"""

from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
import time
import uuid
import re

import jieba
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from score_normalization import ScoreNormalizer, ScoreFuser, FusedResult

console = Console()


@dataclass
class HybridSearchResult:
    """混合搜尋結果"""
    query: str
    results: List[FusedResult]
    bm25_time_ms: float
    vector_time_ms: float
    fusion_time_ms: float
    total_time_ms: float
    bm25_candidates: int
    vector_candidates: int
    final_results: int
    alpha: float


class HybridSearchEngine:
    """
    混合檢索引擎

    結合 BM25 關鍵字搜尋和向量語義搜尋的優點：
    - BM25：精確匹配專有名詞、產品代碼、錯誤代碼
    - Vector：理解語義相似性、同義詞、意圖

    Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                     Hybrid Search 架構                          │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  使用者查詢                                                      │
    │      │                                                          │
    │      ├──────────────────┬──────────────────┐                   │
    │      ▼                  ▼                  │                   │
    │  ┌────────────┐    ┌────────────┐          │                   │
    │  │   BM25     │    │   Vector   │          │                   │
    │  │  關鍵字     │    │   語義     │          │                   │
    │  │  Top-50    │    │   Top-50   │          │                   │
    │  └────────────┘    └────────────┘          │                   │
    │      │                  │                  │                   │
    │      └────────┬─────────┘                  │                   │
    │               ▼                            │                   │
    │       ┌────────────────┐                   │                   │
    │       │  Score Fusion  │                   │                   │
    │       │ α*BM25 + β*Vec │                   │                   │
    │       └────────────────┘                   │                   │
    │               │                            │                   │
    │               ▼                            │                   │
    │         最終結果 Top-K                      │                   │
    │                                            │                   │
    └─────────────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
        collection_name: str = "hybrid_search_kb",
        default_alpha: float = 0.5,
        tokenizer: Callable[[str], List[str]] = None
    ):
        """
        初始化混合檢索引擎

        Args:
            embedding_model: Embedding 模型名稱
            collection_name: Qdrant 集合名稱
            default_alpha: 預設 BM25 權重 (0-1)
            tokenizer: 自訂分詞器，預設使用 jieba
        """
        console.print("[bold blue]初始化混合檢索引擎[/bold blue]\n")

        self.collection_name = collection_name
        self.default_alpha = default_alpha

        # 分詞器（中文使用 jieba）
        self.tokenizer = tokenizer or self._default_tokenizer
        console.print("分詞器: jieba")

        # 載入 Embedding 模型
        console.print(f"載入 Embedding 模型: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        console.print(f"  ✓ 維度: {self.embedding_dim}")

        # 初始化向量資料庫
        console.print("初始化向量資料庫...")
        self.vector_db = QdrantClient(":memory:")
        self._init_collection()
        console.print("  ✓ Qdrant (記憶體模式)")

        # BM25 索引（將在索引文件時建立）
        self.bm25_index = None
        self.documents = []
        self.doc_ids = []
        self.doc_metadata = []

        # 分數融合器
        self.fuser = ScoreFuser()

        console.print("\n[green]✓ 混合檢索引擎就緒[/green]\n")

    def _default_tokenizer(self, text: str) -> List[str]:
        """
        預設分詞器（jieba）

        Args:
            text: 輸入文本

        Returns:
            分詞結果列表
        """
        # 使用 jieba 分詞，過濾空白和標點
        tokens = jieba.lcut(text)
        # 過濾停用詞和單字元
        tokens = [t.strip() for t in tokens if len(t.strip()) > 1]
        return tokens                                                      # ‹1›

    def _init_collection(self) -> None:
        """初始化向量集合"""
        collections = self.vector_db.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.vector_db.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )

    def index_documents(
        self,
        documents: List[str],
        metadata_list: Optional[List[Dict]] = None
    ) -> int:
        """
        索引文件

        同時建立 BM25 索引和向量索引。

        Args:
            documents: 文件列表
            metadata_list: 元資料列表

        Returns:
            索引的文件數量
        """
        if metadata_list is None:
            metadata_list = [{}] * len(documents)

        console.print(f"索引 {len(documents)} 份文件...")

        # 儲存文件
        self.documents = documents
        self.doc_ids = [str(uuid.uuid4()) for _ in documents]
        self.doc_metadata = metadata_list

        # 建立 BM25 索引
        console.print("  建立 BM25 索引...")
        tokenized_docs = [self.tokenizer(doc) for doc in documents]
        self.bm25_index = BM25Okapi(tokenized_docs)                         # ‹2›

        # 建立向量索引
        console.print("  建立向量索引...")
        embeddings = self.embedding_model.encode(
            documents,
            show_progress_bar=True
        )

        points = [
            PointStruct(
                id=doc_id,
                vector=embedding.tolist(),
                payload={"content": doc, "index": i, **meta}
            )
            for i, (doc_id, doc, embedding, meta) in enumerate(
                zip(self.doc_ids, documents, embeddings, metadata_list)
            )
        ]

        self.vector_db.upsert(
            collection_name=self.collection_name,
            points=points
        )

        console.print(f"[green]✓ 索引完成[/green]")
        return len(documents)

    def _bm25_search(self, query: str, top_k: int = 50) -> List[Dict]:
        """
        BM25 關鍵字搜尋

        Args:
            query: 查詢字串
            top_k: 返回數量

        Returns:
            搜尋結果列表
        """
        if self.bm25_index is None:
            return []

        tokenized_query = self.tokenizer(query)
        scores = self.bm25_index.get_scores(tokenized_query)               # ‹3›

        # 取得 top_k 結果
        top_indices = scores.argsort()[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # 只返回有分數的結果
                results.append({
                    "id": self.doc_ids[idx],
                    "content": self.documents[idx],
                    "score": float(scores[idx]),
                    "metadata": self.doc_metadata[idx]
                })

        return results

    def _vector_search(self, query: str, top_k: int = 50) -> List[Dict]:
        """
        向量語義搜尋

        Args:
            query: 查詢字串
            top_k: 返回數量

        Returns:
            搜尋結果列表
        """
        query_embedding = self.embedding_model.encode(query).tolist()

        results = self.vector_db.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k
        )                                                                  # ‹4›

        return [
            {
                "id": str(r.id),
                "content": r.payload.get("content", ""),
                "score": r.score,
                "metadata": {k: v for k, v in r.payload.items() if k != "content"}
            }
            for r in results
        ]

    def search(
        self,
        query: str,
        alpha: float = None,
        top_k: int = 10,
        bm25_candidates: int = 50,
        vector_candidates: int = 50,
        fusion_method: str = "weighted_sum"
    ) -> HybridSearchResult:
        """
        執行混合搜尋

        Args:
            query: 使用者查詢
            alpha: BM25 權重 (0-1)，None 使用預設值
            top_k: 最終返回數量
            bm25_candidates: BM25 召回候選數
            vector_candidates: 向量召回候選數
            fusion_method: 融合方法 ("weighted_sum" 或 "rrf")

        Returns:
            HybridSearchResult 搜尋結果
        """
        alpha = alpha if alpha is not None else self.default_alpha
        total_start = time.time()

        # BM25 搜尋
        bm25_start = time.time()
        bm25_results = self._bm25_search(query, bm25_candidates)
        bm25_time = (time.time() - bm25_start) * 1000

        # 向量搜尋
        vector_start = time.time()
        vector_results = self._vector_search(query, vector_candidates)
        vector_time = (time.time() - vector_start) * 1000

        # 分數融合
        fusion_start = time.time()
        if fusion_method == "rrf":
            fused_results = self.fuser.reciprocal_rank_fusion(
                bm25_results,
                vector_results,
                top_k=top_k
            )
        else:
            fused_results = self.fuser.weighted_sum_fusion(               # ‹5›
                bm25_results,
                vector_results,
                alpha=alpha,
                top_k=top_k
            )
        fusion_time = (time.time() - fusion_start) * 1000

        total_time = (time.time() - total_start) * 1000

        return HybridSearchResult(
            query=query,
            results=fused_results,
            bm25_time_ms=bm25_time,
            vector_time_ms=vector_time,
            fusion_time_ms=fusion_time,
            total_time_ms=total_time,
            bm25_candidates=len(bm25_results),
            vector_candidates=len(vector_results),
            final_results=len(fused_results),
            alpha=alpha
        )


def display_hybrid_result(result: HybridSearchResult) -> None:
    """美化顯示混合搜尋結果"""
    console.print(Panel(
        f"[bold]查詢：{result.query}[/bold]\n\n"
        f"Alpha (BM25 權重): {result.alpha:.2f}\n"
        f"BM25 候選: {result.bm25_candidates} ({result.bm25_time_ms:.1f}ms)\n"
        f"向量候選: {result.vector_candidates} ({result.vector_time_ms:.1f}ms)\n"
        f"最終結果: {result.final_results} 份\n"
        f"總耗時: {result.total_time_ms:.1f}ms",
        title="混合搜尋結果",
        border_style="blue"
    ))

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", width=3, justify="center")
    table.add_column("BM25 排名", width=10, justify="center")
    table.add_column("向量排名", width=10, justify="center")
    table.add_column("融合分數", width=10, justify="right")
    table.add_column("內容預覽", width=45)

    for r in result.results[:5]:
        bm25_rank = str(r.bm25_rank) if r.bm25_rank <= result.bm25_candidates else "-"
        vector_rank = str(r.vector_rank) if r.vector_rank <= result.vector_candidates else "-"
        preview = r.content[:40].replace('\n', ' ') + "..."

        table.add_row(
            str(r.final_rank),
            bm25_rank,
            vector_rank,
            f"{r.fused_score:.4f}",
            preview
        )

    console.print(table)


def demo_hybrid_vs_pure():
    """演示混合搜尋 vs 純向量搜尋的差異"""
    console.print("\n[bold]═══ 混合搜尋 vs 純語義搜尋 對比演示 ═══[/bold]\n")

    # 建立引擎
    engine = HybridSearchEngine()

    # 測試資料（包含專有名詞和產品代碼）
    documents = [
        "如何重設密碼？請點擊登入頁面的「忘記密碼」連結。",
        "錯誤代碼 E001：連線逾時，請檢查網路設定。",
        "錯誤代碼 E002：認證失敗，請確認帳號密碼。",
        "錯誤代碼 E003：權限不足，請聯繫管理員。",
        "產品型號 AX-2024-PRO 的規格：8 核心、32GB 記憶體。",
        "產品型號 AX-2024-LITE 的規格：4 核心、16GB 記憶體。",
        "如何聯繫客服？Email: support@example.com。",
        "API 文件請參考 https://docs.example.com/api/v2。",
        "密碼忘記的話，可以透過驗證碼重新設定新密碼。",
        "當系統出現異常時，請記錄錯誤訊息並回報。",
    ]

    engine.index_documents(documents)

    # 測試案例
    test_cases = [
        {
            "query": "E002 錯誤",
            "description": "精確匹配錯誤代碼"
        },
        {
            "query": "AX-2024-PRO 規格",
            "description": "精確匹配產品型號"
        },
        {
            "query": "密碼忘記怎麼辦",
            "description": "語義理解查詢"
        },
    ]

    for case in test_cases:
        console.print(f"\n[yellow]測試案例：{case['description']}[/yellow]")
        console.print(f"查詢：{case['query']}\n")

        # 純向量搜尋 (alpha=0)
        console.print("[dim]--- 純向量搜尋 (alpha=0) ---[/dim]")
        result_vector = engine.search(case["query"], alpha=0, top_k=3)
        for r in result_vector.results:
            console.print(f"  {r.final_rank}. [{r.fused_score:.3f}] {r.content[:50]}...")

        # 純 BM25 搜尋 (alpha=1)
        console.print("\n[dim]--- 純 BM25 搜尋 (alpha=1) ---[/dim]")
        result_bm25 = engine.search(case["query"], alpha=1, top_k=3)
        for r in result_bm25.results:
            console.print(f"  {r.final_rank}. [{r.fused_score:.3f}] {r.content[:50]}...")

        # 混合搜尋 (alpha=0.5)
        console.print("\n[dim]--- 混合搜尋 (alpha=0.5) ---[/dim]")
        result_hybrid = engine.search(case["query"], alpha=0.5, top_k=3)
        for r in result_hybrid.results:
            console.print(f"  {r.final_rank}. [{r.fused_score:.3f}] {r.content[:50]}...")

        console.print("\n" + "─" * 60)


def main():
    """主函數"""
    demo_hybrid_vs_pure()


if __name__ == "__main__":
    main()
