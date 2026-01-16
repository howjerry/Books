# 第 13 章：企業級部署與維運：讓 Agent 系統穩定運行

> 本章學習目標：
> - 設計 Kubernetes 部署架構
> - 建立完整的 CI/CD 流水線
> - 實作藍綠部署與金絲雀發布
> - 規劃災難恢復與高可用方案

---

## 13.1 生產環境的挑戰

將 Agent 系統從開發環境推向生產，面臨諸多挑戰：

```mermaid
graph TB
    subgraph "生產環境挑戰"
        A[可用性] --> A1[99.9% SLA]
        A --> A2[零停機部署]

        B[擴展性] --> B1[水平擴展]
        B --> B2[流量突增應對]

        C[可維護性] --> C1[版本管理]
        C --> C2[配置管理]

        D[安全性] --> D1[網路隔離]
        D --> D2[秘密管理]
    end
```

### 13.1.1 生產就緒檢查清單

```python
# deployment/readiness_check.py
"""
生產就緒檢查
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class CheckStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "n/a"


@dataclass
class CheckResult:
    """檢查結果"""
    name: str
    category: str
    status: CheckStatus
    message: str
    remediation: str = None


# ‹1› 生產就緒檢查項目
PRODUCTION_CHECKS = [
    # 基礎設施
    {
        "name": "健康檢查端點",
        "category": "infrastructure",
        "check": "has_health_endpoint",
        "description": "服務必須提供 /health 和 /ready 端點"
    },
    {
        "name": "資源限制",
        "category": "infrastructure",
        "check": "has_resource_limits",
        "description": "必須設定 CPU 和記憶體限制"
    },
    {
        "name": "副本數量",
        "category": "infrastructure",
        "check": "min_replicas",
        "description": "生產環境至少 2 個副本"
    },

    # 可觀測性
    {
        "name": "日誌收集",
        "category": "observability",
        "check": "has_logging",
        "description": "必須配置結構化日誌"
    },
    {
        "name": "指標導出",
        "category": "observability",
        "check": "has_metrics",
        "description": "必須導出 Prometheus 指標"
    },
    {
        "name": "追蹤整合",
        "category": "observability",
        "check": "has_tracing",
        "description": "必須整合分散式追蹤"
    },

    # 安全性
    {
        "name": "秘密管理",
        "category": "security",
        "check": "uses_secrets",
        "description": "敏感資訊必須使用 Kubernetes Secrets"
    },
    {
        "name": "網路策略",
        "category": "security",
        "check": "has_network_policy",
        "description": "必須定義網路存取策略"
    },
    {
        "name": "RBAC 配置",
        "category": "security",
        "check": "has_rbac",
        "description": "必須配置適當的 RBAC 權限"
    },

    # 可靠性
    {
        "name": "備份策略",
        "category": "reliability",
        "check": "has_backup",
        "description": "必須配置資料備份"
    },
    {
        "name": "災難恢復",
        "category": "reliability",
        "check": "has_dr_plan",
        "description": "必須有災難恢復計劃"
    },
]
```

---

## 13.2 Kubernetes 部署架構

### 13.2.1 部署清單設計

```yaml
# kubernetes/base/deployment.yaml
# ‹1› Agent 服務部署配置

apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-memory-service
  labels:
    app: agent-memory
    component: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-memory
  template:
    metadata:
      labels:
        app: agent-memory
        component: api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      # ‹2› 服務帳戶
      serviceAccountName: agent-memory-sa

      # ‹3› 初始化容器（等待依賴就緒）
      initContainers:
        - name: wait-for-redis
          image: busybox:1.28
          command: ['sh', '-c', 'until nc -z redis-service 6379; do echo waiting for redis; sleep 2; done;']
        - name: wait-for-postgres
          image: busybox:1.28
          command: ['sh', '-c', 'until nc -z postgres-service 5432; do echo waiting for postgres; sleep 2; done;']

      containers:
        - name: agent-api
          image: agent-memory:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 8080
              name: http
            - containerPort: 9090
              name: grpc

          # ‹4› 資源限制
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2000m"
              memory: "2Gi"

          # ‹5› 環境變數
          env:
            - name: ENVIRONMENT
              value: "production"
            - name: LOG_LEVEL
              value: "info"
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace

          # ‹6› 秘密引用
          envFrom:
            - secretRef:
                name: agent-secrets
            - configMapRef:
                name: agent-config

          # ‹7› 健康檢查
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3

          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3

          startupProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 30

          # ‹8› 卷掛載
          volumeMounts:
            - name: config-volume
              mountPath: /app/config
            - name: tmp-volume
              mountPath: /tmp

      # ‹9› 卷定義
      volumes:
        - name: config-volume
          configMap:
            name: agent-config-files
        - name: tmp-volume
          emptyDir: {}

      # ‹10› 調度策略
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: agent-memory
                topologyKey: kubernetes.io/hostname

      # ‹11› 容錯設定
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: agent-memory
```

