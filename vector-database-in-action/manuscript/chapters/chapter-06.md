# 第 6 章：LSH 搜尋最佳化

> 「最佳化的藝術在於找到問題的本質，然後用最簡單的方式解決它。」

## 本章學習目標

完成本章後，你將能夠：
- 理解 BallTree 的節點分割與查詢機制
- 掌握 Annoy 演算法的索引結構與性能最佳化方法
- 應用隨機投影技術進行高維資料降維與檢索
- 根據應用場景選擇適合的近似搜尋演算法

---

## 引言：當 LSH 不夠用時

在上一章中，我們學習了 LSH 的基本原理。LSH 雖然簡單有效，但它有一個根本性的問題：**參數調優困難**。雜湊表的數量和每個表的雜湊函式數量對性能有巨大影響，而且這種影響是非線性的。

本章將介紹幾種更精緻的技術：

- **BallTree**：通過層次化的球形分區組織資料
- **Annoy**：Spotify 開發的樹森林方法，結合了 k-d tree 的思想
- **隨機投影**：一種有理論保證的降維技術

這些方法各有特點，適用於不同的場景。

---

## 6.1 BallTree 演算法的工作原理

### 6.1.1 BallTree 的節點分割與索引建構

**核心思想**

BallTree 將資料點組織成一個層次化的「球」結構。每個節點代表一個球，包含該球內的所有資料點。

```
BallTree 結構示意：

                    ┌─────────────────┐
                    │   Root Ball     │
                    │  center: [...]  │
                    │  radius: R      │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────┴────────┐           ┌────────┴────────┐
     │   Left Ball     │           │   Right Ball    │
     │  center: [...]  │           │  center: [...]  │
     │  radius: r1     │           │  radius: r2     │
     └────────┬────────┘           └────────┬────────┘
              │                             │
         ┌────┴────┐                   ┌────┴────┐
         │         │                   │         │
        ...       ...                 ...       ...

每個球的性質：
- center: 球心（通常是包含點的質心）
- radius: 半徑（到最遠點的距離）
- 保證：球內所有點到球心的距離 ≤ radius
```

**建構演算法**

