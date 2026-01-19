# 第 5 章：分層定位與局部敏感雜湊

> 「最快的路不一定是直線，有時候繞道反而更快到達目的地。」

## 本章學習目標

完成本章後，你將能夠：
- 理解 HNSW 的分層圖結構與搜尋路徑最佳化原理
- 掌握 LSH 的雜湊函式設計與參數調優方法
- 分析 HNSW 與 LSH 的時間複雜度與適用場景
- 應用這兩種演算法解決實際的向量檢索問題

---

## 引言：從暴力到智慧

在上一章中，我們學習了暴力搜尋。它簡單、精確，但當資料量達到百萬級時，每次查詢都要遍歷所有向量，這是不可接受的。

想像你在一個擁有一百萬本書的圖書館中尋找一本特定的書。暴力搜尋就像是從第一本書開始，一本一本地檢查。而 HNSW 和 LSH 提供了更聰明的方法：

- **HNSW**（Hierarchical Navigable Small World）：像是圖書館的多層索引系統。你先看樓層指示牌，找到對的樓層；再看區域指示牌，找到對的區域；最後在書架間找到目標。
- **LSH**（Locality Sensitive Hashing）：像是把書按主題分類。當你尋找一本關於「機器學習」的書時，直接去「計算機科學」區，而不是遍歷整個圖書館。

本章將深入探討這兩種革命性的演算法。

---

## 5.1 HNSW 的核心原理：圖結構與分層搜尋路徑最佳化

### 5.1.1 基於圖結構的近鄰搜尋模型

**從小世界網絡說起**

1998 年，社會學家 Duncan Watts 和 Steven Strogatz 提出了「小世界網絡」理論：在一個龐大的社交網絡中，任意兩個人之間的平均距離出奇地小（約 6 步）。這就是著名的「六度分隔」理論。

HNSW 借鑒了這個思想：如果我們能把向量組織成一個「小世界」網絡，那麼從任意起點到達目標的步數就會很少。

**可導航小世界圖（NSW）**

在深入 HNSW 之前，先理解其前身 NSW：

```
NSW 的構建過程：

1. 初始化：空圖

2. 逐一插入向量：
   對於新向量 v：
   a) 從現有圖中隨機選一個入口點
   b) 貪婪搜尋找到 v 的 M 個最近鄰
   c) 將 v 與這 M 個鄰居連接

3. 結果：一個稀疏但高度連通的圖

NSW 的搜尋過程：

1. 從入口點開始
2. 重複以下步驟：
   a) 檢查當前節點的所有鄰居
   b) 移動到最接近查詢的鄰居
   c) 如果沒有更近的鄰居，停止
3. 返回找到的最近點
```

```python
import numpy as np
from typing import List, Set, Tuple
import heapq

class NSWGraph:
    """
    可導航小世界圖的簡化實現

    ‹1› 每個節點維護固定數量的鄰居連接
    """

    def __init__(self, max_neighbors: int = 16):
        self.max_neighbors = max_neighbors
        self.nodes = {}  # {node_id: vector}
        self.edges = {}  # {node_id: set of neighbor_ids}

    def _distance(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """計算歐幾里得距離"""
        return np.sqrt(np.sum((v1 - v2) ** 2))

    def _greedy_search(
        self,
        query: np.ndarray,
        entry_point: int,
        ef: int = 1
    ) -> List[Tuple[float, int]]:
        """
        貪婪搜尋

        ‹1› ef: 搜尋時維護的候選集大小
        """
        visited = set()
        candidates = []  # 最小堆 (distance, node_id)
        result = []  # 最大堆 (-distance, node_id)

        # 初始化
        entry_dist = self._distance(query, self.nodes[entry_point])
        heapq.heappush(candidates, (entry_dist, entry_point))
        heapq.heappush(result, (-entry_dist, entry_point))
        visited.add(entry_point)

        while candidates:
            current_dist, current_node = heapq.heappop(candidates)

            # 如果當前節點比結果集中最遠的還遠，停止
            if result and current_dist > -result[0][0]:
                break

            # 檢查鄰居
            for neighbor in self.edges.get(current_node, set()):
                if neighbor in visited:
                    continue

                visited.add(neighbor)
                neighbor_dist = self._distance(query, self.nodes[neighbor])

                # 如果比結果集中最遠的更近，加入
                if len(result) < ef or neighbor_dist < -result[0][0]:
                    heapq.heappush(candidates, (neighbor_dist, neighbor))
                    heapq.heappush(result, (-neighbor_dist, neighbor))

                    # 維護結果集大小
                    if len(result) > ef:
                        heapq.heappop(result)

        # 返回按距離排序的結果
        return sorted([(-d, n) for d, n in result])

    def insert(self, node_id: int, vector: np.ndarray):
        """
        插入新節點
        """
        self.nodes[node_id] = vector
        self.edges[node_id] = set()

        if len(self.nodes) == 1:
            return  # 第一個節點，沒有鄰居

        # 隨機選擇入口點
        entry_point = np.random.choice(list(self.nodes.keys()))

        # 搜尋最近的鄰居
        neighbors = self._greedy_search(
            vector,
            entry_point,
            ef=self.max_neighbors
        )

        # 建立雙向連接
        for dist, neighbor_id in neighbors[:self.max_neighbors]:
            if neighbor_id == node_id:
                continue

            self.edges[node_id].add(neighbor_id)
            self.edges[neighbor_id].add(node_id)

            # 如果鄰居的連接數超過上限，移除最遠的
            if len(self.edges[neighbor_id]) > self.max_neighbors:
                # 找到最遠的鄰居並移除
                farthest = max(
                    self.edges[neighbor_id],
                    key=lambda n: self._distance(
                        self.nodes[neighbor_id],
                        self.nodes[n]
                    )
                )
                self.edges[neighbor_id].remove(farthest)
                self.edges[farthest].discard(neighbor_id)

    def search(self, query: np.ndarray, k: int = 10) -> List[int]:
        """
        搜尋最近的 k 個節點
        """
        if not self.nodes:
            return []

        entry_point = np.random.choice(list(self.nodes.keys()))
        results = self._greedy_search(query, entry_point, ef=max(k * 2, 50))

        return [node_id for _, node_id in results[:k]]
```

