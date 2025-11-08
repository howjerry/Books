# 第 7 章：企業級 Agent 架構設計 - 智慧客戶支援平台

## 📖 概述

本章實作了完整的企業級智慧客戶支援平台，展示如何設計和部署可服務 10,000+ 用戶的 Agent 系統。

## 🎯 系統架構

### 核心組件

1. **API Gateway**
   - 認證與授權
   - 限流 (60 請求/分鐘/用戶)
   - 請求路由
   - 快取管理

2. **Router Agent**
   - 意圖識別
   - 請求分發
   - 智慧路由

3. **專業化 Agents**
   - FAQ Agent - 常見問題查詢
   - Order Agent - 訂單管理
   - Refund Agent - 退款處理
   - Technical Agent - 技術支援

4. **資料層**
   - PostgreSQL - 主資料庫
   - Redis - 快取與會話管理
   - Elasticsearch - 全文搜尋（可選）

## 📁 專案結構

```
chapter-07/
├── gateway/                    # API Gateway
│   ├── main.py                 # FastAPI 應用
│   └── Dockerfile
├── agents/                     # Agent 服務
│   ├── router_agent.py         # 路由 Agent
│   ├── faq_agent.py           # FAQ Agent
│   └── Dockerfile
├── database/                   # 資料庫
│   └── schema.sql             # 資料庫架構
├── k8s/                       # Kubernetes 配置
│   └── deployment.yaml        # 部署配置
├── cache/                     # 快取管理
│   ├── redis_cache.py         # Redis 快取
│   └── cache_warmer.py        # 快取預熱
├── monitoring/                # 監控
│   └── cost_tracker.py        # 成本追蹤
├── tests/                     # 測試
│   └── load_test.py           # 負載測試
├── docker-compose.yml         # Docker Compose 配置
├── requirements.txt           # Python 依賴
├── .env.example               # 環境變數範例
└── README.md                  # 本文件
```

## 🚀 快速開始

### 方式 1：使用 Docker Compose（推薦）

這是最簡單的本地開發方式。

```bash
# 1. 複製環境變數範例
cp .env.example .env

# 2. 編輯 .env，填入你的 ANTHROPIC_API_KEY
nano .env

# 3. 啟動所有服務
docker-compose up -d

# 4. 檢查服務狀態
docker-compose ps

# 5. 查看日誌
docker-compose logs -f api-gateway

# 6. 測試 API
curl http://localhost:8000/health
```

**服務端口**：
- API Gateway: http://localhost:8000
- Router Agent: http://localhost:8001
- FAQ Agent: http://localhost:8002
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 方式 2：本地開發

需要手動啟動 PostgreSQL 和 Redis。

```bash
# 1. 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 設定環境變數
cp .env.example .env
# 編輯 .env

# 4. 啟動 PostgreSQL 和 Redis（需要預先安裝）
# 或使用 Docker:
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 5. 初始化資料庫
psql -h localhost -U postgres -d support_platform -f database/schema.sql

# 6. 啟動服務（不同終端）
# 終端 1: API Gateway
cd gateway && uvicorn main:app --port 8000 --reload

# 終端 2: Router Agent
cd agents && uvicorn router_agent:router_app --port 8001 --reload

# 終端 3: FAQ Agent
cd agents && uvicorn faq_agent:faq_app --port 8002 --reload
```

### 方式 3：Kubernetes 部署（生產環境）

```bash
# 1. 建立 Kubernetes Secret
kubectl create secret generic api-secrets \
  --from-literal=anthropic-api-key=YOUR_API_KEY

kubectl create secret generic postgres-secret \
  --from-literal=username=postgres \
  --from-literal=password=SECURE_PASSWORD

# 2. 部署應用
kubectl apply -f k8s/deployment.yaml

# 3. 檢查部署狀態
kubectl get pods
kubectl get services

# 4. 獲取外部 IP
kubectl get service api-gateway

# 5. 測試
curl http://<EXTERNAL-IP>/health
```

## 💡 使用範例

### 範例 1：基本聊天請求

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "session_id": "session_123",
    "message": "如何追蹤我的訂單？",
    "user_id": "user_456",
    "metadata": {}
  }'
```

**回應**：
```json
{
  "session_id": "session_123",
  "message": "您可以在「我的訂單」頁面輸入訂單編號來追蹤物流狀態...",
  "agent_type": "faq",
  "timestamp": "2025-11-08T10:00:00Z",
  "response_time_ms": 245
}
```

### 範例 2：獲取會話歷史

```bash
curl http://localhost:8000/api/v1/session/session_123/history \
  -H "X-API-Key: your_api_key"
```

### 範例 3：清除會話

```bash
curl -X DELETE http://localhost:8000/api/v1/session/session_123 \
  -H "X-API-Key: your_api_key"
```

## 🧪 測試

### 單元測試

```bash
pytest tests/ -v
```

### 負載測試

```bash
# 使用內建的負載測試腳本
python tests/load_test.py

