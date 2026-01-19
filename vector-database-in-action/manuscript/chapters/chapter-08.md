# Chapter 8：FAISS 向量檢索引擎

> 「FAISS 就像是向量世界的瑞士軍刀——無論你的需求是速度、精確度還是記憶體效率，它都有對應的解決方案。」

## 學習目標

完成本章後，你將能夠：

- 理解 FAISS 的核心架構與設計理念
- 掌握各種 FAISS 索引的特性與適用場景
- 學會根據數據規模選擇最適合的索引類型
- 實作高效的向量檢索系統
- 優化 FAISS 的效能與記憶體使用

---

## 8.1 FAISS 簡介

FAISS（Facebook AI Similarity Search）是 Facebook AI Research 開發的高效向量相似性搜尋函式庫。它專為處理大規模向量數據設計，能夠在數十億向量中進行毫秒級的相似性搜尋。

### 8.1.1 為什麼選擇 FAISS

```python
"""
FAISS 的核心優勢展示

‹1› 效能：比純 Python 實作快 100-1000 倍
‹2› 規模：支援數十億向量的索引
‹3› 靈活：提供多種索引類型滿足不同需求
‹4› GPU 支援：可利用 GPU 加速搜尋
"""

import numpy as np
import time

# 首先展示為什麼需要 FAISS
def naive_search(database: np.ndarray, query: np.ndarray, k: int = 10):
    """
    ‹1› 純 Python 的暴力搜尋

    計算查詢向量與所有資料庫向量的距離
    這是最簡單但最慢的方式
    """
    distances = np.linalg.norm(database - query, axis=1)
    indices = np.argpartition(distances, k)[:k]
    indices = indices[np.argsort(distances[indices])]
    return indices, distances[indices]


def demonstrate_why_faiss():
    """
    展示為什麼需要專門的向量搜尋引擎
    """
    print("為什麼需要 FAISS？")
    print("=" * 60)

    np.random.seed(42)

    # 不同規模的測試
    scales = [10000, 100000, 1000000]
    dim = 128

    for n in scales:
        # 生成測試數據
        database = np.random.randn(n, dim).astype(np.float32)
        query = np.random.randn(dim).astype(np.float32)

        # 測試暴力搜尋
        start = time.perf_counter()
        _ = naive_search(database, query, k=10)
        naive_time = time.perf_counter() - start

        print(f"數據量: {n:>10,} 向量 | 暴力搜尋: {naive_time*1000:>8.2f} ms")

    print()
    print("隨著數據量增長，暴力搜尋變得不可接受")
    print("FAISS 使用近似最近鄰（ANN）演算法解決這個問題")


if __name__ == "__main__":
    demonstrate_why_faiss()
```

### 8.1.2 安裝 FAISS

```bash
# CPU 版本
pip install faiss-cpu

# GPU 版本（需要 CUDA）
pip install faiss-gpu

# 使用 Conda（推薦，更穩定）
conda install -c pytorch faiss-cpu
# 或
conda install -c pytorch faiss-gpu
```

### 8.1.3 FAISS 的基本使用

```python
import faiss
import numpy as np

class FAISSBasicExample:
    """
    FAISS 基本使用範例

    ‹1› 展示最簡單的 FAISS 工作流程
    """

    def __init__(self, dimension: int):
        """
        ‹1› 初始化

        Args:
            dimension: 向量維度
        """
        self.dimension = dimension
        self.index = None

    def create_flat_index(self):
        """
        ‹2› 創建最基本的平面索引

        IndexFlatL2：使用 L2 距離的暴力搜尋
        這是最精確但最慢的索引類型
        """
        self.index = faiss.IndexFlatL2(self.dimension)
        print(f"創建了 {self.dimension} 維的平面索引")
        print(f"索引是否已訓練: {self.index.is_trained}")  # Flat 索引不需要訓練

    def add_vectors(self, vectors: np.ndarray):
        """
        ‹3› 添加向量到索引

        Args:
            vectors: 要添加的向量，shape (n, dimension)
        """
        # FAISS 要求 float32 類型
        vectors = vectors.astype(np.float32)

        # 確保維度正確
        assert vectors.shape[1] == self.dimension, \
            f"維度不匹配: 期望 {self.dimension}, 實際 {vectors.shape[1]}"

        # 添加向量
        self.index.add(vectors)
        print(f"添加了 {len(vectors)} 個向量，目前總數: {self.index.ntotal}")

    def search(self, query: np.ndarray, k: int = 10):
        """
        ‹4› 搜尋最相似的向量

        Args:
            query: 查詢向量，shape (1, dimension) 或 (dimension,)
            k: 返回的最近鄰數量

        Returns:
            distances: 距離，shape (1, k)
            indices: 索引，shape (1, k)
        """
        # 確保查詢是 2D
        if query.ndim == 1:
            query = query.reshape(1, -1)

        query = query.astype(np.float32)

        # 執行搜尋
        distances, indices = self.index.search(query, k)

        return distances, indices

    def batch_search(self, queries: np.ndarray, k: int = 10):
        """
        ‹5› 批量搜尋

        Args:
            queries: 查詢向量，shape (n_queries, dimension)
            k: 返回的最近鄰數量

        Returns:
            distances: 距離，shape (n_queries, k)
            indices: 索引，shape (n_queries, k)
        """
        queries = queries.astype(np.float32)
        return self.index.search(queries, k)


def faiss_quickstart():
    """
    ‹1› FAISS 快速入門示範
    """
    print("FAISS 快速入門")
    print("=" * 60)

    # 參數設定
    dimension = 128
    n_database = 100000
    n_queries = 100
    k = 10

    np.random.seed(42)

    # 生成測試數據
    print(f"\n生成 {n_database:,} 個 {dimension} 維向量...")
    database = np.random.randn(n_database, dimension).astype(np.float32)
    queries = np.random.randn(n_queries, dimension).astype(np.float32)

    # 創建索引
    example = FAISSBasicExample(dimension)
    example.create_flat_index()

    # 添加向量
    print("\n添加向量到索引...")
    start = time.perf_counter()
    example.add_vectors(database)
    add_time = time.perf_counter() - start
    print(f"添加時間: {add_time*1000:.2f} ms")

    # 單一查詢
    print("\n執行單一查詢...")
    start = time.perf_counter()
    distances, indices = example.search(queries[0], k)
    single_time = time.perf_counter() - start
    print(f"單一查詢時間: {single_time*1000:.2f} ms")
    print(f"最近的 {k} 個向量索引: {indices[0]}")
    print(f"對應的距離: {distances[0]}")

    # 批量查詢
    print(f"\n執行 {n_queries} 個批量查詢...")
    start = time.perf_counter()
    distances, indices = example.batch_search(queries, k)
    batch_time = time.perf_counter() - start
    print(f"批量查詢總時間: {batch_time*1000:.2f} ms")
    print(f"每個查詢平均時間: {batch_time/n_queries*1000:.4f} ms")


if __name__ == "__main__":
    faiss_quickstart()
```

