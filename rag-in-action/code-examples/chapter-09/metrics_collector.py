"""
chapter-09/metrics_collector.py

RAG 系統指標收集器與中間件

本模組實作 FastAPI 中間件，自動收集 RAG 請求指標。

使用方式：
    from metrics_collector import MetricsMiddleware
    app.add_middleware(MetricsMiddleware)

依賴安裝：
    pip install fastapi prometheus-client structlog
"""

from typing import Callable, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from monitoring_metrics import RAGMetrics, RAGRequestMetrics


# 設定結構化日誌
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@dataclass
class RequestContext:
    """請求上下文，用於追蹤整個請求生命週期"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start_time: float = field(default_factory=time.time)
    query: str = ""
    endpoint: str = ""

    # 計時器
    retrieval_start: float = 0
    retrieval_end: float = 0
    llm_start: float = 0
    llm_end: float = 0

    # 結果
    retrieved_docs: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    has_answer: bool = False
    citation_count: int = 0
    hallucination_risk: float = 0

    def start_retrieval(self):
        """標記檢索開始"""
        self.retrieval_start = time.time()

    def end_retrieval(self, doc_count: int):
        """標記檢索結束"""
        self.retrieval_end = time.time()
        self.retrieved_docs = doc_count

    def start_llm(self):
        """標記 LLM 推理開始"""
        self.llm_start = time.time()

    def end_llm(self, input_tokens: int, output_tokens: int):
        """標記 LLM 推理結束"""
        self.llm_end = time.time()
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def to_metrics(self) -> RAGRequestMetrics:
        """轉換為指標物件"""
        end_time = time.time()
        return RAGRequestMetrics(
            query=self.query,
            latency_ms=(end_time - self.start_time) * 1000,
            retrieval_latency_ms=(self.retrieval_end - self.retrieval_start) * 1000 if self.retrieval_end else 0,
            llm_latency_ms=(self.llm_end - self.llm_start) * 1000 if self.llm_end else 0,
            retrieved_docs=self.retrieved_docs,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            has_answer=self.has_answer,
            citation_count=self.citation_count,
            hallucination_risk=self.hallucination_risk
        )


# 全域請求上下文儲存（使用 contextvars 更安全）
from contextvars import ContextVar
_request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    'request_context', default=None
)


def get_request_context() -> Optional[RequestContext]:
    """取得當前請求上下文"""
    return _request_context.get()


def set_request_context(ctx: RequestContext):
    """設定當前請求上下文"""
    _request_context.set(ctx)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    指標收集中間件

    自動為每個請求收集延遲、狀態碼等指標。
    """

    def __init__(self, app: FastAPI, metrics: RAGMetrics = None):
        super().__init__(app)
        self.metrics = metrics or RAGMetrics()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """處理請求並收集指標"""

        # 建立請求上下文
        ctx = RequestContext(
            endpoint=request.url.path,
            query=request.query_params.get("q", "")
        )
        set_request_context(ctx)

        # 記錄請求開始                                      # ‹1›
        logger.info(
            "request_started",
            request_id=ctx.request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown"
        )

        try:
            # 執行請求
            response = await call_next(request)

            # 記錄請求結束                                  # ‹2›
            latency_ms = (time.time() - ctx.start_time) * 1000

            logger.info(
                "request_completed",
                request_id=ctx.request_id,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2)
            )

            # 收集指標
            self.metrics.request_total.labels(
                status="success" if response.status_code < 400 else "error",
                endpoint=ctx.endpoint
            ).inc()

            self.metrics.request_latency.labels(
                endpoint=ctx.endpoint
            ).observe(latency_ms / 1000)

            return response

        except Exception as e:
            # 記錄錯誤                                      # ‹3›
            logger.error(
                "request_failed",
                request_id=ctx.request_id,
                error=str(e),
                error_type=type(e).__name__
            )

            self.metrics.request_total.labels(
                status="error",
                endpoint=ctx.endpoint
            ).inc()

            raise


