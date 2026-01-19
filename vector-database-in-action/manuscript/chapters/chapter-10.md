# Chapter 10：系統架構設計

> 「好的架構不是一開始就設計出來的，而是在解決真實問題的過程中逐漸演化而來。」

## 學習目標

完成本章後，你將能夠：

- 理解向量搜尋系統的核心架構組件
- 設計高可用、可擴展的向量搜尋系統
- 選擇適合的部署模式和技術棧
- 實作資料流水線和索引更新策略
- 處理系統容錯和災難恢復

---

## 10.1 架構概覽

### 10.1.1 向量搜尋系統的核心組件

一個完整的向量搜尋系統通常包含以下組件：

```
                    向量搜尋系統架構
    ┌─────────────────────────────────────────────────────┐
    │                     客戶端層                        │
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
    │  │ Web App │ │ Mobile  │ │   API   │ │   SDK   │  │
    │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
    │       └───────────┼───────────┼───────────┘       │
    └───────────────────┼───────────┼───────────────────┘
                        │           │
    ┌───────────────────┼───────────┼───────────────────┐
    │                   ▼           ▼                   │
    │              ┌─────────────────────┐              │
    │              │    API Gateway      │              │
    │              │  (負載均衡/限流)    │              │
    │              └──────────┬──────────┘              │
    │                         │                         │
    │         ┌───────────────┼───────────────┐        │
    │         ▼               ▼               ▼        │
    │    ┌─────────┐    ┌─────────┐    ┌─────────┐    │
    │    │ Query   │    │ Index   │    │ Admin   │    │
    │    │ Service │    │ Service │    │ Service │    │
    │    └────┬────┘    └────┬────┘    └────┬────┘    │
    │         │              │              │          │
    │         └──────────────┼──────────────┘          │
    │                        │                         │
    │              ┌─────────┴─────────┐               │
    │              │   Vector Store    │               │
    │              │ (FAISS/Milvus/..) │               │
    │              └─────────┬─────────┘               │
    │                        │                         │
    │    ┌───────────────────┼───────────────────┐    │
    │    ▼                   ▼                   ▼    │
    │ ┌──────┐         ┌──────────┐        ┌───────┐  │
    │ │ Cache│         │ Metadata │        │Message│  │
    │ │(Redis)│        │(PostgreSQL)│      │ Queue │  │
    │ └──────┘         └──────────┘        └───────┘  │
    └─────────────────────────────────────────────────┘
```

### 10.1.2 組件職責

```python
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum

class ComponentType(Enum):
    """系統組件類型"""
    API_GATEWAY = "api_gateway"
    QUERY_SERVICE = "query_service"
    INDEX_SERVICE = "index_service"
    EMBEDDING_SERVICE = "embedding_service"
    VECTOR_STORE = "vector_store"
    METADATA_STORE = "metadata_store"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"


@dataclass
class SystemComponent:
    """
    系統組件定義

    ‹1› 描述組件職責和依賴
    """
    name: str
    component_type: ComponentType
    responsibilities: List[str]
    dependencies: List[str]
    scalability: str  # horizontal, vertical, none


# 定義系統組件
SYSTEM_COMPONENTS = [
    SystemComponent(
        name="API Gateway",
        component_type=ComponentType.API_GATEWAY,
        responsibilities=[
            "請求路由和負載均衡",
            "身份驗證和授權",
            "速率限制和流量控制",
            "請求/響應轉換",
            "API 版本管理"
        ],
        dependencies=[],
        scalability="horizontal"
    ),
    SystemComponent(
        name="Query Service",
        component_type=ComponentType.QUERY_SERVICE,
        responsibilities=[
            "接收搜尋請求",
            "查詢向量化（調用嵌入服務）",
            "執行向量搜尋",
            "結果後處理和重排序",
            "快取管理"
        ],
        dependencies=["embedding_service", "vector_store", "cache"],
        scalability="horizontal"
    ),
    SystemComponent(
        name="Index Service",
        component_type=ComponentType.INDEX_SERVICE,
        responsibilities=[
            "數據攝取和驗證",
            "向量生成（調用嵌入服務）",
            "索引建構和更新",
            "分區管理",
            "索引優化和重建"
        ],
        dependencies=["embedding_service", "vector_store", "message_queue"],
        scalability="horizontal"
    ),
    SystemComponent(
        name="Embedding Service",
        component_type=ComponentType.EMBEDDING_SERVICE,
        responsibilities=[
            "文字向量化",
            "圖片向量化",
            "模型管理和版本控制",
            "批量處理優化"
        ],
        dependencies=[],
        scalability="horizontal"
    ),
    SystemComponent(
        name="Vector Store",
        component_type=ComponentType.VECTOR_STORE,
        responsibilities=[
            "向量存儲",
            "近似最近鄰搜尋",
            "索引管理",
            "數據持久化"
        ],
        dependencies=["metadata_store"],
        scalability="horizontal"
    )
]


def print_system_architecture():
    """
    ‹1› 輸出系統架構說明
    """
    print("向量搜尋系統組件說明")
    print("=" * 70)

    for component in SYSTEM_COMPONENTS:
        print(f"\n{component.name}")
        print("-" * 40)
        print(f"類型: {component.component_type.value}")
        print(f"擴展性: {component.scalability}")
        print("職責:")
        for resp in component.responsibilities:
            print(f"  - {resp}")
        if component.dependencies:
            print(f"依賴: {', '.join(component.dependencies)}")


if __name__ == "__main__":
    print_system_architecture()
```

---

## 10.2 數據流設計

### 10.2.1 查詢流程

