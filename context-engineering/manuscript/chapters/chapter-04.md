# 第 4 章：推論迴圈的解剖學

> 「Agent 不是什麼神秘的東西，它就是一個跑在 while true 裡面的 API 呼叫。」
> — Geoffrey Huntley

---

## 本章學習目標

完成本章後，你將能夠：

- 詳細描述 Coding Agent 推論迴圈的每個階段
- 理解 HTTP 協議層級的 API 呼叫細節
- 比較 Streaming 與 Non-streaming 的實作差異
- 運用狀態機設計模式建模 Agent 行為
- 使用 Go 語言從零建構一個完整的聊天介面
- 實作工具註冊、呼叫、結果分配的完整流程

---

## 4.1 推論迴圈：Agent 的心跳

每一個 Coding Agent 的核心都是一個**推論迴圈**（Inference Loop）。這個迴圈不斷重複「思考→行動→觀察」的循環，直到任務完成或達到終止條件。

### 4.1.1 迴圈的五個階段

```
┌──────────────────────────────────────────────────────────────────┐
│                        推論迴圈                                   │
│                                                                  │
│    ┌──────────────────────────────────────────────────────┐     │
│    │                    Context 累積                       │     │
│    │  [System] + [User₁] + [Asst₁] + [Tool₁] + [Asst₂]... │     │
│    └────────────────────────┬─────────────────────────────┘     │
│                             │                                    │
│                             ▼                                    │
│    ┌─────────────────────────────────────────────────────┐      │
│    │              階段 1：輸入組裝                         │      │
│    │  • 系統提示詞（Harness Prompt）                      │      │
│    │  • 對話歷史                                          │      │
│    │  • 工具定義                                          │      │
│    └────────────────────────┬────────────────────────────┘      │
│                             │                                    │
│                             ▼                                    │
│    ┌─────────────────────────────────────────────────────┐      │
│    │              階段 2：API 推論                         │      │
│    │  • HTTP POST 到 /v1/messages                        │      │
│    │  • 等待模型生成回應                                   │      │
│    └────────────────────────┬────────────────────────────┘      │
│                             │                                    │
│                             ▼                                    │
│    ┌─────────────────────────────────────────────────────┐      │
│    │              階段 3：回應解析                         │      │
│    │  • 檢查 stop_reason                                 │      │
│    │  • 識別是否有工具呼叫                                │      │
│    └────────────────────────┬────────────────────────────┘      │
│                             │                                    │
│              ┌──────────────┴──────────────┐                    │
│              │                             │                    │
│              ▼                             ▼                    │
│    ┌─────────────────┐         ┌─────────────────────────┐      │
│    │ stop_reason:    │         │ stop_reason:            │      │
│    │ "end_turn"      │         │ "tool_use"              │      │
│    │                 │         │                         │      │
│    │ → 輸出結果      │         │ → 階段 4：執行工具       │      │
│    │ → 結束迴圈      │         │ → 階段 5：結果分配       │      │
│    └─────────────────┘         │ → 返回階段 1            │      │
│                                └─────────────────────────┘      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.1.2 為何是「迴圈」而非「單次呼叫」？

傳統的 LLM 應用（如聊天機器人）通常是「一問一答」：

```
使用者 → API → 回應 → 使用者
```

但 Coding Agent 需要**自主決策**——模型必須能夠：
1. 決定需要什麼資訊
2. 呼叫工具獲取資訊
3. 根據結果決定下一步
4. 重複直到任務完成

這就產生了迴圈結構：

```
使用者 → API → 工具呼叫 → 執行 → 結果 → API → 工具呼叫 → ... → 最終回應 → 使用者
```

### 4.1.3 迴圈終止條件

推論迴圈不能無限運行，需要明確的終止條件：

| 終止原因 | 說明 | 處理方式 |
|----------|------|----------|
| `end_turn` | 模型認為任務完成 | 輸出最終回應 |
| `max_tokens` | 達到 token 上限 | 可能需要繼續 |
| `tool_use` | 需要工具呼叫 | 執行工具，繼續迴圈 |
| 迭代上限 | 達到最大迴圈次數 | 強制終止，返回錯誤 |
| 錯誤累積 | 連續錯誤過多 | 終止並報告問題 |

---

## 4.2 HTTP 協議層級的 API 呼叫

要真正理解推論迴圈，我們需要深入到 HTTP 協議層級。

### 4.2.1 API 請求結構

Claude API 的訊息端點使用標準的 HTTP POST：

```http
POST /v1/messages HTTP/1.1
Host: api.anthropic.com
Content-Type: application/json
X-API-Key: sk-ant-api03-...
anthropic-version: 2023-06-01

