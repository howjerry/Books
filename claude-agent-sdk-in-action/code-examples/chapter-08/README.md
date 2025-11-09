# 第 8 章：生產環境的安全與監控 - 建立可觀測性體系

## 📖 概述

本章實作了完整的安全與監控體系，包含認證授權、指標監控、日誌聚合、分散式追蹤。

## 🎯 核心組件

### 安全層
1. **JWT 認證** - Token 驗證與刷新
2. **RBAC 權限控制** - 角色基礎的訪問控制
3. **資料加密** - 敏感資料加密儲存
4. **審計日誌** - 安全事件追蹤

### 監控層
1. **Prometheus** - 指標收集與儲存
2. **Grafana** - 視覺化儀表板
3. **Alertmanager** - 告警管理

### 日誌層
1. **結構化日誌** - JSON 格式日誌
2. **Elasticsearch** - 日誌儲存與搜尋
3. **Logstash** - 日誌處理
4. **Kibana** - 日誌分析UI

### 追蹤層
1. **OpenTelemetry** - 分散式追蹤
2. **Jaeger** - 追蹤視覺化

## 🚀 快速開始

### 啟動監控堆疊

```bash
# 1. 啟動所有服務
docker-compose up -d

# 2. 檢查服務狀態
docker-compose ps

# 3. 訪問各個UI
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
# Kibana: http://localhost:5601
# Jaeger: http://localhost:16686
```

### 訪問儀表板

**Prometheus**:
- URL: http://localhost:9090
- 查詢範例: `rate(agent_requests_total[5m])`

**Grafana**:
- URL: http://localhost:3000
- 用戶名/密碼: admin/admin
- 預設儀表板已配置

**Kibana**:
- URL: http://localhost:5601
- 搜尋範例: `level:ERROR AND agent_type:faq`

**Jaeger**:
- URL: http://localhost:16686
- 選擇服務查看追蹤

## 💡 使用範例

### 範例 1：JWT 認證

```python
from security.jwt_auth import JWTAuth

# 初始化
jwt_auth = JWTAuth(secret_key="your_secret_key")

# 創建 Token
access_token = jwt_auth.create_access_token(
    user_id="user123",
    scopes=["view:agent", "create:agent"]
)

# 驗證 Token
payload = jwt_auth.verify_token(access_token)
print(payload)  # {'sub': 'user123', 'scopes': [...], ...}
```

### 範例 2：記錄 Prometheus 指標

```python
from monitoring.metrics import MetricsCollector

metrics = MetricsCollector()

# 使用裝飾器追蹤請求
@metrics.track_request("faq", "/handle")
async def handle_faq_request():
    # 處理請求
    return {"message": "Success"}

# 記錄 API 使用
metrics.record_api_usage(
    agent_type="faq",
    model="claude-3-haiku",
    input_tokens=100,
    output_tokens=50,
    cost=0.005
)
```

### 範例 3：結構化日誌

```python
from logging_config.structured_logger import StructuredLogger

logger = StructuredLogger("faq-agent")

# 記錄請求
logger.info(
    "Request processed",
    user_id="user123",
    session_id="session456",
    agent_type="faq",
    duration_ms=245
)

# 記錄錯誤
logger.error(
    "Database connection failed",
    error_type="ConnectionError",
    retry_count=3
)
```

### 範例 4：分散式追蹤

```python
from tracing.opentelemetry_setup import TracingSetup
from opentelemetry import trace

# 初始化追蹤
tracing = TracingSetup(service_name="faq-agent")
tracing.setup_all(app)

# 手動創建 Span
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_request") as span:
    span.set_attribute("user_id", user_id)
    span.set_attribute("agent_type", "faq")

    # 處理請求
    result = await process()

    span.add_event("Processing completed")
```

## 📊 關鍵指標

### Prometheus 查詢範例

```promql
# 請求速率
rate(agent_requests_total[5m])

# P95 回應時間
histogram_quantile(0.95, rate(agent_request_duration_seconds_bucket[5m]))

# 錯誤率
rate(agent_errors_total[5m]) / rate(agent_requests_total[5m])

# API 成本（每小時）
rate(anthropic_api_cost_total[1h]) * 3600

# 快取命中率
sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))
```

### 告警規則

