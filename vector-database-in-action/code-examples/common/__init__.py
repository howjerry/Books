"""
向量資料庫實戰 - 通用模組
Vector Database in Action - Common Module
"""

from .utils import (
    # Distance functions
    euclidean_distance,
    cosine_similarity,
    cosine_distance,
    manhattan_distance,
    chebyshev_distance,
    dot_product,

    # Batch operations
    batch_euclidean_distances,
    batch_cosine_similarities,

    # Evaluation metrics
    precision_at_k,
    recall_at_k,
    f1_at_k,
    average_precision,
    mean_average_precision,
    dcg_at_k,
    ndcg_at_k,

    # Utilities
    timeit,
    Timer,
    normalize_vectors,
    chunk_list,
    generate_random_vectors,
    scalar_quantize,
    scalar_dequantize,
)

__all__ = [
    # Distance functions
    'euclidean_distance',
    'cosine_similarity',
    'cosine_distance',
    'manhattan_distance',
    'chebyshev_distance',
    'dot_product',

    # Batch operations
    'batch_euclidean_distances',
    'batch_cosine_similarities',

    # Evaluation metrics
    'precision_at_k',
    'recall_at_k',
    'f1_at_k',
    'average_precision',
    'mean_average_precision',
    'dcg_at_k',
    'ndcg_at_k',

    # Utilities
    'timeit',
    'Timer',
    'normalize_vectors',
    'chunk_list',
    'generate_random_vectors',
    'scalar_quantize',
    'scalar_dequantize',
]
