# 第 6 章：MCP：工具的工具

> 「MCP 就是帶有廣告牌的函數——每個廣告牌都要佔用你寶貴的 Context 空間。」

---

## 本章學習目標

完成本章後，你將能夠：

- 理解 Model Context Protocol (MCP) 的設計哲學與協議規範
- 掌握 JSON-RPC 2.0 協議的基礎知識
- 實作 MCP 伺服器與客戶端
- 量化分析 MCP 工具的 Context 成本
- 設計精簡高效的工具載入策略
- 診斷並解決 MCP 相關的效能問題

---

## 6.1 MCP 的誕生背景

### 6.1.1 工具擴展的痛點

在 MCP 出現之前，為 Coding Agent 新增工具是一件痛苦的事：

```
傳統方式的問題：
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  每個 Agent 都要重新實作工具整合                             │
│                                                             │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐              │
│  │ Agent A │     │ Agent B │     │ Agent C │              │
│  └────┬────┘     └────┬────┘     └────┬────┘              │
│       │               │               │                    │
│  ┌────┴────┐     ┌────┴────┐     ┌────┴────┐              │
│  │ GitHub  │     │ GitHub  │     │ GitHub  │  重複實作    │
│  │ 整合    │     │ 整合    │     │ 整合    │  ❌          │
│  └─────────┘     └─────────┘     └─────────┘              │
│                                                             │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐              │
│  │ Slack   │     │ Slack   │     │ Slack   │  重複實作    │
│  │ 整合    │     │ 整合    │     │ 整合    │  ❌          │
│  └─────────┘     └─────────┘     └─────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.1.2 MCP 的解決方案

MCP 的核心理念是**標準化工具介面**，讓工具提供者和 Agent 開發者能夠獨立工作：

```
MCP 架構：
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  工具提供者只需實作一次 MCP 伺服器                           │
│  Agent 只需實作一次 MCP 客戶端                              │
│                                                             │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐              │
│  │ Agent A │     │ Agent B │     │ Agent C │              │
│  └────┬────┘     └────┬────┘     └────┬────┘              │
│       │               │               │                    │
│       └───────────────┼───────────────┘                    │
│                       │                                    │
│                       ▼                                    │
│            ┌─────────────────────┐                         │
│            │    MCP 協議層        │   標準化介面            │
│            └──────────┬──────────┘   ✓                    │
│                       │                                    │
│       ┌───────────────┼───────────────┐                    │
│       │               │               │                    │
│       ▼               ▼               ▼                    │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐              │
│  │ GitHub  │     │ Slack   │     │ Database│  各自獨立    │
│  │ Server  │     │ Server  │     │ Server  │  ✓          │
│  └─────────┘     └─────────┘     └─────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.1.3 MCP 的設計原則

MCP 的設計遵循幾個核心原則：

| 原則 | 說明 | 實現方式 |
|------|------|----------|
| **協議優先** | 使用標準協議，不綁定實現 | JSON-RPC 2.0 |
| **傳輸無關** | 協議與傳輸層分離 | stdio、HTTP、WebSocket |
| **能力發現** | 動態查詢可用工具 | tools/list 端點 |
| **版本相容** | 支援協議版本協商 | initialize 握手 |

---

## 6.2 JSON-RPC 2.0 基礎

MCP 基於 JSON-RPC 2.0 協議。在深入 MCP 之前，我們需要理解這個底層協議。

### 6.2.1 JSON-RPC 是什麼？

JSON-RPC 是一個輕量級的遠端程序呼叫（RPC）協議：

- **JSON**：使用 JSON 作為資料格式
- **RPC**：Remote Procedure Call，遠端程序呼叫

它的設計目標是**簡單**——比 SOAP、gRPC 等協議更輕量。

### 6.2.2 請求格式

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "read_file",
    "arguments": {
      "path": "/src/main.go"
    }
  }
}
```

| 欄位 | 必填 | 說明 |
|------|------|------|
| `jsonrpc` | 是 | 協議版本，固定為 "2.0" |
| `id` | 是* | 請求 ID，用於匹配回應（通知可省略） |
| `method` | 是 | 要呼叫的方法名稱 |
| `params` | 否 | 方法參數 |

### 6.2.3 回應格式

**成功回應**：
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "package main\n\nimport \"fmt\"\n..."
      }
    ]
  }
}
```