### 13.2.2 服務與網路配置

```yaml
# kubernetes/base/service.yaml
# ‹1› 服務定義

apiVersion: v1
kind: Service
metadata:
  name: agent-memory-service
  labels:
    app: agent-memory
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: 8080
    - name: grpc
      port: 9090
      targetPort: 9090
  selector:
    app: agent-memory
    component: api

---
# ‹2› Ingress 配置
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agent-memory-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - agent-api.example.com
      secretName: agent-tls-secret
  rules:
    - host: agent-api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: agent-memory-service
                port:
                  number: 80

---
# ‹3› 網路策略
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent-memory-network-policy
spec:
  podSelector:
    matchLabels:
      app: agent-memory
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # 只允許來自 Ingress controller 的流量
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - port: 8080
    # 允許內部服務間通訊
    - from:
        - podSelector:
            matchLabels:
              app: agent-memory
      ports:
        - port: 9090
  egress:
    # 允許訪問資料庫
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - port: 5432
    # 允許訪問 Redis
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - port: 6379
    # 允許訪問外部 API
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - port: 443
```

### 13.2.3 水平自動擴展

```yaml
# kubernetes/base/hpa.yaml
# ‹1› 水平 Pod 自動擴展

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-memory-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent-memory-service
  minReplicas: 3
  maxReplicas: 20

  # ‹2› 擴展指標
  metrics:
    # CPU 使用率
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

    # 記憶體使用率
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80

    # 自定義指標：請求佇列長度
    - type: Pods
      pods:
        metric:
          name: agent_request_queue_length
        target:
          type: AverageValue
          averageValue: "100"

  # ‹3› 擴展行為
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
        - type: Pods
          value: 4
          periodSeconds: 60
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 25
          periodSeconds: 120
      selectPolicy: Min
```

---

## 13.3 CI/CD 流水線

### 13.3.1 GitHub Actions 配置

```yaml
# .github/workflows/ci-cd.yaml
# ‹1› 完整的 CI/CD 流水線

name: Agent Memory CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ‹2› 程式碼品質檢查
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install ruff mypy black

      - name: Run linters
        run: |
          ruff check .
          black --check .
          mypy src/

  # ‹3› 單元測試
  test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379
        run: |
          pytest tests/ -v --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

  # ‹4› 安全掃描
  security:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'

      - name: Run Bandit security linter
        run: |
          pip install bandit
          bandit -r src/ -ll

  # ‹5› 建構 Docker 映像
  build:
    runs-on: ubuntu-latest
    needs: [test, security]
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=sha,prefix=
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ‹6› 部署到 Staging
  deploy-staging:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/develop'
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Set up kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBE_CONFIG_STAGING }}" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig

      - name: Deploy to staging
        run: |
          kubectl set image deployment/agent-memory-service \
            agent-api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            -n staging

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/agent-memory-service -n staging --timeout=300s

  # ‹7› 部署到 Production
  deploy-production:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Set up kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBE_CONFIG_PRODUCTION }}" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig

      - name: Deploy canary
        run: |
          # 先部署金絲雀
          kubectl set image deployment/agent-memory-canary \
            agent-api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            -n production

      - name: Run smoke tests
        run: |
          ./scripts/smoke-test.sh https://canary.agent-api.example.com

      - name: Promote to production
        run: |
          kubectl set image deployment/agent-memory-service \
            agent-api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            -n production

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/agent-memory-service -n production --timeout=600s
```

---

## 13.4 藍綠部署與金絲雀發布

### 13.4.1 金絲雀發布實作

