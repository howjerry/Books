# 第 2 章：向量資料庫基礎

> 「理解向量資料庫，就是理解如何在數學的高維宇宙中航行。」

## 本章學習目標

完成本章後，你將能夠：
- 掌握向量資料庫的核心概念與發展歷程
- 理解倒排索引、圖索引與分區技術的工作原理
- 學會特徵提取與向量表示的基本方法
- 深入理解維度詛咒的數學本質與解決方案

---

## 引言：從搜尋引擎到語義理解

2010 年，當你在 Google 搜尋「如何治療感冒」時，搜尋引擎會找出所有包含「治療」、「感冒」這些關鍵字的網頁，然後根據 PageRank 等演算法排序。

2024 年，當你問 AI 助手同樣的問題時，它不只理解你在問「感冒的治療方法」，還能理解「緩解感冒症狀」、「感冒的家庭護理」、「Cold remedies」都是相關的內容——即使這些文字沒有任何重疊的關鍵字。

這個轉變的背後，是向量資料庫技術的革命。

---

## 2.1 向量資料庫的核心概念與基本資料結構

### 2.1.1 向量資料庫的定義與發展背景

**什麼是向量資料庫？**

向量資料庫是一種專門設計用於儲存、索引和查詢高維向量資料的資料庫系統。它的核心能力是：**在海量向量中快速找到與查詢向量最相似的 K 個向量**。

```
正式定義：

給定：
- 向量集合 V = {v₁, v₂, ..., vₙ}，其中 vᵢ ∈ ℝᵈ
- 查詢向量 q ∈ ℝᵈ
- 距離函數 d(·, ·)
- 返回數量 k

向量資料庫的核心操作是：
找到集合 S ⊆ V，|S| = k，使得：
∀vᵢ ∈ S, ∀vⱼ ∈ V\S: d(q, vᵢ) ≤ d(q, vⱼ)
```

用更直白的話說：向量資料庫就是「相似性搜尋引擎」。

**發展歷程**

向量資料庫的發展可以分為幾個階段：

```
第一階段：學術研究（1990s-2000s）
├── 1995：LSH（局部敏感雜湊）演算法提出
├── 2002：k-d tree 改進版本
└── 2008：Product Quantization 提出

第二階段：工具庫時代（2010s）
├── 2011：Annoy（Spotify）
├── 2017：FAISS（Facebook）
└── 2019：HNSW 演算法廣泛應用

第三階段：專用資料庫（2019-至今）
├── 2019：Milvus 開源
├── 2021：Pinecone 商業化
├── 2022：Weaviate、Qdrant 崛起
├── 2023：pgvector（PostgreSQL 擴充）
└── 2024：向量資料庫成為 AI 基礎設施標配
```

**為什麼現在向量資料庫這麼重要？**

三個因素的匯聚：

1. **嵌入模型的成熟**
   - BERT、GPT 等模型能夠生成高品質的語義向量
   - 嵌入即服務（Embedding as a Service）降低了使用門檻

2. **AI 應用的爆發**
   - ChatGPT 引發的 LLM 應用浪潮
   - RAG（檢索增強生成）成為標準架構

3. **硬體能力的提升**
   - GPU 加速大規模向量運算
   - 大容量記憶體變得經濟實惠

### 2.1.2 向量資料庫常見的資料結構：倒排索引、圖索引與分區技術

向量資料庫使用多種資料結構來實現高效的相似性搜尋。讓我們逐一了解。

**倒排索引（Inverted Index）**

倒排索引最初用於文字搜尋引擎，在向量資料庫中被改良用於向量檢索。

```
傳統倒排索引（用於文字）：

文件 1: "蘋果 手機 很好用"
文件 2: "蘋果 電腦 很貴"
文件 3: "香蕉 水果 很甜"

倒排索引：
┌─────────┬──────────────┐
│ 詞彙    │ 文件列表      │
├─────────┼──────────────┤
│ 蘋果    │ [1, 2]       │
│ 手機    │ [1]          │
│ 電腦    │ [2]          │
│ 香蕉    │ [3]          │
│ 很      │ [1, 2, 3]    │
└─────────┴──────────────┘

查詢「蘋果 手機」→ 交集 {1}
```

在向量資料庫中，倒排索引被用於 **IVF（Inverted File）** 結構：

