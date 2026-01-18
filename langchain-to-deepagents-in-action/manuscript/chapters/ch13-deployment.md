# Chapter 13: 容器化與部署

> 「軟體的價值在於運行，而非編寫。」——佚名

---

## 本章學習目標

完成本章後，你將能夠：

1. 使用 Docker 容器化 TechAssist Agent 應用
2. 設計適合 Agent 系統的 Kubernetes 架構
3. 建立完整的 CI/CD 流水線
4. 實施藍綠部署和金絲雀發布策略
5. 配置生產環境的監控和告警

---

## 13.1 容器化策略

### 場景：準備上線

經過數月的開發和測試，TechAssist v2.0 終於準備好進入生產環境。DevOps 團隊收到部署需求：

> 「我們需要在三個區域部署 TechAssist，支持高可用和自動擴縮容。預計日活用戶 10,000+，峰值 QPS 100。」

### 13.1.1 容器化架構

```mermaid
graph TB
    subgraph "TechAssist 容器群"
        API[API Gateway<br/>FastAPI]
        WORKER1[Agent Worker 1]
        WORKER2[Agent Worker 2]
        WORKER3[Agent Worker N...]
    end

    subgraph "支援服務"
        REDIS[Redis<br/>快取 & 隊列]
        QDRANT[Qdrant<br/>向量資料庫]
        POSTGRES[PostgreSQL<br/>持久化]
    end

    subgraph "可觀測性"
        OTEL[OTel Collector]
        PROMETHEUS[Prometheus]
        JAEGER[Jaeger]
    end

    API --> WORKER1
    API --> WORKER2
    API --> WORKER3

    WORKER1 --> REDIS
    WORKER1 --> QDRANT
    WORKER1 --> POSTGRES

    WORKER1 --> OTEL
    OTEL --> PROMETHEUS
    OTEL --> JAEGER
```

### 13.1.2 Dockerfile 設計

```dockerfile
# techassist_v20/Dockerfile
# ‹1› 多階段構建：構建階段
FROM python:3.11-slim as builder

WORKDIR /app

# 安裝構建依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .

# 創建虛擬環境並安裝依賴
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# ‹2› 運行階段
FROM python:3.11-slim as runtime

WORKDIR /app

# 安裝運行時依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 從構建階段複製虛擬環境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ‹3› 創建非 root 用戶
RUN useradd --create-home --shell /bin/bash techassist
USER techassist

# 複製應用程式碼
COPY --chown=techassist:techassist . .

# ‹4› 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 暴露端口
EXPOSE 8000

# ‹5› 啟動命令
CMD ["uvicorn", "techassist_v20.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Dockerfile 解析：**
- ‹1› 多階段構建減小最終鏡像大小
- ‹2› 運行階段只包含必要組件
- ‹3› 非 root 用戶增強安全性
- ‹4› 健康檢查支援 K8s 存活探針
- ‹5› 使用 uvicorn 作為 ASGI 服務器

### 13.1.3 Docker Compose 開發環境

```yaml
# docker-compose.yml
version: '3.8'

services:
  # ‹1› TechAssist API
  techassist:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
      - POSTGRES_URL=postgresql://techassist:secret@postgres:5432/techassist
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    depends_on:
      - redis
      - qdrant
      - postgres
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  # ‹2› Redis 快取
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # ‹3› Qdrant 向量資料庫
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334

  # ‹4› PostgreSQL
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=techassist
      - POSTGRES_PASSWORD=secret
      - POSTGRES_DB=techassist
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # ‹5› OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP

  # ‹6› Jaeger 追蹤
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "14250:14250"  # gRPC

  # ‹7› Prometheus 指標
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  # ‹8› Grafana 儀表板
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning

volumes:
  redis_data:
  qdrant_data:
  postgres_data:
  prometheus_data:
  grafana_data:
```

---

## 13.2 Kubernetes 部署

### 13.2.1 K8s 資源設計

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: techassist
  labels:
    app: techassist
    environment: production
```