---

## 8.2 FAISS 索引類型

FAISS 提供了豐富的索引類型，從精確搜尋到各種近似搜尋，滿足不同的效能和精確度需求。

### 8.2.1 索引類型總覽

```
                    FAISS 索引類型分類
                           │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
    精確搜尋           量化索引          複合索引
        │                 │                 │
   IndexFlat          IndexIVF          IndexIVF
   - FlatL2           - IVFPQ           + Flat/PQ/SQ
   - FlatIP           - IVFSQ
                      - IVFFlat
                           │
                      ┌────┴────┐
                      │         │
                   IndexPQ   IndexHNSW
                   - 乘積量化  - 圖索引
```

### 8.2.2 IndexFlat：精確搜尋

```python
import faiss
import numpy as np
import time

class FlatIndexDemo:
    """
    IndexFlat 索引示範

    ‹1› 暴力搜尋，100% 精確
    ‹2› 適合小型數據集或作為基準
    """

    @staticmethod
    def compare_flat_indexes():
        """
        ‹1› 比較不同的 Flat 索引

        - IndexFlatL2：歐氏距離（L2）
        - IndexFlatIP：內積（Inner Product）
        """
        print("Flat 索引比較")
        print("=" * 60)

        dimension = 128
        n = 10000
        np.random.seed(42)

        # 生成測試數據
        database = np.random.randn(n, dimension).astype(np.float32)
        query = np.random.randn(1, dimension).astype(np.float32)

        # L2 距離索引
        index_l2 = faiss.IndexFlatL2(dimension)
        index_l2.add(database)

        # 內積索引（用於餘弦相似度，需要先正規化）
        # 正規化向量
        faiss.normalize_L2(database)
        faiss.normalize_L2(query)

        index_ip = faiss.IndexFlatIP(dimension)
        index_ip.add(database)

        # 搜尋比較
        k = 5
        distances_l2, indices_l2 = index_l2.search(query, k)
        distances_ip, indices_ip = index_ip.search(query, k)

        print("IndexFlatL2 結果（歐氏距離，越小越相似）:")
        print(f"  索引: {indices_l2[0]}")
        print(f"  距離: {distances_l2[0]}")

        print("\nIndexFlatIP 結果（內積，越大越相似）:")
        print(f"  索引: {indices_ip[0]}")
        print(f"  相似度: {distances_ip[0]}")

    @staticmethod
    def flat_index_limitations():
        """
        ‹2› 展示 Flat 索引的局限性
        """
        print("\nFlat 索引的規模限制")
        print("=" * 60)

        dimension = 128

        # 測試不同規模
        sizes = [10000, 100000, 500000]

        for n in sizes:
            database = np.random.randn(n, dimension).astype(np.float32)
            query = np.random.randn(1, dimension).astype(np.float32)

            index = faiss.IndexFlatL2(dimension)
            index.add(database)

            # 測量搜尋時間
            start = time.perf_counter()
            for _ in range(100):
                _ = index.search(query, 10)
            elapsed = (time.perf_counter() - start) / 100

            # 估算記憶體使用
            memory_mb = n * dimension * 4 / (1024 * 1024)

            print(f"規模: {n:>8,} | 搜尋時間: {elapsed*1000:>6.2f} ms | "
                  f"記憶體: {memory_mb:>6.1f} MB")


if __name__ == "__main__":
    FlatIndexDemo.compare_flat_indexes()
    FlatIndexDemo.flat_index_limitations()
```

### 8.2.3 IndexIVF：倒排檔案索引

IVF（Inverted File）索引是 FAISS 中最常用的近似搜尋索引，它將向量空間分割成多個區域（Voronoi cells），搜尋時只需要檢查相關區域。

