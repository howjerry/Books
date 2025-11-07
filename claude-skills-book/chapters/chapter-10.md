# 第 10 章：企業部署、安全與 MCP 生態

前九章構建了完整的 WebGuard 測試平台：從 Skills 開發、編排、CI/CD，到完整的四層架構。本章將探討企業級部署的關鍵主題：Kubernetes 生產環境部署、安全最佳實踐、密鑰管理、MCP（Model Context Protocol）整合，以及未來展望。這是將系統從「可運行」提升到「生產就緒」的最後一哩路。

## 10.1 安全性最佳實踐

### 10.1.1 密鑰管理（Secrets Management）

**問題場景：**

測試系統需要管理大量敏感信息：
- API Keys (Anthropic, 第三方服務)
- 數據庫密碼
- OAuth 憑證
- 加密金鑰

**錯誤做法：**

```python
# ❌ 硬編碼在代碼中
API_KEY = "sk-ant-1234567890abcdef"

# ❌ 提交到 Git
# config.py
POSTGRES_PASSWORD = "admin123"
```

**正確做法 1：環境變數**

```python
# ✅ 從環境變數讀取
import os

API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY 環境變數未設置")
```

**正確做法 2：專用密鑰管理系統**

使用 HashiCorp Vault：

```python
import hvac

class VaultClient:
    """HashiCorp Vault 客戶端"""

    def __init__(self, url: str, token: str):
        self.client = hvac.Client(url=url, token=token)

    def get_secret(self, path: str, key: str) -> str:
        """從 Vault 獲取密鑰"""
        secret = self.client.secrets.kv.v2.read_secret_version(path=path)
        return secret['data']['data'][key]


# 使用
vault = VaultClient(
    url='https://vault.example.com:8200',
    token=os.getenv('VAULT_TOKEN')
)

anthropic_key = vault.get_secret('webguard/api', 'anthropic_api_key')
db_password = vault.get_secret('webguard/database', 'password')
```

### 10.1.2 加密敏感數據

使用 Fernet 對稱加密：

```python
from cryptography.fernet import Fernet
import os
import base64


class SecureConfig:
    """安全配置管理器"""

    def __init__(self):
        """初始化加密器"""
        # 從環境變數獲取加密金鑰（32 bytes, base64 編碼）
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            raise ValueError("ENCRYPTION_KEY 未設置")

        self.cipher = Fernet(key.encode())

    def encrypt(self, value: str) -> str:
        """加密字串"""
        return self.cipher.encrypt(value.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """解密字串"""
        return self.cipher.decrypt(encrypted.encode()).decode()


# 生成加密金鑰（只執行一次，妥善保管）
def generate_encryption_key() -> str:
    """生成 Fernet 加密金鑰"""
    key = Fernet.generate_key()
    return key.decode()


# 使用範例
config = SecureConfig()

# 加密 API Key 存入數據庫
encrypted_key = config.encrypt("sk-ant-1234567890abcdef")
# 存入數據庫...

# 使用時解密
original_key = config.decrypt(encrypted_key)
```

### 10.1.3 API 金鑰輪換

定期輪換 API Keys 降低洩露風險：