{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 4096,
  "system": "你是一個專業的程式碼助手...",
  "messages": [
    {"role": "user", "content": "幫我讀取 main.go 的內容"}
  ],
  "tools": [
    {
      "name": "read_file",
      "description": "讀取指定路徑的檔案內容",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "檔案路徑"}
        },
        "required": ["path"]
      }
    }
  ]
}
```

### 4.2.2 API 回應結構

回應包含模型的輸出以及元資訊：

```json
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "我來讀取 main.go 的內容。"
    },
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lhl",
      "name": "read_file",
      "input": {
        "path": "main.go"
      }
    }
  ],
  "model": "claude-sonnet-4-20250514",
  "stop_reason": "tool_use",
  "usage": {
    "input_tokens": 512,
    "output_tokens": 89
  }
}
```

### 4.2.3 工具結果的回傳

執行工具後，需要將結果以特定格式回傳：

```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 4096,
  "messages": [
    {"role": "user", "content": "幫我讀取 main.go 的內容"},
    {
      "role": "assistant",
      "content": [
        {"type": "text", "text": "我來讀取 main.go 的內容。"},
        {
          "type": "tool_use",
          "id": "toolu_01A09q90qw90lq917835lhl",
          "name": "read_file",
          "input": {"path": "main.go"}
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_01A09q90qw90lq917835lhl",
          "content": "package main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"Hello, World!\")\n}"
        }
      ]
    }
  ]
}
```

**關鍵觀察**：
- `tool_result` 的 `tool_use_id` 必須匹配原本的工具呼叫
- 工具結果以 `user` 角色發送（這是 API 的設計）
- 整個對話歷史需要完整保留

---

## 4.3 Streaming vs Non-streaming

API 支援兩種回應模式，各有適用場景。

### 4.3.1 Non-streaming（同步模式）

等待整個回應生成完成後一次返回：

```
┌─────────┐      請求       ┌─────────┐
│ Client  │ ────────────── │  API    │
│         │                │         │
│         │   等待 3-10 秒  │ 生成中... │
│         │                │         │
│         │ ◄───────────── │         │
└─────────┘    完整回應     └─────────┘
```

**優點**：
- 實作簡單
- 回應完整、易於處理

**缺點**：
- 使用者需要長時間等待
- 無法即時顯示進度

### 4.3.2 Streaming（串流模式）

使用 Server-Sent Events (SSE) 即時傳輸：

```
┌─────────┐      請求       ┌─────────┐
│ Client  │ ─────────────► │  API    │
│         │                │         │
│         │ ◄── event 1 ── │         │
│         │ ◄── event 2 ── │ 逐步    │
│         │ ◄── event 3 ── │ 生成    │
│         │ ◄── ...     ── │         │
│         │ ◄── [DONE]  ── │         │
└─────────┘                └─────────┘
```

**SSE 事件格式**：

```
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"我來"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"讀取"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"這個"}}

