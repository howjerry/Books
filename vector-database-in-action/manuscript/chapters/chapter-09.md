# Chapter 9：Milvus 分散式向量資料庫

> 「如果 FAISS 是一把瑞士軍刀，那 Milvus 就是一個完整的工具工廠——不僅有工具，還有自動化生產線。」

## 學習目標

完成本章後，你將能夠：

- 理解 Milvus 的架構設計與核心概念
- 掌握 Milvus 的安裝、配置與基本操作
- 學會設計適合的 Schema 和索引策略
- 實作混合查詢（向量搜尋 + 標量過濾）
- 理解 Milvus 的分散式特性與高可用設計

---

## 9.1 Milvus 簡介

Milvus 是一個開源的雲原生向量資料庫，專為處理大規模向量數據設計。它建立在 FAISS、Annoy、HNSW 等成熟的向量索引庫之上，提供了完整的資料庫功能。

### 9.1.1 Milvus vs FAISS

```
                    FAISS vs Milvus 比較
    ┌──────────────────┬────────────────┬────────────────┐
    │      特性        │     FAISS      │     Milvus     │
    ├──────────────────┼────────────────┼────────────────┤
    │   類型           │   函式庫       │   資料庫       │
    │   持久化         │   手動         │   自動         │
    │   分散式         │   不支援       │   原生支援     │
    │   CRUD           │   有限         │   完整         │
    │   混合查詢       │   不支援       │   支援         │
    │   事務           │   不支援       │   支援         │
    │   高可用         │   手動實現     │   內建         │
    │   水平擴展       │   手動分片     │   自動分片     │
    └──────────────────┴────────────────┴────────────────┘
```

### 9.1.2 Milvus 架構概覽

```
                        Milvus 2.x 架構
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
    Access Layer         Coordinator          Worker Nodes
        │                     │                     │
    ┌───┴───┐           ┌─────┼─────┐         ┌─────┼─────┐
    │ Proxy │           │Root │Query│         │Query│Index│
    │       │           │Coord│Coord│         │Node │Node │
    └───────┘           │Data │     │         │Data │     │
                        │Coord│     │         │Node │     │
                        └─────┴─────┘         └─────┴─────┘
                              │
                        ┌─────┴─────┐
                        │  Storage  │
                        │ (S3/MinIO)│
                        │   etcd    │
                        │   Pulsar  │
                        └───────────┘
```

### 9.1.3 核心概念

```python
"""
Milvus 核心概念說明

‹1› Collection（集合）= 資料表
‹2› Partition（分區）= 資料分組
‹3› Segment（段）= 儲存單位
‹4› Entity（實體）= 資料行
‹5› Field（欄位）= 資料列
"""

# 概念對照表
concepts = """
┌──────────────┬──────────────┬──────────────┐
│   Milvus     │   關係型DB   │    說明      │
├──────────────┼──────────────┼──────────────┤
│ Collection   │ Table        │ 資料集合     │
│ Partition    │ Partition    │ 資料分區     │
│ Entity       │ Row          │ 單筆資料     │
│ Field        │ Column       │ 欄位定義     │
│ Schema       │ Schema       │ 結構定義     │
│ Primary Key  │ Primary Key  │ 主鍵         │
│ Index        │ Index        │ 索引         │
└──────────────┴──────────────┴──────────────┘
"""
print(concepts)
```

---

## 9.2 安裝與配置

### 9.2.1 安裝方式

```bash
# 方式 1：使用 Docker Compose（推薦開發環境）
# 下載 docker-compose 檔案
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml

# 啟動 Milvus
docker-compose up -d

# 檢查狀態
docker-compose ps

# 方式 2：使用 Helm 安裝（推薦生產環境）
helm repo add milvus https://milvus-io.github.io/milvus-helm/
helm repo update
helm install my-milvus milvus/milvus

# 方式 3：Milvus Lite（輕量版，適合測試）
pip install milvus
```

### 9.2.2 安裝 Python SDK

```bash
pip install pymilvus
```

### 9.2.3 連接 Milvus

```python
from pymilvus import connections, utility
import time

class MilvusConnection:
    """
    Milvus 連接管理器

    ‹1› 支援連接池
    ‹2› 自動重連
    ‹3› 健康檢查
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        alias: str = "default"
    ):
        """
        ‹1› 初始化連接配置

        Args:
            host: Milvus 伺服器地址
            port: 連接埠
            alias: 連接別名（支援多個連接）
        """
        self.host = host
        self.port = port
        self.alias = alias

    def connect(self, timeout: float = 10.0) -> bool:
        """
        ‹2› 建立連接

        Args:
            timeout: 連接超時時間

        Returns:
            是否連接成功
        """
        try:
            connections.connect(
                alias=self.alias,
                host=self.host,
                port=self.port,
                timeout=timeout
            )
            print(f"成功連接到 Milvus: {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"連接失敗: {e}")
            return False

    def disconnect(self):
        """
        ‹3› 斷開連接
        """
        connections.disconnect(self.alias)
        print("已斷開 Milvus 連接")

    def is_connected(self) -> bool:
        """
        ‹4› 檢查連接狀態
        """
        try:
            # 嘗試執行簡單操作來檢查連接
            utility.list_collections(using=self.alias)
            return True
        except:
            return False

    def health_check(self) -> dict:
        """
        ‹5› 健康檢查

        Returns:
            健康狀態資訊
        """
        health = {
            "connected": False,
            "server_version": None,
            "collections_count": 0
        }

        try:
            if self.is_connected():
                health["connected"] = True
                health["server_version"] = utility.get_server_version()
                health["collections_count"] = len(utility.list_collections())
        except Exception as e:
            health["error"] = str(e)

        return health


def demonstrate_connection():
    """
    ‹1› 連接示範
    """
    print("Milvus 連接示範")
    print("=" * 60)

    # 創建連接
    conn = MilvusConnection(host="localhost", port=19530)

    # 連接
    if conn.connect():
        # 健康檢查
        health = conn.health_check()
        print(f"\n健康狀態:")
        for key, value in health.items():
            print(f"  {key}: {value}")

        # 列出現有集合
        collections = utility.list_collections()
        print(f"\n現有集合: {collections}")

        # 斷開連接
        conn.disconnect()
    else:
        print("無法連接到 Milvus，請確認服務是否運行")


if __name__ == "__main__":
    demonstrate_connection()
```