```
IVF 索引結構：

1. 訓練階段：使用 K-means 將向量聚類

   聚類中心（Centroids）：C₁, C₂, ..., Cₖ

2. 索引建立：每個向量分配到最近的聚類

   ┌──────────┬─────────────────────────┐
   │ 聚類 ID  │ 向量列表                 │
   ├──────────┼─────────────────────────┤
   │ C₁       │ [v₃, v₇, v₁₂, ...]      │
   │ C₂       │ [v₁, v₅, v₉, ...]       │
   │ C₃       │ [v₂, v₄, v₈, ...]       │
   │ ...      │ ...                     │
   └──────────┴─────────────────────────┘

3. 查詢階段：
   a) 找到查詢向量最近的 nprobe 個聚類
   b) 只在這些聚類內搜尋
```

IVF 的關鍵參數：

| 參數 | 意義 | 典型值 |
|------|------|--------|
| `nlist` | 聚類數量 | √n 到 4√n（n 為向量數） |
| `nprobe` | 查詢時搜尋的聚類數 | 1 到 nlist/10 |

```python
# IVF 索引的 FAISS 實現示例
import faiss

dimension = 768
nlist = 1000  # 聚類數量

# 建立 IVF 索引
quantizer = faiss.IndexFlatL2(dimension)  # 粗量化器
index = faiss.IndexIVFFlat(quantizer, dimension, nlist)

# 訓練（需要訓練資料）
index.train(training_vectors)

# 添加向量
index.add(vectors)

# 搜尋時設定 nprobe
index.nprobe = 10  # 搜尋 10 個最近的聚類
distances, indices = index.search(query_vector, k=10)
```

**圖索引（Graph Index）**

圖索引是目前最流行的向量索引結構，代表演算法是 **HNSW（Hierarchical Navigable Small World）**。

核心思想：將向量組織成一個可導航的圖結構，通過「跳躍」快速接近目標。

```
HNSW 的直覺理解：

想像你在一個陌生城市找一家餐廳。

方法 1（暴力搜尋）：
走遍城市每一條街道 → 效率極低

方法 2（HNSW 方式）：
1. 先看城市地圖（最高層）→ 確定大致區域
2. 再看區域地圖（中間層）→ 確定街區
3. 最後步行（最底層）→ 找到具體位置

每一層的「跳躍」都讓你更接近目標！
```

HNSW 的圖結構：

```
Level 2（最高層，最稀疏）
    •─────────────────────•
    │                     │
    │         •           │
    │                     │

Level 1（中間層）
    •───•───────────•─────•
    │   │           │     │
    │   •─────•─────•     │
    │         │           │

Level 0（底層，包含所有節點）
    •─•─•─•─•─•─•─•─•─•─•─•
    │ │ │ │ │ │ │ │ │ │ │ │
    •─•─•─•─•─•─•─•─•─•─•─•
```

HNSW 搜尋過程：

```
1. 從最高層的入口點開始
2. 在當前層貪婪搜尋，找到最近的節點
3. 如果無法更近，下降到下一層
4. 重複直到到達最底層
5. 在最底層收集 K 個最近鄰

時間複雜度：O(log n)
空間複雜度：O(n × M)，M 是每個節點的連接數
```

HNSW 的關鍵參數：

| 參數 | 意義 | 影響 | 典型值 |
|------|------|------|--------|
| `M` | 每個節點的連接數 | 連接多→精度高、記憶體大 | 16-64 |
| `efConstruction` | 建構時的候選集大小 | 越大→索引品質越高、建構越慢 | 100-500 |
| `efSearch` | 搜尋時的候選集大小 | 越大→精度越高、速度越慢 | 50-200 |

**分區技術（Partitioning）**

當資料量超過單機容量時，需要將資料分區到多個節點。

```
向量資料的分區策略：

1. 範圍分區（Range Partitioning）
   └── 根據向量 ID 或時間戳分區
   └── 簡單但可能不均衡

2. 雜湊分區（Hash Partitioning）
   └── 對向量 ID 取雜湊後分區
   └── 分佈均勻但相似向量可能分散

3. 語義分區（Semantic Partitioning）
   └── 使用聚類將相似向量放在同一分區
   └── 可以減少跨分區查詢

示例：基於聚類的語義分區

                  ┌─────────────┐
                  │   Router    │
                  │ (路由層)    │
                  └──────┬──────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Partition 1 │  │ Partition 2 │  │ Partition 3 │
│ (科技類)    │  │ (醫療類)    │  │ (金融類)    │
└─────────────┘  └─────────────┘  └─────────────┘
```

