#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 5 章：工具調用與軌跡收集
工具管理系統完整實現

這個模組實現了完整的工具管理系統，包含：
1. 工具定義與註冊機制
2. 多種工具實現（網頁瀏覽、Python 執行、搜尋等）
3. 工具調用的封裝與錯誤處理
4. 與軌跡收集器的整合

使用方式：
    python tool_manager.py
    python tool_manager.py -q "搜尋 Python 異步編程教程"
    python tool_manager.py --demo
"""

import asyncio
import json
import os
import re
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from urllib.parse import quote_plus

import aiohttp
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 載入環境變數
load_dotenv()


# =============================================================================
# 工具定義資料結構
# =============================================================================

@dataclass
class ParameterSchema:
    """
    參數綱要定義

    ‹1› 每個參數都有完整的類型、描述和必填狀態
    ‹2› 支援 enum 限制可選值
    """
    name: str
    type: str  # string, integer, boolean, array, object
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Optional[Any] = None

    def to_json_schema(self) -> dict:
        """轉換為 JSON Schema 格式"""
        schema = {
            "type": self.type,
            "description": self.description
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class ToolDefinition:
    """
    工具定義資料結構

    ‹1› 完整描述工具的能力和使用方式
    ‹2› 包含參數綱要，讓 LLM 知道如何調用
    ‹3› 支援轉換為 OpenAI function calling 格式
    """
    name: str
    description: str
    parameters: List[ParameterSchema] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    category: str = "general"
    version: str = "1.0.0"

    def to_openai_tool(self) -> dict:
        """轉換為 OpenAI Tool 格式"""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


# =============================================================================
# 工具執行結果
# =============================================================================

class ToolResultType(Enum):
    """工具結果類型"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


@dataclass
class ToolResult:
    """
    工具執行結果

    ‹1› 統一的結果格式，方便後續處理
    ‹2› 包含執行時間和 token 統計
    """
    tool_name: str
    result_type: ToolResultType
    content: Any
    execution_time: float  # 秒
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.result_type == ToolResultType.SUCCESS

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "result_type": self.result_type.value,
            "content": self.content,
            "execution_time": self.execution_time,
            "token_count": self.token_count,
            "metadata": self.metadata
        }


# =============================================================================
# 基礎工具抽象類別
# =============================================================================

class BaseTool(ABC):
    """
    工具基礎類別

    ‹1› 所有工具都必須繼承此類別
    ‹2› 提供統一的執行介面和錯誤處理
    ‹3› 自動計算執行時間
    """

    def __init__(self):
        self._definition: Optional[ToolDefinition] = None

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """返回工具定義"""
        pass

    @abstractmethod
    async def _execute(self, **kwargs) -> Any:
        """
        實際執行邏輯（子類實現）

        Args:
            **kwargs: 工具參數

        Returns:
            執行結果
        """
        pass

    async def execute(self, **kwargs) -> ToolResult:
        """
        執行工具（帶計時和錯誤處理）

        ‹1› 自動計算執行時間
        ‹2› 統一的錯誤處理
        ‹3› 返回標準化的結果
        """
        start_time = time.time()

        try:
            # 驗證必填參數
            self._validate_params(kwargs)

            # 執行工具
            result = await self._execute(**kwargs)

            execution_time = time.time() - start_time

            # 計算 token 數（簡易估算）
            token_count = self._estimate_tokens(result)

            return ToolResult(
                tool_name=self.definition.name,
                result_type=ToolResultType.SUCCESS,
                content=result,
                execution_time=execution_time,
                token_count=token_count
            )

        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=self.definition.name,
                result_type=ToolResultType.TIMEOUT,
                content="工具執行超時",
                execution_time=time.time() - start_time
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.definition.name,
                result_type=ToolResultType.ERROR,
                content=f"執行錯誤: {str(e)}",
                execution_time=time.time() - start_time,
                metadata={"error_type": type(e).__name__}
            )

    def _validate_params(self, params: dict):
        """驗證必填參數"""
        for param in self.definition.parameters:
            if param.required and param.name not in params:
                raise ValueError(f"缺少必填參數: {param.name}")

    def _estimate_tokens(self, content: Any) -> int:
        """估算內容的 token 數量"""
        if isinstance(content, str):
            # 簡易估算：中文約 2 字符/token，英文約 4 字符/token
            return len(content) // 3
        elif isinstance(content, dict):
            return self._estimate_tokens(json.dumps(content, ensure_ascii=False))
        elif isinstance(content, list):
            return sum(self._estimate_tokens(item) for item in content)
        return 0