```python
class IVFIndexDemo:
    """
    IVF 索引示範

    ‹1› 將向量空間分割成 nlist 個區域
    ‹2› 搜尋時只檢查 nprobe 個最近的區域
    ‹3› 犧牲一些精確度換取速度
    """

    def __init__(self, dimension: int, nlist: int = 100):
        """
        ‹1› 初始化 IVF 索引

        Args:
            dimension: 向量維度
            nlist: 分區數量（聚類中心數）
        """
        self.dimension = dimension
        self.nlist = nlist

        # IVF 需要一個量化器來決定向量屬於哪個分區
        self.quantizer = faiss.IndexFlatL2(dimension)

        # 創建 IVF 索引
        # IVFFlat: IVF + Flat（分區內精確搜尋）
        self.index = faiss.IndexIVFFlat(
            self.quantizer,  # 量化器
            dimension,       # 維度
            nlist,           # 分區數
            faiss.METRIC_L2  # 距離度量
        )

    def train(self, training_data: np.ndarray):
        """
        ‹2› 訓練索引

        IVF 索引需要訓練來決定分區的位置（聚類中心）
        訓練數據應該代表整體數據分佈
        """
        training_data = training_data.astype(np.float32)

        print(f"訓練 IVF 索引，使用 {len(training_data)} 個向量...")
        start = time.perf_counter()
        self.index.train(training_data)
        elapsed = time.perf_counter() - start
        print(f"訓練完成，耗時: {elapsed:.2f} 秒")
        print(f"索引已訓練: {self.index.is_trained}")

    def add(self, vectors: np.ndarray):
        """
        ‹3› 添加向量
        """
        vectors = vectors.astype(np.float32)
        self.index.add(vectors)
        print(f"添加了 {len(vectors)} 個向量，總數: {self.index.ntotal}")

    def search(self, query: np.ndarray, k: int = 10, nprobe: int = 1):
        """
        ‹4› 搜尋

        Args:
            query: 查詢向量
            k: 返回數量
            nprobe: 搜尋的分區數（越大越精確但越慢）
        """
        if query.ndim == 1:
            query = query.reshape(1, -1)
        query = query.astype(np.float32)

        # 設定搜尋的分區數
        self.index.nprobe = nprobe

        return self.index.search(query, k)


def demonstrate_ivf():
    """
    ‹1› IVF 索引示範
    """
    print("IVF 索引示範")
    print("=" * 60)

    # 參數設定
    dimension = 128
    n_database = 1000000  # 100 萬
    n_train = 100000      # 訓練用 10%
    nlist = 1000          # 1000 個分區

    np.random.seed(42)

    print(f"生成 {n_database:,} 個向量...")
    database = np.random.randn(n_database, dimension).astype(np.float32)
    query = np.random.randn(1, dimension).astype(np.float32)

    # 創建和訓練 IVF 索引
    ivf_index = IVFIndexDemo(dimension, nlist)
    ivf_index.train(database[:n_train])
    ivf_index.add(database)

    # 測試不同 nprobe 值
    print("\nnprobe 對搜尋效能的影響:")
    print(f"{'nprobe':<10} {'時間(ms)':<12} {'召回率':<10}")
    print("-" * 35)

    # 先用 Flat 索引得到真實結果
    flat_index = faiss.IndexFlatL2(dimension)
    flat_index.add(database)
    _, true_neighbors = flat_index.search(query, 100)
    true_set = set(true_neighbors[0])

    for nprobe in [1, 5, 10, 50, 100, 200]:
        # 測量時間
        start = time.perf_counter()
        for _ in range(100):
            distances, indices = ivf_index.search(query, 100, nprobe=nprobe)
        elapsed = (time.perf_counter() - start) / 100

        # 計算召回率
        found_set = set(indices[0])
        recall = len(found_set & true_set) / len(true_set)

        print(f"{nprobe:<10} {elapsed*1000:<12.2f} {recall:<10.2%}")

    print("\n結論：nprobe 越大，精確度越高但速度越慢")


if __name__ == "__main__":
    demonstrate_ivf()
```

### 8.2.4 IndexIVFPQ：乘積量化

乘積量化（Product Quantization）是一種壓縮技術，可以大幅減少記憶體使用。

```python
class IVFPQIndexDemo:
    """
    IVFPQ 索引示範

    ‹1› 結合 IVF 和乘積量化（PQ）
    ‹2› 大幅減少記憶體使用
    ‹3› 適合超大規模數據集
    """

    def __init__(
        self,
        dimension: int,
        nlist: int = 100,
        m: int = 8,
        nbits: int = 8
    ):
        """
        ‹1› 初始化 IVFPQ 索引

        Args:
            dimension: 向量維度（必須能被 m 整除）
            nlist: IVF 分區數
            m: PQ 子空間數量
            nbits: 每個子空間的位元數（通常是 8）
        """
        self.dimension = dimension
        self.nlist = nlist
        self.m = m
        self.nbits = nbits

        # 檢查維度可整除
        assert dimension % m == 0, \
            f"維度 {dimension} 必須能被子空間數 {m} 整除"

        # 量化器
        self.quantizer = faiss.IndexFlatL2(dimension)

        # 創建 IVFPQ 索引
        self.index = faiss.IndexIVFPQ(
            self.quantizer,
            dimension,
            nlist,
            m,           # 子空間數
            nbits        # 每個子空間的位元數
        )

    def train(self, training_data: np.ndarray):
        """訓練索引"""
        training_data = training_data.astype(np.float32)
        self.index.train(training_data)

    def add(self, vectors: np.ndarray):
        """添加向量"""
        vectors = vectors.astype(np.float32)
        self.index.add(vectors)

    def search(self, query: np.ndarray, k: int = 10, nprobe: int = 10):
        """搜尋"""
        if query.ndim == 1:
            query = query.reshape(1, -1)
        query = query.astype(np.float32)
        self.index.nprobe = nprobe
        return self.index.search(query, k)


def demonstrate_pq_memory_savings():
    """
    ‹1› 展示乘積量化的記憶體節省
    """
    print("乘積量化（PQ）記憶體節省比較")
    print("=" * 60)

    dimension = 128
    n = 1000000  # 100 萬向量

    # 計算記憶體使用
    # Flat 索引：每個向量 dimension * 4 bytes
    flat_memory = n * dimension * 4 / (1024 * 1024)

    # PQ 索引：每個向量 m bytes（m 個子空間，每個 1 byte）
    m = 8
    pq_memory = n * m / (1024 * 1024)

    # IVFPQ：PQ + 聚類中心（可忽略不計）
    ivfpq_memory = pq_memory

    print(f"向量數量: {n:,}")
    print(f"向量維度: {dimension}")
    print()
    print(f"{'索引類型':<15} {'記憶體使用':<15} {'壓縮比':<10}")
    print("-" * 40)
    print(f"{'IndexFlat':<15} {flat_memory:>10.1f} MB {'1x':<10}")
    print(f"{'IndexPQ (m=8)':<15} {pq_memory:>10.1f} MB {flat_memory/pq_memory:>9.1f}x")
    print(f"{'IndexIVFPQ':<15} {ivfpq_memory:>10.1f} MB {flat_memory/ivfpq_memory:>9.1f}x")


def demonstrate_ivfpq():
    """
    ‹2› IVFPQ 索引完整示範
    """
    print("\nIVFPQ 索引示範")
    print("=" * 60)

    # 參數
    dimension = 128
    n_database = 1000000
    n_train = 100000
    nlist = 1000
    m = 8  # 子空間數

    np.random.seed(42)

    print(f"生成 {n_database:,} 個向量...")
    database = np.random.randn(n_database, dimension).astype(np.float32)
    query = np.random.randn(1, dimension).astype(np.float32)

    # 創建 IVFPQ 索引
    print("\n創建和訓練 IVFPQ 索引...")
    ivfpq = IVFPQIndexDemo(dimension, nlist, m)

    start = time.perf_counter()
    ivfpq.train(database[:n_train])
    train_time = time.perf_counter() - start
    print(f"訓練時間: {train_time:.2f} 秒")

    start = time.perf_counter()
    ivfpq.add(database)
    add_time = time.perf_counter() - start
    print(f"添加時間: {add_time:.2f} 秒")

    # 與 IVFFlat 比較
    print("\n創建 IVFFlat 索引作為對照...")
    quantizer = faiss.IndexFlatL2(dimension)
    ivf_flat = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_L2)
    ivf_flat.train(database[:n_train])
    ivf_flat.add(database)

    # 比較搜尋性能
    print("\n搜尋性能比較（nprobe=50）:")
    print(f"{'索引類型':<15} {'搜尋時間(ms)':<15}")
    print("-" * 30)

    # IVFPQ
    ivfpq.index.nprobe = 50
    start = time.perf_counter()
    for _ in range(100):
        _ = ivfpq.search(query, 10, nprobe=50)
    ivfpq_time = (time.perf_counter() - start) / 100
    print(f"{'IVFPQ':<15} {ivfpq_time*1000:<15.2f}")

    # IVFFlat
    ivf_flat.nprobe = 50
    start = time.perf_counter()
    for _ in range(100):
        _ = ivf_flat.search(query, 10)
    ivfflat_time = (time.perf_counter() - start) / 100
    print(f"{'IVFFlat':<15} {ivfflat_time*1000:<15.2f}")


if __name__ == "__main__":
    demonstrate_pq_memory_savings()
    demonstrate_ivfpq()
```