event: message_stop
data: {"type":"message_stop"}
```

### 4.3.3 Streaming 的事件類型

Claude API 的 streaming 包含以下事件：

| 事件類型 | 說明 | 用途 |
|----------|------|------|
| `message_start` | 訊息開始 | 獲取 message ID |
| `content_block_start` | 內容區塊開始 | 識別文字或工具呼叫 |
| `content_block_delta` | 內容增量 | 即時顯示文字 |
| `content_block_stop` | 內容區塊結束 | 標記區塊完成 |
| `message_delta` | 訊息增量 | 獲取 stop_reason |
| `message_stop` | 訊息結束 | 結束處理 |

### 4.3.4 何時選擇哪種模式？

| 場景 | 推薦模式 | 原因 |
|------|----------|------|
| CLI 互動介面 | Streaming | 使用者需要即時回饋 |
| 批次處理 | Non-streaming | 無需即時顯示 |
| Web UI | Streaming | 使用者體驗 |
| 工具密集任務 | Non-streaming | 工具呼叫頻繁時開銷較小 |

---

## 4.4 狀態機設計模式

推論迴圈可以用**有限狀態機**（Finite State Machine, FSM）來建模，這是一種經典的軟體設計模式。

### 4.4.1 狀態機的學術背景

有限狀態機由以下元素組成：
- **狀態集合** $S = \{s_1, s_2, ..., s_n\}$
- **輸入集合** $\Sigma$
- **轉移函數** $\delta: S \times \Sigma \rightarrow S$
- **初始狀態** $s_0 \in S$
- **終止狀態** $F \subseteq S$

對於推論迴圈，我們可以定義：

```
S = {Idle, WaitingResponse, ProcessingToolCall, ExecutingTool, Done, Error}
```

### 4.4.2 Agent 狀態轉移圖

```
                    ┌──────────────────────────────────────┐
                    │                                      │
                    │                                      ▼
┌─────────┐  使用者輸入  ┌──────────────────┐  API 回應   ┌─────────────────┐
│  Idle   │ ─────────► │ WaitingResponse  │ ─────────► │ ProcessingResp  │
└─────────┘            └──────────────────┘            └────────┬────────┘
     ▲                                                         │
     │                                                         │
     │                    ┌────────────────────────────────────┤
     │                    │                                    │
     │                    │ stop_reason = "end_turn"           │ stop_reason = "tool_use"
     │                    ▼                                    ▼
     │             ┌─────────┐                        ┌────────────────┐
     │             │  Done   │                        │ ExecutingTool  │
     │             └─────────┘                        └────────┬───────┘
     │                                                         │
     │                                                         │ 工具完成
     └─────────────────────────────────────────────────────────┘
```

### 4.4.3 狀態機的程式碼實現

```go
// ‹1› 定義 Agent 狀態
type AgentState int

const (
    StateIdle AgentState = iota      // 等待使用者輸入
    StateWaitingResponse             // 等待 API 回應
    StateProcessingResponse          // 處理回應中
    StateExecutingTool               // 執行工具中
    StateDone                        // 任務完成
    StateError                       // 發生錯誤
)

// ‹2› 狀態轉移事件
type Event int

const (
    EventUserInput Event = iota      // 使用者輸入
    EventAPIResponse                 // 收到 API 回應
    EventToolCall                    // 需要工具呼叫
    EventToolComplete                // 工具執行完成
    EventEndTurn                     // 模型結束回合
    EventError                       // 發生錯誤
)

// ‹3› 狀態機結構
type AgentStateMachine struct {
    currentState AgentState
    transitions  map[AgentState]map[Event]AgentState
}

// ‹4› 初始化狀態轉移表
func NewAgentStateMachine() *AgentStateMachine {
    sm := &AgentStateMachine{
        currentState: StateIdle,
        transitions:  make(map[AgentState]map[Event]AgentState),
    }

    // 定義合法的狀態轉移
    sm.transitions[StateIdle] = map[Event]AgentState{
        EventUserInput: StateWaitingResponse,
    }
    sm.transitions[StateWaitingResponse] = map[Event]AgentState{
        EventAPIResponse: StateProcessingResponse,
        EventError:       StateError,
    }
    sm.transitions[StateProcessingResponse] = map[Event]AgentState{
        EventToolCall: StateExecutingTool,
        EventEndTurn:  StateDone,
        EventError:    StateError,
    }
    sm.transitions[StateExecutingTool] = map[Event]AgentState{
        EventToolComplete: StateWaitingResponse,
        EventError:        StateError,
    }

    return sm
}

