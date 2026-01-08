# 第 11 章：生產環境部署

> **本章目標**：將深度研究代理人系統部署到生產環境，建立完整的監控、日誌與擴展機制。

---

## 引言：從開發到生產

在前面的章節中，我們建構了一套功能完整的深度研究代理人系統。你已經擁有：

- 核心研究代理人（第 9 章）
- 多代理人協作系統（第 10 章）
- 完整的工具鏈與記憶管理（第 5-7 章）

現在，是時候將這套系統部署到生產環境了。

**生產環境與開發環境的差異：**

| 面向 | 開發環境 | 生產環境 |
|------|----------|----------|
| **可用性** | 可以隨時停機 | 需要高可用性 |
| **規模** | 單一使用者 | 大量併發請求 |
| **監控** | 手動觀察 | 自動化監控告警 |
| **日誌** | 本地輸出 | 集中式日誌管理 |
| **安全** | 較寬鬆 | 嚴格的安全控制 |
| **部署** | 手動執行 | 自動化 CI/CD |

本章將帶你完成這個轉變。完成本章後，你將擁有：

1. **Docker 容器化**：標準化的部署單元
2. **Kubernetes 編排**：自動擴展與高可用性
3. **Prometheus 監控**：即時效能指標收集
4. **Grafana 儀表板**：視覺化監控介面
5. **結構化日誌**：便於追蹤與除錯
6. **安全機制**：API 認證、速率限制

讓我們開始吧。

---

## 11.1 部署架構設計

在動手之前，我們需要先設計整體的部署架構。

### 11.1.1 系統架構圖

```
                              ┌─────────────────┐
                              │   Load Balancer │
                              │   (Nginx/HAProxy)│
                              └────────┬────────┘
                                       │
                 ┌─────────────────────┼─────────────────────┐
                 │                     │                     │
                 ▼                     ▼                     ▼
          ┌──────────┐          ┌──────────┐          ┌──────────┐
          │ API Pod  │          │ API Pod  │          │ API Pod  │
          │ (FastAPI)│          │ (FastAPI)│          │ (FastAPI)│
          └────┬─────┘          └────┬─────┘          └────┬─────┘
               │                     │                     │
               └─────────────────────┼─────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
             ┌──────────┐     ┌──────────┐     ┌──────────┐
             │  Agent   │     │  Agent   │     │  Agent   │
             │  Worker  │     │  Worker  │     │  Worker  │
             └────┬─────┘     └────┬─────┘     └────┬─────┘
                  │                │                │
                  └────────────────┼────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
             ┌──────────┐   ┌──────────┐   ┌──────────┐
             │  Redis   │   │ PostgreSQL│  │   LLM    │
             │  (Cache) │   │  (Store)  │  │  (vLLM)  │
             └──────────┘   └──────────┘   └──────────┘

                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │    Observability Stack   │
                    │ ┌──────────────────────┐ │
                    │ │ Prometheus │ Grafana │ │
                    │ │            │         │ │
                    │ └──────────────────────┘ │
                    │ ┌──────────────────────┐ │
                    │ │   ELK / Loki Stack   │ │
                    │ └──────────────────────┘ │
                    └──────────────────────────┘
```

### 11.1.2 核心組件說明

| 組件 | 職責 | 技術選型 |
|------|------|----------|
| **API 閘道** | 請求路由、認證、限流 | Nginx / Traefik |
| **API 服務** | 處理 HTTP 請求 | FastAPI |
| **Agent Worker** | 執行研究任務 | Python + Celery |
| **任務佇列** | 任務排程與分發 | Redis / RabbitMQ |
| **資料庫** | 持久化儲存 | PostgreSQL |
| **快取** | 熱點資料快取 | Redis |
| **LLM 服務** | 推理服務 | vLLM |
| **監控** | 指標收集與視覺化 | Prometheus + Grafana |
| **日誌** | 日誌收集與查詢 | Loki / ELK |

### 11.1.3 部署選項比較

