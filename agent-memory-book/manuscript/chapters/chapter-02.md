# 第 2 章：優化檢索品質：從 Naive RAG 到 Advanced RAG

> 本章學習目標：
> - 識別 Naive RAG 的三大痛點及其根本原因
> - 掌握查詢改寫、混合檢索、重排序三大優化技術
> - 建立量化評估框架，學會使用 MRR、NDCG、Hit Rate 指標
> - 將檢索準確率從 65% 提升到 84%

---

## 2.1 Naive RAG 的三大痛點

在上一章，我們建立了一個能運作的 RAG 系統。但在實際企業場景中，它很快就會遇到瓶頸。讓我們深入分析這些問題的根源。

### 2.1.1 低召回率問題

**場景**：使用者搜尋「WFH 政策」，但文件中使用的是「遠端工作」。

```
使用者查詢: "公司的 WFH 規定是什麼？"
文件內容: "遠端工作政策適用於所有全職員工..."

向量相似度: 0.42 (低於閾值 0.5)
結果: 未檢索到相關內容
```

**根本原因**：

1. **詞彙鴻溝（Lexical Gap）**：「WFH」和「遠端工作」在向量空間中距離較遠
2. **Embedding 模型的局限**：通用模型可能不理解特定領域的同義詞
3. **查詢過於簡短**：短查詢的向量表示缺乏語義豐富性

### 2.1.2 檢索噪音干擾

**場景**：使用者問「新員工入職流程」，Top-5 結果中只有 2 個相關。

```
查詢: "新員工入職流程是什麼？"

Top-5 結果:
1. ✅ "新員工入職第一天需要..." (相關度: 0.85)
2. ✅ "入職培訓安排如下..." (相關度: 0.78)
3. ❌ "員工離職流程包括..." (相關度: 0.71)  # 噪音！
4. ❌ "員工福利包括..." (相關度: 0.68)      # 噪音！
5. ✅ "新員工需要準備的材料..." (相關度: 0.65)
```

**根本原因**：

1. **語義相似但意圖不同**：「入職」和「離職」向量距離近，但意圖相反
2. **召回多排序難**：向量搜尋優化了召回，但排序能力有限
3. **上下文污染**：無關內容進入 LLM 的上下文，影響回答品質

### 2.1.3 語義漂移問題

**場景**：複雜問題被簡化理解。

```
使用者查詢: "2024 年 Q3 和 Q4 的銷售額對比，哪個季度增長更快？"

系統理解: "2024 銷售額" (丟失了比較的語義)

結果: 只找到單一季度的數據，無法完成比較
```

**根本原因**：

1. **語義壓縮損失**：複雜查詢被壓縮成單一向量時丟失細節
2. **缺乏查詢分解**：系統沒有將複雜問題拆分為子問題
3. **單一檢索策略**：對所有類型的問題使用相同的檢索方式

---

## 2.2 技術 1：查詢改寫與擴展

查詢改寫是提升召回率最有效的技術之一。核心思想是：**不要用使用者原始查詢搜尋，而是用改寫或擴展後的查詢搜尋**。

### ‹1› HyDE（Hypothetical Document Embeddings）

**原理**：先讓 LLM 生成一個「假設性的答案」，然後用這個答案去搜尋真實文件。

```mermaid
graph LR
    A[使用者查詢] --> B[LLM]
    B --> C[假設性答案]
    C --> D[Embedding]
    D --> E[向量搜尋]
    E --> F[真實文件]

    style B fill:#f9f,stroke:#333
    style C fill:#ffc,stroke:#333
```

**為什麼有效**：
- 假設性答案比問題更長，向量表示更豐富
- 答案的寫作風格更接近文件，提升匹配度
- 彌補了「問題」和「答案」之間的語義鴻溝