**NSW 的問題**

單層 NSW 有一個明顯的問題：**早期停止**。

```
問題示例：

假設查詢 q 的真正最近鄰是 t，但它們之間沒有直接路徑。

     ●──●──●──●
    /          \
   q ●          ● t
    \          /
     ●──●──●──●

貪婪搜尋可能陷入局部最優：
- 找到一個「還不錯」的鄰居 x
- x 的所有鄰居都比 x 離 q 更遠
- 搜尋停止，但 t 被遺漏

這就是為什麼需要分層結構。
```

### 5.1.2 分層搜尋路徑的建構與更新

**HNSW 的核心思想**

HNSW 通過添加「高速公路」層來解決早期停止的問題：

```
HNSW 的分層結構：

Layer 2（最高層，最稀疏）
    •─────────────────────•
    │                     │
    快速跨越大距離

Layer 1（中間層）
    •───•───────────•─────•
    │   │           │     │
    中等粒度的導航

Layer 0（底層，最密集，包含所有節點）
    •─•─•─•─•─•─•─•─•─•─•─•
    精確定位

規則：
- 如果一個節點出現在 Layer i，它必須出現在 Layer 0 到 i-1
- 節點進入更高層的概率指數遞減
- 搜尋從最高層開始，逐層下降
```

**數學基礎：層級分配**

```
節點的最大層級決定方式：

l = floor(-ln(uniform(0, 1)) × mL)

其中：
- uniform(0, 1) 是 [0, 1] 均勻分佈的隨機數
- mL 是層級乘數，通常設為 1/ln(M)
- M 是每個節點的最大鄰居數

這導致：
- 大約 1/M 的節點會進入 Layer 1
- 大約 1/M² 的節點會進入 Layer 2
- 以此類推

例如 M = 16：
- Layer 0: 100% 的節點
- Layer 1: 約 6.25% 的節點
- Layer 2: 約 0.39% 的節點
- Layer 3: 約 0.024% 的節點
```

**HNSW 的完整實現**