---

## 9.3 Schema 設計與集合管理

### 9.3.1 定義 Schema

```python
from pymilvus import (
    connections, utility, Collection, CollectionSchema,
    FieldSchema, DataType
)
import numpy as np

class SchemaDesigner:
    """
    Milvus Schema 設計器

    ‹1› 定義欄位結構
    ‹2› 設定主鍵和向量欄位
    ‹3› 支援多種數據類型
    """

    @staticmethod
    def create_basic_schema(
        vector_dim: int,
        description: str = ""
    ) -> CollectionSchema:
        """
        ‹1› 創建基本 Schema

        包含：ID、向量
        """
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True  # 自動生成 ID
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=vector_dim
            )
        ]

        return CollectionSchema(
            fields=fields,
            description=description
        )

    @staticmethod
    def create_document_schema(
        vector_dim: int,
        max_title_length: int = 256,
        max_content_length: int = 4096
    ) -> CollectionSchema:
        """
        ‹2› 創建文件搜尋 Schema

        包含：ID、標題、內容、向量、元數據
        """
        fields = [
            # 主鍵
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True
            ),
            # 文字欄位
            FieldSchema(
                name="title",
                dtype=DataType.VARCHAR,
                max_length=max_title_length
            ),
            FieldSchema(
                name="content",
                dtype=DataType.VARCHAR,
                max_length=max_content_length
            ),
            # 向量欄位
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=vector_dim
            ),
            # 元數據欄位
            FieldSchema(
                name="category",
                dtype=DataType.VARCHAR,
                max_length=64
            ),
            FieldSchema(
                name="timestamp",
                dtype=DataType.INT64
            ),
            FieldSchema(
                name="score",
                dtype=DataType.FLOAT
            )
        ]

        return CollectionSchema(
            fields=fields,
            description="文件語意搜尋集合"
        )

    @staticmethod
    def create_multimodal_schema(
        text_vector_dim: int = 768,
        image_vector_dim: int = 512
    ) -> CollectionSchema:
        """
        ‹3› 創建多模態 Schema

        支援文字和圖片向量的混合搜尋
        """
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True
            ),
            FieldSchema(
                name="name",
                dtype=DataType.VARCHAR,
                max_length=256
            ),
            # 文字向量
            FieldSchema(
                name="text_embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=text_vector_dim
            ),
            # 圖片向量
            FieldSchema(
                name="image_embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=image_vector_dim
            ),
            # 元數據
            FieldSchema(
                name="modality",
                dtype=DataType.VARCHAR,
                max_length=32
            )
        ]

        return CollectionSchema(
            fields=fields,
            description="多模態搜尋集合"
        )


def demonstrate_schema():
    """
    ‹1› Schema 設計示範
    """
    print("Milvus Schema 設計示範")
    print("=" * 60)

    # 基本 Schema
    basic_schema = SchemaDesigner.create_basic_schema(
        vector_dim=128,
        description="基本向量搜尋"
    )
    print("\n基本 Schema:")
    for field in basic_schema.fields:
        print(f"  - {field.name}: {field.dtype}")

    # 文件 Schema
    doc_schema = SchemaDesigner.create_document_schema(
        vector_dim=768,
        max_title_length=256,
        max_content_length=4096
    )
    print("\n文件搜尋 Schema:")
    for field in doc_schema.fields:
        extra = ""
        if field.dtype == DataType.FLOAT_VECTOR:
            extra = f" (dim={field.dim})"
        elif field.dtype == DataType.VARCHAR:
            extra = f" (max_len={field.max_length})"
        print(f"  - {field.name}: {field.dtype}{extra}")

    # 多模態 Schema
    multi_schema = SchemaDesigner.create_multimodal_schema()
    print("\n多模態 Schema:")
    for field in multi_schema.fields:
        extra = ""
        if field.dtype == DataType.FLOAT_VECTOR:
            extra = f" (dim={field.dim})"
        print(f"  - {field.name}: {field.dtype}{extra}")


if __name__ == "__main__":
    demonstrate_schema()
```

### 9.3.2 集合管理

