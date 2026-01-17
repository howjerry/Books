"""
chapter-07/tune_alpha.py

Alpha 參數調優腳本

本模組提供系統化方法來調優混合搜尋中的 alpha 參數，
找到最適合你業務場景的 BM25 與向量搜尋的權重比例。

使用方式：
    python tune_alpha.py

依賴安裝：
    pip install matplotlib numpy rich
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

console = Console()


@dataclass
class TuningResult:
    """調優結果"""
    alpha: float
    precision_at_k: float
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    avg_latency_ms: float


class AlphaTuner:
    """
    Alpha 參數調優器

    透過 Grid Search 找到最佳的 alpha 值。
    """

    def __init__(
        self,
        engine,  # HybridSearchEngine
        test_data: List[Dict]
    ):
        """
        初始化調優器

        Args:
            engine: 混合搜尋引擎實例
            test_data: 測試資料，格式為：
                [
                    {
                        "query": "查詢文字",
                        "relevant_ids": ["doc1", "doc2"]  # 相關文件 ID
                    },
                    ...
                ]
        """
        self.engine = engine
        self.test_data = test_data

    def _calculate_precision_at_k(
        self,
        retrieved_ids: List[str],
        relevant_ids: set,
        k: int
    ) -> float:
        """計算 Precision@k"""
        retrieved_k = set(retrieved_ids[:k])
        relevant_retrieved = retrieved_k & relevant_ids
        return len(relevant_retrieved) / k if k > 0 else 0

    def _calculate_recall_at_k(
        self,
        retrieved_ids: List[str],
        relevant_ids: set,
        k: int
    ) -> float:
        """計算 Recall@k"""
        retrieved_k = set(retrieved_ids[:k])
        relevant_retrieved = retrieved_k & relevant_ids
        return len(relevant_retrieved) / len(relevant_ids) if relevant_ids else 0

    def _calculate_mrr(
        self,
        retrieved_ids: List[str],
        relevant_ids: set
    ) -> float:
        """計算 Mean Reciprocal Rank"""
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in relevant_ids:
                return 1.0 / (i + 1)
        return 0.0

    def _calculate_ndcg_at_k(
        self,
        retrieved_ids: List[str],
        relevant_ids: set,
        k: int
    ) -> float:
        """計算 NDCG@k"""
        import math

        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids[:k]):
            if doc_id in relevant_ids:
                dcg += 1.0 / math.log2(i + 2)

        # 理想情況
        ideal_dcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant_ids), k)))

        return dcg / ideal_dcg if ideal_dcg > 0 else 0.0

    def evaluate_alpha(self, alpha: float, top_k: int = 10) -> TuningResult:
        """
        評估特定 alpha 值的效能

        Args:
            alpha: BM25 權重
            top_k: 評估的 top-k

        Returns:
            TuningResult 評估結果
        """
        precisions = []
        recalls = []
        mrrs = []
        ndcgs = []
        latencies = []

        for item in self.test_data:
            query = item["query"]
            relevant_ids = set(item["relevant_ids"])

            # 執行搜尋
            result = self.engine.search(query, alpha=alpha, top_k=top_k)
            retrieved_ids = [r.doc_id for r in result.results]

            # 計算指標
            precisions.append(self._calculate_precision_at_k(retrieved_ids, relevant_ids, top_k))
            recalls.append(self._calculate_recall_at_k(retrieved_ids, relevant_ids, top_k))
            mrrs.append(self._calculate_mrr(retrieved_ids, relevant_ids))
            ndcgs.append(self._calculate_ndcg_at_k(retrieved_ids, relevant_ids, top_k))
            latencies.append(result.total_time_ms)

        return TuningResult(
            alpha=alpha,
            precision_at_k=np.mean(precisions),
            recall_at_k=np.mean(recalls),
            mrr=np.mean(mrrs),
            ndcg_at_k=np.mean(ndcgs),
            avg_latency_ms=np.mean(latencies)
        )                                                                  # ‹1›

    def grid_search(
        self,
        alpha_range: List[float] = None,
        top_k: int = 10,
        primary_metric: str = "ndcg_at_k"
    ) -> Tuple[float, List[TuningResult]]:
        """
        Grid Search 找最佳 alpha

        Args:
            alpha_range: alpha 值範圍，預設 [0, 0.1, 0.2, ..., 1.0]
            top_k: 評估的 top-k
            primary_metric: 主要優化指標

        Returns:
            (最佳 alpha, 所有結果列表)
        """
        if alpha_range is None:
            alpha_range = [i / 10 for i in range(11)]  # 0.0 到 1.0，步長 0.1

        results = []

        console.print(f"\n[bold]Grid Search: 評估 {len(alpha_range)} 個 alpha 值[/bold]\n")

        with Progress() as progress:
            task = progress.add_task("調優中...", total=len(alpha_range))

            for alpha in alpha_range:
                result = self.evaluate_alpha(alpha, top_k)
                results.append(result)
                progress.update(task, advance=1)

        # 找最佳 alpha
        best_result = max(results, key=lambda r: getattr(r, primary_metric))
        best_alpha = best_result.alpha

        return best_alpha, results                                         # ‹2›

    def visualize_results(
        self,
        results: List[TuningResult],
        best_alpha: float,
        save_path: str = "alpha_tuning.png"
    ) -> None:
        """
        視覺化調優結果

        Args:
            results: 調優結果列表
            best_alpha: 最佳 alpha
            save_path: 儲存路徑
        """
        alphas = [r.alpha for r in results]
        precisions = [r.precision_at_k for r in results]
        recalls = [r.recall_at_k for r in results]
        ndcgs = [r.ndcg_at_k for r in results]
        latencies = [r.avg_latency_ms for r in results]

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # Precision@k
        axes[0, 0].plot(alphas, precisions, 'b-o', label='Precision@k')
        axes[0, 0].axvline(x=best_alpha, color='r', linestyle='--', label=f'Best α={best_alpha}')
        axes[0, 0].set_xlabel('Alpha (BM25 Weight)')
        axes[0, 0].set_ylabel('Precision@k')
        axes[0, 0].set_title('Precision@k vs Alpha')
        axes[0, 0].legend()
        axes[0, 0].grid(True)

        # Recall@k
        axes[0, 1].plot(alphas, recalls, 'g-s', label='Recall@k')
        axes[0, 1].axvline(x=best_alpha, color='r', linestyle='--', label=f'Best α={best_alpha}')
        axes[0, 1].set_xlabel('Alpha (BM25 Weight)')
        axes[0, 1].set_ylabel('Recall@k')
        axes[0, 1].set_title('Recall@k vs Alpha')
        axes[0, 1].legend()
        axes[0, 1].grid(True)

        # NDCG@k
        axes[1, 0].plot(alphas, ndcgs, 'm-^', label='NDCG@k')
        axes[1, 0].axvline(x=best_alpha, color='r', linestyle='--', label=f'Best α={best_alpha}')
        axes[1, 0].set_xlabel('Alpha (BM25 Weight)')
        axes[1, 0].set_ylabel('NDCG@k')
        axes[1, 0].set_title('NDCG@k vs Alpha')
        axes[1, 0].legend()
        axes[1, 0].grid(True)

        # Latency
        axes[1, 1].plot(alphas, latencies, 'c-d', label='Latency')
        axes[1, 1].set_xlabel('Alpha (BM25 Weight)')
        axes[1, 1].set_ylabel('Latency (ms)')
        axes[1, 1].set_title('Latency vs Alpha')
        axes[1, 1].legend()
        axes[1, 1].grid(True)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        console.print(f"[green]✓ 調優曲線已儲存至 {save_path}[/green]")


def display_tuning_results(results: List[TuningResult], best_alpha: float):
    """顯示調優結果表格"""
    table = Table(title="Alpha 調優結果")
    table.add_column("Alpha", justify="right", style="cyan")
    table.add_column("P@k", justify="right")
    table.add_column("R@k", justify="right")
    table.add_column("MRR", justify="right")
    table.add_column("NDCG@k", justify="right", style="green")
    table.add_column("延遲 (ms)", justify="right")

    for r in results:
        style = "bold yellow" if r.alpha == best_alpha else ""
        table.add_row(
            f"{r.alpha:.1f}" + (" ★" if r.alpha == best_alpha else ""),
            f"{r.precision_at_k:.4f}",
            f"{r.recall_at_k:.4f}",
            f"{r.mrr:.4f}",
            f"{r.ndcg_at_k:.4f}",
            f"{r.avg_latency_ms:.1f}",
            style=style
        )

    console.print(table)


def demo_alpha_tuning():
    """演示 Alpha 調優"""
    from hybrid_search import HybridSearchEngine

    console.print("\n[bold]═══ Alpha 參數調優演示 ═══[/bold]\n")

    # 建立引擎
    engine = HybridSearchEngine()

    # 索引測試文件
    documents = [
        "如何重設密碼？請點擊登入頁面的「忘記密碼」連結。",
        "錯誤代碼 E001：連線逾時，請檢查網路設定。",
        "錯誤代碼 E002：認證失敗，請確認帳號密碼。",
        "錯誤代碼 E003：權限不足，請聯繫管理員。",
        "產品型號 AX-2024-PRO 的規格：8 核心、32GB 記憶體。",
        "產品型號 AX-2024-LITE 的規格：4 核心、16GB 記憶體。",
        "忘記密碼可以透過驗證碼重設。",
        "密碼重設連結有效期為 24 小時。",
        "如何變更密碼？登入後到「帳戶設定」。",
        "系統出現 E001 錯誤時，通常是網路問題。",
    ]

    doc_ids = engine.index_documents(documents)

    # 測試資料（包含正確答案）
    test_data = [
        {
            "query": "密碼忘記怎麼辦",
            "relevant_ids": [engine.doc_ids[0], engine.doc_ids[6], engine.doc_ids[7]]
        },
        {
            "query": "E001 錯誤",
            "relevant_ids": [engine.doc_ids[1], engine.doc_ids[9]]
        },
        {
            "query": "AX-2024-PRO",
            "relevant_ids": [engine.doc_ids[4]]
        },
        {
            "query": "認證失敗怎麼處理",
            "relevant_ids": [engine.doc_ids[2]]
        },
    ]

    # 調優
    tuner = AlphaTuner(engine, test_data)
    best_alpha, results = tuner.grid_search(
        alpha_range=[0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0],
        top_k=5,
        primary_metric="ndcg_at_k"
    )

    # 顯示結果
    display_tuning_results(results, best_alpha)
    console.print(f"\n[bold green]最佳 Alpha: {best_alpha}[/bold green]")

    # 視覺化
    tuner.visualize_results(results, best_alpha)


class QueryTypeAdaptiveAlpha:
    """
    查詢類型自適應 Alpha

    根據查詢的特徵自動調整 alpha 權重。
    """

    def __init__(self):
        # 專有名詞、代碼的正則表達式
        self.code_patterns = [
            r'[A-Z]{2,}-\d+',           # 產品代碼如 AX-2024
            r'E\d{3,4}',                # 錯誤代碼如 E001
            r'v\d+\.\d+',               # 版本號如 v2.0
            r'API-\w+',                 # API 標識
        ]

    def estimate_alpha(self, query: str) -> float:
        """
        根據查詢特徵估計最佳 alpha

        Args:
            query: 查詢文字

        Returns:
            建議的 alpha 值
        """
        import re

        # 檢查是否包含代碼/專有名詞
        for pattern in self.code_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return 0.8  # 偏向 BM25（精確匹配）              # ‹3›

        # 檢查查詢長度
        word_count = len(query.split())

        if word_count <= 2:
            # 短查詢：可能是代碼或關鍵詞
            return 0.6
        elif word_count <= 5:
            # 中等查詢：平衡
            return 0.5
        else:
            # 長查詢：偏向語義
            return 0.3                                           # ‹4›


if __name__ == "__main__":
    demo_alpha_tuning()