```python
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class BallNode:
    """BallTree 節點"""
    center: np.ndarray      # 球心
    radius: float           # 半徑
    indices: List[int]      # 該節點包含的點索引
    left: Optional['BallNode'] = None
    right: Optional['BallNode'] = None
    is_leaf: bool = False


class BallTree:
    """
    BallTree 實現

    ‹1› 層次化的球形分區
    ‹2› 支援高效的範圍查詢和最近鄰查詢
    """

    def __init__(self, leaf_size: int = 40):
        """
        初始化

        ‹1› leaf_size: 葉節點的最大點數
        """
        self.leaf_size = leaf_size
        self.root = None
        self.vectors = None

    def _compute_ball(self, indices: List[int]) -> Tuple[np.ndarray, float]:
        """
        計算包含指定點的最小包圍球

        ‹1› 使用質心作為球心（近似）
        ‹2› 半徑為到最遠點的距離
        """
        points = self.vectors[indices]
        center = np.mean(points, axis=0)
        distances = np.sqrt(np.sum((points - center) ** 2, axis=1))
        radius = np.max(distances)
        return center, radius

    def _split_points(
        self,
        indices: List[int]
    ) -> Tuple[List[int], List[int]]:
        """
        將點分成兩組

        ‹1› 找到距離最遠的兩個點
        ‹2› 其他點根據到這兩個點的距離分配
        """
        points = self.vectors[indices]

        # 找到「最分散」的維度
        # 選擇方差最大的維度進行分割
        variances = np.var(points, axis=0)
        split_dim = np.argmax(variances)

        # 按該維度排序
        sorted_indices = np.argsort(points[:, split_dim])
        mid = len(sorted_indices) // 2

        left_indices = [indices[i] for i in sorted_indices[:mid]]
        right_indices = [indices[i] for i in sorted_indices[mid:]]

        return left_indices, right_indices

    def _build_tree(self, indices: List[int]) -> BallNode:
        """
        遞迴建構 BallTree
        """
        center, radius = self._compute_ball(indices)

        # 如果點數少於閾值，建立葉節點
        if len(indices) <= self.leaf_size:
            return BallNode(
                center=center,
                radius=radius,
                indices=indices,
                is_leaf=True
            )

        # 分割點
        left_indices, right_indices = self._split_points(indices)

        # 遞迴建構子樹
        node = BallNode(
            center=center,
            radius=radius,
            indices=indices,
            left=self._build_tree(left_indices),
            right=self._build_tree(right_indices)
        )

        return node

    def fit(self, vectors: np.ndarray):
        """
        建構索引

        ‹1› 時間複雜度：O(n log n)
        """
        self.vectors = vectors
        indices = list(range(len(vectors)))
        self.root = self._build_tree(indices)

    def _distance(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """計算歐幾里得距離"""
        return np.sqrt(np.sum((v1 - v2) ** 2))

    def _min_distance_to_ball(
        self,
        query: np.ndarray,
        node: BallNode
    ) -> float:
        """
        計算查詢點到球的最小可能距離

        ‹1› 如果查詢點在球內，返回 0
        ‹2› 否則返回到球面的距離
        """
        dist_to_center = self._distance(query, node.center)
        return max(0, dist_to_center - node.radius)

    def query(
        self,
        query: np.ndarray,
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        查詢最近的 k 個點
        """
        import heapq

        # 使用最大堆維護 top-k
        # (-distance, index) 的形式，因為 heapq 是最小堆
        results = []

        def search(node: BallNode):
            """遞迴搜尋"""
            # 剪枝：如果到球的最小距離大於當前第 k 近的距離
            if len(results) >= k:
                min_possible_dist = self._min_distance_to_ball(query, node)
                if min_possible_dist > -results[0][0]:
                    return

            if node.is_leaf:
                # 葉節點：計算所有點的距離
                for idx in node.indices:
                    dist = self._distance(query, self.vectors[idx])

                    if len(results) < k:
                        heapq.heappush(results, (-dist, idx))
                    elif dist < -results[0][0]:
                        heapq.heapreplace(results, (-dist, idx))
            else:
                # 內部節點：決定搜尋順序
                left_dist = self._distance(query, node.left.center)
                right_dist = self._distance(query, node.right.center)

                # 先搜尋更近的子樹
                if left_dist <= right_dist:
                    search(node.left)
                    search(node.right)
                else:
                    search(node.right)
                    search(node.left)

        search(self.root)

        # 提取結果
        results = sorted([(-d, idx) for d, idx in results])
        indices = np.array([idx for _, idx in results])
        distances = np.array([d for d, _ in results])

        return indices, distances

    def query_radius(
        self,
        query: np.ndarray,
        radius: float
    ) -> List[int]:
        """
        範圍查詢：返回距離小於 radius 的所有點
        """
        results = []

        def search(node: BallNode):
            # 剪枝：如果到球的最小距離大於查詢半徑
            min_dist = self._min_distance_to_ball(query, node)
            if min_dist > radius:
                return

            if node.is_leaf:
                for idx in node.indices:
                    dist = self._distance(query, self.vectors[idx])
                    if dist <= radius:
                        results.append(idx)
            else:
                search(node.left)
                search(node.right)

        search(self.root)
        return results


# 使用示例
def demo_balltree():
    np.random.seed(42)

    # 生成測試資料
    n_vectors = 10000
    dim = 128
    vectors = np.random.randn(n_vectors, dim).astype(np.float32)
    query = np.random.randn(dim).astype(np.float32)

    # 建構 BallTree
    print("建構 BallTree...")
    tree = BallTree(leaf_size=40)
    tree.fit(vectors)

    # 查詢
    print("查詢中...")
    indices, distances = tree.query(query, k=10)

    print(f"最近的 10 個點: {indices}")
    print(f"對應距離: {distances}")

    # 驗證
    all_distances = np.sqrt(np.sum((vectors - query) ** 2, axis=1))
    true_indices = np.argsort(all_distances)[:10]
    recall = len(set(indices) & set(true_indices)) / 10
    print(f"召回率: {recall * 100:.1f}%")
```

### 6.1.2 BallTree 查詢過程與複雜度分析

**查詢過程詳解**

```
BallTree 查詢的剪枝策略：

對於查詢點 q 和球節點 B（球心 c，半徑 r）：

1. 計算 q 到球心的距離：d(q, c)

2. 計算 q 到球的最小可能距離：
   min_dist = max(0, d(q, c) - r)

3. 剪枝條件：
   如果 min_dist > 當前第 k 近的距離
   則跳過整個子樹

示意圖：

       q •                    query point
       |
       | d(q,c) - r = min_dist
       |
    ---|---                   ball surface
   /       \
  |    c    |                 ball center
   \       /
    ---|---
       |
       | r (radius)
       |

如果 min_dist > k-th nearest distance
則球內不可能有更近的點，可以剪枝
```

**複雜度分析**