```yaml
# kubernetes/canary/deployment.yaml
# ‹1› 金絲雀部署配置

apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-memory-canary
  labels:
    app: agent-memory
    version: canary
spec:
  replicas: 1
  selector:
    matchLabels:
      app: agent-memory
      version: canary
  template:
    metadata:
      labels:
        app: agent-memory
        version: canary
    spec:
      containers:
        - name: agent-api
          image: agent-memory:canary
          # ... 其他配置與主部署相同

---
# ‹2› 流量分割
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: agent-memory-vs
spec:
  hosts:
    - agent-api.example.com
  http:
    - match:
        - headers:
            x-canary:
              exact: "true"
      route:
        - destination:
            host: agent-memory-canary
            port:
              number: 80
    - route:
        - destination:
            host: agent-memory-service
            port:
              number: 80
          weight: 95
        - destination:
            host: agent-memory-canary
            port:
              number: 80
          weight: 5

---
# ‹3› 金絲雀分析
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: canary-analysis
spec:
  metrics:
    - name: success-rate
      interval: 1m
      count: 5
      successCondition: result >= 0.95
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            sum(rate(agent_requests_total{version="canary",status="success"}[5m])) /
            sum(rate(agent_requests_total{version="canary"}[5m]))

    - name: latency-p99
      interval: 1m
      count: 5
      successCondition: result <= 2000
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            histogram_quantile(0.99,
              sum(rate(agent_request_duration_seconds_bucket{version="canary"}[5m])) by (le)
            ) * 1000
```

### 13.4.2 漸進式發布控制器

```python
# deployment/progressive_rollout.py
"""
漸進式發布控制器
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio


@dataclass
class RolloutStage:
    """發布階段"""
    name: str
    traffic_percentage: int
    duration_minutes: int
    success_criteria: Dict[str, float]


@dataclass
class RolloutStatus:
    """發布狀態"""
    stage: str
    traffic_percentage: int
    started_at: datetime
    metrics: Dict[str, float]
    healthy: bool
    message: str


class ProgressiveRolloutController:
    """
    漸進式發布控制器
    ‹1› 自動管理金絲雀發布流程
    """

    def __init__(
        self,
        kubernetes_client,
        metrics_client,
        alerting_client
    ):
        self.k8s = kubernetes_client
        self.metrics = metrics_client
        self.alerting = alerting_client

        # ‹2› 預設發布階段
        self.default_stages = [
            RolloutStage(
                name="canary-5",
                traffic_percentage=5,
                duration_minutes=10,
                success_criteria={
                    "error_rate": 0.01,
                    "latency_p99_ms": 2000
                }
            ),
            RolloutStage(
                name="canary-25",
                traffic_percentage=25,
                duration_minutes=15,
                success_criteria={
                    "error_rate": 0.01,
                    "latency_p99_ms": 2000
                }
            ),
            RolloutStage(
                name="canary-50",
                traffic_percentage=50,
                duration_minutes=20,
                success_criteria={
                    "error_rate": 0.01,
                    "latency_p99_ms": 2000
                }
            ),
            RolloutStage(
                name="full",
                traffic_percentage=100,
                duration_minutes=0,
                success_criteria={}
            ),
        ]

    async def execute_rollout(
        self,
        deployment_name: str,
        new_image: str,
        namespace: str = "production",
        stages: List[RolloutStage] = None
    ) -> bool:
        """
        執行漸進式發布
        ‹3› 逐階段增加流量，監控指標
        """
        stages = stages or self.default_stages

        for i, stage in enumerate(stages):
            print(f"Starting stage: {stage.name} ({stage.traffic_percentage}%)")

            # 更新流量比例
            await self._update_traffic_split(
                deployment_name,
                namespace,
                stage.traffic_percentage
            )

            # 等待並監控
            if stage.duration_minutes > 0:
                healthy = await self._monitor_stage(
                    deployment_name,
                    namespace,
                    stage.duration_minutes,
                    stage.success_criteria
                )

                if not healthy:
                    print(f"Stage {stage.name} failed, initiating rollback")
                    await self._rollback(deployment_name, namespace)
                    return False

            print(f"Stage {stage.name} completed successfully")

        print("Rollout completed successfully")
        return True

    async def _update_traffic_split(
        self,
        deployment_name: str,
        namespace: str,
        canary_percentage: int
    ):
        """
        更新流量分配
        ‹4› 調整金絲雀的流量比例
        """
        stable_percentage = 100 - canary_percentage

        # 更新 VirtualService
        await self.k8s.patch_virtual_service(
            name=f"{deployment_name}-vs",
            namespace=namespace,
            patch={
                "spec": {
                    "http": [{
                        "route": [
                            {
                                "destination": {"host": deployment_name},
                                "weight": stable_percentage
                            },
                            {
                                "destination": {"host": f"{deployment_name}-canary"},
                                "weight": canary_percentage
                            }
                        ]
                    }]
                }
            }
        )

    async def _monitor_stage(
        self,
        deployment_name: str,
        namespace: str,
        duration_minutes: int,
        success_criteria: Dict[str, float]
    ) -> bool:
        """
        監控階段
        ‹5› 持續檢查指標是否達標
        """
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        check_interval = 30  # 每 30 秒檢查一次

        while datetime.now() < end_time:
            metrics = await self._get_canary_metrics(deployment_name, namespace)

            # 檢查成功條件
            for metric_name, threshold in success_criteria.items():
                actual = metrics.get(metric_name, 0)

                if metric_name == "error_rate" and actual > threshold:
                    print(f"Error rate {actual:.4f} exceeds threshold {threshold}")
                    return False

                if metric_name == "latency_p99_ms" and actual > threshold:
                    print(f"Latency {actual:.2f}ms exceeds threshold {threshold}ms")
                    return False

            await asyncio.sleep(check_interval)

        return True

    async def _get_canary_metrics(
        self,
        deployment_name: str,
        namespace: str
    ) -> Dict[str, float]:
        """獲取金絲雀指標"""
        error_rate = await self.metrics.query(
            f'sum(rate(agent_requests_total{{version="canary",status="error"}}[5m])) / '
            f'sum(rate(agent_requests_total{{version="canary"}}[5m]))'
        )

        latency = await self.metrics.query(
            f'histogram_quantile(0.99, '
            f'sum(rate(agent_request_duration_seconds_bucket{{version="canary"}}[5m])) by (le)) * 1000'
        )

        return {
            "error_rate": error_rate,
            "latency_p99_ms": latency
        }

    async def _rollback(self, deployment_name: str, namespace: str):
        """
        回滾
        ‹6› 將流量完全切回穩定版本
        """
        await self._update_traffic_split(deployment_name, namespace, 0)

        await self.alerting.send_alert(
            severity="warning",
            title=f"Rollout rollback: {deployment_name}",
            message="Canary deployment failed health checks, traffic rolled back to stable version"
        )
```

