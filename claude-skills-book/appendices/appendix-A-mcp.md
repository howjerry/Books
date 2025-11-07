# 附錄 A：Model Context Protocol (MCP) 完整規範與範例

## A.1 MCP 協定概述

### A.1.1 什麼是 MCP？

**Model Context Protocol (MCP)** 是 Anthropic 於 2024 年 11 月發布的開放協定，旨在標準化 AI 模型與外部系統的通訊方式。

**核心目標**:
- 統一的介面標準
- 安全的資料存取
- 可擴展的架構
- 跨平台互操作性

### A.1.2 MCP 架構

```
┌─────────────────┐
│   AI Application │  ← Your App (Claude, ChatGPT, etc.)
│   (MCP Client)   │
└─────────────────┘
         ↓ MCP Protocol
┌─────────────────┐
│   MCP Server    │  ← Your Integration
│   (Resources,   │
│    Tools,       │
│    Prompts)     │
└─────────────────┘
         ↓
┌─────────────────┐
│  External       │  ← Databases, APIs, Files
│  Systems        │
└─────────────────┘
```

### A.1.3 核心概念

**Resources (資源)**
- 可被 AI 讀取的數據源
- 例如：文件、資料庫記錄、API 回應

**Tools (工具)**
- AI 可以調用的函數
- 例如：查詢資料庫、發送郵件、執行計算

**Prompts (提示)**
- 預定義的提示模板
- 幫助 AI 執行特定任務

**Sampling (採樣)**
- AI 請求更多 context 的機制
- 動態獲取相關資訊

## A.2 創建 MCP Server (Python)

### A.2.1 基礎結構

```python
# mcp_server.py
from typing import Any, Dict, List
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent
)

class WebGuardMCPServer(Server):
    """WebGuard MCP Server"""

    def __init__(self):
        super().__init__("webguard")

        # 註冊資源
        self.register_resource_handler(self.list_resources)

        # 註冊工具
        self.register_tool_handler(self.list_tools)
        self.register_tool_call_handler(self.call_tool)

    async def list_resources(self) -> List[Resource]:
        """列出可用資源"""
        return [
            Resource(
                uri="webguard://test-results/latest",
                name="Latest Test Results",
                description="Most recent test execution results",
                mimeType="application/json"
            ),
            Resource(
                uri="webguard://test-suites",
                name="Test Suites",
                description="Available test suites",
                mimeType="application/json"
            ),
            Resource(
                uri="webguard://reports/{date}",
                name="Daily Reports",
                description="Test reports by date",
                mimeType="text/html"
            )
        ]

    async def list_tools(self) -> List[Tool]:
        """列出可用工具"""
        return [
            Tool(
                name="run_health_check",
                description="Run website health check",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Website URL"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds",
                            "default": 30
                        }
                    },
                    "required": ["url"]
                }
            ),
            Tool(
                name="run_browser_test",
                description="Run browser-based E2E test",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "test_suite": {
                            "type": "string",
                            "description": "Test suite name"
                        },
                        "browser": {
                            "type": "string",
                            "enum": ["chromium", "firefox", "webkit"],
                            "default": "chromium"
                        }
                    },
                    "required": ["test_suite"]
                }
            ),
            Tool(
                name="query_test_results",
                description="Query historical test results",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "format": "date"
                        },
                        "end_date": {
                            "type": "string",
                            "format": "date"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["passed", "failed", "skipped"]
                        }
                    }
                }
            )
        ]

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent]:
        """執行工具調用"""

        if name == "run_health_check":
            return await self._run_health_check(arguments)

        elif name == "run_browser_test":
            return await self._run_browser_test(arguments)

        elif name == "query_test_results":
            return await self._query_test_results(arguments)

        else:
            raise ValueError(f"Unknown tool: {name}")

    async def _run_health_check(
        self,
        args: Dict[str, Any]
    ) -> List[TextContent]:
        """執行健康檢查"""
        from src.skills.web_health_check import execute_health_check

        result = execute_health_check(
            url=args["url"],
            timeout=args.get("timeout", 30)
        )

        # 格式化回應
        text = f"""Health Check Result:
- URL: {result['url']}
- Status: {'✓ Healthy' if result['is_healthy'] else '✗ Unhealthy'}
- HTTP Status: {result['status_code']}
- Response Time: {result['response_time_ms']:.0f}ms
- Page Title: {result['page_title'] or 'N/A'}
"""

        if result['errors']:
            text += f"\nErrors:\n"
            for error in result['errors']:
                text += f"- {error}\n"

        return [TextContent(
            type="text",
            text=text
        )]

    async def _run_browser_test(
        self,
        args: Dict[str, Any]
    ) -> List[TextContent]:
        """執行瀏覽器測試"""
        # 實作...
        pass

    async def _query_test_results(
        self,
        args: Dict[str, Any]
    ) -> List[TextContent]:
        """查詢測試結果"""
        # 實作...
        pass


# 啟動 server
async def main():
    import asyncio
    from mcp.server.stdio import stdio_server

    server = WebGuardMCPServer()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="webguard",
                server_version="1.0.0"
            )
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### A.2.2 配置 MCP Server

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "webguard": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "your-key-here",
        "DATABASE_URL": "postgresql://localhost/webguard"
      }
    }
  }
}
```

## A.3 創建 MCP Server (TypeScript)