```
建構複雜度：

1. 計算包圍球：O(n)
2. 分割點：O(n)
3. 遞迴建構：T(n) = 2T(n/2) + O(n) = O(n log n)

查詢複雜度：

最佳情況：O(log n)
- 每次只需要搜尋一個子樹
- 發生在資料分佈均勻且查詢點明顯靠近某一側

平均情況：O(n^(1-1/d) log n)，d 是維度
- 隨著維度增加，剪枝效果下降

最差情況：O(n)
- 所有球都與查詢範圍重疊
- 高維空間中常見（維度詛咒）

空間複雜度：O(n)
- 每個點只存儲一次
- 樹結構開銷是常數因子
```

**與 k-d tree 的比較**

| 特性 | BallTree | k-d tree |
|------|----------|----------|
| 分割方式 | 球形 | 超平面 |
| 適用距離 | 任何距離度量 | 主要是 L2 |
| 高維性能 | 較好 | 迅速退化 |
| 建構時間 | 較慢 | 較快 |
| 查詢時間 | 較穩定 | 差異大 |

---

## 6.2 Annoy 搜尋演算法

### 6.2.1 Annoy 的索引結構設計與分區原理

**Annoy 簡介**

Annoy（Approximate Nearest Neighbors Oh Yeah）是 Spotify 開發的近似最近鄰搜尋庫。它的設計目標是：

1. **記憶體映射**：索引可以被多個進程共享
2. **快速建構**：比 HNSW 建構更快
3. **不可變索引**：建構後不能添加新點（但查詢更快）

```
Annoy 的核心思想：

1. 建構多棵隨機二叉樹
2. 每棵樹使用隨機超平面分割空間
3. 查詢時遍歷所有樹，合併候選集

與 k-d tree 的區別：
- k-d tree：選擇某個座標軸分割
- Annoy：選擇隨機方向分割（更適合高維）
```

**分割策略**

```python
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class AnnoyNode:
    """Annoy 樹節點"""
    # 分割超平面：n · x = c
    normal: np.ndarray = None   # 法向量
    offset: float = 0.0         # 偏移量

    # 子節點
    left: Optional['AnnoyNode'] = None
    right: Optional['AnnoyNode'] = None

    # 葉節點資料
    indices: List[int] = None
    is_leaf: bool = False


class AnnoyIndex:
    """
    Annoy 索引實現

    ‹1› 使用隨機超平面構建二叉樹
    ‹2› 支援多棵樹提高召回率
    """

    def __init__(
        self,
        dim: int,
        n_trees: int = 10,
        max_leaf_size: int = 100
    ):
        """
        初始化

        ‹1› n_trees: 樹的數量
        ‹2› max_leaf_size: 葉節點最大點數
        """
        self.dim = dim
        self.n_trees = n_trees
        self.max_leaf_size = max_leaf_size

        self.trees = []
        self.vectors = None

    def _create_split(
        self,
        indices: List[int]
    ) -> Tuple[np.ndarray, float, List[int], List[int]]:
        """
        創建分割超平面

        ‹1› 隨機選擇兩個點
        ‹2› 超平面垂直於連線並通過中點
        """
        # 隨機選擇兩個點
        i, j = np.random.choice(len(indices), 2, replace=False)
        p1 = self.vectors[indices[i]]
        p2 = self.vectors[indices[j]]

        # 超平面法向量
        normal = p1 - p2
        normal = normal / np.linalg.norm(normal)

        # 超平面通過中點
        midpoint = (p1 + p2) / 2
        offset = np.dot(normal, midpoint)

        # 分割點
        left_indices = []
        right_indices = []

        for idx in indices:
            point = self.vectors[idx]
            if np.dot(normal, point) <= offset:
                left_indices.append(idx)
            else:
                right_indices.append(idx)

        # 處理退化情況
        if len(left_indices) == 0 or len(right_indices) == 0:
            mid = len(indices) // 2
            left_indices = indices[:mid]
            right_indices = indices[mid:]

        return normal, offset, left_indices, right_indices

    def _build_tree(self, indices: List[int]) -> AnnoyNode:
        """
        遞迴建構一棵樹
        """
        # 葉節點
        if len(indices) <= self.max_leaf_size:
            return AnnoyNode(
                indices=indices,
                is_leaf=True
            )

        # 創建分割
        normal, offset, left_indices, right_indices = self._create_split(indices)

        # 遞迴建構
        node = AnnoyNode(
            normal=normal,
            offset=offset,
            left=self._build_tree(left_indices),
            right=self._build_tree(right_indices)
        )

        return node

    def build(self, vectors: np.ndarray):
        """
        建構索引

        ‹1› 建構 n_trees 棵樹
        """
        self.vectors = vectors
        indices = list(range(len(vectors)))

        print(f"建構 {self.n_trees} 棵樹...")
        for i in range(self.n_trees):
            tree = self._build_tree(indices)
            self.trees.append(tree)

            if (i + 1) % 10 == 0:
                print(f"  已建構 {i + 1} 棵樹")

    def _search_tree(
        self,
        query: np.ndarray,
        tree: AnnoyNode,
        n_candidates: int
    ) -> List[int]:
        """
        在單棵樹中搜尋

        ‹1› 優先搜尋查詢點所在的一側
        ‹2› 如果候選不足，搜尋另一側
        """
        import heapq

        # (priority, node, depth)
        # priority 越小越優先
        heap = [(0.0, tree, 0)]
        candidates = []

        while heap and len(candidates) < n_candidates:
            _, node, depth = heapq.heappop(heap)

            if node.is_leaf:
                candidates.extend(node.indices)
            else:
                # 計算查詢點到超平面的距離
                dist = np.dot(node.normal, query) - node.offset

                # 查詢點在左側
                if dist <= 0:
                    # 優先搜尋左子樹
                    heapq.heappush(heap, (depth, node.left, depth + 1))
                    # 另一側用距離作為優先級
                    heapq.heappush(heap, (abs(dist), node.right, depth + 1))
                else:
                    heapq.heappush(heap, (depth, node.right, depth + 1))
                    heapq.heappush(heap, (abs(dist), node.left, depth + 1))

        return candidates

    def query(
        self,
        query: np.ndarray,
        k: int = 10,
        search_k: int = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        查詢最近的 k 個點

        ‹1› search_k: 每棵樹搜尋的候選數（默認 k * n_trees）
        """
        if search_k is None:
            search_k = k * self.n_trees

        candidates_per_tree = search_k // self.n_trees

        # 從所有樹收集候選
        all_candidates = set()
        for tree in self.trees:
            candidates = self._search_tree(query, tree, candidates_per_tree)
            all_candidates.update(candidates)

        # 計算精確距離
        all_candidates = list(all_candidates)
        candidate_vectors = self.vectors[all_candidates]

        distances = np.sqrt(np.sum((candidate_vectors - query) ** 2, axis=1))

        # 排序
        top_k_idx = np.argsort(distances)[:k]

        indices = np.array([all_candidates[i] for i in top_k_idx])
        dists = distances[top_k_idx]

        return indices, dists


# 使用示例
def demo_annoy():
    np.random.seed(42)

    # 生成測試資料
    n_vectors = 100000
    dim = 128
    vectors = np.random.randn(n_vectors, dim).astype(np.float32)
    query = np.random.randn(dim).astype(np.float32)

    # 建構 Annoy 索引
    print("建構 Annoy 索引...")
    annoy = AnnoyIndex(dim=dim, n_trees=20, max_leaf_size=100)
    annoy.build(vectors)

    # 查詢
    print("\n查詢中...")
    indices, distances = annoy.query(query, k=10)

    print(f"最近的 10 個點: {indices}")
    print(f"對應距離: {distances[:5]}...")

    # 驗證
    all_distances = np.sqrt(np.sum((vectors - query) ** 2, axis=1))
    true_indices = np.argsort(all_distances)[:10]
    recall = len(set(indices) & set(true_indices)) / 10
    print(f"召回率: {recall * 100:.1f}%")
```