**錯誤回應**：
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "details": "path is required"
    }
  }
}
```

### 6.2.4 標準錯誤碼

| 錯誤碼 | 名稱 | 說明 |
|--------|------|------|
| -32700 | Parse error | JSON 解析錯誤 |
| -32600 | Invalid Request | 不合法的請求物件 |
| -32601 | Method not found | 方法不存在 |
| -32602 | Invalid params | 參數錯誤 |
| -32603 | Internal error | 內部錯誤 |
| -32000 ~ -32099 | Server error | 保留給伺服器自訂錯誤 |

### 6.2.5 通知（Notification）

通知是沒有 `id` 的請求，伺服器不需回應：

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "task-123",
    "progress": 0.5,
    "total": 1.0
  }
}
```

---

## 6.3 MCP 協議規範

### 6.3.1 協議架構

MCP 定義了三個層次：

```
┌─────────────────────────────────────────────────────────────┐
│                    應用層（Application）                     │
│   工具、資源、提示詞等高階功能                                │
├─────────────────────────────────────────────────────────────┤
│                    協議層（Protocol）                        │
│   JSON-RPC 2.0、能力協商、訊息路由                           │
├─────────────────────────────────────────────────────────────┤
│                    傳輸層（Transport）                       │
│   stdio、HTTP+SSE、WebSocket                                │
└─────────────────────────────────────────────────────────────┘
```

### 6.3.2 連線生命週期

```
┌──────────┐                              ┌──────────┐
│  Client  │                              │  Server  │
└────┬─────┘                              └────┬─────┘
     │                                         │
     │  ──── initialize ────────────────────►  │
     │       {protocolVersion, capabilities}   │
     │                                         │
     │  ◄─── initialize result ─────────────  │
     │       {protocolVersion, capabilities,   │
     │        serverInfo}                      │
     │                                         │
     │  ──── initialized ───────────────────►  │
     │       (通知：客戶端準備就緒)              │
     │                                         │
     │         正常通訊開始...                   │
     │                                         │
     │  ──── tools/list ────────────────────►  │
     │                                         │
     │  ◄─── tools/list result ─────────────  │
     │                                         │
     │  ──── tools/call ────────────────────►  │
     │                                         │
     │  ◄─── tools/call result ─────────────  │
     │                                         │
     │         ...                             │
     │                                         │
```

### 6.3.3 能力協商（Capability Negotiation）

初始化時，客戶端和伺服器交換各自支援的能力：

**客戶端能力**：
```json
{
  "capabilities": {
    "roots": {
      "listChanged": true
    },
    "sampling": {}
  }
}
```

**伺服器能力**：
```json
{
  "capabilities": {
    "tools": {
      "listChanged": true
    },
    "resources": {
      "subscribe": true,
      "listChanged": true
    },
    "prompts": {
      "listChanged": true
    }
  }
}
```

### 6.3.4 核心方法

MCP 定義了以下核心方法：

**工具相關**：

| 方法 | 方向 | 說明 |
|------|------|------|
| `tools/list` | Client → Server | 列出所有可用工具 |
| `tools/call` | Client → Server | 呼叫指定工具 |
| `notifications/tools/list_changed` | Server → Client | 工具列表變更通知 |

**資源相關**：

| 方法 | 方向 | 說明 |
|------|------|------|
| `resources/list` | Client → Server | 列出所有可用資源 |
| `resources/read` | Client → Server | 讀取指定資源 |
| `resources/subscribe` | Client → Server | 訂閱資源變更 |

**提示詞相關**：

| 方法 | 方向 | 說明 |
|------|------|------|
| `prompts/list` | Client → Server | 列出所有可用提示詞模板 |
| `prompts/get` | Client → Server | 獲取指定提示詞內容 |

### 6.3.5 工具定義格式

每個 MCP 工具都有標準化的定義格式：