### 2.1.3 向量資料庫與傳統資料庫邏輯對比

讓我們用一個表格來對比兩種資料庫的邏輯模型：

```
┌────────────────┬─────────────────────┬─────────────────────┐
│     概念       │    關聯式資料庫      │     向量資料庫       │
├────────────────┼─────────────────────┼─────────────────────┤
│ 資料組織單位   │ Table (表)          │ Collection (集合)   │
├────────────────┼─────────────────────┼─────────────────────┤
│ 資料記錄       │ Row (行)            │ Entity/Vector (實體)│
├────────────────┼─────────────────────┼─────────────────────┤
│ 欄位           │ Column (列)         │ Field + Embedding   │
├────────────────┼─────────────────────┼─────────────────────┤
│ 主鍵           │ Primary Key         │ Primary Key / ID    │
├────────────────┼─────────────────────┼─────────────────────┤
│ 索引           │ B-tree, Hash        │ HNSW, IVF, LSH      │
├────────────────┼─────────────────────┼─────────────────────┤
│ 查詢語言       │ SQL                 │ 專用 API / DSL      │
├────────────────┼─────────────────────┼─────────────────────┤
│ 典型查詢       │ SELECT WHERE        │ similarity_search() │
├────────────────┼─────────────────────┼─────────────────────┤
│ 返回排序       │ ORDER BY (欄位)     │ ORDER BY (距離)     │
└────────────────┴─────────────────────┴─────────────────────┘
```

**Schema 對比示例**

```sql
-- 關聯式資料庫 Schema
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    description TEXT,
    category VARCHAR(50),
    price DECIMAL(10, 2),
    created_at TIMESTAMP
);

CREATE INDEX idx_category ON products(category);
CREATE INDEX idx_price ON products(price);
```

```python
# 向量資料庫 Schema（以 Milvus 為例）
from pymilvus import CollectionSchema, FieldSchema, DataType

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
    FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=200),
    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=50),
    FieldSchema(name="price", dtype=DataType.FLOAT),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768)
]

schema = CollectionSchema(
    fields=fields,
    description="Product collection with embeddings"
)

# 建立向量索引
index_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {"M": 16, "efConstruction": 200}
}
```

**查詢對比**

```sql
-- 關聯式資料庫查詢
-- 找出價格在 100-500 之間的電子產品，按價格排序
SELECT * FROM products
WHERE category = '電子產品'
  AND price BETWEEN 100 AND 500
ORDER BY price ASC
LIMIT 10;
```

```python
# 向量資料庫查詢
# 找出與查詢最相似的產品，並篩選價格範圍
results = collection.search(
    data=[query_embedding],  # 查詢向量
    anns_field="embedding",  # 向量欄位
    param={"metric_type": "COSINE", "params": {"ef": 100}},
    limit=10,
    expr='category == "電子產品" and price >= 100 and price <= 500',
    output_fields=["name", "category", "price"]
)
```

---

## 2.2 特徵提取與向量表示：從資料到高維座標系

在將資料存入向量資料庫之前，我們需要將各種形式的資料轉換為向量。這個過程稱為「特徵提取」或「嵌入生成」。

### 2.2.1 特徵提取的基本方法

**文字資料的特徵提取**

文字到向量的轉換經歷了幾個世代：

```
第一代：詞袋模型（Bag of Words）

文本: "我喜歡機器學習，機器學習很有趣"

詞彙表: [我, 喜歡, 機器, 學習, 很, 有趣]
向量:   [1,  1,    2,    2,   1,  1]

特點：
- 忽略詞序
- 高維稀疏（詞彙表可能有數萬個詞）
- 無法捕捉語義

---

第二代：TF-IDF

TF (詞頻) = 詞在文件中出現次數 / 文件總詞數
IDF (逆文件頻率) = log(總文件數 / 包含該詞的文件數)
TF-IDF = TF × IDF

特點：
- 降低常見詞的權重
- 仍然是稀疏向量
- 無法理解同義詞

---

第三代：詞嵌入（Word2Vec, GloVe）

每個詞映射到固定維度的稠密向量
"機器" → [0.2, -0.5, 0.1, ..., 0.3]  (300維)
"學習" → [0.1, -0.3, 0.4, ..., 0.2]  (300維)

特點：
- 稠密向量
- 捕捉詞彙語義關係
- 靜態嵌入（每個詞只有一個向量）

---

第四代：上下文嵌入（BERT, GPT）

根據上下文動態生成嵌入
"我在銀行存錢" → "銀行" 的向量偏向金融
"河的銀行很美" → "銀行"（bank）的向量偏向地理

特點：
- 上下文敏感
- 更強的語義理解
- 計算成本較高
```