```python
import numpy as np
from typing import List, Dict, Set, Tuple
import heapq
import math

class HNSW:
    """
    HNSW (Hierarchical Navigable Small World) 實現

    ‹1› 分層圖結構
    ‹2› 支援高效的插入和搜尋
    """

    def __init__(
        self,
        dim: int,
        M: int = 16,
        ef_construction: int = 200,
        mL: float = None
    ):
        """
        初始化 HNSW 索引

        ‹1› M: 每個節點在每一層的最大鄰居數
        ‹2› ef_construction: 建構時的候選集大小
        ‹3› mL: 層級乘數
        """
        self.dim = dim
        self.M = M
        self.M0 = 2 * M  # Layer 0 的最大鄰居數（通常是 2M）
        self.ef_construction = ef_construction
        self.mL = mL if mL else 1.0 / math.log(M)

        # 資料結構
        self.vectors = {}  # {node_id: vector}
        self.layers = []  # 每一層的鄰接表
        self.max_layer = -1
        self.entry_point = None
        self.node_levels = {}  # {node_id: max_level}

    def _distance(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """計算歐幾里得距離"""
        return np.sqrt(np.sum((v1 - v2) ** 2))

    def _get_random_level(self) -> int:
        """隨機決定節點的最高層級"""
        r = np.random.random()
        level = int(-math.log(r) * self.mL)
        return level

    def _search_layer(
        self,
        query: np.ndarray,
        entry_points: List[int],
        ef: int,
        layer: int
    ) -> List[Tuple[float, int]]:
        """
        在單一層中搜尋

        ‹1› 返回 ef 個最近的節點
        """
        visited = set(entry_points)
        candidates = []  # 最小堆
        results = []  # 最大堆

        for ep in entry_points:
            dist = self._distance(query, self.vectors[ep])
            heapq.heappush(candidates, (dist, ep))
            heapq.heappush(results, (-dist, ep))

        while candidates:
            current_dist, current_node = heapq.heappop(candidates)

            # 剪枝：如果當前候選比結果集中最遠的還遠
            if results and current_dist > -results[0][0]:
                break

            # 獲取當前層的鄰居
            if layer < len(self.layers) and current_node in self.layers[layer]:
                neighbors = self.layers[layer][current_node]
            else:
                neighbors = set()

            for neighbor in neighbors:
                if neighbor in visited:
                    continue

                visited.add(neighbor)
                neighbor_dist = self._distance(query, self.vectors[neighbor])

                # 如果結果集未滿，或者比最遠的更近
                if len(results) < ef or neighbor_dist < -results[0][0]:
                    heapq.heappush(candidates, (neighbor_dist, neighbor))
                    heapq.heappush(results, (-neighbor_dist, neighbor))

                    if len(results) > ef:
                        heapq.heappop(results)

        return sorted([(-d, n) for d, n in results])

    def _select_neighbors_simple(
        self,
        candidates: List[Tuple[float, int]],
        M: int
    ) -> List[int]:
        """簡單的鄰居選擇：取最近的 M 個"""
        return [node_id for _, node_id in candidates[:M]]

    def _select_neighbors_heuristic(
        self,
        query: np.ndarray,
        candidates: List[Tuple[float, int]],
        M: int,
        extend_candidates: bool = True
    ) -> List[int]:
        """
        啟發式鄰居選擇

        ‹1› 不只選擇最近的，還考慮多樣性
        ‹2› 避免選擇互相太近的鄰居
        """
        selected = []
        remaining = list(candidates)

        while remaining and len(selected) < M:
            # 選擇當前最近的
            best = remaining[0]
            remaining = remaining[1:]

            # 檢查是否比已選擇的任何一個更近
            good = True
            for _, selected_id in [(d, i) for d, i in
                                   zip([self._distance(query, self.vectors[s])
                                        for s in selected], selected)]:
                if (self._distance(self.vectors[best[1]],
                                   self.vectors[selected_id]) <
                    best[0]):
                    good = False
                    break

            if good:
                selected.append(best[1])

        return selected

    def insert(self, node_id: int, vector: np.ndarray):
        """
        插入新節點

        ‹1› 決定節點的層級
        ‹2› 從最高層開始搜尋
        ‹3› 在每一層建立連接
        """
        self.vectors[node_id] = vector
        node_level = self._get_random_level()
        self.node_levels[node_id] = node_level

        # 確保層結構足夠
        while len(self.layers) <= node_level:
            self.layers.append({})

        # 第一個節點
        if self.entry_point is None:
            self.entry_point = node_id
            self.max_layer = node_level
            for layer in range(node_level + 1):
                self.layers[layer][node_id] = set()
            return

        # 從入口點開始
        current_node = self.entry_point

        # 在高於 node_level 的層中只做貪婪搜尋（不建立連接）
        for layer in range(self.max_layer, node_level, -1):
            result = self._search_layer(
                vector, [current_node], ef=1, layer=layer
            )
            current_node = result[0][1]

        # 在 node_level 及以下的層中搜尋並建立連接
        for layer in range(min(node_level, self.max_layer), -1, -1):
            # 搜尋候選鄰居
            result = self._search_layer(
                vector, [current_node], ef=self.ef_construction, layer=layer
            )

            # 選擇鄰居
            max_neighbors = self.M if layer > 0 else self.M0
            neighbors = self._select_neighbors_simple(result, max_neighbors)

            # 初始化節點的鄰居集
            if node_id not in self.layers[layer]:
                self.layers[layer][node_id] = set()

            # 建立雙向連接
            for neighbor in neighbors:
                self.layers[layer][node_id].add(neighbor)

                if neighbor not in self.layers[layer]:
                    self.layers[layer][neighbor] = set()
                self.layers[layer][neighbor].add(node_id)

                # 如果鄰居的連接數超過上限，修剪
                if len(self.layers[layer][neighbor]) > max_neighbors:
                    # 重新選擇鄰居
                    neighbor_candidates = [
                        (self._distance(self.vectors[neighbor],
                                       self.vectors[n]), n)
                        for n in self.layers[layer][neighbor]
                    ]
                    neighbor_candidates.sort()
                    new_neighbors = self._select_neighbors_simple(
                        neighbor_candidates, max_neighbors
                    )
                    removed = self.layers[layer][neighbor] - set(new_neighbors)
                    self.layers[layer][neighbor] = set(new_neighbors)

                    # 移除反向連接
                    for removed_id in removed:
                        if removed_id in self.layers[layer]:
                            self.layers[layer][removed_id].discard(neighbor)

            # 更新下一層的入口點
            if result:
                current_node = result[0][1]

        # 更新全局入口點
        if node_level > self.max_layer:
            self.max_layer = node_level
            self.entry_point = node_id

    def search(
        self,
        query: np.ndarray,
        k: int = 10,
        ef: int = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        搜尋最近的 k 個節點

        ‹1› ef: 搜尋時的候選集大小（越大越精確但越慢）
        """
        if self.entry_point is None:
            return np.array([]), np.array([])

        if ef is None:
            ef = max(k, 50)

        # 從入口點開始
        current_node = self.entry_point

        # 在高層中貪婪搜尋
        for layer in range(self.max_layer, 0, -1):
            result = self._search_layer(
                query, [current_node], ef=1, layer=layer
            )
            current_node = result[0][1]

        # 在底層搜尋
        result = self._search_layer(
            query, [current_node], ef=ef, layer=0
        )

        # 返回 top-k
        result = result[:k]
        indices = np.array([node_id for _, node_id in result])
        distances = np.array([dist for dist, _ in result])

        return indices, distances


# 使用示例
def demo_hnsw():
    """HNSW 使用演示"""
    np.random.seed(42)

    # 生成測試資料
    n_vectors = 10000
    dim = 128

    vectors = np.random.randn(n_vectors, dim).astype(np.float32)
    query = np.random.randn(dim).astype(np.float32)

    # 建立索引
    print("建立 HNSW 索引...")
    hnsw = HNSW(dim=dim, M=16, ef_construction=200)

    for i, vector in enumerate(vectors):
        hnsw.insert(i, vector)
        if (i + 1) % 1000 == 0:
            print(f"  已插入 {i + 1} 個向量")

    # 搜尋
    print("\n搜尋中...")
    indices, distances = hnsw.search(query, k=10, ef=100)

    print(f"最近的 10 個向量索引: {indices}")
    print(f"對應的距離: {distances}")

    # 驗證（與暴力搜尋比較）
    print("\n驗證（暴力搜尋）...")
    all_distances = np.sqrt(np.sum((vectors - query) ** 2, axis=1))
    true_indices = np.argsort(all_distances)[:10]

    recall = len(set(indices) & set(true_indices)) / 10
    print(f"召回率: {recall * 100:.1f}%")

if __name__ == "__main__":
    demo_hnsw()
```

