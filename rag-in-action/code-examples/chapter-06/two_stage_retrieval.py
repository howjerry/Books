"""
chapter-06/two_stage_retrieval.py

二階段檢索系統

本模組實作完整的二階段檢索 Pipeline：
1. 第一階段：使用 Bi-Encoder 快速召回 Top-N 候選文件
2. 第二階段：使用 Cross-Encoder 對候選文件精確排序

使用方式：
    from two_stage_retrieval import TwoStageRetriever
    retriever = TwoStageRetriever()
    results = retriever.search(query)

依賴安裝：
    pip install sentence-transformers qdrant-client rich
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import time
import uuid

from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from rich.console import Console
from rich.panel import Panel

console = Console()


@dataclass
class RetrievalResult:
    """檢索結果"""
    doc_id: str
    content: str
    stage1_score: float
    stage2_score: float
    final_rank: int
    metadata: Dict = field(default_factory=dict)


@dataclass
class SearchResponse:
    """搜尋回應"""
    query: str
    results: List[RetrievalResult]
    stage1_time_ms: float
    stage2_time_ms: float
    total_time_ms: float
    stage1_candidates: int
    final_results: int


class TwoStageRetriever:
    """
    二階段檢索器

    結合 Bi-Encoder 的速度優勢和 Cross-Encoder 的精準度優勢。

    Architecture:
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Query     │ ──► │ Bi-Encoder  │ ──► │ Cross-Enc   │
    │             │     │ Top-50 快速 │     │ Top-5 精確  │
    └─────────────┘     └─────────────┘     └─────────────┘
                              │                   │
                              ▼                   ▼
                        候選文件 50 個      最終結果 5 個
                        延遲 ~10ms         延遲 ~50ms
    """

    def __init__(
        self,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
        rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        collection_name: str = "two_stage_kb",
        stage1_top_n: int = 50,                                         # ‹1›
        stage2_top_k: int = 5                                           # ‹2›
    ):
        """
        初始化二階段檢索器

        Args:
            embedding_model: 第一階段使用的 Embedding 模型
            rerank_model: 第二階段使用的 Re-Ranker 模型
            collection_name: 向量資料庫集合名稱
            stage1_top_n: 第一階段召回的候選數量
            stage2_top_k: 最終返回的結果數量
        """
        console.print("[bold blue]初始化二階段檢索器[/bold blue]\n")

        self.stage1_top_n = stage1_top_n
        self.stage2_top_k = stage2_top_k
        self.collection_name = collection_name

        # 第一階段：Bi-Encoder
        console.print("載入 Bi-Encoder (Stage 1)...")
        self.bi_encoder = SentenceTransformer(embedding_model)
        self.embedding_dim = self.bi_encoder.get_sentence_embedding_dimension()
        console.print(f"  ✓ {embedding_model}")

        # 第二階段：Cross-Encoder
        console.print("載入 Cross-Encoder (Stage 2)...")
        self.cross_encoder = CrossEncoder(rerank_model)
        console.print(f"  ✓ {rerank_model}")

        # 向量資料庫
        console.print("初始化向量資料庫...")
        self.vector_db = QdrantClient(":memory:")
        self._init_collection()
        console.print("  ✓ Qdrant (記憶體模式)")

        console.print("\n[green]✓ 二階段檢索器就緒[/green]\n")

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

        Args:
            documents: 文件列表
            metadata_list: 元資料列表

        Returns:
            索引的文件數量
        """
        if metadata_list is None:
            metadata_list = [{}] * len(documents)

        console.print(f"索引 {len(documents)} 份文件...")

        # 編碼文件
        embeddings = self.bi_encoder.encode(
            documents,
            show_progress_bar=True
        )

        # 上傳到向量資料庫
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding.tolist(),
                payload={"content": doc, **meta}
            )
            for doc, embedding, meta in zip(documents, embeddings, metadata_list)
        ]

        self.vector_db.upsert(
            collection_name=self.collection_name,
            points=points
        )

        console.print(f"[green]✓ 索引完成[/green]")
        return len(documents)

    def search(
        self,
        query: str,
        stage1_top_n: int = None,
        stage2_top_k: int = None
    ) -> SearchResponse:
        """
        執行二階段檢索

        Args:
            query: 使用者查詢
            stage1_top_n: 第一階段召回數量（覆蓋預設值）
            stage2_top_k: 最終返回數量（覆蓋預設值）

        Returns:
            SearchResponse 搜尋結果
        """
        stage1_top_n = stage1_top_n or self.stage1_top_n
        stage2_top_k = stage2_top_k or self.stage2_top_k

        total_start = time.time()

        # ═══ 第一階段：Bi-Encoder 快速召回 ═══
        stage1_start = time.time()

        query_embedding = self.bi_encoder.encode(query).tolist()        # ‹3›

        stage1_results = self.vector_db.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=stage1_top_n
        )

        stage1_time = (time.time() - stage1_start) * 1000

        if not stage1_results:
            return SearchResponse(
                query=query,
                results=[],
                stage1_time_ms=stage1_time,
                stage2_time_ms=0,
                total_time_ms=(time.time() - total_start) * 1000,
                stage1_candidates=0,
                final_results=0
            )

        # ═══ 第二階段：Cross-Encoder 精確排序 ═══
        stage2_start = time.time()

        # 準備 query-document pairs
        pairs = [
            [query, r.payload.get("content", "")]
            for r in stage1_results
        ]

        # Cross-Encoder 打分
        cross_scores = self.cross_encoder.predict(pairs)                # ‹4›

        # 結合結果
        combined = []
        for r, cross_score in zip(stage1_results, cross_scores):
            combined.append({
                "doc_id": str(r.id),
                "content": r.payload.get("content", ""),
                "stage1_score": r.score,
                "stage2_score": float(cross_score),
                "metadata": {k: v for k, v in r.payload.items() if k != "content"}
            })

        # 按 Cross-Encoder 分數排序
        combined.sort(key=lambda x: x["stage2_score"], reverse=True)    # ‹5›

        stage2_time = (time.time() - stage2_start) * 1000

        # 取 Top-K 最終結果
        final_results = [
            RetrievalResult(
                doc_id=item["doc_id"],
                content=item["content"],
                stage1_score=item["stage1_score"],
                stage2_score=item["stage2_score"],
                final_rank=i + 1,
                metadata=item["metadata"]
            )
            for i, item in enumerate(combined[:stage2_top_k])
        ]

        total_time = (time.time() - total_start) * 1000

        return SearchResponse(
            query=query,
            results=final_results,
            stage1_time_ms=stage1_time,
            stage2_time_ms=stage2_time,
            total_time_ms=total_time,
            stage1_candidates=len(stage1_results),
            final_results=len(final_results)
        )