### 6.2.2 Annoy 在大規模向量檢索中的性能最佳化

**使用官方 Annoy 庫**

```python
from annoy import AnnoyIndex
import numpy as np
import time

def benchmark_annoy(
    n_vectors: int = 1000000,
    dim: int = 128,
    n_trees: int = 50
):
    """
    Annoy 性能測試

    ‹1› 使用官方 Annoy 庫
    """
    print(f"向量數量: {n_vectors:,}")
    print(f"維度: {dim}")
    print(f"樹數量: {n_trees}")
    print("-" * 50)

    # 生成資料
    print("生成測試資料...")
    vectors = np.random.randn(n_vectors, dim).astype(np.float32)

    # 建構索引
    print("建構索引...")
    index = AnnoyIndex(dim, 'euclidean')

    start = time.time()
    for i, vector in enumerate(vectors):
        index.add_item(i, vector)
        if (i + 1) % 100000 == 0:
            print(f"  已添加 {i + 1:,} 個向量")

    index.build(n_trees)
    build_time = time.time() - start
    print(f"建構時間: {build_time:.2f} 秒")

    # 保存索引（可選）
    # index.save('vectors.ann')
    # 載入索引
    # index.load('vectors.ann')

    # 測試查詢
    print("\n查詢性能測試...")
    n_queries = 1000
    queries = np.random.randn(n_queries, dim).astype(np.float32)

    search_k_values = [10, 50, 100, 500, 1000]
    k = 10

    for search_k in search_k_values:
        start = time.time()
        for query in queries:
            _ = index.get_nns_by_vector(query, k, search_k=search_k)
        query_time = (time.time() - start) / n_queries * 1000

        # 計算召回率（採樣）
        recall_samples = []
        for query in queries[:100]:
            result = index.get_nns_by_vector(query, k, search_k=search_k)

            # 暴力搜尋作為真值
            distances = np.sqrt(np.sum((vectors - query) ** 2, axis=1))
            true_result = np.argsort(distances)[:k]

            recall = len(set(result) & set(true_result)) / k
            recall_samples.append(recall)

        avg_recall = np.mean(recall_samples)

        print(f"search_k={search_k:4d}: "
              f"召回率={avg_recall*100:.1f}%, "
              f"查詢時間={query_time:.2f}ms")

    # 記憶體使用
    import os
    temp_file = '/tmp/annoy_test.ann'
    index.save(temp_file)
    file_size = os.path.getsize(temp_file) / (1024 * 1024)
    os.remove(temp_file)
    print(f"\n索引大小: {file_size:.1f} MB")


# 運行基準測試
if __name__ == "__main__":
    benchmark_annoy(n_vectors=100000, dim=128, n_trees=50)
```