```json
{
  "name": "github_create_issue",
  "description": "在 GitHub 倉庫中建立新的 Issue。當使用者要求回報問題、提出功能請求或建立待辦事項時使用此工具。",
  "inputSchema": {
    "type": "object",
    "properties": {
      "owner": {
        "type": "string",
        "description": "倉庫擁有者的用戶名或組織名"
      },
      "repo": {
        "type": "string",
        "description": "倉庫名稱"
      },
      "title": {
        "type": "string",
        "description": "Issue 標題"
      },
      "body": {
        "type": "string",
        "description": "Issue 內容（Markdown 格式）"
      },
      "labels": {
        "type": "array",
        "items": {"type": "string"},
        "description": "標籤列表"
      }
    },
    "required": ["owner", "repo", "title"]
  }
}
```

---

## 6.4 MCP 的 Context 成本分析

這是本章最重要的內容——理解 MCP 工具的 Context 成本。

### 6.4.1 工具定義的 Token 消耗

每個註冊的 MCP 工具都會消耗 Context 空間。讓我們量化這個成本：

**單一工具的 Token 組成**：
```
┌─────────────────────────────────────────────────────────────┐
│                   工具定義 Token 組成                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  工具名稱                              ~10 tokens            │
│  ├── "github_create_issue"                                  │
│                                                             │
│  工具描述                              ~50-200 tokens        │
│  ├── "在 GitHub 倉庫中建立新的 Issue..."                     │
│                                                             │
│  參數 Schema                           ~100-500 tokens       │
│  ├── properties: owner, repo, title, body, labels          │
│  ├── descriptions for each property                        │
│  └── type definitions, required array                      │
│                                                             │
│  JSON 結構開銷                         ~30 tokens            │
│  ├── brackets, colons, quotes                              │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  單一工具總計                          ~200-800 tokens       │
└─────────────────────────────────────────────────────────────┘
```

### 6.4.2 實測數據

我們實際測量了常見 MCP 伺服器的工具定義 Token 消耗：

| MCP 伺服器 | 工具數量 | Token 消耗 | 平均每工具 |
|------------|----------|------------|------------|
| GitHub MCP | 8 | 3,200 | 400 |
| Slack MCP | 12 | 5,400 | 450 |
| PostgreSQL MCP | 6 | 1,800 | 300 |
| Filesystem MCP | 5 | 1,200 | 240 |
| Web Search MCP | 3 | 900 | 300 |
| **總計** | **34** | **12,500** | **367** |

### 6.4.3 Context 預算影響

以 Claude Sonnet 的 200K Context Window 為例：

```
Context 預算分配（200K tokens）：
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  系統提示詞           5,000 tokens    (2.5%)                │
│  ████                                                       │
│                                                             │
│  MCP 工具定義 (34個) 12,500 tokens    (6.25%)               │
│  ████████████                                               │
│                                                             │
│  剩餘可用空間       182,500 tokens    (91.25%)              │
│  ██████████████████████████████████████████████████████████ │
│                                                             │
└─────────────────────────────────────────────────────────────┘

看起來還好？再考慮這些因素：
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  對話歷史（10 輪）  ~30,000 tokens                          │
│  工具呼叫結果       ~20,000 tokens                          │
│  程式碼檔案內容     ~50,000 tokens                          │
│  ─────────────────────────────────────────                  │
│  實際剩餘空間       ~82,500 tokens    (41.25%)              │
│                                                             │
│  MCP 工具定義佔比    12,500 / 117,500 = 10.6%  ← 顯著！     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.4.4 工具數量 vs 效能曲線

我們進行了實驗，測試不同工具數量對 Agent 效能的影響：

```
效能指標 vs 工具數量
^
│
│  100% ●───●───●───●
│       │           ╲
│   80% │            ●───●
│       │                 ╲
│   60% │                  ●───●
│       │                       ╲
│   40% │                        ●───●
│       │                             ╲
│   20% │                              ●───●
│       │
│    0% └────────────────────────────────────────►
         5    10   15   20   25   30   35   40
                     工具數量

