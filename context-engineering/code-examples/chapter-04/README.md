# 第 4 章：推論迴圈的解剖學 - 程式碼範例

> 用 Go 語言建構基本聊天介面

---

## 本目錄內容

本目錄包含第 4 章「推論迴圈的解剖學」的完整可運行程式碼範例。

### 檔案清單

```
chapter-04/
├── README.md           # 本文件
├── main.go             # 主程式入口
├── client.go           # Claude API 客戶端
├── loop.go             # 推論迴圈實作
├── tools.go            # 工具定義與註冊
├── prompt.go           # Harness Prompt 管理
├── go.mod              # Go 模組定義
└── go.sum              # 依賴版本鎖定
```

---

## 執行方式

### 前置需求

- Go 1.21+
- Claude API Key

### 設定

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 執行

```bash
cd code-examples/chapter-04
go run .
```

---

## 核心概念

本範例展示：

1. **推論迴圈的五個階段**
   - 輸入 → 推論 → 工具呼叫 → 結果分配 → 再推論

2. **Harness Prompt 設計**
   - 角色定義
   - 能力範圍
   - 行為準則

3. **工具註冊機制**
   - JSON Schema 參數定義
   - 工具描述最佳實踐

4. **結果分配技巧**
   - 工具結果注入 Context
   - 錯誤處理與恢復

---

## 學習目標對照

| 學習目標 | 對應程式碼 |
|----------|-----------|
| 推論迴圈實作 | `loop.go` |
| Harness Prompt | `prompt.go` |
| 工具註冊 | `tools.go` |
| API 客戶端 | `client.go` |

---

## 延伸練習

1. 新增一個自訂工具到 `tools.go`
2. 修改 `prompt.go` 中的系統提示詞
3. 實作錯誤重試機制