// ‹5› 狀態轉移函數
func (sm *AgentStateMachine) Transition(event Event) error {
    if transitions, ok := sm.transitions[sm.currentState]; ok {
        if nextState, ok := transitions[event]; ok {
            sm.currentState = nextState
            return nil
        }
    }
    return fmt.Errorf("invalid transition: state=%d, event=%d",
        sm.currentState, event)
}
```

---

## 4.5 Harness Prompt 的結構

**Harness Prompt**（駕馭提示詞）是包裝 LLM 的系統提示詞，它決定了 Agent 的「人格」和行為模式。

### 4.5.1 五個核心組件

```
┌─────────────────────────────────────────────────────────────┐
│                    Harness Prompt 結構                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. 角色定義（Identity）                              │   │
│  │     • 你是誰                                         │   │
│  │     • 你的專長                                       │   │
│  │     • 你的目標                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  2. 能力範圍（Capabilities）                          │   │
│  │     • 你能做什麼                                     │   │
│  │     • 你不能做什麼                                   │   │
│  │     • 可用的工具清單                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  3. 行為準則（Guidelines）                            │   │
│  │     • 如何處理不確定性                               │   │
│  │     • 錯誤處理策略                                   │   │
│  │     • 安全邊界                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  4. 輸出格式（Output Format）                         │   │
│  │     • 回應的結構                                     │   │
│  │     • 程式碼區塊格式                                 │   │
│  │     • 特殊標記使用                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  5. 工具使用指引（Tool Usage）                        │   │
│  │     • 何時使用哪個工具                               │   │
│  │     • 工具組合策略                                   │   │
│  │     • 失敗時的替代方案                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.5.2 範例 Harness Prompt

```markdown
# 角色定義
你是一個專業的 Coding Agent，專精於 Go 語言開發。你的目標是幫助開發者完成程式設計任務，包括撰寫程式碼、除錯、重構和文件撰寫。

# 能力範圍
你可以：
- 讀取和分析專案中的檔案
- 搜尋程式碼庫中的特定模式
- 執行 shell 命令（需謹慎）
- 編輯現有檔案
- 建立新檔案

你不可以：
- 刪除使用者的檔案（除非明確要求）
- 執行可能造成不可逆傷害的命令
- 存取網路資源

# 行為準則
1. 在修改檔案之前，先讀取現有內容以了解上下文
2. 每次只進行必要的最小修改
3. 對於破壞性操作，先確認使用者意圖
4. 遇到錯誤時，嘗試替代方案而非直接放棄

# 輸出格式
- 程式碼使用 markdown 程式碼區塊
- 解釋保持簡潔，重點說明「為什麼」
- 修改後顯示相關的變更摘要

# 工具使用策略
- 搜尋時優先使用 grep，再用 glob 確認檔案位置
- 編輯前先 read 確認內容
- 批量操作前先在單一檔案測試
```

### 4.5.3 Harness Prompt 的設計原則

**原則 1：明確優於模糊**
```
❌ 「小心處理檔案」
✓ 「在刪除檔案前，先列出要刪除的檔案清單並等待確認」
```

**原則 2：正面指示優於負面禁止**
```
❌ 「不要一次修改太多檔案」
✓ 「每次最多修改 3 個檔案，確認結果後再繼續」
```

**原則 3：提供具體範例**
```
✓ 「當遇到編譯錯誤時，例如 'undefined variable'，
   先搜尋該變數的定義位置，再分析是否為拼寫錯誤或作用域問題」
```

---

## 4.6 工具註冊機制

讓 LLM 能夠「看見」並使用你的函數，需要精確的工具定義。

