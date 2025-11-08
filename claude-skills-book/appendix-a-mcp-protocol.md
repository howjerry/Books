# 附錄 A: MCP Protocol 參考

## A.1 什麼是 MCP (Model Context Protocol)

**Model Context Protocol (MCP)** 是 Anthropic 推出的開放標準協議，用於 AI 模型與外部系統之間的結構化通訊。MCP 讓 Claude 能夠安全地存取本地文件、數據庫、API 服務等資源，大幅擴展 AI 的能力邊界。

### A.1.1 核心概念

```
┌─────────────┐        MCP Protocol        ┌──────────────┐
│   Claude    │ ←────────────────────────→ │  MCP Server  │
│  (Client)   │    JSON-RPC 2.0 over       │              │
└─────────────┘    stdio/HTTP/SSE          └──────────────┘
                                                    │
                                                    ▼
                                            ┌──────────────┐
                                            │   Resources  │
                                            │  (Files, DB) │
                                            └──────────────┘
```

**關鍵術語**：

- **MCP Client**：發起請求的 AI 應用（如 Claude Desktop、Claude Code）
- **MCP Server**：提供資源和工具的服務端程序
- **Resources**：可存取的數據源（文件、數據庫記錄、API 回應等）
- **Tools**：可執行的操作（查詢數據庫、發送 HTTP 請求、執行腳本等）
- **Prompts**：預定義的提示模板

### A.1.2 傳輸協議

MCP 支援三種傳輸方式：

| 傳輸方式 | 使用場景 | 範例 |
|---------|---------|------|
| **stdio** | 本地進程間通訊 | Claude Desktop ↔ 本地 MCP Server |
| **HTTP + SSE** | 遠程服務 | Claude ↔ 雲端 API Gateway |
| **WebSocket** | 雙向實時通訊 | 瀏覽器擴展 ↔ MCP Server |

## A.2 MCP Server 基本結構

### A.2.1 最小化 MCP Server (Python)

