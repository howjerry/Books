# Chapter 7：相似性度量基礎

> 「選擇正確的相似性度量，就像選擇正確的尺子——用錯了工具，測量結果就毫無意義。」

## 學習目標

完成本章後，你將能夠：

- 理解各種相似性度量的數學原理與幾何意義
- 掌握歐氏距離、餘弦相似度、曼哈頓距離等核心度量方法
- 學會根據應用場景選擇最適合的相似性度量
- 實作高效能的批量相似性計算
- 理解度量選擇對檢索品質的影響

---

## 7.1 為什麼相似性度量如此重要

在向量資料庫的世界中，相似性度量是一切檢索操作的基礎。當你說「找出與這張圖片最相似的圖片」或「搜尋與這段文字語意最接近的文件」時，背後都依賴著相似性度量來量化「相似」這個概念。

### 7.1.1 從直覺到數學

想像你站在一個巨大的圖書館中，手裡拿著一本書，想要找到「最相似」的書籍。你可能會考慮：

- **主題相似**：都是關於機器學習的書
- **風格相似**：都是實戰導向的寫作風格
- **難度相似**：都適合中級讀者
- **長度相似**：都在 300-400 頁之間

每一個維度都可以被量化，而這本書就變成了一個多維向量。相似性度量的任務，就是定義如何計算兩個這樣的向量之間的「距離」或「相似程度」。

```python
import numpy as np
from typing import List, Tuple, Callable
import time

class SimilarityMetrics:
    """
    相似性度量工具類

    ‹1› 提供多種相似性度量的實作
    ‹2› 支援單一向量對和批量計算
    ‹3› 包含效能基準測試功能
    """

    @staticmethod
    def normalize(vector: np.ndarray) -> np.ndarray:
        """
        ‹1› L2 正規化向量

        將向量轉換為單位向量，使其長度為 1
        這是計算餘弦相似度的前置處理
        """
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    @staticmethod
    def batch_normalize(vectors: np.ndarray) -> np.ndarray:
        """
        ‹2› 批量 L2 正規化

        對多個向量同時進行正規化
        利用 NumPy 的向量化操作提升效能
        """
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        # 避免除以零
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms
```

### 7.1.2 度量的分類

相似性度量大致可以分為兩類：

| 類型 | 特點 | 範例 |
|------|------|------|
| **距離度量** | 值越小越相似，最小為 0 | 歐氏距離、曼哈頓距離 |
| **相似度度量** | 值越大越相似，最大通常為 1 | 餘弦相似度、Jaccard 相似度 |

這兩類度量可以互相轉換。例如，餘弦距離 = 1 - 餘弦相似度。

---

## 7.2 歐氏距離（Euclidean Distance）

歐氏距離是最直觀、最常用的距離度量，它計算的是兩點之間的「直線距離」。

### 7.2.1 數學定義

對於兩個 n 維向量 $\mathbf{a} = (a_1, a_2, ..., a_n)$ 和 $\mathbf{b} = (b_1, b_2, ..., b_n)$：

$$d_{euclidean}(\mathbf{a}, \mathbf{b}) = \sqrt{\sum_{i=1}^{n}(a_i - b_i)^2}$$

在二維空間中，這就是我們熟悉的畢達哥拉斯定理。

### 7.2.2 幾何意義

```
    y
    │
    │     B(3,4)
    │    ╱│
    │   ╱ │ 4
    │  ╱  │
    │ ╱   │
    │╱────┼───── x
    A(0,0)  3

    距離 = √(3² + 4²) = √25 = 5
```

### 7.2.3 Python 實作

```python
class EuclideanDistance:
    """
    歐氏距離計算器

    ‹1› 提供多種實作方式比較效能
    ‹2› 支援 GPU 加速（透過 CuPy）
    """

    @staticmethod
    def naive(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹1› 樸素實作：使用 Python 迴圈

        這是最直觀但最慢的實作方式
        僅用於教學目的，不建議在生產環境使用
        """
        total = 0.0
        for i in range(len(a)):
            diff = a[i] - b[i]
            total += diff * diff
        return np.sqrt(total)

    @staticmethod
    def numpy_basic(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹2› NumPy 基本實作

        使用 NumPy 的向量化操作
        比樸素實作快 10-100 倍
        """
        diff = a - b
        return np.sqrt(np.sum(diff ** 2))

    @staticmethod
    def numpy_norm(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹3› NumPy norm 實作

        使用 np.linalg.norm 函數
        內部經過高度優化，通常是最快的單向量對計算方式
        """
        return np.linalg.norm(a - b)

    @staticmethod
    def numpy_dot(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹4› 使用點積展開式

        利用 ||a - b||² = ||a||² + ||b||² - 2(a·b)
        當已經預計算了向量的模時，這種方式更有效率
        """
        return np.sqrt(np.dot(a, a) + np.dot(b, b) - 2 * np.dot(a, b))

    @staticmethod
    def batch_compute(
        queries: np.ndarray,  # shape: (n_queries, dim)
        database: np.ndarray  # shape: (n_database, dim)
    ) -> np.ndarray:
        """
        ‹5› 批量計算歐氏距離

        計算多個查詢向量與資料庫中所有向量的距離
        返回形狀為 (n_queries, n_database) 的距離矩陣

        使用廣播機制和矩陣運算優化效能
        """
        # 計算 ||q||² for all queries
        queries_sq = np.sum(queries ** 2, axis=1, keepdims=True)

        # 計算 ||d||² for all database vectors
        database_sq = np.sum(database ** 2, axis=1, keepdims=True)

        # 計算 q·d for all pairs
        cross_term = np.dot(queries, database.T)

        # ||q - d||² = ||q||² + ||d||² - 2(q·d)
        distances_sq = queries_sq + database_sq.T - 2 * cross_term

        # 處理數值誤差可能導致的負值
        distances_sq = np.maximum(distances_sq, 0)

        return np.sqrt(distances_sq)


def benchmark_euclidean_implementations():
    """
    ‹1› 基準測試各種歐氏距離實作

    比較不同實作方式在各種維度下的效能
    """
    dimensions = [64, 128, 256, 512, 1024]
    n_iterations = 10000

    print("歐氏距離實作效能比較")
    print("=" * 70)
    print(f"{'維度':<10} {'樸素實作':<15} {'NumPy 基本':<15} {'NumPy norm':<15} {'點積展開':<15}")
    print("-" * 70)

    for dim in dimensions:
        # 生成隨機測試向量
        np.random.seed(42)
        a = np.random.randn(dim).astype(np.float32)
        b = np.random.randn(dim).astype(np.float32)

        results = {}

        # 測試樸素實作（只測試較少次數因為太慢）
        start = time.perf_counter()
        for _ in range(min(n_iterations, 1000)):
            _ = EuclideanDistance.naive(a, b)
        results['naive'] = (time.perf_counter() - start) / min(n_iterations, 1000) * 1000

        # 測試 NumPy 基本實作
        start = time.perf_counter()
        for _ in range(n_iterations):
            _ = EuclideanDistance.numpy_basic(a, b)
        results['numpy_basic'] = (time.perf_counter() - start) / n_iterations * 1000

        # 測試 NumPy norm 實作
        start = time.perf_counter()
        for _ in range(n_iterations):
            _ = EuclideanDistance.numpy_norm(a, b)
        results['numpy_norm'] = (time.perf_counter() - start) / n_iterations * 1000

        # 測試點積展開實作
        start = time.perf_counter()
        for _ in range(n_iterations):
            _ = EuclideanDistance.numpy_dot(a, b)
        results['numpy_dot'] = (time.perf_counter() - start) / n_iterations * 1000

        print(f"{dim:<10} {results['naive']:<15.4f} {results['numpy_basic']:<15.4f} "
              f"{results['numpy_norm']:<15.4f} {results['numpy_dot']:<15.4f}")

    print("\n單位：毫秒/次")


# 執行基準測試
if __name__ == "__main__":
    benchmark_euclidean_implementations()
```