**Annoy 最佳化技巧**

```python
def optimize_annoy_for_recall(
    vectors: np.ndarray,
    target_recall: float = 0.95,
    k: int = 10
):
    """
    為目標召回率最佳化 Annoy 參數

    ‹1› 找到達到目標召回率的最小參數
    """
    from annoy import AnnoyIndex

    dim = vectors.shape[1]
    n_test = min(100, len(vectors))

    # 準備測試資料
    test_queries = vectors[:n_test]

    # 暴力搜尋作為真值
    ground_truth = []
    for query in test_queries:
        distances = np.sqrt(np.sum((vectors - query) ** 2, axis=1))
        ground_truth.append(np.argsort(distances)[1:k+1])  # 排除自身

    def test_config(n_trees: int, search_k: int) -> Tuple[float, float]:
        """測試配置的召回率和查詢時間"""
        index = AnnoyIndex(dim, 'euclidean')
        for i, v in enumerate(vectors):
            index.add_item(i, v)
        index.build(n_trees)

        recalls = []
        times = []

        for query, gt in zip(test_queries, ground_truth):
            start = time.time()
            result = index.get_nns_by_vector(query, k + 1, search_k=search_k)
            times.append(time.time() - start)

            result = [r for r in result if r != np.where(
                np.all(vectors == query, axis=1)
            )[0]][:k]
            recall = len(set(result) & set(gt)) / k
            recalls.append(recall)

        return np.mean(recalls), np.mean(times) * 1000

    # 搜尋最佳參數
    best_config = None
    best_time = float('inf')

    for n_trees in [10, 20, 50, 100]:
        for search_k in [k, k*5, k*10, k*50, k*100]:
            recall, query_time = test_config(n_trees, search_k)

            if recall >= target_recall and query_time < best_time:
                best_time = query_time
                best_config = {
                    'n_trees': n_trees,
                    'search_k': search_k,
                    'recall': recall,
                    'query_time_ms': query_time
                }

            print(f"n_trees={n_trees}, search_k={search_k}: "
                  f"recall={recall:.3f}, time={query_time:.2f}ms")

    print(f"\n最佳配置: {best_config}")
    return best_config
```

---

## 6.3 隨機投影在 LSH 中的應用

### 6.3.1 隨機投影的數學基礎

**Johnson-Lindenstrauss 引理**

這是隨機投影理論的基石：

```
Johnson-Lindenstrauss 引理：

對於任意 n 個點的集合和任意 ε ∈ (0, 1)，
存在從 ℝ^d 到 ℝ^k 的映射 f，其中 k = O(log n / ε²)，
使得對於所有點對 (u, v)：

(1 - ε)||u - v||² ≤ ||f(u) - f(v)||² ≤ (1 + ε)||u - v||²

直覺：
- 可以將高維資料投影到低維空間
- 只要維度 k 足夠（與 log n 成正比）
- 點之間的距離就能以 (1 ± ε) 的倍數保持

實際意義：
- 100 萬個 768 維向量
- 想要 ε = 0.1 的精度
- 只需要 k ≈ 4600 維（節省 40%）
- 想要 ε = 0.2 的精度
- 只需要 k ≈ 1150 維（節省 85%）
```

**隨機投影矩陣**