```yaml
# k8s/configmap.yaml
# ‹1› 配置映射
apiVersion: v1
kind: ConfigMap
metadata:
  name: techassist-config
  namespace: techassist
data:
  LOG_LEVEL: "INFO"
  MAX_CONCURRENT_REQUESTS: "50"
  CACHE_TTL: "3600"
  QUALITY_THRESHOLD: "0.8"
```

```yaml
# k8s/secret.yaml
# ‹2› 敏感配置（實際應使用外部密鑰管理）
apiVersion: v1
kind: Secret
metadata:
  name: techassist-secrets
  namespace: techassist
type: Opaque
data:
  ANTHROPIC_API_KEY: <base64-encoded>
  POSTGRES_PASSWORD: <base64-encoded>
```

### 13.2.2 Deployment 配置

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: techassist-api
  namespace: techassist
  labels:
    app: techassist
    component: api
spec:
  # ‹1› 副本數
  replicas: 3

  selector:
    matchLabels:
      app: techassist
      component: api

  # ‹2› 滾動更新策略
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0

  template:
    metadata:
      labels:
        app: techassist
        component: api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"

    spec:
      # ‹3› 服務帳號
      serviceAccountName: techassist-sa

      # ‹4› 反親和性：分散到不同節點
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: techassist
                topologyKey: kubernetes.io/hostname

      containers:
        - name: techassist
          image: techassist:v2.0.0
          imagePullPolicy: Always

          ports:
            - containerPort: 8000
              name: http

          # ‹5› 環境變數
          envFrom:
            - configMapRef:
                name: techassist-config
            - secretRef:
                name: techassist-secrets

          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: REDIS_URL
              value: "redis://redis-master.techassist:6379"
            - name: QDRANT_URL
              value: "http://qdrant.techassist:6333"

          # ‹6› 資源限制
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "2Gi"
              cpu: "1000m"

          # ‹7› 探針配置
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
            timeoutSeconds: 5
            failureThreshold: 3

          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3

          # ‹8› 生命週期鉤子
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 10"]

          # ‹9› 卷掛載
          volumeMounts:
            - name: logs
              mountPath: /app/logs
            - name: tmp
              mountPath: /tmp

      volumes:
        - name: logs
          emptyDir: {}
        - name: tmp
          emptyDir: {}

      # ‹10› 終止等待時間
      terminationGracePeriodSeconds: 60
```

**K8s Deployment 解析：**
- ‹1› 3 副本確保高可用
- ‹2› 滾動更新，零停機
- ‹3› 最小權限服務帳號
- ‹4› 反親和性分散風險
- ‹5› 分離配置和密鑰
- ‹6› 資源限制防止資源耗盡
- ‹7› 存活和就緒探針
- ‹8› preStop 鉤子優雅終止
- ‹9› emptyDir 臨時存儲
- ‹10› 足夠的終止等待時間

### 13.2.3 Service 和 Ingress

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: techassist-api
  namespace: techassist
spec:
  selector:
    app: techassist
    component: api
  ports:
    - port: 80
      targetPort: 8000
      name: http
  type: ClusterIP
---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: techassist-ingress
  namespace: techassist
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
    - hosts:
        - api.techassist.example.com
      secretName: techassist-tls
  rules:
    - host: api.techassist.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: techassist-api
                port:
                  number: 80
```

### 13.2.4 HPA 自動擴縮容

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: techassist-hpa
  namespace: techassist
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: techassist-api

  # ‹1› 副本數範圍
  minReplicas: 3
  maxReplicas: 20

  # ‹2› 擴縮容指標
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

    # ‹3› 自定義指標：請求速率
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "50"

  # ‹4› 擴縮容行為
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
          value: 10
          periodSeconds: 60
      selectPolicy: Min