### 8.2.5 IndexHNSW：分層可導航小世界圖

HNSW（Hierarchical Navigable Small World）是一種基於圖的索引結構，提供極高的搜尋效率。

```python
class HNSWIndexDemo:
    """
    HNSW 索引示範

    ‹1› 基於圖的索引結構
    ‹2› 搜尋速度極快
    ‹3› 記憶體使用較高
    """

    def __init__(self, dimension: int, M: int = 32, ef_construction: int = 200):
        """
        ‹1› 初始化 HNSW 索引

        Args:
            dimension: 向量維度
            M: 每個節點的連接數（越大越精確但更耗記憶體）
            ef_construction: 建構時的搜尋範圍（影響索引品質）
        """
        self.dimension = dimension
        self.M = M
        self.ef_construction = ef_construction

        # 創建 HNSW 索引
        self.index = faiss.IndexHNSWFlat(dimension, M)
        self.index.hnsw.efConstruction = ef_construction

    def add(self, vectors: np.ndarray):
        """
        ‹2› 添加向量

        注意：HNSW 不需要訓練，但添加較慢
        """
        vectors = vectors.astype(np.float32)
        self.index.add(vectors)

    def search(self, query: np.ndarray, k: int = 10, ef_search: int = 64):
        """
        ‹3› 搜尋

        Args:
            query: 查詢向量
            k: 返回數量
            ef_search: 搜尋時的候選集大小（越大越精確）
        """
        if query.ndim == 1:
            query = query.reshape(1, -1)
        query = query.astype(np.float32)

        # 設定搜尋參數
        self.index.hnsw.efSearch = ef_search

        return self.index.search(query, k)


def demonstrate_hnsw():
    """
    ‹1› HNSW 索引示範
    """
    print("HNSW 索引示範")
    print("=" * 60)

    dimension = 128
    n_database = 100000
    M = 32  # 連接數

    np.random.seed(42)

    print(f"生成 {n_database:,} 個向量...")
    database = np.random.randn(n_database, dimension).astype(np.float32)
    query = np.random.randn(1, dimension).astype(np.float32)

    # 創建 HNSW 索引
    print("\n創建 HNSW 索引...")
    hnsw = HNSWIndexDemo(dimension, M=M)

    start = time.perf_counter()
    hnsw.add(database)
    add_time = time.perf_counter() - start
    print(f"添加時間: {add_time:.2f} 秒")

    # 先用 Flat 索引得到真實結果
    flat_index = faiss.IndexFlatL2(dimension)
    flat_index.add(database)
    _, true_neighbors = flat_index.search(query, 100)
    true_set = set(true_neighbors[0])

    # 測試不同 ef_search 值
    print("\nef_search 對搜尋效能的影響:")
    print(f"{'ef_search':<12} {'時間(ms)':<12} {'召回率':<10}")
    print("-" * 35)

    for ef_search in [16, 32, 64, 128, 256, 512]:
        start = time.perf_counter()
        for _ in range(1000):
            distances, indices = hnsw.search(query, 100, ef_search=ef_search)
        elapsed = (time.perf_counter() - start) / 1000

        found_set = set(indices[0])
        recall = len(found_set & true_set) / len(true_set)

        print(f"{ef_search:<12} {elapsed*1000:<12.3f} {recall:<10.2%}")

    print("\n結論：ef_search 越大，精確度越高但速度越慢")


if __name__ == "__main__":
    demonstrate_hnsw()
```

---

## 8.3 索引選擇指南

### 8.3.1 決策樹

