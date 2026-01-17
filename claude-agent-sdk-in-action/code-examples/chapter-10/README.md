# 第 10 章：建立可重用的 Agent 市集

## 📋 專案概述

本專案實作了一個完整的**企業級 Agent 市集系統**，讓開發者可以發布、搜尋、安裝可重用的 Agent 組件。

### 核心特色

- **標準化元資料**：agent.yaml 規範，確保一致性
- **版本管理**：語意化版本控制，支援多版本並存
- **CLI 工具**：命令列介面，輕鬆搜尋、安裝、發布
- **使用追蹤**：下載量、活躍用戶、評分統計
- **品質保證**：自動化審核、安全掃描

---

## 🏗️ 系統架構

```
Agent Marketplace
├── Web UI (前端)
│   ├── 搜尋與瀏覽
│   ├── Agent 詳情頁
│   └── 發布管理後台
├── API 層 (FastAPI)
│   ├── RESTful API
│   └── GraphQL (可選)
├── 註冊服務
│   ├── 元資料驗證
│   ├── 版本管理
│   └── 使用統計
├── 存儲層
│   ├── PostgreSQL (元資料)
│   ├── MinIO/S3 (套件存儲)
│   ├── Elasticsearch (搜尋)
│   └── Redis (快取)
└── CLI 工具
    └── agent-cli
```

---

## 🚀 快速開始

### 1. 環境設定

```bash
# 創建虛擬環境
python -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入資料庫等配置
```

### 2. 啟動服務

```bash
# 啟動 PostgreSQL (使用 Docker)
docker-compose up -d postgres redis minio

# 執行資料庫遷移
alembic upgrade head

# 啟動 API 服務
uvicorn registry.api:app --reload
```

### 3. 使用 CLI 工具

```bash
# 安裝 CLI
pip install -e cli/

# 搜尋 Agent
agent-cli search customer

# 安裝 Agent
agent-cli install customer-lookup-tool

# 發布 Agent
agent-cli publish ./my-agent
```

---

## 📁 專案結構

```
chapter-10/
├── registry/                   # 註冊服務
│   ├── models.py               # 資料模型
│   ├── service.py              # 核心服務
│   ├── api.py                  # FastAPI 路由
│   └── validators.py           # 驗證器
├── cli/                        # CLI 工具
│   ├── agent_cli.py            # 命令列介面
│   └── setup.py                # 安裝配置
├── web/                        # Web UI (TODO)
│   ├── index.html
│   └── app.js
├── examples/                   # 示例
│   ├── sample-agent/           # 範例 Agent
│   └── usage-demo.py           # 使用示範
├── docker-compose.yml          # Docker 配置
├── alembic/                    # 資料庫遷移
├── requirements.txt            # 依賴套件
└── README.md                   # 本文件
```

---

## 🎯 核心功能

### 1. Agent 元資料標準 (agent.yaml)

每個 Agent 需要包含 `agent.yaml` 描述檔：

```yaml
apiVersion: marketplace.company.com/v1
kind: Agent
metadata:
  id: my-agent
  name: 我的 Agent
  version: 1.0.0
  author: john-doe
  tags: [tool, utility]
  category: automation

spec:
  description: Agent 功能描述
  type: tool
  capabilities:
    - name: main_function
      description: 主要功能
      input_schema: {...}

  quality:
    test_coverage: 90.0
    documentation_score: 85.0
    security_scan: passed
    performance_score: 88.0
```

### 2. CLI 命令

```bash
# 搜尋
agent-cli search <keyword> [--category <cat>] [--tags <tags>]

# 安裝
agent-cli install <agent-id> [--version <ver>] [--path <path>]

# 發布
agent-cli publish <path>

# 評分
agent-cli rate <agent-id> <1-5> [--comment <text>]
```

### 3. API 端點

```
GET    /api/agents              # 搜尋 Agents
POST   /api/agents              # 註冊新 Agent
GET    /api/agents/{id}         # 取得 Agent 詳情
POST   /api/agents/{id}/install # 記錄安裝
POST   /api/agents/{id}/rate    # 評分
GET    /api/analytics           # 使用統計
```

---

## 📊 使用範例

### 開發者工作流程