### 7.2.4 歐氏距離的特性

**優點：**
- 直觀易懂，符合人類對「距離」的認知
- 計算簡單，硬體支援度高
- 對絕對數值敏感，適合需要考慮向量長度的場景

**缺點：**
- 受維度災難影響嚴重
- 對特徵尺度敏感，需要標準化
- 在高維空間中，所有點之間的距離趨於相同

**適用場景：**
- 圖片相似性（像素級比較）
- 低維度的數值特徵比較
- 需要考慮向量大小的應用

---

## 7.3 餘弦相似度（Cosine Similarity）

餘弦相似度測量的是兩個向量之間的夾角，而不是它們之間的距離。這使得它特別適合處理文字和語意相關的應用。

### 7.3.1 數學定義

$$\text{cosine}(\mathbf{a}, \mathbf{b}) = \frac{\mathbf{a} \cdot \mathbf{b}}{||\mathbf{a}|| \cdot ||\mathbf{b}||} = \frac{\sum_{i=1}^{n} a_i b_i}{\sqrt{\sum_{i=1}^{n} a_i^2} \cdot \sqrt{\sum_{i=1}^{n} b_i^2}}$$

餘弦相似度的值域為 [-1, 1]：
- 1：向量方向完全相同
- 0：向量正交（無關）
- -1：向量方向完全相反

### 7.3.2 幾何意義

```
              y
              │    B
              │   ╱
              │  ╱  θ = 45°
              │ ╱   cos(45°) ≈ 0.707
              │╱
    ──────────┼────────── x
              │╲
              │ ╲  θ = 135°
              │  ╲ cos(135°) ≈ -0.707
              │   ╲
              │    C
```

### 7.3.3 Python 實作

```python
class CosineSimilarity:
    """
    餘弦相似度計算器

    ‹1› 支援多種實作方式
    ‹2› 包含預正規化優化
    ‹3› 支援批量計算
    """

    @staticmethod
    def basic(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹1› 基本實作

        直接按照公式計算
        """
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    @staticmethod
    def with_prenormalized(a_normalized: np.ndarray, b_normalized: np.ndarray) -> float:
        """
        ‹2› 預正規化實作

        當向量已經正規化為單位向量時
        餘弦相似度就等於點積
        這是最快的計算方式
        """
        return np.dot(a_normalized, b_normalized)

    @staticmethod
    def batch_compute(
        queries: np.ndarray,  # shape: (n_queries, dim)
        database: np.ndarray,  # shape: (n_database, dim)
        prenormalized: bool = False
    ) -> np.ndarray:
        """
        ‹3› 批量計算餘弦相似度

        返回形狀為 (n_queries, n_database) 的相似度矩陣

        Args:
            queries: 查詢向量矩陣
            database: 資料庫向量矩陣
            prenormalized: 向量是否已經正規化
        """
        if not prenormalized:
            # 正規化查詢向量
            query_norms = np.linalg.norm(queries, axis=1, keepdims=True)
            query_norms = np.where(query_norms == 0, 1, query_norms)
            queries = queries / query_norms

            # 正規化資料庫向量
            db_norms = np.linalg.norm(database, axis=1, keepdims=True)
            db_norms = np.where(db_norms == 0, 1, db_norms)
            database = database / db_norms

        # 正規化後的餘弦相似度就是矩陣乘法
        return np.dot(queries, database.T)

    @staticmethod
    def to_distance(similarity: float) -> float:
        """
        ‹4› 將餘弦相似度轉換為餘弦距離

        餘弦距離 = 1 - 餘弦相似度
        值域為 [0, 2]
        """
        return 1.0 - similarity

    @staticmethod
    def angular_distance(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹5› 角度距離

        直接計算向量之間的夾角（弧度）
        這是真正的「角度」距離
        """
        cos_sim = CosineSimilarity.basic(a, b)
        # 處理數值誤差
        cos_sim = np.clip(cos_sim, -1.0, 1.0)
        return np.arccos(cos_sim)


def demonstrate_cosine_vs_euclidean():
    """
    ‹1› 展示餘弦相似度與歐氏距離的差異

    說明為什麼在某些場景下餘弦相似度更適合
    """
    print("餘弦相似度 vs 歐氏距離")
    print("=" * 60)

    # 場景 1：文件長度不同但主題相同
    print("\n場景 1：文件長度差異")
    print("-" * 40)

    # 假設這是兩篇關於「機器學習」的文件的 TF-IDF 向量
    # 第一篇是短文（500 字），第二篇是長文（5000 字）
    doc_short = np.array([0.2, 0.3, 0.1, 0.4])  # 短文件
    doc_long = np.array([2.0, 3.0, 1.0, 4.0])   # 長文件（內容相似但詞頻高 10 倍）

    euclidean = EuclideanDistance.numpy_norm(doc_short, doc_long)
    cosine = CosineSimilarity.basic(doc_short, doc_long)

    print(f"短文件向量: {doc_short}")
    print(f"長文件向量: {doc_long}")
    print(f"歐氏距離: {euclidean:.4f} （看起來很不相似）")
    print(f"餘弦相似度: {cosine:.4f} （完全相同的方向！）")

    # 場景 2：方向不同的向量
    print("\n場景 2：主題不同的文件")
    print("-" * 40)

    doc_ml = np.array([0.8, 0.6, 0.0, 0.0])     # 機器學習主題
    doc_web = np.array([0.0, 0.0, 0.7, 0.7])    # 網頁開發主題

    euclidean = EuclideanDistance.numpy_norm(doc_ml, doc_web)
    cosine = CosineSimilarity.basic(doc_ml, doc_web)

    print(f"機器學習文件: {doc_ml}")
    print(f"網頁開發文件: {doc_web}")
    print(f"歐氏距離: {euclidean:.4f}")
    print(f"餘弦相似度: {cosine:.4f} （正交，完全不相關）")

    # 場景 3：相似但略有差異
    print("\n場景 3：相似主題的文件")
    print("-" * 40)

    doc_dl = np.array([0.7, 0.5, 0.3, 0.1])     # 深度學習
    doc_nn = np.array([0.6, 0.6, 0.4, 0.1])     # 神經網路

    euclidean = EuclideanDistance.numpy_norm(doc_dl, doc_nn)
    cosine = CosineSimilarity.basic(doc_dl, doc_nn)

    print(f"深度學習文件: {doc_dl}")
    print(f"神經網路文件: {doc_nn}")
    print(f"歐氏距離: {euclidean:.4f}")
    print(f"餘弦相似度: {cosine:.4f} （高度相似）")


if __name__ == "__main__":
    demonstrate_cosine_vs_euclidean()
```

