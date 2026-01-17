"""
chapter-07/score_normalization.py

分數正規化模組

本模組實作多種分數正規化與融合策略，
用於將不同來源的檢索分數統一到可比較的尺度。

使用方式：
    from score_normalization import ScoreNormalizer
    normalizer = ScoreNormalizer()
    normalized = normalizer.min_max_normalize(scores)

依賴安裝：
    pip install numpy scikit-learn
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import numpy as np
from enum import Enum


class NormalizationMethod(Enum):
    """正規化方法"""
    MIN_MAX = "min_max"
    Z_SCORE = "z_score"
    PERCENTILE = "percentile"
    SIGMOID = "sigmoid"


class FusionMethod(Enum):
    """分數融合方法"""
    WEIGHTED_SUM = "weighted_sum"               # 加權平均
    RECIPROCAL_RANK = "reciprocal_rank"         # RRF
    CONVEX_COMBINATION = "convex_combination"   # 凸組合


@dataclass
class FusedResult:
    """融合後的結果"""
    doc_id: str
    content: str
    bm25_score: float
    vector_score: float
    bm25_rank: int
    vector_rank: int
    fused_score: float
    final_rank: int
    metadata: Dict = None


class ScoreNormalizer:
    """
    分數正規化器

    將不同分布的分數統一到 [0, 1] 區間，
    使 BM25 和向量搜尋的分數可以直接比較。
    """

    @staticmethod
    def min_max_normalize(scores: List[float], epsilon: float = 1e-10) -> List[float]:
        """
        Min-Max 正規化

        公式: (x - min) / (max - min)

        Args:
            scores: 原始分數列表
            epsilon: 防止除零的小數

        Returns:
            正規化後的分數列表 [0, 1]
        """
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score + epsilon

        return [(s - min_score) / score_range for s in scores]           # ‹1›

    @staticmethod
    def z_score_normalize(scores: List[float], epsilon: float = 1e-10) -> List[float]:
        """
        Z-Score 正規化（標準化）

        公式: (x - mean) / std

        Args:
            scores: 原始分數列表
            epsilon: 防止除零的小數

        Returns:
            正規化後的分數列表
        """
        if not scores:
            return []

        mean = np.mean(scores)
        std = np.std(scores) + epsilon

        return [(s - mean) / std for s in scores]                         # ‹2›

    @staticmethod
    def percentile_normalize(scores: List[float]) -> List[float]:
        """
        百分位數正規化

        將分數轉換為其在分布中的百分位數

        Args:
            scores: 原始分數列表

        Returns:
            百分位數列表 [0, 1]
        """
        if not scores:
            return []

        from scipy import stats

        # 計算每個分數的百分位
        percentiles = [stats.percentileofscore(scores, s) / 100 for s in scores]
        return percentiles                                                 # ‹3›

    @staticmethod
    def sigmoid_normalize(
        scores: List[float],
        scale: float = 1.0,
        shift: float = 0.0
    ) -> List[float]:
        """
        Sigmoid 正規化

        使用 sigmoid 函數將分數壓縮到 (0, 1)

        Args:
            scores: 原始分數列表
            scale: 縮放係數
            shift: 平移量

        Returns:
            正規化後的分數列表 (0, 1)
        """
        if not scores:
            return []

        return [1 / (1 + np.exp(-scale * (s - shift))) for s in scores]   # ‹4›


class ScoreFuser:
    """
    分數融合器

    將 BM25 和向量搜尋的結果融合為統一排序。
    """

    def __init__(
        self,
        normalizer: ScoreNormalizer = None,
        normalization_method: NormalizationMethod = NormalizationMethod.MIN_MAX
    ):
        """
        初始化融合器

        Args:
            normalizer: 分數正規化器實例
            normalization_method: 正規化方法
        """
        self.normalizer = normalizer or ScoreNormalizer()
        self.normalization_method = normalization_method

    def _normalize(self, scores: List[float]) -> List[float]:
        """根據配置的方法進行正規化"""
        if self.normalization_method == NormalizationMethod.MIN_MAX:
            return self.normalizer.min_max_normalize(scores)
        elif self.normalization_method == NormalizationMethod.Z_SCORE:
            return self.normalizer.z_score_normalize(scores)
        elif self.normalization_method == NormalizationMethod.PERCENTILE:
            return self.normalizer.percentile_normalize(scores)
        elif self.normalization_method == NormalizationMethod.SIGMOID:
            return self.normalizer.sigmoid_normalize(scores)
        else:
            return scores

    def weighted_sum_fusion(
        self,
        bm25_results: List[Dict],
        vector_results: List[Dict],
        alpha: float = 0.5,
        top_k: int = 10
    ) -> List[FusedResult]:
        """
        加權平均融合

        公式: final_score = alpha * bm25_score + (1 - alpha) * vector_score

        Args:
            bm25_results: BM25 檢索結果 [{"id": ..., "content": ..., "score": ...}]
            vector_results: 向量檢索結果
            alpha: BM25 權重 (0-1)，0 表示純向量搜尋，1 表示純 BM25
            top_k: 返回結果數量

        Returns:
            融合後的結果列表
        """
        # 建立文件索引
        doc_map = {}

        # 處理 BM25 結果
        bm25_scores = [r["score"] for r in bm25_results]
        bm25_normalized = self._normalize(bm25_scores)

        for i, (result, norm_score) in enumerate(zip(bm25_results, bm25_normalized)):
            doc_id = result["id"]
            doc_map[doc_id] = {
                "content": result["content"],
                "bm25_score": norm_score,
                "bm25_rank": i + 1,
                "vector_score": 0.0,
                "vector_rank": len(vector_results) + 1,
                "metadata": result.get("metadata", {})
            }

        # 處理向量結果
        vector_scores = [r["score"] for r in vector_results]
        vector_normalized = self._normalize(vector_scores)

        for i, (result, norm_score) in enumerate(zip(vector_results, vector_normalized)):
            doc_id = result["id"]
            if doc_id in doc_map:
                doc_map[doc_id]["vector_score"] = norm_score
                doc_map[doc_id]["vector_rank"] = i + 1
            else:
                doc_map[doc_id] = {
                    "content": result["content"],
                    "bm25_score": 0.0,
                    "bm25_rank": len(bm25_results) + 1,
                    "vector_score": norm_score,
                    "vector_rank": i + 1,
                    "metadata": result.get("metadata", {})
                }

        # 計算融合分數
        fused_results = []
        for doc_id, data in doc_map.items():
            fused_score = (
                alpha * data["bm25_score"] +
                (1 - alpha) * data["vector_score"]
            )                                                              # ‹5›

            fused_results.append(FusedResult(
                doc_id=doc_id,
                content=data["content"],
                bm25_score=data["bm25_score"],
                vector_score=data["vector_score"],
                bm25_rank=data["bm25_rank"],
                vector_rank=data["vector_rank"],
                fused_score=fused_score,
                final_rank=0,
                metadata=data["metadata"]
            ))

        # 排序並更新排名
        fused_results.sort(key=lambda x: x.fused_score, reverse=True)
        for i, result in enumerate(fused_results):
            result.final_rank = i + 1

        return fused_results[:top_k]

    def reciprocal_rank_fusion(
        self,
        bm25_results: List[Dict],
        vector_results: List[Dict],
        k: int = 60,
        top_k: int = 10
    ) -> List[FusedResult]:
        """
        Reciprocal Rank Fusion (RRF)

        公式: score = Σ 1 / (k + rank)

        RRF 不需要正規化，直接使用排名計算分數。

        Args:
            bm25_results: BM25 檢索結果
            vector_results: 向量檢索結果
            k: RRF 參數，控制排名對分數的影響（通常 60）
            top_k: 返回結果數量

        Returns:
            融合後的結果列表
        """
        doc_map = {}

        # 處理 BM25 結果
        for i, result in enumerate(bm25_results):
            doc_id = result["id"]
            rrf_score = 1 / (k + i + 1)                                    # ‹6›
            doc_map[doc_id] = {
                "content": result["content"],
                "bm25_score": result["score"],
                "bm25_rank": i + 1,
                "bm25_rrf": rrf_score,
                "vector_score": 0.0,
                "vector_rank": len(vector_results) + 1,
                "vector_rrf": 0.0,
                "metadata": result.get("metadata", {})
            }

        # 處理向量結果
        for i, result in enumerate(vector_results):
            doc_id = result["id"]
            rrf_score = 1 / (k + i + 1)

            if doc_id in doc_map:
                doc_map[doc_id]["vector_score"] = result["score"]
                doc_map[doc_id]["vector_rank"] = i + 1
                doc_map[doc_id]["vector_rrf"] = rrf_score
            else:
                doc_map[doc_id] = {
                    "content": result["content"],
                    "bm25_score": 0.0,
                    "bm25_rank": len(bm25_results) + 1,
                    "bm25_rrf": 0.0,
                    "vector_score": result["score"],
                    "vector_rank": i + 1,
                    "vector_rrf": rrf_score,
                    "metadata": result.get("metadata", {})
                }

        # 計算 RRF 融合分數
        fused_results = []
        for doc_id, data in doc_map.items():
            fused_score = data["bm25_rrf"] + data["vector_rrf"]            # ‹7›

            fused_results.append(FusedResult(
                doc_id=doc_id,
                content=data["content"],
                bm25_score=data["bm25_score"],
                vector_score=data["vector_score"],
                bm25_rank=data["bm25_rank"],
                vector_rank=data["vector_rank"],
                fused_score=fused_score,
                final_rank=0,
                metadata=data["metadata"]
            ))

        # 排序並更新排名
        fused_results.sort(key=lambda x: x.fused_score, reverse=True)
        for i, result in enumerate(fused_results):
            result.final_rank = i + 1

        return fused_results[:top_k]


def compare_normalization_methods():
    """比較不同正規化方法的效果"""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # 模擬 BM25 分數（通常較大且分布不均）
    bm25_scores = [15.2, 12.8, 10.5, 8.3, 6.1, 4.2, 2.5, 1.2]

    # 模擬向量分數（通常在 0-1 之間）
    vector_scores = [0.92, 0.88, 0.85, 0.82, 0.75, 0.68, 0.55, 0.42]

    normalizer = ScoreNormalizer()

    console.print("\n[bold]分數正規化方法比較[/bold]\n")

    # BM25 正規化
    table = Table(title="BM25 分數正規化")
    table.add_column("原始分數", justify="right")
    table.add_column("Min-Max", justify="right")
    table.add_column("Z-Score", justify="right")
    table.add_column("Sigmoid", justify="right")

    min_max = normalizer.min_max_normalize(bm25_scores)
    z_score = normalizer.z_score_normalize(bm25_scores)
    sigmoid = normalizer.sigmoid_normalize(bm25_scores, scale=0.2, shift=8)

    for orig, mm, zs, sig in zip(bm25_scores, min_max, z_score, sigmoid):
        table.add_row(
            f"{orig:.2f}",
            f"{mm:.4f}",
            f"{zs:.4f}",
            f"{sig:.4f}"
        )

    console.print(table)

    # 向量分數正規化
    table2 = Table(title="向量分數正規化")
    table2.add_column("原始分數", justify="right")
    table2.add_column("Min-Max", justify="right")
    table2.add_column("Z-Score", justify="right")
    table2.add_column("Sigmoid", justify="right")

    min_max_v = normalizer.min_max_normalize(vector_scores)
    z_score_v = normalizer.z_score_normalize(vector_scores)
    sigmoid_v = normalizer.sigmoid_normalize(vector_scores, scale=5, shift=0.7)

    for orig, mm, zs, sig in zip(vector_scores, min_max_v, z_score_v, sigmoid_v):
        table2.add_row(
            f"{orig:.2f}",
            f"{mm:.4f}",
            f"{zs:.4f}",
            f"{sig:.4f}"
        )

    console.print(table2)


if __name__ == "__main__":
    compare_normalization_methods()