```python
import numpy as np

def create_random_projection_matrix(
    d_original: int,
    d_target: int,
    method: str = 'gaussian'
) -> np.ndarray:
    """
    創建隨機投影矩陣

    ‹1› method: 投影方法
        - 'gaussian': 高斯隨機矩陣
        - 'sparse': 稀疏隨機矩陣（更快）
        - 'achlioptas': Achlioptas 稀疏矩陣
    """
    if method == 'gaussian':
        # 高斯隨機矩陣
        R = np.random.randn(d_target, d_original) / np.sqrt(d_target)

    elif method == 'sparse':
        # 稀疏隨機矩陣（每行約 √d 個非零元素）
        sparsity = 1 / np.sqrt(d_original)
        R = np.zeros((d_target, d_original))
        for i in range(d_target):
            mask = np.random.random(d_original) < sparsity
            R[i, mask] = np.random.randn(mask.sum())
        R /= np.sqrt(d_target * sparsity)

    elif method == 'achlioptas':
        # Achlioptas 稀疏矩陣
        # P(R_ij = +1) = P(R_ij = -1) = 1/6
        # P(R_ij = 0) = 2/3
        probs = np.random.random((d_target, d_original))
        R = np.zeros((d_target, d_original))
        R[probs < 1/6] = np.sqrt(3)
        R[probs > 5/6] = -np.sqrt(3)
        R /= np.sqrt(d_target)

    else:
        raise ValueError(f"未知方法: {method}")

    return R.astype(np.float32)


class RandomProjection:
    """
    隨機投影降維

    ‹1› 保持距離的近似降維
    ‹2› 時間複雜度：O(d × k) 每個向量
    """

    def __init__(
        self,
        d_original: int,
        d_target: int = None,
        epsilon: float = 0.1,
        method: str = 'gaussian'
    ):
        """
        初始化

        ‹1› 可以指定目標維度，或通過 epsilon 計算
        """
        self.d_original = d_original

        if d_target is not None:
            self.d_target = d_target
        else:
            # 根據 JL 引理計算
            # k >= 4 * log(n) / (epsilon^2 / 2 - epsilon^3 / 3)
            # 簡化：k >= 8 * log(n) / epsilon^2
            # 假設 n = 1,000,000
            n = 1000000
            self.d_target = int(8 * np.log(n) / epsilon ** 2)

        self.method = method
        self.R = None

    def fit(self, X: np.ndarray = None):
        """
        生成投影矩陣
        """
        self.R = create_random_projection_matrix(
            self.d_original,
            self.d_target,
            self.method
        )
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        應用投影
        """
        return np.dot(X, self.R.T)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """
        擬合並投影
        """
        self.fit(X)
        return self.transform(X)


def verify_jl_lemma(
    n_points: int = 1000,
    d_original: int = 768,
    d_target: int = 128,
    n_pairs: int = 10000
):
    """
    驗證 Johnson-Lindenstrauss 引理

    ‹1› 比較投影前後的距離比例
    """
    # 生成隨機點
    X = np.random.randn(n_points, d_original).astype(np.float32)

    # 隨機投影
    rp = RandomProjection(d_original, d_target)
    X_projected = rp.fit_transform(X)

    # 隨機選擇點對
    pairs = np.random.choice(n_points, (n_pairs, 2), replace=True)

    # 計算距離比例
    ratios = []
    for i, j in pairs:
        if i == j:
            continue

        original_dist = np.linalg.norm(X[i] - X[j])
        projected_dist = np.linalg.norm(X_projected[i] - X_projected[j])

        ratio = projected_dist / original_dist
        ratios.append(ratio)

    ratios = np.array(ratios)

    print(f"原始維度: {d_original}")
    print(f"投影維度: {d_target}")
    print(f"壓縮比: {d_original / d_target:.1f}x")
    print(f"\n距離比例統計:")
    print(f"  平均值: {np.mean(ratios):.4f} (理想: 1.0)")
    print(f"  標準差: {np.std(ratios):.4f}")
    print(f"  最小值: {np.min(ratios):.4f}")
    print(f"  最大值: {np.max(ratios):.4f}")
    print(f"  [0.9, 1.1] 範圍內: {np.mean((ratios > 0.9) & (ratios < 1.1)) * 100:.1f}%")
    print(f"  [0.8, 1.2] 範圍內: {np.mean((ratios > 0.8) & (ratios < 1.2)) * 100:.1f}%")


# 驗證
verify_jl_lemma(n_points=1000, d_original=768, d_target=128)
```

### 6.3.2 隨機投影在高維資料降維與檢索中的實際應用

