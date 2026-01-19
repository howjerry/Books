# Chapter 11：性能優化與監控

> 「優化不是讓系統變快，而是找出讓系統變慢的原因並消除它。」

## 學習目標

完成本章後，你將能夠：

- 識別向量搜尋系統的效能瓶頸
- 應用多種優化技術提升搜尋效能
- 建立完整的監控和告警系統
- 進行效能基準測試和容量規劃
- 實作生產環境的效能調優

---

## 11.1 效能指標體系

### 11.1.1 核心效能指標

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import time
import numpy as np

class PerformanceMetric(Enum):
    """效能指標類型"""
    LATENCY = "latency"           # 延遲
    THROUGHPUT = "throughput"     # 吞吐量
    ACCURACY = "accuracy"         # 精確度
    RESOURCE = "resource"         # 資源使用


@dataclass
class LatencyMetrics:
    """
    延遲指標

    ‹1› 追蹤各階段延遲
    """
    total_ms: float              # 總延遲
    embedding_ms: float          # 向量化延遲
    search_ms: float             # 搜尋延遲
    postprocess_ms: float        # 後處理延遲
    network_ms: float            # 網絡延遲

    def breakdown(self) -> Dict[str, float]:
        """延遲分解"""
        return {
            "embedding": self.embedding_ms / self.total_ms * 100,
            "search": self.search_ms / self.total_ms * 100,
            "postprocess": self.postprocess_ms / self.total_ms * 100,
            "network": self.network_ms / self.total_ms * 100
        }


@dataclass
class ThroughputMetrics:
    """
    吞吐量指標

    ‹2› 追蹤系統處理能力
    """
    qps: float                   # 每秒查詢數
    concurrent_queries: int      # 並發查詢數
    batch_size: int              # 批次大小
    vectors_per_second: int      # 每秒處理向量數


@dataclass
class AccuracyMetrics:
    """
    精確度指標

    ‹3› 追蹤搜尋品質
    """
    recall_at_k: float           # Recall@K
    precision_at_k: float        # Precision@K
    ndcg_at_k: float             # NDCG@K
    mrr: float                   # Mean Reciprocal Rank


class PerformanceProfiler:
    """
    效能分析器

    ‹1› 收集效能數據
    ‹2› 識別瓶頸
    ‹3› 生成報告
    """

    def __init__(self):
        self.latency_samples: List[LatencyMetrics] = []
        self.throughput_samples: List[ThroughputMetrics] = []
        self.accuracy_samples: List[AccuracyMetrics] = []

    def record_latency(self, metrics: LatencyMetrics):
        """記錄延遲數據"""
        self.latency_samples.append(metrics)

    def get_latency_stats(self) -> Dict[str, float]:
        """
        ‹1› 獲取延遲統計
        """
        if not self.latency_samples:
            return {}

        totals = [s.total_ms for s in self.latency_samples]
        return {
            "min": min(totals),
            "max": max(totals),
            "mean": np.mean(totals),
            "p50": np.percentile(totals, 50),
            "p95": np.percentile(totals, 95),
            "p99": np.percentile(totals, 99),
            "std": np.std(totals)
        }

    def identify_bottleneck(self) -> str:
        """
        ‹2› 識別效能瓶頸
        """
        if not self.latency_samples:
            return "insufficient_data"

        # 計算各階段的平均佔比
        breakdowns = [s.breakdown() for s in self.latency_samples[-100:]]
        avg_breakdown = {
            key: np.mean([b[key] for b in breakdowns])
            for key in breakdowns[0].keys()
        }

        # 找出佔比最高的階段
        bottleneck = max(avg_breakdown.items(), key=lambda x: x[1])
        return bottleneck[0]

    def generate_report(self) -> str:
        """
        ‹3› 生成效能報告
        """
        stats = self.get_latency_stats()
        bottleneck = self.identify_bottleneck()

        report = f"""
效能分析報告
============

延遲統計 (ms):
  最小值: {stats.get('min', 0):.2f}
  最大值: {stats.get('max', 0):.2f}
  平均值: {stats.get('mean', 0):.2f}
  P50: {stats.get('p50', 0):.2f}
  P95: {stats.get('p95', 0):.2f}
  P99: {stats.get('p99', 0):.2f}

效能瓶頸: {bottleneck}

優化建議:
"""
        if bottleneck == "embedding":
            report += "  - 考慮使用更快的嵌入模型\n"
            report += "  - 啟用嵌入快取\n"
            report += "  - 使用 GPU 加速嵌入生成\n"
        elif bottleneck == "search":
            report += "  - 優化索引參數（nlist, nprobe）\n"
            report += "  - 考慮使用更快的索引類型（HNSW）\n"
            report += "  - 增加搜尋節點數量\n"
        elif bottleneck == "postprocess":
            report += "  - 減少返回結果數量\n"
            report += "  - 簡化後處理邏輯\n"
            report += "  - 使用更高效的排序算法\n"
        elif bottleneck == "network":
            report += "  - 檢查網絡延遲\n"
            report += "  - 考慮部署在更近的區域\n"
            report += "  - 使用連接池\n"

        return report


def demonstrate_profiling():
    """
    ‹1› 效能分析示範
    """
    print("效能分析示範")
    print("=" * 60)

    profiler = PerformanceProfiler()

    # 模擬收集效能數據
    np.random.seed(42)
    for _ in range(100):
        metrics = LatencyMetrics(
            total_ms=np.random.uniform(50, 200),
            embedding_ms=np.random.uniform(10, 50),
            search_ms=np.random.uniform(20, 100),
            postprocess_ms=np.random.uniform(5, 30),
            network_ms=np.random.uniform(5, 20)
        )
        profiler.record_latency(metrics)

    # 生成報告
    print(profiler.generate_report())


