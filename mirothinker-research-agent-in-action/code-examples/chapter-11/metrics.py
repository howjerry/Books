#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 11 章：生產環境部署
Prometheus 監控指標模組

這個模組實現了應用程式指標收集：
1. 請求計數與延遲
2. 研究任務統計
3. LLM 調用追蹤
4. 快取效能指標

使用方式：
    from metrics import REQUEST_COUNT, track_request
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import REGISTRY, CollectorRegistry
from functools import wraps
import time
from typing import Callable


# =============================================================================
# 指標定義
# =============================================================================

# ‹1› 請求計數器
REQUEST_COUNT = Counter(
    'research_requests_total',
    'Total number of research requests',
    ['method', 'endpoint', 'status']
)

# ‹2› 請求延遲直方圖
REQUEST_LATENCY = Histogram(
    'research_request_duration_seconds',
    'Request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

# ‹3› 活躍請求計數
ACTIVE_REQUESTS = Gauge(
    'research_active_requests',
    'Number of active requests',
    ['endpoint']
)

# ‹4› 研究任務指標
RESEARCH_TASKS = Counter(
    'research_tasks_total',
    'Total number of research tasks',
    ['status', 'agent_type']
)

RESEARCH_DURATION = Histogram(
    'research_task_duration_seconds',
    'Research task duration in seconds',
    ['agent_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0]
)

# ‹5› LLM 調用指標
LLM_CALLS = Counter(
    'llm_calls_total',
    'Total number of LLM API calls',
    ['model', 'status']
)

LLM_TOKENS = Counter(
    'llm_tokens_total',
    'Total number of tokens processed',
    ['model', 'type']  # type: input/output
)

LLM_LATENCY = Histogram(
    'llm_call_duration_seconds',
    'LLM API call latency',
    ['model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# ‹6› 快取指標
CACHE_HITS = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

CACHE_SIZE = Gauge(
    'cache_size_bytes',
    'Current cache size in bytes',
    ['cache_type']
)

# ‹7› Worker 指標
WORKER_TASKS = Gauge(
    'worker_active_tasks',
    'Number of active worker tasks',
    ['worker_id']
)

WORKER_QUEUE_LENGTH = Gauge(
    'worker_queue_length',
    'Number of tasks in worker queue',
    ['queue_name']
)

# ‹8› 系統資訊
SYSTEM_INFO = Info(
    'research_agent_info',
    'Research agent system information'
)


# =============================================================================
# 初始化函數
# =============================================================================

def setup_metrics():
    """初始化指標系統"""
    SYSTEM_INFO.info({
        'version': '1.0.0',
        'python_version': '3.11',
        'environment': 'production'
    })


# =============================================================================
# 裝飾器
# =============================================================================

def track_request(endpoint: str):
    """
    請求追蹤裝飾器

    自動記錄請求計數、延遲和活躍數
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            method = "POST"
            ACTIVE_REQUESTS.labels(endpoint=endpoint).inc()

            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status
                ).inc()
                REQUEST_LATENCY.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
                ACTIVE_REQUESTS.labels(endpoint=endpoint).dec()

        return wrapper
    return decorator


def track_research_task(agent_type: str):
    """
    研究任務追蹤裝飾器
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                RESEARCH_TASKS.labels(
                    status=status,
                    agent_type=agent_type
                ).inc()
                RESEARCH_DURATION.labels(
                    agent_type=agent_type
                ).observe(duration)

        return wrapper
    return decorator


def track_llm_call(model: str):
    """
    LLM 調用追蹤裝飾器
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)

                # 記錄 token 使用
                if hasattr(result, 'usage'):
                    LLM_TOKENS.labels(model=model, type='input').inc(
                        result.usage.prompt_tokens
                    )
                    LLM_TOKENS.labels(model=model, type='output').inc(
                        result.usage.completion_tokens
                    )

                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                LLM_CALLS.labels(model=model, status=status).inc()
                LLM_LATENCY.labels(model=model).observe(duration)

        return wrapper
    return decorator


# =============================================================================
# 快取追蹤
# =============================================================================

class MetricsCache:
    """
    帶指標的快取包裝器
    """

    def __init__(self, cache, cache_type: str = "default"):
        self._cache = cache
        self._type = cache_type
        self._size = 0

    async def get(self, key: str):
        """獲取快取值"""
        value = await self._cache.get(key) if hasattr(self._cache, 'get') else self._cache.get(key)

        if value is not None:
            CACHE_HITS.labels(cache_type=self._type).inc()
        else:
            CACHE_MISSES.labels(cache_type=self._type).inc()

        return value

    async def set(self, key: str, value, ttl: int = None):
        """設置快取值"""
        if hasattr(self._cache, 'set'):
            await self._cache.set(key, value, ttl)
        else:
            self._cache[key] = value

        # 更新快取大小估計
        self._size += len(str(value))
        CACHE_SIZE.labels(cache_type=self._type).set(self._size)

    @property
    def hit_rate(self) -> float:
        """計算快取命中率"""
        try:
            hits = CACHE_HITS.labels(cache_type=self._type)._value.get()
            misses = CACHE_MISSES.labels(cache_type=self._type)._value.get()
            total = hits + misses
            return hits / total if total > 0 else 0
        except:
            return 0


# =============================================================================
# 健康檢查指標
# =============================================================================

class HealthMetrics:
    """
    健康檢查指標收集器
    """

    def __init__(self):
        self._checks = {}
        self._last_check_time = None

    def register_check(self, name: str, check_func: Callable):
        """註冊健康檢查"""
        self._checks[name] = check_func

    async def run_checks(self) -> dict:
        """執行所有健康檢查"""
        results = {}
        all_healthy = True

        for name, check_func in self._checks.items():
            try:
                healthy = await check_func()
                results[name] = {"healthy": healthy}
                if not healthy:
                    all_healthy = False
            except Exception as e:
                results[name] = {"healthy": False, "error": str(e)}
                all_healthy = False

        self._last_check_time = time.time()

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": results,
            "timestamp": self._last_check_time
        }


# 全域健康指標收集器
health_metrics = HealthMetrics()


# =============================================================================
# 示範
# =============================================================================

def demo():
    """示範指標使用"""
    print("=" * 60)
    print("  Prometheus 指標模組示範")
    print("=" * 60)

    # 模擬請求計數
    REQUEST_COUNT.labels(method="POST", endpoint="/research", status="success").inc()
    REQUEST_COUNT.labels(method="POST", endpoint="/research", status="success").inc()
    REQUEST_COUNT.labels(method="POST", endpoint="/research", status="error").inc()

    print("\n請求計數指標已記錄")

    # 模擬延遲記錄
    REQUEST_LATENCY.labels(method="POST", endpoint="/research").observe(1.5)
    REQUEST_LATENCY.labels(method="POST", endpoint="/research").observe(2.3)

    print("請求延遲指標已記錄")

    # 模擬研究任務
    RESEARCH_TASKS.labels(status="completed", agent_type="coordinator").inc()
    RESEARCH_DURATION.labels(agent_type="coordinator").observe(45.2)

    print("研究任務指標已記錄")

    # 模擬 LLM 調用
    LLM_CALLS.labels(model="qwen-72b", status="success").inc()
    LLM_TOKENS.labels(model="qwen-72b", type="input").inc(1500)
    LLM_TOKENS.labels(model="qwen-72b", type="output").inc(800)
    LLM_LATENCY.labels(model="qwen-72b").observe(3.2)

    print("LLM 調用指標已記錄")

    # 模擬快取
    CACHE_HITS.labels(cache_type="search").inc(85)
    CACHE_MISSES.labels(cache_type="search").inc(15)

    print("快取指標已記錄")

    # 導出指標
    print("\n" + "-" * 40)
    print("指標導出預覽:")
    print("-" * 40)

    from prometheus_client import generate_latest
    metrics_output = generate_latest().decode('utf-8')

    # 只顯示部分指標
    for line in metrics_output.split('\n')[:30]:
        if line and not line.startswith('#'):
            print(f"  {line}")

    print("  ...")


if __name__ == "__main__":
    demo()