```python
# advanced_rag.py
"""
進階 RAG 系統：查詢改寫模組
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class QueryRewriter:
    """
    查詢改寫器
    ‹1› 使用多種策略改寫使用者查詢
    """

    def __init__(self, llm: ChatOpenAI = None):
        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    async def hyde_rewrite(self, query: str) -> str:
        """
        HyDE: 生成假設性答案
        ‹2› 用假設的答案文本去搜尋，而非原始問題
        """
        prompt = ChatPromptTemplate.from_template("""
請根據以下問題，撰寫一段可能回答這個問題的企業文件內容。
不需要真實準確，只需要模擬文件的寫作風格和可能的內容結構。

問題: {query}

假設性文件內容:
""")

        chain = prompt | self.llm
        result = await chain.ainvoke({"query": query})
        return result.content

    async def multi_query_rewrite(self, query: str, n: int = 3) -> list[str]:
        """
        多查詢改寫
        ‹3› 生成多個不同角度的查詢，增加召回多樣性
        """
        prompt = ChatPromptTemplate.from_template("""
請將以下問題改寫成 {n} 個不同的版本。
每個版本應該:
- 使用不同的詞彙和表達方式
- 從不同角度詢問同一件事
- 包含可能的同義詞

原始問題: {query}

請以 JSON 陣列格式輸出改寫後的問題:
["問題1", "問題2", "問題3"]
""")

        chain = prompt | self.llm
        result = await chain.ainvoke({"query": query, "n": n})

        import json
        try:
            queries = json.loads(result.content)
            return [query] + queries  # 包含原始查詢
        except json.JSONDecodeError:
            return [query]

    async def query_decomposition(self, query: str) -> list[str]:
        """
        查詢分解
        ‹4› 將複雜問題拆解為多個子問題
        """
        prompt = ChatPromptTemplate.from_template("""
分析以下問題，判斷是否需要拆解為多個子問題。

如果問題涉及:
- 多個實體的比較
- 多個步驟的流程
- 需要從不同來源收集資訊

則將其拆解為獨立的子問題。

原始問題: {query}

請以 JSON 格式輸出:
{{
    "needs_decomposition": true/false,
    "sub_queries": ["子問題1", "子問題2", ...],
    "reasoning": "為什麼這樣拆解"
}}
""")

        chain = prompt | self.llm
        result = await chain.ainvoke({"query": query})

        import json
        try:
            parsed = json.loads(result.content)
            if parsed.get("needs_decomposition"):
                return parsed.get("sub_queries", [query])
            return [query]
        except json.JSONDecodeError:
            return [query]
```

### ‹2› Multi-Query Rewriting 實戰效果

```python
# 使用範例
rewriter = QueryRewriter()

original = "公司的 WFH 規定是什麼？"

# 多查詢改寫結果
expanded_queries = await rewriter.multi_query_rewrite(original)
# 輸出:
# [
#     "公司的 WFH 規定是什麼？",
#     "遠端工作政策有哪些內容？",
#     "在家辦公需要遵守什麼規則？",
#     "公司允許員工 work from home 嗎？"
# ]
```

**效果對比**：

| 查詢方式 | 召回的文件數 | 相關文件數 | 召回率 |
|----------|--------------|------------|--------|
| 原始查詢 | 3 | 1 | 33% |
| 多查詢改寫 | 8 | 5 | 63% |

### ‹3› Query Decomposition 應用場景

```python
# 複雜查詢分解範例
complex_query = "比較 2024 年 Q3 和 Q4 的銷售額，分析增長原因"

sub_queries = await rewriter.query_decomposition(complex_query)
# 輸出:
# [
#     "2024 年 Q3 的銷售額是多少？",
#     "2024 年 Q4 的銷售額是多少？",
#     "2024 年下半年銷售增長的原因是什麼？"
# ]
```

---

## 2.3 技術 2：混合檢索策略

向量搜尋雖然強大，但對於精確匹配（如產品編號、人名）效果不佳。混合檢索結合了關鍵字搜尋和向量搜尋的優勢。