### 5.1.3 HNSW 索引時間複雜度分析

**建構複雜度**

```
插入單個節點的複雜度：

1. 層級決定：O(1)

2. 高層搜尋（從最高層到節點層）：
   - 每層訪問 O(log n) 個節點
   - 共 O(log n) 層
   - 總計：O(log² n)

3. 連接建立（從節點層到底層）：
   - 每層搜尋：O(ef_construction × log n)
   - 每層連接：O(M)
   - 共 O(log n) 層（平均）
   - 總計：O(ef_construction × log² n)

插入 n 個節點的總複雜度：O(n × ef_construction × log² n)
```

**搜尋複雜度**

```
搜尋複雜度分析：

1. 高層搜尋（從最高層到 Layer 1）：
   - 每層訪問 O(1) 個節點
   - 共 O(log n) 層
   - 總計：O(log n)

2. 底層搜尋：
   - 訪問 O(ef) 個節點
   - 每個節點檢查 O(M) 個鄰居
   - 總計：O(ef × M)

總搜尋複雜度：O(log n + ef × M)

對於固定的 ef 和 M，簡化為：O(log n)
```

**空間複雜度**

```
空間複雜度分析：

1. 向量儲存：O(n × d)

2. 圖結構：
   - Layer 0：n 個節點，每個 O(M0) 條邊 → O(n × M0)
   - Layer 1：約 n/M 個節點，每個 O(M) 條邊 → O(n)
   - Layer 2：約 n/M² 個節點 → O(n/M)
   - 總計：O(n × M0) ≈ O(n × M)

總空間複雜度：O(n × d + n × M)

對於典型的 M = 16-64，圖結構開銷約為向量本身的 5-20%
```

---

## 5.2 局部敏感雜湊的設計與性能調優

### 5.2.1 雜湊函式的設計與向量分區原理

**LSH 的核心思想**

傳統雜湊函式（如 MD5）的設計目標是：相似的輸入產生完全不同的輸出。

LSH 恰恰相反：**相似的向量應該有更高的概率被映射到相同的雜湊桶**。

```
LSH 的基本性質：

對於雜湊函式 h 和相似度閾值 s：

1. 如果 sim(v1, v2) ≥ s，則 P[h(v1) = h(v2)] ≥ p1（高概率碰撞）
2. 如果 sim(v1, v2) < s，則 P[h(v1) = h(v2)] ≤ p2（低概率碰撞）

其中 p1 > p2，差距越大，LSH 的品質越好
```

**隨機超平面 LSH（用於餘弦相似度）**

```
原理：

1. 生成隨機向量 r（與資料同維度）
2. 雜湊函式：h(v) = sign(v · r)
   - 如果內積 > 0，返回 1
   - 如果內積 ≤ 0，返回 0

為什麼這有效？

v · r > 0 意味著 v 和 r 的夾角 < 90°

對於兩個向量 v1 和 v2：
- 它們的夾角為 θ
- 它們在隨機超平面同側的概率 = 1 - θ/π
- 即：P[h(v1) = h(v2)] = 1 - arccos(cos(v1, v2)) / π
```

