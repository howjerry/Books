#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 11 章：生產環境部署
FastAPI 應用服務

這個模組實現了生產就緒的 API 服務：
1. RESTful API 端點
2. 中間件整合（日誌、認證、速率限制）
3. 健康檢查端點
4. Prometheus 指標導出

使用方式：
    uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
import uvicorn

from dotenv import load_dotenv

# 導入本地模組
from metrics import (
    REQUEST_COUNT, REQUEST_LATENCY, ACTIVE_REQUESTS,
    RESEARCH_TASKS, track_request, setup_metrics
)
from logging_module import (
    LogManager, get_logger, set_request_id, log_with_context,
    LoggingMiddleware, audit_logger
)

load_dotenv()


# =============================================================================
# 資料模型
# =============================================================================

class ResearchRequest(BaseModel):
    """研究請求模型"""
    question: str = Field(..., min_length=5, max_length=2000, description="研究問題")
    max_sources: int = Field(default=10, ge=1, le=50, description="最大來源數")
    verify: bool = Field(default=True, description="是否執行事實查證")
    language: str = Field(default="zh-TW", description="輸出語言")


class ResearchResponse(BaseModel):
    """研究回應模型"""
    research_id: str
    question: str
    status: str
    summary: Optional[str] = None
    key_findings: List[str] = []
    sources: List[Dict[str, Any]] = []
    confidence_score: float = 0.0
    created_at: str
    completed_at: Optional[str] = None


class HealthResponse(BaseModel):
    """健康檢查回應"""
    status: str
    version: str
    uptime: float
    checks: Dict[str, Dict[str, Any]]


class ErrorResponse(BaseModel):
    """錯誤回應"""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


# =============================================================================
# 應用程式初始化
# =============================================================================

# 啟動時間
START_TIME = datetime.now()

# 日誌管理器
log_manager = LogManager()
log_manager.setup(level="INFO", json_output=True)
logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理

    ‹1› 啟動時初始化資源
    ‹2› 關閉時清理資源
    """
    # 啟動時
    logger.info("API 服務啟動中...")
    setup_metrics()

    yield

    # 關閉時
    logger.info("API 服務關閉中...")


# 建立 FastAPI 應用
app = FastAPI(
    title="深度研究代理人 API",
    description="基於 MiroThinker 的深度研究代理人服務",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日誌中間件
app.add_middleware(LoggingMiddleware)


# =============================================================================
# 健康檢查
# =============================================================================

async def check_database() -> bool:
    """檢查資料庫連接"""
    # 在實際應用中，這裡會檢查資料庫連接
    return True


async def check_redis() -> bool:
    """檢查 Redis 連接"""
    # 在實際應用中，這裡會檢查 Redis 連接
    return True


async def check_llm() -> bool:
    """檢查 LLM 服務"""
    # 在實際應用中，這裡會檢查 LLM API 連接
    return True


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    健康檢查端點

    用於 Kubernetes liveness probe
    """
    uptime = (datetime.now() - START_TIME).total_seconds()

    checks = {
        "database": {"healthy": await check_database()},
        "redis": {"healthy": await check_redis()},
        "llm": {"healthy": await check_llm()}
    }

    all_healthy = all(c["healthy"] for c in checks.values())

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        version="1.0.0",
        uptime=uptime,
        checks=checks
    )


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """
    就緒檢查端點

    用於 Kubernetes readiness probe
    """
    # 檢查所有依賴
    db_ok = await check_database()
    redis_ok = await check_redis()
    llm_ok = await check_llm()

    if not all([db_ok, redis_ok, llm_ok]):
        raise HTTPException(status_code=503, detail="Service not ready")

    return {"status": "ready"}


# =============================================================================
# 指標端點
# =============================================================================