### ‹1› BM25 關鍵字搜尋

**BM25** 是傳統資訊檢索的黃金標準算法，基於詞頻（TF）和逆文件頻率（IDF）。

```python
# hybrid_search.py
"""
混合檢索模組
"""

from rank_bm25 import BM25Okapi
import jieba  # 中文分詞
from typing import List, Tuple
import numpy as np


class BM25Retriever:
    """
    BM25 關鍵字檢索器
    ‹1› 適合精確匹配場景
    """

    def __init__(self, documents: List[str]):
        # ‹2› 中文分詞處理
        self.tokenized_docs = [
            list(jieba.cut(doc)) for doc in documents
        ]
        self.bm25 = BM25Okapi(self.tokenized_docs)
        self.documents = documents

    def search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        """
        BM25 搜尋
        ‹3› 返回文件和 BM25 分數
        """
        tokenized_query = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_query)

        # 獲取 Top-K
        top_indices = np.argsort(scores)[::-1][:k]

        results = [
            (self.documents[i], float(scores[i]))
            for i in top_indices
            if scores[i] > 0
        ]

        return results
```

### ‹2› Dense Vector Search

```python
class DenseRetriever:
    """
    稠密向量檢索器
    ‹4› 使用預訓練的 Embedding 模型
    """

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        """
        向量相似度搜尋
        ‹5› 返回文件和餘弦相似度分數
        """
        results = self.vector_store.similarity_search_with_score(query, k=k)

        # ChromaDB 返回的是距離，需要轉換為相似度
        return [
            (doc.page_content, 1 - distance)  # distance → similarity
            for doc, distance in results
        ]
```

### ‹3› Hybrid Fusion 算法

```python
class HybridRetriever:
    """
    混合檢索器
    ‹6› 結合 BM25 和向量搜尋
    """

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        dense_retriever: DenseRetriever,
        alpha: float = 0.5  # ‹7› BM25 的權重
    ):
        self.bm25 = bm25_retriever
        self.dense = dense_retriever
        self.alpha = alpha

    def search(
        self,
        query: str,
        k: int = 5,
        fusion_method: str = "weighted_sum"
    ) -> List[Tuple[str, float]]:
        """
        混合搜尋
        ‹8› 支援多種融合策略
        """
        # 分別搜尋
        bm25_results = self.bm25.search(query, k=k*2)
        dense_results = self.dense.search(query, k=k*2)

        if fusion_method == "weighted_sum":
            return self._weighted_sum_fusion(bm25_results, dense_results, k)
        elif fusion_method == "rrf":
            return self._reciprocal_rank_fusion(bm25_results, dense_results, k)
        else:
            raise ValueError(f"Unknown fusion method: {fusion_method}")

    def _weighted_sum_fusion(
        self,
        bm25_results: List[Tuple[str, float]],
        dense_results: List[Tuple[str, float]],
        k: int
    ) -> List[Tuple[str, float]]:
        """
        加權求和融合
        ‹9› 簡單但需要分數歸一化
        """
        # 歸一化 BM25 分數到 [0, 1]
        bm25_dict = {}
        if bm25_results:
            max_bm25 = max(score for _, score in bm25_results)
            bm25_dict = {
                doc: score / max_bm25 if max_bm25 > 0 else 0
                for doc, score in bm25_results
            }

        # Dense 分數已經在 [0, 1]
        dense_dict = {doc: score for doc, score in dense_results}

        # 合併所有文件
        all_docs = set(bm25_dict.keys()) | set(dense_dict.keys())

        # 計算融合分數
        fused_scores = []
        for doc in all_docs:
            bm25_score = bm25_dict.get(doc, 0)
            dense_score = dense_dict.get(doc, 0)
            fused = self.alpha * bm25_score + (1 - self.alpha) * dense_score
            fused_scores.append((doc, fused))

        # 排序並返回 Top-K
        fused_scores.sort(key=lambda x: x[1], reverse=True)
        return fused_scores[:k]

    def _reciprocal_rank_fusion(
        self,
        bm25_results: List[Tuple[str, float]],
        dense_results: List[Tuple[str, float]],
        k: int,
        rrf_k: int = 60  # ‹10› RRF 常數，通常設為 60
    ) -> List[Tuple[str, float]]:
        """
        Reciprocal Rank Fusion (RRF)
        ‹11› 基於排名而非分數的融合方法
        公式: score = Σ(1 / (k + rank_i))
        """
        rrf_scores = {}

        # BM25 的排名貢獻
        for rank, (doc, _) in enumerate(bm25_results, start=1):
            rrf_scores[doc] = rrf_scores.get(doc, 0) + 1 / (rrf_k + rank)

        # Dense 的排名貢獻
        for rank, (doc, _) in enumerate(dense_results, start=1):
            rrf_scores[doc] = rrf_scores.get(doc, 0) + 1 / (rrf_k + rank)

        # 排序
        sorted_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_results[:k]
```