```python
import numpy as np
from typing import List, Tuple, Dict

class RandomProjectionLSH:
    """
    隨機投影 LSH（用於餘弦相似度）

    ‹1› 使用隨機超平面將向量映射到二進位編碼
    """

    def __init__(
        self,
        dim: int,
        n_hashes: int = 16,
        n_tables: int = 4
    ):
        """
        初始化

        ‹1› n_hashes: 每個雜湊表的位數
        ‹2› n_tables: 雜湊表數量（越多召回率越高）
        """
        self.dim = dim
        self.n_hashes = n_hashes
        self.n_tables = n_tables

        # 生成隨機投影矩陣
        self.projections = [
            np.random.randn(n_hashes, dim).astype(np.float32)
            for _ in range(n_tables)
        ]

        # 雜湊表
        self.tables = [dict() for _ in range(n_tables)]
        self.vectors = {}  # {id: vector}

    def _hash_vector(
        self,
        vector: np.ndarray,
        table_idx: int
    ) -> int:
        """
        將向量雜湊到整數

        ‹1› 使用符號函數將投影結果轉換為二進位
        """
        projections = self.projections[table_idx]
        # 計算投影
        dots = np.dot(projections, vector)
        # 轉換為二進位
        bits = (dots > 0).astype(int)
        # 轉換為整數
        hash_value = sum(bit << i for i, bit in enumerate(bits))
        return hash_value

    def insert(self, id: int, vector: np.ndarray):
        """
        插入向量
        """
        self.vectors[id] = vector

        for table_idx in range(self.n_tables):
            hash_value = self._hash_vector(vector, table_idx)

            if hash_value not in self.tables[table_idx]:
                self.tables[table_idx][hash_value] = []
            self.tables[table_idx][hash_value].append(id)

    def search(
        self,
        query: np.ndarray,
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        搜尋最近的 k 個向量
        """
        # 收集候選
        candidates = set()
        for table_idx in range(self.n_tables):
            hash_value = self._hash_vector(query, table_idx)
            if hash_value in self.tables[table_idx]:
                candidates.update(self.tables[table_idx][hash_value])

        if not candidates:
            return np.array([]), np.array([])

        # 對候選計算精確距離
        candidate_vectors = np.array([self.vectors[c] for c in candidates])
        candidate_ids = list(candidates)

        # 餘弦相似度
        query_norm = query / np.linalg.norm(query)
        candidate_norms = candidate_vectors / np.linalg.norm(
            candidate_vectors, axis=1, keepdims=True
        )
        similarities = np.dot(candidate_norms, query_norm)

        # 排序
        top_k_idx = np.argsort(-similarities)[:k]

        indices = np.array([candidate_ids[i] for i in top_k_idx])
        distances = 1 - similarities[top_k_idx]  # 餘弦距離

        return indices, distances


# 歐幾里得距離的 LSH（p-stable LSH）
class EuclideanLSH:
    """
    歐幾里得距離的 LSH

    ‹1› 使用 p-stable 分佈（高斯分佈）
    ‹2› 將向量映射到離散桶
    """

    def __init__(
        self,
        dim: int,
        n_hashes: int = 16,
        n_tables: int = 4,
        bucket_width: float = 4.0
    ):
        """
        初始化

        ‹1› bucket_width: 桶寬度，越大越寬鬆
        """
        self.dim = dim
        self.n_hashes = n_hashes
        self.n_tables = n_tables
        self.bucket_width = bucket_width

        # 隨機投影向量和偏移
        self.projections = []
        self.biases = []

        for _ in range(n_tables):
            # 高斯隨機向量
            proj = np.random.randn(n_hashes, dim).astype(np.float32)
            # 均勻分佈的偏移
            bias = np.random.uniform(0, bucket_width, n_hashes).astype(np.float32)
            self.projections.append(proj)
            self.biases.append(bias)

        self.tables = [dict() for _ in range(n_tables)]
        self.vectors = {}

    def _hash_vector(
        self,
        vector: np.ndarray,
        table_idx: int
    ) -> Tuple[int, ...]:
        """
        計算雜湊值

        ‹1› h(v) = floor((v · a + b) / w)
        """
        proj = self.projections[table_idx]
        bias = self.biases[table_idx]

        dots = np.dot(proj, vector) + bias
        buckets = np.floor(dots / self.bucket_width).astype(int)

        return tuple(buckets)

    def insert(self, id: int, vector: np.ndarray):
        """插入向量"""
        self.vectors[id] = vector

        for table_idx in range(self.n_tables):
            hash_value = self._hash_vector(vector, table_idx)

            if hash_value not in self.tables[table_idx]:
                self.tables[table_idx][hash_value] = []
            self.tables[table_idx][hash_value].append(id)

    def search(
        self,
        query: np.ndarray,
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """搜尋最近的 k 個向量"""
        candidates = set()

        for table_idx in range(self.n_tables):
            hash_value = self._hash_vector(query, table_idx)
            if hash_value in self.tables[table_idx]:
                candidates.update(self.tables[table_idx][hash_value])

        if not candidates:
            return np.array([]), np.array([])

        # 計算精確距離
        candidate_vectors = np.array([self.vectors[c] for c in candidates])
        candidate_ids = list(candidates)

        distances = np.sqrt(np.sum((candidate_vectors - query) ** 2, axis=1))

        # 排序
        top_k_idx = np.argsort(distances)[:k]

        indices = np.array([candidate_ids[i] for i in top_k_idx])
        dists = distances[top_k_idx]

        return indices, dists
```

### 5.2.2 LSH 桶化與參數調優

**參數對性能的影響**

```
LSH 的關鍵參數：

1. n_hashes（每個表的雜湊數）：
   - 越多 → 每個桶越小 → 精度越高，召回率越低
   - 越少 → 每個桶越大 → 召回率越高，精度越低

2. n_tables（雜湊表數量）：
   - 越多 → 候選越多 → 召回率越高，計算量越大
   - 越少 → 候選越少 → 速度越快，召回率越低

3. bucket_width（桶寬度，歐幾里得 LSH）：
   - 越大 → 桶越寬 → 召回率越高，精度越低
   - 越小 → 桶越窄 → 精度越高，召回率越低

權衡：
- 召回率 ↑ = 候選數 ↑ = 計算量 ↑ = 速度 ↓
- 需要在召回率和速度之間找到平衡點
```

**理論分析**

```
假設兩個向量的相似度為 s（餘弦相似度）：

單個雜湊函式碰撞概率：
p(s) = 1 - arccos(s) / π

使用 k 個雜湊函式（AND 邏輯）：
P_table(s) = p(s)^k

使用 L 個雜湊表（OR 邏輯）：
P_total(s) = 1 - (1 - p(s)^k)^L

例如，對於 s = 0.9（高相似度）：
p(0.9) ≈ 0.86

k = 16, L = 4:
P_table(0.9) = 0.86^16 ≈ 0.093
P_total(0.9) = 1 - (1 - 0.093)^4 ≈ 0.32

召回率約 32%！需要增加 L 或減少 k。

k = 8, L = 10:
P_table(0.9) = 0.86^8 ≈ 0.30
P_total(0.9) = 1 - (1 - 0.30)^10 ≈ 0.97

召回率約 97%，好多了！
```

**參數調優策略**