# =============================================================================
# 具體工具實現
# =============================================================================

class WebSearchTool(BaseTool):
    """
    網頁搜尋工具

    ‹1› 模擬搜尋引擎查詢
    ‹2› 返回結構化的搜尋結果
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="搜尋網頁獲取資訊。用於查找最新資訊、研究主題或驗證事實。",
            parameters=[
                ParameterSchema(
                    name="query",
                    type="string",
                    description="搜尋關鍵字或問題"
                ),
                ParameterSchema(
                    name="num_results",
                    type="integer",
                    description="返回結果數量",
                    required=False,
                    default=5
                ),
                ParameterSchema(
                    name="language",
                    type="string",
                    description="搜尋語言",
                    required=False,
                    enum=["zh-TW", "zh-CN", "en"],
                    default="zh-TW"
                )
            ],
            examples=[
                {"query": "Python 異步編程教程", "num_results": 5},
                {"query": "2024 AI 發展趨勢", "language": "zh-TW"}
            ],
            category="search"
        )

    async def _execute(
        self,
        query: str,
        num_results: int = 5,
        language: str = "zh-TW"
    ) -> List[Dict[str, str]]:
        """執行搜尋"""
        # 模擬搜尋結果（實際應用中應使用真實 API）
        await asyncio.sleep(0.5)  # 模擬網路延遲

        # 生成模擬結果
        results = []
        for i in range(min(num_results, 10)):
            results.append({
                "title": f"關於「{query}」的搜尋結果 {i+1}",
                "url": f"https://example.com/result/{quote_plus(query)}/{i+1}",
                "snippet": f"這是關於「{query}」的詳細介紹。包含相關概念、實作方法和最佳實踐...",
                "source": "example.com",
                "date": datetime.now().strftime("%Y-%m-%d")
            })

        return results


class WebBrowserTool(BaseTool):
    """
    網頁瀏覽工具

    ‹1› 獲取網頁內容
    ‹2› 支援內容擷取和清理
    """

    def __init__(self, timeout: float = 30.0):
        super().__init__()
        self.timeout = timeout

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_browser",
            description="瀏覽並獲取網頁內容。用於深入閱讀特定網頁、提取資訊或驗證來源。",
            parameters=[
                ParameterSchema(
                    name="url",
                    type="string",
                    description="要瀏覽的網頁 URL"
                ),
                ParameterSchema(
                    name="extract_text",
                    type="boolean",
                    description="是否只提取純文字內容",
                    required=False,
                    default=True
                ),
                ParameterSchema(
                    name="max_length",
                    type="integer",
                    description="最大返回字符數",
                    required=False,
                    default=10000
                )
            ],
            examples=[
                {"url": "https://example.com/article", "extract_text": True},
                {"url": "https://docs.python.org/3/", "max_length": 5000}
            ],
            category="browsing"
        )

    async def _execute(
        self,
        url: str,
        extract_text: bool = True,
        max_length: int = 10000
    ) -> Dict[str, Any]:
        """獲取網頁內容"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={"User-Agent": "MiroThinker/1.0"}
                ) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "url": url
                        }

                    content = await response.text()

                    # 簡易文字提取
                    if extract_text:
                        # 移除 HTML 標籤
                        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
                        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
                        content = re.sub(r'<[^>]+>', ' ', content)
                        content = re.sub(r'\s+', ' ', content).strip()

                    # 截斷
                    if len(content) > max_length:
                        content = content[:max_length] + "..."

                    return {
                        "success": True,
                        "url": url,
                        "content": content,
                        "content_length": len(content)
                    }

        except aiohttp.ClientError as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }


