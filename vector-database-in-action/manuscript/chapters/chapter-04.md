# 第 4 章：向量相似性搜尋初步

> 「搜尋的本質是在無限中尋找有限，在混沌中發現秩序。」

## 本章學習目標

完成本章後，你將能夠：
- 實現基於暴力搜尋的向量相似性檢索
- 掌握歐幾里得距離與餘弦相似度的計算與應用
- 理解精度、召回率與 F1 評分的評估體系
- 應用各種技術提升向量搜尋性能

---

## 引言：搜尋的起點

在深入學習複雜的索引結構之前，讓我們先回到最基本的問題：**如何在一堆向量中找到與查詢最相似的幾個？**

最直接的答案是：計算查詢向量與所有向量的距離，然後返回距離最小的 K 個。這就是「暴力搜尋」（Brute Force Search），也稱為「精確最近鄰搜尋」（Exact Nearest Neighbor Search）。

雖然暴力搜尋在大規模資料上效率不高，但它有兩個重要價值：

1. **作為基準**：所有近似方法都以暴力搜尋的結果為「黃金標準」
2. **小規模應用**：當資料量小於 1 萬時，暴力搜尋可能是最簡單有效的選擇

本章將帶你深入理解暴力搜尋的實現、最佳化，以及如何評估搜尋的品質。

---

## 4.1 基於暴力搜尋的向量相似性檢索

### 4.1.1 暴力搜尋的原理與實現

**演算法原理**

```
暴力搜尋演算法：

輸入：
  - 向量集合 V = {v₁, v₂, ..., vₙ}
  - 查詢向量 q
  - 返回數量 k
  - 距離函數 d(·, ·)

過程：
  1. 對於每個向量 vᵢ，計算 d(q, vᵢ)
  2. 將所有距離排序
  3. 返回距離最小的 k 個向量

時間複雜度：O(n × d)
  - n: 向量數量
  - d: 向量維度

空間複雜度：O(n × d) 用於儲存向量
            O(n) 用於儲存距離（查詢時）
```

**基本實現**

```python
import numpy as np
from typing import List, Tuple
import heapq

class BruteForceSearch:
    """
    暴力搜尋實現

    ‹1› 支援多種距離度量
    ‹2› 支援批次查詢
    """

    def __init__(self, metric: str = 'euclidean'):
        """
        初始化

        ‹1› metric: 距離度量，支援 'euclidean', 'cosine', 'dot'
        """
        self.vectors = None
        self.metric = metric
        self.normalized = False

    def fit(self, vectors: np.ndarray):
        """
        載入向量集合

        ‹1› 對於餘弦相似度，預先正規化可以加速查詢
        """
        self.vectors = vectors.astype(np.float32)

        if self.metric == 'cosine':
            # 預先正規化
            norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1  # 避免除以零
            self.vectors = self.vectors / norms
            self.normalized = True

    def _compute_distances(self, query: np.ndarray) -> np.ndarray:
        """
        計算查詢向量與所有向量的距離
        """
        if self.metric == 'euclidean':
            # 歐幾里得距離
            diff = self.vectors - query
            distances = np.sqrt(np.sum(diff ** 2, axis=1))

        elif self.metric == 'cosine':
            # 餘弦距離 = 1 - 餘弦相似度
            if not self.normalized:
                query_norm = query / np.linalg.norm(query)
            else:
                query_norm = query / np.linalg.norm(query)
            similarities = np.dot(self.vectors, query_norm)
            distances = 1 - similarities

        elif self.metric == 'dot':
            # 負內積（因為我們要最小化距離）
            distances = -np.dot(self.vectors, query)

        else:
            raise ValueError(f"不支援的度量: {self.metric}")

        return distances

    def search(
        self,
        query: np.ndarray,
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        搜尋最近的 k 個向量

        返回：
          - indices: 最近鄰的索引
          - distances: 對應的距離
        """
        query = query.astype(np.float32)
        distances = self._compute_distances(query)

        # 找出最小的 k 個
        if k >= len(distances):
            indices = np.argsort(distances)
        else:
            # 使用 argpartition 提高效率
            indices = np.argpartition(distances, k)[:k]
            # 對 top-k 進行排序
            indices = indices[np.argsort(distances[indices])]

        return indices, distances[indices]

    def batch_search(
        self,
        queries: np.ndarray,
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        批次搜尋

        ‹1› 對多個查詢向量同時搜尋
        """
        all_indices = []
        all_distances = []

        for query in queries:
            indices, distances = self.search(query, k)
            all_indices.append(indices)
            all_distances.append(distances)

        return np.array(all_indices), np.array(all_distances)


# 使用示例
if __name__ == "__main__":
    # 生成測試資料
    np.random.seed(42)
    n_vectors = 10000
    dimension = 128

    vectors = np.random.randn(n_vectors, dimension).astype(np.float32)
    query = np.random.randn(dimension).astype(np.float32)

    # 建立搜尋器
    searcher = BruteForceSearch(metric='cosine')
    searcher.fit(vectors)

    # 搜尋
    indices, distances = searcher.search(query, k=10)

    print(f"最近的 10 個向量索引: {indices}")
    print(f"對應的距離: {distances}")
```