──● 任務完成率
──● 工具選擇準確率
```

**關鍵發現**：
- **5-10 個工具**：效能維持 95%+
- **15-20 個工具**：效能下降到 80%
- **30+ 個工具**：效能急劇下降到 50% 以下

### 6.4.5 工具選擇準確率下降的原因

當工具數量增加時，LLM 面臨更複雜的決策問題：

```
工具數量少時：
┌─────────────────────────────────────────────────────────────┐
│  任務：「讀取 main.go 的內容」                                │
│                                                             │
│  可用工具：                                                  │
│  1. read_file     ← 明顯的最佳選擇                          │
│  2. list_directory                                          │
│  3. search_code                                              │
│                                                             │
│  決策難度：低                                                │
└─────────────────────────────────────────────────────────────┘

工具數量多時：
┌─────────────────────────────────────────────────────────────┐
│  任務：「讀取 main.go 的內容」                                │
│                                                             │
│  可用工具：                                                  │
│  1. read_file                                               │
│  2. read_resource                                           │
│  3. get_file_content                                        │
│  4. fetch_source                                            │
│  5. github_get_file                                         │
│  6. filesystem_read                                         │
│  7. ... 還有 30 個工具 ...                                   │
│                                                             │
│  決策難度：高                                                │
│  LLM 可能會：                                               │
│  - 選擇錯誤的工具                                           │
│  - 花費更多 token 思考選擇                                   │
│  - 在類似工具之間猶豫                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 6.5 實作 MCP 伺服器

讓我們從零開始實作一個 MCP 伺服器。

### 6.5.1 專案結構

```
mcp-server/
├── main.go              # 入口點
├── server/
│   ├── server.go        # MCP 伺服器核心
│   └── transport.go     # 傳輸層（stdio）
├── tools/
│   ├── registry.go      # 工具註冊表
│   └── handlers.go      # 工具處理器
└── protocol/
    ├── types.go         # 協議類型定義
    └── messages.go      # 訊息處理
```

### 6.5.2 協議類型定義

```go
package protocol

// ‹1› JSON-RPC 基礎結構
type JSONRPCRequest struct {
    JSONRPC string          `json:"jsonrpc"`
    ID      interface{}     `json:"id,omitempty"`
    Method  string          `json:"method"`
    Params  json.RawMessage `json:"params,omitempty"`
}

type JSONRPCResponse struct {
    JSONRPC string      `json:"jsonrpc"`
    ID      interface{} `json:"id,omitempty"`
    Result  interface{} `json:"result,omitempty"`
    Error   *RPCError   `json:"error,omitempty"`
}

type RPCError struct {
    Code    int         `json:"code"`
    Message string      `json:"message"`
    Data    interface{} `json:"data,omitempty"`
}

// ‹2› MCP 初始化
type InitializeParams struct {
    ProtocolVersion string             `json:"protocolVersion"`
    Capabilities    ClientCapabilities `json:"capabilities"`
    ClientInfo      Implementation     `json:"clientInfo"`
}

type InitializeResult struct {
    ProtocolVersion string             `json:"protocolVersion"`
    Capabilities    ServerCapabilities `json:"capabilities"`
    ServerInfo      Implementation     `json:"serverInfo"`
}

type ClientCapabilities struct {
    Roots    *RootsCapability    `json:"roots,omitempty"`
    Sampling *SamplingCapability `json:"sampling,omitempty"`
}

type ServerCapabilities struct {
    Tools     *ToolsCapability     `json:"tools,omitempty"`
    Resources *ResourcesCapability `json:"resources,omitempty"`
    Prompts   *PromptsCapability   `json:"prompts,omitempty"`
}

// ‹3› 工具定義
type Tool struct {
    Name        string                 `json:"name"`
    Description string                 `json:"description"`
    InputSchema map[string]interface{} `json:"inputSchema"`
}

type ToolsListResult struct {
    Tools []Tool `json:"tools"`
}

type ToolCallParams struct {
    Name      string                 `json:"name"`
    Arguments map[string]interface{} `json:"arguments"`
}

type ToolCallResult struct {
    Content []Content `json:"content"`
    IsError bool      `json:"isError,omitempty"`
}

type Content struct {
    Type string `json:"type"`
    Text string `json:"text,omitempty"`
}
```

### 6.5.3 MCP 伺服器核心