```python
def tune_lsh_parameters(
    vectors: np.ndarray,
    queries: np.ndarray,
    ground_truth: List[List[int]],
    target_recall: float = 0.95,
    k: int = 10
) -> Dict:
    """
    自動調優 LSH 參數

    ‹1› 使用網格搜尋找到滿足召回率的最小參數
    """
    dim = vectors.shape[1]

    best_params = None
    best_query_time = float('inf')

    # 參數網格
    n_hashes_range = [4, 8, 12, 16, 20]
    n_tables_range = [2, 4, 8, 16, 32]

    for n_hashes in n_hashes_range:
        for n_tables in n_tables_range:
            # 建立索引
            lsh = RandomProjectionLSH(
                dim=dim,
                n_hashes=n_hashes,
                n_tables=n_tables
            )

            for i, vector in enumerate(vectors):
                lsh.insert(i, vector)

            # 測試召回率
            recalls = []
            import time
            total_time = 0

            for query, gt in zip(queries, ground_truth):
                start = time.time()
                indices, _ = lsh.search(query, k=k)
                total_time += time.time() - start

                recall = len(set(indices) & set(gt[:k])) / k
                recalls.append(recall)

            avg_recall = np.mean(recalls)
            avg_time = total_time / len(queries)

            print(f"n_hashes={n_hashes}, n_tables={n_tables}: "
                  f"recall={avg_recall:.3f}, time={avg_time*1000:.2f}ms")

            if avg_recall >= target_recall and avg_time < best_query_time:
                best_query_time = avg_time
                best_params = {
                    'n_hashes': n_hashes,
                    'n_tables': n_tables,
                    'recall': avg_recall,
                    'query_time_ms': avg_time * 1000
                }

    return best_params
```

### 5.2.3 LSH 的記憶體佔用與計算性能分析

**記憶體分析**

```
LSH 記憶體佔用：

1. 向量儲存：O(n × d)

2. 投影矩陣：O(L × k × d)
   - L: 雜湊表數量
   - k: 每表雜湊數
   - d: 向量維度
   - 例如：L=10, k=16, d=768 → 約 470 KB

3. 雜湊表：
   - 每個表：O(n) 個 ID 存儲
   - 總計：O(L × n)
   - 例如：L=10, n=1M → 約 40 MB

總記憶體：O(n × d + L × k × d + L × n)
         ≈ O(n × d)（向量主導）

對比 HNSW：
LSH 的額外開銷較小（無圖結構）
但通常需要更多雜湊表來達到相同召回率
```

**計算性能分析**

```
查詢時間分析：

1. 雜湊計算：O(L × k × d)
   - 計算 L 個雜湊值
   - 每個需要 k 次投影

2. 候選收集：O(L)
   - 查找 L 個雜湊表

3. 精確距離計算：O(|candidates| × d)
   - 對所有候選計算距離

總時間：O(L × k × d + |candidates| × d)

關鍵問題：|candidates| 的大小

- 如果參數設置太寬鬆：候選太多，精確計算耗時
- 如果參數設置太嚴格：候選太少，召回率低

最佳情況：|candidates| = O(1)，查詢時間 O(L × k × d)
最差情況：|candidates| = O(n)，退化為暴力搜尋
```

---

## 5.3 HNSW 與 LSH 的具體應用

### 5.3.1 HNSW 在推薦系統中的應用

```python
import numpy as np
from typing import List, Dict

class HNSWRecommender:
    """
    基於 HNSW 的推薦系統

    ‹1› 將使用者和物品映射到同一嵌入空間
    ‹2› 使用 HNSW 快速找到最相似的物品
    """

    def __init__(self, dim: int, M: int = 32, ef_construction: int = 200):
        self.dim = dim
        self.item_index = None  # HNSW 索引
        self.item_embeddings = {}  # {item_id: embedding}
        self.item_metadata = {}  # {item_id: metadata}

    def index_items(
        self,
        items: Dict[int, Dict],
        embedding_model
    ):
        """
        為物品建立索引

        ‹1› items: {item_id: {'title': ..., 'description': ...}}
        ‹2› embedding_model: 用於生成嵌入的模型
        """
        # 使用 FAISS 的 HNSW 實現（更高效）
        import faiss

        # 生成嵌入
        item_ids = list(items.keys())
        texts = [f"{items[id]['title']} {items[id]['description']}"
                 for id in item_ids]
        embeddings = embedding_model.encode(texts)

        # 建立索引
        self.item_index = faiss.IndexHNSWFlat(self.dim, 32)
        self.item_index.hnsw.efConstruction = 200
        self.item_index.add(embeddings)

        # 保存映射
        for i, item_id in enumerate(item_ids):
            self.item_embeddings[item_id] = embeddings[i]
            self.item_metadata[item_id] = items[item_id]

        self.id_to_index = {id: i for i, id in enumerate(item_ids)}
        self.index_to_id = {i: id for i, id in enumerate(item_ids)}

    def recommend_for_user(
        self,
        user_embedding: np.ndarray,
        k: int = 10,
        exclude_items: List[int] = None
    ) -> List[Dict]:
        """
        為使用者推薦物品

        ‹1› user_embedding: 使用者的嵌入向量
        ‹2› exclude_items: 要排除的物品（如已購買）
        """
        # 設置搜尋參數
        self.item_index.hnsw.efSearch = 100

        # 搜尋更多候選，以便過濾後仍有足夠結果
        search_k = k * 3 if exclude_items else k
        distances, indices = self.item_index.search(
            user_embedding.reshape(1, -1).astype(np.float32),
            search_k
        )

        # 過濾並構建結果
        recommendations = []
        for idx, dist in zip(indices[0], distances[0]):
            item_id = self.index_to_id[idx]

            if exclude_items and item_id in exclude_items:
                continue

            recommendations.append({
                'item_id': item_id,
                'score': 1 / (1 + dist),  # 距離轉換為分數
                **self.item_metadata[item_id]
            })

            if len(recommendations) >= k:
                break

        return recommendations

    def find_similar_items(
        self,
        item_id: int,
        k: int = 10
    ) -> List[Dict]:
        """
        找到相似物品
        """
        if item_id not in self.item_embeddings:
            return []

        item_embedding = self.item_embeddings[item_id]
        return self.recommend_for_user(
            item_embedding, k=k+1, exclude_items=[item_id]
        )


# 使用示例
def demo_recommender():
    from sentence_transformers import SentenceTransformer

    # 載入嵌入模型
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 模擬物品資料
    items = {
        1: {'title': '機器學習入門', 'description': '從零開始學習機器學習'},
        2: {'title': '深度學習實戰', 'description': '神經網路和深度學習的實踐指南'},
        3: {'title': '自然語言處理', 'description': 'NLP 技術和應用'},
        4: {'title': '資料結構與演算法', 'description': '基礎計算機科學'},
        5: {'title': 'Python 程式設計', 'description': 'Python 語言入門教程'},
    }

    # 建立推薦系統
    recommender = HNSWRecommender(dim=384)
    recommender.index_items(items, model)

    # 模擬使用者偏好
    user_query = "我想學習人工智慧和機器學習"
    user_embedding = model.encode([user_query])[0]

    # 獲取推薦
    recommendations = recommender.recommend_for_user(user_embedding, k=3)

    print("推薦結果：")
    for rec in recommendations:
        print(f"  - {rec['title']} (分數: {rec['score']:.3f})")
```

