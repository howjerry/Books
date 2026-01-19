# Chapter 12：自動駕駛感知系統案例

> 「在自動駕駛中，毫秒級的延遲可能意味著生命與死亡的差別。向量搜尋讓車輛能夠在瞬間識別出周圍的一切。」

## 學習目標

完成本章後，你將能夠：

- 理解自動駕駛感知系統的架構與挑戰
- 設計高效的物件識別向量搜尋系統
- 實作即時的場景理解和異常檢測
- 優化低延遲的向量搜尋管道
- 建構可靠的自動駕駛數據管理系統

---

## 12.1 自動駕駛感知系統概述

### 12.1.1 感知系統的角色

自動駕駛感知系統是車輛的「眼睛」和「耳朵」，負責理解車輛周圍的環境。向量搜尋在其中扮演關鍵角色：

```
                    自動駕駛感知系統架構
    ┌─────────────────────────────────────────────────────┐
    │                    感測器層                         │
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
    │  │ Camera  │ │  LiDAR  │ │  Radar  │ │  GPS    │  │
    │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
    └───────┼───────────┼───────────┼───────────┼───────┘
            │           │           │           │
    ┌───────┼───────────┼───────────┼───────────┼───────┐
    │       ▼           ▼           ▼           ▼       │
    │                  感知處理層                        │
    │  ┌─────────────────────────────────────────────┐  │
    │  │          特徵提取（CNN/Transformer）         │  │
    │  └─────────────────────┬───────────────────────┘  │
    │                        │                          │
    │  ┌─────────────────────▼───────────────────────┐  │
    │  │              向量搜尋引擎                    │  │
    │  │  • 物件識別：與已知物件向量比對              │  │
    │  │  • 場景理解：與已知場景向量比對              │  │
    │  │  • 異常檢測：檢測未知物件                    │  │
    │  └─────────────────────┬───────────────────────┘  │
    │                        │                          │
    │  ┌─────────────────────▼───────────────────────┐  │
    │  │              融合與決策                      │  │
    │  └─────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────┘
```

### 12.1.2 向量搜尋的應用場景

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from enum import Enum
import numpy as np

class PerceptionTask(Enum):
    """感知任務類型"""
    OBJECT_DETECTION = "object_detection"       # 物件偵測
    SCENE_RECOGNITION = "scene_recognition"     # 場景識別
    ANOMALY_DETECTION = "anomaly_detection"     # 異常檢測
    LANE_DETECTION = "lane_detection"           # 車道檢測
    SIGN_RECOGNITION = "sign_recognition"       # 標誌識別


@dataclass
class PerceptionObject:
    """感知物件"""
    object_id: str
    object_class: str              # 物件類別
    confidence: float              # 置信度
    bounding_box: Tuple[float, float, float, float]  # x, y, w, h
    distance: float                # 與車輛距離（米）
    velocity: Tuple[float, float]  # 速度（m/s）
    feature_vector: np.ndarray     # 特徵向量


@dataclass
class PerceptionResult:
    """感知結果"""
    timestamp: float
    frame_id: int
    objects: List[PerceptionObject]
    scene_type: str
    anomaly_score: float
    processing_time_ms: float


class PerceptionSystemOverview:
    """
    感知系統概覽

    ‹1› 定義系統需求
    ‹2› 說明向量搜尋的角色
    """

    @staticmethod
    def get_requirements() -> Dict[str, Any]:
        """
        ‹1› 自動駕駛感知系統需求
        """
        return {
            "latency": {
                "target_ms": 50,       # 目標延遲 < 50ms
                "max_ms": 100,         # 最大延遲 < 100ms
                "reason": "30 FPS 視頻需要在 33ms 內處理"
            },
            "accuracy": {
                "recall": 0.99,        # 召回率 > 99%（不能漏檢）
                "precision": 0.95,     # 精確度 > 95%
                "reason": "安全關鍵系統需要高可靠性"
            },
            "throughput": {
                "frames_per_second": 30,
                "objects_per_frame": 100,
                "reason": "多攝像頭同時處理"
            },
            "database_size": {
                "object_classes": 1000,         # 物件類別
                "scene_templates": 10000,       # 場景模板
                "anomaly_samples": 100000,      # 異常樣本
            }
        }

    @staticmethod
    def print_use_cases():
        """
        ‹2› 向量搜尋應用場景
        """
        use_cases = """
        向量搜尋在自動駕駛中的應用
        ==========================

        1. 物件識別
           ─────────
           場景：識別道路上的行人、車輛、動物等
           方法：將檢測到的物件特徵與已知物件向量庫比對
           要求：延遲 < 10ms，召回率 > 99%

        2. 場景理解
           ─────────
           場景：判斷當前是城市道路、高速公路還是鄉村道路
           方法：將場景特徵與場景模板庫比對
           要求：準確率 > 95%，支援多場景混合

        3. 交通標誌識別
           ─────────────
           場景：識別限速牌、路標、紅綠燈等
           方法：將標誌特徵與標誌向量庫比對
           要求：準確率 > 99.5%，支援部分遮擋

        4. 異常物件檢測
           ─────────────
           場景：檢測道路上的異常物件（落石、事故車輛等）
           方法：與正常物件向量庫比對，異常度高則觸發警報
           要求：誤報率 < 1%，漏報率 < 0.1%

        5. 車輛重識別
           ──────────
           場景：跨攝像頭追蹤同一車輛
           方法：提取車輛特徵向量，跨時間跨攝像頭比對
           要求：準確率 > 90%，支援外觀變化
        """
        print(use_cases)


