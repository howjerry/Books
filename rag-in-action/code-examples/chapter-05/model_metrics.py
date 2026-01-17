"""
chapter-05/model_metrics.py

Embedding 模型評估指標計算模組

本模組提供各種 IR（資訊檢索）評估指標的計算實作，
用於量化比較不同 Embedding 模型的檢索效果。

指標說明：
1. Precision@k - 前 k 個結果中相關的比例
2. Recall@k - 相關文件被檢索到的比例
3. MRR (Mean Reciprocal Rank) - 第一個相關結果排名倒數的平均
4. NDCG@k (Normalized DCG) - 考慮排名位置的指標
5. MAP (Mean Average Precision) - 平均精確度均值

使用方式：
    from model_metrics import MetricsCalculator
    calculator = MetricsCalculator()
    metrics = calculator.compute_all(predictions, ground_truth)
"""

from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class RetrievalMetrics:
    """檢索評估指標集合"""
    precision_at_1: float
    precision_at_3: float
    precision_at_5: float
    precision_at_10: float
    recall_at_5: float
    recall_at_10: float
    mrr: float
    ndcg_at_5: float
    ndcg_at_10: float
    map_score: float

    def to_dict(self) -> Dict:
        return {
            "P@1": round(self.precision_at_1, 4),
            "P@3": round(self.precision_at_3, 4),
            "P@5": round(self.precision_at_5, 4),
            "P@10": round(self.precision_at_10, 4),
            "R@5": round(self.recall_at_5, 4),
            "R@10": round(self.recall_at_10, 4),
            "MRR": round(self.mrr, 4),
            "NDCG@5": round(self.ndcg_at_5, 4),
            "NDCG@10": round(self.ndcg_at_10, 4),
            "MAP": round(self.map_score, 4),
        }


