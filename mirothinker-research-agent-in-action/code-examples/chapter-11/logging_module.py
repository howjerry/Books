#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 11 章：生產環境部署
結構化日誌模組

這個模組實現了生產級日誌系統：
1. JSON 結構化日誌
2. 請求追蹤
3. 審計日誌
4. FastAPI 中間件

使用方式：
    from logging_module import get_logger, log_with_context
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextlib import contextmanager
import uuid
import contextvars
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


# 請求 ID 上下文變數
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='')


# =============================================================================
# 結構化日誌格式器
# =============================================================================

class StructuredFormatter(logging.Formatter):
    """
    結構化 JSON 日誌格式器

    輸出格式：
    {
        "timestamp": "2024-01-15T10:30:00.000Z",
        "level": "INFO",
        "logger": "research_agent",
        "message": "Research completed",
        "request_id": "abc123",
        "duration": 5.2,
        ...
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加請求 ID
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        # 添加額外欄位
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # 添加異常資訊
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class PrettyFormatter(logging.Formatter):
    """
    美化日誌格式器（開發用）
    """

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, '')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        request_id = request_id_var.get()
        request_id_str = f"[{request_id}] " if request_id else ""

        extra = ""
        if hasattr(record, 'extra_fields'):
            extra = f" | {record.extra_fields}"

        return (
            f"{color}{timestamp} | {record.levelname:8} | "
            f"{request_id_str}{record.name} | "
            f"{record.getMessage()}{extra}{self.RESET}"
        )


# =============================================================================
# 日誌管理器
# =============================================================================

class LogManager:
    """
    日誌管理器

    ‹1› 集中管理日誌配置
    ‹2› 支援結構化日誌
    ‹3› 支援請求追蹤
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._loggers: Dict[str, logging.Logger] = {}

    def setup(
        self,
        level: str = "INFO",
        json_output: bool = True,
        extra_handlers: list = None
    ):
        """
        設置日誌系統

        Args:
            level: 日誌級別
            json_output: 是否使用 JSON 格式
            extra_handlers: 額外的處理器
        """
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper()))

        # 清除現有處理器
        root_logger.handlers.clear()

        # 建立處理器
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper()))

        if json_output:
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(PrettyFormatter())

        root_logger.addHandler(handler)

        # 添加額外處理器
        if extra_handlers:
            for h in extra_handlers:
                root_logger.addHandler(h)

    def get_logger(self, name: str) -> logging.Logger:
        """獲取日誌器"""
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        return self._loggers[name]


# 建立全域日誌管理器
log_manager = LogManager()


# =============================================================================
# 日誌輔助函數
# =============================================================================

def get_logger(name: str = "research_agent") -> logging.Logger:
    """獲取日誌器"""
    return log_manager.get_logger(name)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **extra_fields
):
    """
    帶上下文的日誌記錄

    自動添加請求 ID 等上下文資訊
    """
    record = logger.makeRecord(
        logger.name,
        getattr(logging, level.upper()),
        "",
        0,
        message,
        (),
        None
    )
    record.extra_fields = extra_fields
    logger.handle(record)


@contextmanager
def log_operation(
    logger: logging.Logger,
    operation: str,
    **context
):
    """
    操作日誌上下文管理器

    自動記錄操作開始、結束和耗時
    """
    start_time = datetime.now()

    log_with_context(
        logger,
        "INFO",
        f"開始 {operation}",
        operation=operation,
        phase="start",
        **context
    )

    try:
        yield
        duration = (datetime.now() - start_time).total_seconds()
        log_with_context(
            logger,
            "INFO",
            f"完成 {operation}",
            operation=operation,
            phase="end",
            duration=duration,
            status="success",
            **context
        )
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        log_with_context(
            logger,
            "ERROR",
            f"失敗 {operation}: {str(e)}",
            operation=operation,
            phase="end",
            duration=duration,
            status="error",
            error=str(e),
            **context
        )
        raise


def set_request_id(request_id: str = None) -> str:
    """設置請求 ID"""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> str:
    """獲取請求 ID"""
    return request_id_var.get()