def demonstrate_overview():
    """
    ‹1› 系統概覽示範
    """
    print("自動駕駛感知系統概覽")
    print("=" * 60)

    overview = PerceptionSystemOverview()

    # 需求
    reqs = overview.get_requirements()
    print("\n系統需求:")
    print(f"  延遲: < {reqs['latency']['target_ms']}ms（最大 {reqs['latency']['max_ms']}ms）")
    print(f"  召回率: > {reqs['accuracy']['recall']:.0%}")
    print(f"  精確度: > {reqs['accuracy']['precision']:.0%}")
    print(f"  吞吐量: {reqs['throughput']['frames_per_second']} FPS")

    # 應用場景
    overview.print_use_cases()


if __name__ == "__main__":
    demonstrate_overview()
```

---

## 12.2 物件識別向量搜尋系統

### 12.2.1 系統架構

```python
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import time

@dataclass
class ObjectClass:
    """物件類別定義"""
    class_id: int
    name: str
    category: str  # vehicle, pedestrian, cyclist, animal, obstacle
    danger_level: int  # 1-5
    reference_vectors: List[np.ndarray]


class ObjectRecognitionSystem:
    """
    物件識別系統

    ‹1› 管理物件類別向量庫
    ‹2› 即時物件識別
    ‹3› 支援增量更新
    """

    def __init__(self, dimension: int = 512):
        """
        ‹1› 初始化

        Args:
            dimension: 特徵向量維度
        """
        self.dimension = dimension
        self.classes: Dict[int, ObjectClass] = {}
        self.class_vectors: np.ndarray = None
        self.class_ids: List[int] = []

        # 效能統計
        self.stats = {
            "total_queries": 0,
            "total_latency_ms": 0,
            "cache_hits": 0
        }

        # 簡單快取
        self.cache: Dict[str, Tuple[int, float]] = {}
        self.cache_size = 1000

    def register_class(self, object_class: ObjectClass):
        """
        ‹2› 註冊物件類別
        """
        self.classes[object_class.class_id] = object_class
        print(f"註冊類別: {object_class.name} (ID: {object_class.class_id})")

    def build_index(self):
        """
        ‹3› 建構搜尋索引

        將所有類別的參考向量合併成一個索引
        """
        vectors = []
        ids = []

        for class_id, obj_class in self.classes.items():
            for vec in obj_class.reference_vectors:
                vectors.append(vec)
                ids.append(class_id)

        if vectors:
            self.class_vectors = np.array(vectors).astype(np.float32)
            self.class_ids = ids
            # 正規化
            norms = np.linalg.norm(self.class_vectors, axis=1, keepdims=True)
            self.class_vectors = self.class_vectors / norms

            print(f"索引建構完成: {len(vectors)} 個參考向量")

    def recognize(
        self,
        feature_vector: np.ndarray,
        top_k: int = 3,
        threshold: float = 0.7
    ) -> List[Tuple[int, str, float]]:
        """
        ‹4› 識別物件

        Args:
            feature_vector: 待識別物件的特徵向量
            top_k: 返回前 k 個候選
            threshold: 相似度閾值

        Returns:
            [(class_id, class_name, similarity), ...]
        """
        start_time = time.perf_counter()

        # 檢查快取
        cache_key = self._get_cache_key(feature_vector)
        if cache_key in self.cache:
            self.stats["cache_hits"] += 1
            cached = self.cache[cache_key]
            return [(cached[0], self.classes[cached[0]].name, cached[1])]

        # 正規化查詢向量
        feature_vector = feature_vector.astype(np.float32)
        norm = np.linalg.norm(feature_vector)
        if norm > 0:
            feature_vector = feature_vector / norm

        # 計算相似度（餘弦相似度 = 內積）
        similarities = np.dot(self.class_vectors, feature_vector)

        # 找出前 k 個
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            sim = similarities[idx]
            if sim >= threshold:
                class_id = self.class_ids[idx]
                class_name = self.classes[class_id].name
                results.append((class_id, class_name, float(sim)))

        # 更新快取
        if results:
            self._update_cache(cache_key, results[0][0], results[0][2])

        # 更新統計
        latency = (time.perf_counter() - start_time) * 1000
        self.stats["total_queries"] += 1
        self.stats["total_latency_ms"] += latency

        return results

    def batch_recognize(
        self,
        feature_vectors: np.ndarray,
        top_k: int = 1,
        threshold: float = 0.7
    ) -> List[List[Tuple[int, str, float]]]:
        """
        ‹5› 批量識別

        同時識別多個物件，提高吞吐量
        """
        start_time = time.perf_counter()

        # 正規化
        feature_vectors = feature_vectors.astype(np.float32)
        norms = np.linalg.norm(feature_vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        feature_vectors = feature_vectors / norms

        # 批量計算相似度
        similarities = np.dot(feature_vectors, self.class_vectors.T)

        results = []
        for i, sims in enumerate(similarities):
            top_indices = np.argsort(sims)[-top_k:][::-1]
            item_results = []
            for idx in top_indices:
                sim = sims[idx]
                if sim >= threshold:
                    class_id = self.class_ids[idx]
                    class_name = self.classes[class_id].name
                    item_results.append((class_id, class_name, float(sim)))
            results.append(item_results)

        # 更新統計
        latency = (time.perf_counter() - start_time) * 1000
        self.stats["total_queries"] += len(feature_vectors)
        self.stats["total_latency_ms"] += latency

        return results

    def _get_cache_key(self, vector: np.ndarray) -> str:
        """生成快取鍵"""
        # 使用向量的量化版本作為鍵
        quantized = (vector[:8] * 100).astype(int).tobytes()
        return quantized.hex()

    def _update_cache(self, key: str, class_id: int, similarity: float):
        """更新快取"""
        if len(self.cache) >= self.cache_size:
            # 簡單的 FIFO 淘汰
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = (class_id, similarity)

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計"""
        total = self.stats["total_queries"]
        return {
            "total_queries": total,
            "avg_latency_ms": self.stats["total_latency_ms"] / max(total, 1),
            "cache_hit_rate": self.stats["cache_hits"] / max(total, 1)
        }


def demonstrate_object_recognition():
    """
    ‹1› 物件識別示範
    """
    print("物件識別系統示範")
    print("=" * 60)

    # 初始化系統
    system = ObjectRecognitionSystem(dimension=512)

    # 註冊物件類別
    np.random.seed(42)

    classes = [
        ("car", "vehicle", 2),
        ("truck", "vehicle", 3),
        ("bus", "vehicle", 3),
        ("pedestrian", "pedestrian", 4),
        ("cyclist", "cyclist", 4),
        ("motorcycle", "vehicle", 3),
        ("dog", "animal", 3),
        ("traffic_cone", "obstacle", 2),
        ("barrier", "obstacle", 2),
        ("debris", "obstacle", 5),
    ]

    for i, (name, category, danger) in enumerate(classes):
        # 為每個類別生成多個參考向量
        ref_vectors = [np.random.randn(512).astype(np.float32) for _ in range(10)]
        system.register_class(ObjectClass(
            class_id=i,
            name=name,
            category=category,
            danger_level=danger,
            reference_vectors=ref_vectors
        ))

    # 建構索引
    system.build_index()

    # 模擬識別
    print("\n單一物件識別:")
    print("-" * 40)

    # 生成類似 "car" 的特徵向量
    test_vector = system.classes[0].reference_vectors[0] + np.random.randn(512) * 0.1
    results = system.recognize(test_vector, top_k=3)

    for class_id, class_name, similarity in results:
        print(f"  類別: {class_name}, 相似度: {similarity:.4f}")

    # 批量識別
    print("\n批量識別（100 個物件）:")
    print("-" * 40)

    batch_vectors = np.random.randn(100, 512).astype(np.float32)
    start = time.perf_counter()
    batch_results = system.batch_recognize(batch_vectors, top_k=1)
    elapsed = (time.perf_counter() - start) * 1000

    recognized = sum(1 for r in batch_results if r)
    print(f"  識別數量: {recognized}/100")
    print(f"  總耗時: {elapsed:.2f}ms")
    print(f"  每物件耗時: {elapsed/100:.3f}ms")

    # 統計
    print("\n系統統計:")
    stats = system.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    demonstrate_object_recognition()
```

### 12.2.2 低延遲優化

```python
import numpy as np
from typing import List, Tuple
import time

class LowLatencyOptimizer:
    """
    低延遲優化器

    ‹1› 向量量化
    ‹2› 分層搜尋
    ‹3› GPU 加速
    """

    def __init__(self, dimension: int):
        self.dimension = dimension

    def quantize_vectors(
        self,
        vectors: np.ndarray,
        bits: int = 8
    ) -> np.ndarray:
        """
        ‹1› 向量量化

        將 float32 向量量化為 int8，減少記憶體和計算量
        """
        # 找出範圍
        min_val = vectors.min()
        max_val = vectors.max()
        scale = (max_val - min_val) / (2 ** bits - 1)

        # 量化
        quantized = ((vectors - min_val) / scale).astype(np.uint8)

        return quantized, min_val, scale

    def hierarchical_search(
        self,
        query: np.ndarray,
        coarse_vectors: np.ndarray,
        fine_vectors: np.ndarray,
        coarse_k: int = 10,
        final_k: int = 1
    ) -> List[Tuple[int, float]]:
        """
        ‹2› 分層搜尋

        先用粗粒度向量快速篩選，再用細粒度向量精確排序
        """
        # 粗粒度搜尋
        coarse_sims = np.dot(coarse_vectors, query)
        coarse_indices = np.argpartition(coarse_sims, -coarse_k)[-coarse_k:]

        # 細粒度搜尋
        fine_candidates = fine_vectors[coarse_indices]
        fine_sims = np.dot(fine_candidates, query)
        fine_indices = np.argsort(fine_sims)[-final_k:][::-1]

        results = [
            (coarse_indices[i], fine_sims[i])
            for i in fine_indices
        ]

        return results

    def create_coarse_vectors(
        self,
        vectors: np.ndarray,
        reduction_factor: int = 4
    ) -> np.ndarray:
        """
        ‹3› 創建粗粒度向量

        通過降維或池化減少向量維度
        """
        n, d = vectors.shape
        new_d = d // reduction_factor

        # 使用平均池化
        coarse = vectors.reshape(n, new_d, reduction_factor).mean(axis=2)

        # 正規化
        norms = np.linalg.norm(coarse, axis=1, keepdims=True)
        coarse = coarse / norms

        return coarse.astype(np.float32)


def demonstrate_low_latency():
    """
    ‹1› 低延遲優化示範
    """
    print("低延遲優化示範")
    print("=" * 60)

    np.random.seed(42)

    dimension = 512
    n_vectors = 10000
    n_queries = 100

    # 生成測試數據
    database = np.random.randn(n_vectors, dimension).astype(np.float32)
    # 正規化
    database = database / np.linalg.norm(database, axis=1, keepdims=True)
    queries = np.random.randn(n_queries, dimension).astype(np.float32)
    queries = queries / np.linalg.norm(queries, axis=1, keepdims=True)

    optimizer = LowLatencyOptimizer(dimension)

    # 1. 基準：直接搜尋
    print("\n1. 基準（直接搜尋）:")
    start = time.perf_counter()
    for query in queries:
        sims = np.dot(database, query)
        _ = np.argmax(sims)
    baseline_time = (time.perf_counter() - start) * 1000
    print(f"   總時間: {baseline_time:.2f}ms")
    print(f"   每查詢: {baseline_time/n_queries:.3f}ms")

    # 2. 分層搜尋
    print("\n2. 分層搜尋:")
    coarse_vectors = optimizer.create_coarse_vectors(database, reduction_factor=4)
    print(f"   粗粒度維度: {coarse_vectors.shape[1]}")

    start = time.perf_counter()
    for query in queries:
        coarse_query = optimizer.create_coarse_vectors(
            query.reshape(1, -1), reduction_factor=4
        )[0]
        _ = optimizer.hierarchical_search(
            query, coarse_vectors, database,
            coarse_k=100, final_k=1
        )
    hierarchical_time = (time.perf_counter() - start) * 1000
    print(f"   總時間: {hierarchical_time:.2f}ms")
    print(f"   每查詢: {hierarchical_time/n_queries:.3f}ms")
    print(f"   加速比: {baseline_time/hierarchical_time:.2f}x")

    # 3. 向量量化
    print("\n3. 向量量化:")
    quantized, min_val, scale = optimizer.quantize_vectors(database)
    print(f"   原始大小: {database.nbytes / 1024:.1f} KB")
    print(f"   量化後大小: {quantized.nbytes / 1024:.1f} KB")
    print(f"   壓縮比: {database.nbytes / quantized.nbytes:.1f}x")


if __name__ == "__main__":
    demonstrate_low_latency()
```

---

## 12.3 場景理解系統

### 12.3.1 場景分類

```python
from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass
from enum import Enum

class SceneType(Enum):
    """場景類型"""
    HIGHWAY = "highway"              # 高速公路
    URBAN = "urban"                  # 城市道路
    RESIDENTIAL = "residential"      # 住宅區
    RURAL = "rural"                  # 鄉村道路
    INTERSECTION = "intersection"    # 十字路口
    TUNNEL = "tunnel"               # 隧道
    PARKING = "parking"             # 停車場
    CONSTRUCTION = "construction"    # 施工區


@dataclass
class SceneTemplate:
    """場景模板"""
    template_id: str
    scene_type: SceneType
    description: str
    feature_vector: np.ndarray
    typical_objects: List[str]
    speed_limit: Optional[int]
    risk_level: int  # 1-5


class SceneUnderstandingSystem:
    """
    場景理解系統

    ‹1› 識別當前道路場景
    ‹2› 提供駕駛建議
    ‹3› 支援場景轉換檢測
    """

    def __init__(self, dimension: int = 1024):
        """
        ‹1› 初始化
        """
        self.dimension = dimension
        self.templates: Dict[str, SceneTemplate] = {}
        self.template_vectors: np.ndarray = None
        self.template_ids: List[str] = []

        # 場景歷史（用於平滑）
        self.scene_history: List[SceneType] = []
        self.history_size = 10

    def register_template(self, template: SceneTemplate):
        """
        ‹2› 註冊場景模板
        """
        self.templates[template.template_id] = template
        print(f"註冊場景: {template.scene_type.value}")

    def build_index(self):
        """
        ‹3› 建構場景索引
        """
        vectors = []
        ids = []

        for template_id, template in self.templates.items():
            vectors.append(template.feature_vector)
            ids.append(template_id)

        if vectors:
            self.template_vectors = np.array(vectors).astype(np.float32)
            self.template_ids = ids
            # 正規化
            norms = np.linalg.norm(self.template_vectors, axis=1, keepdims=True)
            self.template_vectors = self.template_vectors / norms

            print(f"索引建構完成: {len(vectors)} 個場景模板")

    def classify_scene(
        self,
        scene_vector: np.ndarray,
        top_k: int = 3
    ) -> List[Tuple[SceneType, float, Dict]]:
        """
        ‹4› 分類場景

        Args:
            scene_vector: 場景特徵向量
            top_k: 返回前 k 個候選場景

        Returns:
            [(scene_type, confidence, metadata), ...]
        """
        # 正規化
        scene_vector = scene_vector.astype(np.float32)
        norm = np.linalg.norm(scene_vector)
        if norm > 0:
            scene_vector = scene_vector / norm

        # 計算相似度
        similarities = np.dot(self.template_vectors, scene_vector)

        # 獲取前 k 個
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            template_id = self.template_ids[idx]
            template = self.templates[template_id]
            confidence = float(similarities[idx])

            metadata = {
                "template_id": template_id,
                "description": template.description,
                "typical_objects": template.typical_objects,
                "speed_limit": template.speed_limit,
                "risk_level": template.risk_level
            }

            results.append((template.scene_type, confidence, metadata))

        return results

    def update_scene(self, scene_vector: np.ndarray) -> Tuple[SceneType, float]:
        """
        ‹5› 更新當前場景（帶平滑）

        使用滑動窗口平滑場景判斷，避免閃爍
        """
        # 分類當前幀
        results = self.classify_scene(scene_vector, top_k=1)

        if not results:
            return SceneType.URBAN, 0.5  # 預設

        current_scene, confidence, _ = results[0]

        # 更新歷史
        self.scene_history.append(current_scene)
        if len(self.scene_history) > self.history_size:
            self.scene_history.pop(0)

        # 投票決定最終場景
        from collections import Counter
        scene_counts = Counter(self.scene_history)
        final_scene = scene_counts.most_common(1)[0][0]

        # 計算平滑後的置信度
        smooth_confidence = scene_counts[final_scene] / len(self.scene_history)

        return final_scene, smooth_confidence * confidence

    def detect_scene_transition(self) -> Optional[Tuple[SceneType, SceneType]]:
        """
        ‹6› 檢測場景轉換

        Returns:
            (from_scene, to_scene) 如果檢測到轉換
        """
        if len(self.scene_history) < 4:
            return None

        # 檢查最近的場景變化
        recent = self.scene_history[-4:]
        if recent[0] == recent[1] and recent[2] == recent[3] and recent[0] != recent[2]:
            return (recent[0], recent[2])

        return None

    def get_driving_suggestions(self, scene_type: SceneType) -> List[str]:
        """
        ‹7› 獲取駕駛建議
        """
        suggestions = {
            SceneType.HIGHWAY: [
                "保持車道",
                "注意前車距離",
                "注意高速出口"
            ],
            SceneType.URBAN: [
                "注意行人和自行車",
                "注意交通信號",
                "注意突然變道的車輛"
            ],
            SceneType.RESIDENTIAL: [
                "減速慢行",
                "注意兒童和寵物",
                "注意停放車輛"
            ],
            SceneType.INTERSECTION: [
                "減速觀察",
                "注意各方來車",
                "遵守信號燈"
            ],
            SceneType.TUNNEL: [
                "開啟車燈",
                "保持車距",
                "注意隧道出口光線變化"
            ],
            SceneType.CONSTRUCTION: [
                "大幅減速",
                "注意施工人員",
                "遵循臨時標誌"
            ]
        }

        return suggestions.get(scene_type, ["保持警惕"])


def demonstrate_scene_understanding():
    """
    ‹1› 場景理解示範
    """
    print("場景理解系統示範")
    print("=" * 60)

    np.random.seed(42)

    # 初始化系統
    system = SceneUnderstandingSystem(dimension=1024)

    # 註冊場景模板
    scene_configs = [
        (SceneType.HIGHWAY, "高速公路直道", ["car", "truck"], 120, 2),
        (SceneType.HIGHWAY, "高速公路彎道", ["car", "truck"], 100, 3),
        (SceneType.URBAN, "城市主幹道", ["car", "pedestrian", "traffic_light"], 60, 3),
        (SceneType.URBAN, "城市小街", ["car", "pedestrian", "bicycle"], 40, 4),
        (SceneType.INTERSECTION, "十字路口", ["car", "pedestrian", "traffic_light"], 30, 5),
        (SceneType.RESIDENTIAL, "住宅區道路", ["car", "pedestrian", "bicycle"], 30, 4),
        (SceneType.TUNNEL, "隧道入口", ["car", "truck"], 80, 3),
        (SceneType.CONSTRUCTION, "施工區域", ["car", "barrier", "worker"], 20, 5),
    ]

    for i, (scene_type, desc, objects, speed, risk) in enumerate(scene_configs):
        template = SceneTemplate(
            template_id=f"scene_{i}",
            scene_type=scene_type,
            description=desc,
            feature_vector=np.random.randn(1024).astype(np.float32),
            typical_objects=objects,
            speed_limit=speed,
            risk_level=risk
        )
        system.register_template(template)

    # 建構索引
    system.build_index()

    # 模擬場景分類
    print("\n場景分類示範:")
    print("-" * 50)

    # 生成類似 "高速公路" 的測試向量
    highway_template = list(system.templates.values())[0]
    test_vector = highway_template.feature_vector + np.random.randn(1024) * 0.2

    results = system.classify_scene(test_vector, top_k=3)

    print("輸入: 模擬高速公路場景")
    print("\n識別結果:")
    for scene_type, confidence, metadata in results:
        print(f"  場景: {scene_type.value}")
        print(f"  置信度: {confidence:.2%}")
        print(f"  描述: {metadata['description']}")
        print(f"  限速: {metadata['speed_limit']} km/h")
        print(f"  風險等級: {metadata['risk_level']}/5")
        print()

    # 獲取駕駛建議
    print("駕駛建議:")
    suggestions = system.get_driving_suggestions(results[0][0])
    for suggestion in suggestions:
        print(f"  • {suggestion}")


if __name__ == "__main__":
    demonstrate_scene_understanding()
```

---

## 12.4 異常檢測系統

### 12.4.1 基於向量的異常檢測

```python
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class AnomalyType(Enum):
    """異常類型"""
    UNKNOWN_OBJECT = "unknown_object"      # 未知物件
    UNUSUAL_BEHAVIOR = "unusual_behavior"   # 異常行為
    ROAD_HAZARD = "road_hazard"            # 道路危險
    SENSOR_ERROR = "sensor_error"          # 感測器錯誤


@dataclass
class AnomalyResult:
    """異常檢測結果"""
    is_anomaly: bool
    anomaly_score: float
    anomaly_type: Optional[AnomalyType]
    confidence: float
    description: str
    nearest_normal: Optional[str]


class AnomalyDetectionSystem:
    """
    異常檢測系統

    ‹1› 檢測未知物件
    ‹2› 檢測異常行為
    ‹3› 支援自適應閾值
    """

    def __init__(self, dimension: int = 512):
        """
        ‹1› 初始化

        Args:
            dimension: 特徵向量維度
        """
        self.dimension = dimension

        # 正常樣本向量庫
        self.normal_vectors: np.ndarray = None
        self.normal_labels: List[str] = []

        # 閾值（動態調整）
        self.anomaly_threshold = 0.5
        self.threshold_history: List[float] = []

        # 統計
        self.stats = {
            "total_detections": 0,
            "anomalies_detected": 0,
            "false_positives": 0
        }

    def add_normal_samples(
        self,
        vectors: np.ndarray,
        labels: List[str]
    ):
        """
        ‹2› 添加正常樣本

        Args:
            vectors: 正常樣本的特徵向量
            labels: 對應的標籤
        """
        # 正規化
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / norms

        if self.normal_vectors is None:
            self.normal_vectors = vectors.astype(np.float32)
            self.normal_labels = labels
        else:
            self.normal_vectors = np.vstack([self.normal_vectors, vectors])
            self.normal_labels.extend(labels)

        print(f"添加了 {len(labels)} 個正常樣本，總計: {len(self.normal_labels)}")

    def detect(
        self,
        feature_vector: np.ndarray,
        k_neighbors: int = 5
    ) -> AnomalyResult:
        """
        ‹3› 檢測異常

        使用 k-NN 距離判斷是否為異常

        Args:
            feature_vector: 待檢測的特徵向量
            k_neighbors: 參考的鄰居數量

        Returns:
            異常檢測結果
        """
        self.stats["total_detections"] += 1

        # 正規化
        feature_vector = feature_vector.astype(np.float32)
        norm = np.linalg.norm(feature_vector)
        if norm > 0:
            feature_vector = feature_vector / norm

        # 計算與所有正常樣本的相似度
        similarities = np.dot(self.normal_vectors, feature_vector)

        # 找出最相似的 k 個
        top_k_indices = np.argsort(similarities)[-k_neighbors:]
        top_k_similarities = similarities[top_k_indices]

        # 計算異常分數（1 - 平均相似度）
        avg_similarity = np.mean(top_k_similarities)
        anomaly_score = 1 - avg_similarity

        # 判斷是否異常
        is_anomaly = anomaly_score > self.anomaly_threshold

        # 確定異常類型
        anomaly_type = None
        if is_anomaly:
            if anomaly_score > 0.8:
                anomaly_type = AnomalyType.UNKNOWN_OBJECT
            elif anomaly_score > 0.6:
                anomaly_type = AnomalyType.UNUSUAL_BEHAVIOR
            else:
                anomaly_type = AnomalyType.ROAD_HAZARD

            self.stats["anomalies_detected"] += 1

        # 獲取最近的正常樣本
        nearest_idx = top_k_indices[-1]
        nearest_normal = self.normal_labels[nearest_idx]

        # 生成描述
        if is_anomaly:
            description = f"檢測到異常，與最近正常樣本({nearest_normal})的相似度僅為 {avg_similarity:.2%}"
        else:
            description = f"正常，與 {nearest_normal} 相似度為 {avg_similarity:.2%}"

        return AnomalyResult(
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            anomaly_type=anomaly_type,
            confidence=abs(anomaly_score - self.anomaly_threshold) / 0.5,
            description=description,
            nearest_normal=nearest_normal
        )

    def batch_detect(
        self,
        feature_vectors: np.ndarray,
        k_neighbors: int = 5
    ) -> List[AnomalyResult]:
        """
        ‹4› 批量異常檢測
        """
        results = []
        for vector in feature_vectors:
            result = self.detect(vector, k_neighbors)
            results.append(result)
        return results

    def update_threshold(self, feedback: List[Tuple[float, bool]]):
        """
        ‹5› 根據反饋更新閾值

        Args:
            feedback: [(anomaly_score, was_actually_anomaly), ...]
        """
        if not feedback:
            return

        # 收集正確分類的分數
        true_anomaly_scores = [s for s, a in feedback if a]
        true_normal_scores = [s for s, a in feedback if not a]

        if true_anomaly_scores and true_normal_scores:
            # 找出最佳分界點
            min_anomaly = min(true_anomaly_scores)
            max_normal = max(true_normal_scores)

            if min_anomaly > max_normal:
                # 可以清晰分界
                new_threshold = (min_anomaly + max_normal) / 2
            else:
                # 有重疊，保守處理
                new_threshold = np.percentile(true_anomaly_scores, 25)

            # 平滑更新
            self.anomaly_threshold = 0.7 * self.anomaly_threshold + 0.3 * new_threshold
            self.threshold_history.append(self.anomaly_threshold)

            print(f"更新異常閾值: {self.anomaly_threshold:.3f}")

    def get_statistics(self) -> Dict[str, float]:
        """
        ‹6› 獲取統計資訊
        """
        total = self.stats["total_detections"]
        return {
            "total_detections": total,
            "anomalies_detected": self.stats["anomalies_detected"],
            "anomaly_rate": self.stats["anomalies_detected"] / max(total, 1),
            "current_threshold": self.anomaly_threshold
        }


def demonstrate_anomaly_detection():
    """
    ‹1› 異常檢測示範
    """
    print("異常檢測系統示範")
    print("=" * 60)

    np.random.seed(42)

    # 初始化系統
    system = AnomalyDetectionSystem(dimension=512)

    # 添加正常樣本
    normal_classes = ["car", "truck", "pedestrian", "cyclist", "bus"]
    for cls in normal_classes:
        # 每個類別 100 個樣本
        vectors = np.random.randn(100, 512).astype(np.float32)
        # 添加類別特定的偏移
        vectors += np.random.randn(512) * 2  # 類別中心
        labels = [cls] * 100
        system.add_normal_samples(vectors, labels)

    # 測試正常樣本
    print("\n測試正常樣本:")
    print("-" * 50)

    normal_test = np.random.randn(512).astype(np.float32)
    normal_test += system.normal_vectors[0]  # 接近已知類別
    result = system.detect(normal_test)

    print(f"  是否異常: {result.is_anomaly}")
    print(f"  異常分數: {result.anomaly_score:.3f}")
    print(f"  描述: {result.description}")

    # 測試異常樣本
    print("\n測試異常樣本:")
    print("-" * 50)

    anomaly_test = np.random.randn(512).astype(np.float32) * 5  # 偏離正常分佈
    result = system.detect(anomaly_test)

    print(f"  是否異常: {result.is_anomaly}")
    print(f"  異常分數: {result.anomaly_score:.3f}")
    print(f"  異常類型: {result.anomaly_type.value if result.anomaly_type else 'N/A'}")
    print(f"  置信度: {result.confidence:.2%}")
    print(f"  描述: {result.description}")

    # 批量檢測
    print("\n批量檢測（100 個樣本）:")
    print("-" * 50)

    # 90 個正常 + 10 個異常
    normal_batch = np.random.randn(90, 512).astype(np.float32)
    anomaly_batch = np.random.randn(10, 512).astype(np.float32) * 5
    batch = np.vstack([normal_batch, anomaly_batch])
    np.random.shuffle(batch)

    results = system.batch_detect(batch)

    anomaly_count = sum(1 for r in results if r.is_anomaly)
    print(f"  檢測到的異常數: {anomaly_count}/100")

    # 統計
    print("\n系統統計:")
    stats = system.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    demonstrate_anomaly_detection()
```

---

## 12.5 完整系統整合

### 12.5.1 感知管線

```python
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

@dataclass
class SensorFrame:
    """感測器幀"""
    frame_id: int
    timestamp: float
    camera_data: np.ndarray  # 圖像數據
    lidar_points: np.ndarray  # 點雲數據
    radar_data: np.ndarray  # 雷達數據


@dataclass
class PerceptionOutput:
    """感知輸出"""
    frame_id: int
    timestamp: float
    detected_objects: List[Dict]
    scene_type: str
    scene_confidence: float
    anomalies: List[Dict]
    processing_time_ms: float


class PerceptionPipeline:
    """
    感知管線

    ‹1› 整合所有感知模組
    ‹2› 處理感測器數據流
    ‹3› 輸出統一的感知結果
    """

    def __init__(self):
        """
        ‹1› 初始化感知管線
        """
        # 初始化各子系統
        self.object_system = None  # ObjectRecognitionSystem
        self.scene_system = None   # SceneUnderstandingSystem
        self.anomaly_system = None # AnomalyDetectionSystem

        # 特徵提取器（模擬）
        self.feature_dim = 512

        # 效能監控
        self.latency_history: List[float] = []
        self.fps_target = 30

    def initialize(self):
        """
        ‹2› 初始化所有子系統
        """
        print("初始化感知管線...")

        # 這裡應該初始化各個子系統
        # self.object_system = ObjectRecognitionSystem()
        # self.scene_system = SceneUnderstandingSystem()
        # self.anomaly_system = AnomalyDetectionSystem()

        print("感知管線初始化完成")

    def extract_features(self, frame: SensorFrame) -> Dict[str, np.ndarray]:
        """
        ‹3› 提取特徵

        從感測器數據提取特徵向量
        """
        # 模擬特徵提取
        # 實際應使用 CNN/Transformer 模型

        features = {
            "object_features": np.random.randn(10, self.feature_dim).astype(np.float32),
            "scene_feature": np.random.randn(self.feature_dim * 2).astype(np.float32),
            "global_feature": np.random.randn(self.feature_dim).astype(np.float32)
        }

        return features

    def process_frame(self, frame: SensorFrame) -> PerceptionOutput:
        """
        ‹4› 處理單幀數據

        完整的感知處理流程
        """
        start_time = time.perf_counter()

        # 1. 特徵提取
        features = self.extract_features(frame)

        # 2. 物件識別
        detected_objects = self._detect_objects(features["object_features"])

        # 3. 場景理解
        scene_type, scene_confidence = self._understand_scene(features["scene_feature"])

        # 4. 異常檢測
        anomalies = self._detect_anomalies(features["global_feature"])

        # 計算處理時間
        processing_time = (time.perf_counter() - start_time) * 1000
        self.latency_history.append(processing_time)

        # 保持歷史記錄在合理範圍
        if len(self.latency_history) > 1000:
            self.latency_history.pop(0)

        return PerceptionOutput(
            frame_id=frame.frame_id,
            timestamp=frame.timestamp,
            detected_objects=detected_objects,
            scene_type=scene_type,
            scene_confidence=scene_confidence,
            anomalies=anomalies,
            processing_time_ms=processing_time
        )

    def _detect_objects(self, features: np.ndarray) -> List[Dict]:
        """檢測物件（模擬）"""
        objects = []
        for i, feat in enumerate(features):
            obj = {
                "id": i,
                "class": np.random.choice(["car", "pedestrian", "cyclist"]),
                "confidence": np.random.uniform(0.7, 0.99),
                "bbox": [np.random.rand() * 100 for _ in range(4)],
                "distance": np.random.uniform(5, 50)
            }
            objects.append(obj)
        return objects

    def _understand_scene(self, feature: np.ndarray) -> tuple:
        """理解場景（模擬）"""
        scenes = ["highway", "urban", "residential"]
        scene = np.random.choice(scenes)
        confidence = np.random.uniform(0.8, 0.99)
        return scene, confidence

    def _detect_anomalies(self, feature: np.ndarray) -> List[Dict]:
        """檢測異常（模擬）"""
        anomalies = []
        if np.random.random() < 0.1:  # 10% 異常率
            anomalies.append({
                "type": "unknown_object",
                "score": np.random.uniform(0.6, 0.9),
                "location": [np.random.rand() * 100 for _ in range(2)]
            })
        return anomalies

    def get_performance_stats(self) -> Dict[str, float]:
        """
        ‹5› 獲取效能統計
        """
        if not self.latency_history:
            return {}

        latencies = np.array(self.latency_history)
        return {
            "avg_latency_ms": np.mean(latencies),
            "p95_latency_ms": np.percentile(latencies, 95),
            "p99_latency_ms": np.percentile(latencies, 99),
            "max_latency_ms": np.max(latencies),
            "frames_processed": len(self.latency_history),
            "real_fps": 1000 / np.mean(latencies)
        }


def demonstrate_pipeline():
    """
    ‹1› 感知管線示範
    """
    print("感知管線完整示範")
    print("=" * 60)

    # 初始化管線
    pipeline = PerceptionPipeline()
    pipeline.initialize()

    # 模擬處理 100 幀
    print("\n處理 100 幀數據...")
    print("-" * 50)

    for i in range(100):
        frame = SensorFrame(
            frame_id=i,
            timestamp=time.time(),
            camera_data=np.random.rand(480, 640, 3),
            lidar_points=np.random.rand(10000, 3),
            radar_data=np.random.rand(100, 4)
        )

        output = pipeline.process_frame(frame)

        if i % 20 == 0:
            print(f"  幀 {i}: {len(output.detected_objects)} 物件, "
                  f"場景={output.scene_type}, "
                  f"延遲={output.processing_time_ms:.2f}ms")

    # 效能統計
    print("\n效能統計:")
    print("-" * 50)
    stats = pipeline.get_performance_stats()
    for key, value in stats.items():
        print(f"  {key}: {value:.2f}")


if __name__ == "__main__":
    demonstrate_pipeline()
```

---

## 12.6 本章回顧

### 核心要點

1. **物件識別**
   - 使用向量相似度快速識別已知物件
   - 支援批量處理提高吞吐量
   - 快取常見查詢減少延遲

2. **場景理解**
   - 場景模板匹配
   - 滑動窗口平滑
   - 場景轉換檢測

3. **異常檢測**
   - k-NN 距離異常檢測
   - 自適應閾值調整
   - 多類型異常分類

4. **低延遲優化**
   - 向量量化
   - 分層搜尋
   - GPU 加速

5. **系統整合**
   - 統一的感知管線
   - 多模組協作
   - 效能監控

### 最佳實踐

- 延遲目標 < 50ms（30 FPS）
- 召回率 > 99%（安全關鍵）
- 使用批量處理提高效率
- 實施多層快取策略

---

## 思考題

1. 如何在保證低延遲的同時提高物件識別的準確度？

2. 場景轉換時，系統應該如何平滑過渡？有哪些策略？

3. 異常檢測的閾值如何根據不同場景動態調整？

4. 多感測器融合時，向量搜尋應該如何設計？

5. 如何處理極端天氣條件下的感知挑戰？

---

下一章，我們將通過語意搜尋引擎的案例，展示向量搜尋在企業知識管理中的應用。