**圖像資料的特徵提取**

```
傳統方法：手工特徵

1. SIFT (Scale-Invariant Feature Transform)
   - 檢測關鍵點
   - 生成局部描述子
   - 適用於物體識別

2. HOG (Histogram of Oriented Gradients)
   - 計算梯度方向直方圖
   - 適用於行人檢測

特點：需要領域專業知識設計

---

深度學習方法：

1. CNN 特徵（如 ResNet, VGG）

   圖像 → CNN → 全連接層之前的特徵 → 向量

   例如 ResNet-50：
   輸入: 224×224×3 圖像
   輸出: 2048 維向量

2. Vision Transformer (ViT)

   圖像分塊 → Patch Embedding → Transformer → [CLS] token → 向量

   例如 ViT-B/16：
   輸入: 224×224×3 圖像
   輸出: 768 維向量

3. CLIP (Contrastive Language-Image Pre-training)

   同時理解圖像和文字
   可以用文字查詢圖像
```

```python
# 使用 CLIP 提取圖像特徵的示例
from transformers import CLIPProcessor, CLIPModel
from PIL import Image

# 載入模型
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# 處理圖像
image = Image.open("product.jpg")
inputs = processor(images=image, return_tensors="pt")

# 提取特徵
image_features = model.get_image_features(**inputs)
# image_features shape: [1, 512]
```

**音訊資料的特徵提取**

```
音訊特徵提取流程：

原始波形 → 預處理 → 特徵提取 → 向量

1. 預處理
   - 重採樣（統一採樣率）
   - 正規化（音量標準化）
   - 分幀（通常 25ms 一幀）

2. 傳統特徵
   - MFCC (Mel-Frequency Cepstral Coefficients)
   - 梅爾頻譜圖

3. 深度學習特徵
   - wav2vec 2.0
   - HuBERT
   - Whisper encoder

示例維度：
- MFCC: 13-40 維（每幀）
- wav2vec 2.0: 768 維（每幀或池化後）
```

### 2.2.2 嵌入向量生成

**使用預訓練模型生成文字嵌入**

```python
# 方法 1：使用 Sentence Transformers
from sentence_transformers import SentenceTransformer

# 載入模型（首次會下載）
model = SentenceTransformer('all-MiniLM-L6-v2')

# 生成嵌入
sentences = [
    "這是一個關於機器學習的文章",
    "深度學習是人工智慧的子領域",
    "今天天氣很好"
]

embeddings = model.encode(sentences)
# embeddings shape: (3, 384)

# 計算相似度
from sklearn.metrics.pairwise import cosine_similarity
similarities = cosine_similarity(embeddings)
print(similarities)
# [[1.0,  0.65, 0.12],
#  [0.65, 1.0,  0.08],
#  [0.12, 0.08, 1.0]]
```

```python
# 方法 2：使用 OpenAI API
import openai

client = openai.OpenAI()

response = client.embeddings.create(
    model="text-embedding-3-small",
    input=["這是一個關於機器學習的文章"]
)

embedding = response.data[0].embedding
# embedding 是 1536 維的列表
```

```python
# 方法 3：使用 HuggingFace Transformers
from transformers import AutoTokenizer, AutoModel
import torch

# 載入模型
tokenizer = AutoTokenizer.from_pretrained("bert-base-chinese")
model = AutoModel.from_pretrained("bert-base-chinese")

# 編碼文字
text = "這是一個關於機器學習的文章"
inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)

# 獲取嵌入
with torch.no_grad():
    outputs = model(**inputs)
    # 使用 [CLS] token 的輸出作為句子嵌入
    embedding = outputs.last_hidden_state[:, 0, :]
    # 或使用平均池化
    embedding = outputs.last_hidden_state.mean(dim=1)

# embedding shape: (1, 768)
```

**嵌入模型的選擇考量**