| 選項 | 適用場景 | 優點 | 缺點 |
|------|----------|------|------|
| **單機 Docker** | 小型部署、測試 | 簡單、快速 | 無高可用、難擴展 |
| **Docker Compose** | 中小型部署 | 易管理、本地開發 | 單節點限制 |
| **Kubernetes** | 生產環境 | 高可用、自動擴展 | 學習曲線陡峭 |
| **雲端託管** | 快速上線 | 省運維、彈性擴展 | 成本較高、供應商鎖定 |

**本章選擇：Kubernetes**

對於生產級部署，Kubernetes 提供了最佳的可擴展性與可靠性。

---

## 11.2 Docker 容器化

第一步是將應用程式容器化。

### 11.2.1 專案結構

```
research-agent/
├── api/
│   ├── main.py           # FastAPI 應用
│   ├── routers/          # API 路由
│   ├── models/           # 資料模型
│   └── Dockerfile
├── worker/
│   ├── tasks.py          # Celery 任務
│   ├── agents/           # 代理人模組
│   └── Dockerfile
├── docker-compose.yml    # 本地開發
├── kubernetes/           # K8s 配置
│   ├── api-deployment.yaml
│   ├── worker-deployment.yaml
│   └── ...
└── monitoring/
    ├── prometheus.yml
    └── grafana/
```

### 11.2.2 API 服務 Dockerfile

```dockerfile
# api/Dockerfile
# 深度研究代理人 - API 服務
# ================================

# ‹1› 使用 Python 官方映像作為基礎
FROM python:3.11-slim as builder

# ‹2› 設定工作目錄
WORKDIR /app

# ‹3› 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ‹4› 複製依賴檔案
COPY requirements.txt .

# ‹5› 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# ‹6› 複製應用程式碼
COPY . .

# ============================
# 生產階段
# ============================
FROM python:3.11-slim

WORKDIR /app

# ‹7› 只複製必要檔案
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app .

# ‹8› 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ‹9› 建立非 root 使用者
RUN useradd --create-home appuser
USER appuser

# ‹10› 暴露端口
EXPOSE 8000

# ‹11› 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ‹12› 啟動命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 11.2.3 Worker 服務 Dockerfile

```dockerfile
# worker/Dockerfile
# 深度研究代理人 - Worker 服務
# ================================

FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴（包含 Playwright 需要的庫）
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Playwright 瀏覽器
RUN playwright install chromium

COPY . .

ENV PYTHONUNBUFFERED=1

RUN useradd --create-home appuser
USER appuser

# Celery Worker 啟動命令
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info", "--concurrency=4"]
```

### 11.2.4 Docker Compose（本地開發）

```yaml
# docker-compose.yml
# 深度研究代理人 - 本地開發環境
# ================================

version: '3.8'

services:
  # ‹1› API 服務
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/research
      - REDIS_URL=redis://redis:6379/0
      - LLM_API_URL=http://llm:8080/v1
    depends_on:
      - db
      - redis
    volumes:
      - ./api:/app
    networks:
      - research-net

  # ‹2› Worker 服務
  worker:
    build: ./worker
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/research
      - REDIS_URL=redis://redis:6379/0
      - LLM_API_URL=http://llm:8080/v1
    depends_on:
      - db
      - redis
    volumes:
      - ./worker:/app
    networks:
      - research-net
    deploy:
      replicas: 2

  # ‹3› PostgreSQL 資料庫
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=research
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - research-net

  # ‹4› Redis 快取與任務佇列
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    networks:
      - research-net

  # ‹5› Prometheus 監控
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - research-net

  # ‹6› Grafana 儀表板
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    networks:
      - research-net

networks:
  research-net:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
  grafana-data:
```

---

## 11.3 Kubernetes 部署

對於生產環境，我們使用 Kubernetes 來編排容器。

### 11.3.1 命名空間與配置

```yaml
# kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: research-agent
  labels:
    app: research-agent
    environment: production
```

```yaml
# kubernetes/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: research-agent-config
  namespace: research-agent
data:
  LOG_LEVEL: "INFO"
  MAX_CONCURRENT_REQUESTS: "100"
  WORKER_CONCURRENCY: "4"
  CACHE_TTL: "3600"
```

```yaml
# kubernetes/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: research-agent-secrets
  namespace: research-agent
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:password@db:5432/research"
  REDIS_URL: "redis://:password@redis:6379/0"
  LLM_API_KEY: "your-api-key-here"