**為什麼選擇 RRF？**

| 融合方法 | 優點 | 缺點 |
|----------|------|------|
| 加權求和 | 直觀，可調參數 | 需要分數歸一化，對異常值敏感 |
| RRF | 不需歸一化，穩定 | 無法調整權重 |
| 學習型融合 | 最優結果 | 需要標註資料訓練 |

---

## 2.4 技術 3：重排序機制

檢索階段追求「高召回」，而重排序階段追求「高精度」。重排序使用更複雜的模型對候選結果進行精細排序。

### ‹1› Cross-Encoder Reranking

**原理**：Cross-Encoder 將查詢和文件拼接後一起輸入模型，讓模型直接判斷相關性分數。

```mermaid
graph LR
    subgraph "Bi-Encoder (檢索)"
        A1[Query] --> B1[Encoder]
        A2[Doc] --> B2[Encoder]
        B1 --> C1[Cosine Sim]
        B2 --> C1
    end

    subgraph "Cross-Encoder (重排序)"
        D1["[CLS] Query [SEP] Doc [SEP]"] --> E1[Encoder]
        E1 --> F1[Relevance Score]
    end
```

```python
# reranker.py
"""
重排序模組
"""

from sentence_transformers import CrossEncoder
from typing import List, Tuple


class CrossEncoderReranker:
    """
    Cross-Encoder 重排序器
    ‹1› 使用交叉編碼器精細排序
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        # ‹2› 載入預訓練的重排序模型
        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        重排序文件
        ‹3› 返回重新排序後的文件和分數
        """
        if not documents:
            return []

        # ‹4› 構建 [query, doc] 對
        pairs = [[query, doc] for doc in documents]

        # ‹5› 預測相關性分數
        scores = self.model.predict(pairs)

        # ‹6› 組合並排序
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        return doc_scores[:top_k]
```

### ‹2› LLM-based Reranking

當 Cross-Encoder 效果不夠好時，可以使用 LLM 進行重排序。

```python
class LLMReranker:
    """
    LLM-based 重排序器
    ‹7› 使用 LLM 的推理能力進行排序
    """

    def __init__(self, llm: ChatOpenAI = None):
        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        使用 LLM 重排序
        ‹8› 讓 LLM 評估每個文件的相關性
        """
        prompt = ChatPromptTemplate.from_template("""
請評估以下文件與查詢的相關性，並給出 0-10 的分數。

查詢: {query}

文件:
{document}

請只輸出一個數字（0-10），表示相關性分數。
10 = 完全相關，0 = 完全不相關
""")

        results = []

        for doc in documents:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "query": query,
                "document": doc[:500]  # ‹9› 截斷以控制成本
            })

            try:
                score = float(response.content.strip())
                score = max(0, min(10, score)) / 10  # 歸一化到 [0, 1]
            except ValueError:
                score = 0.5

            results.append((doc, score))

        # 排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
```