```python
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class APIKeyRotator:
    """API 金鑰輪換器"""

    def __init__(self, vault_client: VaultClient):
        self.vault = vault_client

    def rotate_anthropic_key(self, new_key: str) -> Dict[str, Any]:
        """
        輪換 Anthropic API Key

        流程：
        1. 驗證新金鑰有效性
        2. 更新 Vault 密鑰
        3. 滾動重啟服務
        4. 撤銷舊金鑰（可選）

        Args:
            new_key: 新的 API Key

        Returns:
            輪換結果
        """
        # 1. 驗證新金鑰
        if not self._validate_key(new_key):
            raise ValueError("新金鑰驗證失敗")

        # 2. 保存舊金鑰（備份）
        old_key = self.vault.get_secret('webguard/api', 'anthropic_api_key')
        self.vault.client.secrets.kv.v2.create_or_update_secret(
            path='webguard/api/backup',
            secret={
                'old_key': old_key,
                'rotated_at': datetime.now().isoformat()
            }
        )

        # 3. 更新新金鑰
        self.vault.client.secrets.kv.v2.create_or_update_secret(
            path='webguard/api',
            secret={'anthropic_api_key': new_key}
        )

        logger.info("API 金鑰已更新到 Vault")

        # 4. 觸發服務重啟（Kubernetes Rolling Update）
        self._trigger_rolling_restart()

        return {
            "success": True,
            "rotated_at": datetime.now().isoformat(),
            "message": "API 金鑰輪換成功"
        }

    def _validate_key(self, key: str) -> bool:
        """驗證 API Key 是否有效"""
        import anthropic

        try:
            client = anthropic.Anthropic(api_key=key)
            # 發送測試請求
            client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            logger.error(f"金鑰驗證失敗: {e}")
            return False

    def _trigger_rolling_restart(self):
        """觸發 Kubernetes Rolling Restart"""
        import subprocess

        subprocess.run([
            'kubectl', 'rollout', 'restart',
            'deployment/webguard-api', '-n', 'webguard'
        ], check=True)

        logger.info("已觸發服務滾動重啟")


# 定時輪換（每 90 天）
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def scheduled_key_rotation():
    """定時輪換金鑰（需要手動生成新金鑰）"""
    logger.warning("金鑰輪換提醒：請手動生成新 Anthropic API Key 並調用 rotate_anthropic_key()")
    # 發送告警通知...

scheduler.add_job(
    scheduled_key_rotation,
    trigger='interval',
    days=90
)
```

### 10.1.4 HTTPS 與 TLS

**配置 Nginx SSL：**

```nginx
# /etc/nginx/sites-available/webguard
server {
    listen 443 ssl http2;
    server_name webguard.example.com;

    # SSL 證書（Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/webguard.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/webguard.example.com/privkey.pem;

    # SSL 配置（Mozilla Intermediate）
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:...';
    ssl_prefer_server_ciphers on;

    # HSTS (強制 HTTPS，180 天)
    add_header Strict-Transport-Security "max-age=15552000; includeSubDomains" always;

    # 安全 Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location /api/ {
        proxy_pass http://webguard_api;
        # 代理配置...
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name webguard.example.com;
    return 301 https://$server_name$request_uri;
}
```

### 10.1.5 輸入驗證與防護

**防止 SQL 注入：**

```python
# ❌ 錯誤：字串拼接
query = f"SELECT * FROM users WHERE username = '{username}'"

# ✅ 正確：使用參數化查詢
from sqlalchemy import text

query = text("SELECT * FROM users WHERE username = :username")
result = session.execute(query, {"username": username})
```

**防止 XSS：**

```python
from html import escape

def sanitize_input(user_input: str) -> str:
    """清理用戶輸入，防止 XSS"""
    return escape(user_input)


# API 響應
@app.get("/api/v1/test-results/{result_id}")
async def get_test_result(result_id: int):
    result = get_result_from_db(result_id)

    # 清理錯誤訊息（可能包含用戶輸入）
    if result.error_message:
        result.error_message = sanitize_input(result.error_message)

    return result
```

**速率限制（Rate Limiting）：**

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.post("/api/v1/executions/trigger")
@limiter.limit("10/minute")  # 每分鐘最多 10 次
async def trigger_execution(request: Request, ...):
    # 執行邏輯...
    pass
```


## 10.2 Kubernetes 生產環境部署

### 10.2.1 Kubernetes 資源清單

**Namespace：**

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: webguard
```

**ConfigMap：**

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: webguard-config
  namespace: webguard
data:
  DATABASE_HOST: "postgres.webguard.svc.cluster.local"
  REDIS_HOST: "redis.webguard.svc.cluster.local"
  LOG_LEVEL: "INFO"
  CELERY_BROKER_URL: "redis://redis:6379/0"
  CELERY_RESULT_BACKEND: "redis://redis:6379/1"
```

**Secret：**

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: webguard-secrets
  namespace: webguard
type: Opaque
data:
  # Base64 編碼（實際部署使用 Sealed Secrets 或 External Secrets）
  ANTHROPIC_API_KEY: c2stYW50LTEyMzQ1Njc4OTBhYmNkZWY=
  DATABASE_PASSWORD: cGFzc3dvcmQxMjM=
  ENCRYPTION_KEY: YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXow
```