### 7.3.4 餘弦相似度的特性

**優點：**
- 對向量的絕對大小不敏感，只關注方向
- 特別適合文字和語意比較
- 在高維空間中表現穩定

**缺點：**
- 忽略了向量的大小資訊
- 對於非負向量（如詞頻），值域變為 [0, 1]
- 當向量稀疏時，計算效率可能較低

**適用場景：**
- 文件相似性比較
- 語意搜尋
- 推薦系統中的用戶/物品相似度
- 詞向量和句向量比較

---

## 7.4 曼哈頓距離（Manhattan Distance）

曼哈頓距離，也稱為 L1 距離或城市街區距離，計算的是在座標軸方向上移動的總距離。

### 7.4.1 數學定義

$$d_{manhattan}(\mathbf{a}, \mathbf{b}) = \sum_{i=1}^{n}|a_i - b_i|$$

### 7.4.2 幾何意義

想像你在一個棋盤格狀的城市中，只能沿著街道行走（不能穿越建築物），從 A 點到 B 點的最短路徑就是曼哈頓距離。

```
    y
    │
  4 │     ┌───────B
    │     │       │
  3 │     │       │
    │     │       │
  2 │     │       │
    │     │       │
  1 │  A──┘       │
    │             │
  0 └─────────────┴── x
    0  1  2  3  4  5

    曼哈頓距離 = |5-1| + |4-1| = 4 + 3 = 7
    歐氏距離 = √(4² + 3²) = 5
```

### 7.4.3 Python 實作

```python
class ManhattanDistance:
    """
    曼哈頓距離（L1 距離）計算器

    ‹1› 適用於稀疏數據和離散特徵
    ‹2› 對異常值不敏感
    """

    @staticmethod
    def basic(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹1› 基本實作
        """
        return np.sum(np.abs(a - b))

    @staticmethod
    def weighted(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> float:
        """
        ‹2› 加權曼哈頓距離

        允許對不同維度賦予不同的重要性
        """
        return np.sum(weights * np.abs(a - b))

    @staticmethod
    def batch_compute(
        queries: np.ndarray,
        database: np.ndarray
    ) -> np.ndarray:
        """
        ‹3› 批量計算曼哈頓距離

        使用廣播機制計算所有查詢與資料庫向量的距離
        """
        # 擴展維度以進行廣播
        # queries: (n_queries, 1, dim)
        # database: (1, n_database, dim)
        # 結果: (n_queries, n_database, dim)
        diff = np.abs(queries[:, np.newaxis, :] - database[np.newaxis, :, :])

        # 沿最後一個軸求和得到距離
        return np.sum(diff, axis=2)

    @staticmethod
    def sparse_compute(
        a_indices: np.ndarray, a_values: np.ndarray,
        b_indices: np.ndarray, b_values: np.ndarray,
        dim: int
    ) -> float:
        """
        ‹4› 稀疏向量的曼哈頓距離

        當向量非常稀疏時，只需要計算非零元素
        """
        # 建立索引到值的映射
        a_dict = dict(zip(a_indices, a_values))
        b_dict = dict(zip(b_indices, b_values))

        # 合併所有非零索引
        all_indices = set(a_indices) | set(b_indices)

        distance = 0.0
        for idx in all_indices:
            a_val = a_dict.get(idx, 0.0)
            b_val = b_dict.get(idx, 0.0)
            distance += abs(a_val - b_val)

        return distance


def compare_l1_vs_l2():
    """
    ‹1› 比較曼哈頓距離和歐氏距離對異常值的敏感度
    """
    print("曼哈頓距離 vs 歐氏距離：異常值敏感度")
    print("=" * 60)

    # 基準向量
    base = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    # 正常差異
    normal_diff = np.array([1.2, 2.1, 2.9, 4.2, 4.8])

    # 包含異常值的差異
    outlier_diff = np.array([1.2, 2.1, 2.9, 4.2, 15.0])  # 最後一個是異常值

    print(f"基準向量: {base}")
    print(f"正常向量: {normal_diff}")
    print(f"異常向量: {outlier_diff}")
    print()

    # 計算距離
    l1_normal = ManhattanDistance.basic(base, normal_diff)
    l2_normal = EuclideanDistance.numpy_norm(base, normal_diff)

    l1_outlier = ManhattanDistance.basic(base, outlier_diff)
    l2_outlier = EuclideanDistance.numpy_norm(base, outlier_diff)

    print(f"{'度量':<15} {'正常差異':<15} {'異常值':<15} {'增幅比例':<15}")
    print("-" * 60)
    print(f"{'曼哈頓 (L1)':<15} {l1_normal:<15.4f} {l1_outlier:<15.4f} {l1_outlier/l1_normal:<15.2f}x")
    print(f"{'歐氏 (L2)':<15} {l2_normal:<15.4f} {l2_outlier:<15.4f} {l2_outlier/l2_normal:<15.2f}x")

    print("\n結論：歐氏距離對異常值更敏感（因為平方放大了大的差異）")


if __name__ == "__main__":
    compare_l1_vs_l2()
```