### 4.6.1 JSON Schema 基礎

工具的參數使用 JSON Schema 定義，這是一個描述 JSON 資料結構的標準：

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "要讀取的檔案路徑，相對於專案根目錄"
    },
    "encoding": {
      "type": "string",
      "enum": ["utf-8", "ascii", "latin-1"],
      "default": "utf-8",
      "description": "檔案編碼格式"
    }
  },
  "required": ["path"]
}
```

### 4.6.2 工具定義的最佳實踐

**1. 名稱要直觀**
```json
✓ "read_file", "search_code", "run_test"
❌ "rf", "sc", "exec1"
```

**2. 描述要告訴 LLM「何時」使用**
```json
{
  "name": "read_file",
  "description": "讀取指定檔案的內容。當你需要查看檔案內容、理解程式碼結構、或在修改前確認現有內容時，使用此工具。支援文字檔案，二進位檔案會返回錯誤。"
}
```

**3. 參數描述要精確**
```json
{
  "properties": {
    "pattern": {
      "type": "string",
      "description": "正則表達式搜尋模式。例如：'func.*Test' 會匹配所有測試函數定義。注意：需要跳脫特殊字元。"
    }
  }
}
```

### 4.6.3 Go 語言的工具註冊實現

```go
// ‹1› 工具定義結構
type ToolDefinition struct {
    Name        string                 `json:"name"`
    Description string                 `json:"description"`
    InputSchema map[string]interface{} `json:"input_schema"`
}

// ‹2› 工具處理器介面
type ToolHandler interface {
    Execute(input map[string]interface{}) (string, error)
    GetDefinition() ToolDefinition
}

// ‹3› 工具註冊表
type ToolRegistry struct {
    handlers map[string]ToolHandler
}

func NewToolRegistry() *ToolRegistry {
    return &ToolRegistry{
        handlers: make(map[string]ToolHandler),
    }
}

// ‹4› 註冊工具
func (r *ToolRegistry) Register(handler ToolHandler) {
    def := handler.GetDefinition()
    r.handlers[def.Name] = handler
}

// ‹5› 獲取所有工具定義（用於 API 請求）
func (r *ToolRegistry) GetDefinitions() []ToolDefinition {
    defs := make([]ToolDefinition, 0, len(r.handlers))
    for _, handler := range r.handlers {
        defs = append(defs, handler.GetDefinition())
    }
    return defs
}

// ‹6› 執行工具
func (r *ToolRegistry) Execute(name string, input map[string]interface{}) (string, error) {
    handler, ok := r.handlers[name]
    if !ok {
        return "", fmt.Errorf("unknown tool: %s", name)
    }
    return handler.Execute(input)
}
```

---

## 4.7 完整實作：Go 語言聊天介面

現在讓我們將所有概念整合，建構一個完整的 Coding Agent。

### 4.7.1 專案結構

```
coding-agent/
├── main.go              # 程式入口
├── agent/
│   ├── agent.go         # Agent 核心邏輯
│   ├── state.go         # 狀態機
│   └── types.go         # 型別定義
├── tools/
│   ├── registry.go      # 工具註冊表
│   ├── read_file.go     # 讀取檔案工具
│   └── bash.go          # 執行命令工具
└── client/
    └── claude.go        # Claude API 客戶端
```

### 4.7.2 API 客戶端實現

```go
package client

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
)

// ‹1› API 客戶端結構
type ClaudeClient struct {
    apiKey     string
    baseURL    string
    httpClient *http.Client
}

// ‹2› 訊息請求結構
type MessageRequest struct {
    Model     string    `json:"model"`
    MaxTokens int       `json:"max_tokens"`
    System    string    `json:"system,omitempty"`
    Messages  []Message `json:"messages"`
    Tools     []Tool    `json:"tools,omitempty"`
}

type Message struct {
    Role    string        `json:"role"`
    Content []ContentBlock `json:"content"`
}

