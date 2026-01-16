# 第 5 章：五大核心工具 - 程式碼範例

> Read、List、Bash、Edit、Search Tool 完整實作

---

## 本目錄內容

本目錄包含第 5 章「五大核心工具」的完整可運行程式碼範例。

### 檔案清單

```
chapter-05/
├── README.md           # 本文件
├── main.go             # 主程式入口
├── tools/
│   ├── read.go         # Read Tool 實作
│   ├── list.go         # List Tool 實作
│   ├── bash.go         # Bash Tool 實作
│   ├── edit.go         # Edit Tool 實作
│   └── search.go       # Search Tool 實作
├── agent/
│   └── fizzbuzz.go     # FizzBuzz Agent 範例
├── go.mod
└── go.sum
```

---

## 執行方式

### 前置需求

- Go 1.21+
- Claude API Key
- ripgrep（用於 Search Tool）

### 安裝 ripgrep

```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
sudo apt install ripgrep

# Windows
choco install ripgrep
```

### 執行 FizzBuzz Agent

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
cd code-examples/chapter-05
go run . fizzbuzz
```

---

## 五大工具說明

### Read Tool
將檔案內容載入 Context，支援分頁讀取大檔案。

### List Tool
探索目錄結構，發現專案中的相關檔案。

### Bash Tool
執行系統命令，包含白名單/黑名單安全機制。

### Edit Tool
修改檔案內容，支援精確替換與差異驗證。

### Search Tool
整合 ripgrep 的高效程式碼搜尋。

---

## 學習目標對照

| 學習目標 | 對應程式碼 |
|----------|-----------|
| Read Tool | `tools/read.go` |
| List Tool | `tools/list.go` |
| Bash Tool | `tools/bash.go` |
| Edit Tool | `tools/edit.go` |
| Search Tool | `tools/search.go` |
| FizzBuzz Agent | `agent/fizzbuzz.go` |

---

## 延伸練習

1. 為 Bash Tool 新增更多安全限制
2. 實作 Edit Tool 的備份機制
3. 擴展 Search Tool 支援更多過濾選項