**Cross-Encoder vs LLM Reranking**：

| 維度 | Cross-Encoder | LLM Reranking |
|------|---------------|---------------|
| 延遲 | ~10ms/doc | ~500ms/doc |
| 成本 | 幾乎免費（本地） | $0.001/doc（GPT-4o-mini） |
| 品質 | 好 | 最好 |
| 適用場景 | 大量候選文件 | 少量高價值候選 |

**最佳實踐**：兩階段重排序
1. 先用 Cross-Encoder 從 Top-50 篩選到 Top-10
2. 再用 LLM 從 Top-10 精選 Top-5

---

## 2.5 實作：整合三大優化技術

現在讓我們將查詢改寫、混合檢索、重排序整合成一個完整的 Advanced RAG 系統。

```python
# advanced_rag_pipeline.py
"""
Advanced RAG Pipeline
‹1› 整合所有優化技術
"""

from typing import List, Dict, Any
import asyncio


class AdvancedRAGPipeline:
    """
    進階 RAG 管線
    ‹2› 四階段處理流程
    """

    def __init__(
        self,
        query_rewriter: QueryRewriter,
        hybrid_retriever: HybridRetriever,
        reranker: CrossEncoderReranker,
        llm: ChatOpenAI
    ):
        self.rewriter = query_rewriter
        self.retriever = hybrid_retriever
        self.reranker = reranker
        self.llm = llm

        self.prompt_template = ChatPromptTemplate.from_template("""
基於以下參考文件回答問題。

參考文件:
{context}

問題: {question}

回答:
""")

    async def process(
        self,
        query: str,
        use_query_rewrite: bool = True,
        use_hybrid_search: bool = True,
        use_rerank: bool = True,
        retrieval_k: int = 20,
        final_k: int = 5
    ) -> Dict[str, Any]:
        """
        完整的 RAG 處理流程
        ‹3› 每個優化步驟可以獨立開關
        """
        pipeline_stats = {
            "original_query": query,
            "steps": []
        }

        # ========== 階段 1: 查詢改寫 ==========
        if use_query_rewrite:
            expanded_queries = await self.rewriter.multi_query_rewrite(query)
            pipeline_stats["steps"].append({
                "name": "query_rewrite",
                "input": query,
                "output": expanded_queries
            })
        else:
            expanded_queries = [query]

        # ========== 階段 2: 檢索 ==========
        all_candidates = []

        for q in expanded_queries:
            if use_hybrid_search:
                results = self.retriever.search(q, k=retrieval_k, fusion_method="rrf")
            else:
                results = self.retriever.dense.search(q, k=retrieval_k)

            all_candidates.extend(results)

        # 去重
        seen = set()
        unique_candidates = []
        for doc, score in all_candidates:
            if doc not in seen:
                seen.add(doc)
                unique_candidates.append((doc, score))

        pipeline_stats["steps"].append({
            "name": "retrieval",
            "candidates_count": len(unique_candidates)
        })

        # ========== 階段 3: 重排序 ==========
        if use_rerank and unique_candidates:
            docs_to_rerank = [doc for doc, _ in unique_candidates[:50]]  # ‹4› 限制重排序數量
            reranked = self.reranker.rerank(query, docs_to_rerank, top_k=final_k)
            final_docs = [doc for doc, _ in reranked]

            pipeline_stats["steps"].append({
                "name": "rerank",
                "input_count": len(docs_to_rerank),
                "output_count": len(final_docs)
            })
        else:
            final_docs = [doc for doc, _ in unique_candidates[:final_k]]

        # ========== 階段 4: 生成 ==========
        context = "\n\n---\n\n".join(final_docs)

        chain = self.prompt_template | self.llm | StrOutputParser()
        answer = await chain.ainvoke({
            "context": context,
            "question": query
        })

        return {
            "query": query,
            "answer": answer,
            "sources": final_docs,
            "pipeline_stats": pipeline_stats
        }
```