```typescript
// mcp-server.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool
} from "@modelcontextprotocol/sdk/types.js";

class WebGuardMCPServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: "webguard-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
          resources: {}
        },
      }
    );

    this.setupToolHandlers();
    this.setupResourceHandlers();
  }

  private setupToolHandlers() {
    // 列出工具
    this.server.setRequestHandler(
      ListToolsRequestSchema,
      async () => ({
        tools: [
          {
            name: "run_health_check",
            description: "Run website health check",
            inputSchema: {
              type: "object",
              properties: {
                url: {
                  type: "string",
                  description: "Website URL"
                },
                timeout: {
                  type: "number",
                  description: "Timeout in seconds",
                  default: 30
                }
              },
              required: ["url"]
            }
          }
        ] as Tool[]
      })
    );

    // 處理工具調用
    this.server.setRequestHandler(
      CallToolRequestSchema,
      async (request) => {
        const { name, arguments: args } = request.params;

        switch (name) {
          case "run_health_check":
            return await this.runHealthCheck(args);

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      }
    );
  }

  private setupResourceHandlers() {
    // 實作資源處理器
  }

  private async runHealthCheck(args: any) {
    // 執行健康檢查邏輯
    const { url, timeout = 30 } = args;

    // 調用實際的健康檢查函數
    // ...

    return {
      content: [
        {
          type: "text",
          text: `Health check completed for ${url}`
        }
      ]
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("WebGuard MCP server running on stdio");
  }
}

// 啟動
const server = new WebGuardMCPServer();
server.run().catch(console.error);
```

## A.4 MCP 與 Skills 整合

### A.4.1 從 Skill 調用 MCP Server

```python
# src/skills/mcp_integration.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPSkillIntegration:
    """MCP 整合"""

    def __init__(self, server_command: str):
        self.server_command = server_command
        self.session: ClientSession = None

    async def connect(self):
        """連接到 MCP Server"""
        server_params = StdioServerParameters(
            command=self.server_command.split()[0],
            args=self.server_command.split()[1:],
            env=None
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.session = session

    async def call_tool(self, tool_name: str, arguments: dict):
        """調用 MCP 工具"""
        if not self.session:
            await self.connect()

        result = await self.session.call_tool(tool_name, arguments)
        return result

    async def list_tools(self):
        """列出可用工具"""
        if not self.session:
            await self.connect()

        tools = await self.session.list_tools()
        return tools


# 使用範例
async def main():
    integration = MCPSkillIntegration("python mcp_server.py")

    # 列出工具
    tools = await integration.list_tools()
    print("Available tools:", [tool.name for tool in tools])

    # 調用工具
    result = await integration.call_tool(
        "run_health_check",
        {"url": "https://example.com", "timeout": 30}
    )
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

## A.5 生產環境考量

### A.5.1 錯誤處理

```python
class RobustMCPServer(Server):
    """強健的 MCP Server"""

    async def call_tool(self, name: str, arguments: Dict):
        try:
            # 驗證參數
            self._validate_arguments(name, arguments)

            # 執行工具
            result = await self._execute_tool(name, arguments)

            # 驗證結果
            self._validate_result(result)

            return result

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return [TextContent(
                type="text",
                text=f"Error: Invalid arguments - {str(e)}"
            )]

        except TimeoutError as e:
            logger.error(f"Timeout: {str(e)}")
            return [TextContent(
                type="text",
                text=f"Error: Operation timed out"
            )]

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
```

### A.5.2 日誌和監控

```python
import logging
from prometheus_client import Counter, Histogram

# 指標
mcp_requests = Counter(
    'mcp_requests_total',
    'Total MCP requests',
    ['tool_name', 'status']
)

mcp_duration = Histogram(
    'mcp_request_duration_seconds',
    'MCP request duration',
    ['tool_name']
)

class MonitoredMCPServer(Server):
    """帶監控的 MCP Server"""

    async def call_tool(self, name: str, arguments: Dict):
        with mcp_duration.labels(tool_name=name).time():
            try:
                result = await super().call_tool(name, arguments)
                mcp_requests.labels(
                    tool_name=name,
                    status='success'
                ).inc()
                return result

            except Exception as e:
                mcp_requests.labels(
                    tool_name=name,
                    status='error'
                ).inc()
                raise
```

## A.6 最佳實踐

### A.6.1 設計原則

**單一職責**
- 每個 MCP Server 專注特定領域
- 例如：webguard-server, database-server, file-server

**清晰的介面**
- 詳細的工具描述
- 明確的參數定義
- 結構化的回應

**錯誤處理**
- 優雅的降級
- 有意義的錯誤訊息
- 適當的重試機制

### A.6.2 安全考量

```python
class SecureMCPServer(Server):
    """安全的 MCP Server"""

    def __init__(self, allowed_operations: set):
        super().__init__("secure-server")
        self.allowed_operations = allowed_operations

    async def call_tool(self, name: str, arguments: Dict):
        # 檢查權限
        if name not in self.allowed_operations:
            raise PermissionError(f"Operation {name} not allowed")

        # 驗證輸入
        self._sanitize_arguments(arguments)

        # 執行
        result = await super().call_tool(name, arguments)

        # 過濾敏感資料
        return self._filter_sensitive_data(result)
```

## A.7 參考資源

### 官方文檔
- MCP 規範: https://spec.modelcontextprotocol.io
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- TypeScript SDK: https://github.com/modelcontextprotocol/typescript-sdk

### 社群資源
- MCP Discord: [Link]
- 範例儲存庫: https://github.com/modelcontextprotocol/servers

---

*MCP 正在快速發展，請定期檢查官方文檔以獲取最新資訊。*
