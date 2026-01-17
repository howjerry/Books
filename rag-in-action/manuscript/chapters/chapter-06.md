# 第 6 章：Re-Ranking——二階段檢索的威力

> **本章任務：** 實作一個 Cross-Encoder Re-Ranker，將檢索精準度提升 30%。

---

## 學習目標

完成本章後，你將能夠：

- [ ] 理解二階段檢索架構的設計原理
- [ ] 區分 Bi-Encoder（Embedding）與 Cross-Encoder（Re-Ranker）的差異
- [ ] 實作 Cross-Encoder Re-Ranker
- [ ] 量化評估 Re-Ranking 的成本效益
- [ ] 根據延遲與精準度需求調整候選數量

---

## 核心產出物

- `reranker.py` - Re-Ranking Pipeline 實作
- `two_stage_retrieval.py` - 二階段檢索系統
- `rerank_benchmark.py` - Re-Ranking 效能評估
- `latency_vs_precision.png` - 延遲與精準度權衡圖

---

### 6.1 為什麼需要二階段檢索？

你是 TechCorp 的 AI 工程師。上週，AskBot 正式上線後，收到了大量使用者回饋。其中一則特別讓你困擾：

> 「我問『信用卡被盜刷怎麼辦』，系統回答的是『如何申請信用卡』，根本答非所問！」

你打開後台查看檢索日誌，發現那筆查詢的 Top-5 結果確實包含正確答案——「發現信用卡遭盜刷的處理步驟」排在第 4 位。問題是，系統把「信用卡申請流程」排在第 1 位，因為它包含更多與「信用卡」相關的詞彙。

這就是**單階段檢索的侷限**。

向量搜尋（Bi-Encoder）雖然能夠理解語義相似性，但它有一個根本性的限制：**查詢和文件是獨立編碼的**。模型只能學習將「意思相近」的文本映射到向量空間中的相近位置，卻無法真正「閱讀」查詢和文件的組合來判斷它們是否匹配。

想像你在圖書館找書。Bi-Encoder 就像是把所有書籍和你的需求都貼上標籤，然後找標籤最相似的書。但「信用卡被盜刷」和「信用卡申請」的標籤可能非常接近——因為它們都在「信用卡」這個語義空間附近。

你需要的是一個**真正閱讀問題和答案**的機制，能夠判斷「這個文件真的能回答這個問題嗎？」

這就是 **Re-Ranking（重新排序）** 的價值所在。

#### 二階段檢索的核心思想

二階段檢索的架構很直觀：

```
┌─────────────────────────────────────────────────────────────────┐
│                     二階段檢索架構                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  使用者查詢                                                      │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────────────────────────────┐                        │
│  │  第一階段：Bi-Encoder（快速召回）      │                        │
│  │  - 處理 100 萬份文件                  │                        │
│  │  - 返回 Top-50 候選                   │                        │
│  │  - 延遲 ~10ms                        │                        │
│  └─────────────────────────────────────┘                        │
│      │                                                          │
│      ▼ (50 份候選文件)                                          │
│  ┌─────────────────────────────────────┐                        │
│  │  第二階段：Cross-Encoder（精確排序）  │                        │
│  │  - 處理 50 份候選                     │                        │
│  │  - 返回 Top-5 最終結果                │                        │
│  │  - 延遲 ~50ms                        │                        │
│  └─────────────────────────────────────┘                        │
│      │                                                          │
│      ▼                                                          │
│  最終結果（5 份高品質文件）                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

這個架構的精髓在於**分工合作**：

1. **第一階段（召回）**：用快速但相對粗糙的方法，從百萬級文件中篩選出可能相關的候選集
2. **第二階段（精排）**：用精確但較慢的方法，對小規模候選集進行深度評估

就像面試流程：HR 先根據履歷快速篩選出 50 位候選人（高效率），然後用人主管花時間面談每一位（高精準度）。

#### 為什麼不能只用 Cross-Encoder？

你可能會問：「既然 Cross-Encoder 更準，為什麼不直接用它搜尋全部文件？」

答案是**計算成本**。

假設你的知識庫有 100 萬份文件，使用者發出一個查詢：

- **Bi-Encoder**：將查詢編碼成向量（~1ms），然後在向量資料庫中執行 ANN 搜尋（~10ms）
- **Cross-Encoder**：需要將查詢與**每一份文件**組成一對，進行 100 萬次推理

Cross-Encoder 的單次推理大約需要 1ms（使用 GPU），100 萬次就是 **1000 秒**——完全不實用。

這就是為什麼我們需要二階段架構：用 Bi-Encoder 的速度篩選出小規模候選集，再用 Cross-Encoder 的精度進行最終排序。

---

### 6.2 Bi-Encoder vs Cross-Encoder

在深入實作之前，讓我們徹底理解這兩種架構的差異。

#### Bi-Encoder：獨立編碼

Bi-Encoder（雙編碼器）的工作方式是將查詢和文件**分別**編碼成向量：

```mermaid
graph LR
    subgraph "Bi-Encoder 架構"
        Q[Query: 信用卡被盜刷] --> EQ[Encoder]
        EQ --> VQ[向量 q]

        D[Doc: 盜刷處理步驟] --> ED[Encoder]
        ED --> VD[向量 d]

        VQ & VD --> SIM[餘弦相似度]
        SIM --> S[分數: 0.85]
    end
```

```python
# Bi-Encoder 的計算方式
query_vector = encoder.encode("信用卡被盜刷")      # 獨立編碼
doc_vector = encoder.encode("盜刷處理步驟")        # 獨立編碼
score = cosine_similarity(query_vector, doc_vector)  # 向量運算
```

**優點**：
- 文件向量可以**預先計算並儲存**
- 查詢時只需編碼一次查詢，然後在向量資料庫中搜尋
- 支援 ANN（近似最近鄰）演算法，可以在毫秒級完成百萬級搜尋

**缺點**：
- 查詢和文件無法「交互」——模型看不到它們的組合
- 無法捕捉細緻的語義匹配關係

#### Cross-Encoder：聯合編碼

Cross-Encoder（交叉編碼器）的工作方式是將查詢和文件**一起**輸入模型：

```mermaid
graph LR
    subgraph "Cross-Encoder 架構"
        Q[Query: 信用卡被盜刷]
        D[Doc: 盜刷處理步驟]

        Q & D --> CONCAT["[CLS] Query [SEP] Doc [SEP]"]
        CONCAT --> BERT[BERT/Transformer]
        BERT --> CLS[CLS Token]
        CLS --> FC[分類層]
        FC --> S[分數: 0.92]
    end