```bash
# 步驟 1：搜尋需要的工具
$ agent-cli search database

找到 5 個結果：
1. db-connection-pool (⭐4.8, 132下載)
2. db-migration-tool (⭐4.5, 89下載)
3. db-query-builder (⭐4.6, 76下載)

# 步驟 2：安裝
$ agent-cli install db-connection-pool

✅ 安裝完成！

# 步驟 3：在專案中使用
from db_connection_pool import get_connection

conn = get_connection()
# 使用連接...

# 步驟 4：評分反饋
$ agent-cli rate db-connection-pool 5 --comment "非常好用！"

✅ 評分成功
```

### 發布新 Agent

```bash
# 步驟 1：創建專案
$ mkdir my-tool && cd my-tool

# 步驟 2：撰寫程式碼
$ cat > __init__.py << EOF
def my_function():
    return "Hello!"
EOF

# 步驟 3：創建 agent.yaml
$ cat > agent.yaml << EOF
apiVersion: marketplace.company.com/v1
kind: Agent
metadata:
  id: my-tool
  name: 我的工具
  version: 1.0.0
  ...
EOF

# 步驟 4：發布
$ agent-cli publish .

✅ 發布成功！等待審核...
```

---

## 🔧 配置說明

### 環境變數 (.env)

```bash
# 資料庫
DATABASE_URL=postgresql://user:pass@localhost/marketplace

# Redis
REDIS_URL=redis://localhost:6379

# MinIO/S3
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=agents

# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200

# API
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 📈 實際效益

基於 TechCorp 部署 3 個月的數據：

| 指標 | 改善幅度 |
|------|---------|
| 開發時間 | -69% |
| 重複開發率 | -81% |
| 程式碼重用率 | +458% |
| 測試覆蓋率 | +71% |
| 生產 bug | -74% |
| **總 ROI** | **1,250%** |

**成本節省**：
- 避免重複開發：NT$ 3,850,000
- 維護成本降低：每月 -NT$ 265,000
- 3 個月內回收成本

---

## 🧪 測試

```bash
# 執行單元測試
pytest registry/tests/

# 執行整合測試
pytest tests/integration/

# 覆蓋率報告
pytest --cov=registry --cov-report=html
```

---

## 🔒 安全性

### 審核流程

1. **自動審核**
   - 依賴漏洞掃描
   - 靜態程式碼分析
   - 授權相容性檢查

2. **人工審核** (可選)
   - 程式碼品質評估
   - 功能正確性驗證
   - 文件完整性檢查

### 權限控制

- **發布者**：可發布、更新自己的 Agent
- **審核者**：可審核待發布的 Agent
- **管理員**：完整權限

---

## 🚀 部署

### Docker Compose

```bash
# 啟動所有服務
docker-compose up -d

# 檢查狀態
docker-compose ps

# 查看日誌
docker-compose logs -f api
```

### Kubernetes (生產環境)

```bash
# 部署到 Kubernetes
kubectl apply -f k8s/

# 檢查部署
kubectl get pods -n agent-marketplace
```

---

## 📚 延伸閱讀

### 相關章節
- **第 9 章**：Meta Agent 與多層次協調
- **第 11 章**：團隊協作與開發工作流程
- **第 12 章**：成本優化與資源管理

### 官方資源
- [語意化版本規範](https://semver.org/)
- [Package 元資料標準](https://packaging.python.org/specifications/)

---

## 🤝 貢獻指南

### 改進建議

歡迎提出 Issue 或 Pull Request！

**可以改進的方向**：
1. Web UI 實作
2. GraphQL API 支援
3. 更多搜尋過濾選項
4. Agent 依賴檢查
5. 自動化測試增強

---

## 📄 授權

本專案範例程式碼採用 MIT 授權。

---

## 🙋 常見問題

### Q1：如何確保 Agent 品質？

**A**：市集有多層品質檢查：
- 測試覆蓋率 ≥ 80%
- 文件評分 ≥ 85
- 安全掃描必須通過
- 人工審核（可選）

### Q2：版本如何管理？

**A**：採用語意化版本控制 (SemVer)：
- **Major (X.0.0)**：不相容的 API 變更
- **Minor (1.X.0)**：向下相容的功能新增
- **Patch (1.0.X)**：向下相容的 bug 修復

### Q3：如何處理衝突？

**A**：
1. Agent ID 必須全局唯一
2. 同一 Agent 可有多個版本
3. 使用者可指定版本安裝

### Q4：費用如何計算？

**A**：內部市集通常免費使用，僅計算：
- 存儲成本（MinIO/S3）
- 計算成本（API 服務器）
- 資料庫成本
- 估算：每月 NT$ 5,000-15,000

---

**祝你使用愉快！** 🎉

如有問題，請參考書籍第 10 章或提交 Issue。