```

---

## 13.3 CI/CD 流水線

### 13.3.1 GitHub Actions 配置

```yaml
# .github/workflows/ci-cd.yaml
name: TechAssist CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ‹1› 測試階段
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: pytest --cov=techassist_v20 --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4

  # ‹2› 安全掃描
  security:
    runs-on: ubuntu-latest
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
          bandit -r techassist_v20/ -ll

  # ‹3› 構建和推送鏡像
  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    permissions:
      contents: read
      packages: write

    outputs:
      image_tag: ${{ steps.meta.outputs.tags }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
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
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ‹4› 部署到 Staging
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Set up kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBE_CONFIG_STAGING }}" | base64 -d > ~/.kube/config

      - name: Deploy to staging
        run: |
          kubectl set image deployment/techassist-api \
            techassist=${{ needs.build.outputs.image_tag }} \
            -n techassist-staging

      - name: Wait for rollout
        run: kubectl rollout status deployment/techassist-api -n techassist-staging --timeout=300s

  # ‹5› 部署到生產（需要審批）
  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://api.techassist.example.com

    steps:
      - uses: actions/checkout@v4

      - name: Set up kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBE_CONFIG_PRODUCTION }}" | base64 -d > ~/.kube/config

      - name: Deploy canary (10%)
        run: |
          kubectl apply -f k8s/canary-deployment.yaml
          kubectl set image deployment/techassist-api-canary \
            techassist=${{ needs.build.outputs.image_tag }} \
            -n techassist

      - name: Wait and verify canary
        run: |
          sleep 300  # 等待 5 分鐘
          # 檢查錯誤率
          ERROR_RATE=$(kubectl exec -n techassist deploy/prometheus -- \
            promtool query instant 'rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])' | jq -r '.data.result[0].value[1]')
          if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
            echo "Error rate too high: $ERROR_RATE"
            kubectl rollout undo deployment/techassist-api-canary -n techassist
            exit 1
          fi

      - name: Promote to full deployment
        run: |
          kubectl set image deployment/techassist-api \
            techassist=${{ needs.build.outputs.image_tag }} \
            -n techassist
          kubectl rollout status deployment/techassist-api -n techassist --timeout=600s

      - name: Cleanup canary
        run: kubectl delete deployment techassist-api-canary -n techassist --ignore-not-found
```

---

## 13.4 藍綠部署與金絲雀發布

### 13.4.1 藍綠部署配置

```yaml
# k8s/blue-green/blue-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: techassist-blue
  namespace: techassist
  labels:
    app: techassist
    version: blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: techassist
      version: blue
  template:
    metadata:
      labels:
        app: techassist
        version: blue
    spec:
      containers:
        - name: techassist
          image: techassist:v2.0.0
          # ... 其他配置
---
# k8s/blue-green/green-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: techassist-green
  namespace: techassist
  labels:
    app: techassist
    version: green
spec:
  replicas: 0  # 初始為 0
  selector:
    matchLabels:
      app: techassist
      version: green
  template:
    metadata:
      labels:
        app: techassist
        version: green
    spec:
      containers:
        - name: techassist
          image: techassist:v2.1.0  # 新版本
          # ... 其他配置
---
# k8s/blue-green/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: techassist-api
  namespace: techassist
spec:
  selector:
    app: techassist
    version: blue  # 切換這裡來切換流量
  ports:
    - port: 80
      targetPort: 8000
```

### 13.4.2 藍綠切換腳本

```bash
#!/bin/bash
# scripts/blue-green-switch.sh

set -e

NAMESPACE="techassist"
NEW_VERSION=$1

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <blue|green>"
    exit 1
fi

# ‹1› 確定當前和目標版本
CURRENT=$(kubectl get svc techassist-api -n $NAMESPACE -o jsonpath='{.spec.selector.version}')

if [ "$CURRENT" == "$NEW_VERSION" ]; then
    echo "Already running $NEW_VERSION"
    exit 0
fi

echo "Switching from $CURRENT to $NEW_VERSION"

# ‹2› 擴展新版本
kubectl scale deployment techassist-$NEW_VERSION --replicas=3 -n $NAMESPACE