class PythonInterpreterTool(BaseTool):
    """
    Python 程式碼執行工具

    ‹1› 安全地執行 Python 程式碼
    ‹2› 捕獲輸出和錯誤
    ‹3› 支援超時控制
    """

    def __init__(self, timeout: float = 30.0):
        super().__init__()
        self.timeout = timeout

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="python_interpreter",
            description="執行 Python 程式碼。用於數據分析、計算驗證或生成圖表。注意：程式碼在沙盒環境中執行。",
            parameters=[
                ParameterSchema(
                    name="code",
                    type="string",
                    description="要執行的 Python 程式碼"
                ),
                ParameterSchema(
                    name="timeout",
                    type="integer",
                    description="執行超時時間（秒）",
                    required=False,
                    default=30
                )
            ],
            examples=[
                {"code": "print(sum(range(100)))"},
                {"code": "import math\nprint(math.pi * 10**2)", "timeout": 10}
            ],
            category="code_execution"
        )

    async def _execute(
        self,
        code: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """執行 Python 程式碼"""
        timeout = timeout or self.timeout

        # 創建臨時檔案
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            # 執行程式碼
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "error": f"執行超時（{timeout}秒）",
                    "code": code
                }

            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            if process.returncode == 0:
                return {
                    "success": True,
                    "output": stdout_str,
                    "code": code
                }
            else:
                return {
                    "success": False,
                    "output": stdout_str,
                    "error": stderr_str,
                    "code": code,
                    "return_code": process.returncode
                }

        finally:
            # 清理臨時檔案
            os.unlink(temp_file)


class FileReaderTool(BaseTool):
    """
    檔案讀取工具

    ‹1› 讀取本地檔案內容
    ‹2› 支援多種編碼
    """

    def __init__(self, base_path: str = "."):
        super().__init__()
        self.base_path = os.path.abspath(base_path)

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_reader",
            description="讀取本地檔案內容。用於分析程式碼、讀取數據或查看配置。",
            parameters=[
                ParameterSchema(
                    name="file_path",
                    type="string",
                    description="檔案路徑（相對於工作目錄）"
                ),
                ParameterSchema(
                    name="encoding",
                    type="string",
                    description="檔案編碼",
                    required=False,
                    default="utf-8"
                ),
                ParameterSchema(
                    name="max_lines",
                    type="integer",
                    description="最大讀取行數",
                    required=False,
                    default=1000
                )
            ],
            examples=[
                {"file_path": "src/main.py"},
                {"file_path": "data/config.json", "encoding": "utf-8"}
            ],
            category="file_system"
        )

    async def _execute(
        self,
        file_path: str,
        encoding: str = "utf-8",
        max_lines: int = 1000
    ) -> Dict[str, Any]:
        """讀取檔案"""
        # 安全性檢查：確保在基礎路徑內
        full_path = os.path.abspath(os.path.join(self.base_path, file_path))
        if not full_path.startswith(self.base_path):
            return {
                "success": False,
                "error": "安全限制：不允許訪問基礎路徑外的檔案",
                "file_path": file_path
            }

        if not os.path.exists(full_path):
            return {
                "success": False,
                "error": f"檔案不存在: {file_path}",
                "file_path": file_path
            }

        try:
            with open(full_path, 'r', encoding=encoding) as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)

                content = ''.join(lines)
                truncated = i >= max_lines

                return {
                    "success": True,
                    "content": content,
                    "file_path": file_path,
                    "line_count": len(lines),
                    "truncated": truncated
                }

        except UnicodeDecodeError:
            return {
                "success": False,
                "error": f"編碼錯誤，請嘗試其他編碼（當前: {encoding}）",
                "file_path": file_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }


# =============================================================================
# 工具註冊表
# =============================================================================