```python
def index_selection_guide():
    """
    ‹1› 索引選擇指南
    """
    guide = """
    FAISS 索引選擇決策樹
    =====================

                    你的數據量是多少？
                          │
         ┌────────────────┼────────────────┐
         │                │                │
      < 10K          10K - 1M           > 1M
         │                │                │
    IndexFlat         記憶體充足？        記憶體充足？
    (精確搜尋)      ┌────┴────┐        ┌────┴────┐
                   是        否        是        否
                   │         │         │         │
              IndexHNSW  IndexIVFPQ  IndexHNSW  IndexIVFPQ
              (最快)    (壓縮)     + OPQ     + OPQ

    詳細建議：
    =========

    IndexFlat（< 10K 向量）
    - 優點：100% 精確，無需訓練
    - 缺點：O(n) 搜尋複雜度
    - 用途：小型應用、基準測試

    IndexIVFFlat（10K - 100K）
    - 優點：較快的搜尋，仍然精確
    - 缺點：需要訓練，記憶體使用較高
    - 參數：nlist = sqrt(n), nprobe = nlist/10

    IndexHNSW（10K - 10M，記憶體充足）
    - 優點：極快的搜尋，高精確度
    - 缺點：記憶體使用高，添加慢
    - 參數：M = 32-64, ef_construction = 200

    IndexIVFPQ（> 1M 或記憶體受限）
    - 優點：極低的記憶體使用
    - 缺點：精確度較低
    - 參數：m = 8-64, nlist = sqrt(n)
    """
    print(guide)


def benchmark_all_indexes():
    """
    ‹2› 對所有索引類型進行基準測試
    """
    print("各索引類型基準測試")
    print("=" * 80)

    dimension = 128
    n_database = 100000
    n_train = 10000
    k = 10

    np.random.seed(42)
    database = np.random.randn(n_database, dimension).astype(np.float32)
    queries = np.random.randn(100, dimension).astype(np.float32)

    results = []

    # 1. IndexFlatL2
    print("\n測試 IndexFlatL2...")
    index = faiss.IndexFlatL2(dimension)
    start = time.perf_counter()
    index.add(database)
    build_time = time.perf_counter() - start

    start = time.perf_counter()
    _, true_indices = index.search(queries, k)
    search_time = time.perf_counter() - start

    results.append({
        'name': 'IndexFlatL2',
        'build_time': build_time,
        'search_time': search_time,
        'memory_mb': n_database * dimension * 4 / 1024 / 1024,
        'recall': 1.0
    })

    # 2. IndexIVFFlat
    print("測試 IndexIVFFlat...")
    nlist = 100
    quantizer = faiss.IndexFlatL2(dimension)
    index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_L2)

    start = time.perf_counter()
    index.train(database[:n_train])
    index.add(database)
    build_time = time.perf_counter() - start

    index.nprobe = 10
    start = time.perf_counter()
    _, indices = index.search(queries, k)
    search_time = time.perf_counter() - start

    # 計算召回率
    recall = np.mean([
        len(set(indices[i]) & set(true_indices[i])) / k
        for i in range(len(queries))
    ])

    results.append({
        'name': 'IndexIVFFlat',
        'build_time': build_time,
        'search_time': search_time,
        'memory_mb': n_database * dimension * 4 / 1024 / 1024,
        'recall': recall
    })

    # 3. IndexIVFPQ
    print("測試 IndexIVFPQ...")
    m = 8
    quantizer = faiss.IndexFlatL2(dimension)
    index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, 8)

    start = time.perf_counter()
    index.train(database[:n_train])
    index.add(database)
    build_time = time.perf_counter() - start

    index.nprobe = 10
    start = time.perf_counter()
    _, indices = index.search(queries, k)
    search_time = time.perf_counter() - start

    recall = np.mean([
        len(set(indices[i]) & set(true_indices[i])) / k
        for i in range(len(queries))
    ])

    results.append({
        'name': 'IndexIVFPQ',
        'build_time': build_time,
        'search_time': search_time,
        'memory_mb': n_database * m / 1024 / 1024,
        'recall': recall
    })

    # 4. IndexHNSWFlat
    print("測試 IndexHNSWFlat...")
    M = 32
    index = faiss.IndexHNSWFlat(dimension, M)

    start = time.perf_counter()
    index.add(database)
    build_time = time.perf_counter() - start

    index.hnsw.efSearch = 64
    start = time.perf_counter()
    _, indices = index.search(queries, k)
    search_time = time.perf_counter() - start

    recall = np.mean([
        len(set(indices[i]) & set(true_indices[i])) / k
        for i in range(len(queries))
    ])

    # HNSW 記憶體估計：向量 + 圖結構
    hnsw_memory = (n_database * dimension * 4 + n_database * M * 2 * 4) / 1024 / 1024

    results.append({
        'name': 'IndexHNSWFlat',
        'build_time': build_time,
        'search_time': search_time,
        'memory_mb': hnsw_memory,
        'recall': recall
    })

    # 輸出結果
    print("\n" + "=" * 80)
    print(f"{'索引類型':<20} {'建構時間(s)':<15} {'搜尋時間(ms)':<15} "
          f"{'記憶體(MB)':<15} {'召回率':<10}")
    print("-" * 80)

    for r in results:
        print(f"{r['name']:<20} {r['build_time']:<15.2f} {r['search_time']*1000:<15.2f} "
              f"{r['memory_mb']:<15.1f} {r['recall']:<10.2%}")


if __name__ == "__main__":
    index_selection_guide()
    benchmark_all_indexes()
```

---

## 8.4 進階功能

### 8.4.1 索引工廠

FAISS 提供了一個強大的索引工廠函數，可以用字串描述來創建複雜的索引。

```python
class IndexFactoryDemo:
    """
    FAISS 索引工廠示範

    ‹1› 使用字串描述創建索引
    ‹2› 支援複雜的索引組合
    """

    @staticmethod
    def demonstrate_factory():
        """
        ‹1› 展示索引工廠的使用
        """
        print("FAISS 索引工廠示範")
        print("=" * 60)

        dimension = 128

        # 各種索引描述字串
        index_descriptions = [
            ("Flat", "精確搜尋"),
            ("IVF100,Flat", "IVF + Flat"),
            ("IVF100,PQ8", "IVF + PQ"),
            ("IVF100,SQ8", "IVF + 標量量化"),
            ("HNSW32", "HNSW（M=32）"),
            ("IVF100,HNSW32", "IVF + HNSW"),
            ("OPQ8,IVF100,PQ8", "OPQ + IVF + PQ"),
        ]

        print(f"{'索引描述':<25} {'說明':<25} {'需要訓練':<10}")
        print("-" * 60)

        for desc, explanation in index_descriptions:
            try:
                index = faiss.index_factory(dimension, desc)
                needs_training = "是" if not index.is_trained else "否"
                print(f"{desc:<25} {explanation:<25} {needs_training:<10}")
            except Exception as e:
                print(f"{desc:<25} 錯誤: {str(e)[:30]}")

    @staticmethod
    def index_factory_strings():
        """
        ‹2› 索引工廠字串語法說明
        """
        syntax = """
        索引工廠字串語法
        ================

        基本索引：
        - Flat          暴力搜尋（L2 距離）
        - FlatIP        暴力搜尋（內積）

        IVF 索引：
        - IVF{nlist},Flat    IVF + 精確搜尋
        - IVF{nlist},PQ{m}   IVF + 乘積量化
        - IVF{nlist},SQ{bits} IVF + 標量量化

        HNSW 索引：
        - HNSW{M}            HNSW（M 為連接數）
        - HNSW{M},Flat       HNSW + Flat

        預處理：
        - PCA{d}             PCA 降維到 d
        - OPQ{m}             最佳乘積量化旋轉

        組合範例：
        - PCA64,IVF100,PQ8   先 PCA 降到 64 維，再用 IVFPQ
        - OPQ16,IVF1000,PQ16 OPQ 預處理 + IVFPQ
        """
        print(syntax)


def practical_index_factory():
    """
    ‹1› 實際應用索引工廠
    """
    print("\n實際應用：使用索引工廠創建最佳索引")
    print("=" * 60)

    dimension = 128
    n_database = 100000
    n_train = 10000

    np.random.seed(42)
    database = np.random.randn(n_database, dimension).astype(np.float32)
    queries = np.random.randn(100, dimension).astype(np.float32)

    # 使用索引工廠創建索引
    index_string = "IVF100,PQ8"
    print(f"創建索引: {index_string}")

    index = faiss.index_factory(dimension, index_string, faiss.METRIC_L2)

    # 訓練
    print("訓練索引...")
    index.train(database[:n_train])

    # 添加
    print("添加向量...")
    index.add(database)

    # 設定搜尋參數
    faiss.ParameterSpace().set_index_parameter(index, "nprobe", 10)

    # 搜尋
    print("執行搜尋...")
    distances, indices = index.search(queries, 10)

    print(f"\n第一個查詢的結果:")
    print(f"最近的 10 個索引: {indices[0]}")
    print(f"對應的距離: {distances[0]}")


if __name__ == "__main__":
    IndexFactoryDemo.demonstrate_factory()
    IndexFactoryDemo.index_factory_strings()
    practical_index_factory()
```

