"""
chapter-04/chunking_evaluator.py

Chunking 效果評估框架

本模組提供量化評估不同 Chunking 策略效果的工具，
包含多維度指標計算和視覺化比較功能。

評估維度：
1. 語義完整性 - chunk 內部語義是否連貫
2. 資訊保留率 - 重要資訊是否被保留
3. 檢索效果 - 對 RAG Pipeline 精準度的影響
4. 效率指標 - 切割速度和 chunk 數量

使用方式：
    from chunking_evaluator import ChunkingEvaluator
    evaluator = ChunkingEvaluator()
    results = evaluator.evaluate_all(document, query_set)

依賴安裝：
    pip install sentence-transformers numpy scikit-learn matplotlib pandas rich
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import time
import json

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

from chunking_strategies import (
    ChunkingStrategy,
    ChunkingFactory,
    Chunk,
    BaseChunker
)

console = Console()


@dataclass
class ChunkingMetrics:
    """Chunking 評估指標"""
    strategy: str
    chunk_count: int
    avg_chunk_size: float
    std_chunk_size: float
    min_chunk_size: int
    max_chunk_size: int

    # 語義指標
    semantic_coherence: float = 0.0
    boundary_quality: float = 0.0

    # 檢索指標
    retrieval_precision: float = 0.0
    retrieval_recall: float = 0.0
    retrieval_f1: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank

    # 效率指標
    chunking_time_ms: float = 0.0
    tokens_per_chunk: float = 0.0

    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            "strategy": self.strategy,
            "chunk_count": self.chunk_count,
            "avg_chunk_size": round(self.avg_chunk_size, 2),
            "std_chunk_size": round(self.std_chunk_size, 2),
            "min_chunk_size": self.min_chunk_size,
            "max_chunk_size": self.max_chunk_size,
            "semantic_coherence": round(self.semantic_coherence, 4),
            "boundary_quality": round(self.boundary_quality, 4),
            "retrieval_precision": round(self.retrieval_precision, 4),
            "retrieval_recall": round(self.retrieval_recall, 4),
            "retrieval_f1": round(self.retrieval_f1, 4),
            "mrr": round(self.mrr, 4),
            "chunking_time_ms": round(self.chunking_time_ms, 2),
        }


@dataclass
class EvaluationQuery:
    """評估用的查詢"""
    query: str
    relevant_text: str  # 文件中與查詢相關的原文片段
    expected_answer: Optional[str] = None


@dataclass
class RetrievalResult:
    """檢索結果"""
    chunk_index: int
    score: float
    is_relevant: bool


class ChunkingEvaluator:
    """
    Chunking 策略評估器

    提供多維度的評估指標，幫助選擇最適合的 Chunking 策略

    Attributes:
        embedding_model: 用於計算語義相似度的模型
        chunk_size: 評估時使用的 chunk 大小
        chunk_overlap: 評估時使用的重疊大小
    """

    def __init__(
        self,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        初始化評估器

        Args:
            embedding_model: Embedding 模型名稱
            chunk_size: 目標 chunk 大小
            chunk_overlap: chunk 重疊大小
        """
        console.print("初始化 Chunking 評估器...")
        self.model = SentenceTransformer(embedding_model)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        console.print("[green]✓ 評估器就緒[/green]\n")

    def evaluate_strategy(
        self,
        strategy: ChunkingStrategy,
        document: str,
        queries: Optional[List[EvaluationQuery]] = None,
        **chunker_kwargs
    ) -> ChunkingMetrics:
        """
        評估單一 Chunking 策略

        Args:
            strategy: 要評估的策略
            document: 測試文件
            queries: 評估用的查詢集（可選）
            **chunker_kwargs: 傳遞給 Chunker 的額外參數

        Returns:
            ChunkingMetrics 評估結果
        """
        # 1. 建立 Chunker 並計時
        start_time = time.time()

        # 語義切割需要額外處理，避免重複載入模型
        if strategy == ChunkingStrategy.SEMANTIC:
            chunker_kwargs['embedding_model'] = self.model.get_sentence_embedding_dimension()
            # 這裡簡化處理，實際應該重用模型
            chunker = ChunkingFactory.create(
                strategy,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
        else:
            chunker = ChunkingFactory.create(
                strategy,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                **chunker_kwargs
            )

        # 2. 執行切割
        chunks = chunker.chunk(document)
        chunking_time = (time.time() - start_time) * 1000

        # 3. 計算基礎指標
        chunk_sizes = [chunk.length for chunk in chunks]

        metrics = ChunkingMetrics(
            strategy=strategy.value,
            chunk_count=len(chunks),
            avg_chunk_size=np.mean(chunk_sizes) if chunk_sizes else 0,
            std_chunk_size=np.std(chunk_sizes) if chunk_sizes else 0,
            min_chunk_size=min(chunk_sizes) if chunk_sizes else 0,
            max_chunk_size=max(chunk_sizes) if chunk_sizes else 0,
            chunking_time_ms=chunking_time
        )

        # 4. 計算語義指標
        if len(chunks) > 1:
            metrics.semantic_coherence = self._compute_semantic_coherence(chunks)
            metrics.boundary_quality = self._compute_boundary_quality(chunks)

        # 5. 計算檢索指標（如果提供了查詢集）
        if queries:
            retrieval_metrics = self._compute_retrieval_metrics(chunks, queries)
            metrics.retrieval_precision = retrieval_metrics["precision"]
            metrics.retrieval_recall = retrieval_metrics["recall"]
            metrics.retrieval_f1 = retrieval_metrics["f1"]
            metrics.mrr = retrieval_metrics["mrr"]

        return metrics

    def evaluate_all(
        self,
        document: str,
        queries: Optional[List[EvaluationQuery]] = None,
        strategies: Optional[List[ChunkingStrategy]] = None
    ) -> Dict[str, ChunkingMetrics]:
        """
        評估所有（或指定的）Chunking 策略

        Args:
            document: 測試文件
            queries: 評估用的查詢集
            strategies: 要評估的策略列表（預設全部）

        Returns:
            策略名稱到評估結果的映射
        """
        if strategies is None:
            strategies = [
                ChunkingStrategy.FIXED_SIZE,
                ChunkingStrategy.RECURSIVE,
                ChunkingStrategy.HEADING_BASED,
            ]
            # 語義切割和程式碼切割較慢，可選擇性加入

        results = {}

        with Progress() as progress:
            task = progress.add_task(
                "[cyan]評估 Chunking 策略...",
                total=len(strategies)
            )

            for strategy in strategies:
                try:
                    metrics = self.evaluate_strategy(strategy, document, queries)
                    results[strategy.value] = metrics
                except Exception as e:
                    console.print(f"[red]評估 {strategy.value} 失敗: {e}[/red]")

                progress.update(task, advance=1)

        return results

    def _compute_semantic_coherence(self, chunks: List[Chunk]) -> float:
        """
        計算語義連貫性

        測量每個 chunk 內部的語義一致性。
        分數越高表示 chunk 內的內容越相關。
        """
        coherence_scores = []

        for chunk in chunks:
            # 將 chunk 分成句子
            sentences = [s.strip() for s in chunk.text.split('。') if s.strip()]

            if len(sentences) < 2:
                coherence_scores.append(1.0)  # 單句 chunk 視為完全連貫
                continue

            # 計算句子間的平均相似度
            embeddings = self.model.encode(sentences)
            sim_matrix = cosine_similarity(embeddings)

            # 取上三角矩陣的平均值（排除對角線）
            n = len(sentences)
            total_sim = 0
            count = 0

            for i in range(n):
                for j in range(i + 1, n):
                    total_sim += sim_matrix[i][j]
                    count += 1

            avg_sim = total_sim / count if count > 0 else 1.0
            coherence_scores.append(avg_sim)

        return np.mean(coherence_scores)

    def _compute_boundary_quality(self, chunks: List[Chunk]) -> float:
        """
        計算邊界品質

        測量相鄰 chunk 之間的語義差異。
        分數越高表示切割點選得越好（在語義邊界處切割）。
        """
        if len(chunks) < 2:
            return 1.0

        # 計算每個 chunk 的 Embedding
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.model.encode(chunk_texts)

        # 計算相鄰 chunk 的差異度（1 - 相似度）
        differences = []

        for i in range(len(embeddings) - 1):
            sim = cosine_similarity(
                embeddings[i].reshape(1, -1),
                embeddings[i + 1].reshape(1, -1)
            )[0][0]
            differences.append(1 - sim)

        # 邊界品質 = 平均差異度（差異越大表示切割點越好）
        return np.mean(differences)

    def _compute_retrieval_metrics(
        self,
        chunks: List[Chunk],
        queries: List[EvaluationQuery]
    ) -> Dict[str, float]:
        """
        計算檢索相關指標

        使用向量相似度檢索，評估 chunk 切割對檢索效果的影響
        """
        # 編碼所有 chunk
        chunk_texts = [chunk.text for chunk in chunks]
        chunk_embeddings = self.model.encode(chunk_texts)

        precision_scores = []
        recall_scores = []
        reciprocal_ranks = []

        for eq in queries:
            # 編碼查詢
            query_embedding = self.model.encode(eq.query)

            # 計算相似度
            similarities = cosine_similarity(
                query_embedding.reshape(1, -1),
                chunk_embeddings
            )[0]

            # 排序取 top-k
            top_k = 3
            top_indices = np.argsort(similarities)[-top_k:][::-1]

            # 判斷哪些 chunk 是相關的
            relevant_chunks = []
            for i, chunk in enumerate(chunks):
                # 簡單判斷：如果 chunk 包含查詢的相關文字，則視為相關
                if eq.relevant_text.lower() in chunk.text.lower():
                    relevant_chunks.append(i)

            if not relevant_chunks:
                # 如果沒有明確相關的 chunk，跳過這個查詢
                continue

            # 計算 Precision@k
            relevant_in_top_k = sum(1 for i in top_indices if i in relevant_chunks)
            precision = relevant_in_top_k / top_k
            precision_scores.append(precision)

            # 計算 Recall@k
            recall = relevant_in_top_k / len(relevant_chunks)
            recall_scores.append(recall)

            # 計算 MRR
            for rank, idx in enumerate(top_indices, 1):
                if idx in relevant_chunks:
                    reciprocal_ranks.append(1 / rank)
                    break
            else:
                reciprocal_ranks.append(0)

        # 計算平均值
        precision = np.mean(precision_scores) if precision_scores else 0
        recall = np.mean(recall_scores) if recall_scores else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        mrr = np.mean(reciprocal_ranks) if reciprocal_ranks else 0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "mrr": mrr
        }

    def display_comparison(self, results: Dict[str, ChunkingMetrics]) -> None:
        """美化顯示評估結果比較"""
        console.print("\n")
        console.print(Panel(
            "[bold]Chunking 策略評估報告[/bold]",
            border_style="blue"
        ))

        # 基礎指標表
        console.print("\n[bold cyan]1. 基礎指標[/bold cyan]\n")

        table1 = Table(show_header=True, header_style="bold")
        table1.add_column("策略", style="cyan")
        table1.add_column("Chunk 數", justify="right")
        table1.add_column("平均大小", justify="right")
        table1.add_column("標準差", justify="right")
        table1.add_column("最小", justify="right")
        table1.add_column("最大", justify="right")
        table1.add_column("耗時(ms)", justify="right")

        for name, metrics in results.items():
            table1.add_row(
                name,
                str(metrics.chunk_count),
                f"{metrics.avg_chunk_size:.0f}",
                f"{metrics.std_chunk_size:.0f}",
                str(metrics.min_chunk_size),
                str(metrics.max_chunk_size),
                f"{metrics.chunking_time_ms:.1f}"
            )

        console.print(table1)

        # 語義指標表
        console.print("\n[bold cyan]2. 語義品質指標[/bold cyan]\n")

        table2 = Table(show_header=True, header_style="bold")
        table2.add_column("策略", style="cyan")
        table2.add_column("語義連貫性", justify="right")
        table2.add_column("邊界品質", justify="right")

        for name, metrics in results.items():
            # 使用顏色標示分數高低
            coherence_color = "green" if metrics.semantic_coherence > 0.7 else "yellow" if metrics.semantic_coherence > 0.5 else "red"
            boundary_color = "green" if metrics.boundary_quality > 0.3 else "yellow" if metrics.boundary_quality > 0.2 else "red"

            table2.add_row(
                name,
                f"[{coherence_color}]{metrics.semantic_coherence:.3f}[/{coherence_color}]",
                f"[{boundary_color}]{metrics.boundary_quality:.3f}[/{boundary_color}]"
            )

        console.print(table2)

        # 檢索指標表（如果有）
        has_retrieval = any(m.retrieval_precision > 0 for m in results.values())
        if has_retrieval:
            console.print("\n[bold cyan]3. 檢索效果指標[/bold cyan]\n")

            table3 = Table(show_header=True, header_style="bold")
            table3.add_column("策略", style="cyan")
            table3.add_column("Precision@3", justify="right")
            table3.add_column("Recall@3", justify="right")
            table3.add_column("F1", justify="right")
            table3.add_column("MRR", justify="right")

            for name, metrics in results.items():
                table3.add_row(
                    name,
                    f"{metrics.retrieval_precision:.3f}",
                    f"{metrics.retrieval_recall:.3f}",
                    f"{metrics.retrieval_f1:.3f}",
                    f"{metrics.mrr:.3f}"
                )

            console.print(table3)

        # 推薦
        console.print("\n[bold cyan]4. 策略推薦[/bold cyan]\n")

        # 找出各維度的最佳策略
        best_coherence = max(results.items(), key=lambda x: x[1].semantic_coherence)
        best_boundary = max(results.items(), key=lambda x: x[1].boundary_quality)
        fastest = min(results.items(), key=lambda x: x[1].chunking_time_ms)

        console.print(f"  • 語義連貫性最佳: [green]{best_coherence[0]}[/green] ({best_coherence[1].semantic_coherence:.3f})")
        console.print(f"  • 邊界品質最佳: [green]{best_boundary[0]}[/green] ({best_boundary[1].boundary_quality:.3f})")
        console.print(f"  • 處理速度最快: [green]{fastest[0]}[/green] ({fastest[1].chunking_time_ms:.1f}ms)")

        if has_retrieval:
            best_f1 = max(results.items(), key=lambda x: x[1].retrieval_f1)
            console.print(f"  • 檢索效果最佳: [green]{best_f1[0]}[/green] (F1={best_f1[1].retrieval_f1:.3f})")

    def export_results(
        self,
        results: Dict[str, ChunkingMetrics],
        filepath: str = "chunking_evaluation.json"
    ) -> None:
        """匯出評估結果為 JSON"""
        export_data = {
            name: metrics.to_dict()
            for name, metrics in results.items()
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        console.print(f"\n[green]評估結果已匯出至: {filepath}[/green]")


def create_sample_queries() -> List[EvaluationQuery]:
    """建立範例評估查詢集"""
    return [
        EvaluationQuery(
            query="如何安裝 AskBot？",
            relevant_text="使用 pip 安裝 AskBot SDK"
        ),
        EvaluationQuery(
            query="ask 方法有什麼參數？",
            relevant_text="ask(query: str, top_k: int = 3)"
        ),
        EvaluationQuery(
            query="API 金鑰無效怎麼辦？",
            relevant_text="當 API 金鑰無效時，會拋出 AuthenticationError"
        ),
        EvaluationQuery(
            query="免費方案的限制是什麼？",
            relevant_text="免費方案每月可發送 1000 次查詢"
        ),
    ]


def main():
    """演示 Chunking 評估流程"""
    console.print("\n[bold]═══ Chunking 策略評估演示 ═══[/bold]\n")

    # 測試文件
    sample_document = """# AskBot API 完整指南

## 1. 簡介

AskBot 是一個企業級的 AI 問答系統。它結合了先進的語義搜尋技術和大型語言模型，能夠準確理解使用者的問題並從知識庫中找到相關答案。

本指南將詳細介紹如何使用 AskBot API，包括安裝、配置、基本用法和進階功能。

## 2. 安裝與配置

### 2.1 安裝

使用 pip 安裝 AskBot SDK：

```bash
pip install askbot-sdk
```

如果需要額外的功能，可以安裝完整版本：

```bash
pip install askbot-sdk[full]
```

### 2.2 配置

首先，您需要獲取 API 金鑰。請登入 AskBot 控制台並前往「設定」>「API 金鑰」頁面。

配置環境變數：

```bash
export ASKBOT_API_KEY=your_api_key
```

或者在程式碼中直接設定：

```python
from askbot import AskBot

bot = AskBot(api_key="your_api_key")
```

## 3. 基本用法

### 3.1 發送查詢

使用 `ask()` 方法發送問題：

```python
response = bot.ask("如何重設密碼？")
print(response.answer)
```

`ask(query: str, top_k: int = 3) -> Response` 方法接受以下參數：

- `query`: 使用者的問題字串
- `top_k`: 從知識庫中檢索的文件數量，預設為 3

### 3.2 處理回應

Response 物件包含以下屬性：

- `answer`: AI 生成的回答
- `sources`: 參考的知識庫文件列表
- `confidence`: 回答的信心分數

```python
for source in response.sources:
    print(f"來源: {source.title}")
    print(f"相關度: {source.score}")
```

## 4. 進階功能

### 4.1 對話歷史

AskBot 支援多輪對話。使用 `conversation_id` 參數來維持對話上下文：

```python
response1 = bot.ask("什麼是 RAG？", conversation_id="conv_123")
response2 = bot.ask("它有什麼優點？", conversation_id="conv_123")
```

### 4.2 自訂知識庫

您可以上傳自己的文件到知識庫：

```python
bot.upload_document("manual.pdf", collection="support")
```

支援的格式包括 PDF、Word、Markdown 和純文字。

## 5. 錯誤處理

### 5.1 常見錯誤

當 API 金鑰無效時，會拋出 AuthenticationError。建議使用 try-except 處理各種錯誤：

```python
from askbot.exceptions import AuthenticationError, RateLimitError

try:
    response = bot.ask("問題")
except AuthenticationError:
    print("API 金鑰無效，請檢查設定")
except RateLimitError:
    print("已達到請求限制，請稍後再試")
```

### 5.2 重試機制

SDK 內建了指數退避重試機制。您可以自訂重試策略：

```python
bot = AskBot(
    api_key="your_key",
    max_retries=3,
    retry_delay=1.0
)
```

## 6. 計費與限制

### 6.1 方案比較

- 免費方案：每月可發送 1000 次查詢
- 專業方案：每月 10,000 次查詢，支援自訂知識庫
- 企業方案：無限查詢，專屬支援

### 6.2 速率限制

- 免費方案：每分鐘 10 次請求
- 專業方案：每分鐘 60 次請求
- 企業方案：每分鐘 600 次請求

## 7. 常見問題

Q: AskBot 支援哪些語言？
A: 目前支援中文、英文和日文，更多語言即將推出。

Q: 知識庫最大容量是多少？
A: 免費方案 100MB，專業方案 1GB，企業方案 10GB。

Q: 如何提升回答準確度？
A: 可以透過優化知識庫內容、調整 top_k 參數、使用對話上下文等方式。
"""

    # 建立評估器
    evaluator = ChunkingEvaluator(chunk_size=400, chunk_overlap=50)

    # 建立評估查詢集
    queries = create_sample_queries()

    # 評估所有策略
    results = evaluator.evaluate_all(sample_document, queries)

    # 顯示比較結果
    evaluator.display_comparison(results)

    # 匯出結果
    evaluator.export_results(results, "chunking_evaluation.json")


if __name__ == "__main__":
    main()