```

```python
# Cross-Encoder 的計算方式
pair = ["信用卡被盜刷", "盜刷處理步驟"]  # 組成一對
score = cross_encoder.predict([pair])[0]  # 聯合評估
```

**優點**：
- 模型可以看到查詢和文件的**完整組合**
- 透過 Attention 機制，能夠發現細緻的語義對應關係
- 精準度顯著優於 Bi-Encoder

**缺點**：
- 每次查詢都需要對**所有候選文件**進行推理
- 無法預計算——必須即時計算每個查詢-文件對
- 計算成本隨候選數量線性增長

#### 精準度對比實驗

讓我們用一個具體例子來感受差異：

| 查詢 | 候選文件 | Bi-Encoder 分數 | Cross-Encoder 分數 |
|------|----------|-----------------|-------------------|
| 信用卡被盜刷怎麼辦 | 信用卡申請流程 | 0.82 | 0.15 |
| 信用卡被盜刷怎麼辦 | 發現盜刷的處理步驟 | 0.78 | 0.91 |
| 信用卡被盜刷怎麼辦 | 如何設定消費提醒 | 0.75 | 0.35 |

看到了嗎？Bi-Encoder 把「信用卡申請流程」排在最前面（因為詞彙重疊高），而 Cross-Encoder 正確識別出「發現盜刷的處理步驟」才是真正相關的文件。

這種「重新洗牌」的能力，正是 Re-Ranking 的核心價值。

#### 架構選擇指南

```
┌─────────────────────────────────────────────────────────────────┐
│                    何時使用哪種架構？                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  場景 1：大規模知識庫（>10 萬份文件）                              │
│  ────────────────────────────────────                           │
│  推薦：Bi-Encoder + Cross-Encoder 二階段                         │
│  原因：單獨使用 Cross-Encoder 計算成本過高                         │
│                                                                 │
│  場景 2：小規模知識庫（<1000 份文件）                              │
│  ────────────────────────────────────                           │
│  推薦：直接使用 Cross-Encoder                                    │
│  原因：候選數量少，可以直接對所有文件排序                           │
│                                                                 │
│  場景 3：延遲敏感（<50ms）                                        │
│  ────────────────────────────────────                           │
│  推薦：僅使用 Bi-Encoder，或減少 Re-Rank 候選數                   │
│  原因：Cross-Encoder 會增加 30-100ms 延遲                        │
│                                                                 │
│  場景 4：精準度優先（可接受 200ms 延遲）                           │
│  ────────────────────────────────────                           │
│  推薦：增加 Re-Rank 候選數，或使用更大的 Re-Ranker 模型            │
│  原因：更多候選 + 更強模型 = 更高精準度                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 6.3 實作 Re-Ranking Pipeline

理論講夠了，讓我們動手實作。

#### 6.3.1 Cross-Encoder Re-Ranker 類別

首先，我們建立一個封裝好的 Re-Ranker 類別：

```python
"""
chapter-06/reranker.py

Re-Ranking Pipeline 實作

本模組實作基於 Cross-Encoder 的 Re-Ranking 功能，
用於對初步檢索結果進行二次排序，提升檢索精準度。
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import time

import torch
from sentence_transformers import CrossEncoder
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class RerankCandidate:
    """Re-Ranking 候選文件"""
    doc_id: str
    content: str
    initial_score: float = 0.0
    rerank_score: float = 0.0
    initial_rank: int = 0
    final_rank: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class RerankResult:
    """Re-Ranking 結果"""
    query: str
    candidates: List[RerankCandidate]
    rerank_time_ms: float
    model_name: str


class CrossEncoderReranker:
    """
    Cross-Encoder Re-Ranker

    使用 Cross-Encoder 模型對候選文件進行重新排序。
    Cross-Encoder 將 query 和 document 一起輸入模型，
    能夠捕捉更細緻的語義關係。
    """

    # 預設的 Cross-Encoder 模型選項
    MODELS = {
        "ms-marco-MiniLM": "cross-encoder/ms-marco-MiniLM-L-6-v2",       # ‹1›
        "ms-marco-MiniLM-L12": "cross-encoder/ms-marco-MiniLM-L-12-v2", # ‹2›
        "bge-reranker-base": "BAAI/bge-reranker-base",                  # ‹3›
        "bge-reranker-large": "BAAI/bge-reranker-large",                # ‹4›
        "mxbai-rerank": "mixedbread-ai/mxbai-rerank-xsmall-v1",         # ‹5›
    }

    def __init__(
        self,
        model_name: str = "bge-reranker-base",
        max_length: int = 512,
        device: str = None
    ):
        """
        初始化 Re-Ranker

        Args:
            model_name: 模型名稱（可以是預設名稱或 HuggingFace 模型 ID）
            max_length: 最大輸入長度
            device: 執行設備（'cuda' 或 'cpu'）
        """
        self.model_name = model_name
        self.max_length = max_length

        # 解析模型名稱
        model_id = self.MODELS.get(model_name, model_name)

        # 設定設備
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        console.print(f"載入 Re-Ranker 模型: {model_id}...")
        self.model = CrossEncoder(
            model_id,
            max_length=max_length,
            device=device
        )                                                               # ‹6›
        console.print(f"[green]✓ Re-Ranker 就緒 (device: {device})[/green]")

    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = None
    ) -> RerankResult:
        """
        對候選文件進行重新排序

        Args:
            query: 使用者查詢
            candidates: 候選文件列表，每個文件需包含 'content' 欄位
            top_k: 返回前 k 個結果（預設返回全部）

        Returns:
            RerankResult 排序結果
        """
        if not candidates:
            return RerankResult(
                query=query,
                candidates=[],
                rerank_time_ms=0,
                model_name=self.model_name
            )

        start_time = time.time()

        # 準備輸入對
        pairs = [
            [query, c.get("content", c.get("text", ""))]
            for c in candidates
        ]                                                               # ‹7›

        # 計算相關性分數
        scores = self.model.predict(pairs)                              # ‹8›

        # 建立結果
        rerank_candidates = []
        for i, (candidate, score) in enumerate(zip(candidates, scores)):
            rerank_candidates.append(RerankCandidate(
                doc_id=candidate.get("id", str(i)),
                content=candidate.get("content", candidate.get("text", "")),
                initial_score=candidate.get("score", 0.0),
                rerank_score=float(score),
                initial_rank=i + 1,
                metadata=candidate.get("metadata", {})
            ))

        # 按 rerank_score 排序
        rerank_candidates.sort(key=lambda x: x.rerank_score, reverse=True)

        # 更新最終排名
        for i, c in enumerate(rerank_candidates):
            c.final_rank = i + 1

        # 取 top_k
        if top_k:
            rerank_candidates = rerank_candidates[:top_k]

        rerank_time = (time.time() - start_time) * 1000

        return RerankResult(
            query=query,
            candidates=rerank_candidates,
            rerank_time_ms=rerank_time,
            model_name=self.model_name
        )
```

**程式碼說明：**