### 8.4.2 GPU 加速

```python
class GPUAccelerationDemo:
    """
    FAISS GPU 加速示範

    ‹1› 使用 GPU 加速搜尋
    ‹2› 支援多 GPU
    """

    @staticmethod
    def check_gpu_availability():
        """
        ‹1› 檢查 GPU 是否可用
        """
        print("檢查 GPU 可用性")
        print("=" * 40)

        try:
            import faiss

            ngpus = faiss.get_num_gpus()
            print(f"可用 GPU 數量: {ngpus}")

            if ngpus > 0:
                for i in range(ngpus):
                    res = faiss.StandardGpuResources()
                    print(f"GPU {i}: 可用")
            else:
                print("未檢測到 GPU，將使用 CPU")

            return ngpus > 0
        except Exception as e:
            print(f"GPU 檢測失敗: {e}")
            return False

    @staticmethod
    def cpu_to_gpu_index(cpu_index, gpu_id: int = 0):
        """
        ‹2› 將 CPU 索引轉換為 GPU 索引
        """
        try:
            res = faiss.StandardGpuResources()
            gpu_index = faiss.index_cpu_to_gpu(res, gpu_id, cpu_index)
            return gpu_index
        except Exception as e:
            print(f"轉換失敗: {e}")
            return None

    @staticmethod
    def gpu_to_cpu_index(gpu_index):
        """
        ‹3› 將 GPU 索引轉換回 CPU 索引
        """
        return faiss.index_gpu_to_cpu(gpu_index)


def demonstrate_gpu_speedup():
    """
    ‹1› 展示 GPU 加速效果（如果有 GPU）
    """
    print("\nGPU 加速示範")
    print("=" * 60)

    has_gpu = GPUAccelerationDemo.check_gpu_availability()

    if not has_gpu:
        print("\n無 GPU 可用，跳過 GPU 測試")
        print("以下是預期的加速效果（根據典型硬體）：")
        print(f"{'數據量':<15} {'CPU (ms)':<15} {'GPU (ms)':<15} {'加速比':<10}")
        print("-" * 55)
        print(f"{'100K':<15} {'50':<15} {'2':<15} {'25x':<10}")
        print(f"{'1M':<15} {'500':<15} {'10':<15} {'50x':<10}")
        print(f"{'10M':<15} {'5000':<15} {'50':<15} {'100x':<10}")
        return

    # 有 GPU 時的實際測試
    dimension = 128
    n_database = 1000000

    np.random.seed(42)
    database = np.random.randn(n_database, dimension).astype(np.float32)
    queries = np.random.randn(1000, dimension).astype(np.float32)

    # CPU 索引
    print("\n創建 CPU 索引...")
    cpu_index = faiss.IndexFlatL2(dimension)
    cpu_index.add(database)

    # CPU 搜尋
    start = time.perf_counter()
    _, _ = cpu_index.search(queries, 10)
    cpu_time = time.perf_counter() - start
    print(f"CPU 搜尋時間: {cpu_time*1000:.2f} ms")

    # GPU 索引
    print("\n創建 GPU 索引...")
    gpu_index = GPUAccelerationDemo.cpu_to_gpu_index(cpu_index)

    if gpu_index:
        # GPU 搜尋
        start = time.perf_counter()
        _, _ = gpu_index.search(queries, 10)
        gpu_time = time.perf_counter() - start
        print(f"GPU 搜尋時間: {gpu_time*1000:.2f} ms")
        print(f"加速比: {cpu_time/gpu_time:.1f}x")


if __name__ == "__main__":
    demonstrate_gpu_speedup()
```

### 8.4.3 索引的儲存與載入

```python
class IndexPersistenceDemo:
    """
    索引持久化示範

    ‹1› 儲存索引到磁碟
    ‹2› 從磁碟載入索引
    """

    @staticmethod
    def save_index(index, path: str):
        """
        ‹1› 儲存索引
        """
        faiss.write_index(index, path)
        print(f"索引已儲存到: {path}")

    @staticmethod
    def load_index(path: str):
        """
        ‹2› 載入索引
        """
        index = faiss.read_index(path)
        print(f"索引已從 {path} 載入")
        print(f"向量數量: {index.ntotal}")
        return index

    @staticmethod
    def demonstrate_persistence():
        """
        ‹3› 完整的持久化示範
        """
        print("索引持久化示範")
        print("=" * 60)

        import os
        import tempfile

        dimension = 128
        n = 10000

        np.random.seed(42)
        database = np.random.randn(n, dimension).astype(np.float32)

        # 創建索引
        index = faiss.IndexFlatL2(dimension)
        index.add(database)
        print(f"創建了包含 {index.ntotal} 個向量的索引")

        # 儲存
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_index.faiss")

            # 測量儲存時間和大小
            start = time.perf_counter()
            IndexPersistenceDemo.save_index(index, path)
            save_time = time.perf_counter() - start

            file_size = os.path.getsize(path) / (1024 * 1024)
            print(f"儲存時間: {save_time*1000:.2f} ms")
            print(f"檔案大小: {file_size:.2f} MB")

            # 載入
            start = time.perf_counter()
            loaded_index = IndexPersistenceDemo.load_index(path)
            load_time = time.perf_counter() - start
            print(f"載入時間: {load_time*1000:.2f} ms")

            # 驗證
            query = np.random.randn(1, dimension).astype(np.float32)
            d1, i1 = index.search(query, 5)
            d2, i2 = loaded_index.search(query, 5)

            print(f"\n驗證結果一致性:")
            print(f"原索引結果: {i1[0]}")
            print(f"載入索引結果: {i2[0]}")
            print(f"結果一致: {np.array_equal(i1, i2)}")


if __name__ == "__main__":
    IndexPersistenceDemo.demonstrate_persistence()
```