**使用堆積結構最佳化**

當只需要 top-k 結果時，可以使用最大堆來避免完整排序：

```python
import heapq

def search_with_heap(
    vectors: np.ndarray,
    query: np.ndarray,
    k: int,
    metric: str = 'euclidean'
) -> Tuple[List[int], List[float]]:
    """
    使用堆積結構的搜尋

    ‹1› 維護一個大小為 k 的最大堆
    ‹2› 時間複雜度：O(n log k)
    """
    # 使用最大堆（Python 的 heapq 是最小堆，用負值模擬最大堆）
    max_heap = []

    for i, vector in enumerate(vectors):
        if metric == 'euclidean':
            dist = np.sqrt(np.sum((vector - query) ** 2))
        elif metric == 'cosine':
            dist = 1 - np.dot(vector, query) / (
                np.linalg.norm(vector) * np.linalg.norm(query)
            )

        if len(max_heap) < k:
            heapq.heappush(max_heap, (-dist, i))  # 負值用於模擬最大堆
        elif dist < -max_heap[0][0]:
            heapq.heapreplace(max_heap, (-dist, i))

    # 提取結果並排序
    results = [(i, -d) for d, i in max_heap]
    results.sort(key=lambda x: x[1])

    indices = [r[0] for r in results]
    distances = [r[1] for r in results]

    return indices, distances
```

### 4.1.2 暴力搜尋最佳化

雖然暴力搜尋的時間複雜度無法改變，但我們可以通過各種技術加速常數因子。

**向量化計算**

```python
import numpy as np

def vectorized_euclidean_distance(vectors: np.ndarray, query: np.ndarray) -> np.ndarray:
    """
    向量化的歐幾里得距離計算

    ‹1› 使用廣播和矩陣運算
    ‹2› 比逐個計算快 10-100 倍
    """
    # 方法 1：直接計算
    # diff = vectors - query
    # distances = np.sqrt(np.sum(diff ** 2, axis=1))

    # 方法 2：展開公式，更高效
    # ||a - b||² = ||a||² + ||b||² - 2<a, b>
    vectors_sq = np.sum(vectors ** 2, axis=1)
    query_sq = np.sum(query ** 2)
    dot_product = np.dot(vectors, query)

    distances_sq = vectors_sq + query_sq - 2 * dot_product
    distances_sq = np.maximum(distances_sq, 0)  # 數值穩定性
    distances = np.sqrt(distances_sq)

    return distances


def vectorized_cosine_similarity(vectors: np.ndarray, query: np.ndarray) -> np.ndarray:
    """
    向量化的餘弦相似度計算
    """
    # 正規化向量
    vectors_norm = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    query_norm = query / np.linalg.norm(query)

    # 內積即為餘弦相似度
    similarities = np.dot(vectors_norm, query_norm)

    return similarities
```

**批次處理**

```python
def batch_search_optimized(
    vectors: np.ndarray,
    queries: np.ndarray,
    k: int
) -> Tuple[np.ndarray, np.ndarray]:
    """
    批次搜尋的最佳化實現

    ‹1› 使用矩陣乘法一次計算所有距離
    """
    n_vectors = len(vectors)
    n_queries = len(queries)

    # 計算所有查詢與所有向量的相似度
    # vectors: (n_vectors, d)
    # queries: (n_queries, d)
    # similarities: (n_queries, n_vectors)

    # 正規化
    vectors_norm = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    queries_norm = queries / np.linalg.norm(queries, axis=1, keepdims=True)

    # 矩陣乘法
    similarities = np.dot(queries_norm, vectors_norm.T)

    # 對每個查詢找 top-k
    all_indices = np.zeros((n_queries, k), dtype=np.int64)
    all_similarities = np.zeros((n_queries, k), dtype=np.float32)

    for i in range(n_queries):
        indices = np.argpartition(similarities[i], -k)[-k:]
        indices = indices[np.argsort(-similarities[i][indices])]
        all_indices[i] = indices
        all_similarities[i] = similarities[i][indices]

    return all_indices, all_similarities
```

**SIMD 加速**