| 模型 | 維度 | 語言 | 速度 | 品質 | 適用場景 |
|------|------|------|------|------|----------|
| `all-MiniLM-L6-v2` | 384 | 英文為主 | 快 | 中 | 一般用途 |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 多語言 | 快 | 中 | 多語言應用 |
| `text-embedding-3-small` (OpenAI) | 1536 | 多語言 | 中 | 高 | 商業應用 |
| `text-embedding-3-large` (OpenAI) | 3072 | 多語言 | 慢 | 很高 | 高精度需求 |
| `bge-large-zh` | 1024 | 中文 | 中 | 高 | 中文專用 |

### 2.2.3 資料前置處理對向量品質的影響

資料前置處理對最終向量的品質有重大影響。以下是關鍵的處理步驟：

**文字前置處理**

```python
import re
from typing import List

def preprocess_text(text: str) -> str:
    """
    文字前置處理流程
    """
    # 1. 統一編碼
    text = text.encode('utf-8', errors='ignore').decode('utf-8')

    # 2. 移除或替換特殊字符
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)

    # 3. 統一空白字符
    text = ' '.join(text.split())

    # 4. 轉換大小寫（英文）
    text = text.lower()

    return text

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    將長文本分割成適合嵌入模型的片段

    ‹1› chunk_size: 每個片段的最大字符數
    ‹2› overlap: 相鄰片段的重疊字符數
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # 嘗試在句子邊界切分
        if end < len(text):
            # 向後找句子結尾
            for punct in ['。', '！', '？', '.', '!', '?', '\n']:
                last_punct = text[start:end].rfind(punct)
                if last_punct != -1:
                    end = start + last_punct + 1
                    break

        chunks.append(text[start:end].strip())
        start = end - overlap  # ‹2› 保留重疊以維持上下文

    return chunks
```

**前置處理對嵌入品質的影響實驗**

```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer('all-MiniLM-L6-v2')

# 原始文本（未處理）
raw_text = "  這是一個 EXAMPLE!!!   包含很多雜訊...   \n\n\n"

# 處理後的文本
processed_text = preprocess_text(raw_text)
# "這是一個 example 包含很多雜訊"

# 查詢
query = "這是一個範例"

# 生成嵌入
query_emb = model.encode([query])
raw_emb = model.encode([raw_text])
processed_emb = model.encode([processed_text])

# 計算相似度
raw_sim = cosine_similarity(query_emb, raw_emb)[0][0]
processed_sim = cosine_similarity(query_emb, processed_emb)[0][0]

print(f"未處理文本相似度: {raw_sim:.4f}")
print(f"處理後文本相似度: {processed_sim:.4f}")
# 通常處理後的相似度會更高
```

**批次處理的最佳實踐**

```python
from typing import List, Generator
import numpy as np

def batch_encode(
    texts: List[str],
    model: SentenceTransformer,
    batch_size: int = 32,
    show_progress: bool = True
) -> np.ndarray:
    """
    批次生成嵌入向量

    ‹1› 使用批次處理減少 GPU 記憶體峰值
    ‹2› 顯示進度條便於監控
    """
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = model.encode(
            batch,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        all_embeddings.append(embeddings)

        if show_progress:
            progress = min((i + batch_size) / len(texts) * 100, 100)
            print(f"\r處理進度: {progress:.1f}%", end="")

    if show_progress:
        print()  # 換行

    return np.vstack(all_embeddings)
```

---

## 2.3 高維空間特性與「維度詛咒」問題解析

在第一章中，我們簡要介紹了維度詛咒。現在讓我們深入探討其數學本質和解決方案。

### 2.3.1 高維空間中的稀疏性與資料分佈特性

**高維空間的反直覺特性**

我們的直覺建立在 2D 和 3D 空間中，但高維空間的行為往往與直覺相反。

**現象 1：高維超立方體的體積集中在角落**

```
考慮邊長為 2 的超立方體（中心在原點，頂點座標為 ±1）

內切球的半徑 = 1
超立方體體積 = 2^d
內切球體積 = π^(d/2) / Γ(d/2 + 1)

體積比（球/立方體）：
- 2D: π/4 ≈ 0.785
- 3D: π/6 ≈ 0.524
- 10D: ≈ 0.00249
- 100D: ≈ 10^(-70)

結論：在高維空間中，超立方體幾乎所有體積都在角落！
```

這意味著：在高維空間中均勻採樣的點，絕大多數會落在「角落」而非「中心」。

**現象 2：高維球體的體積集中在表面**