```python
#!/usr/bin/env python3
"""
最小化 MCP Server 範例
提供基本的健康檢查工具
"""
import asyncio
import json
import sys
from typing import Any, Dict

class MCPServer:
    """MCP Server 基礎類別"""

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.tools = {}

    def register_tool(self, name: str, description: str, handler):
        """註冊工具"""
        self.tools[name] = {
            "description": description,
            "handler": handler
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """處理 JSON-RPC 請求"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": self.name,
                        "version": self.version
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": name,
                            "description": info["description"],
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                        for name, info in self.tools.items()
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            if tool_name in self.tools:
                result = await self.tools[tool_name]["handler"](params.get("arguments", {}))
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result)
                            }
                        ]
                    }
                }

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

    async def run(self):
        """啟動 Server (stdio 模式)"""
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            try:
                request = json.loads(line)
                response = await self.handle_request(request)
                print(json.dumps(response), flush=True)
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)

# 使用範例
async def health_check_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """健康檢查工具處理器"""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time()
    }

async def main():
    server = MCPServer(name="demo-server", version="1.0.0")
    server.register_tool(
        name="health_check",
        description="檢查 MCP Server 健康狀態",
        handler=health_check_handler
    )
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### A.2.2 MCP Server 配置 (Claude Desktop)

在 `~/Library/Application Support/Claude/claude_desktop_config.json` 添加：

```json
{
  "mcpServers": {
    "demo-server": {
      "command": "python3",
      "args": ["/path/to/demo_mcp_server.py"],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## A.3 Resources API

### A.3.1 提供文件資源

```python
class FileResourceServer(MCPServer):
    """提供文件系統資源的 MCP Server"""

    def __init__(self, base_path: str):
        super().__init__(name="file-server", version="1.0.0")
        self.base_path = Path(base_path)
        self.resources = {}
        self._scan_resources()

    def _scan_resources(self):
        """掃描並註冊資源"""
        for file_path in self.base_path.rglob("*.md"):
            uri = f"file://{file_path}"
            self.resources[uri] = {
                "uri": uri,
                "name": file_path.name,
                "mimeType": "text/markdown",
                "path": file_path
            }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """處理 resources/* 請求"""
        method = request.get("method")

        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "resources": [
                        {
                            "uri": info["uri"],
                            "name": info["name"],
                            "mimeType": info["mimeType"]
                        }
                        for info in self.resources.values()
                    ]
                }
            }

        elif method == "resources/read":
            uri = request.get("params", {}).get("uri")
            if uri in self.resources:
                content = self.resources[uri]["path"].read_text()
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "text/markdown",
                                "text": content
                            }
                        ]
                    }
                }

        return await super().handle_request(request)
```

### A.3.2 動態資源更新

```python
async def watch_resources(self):
    """監控文件系統變化並發送通知"""
    while True:
        await asyncio.sleep(5)  # 每 5 秒檢查

        old_uris = set(self.resources.keys())
        self._scan_resources()
        new_uris = set(self.resources.keys())

        if old_uris != new_uris:
            # 發送 resources/updated 通知
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/resources/updated",
                "params": {}
            }
            print(json.dumps(notification), flush=True)
```

## A.4 Tools API

### A.4.1 完整工具定義

```python
async def handle_tools_list(self) -> Dict[str, Any]:
    """返回工具列表（完整 schema）"""
    return {
        "tools": [
            {
                "name": "query_database",
                "description": "查詢 PostgreSQL 數據庫",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SQL 查詢語句（僅支援 SELECT）"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回結果數量限制",
                            "default": 100,
                            "minimum": 1,
                            "maximum": 1000
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "execute_health_check",
                "description": "執行網站健康檢查",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "format": "uri",
                            "description": "要檢查的網站 URL"
                        },
                        "timeout": {
                            "type": "integer",
                            "default": 30,
                            "description": "超時時間（秒）"
                        }
                    },
                    "required": ["url"]
                }
            }
        ]
    }
```

### A.4.2 工具執行與錯誤處理

```python
async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """執行工具並處理錯誤"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    try:
        # 驗證參數
        if tool_name == "query_database":
            query = arguments.get("query", "")
            if not query.strip().upper().startswith("SELECT"):
                raise ValueError("僅支援 SELECT 查詢")

            # 執行查詢
            result = await self.db.execute(query, limit=arguments.get("limit", 100))

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "rows": result,
                            "count": len(result)
                        }, ensure_ascii=False, indent=2)
                    }
                ],
                "isError": False
            }

        elif tool_name == "execute_health_check":
            url = arguments["url"]
            timeout = arguments.get("timeout", 30)

            async with aiohttp.ClientSession() as session:
                start_time = asyncio.get_event_loop().time()
                async with session.get(url, timeout=timeout) as response:
                    elapsed = asyncio.get_event_loop().time() - start_time

                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "url": url,
                                    "status_code": response.status,
                                    "response_time_ms": int(elapsed * 1000),
                                    "healthy": 200 <= response.status < 300
                                })
                            }
                        ]
                    }

    except ValueError as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"參數驗證錯誤: {str(e)}"
                }
            ],
            "isError": True
        }

    except asyncio.TimeoutError:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"請求超時（{timeout}s）"
                }
            ],
            "isError": True
        }

    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"執行錯誤: {str(e)}"
                }
            ],
            "isError": True
        }
```

## A.5 Prompts API

### A.5.1 定義提示模板

```python
PROMPTS = {
    "code_review": {
        "name": "code_review",
        "description": "生成代碼審查提示",
        "arguments": [
            {
                "name": "language",
                "description": "編程語言（python, typescript 等）",
                "required": True
            },
            {
                "name": "focus_areas",
                "description": "審查重點（security, performance, style）",
                "required": False
            }
        ]
    }
}

async def handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """生成提示內容"""
    prompt_name = params.get("name")
    arguments = params.get("arguments", {})

    if prompt_name == "code_review":
        language = arguments.get("language", "python")
        focus_areas = arguments.get("focus_areas", "security,performance,style").split(",")

        prompt_text = f"""請審查以下 {language} 代碼，重點關注：

"""
        for area in focus_areas:
            if area == "security":
                prompt_text += "- **安全性**：檢查 SQL 注入、XSS、敏感資訊洩漏\n"
            elif area == "performance":
                prompt_text += "- **性能**：識別 N+1 查詢、記憶體洩漏、低效算法\n"
            elif area == "style":
                prompt_text += "- **風格**：確保符合 PEP 8 / Airbnb 規範\n"

        return {
            "description": f"{language} 代碼審查",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": prompt_text
                    }
                }
            ]
        }
```

## A.6 在 Skills 中使用 MCP

### A.6.1 Skills + MCP 整合架構

```
┌──────────────────────────────────────────────┐
│         Claude Code Skills System            │
├──────────────────────────────────────────────┤
│                                              │
│  ┌────────────┐         ┌──────────────┐    │
│  │  Skill A   │────────→│  MCP Client  │    │
│  │ (測試執行)  │         │   (Claude)   │    │
│  └────────────┘         └──────┬───────┘    │
│                                │             │
│  ┌────────────┐                │             │
│  │  Skill B   │────────────────┘             │
│  │ (數據分析)  │                              │
│  └────────────┘                              │
└───────────────────────────────┬──────────────┘
                                │ MCP Protocol
                                ▼
                    ┌────────────────────────┐
                    │   MCP Server Layer     │
                    ├────────────────────────┤
                    │ • Database Server      │
                    │ • File System Server   │
                    │ • API Gateway Server   │
                    └────────────────────────┘
```

### A.6.2 實戰範例：Skills 調用 MCP Tools

**SKILL.md**:
```markdown
---
name: analyze-test-results
description: 使用 MCP 從數據庫分析測試結果
tags: [mcp, database, analysis]
author: your-team
version: 1.0.0
---

# Analyze Test Results

從 PostgreSQL 數據庫提取測試結果並生成分析報告。

## 前置條件

- MCP Database Server 已配置（見附錄 A.6.3）
- 數據庫包含 `test_results` 表

## 執行邏輯

1. 通過 MCP 查詢最近 7 天的測試結果
2. 計算通過率、失敗率、平均執行時間
3. 識別不穩定的測試（flaky tests）
4. 生成 Markdown 報告

## MCP 工具調用

使用 `query_database` 工具：
- 查詢語句：見下方 SQL
- 返回格式：JSON 格式測試記錄列表
```

**Python 實現**:
```python
#!/usr/bin/env python3
"""
Skills: analyze-test-results
依賴 MCP Database Server 提供數據查詢
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

async def execute_skill() -> Dict[str, Any]:
    """執行測試結果分析 Skill"""

    # Step 1: 通過 MCP 查詢數據庫
    # 注意：在實際環境中，Claude 會自動調用 MCP tools
    # 這裡展示預期的數據結構
    query = """
    SELECT
        test_name,
        status,
        duration_ms,
        error_message,
        executed_at
    FROM test_results
    WHERE executed_at >= NOW() - INTERVAL '7 days'
    ORDER BY executed_at DESC
    """

    # Claude 會調用 MCP Server 的 query_database 工具
    # 等效於：result = await mcp.call_tool("query_database", {"query": query})

    # Step 2: 分析數據（假設已從 MCP 獲得數據）
    results = [
        # MCP 返回的數據示例
        {"test_name": "test_login", "status": "passed", "duration_ms": 1200, ...},
        {"test_name": "test_checkout", "status": "failed", "duration_ms": 3400, ...},
        # ...
    ]

    analysis = analyze_results(results)

    # Step 3: 生成報告
    report = generate_markdown_report(analysis)

    return {
        "status": "success",
        "report": report,
        "summary": analysis
    }

def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析測試結果"""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = total - passed

    # 計算平均執行時間
    avg_duration = sum(r["duration_ms"] for r in results) / total if total > 0 else 0

    # 識別 flaky tests（交替通過/失敗）
    test_history = {}
    for r in results:
        name = r["test_name"]
        if name not in test_history:
            test_history[name] = []
        test_history[name].append(r["status"])

    flaky_tests = [
        name for name, statuses in test_history.items()
        if "passed" in statuses and "failed" in statuses
    ]

    return {
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total * 100, 2) if total > 0 else 0,
        "avg_duration_ms": round(avg_duration, 2),
        "flaky_tests": flaky_tests
    }

def generate_markdown_report(analysis: Dict[str, Any]) -> str:
    """生成 Markdown 報告"""
    return f"""
# 測試結果分析報告

**分析時間**：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**統計週期**：最近 7 天

## 📊 整體統計

| 指標 | 數值 |
|------|------|
| 總測試數 | {analysis['total_tests']} |
| 通過數 | {analysis['passed']} |
| 失敗數 | {analysis['failed']} |
| **通過率** | **{analysis['pass_rate']}%** |
| 平均執行時間 | {analysis['avg_duration_ms']} ms |

## ⚠️ 不穩定測試 (Flaky Tests)

{chr(10).join(f'- `{test}`' for test in analysis['flaky_tests']) if analysis['flaky_tests'] else '_無_'}

## 💡 建議

{'- ✅ 測試穩定性良好' if analysis['pass_rate'] >= 95 else '- ⚠️ 建議調查失敗原因'}
{'- ⚠️ 優先修復不穩定測試' if analysis['flaky_tests'] else ''}
"""

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(execute_skill())
    print(result["report"])
```

### A.6.3 配置 MCP Database Server

**1. 安裝 MCP Database Server**:
```bash
npm install -g @modelcontextprotocol/server-postgres
```

**2. 配置 Claude Desktop**:
```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://user:password@localhost:5432/webguard_db"
      ]
    }
  }
}
```

**3. 在 Skill 中使用**:

Claude 會自動發現 `query_database` 工具，你只需在 Skill 的提示中說明：

```markdown
請使用 query_database 工具執行以下查詢：

SELECT test_name, status, duration_ms
FROM test_results
WHERE executed_at >= NOW() - INTERVAL '7 days'
```

Claude 會自動調用 MCP 工具並返回結果。

## A.7 安全性最佳實踐

### A.7.1 參數驗證

```python
from pydantic import BaseModel, Field, validator

class QueryDatabaseParams(BaseModel):
    """查詢參數驗證"""
    query: str = Field(..., min_length=1, max_length=10000)
    limit: int = Field(default=100, ge=1, le=1000)

    @validator("query")
    def validate_read_only(cls, v):
        """確保僅允許讀取操作"""
        query_upper = v.strip().upper()
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"]

        if any(keyword in query_upper for keyword in forbidden_keywords):
            raise ValueError(f"禁止使用修改操作：{forbidden_keywords}")

        return v
```

### A.7.2 速率限制

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    """工具調用速率限制"""

    def __init__(self, max_calls: int = 100, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window = timedelta(seconds=window_seconds)
        self.call_history = defaultdict(list)

    def check_limit(self, tool_name: str) -> bool:
        """檢查是否超過速率限制"""
        now = datetime.now()
        cutoff = now - self.window

        # 清除過期記錄
        self.call_history[tool_name] = [
            timestamp for timestamp in self.call_history[tool_name]
            if timestamp > cutoff
        ]

        # 檢查限制
        if len(self.call_history[tool_name]) >= self.max_calls:
            return False

        # 記錄本次調用
        self.call_history[tool_name].append(now)
        return True

# 使用
rate_limiter = RateLimiter(max_calls=100, window_seconds=60)

async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
    tool_name = params.get("name")

    if not rate_limiter.check_limit(tool_name):
        return {
            "content": [{
                "type": "text",
                "text": "速率限制：每分鐘最多 100 次調用"
            }],
            "isError": True
        }

    # 繼續執行工具...
```

### A.7.3 敏感資訊遮罩

```python
import re

def mask_sensitive_data(text: str) -> str:
    """遮罩敏感資訊"""
    # 遮罩密碼
    text = re.sub(
        r'(password|passwd|pwd)[\s:=]+\S+',
        r'\1: ********',
        text,
        flags=re.IGNORECASE
    )

    # 遮罩 API Keys
    text = re.sub(
        r'(api[_-]?key|token)[\s:=]+[\w-]+',
        r'\1: ********',
        text,
        flags=re.IGNORECASE
    )

    # 遮罩信用卡號
    text = re.sub(
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        r'****-****-****-****',
        text
    )

    return text
```

## A.8 MCP 官方 Servers 清單

| Server | 功能 | NPM 包 |
|--------|------|--------|
| **Filesystem** | 本地文件讀寫 | `@modelcontextprotocol/server-filesystem` |
| **PostgreSQL** | 數據庫查詢 | `@modelcontextprotocol/server-postgres` |
| **GitHub** | 倉庫、Issues、PR | `@modelcontextprotocol/server-github` |
| **Google Drive** | 雲端文件存取 | `@modelcontextprotocol/server-gdrive` |
| **Slack** | 消息發送、頻道管理 | `@modelcontextprotocol/server-slack` |
| **Memory** | 持久化知識存儲 | `@modelcontextprotocol/server-memory` |

### 安裝範例

```bash
# 文件系統訪問
npm install -g @modelcontextprotocol/server-filesystem

# GitHub 整合
npm install -g @modelcontextprotocol/server-github
```

### 配置範例

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/you/Projects"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

## A.9 故障排除

### A.9.1 常見錯誤

**1. Server 無法啟動**

```bash
# 檢查 Server 配置
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq '.mcpServers'

# 測試 Server 可執行性
python3 /path/to/your_mcp_server.py
```

**2. 工具無法發現**

確保 `initialize` 響應包含 `capabilities.tools`:

```json
{
  "capabilities": {
    "tools": {}  // ← 必須存在
  }
}
```

**3. 參數驗證失敗**

檢查 `inputSchema` 與實際參數是否匹配：

```python
# 錯誤：schema 要求 "url"，但傳入 "website"
arguments = {"website": "https://example.com"}  # ❌

# 正確
arguments = {"url": "https://example.com"}  # ✅
```

### A.9.2 調試技巧

**啟用 MCP Server 日誌**:

```python
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stderr  # 輸出到 stderr，不干擾 stdio 通訊
)

logger = logging.getLogger(__name__)
logger.debug("MCP Server started")
```

**使用 MCP Inspector**:

```bash
# 安裝 Inspector
npm install -g @modelcontextprotocol/inspector

# 啟動調試
mcp-inspector python3 /path/to/your_server.py
```

## A.10 進階主題

### A.10.1 自定義傳輸層

```python
from aiohttp import web

class HTTPMCPServer(MCPServer):
    """基於 HTTP + SSE 的 MCP Server"""

    async def handle_http_request(self, request: web.Request) -> web.Response:
        """處理 HTTP POST 請求"""
        data = await request.json()
        response = await self.handle_request(data)
        return web.json_response(response)

    async def sse_endpoint(self, request: web.Request) -> web.StreamResponse:
        """Server-Sent Events 端點（用於通知）"""
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        await response.prepare(request)

        # 發送心跳
        while True:
            await asyncio.sleep(30)
            await response.write(b'event: ping\ndata: {}\n\n')

    def run_http_server(self, port: int = 8080):
        """啟動 HTTP Server"""
        app = web.Application()
        app.router.add_post('/mcp', self.handle_http_request)
        app.router.add_get('/events', self.sse_endpoint)
        web.run_app(app, port=port)
```

### A.10.2 MCP Server 集群

```python
class LoadBalancedMCPClient:
    """負載均衡 MCP Client"""

    def __init__(self, server_urls: List[str]):
        self.servers = server_urls
        self.current_index = 0

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """輪詢方式調用工具"""
        server_url = self.servers[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.servers)

        async with aiohttp.ClientSession() as session:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            async with session.post(f"{server_url}/mcp", json=request) as response:
                result = await response.json()
                return result.get("result")
```

## A.11 參考資源

### 官方文檔

- **MCP 規範**：https://modelcontextprotocol.io/specification
- **官方 SDKs**：https://github.com/modelcontextprotocol
- **Server 示例**：https://github.com/modelcontextprotocol/servers

### 社群資源

- **MCP Discord**：https://discord.gg/modelcontextprotocol
- **Awesome MCP**：https://github.com/punkpeye/awesome-mcp

### 相關章節

- **Chapter 5.4**：Skills 與 MCP 整合實戰
- **Chapter 9.3**：WebGuard 數據層 MCP 封裝
- **Chapter 10.5**：MCP 生態系統與未來展望

---

**本附錄涵蓋了 MCP Protocol 的核心概念、實現細節和實戰範例。建議與 Chapter 5、Chapter 9 配合閱讀，完整掌握 Skills + MCP 的強大組合。**