---

## 2.6 評估框架：如何量化檢索品質

「沒有量化，就沒有改進。」讓我們建立一個嚴謹的評估框架。

### 2.6.1 核心評估指標

**Hit Rate@K（命中率）**

在 Top-K 結果中是否包含相關文件？

```
Hit Rate@5 = 有多少查詢的 Top-5 結果中包含正確答案 / 總查詢數
```

**MRR（Mean Reciprocal Rank，平均倒數排名）**

正確答案排在第幾位？

```
RR = 1 / (正確答案的排名)
MRR = 所有查詢的 RR 平均值

例如：
- 正確答案排在第 1 位: RR = 1/1 = 1.0
- 正確答案排在第 3 位: RR = 1/3 = 0.33
- 正確答案不在 Top-K: RR = 0
```

**NDCG（Normalized Discounted Cumulative Gain）**

考慮排名位置的加權相關性分數。

```python
# evaluation.py
"""
RAG 評估框架
"""

from typing import List, Dict, Any
import numpy as np


class RAGEvaluator:
    """
    RAG 系統評估器
    ‹1› 計算標準檢索評估指標
    """

    def hit_rate_at_k(
        self,
        retrieved_docs: List[List[str]],
        relevant_docs: List[List[str]],
        k: int = 5
    ) -> float:
        """
        計算 Hit Rate@K
        ‹2› 評估召回能力
        """
        hits = 0

        for retrieved, relevant in zip(retrieved_docs, relevant_docs):
            top_k = set(retrieved[:k])
            relevant_set = set(relevant)

            if top_k & relevant_set:  # 有交集
                hits += 1

        return hits / len(retrieved_docs)

    def mrr_at_k(
        self,
        retrieved_docs: List[List[str]],
        relevant_docs: List[List[str]],
        k: int = 10
    ) -> float:
        """
        計算 MRR@K
        ‹3› 評估排序品質
        """
        reciprocal_ranks = []

        for retrieved, relevant in zip(retrieved_docs, relevant_docs):
            relevant_set = set(relevant)

            for rank, doc in enumerate(retrieved[:k], start=1):
                if doc in relevant_set:
                    reciprocal_ranks.append(1 / rank)
                    break
            else:
                reciprocal_ranks.append(0)

        return np.mean(reciprocal_ranks)

    def ndcg_at_k(
        self,
        retrieved_docs: List[List[str]],
        relevant_docs: List[List[str]],
        relevance_scores: List[Dict[str, float]] = None,
        k: int = 10
    ) -> float:
        """
        計算 NDCG@K
        ‹4› 考慮位置折扣的相關性評估
        """
        ndcg_scores = []

        for i, (retrieved, relevant) in enumerate(zip(retrieved_docs, relevant_docs)):
            # 如果沒有提供相關性分數，使用二元相關性
            if relevance_scores:
                scores = relevance_scores[i]
            else:
                scores = {doc: 1.0 for doc in relevant}

            # 計算 DCG
            dcg = 0
            for rank, doc in enumerate(retrieved[:k], start=1):
                rel = scores.get(doc, 0)
                dcg += rel / np.log2(rank + 1)

            # 計算 IDCG (理想排序的 DCG)
            ideal_rels = sorted(scores.values(), reverse=True)[:k]
            idcg = sum(
                rel / np.log2(rank + 1)
                for rank, rel in enumerate(ideal_rels, start=1)
            )

            # NDCG
            ndcg = dcg / idcg if idcg > 0 else 0
            ndcg_scores.append(ndcg)

        return np.mean(ndcg_scores)
```

### 2.6.2 建立評估資料集