### 7.4.4 曼哈頓距離的特性

**優點：**
- 對異常值不如歐氏距離敏感
- 計算簡單，不需要平方和開方
- 適合稀疏數據
- 在高維空間中更穩定

**缺點：**
- 不符合「最短路徑」的直覺
- 受座標系旋轉影響

**適用場景：**
- 稀疏特徵向量
- 離散型特徵
- 需要對異常值魯棒的應用
- 某些推薦系統場景

---

## 7.5 內積（Dot Product / Inner Product）

內積是最簡單的相似性度量之一，但在某些場景下非常有用。

### 7.5.1 數學定義

$$\mathbf{a} \cdot \mathbf{b} = \sum_{i=1}^{n} a_i b_i = ||\mathbf{a}|| \cdot ||\mathbf{b}|| \cdot \cos(\theta)$$

### 7.5.2 與餘弦相似度的關係

對於單位向量（長度為 1 的向量）：

$$\mathbf{a} \cdot \mathbf{b} = \cos(\theta)$$

這意味著，如果我們預先將所有向量正規化，內積就等於餘弦相似度。這是許多向量資料庫採用的優化策略。

### 7.5.3 Python 實作

```python
class InnerProduct:
    """
    內積（點積）相似度計算器

    ‹1› 最簡單但常被低估的相似性度量
    ‹2› 在很多場景下是最佳選擇
    """

    @staticmethod
    def basic(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹1› 基本實作
        """
        return np.dot(a, b)

    @staticmethod
    def batch_compute(
        queries: np.ndarray,
        database: np.ndarray
    ) -> np.ndarray:
        """
        ‹2› 批量計算內積

        這是最快的批量相似度計算方式
        直接使用矩陣乘法
        """
        return np.dot(queries, database.T)

    @staticmethod
    def maximum_inner_product_search(
        query: np.ndarray,
        database: np.ndarray,
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        ‹3› 最大內積搜尋（MIPS）

        找出與查詢向量內積最大的 k 個向量
        這是推薦系統中常用的檢索方式

        Returns:
            (indices, scores): 最相似的 k 個向量的索引和分數
        """
        scores = np.dot(database, query)

        # 找出前 k 個最大值的索引
        # 使用 argpartition 比完整排序更快
        if k < len(scores):
            indices = np.argpartition(scores, -k)[-k:]
            # 對這 k 個結果排序
            indices = indices[np.argsort(scores[indices])[::-1]]
        else:
            indices = np.argsort(scores)[::-1][:k]

        return indices, scores[indices]


def demonstrate_mips():
    """
    ‹1› 展示最大內積搜尋的應用

    模擬推薦系統場景
    """
    print("最大內積搜尋（MIPS）- 推薦系統範例")
    print("=" * 60)

    np.random.seed(42)

    # 模擬用戶和物品的嵌入向量
    n_users = 100
    n_items = 10000
    embedding_dim = 64

    # 用戶嵌入（代表用戶偏好）
    user_embeddings = np.random.randn(n_users, embedding_dim).astype(np.float32)

    # 物品嵌入（代表物品特徵）
    item_embeddings = np.random.randn(n_items, embedding_dim).astype(np.float32)

    # 為特定用戶推薦物品
    user_id = 0
    user_vector = user_embeddings[user_id]

    start_time = time.perf_counter()
    top_indices, top_scores = InnerProduct.maximum_inner_product_search(
        user_vector, item_embeddings, k=10
    )
    elapsed = time.perf_counter() - start_time

    print(f"用戶 {user_id} 的 Top-10 推薦物品：")
    print(f"{'排名':<6} {'物品 ID':<12} {'分數':<12}")
    print("-" * 30)
    for rank, (idx, score) in enumerate(zip(top_indices, top_scores), 1):
        print(f"{rank:<6} {idx:<12} {score:<12.4f}")

    print(f"\n搜尋時間：{elapsed*1000:.2f} ms")
    print(f"物品數量：{n_items:,}")


if __name__ == "__main__":
    demonstrate_mips()
```

### 7.5.4 內積的特性

**優點：**
- 計算最簡單，效能最高
- 對於正規化向量等價於餘弦相似度
- 矩陣運算高度優化（BLAS、GPU）

**缺點：**
- 同時考慮方向和大小
- 值域沒有上界
- 難以直接解釋

**適用場景：**
- 推薦系統（用戶-物品匹配）
- 預正規化的語意搜尋
- 需要考慮向量「強度」的場景

---

## 7.6 Jaccard 相似度

Jaccard 相似度用於比較兩個集合的相似程度，在處理稀疏數據和集合型特徵時特別有用。

### 7.6.1 數學定義

對於兩個集合 A 和 B：

$$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$

對於向量形式，可以使用加權版本：

$$J_{weighted}(\mathbf{a}, \mathbf{b}) = \frac{\sum_{i} \min(a_i, b_i)}{\sum_{i} \max(a_i, b_i)}$$

### 7.6.2 Python 實作