type ContentBlock struct {
    Type      string                 `json:"type"`
    Text      string                 `json:"text,omitempty"`
    ID        string                 `json:"id,omitempty"`
    Name      string                 `json:"name,omitempty"`
    Input     map[string]interface{} `json:"input,omitempty"`
    ToolUseID string                 `json:"tool_use_id,omitempty"`
    Content   string                 `json:"content,omitempty"`
}

// ‹3› 訊息回應結構
type MessageResponse struct {
    ID         string         `json:"id"`
    Type       string         `json:"type"`
    Role       string         `json:"role"`
    Content    []ContentBlock `json:"content"`
    Model      string         `json:"model"`
    StopReason string         `json:"stop_reason"`
    Usage      Usage          `json:"usage"`
}

type Usage struct {
    InputTokens  int `json:"input_tokens"`
    OutputTokens int `json:"output_tokens"`
}

// ‹4› 建立客戶端
func NewClaudeClient(apiKey string) *ClaudeClient {
    return &ClaudeClient{
        apiKey:     apiKey,
        baseURL:    "https://api.anthropic.com",
        httpClient: &http.Client{},
    }
}

// ‹5› 發送訊息
func (c *ClaudeClient) CreateMessage(req MessageRequest) (*MessageResponse, error) {
    // 序列化請求
    body, err := json.Marshal(req)
    if err != nil {
        return nil, fmt.Errorf("marshal request: %w", err)
    }

    // 建立 HTTP 請求
    httpReq, err := http.NewRequest("POST", c.baseURL+"/v1/messages", bytes.NewReader(body))
    if err != nil {
        return nil, fmt.Errorf("create request: %w", err)
    }

    // 設定標頭
    httpReq.Header.Set("Content-Type", "application/json")
    httpReq.Header.Set("X-API-Key", c.apiKey)
    httpReq.Header.Set("anthropic-version", "2023-06-01")

    // 發送請求
    resp, err := c.httpClient.Do(httpReq)
    if err != nil {
        return nil, fmt.Errorf("send request: %w", err)
    }
    defer resp.Body.Close()

    // 讀取回應
    respBody, err := io.ReadAll(resp.Body)
    if err != nil {
        return nil, fmt.Errorf("read response: %w", err)
    }

    // 檢查狀態碼
    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("API error (status %d): %s", resp.StatusCode, respBody)
    }

    // 解析回應
    var msgResp MessageResponse
    if err := json.Unmarshal(respBody, &msgResp); err != nil {
        return nil, fmt.Errorf("unmarshal response: %w", err)
    }

    return &msgResp, nil
}
```

### 4.7.3 Agent 核心邏輯

```go
package agent

import (
    "fmt"
    "coding-agent/client"
    "coding-agent/tools"
)

// ‹1› Agent 結構
type Agent struct {
    client    *client.ClaudeClient
    registry  *tools.ToolRegistry
    state     *StateMachine
    messages  []client.Message
    system    string
    maxTurns  int
}

// ‹2› 建立 Agent
func NewAgent(apiKey string, system string) *Agent {
    agent := &Agent{
        client:   client.NewClaudeClient(apiKey),
        registry: tools.NewToolRegistry(),
        state:    NewStateMachine(),
        messages: make([]client.Message, 0),
        system:   system,
        maxTurns: 50, // 最大迭代次數
    }

    // 註冊預設工具
    agent.registry.Register(&tools.ReadFileHandler{})
    agent.registry.Register(&tools.BashHandler{})

    return agent
}