**Deployment (API)：**

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webguard-api
  namespace: webguard
spec:
  replicas: 3  # 3 個副本（高可用）
  selector:
    matchLabels:
      app: webguard-api
  template:
    metadata:
      labels:
        app: webguard-api
    spec:
      containers:
      - name: api
        image: webguard/api:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_HOST
          valueFrom:
            configMapKeyRef:
              name: webguard-config
              key: DATABASE_HOST
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: webguard-secrets
              key: ANTHROPIC_API_KEY
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
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**Service (API)：**

```yaml
# k8s/api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: webguard-api
  namespace: webguard
spec:
  selector:
    app: webguard-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

**Ingress：**

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: webguard-ingress
  namespace: webguard
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - webguard.example.com
    secretName: webguard-tls
  rules:
  - host: webguard.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: webguard-api
            port:
              number: 80
```

**HorizontalPodAutoscaler（自動擴展）：**

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webguard-api-hpa
  namespace: webguard
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webguard-api
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

### 10.2.2 Helm Chart

將所有資源打包成 Helm Chart：

```yaml
# helm/webguard/Chart.yaml
apiVersion: v2
name: webguard
description: WebGuard Test Automation Platform
version: 1.0.0
appVersion: "1.0.0"
```

```yaml
# helm/webguard/values.yaml
replicaCount: 3

image:
  repository: webguard/api
  tag: v1.0.0
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: webguard.example.com
      paths:
        - path: /api
          pathType: Prefix
  tls:
    - secretName: webguard-tls
      hosts:
        - webguard.example.com

resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

postgresql:
  enabled: true
  auth:
    username: webguard
    password: changeme
    database: webguard

redis:
  enabled: true
  architecture: standalone
```

**部署 Helm Chart：**

```bash
# 安裝
helm install webguard ./helm/webguard -n webguard --create-namespace

# 升級
helm upgrade webguard ./helm/webguard -n webguard

# 回滾
helm rollback webguard 1 -n webguard

# 卸載
helm uninstall webguard -n webguard
```


## 10.3 MCP（Model Context Protocol）整合

### 10.3.1 什麼是 MCP？

**MCP（Model Context Protocol）** 是 Anthropic 提出的開放協定，讓 AI 應用程式能夠：

- 與外部工具和數據源交互
- 標準化 AI Agent 與服務的通信
- 構建可重用的 AI 功能模塊

**WebGuard MCP 整合價值：**

- 將 Skills 暴露為 MCP Tools，供 Claude 直接調用
- Claude 可自動發現並使用測試功能
- 實現「對話式測試」：用戶與 Claude 對話即可執行測試

### 10.3.2 實作 MCP Server

