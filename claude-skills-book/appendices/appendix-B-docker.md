# 附錄 B：Docker 與 Kubernetes 配置

## B.1 Docker 化 WebGuard

### B.1.1 多階段 Dockerfile

```dockerfile
# Dockerfile
# Stage 1: Base
FROM python:3.11-slim AS base

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Python Dependencies
FROM base AS python-deps

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry export -f requirements.txt --output requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Stage 3: Node.js Dependencies (for Stagehand)
FROM base AS node-deps

# 安裝 Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

COPY package.json package-lock.json ./
RUN npm ci --only=production

# Stage 4: Final
FROM base AS final

# 複製 Python 依賴
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# 複製 Node.js 和依賴
COPY --from=node-deps /usr/bin/node /usr/bin/node
COPY --from=node-deps /usr/lib /usr/lib
COPY --from=node-deps /app/node_modules ./node_modules

# 複製應用代碼
COPY . .

# 創建非 root 用戶
RUN useradd -m -u 1000 webguard && \
    chown -R webguard:webguard /app

USER webguard

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# 入口點
ENTRYPOINT ["python"]
CMD ["src/main.py"]
```

### B.1.2 .dockerignore

```
# .dockerignore
**/__pycache__
**/*.pyc
**/*.pyo
**/*.pyd
.pytest_cache
.coverage
htmlcov/
dist/
build/
*.egg-info/

node_modules/
npm-debug.log

.git
.gitignore
.env
.env.*

reports/
data/*.db
*.log
*.tmp

.vscode/
.idea/
*.swp

README.md
docs/
tests/
```

## B.2 Docker Compose 完整配置

### B.2.1 生產級 docker-compose.yml

```yaml
# docker-compose.yml
version: '3.9'

services:
  # PostgreSQL 資料庫
  postgres:
    image: postgres:15-alpine
    container_name: webguard-postgres
    environment:
      POSTGRES_DB: webguard
      POSTGRES_USER: webguard
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U webguard"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - webguard-network

  # Redis 快取和佇列
  redis:
    image: redis:7-alpine
    container_name: webguard-redis
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - webguard-network

  # MinIO 對象存儲 (S3-compatible)
  minio:
    image: minio/minio:latest
    container_name: webguard-minio
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin}
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    networks:
      - webguard-network

  # WebGuard 應用
  webguard:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - BUILD_DATE=${BUILD_DATE:-$(date -u +'%Y-%m-%dT%H:%M:%SZ')}
        - VCS_REF=${VCS_REF:-$(git rev-parse --short HEAD)}
    container_name: webguard-app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    environment:
      # Anthropic
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      ANTHROPIC_MODEL: ${ANTHROPIC_MODEL:-claude-3-5-sonnet-20241022}

      # Database
      DATABASE_URL: postgresql://webguard:${POSTGRES_PASSWORD:-changeme}@postgres:5432/webguard

      # Redis
      REDIS_URL: redis://redis:6379/0

      # MinIO
      S3_ENDPOINT: http://minio:9000
      S3_ACCESS_KEY: ${MINIO_ROOT_USER:-minioadmin}
      S3_SECRET_KEY: ${MINIO_ROOT_PASSWORD:-minioadmin}
      S3_BUCKET: webguard-results

      # Application
      APP_ENV: ${APP_ENV:-production}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      WORKERS: ${WORKERS:-4}

    volumes:
      - ./reports:/app/reports
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    restart: unless-stopped
    networks:
      - webguard-network
    labels:
      - "com.webguard.service=api"
      - "com.webguard.version=1.0.0"

  # Celery Worker (任務執行)
  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: webguard-celery-worker
    command: celery -A src.tasks worker --loglevel=info --concurrency=4
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://webguard:${POSTGRES_PASSWORD:-changeme}@postgres:5432/webguard
      REDIS_URL: redis://redis:6379/0
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    volumes:
      - ./reports:/app/reports
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - webguard-network

  # Celery Beat (排程)
  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: webguard-celery-beat
    command: celery -A src.tasks beat --loglevel=info
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://webguard:${POSTGRES_PASSWORD:-changeme}@postgres:5432/webguard
      REDIS_URL: redis://redis:6379/0
    restart: unless-stopped
    networks:
      - webguard-network

  # Prometheus (指標收集)
  prometheus:
    image: prom/prometheus:latest
    container_name: webguard-prometheus
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    ports:
      - "9090:9090"
    networks:
      - webguard-network

  # Grafana (可視化)
  grafana:
    image: grafana/grafana:latest
    container_name: webguard-grafana
    depends_on:
      - prometheus
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_INSTALL_PLUGINS: grafana-piechart-panel
    volumes:
      - grafana-data:/var/lib/grafana
      - ./docker/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./docker/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    ports:
      - "3000:3000"
    networks:
      - webguard-network

  # Nginx (反向代理)
  nginx:
    image: nginx:alpine
    container_name: webguard-nginx
    depends_on:
      - webguard
      - grafana
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/ssl:/etc/nginx/ssl:ro
    ports:
      - "80:80"
      - "443:443"
    restart: unless-stopped
    networks:
      - webguard-network

volumes:
  postgres-data:
    driver: local
  redis-data:
    driver: local
  minio-data:
    driver: local
  prometheus-data:
    driver: local
  grafana-data:
    driver: local

networks:
  webguard-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/16
```