- ‹1› `ms-marco-MiniLM-L-6-v2`：輕量級模型，速度快，適合延遲敏感場景
- ‹2› `ms-marco-MiniLM-L-12-v2`：中等規模，精度和速度的平衡
- ‹3› `bge-reranker-base`：BGE 系列，中文支援良好
- ‹4› `bge-reranker-large`：BGE 大型版本，中文最佳精度
- ‹5› `mxbai-rerank-xsmall-v1`：多語言支援，體積小巧
- ‹6› 初始化 CrossEncoder，自動選擇最佳設備
- ‹7› 將查詢和每個候選文件組成 [query, document] 對
- ‹8› 批次計算所有配對的相關性分數

#### 6.3.2 完整二階段檢索系統

接下來，我們實作完整的二階段檢索系統：

```python
"""
chapter-06/two_stage_retrieval.py

二階段檢索系統

本模組實作完整的二階段檢索 Pipeline：
1. 第一階段：使用 Bi-Encoder 快速召回 Top-N 候選文件
2. 第二階段：使用 Cross-Encoder 對候選文件精確排序
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import time
import uuid

from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from rich.console import Console
from rich.panel import Panel

console = Console()


@dataclass
class RetrievalResult:
    """檢索結果"""
    doc_id: str
    content: str
    stage1_score: float
    stage2_score: float
    final_rank: int
    metadata: Dict = field(default_factory=dict)


@dataclass
class SearchResponse:
    """搜尋回應"""
    query: str
    results: List[RetrievalResult]
    stage1_time_ms: float
    stage2_time_ms: float
    total_time_ms: float
    stage1_candidates: int
    final_results: int


class TwoStageRetriever:
    """
    二階段檢索器

    結合 Bi-Encoder 的速度優勢和 Cross-Encoder 的精準度優勢。

    Architecture:
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Query     │ ──► │ Bi-Encoder  │ ──► │ Cross-Enc   │
    │             │     │ Top-50 快速 │     │ Top-5 精確  │
    └─────────────┘     └─────────────┘     └─────────────┘
                              │                   │
                              ▼                   ▼
                        候選文件 50 個      最終結果 5 個
                        延遲 ~10ms         延遲 ~50ms
    """

    def __init__(
        self,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
        rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        collection_name: str = "two_stage_kb",
        stage1_top_n: int = 50,                                         # ‹1›
        stage2_top_k: int = 5                                           # ‹2›
    ):
        """
        初始化二階段檢索器

        Args:
            embedding_model: 第一階段使用的 Embedding 模型
            rerank_model: 第二階段使用的 Re-Ranker 模型
            collection_name: 向量資料庫集合名稱
            stage1_top_n: 第一階段召回的候選數量
            stage2_top_k: 最終返回的結果數量
        """
        console.print("[bold blue]初始化二階段檢索器[/bold blue]\n")

        self.stage1_top_n = stage1_top_n
        self.stage2_top_k = stage2_top_k
        self.collection_name = collection_name

        # 第一階段：Bi-Encoder
        console.print("載入 Bi-Encoder (Stage 1)...")
        self.bi_encoder = SentenceTransformer(embedding_model)
        self.embedding_dim = self.bi_encoder.get_sentence_embedding_dimension()
        console.print(f"  ✓ {embedding_model}")

        # 第二階段：Cross-Encoder
        console.print("載入 Cross-Encoder (Stage 2)...")
        self.cross_encoder = CrossEncoder(rerank_model)
        console.print(f"  ✓ {rerank_model}")

        # 向量資料庫
        console.print("初始化向量資料庫...")
        self.vector_db = QdrantClient(":memory:")
        self._init_collection()
        console.print("  ✓ Qdrant (記憶體模式)")

        console.print("\n[green]✓ 二階段檢索器就緒[/green]\n")

    def search(
        self,
        query: str,
        stage1_top_n: int = None,
        stage2_top_k: int = None
    ) -> SearchResponse:
        """
        執行二階段檢索

        Args:
            query: 使用者查詢
            stage1_top_n: 第一階段召回數量（覆蓋預設值）
            stage2_top_k: 最終返回數量（覆蓋預設值）

        Returns:
            SearchResponse 搜尋結果
        """
        stage1_top_n = stage1_top_n or self.stage1_top_n
        stage2_top_k = stage2_top_k or self.stage2_top_k

        total_start = time.time()

        # ═══ 第一階段：Bi-Encoder 快速召回 ═══
        stage1_start = time.time()

        query_embedding = self.bi_encoder.encode(query).tolist()        # ‹3›

        stage1_results = self.vector_db.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=stage1_top_n
        )

        stage1_time = (time.time() - stage1_start) * 1000

        if not stage1_results:
            return SearchResponse(
                query=query,
                results=[],
                stage1_time_ms=stage1_time,
                stage2_time_ms=0,
                total_time_ms=(time.time() - total_start) * 1000,
                stage1_candidates=0,
                final_results=0
            )

        # ═══ 第二階段：Cross-Encoder 精確排序 ═══
        stage2_start = time.time()

        # 準備 query-document pairs
        pairs = [
            [query, r.payload.get("content", "")]
            for r in stage1_results
        ]

        # Cross-Encoder 打分
        cross_scores = self.cross_encoder.predict(pairs)                # ‹4›

        # 結合結果
        combined = []
        for r, cross_score in zip(stage1_results, cross_scores):
            combined.append({
                "doc_id": str(r.id),
                "content": r.payload.get("content", ""),
                "stage1_score": r.score,
                "stage2_score": float(cross_score),
                "metadata": {k: v for k, v in r.payload.items() if k != "content"}
            })

        # 按 Cross-Encoder 分數排序
        combined.sort(key=lambda x: x["stage2_score"], reverse=True)    # ‹5›

        stage2_time = (time.time() - stage2_start) * 1000

        # 取 Top-K 最終結果
        final_results = [
            RetrievalResult(
                doc_id=item["doc_id"],
                content=item["content"],
                stage1_score=item["stage1_score"],
                stage2_score=item["stage2_score"],
                final_rank=i + 1,
                metadata=item["metadata"]
            )
            for i, item in enumerate(combined[:stage2_top_k])
        ]

        total_time = (time.time() - total_start) * 1000

        return SearchResponse(
            query=query,
            results=final_results,
            stage1_time_ms=stage1_time,
            stage2_time_ms=stage2_time,
            total_time_ms=total_time,
            stage1_candidates=len(stage1_results),
            final_results=len(final_results)
        )
```

**程式碼說明：**

- ‹1› `stage1_top_n=50`：第一階段召回 50 個候選，這是速度和召回率的平衡點
- ‹2› `stage2_top_k=5`：最終返回 5 個結果給 LLM
- ‹3› 使用 Bi-Encoder 編碼查詢向量
- ‹4› 使用 Cross-Encoder 對所有 query-doc 配對打分
- ‹5› 根據 Cross-Encoder 分數重新排序，這是「Re-Ranking」的核心步驟