```python
class CollectionManager:
    """
    Milvus 集合管理器

    ‹1› 創建、刪除、載入集合
    ‹2› 分區管理
    ‹3› 集合統計
    """

    def __init__(self, alias: str = "default"):
        """
        ‹1› 初始化

        Args:
            alias: 連接別名
        """
        self.alias = alias

    def create_collection(
        self,
        name: str,
        schema: CollectionSchema,
        shards_num: int = 2
    ) -> Collection:
        """
        ‹2› 創建集合

        Args:
            name: 集合名稱
            schema: Schema 定義
            shards_num: 分片數量

        Returns:
            Collection 實例
        """
        if utility.has_collection(name, using=self.alias):
            print(f"集合 {name} 已存在，先刪除...")
            utility.drop_collection(name, using=self.alias)

        collection = Collection(
            name=name,
            schema=schema,
            using=self.alias,
            shards_num=shards_num
        )
        print(f"創建集合: {name}")
        return collection

    def get_collection(self, name: str) -> Collection:
        """
        ‹3› 獲取現有集合
        """
        if not utility.has_collection(name, using=self.alias):
            raise ValueError(f"集合 {name} 不存在")

        return Collection(name=name, using=self.alias)

    def list_collections(self) -> list:
        """
        ‹4› 列出所有集合
        """
        return utility.list_collections(using=self.alias)

    def drop_collection(self, name: str):
        """
        ‹5› 刪除集合
        """
        if utility.has_collection(name, using=self.alias):
            utility.drop_collection(name, using=self.alias)
            print(f"刪除集合: {name}")
        else:
            print(f"集合 {name} 不存在")

    def get_collection_stats(self, name: str) -> dict:
        """
        ‹6› 獲取集合統計資訊
        """
        collection = self.get_collection(name)
        return {
            "name": name,
            "description": collection.description,
            "num_entities": collection.num_entities,
            "schema": {
                field.name: str(field.dtype)
                for field in collection.schema.fields
            }
        }

    def create_partition(self, collection_name: str, partition_name: str):
        """
        ‹7› 創建分區
        """
        collection = self.get_collection(collection_name)
        if not collection.has_partition(partition_name):
            collection.create_partition(partition_name)
            print(f"創建分區: {collection_name}/{partition_name}")

    def list_partitions(self, collection_name: str) -> list:
        """
        ‹8› 列出分區
        """
        collection = self.get_collection(collection_name)
        return [p.name for p in collection.partitions]


def demonstrate_collection_management():
    """
    ‹1› 集合管理示範
    """
    print("Milvus 集合管理示範")
    print("=" * 60)

    # 假設已連接到 Milvus
    # connections.connect("default", host="localhost", port=19530)

    manager = CollectionManager()

    # 創建 Schema
    schema = SchemaDesigner.create_document_schema(vector_dim=768)

    # 創建集合
    collection = manager.create_collection(
        name="documents",
        schema=schema,
        shards_num=2
    )

    # 創建分區
    manager.create_partition("documents", "tech")
    manager.create_partition("documents", "business")
    manager.create_partition("documents", "news")

    # 列出分區
    partitions = manager.list_partitions("documents")
    print(f"\n分區列表: {partitions}")

    # 獲取統計
    stats = manager.get_collection_stats("documents")
    print(f"\n集合統計:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 清理
    manager.drop_collection("documents")


# if __name__ == "__main__":
#     demonstrate_collection_management()
```

---

## 9.4 數據操作

### 9.4.1 插入數據

```python
from typing import List, Dict, Any
import numpy as np

class DataOperations:
    """
    Milvus 數據操作類

    ‹1› 插入數據
    ‹2› 更新數據（透過 upsert）
    ‹3› 刪除數據
    """

    def __init__(self, collection: Collection):
        """
        ‹1› 初始化

        Args:
            collection: Milvus Collection 實例
        """
        self.collection = collection

    def insert(
        self,
        data: List[Dict[str, Any]],
        partition_name: str = None
    ) -> List[int]:
        """
        ‹2› 插入數據

        Args:
            data: 要插入的數據列表
            partition_name: 目標分區（可選）

        Returns:
            插入的實體 ID 列表
        """
        # 將 dict 列表轉換為 Milvus 需要的格式
        # {field_name: [values]}
        formatted_data = {}
        for field in self.collection.schema.fields:
            if not field.auto_id:
                formatted_data[field.name] = [
                    item.get(field.name) for item in data
                ]

        # 插入
        if partition_name:
            result = self.collection.insert(
                formatted_data,
                partition_name=partition_name
            )
        else:
            result = self.collection.insert(formatted_data)

        print(f"插入了 {len(data)} 筆數據")
        return result.primary_keys

    def insert_batch(
        self,
        data: List[Dict[str, Any]],
        batch_size: int = 1000,
        partition_name: str = None
    ) -> List[int]:
        """
        ‹3› 批量插入（大數據量時使用）

        Args:
            data: 要插入的數據列表
            batch_size: 每批次大小
            partition_name: 目標分區

        Returns:
            所有插入的實體 ID 列表
        """
        all_ids = []

        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            ids = self.insert(batch, partition_name)
            all_ids.extend(ids)
            print(f"進度: {min(i + batch_size, len(data))}/{len(data)}")

        return all_ids

    def upsert(
        self,
        data: List[Dict[str, Any]],
        partition_name: str = None
    ):
        """
        ‹4› Upsert（插入或更新）

        如果主鍵存在則更新，否則插入
        """
        formatted_data = {}
        for field in self.collection.schema.fields:
            formatted_data[field.name] = [
                item.get(field.name) for item in data
            ]

        if partition_name:
            self.collection.upsert(
                formatted_data,
                partition_name=partition_name
            )
        else:
            self.collection.upsert(formatted_data)

        print(f"Upsert 了 {len(data)} 筆數據")

    def delete(self, expr: str, partition_name: str = None):
        """
        ‹5› 刪除數據

        Args:
            expr: 刪除條件表達式
            partition_name: 目標分區
        """
        if partition_name:
            self.collection.delete(expr, partition_name=partition_name)
        else:
            self.collection.delete(expr)

        print(f"刪除符合條件的數據: {expr}")


def demonstrate_data_operations():
    """
    ‹1› 數據操作示範
    """
    print("Milvus 數據操作示範")
    print("=" * 60)

    # 準備測試數據
    np.random.seed(42)

    dimension = 768
    n_docs = 100

    documents = []
    for i in range(n_docs):
        documents.append({
            "title": f"Document {i}",
            "content": f"This is the content of document {i}...",
            "embedding": np.random.randn(dimension).tolist(),
            "category": ["tech", "business", "news"][i % 3],
            "timestamp": 1700000000 + i * 3600,
            "score": np.random.random()
        })

    print(f"準備了 {len(documents)} 篇文件")
    print(f"欄位: {list(documents[0].keys())}")

    # 以下操作需要實際連接 Milvus
    """
    # 連接
    connections.connect("default", host="localhost", port=19530)

    # 創建集合
    schema = SchemaDesigner.create_document_schema(vector_dim=dimension)
    collection = Collection(
        name="demo_documents",
        schema=schema
    )

    # 創建數據操作實例
    ops = DataOperations(collection)

    # 批量插入
    ids = ops.insert_batch(documents, batch_size=50)
    print(f"插入的 ID: {ids[:5]}...")

    # Upsert 示範
    updated_docs = documents[:5]
    for doc in updated_docs:
        doc["score"] = 1.0  # 更新分數

    ops.upsert(updated_docs)

    # 刪除示範
    ops.delete("score < 0.2")

    # 清理
    utility.drop_collection("demo_documents")
    """


if __name__ == "__main__":
    demonstrate_data_operations()
```