```python
# webguard/mcp_server.py
from mcp.server import Server, Tool, Resource
from mcp.types import TextContent, EmbeddedResource
from typing import Dict, Any, List
import asyncio
from webguard.orchestrator import SkillOrchestrator
from webguard.skill_loader import load_all_skills
import logging

logger = logging.getLogger(__name__)


class WebGuardMCPServer:
    """WebGuard MCP Server"""

    def __init__(self):
        """初始化 MCP Server"""
        self.server = Server("webguard")
        self.orchestrator = SkillOrchestrator()

        # 載入所有 Skills
        load_all_skills(self.orchestrator)

        # 註冊 MCP Tools
        self._register_tools()

        # 註冊 MCP Resources
        self._register_resources()

    def _register_tools(self):
        """註冊 MCP Tools"""

        @self.server.tool()
        async def run_health_check(url: str) -> Dict[str, Any]:
            """
            Run website health check

            Args:
                url: Website URL to check

            Returns:
                Health check result
            """
            result = await self.orchestrator.execute_skill(
                "web-health-check",
                {"url": url}
            )

            return result.to_dict()

        @self.server.tool()
        async def run_api_test(
            endpoint: str,
            method: str = "GET",
            expected_status: int = 200
        ) -> Dict[str, Any]:
            """
            Run API endpoint test

            Args:
                endpoint: API endpoint URL
                method: HTTP method
                expected_status: Expected HTTP status code

            Returns:
                Test result
            """
            result = await self.orchestrator.execute_skill(
                "api-test",
                {
                    "endpoint": endpoint,
                    "method": method,
                    "expected_status": expected_status
                }
            )

            return result.to_dict()

        @self.server.tool()
        async def run_e2e_test(test_suite_id: int) -> Dict[str, Any]:
            """
            Run end-to-end test suite

            Args:
                test_suite_id: Test suite ID from database

            Returns:
                Test execution result
            """
            from webguard.database import Session
            from webguard.models import TestSuite

            session = Session()

            try:
                suite = session.query(TestSuite).filter_by(id=test_suite_id).first()

                if not suite:
                    return {
                        "success": False,
                        "error": f"Test suite {test_suite_id} not found"
                    }

                # 執行測試套件
                from webguard.tasks import execute_test_suite
                task = execute_test_suite.delay(test_suite_id, triggered_by='mcp')

                return {
                    "success": True,
                    "task_id": task.id,
                    "message": f"Test suite '{suite.name}' execution queued"
                }

            finally:
                session.close()

        @self.server.tool()
        async def get_test_results(execution_id: int) -> Dict[str, Any]:
            """
            Get test execution results

            Args:
                execution_id: Test execution ID

            Returns:
                Detailed test results
            """
            from webguard.database import Session
            from webguard.models import TestExecution, TestResult

            session = Session()

            try:
                execution = session.query(TestExecution).filter_by(id=execution_id).first()

                if not execution:
                    return {
                        "success": False,
                        "error": f"Execution {execution_id} not found"
                    }

                results = session.query(TestResult).filter_by(execution_id=execution_id).all()

                return {
                    "success": True,
                    "execution": {
                        "id": execution.id,
                        "status": execution.status,
                        "total_tests": execution.total_tests,
                        "passed_tests": execution.passed_tests,
                        "failed_tests": execution.failed_tests,
                        "execution_time_ms": execution.execution_time_ms
                    },
                    "results": [
                        {
                            "test_name": r.test_name,
                            "status": r.status,
                            "error_message": r.error_message,
                            "execution_time_ms": r.execution_time_ms
                        }
                        for r in results
                    ]
                }

            finally:
                session.close()

    def _register_resources(self):
        """註冊 MCP Resources"""

        @self.server.resource("webguard://test-suites")
        async def get_test_suites() -> List[Resource]:
            """獲取所有測試套件"""
            from webguard.database import Session
            from webguard.models import TestSuite

            session = Session()

            try:
                suites = session.query(TestSuite).all()

                return [
                    Resource(
                        uri=f"webguard://test-suite/{suite.id}",
                        name=suite.name,
                        description=suite.description or "",
                        mimeType="application/json"
                    )
                    for suite in suites
                ]

            finally:
                session.close()

    async def run(self):
        """啟動 MCP Server"""
        await self.server.run()


# 啟動 MCP Server
if __name__ == "__main__":
    server = WebGuardMCPServer()
    asyncio.run(server.run())
```

### 10.3.3 Claude Desktop 整合

**配置 Claude Desktop 使用 WebGuard MCP Server：**

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "webguard": {
      "command": "python",
      "args": ["-m", "webguard.mcp_server"],
      "env": {
        "DATABASE_URL": "postgresql://webguard:password@localhost:5432/webguard",
        "REDIS_URL": "redis://localhost:6379/0",
        "ANTHROPIC_API_KEY": "your_api_key"
      }
    }
  }
}
```

**使用範例（Claude 對話）：**

```
User: 幫我檢查 https://example.com 的健康狀態

Claude: 我將使用 WebGuard 的健康檢查工具來測試這個網站。

[Claude 調用 run_health_check MCP Tool]

健康檢查結果：
- 狀態：✅ 正常
- 響應時間：245ms
- HTTP 狀態碼：200