class MetricsCalculator:
    """
    IR 評估指標計算器

    提供標準的資訊檢索評估指標計算。

    Example:
        >>> calculator = MetricsCalculator()
        >>> # ranked_docs: 按相關性排序的文件 ID 列表
        >>> # relevant_docs: 真正相關的文件 ID 集合
        >>> metrics = calculator.compute_all(ranked_docs, relevant_docs)
    """

    @staticmethod
    def precision_at_k(
        ranked_docs: List[int],
        relevant_docs: Set[int],
        k: int
    ) -> float:
        """
        計算 Precision@k

        Precision@k = (前 k 個結果中相關的數量) / k

        Args:
            ranked_docs: 按相關性排序的文件 ID 列表
            relevant_docs: 真正相關的文件 ID 集合
            k: 取前 k 個結果

        Returns:
            Precision@k 分數
        """
        if k <= 0:
            return 0.0

        top_k = set(ranked_docs[:k])
        relevant_in_top_k = len(top_k & relevant_docs)

        return relevant_in_top_k / k                                    # ‹1›

    @staticmethod
    def recall_at_k(
        ranked_docs: List[int],
        relevant_docs: Set[int],
        k: int
    ) -> float:
        """
        計算 Recall@k

        Recall@k = (前 k 個結果中相關的數量) / (總相關文件數量)

        Args:
            ranked_docs: 按相關性排序的文件 ID 列表
            relevant_docs: 真正相關的文件 ID 集合
            k: 取前 k 個結果

        Returns:
            Recall@k 分數
        """
        if not relevant_docs:
            return 0.0

        top_k = set(ranked_docs[:k])
        relevant_in_top_k = len(top_k & relevant_docs)

        return relevant_in_top_k / len(relevant_docs)                   # ‹2›

    @staticmethod
    def reciprocal_rank(
        ranked_docs: List[int],
        relevant_docs: Set[int]
    ) -> float:
        """
        計算 Reciprocal Rank (RR)

        RR = 1 / (第一個相關結果的排名)

        Args:
            ranked_docs: 按相關性排序的文件 ID 列表
            relevant_docs: 真正相關的文件 ID 集合

        Returns:
            Reciprocal Rank 分數
        """
        for rank, doc_id in enumerate(ranked_docs, 1):
            if doc_id in relevant_docs:
                return 1.0 / rank                                       # ‹3›

        return 0.0  # 沒有找到相關文件

    @staticmethod
    def dcg_at_k(
        ranked_docs: List[int],
        relevant_docs: Set[int],
        k: int
    ) -> float:
        """
        計算 DCG@k (Discounted Cumulative Gain)

        DCG@k = Σ (rel_i / log2(i + 1)) for i = 1 to k

        Args:
            ranked_docs: 按相關性排序的文件 ID 列表
            relevant_docs: 真正相關的文件 ID 集合
            k: 取前 k 個結果

        Returns:
            DCG@k 分數
        """
        dcg = 0.0

        for i, doc_id in enumerate(ranked_docs[:k]):
            if doc_id in relevant_docs:
                # 使用二元相關性 (0 或 1)
                dcg += 1.0 / np.log2(i + 2)  # i+2 因為 log2(1) = 0    # ‹4›

        return dcg

    @staticmethod
    def ndcg_at_k(
        ranked_docs: List[int],
        relevant_docs: Set[int],
        k: int
    ) -> float:
        """
        計算 NDCG@k (Normalized DCG)

        NDCG@k = DCG@k / IDCG@k

        其中 IDCG@k 是理想情況下的 DCG

        Args:
            ranked_docs: 按相關性排序的文件 ID 列表
            relevant_docs: 真正相關的文件 ID 集合
            k: 取前 k 個結果

        Returns:
            NDCG@k 分數
        """
        dcg = MetricsCalculator.dcg_at_k(ranked_docs, relevant_docs, k)

        # IDCG: 理想情況（所有相關文件排在最前面）
        ideal_k = min(k, len(relevant_docs))
        idcg = sum(1.0 / np.log2(i + 2) for i in range(ideal_k))        # ‹5›

        if idcg == 0:
            return 0.0

        return dcg / idcg

    @staticmethod
    def average_precision(
        ranked_docs: List[int],
        relevant_docs: Set[int]
    ) -> float:
        """
        計算 Average Precision (AP)

        AP = (Σ P@k × rel(k)) / |相關文件|

        其中 rel(k) = 1 如果第 k 個結果相關，否則 = 0

        Args:
            ranked_docs: 按相關性排序的文件 ID 列表
            relevant_docs: 真正相關的文件 ID 集合

        Returns:
            Average Precision 分數
        """
        if not relevant_docs:
            return 0.0

        precision_sum = 0.0
        relevant_count = 0

        for i, doc_id in enumerate(ranked_docs):
            if doc_id in relevant_docs:
                relevant_count += 1
                precision_at_i = relevant_count / (i + 1)
                precision_sum += precision_at_i                         # ‹6›

        return precision_sum / len(relevant_docs)

    def compute_query_metrics(
        self,
        ranked_docs: List[int],
        relevant_docs: Set[int]
    ) -> RetrievalMetrics:
        """
        計算單一查詢的所有指標

        Args:
            ranked_docs: 按相關性排序的文件 ID 列表
            relevant_docs: 真正相關的文件 ID 集合

        Returns:
            RetrievalMetrics 物件
        """
        return RetrievalMetrics(
            precision_at_1=self.precision_at_k(ranked_docs, relevant_docs, 1),
            precision_at_3=self.precision_at_k(ranked_docs, relevant_docs, 3),
            precision_at_5=self.precision_at_k(ranked_docs, relevant_docs, 5),
            precision_at_10=self.precision_at_k(ranked_docs, relevant_docs, 10),
            recall_at_5=self.recall_at_k(ranked_docs, relevant_docs, 5),
            recall_at_10=self.recall_at_k(ranked_docs, relevant_docs, 10),
            mrr=self.reciprocal_rank(ranked_docs, relevant_docs),
            ndcg_at_5=self.ndcg_at_k(ranked_docs, relevant_docs, 5),
            ndcg_at_10=self.ndcg_at_k(ranked_docs, relevant_docs, 10),
            map_score=self.average_precision(ranked_docs, relevant_docs),
        )

    def compute_all(
        self,
        all_ranked_docs: List[List[int]],
        all_relevant_docs: List[Set[int]]
    ) -> RetrievalMetrics:
        """
        計算多個查詢的平均指標

        Args:
            all_ranked_docs: 每個查詢的排序結果列表
            all_relevant_docs: 每個查詢的相關文件集合

        Returns:
            平均的 RetrievalMetrics 物件
        """
        assert len(all_ranked_docs) == len(all_relevant_docs)

        all_metrics = [
            self.compute_query_metrics(ranked, relevant)
            for ranked, relevant in zip(all_ranked_docs, all_relevant_docs)
        ]

        # 計算平均值
        return RetrievalMetrics(
            precision_at_1=np.mean([m.precision_at_1 for m in all_metrics]),
            precision_at_3=np.mean([m.precision_at_3 for m in all_metrics]),
            precision_at_5=np.mean([m.precision_at_5 for m in all_metrics]),
            precision_at_10=np.mean([m.precision_at_10 for m in all_metrics]),
            recall_at_5=np.mean([m.recall_at_5 for m in all_metrics]),
            recall_at_10=np.mean([m.recall_at_10 for m in all_metrics]),
            mrr=np.mean([m.mrr for m in all_metrics]),
            ndcg_at_5=np.mean([m.ndcg_at_5 for m in all_metrics]),
            ndcg_at_10=np.mean([m.ndcg_at_10 for m in all_metrics]),
            map_score=np.mean([m.map_score for m in all_metrics]),
        )