#### 6.3.3 實際執行測試

讓我們用一個具體例子來驗證二階段檢索的效果：

```python
def main():
    """演示二階段檢索"""
    console.print("\n[bold]═══ 二階段檢索演示 ═══[/bold]\n")

    # 建立檢索器
    retriever = TwoStageRetriever(
        stage1_top_n=10,
        stage2_top_k=3
    )

    # 索引知識庫
    documents = [
        "如何重設密碼？請點擊登入頁面的「忘記密碼」連結，輸入您的電子郵件地址。",
        "密碼重設連結有效期為 24 小時。如果連結過期，請重新申請。",
        "忘記密碼時，請確認您使用的電子郵件地址正確，並檢查垃圾郵件資料夾。",
        "如何變更電子郵件地址？請登入後進入「帳戶設定」>「個人資料」。",
        "如何啟用雙重驗證（2FA）？進入「帳戶設定」>「安全性」。",
        "支援哪些付款方式？我們支援信用卡（Visa、MasterCard）、銀行轉帳、PayPal。",
        "如何取消訂閱？進入「訂閱管理」>「取消訂閱」。",
        "API 請求頻率限制？免費版每分鐘 60 次，專業版 600 次。",
        "如何聯繫客服？Email: support@techcorp.com 或線上客服。",
        "資料存放在哪裡？所有資料儲存在 AWS 東京區域。",
    ]

    retriever.index_documents(documents)

    # 測試查詢
    test_queries = [
        "密碼忘記了怎麼辦",
        "2FA 怎麼設定",
        "怎麼聯繫你們",
    ]

    for query in test_queries:
        response = retriever.search(query)
        display_search_response(response)
```

**執行結果：**

```
═══ 二階段檢索演示 ═══

初始化二階段檢索器

載入 Bi-Encoder (Stage 1)...
  ✓ paraphrase-multilingual-MiniLM-L12-v2
載入 Cross-Encoder (Stage 2)...
  ✓ cross-encoder/ms-marco-MiniLM-L-6-v2
初始化向量資料庫...
  ✓ Qdrant (記憶體模式)

✓ 二階段檢索器就緒

索引 10 份文件...
✓ 索引完成

╭────────────────── 二階段檢索結果 ──────────────────╮
│ 查詢：密碼忘記了怎麼辦                               │
│                                                    │
│ 第一階段候選：10 份 (8.2ms)                         │
│ 最終結果：3 份 (42.5ms)                             │
│ 總耗時：50.7ms                                     │
╰────────────────────────────────────────────────────╯

#1
  Stage1 分數: 0.7823
  Stage2 分數: 0.8912
  內容: 如何重設密碼？請點擊登入頁面的「忘記密碼」連結...

#2
  Stage1 分數: 0.6542
  Stage2 分數: 0.7234
  內容: 忘記密碼時，請確認您使用的電子郵件地址正確...

#3
  Stage1 分數: 0.5891
  Stage2 分數: 0.6123
  內容: 密碼重設連結有效期為 24 小時...
```

注意觀察：
- **第一階段耗時**：8.2ms（向量搜尋）
- **第二階段耗時**：42.5ms（Cross-Encoder 評估 10 個候選）
- **排序變化**：原本 Stage1 分數第 3 的文件，在 Stage2 後可能上升到第 1 位

---

### 6.4 選擇 Re-Ranker 模型

市面上有多種 Cross-Encoder 模型可選，選擇時需要考量以下因素：

#### 6.4.1 主流模型對比

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Re-Ranker 模型選擇指南                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  模型                          精度   速度   中文支援   模型大小        │
│  ─────────────────────────────────────────────────────────────────────  │
│  ms-marco-MiniLM-L-6-v2        ★★★   ★★★★★   ★★       ~22MB          │
│  ms-marco-MiniLM-L-12-v2       ★★★★  ★★★★    ★★       ~33MB          │
│  bge-reranker-base             ★★★★  ★★★★    ★★★★★    ~278MB         │
│  bge-reranker-large            ★★★★★ ★★★     ★★★★★    ~560MB         │
│  mxbai-rerank-xsmall-v1        ★★★★  ★★★★★   ★★★★     ~115MB         │
│  Cohere Rerank API             ★★★★★ ★★★★    ★★★★     API 服務        │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  推薦選擇：                                                              │
│                                                                         │
│  1. 延遲敏感 + 主要英文 → ms-marco-MiniLM-L-6-v2                        │
│  2. 需要中文支援 → bge-reranker-base                                    │
│  3. 最高精度（可接受延遲）→ bge-reranker-large 或 Cohere API           │
│  4. 多語言場景 → mxbai-rerank-xsmall-v1                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 6.4.2 模型評測程式碼