```python
from typing import Optional
import time
from dataclasses import dataclass
import numpy as np

@dataclass
class SearchRequest:
    """搜尋請求"""
    query_text: str
    top_k: int = 10
    filters: Optional[Dict[str, Any]] = None
    rerank: bool = False


@dataclass
class SearchResult:
    """搜尋結果"""
    doc_id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class QueryPipeline:
    """
    查詢處理流水線

    ‹1› 定義標準的查詢處理流程
    ‹2› 支援中間件擴展
    ‹3› 包含效能監控
    """

    def __init__(self):
        self.embedding_service = None
        self.vector_store = None
        self.cache = None
        self.reranker = None

        # 效能指標
        self.metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "avg_latency_ms": 0
        }

    def process(self, request: SearchRequest) -> List[SearchResult]:
        """
        ‹1› 處理搜尋請求

        流程：
        1. 檢查快取
        2. 文字向量化
        3. 向量搜尋
        4. 結果後處理
        5. 可選重排序
        6. 更新快取
        """
        start_time = time.perf_counter()
        self.metrics["total_queries"] += 1

        # Step 1: 檢查快取
        cache_key = self._generate_cache_key(request)
        cached_result = self._check_cache(cache_key)
        if cached_result:
            self.metrics["cache_hits"] += 1
            return cached_result

        # Step 2: 文字向量化
        query_vector = self._embed_query(request.query_text)

        # Step 3: 向量搜尋
        raw_results = self._vector_search(
            query_vector,
            request.top_k * 2 if request.rerank else request.top_k,
            request.filters
        )

        # Step 4: 結果後處理
        results = self._post_process(raw_results)

        # Step 5: 可選重排序
        if request.rerank:
            results = self._rerank(request.query_text, results)
            results = results[:request.top_k]

        # Step 6: 更新快取
        self._update_cache(cache_key, results)

        # 更新效能指標
        latency = (time.perf_counter() - start_time) * 1000
        self._update_metrics(latency)

        return results

    def _generate_cache_key(self, request: SearchRequest) -> str:
        """生成快取鍵"""
        import hashlib
        key_str = f"{request.query_text}:{request.top_k}:{request.filters}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _check_cache(self, key: str) -> Optional[List[SearchResult]]:
        """檢查快取"""
        if self.cache:
            return self.cache.get(key)
        return None

    def _embed_query(self, text: str) -> np.ndarray:
        """文字向量化（模擬）"""
        # 實際應調用 embedding_service
        return np.random.randn(768).astype(np.float32)

    def _vector_search(
        self,
        query_vector: np.ndarray,
        top_k: int,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """執行向量搜尋（模擬）"""
        # 實際應調用 vector_store
        return [
            {"doc_id": f"doc_{i}", "score": 0.9 - i * 0.1, "content": f"Content {i}"}
            for i in range(top_k)
        ]

    def _post_process(self, raw_results: List[Dict]) -> List[SearchResult]:
        """結果後處理"""
        return [
            SearchResult(
                doc_id=r["doc_id"],
                score=r["score"],
                content=r["content"],
                metadata={}
            )
            for r in raw_results
        ]

    def _rerank(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """重排序（模擬）"""
        # 實際應使用 cross-encoder 等模型
        return sorted(results, key=lambda x: x.score, reverse=True)

    def _update_cache(self, key: str, results: List[SearchResult]):
        """更新快取"""
        if self.cache:
            self.cache.set(key, results, ttl=300)

    def _update_metrics(self, latency: float):
        """更新效能指標"""
        n = self.metrics["total_queries"]
        self.metrics["avg_latency_ms"] = (
            (self.metrics["avg_latency_ms"] * (n - 1) + latency) / n
        )


def demonstrate_query_pipeline():
    """
    ‹1› 查詢流水線示範
    """
    print("查詢處理流水線")
    print("=" * 60)

    pipeline = QueryPipeline()

    # 模擬查詢
    request = SearchRequest(
        query_text="什麼是向量資料庫？",
        top_k=5,
        rerank=True
    )

    print(f"查詢: {request.query_text}")
    print(f"Top-K: {request.top_k}")
    print(f"重排序: {request.rerank}")
    print()

    # 執行查詢
    results = pipeline.process(request)

    print("搜尋結果:")
    print("-" * 40)
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result.doc_id}] Score: {result.score:.4f}")
        print(f"   {result.content}")
        print()

    print("效能指標:")
    for key, value in pipeline.metrics.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    demonstrate_query_pipeline()
```

### 10.2.2 索引更新流程