---

## 13.5 災難恢復與高可用

### 13.5.1 備份策略

```python
# deployment/backup.py
"""
備份與恢復系統
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio


@dataclass
class BackupConfig:
    """備份配置"""
    name: str
    schedule: str  # cron 表達式
    retention_days: int
    storage_class: str
    encryption: bool


@dataclass
class BackupJob:
    """備份任務"""
    job_id: str
    backup_type: str  # full, incremental
    started_at: datetime
    completed_at: Optional[datetime]
    status: str  # running, completed, failed
    size_bytes: int
    location: str


class BackupManager:
    """
    備份管理器
    ‹1› 管理資料備份和恢復
    """

    def __init__(
        self,
        storage_client,
        database_client,
        vector_db_client
    ):
        self.storage = storage_client
        self.db = database_client
        self.vector_db = vector_db_client

        # ‹2› 備份配置
        self.backup_configs = {
            "postgres": BackupConfig(
                name="postgres-backup",
                schedule="0 2 * * *",  # 每天凌晨 2 點
                retention_days=30,
                storage_class="STANDARD",
                encryption=True
            ),
            "redis": BackupConfig(
                name="redis-backup",
                schedule="0 */6 * * *",  # 每 6 小時
                retention_days=7,
                storage_class="STANDARD",
                encryption=True
            ),
            "vector_db": BackupConfig(
                name="vector-db-backup",
                schedule="0 3 * * *",  # 每天凌晨 3 點
                retention_days=14,
                storage_class="STANDARD",
                encryption=True
            ),
        }

    async def create_backup(
        self,
        backup_type: str,
        full: bool = True
    ) -> BackupJob:
        """
        創建備份
        ‹3› 執行指定類型的備份
        """
        config = self.backup_configs.get(backup_type)
        if not config:
            raise ValueError(f"Unknown backup type: {backup_type}")

        job = BackupJob(
            job_id=f"{backup_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            backup_type="full" if full else "incremental",
            started_at=datetime.now(),
            completed_at=None,
            status="running",
            size_bytes=0,
            location=""
        )

        try:
            if backup_type == "postgres":
                location, size = await self._backup_postgres(config)
            elif backup_type == "redis":
                location, size = await self._backup_redis(config)
            elif backup_type == "vector_db":
                location, size = await self._backup_vector_db(config)

            job.completed_at = datetime.now()
            job.status = "completed"
            job.size_bytes = size
            job.location = location

        except Exception as e:
            job.completed_at = datetime.now()
            job.status = "failed"
            raise

        return job

    async def _backup_postgres(
        self,
        config: BackupConfig
    ) -> tuple:
        """
        PostgreSQL 備份
        ‹4› 使用 pg_dump 創建備份
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"postgres_backup_{timestamp}.sql.gz"
        location = f"s3://backups/postgres/{filename}"

        # 執行 pg_dump
        await self.db.execute_backup(
            output_path=f"/tmp/{filename}",
            compressed=True
        )

        # 上傳到雲端儲存
        size = await self.storage.upload(
            local_path=f"/tmp/{filename}",
            remote_path=location,
            storage_class=config.storage_class,
            encrypt=config.encryption
        )

        return location, size

    async def restore_from_backup(
        self,
        backup_type: str,
        backup_location: str,
        target_timestamp: datetime = None
    ) -> bool:
        """
        從備份恢復
        ‹5› 支援 point-in-time 恢復
        """
        print(f"Starting restore from {backup_location}")

        # 下載備份
        local_path = await self.storage.download(backup_location)

        if backup_type == "postgres":
            await self.db.restore(
                backup_path=local_path,
                target_timestamp=target_timestamp
            )
        elif backup_type == "redis":
            await self._restore_redis(local_path)
        elif backup_type == "vector_db":
            await self._restore_vector_db(local_path)

        print("Restore completed successfully")
        return True

    async def cleanup_old_backups(self):
        """
        清理過期備份
        ‹6› 根據保留策略刪除舊備份
        """
        for backup_type, config in self.backup_configs.items():
            cutoff = datetime.now() - timedelta(days=config.retention_days)

            backups = await self.storage.list_backups(
                prefix=f"backups/{backup_type}/"
            )

            for backup in backups:
                if backup.created_at < cutoff:
                    await self.storage.delete(backup.location)
                    print(f"Deleted old backup: {backup.location}")
```