def explain_metrics():
    """解釋各種指標的意義"""
    explanations = """
    ╔════════════════════════════════════════════════════════════════╗
    ║                    IR 評估指標說明                              ║
    ╠════════════════════════════════════════════════════════════════╣
    ║                                                                 ║
    ║ Precision@k (P@k)                                              ║
    ║ ───────────────────                                            ║
    ║ 前 k 個結果中，有多少比例是相關的                               ║
    ║ 適用：當使用者只看前幾個結果時                                  ║
    ║ 範例：P@3 = 0.67 表示前 3 個結果中有 2 個相關                  ║
    ║                                                                 ║
    ║ Recall@k (R@k)                                                 ║
    ║ ───────────────────                                            ║
    ║ 所有相關文件中，有多少被包含在前 k 個結果                       ║
    ║ 適用：當需要找到所有相關文件時                                  ║
    ║ 範例：R@5 = 0.80 表示 80% 的相關文件出現在前 5 個結果         ║
    ║                                                                 ║
    ║ MRR (Mean Reciprocal Rank)                                     ║
    ║ ───────────────────────────                                    ║
    ║ 第一個相關結果排名的倒數                                        ║
    ║ 適用：當使用者只需要一個正確答案時                              ║
    ║ 範例：MRR = 0.50 表示平均第一個相關結果出現在第 2 位           ║
    ║                                                                 ║
    ║ NDCG@k (Normalized Discounted Cumulative Gain)                 ║
    ║ ───────────────────────────────────────────────                ║
    ║ 考慮排名位置的指標，越前面的位置權重越高                        ║
    ║ 適用：當排名順序很重要時                                        ║
    ║ 範例：NDCG@5 = 0.85 表示排名接近理想情況                       ║
    ║                                                                 ║
    ║ MAP (Mean Average Precision)                                   ║
    ║ ───────────────────────────                                    ║
    ║ 所有相關結果出現位置的平均精確度                                ║
    ║ 適用：綜合評估整體檢索品質                                      ║
    ║ 範例：MAP = 0.75 表示整體檢索效果良好                          ║
    ║                                                                 ║
    ╚════════════════════════════════════════════════════════════════╝
    """
    print(explanations)


def main():
    """演示指標計算"""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # 範例資料
    ranked_docs = [3, 1, 0, 5, 2, 4, 6, 7, 8, 9]  # 檢索結果（按相關性排序）
    relevant_docs = {0, 1, 2}  # 真正相關的文件

    calculator = MetricsCalculator()
    metrics = calculator.compute_query_metrics(ranked_docs, set(relevant_docs))

    console.print("\n[bold]═══ IR 指標計算演示 ═══[/bold]\n")

    console.print(f"檢索結果: {ranked_docs}")
    console.print(f"相關文件: {relevant_docs}")

    table = Table(title="評估指標")
    table.add_column("指標", style="cyan")
    table.add_column("值", justify="right")
    table.add_column("說明")

    table.add_row("P@1", f"{metrics.precision_at_1:.3f}", "第 1 個結果是否相關")
    table.add_row("P@3", f"{metrics.precision_at_3:.3f}", "前 3 個結果中相關的比例")
    table.add_row("P@5", f"{metrics.precision_at_5:.3f}", "前 5 個結果中相關的比例")
    table.add_row("R@5", f"{metrics.recall_at_5:.3f}", "前 5 個結果涵蓋的相關文件比例")
    table.add_row("MRR", f"{metrics.mrr:.3f}", "第一個相關結果排名的倒數")
    table.add_row("NDCG@5", f"{metrics.ndcg_at_5:.3f}", "考慮位置的增益指標")
    table.add_row("MAP", f"{metrics.map_score:.3f}", "平均精確度")

    console.print(table)

    console.print("\n")
    explain_metrics()


if __name__ == "__main__":
    main()