---

## 8.5 實戰：構建語意搜尋引擎

```python
from typing import List, Tuple, Optional
import numpy as np
import faiss

class SemanticSearchEngine:
    """
    基於 FAISS 的語意搜尋引擎

    ‹1› 支援多種索引類型
    ‹2› 自動選擇最佳索引
    ‹3› 支援增量更新
    """

    def __init__(
        self,
        dimension: int,
        index_type: str = "auto",
        metric: str = "cosine"
    ):
        """
        ‹1› 初始化搜尋引擎

        Args:
            dimension: 向量維度
            index_type: 索引類型（auto, flat, ivf, hnsw, ivfpq）
            metric: 距離度量（cosine, l2, ip）
        """
        self.dimension = dimension
        self.index_type = index_type
        self.metric = metric

        self.index = None
        self.is_trained = False
        self.documents = []  # 儲存原始文件
        self.id_map = {}     # ID 到索引的映射

    def _create_index(self, n_vectors: int):
        """
        ‹2› 根據數據量自動選擇索引類型
        """
        # 決定度量
        if self.metric == "cosine":
            metric_type = faiss.METRIC_INNER_PRODUCT
        elif self.metric == "ip":
            metric_type = faiss.METRIC_INNER_PRODUCT
        else:
            metric_type = faiss.METRIC_L2

        # 自動選擇索引類型
        if self.index_type == "auto":
            if n_vectors < 10000:
                index_string = "Flat"
            elif n_vectors < 100000:
                nlist = int(np.sqrt(n_vectors))
                index_string = f"IVF{nlist},Flat"
            elif n_vectors < 1000000:
                nlist = int(np.sqrt(n_vectors))
                index_string = f"IVF{nlist},PQ16"
            else:
                nlist = int(np.sqrt(n_vectors))
                index_string = f"OPQ16,IVF{nlist},PQ16"
        else:
            index_string = {
                "flat": "Flat",
                "ivf": "IVF100,Flat",
                "hnsw": "HNSW32",
                "ivfpq": "IVF100,PQ16"
            }.get(self.index_type, "Flat")

        print(f"創建索引: {index_string}")
        self.index = faiss.index_factory(self.dimension, index_string, metric_type)

    def add_documents(
        self,
        vectors: np.ndarray,
        documents: List[str],
        ids: Optional[List[str]] = None
    ):
        """
        ‹3› 添加文件和向量

        Args:
            vectors: 向量，shape (n, dimension)
            documents: 原始文件列表
            ids: 文件 ID 列表（可選）
        """
        vectors = vectors.astype(np.float32)

        # 如果使用餘弦相似度，需要正規化
        if self.metric == "cosine":
            faiss.normalize_L2(vectors)

        # 創建索引（如果尚未創建）
        if self.index is None:
            self._create_index(len(vectors))

        # 訓練索引（如果需要）
        if not self.index.is_trained:
            print("訓練索引...")
            self.index.train(vectors)

        # 添加向量
        start_idx = self.index.ntotal
        self.index.add(vectors)

        # 儲存文件
        for i, doc in enumerate(documents):
            idx = start_idx + i
            self.documents.append(doc)
            if ids:
                self.id_map[ids[i]] = idx

        print(f"添加了 {len(vectors)} 個文件，總數: {self.index.ntotal}")

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        nprobe: int = 10
    ) -> List[Tuple[int, float, str]]:
        """
        ‹4› 搜尋相似文件

        Args:
            query_vector: 查詢向量
            k: 返回數量
            nprobe: IVF 搜尋參數

        Returns:
            [(索引, 距離/相似度, 文件內容), ...]
        """
        query_vector = query_vector.astype(np.float32)

        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        # 如果使用餘弦相似度，需要正規化
        if self.metric == "cosine":
            faiss.normalize_L2(query_vector)

        # 設定搜尋參數
        if hasattr(self.index, 'nprobe'):
            self.index.nprobe = nprobe

        # 搜尋
        distances, indices = self.index.search(query_vector, k)

        # 整理結果
        results = []
        for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
            if idx >= 0 and idx < len(self.documents):
                results.append((idx, float(dist), self.documents[idx]))

        return results

    def save(self, path: str):
        """
        ‹5› 儲存引擎狀態
        """
        import pickle

        # 儲存索引
        faiss.write_index(self.index, f"{path}.index")

        # 儲存元數據
        metadata = {
            'dimension': self.dimension,
            'index_type': self.index_type,
            'metric': self.metric,
            'documents': self.documents,
            'id_map': self.id_map
        }
        with open(f"{path}.meta", 'wb') as f:
            pickle.dump(metadata, f)

        print(f"引擎已儲存到: {path}")

    @classmethod
    def load(cls, path: str) -> 'SemanticSearchEngine':
        """
        ‹6› 載入引擎狀態
        """
        import pickle

        # 載入元數據
        with open(f"{path}.meta", 'rb') as f:
            metadata = pickle.load(f)

        # 創建引擎實例
        engine = cls(
            dimension=metadata['dimension'],
            index_type=metadata['index_type'],
            metric=metadata['metric']
        )

        # 載入索引
        engine.index = faiss.read_index(f"{path}.index")
        engine.documents = metadata['documents']
        engine.id_map = metadata['id_map']

        print(f"引擎已從 {path} 載入")
        print(f"文件數量: {engine.index.ntotal}")

        return engine


def demonstrate_search_engine():
    """
    ‹1› 語意搜尋引擎完整示範
    """
    print("語意搜尋引擎示範")
    print("=" * 60)

    # 模擬文件和嵌入向量
    # 在實際應用中，這些向量會由嵌入模型生成
    documents = [
        "機器學習是人工智慧的一個重要分支",
        "深度學習使用多層神經網路",
        "自然語言處理讓電腦理解人類語言",
        "電腦視覺使機器能夠看到和理解圖像",
        "推薦系統根據用戶偏好推薦內容",
        "強化學習通過獎勵機制學習",
        "向量資料庫儲存和搜尋高維向量",
        "FAISS 是高效的相似性搜尋函式庫",
        "語意搜尋理解查詢的含義",
        "知識圖譜表示實體之間的關係",
    ]

    # 模擬嵌入向量（實際應使用真實的嵌入模型）
    dimension = 128
    np.random.seed(42)

    # 為每個文件生成一個隨機向量
    # 讓相似主題的文件向量更接近
    vectors = np.random.randn(len(documents), dimension).astype(np.float32)

    # 創建搜尋引擎
    engine = SemanticSearchEngine(
        dimension=dimension,
        index_type="auto",
        metric="cosine"
    )

    # 添加文件
    engine.add_documents(
        vectors,
        documents,
        ids=[f"doc_{i}" for i in range(len(documents))]
    )

    # 搜尋
    print("\n執行搜尋...")
    query_vector = vectors[0]  # 使用第一個文件作為查詢
    results = engine.search(query_vector, k=5)

    print("\n搜尋結果（查詢：機器學習相關）:")
    print("-" * 60)
    for idx, score, doc in results:
        print(f"[{idx}] 相似度: {score:.4f}")
        print(f"    {doc}")
        print()


if __name__ == "__main__":
    demonstrate_search_engine()
```