```python
class JaccardSimilarity:
    """
    Jaccard 相似度計算器

    ‹1› 適用於集合型數據
    ‹2› 支援二元向量和加權向量
    """

    @staticmethod
    def set_based(set_a: set, set_b: set) -> float:
        """
        ‹1› 集合版本的 Jaccard 相似度
        """
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        if union == 0:
            return 0.0

        return intersection / union

    @staticmethod
    def binary_vector(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹2› 二元向量的 Jaccard 相似度

        向量元素只有 0 和 1
        """
        # 將非零元素視為 1
        a_binary = (a != 0).astype(int)
        b_binary = (b != 0).astype(int)

        intersection = np.sum(a_binary & b_binary)
        union = np.sum(a_binary | b_binary)

        if union == 0:
            return 0.0

        return intersection / union

    @staticmethod
    def weighted(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹3› 加權 Jaccard 相似度（Ruzicka 相似度）

        適用於非負實數向量
        """
        min_sum = np.sum(np.minimum(a, b))
        max_sum = np.sum(np.maximum(a, b))

        if max_sum == 0:
            return 0.0

        return min_sum / max_sum

    @staticmethod
    def minhash_signature(
        elements: set,
        num_hashes: int = 128,
        seed: int = 42
    ) -> np.ndarray:
        """
        ‹4› 計算 MinHash 簽名

        MinHash 是一種用於估計 Jaccard 相似度的技術
        可以大幅減少計算量和儲存空間
        """
        np.random.seed(seed)

        # 生成多個哈希函數的參數
        # h(x) = (a*x + b) mod p
        p = 2**31 - 1  # 大質數
        a = np.random.randint(1, p, size=num_hashes)
        b = np.random.randint(0, p, size=num_hashes)

        signature = np.full(num_hashes, np.inf)

        for element in elements:
            # 將元素轉換為數字
            if isinstance(element, str):
                element_hash = hash(element) % p
            else:
                element_hash = int(element) % p

            # 計算所有哈希函數的值
            hash_values = (a * element_hash + b) % p

            # 更新最小值
            signature = np.minimum(signature, hash_values)

        return signature.astype(np.int64)

    @staticmethod
    def estimate_jaccard_from_minhash(
        sig_a: np.ndarray,
        sig_b: np.ndarray
    ) -> float:
        """
        ‹5› 從 MinHash 簽名估計 Jaccard 相似度

        估計值 = 相同位置數 / 總位置數
        """
        return np.mean(sig_a == sig_b)


def demonstrate_minhash():
    """
    ‹1› 展示 MinHash 的效果
    """
    print("MinHash 近似 Jaccard 相似度")
    print("=" * 60)

    # 創建兩個有重疊的集合
    set_a = set(range(0, 100))      # {0, 1, 2, ..., 99}
    set_b = set(range(50, 150))     # {50, 51, ..., 149}

    # 真實 Jaccard 相似度
    true_jaccard = JaccardSimilarity.set_based(set_a, set_b)
    print(f"集合 A: {{0, 1, ..., 99}}")
    print(f"集合 B: {{50, 51, ..., 149}}")
    print(f"真實 Jaccard 相似度: {true_jaccard:.4f}")
    print()

    # 測試不同數量的哈希函數
    print(f"{'哈希函數數':<15} {'估計值':<15} {'誤差':<15}")
    print("-" * 45)

    for num_hashes in [16, 32, 64, 128, 256, 512]:
        sig_a = JaccardSimilarity.minhash_signature(set_a, num_hashes)
        sig_b = JaccardSimilarity.minhash_signature(set_b, num_hashes)

        estimated = JaccardSimilarity.estimate_jaccard_from_minhash(sig_a, sig_b)
        error = abs(estimated - true_jaccard)

        print(f"{num_hashes:<15} {estimated:<15.4f} {error:<15.4f}")

    print("\n結論：更多的哈希函數 → 更準確的估計")


if __name__ == "__main__":
    demonstrate_minhash()
```

### 7.6.3 Jaccard 相似度的特性

**優點：**
- 適合集合型數據
- 對集合大小的差異不敏感
- 可以使用 MinHash 進行高效近似

**缺點：**
- 只考慮元素的存在與否，不考慮頻率
- 對於連續型特徵需要離散化

**適用場景：**
- 文件去重
- 購物籃分析
- 標籤相似性
- 用戶行為集合比較

---

## 7.7 漢明距離（Hamming Distance）

漢明距離計算兩個等長字串（或二進位向量）在相同位置上不同字元的數量。

### 7.7.1 數學定義

對於兩個等長的二進位向量：

$$d_{hamming}(\mathbf{a}, \mathbf{b}) = \sum_{i=1}^{n} \mathbf{1}[a_i \neq b_i]$$

### 7.7.2 Python 實作