# ‹3› 等待就緒
kubectl rollout status deployment/techassist-$NEW_VERSION -n $NAMESPACE --timeout=300s

# ‹4› 健康檢查
echo "Running health checks..."
for i in {1..5}; do
    POD=$(kubectl get pods -n $NAMESPACE -l version=$NEW_VERSION -o jsonpath='{.items[0].metadata.name}')
    HEALTH=$(kubectl exec -n $NAMESPACE $POD -- curl -s http://localhost:8000/health | jq -r '.status')
    if [ "$HEALTH" != "healthy" ]; then
        echo "Health check failed, aborting"
        kubectl scale deployment techassist-$NEW_VERSION --replicas=0 -n $NAMESPACE
        exit 1
    fi
    sleep 5
done

# ‹5› 切換流量
kubectl patch svc techassist-api -n $NAMESPACE -p "{\"spec\":{\"selector\":{\"version\":\"$NEW_VERSION\"}}}"

echo "Traffic switched to $NEW_VERSION"

# ‹6› 縮減舊版本
sleep 60  # 等待現有連接完成
kubectl scale deployment techassist-$CURRENT --replicas=0 -n $NAMESPACE

echo "Blue-green switch completed"
```

### 13.4.3 金絲雀發布配置

```yaml
# k8s/canary/canary-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: techassist-api-canary
  namespace: techassist
  labels:
    app: techassist
    track: canary
spec:
  replicas: 1  # 金絲雀只需少量副本
  selector:
    matchLabels:
      app: techassist
      track: canary
  template:
    metadata:
      labels:
        app: techassist
        track: canary
    spec:
      containers:
        - name: techassist
          image: techassist:v2.1.0-canary
          # ... 配置
---
# k8s/canary/traffic-split.yaml (Istio)
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: techassist-vs
  namespace: techassist
spec:
  hosts:
    - techassist-api
  http:
    - route:
        - destination:
            host: techassist-api
            subset: stable
          weight: 90
        - destination:
            host: techassist-api
            subset: canary
          weight: 10
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: techassist-dr
  namespace: techassist
spec:
  host: techassist-api
  subsets:
    - name: stable
      labels:
        track: stable
    - name: canary
      labels:
        track: canary
```

---

## 13.5 生產環境監控

### 13.5.1 Prometheus 告警規則

```yaml
# k8s/monitoring/alerting-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: techassist-alerts
  namespace: techassist
spec:
  groups:
    - name: techassist-availability
      rules:
        # ‹1› 高錯誤率
        - alert: HighErrorRate
          expr: |
            sum(rate(http_requests_total{status=~"5..",app="techassist"}[5m])) /
            sum(rate(http_requests_total{app="techassist"}[5m])) > 0.01
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "TechAssist 錯誤率過高"
            description: "錯誤率 {{ $value | humanizePercentage }} 超過 1%"

        # ‹2› 高延遲
        - alert: HighLatency
          expr: |
            histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{app="techassist"}[5m])) by (le)) > 5
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "TechAssist P95 延遲過高"
            description: "P95 延遲 {{ $value }}s 超過 5 秒"

        # ‹3› Pod 不健康
        - alert: PodNotReady
          expr: |
            kube_pod_status_ready{namespace="techassist",condition="true"} == 0
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "TechAssist Pod 未就緒"
            description: "Pod {{ $labels.pod }} 未就緒超過 5 分鐘"

    - name: techassist-resources
      rules:
        # ‹4› 記憶體壓力
        - alert: HighMemoryUsage
          expr: |
            container_memory_usage_bytes{namespace="techassist",container="techassist"} /
            container_spec_memory_limit_bytes{namespace="techassist",container="techassist"} > 0.85
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "TechAssist 記憶體使用率高"

        # ‹5› CPU 飽和
        - alert: HighCPUUsage
          expr: |
            rate(container_cpu_usage_seconds_total{namespace="techassist",container="techassist"}[5m]) /
            container_spec_cpu_quota{namespace="techassist",container="techassist"} * 100000 > 80
          for: 10m
          labels:
            severity: warning

    - name: techassist-business
      rules:
        # ‹6› LLM API 錯誤
        - alert: LLMAPIErrors
          expr: |
            rate(llm_errors_total{app="techassist"}[5m]) > 0.1
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "LLM API 錯誤頻繁"

        # ‹7› 成本異常
        - alert: CostSpike
          expr: |
            sum(increase(agent_cost_usd{app="techassist"}[1h])) > 100
          for: 30m
          labels:
            severity: warning
          annotations:
            summary: "TechAssist 成本異常"
            description: "過去一小時成本 ${{ $value }}"
