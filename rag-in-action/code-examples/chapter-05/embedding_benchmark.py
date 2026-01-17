"""
chapter-05/embedding_benchmark.py

Embedding 模型評估框架

本模組提供標準化的 Embedding 模型評估流程，
支援多維度指標計算和視覺化比較。

評估維度：
1. 精準度 - 檢索效果（Precision, Recall, MRR）
2. 速度 - 編碼速度（tokens/sec）
3. 資源 - 記憶體使用量、模型大小

使用方式：
    from embedding_benchmark import EmbeddingBenchmark
    benchmark = EmbeddingBenchmark()
    results = benchmark.run_all()

依賴安裝：
    pip install sentence-transformers numpy scikit-learn pandas rich tqdm
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import time
import gc
import os
import psutil

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from tqdm import tqdm

console = Console()


@dataclass
class BenchmarkQuery:
    """評估用查詢"""
    query: str
    relevant_docs: List[int]  # 相關文件的索引
    category: str = "general"


@dataclass
class EmbeddingModelConfig:
    """Embedding 模型配置"""
    name: str
    model_id: str
    dimension: int
    max_seq_length: int
    description: str
    is_multilingual: bool = False
    provider: str = "open_source"


@dataclass
class BenchmarkResult:
    """評估結果"""
    model_name: str
    model_id: str
    dimension: int

    # 精準度指標
    precision_at_1: float = 0.0
    precision_at_3: float = 0.0
    precision_at_5: float = 0.0
    recall_at_5: float = 0.0
    mrr: float = 0.0
    ndcg_at_5: float = 0.0

    # 速度指標
    encoding_speed: float = 0.0  # tokens per second
    avg_encode_time_ms: float = 0.0

    # 資源指標
    model_size_mb: float = 0.0
    memory_usage_mb: float = 0.0
    load_time_sec: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "model_name": self.model_name,
            "model_id": self.model_id,
            "dimension": self.dimension,
            "precision_at_1": round(self.precision_at_1, 4),
            "precision_at_3": round(self.precision_at_3, 4),
            "precision_at_5": round(self.precision_at_5, 4),
            "recall_at_5": round(self.recall_at_5, 4),
            "mrr": round(self.mrr, 4),
            "ndcg_at_5": round(self.ndcg_at_5, 4),
            "encoding_speed": round(self.encoding_speed, 2),
            "avg_encode_time_ms": round(self.avg_encode_time_ms, 2),
            "model_size_mb": round(self.model_size_mb, 2),
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "load_time_sec": round(self.load_time_sec, 2),
        }


# 預定義的候選模型列表
CANDIDATE_MODELS: List[EmbeddingModelConfig] = [
    EmbeddingModelConfig(
        name="MiniLM-L6",
        model_id="all-MiniLM-L6-v2",
        dimension=384,
        max_seq_length=256,
        description="輕量級英文模型，速度快",
        is_multilingual=False,
        provider="open_source"
    ),
    EmbeddingModelConfig(
        name="MiniLM-L12",
        model_id="all-MiniLM-L12-v2",
        dimension=384,
        max_seq_length=256,
        description="MiniLM 加強版，精度更高",
        is_multilingual=False,
        provider="open_source"
    ),
    EmbeddingModelConfig(
        name="MPNet-base",
        model_id="all-mpnet-base-v2",
        dimension=768,
        max_seq_length=384,
        description="通用英文模型，品質最佳",
        is_multilingual=False,
        provider="open_source"
    ),
    EmbeddingModelConfig(
        name="Multilingual-MiniLM",
        model_id="paraphrase-multilingual-MiniLM-L12-v2",
        dimension=384,
        max_seq_length=128,
        description="多語言輕量模型，支援 50+ 語言",
        is_multilingual=True,
        provider="open_source"
    ),
    EmbeddingModelConfig(
        name="Multilingual-MPNet",
        model_id="paraphrase-multilingual-mpnet-base-v2",
        dimension=768,
        max_seq_length=128,
        description="多語言重量級模型",
        is_multilingual=True,
        provider="open_source"
    ),
    EmbeddingModelConfig(
        name="E5-small",
        model_id="intfloat/e5-small-v2",
        dimension=384,
        max_seq_length=512,
        description="E5 系列輕量版",
        is_multilingual=False,
        provider="open_source"
    ),
    EmbeddingModelConfig(
        name="E5-base",
        model_id="intfloat/e5-base-v2",
        dimension=768,
        max_seq_length=512,
        description="E5 系列基礎版",
        is_multilingual=False,
        provider="open_source"
    ),
    EmbeddingModelConfig(
        name="E5-multilingual",
        model_id="intfloat/multilingual-e5-base",
        dimension=768,
        max_seq_length=512,
        description="E5 多語言版本",
        is_multilingual=True,
        provider="open_source"
    ),
    EmbeddingModelConfig(
        name="BGE-small-zh",
        model_id="BAAI/bge-small-zh-v1.5",
        dimension=512,
        max_seq_length=512,
        description="中文專用輕量模型",
        is_multilingual=False,
        provider="open_source"
    ),
    EmbeddingModelConfig(
        name="BGE-base-zh",
        model_id="BAAI/bge-base-zh-v1.5",
        dimension=768,
        max_seq_length=512,
        description="中文專用基礎模型",
        is_multilingual=False,
        provider="open_source"
    ),
]


class EmbeddingBenchmark:
    """
    Embedding 模型評估器

    提供標準化的評估流程，支援：
    1. 模型載入和資源監控
    2. 編碼速度測試
    3. 檢索品質評估
    4. 結果比較和視覺化
    """

    def __init__(
        self,
        documents: Optional[List[str]] = None,
        queries: Optional[List[BenchmarkQuery]] = None
    ):
        """
        初始化評估器

        Args:
            documents: 測試文件集
            queries: 測試查詢集
        """
        self.documents = documents or self._get_default_documents()
        self.queries = queries or self._get_default_queries()
        self.results: Dict[str, BenchmarkResult] = {}

    def _get_default_documents(self) -> List[str]:
        """取得預設測試文件"""
        return [
            "如何重設密碼？請點擊登入頁面的「忘記密碼」連結，輸入您的電子郵件地址，系統將寄送重設連結。",
            "如何變更電子郵件地址？請登入後進入「帳戶設定」>「個人資料」，即可修改電子郵件。",
            "如何啟用雙重驗證（2FA）？進入「帳戶設定」>「安全性」，點擊「啟用雙重驗證」。",
            "如何刪除帳戶？請聯繫客服團隊 support@techcorp.com，我們將在 5 個工作日內處理。",
            "支援哪些付款方式？我們支援信用卡（Visa、MasterCard）、銀行轉帳、PayPal。",
            "如何取消訂閱？進入「訂閱管理」>「取消訂閱」。取消後仍可使用至當期結束。",
            "檔案上傳大小限制？免費版單檔上限 10MB，專業版上限 100MB。",
            "App 閃退怎麼辦？請確認已更新至最新版本，若問題持續請清除快取。",
            "API 請求頻率限制？免費版每分鐘 60 次，專業版 600 次。",
            "如何取得 API 金鑰？登入後進入「開發者設定」>「API 金鑰」。",
            "資料存放在哪裡？所有資料儲存在 AWS 東京區域，符合 ISO 27001 認證。",
            "如何聯繫客服？Email: support@techcorp.com 或線上客服（週一至週五）。",
        ]

    def _get_default_queries(self) -> List[BenchmarkQuery]:
        """取得預設測試查詢"""
        return [
            BenchmarkQuery(
                query="密碼忘記了怎麼辦",
                relevant_docs=[0],
                category="account"
            ),
            BenchmarkQuery(
                query="怎麼改 email",
                relevant_docs=[1],
                category="account"
            ),
            BenchmarkQuery(
                query="2FA 設定方法",
                relevant_docs=[2],
                category="security"
            ),
            BenchmarkQuery(
                query="想要刪除帳號",
                relevant_docs=[3],
                category="account"
            ),
            BenchmarkQuery(
                query="可以用什麼方式付款",
                relevant_docs=[4],
                category="payment"
            ),
            BenchmarkQuery(
                query="怎麼停止訂閱",
                relevant_docs=[5],
                category="subscription"
            ),
            BenchmarkQuery(
                query="上傳檔案有大小限制嗎",
                relevant_docs=[6],
                category="technical"
            ),
            BenchmarkQuery(
                query="手機 App 一直當掉",
                relevant_docs=[7],
                category="technical"
            ),
            BenchmarkQuery(
                query="API 有流量限制嗎",
                relevant_docs=[8],
                category="api"
            ),
            BenchmarkQuery(
                query="怎麼拿到 API key",
                relevant_docs=[9],
                category="api"
            ),
        ]

    def evaluate_model(
        self,
        config: EmbeddingModelConfig,
        verbose: bool = True
    ) -> BenchmarkResult:
        """
        評估單一模型

        Args:
            config: 模型配置
            verbose: 是否顯示詳細資訊

        Returns:
            BenchmarkResult 評估結果
        """
        if verbose:
            console.print(f"\n[bold blue]評估模型: {config.name}[/bold blue]")

        result = BenchmarkResult(
            model_name=config.name,
            model_id=config.model_id,
            dimension=config.dimension
        )

        # 1. 載入模型（測量載入時間和記憶體）
        gc.collect()
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024

        load_start = time.time()
        try:
            model = SentenceTransformer(config.model_id)                # ‹1›
        except Exception as e:
            console.print(f"[red]載入失敗: {e}[/red]")
            return result

        result.load_time_sec = time.time() - load_start
        memory_after = psutil.Process().memory_info().rss / 1024 / 1024
        result.memory_usage_mb = memory_after - memory_before

        if verbose:
            console.print(f"  載入時間: {result.load_time_sec:.2f}s")
            console.print(f"  記憶體增量: {result.memory_usage_mb:.1f}MB")

        # 2. 測量編碼速度
        speed_result = self._measure_encoding_speed(model, verbose)     # ‹2›
        result.encoding_speed = speed_result["tokens_per_sec"]
        result.avg_encode_time_ms = speed_result["avg_time_ms"]

        # 3. 計算檢索指標
        retrieval_metrics = self._evaluate_retrieval(model, verbose)    # ‹3›
        result.precision_at_1 = retrieval_metrics["precision_at_1"]
        result.precision_at_3 = retrieval_metrics["precision_at_3"]
        result.precision_at_5 = retrieval_metrics["precision_at_5"]
        result.recall_at_5 = retrieval_metrics["recall_at_5"]
        result.mrr = retrieval_metrics["mrr"]
        result.ndcg_at_5 = retrieval_metrics["ndcg_at_5"]

        # 4. 估算模型大小
        try:
            model_path = model._modules['0'].auto_model.config._name_or_path
            result.model_size_mb = result.memory_usage_mb * 0.8  # 粗略估算
        except:
            result.model_size_mb = result.memory_usage_mb * 0.8

        # 清理記憶體
        del model
        gc.collect()

        self.results[config.name] = result
        return result

    def _measure_encoding_speed(
        self,
        model: SentenceTransformer,
        verbose: bool
    ) -> Dict:
        """測量編碼速度"""
        # 準備測試文本
        test_texts = self.documents * 10  # 重複以獲得穩定的測量
        total_tokens = sum(len(t.split()) for t in test_texts)

        # 熱身
        _ = model.encode(test_texts[:5])

        # 正式測量
        times = []
        for _ in range(3):
            start = time.time()
            _ = model.encode(test_texts, show_progress_bar=False)
            times.append(time.time() - start)

        avg_time = np.mean(times)
        tokens_per_sec = total_tokens / avg_time

        if verbose:
            console.print(f"  編碼速度: {tokens_per_sec:.0f} tokens/s")

        return {
            "tokens_per_sec": tokens_per_sec,
            "avg_time_ms": (avg_time / len(test_texts)) * 1000
        }

    def _evaluate_retrieval(
        self,
        model: SentenceTransformer,
        verbose: bool
    ) -> Dict:
        """評估檢索效果"""
        # 編碼文件
        doc_embeddings = model.encode(self.documents, show_progress_bar=False)

        precision_at_1, precision_at_3, precision_at_5 = [], [], []
        recall_at_5_scores = []
        reciprocal_ranks = []
        ndcg_at_5_scores = []

        for query in self.queries:
            # 編碼查詢
            query_embedding = model.encode(query.query)

            # 計算相似度
            similarities = cosine_similarity(
                query_embedding.reshape(1, -1),
                doc_embeddings
            )[0]

            # 排序
            ranked_indices = np.argsort(similarities)[::-1]

            # 計算指標
            relevant_set = set(query.relevant_docs)

            # Precision@k
            top_1 = set(ranked_indices[:1])
            top_3 = set(ranked_indices[:3])
            top_5 = set(ranked_indices[:5])

            precision_at_1.append(len(top_1 & relevant_set) / 1)
            precision_at_3.append(len(top_3 & relevant_set) / 3)
            precision_at_5.append(len(top_5 & relevant_set) / 5)

            # Recall@5
            recall_at_5_scores.append(
                len(top_5 & relevant_set) / len(relevant_set)
            )

            # MRR
            for rank, idx in enumerate(ranked_indices, 1):
                if idx in relevant_set:
                    reciprocal_ranks.append(1 / rank)
                    break
            else:
                reciprocal_ranks.append(0)

            # NDCG@5
            ndcg = self._compute_ndcg(ranked_indices[:5], relevant_set)
            ndcg_at_5_scores.append(ndcg)

        metrics = {
            "precision_at_1": np.mean(precision_at_1),
            "precision_at_3": np.mean(precision_at_3),
            "precision_at_5": np.mean(precision_at_5),
            "recall_at_5": np.mean(recall_at_5_scores),
            "mrr": np.mean(reciprocal_ranks),
            "ndcg_at_5": np.mean(ndcg_at_5_scores),
        }

        if verbose:
            console.print(f"  Precision@1: {metrics['precision_at_1']:.3f}")
            console.print(f"  MRR: {metrics['mrr']:.3f}")
            console.print(f"  NDCG@5: {metrics['ndcg_at_5']:.3f}")

        return metrics

    def _compute_ndcg(
        self,
        ranked_indices: np.ndarray,
        relevant_set: set
    ) -> float:
        """計算 NDCG"""
        # DCG
        dcg = 0
        for i, idx in enumerate(ranked_indices):
            if idx in relevant_set:
                dcg += 1 / np.log2(i + 2)  # i+2 因為 log2(1) = 0

        # IDCG (理想情況)
        idcg = sum(1 / np.log2(i + 2) for i in range(len(relevant_set)))

        return dcg / idcg if idcg > 0 else 0

    def run_all(
        self,
        models: Optional[List[EmbeddingModelConfig]] = None,
        verbose: bool = True
    ) -> Dict[str, BenchmarkResult]:
        """
        評估所有模型

        Args:
            models: 要評估的模型列表（預設使用 CANDIDATE_MODELS）
            verbose: 是否顯示詳細資訊

        Returns:
            模型名稱到評估結果的映射
        """
        models = models or CANDIDATE_MODELS

        console.print(Panel(
            f"[bold]Embedding 模型評估[/bold]\n\n"
            f"文件數: {len(self.documents)}\n"
            f"查詢數: {len(self.queries)}\n"
            f"候選模型: {len(models)}",
            title="Benchmark 配置",
            border_style="blue"
        ))

        for config in models:
            try:
                self.evaluate_model(config, verbose)
            except Exception as e:
                console.print(f"[red]評估 {config.name} 時發生錯誤: {e}[/red]")

        return self.results

    def display_results(self) -> None:
        """顯示評估結果"""
        if not self.results:
            console.print("[yellow]尚無評估結果[/yellow]")
            return

        console.print("\n")
        console.print(Panel(
            "[bold]Embedding 模型評估報告[/bold]",
            border_style="green"
        ))

        # 精準度指標表
        console.print("\n[bold cyan]1. 精準度指標[/bold cyan]\n")

        table1 = Table(show_header=True, header_style="bold")
        table1.add_column("模型", style="cyan", width=20)
        table1.add_column("P@1", justify="right")
        table1.add_column("P@3", justify="right")
        table1.add_column("P@5", justify="right")
        table1.add_column("R@5", justify="right")
        table1.add_column("MRR", justify="right")
        table1.add_column("NDCG@5", justify="right")

        # 按 MRR 排序
        sorted_results = sorted(
            self.results.values(),
            key=lambda x: x.mrr,
            reverse=True
        )

        for r in sorted_results:
            mrr_color = "green" if r.mrr > 0.8 else "yellow" if r.mrr > 0.6 else "red"
            table1.add_row(
                r.model_name,
                f"{r.precision_at_1:.3f}",
                f"{r.precision_at_3:.3f}",
                f"{r.precision_at_5:.3f}",
                f"{r.recall_at_5:.3f}",
                f"[{mrr_color}]{r.mrr:.3f}[/{mrr_color}]",
                f"{r.ndcg_at_5:.3f}"
            )

        console.print(table1)

        # 速度和資源指標表
        console.print("\n[bold cyan]2. 速度與資源指標[/bold cyan]\n")

        table2 = Table(show_header=True, header_style="bold")
        table2.add_column("模型", style="cyan", width=20)
        table2.add_column("維度", justify="right")
        table2.add_column("速度 (tok/s)", justify="right")
        table2.add_column("單次編碼 (ms)", justify="right")
        table2.add_column("記憶體 (MB)", justify="right")
        table2.add_column("載入時間 (s)", justify="right")

        # 按速度排序
        sorted_by_speed = sorted(
            self.results.values(),
            key=lambda x: x.encoding_speed,
            reverse=True
        )

        for r in sorted_by_speed:
            speed_color = "green" if r.encoding_speed > 5000 else "yellow" if r.encoding_speed > 2000 else "red"
            table2.add_row(
                r.model_name,
                str(r.dimension),
                f"[{speed_color}]{r.encoding_speed:.0f}[/{speed_color}]",
                f"{r.avg_encode_time_ms:.2f}",
                f"{r.memory_usage_mb:.0f}",
                f"{r.load_time_sec:.2f}"
            )

        console.print(table2)

        # 推薦
        console.print("\n[bold cyan]3. 推薦[/bold cyan]\n")

        best_accuracy = max(self.results.values(), key=lambda x: x.mrr)
        fastest = max(self.results.values(), key=lambda x: x.encoding_speed)
        best_balanced = max(
            self.results.values(),
            key=lambda x: x.mrr * 0.6 + (x.encoding_speed / 10000) * 0.4
        )

        console.print(f"  • 精準度最佳: [green]{best_accuracy.model_name}[/green] (MRR={best_accuracy.mrr:.3f})")
        console.print(f"  • 速度最快: [green]{fastest.model_name}[/green] ({fastest.encoding_speed:.0f} tok/s)")
        console.print(f"  • 綜合最佳: [green]{best_balanced.model_name}[/green]")

    def export_results(self, filepath: str = "benchmark_results.json") -> None:
        """匯出評估結果為 JSON"""
        import json

        export_data = {
            name: result.to_dict()
            for name, result in self.results.items()
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        console.print(f"\n[green]結果已匯出至: {filepath}[/green]")


def main():
    """執行 Embedding 模型評估"""
    console.print("\n[bold]═══ Embedding 模型 Benchmark ═══[/bold]\n")

    # 只測試部分模型以節省時間
    test_models = [
        CANDIDATE_MODELS[0],  # MiniLM-L6
        CANDIDATE_MODELS[3],  # Multilingual-MiniLM
        CANDIDATE_MODELS[5],  # E5-small
    ]

    benchmark = EmbeddingBenchmark()
    benchmark.run_all(models=test_models)
    benchmark.display_results()
    benchmark.export_results()


if __name__ == "__main__":
    main()