---

## 9.5 索引與搜尋

### 9.5.1 創建索引

```python
class IndexManager:
    """
    Milvus 索引管理器

    ‹1› 支援多種索引類型
    ‹2› 自動選擇最佳索引
    ‹3› 索引參數優化
    """

    # 支援的索引類型
    INDEX_TYPES = {
        "FLAT": {
            "description": "暴力搜尋，100% 精確",
            "params": {},
            "search_params": {"metric_type": "L2"}
        },
        "IVF_FLAT": {
            "description": "倒排檔案 + 精確搜尋",
            "params": {"nlist": 128},
            "search_params": {"nprobe": 10}
        },
        "IVF_SQ8": {
            "description": "倒排檔案 + 標量量化",
            "params": {"nlist": 128},
            "search_params": {"nprobe": 10}
        },
        "IVF_PQ": {
            "description": "倒排檔案 + 乘積量化",
            "params": {"nlist": 128, "m": 8, "nbits": 8},
            "search_params": {"nprobe": 10}
        },
        "HNSW": {
            "description": "分層可導航小世界圖",
            "params": {"M": 16, "efConstruction": 200},
            "search_params": {"ef": 64}
        },
        "ANNOY": {
            "description": "近似最近鄰（Spotify）",
            "params": {"n_trees": 8},
            "search_params": {"search_k": -1}
        },
        "AUTOINDEX": {
            "description": "自動選擇最佳索引",
            "params": {},
            "search_params": {}
        }
    }

    def __init__(self, collection: Collection):
        """
        ‹1› 初始化
        """
        self.collection = collection

    def create_index(
        self,
        field_name: str,
        index_type: str = "IVF_FLAT",
        metric_type: str = "L2",
        params: dict = None
    ):
        """
        ‹2› 創建向量索引

        Args:
            field_name: 向量欄位名稱
            index_type: 索引類型
            metric_type: 距離度量（L2, IP, COSINE）
            params: 索引參數（覆蓋默認值）
        """
        if index_type not in self.INDEX_TYPES:
            raise ValueError(f"不支援的索引類型: {index_type}")

        # 合併默認參數和自定義參數
        default_params = self.INDEX_TYPES[index_type]["params"].copy()
        if params:
            default_params.update(params)

        index_params = {
            "index_type": index_type,
            "metric_type": metric_type,
            "params": default_params
        }

        print(f"創建索引: {index_type}")
        print(f"  欄位: {field_name}")
        print(f"  度量: {metric_type}")
        print(f"  參數: {default_params}")

        self.collection.create_index(
            field_name=field_name,
            index_params=index_params
        )
        print("索引創建完成")

    def create_scalar_index(self, field_name: str):
        """
        ‹3› 創建標量索引

        用於加速過濾查詢
        """
        self.collection.create_index(
            field_name=field_name,
            index_name=f"idx_{field_name}"
        )
        print(f"創建標量索引: {field_name}")

    def drop_index(self, field_name: str):
        """
        ‹4› 刪除索引
        """
        self.collection.drop_index(field_name=field_name)
        print(f"刪除索引: {field_name}")

    def get_index_info(self) -> list:
        """
        ‹5› 獲取索引資訊
        """
        return self.collection.indexes

    @staticmethod
    def recommend_index(n_vectors: int, dimension: int) -> str:
        """
        ‹6› 推薦索引類型

        根據數據規模自動推薦
        """
        if n_vectors < 10000:
            return "FLAT"
        elif n_vectors < 100000:
            return "IVF_FLAT"
        elif n_vectors < 1000000:
            return "HNSW"
        else:
            return "IVF_PQ"

    @staticmethod
    def calculate_nlist(n_vectors: int) -> int:
        """
        ‹7› 計算建議的 nlist 值
        """
        return min(int(np.sqrt(n_vectors) * 4), n_vectors // 30)


def demonstrate_index():
    """
    ‹1› 索引示範
    """
    print("Milvus 索引示範")
    print("=" * 60)

    # 列出所有支援的索引類型
    print("\n支援的索引類型:")
    print("-" * 60)
    for name, info in IndexManager.INDEX_TYPES.items():
        print(f"{name}:")
        print(f"  說明: {info['description']}")
        print(f"  參數: {info['params']}")
        print()

    # 推薦索引
    test_cases = [
        (1000, 128),
        (50000, 768),
        (500000, 256),
        (5000000, 512)
    ]

    print("索引推薦:")
    print("-" * 40)
    for n, dim in test_cases:
        recommended = IndexManager.recommend_index(n, dim)
        nlist = IndexManager.calculate_nlist(n)
        print(f"  {n:>10,} 向量, {dim} 維 → {recommended} (nlist={nlist})")


if __name__ == "__main__":
    demonstrate_index()
```