# 或使用 Locust
locust -f tests/locustfile.py --host=http://localhost:8000
```

**預期結果**：
- 100 並發用戶
- 1000 總請求
- 平均回應時間 < 3 秒
- 成功率 > 99%

## 📊 監控

### 健康檢查

```bash
# API Gateway
curl http://localhost:8000/health

# Router Agent
curl http://localhost:8001/health

# FAQ Agent
curl http://localhost:8002/health
```

### 指標查詢

系統會自動記錄以下指標到資料庫：
- API 呼叫次數
- 回應時間
- 錯誤率
- 成本使用

查詢每日統計：
```sql
SELECT
    agent_type,
    COUNT(*) AS calls,
    AVG(response_time_ms) AS avg_response_time,
    SUM(cost_usd) AS total_cost
FROM agent_metrics
WHERE DATE(created_at) = CURRENT_DATE
GROUP BY agent_type;
```

## 💰 成本優化

### 模型選擇策略

系統會自動根據任務類型選擇合適的模型：

| 任務類型 | 模型 | 成本/1K tokens |
|---------|------|---------------|
| FAQ 查詢 | Haiku | $0.00025 (input) |
| 訂單查詢 | Haiku | $0.00025 (input) |
| 退款處理 | Sonnet | $0.003 (input) |
| 技術支援 | Sonnet | $0.003 (input) |
| 複雜問題 | Opus | $0.015 (input) |

### 快取策略

- **L1 快取（記憶體）**：熱門 FAQ (< 1ms)
- **L2 快取（Redis）**：最近查詢 (5-10ms)
- **L3 快取（資料庫）**：物化視圖 (10-50ms)

快取命中率目標：60-80%

## 🔧 配置調整

### 限流設定

編輯 `gateway/main.py`：
```python
# 每用戶每分鐘最多請求數
RATE_LIMIT = 60  # 預設 60

# 快取 TTL
CACHE_TTL = 300  # 5 分鐘
```

### 自動擴展

編輯 `k8s/deployment.yaml`：
```yaml
spec:
  minReplicas: 2   # 最小副本數
  maxReplicas: 10  # 最大副本數
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 70  # CPU 門檻
```

## 🐛 故障排除

### 問題 1：無法連接資料庫

```
Error: could not connect to server: Connection refused
```

**解決方法**：
```bash
# 檢查 PostgreSQL 是否運行
docker-compose ps postgres

# 查看日誌
docker-compose logs postgres

# 重啟服務
docker-compose restart postgres
```

### 問題 2：Redis 連接錯誤

```
Error: Error connecting to Redis
```

**解決方法**：
```bash
# 測試 Redis 連接
redis-cli ping

# 檢查環境變數
echo $REDIS_HOST

# 重啟 Redis
docker-compose restart redis
```

### 問題 3：API 回應慢

**診斷**：
```bash
# 檢查快取命中率
redis-cli INFO stats | grep keyspace_hits

# 查看資料庫慢查詢
psql -U postgres -d support_platform -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# 檢查資源使用
docker stats
```

### 問題 4：429 Too Many Requests

```
Error: Rate limit exceeded
```

**解決方法**：
- 增加 `RATE_LIMIT` 值
- 或等待 60 秒後重試
- 或使用不同的 `user_id`

## 📈 效能基準

### 預期效能（單一實例）

| 指標 | 目標值 |
|------|-------|
| 並發請求 | 100+ |
| 平均回應時間 | < 3 秒 |
| P95 回應時間 | < 5 秒 |
| 錯誤率 | < 1% |
| 快取命中率 | > 60% |

### 擴展能力

使用 Kubernetes 自動擴展：
- 2-10 個 FAQ Agent 副本
- 可服務 10,000+ 並發用戶
- 水平擴展無限制

## 🎓 學習要點

通過本章程式碼，你將學會：

1. ✅ 設計微服務架構的 Agent 系統
2. ✅ 實作無狀態應用設計
3. ✅ 建立多層次快取策略
4. ✅ 使用 Kubernetes 部署和擴展
5. ✅ 實作 API 限流與認證
6. ✅ 進行負載測試與效能優化
7. ✅ 追蹤成本並優化 API 使用

## 🔗 相關章節

- **第 1 章**：建構你的第一個 Claude Agent（基礎）
- **第 4-6 章**：Subagents 與品質保證（進階）
- **第 8 章**：生產環境的安全與監控（下一章）

## 📝 注意事項

1. **API 成本**：完整的系統需要呼叫 Claude API，請注意成本控制
2. **資料隱私**：確保敏感資料加密儲存
3. **擴展性**：根據實際負載調整副本數量
4. **監控**：建議整合 Prometheus + Grafana 進行監控（第 8 章）

## 🎯 下一步

完成本章後，建議：

1. 整合第 8 章的監控系統
2. 添加更多專業化 Agents
3. 實作更複雜的路由邏輯
4. 優化資料庫查詢效能
5. 建立完整的 CI/CD 管線

---

**最後更新**：2025-11-08

## 授權

本程式碼為《Claude Agent SDK 打造企業 Agent》書籍的配套範例，僅供學習使用。