```python
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
import threading
from queue import Queue

class IndexUpdateType(Enum):
    """索引更新類型"""
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    REBUILD = "rebuild"


@dataclass
class IndexTask:
    """索引任務"""
    task_id: str
    update_type: IndexUpdateType
    documents: List[Dict[str, Any]]
    priority: int = 0
    created_at: float = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class IndexPipeline:
    """
    索引處理流水線

    ‹1› 支援批量處理
    ‹2› 異步索引更新
    ‹3› 增量和全量索引
    """

    def __init__(
        self,
        batch_size: int = 100,
        flush_interval: float = 5.0
    ):
        """
        ‹1› 初始化索引流水線

        Args:
            batch_size: 批次大小
            flush_interval: 刷新間隔（秒）
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self.task_queue = Queue()
        self.buffer = []
        self.buffer_lock = threading.Lock()

        self.is_running = False
        self.worker_thread = None

        # 統計
        self.stats = {
            "total_indexed": 0,
            "total_deleted": 0,
            "batches_processed": 0
        }

    def start(self):
        """
        ‹2› 啟動索引服務
        """
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        print("索引服務已啟動")

    def stop(self):
        """
        ‹3› 停止索引服務
        """
        self.is_running = False
        self._flush_buffer()
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        print("索引服務已停止")

    def submit_task(self, task: IndexTask):
        """
        ‹4› 提交索引任務
        """
        self.task_queue.put(task)
        print(f"提交任務: {task.task_id} ({task.update_type.value})")

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        ‹5› 添加文件到緩衝區
        """
        with self.buffer_lock:
            self.buffer.extend(documents)

            if len(self.buffer) >= self.batch_size:
                self._flush_buffer()

    def _worker_loop(self):
        """
        ‹6› 工作執行緒
        """
        last_flush = time.time()

        while self.is_running:
            # 處理任務佇列
            try:
                task = self.task_queue.get(timeout=1)
                self._process_task(task)
            except:
                pass

            # 定期刷新緩衝區
            if time.time() - last_flush >= self.flush_interval:
                self._flush_buffer()
                last_flush = time.time()

    def _process_task(self, task: IndexTask):
        """
        ‹7› 處理索引任務
        """
        print(f"處理任務: {task.task_id}")

        if task.update_type == IndexUpdateType.ADD:
            self._index_documents(task.documents)
        elif task.update_type == IndexUpdateType.UPDATE:
            self._update_documents(task.documents)
        elif task.update_type == IndexUpdateType.DELETE:
            self._delete_documents(task.documents)
        elif task.update_type == IndexUpdateType.REBUILD:
            self._rebuild_index()

        self.stats["batches_processed"] += 1

    def _flush_buffer(self):
        """
        ‹8› 刷新緩衝區
        """
        with self.buffer_lock:
            if self.buffer:
                documents = self.buffer.copy()
                self.buffer.clear()
                self._index_documents(documents)

    def _index_documents(self, documents: List[Dict]):
        """索引文件（模擬）"""
        print(f"索引 {len(documents)} 篇文件...")
        # 實際應：
        # 1. 生成嵌入向量
        # 2. 寫入向量存儲
        # 3. 更新元數據
        self.stats["total_indexed"] += len(documents)

    def _update_documents(self, documents: List[Dict]):
        """更新文件（模擬）"""
        print(f"更新 {len(documents)} 篇文件...")
        # 實際應：
        # 1. 刪除舊向量
        # 2. 生成新向量
        # 3. 寫入新向量

    def _delete_documents(self, documents: List[Dict]):
        """刪除文件（模擬）"""
        print(f"刪除 {len(documents)} 篇文件...")
        self.stats["total_deleted"] += len(documents)

    def _rebuild_index(self):
        """重建索引（模擬）"""
        print("重建索引...")
        # 實際應：
        # 1. 創建新索引
        # 2. 批量重新索引所有數據
        # 3. 切換到新索引
        # 4. 刪除舊索引


def demonstrate_index_pipeline():
    """
    ‹1› 索引流水線示範
    """
    print("索引處理流水線")
    print("=" * 60)

    pipeline = IndexPipeline(batch_size=10, flush_interval=2.0)
    pipeline.start()

    # 模擬添加文件
    for i in range(25):
        doc = {"id": f"doc_{i}", "content": f"Document content {i}"}
        pipeline.add_documents([doc])

    # 提交批量任務
    task = IndexTask(
        task_id="task_001",
        update_type=IndexUpdateType.ADD,
        documents=[{"id": f"batch_{i}"} for i in range(50)]
    )
    pipeline.submit_task(task)

    # 等待處理
    time.sleep(5)

    # 停止服務
    pipeline.stop()

    print("\n統計:")
    for key, value in pipeline.stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    demonstrate_index_pipeline()
```

---

## 10.3 高可用設計

### 10.3.1 複製與分片策略