現代 CPU 支援 SIMD（Single Instruction, Multiple Data）指令，可以並行處理多個數據。

```python
# 使用 numba 進行 SIMD 最佳化
from numba import jit, prange
import numpy as np

@jit(nopython=True, parallel=True, fastmath=True)
def simd_euclidean_distances(vectors: np.ndarray, query: np.ndarray) -> np.ndarray:
    """
    使用 Numba 加速的歐幾里得距離計算

    ‹1› parallel=True 啟用多執行緒
    ‹2› fastmath=True 允許數學最佳化
    """
    n = len(vectors)
    d = len(query)
    distances = np.empty(n, dtype=np.float32)

    for i in prange(n):
        dist_sq = 0.0
        for j in range(d):
            diff = vectors[i, j] - query[j]
            dist_sq += diff * diff
        distances[i] = np.sqrt(dist_sq)

    return distances


@jit(nopython=True, parallel=True)
def simd_dot_products(vectors: np.ndarray, query: np.ndarray) -> np.ndarray:
    """
    使用 Numba 加速的內積計算
    """
    n = len(vectors)
    d = len(query)
    results = np.empty(n, dtype=np.float32)

    for i in prange(n):
        dot = 0.0
        for j in range(d):
            dot += vectors[i, j] * query[j]
        results[i] = dot

    return results
```

**GPU 加速**

對於大規模計算，GPU 可以提供數量級的加速：

```python
import torch

class GPUBruteForceSearch:
    """
    GPU 加速的暴力搜尋

    ‹1› 利用 GPU 的大規模並行能力
    ‹2› 適合批次查詢
    """

    def __init__(self, device: str = 'cuda'):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.vectors = None

    def fit(self, vectors: np.ndarray):
        """載入向量到 GPU"""
        self.vectors = torch.tensor(vectors, dtype=torch.float32, device=self.device)
        # 預先正規化
        self.vectors = torch.nn.functional.normalize(self.vectors, p=2, dim=1)

    def search(
        self,
        queries: np.ndarray,
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        GPU 上的批次搜尋
        """
        queries_tensor = torch.tensor(
            queries, dtype=torch.float32, device=self.device
        )
        queries_tensor = torch.nn.functional.normalize(queries_tensor, p=2, dim=1)

        # 計算餘弦相似度
        similarities = torch.mm(queries_tensor, self.vectors.T)

        # 找 top-k
        top_k_sims, top_k_indices = torch.topk(similarities, k, dim=1)

        return top_k_indices.cpu().numpy(), top_k_sims.cpu().numpy()


# 性能比較
def benchmark_search(n_vectors: int, dimension: int, n_queries: int, k: int):
    """比較 CPU 和 GPU 搜尋性能"""
    import time

    # 生成資料
    vectors = np.random.randn(n_vectors, dimension).astype(np.float32)
    queries = np.random.randn(n_queries, dimension).astype(np.float32)

    # CPU 搜尋
    cpu_searcher = BruteForceSearch(metric='cosine')
    cpu_searcher.fit(vectors)

    start = time.time()
    cpu_indices, cpu_distances = cpu_searcher.batch_search(queries, k)
    cpu_time = time.time() - start

    # GPU 搜尋
    if torch.cuda.is_available():
        gpu_searcher = GPUBruteForceSearch()
        gpu_searcher.fit(vectors)

        # 預熱
        _ = gpu_searcher.search(queries[:10], k)

        start = time.time()
        gpu_indices, gpu_sims = gpu_searcher.search(queries, k)
        gpu_time = time.time() - start

        print(f"CPU 時間: {cpu_time:.3f}s")
        print(f"GPU 時間: {gpu_time:.3f}s")
        print(f"加速比: {cpu_time / gpu_time:.1f}x")
    else:
        print(f"CPU 時間: {cpu_time:.3f}s")
        print("GPU 不可用")
```

**分塊處理大規模資料**

當向量無法完全載入記憶體時，使用分塊處理：

```python
def chunked_search(
    vectors_path: str,
    query: np.ndarray,
    k: int,
    chunk_size: int = 100000
) -> Tuple[np.ndarray, np.ndarray]:
    """
    分塊處理大規模向量搜尋

    ‹1› 逐塊載入向量
    ‹2› 維護全局 top-k
    """
    import h5py

    global_top_k = []  # (distance, global_index)

    with h5py.File(vectors_path, 'r') as f:
        vectors = f['vectors']
        n_total = len(vectors)

        for start_idx in range(0, n_total, chunk_size):
            end_idx = min(start_idx + chunk_size, n_total)

            # 載入當前塊
            chunk = vectors[start_idx:end_idx]

            # 計算距離
            distances = vectorized_euclidean_distance(chunk, query)

            # 更新全局 top-k
            for i, dist in enumerate(distances):
                global_idx = start_idx + i

                if len(global_top_k) < k:
                    heapq.heappush(global_top_k, (-dist, global_idx))
                elif dist < -global_top_k[0][0]:
                    heapq.heapreplace(global_top_k, (-dist, global_idx))

    # 提取結果
    results = [(-d, idx) for d, idx in global_top_k]
    results.sort(key=lambda x: x[0])

    indices = np.array([r[1] for r in results])
    distances = np.array([r[0] for r in results])

    return indices, distances
```