```

### 11.3.2 API 服務部署

```yaml
# kubernetes/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: research-api
  namespace: research-agent
  labels:
    app: research-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: research-api
  template:
    metadata:
      labels:
        app: research-api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: api
        image: research-agent/api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: research-agent-config
        - secretRef:
            name: research-agent-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: research-api
  namespace: research-agent
spec:
  selector:
    app: research-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### 11.3.3 Worker 部署

```yaml
# kubernetes/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: research-worker
  namespace: research-agent
  labels:
    app: research-worker
spec:
  replicas: 5
  selector:
    matchLabels:
      app: research-worker
  template:
    metadata:
      labels:
        app: research-worker
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9100"
    spec:
      containers:
      - name: worker
        image: research-agent/worker:latest
        envFrom:
        - configMapRef:
            name: research-agent-config
        - secretRef:
            name: research-agent-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
```

### 11.3.4 水平自動擴展

```yaml
# kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: research-api-hpa
  namespace: research-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: research-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: research-worker-hpa
  namespace: research-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: research-worker
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: External
    external:
      metric:
        name: celery_queue_length
        selector:
          matchLabels:
            queue: research
      target:
        type: AverageValue
        averageValue: "10"
```

### 11.3.5 Ingress 配置

```yaml
# kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: research-api-ingress
  namespace: research-agent
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.research-agent.example.com
    secretName: research-api-tls
  rules:
  - host: api.research-agent.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: research-api
            port:
              number: 80
```

---

## 11.4 監控與可觀測性

生產環境需要完善的監控體系。

### 11.4.1 Prometheus 配置

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alertmanager:9093

rule_files:
  - "alerts/*.yml"

scrape_configs:
  # ‹1› API 服務指標
  - job_name: 'research-api'
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - research-agent
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      regex: research-api
      action: keep
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      regex: "true"
      action: keep

  # ‹2› Worker 服務指標
  - job_name: 'research-worker'
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - research-agent
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      regex: research-worker
      action: keep

  # ‹3› Redis 指標
  - job_name: 'redis'
    static_configs:
    - targets: ['redis-exporter:9121']

  # ‹4› PostgreSQL 指標
  - job_name: 'postgres'
    static_configs:
    - targets: ['postgres-exporter:9187']