```python
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import hashlib

class ReplicationStrategy(Enum):
    """複製策略"""
    NONE = "none"
    SYNC = "sync"      # 同步複製
    ASYNC = "async"    # 異步複製
    SEMI_SYNC = "semi_sync"  # 半同步


class ShardingStrategy(Enum):
    """分片策略"""
    HASH = "hash"           # 哈希分片
    RANGE = "range"         # 範圍分片
    RANDOM = "random"       # 隨機分片
    CONSISTENT_HASH = "consistent_hash"  # 一致性哈希


@dataclass
class ShardConfig:
    """分片配置"""
    num_shards: int
    replication_factor: int
    strategy: ShardingStrategy


class ShardManager:
    """
    分片管理器

    ‹1› 管理數據分片
    ‹2› 路由查詢到正確的分片
    ‹3› 處理分片的擴展和收縮
    """

    def __init__(self, config: ShardConfig):
        """
        ‹1› 初始化分片管理器
        """
        self.config = config
        self.shards: Dict[int, List[str]] = {}  # shard_id -> [replica_nodes]
        self.hash_ring: List[int] = []  # 用於一致性哈希

        self._initialize_shards()

    def _initialize_shards(self):
        """
        ‹2› 初始化分片
        """
        for shard_id in range(self.config.num_shards):
            # 每個分片有 replication_factor 個副本
            self.shards[shard_id] = [
                f"node_{shard_id}_{r}"
                for r in range(self.config.replication_factor)
            ]

        # 初始化一致性哈希環
        if self.config.strategy == ShardingStrategy.CONSISTENT_HASH:
            virtual_nodes = 150  # 每個分片的虛擬節點數
            for shard_id in range(self.config.num_shards):
                for v in range(virtual_nodes):
                    hash_val = self._hash(f"{shard_id}:{v}")
                    self.hash_ring.append((hash_val, shard_id))
            self.hash_ring.sort(key=lambda x: x[0])

    def _hash(self, key: str) -> int:
        """計算哈希值"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def get_shard(self, doc_id: str) -> int:
        """
        ‹3› 根據文件 ID 獲取分片

        Args:
            doc_id: 文件 ID

        Returns:
            分片 ID
        """
        if self.config.strategy == ShardingStrategy.HASH:
            return self._hash(doc_id) % self.config.num_shards

        elif self.config.strategy == ShardingStrategy.CONSISTENT_HASH:
            hash_val = self._hash(doc_id)
            # 二分搜尋找到第一個大於等於 hash_val 的節點
            for ring_hash, shard_id in self.hash_ring:
                if ring_hash >= hash_val:
                    return shard_id
            return self.hash_ring[0][1]  # 環形結構，回到第一個

        elif self.config.strategy == ShardingStrategy.RANDOM:
            import random
            return random.randint(0, self.config.num_shards - 1)

        else:
            raise ValueError(f"不支援的分片策略: {self.config.strategy}")

    def get_replicas(self, shard_id: int) -> List[str]:
        """
        ‹4› 獲取分片的所有副本節點
        """
        return self.shards.get(shard_id, [])

    def get_primary(self, shard_id: int) -> Optional[str]:
        """
        ‹5› 獲取分片的主節點
        """
        replicas = self.get_replicas(shard_id)
        return replicas[0] if replicas else None

    def route_query(self, query_shards: List[int] = None) -> Dict[int, str]:
        """
        ‹6› 路由查詢請求

        Returns:
            {shard_id: node} 映射
        """
        if query_shards is None:
            query_shards = list(self.shards.keys())

        routing = {}
        for shard_id in query_shards:
            replicas = self.get_replicas(shard_id)
            # 負載均衡：輪詢選擇副本
            import random
            routing[shard_id] = random.choice(replicas) if replicas else None

        return routing

    def add_shard(self) -> int:
        """
        ‹7› 添加新分片
        """
        new_shard_id = len(self.shards)
        self.shards[new_shard_id] = [
            f"node_{new_shard_id}_{r}"
            for r in range(self.config.replication_factor)
        ]
        self.config.num_shards += 1
        print(f"添加分片: {new_shard_id}")
        return new_shard_id

    def remove_shard(self, shard_id: int):
        """
        ‹8› 移除分片（需要先遷移數據）
        """
        if shard_id in self.shards:
            del self.shards[shard_id]
            self.config.num_shards -= 1
            print(f"移除分片: {shard_id}")


def demonstrate_sharding():
    """
    ‹1› 分片示範
    """
    print("分片策略示範")
    print("=" * 60)

    config = ShardConfig(
        num_shards=4,
        replication_factor=3,
        strategy=ShardingStrategy.CONSISTENT_HASH
    )

    manager = ShardManager(config)

    # 顯示分片配置
    print(f"\n分片配置:")
    print(f"  分片數: {config.num_shards}")
    print(f"  副本因子: {config.replication_factor}")
    print(f"  策略: {config.strategy.value}")

    # 顯示分片分佈
    print(f"\n分片分佈:")
    for shard_id, replicas in manager.shards.items():
        print(f"  分片 {shard_id}: {replicas}")

    # 測試路由
    print(f"\n文件路由示範:")
    test_docs = ["doc_001", "doc_002", "doc_003", "user_123", "product_456"]
    for doc_id in test_docs:
        shard_id = manager.get_shard(doc_id)
        primary = manager.get_primary(shard_id)
        print(f"  {doc_id} → 分片 {shard_id} (主: {primary})")

    # 查詢路由
    print(f"\n查詢路由:")
    routing = manager.route_query()
    for shard_id, node in routing.items():
        print(f"  分片 {shard_id} → {node}")


if __name__ == "__main__":
    demonstrate_sharding()
```

### 10.3.2 故障轉移