---

## 4.2 歐幾里得距離與餘弦相似度

選擇正確的距離度量對搜尋結果至關重要。讓我們深入理解兩種最常用的度量。

### 4.2.1 距離與相似度的數學定義

**歐幾里得距離（L2 距離）**

```
定義：
d(a, b) = ||a - b||₂ = √(Σᵢ (aᵢ - bᵢ)²)

性質：
1. 非負性：d(a, b) ≥ 0
2. 同一性：d(a, b) = 0 ⟺ a = b
3. 對稱性：d(a, b) = d(b, a)
4. 三角不等式：d(a, c) ≤ d(a, b) + d(b, c)

範圍：[0, +∞)

幾何意義：兩點之間的直線距離
```

```python
def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算歐幾里得距離

    ‹1› 直接實現
    """
    return np.sqrt(np.sum((a - b) ** 2))


def euclidean_distance_optimized(a: np.ndarray, b: np.ndarray) -> float:
    """
    最佳化的歐幾里得距離計算

    ‹1› 使用 numpy 內建函數
    """
    return np.linalg.norm(a - b)
```

**餘弦相似度**

```
定義：
cos(a, b) = (a · b) / (||a||₂ × ||b||₂) = Σᵢ(aᵢ × bᵢ) / (√Σᵢaᵢ² × √Σᵢbᵢ²)

性質：
1. 範圍：[-1, 1]
2. cos(a, b) = 1 ⟺ a 和 b 同方向
3. cos(a, b) = 0 ⟺ a 和 b 正交
4. cos(a, b) = -1 ⟺ a 和 b 反方向

注意：餘弦相似度不是距離（不滿足三角不等式）

餘弦距離：
d_cos(a, b) = 1 - cos(a, b)

範圍：[0, 2]
```

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算餘弦相似度
    """
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算餘弦距離
    """
    return 1 - cosine_similarity(a, b)
```

**內積（點積）**

```
定義：
<a, b> = a · b = Σᵢ(aᵢ × bᵢ)

性質：
1. 範圍：(-∞, +∞)
2. 對於單位向量：<a, b> = cos(a, b)

使用場景：
- 當向量已經正規化時
- 某些推薦系統中使用原始分數
```

```python
def dot_product(a: np.ndarray, b: np.ndarray) -> float:
    """
    計算內積
    """
    return np.dot(a, b)
```

**三種度量的關係**

```
對於單位向量（||a|| = ||b|| = 1）：

歐幾里得距離² = ||a||² + ||b||² - 2<a, b>
             = 1 + 1 - 2<a, b>
             = 2(1 - <a, b>)
             = 2(1 - cos(a, b))
             = 2 × 餘弦距離

因此，對於正規化的向量：
- 歐幾里得距離和餘弦距離產生相同的排序
- 可以互相轉換
```

### 4.2.2 不同相似度指標的適用場景分析

**歐幾里得距離的適用場景**

```
適合使用歐幾里得距離的情況：

1. 向量的長度有意義
   - 圖像特徵（顏色直方圖、紋理特徵）
   - 時間序列資料
   - 地理座標

2. 資料已經標準化
   - 經過 z-score 標準化
   - 各維度的量綱一致

3. 異常檢測
   - 異常點通常「距離」正常點較遠

4. 聚類分析
   - K-means 使用歐幾里得距離

示例：圖像相似度
圖像 A: [紅色佔比, 綠色佔比, 藍色佔比, ...]
圖像 B: [紅色佔比, 綠色佔比, 藍色佔比, ...]

如果 A 和 B 的顏色分佈相似，它們的歐幾里得距離小
```

**餘弦相似度的適用場景**

```
適合使用餘弦相似度的情況：

1. 向量的方向比長度更重要
   - 文字嵌入（語義方向）
   - 使用者偏好向量

2. 資料稀疏
   - TF-IDF 向量
   - 購買歷史向量

3. 高維資料
   - 餘弦相似度對維度詛咒更魯棒

4. 推薦系統
   - 使用者-物品相似度