---

## 8.6 效能調優

### 8.6.1 參數調優指南

```python
def parameter_tuning_guide():
    """
    ‹1› FAISS 參數調優指南
    """
    guide = """
    FAISS 參數調優指南
    ==================

    1. IndexIVF 參數
    ----------------
    nlist（分區數）:
    - 建議: sqrt(n) 到 4*sqrt(n)
    - 太小 → 搜尋慢，太大 → 訓練慢、召回低

    nprobe（搜尋分區數）:
    - 建議: nlist/10 到 nlist/2
    - 越大 → 越精確但越慢

    2. IndexHNSW 參數
    -----------------
    M（連接數）:
    - 建議: 16-64
    - 越大 → 越精確但記憶體更多

    efConstruction（建構搜尋範圍）:
    - 建議: 100-500
    - 越大 → 索引品質越好但建構越慢

    efSearch（搜尋範圍）:
    - 建議: >= k，通常 k*2 到 k*10
    - 越大 → 越精確但越慢

    3. IndexPQ 參數
    ---------------
    m（子空間數）:
    - 必須能整除 dimension
    - 建議: 8, 16, 32, 64
    - 越大 → 越精確但記憶體更多

    nbits（每子空間位元數）:
    - 通常: 8
    - 8 bits = 256 個聚類中心/子空間

    4. 通用建議
    -----------
    - 先用小數據集找到好的參數組合
    - 使用召回率 vs 速度曲線選擇參數
    - 監控記憶體使用
    - 考慮 GPU 加速對大批量查詢
    """
    print(guide)


def find_optimal_parameters():
    """
    ‹2› 自動搜尋最佳參數
    """
    print("\n自動參數搜尋")
    print("=" * 60)

    dimension = 128
    n_database = 100000
    n_train = 10000

    np.random.seed(42)
    database = np.random.randn(n_database, dimension).astype(np.float32)
    queries = np.random.randn(100, dimension).astype(np.float32)

    # 建立真實結果
    flat_index = faiss.IndexFlatL2(dimension)
    flat_index.add(database)
    _, true_neighbors = flat_index.search(queries, 100)

    # 測試不同的 nlist
    print("\n搜尋最佳 nlist...")
    print(f"{'nlist':<10} {'訓練時間(s)':<15} {'召回率@10':<15}")
    print("-" * 40)

    for nlist in [50, 100, 200, 500, 1000]:
        quantizer = faiss.IndexFlatL2(dimension)
        index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_L2)

        start = time.perf_counter()
        index.train(database[:n_train])
        train_time = time.perf_counter() - start

        index.add(database)
        index.nprobe = max(1, nlist // 10)

        _, indices = index.search(queries, 10)

        recall = np.mean([
            len(set(indices[i]) & set(true_neighbors[i][:10])) / 10
            for i in range(len(queries))
        ])

        print(f"{nlist:<10} {train_time:<15.2f} {recall:<15.2%}")


if __name__ == "__main__":
    parameter_tuning_guide()
    find_optimal_parameters()
```

---

## 8.7 本章回顧

### 核心要點

1. **FAISS 基礎**
   - Facebook 開發的高效向量搜尋函式庫
   - 支援 CPU 和 GPU
   - 提供多種索引類型

2. **索引類型**
   - IndexFlat：精確搜尋，適合小數據
   - IndexIVF：倒排檔案，平衡速度和精確度
   - IndexHNSW：圖索引，極快搜尋
   - IndexPQ：乘積量化，極低記憶體

3. **索引選擇**
   - < 10K：IndexFlat
   - 10K-1M：IndexIVFFlat 或 IndexHNSW
   - > 1M：IndexIVFPQ

4. **進階功能**
   - 索引工廠簡化創建
   - GPU 加速大規模搜尋
   - 持久化支援生產部署

### 最佳實踐

- 總是使用 float32 數據類型
- 對餘弦相似度預先正規化向量
- 用小數據集調優參數後再部署
- 監控召回率和延遲的平衡

---

## 思考題

1. 為什麼 HNSW 的搜尋速度比 IVF 快，但建構速度更慢？

2. 乘積量化（PQ）如何實現向量壓縮？它的精確度損失來自哪裡？

3. 如果你有 10 億個 768 維的向量，記憶體限制為 32GB，你會選擇什麼索引？需要什麼參數？

4. 在生產環境中，如何設計一個支援實時更新的向量搜尋系統？

5. GPU 加速在什麼情況下效益最大？什麼時候 CPU 可能更好？

---

下一章，我們將學習 Milvus——一個專為生產環境設計的分散式向量資料庫，它在 FAISS 的基礎上提供了更完整的功能。