```

### 11.4.2 應用程式指標

```python
#!/usr/bin/env python3
"""
深度研究代理人 - 應用程式指標模組
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time


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
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
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
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
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
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
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

# ‹7› 系統資訊
SYSTEM_INFO = Info(
    'research_agent_info',
    'Research agent system information'
)


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

    async def get(self, key: str):
        """獲取快取值"""
        value = await self._cache.get(key)
        if value is not None:
            CACHE_HITS.labels(cache_type=self._type).inc()
        else:
            CACHE_MISSES.labels(cache_type=self._type).inc()
        return value

    async def set(self, key: str, value, ttl: int = None):
        """設置快取值"""
        await self._cache.set(key, value, ttl)

    @property
    def hit_rate(self) -> float:
        """計算快取命中率"""
        hits = CACHE_HITS.labels(cache_type=self._type)._value.get()
        misses = CACHE_MISSES.labels(cache_type=self._type)._value.get()
        total = hits + misses
        return hits / total if total > 0 else 0


# =============================================================================
# 健康檢查
# =============================================================================

class HealthChecker:
    """
    健康檢查器

    用於 Kubernetes liveness/readiness probes
    """

    def __init__(self):
        self._checks = {}

    def register(self, name: str, check_func):
        """註冊健康檢查"""
        self._checks[name] = check_func

    async def check_all(self) -> dict:
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

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": results
        }

    async def is_ready(self) -> bool:
        """檢查服務是否就緒"""
        result = await self.check_all()
        return result["status"] == "healthy"


# 建立全域健康檢查器
health_checker = HealthChecker()
```

### 11.4.3 告警規則

```yaml
# monitoring/alerts/research-alerts.yml
groups:
- name: research-agent-alerts
  rules:
  # ‹1› 高錯誤率告警
  - alert: HighErrorRate
    expr: |
      sum(rate(research_requests_total{status="error"}[5m]))
      /
      sum(rate(research_requests_total[5m]))
      > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "高錯誤率"
      description: "錯誤率超過 5%: {{ $value | humanizePercentage }}"

  # ‹2› 高延遲告警
  - alert: HighLatency
    expr: |
      histogram_quantile(0.95,
        sum(rate(research_request_duration_seconds_bucket[5m])) by (le, endpoint)
      ) > 30
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "高延遲"
      description: "P95 延遲超過 30 秒: {{ $value | humanizeDuration }}"

  # ‹3› 研究任務失敗告警
  - alert: ResearchTaskFailures
    expr: |
      sum(rate(research_tasks_total{status="error"}[5m])) by (agent_type) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "研究任務失敗"
      description: "Agent {{ $labels.agent_type }} 失敗率上升"

  # ‹4› LLM 調用失敗告警
  - alert: LLMCallFailures
    expr: |
      sum(rate(llm_calls_total{status="error"}[5m]))
      /
      sum(rate(llm_calls_total[5m]))
      > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "LLM 調用失敗率高"
      description: "LLM 調用失敗率超過 10%"

  # ‹5› 快取命中率低告警
  - alert: LowCacheHitRate
    expr: |
      sum(rate(cache_hits_total[5m]))
      /
      (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))
      < 0.5
    for: 15m
    labels:
      severity: warning
    annotations:
      summary: "快取命中率低"
      description: "快取命中率低於 50%: {{ $value | humanizePercentage }}"

  # ‹6› Worker 佇列積壓告警
  - alert: WorkerQueueBacklog
    expr: celery_queue_length{queue="research"} > 100
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Worker 佇列積壓"
      description: "研究任務佇列長度: {{ $value }}"

  # ‹7› Pod 重啟告警
  - alert: PodRestarts
    expr: |
      increase(kube_pod_container_status_restarts_total{namespace="research-agent"}[1h]) > 3
    for: 0m
    labels:
      severity: warning
    annotations:
      summary: "Pod 頻繁重啟"
      description: "Pod {{ $labels.pod }} 在過去 1 小時重啟 {{ $value }} 次"
```

### 11.4.4 Grafana 儀表板

```json
{
  "dashboard": {
    "title": "Research Agent Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(research_requests_total[5m])) by (status)",
            "legendFormat": "{{status}}"
          }
        ]
      },
      {
        "title": "Request Latency (P95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(research_request_duration_seconds_bucket[5m])) by (le, endpoint))",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Research Tasks",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(increase(research_tasks_total[24h]))",
            "legendFormat": "Total Tasks (24h)"
          }
        ]
      },
      {
        "title": "LLM Token Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(llm_tokens_total[5m])) by (type)",
            "legendFormat": "{{type}}"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))"
          }
        ]
      },
      {
        "title": "Active Workers",
        "type": "stat",
        "targets": [
          {
            "expr": "count(up{job=\"research-worker\"} == 1)"
          }
        ]
      }
    ]
  }
}
```

---

## 11.5 結構化日誌

良好的日誌是除錯與追蹤的基礎。

### 11.5.1 日誌模組

```python
#!/usr/bin/env python3
"""
深度研究代理人 - 結構化日誌模組
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextlib import contextmanager
import uuid
import contextvars

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
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))

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
            question_preview=question[:100],
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
            key_id=key_id[:8] + "...",
            endpoint=endpoint
        )


# 建立全域審計日誌器
audit_logger = AuditLogger()
```

### 11.5.2 FastAPI 中間件整合

```python
#!/usr/bin/env python3
"""
FastAPI 日誌中間件
"""

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

from .logging_module import get_logger, set_request_id, log_with_context