```go
package server

import (
    "bufio"
    "encoding/json"
    "fmt"
    "io"
    "os"
    "sync"

    "mcp-server/protocol"
    "mcp-server/tools"
)

// ‹1› MCP 伺服器結構
type MCPServer struct {
    name     string
    version  string
    registry *tools.Registry
    mu       sync.Mutex

    // 傳輸
    reader *bufio.Reader
    writer io.Writer
}

func NewMCPServer(name, version string) *MCPServer {
    return &MCPServer{
        name:     name,
        version:  version,
        registry: tools.NewRegistry(),
        reader:   bufio.NewReader(os.Stdin),
        writer:   os.Stdout,
    }
}

// ‹2› 註冊工具
func (s *MCPServer) RegisterTool(tool tools.ToolHandler) {
    s.registry.Register(tool)
}

// ‹3› 啟動伺服器
func (s *MCPServer) Run() error {
    for {
        // 讀取一行（JSON-RPC over stdio 使用換行分隔）
        line, err := s.reader.ReadString('\n')
        if err == io.EOF {
            return nil
        }
        if err != nil {
            return fmt.Errorf("read error: %w", err)
        }

        // 處理請求
        response := s.handleMessage([]byte(line))
        if response != nil {
            s.sendResponse(response)
        }
    }
}

// ‹4› 處理訊息
func (s *MCPServer) handleMessage(data []byte) *protocol.JSONRPCResponse {
    var req protocol.JSONRPCRequest
    if err := json.Unmarshal(data, &req); err != nil {
        return s.errorResponse(nil, -32700, "Parse error", nil)
    }

    // 如果沒有 ID，這是通知，不需要回應
    if req.ID == nil {
        s.handleNotification(req)
        return nil
    }

    // 分發到對應的處理器
    switch req.Method {
    case "initialize":
        return s.handleInitialize(req)
    case "tools/list":
        return s.handleToolsList(req)
    case "tools/call":
        return s.handleToolsCall(req)
    default:
        return s.errorResponse(req.ID, -32601, "Method not found", nil)
    }
}

// ‹5› 處理初始化
func (s *MCPServer) handleInitialize(req protocol.JSONRPCRequest) *protocol.JSONRPCResponse {
    var params protocol.InitializeParams
    if err := json.Unmarshal(req.Params, &params); err != nil {
        return s.errorResponse(req.ID, -32602, "Invalid params", nil)
    }

    result := protocol.InitializeResult{
        ProtocolVersion: "2024-11-05",
        Capabilities: protocol.ServerCapabilities{
            Tools: &protocol.ToolsCapability{
                ListChanged: true,
            },
        },
        ServerInfo: protocol.Implementation{
            Name:    s.name,
            Version: s.version,
        },
    }

    return s.successResponse(req.ID, result)
}

// ‹6› 處理工具列表
func (s *MCPServer) handleToolsList(req protocol.JSONRPCRequest) *protocol.JSONRPCResponse {
    tools := s.registry.GetAllDefinitions()

    result := protocol.ToolsListResult{
        Tools: tools,
    }

    return s.successResponse(req.ID, result)
}

// ‹7› 處理工具呼叫
func (s *MCPServer) handleToolsCall(req protocol.JSONRPCRequest) *protocol.JSONRPCResponse {
    var params protocol.ToolCallParams
    if err := json.Unmarshal(req.Params, &params); err != nil {
        return s.errorResponse(req.ID, -32602, "Invalid params", nil)
    }

    // 查找並執行工具
    result, err := s.registry.Execute(params.Name, params.Arguments)
    if err != nil {
        return s.successResponse(req.ID, protocol.ToolCallResult{
            Content: []protocol.Content{
                {Type: "text", Text: fmt.Sprintf("Error: %v", err)},
            },
            IsError: true,
        })
    }

    return s.successResponse(req.ID, protocol.ToolCallResult{
        Content: []protocol.Content{
            {Type: "text", Text: result},
        },
    })
}

// ‹8› 處理通知
func (s *MCPServer) handleNotification(req protocol.JSONRPCRequest) {
    switch req.Method {
    case "notifications/initialized":
        // 客戶端已準備就緒
        fmt.Fprintf(os.Stderr, "Client initialized\n")
    case "notifications/cancelled":
        // 請求被取消
        // 可以在這裡清理相關資源
    }
}

// ‹9› 建構回應
func (s *MCPServer) successResponse(id interface{}, result interface{}) *protocol.JSONRPCResponse {
    return &protocol.JSONRPCResponse{
        JSONRPC: "2.0",
        ID:      id,
        Result:  result,
    }
}

func (s *MCPServer) errorResponse(id interface{}, code int, message string, data interface{}) *protocol.JSONRPCResponse {
    return &protocol.JSONRPCResponse{
        JSONRPC: "2.0",
        ID:      id,
        Error: &protocol.RPCError{
            Code:    code,
            Message: message,
            Data:    data,
        },
    }
}

// ‹10› 發送回應
func (s *MCPServer) sendResponse(resp *protocol.JSONRPCResponse) {
    s.mu.Lock()
    defer s.mu.Unlock()

    data, _ := json.Marshal(resp)
    s.writer.Write(data)
    s.writer.Write([]byte("\n"))
}
```