系統會自動觸發以下告警：
- ⚠️ 高錯誤率（> 0.1 req/s，持續 5 分鐘）
- ⚠️ 慢回應（P95 > 5 秒，持續 10 分鐘）
- ⚠️ 高 API 成本（> $10/小時，持續 15 分鐘）
- ⚠️ 低快取命中率（< 30%，持續 15 分鐘）
- 🚨 服務下線（持續 1 分鐘）

## 🔒 安全最佳實踐

### 1. JWT Token 管理

```python
# ✅ 好的做法
access_token = jwt_auth.create_access_token(
    user_id=user_id,
    scopes=["view:agent"]  # 最小權限原則
)
# Token 有效期：1 小時

refresh_token = jwt_auth.create_refresh_token(user_id)
# Refresh Token 有效期：7 天

# ❌ 避免
# - Token 永不過期
# - 在 Token 中儲存敏感資料
# - 不驗證 Token 簽名
```

### 2. 敏感資料加密

```python
# ✅ 加密儲存
from security.encryption import DataEncryption

encryptor = DataEncryption(master_key=os.getenv("MASTER_KEY"))

# 加密 API 金鑰
encrypted_key = encryptor.encrypt(api_key)
await db.store(encrypted_key)

# 解密
decrypted_key = encryptor.decrypt(encrypted_key)
```

### 3. RBAC 權限檢查

```python
# ✅ 每個端點都檢查權限
@app.delete("/api/v1/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    if not RBACManager.has_permission(
        current_user['role'],
        Permission.DELETE_AGENT
    ):
        raise HTTPException(403, "Permission denied")

    # 執行刪除
    ...
```

## 🐛 故障排除

### 問題 1：Prometheus 無法抓取指標

```bash
# 檢查服務是否暴露 /metrics 端點
curl http://localhost:8000/metrics

# 檢查 Prometheus 配置
docker logs prometheus

# 檢查目標狀態
# 訪問 http://localhost:9090/targets
```

### 問題 2：Grafana 無法連接 Prometheus

```bash
# 檢查 Prometheus 是否運行
curl http://prometheus:9090/api/v1/status/config

# 重新配置資料源
# Grafana UI -> Configuration -> Data Sources -> Add Prometheus
# URL: http://prometheus:9090
```

### 問題 3：日誌沒有出現在 Kibana

```bash
# 檢查 Elasticsearch 是否運行
curl http://localhost:9200/_cluster/health

# 檢查 Logstash 是否接收日誌
docker logs logstash

# 檢查索引
curl http://localhost:9200/_cat/indices?v
```

### 問題 4：Jaeger UI 沒有追蹤資料

```bash
# 檢查服務是否正確配置
# 確認環境變數：
# JAEGER_AGENT_HOST=jaeger
# JAEGER_AGENT_PORT=6831

# 檢查 Jaeger 狀態
docker logs jaeger

# 手動發送測試追蹤
python tracing/test_tracing.py
```

## 📈 效能基準

### 監控系統開銷

| 組件 | CPU 開銷 | 記憶體開銷 | 網路開銷 |
|------|---------|-----------|---------|
| Prometheus | < 1% | ~200MB | 最小 |
| Grafana | < 0.5% | ~150MB | 最小 |
| ELK Stack | 2-3% | ~1.5GB | 中等 |
| OpenTelemetry | < 0.5% | ~50MB | 最小 |

### 告警延遲

- 指標告警: < 30 秒
- 日誌告警: < 1 分鐘
- 追蹤告警: < 1 分鐘

## 🎓 學習要點

通過本章程式碼，你將學會：

1. ✅ 實作 JWT 認證系統
2. ✅ 設計 RBAC 權限控制
3. ✅ 使用 Prometheus 收集指標
4. ✅ 建立 Grafana 儀表板
5. ✅ 配置結構化日誌
6. ✅ 整合 ELK Stack
7. ✅ 實作分散式追蹤
8. ✅ 設定告警規則

## 🔗 相關章節

- **第 7 章**：企業級 Agent 架構設計（基礎架構）
- **第 9 章**：多層次協調與元 Agent（下一章）

## 📝 注意事項

1. **密鑰管理**：不要將密鑰硬編碼，使用環境變數或密鑰管理服務
2. **日誌保留**：設定合理的日誌保留策略（建議 30-90 天）
3. **告警疲勞**：避免設定過於敏感的告警閾值
4. **監控成本**：ELK Stack 需要較多資源，考慮成本

---

**最後更新**：2025-11-08

## 授權

本程式碼為《Claude Agent SDK 打造企業 Agent》書籍的配套範例，僅供學習使用。
