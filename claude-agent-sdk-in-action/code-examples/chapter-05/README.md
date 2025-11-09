# 第 5 章：Subagents 協作模式 - 事件響應分析系統

## 專案說明

這是《Claude Agent SDK 打造企業 Agent》第 5 章的完整可運行程式碼範例。

本專案展示如何建立多個 Subagents 協同工作的事件響應系統，處理生產環境的緊急事件。

## 功能特色

✅ **四種協作模式**
- Sequential（順序執行）
- Parallel（平行執行）
- Hierarchical（階層式）
- Event-driven（事件驅動）

✅ **專業化 Subagents**
- Log Analyzer - 分析日誌
- Metrics Analyzer - 分析指標
- Code Inspector - 檢查程式碼

✅ **事件協調器**
- 混合協作模式
- 結果聚合
- 錯誤處理與重試

✅ **完整的錯誤處理**
- 重試機制
- 降級方案
- 部分失敗處理

## 快速開始

### 1. 安裝依賴

```bash
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 並填入 ANTHROPIC_API_KEY
```

### 3. 準備測試資料

```bash
# 建立模擬日誌
echo "2025-11-08 14:30:15 ERROR Database connection timeout" > logs/app.log
echo "2025-11-08 14:30:16 ERROR Database connection timeout" >> logs/app.log
echo "2025-11-08 14:30:17 WARNING Slow query detected" >> logs/app.log
```

### 4. 執行系統

```bash
python main.py
```

## 專案結構

```
chapter-05/
├── main.py                      # 主程式
├── requirements.txt             # Python 依賴
├── .env.example                 # 環境變數範例
├── subagents/                   # Subagent 模組
│   ├── base_subagent.py         # 基礎類別
│   ├── log_analyzer.py          # 日誌分析器
│   ├── metrics_analyzer.py      # 指標分析器
│   └── code_inspector.py        # 程式碼檢查器
├── orchestrator/                # 協調器模組
│   ├── event_orchestrator.py    # 事件協調器
│   └── resilience.py            # 錯誤處理
└── logs/                        # 日誌檔案（執行後產生）
```

## 系統架構

```
警報觸發
    ↓
事件協調器
    ↓
階段 1（平行執行）
    ├── Log Analyzer
    ├── Metrics Analyzer
    └── Code Inspector
    ↓
階段 2（結果聚合）
    ↓
階段 3（評估影響）
    ↓
生成完整報告
```

## 協作模式

### 平行執行
```python
# 同時執行多個獨立分析
results = await asyncio.gather(
    log_analyzer.execute(task, context),
    metrics_analyzer.execute(task, context),
    code_inspector.execute(task, context)
)
```

### 順序執行
```python
# 一個接一個執行
result1 = await analyzer1.execute(task, context)
result2 = await analyzer2.execute(task, context1)
result3 = await analyzer3.execute(task, context2)
```

### 事件驅動
```python
# 根據結果決定下一步
if "database" in result.get("issue_type"):
    db_result = await db_analyzer.execute(task, context)
```

## 效能指標

- **執行時間**: 8 分鐘（vs. 人工 60 分鐘）
- **時間節省**: 87%
- **情境使用**: 25K tokens（vs. 單一 Agent 180K）
- **API 成本**: $0.75（vs. $2.70）

## 錯誤處理

### 重試機制
```python
result = await execute_with_retry(
    subagent,
    task,
    context,
    max_retries=3
)
```

### 降級方案
```python
result = await execute_with_fallback(
    primary_subagent,
    fallback_subagent,
    task,
    context
)
```

### 部分失敗處理
```python
# 即使某些 Subagent 失敗，仍然繼續
successful_results = handle_partial_failure(results)
```

## 學習目標

完成本章後，你將掌握：

✅ 四種 Subagents 協作模式
✅ 設計專業化的 Subagents
✅ 實作事件協調器
✅ 平行執行與非同步編程
✅ 錯誤處理與重試機制
✅ 結果聚合與驗證

## 相關章節

- 第 4 章：你的第一個 Subagent - 大規模程式碼重構系統
- 第 6 章：輸出驗證與品質保證 - 自動化測試生成系統

## 授權

本程式碼為教學用途，版權所有。

---

**最後更新**: 2025-11-08