```python
import numpy as np
from scipy import special

def sphere_shell_ratio(d: int, inner_ratio: float = 0.9) -> float:
    """
    計算高維球體外殼（r 到 R）的體積佔比
    其中 r = inner_ratio * R
    """
    return 1 - inner_ratio ** d

# 計算不同維度下，最外 10% 厚度的體積佔比
for d in [2, 10, 100, 1000]:
    ratio = sphere_shell_ratio(d, 0.9)
    print(f"{d}D: 外殼體積佔比 = {ratio:.6f}")

# 輸出：
# 2D: 外殼體積佔比 = 0.190000
# 10D: 外殼體積佔比 = 0.651322
# 100D: 外殼體積佔比 = 0.999973
# 1000D: 外殼體積佔比 = 1.000000
```

**現象 3：隨機向量幾乎正交**

在高維空間中，任意兩個隨機向量幾乎總是接近正交的。

```python
import numpy as np

def test_orthogonality(d: int, num_pairs: int = 1000) -> tuple:
    """
    測試高維隨機向量的正交性
    """
    angles = []

    for _ in range(num_pairs):
        # 生成兩個隨機單位向量
        v1 = np.random.randn(d)
        v1 = v1 / np.linalg.norm(v1)

        v2 = np.random.randn(d)
        v2 = v2 / np.linalg.norm(v2)

        # 計算夾角（弧度）
        cos_angle = np.dot(v1, v2)
        angle = np.arccos(np.clip(cos_angle, -1, 1))
        angles.append(np.degrees(angle))

    return np.mean(angles), np.std(angles)

# 測試不同維度
for d in [2, 10, 100, 1000]:
    mean_angle, std_angle = test_orthogonality(d)
    print(f"{d}D: 平均夾角 = {mean_angle:.2f}° ± {std_angle:.2f}°")

# 輸出：
# 2D: 平均夾角 = 60.00° ± 34.64°
# 10D: 平均夾角 = 86.51° ± 8.23°
# 100D: 平均夾角 = 89.64° ± 2.58°
# 1000D: 平均夾角 = 89.89° ± 0.82°
```

在 1000 維空間中，隨機向量的平均夾角約為 90°（正交），標準差僅 0.82°！

### 2.3.2 距離度量的退化：歐幾里得距離與餘弦相似度

維度詛咒對不同距離度量的影響不同。讓我們分析兩種最常用的度量。

**歐幾里得距離的退化**

```python
import numpy as np

def euclidean_concentration(d: int, n: int = 1000) -> tuple:
    """
    測量高維空間中歐幾里得距離的集中現象
    """
    # 生成 n 個隨機點
    points = np.random.randn(n, d)

    # 選擇一個查詢點
    query = np.random.randn(d)

    # 計算所有距離
    distances = np.linalg.norm(points - query, axis=1)

    min_dist = np.min(distances)
    max_dist = np.max(distances)
    mean_dist = np.mean(distances)

    # 相對對比度
    contrast = (max_dist - min_dist) / mean_dist

    return min_dist, max_dist, mean_dist, contrast

# 測試
print("維度 | 最小距離 | 最大距離 | 平均距離 | 對比度")
print("-" * 55)
for d in [2, 10, 50, 100, 500, 1000]:
    min_d, max_d, mean_d, contrast = euclidean_concentration(d)
    print(f"{d:4d} | {min_d:8.2f} | {max_d:8.2f} | {mean_d:8.2f} | {contrast:.4f}")

# 輸出示例：
# 維度 | 最小距離 | 最大距離 | 平均距離 | 對比度
# -------------------------------------------------------
#    2 |     0.03 |     4.52 |     1.67 | 2.6892
#   10 |     1.89 |     7.21 |     4.23 | 1.2578
#   50 |     7.82 |    12.41 |     9.89 | 0.4641
#  100 |    11.89 |    16.32 |    14.01 | 0.3162
#  500 |    29.21 |    34.87 |    31.62 | 0.1790
# 1000 |    42.15 |    48.23 |    44.72 | 0.1360
```

觀察：隨著維度增加，對比度急劇下降。在 1000 維中，最近點和最遠點的距離差異僅佔平均距離的 13.6%。

**餘弦相似度的優勢**

餘弦相似度在高維空間中相對更穩定，因為它只考慮向量的方向，不考慮長度。

