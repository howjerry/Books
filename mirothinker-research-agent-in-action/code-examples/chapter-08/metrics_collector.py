#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 8 章：環境搭建與部署
監控指標收集器

這個模組實現了生產監控功能：
1. Prometheus 指標
2. 健康檢查
3. 效能追蹤

使用方式：
    python metrics_collector.py --demo
    python metrics_collector.py --port 9100
"""

import argparse
import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# 資料結構
# =============================================================================

@dataclass
class MetricPoint:
    """指標數據點"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class HealthStatus:
    """健康狀態"""
    status: str  # "healthy", "degraded", "unhealthy"
    components: Dict[str, bool] = field(default_factory=dict)
    latency_ms: float = 0.0
    message: str = ""


# =============================================================================
# 指標類型
# =============================================================================

class Counter:
    """計數器指標"""

    def __init__(self, name: str, description: str, labels: List[str] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: Dict[tuple, float] = {}

    def inc(self, value: float = 1.0, **labels) -> None:
        """增加計數"""
        key = tuple(labels.get(l, "") for l in self.labels)
        self._values[key] = self._values.get(key, 0) + value

    def get(self, **labels) -> float:
        """獲取計數"""
        key = tuple(labels.get(l, "") for l in self.labels)
        return self._values.get(key, 0)

    def to_prometheus(self) -> str:
        """轉換為 Prometheus 格式"""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter"
        ]
        for key, value in self._values.items():
            label_str = ",".join(f'{l}="{v}"' for l, v in zip(self.labels, key))
            if label_str:
                lines.append(f"{self.name}{{{label_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return "\n".join(lines)


class Gauge:
    """儀表指標"""

    def __init__(self, name: str, description: str, labels: List[str] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: Dict[tuple, float] = {}

    def set(self, value: float, **labels) -> None:
        """設置值"""
        key = tuple(labels.get(l, "") for l in self.labels)
        self._values[key] = value

    def get(self, **labels) -> float:
        """獲取值"""
        key = tuple(labels.get(l, "") for l in self.labels)
        return self._values.get(key, 0)

    def to_prometheus(self) -> str:
        """轉換為 Prometheus 格式"""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge"
        ]
        for key, value in self._values.items():
            label_str = ",".join(f'{l}="{v}"' for l, v in zip(self.labels, key))
            if label_str:
                lines.append(f"{self.name}{{{label_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return "\n".join(lines)


class Histogram:
    """直方圖指標"""

    def __init__(
        self,
        name: str,
        description: str,
        labels: List[str] = None,
        buckets: List[float] = None
    ):
        self.name = name
        self.description = description
        self.labels = labels or []
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        self._observations: Dict[tuple, List[float]] = {}

    def observe(self, value: float, **labels) -> None:
        """記錄觀察值"""
        key = tuple(labels.get(l, "") for l in self.labels)
        if key not in self._observations:
            self._observations[key] = []
        self._observations[key].append(value)

    def percentile(self, p: float, **labels) -> float:
        """計算百分位數"""
        key = tuple(labels.get(l, "") for l in self.labels)
        observations = self._observations.get(key, [])
        if not observations:
            return 0.0
        sorted_obs = sorted(observations)
        idx = int(len(sorted_obs) * p)
        return sorted_obs[min(idx, len(sorted_obs) - 1)]

    def to_prometheus(self) -> str:
        """轉換為 Prometheus 格式"""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram"
        ]

        for key, observations in self._observations.items():
            label_str = ",".join(f'{l}="{v}"' for l, v in zip(self.labels, key))
            base_labels = f"{{{label_str}}}" if label_str else ""

            # 計算 bucket
            for bucket in self.buckets:
                count = sum(1 for o in observations if o <= bucket)
                bucket_labels = f'{{le="{bucket}"{("," + label_str) if label_str else ""}}}'
                lines.append(f"{self.name}_bucket{bucket_labels} {count}")

            # +Inf bucket
            inf_labels = f'{{le="+Inf"{("," + label_str) if label_str else ""}}}'
            lines.append(f"{self.name}_bucket{inf_labels} {len(observations)}")

            # sum 和 count
            lines.append(f"{self.name}_sum{base_labels} {sum(observations)}")
            lines.append(f"{self.name}_count{base_labels} {len(observations)}")

        return "\n".join(lines)


# =============================================================================
# 指標收集器
# =============================================================================

class MetricsCollector:
    """
    指標收集器

    ‹1› 請求指標
    ‹2› 模型指標
    ‹3› GPU 指標
    """

    def __init__(self):
        # ‹1› 請求指標
        self.request_total = Counter(
            "research_agent_requests_total",
            "Total number of requests",
            ["endpoint", "status"]
        )

        self.request_latency = Histogram(
            "research_agent_request_latency_seconds",
            "Request latency in seconds",
            ["endpoint"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )

        # ‹2› 模型指標
        self.tokens_generated = Counter(
            "research_agent_tokens_generated_total",
            "Total tokens generated"
        )

        self.tokens_per_second = Gauge(
            "research_agent_tokens_per_second",
            "Current tokens per second throughput"
        )

        self.active_sequences = Gauge(
            "research_agent_active_sequences",
            "Number of active sequences being processed"
        )

        # ‹3› GPU 指標
        self.gpu_memory_used = Gauge(
            "research_agent_gpu_memory_used_bytes",
            "GPU memory used in bytes",
            ["gpu_id"]
        )

        self.gpu_utilization = Gauge(
            "research_agent_gpu_utilization_percent",
            "GPU utilization percentage",
            ["gpu_id"]
        )

        self.kv_cache_usage = Gauge(
            "research_agent_kv_cache_usage_percent",
            "KV cache usage percentage"
        )

    def record_request(self, endpoint: str, status: str, latency: float) -> None:
        """記錄請求"""
        self.request_total.inc(endpoint=endpoint, status=status)
        self.request_latency.observe(latency, endpoint=endpoint)

    def record_tokens(self, count: int) -> None:
        """記錄生成的 tokens"""
        self.tokens_generated.inc(count)

    def update_throughput(self, tokens_per_sec: float) -> None:
        """更新吞吐量"""
        self.tokens_per_second.set(tokens_per_sec)

    def update_sequences(self, count: int) -> None:
        """更新活躍序列數"""
        self.active_sequences.set(count)

    def update_gpu_metrics(
        self,
        gpu_id: str,
        memory_used: int,
        utilization: float
    ) -> None:
        """更新 GPU 指標"""
        self.gpu_memory_used.set(memory_used, gpu_id=gpu_id)
        self.gpu_utilization.set(utilization, gpu_id=gpu_id)

    def update_kv_cache(self, usage_percent: float) -> None:
        """更新 KV Cache 使用率"""
        self.kv_cache_usage.set(usage_percent)

    def to_prometheus(self) -> str:
        """導出為 Prometheus 格式"""
        metrics = [
            self.request_total,
            self.request_latency,
            self.tokens_generated,
            self.tokens_per_second,
            self.active_sequences,
            self.gpu_memory_used,
            self.gpu_utilization,
            self.kv_cache_usage,
        ]
        return "\n\n".join(m.to_prometheus() for m in metrics)


# =============================================================================
# 健康檢查器
# =============================================================================

class HealthChecker:
    """
    健康檢查器

    ‹1› 檢查各組件狀態
    ‹2› 計算整體健康度
    ‹3› 提供詳細報告
    """

    def __init__(self, components: Dict[str, str] = None):
        """
        初始化健康檢查器

        components: 組件名稱到健康檢查 URL 的映射
        """
        self.components = components or {
            "model_server": "http://localhost:8000/health",
            "agent_server": "http://localhost:8080/health",
            "redis": "redis://localhost:6379",
        }

    async def check_all(self) -> HealthStatus:
        """檢查所有組件"""
        import aiohttp

        component_status = {}
        start_time = time.time()

        for name, url in self.components.items():
            try:
                if url.startswith("redis://"):
                    # 模擬 Redis 檢查
                    component_status[name] = True
                else:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url,
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as resp:
                            component_status[name] = resp.status == 200
            except Exception:
                component_status[name] = False

        latency = (time.time() - start_time) * 1000

        # 計算整體狀態
        healthy_count = sum(1 for v in component_status.values() if v)
        total_count = len(component_status)

        if healthy_count == total_count:
            status = "healthy"
            message = "All components operational"
        elif healthy_count >= total_count * 0.5:
            status = "degraded"
            failed = [k for k, v in component_status.items() if not v]
            message = f"Some components failed: {', '.join(failed)}"
        else:
            status = "unhealthy"
            message = "Most components failed"

        return HealthStatus(
            status=status,
            components=component_status,
            latency_ms=latency,
            message=message
        )


# =============================================================================
# 效能追蹤器
# =============================================================================

class PerformanceTracker:
    """
    效能追蹤器

    ‹1› 追蹤請求效能
    ‹2› 計算統計數據
    ‹3› 生成報告
    """

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self._latencies: List[float] = []
        self._throughputs: List[float] = []
        self._errors: int = 0
        self._total_requests: int = 0

    def record(
        self,
        latency_ms: float,
        tokens: int = 0,
        success: bool = True
    ) -> None:
        """記錄一次請求"""
        self._latencies.append(latency_ms)
        if len(self._latencies) > self.window_size:
            self._latencies.pop(0)

        if latency_ms > 0 and tokens > 0:
            throughput = tokens / (latency_ms / 1000)
            self._throughputs.append(throughput)
            if len(self._throughputs) > self.window_size:
                self._throughputs.pop(0)

        self._total_requests += 1
        if not success:
            self._errors += 1

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計數據"""
        if not self._latencies:
            return {
                "p50_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
                "avg_ms": 0,
                "throughput": 0,
                "error_rate": 0,
                "total_requests": 0
            }

        sorted_latencies = sorted(self._latencies)
        n = len(sorted_latencies)

        return {
            "p50_ms": sorted_latencies[n // 2],
            "p95_ms": sorted_latencies[int(n * 0.95)],
            "p99_ms": sorted_latencies[int(n * 0.99)],
            "avg_ms": sum(sorted_latencies) / n,
            "throughput": sum(self._throughputs) / len(self._throughputs) if self._throughputs else 0,
            "error_rate": self._errors / self._total_requests if self._total_requests > 0 else 0,
            "total_requests": self._total_requests
        }

    def generate_report(self) -> str:
        """生成效能報告"""
        stats = self.get_stats()

        lines = [
            "=" * 50,
            "效能報告",
            "=" * 50,
            f"總請求數: {stats['total_requests']:,}",
            f"錯誤率: {stats['error_rate']:.2%}",
            "",
            "延遲 (ms):",
            f"  P50: {stats['p50_ms']:.1f}",
            f"  P95: {stats['p95_ms']:.1f}",
            f"  P99: {stats['p99_ms']:.1f}",
            f"  平均: {stats['avg_ms']:.1f}",
            "",
            f"吞吐量: {stats['throughput']:.1f} tokens/s",
            "=" * 50
        ]

        return "\n".join(lines)


# =============================================================================
# 告警管理器
# =============================================================================

@dataclass
class AlertRule:
    """告警規則"""
    name: str
    condition: str  # 例如: "latency_p99 > 5000"
    severity: str   # "warning", "critical"
    message: str


class AlertManager:
    """
    告警管理器

    ‹1› 定義告警規則
    ‹2› 評估條件
    ‹3› 觸發告警
    """

    DEFAULT_RULES = [
        AlertRule(
            name="high_latency",
            condition="latency_p99 > 5000",
            severity="warning",
            message="P99 延遲超過 5 秒"
        ),
        AlertRule(
            name="critical_latency",
            condition="latency_p99 > 10000",
            severity="critical",
            message="P99 延遲超過 10 秒"
        ),
        AlertRule(
            name="high_error_rate",
            condition="error_rate > 0.05",
            severity="warning",
            message="錯誤率超過 5%"
        ),
        AlertRule(
            name="gpu_memory_high",
            condition="gpu_memory_percent > 0.95",
            severity="warning",
            message="GPU 顯存使用率超過 95%"
        ),
    ]

    def __init__(self, rules: List[AlertRule] = None):
        self.rules = rules or self.DEFAULT_RULES
        self._active_alerts: Dict[str, AlertRule] = {}

    def evaluate(self, metrics: Dict[str, float]) -> List[AlertRule]:
        """評估告警條件"""
        triggered = []

        for rule in self.rules:
            # 解析條件
            parts = rule.condition.split()
            if len(parts) != 3:
                continue

            metric_name, operator, threshold = parts
            threshold = float(threshold)
            value = metrics.get(metric_name, 0)

            # 評估條件
            is_triggered = False
            if operator == ">":
                is_triggered = value > threshold
            elif operator == "<":
                is_triggered = value < threshold
            elif operator == ">=":
                is_triggered = value >= threshold
            elif operator == "<=":
                is_triggered = value <= threshold

            if is_triggered:
                triggered.append(rule)
                self._active_alerts[rule.name] = rule
            elif rule.name in self._active_alerts:
                del self._active_alerts[rule.name]

        return triggered

    def get_active_alerts(self) -> List[AlertRule]:
        """獲取當前活躍的告警"""
        return list(self._active_alerts.values())


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範監控功能"""
    print("=" * 60)
    print("📊 監控指標收集器示範")
    print("=" * 60)

    # 創建指標收集器
    collector = MetricsCollector()

    # 模擬一些請求
    print("\n模擬請求...")
    endpoints = ["/v1/chat/completions", "/v1/embeddings", "/health"]

    for i in range(50):
        endpoint = random.choice(endpoints)
        status = "success" if random.random() > 0.05 else "error"
        latency = random.uniform(0.5, 3.0)

        collector.record_request(endpoint, status, latency)
        collector.record_tokens(random.randint(100, 500))

    # 更新 GPU 指標
    for gpu_id in ["0", "1", "2", "3"]:
        collector.update_gpu_metrics(
            gpu_id,
            memory_used=int(70e9 + random.uniform(-5e9, 5e9)),
            utilization=random.uniform(80, 95)
        )

    collector.update_throughput(random.uniform(40, 60))
    collector.update_sequences(random.randint(50, 150))
    collector.update_kv_cache(random.uniform(60, 80))

    # 顯示 Prometheus 格式
    print("\n" + "-" * 40)
    print("Prometheus 指標格式:")
    print("-" * 40)
    prometheus_output = collector.to_prometheus()
    # 只顯示前幾行
    lines = prometheus_output.split("\n")
    for line in lines[:30]:
        print(line)
    if len(lines) > 30:
        print(f"... 還有 {len(lines) - 30} 行")

    # 效能追蹤
    print("\n" + "-" * 40)
    print("效能追蹤:")
    print("-" * 40)

    tracker = PerformanceTracker()
    for i in range(100):
        latency = random.uniform(100, 2000)
        tokens = random.randint(100, 500)
        success = random.random() > 0.02
        tracker.record(latency, tokens, success)

    print(tracker.generate_report())

    # 告警評估
    print("\n" + "-" * 40)
    print("告警評估:")
    print("-" * 40)

    alert_manager = AlertManager()

    # 模擬一些指標值
    test_metrics = {
        "latency_p99": 6000,  # 超過 5000ms 警告閾值
        "error_rate": 0.03,
        "gpu_memory_percent": 0.92
    }

    triggered = alert_manager.evaluate(test_metrics)
    if triggered:
        print("觸發的告警:")
        for alert in triggered:
            print(f"  [{alert.severity.upper()}] {alert.name}: {alert.message}")
    else:
        print("無告警")


def main():
    parser = argparse.ArgumentParser(description="監控指標收集器")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("--port", type=int, default=9100, help="Prometheus 端口")

    args = parser.parse_args()
    asyncio.run(demo())


if __name__ == "__main__":
    main()
