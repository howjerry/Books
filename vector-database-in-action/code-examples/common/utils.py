"""
向量資料庫實戰 - 通用工具函式
Vector Database in Action - Common Utilities
"""

import numpy as np
from typing import List, Tuple, Dict, Optional, Union
import time
from functools import wraps
import logging

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# 距離計算函式
# ============================================================

def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算歐幾里得距離 (L2)

    Args:
        a: 向量 a
        b: 向量 b

    Returns:
        歐幾里得距離
    """
    return np.sqrt(np.sum((a - b) ** 2))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算餘弦相似度

    Args:
        a: 向量 a
        b: 向量 b

    Returns:
        餘弦相似度 [-1, 1]
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return np.dot(a, b) / (norm_a * norm_b)


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算餘弦距離

    Args:
        a: 向量 a
        b: 向量 b

    Returns:
        餘弦距離 [0, 2]
    """
    return 1 - cosine_similarity(a, b)


def manhattan_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算曼哈頓距離 (L1)

    Args:
        a: 向量 a
        b: 向量 b

    Returns:
        曼哈頓距離
    """
    return np.sum(np.abs(a - b))


def chebyshev_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算切比雪夫距離 (L∞)

    Args:
        a: 向量 a
        b: 向量 b

    Returns:
        切比雪夫距離
    """
    return np.max(np.abs(a - b))


def dot_product(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算內積

    Args:
        a: 向量 a
        b: 向量 b

    Returns:
        內積
    """
    return np.dot(a, b)


# ============================================================
# 批次距離計算
# ============================================================

def batch_euclidean_distances(
    vectors: np.ndarray,
    query: np.ndarray
) -> np.ndarray:
    """
    批次計算歐幾里得距離

    Args:
        vectors: 向量矩陣 (n, d)
        query: 查詢向量 (d,)

    Returns:
        距離陣列 (n,)
    """
    # 使用展開公式: ||a-b||² = ||a||² + ||b||² - 2<a,b>
    vectors_sq = np.sum(vectors ** 2, axis=1)
    query_sq = np.sum(query ** 2)
    dot_products = np.dot(vectors, query)

    distances_sq = vectors_sq + query_sq - 2 * dot_products
    distances_sq = np.maximum(distances_sq, 0)  # 數值穩定性

    return np.sqrt(distances_sq)


def batch_cosine_similarities(
    vectors: np.ndarray,
    query: np.ndarray
) -> np.ndarray:
    """
    批次計算餘弦相似度

    Args:
        vectors: 向量矩陣 (n, d)
        query: 查詢向量 (d,)

    Returns:
        相似度陣列 (n,)
    """
    # 正規化
    vectors_norm = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    query_norm = query / np.linalg.norm(query)

    return np.dot(vectors_norm, query_norm)


# ============================================================
# 評估指標
# ============================================================

def precision_at_k(
    retrieved: List[int],
    relevant: set,
    k: int
) -> float:
    """
    計算 Precision@K

    Args:
        retrieved: 檢索結果列表（按排序）
        relevant: 相關項目集合
        k: K 值

    Returns:
        Precision@K
    """
    retrieved_k = set(retrieved[:k])
    relevant_retrieved = retrieved_k & relevant
    return len(relevant_retrieved) / k


def recall_at_k(
    retrieved: List[int],
    relevant: set,
    k: int
) -> float:
    """
    計算 Recall@K

    Args:
        retrieved: 檢索結果列表（按排序）
        relevant: 相關項目集合
        k: K 值

    Returns:
        Recall@K
    """
    if not relevant:
        return 0.0

    retrieved_k = set(retrieved[:k])
    relevant_retrieved = retrieved_k & relevant
    return len(relevant_retrieved) / len(relevant)


def f1_at_k(
    retrieved: List[int],
    relevant: set,
    k: int
) -> float:
    """
    計算 F1@K

    Args:
        retrieved: 檢索結果列表（按排序）
        relevant: 相關項目集合
        k: K 值

    Returns:
        F1@K
    """
    p = precision_at_k(retrieved, relevant, k)
    r = recall_at_k(retrieved, relevant, k)

    if p + r == 0:
        return 0.0

    return 2 * p * r / (p + r)


def average_precision(
    retrieved: List[int],
    relevant: set
) -> float:
    """
    計算 Average Precision

    Args:
        retrieved: 檢索結果列表（按排序）
        relevant: 相關項目集合

    Returns:
        Average Precision
    """
    if not relevant:
        return 0.0

    score = 0.0
    num_relevant = 0

    for i, doc in enumerate(retrieved):
        if doc in relevant:
            num_relevant += 1
            score += num_relevant / (i + 1)

    return score / len(relevant)


def mean_average_precision(
    all_retrieved: List[List[int]],
    all_relevant: List[set]
) -> float:
    """
    計算 Mean Average Precision

    Args:
        all_retrieved: 所有查詢的檢索結果
        all_relevant: 所有查詢的相關項目

    Returns:
        MAP
    """
    aps = [
        average_precision(retrieved, relevant)
        for retrieved, relevant in zip(all_retrieved, all_relevant)
    ]
    return np.mean(aps)


def dcg_at_k(relevances: List[float], k: int) -> float:
    """
    計算 Discounted Cumulative Gain

    Args:
        relevances: 相關性分數列表
        k: K 值

    Returns:
        DCG@K
    """
    relevances = np.array(relevances[:k])
    discounts = np.log2(np.arange(2, k + 2))
    gains = (2 ** relevances - 1) / discounts
    return np.sum(gains)


def ndcg_at_k(relevances: List[float], k: int) -> float:
    """
    計算 Normalized DCG

    Args:
        relevances: 相關性分數列表
        k: K 值

    Returns:
        NDCG@K
    """
    dcg = dcg_at_k(relevances, k)
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = dcg_at_k(ideal_relevances, k)

    if idcg == 0:
        return 0.0

    return dcg / idcg


# ============================================================
# 效能測量裝飾器
# ============================================================

def timeit(func):
    """
    計時裝飾器
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} 執行時間: {elapsed:.4f} 秒")
        return result
    return wrapper