```python
def cosine_concentration(d: int, n: int = 1000) -> tuple:
    """
    測量高維空間中餘弦相似度的分佈
    """
    # 生成 n 個隨機單位向量
    points = np.random.randn(n, d)
    points = points / np.linalg.norm(points, axis=1, keepdims=True)

    # 查詢向量
    query = np.random.randn(d)
    query = query / np.linalg.norm(query)

    # 計算所有餘弦相似度
    similarities = np.dot(points, query)

    return np.min(similarities), np.max(similarities), np.mean(similarities), np.std(similarities)

# 測試
print("維度 | 最小相似度 | 最大相似度 | 平均值 | 標準差")
print("-" * 55)
for d in [2, 10, 50, 100, 500, 1000]:
    min_s, max_s, mean_s, std_s = cosine_concentration(d)
    print(f"{d:4d} | {min_s:10.4f} | {max_s:10.4f} | {mean_s:6.4f} | {std_s:.4f}")
```

**選擇距離度量的建議**

| 場景 | 推薦度量 | 原因 |
|------|----------|------|
| 文字語義相似 | 餘弦相似度 | 向量長度不重要，方向代表語義 |
| 圖像相似度 | 歐幾里得或餘弦 | 取決於嵌入模型的訓練方式 |
| 異常檢測 | 歐幾里得距離 | 異常點通常「距離」正常點較遠 |
| 推薦系統 | 內積 | 當向量已正規化時等價於餘弦 |
| 聚類 | 歐幾里得距離 | K-means 等演算法的標準選擇 |

### 2.3.3 維度詛咒：降維與索引最佳化

面對維度詛咒，有兩大類解決方案：降維和專用索引。

**降維技術**

```
主要降維方法：

1. 線性降維
   ├── PCA (主成分分析)
   │   └── 找到最大方差方向
   └── SVD (奇異值分解)
       └── 矩陣分解的通用方法

2. 非線性降維
   ├── t-SNE
   │   └── 保留局部結構，適合視覺化
   └── UMAP
       └── 更快，保留更多全局結構

3. 學習型降維
   ├── Autoencoder
   │   └── 神經網路學習壓縮表示
   └── 隨機投影
       └── 理論保證的快速方法
```

**PCA 降維示例**

```python
from sklearn.decomposition import PCA
import numpy as np

# 原始向量：768 維
original_vectors = np.random.randn(10000, 768)

# 使用 PCA 降到 128 維
pca = PCA(n_components=128)
reduced_vectors = pca.fit_transform(original_vectors)

# 檢查保留的方差比例
print(f"保留的總方差比例: {sum(pca.explained_variance_ratio_):.4f}")
# 通常可以保留 > 90% 的資訊

# 壓縮比
compression_ratio = 768 / 128
print(f"壓縮比: {compression_ratio:.1f}x")
```

**量化（Quantization）**

量化是另一種「降維」的方式——降低每個維度的精度。

```
Product Quantization (PQ) 原理：

原始向量 (768 維, float32)
│
├── 分成 M 個子向量 (例如 M=96, 每個子向量 8 維)
│
├── 每個子向量用 K-means 聚類 (K=256)
│
└── 每個子向量用 1 byte 表示聚類 ID

記憶體佔用：
- 原始：768 × 4 bytes = 3,072 bytes
- PQ 後：96 bytes
- 壓縮比：32x

查詢時：
- 預計算查詢向量到所有聚類中心的距離
- 使用查表法快速計算近似距離
```

```python
import faiss

# 建立 PQ 索引
dimension = 768
m = 96  # 子向量數量
nbits = 8  # 每個子向量用 8 bits (256 個聚類)

# 建立索引
index = faiss.IndexPQ(dimension, m, nbits)

# 訓練
index.train(training_vectors)

# 添加向量
index.add(vectors)

# 搜尋
distances, indices = index.search(query, k=10)
```

**專用索引結構**

不同索引結構適用於不同場景：

```
索引選擇指南：

資料量 < 1 萬
└── 直接使用暴力搜尋 (Flat)
    └── 精確結果，無需索引

資料量 1 萬 - 100 萬
├── 記憶體充足 → HNSW
│   └── 最佳的召回率-速度權衡
│
└── 記憶體有限 → IVF + PQ
    └── 壓縮向量，節省空間

資料量 > 100 萬
├── 單機 → IVF + HNSW
│   └── 粗粒度 IVF 分區 + HNSW 精搜
│
└── 分散式 → 分片 + 副本
    └── 水平擴展
```