class TracingMiddleware:
    """
    分散式追蹤中間件

    為每個請求建立追蹤 ID，便於跨服務追蹤。
    """

    def __init__(self, app: FastAPI):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 從 header 取得或生成追蹤 ID
        headers = dict(scope.get("headers", []))
        trace_id = headers.get(
            b"x-trace-id",
            str(uuid.uuid4()).encode()
        ).decode()

        # 注入追蹤 ID 到回應 header
        async def send_with_trace(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-trace-id", trace_id.encode()))
                message["headers"] = headers
            await send(message)

        # 綁定追蹤 ID 到日誌
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        await self.app(scope, receive, send_with_trace)


def create_metrics_app() -> FastAPI:
    """
    建立帶有監控功能的 FastAPI 應用

    Returns:
        配置好監控的 FastAPI 實例
    """
    app = FastAPI(title="RAG Service with Monitoring")
    metrics = RAGMetrics()

    # 加入中間件
    app.add_middleware(MetricsMiddleware, metrics=metrics)

    # Prometheus 指標端點                                  # ‹4›
    @app.get("/metrics")
    async def get_metrics():
        """Prometheus 抓取端點"""
        return PlainTextResponse(
            metrics.get_metrics().decode('utf-8'),
            media_type="text/plain"
        )

    # 健康檢查端點
    @app.get("/health")
    async def health_check():
        """健康檢查"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }

    # 就緒檢查端點
    @app.get("/ready")
    async def readiness_check():
        """就緒檢查"""
        # 這裡可以加入依賴服務的檢查
        return {
            "status": "ready",
            "vector_db": "connected",
            "llm_api": "available"
        }

    return app, metrics


# ═══════════════════════════════════════════════════════════════
# 結構化日誌工具
# ═══════════════════════════════════════════════════════════════

class RAGLogger:
    """
    RAG 專用結構化日誌器

    提供標準化的日誌格式，便於後續分析。
    """

    def __init__(self, service_name: str = "rag-service"):
        self.logger = structlog.get_logger().bind(service=service_name)

    def log_query(
        self,
        query: str,
        request_id: str,
        user_id: str = None
    ):
        """記錄使用者查詢"""
        self.logger.info(
            "query_received",
            request_id=request_id,
            query=query[:100],  # 截斷長查詢
            query_length=len(query),
            user_id=user_id
        )

    def log_retrieval(
        self,
        request_id: str,
        doc_count: int,
        latency_ms: float,
        top_score: float
    ):
        """記錄檢索結果"""
        self.logger.info(
            "retrieval_completed",
            request_id=request_id,
            doc_count=doc_count,
            latency_ms=round(latency_ms, 2),
            top_score=round(top_score, 4)
        )

    def log_llm_call(
        self,
        request_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float
    ):
        """記錄 LLM 呼叫"""
        self.logger.info(
            "llm_call_completed",
            request_id=request_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency_ms, 2),
            estimated_cost_usd=round(
                (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000,
                6
            )
        )

    def log_answer(
        self,
        request_id: str,
        has_answer: bool,
        citation_count: int,
        hallucination_risk: float
    ):
        """記錄回答品質"""
        self.logger.info(
            "answer_generated",
            request_id=request_id,
            has_answer=has_answer,
            citation_count=citation_count,
            hallucination_risk=round(hallucination_risk, 3)
        )

    def log_error(
        self,
        request_id: str,
        error_type: str,
        error_message: str,
        **extra
    ):
        """記錄錯誤"""
        self.logger.error(
            "error_occurred",
            request_id=request_id,
            error_type=error_type,
            error_message=error_message,
            **extra
        )


def demo_metrics_collector():
    """演示指標收集器"""
    import uvicorn

    app, metrics = create_metrics_app()

    # 模擬 RAG 端點
    @app.get("/ask")
    async def ask(q: str):
        ctx = get_request_context()
        if ctx:
            ctx.query = q

            # 模擬檢索
            ctx.start_retrieval()
            time.sleep(0.1)  # 模擬檢索延遲
            ctx.end_retrieval(5)

            # 模擬 LLM
            ctx.start_llm()
            time.sleep(0.5)  # 模擬 LLM 延遲
            ctx.end_llm(800, 150)

            ctx.has_answer = True
            ctx.citation_count = 2
            ctx.hallucination_risk = 0.1

            # 記錄完整指標
            metrics.record_request(ctx.to_metrics())

        return {
            "query": q,
            "answer": "這是模擬回答",
            "sources": ["FAQ-001", "FAQ-002"]
        }

    print("啟動監控示範服務...")
    print("- API: http://localhost:8000/ask?q=測試")
    print("- 指標: http://localhost:8000/metrics")
    print("- 健康: http://localhost:8000/health")

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    demo_metrics_collector()