# =============================================================================
# FastAPI 中間件
# =============================================================================

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    日誌中間件

    ‹1› 為每個請求設置唯一 ID
    ‹2› 記錄請求開始和結束
    ‹3› 記錄響應時間
    """

    async def dispatch(self, request: Request, call_next):
        logger = get_logger("api")

        # ‹1› 設置請求 ID
        incoming_request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(incoming_request_id)

        # ‹2› 記錄請求開始
        start_time = time.time()

        log_with_context(
            logger,
            "INFO",
            f"請求開始: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params) if request.query_params else None,
            client_ip=request.client.host if request.client else "unknown"
        )

        # ‹3› 處理請求
        try:
            response = await call_next(request)

            # ‹4› 記錄請求完成
            duration = time.time() - start_time
            log_with_context(
                logger,
                "INFO",
                f"請求完成: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=round(duration, 3)
            )

            # 添加請求 ID 到響應頭
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time
            log_with_context(
                logger,
                "ERROR",
                f"請求失敗: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration=round(duration, 3)
            )
            raise


# =============================================================================
# 審計日誌
# =============================================================================

class AuditLogger:
    """
    審計日誌記錄器

    記錄重要操作用於合規和追蹤
    """

    def __init__(self):
        self.logger = get_logger("audit")

    def log_research_request(
        self,
        user_id: str,
        question: str,
        ip_address: str
    ):
        """記錄研究請求"""
        log_with_context(
            self.logger,
            "INFO",
            "研究請求",
            event_type="research_request",
            user_id=user_id,
            question_preview=question[:100] if len(question) > 100 else question,
            ip_address=ip_address
        )

    def log_research_complete(
        self,
        user_id: str,
        research_id: str,
        duration: float,
        sources_count: int
    ):
        """記錄研究完成"""
        log_with_context(
            self.logger,
            "INFO",
            "研究完成",
            event_type="research_complete",
            user_id=user_id,
            research_id=research_id,
            duration=duration,
            sources_count=sources_count
        )

    def log_api_key_usage(
        self,
        user_id: str,
        key_id: str,
        endpoint: str
    ):
        """記錄 API Key 使用"""
        log_with_context(
            self.logger,
            "INFO",
            "API Key 使用",
            event_type="api_key_usage",
            user_id=user_id,
            key_id=key_id[:8] + "..." if len(key_id) > 8 else key_id,
            endpoint=endpoint
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any]
    ):
        """記錄安全事件"""
        level = "WARNING" if severity == "medium" else "ERROR" if severity == "high" else "INFO"
        log_with_context(
            self.logger,
            level,
            f"安全事件: {event_type}",
            event_type=f"security_{event_type}",
            severity=severity,
            **details
        )


# 建立全域審計日誌器
audit_logger = AuditLogger()


# =============================================================================
# 示範
# =============================================================================

def demo():
    """示範日誌模組"""
    print("=" * 60)
    print("  結構化日誌模組示範")
    print("=" * 60)

    # 設置日誌系統（使用美化格式）
    log_manager.setup(level="DEBUG", json_output=False)

    logger = get_logger("demo")

    # 設置請求 ID
    request_id = set_request_id()
    print(f"\n請求 ID: {request_id}")

    # 基本日誌
    print("\n基本日誌:")
    logger.info("這是一條資訊日誌")
    logger.warning("這是一條警告日誌")
    logger.error("這是一條錯誤日誌")

    # 帶上下文的日誌
    print("\n帶上下文的日誌:")
    log_with_context(
        logger,
        "INFO",
        "研究任務開始",
        research_id="res_12345",
        question="AI 晶片市場分析",
        user_id="user_001"
    )

    # 使用操作上下文管理器
    print("\n操作上下文管理器:")
    with log_operation(logger, "研究任務", research_id="res_12345"):
        import time
        time.sleep(0.5)  # 模擬操作

    # 審計日誌
    print("\n審計日誌:")
    audit_logger.log_research_request(
        user_id="user_001",
        question="全球半導體市場分析",
        ip_address="192.168.1.100"
    )

    # JSON 格式示範
    print("\n\nJSON 格式日誌示範:")
    log_manager.setup(level="INFO", json_output=True)
    logger2 = get_logger("json_demo")
    log_with_context(
        logger2,
        "INFO",
        "JSON 格式日誌測試",
        user_id="user_001",
        action="demo"
    )


if __name__ == "__main__":
    demo()
