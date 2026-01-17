"""
chapter-06/reranker.py

Re-Ranking Pipeline 實作

本模組實作基於 Cross-Encoder 的 Re-Ranking 功能，
用於對初步檢索結果進行二次排序，提升檢索精準度。

Re-Ranking 原理：
1. 第一階段：使用 Bi-Encoder（Embedding）快速召回候選文件
2. 第二階段：使用 Cross-Encoder 對候選文件進行精確排序

使用方式：
    from reranker import CrossEncoderReranker
    reranker = CrossEncoderReranker()
    reranked = reranker.rerank(query, candidates)

依賴安裝：
    pip install sentence-transformers torch rich
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import time

import torch
from sentence_transformers import CrossEncoder
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class RerankCandidate:
    """Re-Ranking 候選文件"""
    doc_id: str
    content: str
    initial_score: float = 0.0
    rerank_score: float = 0.0
    initial_rank: int = 0
    final_rank: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class RerankResult:
    """Re-Ranking 結果"""
    query: str
    candidates: List[RerankCandidate]
    rerank_time_ms: float
    model_name: str


class CrossEncoderReranker:
    """
    Cross-Encoder Re-Ranker

    使用 Cross-Encoder 模型對候選文件進行重新排序。
    Cross-Encoder 將 query 和 document 一起輸入模型，
    能夠捕捉更細緻的語義關係。

    Attributes:
        model: Cross-Encoder 模型
        model_name: 模型名稱
        max_length: 最大輸入長度
    """

    # 預設的 Cross-Encoder 模型選項
    MODELS = {
        "ms-marco-MiniLM": "cross-encoder/ms-marco-MiniLM-L-6-v2",       # 輕量快速
        "ms-marco-MiniLM-L12": "cross-encoder/ms-marco-MiniLM-L-12-v2", # 更高精度
        "bge-reranker-base": "BAAI/bge-reranker-base",                  # 中文支援
        "bge-reranker-large": "BAAI/bge-reranker-large",                # 中文最佳
        "mxbai-rerank": "mixedbread-ai/mxbai-rerank-xsmall-v1",        # 多語言
    }

    def __init__(
        self,
        model_name: str = "bge-reranker-base",
        max_length: int = 512,
        device: str = None
    ):
        """
        初始化 Re-Ranker

        Args:
            model_name: 模型名稱（可以是預設名稱或 HuggingFace 模型 ID）
            max_length: 最大輸入長度
            device: 執行設備（'cuda' 或 'cpu'）
        """
        self.model_name = model_name
        self.max_length = max_length

        # 解析模型名稱
        model_id = self.MODELS.get(model_name, model_name)

        # 設定設備
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        console.print(f"載入 Re-Ranker 模型: {model_id}...")
        self.model = CrossEncoder(
            model_id,
            max_length=max_length,
            device=device
        )                                                               # ‹1›
        console.print(f"[green]✓ Re-Ranker 就緒 (device: {device})[/green]")

    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = None
    ) -> RerankResult:
        """
        對候選文件進行重新排序

        Args:
            query: 使用者查詢
            candidates: 候選文件列表，每個文件需包含 'content' 欄位
            top_k: 返回前 k 個結果（預設返回全部）

        Returns:
            RerankResult 排序結果
        """
        if not candidates:
            return RerankResult(
                query=query,
                candidates=[],
                rerank_time_ms=0,
                model_name=self.model_name
            )

        start_time = time.time()

        # 準備輸入對
        pairs = [
            [query, c.get("content", c.get("text", ""))]
            for c in candidates
        ]                                                               # ‹2›

        # 計算相關性分數
        scores = self.model.predict(pairs)                              # ‹3›

        # 建立結果
        rerank_candidates = []
        for i, (candidate, score) in enumerate(zip(candidates, scores)):
            rerank_candidates.append(RerankCandidate(
                doc_id=candidate.get("id", str(i)),
                content=candidate.get("content", candidate.get("text", "")),
                initial_score=candidate.get("score", 0.0),
                rerank_score=float(score),
                initial_rank=i + 1,
                metadata=candidate.get("metadata", {})
            ))

        # 按 rerank_score 排序
        rerank_candidates.sort(key=lambda x: x.rerank_score, reverse=True)

        # 更新最終排名
        for i, c in enumerate(rerank_candidates):
            c.final_rank = i + 1

        # 取 top_k
        if top_k:
            rerank_candidates = rerank_candidates[:top_k]

        rerank_time = (time.time() - start_time) * 1000

        return RerankResult(
            query=query,
            candidates=rerank_candidates,
            rerank_time_ms=rerank_time,
            model_name=self.model_name
        )

    def rerank_batch(
        self,
        queries: List[str],
        candidates_list: List[List[Dict]],
        top_k: int = None
    ) -> List[RerankResult]:
        """
        批次重新排序

        Args:
            queries: 查詢列表
            candidates_list: 每個查詢對應的候選文件列表
            top_k: 每個查詢返回前 k 個結果

        Returns:
            RerankResult 列表
        """
        results = []
        for query, candidates in zip(queries, candidates_list):
            result = self.rerank(query, candidates, top_k)
            results.append(result)
        return results


class LightweightReranker:
    """
    輕量級 Re-Ranker（使用 Bi-Encoder）

    當資源受限或延遲要求極高時，可以使用 Bi-Encoder
    進行簡單的 Re-Ranking（重新計算相似度）。

    注意：效果不如 Cross-Encoder，但速度更快。
    """

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ):
        from sentence_transformers import SentenceTransformer

        console.print(f"載入輕量級 Re-Ranker: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        console.print("[green]✓ 輕量級 Re-Ranker 就緒[/green]")

    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = None
    ) -> RerankResult:
        """使用 Bi-Encoder 重新計算相似度"""
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        if not candidates:
            return RerankResult(
                query=query,
                candidates=[],
                rerank_time_ms=0,
                model_name=self.model_name
            )

        start_time = time.time()

        # 編碼 query 和 candidates
        query_embedding = self.model.encode(query)
        doc_texts = [c.get("content", c.get("text", "")) for c in candidates]
        doc_embeddings = self.model.encode(doc_texts)

        # 計算相似度
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1),
            doc_embeddings
        )[0]

        # 建立結果
        rerank_candidates = []
        for i, (candidate, score) in enumerate(zip(candidates, similarities)):
            rerank_candidates.append(RerankCandidate(
                doc_id=candidate.get("id", str(i)),
                content=candidate.get("content", candidate.get("text", "")),
                initial_score=candidate.get("score", 0.0),
                rerank_score=float(score),
                initial_rank=i + 1,
                metadata=candidate.get("metadata", {})
            ))

        # 排序
        rerank_candidates.sort(key=lambda x: x.rerank_score, reverse=True)

        for i, c in enumerate(rerank_candidates):
            c.final_rank = i + 1

        if top_k:
            rerank_candidates = rerank_candidates[:top_k]

        rerank_time = (time.time() - start_time) * 1000

        return RerankResult(
            query=query,
            candidates=rerank_candidates,
            rerank_time_ms=rerank_time,
            model_name=self.model_name
        )


def display_rerank_result(result: RerankResult) -> None:
    """美化顯示 Re-Ranking 結果"""
    console.print(f"\n[bold]查詢：{result.query}[/bold]")
    console.print(f"Re-Ranking 模型: {result.model_name}")
    console.print(f"耗時: {result.rerank_time_ms:.2f} ms\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("最終排名", width=8, justify="center")
    table.add_column("原始排名", width=8, justify="center")
    table.add_column("變化", width=6, justify="center")
    table.add_column("Re-Rank 分數", width=12, justify="right")
    table.add_column("內容預覽", width=50)

    for c in result.candidates[:5]:
        rank_change = c.initial_rank - c.final_rank
        if rank_change > 0:
            change_str = f"[green]↑{rank_change}[/green]"
        elif rank_change < 0:
            change_str = f"[red]↓{-rank_change}[/red]"
        else:
            change_str = "-"

        preview = c.content[:45].replace('\n', ' ') + "..."

        table.add_row(
            str(c.final_rank),
            str(c.initial_rank),
            change_str,
            f"{c.rerank_score:.4f}",
            preview
        )

    console.print(table)


def main():
    """演示 Re-Ranking 功能"""
    console.print("\n[bold]═══ Re-Ranking 演示 ═══[/bold]\n")

    # 模擬候選文件（假設是第一階段檢索的結果）
    candidates = [
        {
            "id": "1",
            "content": "如何重設密碼？請點擊登入頁面的「忘記密碼」連結，輸入您的電子郵件地址。",
            "score": 0.85
        },
        {
            "id": "2",
            "content": "支援哪些付款方式？我們支援信用卡（Visa、MasterCard）、銀行轉帳、PayPal。",
            "score": 0.72
        },
        {
            "id": "3",
            "content": "密碼重設連結有效期為 24 小時。如果連結過期，請重新申請。",
            "score": 0.68
        },
        {
            "id": "4",
            "content": "如何變更電子郵件地址？請登入後進入「帳戶設定」>「個人資料」。",
            "score": 0.65
        },
        {
            "id": "5",
            "content": "忘記密碼時，請確認您使用的電子郵件地址正確，並檢查垃圾郵件資料夾。",
            "score": 0.60
        },
    ]

    query = "密碼忘記了怎麼辦"

    console.print("[yellow]初始排序（按第一階段分數）：[/yellow]")
    for i, c in enumerate(candidates, 1):
        console.print(f"  {i}. [{c['score']:.2f}] {c['content'][:40]}...")

    # 初始化 Re-Ranker（使用輕量版示範，因為 BGE 需要下載）
    console.print("\n")

    try:
        reranker = CrossEncoderReranker(model_name="ms-marco-MiniLM")
    except Exception:
        console.print("[yellow]使用輕量級 Re-Ranker 作為示範[/yellow]")
        reranker = LightweightReranker()

    # 執行 Re-Ranking
    result = reranker.rerank(query, candidates)

    # 顯示結果
    console.print("\n[yellow]Re-Ranking 後：[/yellow]")
    display_rerank_result(result)


if __name__ == "__main__":
    main()