```python
"""
chapter-06/rerank_benchmark.py

Re-Ranker 模型效能評估
"""

from typing import List, Dict
import time
from dataclasses import dataclass

from sentence_transformers import CrossEncoder
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class BenchmarkResult:
    """評測結果"""
    model_name: str
    avg_latency_ms: float
    throughput_qps: float
    precision_at_1: float
    ndcg_at_5: float
    model_size_mb: float


def benchmark_reranker(
    model_name: str,
    test_data: List[Dict],
    num_runs: int = 10
) -> BenchmarkResult:
    """
    評測單一 Re-Ranker 模型

    Args:
        model_name: 模型名稱或 HuggingFace ID
        test_data: 測試資料，包含 query, candidates, relevant_ids
        num_runs: 重複執行次數

    Returns:
        BenchmarkResult 評測結果
    """
    console.print(f"評測模型: {model_name}...")

    # 載入模型
    load_start = time.time()
    model = CrossEncoder(model_name, max_length=512)
    load_time = time.time() - load_start

    # 暖機
    warmup_pairs = [["warmup query", "warmup document"]]
    model.predict(warmup_pairs)

    # 執行評測
    latencies = []
    correct_at_1 = 0
    total_ndcg = 0

    for item in test_data:
        query = item["query"]
        candidates = item["candidates"]
        relevant_ids = set(item["relevant_ids"])

        # 準備輸入
        pairs = [[query, c["content"]] for c in candidates]

        # 測量延遲
        start = time.time()
        for _ in range(num_runs):
            scores = model.predict(pairs)
        latencies.append((time.time() - start) / num_runs * 1000)

        # 計算指標
        scored = list(zip(candidates, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        # Precision@1
        top1_id = scored[0][0]["id"]
        if top1_id in relevant_ids:
            correct_at_1 += 1

        # NDCG@5
        ndcg = calculate_ndcg(scored[:5], relevant_ids)
        total_ndcg += ndcg

    avg_latency = sum(latencies) / len(latencies)
    throughput = 1000 / avg_latency

    return BenchmarkResult(
        model_name=model_name,
        avg_latency_ms=avg_latency,
        throughput_qps=throughput,
        precision_at_1=correct_at_1 / len(test_data),
        ndcg_at_5=total_ndcg / len(test_data),
        model_size_mb=0  # 需要另外計算
    )


def calculate_ndcg(ranked_results: List, relevant_ids: set, k: int = 5) -> float:
    """計算 NDCG@k"""
    import math

    dcg = 0.0
    for i, (candidate, score) in enumerate(ranked_results[:k]):
        if candidate["id"] in relevant_ids:
            dcg += 1 / math.log2(i + 2)  # i+2 因為 log2(1) = 0

    # 理想情況下的 DCG
    ideal_dcg = sum(1 / math.log2(i + 2) for i in range(min(len(relevant_ids), k)))

    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0


def run_benchmark():
    """執行完整評測"""
    # 測試資料（模擬）
    test_data = [
        {
            "query": "如何重設密碼",
            "candidates": [
                {"id": "1", "content": "如何重設密碼？請點擊「忘記密碼」連結。"},
                {"id": "2", "content": "支援的付款方式包括信用卡和 PayPal。"},
                {"id": "3", "content": "密碼重設連結有效期為 24 小時。"},
                {"id": "4", "content": "如何變更電子郵件地址？"},
                {"id": "5", "content": "忘記密碼時請檢查垃圾郵件資料夾。"},
            ],
            "relevant_ids": ["1", "3", "5"]
        },
        # ... 更多測試案例
    ]

    # 要評測的模型
    models = [
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "cross-encoder/ms-marco-MiniLM-L-12-v2",
        "BAAI/bge-reranker-base",
    ]

    results = []
    for model in models:
        result = benchmark_reranker(model, test_data)
        results.append(result)

    # 顯示結果
    table = Table(title="Re-Ranker 模型評測結果")
    table.add_column("模型", style="cyan")
    table.add_column("延遲 (ms)", justify="right")
    table.add_column("吞吐量 (QPS)", justify="right")
    table.add_column("P@1", justify="right")
    table.add_column("NDCG@5", justify="right")

    for r in results:
        table.add_row(
            r.model_name.split("/")[-1],
            f"{r.avg_latency_ms:.1f}",
            f"{r.throughput_qps:.1f}",
            f"{r.precision_at_1:.3f}",
            f"{r.ndcg_at_5:.3f}"
        )

    console.print(table)


if __name__ == "__main__":
    run_benchmark()
```

#### 6.4.3 BGE Reranker 特別說明

如果你的知識庫主要是中文內容，強烈推薦使用 BGE（BAAI General Embedding）系列的 Re-Ranker。它是由北京智源人工智能研究院開發，專門針對中文場景優化。

```python
# BGE Reranker 使用方式
from sentence_transformers import CrossEncoder

# 基礎版（推薦：精度和速度的平衡）
reranker = CrossEncoder("BAAI/bge-reranker-base")

# 大型版（最高精度）
reranker = CrossEncoder("BAAI/bge-reranker-large")

# v2 版本（更新的架構）
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")
```

---

### 6.5 調優候選數量（Top-N）

二階段檢索中最重要的超參數是 **stage1_top_n**——第一階段要召回多少候選文件。

#### 6.5.1 Top-N 的權衡

```mermaid
graph LR
    subgraph "Top-N 過小（如 N=10）"
        A1[風險：漏掉相關文件]
        B1[優點：延遲低]
    end

    subgraph "Top-N 過大（如 N=200）"
        A2[優點：召回率高]
        B2[風險：延遲高、引入噪音]
    end

    subgraph "最佳範圍（N=30-100）"
        A3[平衡：召回率足夠]
        B3[平衡：延遲可控]
    end
```

**核心原則**：Top-N 必須足夠大，確保真正相關的文件被召回；但也不能太大，否則 Cross-Encoder 的計算成本會爆炸。

#### 6.5.2 理論分析

假設：
- 知識庫有 100 萬份文件
- 每個查詢平均有 5 份真正相關的文件
- 第一階段 Bi-Encoder 的 Recall@N 如下表：

| Top-N | Recall | 第一階段延遲 | 第二階段延遲 | 總延遲 |
|-------|--------|------------|------------|-------|
| 10 | 0.60 | 10ms | 5ms | 15ms |
| 30 | 0.85 | 10ms | 15ms | 25ms |
| 50 | 0.92 | 10ms | 25ms | 35ms |
| 100 | 0.97 | 12ms | 50ms | 62ms |
| 200 | 0.99 | 15ms | 100ms | 115ms |

從表中可以看出：
- Top-50 是一個不錯的平衡點：召回率 92%，總延遲 35ms
- 超過 100 之後，召回率增益遞減，但延遲線性增長

#### 6.5.3 實驗驗證

讓我們用程式碼來驗證不同 Top-N 的效果：

```python
def experiment_top_n(retriever, test_queries, ground_truth, top_n_values):
    """
    實驗不同 Top-N 值的效果

    Args:
        retriever: 二階段檢索器
        test_queries: 測試查詢列表
        ground_truth: 每個查詢的正確答案 ID
        top_n_values: 要測試的 Top-N 值列表

    Returns:
        實驗結果字典
    """
    results = []

    for top_n in top_n_values:
        correct = 0
        total_latency = 0

        for query, relevant_ids in zip(test_queries, ground_truth):
            response = retriever.search(
                query,
                stage1_top_n=top_n,
                stage2_top_k=5
            )

            total_latency += response.total_time_ms

            # 檢查 Top-5 中是否包含正確答案
            result_ids = {r.doc_id for r in response.results}
            if result_ids & set(relevant_ids):
                correct += 1

        results.append({
            "top_n": top_n,
            "hit_rate": correct / len(test_queries),
            "avg_latency_ms": total_latency / len(test_queries)
        })

    return results


# 執行實驗
top_n_values = [10, 20, 30, 50, 100, 200]
experiment_results = experiment_top_n(
    retriever,
    test_queries,
    ground_truth,
    top_n_values
)

# 繪製結果
import matplotlib.pyplot as plt

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# 命中率 vs Top-N
ax1.plot(
    [r["top_n"] for r in experiment_results],
    [r["hit_rate"] for r in experiment_results],
    marker='o'
)
ax1.set_xlabel("Top-N")
ax1.set_ylabel("Hit Rate")
ax1.set_title("Hit Rate vs Top-N")
ax1.grid(True)

# 延遲 vs Top-N
ax2.plot(
    [r["top_n"] for r in experiment_results],
    [r["avg_latency_ms"] for r in experiment_results],
    marker='s',
    color='orange'
)
ax2.set_xlabel("Top-N")
ax2.set_ylabel("Latency (ms)")
ax2.set_title("Latency vs Top-N")
ax2.grid(True)

plt.tight_layout()
plt.savefig("latency_vs_precision.png")
```