```python
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time
import threading

class NodeStatus(Enum):
    """節點狀態"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    RECOVERING = "recovering"


@dataclass
class Node:
    """節點信息"""
    node_id: str
    host: str
    port: int
    role: str  # primary, replica
    status: NodeStatus = NodeStatus.UNKNOWN
    last_heartbeat: float = 0


class FailoverManager:
    """
    故障轉移管理器

    ‹1› 監控節點健康
    ‹2› 自動故障轉移
    ‹3› 節點恢復處理
    """

    def __init__(
        self,
        heartbeat_interval: float = 5.0,
        failure_threshold: int = 3
    ):
        """
        ‹1› 初始化

        Args:
            heartbeat_interval: 心跳間隔（秒）
            failure_threshold: 判定故障的失敗次數
        """
        self.heartbeat_interval = heartbeat_interval
        self.failure_threshold = failure_threshold

        self.nodes: Dict[str, Node] = {}
        self.failure_counts: Dict[str, int] = {}

        self.is_running = False
        self.monitor_thread = None

        # 回調函數
        self.on_node_down: Optional[Callable] = None
        self.on_node_up: Optional[Callable] = None
        self.on_failover: Optional[Callable] = None

    def register_node(self, node: Node):
        """
        ‹2› 註冊節點
        """
        self.nodes[node.node_id] = node
        self.failure_counts[node.node_id] = 0
        print(f"註冊節點: {node.node_id} ({node.host}:{node.port})")

    def unregister_node(self, node_id: str):
        """
        ‹3› 取消註冊節點
        """
        if node_id in self.nodes:
            del self.nodes[node_id]
            del self.failure_counts[node_id]
            print(f"取消註冊: {node_id}")

    def start_monitoring(self):
        """
        ‹4› 啟動監控
        """
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("故障監控已啟動")

    def stop_monitoring(self):
        """
        ‹5› 停止監控
        """
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        print("故障監控已停止")

    def _monitor_loop(self):
        """
        ‹6› 監控循環
        """
        while self.is_running:
            for node_id, node in list(self.nodes.items()):
                is_healthy = self._check_health(node)

                if is_healthy:
                    self._handle_healthy_node(node_id, node)
                else:
                    self._handle_unhealthy_node(node_id, node)

            time.sleep(self.heartbeat_interval)

    def _check_health(self, node: Node) -> bool:
        """
        ‹7› 檢查節點健康（模擬）
        """
        # 實際應發送健康檢查請求
        import random
        return random.random() > 0.1  # 90% 健康

    def _handle_healthy_node(self, node_id: str, node: Node):
        """
        ‹8› 處理健康節點
        """
        if node.status == NodeStatus.UNHEALTHY:
            # 節點恢復
            node.status = NodeStatus.RECOVERING
            print(f"節點恢復中: {node_id}")

            if self.on_node_up:
                self.on_node_up(node_id)

        node.status = NodeStatus.HEALTHY
        node.last_heartbeat = time.time()
        self.failure_counts[node_id] = 0

    def _handle_unhealthy_node(self, node_id: str, node: Node):
        """
        ‹9› 處理不健康節點
        """
        self.failure_counts[node_id] += 1

        if self.failure_counts[node_id] >= self.failure_threshold:
            if node.status != NodeStatus.UNHEALTHY:
                node.status = NodeStatus.UNHEALTHY
                print(f"節點故障: {node_id}")

                if self.on_node_down:
                    self.on_node_down(node_id)

                # 如果是主節點，觸發故障轉移
                if node.role == "primary":
                    self._trigger_failover(node_id)

    def _trigger_failover(self, failed_node_id: str):
        """
        ‹10› 觸發故障轉移
        """
        print(f"觸發故障轉移: {failed_node_id}")

        # 找到健康的副本
        healthy_replicas = [
            (nid, node) for nid, node in self.nodes.items()
            if node.status == NodeStatus.HEALTHY and node.role == "replica"
        ]

        if healthy_replicas:
            # 選擇第一個健康副本提升為主
            new_primary_id, new_primary = healthy_replicas[0]
            new_primary.role = "primary"
            print(f"提升 {new_primary_id} 為新的主節點")

            if self.on_failover:
                self.on_failover(failed_node_id, new_primary_id)
        else:
            print("警告：沒有可用的副本進行故障轉移")


def demonstrate_failover():
    """
    ‹1› 故障轉移示範
    """
    print("故障轉移示範")
    print("=" * 60)

    manager = FailoverManager(
        heartbeat_interval=2.0,
        failure_threshold=2
    )

    # 設定回調
    manager.on_node_down = lambda nid: print(f"  [回調] 節點下線: {nid}")
    manager.on_node_up = lambda nid: print(f"  [回調] 節點上線: {nid}")
    manager.on_failover = lambda old, new: print(f"  [回調] 故障轉移: {old} → {new}")

    # 註冊節點
    nodes = [
        Node("node_0", "10.0.0.1", 19530, "primary"),
        Node("node_1", "10.0.0.2", 19530, "replica"),
        Node("node_2", "10.0.0.3", 19530, "replica"),
    ]

    for node in nodes:
        manager.register_node(node)

    # 啟動監控
    manager.start_monitoring()

    # 等待一段時間觀察
    print("\n監控中（10 秒）...")
    time.sleep(10)

    # 停止監控
    manager.stop_monitoring()

    # 顯示最終狀態
    print("\n最終節點狀態:")
    for node_id, node in manager.nodes.items():
        print(f"  {node_id}: {node.status.value} ({node.role})")


if __name__ == "__main__":
    demonstrate_failover()
```

---

## 10.4 快取策略

### 10.4.1 多層快取設計