logger = get_logger("api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    日誌中間件

    ‹1› 為每個請求設置唯一 ID
    ‹2› 記錄請求開始和結束
    ‹3› 記錄響應時間
    """

    async def dispatch(self, request: Request, call_next):
        # ‹1› 設置請求 ID
        request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(request_id)

        # ‹2› 記錄請求開始
        start_time = time.time()

        log_with_context(
            logger,
            "INFO",
            f"請求開始: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
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
                duration=duration
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
                duration=duration
            )
            raise


def setup_logging_middleware(app: FastAPI):
    """設置日誌中間件"""
    app.add_middleware(LoggingMiddleware)
```

---

## 11.6 安全性設計

生產環境需要嚴格的安全控制。

### 11.6.1 API 認證

```python
#!/usr/bin/env python3
"""
API 認證模組
"""

from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from typing import Optional
import hashlib
import secrets
from datetime import datetime, timedelta

from .logging_module import get_logger, audit_logger

logger = get_logger("auth")


# =============================================================================
# API Key 管理
# =============================================================================

class APIKeyManager:
    """
    API Key 管理器

    ‹1› 生成與驗證 API Key
    ‹2› 追蹤使用情況
    ‹3› 支援 Key 撤銷
    """

    def __init__(self, db):
        self.db = db

    def generate_key(
        self,
        user_id: str,
        name: str,
        expires_days: int = 365
    ) -> dict:
        """
        生成新的 API Key

        返回：
        {
            "key": "rk_live_xxxx",  # 只顯示一次
            "key_id": "key_xxxx",
            "prefix": "rk_live_xxxx...",
            "expires_at": "2025-01-15T00:00:00Z"
        }
        """
        # 生成 Key
        key = f"rk_live_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_id = f"key_{secrets.token_urlsafe(8)}"

        # 計算過期時間
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

        # 儲存到資料庫（只存 hash）
        self.db.api_keys.insert({
            "key_id": key_id,
            "key_hash": key_hash,
            "user_id": user_id,
            "name": name,
            "prefix": key[:16] + "...",
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
            "last_used_at": None,
            "is_active": True
        })

        logger.info(f"Generated API key: {key_id} for user: {user_id}")

        return {
            "key": key,
            "key_id": key_id,
            "prefix": key[:16] + "...",
            "expires_at": expires_at.isoformat()
        }

    def validate_key(self, key: str) -> Optional[dict]:
        """
        驗證 API Key

        返回使用者資訊或 None
        """
        if not key.startswith("rk_live_"):
            return None

        key_hash = hashlib.sha256(key.encode()).hexdigest()

        # 查詢資料庫
        record = self.db.api_keys.find_one({
            "key_hash": key_hash,
            "is_active": True
        })

        if not record:
            return None

        # 檢查過期
        if record["expires_at"] < datetime.utcnow():
            return None

        # 更新最後使用時間
        self.db.api_keys.update(
            {"key_id": record["key_id"]},
            {"$set": {"last_used_at": datetime.utcnow()}}
        )

        return {
            "user_id": record["user_id"],
            "key_id": record["key_id"],
            "name": record["name"]
        }

    def revoke_key(self, key_id: str, user_id: str) -> bool:
        """撤銷 API Key"""
        result = self.db.api_keys.update(
            {"key_id": key_id, "user_id": user_id},
            {"$set": {"is_active": False}}
        )
        return result.modified_count > 0


# =============================================================================
# FastAPI 依賴
# =============================================================================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    api_key: str = Security(api_key_header),
    key_manager: APIKeyManager = Depends()
) -> dict:
    """
    驗證 API Key 並返回當前使用者

    用於 FastAPI 路由依賴注入
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key"
        )

    user = key_manager.validate_key(api_key)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )

    # 記錄審計日誌
    audit_logger.log_api_key_usage(
        user_id=user["user_id"],
        key_id=user["key_id"],
        endpoint="current"
    )

    return user
```

### 11.6.2 速率限制

```python
#!/usr/bin/env python3
"""
速率限制模組
"""

from fastapi import HTTPException, Request
from typing import Optional
import time
import asyncio
from collections import defaultdict