```python
class HammingDistance:
    """
    漢明距離計算器

    ‹1› 適用於二進位向量和編碼比較
    ‹2› 支援位元運算優化
    """

    @staticmethod
    def basic(a: np.ndarray, b: np.ndarray) -> int:
        """
        ‹1› 基本實作
        """
        return np.sum(a != b)

    @staticmethod
    def binary_codes(a: int, b: int) -> int:
        """
        ‹2› 整數的漢明距離（位元級）

        使用 XOR 和 popcount 計算
        """
        xor = a ^ b
        return bin(xor).count('1')

    @staticmethod
    def packed_binary(
        a: np.ndarray,  # uint64 array
        b: np.ndarray   # uint64 array
    ) -> int:
        """
        ‹3› 壓縮二進位向量的漢明距離

        將多個 bit 打包成 uint64 以加速計算
        """
        xor = a ^ b
        # 計算每個 uint64 中 1 的數量
        count = 0
        for val in xor:
            count += bin(val).count('1')
        return count

    @staticmethod
    def batch_compute(
        queries: np.ndarray,  # shape: (n_queries, dim)
        database: np.ndarray  # shape: (n_database, dim)
    ) -> np.ndarray:
        """
        ‹4› 批量計算漢明距離
        """
        # 使用廣播計算所有配對的不同位置數
        # queries: (n_queries, 1, dim)
        # database: (1, n_database, dim)
        diff = queries[:, np.newaxis, :] != database[np.newaxis, :, :]
        return np.sum(diff, axis=2)

    @staticmethod
    def similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹5› 漢明相似度

        相似度 = 1 - (漢明距離 / 向量長度)
        """
        distance = HammingDistance.basic(a, b)
        return 1.0 - (distance / len(a))


def demonstrate_hamming_for_image_hashing():
    """
    ‹1› 展示漢明距離在圖片哈希中的應用
    """
    print("漢明距離 - 圖片哈希（感知哈希）範例")
    print("=" * 60)

    # 模擬圖片的 64-bit 感知哈希
    # 實際應用中，這些哈希值是由圖片內容計算得出的

    # 原始圖片
    original_hash = np.array([1, 0, 1, 1, 0, 0, 1, 0,
                              1, 1, 0, 1, 0, 1, 0, 1,
                              0, 1, 1, 0, 1, 0, 1, 0,
                              1, 0, 0, 1, 1, 0, 0, 1,
                              0, 1, 0, 1, 0, 1, 1, 0,
                              1, 0, 1, 0, 1, 0, 0, 1,
                              0, 1, 1, 1, 0, 0, 1, 0,
                              1, 0, 0, 1, 0, 1, 0, 1])

    # 稍微修改的圖片（壓縮/調整大小）
    slightly_modified = original_hash.copy()
    slightly_modified[5] = 1 - slightly_modified[5]
    slightly_modified[20] = 1 - slightly_modified[20]
    slightly_modified[45] = 1 - slightly_modified[45]

    # 完全不同的圖片
    different_hash = np.array([0, 1, 0, 0, 1, 1, 0, 1,
                               0, 0, 1, 0, 1, 0, 1, 0,
                               1, 0, 0, 1, 0, 1, 0, 1,
                               0, 1, 1, 0, 0, 1, 1, 0,
                               1, 0, 1, 0, 1, 0, 0, 1,
                               0, 1, 0, 1, 0, 1, 1, 0,
                               1, 0, 0, 0, 1, 1, 0, 1,
                               0, 1, 1, 0, 1, 0, 1, 0])

    # 計算漢明距離
    dist_to_modified = HammingDistance.basic(original_hash, slightly_modified)
    dist_to_different = HammingDistance.basic(original_hash, different_hash)

    print(f"哈希長度: {len(original_hash)} bits")
    print()
    print(f"原始圖片 vs 稍微修改的圖片:")
    print(f"  漢明距離: {dist_to_modified}")
    print(f"  相似度: {HammingDistance.similarity(original_hash, slightly_modified):.2%}")
    print()
    print(f"原始圖片 vs 完全不同的圖片:")
    print(f"  漢明距離: {dist_to_different}")
    print(f"  相似度: {HammingDistance.similarity(original_hash, different_hash):.2%}")
    print()
    print("判斷規則：漢明距離 ≤ 10 通常表示是相同或相似的圖片")


if __name__ == "__main__":
    demonstrate_hamming_for_image_hashing()
```

### 7.7.3 漢明距離的特性

**優點：**
- 計算極快（可使用位元運算）
- 適合二進位編碼
- 儲存空間效率高

**缺點：**
- 只適用於等長的離散序列
- 不考慮位置的重要性差異

**適用場景：**
- 圖片哈希（pHash、aHash）
- 二進位編碼相似性
- 糾錯碼
- LSH 的漢明空間投影

---

## 7.8 切比雪夫距離（Chebyshev Distance）

切比雪夫距離，也稱為 L∞ 距離或棋盤距離，計算的是所有維度上差異的最大值。

### 7.8.1 數學定義

$$d_{chebyshev}(\mathbf{a}, \mathbf{b}) = \max_{i}|a_i - b_i|$$

### 7.8.2 Python 實作

```python
class ChebyshevDistance:
    """
    切比雪夫距離（L∞ 距離）計算器

    ‹1› 關注最大差異
    ‹2› 適用於需要限制最大偏差的場景
    """

    @staticmethod
    def basic(a: np.ndarray, b: np.ndarray) -> float:
        """
        ‹1› 基本實作
        """
        return np.max(np.abs(a - b))

    @staticmethod
    def batch_compute(
        queries: np.ndarray,
        database: np.ndarray
    ) -> np.ndarray:
        """
        ‹2› 批量計算切比雪夫距離
        """
        diff = np.abs(queries[:, np.newaxis, :] - database[np.newaxis, :, :])
        return np.max(diff, axis=2)


def demonstrate_chebyshev():
    """
    ‹1› 展示切比雪夫距離的特性
    """
    print("切比雪夫距離 - 棋盤移動範例")
    print("=" * 60)

    # 在棋盤上，國王從 (0,0) 移動到 (3,4)
    # 國王每步可以移動到相鄰的 8 個格子
    start = np.array([0, 0])
    end = np.array([3, 4])

    chebyshev = ChebyshevDistance.basic(start, end)
    manhattan = ManhattanDistance.basic(start, end)
    euclidean = EuclideanDistance.numpy_norm(start, end)

    print(f"起點: {start}")
    print(f"終點: {end}")
    print()
    print(f"切比雪夫距離: {chebyshev} （國王需要的最少步數）")
    print(f"曼哈頓距離: {manhattan} （車需要的最少步數）")
    print(f"歐氏距離: {euclidean:.2f} （直線距離）")

    print("\n視覺化：")
    print("  0 1 2 3")
    print("4 . . . E")
    print("3 . . . ↗")
    print("2 . . ↗ .")
    print("1 . ↗ . .")
    print("0 S . . .")
    print()
    print("S = 起點, E = 終點, ↗ = 國王的對角移動路徑")


if __name__ == "__main__":
    demonstrate_chebyshev()
```

---

## 7.9 綜合比較與選擇指南

### 7.9.1 度量方法總覽