```python
class RandomProjectionSearch:
    """
    結合隨機投影和暴力搜尋

    ‹1› 先降維
    ‹2› 在低維空間搜尋
    ‹3› 可選：在原空間重排序
    """

    def __init__(
        self,
        d_original: int,
        d_target: int = 128,
        use_rerank: bool = True
    ):
        self.rp = RandomProjection(d_original, d_target)
        self.use_rerank = use_rerank

        self.original_vectors = None
        self.projected_vectors = None

    def fit(self, vectors: np.ndarray):
        """建構索引"""
        self.original_vectors = vectors
        self.projected_vectors = self.rp.fit_transform(vectors)

    def search(
        self,
        query: np.ndarray,
        k: int = 10,
        rerank_k: int = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        搜尋

        ‹1› rerank_k: 重排序的候選數量
        """
        if rerank_k is None:
            rerank_k = k * 10

        # 投影查詢向量
        query_projected = self.rp.transform(query.reshape(1, -1))[0]

        # 在投影空間搜尋
        distances_projected = np.sqrt(np.sum(
            (self.projected_vectors - query_projected) ** 2, axis=1
        ))

        if self.use_rerank:
            # 獲取候選
            candidate_indices = np.argsort(distances_projected)[:rerank_k]

            # 在原空間重排序
            candidate_vectors = self.original_vectors[candidate_indices]
            distances_original = np.sqrt(np.sum(
                (candidate_vectors - query) ** 2, axis=1
            ))

            top_k_idx = np.argsort(distances_original)[:k]
            indices = candidate_indices[top_k_idx]
            distances = distances_original[top_k_idx]
        else:
            top_k_idx = np.argsort(distances_projected)[:k]
            indices = top_k_idx
            distances = distances_projected[top_k_idx]

        return indices, distances


def compare_rp_methods(
    n_vectors: int = 100000,
    d_original: int = 768,
    d_targets: List[int] = [64, 128, 256, 384],
    k: int = 10
):
    """
    比較不同投影維度的性能
    """
    import time

    # 生成資料
    vectors = np.random.randn(n_vectors, d_original).astype(np.float32)
    queries = np.random.randn(100, d_original).astype(np.float32)

    # 真值
    print("計算真值...")
    ground_truth = []
    for query in queries:
        distances = np.sqrt(np.sum((vectors - query) ** 2, axis=1))
        ground_truth.append(np.argsort(distances)[:k])

    # 基準：原空間暴力搜尋
    print("\n原空間暴力搜尋...")
    start = time.time()
    for query in queries:
        distances = np.sqrt(np.sum((vectors - query) ** 2, axis=1))
        _ = np.argsort(distances)[:k]
    baseline_time = (time.time() - start) / len(queries) * 1000
    print(f"  查詢時間: {baseline_time:.2f} ms")

    # 測試不同投影維度
    print("\n隨機投影搜尋:")
    results = []

    for d_target in d_targets:
        searcher = RandomProjectionSearch(
            d_original=d_original,
            d_target=d_target,
            use_rerank=True
        )
        searcher.fit(vectors)

        # 測試性能
        start = time.time()
        recalls = []

        for query, gt in zip(queries, ground_truth):
            indices, _ = searcher.search(query, k=k, rerank_k=k*10)
            recall = len(set(indices) & set(gt)) / k
            recalls.append(recall)

        query_time = (time.time() - start) / len(queries) * 1000
        avg_recall = np.mean(recalls)

        results.append({
            'd_target': d_target,
            'recall': avg_recall,
            'query_time': query_time,
            'speedup': baseline_time / query_time
        })

        print(f"  d_target={d_target:3d}: "
              f"recall={avg_recall*100:.1f}%, "
              f"time={query_time:.2f}ms, "
              f"speedup={baseline_time/query_time:.1f}x")

    return results
```

### 6.3.3 隨機投影在人物誌降維與檢索中的應用