網站運行正常！
```


## 10.4 生產就緒清單

### 10.4.1 部署前檢查清單

**安全性：**

- [ ] 所有密鑰使用 Vault 或 Kubernetes Secrets 管理
- [ ] 啟用 HTTPS/TLS
- [ ] 配置防火牆規則（只開放必要端口）
- [ ] 啟用速率限制
- [ ] 設置 CORS 策略
- [ ] 輸入驗證與清理
- [ ] SQL 注入防護
- [ ] XSS 防護
- [ ] 定期安全掃描（Snyk, Trivy）

**高可用性：**

- [ ] 至少 3 個 API 副本
- [ ] PostgreSQL 主從複製
- [ ] Redis 哨兵模式或集群
- [ ] 配置 HPA（自動擴展）
- [ ] 設置 PodDisruptionBudget
- [ ] 多可用區部署
- [ ] 備份策略（數據庫、MinIO）

**監控與告警：**

- [ ] Prometheus 指標收集
- [ ] Grafana 儀表板
- [ ] 日誌聚合（ELK/Loki）
- [ ] 錯誤追蹤（Sentry）
- [ ] 鏈路追蹤（Jaeger）
- [ ] 告警規則配置
- [ ] On-call 輪值設置

**性能優化：**

- [ ] 數據庫連接池配置
- [ ] Redis 快取策略
- [ ] CDN 配置（靜態資源）
- [ ] 壓縮響應（gzip）
- [ ] 數據庫索引優化
- [ ] N+1 查詢優化
- [ ] 定期性能測試

### 10.4.2 監控儀表板範例

**Grafana 儀表板關鍵指標：**

```json
{
  "panels": [
    {
      "title": "Test Execution Rate",
      "targets": [
        "rate(webguard_test_executions_total[5m])"
      ]
    },
    {
      "title": "Test Pass Rate (%)",
      "targets": [
        "sum(rate(webguard_test_executions_total{status='passed'}[5m])) / sum(rate(webguard_test_executions_total[5m])) * 100"
      ]
    },
    {
      "title": "P95 Test Duration",
      "targets": [
        "histogram_quantile(0.95, sum(rate(webguard_test_duration_seconds_bucket[5m])) by (le))"
      ]
    },
    {
      "title": "Celery Queue Length",
      "targets": [
        "celery_queue_length{queue='browser'}",
        "celery_queue_length{queue='api'}"
      ]
    },
    {
      "title": "Database Connections",
      "targets": [
        "pg_stat_database_numbackends{datname='webguard'}"
      ]
    }
  ]
}
```


## 10.5 未來展望

### 10.5.1 AI 驅動的測試演進

**當前狀態（本書涵蓋）：**

- AI 輔助測試撰寫（Claude Code Skills）
- 語意化元素定位（Stagehand）
- 自愈測試（Self-Healing Tests）

**未來方向：**

1. **自動測試生成**：Claude 閱讀需求文檔，自動生成測試案例
2. **視覺回歸測試**：AI 識別 UI 變化，判斷是否為 Bug
3. **智能 Bug 分析**：自動分類失敗原因，建議修復方案
4. **預測性測試**：根據代碼變更預測可能失敗的測試
5. **自然語言測試**：用戶用自然語言描述測試，AI 轉換為可執行測試

### 10.5.2 社群與生態系統

**開源貢獻：**

- 將 WebGuard 開源，接受社群貢獻
- 創建 Skills Marketplace（共享可重用 Skills）
- 提供官方 Skills 庫（常見場景）

**MCP 生態整合：**

- 與其他 MCP Servers 互操作
- 支持更多 AI 平台（OpenAI Assistants API、Google Gemini）
- 構建 MCP Tools 生態系統

### 10.5.3 結語

從 Chapter 1 的 Claude Code 簡介，到 Chapter 10 的企業級部署，我們完成了一個完整的技術之旅：

- **理論**：Skills 設計原則、三層架構、測試金字塔
- **實踐**：瀏覽器自動化、API 測試、數據處理、Skills 編排
- **工程**：CI/CD 整合、四層系統架構、高可用性設計
- **未來**：MCP 整合、AI 驅動測試、生態系統

**核心價值觀：**

1. **自動化優先**：減少重複勞動，提升效率
2. **可靠性至上**：測試必須穩定，結果必須可信
3. **開放協作**：擁抱開源，參與生態建設
4. **持續演進**：AI 技術日新月異，測試技術也要與時俱進

希望本書能幫助你構建更好的測試系統，交付更高質量的軟件產品。祝你在 AI 輔助測試的旅程中取得成功！

---

**附註：**

完整代碼範例、配置文件、演示視頻請訪問：
- GitHub: https://github.com/webguard/examples
- 官方文檔: https://webguard.dev/docs
- 社群論壇: https://community.webguard.dev