示例：文字語義相似
句子 A: "我喜歡蘋果" → 嵌入向量 [0.1, 0.2, ...]
句子 B: "我愛蘋果" → 嵌入向量 [0.15, 0.22, ...]

即使向量長度不同，餘弦相似度能捕捉語義相似性
```

**選擇度量的決策流程**

```python
def choose_metric(
    data_type: str,
    is_normalized: bool,
    is_sparse: bool,
    task: str
) -> str:
    """
    根據資料特性選擇距離度量

    ‹1› data_type: 'text', 'image', 'audio', 'numerical'
    ‹2› is_normalized: 是否已正規化
    ‹3› is_sparse: 是否稀疏
    ‹4› task: 'similarity', 'clustering', 'anomaly'
    """

    # 文字資料通常使用餘弦
    if data_type == 'text':
        return 'cosine'

    # 稀疏資料使用餘弦
    if is_sparse:
        return 'cosine'

    # 聚類任務使用歐幾里得
    if task == 'clustering':
        return 'euclidean'

    # 異常檢測使用歐幾里得
    if task == 'anomaly':
        return 'euclidean'

    # 已正規化的資料，兩者等效
    if is_normalized:
        return 'cosine'  # 計算稍快

    # 數值資料默認歐幾里得
    if data_type == 'numerical':
        return 'euclidean'

    return 'cosine'  # 默認
```

**實驗比較**

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances

def compare_metrics_on_text():
    """
    比較不同度量在文字搜尋上的表現
    """
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 測試句子
    sentences = [
        "機器學習是人工智慧的分支",
        "深度學習使用神經網路",
        "自然語言處理分析文字",
        "今天天氣很好",
        "我喜歡吃蘋果",
    ]

    query = "AI 和機器學習有什麼關係"

    # 生成嵌入
    embeddings = model.encode(sentences)
    query_embedding = model.encode([query])[0]

    # 歐幾里得距離
    euclidean_dists = np.sqrt(np.sum((embeddings - query_embedding) ** 2, axis=1))
    euclidean_ranking = np.argsort(euclidean_dists)

    # 餘弦相似度
    cosine_sims = cosine_similarity([query_embedding], embeddings)[0]
    cosine_ranking = np.argsort(-cosine_sims)

    print("查詢:", query)
    print("\n歐幾里得距離排序:")
    for i, idx in enumerate(euclidean_ranking):
        print(f"  {i+1}. [{euclidean_dists[idx]:.4f}] {sentences[idx]}")

    print("\n餘弦相似度排序:")
    for i, idx in enumerate(cosine_ranking):
        print(f"  {i+1}. [{cosine_sims[idx]:.4f}] {sentences[idx]}")

    # 檢查排序是否一致
    print(f"\n排序一致: {list(euclidean_ranking) == list(cosine_ranking)}")
```

---

## 4.3 向量搜尋的精度與召回率

評估搜尋品質需要一套系統化的指標。讓我們學習如何衡量搜尋的好壞。

### 4.3.1 精度、召回率與 F1 評分的計算方法

**基本概念**

```
假設：
- 真正相關的文件集合：R（Relevant）
- 系統返回的文件集合：A（Retrieved/Answered）
- R ∩ A：既相關又被返回的文件

        返回     未返回
      ┌────────┬────────┐
相關   │  TP    │  FN    │
      ├────────┼────────┤
不相關 │  FP    │  TN    │
      └────────┴────────┘

TP (True Positive)：正確返回的相關文件
FP (False Positive)：錯誤返回的不相關文件
FN (False Negative)：遺漏的相關文件
TN (True Negative)：正確未返回的不相關文件
```

**精度（Precision）**

```
定義：返回結果中相關文件的比例

Precision = TP / (TP + FP) = |R ∩ A| / |A|

直覺：「我返回的東西有多少是對的？」

範圍：[0, 1]，越高越好
```

**召回率（Recall）**

```
定義：相關文件被返回的比例

Recall = TP / (TP + FN) = |R ∩ A| / |R|

直覺：「我找到了多少應該找到的東西？」

範圍：[0, 1]，越高越好
```

**F1 評分**

```
定義：精度和召回率的調和平均

F1 = 2 × (Precision × Recall) / (Precision + Recall)

調和平均的特點：
- 當 Precision 和 Recall 都高時，F1 才高
- 對低值更敏感

範圍：[0, 1]

變體：Fβ 評分
Fβ = (1 + β²) × (Precision × Recall) / (β² × Precision + Recall)

- β > 1：更重視召回率
- β < 1：更重視精度
```

**Precision@K 和 Recall@K**

在 top-K 搜尋中，我們特別關注返回 K 個結果時的性能：