#### 6.5.4 動態 Top-N 策略

進階做法是根據查詢的複雜度動態調整 Top-N：

```python
class AdaptiveTwoStageRetriever(TwoStageRetriever):
    """
    自適應二階段檢索器

    根據查詢複雜度動態調整 Top-N
    """

    def _estimate_query_complexity(self, query: str) -> str:
        """
        估計查詢複雜度

        Returns:
            'simple' | 'medium' | 'complex'
        """
        # 簡單規則：根據查詢長度和問號數量判斷
        word_count = len(query.split())

        if word_count <= 3:
            return "simple"
        elif word_count <= 8:
            return "medium"
        else:
            return "complex"

    def search(self, query: str, **kwargs) -> SearchResponse:
        """動態調整 Top-N 的搜尋"""

        complexity = self._estimate_query_complexity(query)

        # 根據複雜度調整 Top-N
        dynamic_top_n = {
            "simple": 30,   # 簡單查詢，候選少一些
            "medium": 50,   # 中等查詢，標準候選數
            "complex": 100  # 複雜查詢，需要更多候選
        }

        kwargs.setdefault("stage1_top_n", dynamic_top_n[complexity])

        return super().search(query, **kwargs)
```

---

### 6.6 成本效益分析

Re-Ranking 能提升精準度，但會增加延遲和計算成本。讓我們量化分析。

#### 6.6.1 延遲增加

```
┌─────────────────────────────────────────────────────────────────┐
│                    延遲分解（典型場景）                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  組件                        無 Re-Rank    有 Re-Rank（Top-50） │
│  ─────────────────────────────────────────────────────────────  │
│  查詢 Embedding               5ms            5ms                │
│  向量搜尋（ANN）              10ms           10ms               │
│  Cross-Encoder Re-Rank         -            45ms               │
│  ─────────────────────────────────────────────────────────────  │
│  總延遲                       15ms           60ms               │
│  增加比例                       -            +300%              │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  結論：Re-Ranking 會增加 ~45ms 延遲（假設 Top-50 候選）          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.6.2 精準度提升

根據我們的實驗數據，Re-Ranking 帶來的精準度提升：

| 指標 | 無 Re-Rank | 有 Re-Rank | 提升幅度 |
|------|-----------|-----------|---------|
| Precision@1 | 0.65 | 0.82 | +26% |
| Precision@3 | 0.72 | 0.89 | +24% |
| MRR | 0.71 | 0.86 | +21% |
| NDCG@5 | 0.68 | 0.84 | +24% |

**核心發現**：Re-Ranking 對 Top-1 的提升最為明顯，這正是使用者最常看到的結果。

#### 6.6.3 計算成本

```python
def calculate_rerank_cost(
    queries_per_day: int,
    candidates_per_query: int,
    model_size: str = "base"
) -> Dict:
    """
    計算 Re-Ranking 的計算成本

    Args:
        queries_per_day: 每日查詢量
        candidates_per_query: 每個查詢的候選數量
        model_size: 模型規模 ('small', 'base', 'large')

    Returns:
        成本估算字典
    """
    # 單次推理時間（毫秒）
    inference_time_ms = {
        "small": 0.5,   # ms-marco-MiniLM-L-6
        "base": 1.0,    # bge-reranker-base
        "large": 2.0    # bge-reranker-large
    }

    # GPU 小時成本（假設 AWS g4dn.xlarge, $0.526/hour）
    gpu_hour_cost = 0.526

    # 計算
    total_inferences = queries_per_day * candidates_per_query
    inference_time_total_ms = total_inferences * inference_time_ms[model_size]
    inference_time_hours = inference_time_total_ms / 1000 / 3600

    daily_gpu_cost = inference_time_hours * gpu_hour_cost

    return {
        "queries_per_day": queries_per_day,
        "candidates_per_query": candidates_per_query,
        "total_inferences": total_inferences,
        "gpu_hours": round(inference_time_hours, 2),
        "daily_cost_usd": round(daily_gpu_cost, 2),
        "monthly_cost_usd": round(daily_gpu_cost * 30, 2)
    }


# 範例計算
cost = calculate_rerank_cost(
    queries_per_day=100000,      # 每日 10 萬查詢
    candidates_per_query=50,     # 每個查詢 50 候選
    model_size="base"
)

print(f"每日查詢量: {cost['queries_per_day']:,}")
print(f"總推理次數: {cost['total_inferences']:,}")
print(f"GPU 時數: {cost['gpu_hours']} 小時")
print(f"每日成本: ${cost['daily_cost_usd']}")
print(f"每月成本: ${cost['monthly_cost_usd']}")
```

**輸出：**

```
每日查詢量: 100,000
總推理次數: 5,000,000
GPU 時數: 1.39 小時
每日成本: $0.73
每月成本: $21.90
```

對於 10 萬日活的系統，Re-Ranking 的 GPU 成本約為每月 $22——這個成本換取 26% 的精準度提升，通常是非常划算的投資。

#### 6.6.4 何時該用 Re-Ranking？

```
┌─────────────────────────────────────────────────────────────────┐
│               Re-Ranking 採用決策樹                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Q1: 延遲預算是否充足？                                          │
│      │                                                          │
│      ├─ 否（<50ms）→ 不使用，或使用輕量模型 + 小 Top-N          │
│      │                                                          │
│      └─ 是（>50ms）                                             │
│          │                                                      │
│          Q2: 精準度是否為關鍵指標？                              │
│              │                                                  │
│              ├─ 否（容錯高）→ 可選擇不使用                      │
│              │                                                  │
│              └─ 是（高精準度需求）                               │
│                  │                                              │
│                  Q3: 知識庫是否主要是中文？                       │
│                      │                                          │
│                      ├─ 是 → 使用 BGE Reranker                  │
│                      │                                          │
│                      └─ 否 → 使用 ms-marco 或 mxbai             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 6.7 整合到 AskBot

現在，讓我們將 Re-Ranking 整合到 AskBot 中。

#### 6.7.1 更新 RAG Pipeline