```

### 13.5.2 Grafana 儀表板

```json
{
  "dashboard": {
    "title": "TechAssist Production Dashboard",
    "rows": [
      {
        "title": "Overview",
        "panels": [
          {
            "title": "Request Rate",
            "type": "stat",
            "targets": [{"expr": "sum(rate(http_requests_total{app='techassist'}[5m]))"}]
          },
          {
            "title": "Error Rate",
            "type": "stat",
            "targets": [{"expr": "sum(rate(http_requests_total{app='techassist',status=~'5..'}[5m])) / sum(rate(http_requests_total{app='techassist'}[5m]))"}]
          },
          {
            "title": "P95 Latency",
            "type": "stat",
            "targets": [{"expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{app='techassist'}[5m])) by (le))"}]
          },
          {
            "title": "Active Pods",
            "type": "stat",
            "targets": [{"expr": "count(kube_pod_status_ready{namespace='techassist',condition='true'})"}]
          }
        ]
      },
      {
        "title": "LLM Metrics",
        "panels": [
          {
            "title": "LLM Calls/min",
            "type": "timeseries",
            "targets": [{"expr": "sum(rate(llm_calls_total{app='techassist'}[1m])) by (model)"}]
          },
          {
            "title": "Token Usage",
            "type": "timeseries",
            "targets": [{"expr": "sum(rate(llm_tokens_total{app='techassist'}[5m])) by (type)"}]
          },
          {
            "title": "Hourly Cost",
            "type": "stat",
            "targets": [{"expr": "sum(increase(agent_cost_usd{app='techassist'}[1h]))"}]
          }
        ]
      }
    ]
  }
}
```

---

## 13.6 災難恢復

### 13.6.1 備份策略

```yaml
# k8s/backup/velero-schedule.yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: techassist-daily-backup
  namespace: velero
spec:
  schedule: "0 2 * * *"  # 每天凌晨 2 點
  template:
    includedNamespaces:
      - techassist
    storageLocation: default
    ttl: 720h  # 保留 30 天
    hooks:
      resources:
        - name: postgres-backup
          includedNamespaces:
            - techassist
          labelSelector:
            matchLabels:
              app: postgres
          pre:
            - exec:
                container: postgres
                command:
                  - /bin/sh
                  - -c
                  - pg_dump -U techassist techassist > /backup/dump.sql
```

### 13.6.2 恢復流程

```bash
#!/bin/bash
# scripts/disaster-recovery.sh

set -e

echo "=== TechAssist 災難恢復流程 ==="

# ‹1› 確認備份
LATEST_BACKUP=$(velero backup get --selector app=techassist -o json | jq -r '.items | sort_by(.metadata.creationTimestamp) | last | .metadata.name')

echo "最新備份: $LATEST_BACKUP"

# ‹2› 恢復命名空間
echo "恢復 Kubernetes 資源..."
velero restore create --from-backup $LATEST_BACKUP --wait

# ‹3› 驗證 Pod 狀態
echo "驗證 Pod 狀態..."
kubectl wait --for=condition=ready pod -l app=techassist -n techassist --timeout=300s