```python
def precision_at_k(retrieved: list, relevant: set, k: int) -> float:
    """
    計算 Precision@K

    ‹1› retrieved: 按排序的返回結果列表
    ‹2› relevant: 相關文件的集合
    """
    retrieved_k = set(retrieved[:k])
    relevant_retrieved = retrieved_k & relevant
    return len(relevant_retrieved) / k


def recall_at_k(retrieved: list, relevant: set, k: int) -> float:
    """
    計算 Recall@K
    """
    retrieved_k = set(retrieved[:k])
    relevant_retrieved = retrieved_k & relevant
    return len(relevant_retrieved) / len(relevant) if relevant else 0


def f1_at_k(retrieved: list, relevant: set, k: int) -> float:
    """
    計算 F1@K
    """
    p = precision_at_k(retrieved, relevant, k)
    r = recall_at_k(retrieved, relevant, k)

    if p + r == 0:
        return 0
    return 2 * p * r / (p + r)


# 示例
retrieved_results = [1, 3, 5, 7, 9, 2, 4, 6, 8, 10]
relevant_items = {1, 2, 3, 4, 5}  # 真正相關的項目

for k in [1, 3, 5, 10]:
    p = precision_at_k(retrieved_results, relevant_items, k)
    r = recall_at_k(retrieved_results, relevant_items, k)
    f1 = f1_at_k(retrieved_results, relevant_items, k)
    print(f"K={k}: P@{k}={p:.3f}, R@{k}={r:.3f}, F1@{k}={f1:.3f}")
```

**Mean Average Precision (MAP)**

```python
def average_precision(retrieved: list, relevant: set) -> float:
    """
    計算 Average Precision

    ‹1› AP 考慮了相關文件出現的位置
    ‹2› 相關文件排名越靠前，AP 越高
    """
    if not relevant:
        return 0.0

    score = 0.0
    num_relevant = 0

    for i, doc in enumerate(retrieved):
        if doc in relevant:
            num_relevant += 1
            precision_at_i = num_relevant / (i + 1)
            score += precision_at_i

    return score / len(relevant)


def mean_average_precision(
    all_retrieved: list,
    all_relevant: list
) -> float:
    """
    計算 Mean Average Precision

    ‹1› all_retrieved: 每個查詢的返回結果列表
    ‹2› all_relevant: 每個查詢的相關文件集合
    """
    aps = []
    for retrieved, relevant in zip(all_retrieved, all_relevant):
        ap = average_precision(retrieved, set(relevant))
        aps.append(ap)

    return np.mean(aps)


# 示例
queries_results = [
    [1, 3, 5, 2, 4],  # 查詢 1 的返回結果
    [2, 1, 4, 3, 5],  # 查詢 2 的返回結果
]
queries_relevant = [
    [1, 2, 3],        # 查詢 1 的相關文件
    [1, 3],           # 查詢 2 的相關文件
]

map_score = mean_average_precision(queries_results, queries_relevant)
print(f"MAP = {map_score:.4f}")
```

**NDCG（Normalized Discounted Cumulative Gain）**

```python
import numpy as np

def dcg_at_k(relevances: list, k: int) -> float:
    """
    計算 Discounted Cumulative Gain

    ‹1› relevances: 返回結果的相關性分數列表
    ‹2› 相關性可以是二元的（0/1）或分級的（0/1/2/3...）
    """
    relevances = np.array(relevances[:k])
    # DCG = Σᵢ (2^relᵢ - 1) / log₂(i + 2)
    discounts = np.log2(np.arange(2, k + 2))
    gains = (2 ** relevances - 1) / discounts
    return np.sum(gains)


def ndcg_at_k(relevances: list, k: int) -> float:
    """
    計算 Normalized DCG

    ‹1› 將 DCG 除以理想情況下的 DCG
    """
    dcg = dcg_at_k(relevances, k)

    # 理想排序：相關性從高到低
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = dcg_at_k(ideal_relevances, k)

    if idcg == 0:
        return 0.0

    return dcg / idcg


# 示例：分級相關性
# 3: 非常相關, 2: 相關, 1: 部分相關, 0: 不相關
relevances = [3, 2, 0, 1, 2, 0, 0, 1]

for k in [3, 5, 8]:
    score = ndcg_at_k(relevances, k)
    print(f"NDCG@{k} = {score:.4f}")
```

### 4.3.2 向量搜尋性能提升方案

**提升精度的策略**