```python
from typing import Any, Optional, Dict
from dataclasses import dataclass
from abc import ABC, abstractmethod
import time
import hashlib
from collections import OrderedDict

class CacheLayer(ABC):
    """快取層抽象介面"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = None):
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

    @abstractmethod
    def clear(self):
        pass


class LRUCache(CacheLayer):
    """
    LRU 本地快取

    ‹1› 最近最少使用淘汰策略
    ‹2› 支援 TTL
    ‹3› 線程安全
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.ttls: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None

        # 檢查 TTL
        if key in self.ttls and time.time() > self.ttls[key]:
            self.delete(key)
            return None

        # 移到末尾（最近訪問）
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key: str, value: Any, ttl: int = None):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value

        if ttl:
            self.ttls[key] = time.time() + ttl

        # 淘汰最舊的項目
        while len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            self.delete(oldest_key)

    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]
        if key in self.ttls:
            del self.ttls[key]

    def clear(self):
        self.cache.clear()
        self.ttls.clear()

    @property
    def size(self) -> int:
        return len(self.cache)


class RedisCache(CacheLayer):
    """
    Redis 分散式快取

    ‹1› 支援集群
    ‹2› 持久化
    ‹3› 高可用
    """

    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self.client = None
        # 實際應使用 redis-py
        # self.client = redis.Redis(host=host, port=port)

    def get(self, key: str) -> Optional[Any]:
        # 模擬
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        # 模擬
        pass

    def delete(self, key: str):
        pass

    def clear(self):
        pass


class MultiLevelCache:
    """
    多層快取

    ‹1› L1: 本地 LRU 快取
    ‹2› L2: Redis 分散式快取
    ‹3› 支援快取穿透防護
    """

    def __init__(
        self,
        l1_size: int = 1000,
        redis_host: str = "localhost",
        redis_port: int = 6379
    ):
        self.l1 = LRUCache(max_size=l1_size)
        self.l2 = RedisCache(host=redis_host, port=redis_port)

        # 統計
        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0
        }

    def get(self, key: str) -> Optional[Any]:
        """
        ‹1› 獲取快取值

        先查 L1，再查 L2
        """
        # 查 L1
        value = self.l1.get(key)
        if value is not None:
            self.stats["l1_hits"] += 1
            return value

        # 查 L2
        value = self.l2.get(key)
        if value is not None:
            self.stats["l2_hits"] += 1
            # 回填 L1
            self.l1.set(key, value)
            return value

        self.stats["misses"] += 1
        return None

    def set(self, key: str, value: Any, ttl: int = 300):
        """
        ‹2› 設置快取值

        同時寫入 L1 和 L2
        """
        self.l1.set(key, value, ttl)
        self.l2.set(key, value, ttl)

    def delete(self, key: str):
        """
        ‹3› 刪除快取
        """
        self.l1.delete(key)
        self.l2.delete(key)

    def get_or_load(
        self,
        key: str,
        loader: callable,
        ttl: int = 300
    ) -> Any:
        """
        ‹4› 獲取或載入

        如果快取未命中，調用 loader 載入數據
        """
        value = self.get(key)
        if value is not None:
            return value

        # 載入數據
        value = loader()

        # 快取穿透防護：即使是 None 也快取（短 TTL）
        if value is None:
            self.set(key, "__NULL__", ttl=60)
        else:
            self.set(key, value, ttl)

        return value

    def get_hit_rate(self) -> float:
        """
        ‹5› 獲取命中率
        """
        total = self.stats["l1_hits"] + self.stats["l2_hits"] + self.stats["misses"]
        if total == 0:
            return 0.0
        return (self.stats["l1_hits"] + self.stats["l2_hits"]) / total


class QueryResultCache:
    """
    查詢結果快取

    ‹1› 專門用於快取搜尋結果
    ‹2› 支援查詢指紋生成
    """

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache

    def generate_key(
        self,
        query_vector: list,
        top_k: int,
        filters: dict = None
    ) -> str:
        """
        ‹1› 生成查詢指紋
        """
        # 對向量進行量化以提高快取命中率
        quantized = [round(v, 2) for v in query_vector[:10]]  # 只用前 10 維
        key_str = f"{quantized}:{top_k}:{filters}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_results(
        self,
        query_vector: list,
        top_k: int,
        filters: dict = None
    ) -> Optional[list]:
        """
        ‹2› 獲取快取的搜尋結果
        """
        key = self.generate_key(query_vector, top_k, filters)
        return self.cache.get(f"query:{key}")

    def cache_results(
        self,
        query_vector: list,
        top_k: int,
        results: list,
        filters: dict = None,
        ttl: int = 300
    ):
        """
        ‹3› 快取搜尋結果
        """
        key = self.generate_key(query_vector, top_k, filters)
        self.cache.set(f"query:{key}", results, ttl)


def demonstrate_caching():
    """
    ‹1› 快取示範
    """
    print("多層快取示範")
    print("=" * 60)

    # 創建多層快取
    cache = MultiLevelCache(l1_size=100)

    # 模擬使用
    print("\n模擬快取操作:")

    for i in range(20):
        key = f"key_{i % 5}"  # 只有 5 個不同的 key

        # 獲取
        value = cache.get(key)
        if value is None:
            # 載入並快取
            value = f"value_{i}"
            cache.set(key, value, ttl=60)
            print(f"  MISS: {key} → 載入 {value}")
        else:
            print(f"  HIT: {key} → {value}")

    # 統計
    print(f"\n快取統計:")
    print(f"  L1 命中: {cache.stats['l1_hits']}")
    print(f"  L2 命中: {cache.stats['l2_hits']}")
    print(f"  未命中: {cache.stats['misses']}")
    print(f"  命中率: {cache.get_hit_rate():.2%}")


if __name__ == "__main__":
    demonstrate_caching()
```

---

## 10.5 部署架構

### 10.5.1 部署模式選擇