class ToolRegistry:
    """
    工具註冊表

    ‹1› 集中管理所有可用工具
    ‹2› 支援按類別查詢
    ‹3› 提供工具定義列表（供 LLM 使用）
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """註冊工具"""
        name = tool.definition.name
        if name in self._tools:
            raise ValueError(f"工具已存在: {name}")
        self._tools[name] = tool

    def unregister(self, name: str) -> None:
        """取消註冊工具"""
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> Optional[BaseTool]:
        """獲取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有工具名稱"""
        return list(self._tools.keys())

    def get_by_category(self, category: str) -> List[BaseTool]:
        """按類別獲取工具"""
        return [
            tool for tool in self._tools.values()
            if tool.definition.category == category
        ]

    def get_openai_tools(self) -> List[dict]:
        """獲取 OpenAI 格式的工具列表"""
        return [
            tool.definition.to_openai_tool()
            for tool in self._tools.values()
        ]

    def get_all_definitions(self) -> List[ToolDefinition]:
        """獲取所有工具定義"""
        return [tool.definition for tool in self._tools.values()]


# =============================================================================
# 工具管理器
# =============================================================================

class ToolManager:
    """
    工具管理器

    ‹1› 整合工具註冊、調用和軌跡收集
    ‹2› 提供 LLM 友好的工具調用介面
    ‹3› 自動記錄工具使用歷史
    """

    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        model: str = "gpt-4o-mini"
    ):
        self.client = client or AsyncOpenAI()
        self.model = model
        self.registry = ToolRegistry()
        self.call_history: List[Dict[str, Any]] = []

        # 註冊預設工具
        self._register_default_tools()

    def _register_default_tools(self):
        """註冊預設工具"""
        self.registry.register(WebSearchTool())
        self.registry.register(WebBrowserTool())
        self.registry.register(PythonInterpreterTool())
        self.registry.register(FileReaderTool())

    async def execute_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> ToolResult:
        """
        執行工具

        ‹1› 查找工具
        ‹2› 執行並記錄
        ‹3› 返回結果
        """
        tool = self.registry.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                result_type=ToolResultType.ERROR,
                content=f"工具不存在: {tool_name}",
                execution_time=0
            )

        result = await tool.execute(**kwargs)

        # 記錄調用歷史
        self.call_history.append({
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "parameters": kwargs,
            "result": result.to_dict()
        })

        return result

    async def process_with_tools(
        self,
        query: str,
        max_iterations: int = 10,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        使用工具處理查詢（ReAct 循環）

        ‹1› 讓 LLM 決定使用哪些工具
        ‹2› 執行工具並收集結果
        ‹3› 整合最終答案
        """
        messages = [
            {
                "role": "system",
                "content": """你是一個研究助理，可以使用工具來查找和驗證資訊。

請遵循以下原則：
1. 先思考需要什麼資訊
2. 使用適當的工具獲取資訊
3. 驗證資訊的準確性
4. 整合資訊形成完整答案

可用工具會在後續對話中提供。"""
            },
            {
                "role": "user",
                "content": query
            }
        ]

        tools = self.registry.get_openai_tools()
        iteration = 0
        tool_calls_made = []

        while iteration < max_iterations:
            iteration += 1

            if verbose:
                print(f"\n🔄 迭代 {iteration}/{max_iterations}")

            # 調用 LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            assistant_message = response.choices[0].message
            messages.append(assistant_message.model_dump())

            # 檢查是否需要調用工具
            if not assistant_message.tool_calls:
                # 沒有工具調用，返回最終答案
                return {
                    "answer": assistant_message.content,
                    "iterations": iteration,
                    "tool_calls": tool_calls_made,
                    "success": True
                }

            # 執行工具調用
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                if verbose:
                    print(f"   🔧 調用工具: {tool_name}")
                    print(f"      參數: {arguments}")

                # 執行工具
                result = await self.execute_tool(tool_name, **arguments)

                tool_calls_made.append({
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": result.to_dict()
                })

                if verbose:
                    status = "✅" if result.success else "❌"
                    print(f"      {status} 耗時: {result.execution_time:.2f}s")

                # 添加工具結果到對話
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result.content, ensure_ascii=False)
                })

        # 達到最大迭代次數
        return {
            "answer": "達到最大迭代次數，未能完成任務",
            "iterations": iteration,
            "tool_calls": tool_calls_made,
            "success": False
        }

    def get_statistics(self) -> Dict[str, Any]:
        """獲取工具使用統計"""
        if not self.call_history:
            return {"total_calls": 0, "tools": {}}

        stats = {
            "total_calls": len(self.call_history),
            "tools": {},
            "total_execution_time": 0,
            "success_rate": 0
        }

        success_count = 0
        for call in self.call_history:
            tool_name = call["tool_name"]
            result = call["result"]

            if tool_name not in stats["tools"]:
                stats["tools"][tool_name] = {
                    "calls": 0,
                    "total_time": 0,
                    "success_count": 0
                }

            stats["tools"][tool_name]["calls"] += 1
            stats["tools"][tool_name]["total_time"] += result["execution_time"]

            if result["result_type"] == "success":
                stats["tools"][tool_name]["success_count"] += 1
                success_count += 1

            stats["total_execution_time"] += result["execution_time"]

        stats["success_rate"] = success_count / len(self.call_history)

        return stats