```python
class PrecisionEnhancer:
    """
    提升搜尋精度的策略集合
    """

    @staticmethod
    def rerank(
        query: np.ndarray,
        candidates: np.ndarray,
        top_k: int,
        rerank_model=None
    ) -> np.ndarray:
        """
        重排序：使用更精確的模型重新排序候選結果

        ‹1› 先用快速方法獲取候選集
        ‹2› 再用精確模型重排序
        """
        if rerank_model is None:
            # 默認使用精確的餘弦相似度
            query_norm = query / np.linalg.norm(query)
            candidates_norm = candidates / np.linalg.norm(
                candidates, axis=1, keepdims=True
            )
            scores = np.dot(candidates_norm, query_norm)
        else:
            # 使用提供的重排序模型
            scores = rerank_model.score(query, candidates)

        reranked_indices = np.argsort(-scores)[:top_k]
        return reranked_indices

    @staticmethod
    def query_expansion(
        original_query: np.ndarray,
        retrieved_embeddings: np.ndarray,
        alpha: float = 0.5
    ) -> np.ndarray:
        """
        查詢擴展：使用初始檢索結果擴展查詢

        ‹1› Rocchio 演算法的簡化版本
        ‹2› 將相關文件的向量加入查詢
        """
        # 假設前幾個結果是相關的
        relevant_centroid = np.mean(retrieved_embeddings[:3], axis=0)

        # 擴展後的查詢
        expanded_query = alpha * original_query + (1 - alpha) * relevant_centroid
        return expanded_query

    @staticmethod
    def diversity_rerank(
        query: np.ndarray,
        candidates: np.ndarray,
        scores: np.ndarray,
        top_k: int,
        diversity_weight: float = 0.3
    ) -> np.ndarray:
        """
        多樣性重排序：平衡相關性和多樣性

        ‹1› MMR (Maximal Marginal Relevance) 演算法
        """
        selected = []
        candidates_list = list(range(len(candidates)))

        while len(selected) < top_k and candidates_list:
            best_score = -np.inf
            best_idx = None

            for idx in candidates_list:
                # 相關性分數
                relevance = scores[idx]

                # 與已選擇項的最大相似度
                if selected:
                    selected_embeddings = candidates[selected]
                    similarities = cosine_similarity(
                        [candidates[idx]], selected_embeddings
                    )[0]
                    max_similarity = np.max(similarities)
                else:
                    max_similarity = 0

                # MMR 分數
                mmr_score = (1 - diversity_weight) * relevance - \
                           diversity_weight * max_similarity

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            selected.append(best_idx)
            candidates_list.remove(best_idx)

        return np.array(selected)
```

**提升召回率的策略**

```python
class RecallEnhancer:
    """
    提升搜尋召回率的策略集合
    """

    @staticmethod
    def multi_vector_query(
        queries: list,
        search_func,
        k: int
    ) -> set:
        """
        多向量查詢：使用多個查詢向量

        ‹1› 將查詢改寫為多個變體
        ‹2› 合併所有結果
        """
        all_results = set()

        for query in queries:
            results = search_func(query, k)
            all_results.update(results)

        return all_results

    @staticmethod
    def increase_candidates(
        search_func,
        query: np.ndarray,
        final_k: int,
        candidate_multiplier: int = 10
    ) -> np.ndarray:
        """
        擴大候選集：檢索更多候選，再篩選

        ‹1› 初始檢索更多結果
        ‹2› 使用更精確的方法篩選
        """
        candidate_k = final_k * candidate_multiplier
        candidates = search_func(query, candidate_k)
        return candidates[:final_k]  # 實際應用中會重排序

    @staticmethod
    def hierarchical_search(
        query: np.ndarray,
        coarse_index,
        fine_index,
        k: int,
        coarse_k: int = 100
    ):
        """
        層次搜尋：粗粒度 + 細粒度

        ‹1› 先用粗粒度索引找候選
        ‹2› 再用細粒度方法精確搜尋
        """
        # 粗粒度搜尋
        coarse_results = coarse_index.search(query, coarse_k)

        # 細粒度搜尋
        fine_results = fine_index.search_in_subset(
            query, coarse_results, k
        )

        return fine_results
```

**評估流程**