```python
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

class DeploymentMode(Enum):
    """部署模式"""
    STANDALONE = "standalone"       # 單機部署
    CLUSTER = "cluster"            # 集群部署
    KUBERNETES = "kubernetes"       # K8s 部署
    SERVERLESS = "serverless"      # 無服務器


@dataclass
class DeploymentConfig:
    """部署配置"""
    mode: DeploymentMode
    min_replicas: int
    max_replicas: int
    cpu_request: str
    memory_request: str
    storage_class: str


def deployment_guide():
    """
    ‹1› 部署模式指南
    """
    guide = """
    向量搜尋系統部署模式選擇
    ========================

    1. 單機部署 (Standalone)
    ------------------------
    適用場景：
    - 開發/測試環境
    - 數據量 < 100 萬向量
    - 低流量應用

    優點：
    - 部署簡單
    - 成本低
    - 維護簡單

    缺點：
    - 無高可用
    - 無法水平擴展
    - 單點故障風險

    2. 集群部署 (Cluster)
    ---------------------
    適用場景：
    - 生產環境
    - 數據量 100 萬 - 10 億向量
    - 中高流量應用

    優點：
    - 高可用
    - 可水平擴展
    - 故障容錯

    缺點：
    - 運維複雜
    - 成本較高
    - 需要專業知識

    3. Kubernetes 部署
    ------------------
    適用場景：
    - 雲原生環境
    - 彈性擴縮容需求
    - 微服務架構

    優點：
    - 自動化運維
    - 彈性擴縮
    - 標準化部署

    缺點：
    - K8s 學習曲線
    - 基礎設施要求

    4. 無服務器部署 (Serverless)
    ---------------------------
    適用場景：
    - 流量波動大
    - 按需計費
    - 快速上線

    優點：
    - 零運維
    - 自動擴縮
    - 按使用付費

    缺點：
    - 冷啟動延遲
    - 成本不可預測
    - 廠商鎖定
    """
    print(guide)


class KubernetesDeploymentGenerator:
    """
    Kubernetes 部署配置生成器

    ‹1› 生成 K8s 部署清單
    """

    @staticmethod
    def generate_deployment(
        name: str,
        image: str,
        replicas: int = 3,
        cpu: str = "1000m",
        memory: str = "2Gi"
    ) -> str:
        """
        ‹1› 生成 Deployment YAML
        """
        return f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  labels:
    app: {name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
      - name: {name}
        image: {image}
        resources:
          requests:
            cpu: "{cpu}"
            memory: "{memory}"
          limits:
            cpu: "{cpu}"
            memory: "{memory}"
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
"""

    @staticmethod
    def generate_hpa(
        name: str,
        min_replicas: int = 2,
        max_replicas: int = 10,
        target_cpu: int = 70
    ) -> str:
        """
        ‹2› 生成 HPA YAML
        """
        return f"""
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {name}-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {name}
  minReplicas: {min_replicas}
  maxReplicas: {max_replicas}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {target_cpu}
"""

    @staticmethod
    def generate_service(name: str, port: int = 8080) -> str:
        """
        ‹3› 生成 Service YAML
        """
        return f"""
apiVersion: v1
kind: Service
metadata:
  name: {name}
spec:
  selector:
    app: {name}
  ports:
  - port: {port}
    targetPort: {port}
  type: ClusterIP
"""


def demonstrate_deployment():
    """
    ‹1› 部署配置示範
    """
    print("Kubernetes 部署配置生成")
    print("=" * 60)

    generator = KubernetesDeploymentGenerator()

    # 生成查詢服務部署
    print("\n--- Query Service Deployment ---")
    print(generator.generate_deployment(
        name="vector-query-service",
        image="vector-search/query-service:v1.0",
        replicas=3,
        cpu="2000m",
        memory="4Gi"
    ))

    # 生成 HPA
    print("\n--- HPA ---")
    print(generator.generate_hpa(
        name="vector-query-service",
        min_replicas=3,
        max_replicas=20
    ))

    # 生成 Service
    print("\n--- Service ---")
    print(generator.generate_service("vector-query-service"))


if __name__ == "__main__":
    deployment_guide()
    demonstrate_deployment()
```

---

## 10.6 監控與告警

### 10.6.1 關鍵指標