### 9.5.2 向量搜尋

```python
from typing import List, Dict, Optional
import numpy as np

class SearchEngine:
    """
    Milvus 搜尋引擎

    ‹1› 向量相似性搜尋
    ‹2› 混合查詢（向量 + 過濾）
    ‹3› 範圍搜尋
    """

    def __init__(self, collection: Collection):
        """
        ‹1› 初始化
        """
        self.collection = collection

    def load(self):
        """
        ‹2› 載入集合到記憶體

        搜尋前必須先載入
        """
        self.collection.load()
        print(f"集合 {self.collection.name} 已載入")

    def release(self):
        """
        ‹3› 釋放集合記憶體
        """
        self.collection.release()
        print(f"集合 {self.collection.name} 已釋放")

    def search(
        self,
        query_vectors: np.ndarray,
        vector_field: str,
        top_k: int = 10,
        metric_type: str = "L2",
        search_params: dict = None,
        output_fields: List[str] = None,
        filter_expr: str = None,
        partition_names: List[str] = None
    ) -> list:
        """
        ‹4› 執行向量搜尋

        Args:
            query_vectors: 查詢向量
            vector_field: 向量欄位名稱
            top_k: 返回數量
            metric_type: 距離度量
            search_params: 搜尋參數
            output_fields: 要返回的欄位
            filter_expr: 過濾表達式
            partition_names: 搜尋的分區

        Returns:
            搜尋結果列表
        """
        # 確保查詢向量是 2D
        if query_vectors.ndim == 1:
            query_vectors = query_vectors.reshape(1, -1)

        # 默認搜尋參數
        if search_params is None:
            search_params = {"metric_type": metric_type, "params": {"nprobe": 10}}

        # 執行搜尋
        results = self.collection.search(
            data=query_vectors.tolist(),
            anns_field=vector_field,
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=output_fields,
            partition_names=partition_names
        )

        return results

    def search_with_filter(
        self,
        query_vector: np.ndarray,
        vector_field: str,
        filter_conditions: Dict[str, any],
        top_k: int = 10
    ) -> list:
        """
        ‹5› 帶過濾條件的搜尋

        Args:
            query_vector: 查詢向量
            vector_field: 向量欄位
            filter_conditions: 過濾條件字典
            top_k: 返回數量

        Returns:
            過濾後的搜尋結果
        """
        # 構建過濾表達式
        expr_parts = []

        for field, condition in filter_conditions.items():
            if isinstance(condition, tuple):
                # 範圍條件 (min, max)
                min_val, max_val = condition
                if min_val is not None:
                    expr_parts.append(f"{field} >= {min_val}")
                if max_val is not None:
                    expr_parts.append(f"{field} <= {max_val}")
            elif isinstance(condition, list):
                # IN 條件
                values = ", ".join([f'"{v}"' if isinstance(v, str) else str(v)
                                   for v in condition])
                expr_parts.append(f"{field} in [{values}]")
            elif isinstance(condition, str):
                # 相等條件
                expr_parts.append(f'{field} == "{condition}"')
            else:
                # 數值相等
                expr_parts.append(f"{field} == {condition}")

        filter_expr = " and ".join(expr_parts) if expr_parts else None

        print(f"過濾表達式: {filter_expr}")

        return self.search(
            query_vectors=query_vector,
            vector_field=vector_field,
            top_k=top_k,
            filter_expr=filter_expr
        )

    def hybrid_search(
        self,
        query_vector: np.ndarray,
        vector_field: str,
        text_query: str,
        text_field: str,
        top_k: int = 10,
        alpha: float = 0.5
    ) -> list:
        """
        ‹6› 混合搜尋（向量 + 文字）

        結合向量相似性和文字匹配的搜尋

        Args:
            query_vector: 查詢向量
            vector_field: 向量欄位
            text_query: 文字查詢
            text_field: 文字欄位
            top_k: 返回數量
            alpha: 向量權重（0-1）

        Returns:
            混合排序的結果
        """
        # 向量搜尋
        vector_results = self.search(
            query_vectors=query_vector,
            vector_field=vector_field,
            top_k=top_k * 2  # 取更多結果用於重排序
        )

        # 文字過濾（簡單的包含匹配）
        filter_expr = f'{text_field} like "%{text_query}%"'

        text_results = self.search(
            query_vectors=query_vector,
            vector_field=vector_field,
            top_k=top_k * 2,
            filter_expr=filter_expr
        )

        # 合併和重排序（這裡簡化處理）
        # 實際應用中可能需要更複雜的融合策略
        return vector_results[:top_k]


def demonstrate_search():
    """
    ‹1› 搜尋示範
    """
    print("Milvus 搜尋示範")
    print("=" * 60)

    # 模擬搜尋結果展示
    dimension = 768
    np.random.seed(42)

    # 模擬查詢向量
    query = np.random.randn(dimension).astype(np.float32)

    print(f"查詢向量維度: {dimension}")
    print(f"查詢向量範圍: [{query.min():.3f}, {query.max():.3f}]")

    # 展示過濾表達式語法
    print("\n過濾表達式語法示範:")
    print("-" * 40)

    expressions = [
        ('category == "tech"', '類別等於 tech'),
        ('score > 0.8', '分數大於 0.8'),
        ('timestamp >= 1700000000', '時間戳大於等於指定值'),
        ('category in ["tech", "business"]', '類別在列表中'),
        ('score > 0.5 and category == "tech"', '組合條件'),
        ('title like "AI%"', '標題以 AI 開頭'),
    ]

    for expr, desc in expressions:
        print(f"  {expr}")
        print(f"    → {desc}")
        print()


if __name__ == "__main__":
    demonstrate_search()
```