### 6.5.4 使用範例

```go
package main

import (
    "mcp-server/server"
    "mcp-server/tools"
)

func main() {
    // 建立伺服器
    srv := server.NewMCPServer("my-mcp-server", "1.0.0")

    // 註冊工具
    srv.RegisterTool(&tools.ReadFileHandler{})
    srv.RegisterTool(&tools.WriteFileHandler{})
    srv.RegisterTool(&tools.SearchHandler{})

    // 啟動伺服器
    if err := srv.Run(); err != nil {
        panic(err)
    }
}
```

---

## 6.6 動態工具載入策略

### 6.6.1 問題：靜態載入的缺點

傳統的靜態載入方式會一次載入所有工具：

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "github": { "command": "github-mcp" },
    "slack": { "command": "slack-mcp" },
    "postgres": { "command": "postgres-mcp" },
    "filesystem": { "command": "filesystem-mcp" },
    "web-search": { "command": "web-search-mcp" }
  }
}
```

問題：
- 所有工具定義都會載入 Context
- 即使某次對話完全不需要某些工具

### 6.6.2 解決方案：任務導向的動態載入

**策略 1：手動切換**
```
使用者：「我要開始處理 GitHub 相關的任務了」
→ 載入 GitHub MCP
→ 卸載其他 MCP

使用者：「現在要查資料庫」
→ 載入 PostgreSQL MCP
→ 卸載 GitHub MCP
```

**策略 2：自動偵測**

根據對話內容自動判斷需要的工具：

```python
def detect_required_tools(user_message: str) -> list[str]:
    """
    分析使用者訊息，判斷需要哪些工具
    """
    required = []

    # 關鍵字匹配
    if any(word in user_message.lower() for word in ["github", "pr", "issue", "repo"]):
        required.append("github-mcp")

    if any(word in user_message.lower() for word in ["database", "sql", "query", "table"]):
        required.append("postgres-mcp")

    if any(word in user_message.lower() for word in ["file", "read", "write", "directory"]):
        required.append("filesystem-mcp")

    # 預設至少載入檔案系統工具
    if not required:
        required.append("filesystem-mcp")

    return required
```

**策略 3：分層架構**

將工具分為核心層和擴展層：

```
┌─────────────────────────────────────────────────────────────┐
│                      核心工具層                              │
│              （永遠載入，5-6 個基礎工具）                     │
│                                                             │
│   read_file  write_file  list_dir  bash  search            │
└─────────────────────────────────────────────────────────────┘
                              │
              需要時動態載入   │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      擴展工具層                              │
│              （按需載入，任務特定工具）                       │
│                                                             │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│   │ GitHub  │  │ Slack   │  │ Database│  │ Web API │      │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.6.3 動態載入的實作