```python
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum
import time

class MetricType(Enum):
    """指標類型"""
    COUNTER = "counter"      # 計數器（只增不減）
    GAUGE = "gauge"          # 測量值（可增可減）
    HISTOGRAM = "histogram"  # 分佈
    SUMMARY = "summary"      # 摘要


@dataclass
class Metric:
    """監控指標"""
    name: str
    type: MetricType
    description: str
    labels: List[str]
    unit: str


# 定義關鍵監控指標
KEY_METRICS = [
    # 查詢相關
    Metric("query_total", MetricType.COUNTER, "查詢總數", ["status", "method"], "requests"),
    Metric("query_latency", MetricType.HISTOGRAM, "查詢延遲", ["method"], "seconds"),
    Metric("query_qps", MetricType.GAUGE, "每秒查詢數", [], "qps"),

    # 索引相關
    Metric("index_total", MetricType.COUNTER, "索引操作總數", ["operation"], "operations"),
    Metric("index_size", MetricType.GAUGE, "索引大小", ["index_name"], "bytes"),
    Metric("vector_count", MetricType.GAUGE, "向量數量", ["collection"], "vectors"),

    # 系統資源
    Metric("cpu_usage", MetricType.GAUGE, "CPU 使用率", ["node"], "percent"),
    Metric("memory_usage", MetricType.GAUGE, "記憶體使用率", ["node"], "percent"),
    Metric("disk_usage", MetricType.GAUGE, "磁碟使用率", ["node"], "percent"),

    # 快取
    Metric("cache_hit_rate", MetricType.GAUGE, "快取命中率", ["cache_level"], "percent"),
    Metric("cache_size", MetricType.GAUGE, "快取大小", ["cache_level"], "bytes"),

    # 搜尋品質
    Metric("recall_rate", MetricType.GAUGE, "召回率", ["method"], "percent"),
    Metric("search_accuracy", MetricType.GAUGE, "搜尋準確度", ["method"], "percent"),
]


class MetricsCollector:
    """
    指標收集器

    ‹1› 收集系統指標
    ‹2› 計算衍生指標
    ‹3› 匯出到監控系統
    """

    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self.start_time = time.time()

    def record_query(self, latency: float, status: str = "success"):
        """
        ‹1› 記錄查詢指標
        """
        # 更新計數器
        key = f"query_total_{status}"
        self.metrics[key] = self.metrics.get(key, 0) + 1

        # 記錄延遲
        latencies = self.metrics.setdefault("query_latencies", [])
        latencies.append(latency)

        # 只保留最近 1000 個樣本
        if len(latencies) > 1000:
            latencies.pop(0)

    def record_index_operation(self, operation: str, count: int = 1):
        """
        ‹2› 記錄索引操作
        """
        key = f"index_total_{operation}"
        self.metrics[key] = self.metrics.get(key, 0) + count

    def get_query_metrics(self) -> Dict[str, Any]:
        """
        ‹3› 獲取查詢指標
        """
        latencies = self.metrics.get("query_latencies", [])
        if not latencies:
            return {}

        import numpy as np
        latencies = np.array(latencies)

        return {
            "total_queries": self.metrics.get("query_total_success", 0) +
                           self.metrics.get("query_total_error", 0),
            "success_rate": self.metrics.get("query_total_success", 0) /
                           max(1, self.metrics.get("query_total_success", 0) +
                               self.metrics.get("query_total_error", 0)),
            "latency_p50": np.percentile(latencies, 50),
            "latency_p95": np.percentile(latencies, 95),
            "latency_p99": np.percentile(latencies, 99),
            "qps": len(latencies) / (time.time() - self.start_time)
        }

    def export_prometheus(self) -> str:
        """
        ‹4› 匯出 Prometheus 格式
        """
        lines = []
        metrics = self.get_query_metrics()

        lines.append(f'# HELP query_total Total number of queries')
        lines.append(f'# TYPE query_total counter')
        lines.append(f'query_total{{status="success"}} {self.metrics.get("query_total_success", 0)}')
        lines.append(f'query_total{{status="error"}} {self.metrics.get("query_total_error", 0)}')

        lines.append(f'# HELP query_latency_seconds Query latency in seconds')
        lines.append(f'# TYPE query_latency_seconds summary')
        lines.append(f'query_latency_seconds{{quantile="0.5"}} {metrics.get("latency_p50", 0)}')
        lines.append(f'query_latency_seconds{{quantile="0.95"}} {metrics.get("latency_p95", 0)}')
        lines.append(f'query_latency_seconds{{quantile="0.99"}} {metrics.get("latency_p99", 0)}')

        return '\n'.join(lines)


class AlertManager:
    """
    告警管理器

    ‹1› 定義告警規則
    ‹2› 評估告警條件
    ‹3› 發送告警通知
    """

    def __init__(self):
        self.rules: List[Dict] = []
        self.active_alerts: List[Dict] = []

    def add_rule(
        self,
        name: str,
        condition: str,
        threshold: float,
        severity: str = "warning",
        duration: int = 60
    ):
        """
        ‹1› 添加告警規則
        """
        self.rules.append({
            "name": name,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "duration": duration,
            "triggered_at": None
        })

    def evaluate(self, metrics: Dict[str, Any]):
        """
        ‹2› 評估告警條件
        """
        for rule in self.rules:
            # 簡單的條件評估（實際應更複雜）
            metric_name = rule["condition"].split()[0]
            metric_value = metrics.get(metric_name, 0)

            if metric_value > rule["threshold"]:
                self._trigger_alert(rule, metric_value)
            else:
                self._resolve_alert(rule)

    def _trigger_alert(self, rule: Dict, value: float):
        """觸發告警"""
        if rule["triggered_at"] is None:
            rule["triggered_at"] = time.time()
            alert = {
                "name": rule["name"],
                "severity": rule["severity"],
                "value": value,
                "threshold": rule["threshold"],
                "timestamp": time.time()
            }
            self.active_alerts.append(alert)
            print(f"[ALERT] {rule['severity'].upper()}: {rule['name']} = {value}")

    def _resolve_alert(self, rule: Dict):
        """解決告警"""
        if rule["triggered_at"] is not None:
            rule["triggered_at"] = None
            print(f"[RESOLVED] {rule['name']}")


def demonstrate_monitoring():
    """
    ‹1› 監控示範
    """
    print("監控與告警示範")
    print("=" * 60)

    # 顯示關鍵指標
    print("\n關鍵監控指標:")
    print("-" * 50)
    for metric in KEY_METRICS[:8]:
        print(f"  {metric.name}: {metric.description} ({metric.type.value})")

    # 模擬收集指標
    collector = MetricsCollector()

    import random
    for _ in range(100):
        latency = random.uniform(0.01, 0.5)
        status = "success" if random.random() > 0.05 else "error"
        collector.record_query(latency, status)

    # 顯示指標
    print("\n收集的指標:")
    metrics = collector.get_query_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # Prometheus 格式
    print("\nPrometheus 格式:")
    print(collector.export_prometheus())

    # 告警示範
    print("\n告警規則示範:")
    alert_manager = AlertManager()
    alert_manager.add_rule(
        name="高延遲告警",
        condition="latency_p99",
        threshold=0.3,
        severity="warning"
    )
    alert_manager.add_rule(
        name="錯誤率過高",
        condition="error_rate",
        threshold=0.1,
        severity="critical"
    )

    # 評估告警
    alert_manager.evaluate(metrics)


if __name__ == "__main__":
    demonstrate_monitoring()
```

---

## 10.7 本章回顧

### 核心要點

1. **系統組件**
   - API Gateway：路由、認證、限流
   - Query Service：處理搜尋請求
   - Index Service：處理索引更新
   - Vector Store：向量存儲和搜尋

2. **數據流設計**
   - 查詢流水線：快取 → 向量化 → 搜尋 → 後處理
   - 索引流水線：批量處理、異步更新

3. **高可用設計**
   - 分片策略：哈希、範圍、一致性哈希
   - 複製策略：同步、異步、半同步
   - 故障轉移：自動檢測、自動切換

4. **快取策略**
   - 多層快取：L1 本地 + L2 分散式
   - 查詢結果快取
   - 快取穿透防護

5. **部署模式**
   - 單機：開發測試
   - 集群：生產環境
   - Kubernetes：雲原生

### 最佳實踐

- 無狀態設計便於水平擴展
- 合理的分片數量（建議 sqrt(n)）
- 快取命中率目標 > 80%
- 延遲 P99 < 100ms

---

## 思考題

1. 如何設計一個支援跨數據中心的向量搜尋系統？需要考慮哪些問題？

2. 在流量突增的情況下，系統應該如何自動擴縮容？

3. 如何實現索引的零停機更新？

4. 快取失效策略應該如何設計？主動失效還是被動失效？

5. 如何平衡搜尋延遲和搜尋精確度？

---

下一章，我們將深入探討向量搜尋系統的效能優化與監控，學習如何識別和解決效能瓶頸。