```python
def comprehensive_comparison():
    """
    ‹1› 綜合比較所有相似性度量
    """
    print("相似性度量綜合比較")
    print("=" * 80)

    np.random.seed(42)

    # 生成測試向量
    dim = 128
    a = np.random.randn(dim).astype(np.float32)
    b = np.random.randn(dim).astype(np.float32)

    # 正規化版本
    a_norm = a / np.linalg.norm(a)
    b_norm = b / np.linalg.norm(b)

    # 二進位版本（用於漢明距離）
    a_binary = (a > 0).astype(int)
    b_binary = (b > 0).astype(int)

    print(f"向量維度: {dim}")
    print()

    results = []

    # 歐氏距離
    euclidean = EuclideanDistance.numpy_norm(a, b)
    results.append(("歐氏距離 (L2)", euclidean, "[0, ∞)", "較小越相似"))

    # 餘弦相似度
    cosine = CosineSimilarity.basic(a, b)
    results.append(("餘弦相似度", cosine, "[-1, 1]", "越大越相似"))

    # 曼哈頓距離
    manhattan = ManhattanDistance.basic(a, b)
    results.append(("曼哈頓距離 (L1)", manhattan, "[0, ∞)", "較小越相似"))

    # 內積
    dot = InnerProduct.basic(a, b)
    results.append(("內積", dot, "(-∞, ∞)", "越大越相似"))

    # 內積（正規化向量）
    dot_norm = InnerProduct.basic(a_norm, b_norm)
    results.append(("內積（正規化）", dot_norm, "[-1, 1]", "越大越相似"))

    # 漢明距離
    hamming = HammingDistance.basic(a_binary, b_binary)
    results.append(("漢明距離", hamming, f"[0, {dim}]", "較小越相似"))

    # 切比雪夫距離
    chebyshev = ChebyshevDistance.basic(a, b)
    results.append(("切比雪夫距離 (L∞)", chebyshev, "[0, ∞)", "較小越相似"))

    print(f"{'度量方法':<20} {'數值':<15} {'值域':<15} {'解釋':<15}")
    print("-" * 65)
    for name, value, range_, interpretation in results:
        print(f"{name:<20} {value:<15.4f} {range_:<15} {interpretation:<15}")


if __name__ == "__main__":
    comprehensive_comparison()
```

### 7.9.2 選擇決策樹

```
                        你的數據是什麼類型？
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
         文字/語意        數值特徵          集合/二進位
            │                 │                 │
       餘弦相似度        需要考慮向量大小？     │
            │           ┌─────┴─────┐          │
            │          是           否          │
            │           │           │          │
            │      歐氏距離     餘弦相似度      │
            │           │           │          │
            │     有異常值？        │      Jaccard
            │     ┌─────┴─────┐    │     或漢明距離
            │    是           否   │
            │     │           │    │
            │ 曼哈頓距離   歐氏距離  │
            │     │           │    │
            └─────┴───────────┴────┘
```

### 7.9.3 場景選擇指南

| 應用場景 | 推薦度量 | 原因 |
|---------|---------|------|
| 語意搜尋 | 餘弦相似度 | 關注語意方向，不關注文件長度 |
| 圖片相似性 | 歐氏距離 | 像素級比較需要考慮絕對差異 |
| 推薦系統 | 內積 / 餘弦 | 用戶-物品匹配 |
| 文件去重 | Jaccard + MinHash | 高效處理大規模集合 |
| 圖片哈希 | 漢明距離 | 二進位編碼快速比較 |
| 時間序列 | 歐氏/DTW | 需要對齊的序列比較 |
| 稀疏特徵 | 曼哈頓/Jaccard | 對稀疏性友好 |
| 異常檢測 | 馬氏距離 | 考慮特徵相關性 |

---

## 7.10 效能優化技巧

### 7.10.1 預計算與快取

```python
class OptimizedSimilaritySearch:
    """
    ‹1› 優化的相似性搜尋類

    使用預計算和快取加速搜尋
    """

    def __init__(self, database: np.ndarray, metric: str = 'cosine'):
        """
        ‹1› 初始化並進行預計算

        Args:
            database: 資料庫向量，shape (n, dim)
            metric: 使用的度量方法
        """
        self.database = database.astype(np.float32)
        self.metric = metric
        self.n, self.dim = database.shape

        # 預計算
        if metric == 'cosine':
            # 預先正規化所有向量
            norms = np.linalg.norm(self.database, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            self.database_normalized = self.database / norms

        elif metric == 'euclidean':
            # 預計算所有向量的平方和
            self.database_sq_norms = np.sum(self.database ** 2, axis=1)

    def search(self, query: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """
        ‹2› 執行相似性搜尋

        Returns:
            (indices, scores): 最相似的 k 個向量
        """
        query = query.astype(np.float32)

        if self.metric == 'cosine':
            # 正規化查詢向量
            query_norm = query / np.linalg.norm(query)
            # 計算相似度（使用預正規化的資料庫）
            similarities = np.dot(self.database_normalized, query_norm)
            # 找出最大的 k 個
            indices = np.argpartition(similarities, -k)[-k:]
            indices = indices[np.argsort(similarities[indices])[::-1]]
            return indices, similarities[indices]

        elif self.metric == 'euclidean':
            # 使用預計算的平方和
            query_sq_norm = np.sum(query ** 2)
            cross_term = np.dot(self.database, query)
            distances_sq = self.database_sq_norms + query_sq_norm - 2 * cross_term
            distances_sq = np.maximum(distances_sq, 0)
            distances = np.sqrt(distances_sq)
            # 找出最小的 k 個
            indices = np.argpartition(distances, k)[:k]
            indices = indices[np.argsort(distances[indices])]
            return indices, distances[indices]


def benchmark_optimization():
    """
    ‹1› 基準測試優化效果
    """
    print("預計算優化效果比較")
    print("=" * 60)

    np.random.seed(42)

    # 生成測試數據
    n_database = 100000
    dim = 256
    n_queries = 100
    k = 10

    database = np.random.randn(n_database, dim).astype(np.float32)
    queries = np.random.randn(n_queries, dim).astype(np.float32)

    print(f"資料庫大小: {n_database:,} 向量")
    print(f"向量維度: {dim}")
    print(f"查詢數量: {n_queries}")
    print()

    # 測試優化版本
    print("測試餘弦相似度...")

    # 初始化（包含預計算）
    start = time.perf_counter()
    searcher = OptimizedSimilaritySearch(database, metric='cosine')
    init_time = time.perf_counter() - start

    # 搜尋
    start = time.perf_counter()
    for query in queries:
        _ = searcher.search(query, k)
    search_time = time.perf_counter() - start

    print(f"  初始化時間（含預計算）: {init_time*1000:.2f} ms")
    print(f"  總搜尋時間: {search_time*1000:.2f} ms")
    print(f"  平均每次搜尋: {search_time/n_queries*1000:.2f} ms")
    print()

    # 測試無優化版本
    print("測試無優化版本...")
    start = time.perf_counter()
    for query in queries:
        # 每次都要正規化
        query_norm = query / np.linalg.norm(query)
        db_norms = np.linalg.norm(database, axis=1, keepdims=True)
        db_normalized = database / db_norms
        similarities = np.dot(db_normalized, query_norm)
        indices = np.argpartition(similarities, -k)[-k:]
    naive_time = time.perf_counter() - start

    print(f"  總搜尋時間: {naive_time*1000:.2f} ms")
    print(f"  平均每次搜尋: {naive_time/n_queries*1000:.2f} ms")
    print()

    speedup = naive_time / search_time
    print(f"加速比: {speedup:.1f}x")


if __name__ == "__main__":
    benchmark_optimization()
```