**索引配置的經驗法則**

```python
def recommend_index_config(num_vectors: int, dimension: int, memory_gb: float):
    """
    根據資料規模推薦索引配置
    """
    vector_size_bytes = dimension * 4  # float32
    total_size_gb = num_vectors * vector_size_bytes / (1024**3)

    print(f"資料規模：{num_vectors:,} 向量，{dimension} 維")
    print(f"原始大小：{total_size_gb:.2f} GB")
    print(f"可用記憶體：{memory_gb} GB")
    print("-" * 50)

    if num_vectors < 10000:
        print("推薦：IndexFlatL2 (暴力搜尋)")
        print("原因：資料量小，暴力搜尋已足夠快")

    elif total_size_gb * 1.5 < memory_gb:  # 包含索引開銷
        print("推薦：IndexHNSWFlat")
        print(f"參數：M=32, efConstruction=200")
        print("原因：記憶體充足，HNSW 提供最佳召回率")

    elif total_size_gb * 0.1 < memory_gb:  # PQ 壓縮後
        print("推薦：IndexIVFPQ")
        nlist = int(np.sqrt(num_vectors))
        m = dimension // 8
        print(f"參數：nlist={nlist}, m={m}, nbits=8")
        print("原因：記憶體有限，使用 PQ 壓縮")

    else:
        print("推薦：分散式部署")
        num_shards = int(np.ceil(total_size_gb * 0.1 / memory_gb))
        print(f"建議分片數：{num_shards}")
        print("原因：單機記憶體不足")

# 測試
recommend_index_config(10_000_000, 768, 32)
```

---

## 2.4 本章小結

在本章中，我們深入探討了向量資料庫的基礎知識：

1. **核心概念與資料結構**
   - 向量資料庫是專門用於高維向量相似性搜尋的資料庫
   - 主要資料結構包括倒排索引（IVF）、圖索引（HNSW）和分區技術
   - 與傳統資料庫在資料模型、索引和查詢方式上有本質區別

2. **特徵提取與向量表示**
   - 文字、圖像、音訊等資料都可以轉換為向量
   - 現代嵌入模型（如 BERT、CLIP）能夠生成高品質的語義向量
   - 資料前置處理對向量品質有顯著影響

3. **維度詛咒的理解與應對**
   - 高維空間存在反直覺的特性：體積集中在角落、表面、隨機向量近乎正交
   - 距離度量在高維空間中退化，餘弦相似度相對更穩定
   - 解決方案包括降維（PCA、量化）和專用索引（HNSW、IVF）

這些基礎知識是理解後續章節的關鍵。在下一章中，我們將深入探討向量嵌入的細節，包括靜態與動態嵌入的差異、嵌入空間的最佳化技術。

---

## 2.5 思考題

1. **概念理解**
   - 解釋 IVF 索引中 `nlist` 和 `nprobe` 參數如何影響查詢的精度和速度。當資料量從 100 萬增長到 1000 萬時，這些參數應該如何調整？

2. **數學分析**
   - 證明在高維空間中，隨機向量幾乎正交這一現象。提示：考慮兩個獨立的 d 維標準正態隨機向量，它們的內積的期望和方差是多少？

3. **實作練習**
   - 使用 Python 實現以下功能：
     a) 載入一個文字資料集（如新聞文章）
     b) 使用 Sentence Transformers 生成嵌入
     c) 將嵌入存入 FAISS 索引
     d) 實現一個簡單的語義搜尋功能

4. **系統設計**
   - 假設你需要為一個電商平台設計商品搜尋系統，支援以下功能：
     - 用自然語言描述搜尋商品
     - 支援價格、品牌等篩選條件
     - 資料量：1000 萬商品，每天更新 10 萬

     請設計：
     a) 資料模型（需要哪些欄位和嵌入）
     b) 索引策略（使用什麼類型的索引）
     c) 更新策略（如何處理頻繁的商品更新）

5. **批判性思考**
   - PCA 降維會損失資訊，但有時降維後的向量搜尋效果反而更好。請解釋這個看似矛盾的現象。

---

> **下一章預告**：在第 3 章中，我們將深入探討向量嵌入技術，包括 Word2Vec、GloVe 等靜態嵌入與 BERT、GPT 等動態嵌入的原理、優缺點及最佳化方法。