### 13.5.2 高可用架構

```yaml
# kubernetes/ha/multi-region.yaml
# ‹1› 多區域高可用配置

apiVersion: v1
kind: ConfigMap
metadata:
  name: ha-config
data:
  primary_region: "us-east-1"
  secondary_region: "us-west-2"
  failover_threshold_seconds: "30"

---
# ‹2› 跨區域服務發現
apiVersion: multicluster.x-k8s.io/v1alpha1
kind: ServiceExport
metadata:
  name: agent-memory-service
  namespace: production
spec:
  export:
    - name: agent-memory-service
      ports:
        - port: 80
          protocol: TCP

---
# ‹3› 全域負載平衡
apiVersion: networking.gke.io/v1beta1
kind: MultiClusterService
metadata:
  name: agent-memory-global
  namespace: production
spec:
  template:
    spec:
      selector:
        app: agent-memory
      ports:
        - port: 80
          targetPort: 8080
  clusters:
    - link: "us-east-1/production-cluster"
      weight: 70
    - link: "us-west-2/production-cluster"
      weight: 30
```

### 13.5.3 災難恢復計劃

```python
# deployment/disaster_recovery.py
"""
災難恢復計劃
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class DisasterType(Enum):
    REGION_OUTAGE = "region_outage"
    DATABASE_CORRUPTION = "database_corruption"
    SECURITY_BREACH = "security_breach"
    DATA_LOSS = "data_loss"


@dataclass
class RecoveryStep:
    """恢復步驟"""
    order: int
    name: str
    description: str
    estimated_duration_minutes: int
    runbook_link: str
    automated: bool


@dataclass
class RecoveryPlan:
    """恢復計劃"""
    disaster_type: DisasterType
    rto_minutes: int  # Recovery Time Objective
    rpo_minutes: int  # Recovery Point Objective
    steps: List[RecoveryStep]
    escalation_contacts: List[str]


# ‹1› 災難恢復計劃
RECOVERY_PLANS = {
    DisasterType.REGION_OUTAGE: RecoveryPlan(
        disaster_type=DisasterType.REGION_OUTAGE,
        rto_minutes=15,
        rpo_minutes=5,
        steps=[
            RecoveryStep(
                order=1,
                name="確認故障",
                description="驗證主要區域確實無法訪問",
                estimated_duration_minutes=2,
                runbook_link="/runbooks/verify-outage",
                automated=True
            ),
            RecoveryStep(
                order=2,
                name="切換 DNS",
                description="將流量切換到備用區域",
                estimated_duration_minutes=5,
                runbook_link="/runbooks/dns-failover",
                automated=True
            ),
            RecoveryStep(
                order=3,
                name="驗證服務",
                description="確認備用區域服務正常",
                estimated_duration_minutes=3,
                runbook_link="/runbooks/verify-services",
                automated=True
            ),
            RecoveryStep(
                order=4,
                name="通知利害關係人",
                description="發送故障通知",
                estimated_duration_minutes=2,
                runbook_link="/runbooks/notify-stakeholders",
                automated=True
            ),
            RecoveryStep(
                order=5,
                name="監控恢復",
                description="持續監控直到主區域恢復",
                estimated_duration_minutes=0,
                runbook_link="/runbooks/monitor-recovery",
                automated=False
            ),
        ],
        escalation_contacts=[
            "oncall@example.com",
            "platform-team@example.com",
            "cto@example.com"
        ]
    ),

    DisasterType.DATABASE_CORRUPTION: RecoveryPlan(
        disaster_type=DisasterType.DATABASE_CORRUPTION,
        rto_minutes=60,
        rpo_minutes=15,
        steps=[
            RecoveryStep(
                order=1,
                name="停止寫入",
                description="立即停止所有資料庫寫入操作",
                estimated_duration_minutes=2,
                runbook_link="/runbooks/stop-writes",
                automated=True
            ),
            RecoveryStep(
                order=2,
                name="評估損壞範圍",
                description="確定受影響的資料範圍",
                estimated_duration_minutes=10,
                runbook_link="/runbooks/assess-corruption",
                automated=False
            ),
            RecoveryStep(
                order=3,
                name="選擇恢復點",
                description="選擇最近的有效備份",
                estimated_duration_minutes=5,
                runbook_link="/runbooks/select-backup",
                automated=False
            ),
            RecoveryStep(
                order=4,
                name="執行恢復",
                description="從備份恢復資料庫",
                estimated_duration_minutes=30,
                runbook_link="/runbooks/restore-database",
                automated=True
            ),
            RecoveryStep(
                order=5,
                name="驗證資料完整性",
                description="執行資料完整性檢查",
                estimated_duration_minutes=10,
                runbook_link="/runbooks/verify-integrity",
                automated=True
            ),
            RecoveryStep(
                order=6,
                name="恢復服務",
                description="重新啟用寫入和服務",
                estimated_duration_minutes=3,
                runbook_link="/runbooks/resume-service",
                automated=True
            ),
        ],
        escalation_contacts=[
            "dba-team@example.com",
            "oncall@example.com",
            "cto@example.com"
        ]
    ),
}


class DisasterRecoveryOrchestrator:
    """
    災難恢復協調器
    ‹2› 自動執行恢復計劃
    """

    def __init__(
        self,
        kubernetes_client,
        database_client,
        dns_client,
        notification_client
    ):
        self.k8s = kubernetes_client
        self.db = database_client
        self.dns = dns_client
        self.notify = notification_client

    async def execute_recovery(
        self,
        disaster_type: DisasterType,
        auto_approve: bool = False
    ) -> Dict:
        """
        執行恢復計劃
        ‹3› 按步驟執行恢復
        """
        plan = RECOVERY_PLANS.get(disaster_type)
        if not plan:
            raise ValueError(f"No recovery plan for: {disaster_type}")

        results = {
            "disaster_type": disaster_type.value,
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "status": "running"
        }

        # 發送初始通知
        await self.notify.send(
            channels=plan.escalation_contacts,
            message=f"Disaster recovery initiated: {disaster_type.value}",
            severity="critical"
        )

        for step in plan.steps:
            step_result = {
                "name": step.name,
                "status": "pending"
            }

            try:
                if step.automated:
                    # 自動執行
                    await self._execute_step(step, disaster_type)
                    step_result["status"] = "completed"
                else:
                    if auto_approve:
                        await self._execute_step(step, disaster_type)
                        step_result["status"] = "completed"
                    else:
                        # 需要人工確認
                        step_result["status"] = "manual_required"
                        step_result["runbook"] = step.runbook_link

            except Exception as e:
                step_result["status"] = "failed"
                step_result["error"] = str(e)
                results["status"] = "failed"

                # 發送失敗通知
                await self.notify.send(
                    channels=plan.escalation_contacts,
                    message=f"Recovery step failed: {step.name} - {str(e)}",
                    severity="critical"
                )
                break

            results["steps"].append(step_result)

        if results["status"] == "running":
            results["status"] = "completed"

        results["completed_at"] = datetime.now().isoformat()
        return results

    async def _execute_step(
        self,
        step: RecoveryStep,
        disaster_type: DisasterType
    ):
        """執行單個恢復步驟"""
        # 根據步驟類型執行對應操作
        step_handlers = {
            "切換 DNS": self._failover_dns,
            "停止寫入": self._stop_database_writes,
            "執行恢復": self._restore_database,
            # ... 其他步驟處理器
        }

        handler = step_handlers.get(step.name)
        if handler:
            await handler()
```