### B.2.2 環境變數管理

```bash
# .env.example
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Database
POSTGRES_PASSWORD=secure_password_here

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=secure_minio_password

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=secure_grafana_password

# Application
APP_ENV=production
LOG_LEVEL=INFO
WORKERS=4

# Build
BUILD_DATE=
VCS_REF=
```

## B.3 Kubernetes 部署

### B.3.1 命名空間

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: webguard
  labels:
    name: webguard
    environment: production
```

### B.3.2 ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: webguard-config
  namespace: webguard
data:
  APP_ENV: "production"
  LOG_LEVEL: "INFO"
  ANTHROPIC_MODEL: "claude-3-5-sonnet-20241022"
  DATABASE_HOST: "postgres-service"
  DATABASE_PORT: "5432"
  DATABASE_NAME: "webguard"
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  S3_ENDPOINT: "http://minio-service:9000"
  S3_BUCKET: "webguard-results"
```

### B.3.3 Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: webguard-secrets
  namespace: webguard
type: Opaque
stringData:
  ANTHROPIC_API_KEY: "sk-ant-your-key-here"
  POSTGRES_PASSWORD: "secure_password"
  MINIO_ROOT_USER: "minioadmin"
  MINIO_ROOT_PASSWORD: "secure_password"
```

### B.3.4 PostgreSQL Deployment

```yaml
# k8s/postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: webguard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: webguard
        - name: POSTGRES_USER
          value: webguard
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: webguard-secrets
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - webguard
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - webguard
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: webguard
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: webguard
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### B.3.5 WebGuard Deployment

```yaml
# k8s/webguard-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webguard
  namespace: webguard
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webguard
  template:
    metadata:
      labels:
        app: webguard
    spec:
      containers:
      - name: webguard
        image: webguard:1.0.0
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: webguard-config
        - secretRef:
            name: webguard-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
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
  name: webguard-service
  namespace: webguard
spec:
  selector:
    app: webguard
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### B.3.6 HorizontalPodAutoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webguard-hpa
  namespace: webguard
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webguard
  minReplicas: 3
  maxReplicas: 10
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
```

### B.3.7 部署腳本

```bash
#!/bin/bash
# deploy.sh

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting WebGuard deployment...${NC}"

# 創建命名空間
echo "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# 創建 ConfigMap 和 Secrets
echo "Creating ConfigMap and Secrets..."
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# 部署資料庫
echo "Deploying PostgreSQL..."
kubectl apply -f k8s/postgres-deployment.yaml

# 等待 PostgreSQL 就緒
echo "Waiting for PostgreSQL..."
kubectl wait --for=condition=ready pod -l app=postgres -n webguard --timeout=300s

# 部署 Redis
echo "Deploying Redis..."
kubectl apply -f k8s/redis-deployment.yaml

# 部署 WebGuard
echo "Deploying WebGuard..."
kubectl apply -f k8s/webguard-deployment.yaml

# 部署 HPA
echo "Deploying HorizontalPodAutoscaler..."
kubectl apply -f k8s/hpa.yaml

# 等待 WebGuard 就緒
echo "Waiting for WebGuard..."
kubectl wait --for=condition=ready pod -l app=webguard -n webguard --timeout=300s

# 顯示狀態
echo -e "${GREEN}Deployment completed!${NC}"
kubectl get all -n webguard
```

## B.4 生產環境最佳實踐

### B.4.1 健康檢查

```python
# src/health.py
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/health")
async def health_check():
    """基礎健康檢查"""
    return {"status": "healthy"}

@app.get("/ready")
async def readiness_check():
    """就緒檢查（檢查依賴）"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "minio": await check_minio()
    }

    all_healthy = all(checks.values())

    return JSONResponse(
        status_code=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if all_healthy else "not ready", "checks": checks}
    )
```

### B.4.2 優雅關閉

```python
# src/graceful_shutdown.py
import signal
import asyncio

class GracefulShutdown:
    """優雅關閉處理"""

    def __init__(self):
        self.is_shutting_down = False
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """處理關閉信號"""
        if self.is_shutting_down:
            return

        self.is_shutting_down = True
        print("Received shutdown signal, gracefully shutting down...")

        # 1. 停止接受新請求
        # 2. 完成當前請求
        # 3. 關閉數據庫連接
        # 4. 清理資源
```

### B.4.3 資源限制

```yaml
# 生產環境資源配置
resources:
  requests:
    memory: "512Mi"    # 最小需求
    cpu: "500m"        # 0.5 CPU
  limits:
    memory: "2Gi"      # 最大限制
    cpu: "2000m"       # 2 CPU
```

---

*Docker 和 Kubernetes 配置應根據實際生產環境需求調整。*
