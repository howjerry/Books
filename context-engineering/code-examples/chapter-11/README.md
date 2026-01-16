# 第 11 章：企業級應用模式 - 程式碼範例

> 夜間工廠、大規模遷移、安全審計

---

## 本目錄內容

本目錄包含第 11 章「企業級應用模式」的程式碼範例。

### 檔案清單

```
chapter-11/
├── README.md                   # 本文件
├── night-factory/
│   ├── start.sh                # 夜間工廠啟動腳本
│   ├── stop.sh                 # 停止腳本
│   ├── crontab.example         # Cron 設定範例
│   ├── config.yaml             # 配置文件
│   └── tasks/                  # 任務定義目錄
│       ├── dependency-update.md
│       ├── lint-fix.md
│       └── tech-debt.md
├── migration/
│   ├── jest-to-vitest/         # Jest → Vitest 遷移
│   │   ├── PROMPT.md
│   │   └── validation.sh
│   └── commonjs-to-esm/        # CommonJS → ESM 遷移
│       ├── PROMPT.md
│       └── validation.sh
├── security/
│   ├── sandbox.sh              # 沙箱執行腳本
│   ├── audit-log.go            # 審計日誌實作
│   └── permissions.yaml        # 權限配置
├── monitoring/
│   ├── dashboard.html          # 簡易監控儀表板
│   ├── alerts.yaml             # 告警設定
│   └── metrics.go              # 指標收集
└── team/
    ├── shared-prompts/         # 團隊共享 PROMPT 模板
    └── review-checklist.md     # 程式碼審查清單
```

---

## 夜間工廠設定

### Crontab 設定

```bash
# 每天晚上 11 點啟動
0 23 * * * /path/to/night-factory/start.sh

# 早上 7 點停止
0 7 * * * /path/to/night-factory/stop.sh
```

### 配置文件

```yaml
# config.yaml
night_factory:
  start_time: "23:00"
  stop_time: "07:00"
  max_iterations: 100
  cost_limit: 50.00  # USD

tasks:
  - name: dependency-update
    priority: 1
    enabled: true
  - name: lint-fix
    priority: 2
    enabled: true
```

---

## 大規模遷移

### Jest → Vitest 遷移

```bash
cd migration/jest-to-vitest
# 查看 PROMPT.md 了解遷移策略
cat PROMPT.md

# 驗證遷移結果
./validation.sh
```

### CommonJS → ESM 遷移

```bash
cd migration/commonjs-to-esm
cat PROMPT.md
./validation.sh
```

---

## 安全機制

### 沙箱執行

```bash
# 在受限環境中執行 Ralph Loop
./security/sandbox.sh --task "migration" --prompt PROMPT.md
```

### 審計日誌

所有操作都會記錄到審計日誌：

```json
{
  "timestamp": "2026-01-13T23:45:00Z",
  "action": "file_edit",
  "file": "src/utils.ts",
  "agent": "ralph-worker-1",
  "commit": "abc123"
}
```

### 權限控制

```yaml
# permissions.yaml
allowed_paths:
  - "src/**"
  - "tests/**"

denied_paths:
  - ".env*"
  - "secrets/**"
  - "config/production.yaml"

allowed_commands:
  - "npm test"
  - "npm run lint"
  - "npm run build"

denied_commands:
  - "rm -rf"
  - "curl"
  - "wget"
```

---

## 監控與告警

### 啟動監控儀表板

```bash
cd monitoring
python -m http.server 8080
# 訪問 http://localhost:8080/dashboard.html
```

### 告警配置

```yaml
# alerts.yaml
alerts:
  - name: high_cost
    condition: "cost > 20"
    action: "stop_and_notify"

  - name: stuck_loop
    condition: "no_progress_minutes > 30"
    action: "restart_or_stop"

  - name: error_rate
    condition: "errors_per_iteration > 0.5"
    action: "notify"
```

---

## 團隊協作

### 共享 PROMPT 模板

團隊成員可以在 `team/shared-prompts/` 中維護標準化的 PROMPT 模板。

### 程式碼審查清單

AI 生成的程式碼仍需經過審查，使用 `team/review-checklist.md` 確保品質。