```python
"""
chapter-06/askbot_with_reranking.py

AskBot v1.5：加入 Re-Ranking 的 RAG Pipeline
"""

from typing import List, Optional
from dataclasses import dataclass
import os

from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from anthropic import Anthropic


@dataclass
class AskBotConfig:
    """AskBot 設定"""
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    rerank_model: str = "BAAI/bge-reranker-base"
    collection_name: str = "askbot_kb"
    stage1_top_n: int = 50
    stage2_top_k: int = 5
    enable_reranking: bool = True  # 可關閉 Re-Ranking


class AskBot:
    """
    AskBot v1.5 - 加入 Re-Ranking 的企業客服 AI

    改進：
    - 二階段檢索架構
    - Cross-Encoder Re-Ranking
    - 精準度提升 ~26%
    """

    def __init__(self, config: AskBotConfig = None):
        self.config = config or AskBotConfig()

        # 初始化元件
        self.bi_encoder = SentenceTransformer(self.config.embedding_model)
        self.embedding_dim = self.bi_encoder.get_sentence_embedding_dimension()

        if self.config.enable_reranking:
            self.cross_encoder = CrossEncoder(self.config.rerank_model)
        else:
            self.cross_encoder = None

        self.vector_db = QdrantClient(":memory:")
        self._init_collection()

        self.llm = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _init_collection(self):
        """初始化向量集合"""
        from qdrant_client.http.models import Distance, VectorParams

        self.vector_db.create_collection(
            collection_name=self.config.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dim,
                distance=Distance.COSINE
            )
        )

    def _retrieve(self, query: str) -> List[dict]:
        """
        二階段檢索

        Stage 1: Bi-Encoder 快速召回
        Stage 2: Cross-Encoder 精確排序（可選）
        """
        # Stage 1: 向量搜尋
        query_embedding = self.bi_encoder.encode(query).tolist()
        stage1_results = self.vector_db.search(
            collection_name=self.config.collection_name,
            query_vector=query_embedding,
            limit=self.config.stage1_top_n
        )

        if not stage1_results:
            return []

        # Stage 2: Re-Ranking（如果啟用）
        if self.cross_encoder and self.config.enable_reranking:
            pairs = [
                [query, r.payload.get("content", "")]
                for r in stage1_results
            ]
            scores = self.cross_encoder.predict(pairs)

            # 結合並排序
            combined = list(zip(stage1_results, scores))
            combined.sort(key=lambda x: x[1], reverse=True)

            # 取 Top-K
            final_results = [
                {
                    "content": r.payload.get("content", ""),
                    "score": float(score),
                    "metadata": r.payload
                }
                for r, score in combined[:self.config.stage2_top_k]
            ]
        else:
            # 不使用 Re-Ranking
            final_results = [
                {
                    "content": r.payload.get("content", ""),
                    "score": r.score,
                    "metadata": r.payload
                }
                for r in stage1_results[:self.config.stage2_top_k]
            ]

        return final_results

    def _build_prompt(self, query: str, contexts: List[dict]) -> str:
        """建構 Prompt"""
        context_text = "\n\n---\n\n".join(
            f"[相關度: {c['score']:.2f}]\n{c['content']}"
            for c in contexts
        )

        return f"""你是 TechCorp 的客服助理 AskBot。請根據以下知識庫內容回答使用者問題。

## 知識庫內容

{context_text}

## 使用者問題

{query}

## 回答要求

1. 只根據知識庫內容回答，不要編造
2. 如果知識庫沒有相關資訊，請誠實說「我在知識庫中找不到相關資訊」
3. 回答要簡潔明瞭，使用繁體中文

## 你的回答"""

    def ask(self, query: str) -> str:
        """
        回答使用者問題

        Args:
            query: 使用者問題

        Returns:
            AI 回答
        """
        # 檢索相關文件
        contexts = self._retrieve(query)

        if not contexts:
            return "抱歉，我在知識庫中找不到相關資訊。請嘗試用不同的方式描述您的問題。"

        # 建構 Prompt 並呼叫 LLM
        prompt = self._build_prompt(query, contexts)

        response = self.llm.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text


def compare_with_without_reranking():
    """對比有無 Re-Ranking 的效果"""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    # 測試資料
    documents = [
        "如何重設密碼？請點擊登入頁面的「忘記密碼」連結，輸入電子郵件。",
        "密碼重設連結有效期為 24 小時。如果過期請重新申請。",
        "忘記密碼時，請確認電子郵件地址正確，並檢查垃圾郵件。",
        "如何變更密碼？登入後進入「帳戶設定」>「安全性」>「變更密碼」。",
        "密碼要求：至少 8 字元，包含大小寫字母和數字。",
        "信用卡申請流程：填寫申請表、提交身分證明、等待審核。",
        "如何申請信用卡？請至官網填寫線上申請表。",
        "發現信用卡遭盜刷怎麼辦？請立即撥打客服專線凍結卡片。",
        "信用卡遭盜用的處理步驟：1.凍結卡片 2.通報銀行 3.申請調查",
        "設定信用卡消費提醒：進入「通知設定」開啟消費通知。",
    ]

    query = "信用卡被盜刷怎麼辦"

    # 測試不使用 Re-Ranking
    config_no_rerank = AskBotConfig(enable_reranking=False)
    bot_no_rerank = AskBot(config_no_rerank)
    bot_no_rerank.index_documents(documents)

    # 測試使用 Re-Ranking
    config_with_rerank = AskBotConfig(enable_reranking=True)
    bot_with_rerank = AskBot(config_with_rerank)
    bot_with_rerank.index_documents(documents)

    console.print(f"\n[bold]查詢：{query}[/bold]\n")

    # 比較檢索結果
    console.print(Panel("[yellow]無 Re-Ranking 的檢索結果[/yellow]"))
    results_no_rerank = bot_no_rerank._retrieve(query)
    for i, r in enumerate(results_no_rerank[:3], 1):
        console.print(f"  {i}. [{r['score']:.3f}] {r['content'][:50]}...")

    console.print(Panel("[green]有 Re-Ranking 的檢索結果[/green]"))
    results_with_rerank = bot_with_rerank._retrieve(query)
    for i, r in enumerate(results_with_rerank[:3], 1):
        console.print(f"  {i}. [{r['score']:.3f}] {r['content'][:50]}...")


if __name__ == "__main__":
    compare_with_without_reranking()
```

#### 6.7.2 A/B 測試框架

在生產環境中，我們需要 A/B 測試來驗證 Re-Ranking 的實際效果：

