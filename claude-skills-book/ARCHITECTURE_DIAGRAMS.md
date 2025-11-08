# Claude Code Skills 技術書 - 架構圖集

本文件包含書中所有關鍵系統架構圖，使用 Mermaid 語法繪製，可在 GitHub、VS Code 等環境中直接渲染。

## 目錄

1. [WebGuard 四層架構](#1-webguard-四層架構)
2. [Skills 生命週期與數據流](#2-skills-生命週期與數據流)
3. [Stagehand 工作流程](#3-stagehand-工作流程)
4. [CI/CD 流程](#4-cicd-流程)
5. [測試金字塔](#5-測試金字塔)
6. [Kubernetes 部署架構](#6-kubernetes-部署架構)
7. [MCP 整合架構](#7-mcp-整合架構)

---

## 1. WebGuard 四層架構

**引用章節**: Chapter 1.3.3, Chapter 9.1-9.2

```mermaid
graph TB
    subgraph "編排層 (Orchestration Layer)"
        A1[Task Scheduler<br/>Celery Beat]
        A2[Workflow Engine<br/>Orchestrator]
        A3[Resource Manager<br/>Worker Pool]
    end

    subgraph "執行層 (Execution Layer)"
        B1[Browser Skills<br/>Stagehand]
        B2[API Skills<br/>Requests/Pytest]
        B3[Data Skills<br/>Pandas/OpenPyXL]
        B4[Custom Skills<br/>User Defined]
    end

    subgraph "存儲層 (Storage Layer)"
        C1[(PostgreSQL<br/>Test Results)]
        C2[(Redis<br/>Cache & Queue)]
        C3[S3/MinIO<br/>Screenshots & Logs]
    end

    subgraph "報告層 (Reporting Layer)"
        D1[Allure Reports<br/>HTML Dashboard]
        D2[Grafana<br/>Metrics & Alerts]
        D3[Notifications<br/>Slack/Email]
    end

    A1 --> A2
    A2 --> A3
    A3 --> B1
    A3 --> B2
    A3 --> B3
    A3 --> B4

    B1 --> C1
    B1 --> C2
    B1 --> C3
    B2 --> C1
    B2 --> C2
    B3 --> C1

    C1 --> D1
    C1 --> D2
    C2 --> D2
    C3 --> D1

    D2 --> D3

    style A1 fill:#e1f5ff
    style A2 fill:#e1f5ff
    style A3 fill:#e1f5ff
    style B1 fill:#fff4e6
    style B2 fill:#fff4e6
    style B3 fill:#fff4e6
    style B4 fill:#fff4e6
    style C1 fill:#f3e5f5
    style C2 fill:#f3e5f5
    style C3 fill:#f3e5f5
    style D1 fill:#e8f5e9
    style D2 fill:#e8f5e9
    style D3 fill:#e8f5e9
```

**說明**：
- **編排層**：負責任務調度、工作流編排、資源管理
- **執行層**：各類 Skills 的執行環境
- **存儲層**：數據持久化、快取、日誌存儲
- **報告層**：測試報告、監控儀表板、告警通知

---

## 2. Skills 生命週期與數據流

**引用章節**: Chapter 3.3, Chapter 7.2

```mermaid
sequenceDiagram
    participant User as 用戶/CI
    participant Claude as Claude AI
    participant Skill as Skill System
    participant Executor as Executor
    participant External as 外部服務

    User->>Claude: 1. 提出需求<br/>"測試登入功能"

    Note over Claude,Skill: 發現階段 (Discovery)
    Claude->>Skill: 2. 掃描可用 Skills
    Skill-->>Claude: 3. 返回匹配的 Skills<br/>└─ browser_login_test

    Note over Claude,Skill: 準備階段 (Preparation)
    Claude->>Skill: 4. 載入 SKILL.md 詳細資訊
    Skill-->>Claude: 5. 返回參數定義與約束
    Claude->>Skill: 6. 準備參數<br/>{url, username, password}
    Skill-->>Claude: 7. 驗證參數格式

    Note over Claude,Executor: 執行階段 (Execution)
    Claude->>Executor: 8. 調用 Skill 執行函數
    Executor->>External: 9. 實際操作<br/>└─ Stagehand/API/等
    External-->>Executor: 10. 返回結果
    Executor->>Executor: 11. 錯誤處理與重試
    Executor-->>Claude: 12. 返回結構化結果

    Note over Claude,User: 報告階段 (Reporting)
    Claude->>User: 13. 生成測試報告
    Claude->>User: 14. 提供建議與洞察

    style User fill:#e3f2fd
    style Claude fill:#fff3e0
    style Skill fill:#f3e5f5
    style Executor fill:#e8f5e9
    style External fill:#fce4ec
```

**數據流說明**：
1. **用戶意圖** → Claude 解析
2. **Skills 發現** → 三層漸進式揭露
3. **參數準備** → Pydantic 驗證
4. **執行調用** → 具體實作
5. **結果返回** → 結構化輸出

---

## 3. Stagehand 工作流程

**引用章節**: Chapter 4.1.3, Chapter 4.2

```mermaid
graph LR
    A[用戶指令<br/>'click login button'] --> B{語意分析}

    B --> C[解析意圖<br/>Action: click<br/>Target: login button]

    C --> D[DOM 遍歷<br/>掃描頁面結構]

    D --> E[元素匹配<br/>AI scoring]

    E --> F{匹配成功?}

    F -->|Yes| G[執行操作<br/>scroll + click]
    F -->|No| H[重試機制<br/>3 次]

    G --> I[驗證結果]
    H --> D

    I --> J{成功?}
    J -->|Yes| K[返回成功]
    J -->|No| L[錯誤處理<br/>截圖 + 日誌]

    L --> M[返回失敗<br/>with context]

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#fff3e0
    style D fill:#f3e5f5
    style E fill:#f3e5f5
    style F fill:#ffccbc
    style G fill:#c8e6c9
    style H fill:#ffecb3
    style I fill:#f3e5f5
    style J fill:#ffccbc
    style K fill:#c8e6c9
    style L fill:#ffccbc
    style M fill:#ffcdd2
```

**核心特性**：
- ✅ 語意理解（不依賴選擇器）
- ✅ 自動重試（Circuit Breaker）
- ✅ 上下文感知（AI scoring）
- ✅ 自愈能力（適應 UI 變化）

---

## 4. CI/CD 流程

**引用章節**: Chapter 8.1-8.3

```mermaid
graph TD
    A[Git Push] --> B[GitHub Actions<br/>Trigger]

    B --> C{代碼檢查}
    C -->|Lint| D[Ruff/Black]
    C -->|Type| E[MyPy]
    C -->|Security| F[Bandit]

    D --> G{通過?}
    E --> G
    F --> G

    G -->|No| H[❌ 失敗通知]
    G -->|Yes| I[單元測試<br/>pytest]

    I --> J{通過?}
    J -->|No| H
    J -->|Yes| K[整合測試<br/>Skills E2E]

    K --> L{通過?}
    L -->|No| H
    L -->|Yes| M[建構 Docker Image]

    M --> N[推送到 Registry]

    N --> O{環境}
    O -->|Staging| P[部署到 Staging]
    O -->|Production| Q[部署到 Production]

    P --> R[冒煙測試]
    R --> S{通過?}
    S -->|Yes| T[✅ 成功]
    S -->|No| U[回滾]

    Q --> V[金絲雀發布<br/>10% 流量]
    V --> W[監控指標]
    W --> X{健康?}
    X -->|Yes| Y[100% 流量]
    X -->|No| U

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style G fill:#ffccbc
    style J fill:#ffccbc
    style L fill:#ffccbc
    style S fill:#ffccbc
    style X fill:#ffccbc
    style H fill:#ffcdd2
    style T fill:#c8e6c9
    style U fill:#ffcdd2
```

**階段說明**：
1. **代碼檢查**: Linting, Type checking, Security scan
2. **測試**: Unit → Integration → E2E
3. **建構**: Docker image + versioning
4. **部署**: Staging → Production (金絲雀)
5. **驗證**: 冒煙測試 + 監控

---

## 5. 測試金字塔

**引用章節**: Chapter 8.2, Chapter 8.5

```mermaid
graph TB
    subgraph "E2E 測試 (10%)"
        A1[完整用戶流程<br/>Stagehand + Skills]
        A2[跨服務整合<br/>API + Browser + DB]
    end

    subgraph "整合測試 (30%)"
        B1[Skills 整合<br/>多個 Skills 協作]
        B2[API 整合<br/>真實 HTTP 請求]
        B3[資料庫整合<br/>實際 PostgreSQL]
    end

    subgraph "單元測試 (60%)"
        C1[Skills 邏輯<br/>Mock 外部依賴]
        C2[參數驗證<br/>Pydantic Models]
        C3[錯誤處理<br/>Exception Cases]
        C4[工具函數<br/>Pure Functions]
    end

    A1 -.-> B1
    A2 -.-> B2
    B1 -.-> C1
    B2 -.-> C2
    B3 -.-> C3

    style A1 fill:#ffebee
    style A2 fill:#ffebee
    style B1 fill:#fff3e0
    style B2 fill:#fff3e0
    style B3 fill:#fff3e0
    style C1 fill:#e8f5e9
    style C2 fill:#e8f5e9
    style C3 fill:#e8f5e9
    style C4 fill:#e8f5e9
```

**測試比例**：
- **60% 單元測試**: 快速、隔離、大量
- **30% 整合測試**: 中速、真實依賴、適量
- **10% E2E 測試**: 慢速、完整流程、少量

**效益**：
- ⚡ 快速反饋（單元測試 < 1分鐘）
- 🎯 精準定位（層層驗證）
- 💰 成本優化（避免過多 E2E）

---

## 6. Kubernetes 部署架構

**引用章節**: Chapter 10.1-10.2

```mermaid
graph TB
    subgraph "Ingress Layer"
        I[Nginx Ingress<br/>SSL Termination]
    end

    subgraph "Application Layer"
        W1[WebGuard API<br/>Deployment x3]
        W2[Celery Workers<br/>Deployment x5]
        W3[Celery Beat<br/>Deployment x1]
    end

    subgraph "Storage Layer"
        P[(PostgreSQL<br/>StatefulSet)]
        R[(Redis<br/>StatefulSet)]
        M[MinIO<br/>StatefulSet]
    end

    subgraph "Monitoring Layer"
        G[Grafana<br/>Deployment]
        Pr[Prometheus<br/>Deployment]
        A[Alertmanager<br/>Deployment]
    end

    I --> W1
    W1 --> P
    W1 --> R
    W2 --> P
    W2 --> R
    W2 --> M
    W3 --> R

    W1 -.->|metrics| Pr
    W2 -.->|metrics| Pr
    P -.->|metrics| Pr
    R -.->|metrics| Pr

    Pr --> G
    Pr --> A

    style I fill:#e1f5ff
    style W1 fill:#fff4e6
    style W2 fill:#fff4e6
    style W3 fill:#fff4e6
    style P fill:#f3e5f5
    style R fill:#f3e5f5
    style M fill:#f3e5f5
    style G fill:#e8f5e9
    style Pr fill:#e8f5e9
    style A fill:#e8f5e9
```

**組件說明**：

| 組件 | 副本數 | 資源需求 | 用途 |
|------|--------|----------|------|
| **Nginx Ingress** | 2 | 500m CPU, 512Mi RAM | SSL 終止、路由 |
| **WebGuard API** | 3 | 1 CPU, 2Gi RAM | RESTful API 服務 |
| **Celery Workers** | 5 | 2 CPU, 4Gi RAM | 執行 Skills 任務 |
| **Celery Beat** | 1 | 500m CPU, 512Mi RAM | 任務調度 |
| **PostgreSQL** | 3 (HA) | 2 CPU, 4Gi RAM | 持久化存儲 |
| **Redis** | 3 (Cluster) | 1 CPU, 2Gi RAM | 快取與消息隊列 |
| **MinIO** | 4 | 1 CPU, 2Gi RAM | 對象存儲 (S3兼容) |
| **Prometheus** | 2 | 2 CPU, 4Gi RAM | 指標收集 |
| **Grafana** | 2 | 500m CPU, 1Gi RAM | 可視化儀表板 |

**高可用特性**：
- ✅ 多副本部署（API、Workers）
- ✅ StatefulSet（資料庫、快取）
- ✅ Pod Anti-Affinity（跨節點分散）
- ✅ HPA（Horizontal Pod Autoscaling）
- ✅ PVC（Persistent Volume Claims）

---

## 7. MCP 整合架構

**引用章節**: Chapter 1.2.3, Chapter 10.5, 附錄 A

```mermaid
graph LR
    subgraph "Claude Skills Layer"
        S1[Browser Skill]
        S2[API Skill]
        S3[Data Skill]
    end

    subgraph "MCP Protocol Layer"
        M[MCP Server<br/>standardized protocol]
    end

    subgraph "External Systems"
        E1[(Database<br/>PostgreSQL)]
        E2[Enterprise API<br/>REST/GraphQL]
        E3[Cloud Services<br/>AWS/GCP/Azure]
        E4[Custom Tools<br/>Internal Systems]
    end

    S1 --> M
    S2 --> M
    S3 --> M

    M --> E1
    M --> E2
    M --> E3
    M --> E4

    style S1 fill:#fff4e6
    style S2 fill:#fff4e6
    style S3 fill:#fff4e6
    style M fill:#e1f5ff
    style E1 fill:#f3e5f5
    style E2 fill:#f3e5f5
    style E3 fill:#f3e5f5
    style E4 fill:#f3e5f5
```

**MCP 優勢**：
1. **標準化協定**: 統一的 Skills ↔ 外部系統通訊
2. **安全性**: 內建認證與授權機制
3. **可擴展性**: 輕鬆添加新的外部服務
4. **版本控制**: 協定版本管理與向後兼容

**實作範例**：
```python
# MCP Server 定義
class DatabaseMCP:
    protocol_version = "1.0"

    async def query(self, sql: str) -> List[Dict]:
        """執行 SQL 查詢"""
        ...

    async def insert(self, table: str, data: Dict) -> int:
        """插入數據"""
        ...
```

---

## 使用指南

### 如何在章節中引用圖表

使用以下格式引用本文件中的圖表：

```markdown
詳細的架構設計請參考 [WebGuard 四層架構圖](../ARCHITECTURE_DIAGRAMS.md#1-webguard-四層架構)。
```

### Mermaid 圖表渲染

本文件中的 Mermaid 圖表可在以下環境自動渲染：
- ✅ GitHub (自動渲染)
- ✅ VS Code (需安裝 Mermaid 擴展)
- ✅ GitLab (內建支持)
- ✅ Notion (需匯入)
- ✅ Obsidian (內建支持)

### 導出為圖片

如需將圖表導出為 PNG/SVG：

```bash
# 使用 mermaid-cli
npm install -g @mermaid-js/mermaid-cli
mmdc -i ARCHITECTURE_DIAGRAMS.md -o diagrams/
```

---

## 圖表維護日誌

| 日期 | 版本 | 更新內容 | 更新者 |
|------|------|----------|--------|
| 2025-11-08 | 1.0.0 | 初始版本，包含 7 個核心架構圖 | Claude (總編輯) |

---

## 相關資源

- 📖 [CROSS_REFERENCES.md](./CROSS_REFERENCES.md) - 章節交叉引用指南
- 📖 [TERMINOLOGY_STANDARDS.md](./TERMINOLOGY_STANDARDS.md) - 術語標準
- 🔗 [Mermaid 官方文檔](https://mermaid.js.org/)
- 🔗 [WebGuard GitHub Repo](https://github.com/example/webguard) (待更新)

---

*圖表最後更新: 2025-11-08*
*文件版本: 1.0.0*