---

## 13.6 總結與下一步

### 本章回顧

在本章中，我們：

1. **設計了 Kubernetes 部署架構**：完整的 Deployment、Service、Ingress 配置
2. **建立了 CI/CD 流水線**：從程式碼提交到生產部署的自動化流程
3. **實作了漸進式發布**：金絲雀發布與自動回滾機制
4. **規劃了災難恢復方案**：備份策略、高可用架構、恢復計劃

### 關鍵決策說明

| 決策點 | 選擇 | 原因 |
|--------|------|------|
| 容器編排 | Kubernetes | 業界標準，功能豐富 |
| CI/CD 平台 | GitHub Actions | 與 GitHub 整合，易於使用 |
| 發布策略 | 金絲雀 | 風險可控，易於回滾 |
| 高可用 | 多區域主動-被動 | 成本與可用性平衡 |
| 備份策略 | 每日全量 + WAL | 支援 point-in-time 恢復 |

### 生產部署檢查清單

- [ ] 所有健康檢查端點已配置
- [ ] 資源限制已設定
- [ ] 自動擴展已啟用
- [ ] 監控告警已配置
- [ ] 日誌收集已設定
- [ ] 備份已驗證
- [ ] 災難恢復計劃已演練
- [ ] 安全掃描已通過

### 全書總結

恭喜你完成了本書的學習！讓我們回顧一下我們的旅程：

```
第一部：基礎篇
├── 第 1 章：建立第一個 RAG 系統
├── 第 2 章：優化檢索品質
└── 第 3 章：向量資料庫選型

第二部：進階篇
├── 第 4 章：從 RAG 到 Agent
├── 第 5 章：多資料來源整合
└── 第 6 章：工具生態系統

第三部：生產篇
├── 第 7 章：記憶系統架構
├── 第 8 章：個人化學習
└── 第 9 章：多模態記憶

第四部：治理篇
├── 第 10 章：可觀測性
├── 第 11 章：成本優化
├── 第 12 章：安全與隱私
└── 第 13 章：企業級部署
```

你現在已經具備了從零開始構建企業級 Agent 記憶系統的完整能力。

### 持續學習資源

- **官方文檔**：LangChain、OpenAI、Anthropic
- **社群**：AI 開發者社群、Kubernetes 社群
- **實踐**：將本書的知識應用到實際專案中

祝你在 AI Agent 開發的道路上一切順利！

---

完整程式碼請參見 `code-examples/chapter-13/` 目錄。