### 7.10.2 SIMD 和 GPU 加速

```python
def demonstrate_simd_potential():
    """
    ‹1› 展示 SIMD 加速的潛力

    通過適當的數據對齊和批量處理
    可以讓 NumPy/BLAS 自動使用 SIMD 指令
    """
    print("SIMD 加速潛力展示")
    print("=" * 60)

    np.random.seed(42)

    # 測試不同的數據對齊
    dim = 256
    n = 10000
    n_iterations = 100

    # 對齊的數據（C 連續，32 字節對齊）
    aligned_data = np.ascontiguousarray(
        np.random.randn(n, dim).astype(np.float32)
    )

    # 非對齊的數據（Fortran 連續）
    unaligned_data = np.asfortranarray(
        np.random.randn(n, dim).astype(np.float32)
    )

    query = np.random.randn(dim).astype(np.float32)

    # 測試對齊數據
    start = time.perf_counter()
    for _ in range(n_iterations):
        _ = np.dot(aligned_data, query)
    aligned_time = time.perf_counter() - start

    # 測試非對齊數據
    start = time.perf_counter()
    for _ in range(n_iterations):
        _ = np.dot(unaligned_data, query)
    unaligned_time = time.perf_counter() - start

    print(f"數據大小: {n:,} x {dim}")
    print(f"迭代次數: {n_iterations}")
    print()
    print(f"對齊數據 (C 連續): {aligned_time*1000:.2f} ms")
    print(f"非對齊數據 (F 連續): {unaligned_time*1000:.2f} ms")
    print(f"對齊加速比: {unaligned_time/aligned_time:.2f}x")
    print()
    print("建議：始終使用 np.ascontiguousarray() 確保數據對齊")


if __name__ == "__main__":
    demonstrate_simd_potential()
```

---

## 7.11 實戰練習

### 練習 1：實作加權歐氏距離

```python
def weighted_euclidean_distance(
    a: np.ndarray,
    b: np.ndarray,
    weights: np.ndarray
) -> float:
    """
    實作加權歐氏距離

    公式：d = sqrt(sum(w_i * (a_i - b_i)^2))

    Args:
        a, b: 輸入向量
        weights: 每個維度的權重

    Returns:
        加權歐氏距離
    """
    # TODO: 實作此函數
    diff = a - b
    weighted_sq_diff = weights * (diff ** 2)
    return np.sqrt(np.sum(weighted_sq_diff))


# 測試
a = np.array([1.0, 2.0, 3.0])
b = np.array([4.0, 5.0, 6.0])
weights = np.array([1.0, 2.0, 3.0])  # 第三個維度最重要

result = weighted_euclidean_distance(a, b, weights)
print(f"加權歐氏距離: {result:.4f}")
# 預期結果：sqrt(1*9 + 2*9 + 3*9) = sqrt(54) ≈ 7.35
```

### 練習 2：實作軟餘弦相似度

```python
def soft_cosine_similarity(
    a: np.ndarray,
    b: np.ndarray,
    similarity_matrix: np.ndarray
) -> float:
    """
    實作軟餘弦相似度

    考慮特徵之間的相似性
    公式：(a^T * S * b) / (sqrt(a^T * S * a) * sqrt(b^T * S * b))

    Args:
        a, b: 輸入向量
        similarity_matrix: 特徵相似度矩陣 S

    Returns:
        軟餘弦相似度
    """
    # TODO: 實作此函數
    numerator = np.dot(a, np.dot(similarity_matrix, b))
    denom_a = np.sqrt(np.dot(a, np.dot(similarity_matrix, a)))
    denom_b = np.sqrt(np.dot(b, np.dot(similarity_matrix, b)))

    if denom_a == 0 or denom_b == 0:
        return 0.0

    return numerator / (denom_a * denom_b)
```

---

## 7.12 本章回顧

在本章中，我們深入探討了向量資料庫中最重要的基礎概念——相似性度量。

### 核心要點

1. **歐氏距離**：直觀的「直線距離」，適合需要考慮向量大小的場景

2. **餘弦相似度**：只關注向量方向，是語意搜尋的首選

3. **曼哈頓距離**：對異常值魯棒，適合稀疏數據

4. **內積**：計算最簡單，對正規化向量等價於餘弦相似度

5. **Jaccard 相似度**：適合集合型數據，可用 MinHash 加速

6. **漢明距離**：適合二進位編碼，計算極快

7. **切比雪夫距離**：關注最大維度差異

### 選擇原則

- 語意/文字數據 → 餘弦相似度
- 需要考慮向量大小 → 歐氏距離
- 有異常值 → 曼哈頓距離
- 集合數據 → Jaccard 相似度
- 二進位編碼 → 漢明距離

### 優化技巧

- 預先正規化向量
- 使用矩陣運算取代迴圈
- 確保數據對齊以啟用 SIMD
- 對於大規模數據使用近似方法

---

## 思考題

1. 為什麼在高維空間中，歐氏距離的區分度會下降？這對向量資料庫的設計有什麼影響？

2. 如果你的應用同時需要考慮向量的方向和大小，有什麼方法可以結合餘弦相似度和歐氏距離？

3. MinHash 為什麼能夠準確估計 Jaccard 相似度？它的誤差界限是多少？

4. 在推薦系統中，為什麼內積搜尋（MIPS）比餘弦相似度搜尋更受歡迎？

5. 設計一個實驗，比較不同相似性度量在你熟悉的數據集上的效果。你期望看到什麼結果？

---

下一章，我們將深入探討 FAISS——Facebook AI 開發的強大向量檢索引擎，學習如何使用各種索引結構來加速相似性搜尋。
