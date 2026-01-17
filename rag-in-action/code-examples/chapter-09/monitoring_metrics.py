"""
chapter-09/monitoring_metrics.py

RAG 系統監控指標定義

本模組定義 RAG 系統的核心監控指標，
使用 Prometheus client 進行指標收集。

使用方式：
    from monitoring_metrics import RAGMetrics
    metrics = RAGMetrics()
    metrics.record_request(latency=0.5, tokens=150)

依賴安裝：
    pip install prometheus-client
"""

from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client import CollectorRegistry, generate_latest
from dataclasses import dataclass
from enum import Enum
import time


class MetricType(Enum):
    """指標類型"""
    COUNTER = "counter"       # 只增不減的計數器
    GAUGE = "gauge"           # 可增可減的瞬時值
    HISTOGRAM = "histogram"   # 分布統計
    SUMMARY = "summary"       # 百分位數統計


@dataclass
class RAGRequestMetrics:
    """單次請求的指標數據"""
    query: str
    latency_ms: float
    retrieval_latency_ms: float
    llm_latency_ms: float
    retrieved_docs: int
    input_tokens: int
    output_tokens: int
    has_answer: bool
    citation_count: int
    hallucination_risk: float


class RAGMetrics:
    """
    RAG 系統指標收集器

    定義並追蹤 RAG 系統的核心監控指標。
    """

    def __init__(self, registry: CollectorRegistry = None):
        """
        初始化指標收集器

        Args:
            registry: Prometheus 指標註冊表
        """
        self.registry = registry or CollectorRegistry()

        # ═══════════════════════════════════════════════════════════════
        # 請求相關指標
        # ═══════════════════════════════════════════════════════════════

        # 請求計數器                                        # ‹1›
        self.request_total = Counter(
            'rag_requests_total',
            'Total number of RAG requests',
            ['status', 'endpoint'],
            registry=self.registry
        )

        # 請求延遲直方圖                                    # ‹2›
        self.request_latency = Histogram(
            'rag_request_latency_seconds',
            'Request latency in seconds',
            ['endpoint'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )

        # ═══════════════════════════════════════════════════════════════
        # 檢索相關指標
        # ═══════════════════════════════════════════════════════════════

        # 檢索延遲                                          # ‹3›
        self.retrieval_latency = Histogram(
            'rag_retrieval_latency_seconds',
            'Retrieval latency in seconds',
            ['retriever_type'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
            registry=self.registry
        )

        # 檢索文件數
        self.retrieved_documents = Histogram(
            'rag_retrieved_documents',
            'Number of documents retrieved per query',
            buckets=[1, 3, 5, 10, 20, 50],
            registry=self.registry
        )

        # 檢索相關性分數
        self.retrieval_score = Histogram(
            'rag_retrieval_score',
            'Relevance score of retrieved documents',
            buckets=[0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95],
            registry=self.registry
        )

        # ═══════════════════════════════════════════════════════════════
        # LLM 相關指標
        # ═══════════════════════════════════════════════════════════════

        # LLM 延遲                                          # ‹4›
        self.llm_latency = Histogram(
            'rag_llm_latency_seconds',
            'LLM inference latency in seconds',
            ['model'],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )

        # Token 使用量
        self.tokens_used = Counter(
            'rag_tokens_total',
            'Total tokens used',
            ['type', 'model'],  # type: input/output
            registry=self.registry
        )

        # 估算成本（美元）
        self.estimated_cost = Counter(
            'rag_cost_usd_total',
            'Estimated cost in USD',
            ['model'],
            registry=self.registry
        )

        # ═══════════════════════════════════════════════════════════════
        # 品質相關指標
        # ═══════════════════════════════════════════════════════════════

        # 回答成功率                                        # ‹5›
        self.answer_rate = Counter(
            'rag_answers_total',
            'Total answers by status',
            ['status'],  # answered/no_context/refused
            registry=self.registry
        )

        # 引用數量
        self.citation_count = Histogram(
            'rag_citation_count',
            'Number of citations per answer',
            buckets=[0, 1, 2, 3, 5, 10],
            registry=self.registry
        )

        # 幻覺風險分數
        self.hallucination_risk = Histogram(
            'rag_hallucination_risk',
            'Hallucination risk score',
            buckets=[0.1, 0.2, 0.3, 0.5, 0.7, 0.9],
            registry=self.registry
        )

        # ═══════════════════════════════════════════════════════════════
        # 系統健康指標
        # ═══════════════════════════════════════════════════════════════

        # 向量資料庫連線狀態                                # ‹6›
        self.vector_db_status = Gauge(
            'rag_vector_db_up',
            'Vector database connection status (1=up, 0=down)',
            registry=self.registry
        )

        # 快取命中率
        self.cache_hits = Counter(
            'rag_cache_hits_total',
            'Cache hit count',
            ['cache_type'],
            registry=self.registry
        )

        self.cache_misses = Counter(
            'rag_cache_misses_total',
            'Cache miss count',
            ['cache_type'],
            registry=self.registry
        )

        # 佇列深度
        self.queue_depth = Gauge(
            'rag_queue_depth',
            'Current request queue depth',
            registry=self.registry
        )

    def record_request(
        self,
        metrics: RAGRequestMetrics,
        endpoint: str = "/ask",
        model: str = "claude-3-haiku"
    ):
        """
        記錄一次完整請求的指標

        Args:
            metrics: 請求指標數據
            endpoint: API 端點
            model: 使用的 LLM 模型
        """
        # 請求計數
        status = "success" if metrics.has_answer else "no_answer"
        self.request_total.labels(status=status, endpoint=endpoint).inc()

        # 延遲指標
        self.request_latency.labels(endpoint=endpoint).observe(
            metrics.latency_ms / 1000
        )
        self.retrieval_latency.labels(retriever_type="hybrid").observe(
            metrics.retrieval_latency_ms / 1000
        )
        self.llm_latency.labels(model=model).observe(
            metrics.llm_latency_ms / 1000
        )

        # 檢索指標
        self.retrieved_documents.observe(metrics.retrieved_docs)

        # Token 與成本
        self.tokens_used.labels(type="input", model=model).inc(
            metrics.input_tokens
        )
        self.tokens_used.labels(type="output", model=model).inc(
            metrics.output_tokens
        )

        # 估算成本（以 Claude Haiku 為例）
        input_cost = metrics.input_tokens * 0.25 / 1_000_000
        output_cost = metrics.output_tokens * 1.25 / 1_000_000
        self.estimated_cost.labels(model=model).inc(input_cost + output_cost)

        # 品質指標
        self.citation_count.observe(metrics.citation_count)
        self.hallucination_risk.observe(metrics.hallucination_risk)

        if metrics.has_answer:
            self.answer_rate.labels(status="answered").inc()
        else:
            self.answer_rate.labels(status="no_context").inc()

    def record_cache_access(self, cache_type: str, hit: bool):
        """記錄快取存取"""
        if hit:
            self.cache_hits.labels(cache_type=cache_type).inc()
        else:
            self.cache_misses.labels(cache_type=cache_type).inc()

    def set_vector_db_status(self, is_up: bool):
        """設定向量資料庫狀態"""
        self.vector_db_status.set(1 if is_up else 0)

    def set_queue_depth(self, depth: int):
        """設定佇列深度"""
        self.queue_depth.set(depth)

    def get_metrics(self) -> bytes:
        """取得 Prometheus 格式的指標"""
        return generate_latest(self.registry)


class MetricsTimer:
    """
    指標計時器

    用於測量程式碼區塊的執行時間。
    """

    def __init__(self, histogram: Histogram, labels: dict = None):
        self.histogram = histogram
        self.labels = labels or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if self.labels:
            self.histogram.labels(**self.labels).observe(elapsed)
        else:
            self.histogram.observe(elapsed)


def demo_metrics():
    """演示指標收集"""
    metrics = RAGMetrics()

    # 模擬請求
    request_metrics = RAGRequestMetrics(
        query="如何重設密碼？",
        latency_ms=1250,
        retrieval_latency_ms=150,
        llm_latency_ms=1050,
        retrieved_docs=5,
        input_tokens=800,
        output_tokens=150,
        has_answer=True,
        citation_count=2,
        hallucination_risk=0.1
    )

    metrics.record_request(request_metrics)

    # 輸出指標
    print(metrics.get_metrics().decode('utf-8'))


if __name__ == "__main__":
    demo_metrics()