// ‹3› 處理使用者輸入（推論迴圈入口）
func (a *Agent) Run(userInput string) (string, error) {
    // 加入使用者訊息
    a.messages = append(a.messages, client.Message{
        Role: "user",
        Content: []client.ContentBlock{
            {Type: "text", Text: userInput},
        },
    })

    // 開始推論迴圈
    turn := 0
    for turn < a.maxTurns {
        turn++

        // ‹4› 呼叫 API
        resp, err := a.client.CreateMessage(client.MessageRequest{
            Model:     "claude-sonnet-4-20250514",
            MaxTokens: 4096,
            System:    a.system,
            Messages:  a.messages,
            Tools:     a.registry.GetDefinitions(),
        })
        if err != nil {
            return "", fmt.Errorf("API call failed: %w", err)
        }

        // 加入助手回應到歷史
        a.messages = append(a.messages, client.Message{
            Role:    "assistant",
            Content: resp.Content,
        })

        // ‹5› 檢查終止條件
        if resp.StopReason == "end_turn" {
            // 提取最終文字回應
            return a.extractTextResponse(resp.Content), nil
        }

        // ‹6› 處理工具呼叫
        if resp.StopReason == "tool_use" {
            toolResults := a.executeTools(resp.Content)
            a.messages = append(a.messages, client.Message{
                Role:    "user",
                Content: toolResults,
            })
            continue // 繼續迴圈
        }

        // 其他終止原因
        return "", fmt.Errorf("unexpected stop reason: %s", resp.StopReason)
    }

    return "", fmt.Errorf("exceeded maximum turns (%d)", a.maxTurns)
}

// ‹7› 執行工具呼叫
func (a *Agent) executeTools(content []client.ContentBlock) []client.ContentBlock {
    results := make([]client.ContentBlock, 0)

    for _, block := range content {
        if block.Type != "tool_use" {
            continue
        }

        // 執行工具
        result, err := a.registry.Execute(block.Name, block.Input)
        if err != nil {
            result = fmt.Sprintf("Error: %v", err)
        }

        // 建立工具結果
        results = append(results, client.ContentBlock{
            Type:      "tool_result",
            ToolUseID: block.ID,
            Content:   result,
        })
    }

    return results
}

// ‹8› 提取文字回應
func (a *Agent) extractTextResponse(content []client.ContentBlock) string {
    for _, block := range content {
        if block.Type == "text" {
            return block.Text
        }
    }
    return ""
}
```

### 4.7.4 主程式

```go
package main

import (
    "bufio"
    "fmt"
    "os"
    "strings"
    "coding-agent/agent"
)

func main() {
    // 從環境變數讀取 API Key
    apiKey := os.Getenv("ANTHROPIC_API_KEY")
    if apiKey == "" {
        fmt.Println("Error: ANTHROPIC_API_KEY not set")
        os.Exit(1)
    }

    // 建立 Agent
    system := `你是一個專業的 Coding Agent。
你可以讀取檔案和執行 shell 命令來幫助使用者完成程式設計任務。
在執行任何修改之前，先確認你理解了任務需求。`

    a := agent.NewAgent(apiKey, system)

    // 互動式介面
    reader := bufio.NewReader(os.Stdin)
    fmt.Println("Coding Agent 已啟動。輸入 'exit' 離開。")
    fmt.Println("─────────────────────────────────────────")

    for {
        fmt.Print("\n你: ")
        input, _ := reader.ReadString('\n')
        input = strings.TrimSpace(input)

        if input == "exit" {
            break
        }

        if input == "" {
            continue
        }

        // 執行 Agent
        response, err := a.Run(input)
        if err != nil {
            fmt.Printf("\n錯誤: %v\n", err)
            continue
        }

        fmt.Printf("\nAgent: %s\n", response)
    }
}
```

---

## 4.8 錯誤處理與恢復

健壯的 Agent 需要優雅地處理各種錯誤情況。

### 4.8.1 錯誤分類

| 錯誤類型 | 範例 | 處理策略 |
|----------|------|----------|
| **可重試錯誤** | API 超時、速率限制 | 指數退避重試 |
| **工具錯誤** | 檔案不存在、權限不足 | 將錯誤傳回 LLM |
| **模型錯誤** | 輸出格式錯誤 | 嘗試修復或重新請求 |
| **致命錯誤** | API Key 無效 | 終止並報告 |

### 4.8.2 重試策略

```go
// 指數退避重試
func (c *ClaudeClient) CreateMessageWithRetry(req MessageRequest) (*MessageResponse, error) {
    maxRetries := 3
    baseDelay := time.Second

    for attempt := 0; attempt < maxRetries; attempt++ {
        resp, err := c.CreateMessage(req)
        if err == nil {
            return resp, nil
        }

        // 檢查是否為可重試錯誤
        if !isRetryable(err) {
            return nil, err
        }

        // 計算延遲時間（指數退避）
        delay := baseDelay * time.Duration(1<<attempt)
        time.Sleep(delay)
    }

    return nil, fmt.Errorf("exceeded max retries")
}

