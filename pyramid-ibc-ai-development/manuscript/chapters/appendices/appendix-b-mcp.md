# 附錄 B：MCP Server 整合清單

## B.1 什麼是 MCP？

MCP（Model Context Protocol）是一個讓 Claude Code 連接到外部工具和資料來源的協定。透過 MCP，你可以讓 Claude Code 直接存取：

- 專案管理工具（Linear、Jira）
- 文件系統（Notion、Confluence）
- 通訊工具（Slack）
- 版本控制（GitHub）
- 資料庫

---

## B.2 MCP 設定檔

MCP 設定檔位於 `~/.claude/mcp_servers.json`：

```json
{
  "servers": [
    {
      "name": "linear",
      "type": "linear",
      "config": {
        "api_key": "${LINEAR_API_KEY}"
      }
    },
    {
      "name": "github",
      "type": "github",
      "config": {
        "token": "${GITHUB_TOKEN}"
      }
    }
  ]
}
```

---

## B.3 常用 MCP Server

### Linear（專案管理）

```json
{
  "name": "linear",
  "type": "linear",
  "config": {
    "api_key": "${LINEAR_API_KEY}"
  }
}
```

**可用指令：**
```
從 Linear ticket LIN-1234 獲取需求
更新 Linear ticket LIN-1234 狀態為 "In Progress"
在 Linear ticket LIN-1234 新增留言
```

**取得 API Key：**
1. 前往 Linear Settings > API
2. 點擊 "Create new API key"
3. 設定環境變數 `LINEAR_API_KEY`

---

### GitHub（版本控制）

```json
{
  "name": "github",
  "type": "github",
  "config": {
    "token": "${GITHUB_TOKEN}",
    "repos": ["owner/repo1", "owner/repo2"]
  }
}
```

**可用指令：**
```
讀取 GitHub Issue #123 的內容
查看 PR #456 的變更
搜尋程式碼中包含 "TODO" 的檔案
```

**取得 Token：**
1. 前往 GitHub Settings > Developer settings > Personal access tokens
2. 產生新 token，選擇需要的 scope
3. 設定環境變數 `GITHUB_TOKEN`

---

### Notion（文件）

```json
{
  "name": "notion",
  "type": "notion",
  "config": {
    "api_key": "${NOTION_API_KEY}",
    "root_page_id": "your-root-page-id"
  }
}
```

**可用指令：**
```
讀取 Notion 頁面 "API 設計規範" 的內容
搜尋 Notion 中包含 "登入" 的頁面
```

---

### Slack（通訊）

```json
{
  "name": "slack",
  "type": "slack",
  "config": {
    "bot_token": "${SLACK_BOT_TOKEN}",
    "channels": ["backend", "frontend", "general"]
  }
}
```

**可用指令：**
```
搜尋 Slack #backend 頻道中關於 "認證" 的討論
在 Slack #frontend 發送訊息
```

---

### PostgreSQL（資料庫）

```json
{
  "name": "database",
  "type": "postgresql",
  "config": {
    "connection_string": "${DATABASE_URL}",
    "read_only": true
  }
}
```

**可用指令：**
```
查詢 users 表的結構
執行 SQL: SELECT COUNT(*) FROM orders WHERE status = 'pending'
```

> ⚠️ **注意**：強烈建議使用唯讀連線，避免意外修改生產資料。

---

## B.4 自訂 MCP Server

如果你需要連接的工具沒有現成的 MCP Server，可以自己開發。

### MCP Server 介面

```python
# custom_mcp_server.py
from mcp import MCPServer, MCPRequest, MCPResponse

class CustomMCPServer(MCPServer):
    name = "custom"

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        if request.action == "get_data":
            data = await self.fetch_data(request.params)
            return MCPResponse(success=True, data=data)

        return MCPResponse(success=False, error="Unknown action")

    async def fetch_data(self, params: dict) -> dict:
        # 實作你的邏輯
        pass
```

### 註冊自訂 Server

```json
{
  "name": "custom",
  "type": "custom",
  "config": {
    "module": "path/to/custom_mcp_server.py",
    "class": "CustomMCPServer"
  }
}
```

---

## B.5 安全性考量

### 最小權限原則

- 只授予 MCP Server 必要的權限
- 使用唯讀 token/連線（如果不需要寫入）
- 限制可存取的資源範圍

### API Key 管理

- 不要把 API key 寫在設定檔中，使用環境變數
- 定期輪換 API key
- 監控 API 使用量

### 資料保護

- 不要讓 MCP 存取敏感資料（密碼、個資）
- 考慮使用資料脫敏
- 遵守公司的資安政策