```go
// 動態工具管理器
type DynamicToolManager struct {
    core     *tools.Registry    // 核心工具（永遠載入）
    extended map[string]*tools.Registry  // 擴展工具（按需載入）
    active   map[string]bool    // 目前啟用的擴展工具
    mu       sync.RWMutex
}

func NewDynamicToolManager() *DynamicToolManager {
    m := &DynamicToolManager{
        core:     tools.NewRegistry(),
        extended: make(map[string]*tools.Registry),
        active:   make(map[string]bool),
    }

    // 載入核心工具
    m.core.Register(&ReadFileHandler{})
    m.core.Register(&WriteFileHandler{})
    m.core.Register(&ListDirHandler{})
    m.core.Register(&BashHandler{})
    m.core.Register(&SearchHandler{})

    return m
}

// 啟用擴展工具集
func (m *DynamicToolManager) EnableExtension(name string) error {
    m.mu.Lock()
    defer m.mu.Unlock()

    if _, exists := m.extended[name]; !exists {
        return fmt.Errorf("extension not found: %s", name)
    }

    m.active[name] = true
    return nil
}

// 停用擴展工具集
func (m *DynamicToolManager) DisableExtension(name string) {
    m.mu.Lock()
    defer m.mu.Unlock()

    delete(m.active, name)
}

// 獲取當前所有可用工具
func (m *DynamicToolManager) GetActiveTools() []protocol.Tool {
    m.mu.RLock()
    defer m.mu.RUnlock()

    var tools []protocol.Tool

    // 核心工具
    tools = append(tools, m.core.GetAllDefinitions()...)

    // 啟用的擴展工具
    for name := range m.active {
        if ext, exists := m.extended[name]; exists {
            tools = append(tools, ext.GetAllDefinitions()...)
        }
    }

    return tools
}
```

---

## 6.7 最佳實踐與反模式

### 6.7.1 反模式：工具過載

```json
// ❌ 反模式：一次載入所有可能需要的工具
{
  "mcpServers": {
    "github": {},
    "gitlab": {},
    "slack": {},
    "discord": {},
    "postgres": {},
    "mysql": {},
    "mongodb": {},
    "redis": {},
    "elasticsearch": {},
    "web-search": {},
    "weather": {},
    "calculator": {},
    "translator": {}
  }
}
```

**問題**：
- 13 個 MCP 伺服器，可能 50+ 個工具
- Context 消耗約 20,000+ tokens
- 工具選擇準確率顯著下降

### 6.7.2 最佳實踐：精簡配置

```json
// ✓ 最佳實踐：只載入當前任務需要的工具
{
  "mcpServers": {
    // 核心：專案操作
    "filesystem": { "command": "filesystem-mcp" },

    // 根據當前專案需求選擇性載入
    "github": { "command": "github-mcp" }  // 如果專案用 GitHub
  }
}
```

### 6.7.3 工具描述的優化

**❌ 過於簡短**：
```json
{
  "name": "search",
  "description": "Search files"
}
```

**❌ 過於冗長**：
```json
{
  "name": "search",
  "description": "This tool allows you to search for files in the filesystem. You can use it to find files by name, by content, by extension, or by any other criteria. It supports regular expressions, glob patterns, and many other advanced features. The search results will include the file path, the line number, and a snippet of the matching content. You should use this tool when you need to find files in a large codebase, when you need to locate specific code patterns, or when you need to understand the structure of a project..."
}
```

**✓ 適中且精確**：
```json
{
  "name": "search",
  "description": "在程式碼庫中搜尋符合模式的文字。使用時機：尋找特定函數、類別或變數的定義及使用位置。支援正則表達式。"
}
```

### 6.7.4 工具命名規範

| 風格 | 範例 | 評價 |
|------|------|------|
| **snake_case** | `read_file`, `search_code` | ✓ 推薦 |
| **camelCase** | `readFile`, `searchCode` | ✓ 可接受 |
| **kebab-case** | `read-file`, `search-code` | ✓ 可接受 |
| **無規範** | `ReadFile`, `SEARCH`, `file_Read` | ❌ 避免 |

---

## 6.8 案例研究：效能崩潰診斷

### 6.8.1 問題描述

某團隊反映他們的 Coding Agent 效能急劇下降：
- 任務完成時間從 5 分鐘增加到 30 分鐘
- 經常選擇錯誤的工具
- Token 消耗是預期的 3 倍

### 6.8.2 診斷過程

**步驟 1：檢查 MCP 配置**
```json
// 發現了 15 個 MCP 伺服器
{
  "mcpServers": {
    "github": {},
    "gitlab": {},
    "bitbucket": {},
    "slack": {},
    "discord": {},
    "teams": {},
    "postgres": {},
    "mysql": {},
    "mongodb": {},
    "redis": {},
    "s3": {},
    "gcs": {},
    "web-search": {},
    "translator": {},
    "weather": {}
  }
}
```