---

## 9.6 實戰：構建完整的語意搜尋系統

```python
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime

class SemanticSearchSystem:
    """
    完整的語意搜尋系統

    ‹1› 文件管理
    ‹2› 向量索引
    ‹3› 混合搜尋
    ‹4› 結果重排序
    """

    def __init__(
        self,
        collection_name: str,
        dimension: int = 768,
        host: str = "localhost",
        port: int = 19530
    ):
        """
        ‹1› 初始化搜尋系統
        """
        self.collection_name = collection_name
        self.dimension = dimension
        self.host = host
        self.port = port

        self.collection = None
        self.is_loaded = False

    def connect(self):
        """
        ‹2› 連接到 Milvus
        """
        connections.connect("default", host=self.host, port=self.port)
        print(f"已連接到 Milvus: {self.host}:{self.port}")

    def initialize(self):
        """
        ‹3› 初始化集合和索引
        """
        # 定義 Schema
        schema = CollectionSchema(
            fields=[
                FieldSchema(name="id", dtype=DataType.INT64,
                           is_primary=True, auto_id=True),
                FieldSchema(name="doc_id", dtype=DataType.VARCHAR,
                           max_length=64),
                FieldSchema(name="title", dtype=DataType.VARCHAR,
                           max_length=512),
                FieldSchema(name="content", dtype=DataType.VARCHAR,
                           max_length=8192),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR,
                           dim=self.dimension),
                FieldSchema(name="category", dtype=DataType.VARCHAR,
                           max_length=64),
                FieldSchema(name="created_at", dtype=DataType.INT64),
                FieldSchema(name="relevance_score", dtype=DataType.FLOAT),
            ],
            description="語意搜尋文件集合"
        )

        # 創建或獲取集合
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            print(f"使用現有集合: {self.collection_name}")
        else:
            self.collection = Collection(
                name=self.collection_name,
                schema=schema,
                shards_num=2
            )
            print(f"創建新集合: {self.collection_name}")

            # 創建索引
            self._create_indexes()

    def _create_indexes(self):
        """
        ‹4› 創建索引
        """
        # 向量索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128}
        }
        self.collection.create_index("embedding", index_params)
        print("創建向量索引: IVF_FLAT")

        # 標量索引
        self.collection.create_index("category")
        self.collection.create_index("created_at")
        print("創建標量索引: category, created_at")

    def load(self):
        """
        ‹5› 載入集合
        """
        if not self.is_loaded:
            self.collection.load()
            self.is_loaded = True
            print("集合已載入到記憶體")

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: np.ndarray
    ) -> List[int]:
        """
        ‹6› 添加文件

        Args:
            documents: 文件列表，每個包含 doc_id, title, content, category
            embeddings: 對應的向量矩陣

        Returns:
            插入的 ID 列表
        """
        # 正規化向量（用於 COSINE 度量）
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        normalized_embeddings = embeddings / norms

        # 準備數據
        data = []
        for i, doc in enumerate(documents):
            data.append({
                "doc_id": doc.get("doc_id", f"doc_{i}"),
                "title": doc.get("title", ""),
                "content": doc.get("content", ""),
                "embedding": normalized_embeddings[i].tolist(),
                "category": doc.get("category", "general"),
                "created_at": doc.get("created_at", int(datetime.now().timestamp())),
                "relevance_score": doc.get("relevance_score", 0.0)
            })

        # 轉換格式
        insert_data = {
            field: [d[field] for d in data]
            for field in data[0].keys()
        }

        result = self.collection.insert(insert_data)
        print(f"添加了 {len(documents)} 篇文件")

        return result.primary_keys

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        category: Optional[str] = None,
        time_range: Optional[tuple] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        ‹7› 搜尋文件

        Args:
            query_embedding: 查詢向量
            top_k: 返回數量
            category: 類別過濾
            time_range: 時間範圍 (start, end)
            min_score: 最低相關性分數

        Returns:
            搜尋結果列表
        """
        self.load()

        # 正規化查詢向量
        query_embedding = query_embedding.reshape(1, -1)
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm

        # 構建過濾表達式
        filters = []
        if category:
            filters.append(f'category == "{category}"')
        if time_range:
            start, end = time_range
            if start:
                filters.append(f"created_at >= {start}")
            if end:
                filters.append(f"created_at <= {end}")
        if min_score > 0:
            filters.append(f"relevance_score >= {min_score}")

        filter_expr = " and ".join(filters) if filters else None

        # 搜尋參數
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 16}
        }

        # 執行搜尋
        results = self.collection.search(
            data=query_embedding.tolist(),
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["doc_id", "title", "content", "category",
                          "created_at", "relevance_score"]
        )

        # 整理結果
        formatted_results = []
        for hits in results:
            for hit in hits:
                formatted_results.append({
                    "id": hit.id,
                    "doc_id": hit.entity.get("doc_id"),
                    "title": hit.entity.get("title"),
                    "content": hit.entity.get("content"),
                    "category": hit.entity.get("category"),
                    "created_at": hit.entity.get("created_at"),
                    "relevance_score": hit.entity.get("relevance_score"),
                    "similarity": hit.score  # COSINE 相似度
                })

        return formatted_results

    def delete_documents(self, doc_ids: List[str]):
        """
        ‹8› 刪除文件
        """
        ids_str = ", ".join([f'"{id}"' for id in doc_ids])
        expr = f"doc_id in [{ids_str}]"
        self.collection.delete(expr)
        print(f"刪除了 {len(doc_ids)} 篇文件")

    def get_statistics(self) -> Dict[str, Any]:
        """
        ‹9› 獲取統計資訊
        """
        return {
            "collection_name": self.collection_name,
            "num_entities": self.collection.num_entities,
            "dimension": self.dimension,
            "indexes": [str(idx) for idx in self.collection.indexes]
        }

    def close(self):
        """
        ‹10› 關閉連接
        """
        if self.is_loaded:
            self.collection.release()
        connections.disconnect("default")
        print("已斷開連接")


def demonstrate_complete_system():
    """
    ‹1› 完整系統示範
    """
    print("完整語意搜尋系統示範")
    print("=" * 60)

    # 模擬文件數據
    documents = [
        {
            "doc_id": "doc_001",
            "title": "深度學習入門指南",
            "content": "深度學習是機器學習的一個分支，使用多層神經網路...",
            "category": "tech"
        },
        {
            "doc_id": "doc_002",
            "title": "自然語言處理最新進展",
            "content": "NLP 領域近年來取得了顯著進展，尤其是 Transformer...",
            "category": "tech"
        },
        {
            "doc_id": "doc_003",
            "title": "企業數位轉型策略",
            "content": "數位轉型已成為企業競爭的關鍵，需要從技術、流程...",
            "category": "business"
        },
        {
            "doc_id": "doc_004",
            "title": "向量資料庫應用實戰",
            "content": "向量資料庫是處理非結構化數據的新興技術...",
            "category": "tech"
        },
        {
            "doc_id": "doc_005",
            "title": "AI 驅動的推薦系統",
            "content": "現代推薦系統結合協同過濾和深度學習技術...",
            "category": "tech"
        }
    ]

    # 模擬嵌入向量
    dimension = 768
    np.random.seed(42)
    embeddings = np.random.randn(len(documents), dimension).astype(np.float32)

    print(f"準備了 {len(documents)} 篇文件")
    print(f"向量維度: {dimension}")

    # 模擬搜尋
    query_embedding = np.random.randn(dimension).astype(np.float32)

    print("\n模擬搜尋結果:")
    print("-" * 40)
    for i, doc in enumerate(documents[:3]):
        similarity = np.random.random() * 0.3 + 0.7  # 模擬相似度
        print(f"{i+1}. [{doc['category']}] {doc['title']}")
        print(f"   相似度: {similarity:.4f}")
        print()

    print("\n實際使用時需要：")
    print("1. 啟動 Milvus 服務")
    print("2. 使用真實的嵌入模型生成向量")
    print("3. 執行 system.connect() 和 system.initialize()")


if __name__ == "__main__":
    demonstrate_complete_system()
```