```python
class SearchEvaluator:
    """
    搜尋系統評估器
    """

    def __init__(self, ground_truth: dict):
        """
        ‹1› ground_truth: {query_id: [relevant_doc_ids]}
        """
        self.ground_truth = ground_truth

    def evaluate(
        self,
        search_results: dict,
        k_values: list = [1, 5, 10, 20]
    ) -> dict:
        """
        全面評估搜尋結果

        ‹1› search_results: {query_id: [retrieved_doc_ids]}
        """
        metrics = {}

        for k in k_values:
            precisions = []
            recalls = []
            ndcgs = []

            for query_id, retrieved in search_results.items():
                relevant = set(self.ground_truth.get(query_id, []))

                if not relevant:
                    continue

                # Precision@K
                p = precision_at_k(retrieved, relevant, k)
                precisions.append(p)

                # Recall@K
                r = recall_at_k(retrieved, relevant, k)
                recalls.append(r)

                # NDCG@K
                relevances = [1 if doc in relevant else 0 for doc in retrieved[:k]]
                ndcg = ndcg_at_k(relevances, k)
                ndcgs.append(ndcg)

            metrics[f'precision@{k}'] = np.mean(precisions)
            metrics[f'recall@{k}'] = np.mean(recalls)
            metrics[f'ndcg@{k}'] = np.mean(ndcgs)

        # MAP
        all_retrieved = list(search_results.values())
        all_relevant = [self.ground_truth.get(qid, [])
                       for qid in search_results.keys()]
        metrics['map'] = mean_average_precision(all_retrieved, all_relevant)

        return metrics

    def print_report(self, metrics: dict):
        """
        打印評估報告
        """
        print("=" * 50)
        print("搜尋評估報告")
        print("=" * 50)

        # 按 K 值分組
        k_values = sorted(set(
            int(key.split('@')[1]) for key in metrics.keys()
            if '@' in key
        ))

        for k in k_values:
            print(f"\nK = {k}")
            print(f"  Precision@{k}: {metrics[f'precision@{k}']:.4f}")
            print(f"  Recall@{k}: {metrics[f'recall@{k}']:.4f}")
            print(f"  NDCG@{k}: {metrics[f'ndcg@{k}']:.4f}")

        print(f"\nMAP: {metrics['map']:.4f}")
        print("=" * 50)


# 使用示例
ground_truth = {
    'query1': [1, 2, 3, 4, 5],
    'query2': [10, 11, 12],
    'query3': [20, 21, 22, 23],
}

search_results = {
    'query1': [1, 6, 2, 7, 3, 8, 4, 9, 5, 10],
    'query2': [10, 13, 11, 14, 12, 15, 16, 17, 18, 19],
    'query3': [25, 20, 21, 26, 22, 27, 23, 28, 29, 30],
}

evaluator = SearchEvaluator(ground_truth)
metrics = evaluator.evaluate(search_results)
evaluator.print_report(metrics)
```

---

## 4.4 本章小結

在本章中，我們學習了向量相似性搜尋的基礎知識：

1. **暴力搜尋的實現與最佳化**
   - 暴力搜尋是最簡單的精確搜尋方法
   - 可以通過向量化計算、SIMD、GPU 加速
   - 對於小規模資料（< 1 萬），暴力搜尋可能是最好的選擇

2. **距離度量的選擇**
   - 歐幾里得距離適合向量長度有意義的場景
   - 餘弦相似度適合語義搜尋和稀疏資料
   - 對於正規化的向量，兩者產生相同的排序

3. **評估指標體系**
   - Precision@K 衡量返回結果的準確性
   - Recall@K 衡量相關文件的覆蓋率
   - MAP 和 NDCG 考慮排序位置的影響

4. **性能提升策略**
   - 重排序、查詢擴展可以提升精度
   - 多向量查詢、擴大候選集可以提升召回率
   - 需要在精度、召回率和效率之間取得平衡

暴力搜尋為我們提供了理解向量搜尋的基礎。在下一章中，我們將學習更高效的近似搜尋方法：HNSW 和 LSH。

---

## 4.5 思考題

1. **概念理解**
   - 解釋為什麼在高維空間中，歐幾里得距離和餘弦距離可能產生不同的搜尋結果。在什麼情況下它們是等價的？

2. **技術分析**
   - 假設你有 100 萬個 512 維的向量，需要支援每秒 100 次查詢。分析：
     a) 暴力搜尋能否滿足需求？
     b) 如果使用 GPU，情況會有什麼變化？
     c) 如果允許近似搜尋（召回率 > 95%），有什麼選擇？

3. **實作練習**
   - 使用 Python 實現以下功能：
     a) 一個支援多種距離度量的暴力搜尋類
     b) 批次查詢的最佳化版本
     c) 完整的評估流程，計算 Precision@K、Recall@K、MAP、NDCG

4. **系統設計**
   - 設計一個混合搜尋策略：
     a) 先用近似方法獲取 100 個候選
     b) 用精確方法重排序得到 top-10
     c) 討論這種方法的優缺點

5. **批判性思考**
   - 「更高的召回率總是更好的」——你同意這個觀點嗎？討論在什麼情況下，我們可能願意犧牲召回率。

---

> **下一章預告**：在第 5 章中，我們將深入學習 HNSW（分層可導航小世界圖）和 LSH（局部敏感雜湊），這是現代向量資料庫中最重要的兩種索引技術。
