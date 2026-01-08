# 第 11 章：生產環境部署 - 程式碼範例

## 概覽

本目錄包含第 11 章「生產環境部署」的完整程式碼範例，展示如何將深度研究代理人部署到生產環境。

## 檔案結構

```
chapter-11/
├── api_server.py          # FastAPI 應用服務
├── metrics.py             # Prometheus 監控指標
├── logging_module.py      # 結構化日誌模組
├── Dockerfile             # 容器映像定義
├── docker-compose.yml     # 本地開發環境
├── requirements.txt       # Python 依賴
├── .env.example           # 環境變數範例
├── README.md              # 本文件
└── monitoring/            # 監控配置（選用）
    ├── prometheus.yml     # Prometheus 配置
    └── grafana/           # Grafana 儀表板
```

## 核心元件

### 1. API 服務 (`api_server.py`)

FastAPI 應用服務，提供：
- RESTful API 端點（研究請求、結果查詢）
- 健康檢查端點（Kubernetes liveness/readiness probe）
- Prometheus 指標端點
- 結構化日誌與請求追蹤
- 背景任務執行

**主要端點**：
| 端點 | 方法 | 說明 |
|------|------|------|
| `/health` | GET | 健康檢查 |
| `/ready` | GET | 就緒檢查 |
| `/metrics` | GET | Prometheus 指標 |
| `/api/v1/research` | POST | 提交研究請求 |
| `/api/v1/research/{id}` | GET | 查詢研究結果 |
| `/api/v1/research` | GET | 列出所有研究 |

### 2. 監控指標 (`metrics.py`)

Prometheus 監控指標模組：
- **請求指標**：計數、延遲、活躍數
- **研究任務指標**：任務計數、執行時間
- **LLM 調用指標**：API 調用、Token 使用
- **快取指標**：命中率、大小

**指標裝飾器**：
```python
@track_request("/api/v1/research")
async def create_research(...):
    ...

@track_research_task("coordinator")
async def execute_research(...):
    ...

@track_llm_call("qwen-72b")
async def call_llm(...):
    ...
```

### 3. 結構化日誌 (`logging_module.py`)

生產級日誌系統：
- JSON 結構化輸出
- 請求 ID 追蹤
- 審計日誌
- FastAPI 中間件整合

**日誌格式**：
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "logger": "api",
  "message": "請求完成",
  "request_id": "abc123",
  "method": "POST",
  "path": "/api/v1/research",
  "status_code": 200,
  "duration": 1.234
}
```

### 4. 容器化 (`Dockerfile`)

多階段建構的 Docker 映像：
- **建構階段**：安裝依賴到虛擬環境
- **生產階段**：最小化映像，非 root 使用者
- **健康檢查**：內建 curl 健康檢查

### 5. 開發環境 (`docker-compose.yml`)

完整的本地開發環境：
- API 服務
- PostgreSQL 資料庫
- Redis 快取
- Prometheus 監控
- Grafana 儀表板
- 資料庫/Redis Exporter

## 快速開始

### 1. 環境準備

```bash
# 複製環境變數範例
cp .env.example .env

# 編輯 .env，填入實際設定值
vim .env
```

### 2. 使用 Docker Compose（推薦）

```bash
# 啟動所有服務
docker-compose up -d

# 查看日誌
docker-compose logs -f api

# 停止服務
docker-compose down
```

### 3. 本地開發

```bash
# 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt

# 啟動服務
uvicorn api_server:app --reload --port 8000
```

## 服務端口

| 服務 | 端口 | 說明 |
|------|------|------|
| API | 8000 | 主要 API 服務 |
| PostgreSQL | 5432 | 資料庫 |
| Redis | 6379 | 快取與任務佇列 |
| Prometheus | 9090 | 監控指標收集 |
| Grafana | 3000 | 監控儀表板 |
| Redis Exporter | 9121 | Redis 指標 |
| Postgres Exporter | 9187 | PostgreSQL 指標 |

## API 使用範例

### 提交研究請求

```bash
curl -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "question": "2024年全球AI晶片市場分析",
    "max_sources": 10,
    "verify": true,
    "language": "zh-TW"
  }'
```

**回應**：
```json
{
  "research_id": "abc123def456",
  "question": "2024年全球AI晶片市場分析",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00"
}
```

### 查詢研究結果

```bash
curl http://localhost:8000/api/v1/research/abc123def456
```

### 健康檢查

```bash
# Liveness probe
curl http://localhost:8000/health

# Readiness probe
curl http://localhost:8000/ready

# Prometheus 指標
curl http://localhost:8000/metrics
```

## 監控與告警

### Prometheus 指標

訪問 http://localhost:9090 查看 Prometheus UI。

**常用查詢**：
```promql
# 請求速率
rate(research_requests_total[5m])

# 平均延遲
histogram_quantile(0.95, rate(research_request_duration_seconds_bucket[5m]))

# 錯誤率
sum(rate(research_requests_total{status="error"}[5m])) / sum(rate(research_requests_total[5m]))

# 活躍研究任務
research_active_requests

# LLM Token 使用
rate(llm_tokens_total[1h])
```

### Grafana 儀表板

訪問 http://localhost:3000（預設帳號：admin/admin）

**建議儀表板**：
1. API 效能概覽
2. 研究任務統計
3. LLM 使用量
4. 系統資源監控

## 生產部署檢查清單

### 安全性
- [ ] 更換預設密碼和金鑰
- [ ] 啟用 HTTPS
- [ ] 設定適當的 CORS 策略
- [ ] 啟用 API 認證
- [ ] 設定速率限制

### 可靠性
- [ ] 配置健康檢查
- [ ] 設定自動重啟
- [ ] 配置資源限制
- [ ] 設定日誌輪轉

### 監控
- [ ] 配置 Prometheus 指標收集
- [ ] 建立 Grafana 儀表板
- [ ] 設定告警規則
- [ ] 配置日誌聚合

### 備份
- [ ] 配置資料庫備份
- [ ] 設定備份驗證
- [ ] 建立災難復原計畫

## 故障排除

### API 服務無法啟動

1. 檢查環境變數是否正確設定
2. 確認資料庫連接正常
3. 檢查端口是否被占用

```bash
# 檢查端口
lsof -i :8000

# 檢查 Docker 容器狀態
docker-compose ps

# 查看容器日誌
docker-compose logs api
```

### 資料庫連接失敗

```bash
# 測試資料庫連接
psql -h localhost -U user -d research

# 檢查 Docker 網路
docker network ls
docker network inspect chapter-11_research-net
```

### Prometheus 無法抓取指標

1. 確認 `/metrics` 端點正常運作
2. 檢查 Prometheus 配置
3. 確認網路連通性

```bash
# 測試指標端點
curl http://localhost:8000/metrics

# 檢查 Prometheus 目標狀態
curl http://localhost:9090/api/v1/targets
```

## 相關章節

- **第 10 章**：多代理人協作系統 - 本章部署的核心功能
- **第 12 章**：進階主題 - 效能優化與擴展
- **第 13 章**：案例研究 - 完整的生產部署案例

## 授權

本程式碼範例遵循書籍的授權條款，僅供學習和參考使用。