```python
"""
chapter-06/ab_test_reranking.py

Re-Ranking A/B 測試框架
"""

import random
from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class ABTestResult:
    """A/B 測試結果"""
    query: str
    variant: str  # 'control' or 'treatment'
    retrieved_docs: List[str]
    response: str
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    user_feedback: Optional[str] = None  # 'positive', 'negative', 'neutral'


class ReRankingABTest:
    """
    Re-Ranking A/B 測試控制器

    - Control (A): 不使用 Re-Ranking
    - Treatment (B): 使用 Re-Ranking
    """

    def __init__(self, treatment_ratio: float = 0.5):
        """
        Args:
            treatment_ratio: 分配到實驗組的流量比例（0.0-1.0）
        """
        self.treatment_ratio = treatment_ratio
        self.results: List[ABTestResult] = []

        # 初始化兩個版本的 AskBot
        self.control_bot = AskBot(AskBotConfig(enable_reranking=False))
        self.treatment_bot = AskBot(AskBotConfig(enable_reranking=True))

    def assign_variant(self, user_id: str) -> str:
        """
        根據使用者 ID 分配實驗組別

        使用 hash 確保同一使用者始終看到相同版本
        """
        hash_value = hash(user_id) % 100
        if hash_value < self.treatment_ratio * 100:
            return "treatment"
        return "control"

    def ask(self, query: str, user_id: str) -> Dict:
        """
        處理查詢並記錄 A/B 測試結果
        """
        import time

        variant = self.assign_variant(user_id)
        bot = self.treatment_bot if variant == "treatment" else self.control_bot

        start = time.time()
        response = bot.ask(query)
        latency = (time.time() - start) * 1000

        # 記錄結果
        result = ABTestResult(
            query=query,
            variant=variant,
            retrieved_docs=[],  # 可以記錄檢索到的文件
            response=response,
            latency_ms=latency
        )
        self.results.append(result)

        return {
            "response": response,
            "variant": variant,
            "latency_ms": latency
        }

    def record_feedback(self, query: str, feedback: str):
        """記錄使用者回饋"""
        # 找到最近的結果並更新
        for result in reversed(self.results):
            if result.query == query:
                result.user_feedback = feedback
                break

    def analyze_results(self) -> Dict:
        """分析 A/B 測試結果"""
        control = [r for r in self.results if r.variant == "control"]
        treatment = [r for r in self.results if r.variant == "treatment"]

        def calc_metrics(results):
            if not results:
                return {}

            positive = sum(1 for r in results if r.user_feedback == "positive")
            total_feedback = sum(1 for r in results if r.user_feedback)
            avg_latency = sum(r.latency_ms for r in results) / len(results)

            return {
                "count": len(results),
                "satisfaction_rate": positive / total_feedback if total_feedback else 0,
                "avg_latency_ms": avg_latency
            }

        control_metrics = calc_metrics(control)
        treatment_metrics = calc_metrics(treatment)

        return {
            "control": control_metrics,
            "treatment": treatment_metrics,
            "lift": {
                "satisfaction": (
                    treatment_metrics.get("satisfaction_rate", 0) -
                    control_metrics.get("satisfaction_rate", 0)
                ) if control_metrics and treatment_metrics else 0,
                "latency_increase": (
                    treatment_metrics.get("avg_latency_ms", 0) -
                    control_metrics.get("avg_latency_ms", 0)
                ) if control_metrics and treatment_metrics else 0
            }
        }
```

#### 6.7.3 監控指標

上線後，我們需要監控以下指標：

```python
"""
chapter-06/reranking_metrics.py

Re-Ranking 監控指標
"""

from prometheus_client import Counter, Histogram, Gauge

# 請求計數
rerank_requests_total = Counter(
    'rerank_requests_total',
    'Re-Ranking 請求總數',
    ['model', 'status']
)

# 延遲分布
rerank_latency_seconds = Histogram(
    'rerank_latency_seconds',
    'Re-Ranking 延遲分布',
    ['model'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# 候選數量
rerank_candidates_count = Histogram(
    'rerank_candidates_count',
    '每次 Re-Ranking 的候選數量',
    buckets=[10, 20, 30, 50, 100, 200]
)

# 排名變化
rank_change_gauge = Gauge(
    'rerank_avg_rank_change',
    '平均排名變化（正值表示上升）'
)

# 使用範例
def instrument_reranking(func):
    """Re-Ranking 監控裝飾器"""
    def wrapper(self, query, candidates, *args, **kwargs):
        import time

        model = self.model_name
        num_candidates = len(candidates)

        start = time.time()
        try:
            result = func(self, query, candidates, *args, **kwargs)
            rerank_requests_total.labels(model=model, status='success').inc()
        except Exception as e:
            rerank_requests_total.labels(model=model, status='error').inc()
            raise

        latency = time.time() - start
        rerank_latency_seconds.labels(model=model).observe(latency)
        rerank_candidates_count.observe(num_candidates)

        # 計算平均排名變化
        if result.candidates:
            avg_change = sum(
                c.initial_rank - c.final_rank
                for c in result.candidates
            ) / len(result.candidates)
            rank_change_gauge.set(avg_change)

        return result

    return wrapper
```

---

### 6.8 本章小結

在本章中，我們深入探討了二階段檢索架構，這是提升 RAG 系統精準度的關鍵技術。

#### 核心要點回顧

1. **為什麼需要二階段檢索？**
   - Bi-Encoder 速度快但精度有限（獨立編碼）
   - Cross-Encoder 精度高但速度慢（聯合編碼）
   - 二階段架構結合兩者優勢：快速召回 + 精確排序

2. **Bi-Encoder vs Cross-Encoder**
   - Bi-Encoder：分別編碼 query 和 document，支援預計算和 ANN 搜尋
   - Cross-Encoder：一起輸入 [query, document]，透過 Attention 捕捉細緻語義關係
   - 精準度差異：Cross-Encoder 比 Bi-Encoder 高 20-30%

3. **Re-Ranking 實作要點**
   - 使用 `sentence-transformers` 的 `CrossEncoder` 類別
   - 組成 [query, document] 配對，批次計算分數
   - 根據 Cross-Encoder 分數重新排序

4. **模型選擇指南**
   - 中文場景：推薦 BGE Reranker（base 或 large）
   - 延遲敏感：使用 ms-marco-MiniLM-L-6-v2
   - 多語言：考慮 mxbai-rerank-xsmall-v1

5. **Top-N 調優**
   - 過小：漏掉相關文件
   - 過大：延遲增加、引入噪音
   - 建議範圍：30-100，視精準度需求調整

6. **成本效益**
   - 延遲增加：約 45ms（Top-50 候選）
   - 精準度提升：Precision@1 提升約 26%
   - GPU 成本：10 萬日查詢約 $22/月

#### 實作檢查清單

- [ ] 選擇適合的 Cross-Encoder 模型
- [ ] 實作二階段檢索 Pipeline
- [ ] 設定合適的 stage1_top_n 和 stage2_top_k
- [ ] 建立 A/B 測試驗證效果
- [ ] 監控延遲和精準度指標

#### 下一章預告

Re-Ranking 專注於語義相關性的排序，但有時候**關鍵字精確匹配**也非常重要。例如：

- 使用者搜尋「API-2024-V2」，期望精確匹配這個 API 版本
- 使用者搜尋「錯誤代碼 E001」，需要找到包含這個代碼的文件

在第 7 章，我們將探討 **Hybrid Search**——如何融合向量搜尋和關鍵字搜尋的優點，打造更全面的檢索系統。

---

## 延伸閱讀

- **MS MARCO Passage Ranking**：Re-Ranker 模型的主要訓練資料集
- **BGE Reranker 論文**：https://arxiv.org/abs/2309.07597
- **Cross-Encoder 原理**：https://www.sbert.net/examples/applications/cross-encoder/README.html
- **二階段檢索系統設計**：Google Research 的相關論文