---

## 9.7 進階主題

### 9.7.1 分區策略

```python
class PartitionStrategy:
    """
    Milvus 分區策略

    ‹1› 按時間分區
    ‹2› 按類別分區
    ‹3› 動態分區管理
    """

    @staticmethod
    def time_based_partition(collection: Collection, timestamp: int) -> str:
        """
        ‹1› 基於時間的分區策略

        按月份創建分區
        """
        from datetime import datetime

        dt = datetime.fromtimestamp(timestamp)
        partition_name = f"p_{dt.year}_{dt.month:02d}"

        if not collection.has_partition(partition_name):
            collection.create_partition(partition_name)
            print(f"創建時間分區: {partition_name}")

        return partition_name

    @staticmethod
    def category_based_partition(collection: Collection, category: str) -> str:
        """
        ‹2› 基於類別的分區策略
        """
        partition_name = f"p_{category.lower().replace(' ', '_')}"

        if not collection.has_partition(partition_name):
            collection.create_partition(partition_name)
            print(f"創建類別分區: {partition_name}")

        return partition_name

    @staticmethod
    def cleanup_old_partitions(
        collection: Collection,
        retention_days: int = 90
    ):
        """
        ‹3› 清理過期分區

        刪除超過保留期限的時間分區
        """
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=retention_days)
        cutoff_str = f"p_{cutoff.year}_{cutoff.month:02d}"

        for partition in collection.partitions:
            if partition.name.startswith("p_") and partition.name < cutoff_str:
                collection.drop_partition(partition.name)
                print(f"刪除過期分區: {partition.name}")


def demonstrate_partition_strategy():
    """
    ‹1› 分區策略示範
    """
    print("Milvus 分區策略示範")
    print("=" * 60)

    print("\n分區策略選擇指南:")
    print("-" * 40)

    strategies = [
        ("時間分區", "按月/週/日分區", "日誌數據、時間序列"),
        ("類別分區", "按業務類別分區", "多租戶、產品分類"),
        ("地理分區", "按地區分區", "全球化應用"),
        ("混合分區", "多維度分區", "複雜業務場景"),
    ]

    for name, desc, use_case in strategies:
        print(f"\n{name}:")
        print(f"  說明: {desc}")
        print(f"  適用: {use_case}")


if __name__ == "__main__":
    demonstrate_partition_strategy()
```