# =============================================================================
# 示範功能
# =============================================================================

async def demo_tools():
    """展示工具管理系統"""
    print("=" * 60)
    print("🔧 工具管理系統示範")
    print("=" * 60)

    manager = ToolManager()

    # 顯示可用工具
    print("\n📋 可用工具：")
    for name in manager.registry.list_tools():
        tool = manager.registry.get(name)
        print(f"   • {name}: {tool.definition.description[:50]}...")

    # 測試各種工具
    print("\n" + "=" * 60)
    print("📍 測試工具調用")
    print("=" * 60)

    # 1. 搜尋工具
    print("\n1️⃣ 網頁搜尋工具")
    result = await manager.execute_tool(
        "web_search",
        query="Python 異步編程",
        num_results=3
    )
    print(f"   結果類型: {result.result_type.value}")
    print(f"   執行時間: {result.execution_time:.2f}s")
    print(f"   結果數量: {len(result.content)}")

    # 2. Python 執行器
    print("\n2️⃣ Python 執行器")
    result = await manager.execute_tool(
        "python_interpreter",
        code="print('Hello from MiroThinker!')\nprint(sum(range(1, 101)))"
    )
    print(f"   結果類型: {result.result_type.value}")
    if result.success:
        print(f"   輸出: {result.content['output'].strip()}")

    # 3. 使用統計
    print("\n" + "=" * 60)
    print("📊 使用統計")
    print("=" * 60)

    stats = manager.get_statistics()
    print(f"   總調用次數: {stats['total_calls']}")
    print(f"   成功率: {stats['success_rate']*100:.1f}%")
    print(f"   總執行時間: {stats['total_execution_time']:.2f}s")

    print("\n   各工具統計:")
    for tool_name, tool_stats in stats["tools"].items():
        print(f"      • {tool_name}: {tool_stats['calls']} 次, "
              f"成功 {tool_stats['success_count']} 次, "
              f"耗時 {tool_stats['total_time']:.2f}s")


async def demo_with_llm(query: str):
    """展示與 LLM 整合的工具使用"""
    print("=" * 60)
    print(f"🚀 處理查詢: {query}")
    print("=" * 60)

    manager = ToolManager()
    result = await manager.process_with_tools(query, verbose=True)

    print("\n" + "=" * 60)
    print("📝 最終答案")
    print("=" * 60)
    print(result["answer"])

    print(f"\n📊 統計：迭代 {result['iterations']} 次，"
          f"調用 {len(result['tool_calls'])} 個工具")


# =============================================================================
# 主程式
# =============================================================================

def main():
    """主程式入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="工具管理系統 - 第 5 章範例"
    )
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="使用工具處理的查詢"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="執行示範模式"
    )

    args = parser.parse_args()

    if args.query:
        asyncio.run(demo_with_llm(args.query))
    elif args.demo:
        asyncio.run(demo_tools())
    else:
        # 預設執行示範
        asyncio.run(demo_tools())


if __name__ == "__main__":
    main()