def display_search_response(response: SearchResponse) -> None:
    """美化顯示搜尋結果"""
    console.print(Panel(
        f"[bold]查詢：{response.query}[/bold]\n\n"
        f"第一階段候選：{response.stage1_candidates} 份 ({response.stage1_time_ms:.1f}ms)\n"
        f"最終結果：{response.final_results} 份 ({response.stage2_time_ms:.1f}ms)\n"
        f"總耗時：{response.total_time_ms:.1f}ms",
        title="二階段檢索結果",
        border_style="blue"
    ))

    for r in response.results:
        score_color = "green" if r.stage2_score > 0.5 else "yellow" if r.stage2_score > 0 else "red"
        console.print(f"\n[bold]#{r.final_rank}[/bold]")
        console.print(f"  Stage1 分數: {r.stage1_score:.4f}")
        console.print(f"  Stage2 分數: [{score_color}]{r.stage2_score:.4f}[/{score_color}]")
        console.print(f"  內容: {r.content[:80]}...")


def main():
    """演示二階段檢索"""
    console.print("\n[bold]═══ 二階段檢索演示 ═══[/bold]\n")

    # 建立檢索器
    retriever = TwoStageRetriever(
        stage1_top_n=10,
        stage2_top_k=3
    )

    # 索引知識庫
    documents = [
        "如何重設密碼？請點擊登入頁面的「忘記密碼」連結，輸入您的電子郵件地址，系統將寄送重設連結。",
        "密碼重設連結有效期為 24 小時。如果連結過期，請重新申請。",
        "忘記密碼時，請確認您使用的電子郵件地址正確，並檢查垃圾郵件資料夾。",
        "如何變更電子郵件地址？請登入後進入「帳戶設定」>「個人資料」，即可修改電子郵件。",
        "如何啟用雙重驗證（2FA）？進入「帳戶設定」>「安全性」，點擊「啟用雙重驗證」。",
        "支援哪些付款方式？我們支援信用卡（Visa、MasterCard）、銀行轉帳、PayPal。",
        "如何取消訂閱？進入「訂閱管理」>「取消訂閱」。取消後仍可使用至當期結束。",
        "API 請求頻率限制？免費版每分鐘 60 次，專業版 600 次。",
        "如何聯繫客服？Email: support@techcorp.com 或線上客服（週一至週五）。",
        "資料存放在哪裡？所有資料儲存在 AWS 東京區域，符合 ISO 27001 認證。",
    ]

    retriever.index_documents(documents)

    # 測試查詢
    test_queries = [
        "密碼忘記了怎麼辦",
        "2FA 怎麼設定",
        "怎麼聯繫你們",
    ]

    for query in test_queries:
        response = retriever.search(query)
        display_search_response(response)
        console.print("\n" + "─" * 60 + "\n")


if __name__ == "__main__":
    main()