### 9.7.2 效能優化

```python
class PerformanceOptimizer:
    """
    Milvus 效能優化器

    ‹1› 批量操作優化
    ‹2› 索引參數調優
    ‹3› 記憶體管理
    """

    @staticmethod
    def optimize_insert(batch_size: int = 10000) -> dict:
        """
        ‹1› 插入優化建議
        """
        return {
            "batch_size": batch_size,
            "tips": [
                "使用批量插入，每批 1000-10000 筆",
                "預先將數據轉換為 float32",
                "使用異步插入處理大量數據",
                "考慮分區插入減少鎖競爭"
            ]
        }

    @staticmethod
    def optimize_search(n_vectors: int) -> dict:
        """
        ‹2› 搜尋優化建議
        """
        recommendations = {
            "index_type": "IVF_FLAT" if n_vectors < 1000000 else "IVF_PQ",
            "nlist": min(int(np.sqrt(n_vectors) * 4), 4096),
            "nprobe": 10,  # 可根據精確度需求調整
            "tips": [
                "預載入常用分區",
                "使用向量正規化提升 COSINE 效能",
                "合理設置 nprobe 平衡精確度和速度",
                "考慮使用 GPU 加速大規模搜尋"
            ]
        }
        return recommendations

    @staticmethod
    def memory_estimation(
        n_vectors: int,
        dimension: int,
        index_type: str = "IVF_FLAT"
    ) -> dict:
        """
        ‹3› 記憶體估算
        """
        # 原始向量大小
        raw_size = n_vectors * dimension * 4  # float32 = 4 bytes

        # 索引額外開銷（近似值）
        index_overhead = {
            "FLAT": 1.0,
            "IVF_FLAT": 1.05,
            "IVF_PQ": 0.1,  # PQ 壓縮
            "HNSW": 1.5,  # 圖結構開銷
        }

        multiplier = index_overhead.get(index_type, 1.0)
        estimated_size = raw_size * multiplier

        return {
            "raw_size_mb": raw_size / (1024 * 1024),
            "estimated_size_mb": estimated_size / (1024 * 1024),
            "index_type": index_type,
            "compression_ratio": 1 / multiplier
        }


def demonstrate_optimization():
    """
    ‹1› 效能優化示範
    """
    print("Milvus 效能優化指南")
    print("=" * 60)

    # 記憶體估算
    test_cases = [
        (100000, 768, "FLAT"),
        (100000, 768, "IVF_FLAT"),
        (100000, 768, "IVF_PQ"),
        (1000000, 768, "IVF_PQ"),
        (10000000, 768, "IVF_PQ"),
    ]

    print("\n記憶體估算:")
    print(f"{'向量數':<12} {'維度':<8} {'索引類型':<12} {'原始大小':<12} {'估計大小':<12}")
    print("-" * 60)

    for n, dim, idx_type in test_cases:
        est = PerformanceOptimizer.memory_estimation(n, dim, idx_type)
        print(f"{n:<12,} {dim:<8} {idx_type:<12} "
              f"{est['raw_size_mb']:<12.1f} {est['estimated_size_mb']:<12.1f}")

    # 搜尋優化
    print("\n搜尋優化建議（100 萬向量）:")
    rec = PerformanceOptimizer.optimize_search(1000000)
    print(f"  推薦索引: {rec['index_type']}")
    print(f"  nlist: {rec['nlist']}")
    print(f"  nprobe: {rec['nprobe']}")
    print("  提示:")
    for tip in rec['tips']:
        print(f"    - {tip}")


if __name__ == "__main__":
    demonstrate_optimization()
```

---

## 9.8 本章回顧

### 核心要點

1. **Milvus 架構**
   - 雲原生分散式設計
   - 存儲計算分離
   - 支援水平擴展

2. **數據模型**
   - Collection = 表
   - Partition = 分區
   - Entity = 行
   - Field = 列

3. **索引類型**
   - FLAT：精確搜尋
   - IVF_FLAT：平衡選擇
   - IVF_PQ：大規模低記憶體
   - HNSW：高速搜尋

4. **混合查詢**
   - 向量搜尋 + 標量過濾
   - 支援複雜的過濾表達式
   - 分區加速查詢

### 最佳實踐

- 根據數據規模選擇索引類型
- 合理設計分區策略
- 預載入常用數據
- 監控效能指標

---

## 思考題

1. Milvus 的存儲計算分離架構有什麼優勢和劣勢？

2. 如何設計一個支援多語言的語意搜尋系統？需要考慮哪些因素？

3. 在什麼場景下應該使用分區？分區的數量應該如何決定？

4. 如何實現向量數據的增量更新？有哪些挑戰？

5. 比較 Milvus、Pinecone 和 Weaviate，它們各有什麼優劣？

---

下一章，我們將學習如何設計完整的向量搜尋系統架構，包括高可用、負載均衡和監控等生產環境必備的要素。