if __name__ == "__main__":
    demonstrate_profiling()
```

---

## 11.2 索引優化

### 11.2.1 索引參數調優

```python
import numpy as np
import time
from typing import Tuple, List, Dict

class IndexOptimizer:
    """
    索引參數優化器

    ‹1› 自動搜尋最佳參數
    ‹2› 平衡精確度和速度
    """

    def __init__(self, dimension: int, n_vectors: int):
        """
        ‹1› 初始化優化器

        Args:
            dimension: 向量維度
            n_vectors: 向量數量
        """
        self.dimension = dimension
        self.n_vectors = n_vectors

    def recommend_ivf_params(
        self,
        target_recall: float = 0.95,
        max_latency_ms: float = 50.0
    ) -> Dict[str, int]:
        """
        ‹2› 推薦 IVF 索引參數

        Args:
            target_recall: 目標召回率
            max_latency_ms: 最大延遲

        Returns:
            推薦的參數
        """
        # nlist 計算規則
        # 建議：4 * sqrt(n) 到 16 * sqrt(n)
        sqrt_n = int(np.sqrt(self.n_vectors))
        nlist_candidates = [
            sqrt_n,
            2 * sqrt_n,
            4 * sqrt_n,
            8 * sqrt_n,
            16 * sqrt_n
        ]

        # 根據數據量選擇 nlist
        if self.n_vectors < 100000:
            nlist = min(nlist_candidates[1], 256)
        elif self.n_vectors < 1000000:
            nlist = min(nlist_candidates[2], 1024)
        else:
            nlist = min(nlist_candidates[3], 4096)

        # nprobe 計算規則
        # 較高召回率需要較大的 nprobe
        if target_recall >= 0.99:
            nprobe = max(nlist // 4, 64)
        elif target_recall >= 0.95:
            nprobe = max(nlist // 8, 32)
        elif target_recall >= 0.90:
            nprobe = max(nlist // 16, 16)
        else:
            nprobe = max(nlist // 32, 8)

        return {
            "nlist": nlist,
            "nprobe": nprobe,
            "estimated_recall": self._estimate_recall(nlist, nprobe)
        }

    def _estimate_recall(self, nlist: int, nprobe: int) -> float:
        """估算召回率"""
        # 簡化的估算公式
        ratio = nprobe / nlist
        return min(0.99, 0.5 + 0.5 * np.sqrt(ratio))

    def recommend_hnsw_params(
        self,
        target_recall: float = 0.95,
        memory_limit_gb: float = 8.0
    ) -> Dict[str, int]:
        """
        ‹3› 推薦 HNSW 索引參數

        Args:
            target_recall: 目標召回率
            memory_limit_gb: 記憶體限制

        Returns:
            推薦的參數
        """
        # M 參數（每個節點的連接數）
        # 較大的 M 提高精確度但增加記憶體
        if target_recall >= 0.99:
            M = 64
        elif target_recall >= 0.95:
            M = 32
        else:
            M = 16

        # efConstruction（建構時的搜尋範圍）
        efConstruction = M * 8  # 經驗值

        # efSearch（搜尋時的候選集大小）
        if target_recall >= 0.99:
            efSearch = 256
        elif target_recall >= 0.95:
            efSearch = 128
        else:
            efSearch = 64

        # 檢查記憶體限制
        estimated_memory_gb = self._estimate_hnsw_memory(M) / (1024 ** 3)
        if estimated_memory_gb > memory_limit_gb:
            # 減小 M
            M = max(8, int(M * memory_limit_gb / estimated_memory_gb))
            efConstruction = M * 8

        return {
            "M": M,
            "efConstruction": efConstruction,
            "efSearch": efSearch,
            "estimated_memory_gb": self._estimate_hnsw_memory(M) / (1024 ** 3)
        }

    def _estimate_hnsw_memory(self, M: int) -> int:
        """估算 HNSW 記憶體使用（bytes）"""
        # 向量存儲 + 圖結構
        vector_memory = self.n_vectors * self.dimension * 4  # float32
        graph_memory = self.n_vectors * M * 2 * 8  # 每個連接 8 bytes
        return vector_memory + graph_memory

    def recommend_pq_params(
        self,
        target_compression: float = 8.0,
        min_recall: float = 0.85
    ) -> Dict[str, int]:
        """
        ‹4› 推薦 PQ 索引參數

        Args:
            target_compression: 目標壓縮比
            min_recall: 最低召回率

        Returns:
            推薦的參數
        """
        # m（子空間數）
        # dimension 必須能被 m 整除
        possible_m = [d for d in range(4, min(65, self.dimension + 1))
                     if self.dimension % d == 0]

        # 根據壓縮比選擇 m
        # 壓縮比 ≈ dimension * 4 / m
        target_m = self.dimension * 4 / target_compression

        # 找最接近的 m
        m = min(possible_m, key=lambda x: abs(x - target_m))

        # nbits（每個子空間的位元數）
        # 通常使用 8（256 個聚類中心）
        nbits = 8

        actual_compression = self.dimension * 4 / m

        return {
            "m": m,
            "nbits": nbits,
            "compression_ratio": actual_compression,
            "memory_per_vector_bytes": m * nbits // 8
        }


def demonstrate_index_optimization():
    """
    ‹1› 索引優化示範
    """
    print("索引參數優化")
    print("=" * 60)

    optimizer = IndexOptimizer(dimension=768, n_vectors=1000000)

    # IVF 參數推薦
    print("\nIVF 索引推薦參數:")
    print("-" * 40)
    for target_recall in [0.90, 0.95, 0.99]:
        params = optimizer.recommend_ivf_params(target_recall=target_recall)
        print(f"  目標召回率 {target_recall:.0%}:")
        print(f"    nlist: {params['nlist']}")
        print(f"    nprobe: {params['nprobe']}")
        print(f"    預估召回率: {params['estimated_recall']:.2%}")
        print()

    # HNSW 參數推薦
    print("HNSW 索引推薦參數:")
    print("-" * 40)
    for target_recall in [0.90, 0.95, 0.99]:
        params = optimizer.recommend_hnsw_params(target_recall=target_recall)
        print(f"  目標召回率 {target_recall:.0%}:")
        print(f"    M: {params['M']}")
        print(f"    efConstruction: {params['efConstruction']}")
        print(f"    efSearch: {params['efSearch']}")
        print(f"    預估記憶體: {params['estimated_memory_gb']:.2f} GB")
        print()

    # PQ 參數推薦
    print("PQ 索引推薦參數:")
    print("-" * 40)
    for target_compression in [4, 8, 16, 32]:
        params = optimizer.recommend_pq_params(target_compression=target_compression)
        print(f"  目標壓縮比 {target_compression}x:")
        print(f"    m: {params['m']}")
        print(f"    實際壓縮比: {params['compression_ratio']:.1f}x")
        print(f"    每向量記憶體: {params['memory_per_vector_bytes']} bytes")
        print()


if __name__ == "__main__":
    demonstrate_index_optimization()
```

### 11.2.2 索引熱身與預載入

```python
import time
import numpy as np
from typing import List

class IndexWarmup:
    """
    索引熱身

    ‹1› 預載入索引到記憶體
    ‹2› 預熱快取
    ‹3› JIT 編譯優化
    """

    def __init__(self, index):
        """
        ‹1› 初始化

        Args:
            index: 向量索引實例
        """
        self.index = index
        self.warmup_queries = []

    def generate_warmup_queries(
        self,
        n_queries: int = 100,
        dimension: int = 768
    ) -> np.ndarray:
        """
        ‹2› 生成熱身查詢

        使用隨機查詢或歷史熱門查詢
        """
        return np.random.randn(n_queries, dimension).astype(np.float32)

    def warmup(
        self,
        queries: np.ndarray = None,
        top_k: int = 10,
        rounds: int = 3
    ) -> Dict[str, float]:
        """
        ‹3› 執行熱身

        Args:
            queries: 熱身查詢（可選）
            top_k: 搜尋 top-k
            rounds: 熱身輪數

        Returns:
            熱身統計
        """
        if queries is None:
            queries = self.generate_warmup_queries()

        print(f"開始索引熱身...")
        print(f"  查詢數量: {len(queries)}")
        print(f"  熱身輪數: {rounds}")

        latencies = []

        for round_idx in range(rounds):
            round_start = time.perf_counter()

            for query in queries:
                start = time.perf_counter()
                # 執行搜尋（這裡是模擬）
                # self.index.search(query.reshape(1, -1), top_k)
                time.sleep(0.001)  # 模擬搜尋
                latencies.append(time.perf_counter() - start)

            round_time = time.perf_counter() - round_start
            print(f"  第 {round_idx + 1} 輪完成: {round_time:.2f}s")

        # 統計
        latencies = np.array(latencies)
        stats = {
            "total_queries": len(latencies),
            "avg_latency_ms": np.mean(latencies) * 1000,
            "p99_latency_ms": np.percentile(latencies, 99) * 1000,
            "improvement": (latencies[:len(queries)].mean() -
                          latencies[-len(queries):].mean()) / latencies[:len(queries)].mean()
        }

        print(f"\n熱身完成:")
        print(f"  平均延遲: {stats['avg_latency_ms']:.2f}ms")
        print(f"  P99 延遲: {stats['p99_latency_ms']:.2f}ms")
        print(f"  效能提升: {stats['improvement']:.1%}")

        return stats


def demonstrate_warmup():
    """
    ‹1› 索引熱身示範
    """
    print("索引熱身示範")
    print("=" * 60)

    warmup = IndexWarmup(index=None)
    queries = warmup.generate_warmup_queries(n_queries=50, dimension=768)
    stats = warmup.warmup(queries, top_k=10, rounds=3)


if __name__ == "__main__":
    demonstrate_warmup()
```

---

## 11.3 查詢優化

### 11.3.1 查詢向量化優化

```python
import numpy as np
from typing import List, Dict, Any
import time

class EmbeddingOptimizer:
    """
    嵌入生成優化

    ‹1› 批量處理
    ‹2› 快取策略
    ‹3› 模型選擇
    """

    def __init__(self, cache_size: int = 10000):
        """
        ‹1› 初始化

        Args:
            cache_size: 嵌入快取大小
        """
        self.cache: Dict[str, np.ndarray] = {}
        self.cache_size = cache_size
        self.cache_hits = 0
        self.cache_misses = 0

    def get_embedding(
        self,
        text: str,
        model: str = "default"
    ) -> np.ndarray:
        """
        ‹2› 獲取文字嵌入（帶快取）
        """
        cache_key = f"{model}:{hash(text)}"

        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]

        self.cache_misses += 1

        # 生成嵌入（模擬）
        embedding = np.random.randn(768).astype(np.float32)

        # 快取
        if len(self.cache) >= self.cache_size:
            # LRU 淘汰
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[cache_key] = embedding
        return embedding

    def batch_get_embeddings(
        self,
        texts: List[str],
        model: str = "default",
        batch_size: int = 32
    ) -> np.ndarray:
        """
        ‹3› 批量獲取嵌入

        批量處理可以顯著提升效能
        """
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        # 先檢查快取
        for i, text in enumerate(texts):
            cache_key = f"{model}:{hash(text)}"
            if cache_key in self.cache:
                embeddings.append((i, self.cache[cache_key]))
                self.cache_hits += 1
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
                self.cache_misses += 1

        # 批量生成未快取的嵌入
        if uncached_texts:
            for batch_start in range(0, len(uncached_texts), batch_size):
                batch_texts = uncached_texts[batch_start:batch_start + batch_size]
                # 模擬批量嵌入生成
                batch_embeddings = np.random.randn(len(batch_texts), 768).astype(np.float32)

                for j, emb in enumerate(batch_embeddings):
                    idx = uncached_indices[batch_start + j]
                    text = uncached_texts[batch_start + j]
                    embeddings.append((idx, emb))

                    # 快取
                    cache_key = f"{model}:{hash(text)}"
                    self.cache[cache_key] = emb

        # 按原始順序排序
        embeddings.sort(key=lambda x: x[0])
        return np.array([e[1] for e in embeddings])

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        ‹4› 獲取快取統計
        """
        total = self.cache_hits + self.cache_misses
        return {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / total if total > 0 else 0
        }


def demonstrate_embedding_optimization():
    """
    ‹1› 嵌入優化示範
    """
    print("嵌入生成優化")
    print("=" * 60)

    optimizer = EmbeddingOptimizer(cache_size=1000)

    # 模擬查詢
    texts = [f"query_{i}" for i in range(100)]
    # 重複一些查詢以測試快取
    texts += [f"query_{i}" for i in range(50)]

    print(f"查詢數量: {len(texts)}")
    print(f"唯一查詢: 100")
    print(f"重複查詢: 50")

    # 批量處理
    start = time.perf_counter()
    embeddings = optimizer.batch_get_embeddings(texts, batch_size=32)
    elapsed = time.perf_counter() - start

    print(f"\n處理時間: {elapsed*1000:.2f}ms")
    print(f"每查詢平均: {elapsed/len(texts)*1000:.3f}ms")

    # 快取統計
    stats = optimizer.get_cache_stats()
    print(f"\n快取統計:")
    print(f"  命中: {stats['cache_hits']}")
    print(f"  未命中: {stats['cache_misses']}")
    print(f"  命中率: {stats['hit_rate']:.2%}")


if __name__ == "__main__":
    demonstrate_embedding_optimization()
```

### 11.3.2 結果重排序優化

```python
from typing import List, Tuple
import numpy as np

class RerankerOptimizer:
    """
    重排序優化

    ‹1› 兩階段檢索
    ‹2› 輕量級重排序
    ‹3› 批量重排序
    """

    def __init__(self):
        self.stats = {
            "total_reranked": 0,
            "avg_improvement": 0
        }

    def two_stage_search(
        self,
        query_vector: np.ndarray,
        database: np.ndarray,
        first_stage_k: int = 100,
        final_k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        ‹1› 兩階段檢索

        第一階段：快速召回
        第二階段：精確重排序
        """
        # 第一階段：使用近似搜尋召回候選
        # （這裡使用精確搜尋模擬）
        distances = np.linalg.norm(database - query_vector, axis=1)
        first_stage_indices = np.argpartition(distances, first_stage_k)[:first_stage_k]

        # 第二階段：對候選進行精確排序
        candidates = database[first_stage_indices]
        candidate_distances = distances[first_stage_indices]

        # 排序
        sorted_indices = np.argsort(candidate_distances)[:final_k]

        results = [
            (first_stage_indices[i], candidate_distances[i])
            for i in sorted_indices
        ]

        return results

    def lightweight_rerank(
        self,
        query: str,
        candidates: List[Tuple[int, float, str]],
        top_k: int = 10
    ) -> List[Tuple[int, float, str]]:
        """
        ‹2› 輕量級重排序

        使用簡單的啟發式規則重排序
        避免使用昂貴的 cross-encoder
        """
        reranked = []

        for idx, score, content in candidates:
            # 計算額外的相關性信號
            bonus = 0

            # 關鍵詞匹配加分
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            overlap = len(query_words & content_words)
            bonus += overlap * 0.05

            # 內容長度適中加分
            word_count = len(content.split())
            if 50 <= word_count <= 500:
                bonus += 0.02

            # 計算最終分數
            final_score = score + bonus
            reranked.append((idx, final_score, content))

        # 排序
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked[:top_k]

    def batch_rerank(
        self,
        queries: List[str],
        all_candidates: List[List[Tuple[int, float, str]]],
        top_k: int = 10
    ) -> List[List[Tuple[int, float, str]]]:
        """
        ‹3› 批量重排序

        並行處理多個查詢的重排序
        """
        results = []
        for query, candidates in zip(queries, all_candidates):
            reranked = self.lightweight_rerank(query, candidates, top_k)
            results.append(reranked)
            self.stats["total_reranked"] += len(candidates)

        return results


def demonstrate_reranking():
    """
    ‹1› 重排序優化示範
    """
    print("重排序優化")
    print("=" * 60)

    optimizer = RerankerOptimizer()

    # 模擬候選結果
    candidates = [
        (0, 0.85, "向量資料庫是一種專門用於存儲和搜尋向量的資料庫系統"),
        (1, 0.82, "FAISS 是 Facebook 開發的向量搜尋函式庫"),
        (2, 0.80, "Milvus 是一個開源的向量資料庫"),
        (3, 0.78, "向量搜尋在推薦系統中有廣泛應用"),
        (4, 0.75, "嵌入模型可以將文字轉換為向量"),
    ]

    query = "向量資料庫"

    print(f"查詢: {query}")
    print(f"\n原始排序:")
    for idx, score, content in candidates:
        print(f"  [{idx}] {score:.2f}: {content[:30]}...")

    # 重排序
    reranked = optimizer.lightweight_rerank(query, candidates, top_k=3)

    print(f"\n重排序後:")
    for idx, score, content in reranked:
        print(f"  [{idx}] {score:.2f}: {content[:30]}...")


if __name__ == "__main__":
    demonstrate_reranking()
```

---

## 11.4 系統監控

### 11.4.1 監控儀表板設計

```python
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import time

@dataclass
class DashboardMetric:
    """儀表板指標"""
    name: str
    value: float
    unit: str
    trend: str  # up, down, stable
    health: str  # healthy, warning, critical


class MonitoringDashboard:
    """
    監控儀表板

    ‹1› 實時指標展示
    ‹2› 趨勢分析
    ‹3› 健康狀態
    """

    def __init__(self):
        self.metrics_history: Dict[str, List[float]] = {}
        self.thresholds = {
            "latency_p99_ms": {"warning": 100, "critical": 500},
            "error_rate": {"warning": 0.01, "critical": 0.05},
            "cpu_usage": {"warning": 70, "critical": 90},
            "memory_usage": {"warning": 80, "critical": 95},
            "qps": {"warning": 1000, "critical": 2000}  # 這是下限
        }

    def record_metric(self, name: str, value: float):
        """
        ‹1› 記錄指標
        """
        if name not in self.metrics_history:
            self.metrics_history[name] = []
        self.metrics_history[name].append(value)
        # 只保留最近 1000 個樣本
        if len(self.metrics_history[name]) > 1000:
            self.metrics_history[name].pop(0)

    def get_current_metrics(self) -> List[DashboardMetric]:
        """
        ‹2› 獲取當前指標
        """
        metrics = []

        for name, history in self.metrics_history.items():
            if not history:
                continue

            current = history[-1]
            trend = self._calculate_trend(history)
            health = self._evaluate_health(name, current)

            unit = self._get_unit(name)

            metrics.append(DashboardMetric(
                name=name,
                value=current,
                unit=unit,
                trend=trend,
                health=health
            ))

        return metrics

    def _calculate_trend(self, history: List[float]) -> str:
        """計算趨勢"""
        if len(history) < 10:
            return "stable"

        recent = history[-10:]
        older = history[-20:-10] if len(history) >= 20 else history[:10]

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        change = (recent_avg - older_avg) / older_avg if older_avg != 0 else 0

        if change > 0.1:
            return "up"
        elif change < -0.1:
            return "down"
        else:
            return "stable"

    def _evaluate_health(self, name: str, value: float) -> str:
        """評估健康狀態"""
        if name not in self.thresholds:
            return "healthy"

        thresholds = self.thresholds[name]

        # QPS 是越高越好
        if name == "qps":
            if value < thresholds["critical"]:
                return "critical"
            elif value < thresholds["warning"]:
                return "warning"
            return "healthy"

        # 其他指標越低越好
        if value >= thresholds["critical"]:
            return "critical"
        elif value >= thresholds["warning"]:
            return "warning"
        return "healthy"

    def _get_unit(self, name: str) -> str:
        """獲取單位"""
        units = {
            "latency_p99_ms": "ms",
            "error_rate": "%",
            "cpu_usage": "%",
            "memory_usage": "%",
            "qps": "req/s",
            "vector_count": "vectors"
        }
        return units.get(name, "")

    def render_dashboard(self) -> str:
        """
        ‹3› 渲染儀表板
        """
        metrics = self.get_current_metrics()

        output = []
        output.append("=" * 70)
        output.append("向量搜尋系統監控儀表板")
        output.append(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("=" * 70)
        output.append("")

        # 健康概覽
        health_counts = {"healthy": 0, "warning": 0, "critical": 0}
        for m in metrics:
            health_counts[m.health] += 1

        output.append("系統健康狀態:")
        output.append(f"  [OK] 正常: {health_counts['healthy']}")
        output.append(f"  [!] 警告: {health_counts['warning']}")
        output.append(f"  [X] 嚴重: {health_counts['critical']}")
        output.append("")

        # 指標詳情
        output.append("指標詳情:")
        output.append("-" * 70)
        output.append(f"{'指標名稱':<25} {'數值':<15} {'趨勢':<10} {'狀態':<10}")
        output.append("-" * 70)

        for m in metrics:
            trend_symbol = {"up": "↑", "down": "↓", "stable": "→"}[m.trend]
            health_symbol = {"healthy": "[OK]", "warning": "[!]", "critical": "[X]"}[m.health]

            value_str = f"{m.value:.2f} {m.unit}"
            output.append(f"{m.name:<25} {value_str:<15} {trend_symbol:<10} {health_symbol:<10}")

        output.append("-" * 70)

        return "\n".join(output)


def demonstrate_dashboard():
    """
    ‹1› 儀表板示範
    """
    print("監控儀表板示範")
    print()

    dashboard = MonitoringDashboard()

    # 模擬記錄指標
    import random
    for _ in range(100):
        dashboard.record_metric("latency_p99_ms", random.uniform(30, 80))
        dashboard.record_metric("error_rate", random.uniform(0, 0.02))
        dashboard.record_metric("cpu_usage", random.uniform(40, 75))
        dashboard.record_metric("memory_usage", random.uniform(50, 85))
        dashboard.record_metric("qps", random.uniform(800, 1500))
        dashboard.record_metric("vector_count", 1000000 + random.randint(-1000, 1000))

    # 渲染儀表板
    print(dashboard.render_dashboard())


if __name__ == "__main__":
    demonstrate_dashboard()
```

### 11.4.2 告警配置

```python
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum
import time

class AlertSeverity(Enum):
    """告警嚴重程度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警狀態"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class AlertRule:
    """告警規則"""
    name: str
    metric: str
    condition: str  # gt, lt, eq
    threshold: float
    severity: AlertSeverity
    duration_seconds: int  # 持續多久才告警
    message_template: str


@dataclass
class Alert:
    """告警實例"""
    rule_name: str
    severity: AlertSeverity
    message: str
    value: float
    status: AlertStatus
    triggered_at: float
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None


class AlertManager:
    """
    告警管理器

    ‹1› 規則評估
    ‹2› 告警觸發與恢復
    ‹3› 通知發送
    """

    def __init__(self):
        self.rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.pending_alerts: Dict[str, float] = {}  # rule_name -> first_triggered_time

        # 通知處理器
        self.notifiers: List[Callable[[Alert], None]] = []

    def add_rule(self, rule: AlertRule):
        """
        ‹1› 添加告警規則
        """
        self.rules.append(rule)
        print(f"添加規則: {rule.name}")

    def add_notifier(self, notifier: Callable[[Alert], None]):
        """
        ‹2› 添加通知處理器
        """
        self.notifiers.append(notifier)

    def evaluate(self, metrics: Dict[str, float]):
        """
        ‹3› 評估所有規則
        """
        current_time = time.time()

        for rule in self.rules:
            if rule.metric not in metrics:
                continue

            value = metrics[rule.metric]
            is_triggered = self._check_condition(value, rule.condition, rule.threshold)

            if is_triggered:
                self._handle_triggered(rule, value, current_time)
            else:
                self._handle_resolved(rule, current_time)

    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """檢查條件"""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "eq":
            return abs(value - threshold) < 0.001
        return False

    def _handle_triggered(self, rule: AlertRule, value: float, current_time: float):
        """處理觸發"""
        if rule.name not in self.pending_alerts:
            self.pending_alerts[rule.name] = current_time

        pending_duration = current_time - self.pending_alerts[rule.name]

        # 檢查是否超過持續時間閾值
        if pending_duration >= rule.duration_seconds:
            if rule.name not in self.active_alerts:
                # 創建新告警
                message = rule.message_template.format(
                    value=value,
                    threshold=rule.threshold
                )
                alert = Alert(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=message,
                    value=value,
                    status=AlertStatus.ACTIVE,
                    triggered_at=current_time
                )
                self.active_alerts[rule.name] = alert
                self._notify(alert)

    def _handle_resolved(self, rule: AlertRule, current_time: float):
        """處理恢復"""
        # 清除 pending
        if rule.name in self.pending_alerts:
            del self.pending_alerts[rule.name]

        # 恢復 active 告警
        if rule.name in self.active_alerts:
            alert = self.active_alerts[rule.name]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = current_time
            self.alert_history.append(alert)
            del self.active_alerts[rule.name]
            print(f"[RESOLVED] {rule.name}")

    def _notify(self, alert: Alert):
        """發送通知"""
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨"
        }

        print(f"\n{severity_emoji[alert.severity]} [{alert.severity.value.upper()}] {alert.rule_name}")
        print(f"   {alert.message}")
        print()

        for notifier in self.notifiers:
            try:
                notifier(alert)
            except Exception as e:
                print(f"通知發送失敗: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """獲取活躍告警"""
        return list(self.active_alerts.values())


def demonstrate_alerting():
    """
    ‹1› 告警示範
    """
    print("告警系統示範")
    print("=" * 60)

    manager = AlertManager()

    # 添加告警規則
    manager.add_rule(AlertRule(
        name="高延遲告警",
        metric="latency_p99_ms",
        condition="gt",
        threshold=100,
        severity=AlertSeverity.WARNING,
        duration_seconds=2,
        message_template="P99 延遲 ({value:.2f}ms) 超過閾值 ({threshold}ms)"
    ))

    manager.add_rule(AlertRule(
        name="錯誤率告警",
        metric="error_rate",
        condition="gt",
        threshold=0.05,
        severity=AlertSeverity.CRITICAL,
        duration_seconds=1,
        message_template="錯誤率 ({value:.2%}) 超過閾值 ({threshold:.2%})"
    ))

    manager.add_rule(AlertRule(
        name="CPU 使用率告警",
        metric="cpu_usage",
        condition="gt",
        threshold=90,
        severity=AlertSeverity.WARNING,
        duration_seconds=3,
        message_template="CPU 使用率 ({value:.1f}%) 超過閾值 ({threshold}%)"
    ))

    # 模擬指標
    print("\n模擬指標評估:")
    print("-" * 40)

    # 正常指標
    manager.evaluate({
        "latency_p99_ms": 50,
        "error_rate": 0.01,
        "cpu_usage": 60
    })
    print("正常指標 - 無告警")

    # 延遲升高
    time.sleep(1)
    manager.evaluate({
        "latency_p99_ms": 150,
        "error_rate": 0.01,
        "cpu_usage": 60
    })
    print("延遲升高中...")

    time.sleep(2)
    manager.evaluate({
        "latency_p99_ms": 150,
        "error_rate": 0.01,
        "cpu_usage": 60
    })

    # 恢復
    time.sleep(1)
    manager.evaluate({
        "latency_p99_ms": 50,
        "error_rate": 0.01,
        "cpu_usage": 60
    })


if __name__ == "__main__":
    demonstrate_alerting()
```

---

## 11.5 負載測試與容量規劃

### 11.5.1 負載測試框架

```python
import numpy as np
import time
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

@dataclass
class LoadTestConfig:
    """負載測試配置"""
    duration_seconds: int
    target_qps: int
    ramp_up_seconds: int
    num_workers: int


@dataclass
class LoadTestResult:
    """負載測試結果"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    actual_qps: float
    error_rate: float


class LoadTester:
    """
    負載測試器

    ‹1› 模擬真實負載
    ‹2› 收集效能指標
    ‹3› 生成測試報告
    """

    def __init__(
        self,
        target_function: Callable[[], bool],
        config: LoadTestConfig
    ):
        """
        ‹1› 初始化

        Args:
            target_function: 要測試的函數，返回 True 表示成功
            config: 測試配置
        """
        self.target_function = target_function
        self.config = config

        self.results: List[Dict[str, Any]] = []
        self.results_lock = threading.Lock()
        self.stop_event = threading.Event()

    def run(self) -> LoadTestResult:
        """
        ‹2› 執行負載測試
        """
        print(f"開始負載測試")
        print(f"  目標 QPS: {self.config.target_qps}")
        print(f"  持續時間: {self.config.duration_seconds}s")
        print(f"  工作執行緒: {self.config.num_workers}")
        print()

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.config.num_workers) as executor:
            # 提交任務
            futures = []
            request_count = 0
            interval = 1.0 / self.config.target_qps

            while time.time() - start_time < self.config.duration_seconds:
                if self.stop_event.is_set():
                    break

                # Ramp up
                elapsed = time.time() - start_time
                if elapsed < self.config.ramp_up_seconds:
                    current_interval = interval * (self.config.ramp_up_seconds / max(elapsed, 0.1))
                else:
                    current_interval = interval

                futures.append(executor.submit(self._execute_request, request_count))
                request_count += 1

                time.sleep(current_interval)

                # 定期輸出進度
                if request_count % 100 == 0:
                    print(f"  已發送 {request_count} 請求...")

            # 等待所有請求完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"請求執行錯誤: {e}")

        # 計算結果
        return self._calculate_results(start_time)

    def _execute_request(self, request_id: int):
        """執行單個請求"""
        start = time.perf_counter()
        try:
            success = self.target_function()
            latency = (time.perf_counter() - start) * 1000

            with self.results_lock:
                self.results.append({
                    "request_id": request_id,
                    "success": success,
                    "latency_ms": latency,
                    "timestamp": time.time()
                })
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            with self.results_lock:
                self.results.append({
                    "request_id": request_id,
                    "success": False,
                    "latency_ms": latency,
                    "error": str(e),
                    "timestamp": time.time()
                })

    def _calculate_results(self, start_time: float) -> LoadTestResult:
        """計算測試結果"""
        if not self.results:
            return LoadTestResult(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                actual_qps=0,
                error_rate=0
            )

        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful
        latencies = [r["latency_ms"] for r in self.results]

        duration = time.time() - start_time

        return LoadTestResult(
            total_requests=total,
            successful_requests=successful,
            failed_requests=failed,
            avg_latency_ms=np.mean(latencies),
            p50_latency_ms=np.percentile(latencies, 50),
            p95_latency_ms=np.percentile(latencies, 95),
            p99_latency_ms=np.percentile(latencies, 99),
            actual_qps=total / duration,
            error_rate=failed / total if total > 0 else 0
        )


def demonstrate_load_testing():
    """
    ‹1› 負載測試示範
    """
    print("負載測試示範")
    print("=" * 60)

    # 模擬目標函數
    def mock_search():
        time.sleep(np.random.uniform(0.01, 0.05))
        return np.random.random() > 0.02  # 2% 錯誤率

    config = LoadTestConfig(
        duration_seconds=5,
        target_qps=50,
        ramp_up_seconds=1,
        num_workers=10
    )

    tester = LoadTester(mock_search, config)
    result = tester.run()

    print("\n負載測試結果:")
    print("-" * 40)
    print(f"總請求數: {result.total_requests}")
    print(f"成功請求: {result.successful_requests}")
    print(f"失敗請求: {result.failed_requests}")
    print(f"錯誤率: {result.error_rate:.2%}")
    print(f"實際 QPS: {result.actual_qps:.2f}")
    print()
    print("延遲統計 (ms):")
    print(f"  平均: {result.avg_latency_ms:.2f}")
    print(f"  P50: {result.p50_latency_ms:.2f}")
    print(f"  P95: {result.p95_latency_ms:.2f}")
    print(f"  P99: {result.p99_latency_ms:.2f}")


if __name__ == "__main__":
    demonstrate_load_testing()
```

### 11.5.2 容量規劃

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class CapacityRequirements:
    """容量需求"""
    vector_count: int
    dimension: int
    qps_target: int
    latency_target_ms: float
    recall_target: float
    availability_target: float


class CapacityPlanner:
    """
    容量規劃器

    ‹1› 估算資源需求
    ‹2› 推薦架構配置
    ‹3› 成本估算
    """

    def __init__(self, requirements: CapacityRequirements):
        """
        ‹1› 初始化

        Args:
            requirements: 容量需求
        """
        self.requirements = requirements

    def estimate_memory(self) -> Dict[str, float]:
        """
        ‹2› 估算記憶體需求
        """
        r = self.requirements

        # 原始向量記憶體
        raw_memory_gb = r.vector_count * r.dimension * 4 / (1024 ** 3)

        # 不同索引類型的記憶體需求
        estimates = {
            "FLAT": raw_memory_gb,
            "IVF_FLAT": raw_memory_gb * 1.05,  # 5% 額外開銷
            "IVF_PQ": raw_memory_gb * 0.15,    # 約 85% 壓縮
            "HNSW": raw_memory_gb * 1.5,       # 50% 圖結構開銷
        }

        return estimates

    def estimate_nodes(self) -> Dict[str, int]:
        """
        ‹3› 估算節點數量
        """
        r = self.requirements

        # 基於 QPS 估算
        # 假設單節點可處理 1000 QPS
        qps_based = max(1, r.qps_target // 1000)

        # 基於記憶體估算（假設每節點 32GB 可用）
        memory_gb = r.vector_count * r.dimension * 4 / (1024 ** 3)
        memory_based = max(1, int(memory_gb / 32) + 1)

        # 基於可用性（至少需要 3 個副本達到 99.9%）
        if r.availability_target >= 0.999:
            min_replicas = 3
        elif r.availability_target >= 0.99:
            min_replicas = 2
        else:
            min_replicas = 1

        return {
            "qps_based": qps_based,
            "memory_based": memory_based,
            "min_replicas": min_replicas,
            "recommended": max(qps_based, memory_based) * min_replicas
        }

    def recommend_index(self) -> str:
        """
        ‹4› 推薦索引類型
        """
        r = self.requirements

        if r.recall_target >= 0.99:
            if r.latency_target_ms >= 100:
                return "IVF_FLAT"
            else:
                return "HNSW"
        elif r.recall_target >= 0.95:
            if r.vector_count > 10_000_000:
                return "IVF_PQ"
            else:
                return "HNSW"
        else:
            return "IVF_PQ"

    def generate_plan(self) -> str:
        """
        ‹5› 生成容量規劃報告
        """
        r = self.requirements
        memory = self.estimate_memory()
        nodes = self.estimate_nodes()
        index = self.recommend_index()

        plan = f"""
容量規劃報告
============

需求摘要:
- 向量數量: {r.vector_count:,}
- 向量維度: {r.dimension}
- 目標 QPS: {r.qps_target:,}
- 目標延遲: {r.latency_target_ms}ms
- 目標召回率: {r.recall_target:.2%}
- 目標可用性: {r.availability_target:.2%}

記憶體估算:
- FLAT 索引: {memory['FLAT']:.2f} GB
- IVF_FLAT 索引: {memory['IVF_FLAT']:.2f} GB
- IVF_PQ 索引: {memory['IVF_PQ']:.2f} GB
- HNSW 索引: {memory['HNSW']:.2f} GB

節點估算:
- 基於 QPS: {nodes['qps_based']} 節點
- 基於記憶體: {nodes['memory_based']} 節點
- 最小副本數: {nodes['min_replicas']}
- 推薦總節點: {nodes['recommended']} 節點

推薦配置:
- 索引類型: {index}
- 節點規格: 32GB 記憶體, 8 vCPU
- 總節點數: {nodes['recommended']}
- 預估月成本: ${nodes['recommended'] * 500:,}（基於雲端定價）

注意事項:
- 建議預留 20% 的資源餘量
- 高峰期可能需要自動擴縮容
- 定期監控資源使用率
"""
        return plan


def demonstrate_capacity_planning():
    """
    ‹1› 容量規劃示範
    """
    print("容量規劃示範")
    print("=" * 60)

    requirements = CapacityRequirements(
        vector_count=10_000_000,
        dimension=768,
        qps_target=5000,
        latency_target_ms=50,
        recall_target=0.95,
        availability_target=0.999
    )

    planner = CapacityPlanner(requirements)
    print(planner.generate_plan())


if __name__ == "__main__":
    demonstrate_capacity_planning()
```

---

## 11.6 本章回顧

### 核心要點

1. **效能指標**
   - 延遲：P50、P95、P99
   - 吞吐量：QPS
   - 精確度：Recall、Precision

2. **索引優化**
   - IVF 參數：nlist、nprobe
   - HNSW 參數：M、efConstruction、efSearch
   - PQ 參數：m、nbits

3. **查詢優化**
   - 嵌入快取
   - 批量處理
   - 兩階段檢索

4. **監控告警**
   - 關鍵指標監控
   - 閾值告警
   - 趨勢分析

5. **容量規劃**
   - 資源估算
   - 節點規劃
   - 成本預估

### 最佳實踐

- 定期進行負載測試
- 監控 P99 延遲而非平均延遲
- 預留 20% 的資源餘量
- 建立完整的監控告警體系

---

## 思考題

1. 如何在不影響線上服務的情況下進行索引參數調優？

2. 當系統延遲突然升高時，應該如何快速定位問題？

3. 如何設計一個自適應的快取策略，根據查詢熱度動態調整？

4. 在多租戶場景下，如何確保各租戶的效能隔離？

5. 如何平衡監控的粒度和監控本身的開銷？

---

下一章，我們將通過一個完整的自動駕駛感知系統案例，展示向量搜尋技術的實際應用。