### 5.3.2 LSH 在文字和影像檢索中的應用

```python
from typing import List, Tuple
import numpy as np

class LSHTextRetrieval:
    """
    基於 LSH 的文字檢索系統

    ‹1› 適合大規模文件檢索
    ‹2› 記憶體效率高於 HNSW
    """

    def __init__(
        self,
        embedding_model,
        n_hashes: int = 12,
        n_tables: int = 8
    ):
        self.embedding_model = embedding_model
        self.dim = embedding_model.get_sentence_embedding_dimension()
        self.lsh = RandomProjectionLSH(
            dim=self.dim,
            n_hashes=n_hashes,
            n_tables=n_tables
        )
        self.documents = {}

    def index_documents(self, documents: List[Dict]):
        """
        索引文件

        ‹1› documents: [{'id': ..., 'text': ...}, ...]
        """
        texts = [doc['text'] for doc in documents]
        embeddings = self.embedding_model.encode(texts)

        for doc, embedding in zip(documents, embeddings):
            self.lsh.insert(doc['id'], embedding)
            self.documents[doc['id']] = doc

    def search(
        self,
        query: str,
        k: int = 10
    ) -> List[Dict]:
        """
        搜尋文件
        """
        query_embedding = self.embedding_model.encode([query])[0]
        indices, distances = self.lsh.search(query_embedding, k)

        results = []
        for idx, dist in zip(indices, distances):
            doc = self.documents[idx].copy()
            doc['score'] = 1 - dist  # 餘弦相似度
            results.append(doc)

        return results


class LSHImageRetrieval:
    """
    基於 LSH 的影像檢索系統

    ‹1› 使用 CLIP 生成影像嵌入
    ‹2› 支援文字到影像搜尋
    """

    def __init__(
        self,
        n_hashes: int = 16,
        n_tables: int = 10
    ):
        from transformers import CLIPProcessor, CLIPModel

        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        self.dim = 512  # CLIP 嵌入維度
        self.lsh = RandomProjectionLSH(
            dim=self.dim,
            n_hashes=n_hashes,
            n_tables=n_tables
        )
        self.images = {}

    def index_images(self, images: List[Dict]):
        """
        索引影像

        ‹1› images: [{'id': ..., 'path': ..., 'metadata': ...}, ...]
        """
        from PIL import Image
        import torch

        for img_data in images:
            image = Image.open(img_data['path'])
            inputs = self.processor(images=image, return_tensors="pt")

            with torch.no_grad():
                embedding = self.model.get_image_features(**inputs)
                embedding = embedding.numpy().flatten()

            self.lsh.insert(img_data['id'], embedding)
            self.images[img_data['id']] = img_data

    def search_by_text(
        self,
        query: str,
        k: int = 10
    ) -> List[Dict]:
        """
        用文字搜尋影像
        """
        import torch

        inputs = self.processor(text=[query], return_tensors="pt", padding=True)

        with torch.no_grad():
            text_embedding = self.model.get_text_features(**inputs)
            text_embedding = text_embedding.numpy().flatten()

        indices, distances = self.lsh.search(text_embedding, k)

        results = []
        for idx, dist in zip(indices, distances):
            img = self.images[idx].copy()
            img['score'] = 1 - dist
            results.append(img)

        return results

    def search_by_image(
        self,
        image_path: str,
        k: int = 10
    ) -> List[Dict]:
        """
        用影像搜尋相似影像
        """
        from PIL import Image
        import torch

        image = Image.open(image_path)
        inputs = self.processor(images=image, return_tensors="pt")

        with torch.no_grad():
            embedding = self.model.get_image_features(**inputs)
            embedding = embedding.numpy().flatten()

        indices, distances = self.lsh.search(embedding, k)

        results = []
        for idx, dist in zip(indices, distances):
            img = self.images[idx].copy()
            img['score'] = 1 - dist
            results.append(img)

        return results
```

### 5.3.3 HNSW 與 LSH 的組合應用：多模態檢索實例