```python
class UserProfileSearch:
    """
    使用者畫像搜尋系統

    ‹1› 使用隨機投影處理高維用戶特徵
    ‹2› 支援相似用戶查找
    """

    def __init__(
        self,
        n_features: int,
        d_target: int = 64
    ):
        """
        初始化

        ‹1› n_features: 原始特徵數量
        """
        self.n_features = n_features
        self.d_target = d_target

        self.rp = RandomProjection(n_features, d_target)
        self.user_profiles = {}  # {user_id: original_profile}
        self.projected_profiles = None
        self.user_ids = []

    def _normalize_profile(self, profile: dict) -> np.ndarray:
        """
        將用戶畫像轉換為向量

        ‹1› 處理各種類型的特徵
        """
        vector = np.zeros(self.n_features, dtype=np.float32)

        # 假設特徵已經按索引組織
        for feature_idx, value in profile.get('features', {}).items():
            if isinstance(feature_idx, int) and feature_idx < self.n_features:
                if isinstance(value, (int, float)):
                    vector[feature_idx] = value
                elif isinstance(value, list):
                    # 多值特徵取平均
                    vector[feature_idx] = np.mean(value)

        return vector

    def add_user(self, user_id: str, profile: dict):
        """添加用戶"""
        vector = self._normalize_profile(profile)
        self.user_profiles[user_id] = {
            'profile': profile,
            'vector': vector
        }

    def build_index(self):
        """建構索引"""
        self.user_ids = list(self.user_profiles.keys())
        vectors = np.array([
            self.user_profiles[uid]['vector']
            for uid in self.user_ids
        ])

        self.projected_profiles = self.rp.fit_transform(vectors)

    def find_similar_users(
        self,
        user_id: str,
        k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        找到相似用戶
        """
        if user_id not in self.user_profiles:
            return []

        # 獲取投影向量
        user_idx = self.user_ids.index(user_id)
        query_projected = self.projected_profiles[user_idx]

        # 計算距離
        distances = np.sqrt(np.sum(
            (self.projected_profiles - query_projected) ** 2, axis=1
        ))

        # 排除自身
        distances[user_idx] = np.inf

        # 取 top-k
        top_k_idx = np.argsort(distances)[:k]

        results = [
            (self.user_ids[idx], 1 / (1 + distances[idx]))
            for idx in top_k_idx
        ]

        return results

    def find_users_by_profile(
        self,
        target_profile: dict,
        k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        根據目標畫像找用戶
        """
        target_vector = self._normalize_profile(target_profile)
        target_projected = self.rp.transform(target_vector.reshape(1, -1))[0]

        distances = np.sqrt(np.sum(
            (self.projected_profiles - target_projected) ** 2, axis=1
        ))

        top_k_idx = np.argsort(distances)[:k]

        results = [
            (self.user_ids[idx], 1 / (1 + distances[idx]))
            for idx in top_k_idx
        ]

        return results


# 使用示例
def demo_user_profile_search():
    # 創建搜尋系統
    search = UserProfileSearch(n_features=1000, d_target=64)

    # 添加模擬用戶
    np.random.seed(42)
    for i in range(10000):
        profile = {
            'features': {
                j: np.random.random()
                for j in np.random.choice(1000, 50, replace=False)
            }
        }
        search.add_user(f'user_{i}', profile)

    # 建構索引
    search.build_index()

    # 查找相似用戶
    similar = search.find_similar_users('user_0', k=5)
    print("與 user_0 相似的用戶:")
    for user_id, score in similar:
        print(f"  {user_id}: {score:.4f}")
```

---

## 6.4 本章小結

在本章中，我們學習了三種重要的向量搜尋最佳化技術：

1. **BallTree**
   - 使用球形包圍盒組織資料
   - 支援任意距離度量
   - 在中等維度下表現良好
   - 適合範圍查詢和需要精確結果的場景

2. **Annoy**
   - 使用隨機超平面構建樹森林
   - 支援記憶體映射，適合多進程共享
   - 索引建構後不可變
   - 適合靜態資料集和需要低記憶體開銷的場景

3. **隨機投影**
   - 有理論保證的降維方法（JL 引理）
   - 可以與任何搜尋方法結合
   - 權衡精度和速度
   - 適合作為預處理步驟或與其他方法組合

**選擇建議**

| 場景 | 推薦方法 |
|------|----------|
| 資料會頻繁更新 | HNSW 或 BallTree |
| 資料靜態，需要低記憶體 | Annoy |
| 需要精確範圍查詢 | BallTree |
| 超高維資料 | 隨機投影 + 其他方法 |
| 需要記憶體映射 | Annoy |
| 需要最高召回率 | HNSW |

---

## 6.5 思考題

1. **概念理解**
   - 解釋 BallTree 的剪枝條件，以及為什麼這個條件在高維空間中可能失效。

2. **技術分析**
   - Annoy 使用隨機超平面分割空間，而 k-d tree 使用座標軸分割。分析這兩種方法在高維空間中的差異。

3. **實作練習**
   - 實現一個結合隨機投影和 BallTree 的搜尋系統：
     a) 先用隨機投影降維
     b) 在低維空間建構 BallTree
     c) 比較與直接使用 BallTree 的性能差異

4. **系統設計**
   - 設計一個多階段的向量搜尋管線：
     a) 第一階段：使用 LSH 或隨機投影快速篩選候選
     b) 第二階段：使用 BallTree 或精確搜尋重排序
     c) 分析這種設計的優缺點

5. **批判性思考**
   - Johnson-Lindenstrauss 引理告訴我們可以保持距離地降維，但實際應用中降維後的搜尋效果可能不如預期。討論可能的原因。

---

> **下一章預告**：在第 7 章中，我們將開始探討相似性測量的更多細節，包括曼哈頓距離、切比雪夫距離等不同的距離度量，以及它們在實際應用中的選擇與最佳化。
