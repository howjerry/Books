# TechAssist v2.0 - Part 4 程式碼範例

本目錄包含《LangChain 到 DeepAgents 實戰》Part 4（Chapter 10-13）的程式碼範例。

## 生產部署組件

| 章節 | 主題 | 目錄/檔案 |
|------|------|-----------|
| Ch10 | 可觀測性 | `observability/` |
| Ch11 | 安全護欄 | `security/` |
| Ch12 | 效能優化 | `optimization/` |
| Ch13 | 容器部署 | `deployment/` |

## 專案結構

```
part4-production/
├── README.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── observability/
│   ├── __init__.py
│   ├── config.py              # OpenTelemetry 配置
│   ├── llm_tracer.py          # LLM 調用追蹤
│   ├── metrics.py             # Agent 指標定義
│   └── otel-collector.yaml    # Collector 配置
├── security/
│   ├── __init__.py
│   ├── input_validator.py     # 輸入驗證
│   ├── output_filter.py       # 輸出過濾
│   ├── rbac.py                # 權限控制
│   └── secure_memory.py       # 安全記憶存儲
├── optimization/
│   ├── __init__.py
│   ├── prompt_compressor.py   # Prompt 壓縮
│   ├── cache.py               # 多層快取
│   ├── model_router.py        # 模型路由
│   └── batch_processor.py     # 批處理器
└── deployment/
    ├── k8s/
    │   ├── namespace.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── hpa.yaml
    │   └── monitoring/
    │       └── alerting-rules.yaml
    └── scripts/
        ├── blue-green-switch.sh
        └── disaster-recovery.sh
```

## 快速開始

### 本地開發

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入 API 密鑰

# 3. 啟動所有服務
docker-compose up -d

# 4. 訪問服務
# - API: http://localhost:8000
# - Grafana: http://localhost:3000
# - Jaeger: http://localhost:16686
# - Prometheus: http://localhost:9090
```

### Kubernetes 部署

```bash
# 1. 創建命名空間
kubectl apply -f deployment/k8s/namespace.yaml

# 2. 配置密鑰
kubectl create secret generic techassist-secrets \
  --from-literal=ANTHROPIC_API_KEY=<your-key> \
  -n techassist

# 3. 部署應用
kubectl apply -f deployment/k8s/

# 4. 檢查狀態
kubectl get pods -n techassist
```

## 主要特性

### 可觀測性 (Chapter 10)

- **OpenTelemetry 整合**：統一的追蹤、指標、日誌
- **LLM 調用追蹤**：Token 使用、延遲、錯誤
- **Agent 指標**：品質分數、迭代次數、成本

### 安全護欄 (Chapter 11)

- **Prompt Injection 防護**：多層驗證
- **輸出過濾**：PII 脫敏、敏感信息移除
- **RBAC**：基於角色的權限控制

### 效能優化 (Chapter 12)

- **Token 優化**：Prompt 壓縮、動態預算
- **多層快取**：L1 內存 + L2 Redis + L3 語義
- **模型路由**：智能選擇最佳模型

### 容器部署 (Chapter 13)

- **Docker**：多階段構建、健康檢查
- **Kubernetes**：HPA、滾動更新、反親和性
- **CI/CD**：GitHub Actions、金絲雀發布

## 版本演進

| 版本 | 新增特性 |
|------|----------|
| v0.1 | 基本 Chain 問答 |
| v0.3 | Tool Calling |
| v0.5 | LangGraph 狀態管理 |
| v0.7 | 多 Agent 協作 |
| v1.0 | DeepAgents 設計模式 |
| **v2.0** | **生產級系統** |

## 相關章節

- Chapter 10: 可觀測性 (Observability)
- Chapter 11: 安全護欄 (Security & Guardrails)
- Chapter 12: 效能與成本優化
- Chapter 13: 容器化與部署