class Timer:
    """
    計時器上下文管理器
    """
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start = None
        self.elapsed = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self.start
        logger.info(f"{self.name} 執行時間: {self.elapsed:.4f} 秒")


# ============================================================
# 資料處理工具
# ============================================================

def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """
    L2 正規化向量

    Args:
        vectors: 向量矩陣 (n, d)

    Returns:
        正規化後的向量
    """
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1  # 避免除以零
    return vectors / norms


def chunk_list(lst: List, chunk_size: int):
    """
    將列表分割成固定大小的塊

    Args:
        lst: 原始列表
        chunk_size: 塊大小

    Yields:
        列表塊
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def generate_random_vectors(
    n: int,
    dim: int,
    seed: Optional[int] = None
) -> np.ndarray:
    """
    生成隨機向量

    Args:
        n: 向量數量
        dim: 向量維度
        seed: 隨機種子

    Returns:
        隨機向量矩陣
    """
    if seed is not None:
        np.random.seed(seed)
    return np.random.randn(n, dim).astype(np.float32)


# ============================================================
# 向量量化工具
# ============================================================

def scalar_quantize(
    vectors: np.ndarray,
    bits: int = 8
) -> Tuple[np.ndarray, Dict]:
    """
    標量量化

    Args:
        vectors: 原始向量
        bits: 量化位數

    Returns:
        量化後的向量和量化參數
    """
    n_levels = 2 ** bits

    # 計算每個維度的範圍
    mins = vectors.min(axis=0)
    maxs = vectors.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1  # 避免除以零

    # 量化
    normalized = (vectors - mins) / ranges
    quantized = np.round(normalized * (n_levels - 1)).astype(np.uint8)

    params = {
        'mins': mins,
        'ranges': ranges,
        'n_levels': n_levels
    }

    return quantized, params


def scalar_dequantize(
    quantized: np.ndarray,
    params: Dict
) -> np.ndarray:
    """
    標量反量化

    Args:
        quantized: 量化後的向量
        params: 量化參數

    Returns:
        反量化後的向量
    """
    normalized = quantized.astype(np.float32) / (params['n_levels'] - 1)
    return normalized * params['ranges'] + params['mins']