```python
class HybridMultiModalRetrieval:
    """
    混合使用 HNSW 和 LSH 的多模態檢索系統

    ‹1› 文字使用 HNSW（需要高召回率）
    ‹2› 影像使用 LSH（數量大，節省記憶體）
    ‹3› 支援跨模態檢索
    """

    def __init__(self):
        from transformers import CLIPProcessor, CLIPModel
        import faiss

        # CLIP 模型
        self.clip_model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32"
        )
        self.clip_processor = CLIPProcessor.from_pretrained(
            "openai/clip-vit-base-patch32"
        )

        self.dim = 512

        # 文字索引：HNSW
        self.text_index = faiss.IndexHNSWFlat(self.dim, 32)
        self.text_index.hnsw.efConstruction = 200

        # 影像索引：LSH
        self.image_lsh = RandomProjectionLSH(
            dim=self.dim,
            n_hashes=12,
            n_tables=8
        )

        self.texts = {}
        self.images = {}
        self.text_id_map = {}
        self.text_count = 0

    def index_text(self, doc_id: int, text: str):
        """索引文字"""
        import torch

        inputs = self.clip_processor(
            text=[text], return_tensors="pt", padding=True
        )

        with torch.no_grad():
            embedding = self.clip_model.get_text_features(**inputs)
            embedding = embedding.numpy().astype(np.float32)

        self.text_index.add(embedding)
        self.text_id_map[self.text_count] = doc_id
        self.texts[doc_id] = text
        self.text_count += 1

    def index_image(self, img_id: int, image_path: str):
        """索引影像"""
        from PIL import Image
        import torch

        image = Image.open(image_path)
        inputs = self.clip_processor(images=image, return_tensors="pt")

        with torch.no_grad():
            embedding = self.clip_model.get_image_features(**inputs)
            embedding = embedding.numpy().flatten()

        self.image_lsh.insert(img_id, embedding)
        self.images[img_id] = image_path

    def search_text_by_text(self, query: str, k: int = 10) -> List[Dict]:
        """文字搜尋文字"""
        import torch

        inputs = self.clip_processor(
            text=[query], return_tensors="pt", padding=True
        )

        with torch.no_grad():
            embedding = self.clip_model.get_text_features(**inputs)
            embedding = embedding.numpy().astype(np.float32)

        self.text_index.hnsw.efSearch = 100
        distances, indices = self.text_index.search(embedding, k)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            doc_id = self.text_id_map[idx]
            results.append({
                'id': doc_id,
                'text': self.texts[doc_id],
                'score': 1 / (1 + dist)
            })

        return results

    def search_images_by_text(self, query: str, k: int = 10) -> List[Dict]:
        """文字搜尋影像"""
        import torch

        inputs = self.clip_processor(
            text=[query], return_tensors="pt", padding=True
        )

        with torch.no_grad():
            embedding = self.clip_model.get_text_features(**inputs)
            embedding = embedding.numpy().flatten()

        indices, distances = self.image_lsh.search(embedding, k)

        results = []
        for idx, dist in zip(indices, distances):
            results.append({
                'id': idx,
                'path': self.images[idx],
                'score': 1 - dist
            })

        return results

    def search_all(self, query: str, k_text: int = 5, k_image: int = 5) -> Dict:
        """
        多模態統一搜尋

        ‹1› 同時返回相關文字和影像
        """
        return {
            'texts': self.search_text_by_text(query, k_text),
            'images': self.search_images_by_text(query, k_image)
        }
```

---

## 5.4 本章小結

在本章中，我們深入學習了兩種核心的近似最近鄰搜尋演算法：

1. **HNSW（分層可導航小世界圖）**
   - 基於「小世界網絡」理論構建分層圖結構
   - 高層用於快速導航，底層用於精確搜尋
   - 查詢時間複雜度 O(log n)，空間複雜度 O(n × M)
   - 優點：召回率高、查詢快；缺點：記憶體佔用大

2. **LSH（局部敏感雜湊）**
   - 使用特殊雜湊函式將相似向量映射到相同桶
   - 通過多個雜湊表提高召回率
   - 需要根據資料特性調優參數
   - 優點：記憶體效率高；缺點：召回率-速度權衡難以控制

3. **選擇建議**
   - 需要高召回率 → HNSW
   - 記憶體受限 → LSH
   - 需要頻繁更新 → LSH（HNSW 更新成本高）
   - 超大規模資料 → 可以組合使用

在下一章中，我們將學習更多 LSH 最佳化技術，包括 BallTree、Annoy 和隨機投影等方法。

---

## 5.5 思考題

1. **概念理解**
   - 解釋 HNSW 中「小世界」的概念，以及為什麼分層結構能夠加速搜尋。

2. **技術分析**
   - 假設你有 1000 萬個 768 維向量，需要達到 95% 的召回率。分析：
     a) HNSW 需要多少記憶體？
     b) LSH 需要多少雜湊表才能達到目標召回率？
     c) 哪種方法更適合這個場景？

3. **實作練習**
   - 實現一個簡化版的 HNSW，支援：
     a) 插入和搜尋操作
     b) 可調的 M 和 ef 參數
     c) 與暴力搜尋的召回率對比

4. **系統設計**
   - 設計一個混合索引策略，用於處理 10 億級別的向量：
     a) 如何分片？
     b) 如何路由查詢？
     c) 如何保證整體召回率？

5. **批判性思考**
   - 「HNSW 幾乎在所有場景下都優於 LSH」——你同意這個觀點嗎？討論可能的例外情況。

---

> **下一章預告**：在第 6 章中，我們將繼續探討 LSH 的最佳化技術，包括 BallTree 演算法、Annoy 搜尋演算法，以及隨機投影在降維和檢索中的應用。