func isRetryable(err error) bool {
    // 速率限制、超時等錯誤是可重試的
    // API Key 錯誤、格式錯誤不可重試
    // ...
}
```

### 4.8.3 工具錯誤的傳遞

當工具執行失敗時，不應該讓 Agent 崩潰，而是將錯誤訊息傳回給模型：

```go
result, err := a.registry.Execute(block.Name, block.Input)
if err != nil {
    // 將錯誤作為工具結果傳回
    result = fmt.Sprintf("工具執行錯誤：%v\n\n請考慮：\n1. 檢查參數是否正確\n2. 嘗試替代方案", err)
}
```

這讓模型有機會根據錯誤訊息調整策略，而不是盲目重試。

---

## 本章小結

本章深入解剖了 Coding Agent 的核心——推論迴圈。

**核心要點**：

1. **推論迴圈是 Agent 的心跳**
   - 不斷循環「輸入→推論→工具呼叫→結果→再推論」
   - 直到模型認為任務完成

2. **HTTP 協議層級的理解很重要**
   - API 請求和回應的結構
   - 工具呼叫和結果的格式

3. **Streaming 提升使用者體驗**
   - SSE 事件流的處理
   - 即時顯示生成內容

4. **狀態機是良好的建模工具**
   - 清晰的狀態定義
   - 明確的轉移規則

5. **Harness Prompt 決定 Agent 行為**
   - 五個核心組件
   - 設計原則：明確、正面、具體

6. **工具註冊需要精確的定義**
   - JSON Schema 描述參數
   - 描述要告訴 LLM「何時」使用

---

## 練習題

### 練習 4.1：擴展工具集
為本章的 Agent 實現以下工具：
- `write_file`：寫入檔案內容
- `list_directory`：列出目錄內容
- `search_code`：在程式碼中搜尋模式

### 練習 4.2：實現 Streaming
修改 `ClaudeClient` 以支援 Streaming 模式，並在 CLI 中即時顯示生成的文字。

### 練習 4.3：改進錯誤處理
設計一個更健壯的錯誤處理機制：
- 分類不同類型的錯誤
- 實現智能重試策略
- 追蹤錯誤歷史避免無限重試

### 練習 4.4：Token 監控
實現一個 Token 使用監控系統：
- 追蹤每輪的 input/output token
- 計算累計成本
- 當接近預算上限時警告

---

## 延伸閱讀

1. **Claude API Documentation** (Anthropic)
   - 官方 API 文件，詳細說明所有端點和參數
   - https://docs.anthropic.com/

2. **"Design Patterns: Elements of Reusable Object-Oriented Software"** (GoF)
   - 狀態機模式的經典解說

3. **"Building LLM Applications"** (Anthropic Cookbook)
   - 實用的 LLM 應用開發範例
   - https://github.com/anthropics/anthropic-cookbook

4. **JSON Schema Specification**
   - 工具參數定義的標準參考
   - https://json-schema.org/

---

## 下一章預告

有了推論迴圈的基礎，第 5 章將介紹讓 Coding Agent 真正有用的**五大核心工具**：Read、List、Bash、Edit、Search。這五個工具是 Claude Code 等主流工具的核心能力，掌握它們的實作，你就能建構出能解決真實問題的 Agent。