# ‹4› 健康檢查
echo "執行健康檢查..."
HEALTH=$(kubectl exec -n techassist deploy/techassist-api -- curl -s http://localhost:8000/health)
echo "健康狀態: $HEALTH"

# ‹5› 流量恢復
echo "恢復流量..."
kubectl patch ingress techassist-ingress -n techassist -p '{"metadata":{"annotations":{"nginx.ingress.kubernetes.io/backend-protocol":"HTTP"}}}'

echo "=== 災難恢復完成 ==="
```

---

## 13.7 本章回顧

### 核心概念

| 概念 | 說明 |
|------|------|
| **多階段構建** | 減小鏡像大小，提高安全性 |
| **HPA** | 基於指標的自動擴縮容 |
| **藍綠部署** | 零停機切換，快速回滾 |
| **金絲雀發布** | 漸進式發布，風險可控 |
| **Prometheus Rules** | 基於指標的告警 |

### 部署架構總覽

```mermaid
graph TB
    subgraph "用戶流量"
        USER[用戶] --> CDN[CDN]
        CDN --> LB[Load Balancer]
    end

    subgraph "Kubernetes 集群"
        LB --> INGRESS[Ingress Controller]
        INGRESS --> SVC[Service]
        SVC --> POD1[Pod 1]
        SVC --> POD2[Pod 2]
        SVC --> POD3[Pod N]
    end

    subgraph "外部服務"
        POD1 --> ANTHROPIC[Anthropic API]
        POD1 --> QDRANT[Qdrant Cloud]
        POD1 --> REDIS[Redis Cluster]
    end

    subgraph "可觀測性"
        POD1 --> OTEL[OTel Collector]
        OTEL --> GRAFANA[Grafana Stack]
    end
```

### 實戰檢查清單

- [ ] 編寫多階段 Dockerfile
- [ ] 配置 K8s Deployment 和 Service
- [ ] 設置 HPA 自動擴縮容
- [ ] 建立 CI/CD 流水線
- [ ] 實施藍綠或金絲雀發布
- [ ] 配置 Prometheus 告警規則
- [ ] 建立災難恢復流程
- [ ] 文檔化運維手冊

---

## 練習題

### 練習 13.1：多環境配置

設計一個配置管理方案，支援：
- 開發、測試、生產三個環境
- 環境特定的 API 密鑰和端點
- 使用 Kustomize 或 Helm 管理差異

### 練習 13.2：自定義 HPA 指標

實現一個基於「Agent 品質分數」的 HPA：
- 當平均品質分數下降時增加副本
- 確保有足夠的資源處理複雜請求

### 練習 13.3：混沌工程

設計一個混沌工程測試計劃：
- Pod 隨機終止
- 網路分區模擬
- LLM API 延遲注入
- 驗證系統的彈性

---

## 全書總結

恭喜你完成了《LangChain 到 DeepAgents 實戰》的全部學習！

### 旅程回顧

| 階段 | 章節 | 核心技能 |
|------|------|----------|
| **基礎構件** | Ch 1-3 | LangChain、LCEL、Tool Use |
| **圖編排** | Ch 4-6 | LangGraph、狀態管理、多 Agent |
| **設計模式** | Ch 7-9 | Planning、Memory、Reflexion |
| **生產落地** | Ch 10-13 | 可觀測性、安全、優化、部署 |

### TechAssist 版本演進

```
v0.1 (Ch1-3)     →  基礎問答 + 工具調用
v0.5 (Ch4-6)     →  狀態管理 + 多 Agent 協作
v1.0 (Ch7-9)     →  DeepAgents 設計模式整合
v2.0 (Ch10-13)   →  生產級系統（可觀測 + 安全 + 部署）
```

### 下一步學習建議

1. **深入 LangGraph**：探索更複雜的圖結構和狀態管理
2. **多模態 Agent**：整合視覺和語音能力
3. **Agent 評估**：建立系統化的品質評估框架
4. **前沿研究**：關注 ReAct、LATS、Tree of Thoughts 等新模式

---

**感謝你的閱讀，祝你在 AI Agent 開發之路上一切順利！**

*— 作者團隊*