```python
# 評估資料集範例
evaluation_dataset = [
    {
        "query": "公司的遠端工作政策是什麼？",
        "relevant_docs": [
            "remote_work_policy.md",
            "hr_handbook_chapter5.pdf"
        ],
        "expected_answer_contains": ["提前3天", "VPN"]
    },
    {
        "query": "新員工入職需要準備什麼？",
        "relevant_docs": [
            "onboarding_guide.pdf"
        ],
        "expected_answer_contains": ["身份證", "銀行帳戶"]
    },
    # ... 更多測試案例
]
```

---

## 2.7 實驗結果分析

我們在 50 個測試查詢上比較了不同配置的效果：

### 實驗設置

- **測試集**：50 個企業知識問答
- **知識庫**：200 份企業文件（約 10 萬字）
- **評估指標**：MRR@10, NDCG@10, Hit Rate@10

### 實驗結果

| 檢索策略 | MRR@10 | NDCG@10 | Hit Rate@10 | 平均延遲 (ms) |
|----------|--------|---------|-------------|---------------|
| Naive RAG (基準) | 0.42 | 0.38 | 0.65 | 120 |
| + Query Rewriting | 0.51 | 0.47 | 0.72 | 180 |
| + Hybrid Search | 0.58 | 0.53 | 0.78 | 240 |
| + Reranking | **0.64** | **0.61** | **0.84** | 380 |

### 關鍵發現

1. **查詢改寫**提升了 21% 的 MRR，主要解決了同義詞問題
2. **混合檢索**在包含專有名詞的查詢上效果顯著
3. **重排序**將 Hit Rate 從 78% 提升到 84%，但增加了 140ms 延遲
4. **總體提升**：MRR 從 0.42 提升到 0.64（+52%）

### 延遲 vs 品質權衡

```mermaid
graph LR
    A[Naive RAG<br/>120ms, MRR=0.42] --> B[+ Rewrite<br/>180ms, MRR=0.51]
    B --> C[+ Hybrid<br/>240ms, MRR=0.58]
    C --> D[+ Rerank<br/>380ms, MRR=0.64]

    style A fill:#f99
    style D fill:#9f9
```

**建議**：
- **即時場景**（<200ms）：使用 Naive RAG + 小幅查詢優化
- **標準場景**（<500ms）：使用完整優化管線
- **批次場景**（無延遲要求）：可加入 LLM Reranking 追求最高品質

---

## 2.8 總結與下一步

### 本章回顧

在本章中，我們：

1. **診斷了 Naive RAG 的三大痛點**：低召回、檢索噪音、語義漂移
2. **掌握了三大優化技術**：
   - 查詢改寫（HyDE、Multi-Query、Query Decomposition）
   - 混合檢索（BM25 + Dense + RRF 融合）
   - 重排序（Cross-Encoder、LLM-based）
3. **建立了評估框架**：MRR、NDCG、Hit Rate
4. **實現了 52% 的效能提升**：MRR 從 0.42 到 0.64

### 關鍵決策說明

| 決策點 | 選擇 | 原因 |
|--------|------|------|
| 融合方法 | RRF | 不需歸一化，穩定可靠 |
| 重排序模型 | Cross-Encoder | 平衡品質與延遲 |
| 查詢擴展數量 | 3 個 | 超過 3 個邊際效益遞減 |

### 下一章預告

在第 3 章「企業級向量資料庫選型與部署」中，我們將：

- 深入比較 Pinecone、Weaviate、Qdrant、Milvus 的效能
- 進行百萬級向量的壓力測試
- 設計高可用的生產環境部署方案
- 計算不同方案的 TCO（總擁有成本）

---

## 本章程式碼清單

| 檔案 | 說明 |
|------|------|
| `advanced_rag.py` | 查詢改寫模組 |
| `hybrid_search.py` | 混合檢索模組 |
| `reranker.py` | 重排序模組 |
| `advanced_rag_pipeline.py` | 整合管線 |
| `evaluation.py` | 評估框架 |

完整程式碼請參見 `code-examples/chapter-02/` 目錄。