class RateLimiter:
    """
    速率限制器

    ‹1› 支援滑動視窗演算法
    ‹2› 支援多層級限制
    ‹3› 支援自訂限制規則
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._local_cache = defaultdict(list)  # 本地快取（無 Redis 時）

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple:
        """
        檢查速率限制

        Args:
            key: 限制鍵（如 user_id, ip）
            limit: 限制次數
            window: 時間視窗（秒）

        Returns:
            (allowed, remaining, reset_at)
        """
        now = time.time()

        if self.redis:
            return await self._check_redis(key, limit, window, now)
        else:
            return self._check_local(key, limit, window, now)

    async def _check_redis(
        self,
        key: str,
        limit: int,
        window: int,
        now: float
    ) -> tuple:
        """使用 Redis 進行速率限制"""
        pipe = self.redis.pipeline()

        # 移除過期的請求記錄
        pipe.zremrangebyscore(key, 0, now - window)

        # 添加當前請求
        pipe.zadd(key, {str(now): now})

        # 計算當前請求數
        pipe.zcard(key)

        # 設置過期時間
        pipe.expire(key, window)

        results = await pipe.execute()
        current_count = results[2]

        if current_count > limit:
            return (False, 0, now + window)

        return (True, limit - current_count, now + window)

    def _check_local(
        self,
        key: str,
        limit: int,
        window: int,
        now: float
    ) -> tuple:
        """使用本地快取進行速率限制"""
        # 清理過期記錄
        self._local_cache[key] = [
            t for t in self._local_cache[key]
            if t > now - window
        ]

        current_count = len(self._local_cache[key])

        if current_count >= limit:
            return (False, 0, now + window)

        self._local_cache[key].append(now)
        return (True, limit - current_count - 1, now + window)


# =============================================================================
# 速率限制配置
# =============================================================================

class RateLimitConfig:
    """速率限制配置"""

    # 預設限制
    DEFAULT = {"limit": 100, "window": 60}  # 每分鐘 100 次

    # 研究 API 限制
    RESEARCH = {"limit": 10, "window": 60}  # 每分鐘 10 次研究

    # LLM 調用限制
    LLM = {"limit": 60, "window": 60}  # 每分鐘 60 次 LLM 調用

    # 依用戶層級
    TIERS = {
        "free": {"limit": 10, "window": 60},
        "pro": {"limit": 100, "window": 60},
        "enterprise": {"limit": 1000, "window": 60}
    }


# =============================================================================
# FastAPI 中間件
# =============================================================================

class RateLimitMiddleware:
    """
    速率限制中間件
    """

    def __init__(self, app, limiter: RateLimiter, config: dict = None):
        self.app = app
        self.limiter = limiter
        self.config = config or RateLimitConfig.DEFAULT

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 獲取客戶端 IP
        client_ip = scope.get("client", ("unknown", 0))[0]

        # 檢查速率限制
        allowed, remaining, reset_at = await self.limiter.check_rate_limit(
            f"ratelimit:{client_ip}",
            self.config["limit"],
            self.config["window"]
        )

        if not allowed:
            # 返回 429 Too Many Requests
            response = {
                "error": "Rate limit exceeded",
                "retry_after": int(reset_at - time.time())
            }

            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"retry-after", str(int(reset_at - time.time())).encode()],
                    [b"x-ratelimit-limit", str(self.config["limit"]).encode()],
                    [b"x-ratelimit-remaining", b"0"],
                    [b"x-ratelimit-reset", str(int(reset_at)).encode()],
                ],
            })

            import json
            await send({
                "type": "http.response.body",
                "body": json.dumps(response).encode()
            })
            return

        # 繼續處理請求
        await self.app(scope, receive, send)
```

---

## 11.7 CI/CD 流程

自動化部署是生產環境的關鍵。

### 11.7.1 GitHub Actions 工作流

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov

    - name: Run tests
      run: pytest tests/ --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    steps:
    - uses: actions/checkout@v4

    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Build and push API image
      uses: docker/build-push-action@v5
      with:
        context: ./api
        push: true
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/api:${{ github.sha }}

    - name: Build and push Worker image
      uses: docker/build-push-action@v5
      with:
        context: ./worker
        push: true
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/worker:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v4

    - name: Setup kubectl
      uses: azure/setup-kubectl@v3

    - name: Configure kubeconfig
      run: |
        echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > ~/.kube/config

    - name: Update image tags
      run: |
        sed -i "s|IMAGE_TAG|${{ github.sha }}|g" kubernetes/*.yaml

    - name: Deploy to Kubernetes
      run: |
        kubectl apply -f kubernetes/

    - name: Wait for rollout
      run: |
        kubectl rollout status deployment/research-api -n research-agent
        kubectl rollout status deployment/research-worker -n research-agent

    - name: Notify deployment
      uses: slackapi/slack-github-action@v1
      with:
        payload: |
          {
            "text": "Deployed to production: ${{ github.sha }}"
          }
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 11.7.2 滾動更新策略

```yaml
# kubernetes/api-deployment.yaml (更新策略部分)
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%       # 最多額外 25% 的 Pod
      maxUnavailable: 0   # 更新時不允許服務中斷
  template:
    spec:
      containers:
      - name: api
        # ...
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 10"]  # 優雅關閉
        terminationGracePeriodSeconds: 30
```

---

## 11.8 章節總結

恭喜！你已經掌握了將深度研究代理人系統部署到生產環境的完整流程。

### 核心概念回顧

1. **容器化部署**
   - 使用 Docker 建立標準化的部署單元
   - 多階段建構優化映像大小
   - 健康檢查確保服務狀態

2. **Kubernetes 編排**
   - Deployment 管理應用程式副本
   - Service 提供服務發現
   - HPA 實現自動擴展
   - Ingress 處理外部流量

3. **監控與可觀測性**
   - Prometheus 收集指標
   - Grafana 視覺化儀表板
   - 告警規則及時發現問題
   - 結構化日誌便於追蹤

4. **安全性設計**
   - API Key 認證
   - 速率限制防止濫用
   - 審計日誌記錄操作

5. **CI/CD 自動化**
   - GitHub Actions 自動測試與部署
   - 滾動更新零停機

### 關鍵產出物

| 類型 | 檔案 | 說明 |
|------|------|------|
| Docker | `Dockerfile` | API 與 Worker 容器化 |
| Compose | `docker-compose.yml` | 本地開發環境 |
| K8s | `*-deployment.yaml` | Kubernetes 部署配置 |
| 監控 | `prometheus.yml` | Prometheus 配置 |
| 監控 | `alerts/*.yml` | 告警規則 |
| 日誌 | `logging_module.py` | 結構化日誌 |
| 安全 | `auth_module.py` | API 認證 |
| CI/CD | `.github/workflows/` | 自動化部署 |

### 部署檢查清單

**部署前：**
- [ ] 所有測試通過
- [ ] 容器映像建構成功
- [ ] 配置檔案已更新
- [ ] Secrets 已設置

**部署時：**
- [ ] 滾動更新進行中
- [ ] 健康檢查通過
- [ ] 監控指標正常

**部署後：**
- [ ] 功能測試通過
- [ ] 效能指標穩定
- [ ] 日誌無異常
- [ ] 告警系統正常

---

## 11.9 下一章預告

在下一章「**基準測試全解析**」中，我們將學習如何評估深度研究代理人的品質：

- **HLE 基準測試**：人類專家級評估
- **GAIA 基準測試**：通用 AI 助手評估
- **BrowseComp 基準測試**：網頁瀏覽能力評估
- **自訂評估指標**：根據業務需求設計
- **A/B 測試框架**：持續優化系統

讓我們繼續前進！

---

## 附錄 A：完整檔案清單

```
deployment/
├── api/
│   ├── Dockerfile
│   ├── main.py
│   ├── routers/
│   ├── middleware/
│   └── requirements.txt
├── worker/
│   ├── Dockerfile
│   ├── tasks.py
│   └── requirements.txt
├── kubernetes/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── api-deployment.yaml
│   ├── worker-deployment.yaml
│   ├── hpa.yaml
│   └── ingress.yaml
├── monitoring/
│   ├── prometheus.yml
│   ├── alerts/
│   │   └── research-alerts.yml
│   └── grafana/
│       └── dashboards/
├── docker-compose.yml
└── .github/
    └── workflows/
        └── deploy.yml
```

## 附錄 B：常用命令速查

```bash
# Docker
docker build -t research-api:latest ./api
docker-compose up -d
docker-compose logs -f api

# Kubernetes
kubectl apply -f kubernetes/
kubectl get pods -n research-agent
kubectl logs -f deployment/research-api -n research-agent
kubectl rollout restart deployment/research-api -n research-agent

# 監控
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
kubectl port-forward svc/grafana 3000:3000 -n monitoring

# 除錯
kubectl exec -it pod/research-api-xxx -n research-agent -- /bin/sh
kubectl describe pod research-api-xxx -n research-agent
```