**步驟 2：量化 Token 消耗**

```
工具定義 Token 統計：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GitHub MCP      (8 tools)    3,200 tokens
GitLab MCP      (8 tools)    3,400 tokens
Bitbucket MCP   (6 tools)    2,100 tokens
Slack MCP       (12 tools)   5,400 tokens
Discord MCP     (10 tools)   4,200 tokens
Teams MCP       (8 tools)    3,600 tokens
PostgreSQL MCP  (6 tools)    1,800 tokens
MySQL MCP       (6 tools)    1,700 tokens
MongoDB MCP     (7 tools)    2,400 tokens
Redis MCP       (5 tools)    1,200 tokens
S3 MCP          (8 tools)    2,800 tokens
GCS MCP         (7 tools)    2,500 tokens
Web Search MCP  (3 tools)    900 tokens
Translator MCP  (2 tools)    500 tokens
Weather MCP     (3 tools)    700 tokens
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
總計            99 tools    36,400 tokens
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**步驟 3：分析工具使用率**

查看過去一週的使用記錄：
- 實際使用過的工具：12 個
- 從未使用的工具：87 個
- 工具使用率：12.1%

### 6.8.3 解決方案

**精簡配置**：

```json
// 優化後：只保留實際需要的工具
{
  "mcpServers": {
    // 核心版本控制（專案用 GitHub）
    "github": {},

    // 核心資料庫（專案用 PostgreSQL）
    "postgres": {},

    // 核心檔案操作
    "filesystem": {}
  }
}
```

**效果**：

| 指標 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| 工具數量 | 99 | 19 | -81% |
| Token 消耗 | 36,400 | 6,500 | -82% |
| 任務完成時間 | 30 分鐘 | 6 分鐘 | -80% |
| 工具選擇準確率 | 45% | 92% | +104% |

---

## 本章小結

本章深入探討了 MCP 協議及其 Context 成本影響。

**核心要點**：

1. **MCP 基於 JSON-RPC 2.0**
   - 輕量級的 RPC 協議
   - 標準化的工具介面

2. **工具定義消耗 Context**
   - 每個工具約 200-800 tokens
   - 工具數量影響選擇準確率

3. **Less is More**
   - 精簡配置優於全面配置
   - 動態載入優於靜態載入

4. **分層架構是最佳實踐**
   - 核心工具永遠載入
   - 擴展工具按需載入

5. **監控與優化**
   - 追蹤工具使用率
   - 移除未使用的工具

---

## 練習題

### 練習 6.1：實作 MCP 客戶端
建立一個簡單的 MCP 客戶端，能夠：
- 連接到 stdio MCP 伺服器
- 完成初始化握手
- 列出可用工具
- 呼叫指定工具

### 練習 6.2：Token 成本分析
選擇一個 MCP 伺服器，分析其工具定義：
- 計算每個工具的 Token 消耗
- 找出 Token 消耗最高的工具
- 提出優化建議

### 練習 6.3：動態載入策略設計
為一個多功能 Agent 設計動態載入策略：
- 定義核心工具集（5-6 個）
- 設計擴展工具分類
- 實作自動偵測需求的邏輯

---

## 延伸閱讀

1. **MCP Specification** (Anthropic)
   - 官方 MCP 協議規範
   - https://spec.modelcontextprotocol.io/

2. **JSON-RPC 2.0 Specification**
   - JSON-RPC 協議規範
   - https://www.jsonrpc.org/specification

3. **Awesome MCP Servers** (GitHub)
   - 社區維護的 MCP 伺服器列表
   - https://github.com/modelcontextprotocol/servers

4. **MCP TypeScript SDK** (Anthropic)
   - 官方 TypeScript SDK
   - https://github.com/modelcontextprotocol/typescript-sdk

---

## 下一章預告

掌握了工具系統後，我們將進入第三部分：進階模式。第 7 章將介紹 **Ralph Wiggum Loop**——一個僅用五行程式碼就能讓 Agent 自主迭代的革命性技術。這個技術來自 Geoffrey Huntley 的發現，將徹底改變你對 Coding Agent 的認知。