@app.get("/metrics", response_class=PlainTextResponse, tags=["Monitoring"])
async def metrics():
    """
    Prometheus 指標端點

    導出所有應用程式指標
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# =============================================================================
# 研究 API
# =============================================================================

# 模擬研究任務存儲
research_tasks: Dict[str, Dict] = {}


@app.post(
    "/api/v1/research",
    response_model=ResearchResponse,
    tags=["Research"],
    summary="提交研究請求"
)
@track_request("/api/v1/research")
async def create_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
):
    """
    提交新的研究請求

    ‹1› 驗證請求
    ‹2› 建立研究任務
    ‹3› 在背景執行研究
    """
    import uuid

    # 生成研究 ID
    research_id = str(uuid.uuid4())[:12]

    # 記錄審計日誌
    audit_logger.log_research_request(
        user_id="anonymous",
        question=request.question,
        ip_address=http_request.client.host if http_request.client else "unknown"
    )

    # 建立任務記錄
    task = {
        "research_id": research_id,
        "question": request.question,
        "status": "pending",
        "max_sources": request.max_sources,
        "verify": request.verify,
        "language": request.language,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result": None
    }

    research_tasks[research_id] = task

    # 在背景執行研究
    background_tasks.add_task(execute_research, research_id)

    RESEARCH_TASKS.labels(status="pending", agent_type="coordinator").inc()

    log_with_context(
        logger,
        "INFO",
        f"研究任務已建立: {research_id}",
        research_id=research_id,
        question_preview=request.question[:50]
    )

    return ResearchResponse(
        research_id=research_id,
        question=request.question,
        status="pending",
        created_at=task["created_at"]
    )


@app.get(
    "/api/v1/research/{research_id}",
    response_model=ResearchResponse,
    tags=["Research"],
    summary="獲取研究結果"
)
async def get_research(research_id: str):
    """
    獲取研究任務結果

    ‹1› 查詢任務狀態
    ‹2› 返回結果或狀態
    """
    if research_id not in research_tasks:
        raise HTTPException(status_code=404, detail="Research not found")

    task = research_tasks[research_id]

    return ResearchResponse(
        research_id=task["research_id"],
        question=task["question"],
        status=task["status"],
        summary=task.get("result", {}).get("summary"),
        key_findings=task.get("result", {}).get("key_findings", []),
        sources=task.get("result", {}).get("sources", []),
        confidence_score=task.get("result", {}).get("confidence_score", 0),
        created_at=task["created_at"],
        completed_at=task.get("completed_at")
    )


@app.get(
    "/api/v1/research",
    response_model=List[ResearchResponse],
    tags=["Research"],
    summary="列出所有研究"
)
async def list_research(
    status: Optional[str] = None,
    limit: int = 20
):
    """
    列出研究任務

    可按狀態篩選
    """
    tasks = list(research_tasks.values())

    if status:
        tasks = [t for t in tasks if t["status"] == status]

    tasks = sorted(tasks, key=lambda x: x["created_at"], reverse=True)[:limit]

    return [
        ResearchResponse(
            research_id=t["research_id"],
            question=t["question"],
            status=t["status"],
            summary=t.get("result", {}).get("summary"),
            key_findings=t.get("result", {}).get("key_findings", []),
            sources=t.get("result", {}).get("sources", []),
            confidence_score=t.get("result", {}).get("confidence_score", 0),
            created_at=t["created_at"],
            completed_at=t.get("completed_at")
        )
        for t in tasks
    ]


async def execute_research(research_id: str):
    """
    背景執行研究任務

    模擬研究過程
    """
    import random

    task = research_tasks.get(research_id)
    if not task:
        return

    try:
        # 更新狀態為執行中
        task["status"] = "running"

        # 模擬研究過程
        await asyncio.sleep(random.uniform(2, 5))

        # 模擬研究結果
        task["result"] = {
            "summary": f"針對「{task['question']}」的研究摘要...",
            "key_findings": [
                "發現 1：重要的市場趨勢",
                "發現 2：技術創新方向",
                "發現 3：潛在風險因素"
            ],
            "sources": [
                {"title": "來源 1", "url": "https://example.com/1", "credibility": 0.9},
                {"title": "來源 2", "url": "https://example.com/2", "credibility": 0.85}
            ],
            "confidence_score": random.uniform(0.7, 0.95)
        }

        task["status"] = "completed"
        task["completed_at"] = datetime.now().isoformat()

        RESEARCH_TASKS.labels(status="completed", agent_type="coordinator").inc()

        log_with_context(
            logger,
            "INFO",
            f"研究任務完成: {research_id}",
            research_id=research_id
        )

    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)

        RESEARCH_TASKS.labels(status="failed", agent_type="coordinator").inc()

        log_with_context(
            logger,
            "ERROR",
            f"研究任務失敗: {research_id}",
            research_id=research_id,
            error=str(e)
        )


# =============================================================================
# 錯誤處理
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 異常處理"""
    from logging_module import get_request_id

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            request_id=get_request_id()
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用異常處理"""
    from logging_module import get_request_id

    logger.exception("Unhandled exception")

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            request_id=get_request_id()
        ).model_dump()
    )


# =============================================================================
# 主程式
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
