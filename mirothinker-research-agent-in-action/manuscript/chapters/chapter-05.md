# 第 5 章：工具調用與軌跡收集

> **本章目標**：深入理解 Tool Use 的設計模式，並建立一套能收集執行軌跡以供強化學習訓練的系統。
>
> **核心產出物**：
> - 工具描述範本與最佳實踐
> - 工具生態架構圖
> - 軌跡數據 Schema
> - 完整可運行的 `tool_manager.py` 和 `trajectory_collector.py`

---

## 開場案例：當工具調用失控時

讓我們從一個常見的困境開始。

你設計了一個研究代理人，為它配備了多種工具：網路搜尋、網頁瀏覽、程式碼執行、檔案讀寫。代理人開始執行任務，但很快你發現問題：

1. **工具選擇錯誤**：代理人用「程式碼執行」來做簡單的數學計算，卻用「搜尋」來查詢已經在本地檔案中的資訊
2. **參數理解偏差**：搜尋工具期望簡潔的關鍵字，代理人卻輸入整段句子
3. **結果解析失敗**：工具返回了 JSON，代理人卻當作純文字處理
4. **重複調用浪費**：同樣的搜尋執行了三次，因為代理人「忘記」了之前的結果

這些問題的根源是什麼？

答案是：**工具設計不良**和**缺乏執行軌跡的學習機制**。

本章將教你如何設計清晰的工具介面，建立強大的工具管理系統，並收集執行軌跡用於持續改進代理人的工具使用能力。

---

## 5.1 Tool Use 的設計原理

工具調用（Tool Use）是代理人與外部世界互動的橋樑。設計良好的工具系統能讓代理人事半功倍。

### 5.1.1 工具的本質

從本質上說，工具是一個**函數**：

```
工具 = f(輸入參數) → 輸出結果
```

但對於 LLM 代理人來說，工具不只是函數，而是一個**語義介面**：

```
┌──────────────────────────────────────────────────────────────────┐
│                    工具的語義介面                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      工具描述                            │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │    │
│  │  │   名稱      │  │   描述     │  │   範例     │     │    │
│  │  │   Name      │  │ Description│  │  Examples  │     │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │    │
│  │                                                         │    │
│  │  ┌─────────────────────────────────────────────────┐   │    │
│  │  │              參數 Schema                         │   │    │
│  │  │  • 參數名稱                                      │   │    │
│  │  │  • 資料類型                                      │   │    │
│  │  │  • 是否必填                                      │   │    │
│  │  │  • 預設值                                        │   │    │
│  │  │  • 約束條件                                      │   │    │
│  │  └─────────────────────────────────────────────────┘   │    │
│  │                                                         │    │
│  │  ┌─────────────────────────────────────────────────┐   │    │
│  │  │              輸出格式                            │   │    │
│  │  │  • 返回類型                                      │   │    │
│  │  │  • 欄位說明                                      │   │    │
│  │  │  • 錯誤格式                                      │   │    │
│  │  └─────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                │                                 │
│                                ▼                                 │
│                    ┌─────────────────┐                          │
│                    │  LLM 理解工具   │                          │
│                    │  並正確調用     │                          │
│                    └─────────────────┘                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.1.2 工具描述的藝術

工具描述是 LLM「理解」工具的唯一途徑。好的描述能大幅提升工具使用的準確性。

**反面教材**：

```python
# ❌ 糟糕的工具描述
{
    "name": "search",
    "description": "搜尋",
    "parameters": {
        "q": {"type": "string"}
    }
}
```

問題：
- 描述過於簡短，LLM 不知道這是搜尋什麼
- 參數名稱不清楚
- 沒有說明輸入格式和限制

**正面教材**：

```python
# ✅ 優秀的工具描述
{
    "name": "web_search",
    "description": """
在網路上搜尋資訊。適用於：
- 查詢最新新聞和時事
- 尋找技術文件和教學
- 獲取公司、產品、人物的公開資訊

不適用於：
- 查詢私有或本地資料
- 需要登入才能訪問的內容
- 即時性要求極高的資訊（如股價）
""",
    "parameters": {
        "query": {
            "type": "string",
            "description": "搜尋關鍵字。建議使用 2-5 個關鍵詞，避免完整句子。",
            "examples": ["Python async await", "Tesla 2024 財報", "GPT-4 技術原理"]
        },
        "num_results": {
            "type": "integer",
            "description": "返回結果數量",
            "default": 5,
            "minimum": 1,
            "maximum": 20
        },
        "language": {
            "type": "string",
            "description": "搜尋語言",
            "enum": ["zh-TW", "zh-CN", "en", "ja"],
            "default": "zh-TW"
        }
    },
    "returns": {
        "type": "array",
        "items": {
            "title": "string",
            "snippet": "string",
            "url": "string"
        }
    }
}
```

### 5.1.3 參數 Schema 設計

JSON Schema 是描述工具參數的標準格式。以下是設計原則：

| 原則 | 說明 | 範例 |
|------|------|------|
| **明確類型** | 使用精確的資料類型 | `"type": "integer"` 而非 `"type": "number"` |
| **合理約束** | 設定最小/最大值、枚舉 | `"minimum": 1, "maximum": 100` |
| **清晰描述** | 每個參數都有說明 | `"description": "使用者 ID，格式為 UUID"` |
| **提供範例** | 給出典型輸入範例 | `"examples": ["abc123", "def456"]` |
| **設定預設值** | 減少必填參數 | `"default": 10` |

```python
# 完整的參數 Schema 範例
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "搜尋查詢字串",
            "minLength": 1,
            "maxLength": 200
        },
        "filters": {
            "type": "object",
            "properties": {
                "date_from": {
                    "type": "string",
                    "format": "date",
                    "description": "起始日期 (YYYY-MM-DD)"
                },
                "date_to": {
                    "type": "string",
                    "format": "date",
                    "description": "結束日期 (YYYY-MM-DD)"
                },
                "source_type": {
                    "type": "string",
                    "enum": ["news", "academic", "blog", "all"],
                    "default": "all"
                }
            }
        }
    },
    "required": ["query"]
}
```

### 5.1.4 錯誤處理最佳實踐

工具執行可能失敗，良好的錯誤處理能幫助代理人從錯誤中恢復：

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any

class ToolErrorType(Enum):
    """工具錯誤類型"""
    INVALID_INPUT = "invalid_input"      # 輸入參數無效
    RATE_LIMITED = "rate_limited"        # 請求頻率限制
    TIMEOUT = "timeout"                  # 執行超時
    NOT_FOUND = "not_found"              # 資源不存在
    PERMISSION_DENIED = "permission_denied"  # 權限不足
    INTERNAL_ERROR = "internal_error"    # 內部錯誤
    NETWORK_ERROR = "network_error"      # 網路錯誤


@dataclass
class ToolResult:
    """工具執行結果"""
    success: bool
    data: Optional[Any] = None
    error_type: Optional[ToolErrorType] = None
    error_message: Optional[str] = None
    retry_after: Optional[int] = None  # 建議重試等待時間（秒）
    suggestions: list[str] = None      # 錯誤恢復建議

    def to_llm_response(self) -> str:
        """轉換為 LLM 可理解的響應"""
        if self.success:
            return f"執行成功。結果：{self.data}"
        else:
            response = f"執行失敗。錯誤類型：{self.error_type.value}\n"
            response += f"錯誤訊息：{self.error_message}\n"
            if self.suggestions:
                response += f"建議：{'; '.join(self.suggestions)}"
            if self.retry_after:
                response += f"\n請在 {self.retry_after} 秒後重試。"
            return response
```

---

## 5.2 MiroThinker 的工具生態

MiroThinker 項目提供了一套豐富的工具生態系統，讓深度研究代理人能夠與真實世界互動。

### 5.2.1 核心工具類別

```
┌──────────────────────────────────────────────────────────────────┐
│                    MiroThinker 工具生態系統                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   資訊獲取類工具                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│    │
│  │  │ 網路搜尋 │  │ 網頁瀏覽 │  │ 學術搜尋 │  │ 新聞搜尋 ││    │
│  │  │WebSearch │  │WebBrowser│  │ Scholar  │  │  News    ││    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘│    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   計算與分析類工具                       │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│    │
│  │  │ Python   │  │ 數據分析 │  │ 圖表生成 │  │ 數學計算 ││    │
│  │  │Interpreter│ │ Pandas   │  │  Chart   │  │Calculator││    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘│    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   檔案處理類工具                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│    │
│  │  │ PDF讀取  │  │ Word處理 │  │ Excel    │  │ 圖片分析 ││    │
│  │  │PDFReader │  │ DocProc  │  │ XlsxProc │  │ ImageAI  ││    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘│    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   專業領域工具                           │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│    │
│  │  │ 金融數據 │  │ 專利搜尋 │  │ 法規查詢 │  │ 醫學文獻 ││    │
│  │  │FinanceAPI│  │ Patent   │  │ LawSearch│  │ PubMed   ││    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘│    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2.2 Web Browsing 工具

Web Browsing 是深度研究的核心能力，讓代理人能像人類一樣瀏覽網頁：

```python
from dataclasses import dataclass
from typing import Optional
from playwright.async_api import async_playwright

@dataclass
class BrowseResult:
    """瀏覽結果"""
    url: str
    title: str
    content: str
    links: list[dict]
    images: list[dict]
    metadata: dict


class WebBrowserTool:
    """
    網頁瀏覽工具

    使用 Playwright 進行無頭瀏覽，支援：
    - 頁面導航
    - 內容提取
    - 元素互動
    - 截圖
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None

    async def initialize(self):
        """初始化瀏覽器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless
        )
        self.context = await self.browser.new_context(
            user_agent="MiroThinker Research Agent/1.0"
        )

    async def browse(
        self,
        url: str,
        extract_links: bool = True,
        extract_images: bool = False,
        wait_for_selector: Optional[str] = None
    ) -> BrowseResult:
        """
        瀏覽網頁並提取內容

        Args:
            url: 目標網址
            extract_links: 是否提取連結
            extract_images: 是否提取圖片
            wait_for_selector: 等待特定元素載入

        Returns:
            BrowseResult: 瀏覽結果
        """
        page = await self.context.new_page()

        try:
            # 導航到頁面
            await page.goto(url, wait_until="networkidle")

            # 等待特定元素
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector)

            # 提取標題
            title = await page.title()

            # 提取主要內容
            content = await page.evaluate("""
                () => {
                    // 移除腳本和樣式
                    const scripts = document.querySelectorAll('script, style');
                    scripts.forEach(s => s.remove());

                    // 嘗試找到主要內容區域
                    const main = document.querySelector('main, article, .content, #content');
                    if (main) return main.innerText;

                    // 退而求其次，使用 body
                    return document.body.innerText;
                }
            """)

            # 提取連結
            links = []
            if extract_links:
                links = await page.evaluate("""
                    () => {
                        return Array.from(document.querySelectorAll('a[href]'))
                            .slice(0, 50)  // 限制數量
                            .map(a => ({
                                text: a.innerText.trim().slice(0, 100),
                                href: a.href
                            }))
                            .filter(l => l.text && l.href.startsWith('http'));
                    }
                """)

            # 提取圖片
            images = []
            if extract_images:
                images = await page.evaluate("""
                    () => {
                        return Array.from(document.querySelectorAll('img[src]'))
                            .slice(0, 20)
                            .map(img => ({
                                alt: img.alt || '',
                                src: img.src
                            }));
                    }
                """)

            # 提取元數據
            metadata = await page.evaluate("""
                () => {
                    const getMeta = (name) => {
                        const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                        return el ? el.content : null;
                    };
                    return {
                        description: getMeta('description') || getMeta('og:description'),
                        author: getMeta('author'),
                        published: getMeta('article:published_time')
                    };
                }
            """)

            return BrowseResult(
                url=url,
                title=title,
                content=content[:10000],  # 限制內容長度
                links=links,
                images=images,
                metadata=metadata
            )

        finally:
            await page.close()

    async def close(self):
        """關閉瀏覽器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
```

### 5.2.3 Python Code Interpreter

程式碼執行讓代理人能進行複雜計算和數據分析：

```python
import sys
import io
import ast
import traceback
from typing import Any
from dataclasses import dataclass
from contextlib import redirect_stdout, redirect_stderr


@dataclass
class CodeExecutionResult:
    """程式碼執行結果"""
    success: bool
    output: str
    error: Optional[str] = None
    return_value: Any = None
    variables: dict = None


class PythonInterpreter:
    """
    Python 程式碼執行器

    安全特性：
    - 限制可用的內建函數
    - 超時控制
    - 記憶體限制
    - 禁止檔案系統操作
    """

    # 允許的內建函數
    ALLOWED_BUILTINS = {
        'abs', 'all', 'any', 'bin', 'bool', 'chr', 'dict', 'dir',
        'divmod', 'enumerate', 'filter', 'float', 'format', 'frozenset',
        'hash', 'hex', 'int', 'isinstance', 'issubclass', 'iter',
        'len', 'list', 'map', 'max', 'min', 'oct', 'ord', 'pow',
        'print', 'range', 'repr', 'reversed', 'round', 'set',
        'slice', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip'
    }

    # 允許導入的模組
    ALLOWED_MODULES = {
        'math', 'statistics', 'random', 'datetime', 'json',
        'collections', 'itertools', 'functools', 're',
        'numpy', 'pandas'  # 數據科學常用
    }

    def __init__(self):
        self.global_namespace = {}
        self._setup_namespace()

    def _setup_namespace(self):
        """設置執行命名空間"""
        # 限制內建函數
        safe_builtins = {
            name: getattr(__builtins__ if isinstance(__builtins__, dict)
                         else __builtins__.__dict__, name, None)
            for name in self.ALLOWED_BUILTINS
            if hasattr(__builtins__ if isinstance(__builtins__, dict)
                      else __builtins__.__dict__, name)
        }

        self.global_namespace = {
            '__builtins__': safe_builtins,
            '__name__': '__main__'
        }

        # 預先導入常用模組
        for module_name in ['math', 'statistics', 'json', 'datetime']:
            try:
                self.global_namespace[module_name] = __import__(module_name)
            except ImportError:
                pass

    def execute(self, code: str, timeout: float = 30.0) -> CodeExecutionResult:
        """
        執行 Python 程式碼

        Args:
            code: 要執行的程式碼
            timeout: 超時時間（秒）

        Returns:
            CodeExecutionResult: 執行結果
        """
        # 安全檢查
        if not self._is_safe(code):
            return CodeExecutionResult(
                success=False,
                output="",
                error="程式碼包含不允許的操作"
            )

        # 捕獲輸出
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # 解析程式碼
            tree = ast.parse(code)

            # 分離表達式和語句
            *statements, last = tree.body if tree.body else [None]

            # 執行語句
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                if statements:
                    exec(
                        compile(ast.Module(body=statements, type_ignores=[]),
                               '<code>', 'exec'),
                        self.global_namespace
                    )

                # 如果最後是表達式，獲取返回值
                return_value = None
                if last and isinstance(last, ast.Expr):
                    return_value = eval(
                        compile(ast.Expression(body=last.value),
                               '<code>', 'eval'),
                        self.global_namespace
                    )
                elif last:
                    exec(
                        compile(ast.Module(body=[last], type_ignores=[]),
                               '<code>', 'exec'),
                        self.global_namespace
                    )

            output = stdout_capture.getvalue()
            if return_value is not None:
                output += f"\n返回值: {return_value}"

            return CodeExecutionResult(
                success=True,
                output=output,
                return_value=return_value,
                variables={k: str(v)[:100] for k, v in self.global_namespace.items()
                          if not k.startswith('_')}
            )

        except Exception as e:
            return CodeExecutionResult(
                success=False,
                output=stdout_capture.getvalue(),
                error=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            )

    def _is_safe(self, code: str) -> bool:
        """檢查程式碼安全性"""
        # 禁止的關鍵字
        forbidden = [
            'import os', 'import sys', 'import subprocess',
            '__import__', 'eval(', 'exec(',
            'open(', 'file(',
            'os.system', 'subprocess',
            '__class__', '__bases__', '__subclasses__'
        ]

        code_lower = code.lower()
        return not any(f in code_lower for f in forbidden)

    def reset(self):
        """重置執行環境"""
        self._setup_namespace()
```

### 5.2.4 自定義工具擴展

MiroThinker 支持用戶自定義工具：

```python
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass


@dataclass
class ToolDefinition:
    """工具定義"""
    name: str
    description: str
    parameters: dict
    returns: dict
    examples: list[dict] = None


class BaseTool(ABC):
    """工具基類"""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """返回工具定義"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """執行工具"""
        pass

    def validate_params(self, **kwargs) -> bool:
        """驗證參數"""
        required = self.definition.parameters.get('required', [])
        for param in required:
            if param not in kwargs:
                return False
        return True


# 自定義工具範例：股票價格查詢
class StockPriceTool(BaseTool):
    """股票價格查詢工具"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="stock_price",
            description="""
查詢股票當前價格和基本資訊。

支持的市場：
- 美股（使用股票代號，如 AAPL, GOOGL）
- 台股（使用股票代號加 .TW，如 2330.TW）

返回資訊包括：當前價格、漲跌幅、成交量等。
""",
            parameters={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代號",
                        "examples": ["AAPL", "2330.TW", "GOOGL"]
                    }
                },
                "required": ["symbol"]
            },
            returns={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "price": {"type": "number"},
                    "change": {"type": "number"},
                    "change_percent": {"type": "number"},
                    "volume": {"type": "integer"}
                }
            },
            examples=[
                {"input": {"symbol": "AAPL"}, "output": {"symbol": "AAPL", "price": 178.50}},
                {"input": {"symbol": "2330.TW"}, "output": {"symbol": "2330.TW", "price": 580.00}}
            ]
        )

    async def execute(self, symbol: str) -> ToolResult:
        """查詢股票價格"""
        try:
            # 這裡應該調用真實的股票 API
            # 以下為模擬數據
            import random

            price = random.uniform(100, 500)
            change = random.uniform(-5, 5)

            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_percent": round(change / price * 100, 2),
                    "volume": random.randint(1000000, 50000000)
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error_type=ToolErrorType.INTERNAL_ERROR,
                error_message=str(e)
            )
```

---

## 5.3 軌跡收集（Trajectory Collection）

軌跡收集是強化學習的基礎。通過記錄代理人的每一步行動，我們可以分析其行為模式並進行優化。

### 5.3.1 什麼是執行軌跡

執行軌跡是代理人完成任務過程中所有步驟的完整記錄：

```
┌──────────────────────────────────────────────────────────────────┐
│                    執行軌跡示意圖                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  任務：「查詢 NVIDIA 最新財報並分析其 AI 業務增長」              │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Step 1                                                   │    │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │    │
│  │ │   Thought   │  │   Action    │  │ Observation │       │    │
│  │ │ 需要先搜尋  │→│ web_search  │→│ 找到5篇相關 │       │    │
│  │ │ 財報資訊    │  │ "NVIDIA Q3  │  │ 新聞報導    │       │    │
│  │ │             │  │  2024 財報" │  │             │       │    │
│  │ └─────────────┘  └─────────────┘  └─────────────┘       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Step 2                                                   │    │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │    │
│  │ │   Thought   │  │   Action    │  │ Observation │       │    │
│  │ │ 第一篇看起  │→│ web_browse  │→│ 完整財報內  │       │    │
│  │ │ 來最相關    │  │ "https://..."│ │ 容提取成功  │       │    │
│  │ └─────────────┘  └─────────────┘  └─────────────┘       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Step 3                                                   │    │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │    │
│  │ │   Thought   │  │   Action    │  │ Observation │       │    │
│  │ │ 需要計算增  │→│ python_exec │→│ 計算結果:   │       │    │
│  │ │ 長率        │  │ "growth =   │  │ 增長 206%   │       │    │
│  │ │             │  │  (new-old)/ │  │             │       │    │
│  │ │             │  │  old * 100" │  │             │       │    │
│  │ └─────────────┘  └─────────────┘  └─────────────┘       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │   Final Answer  │                          │
│                    │  完整分析報告   │                          │
│                    └─────────────────┘                          │
│                                                                  │
│  軌跡元數據：                                                    │
│  • 總步驟數: 3                                                   │
│  • 工具調用: 3 次                                                │
│  • 總耗時: 45 秒                                                 │
│  • Token 消耗: 2,450                                             │
│  • 最終結果: 成功                                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.3.2 軌跡的數據結構

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum
import uuid


class StepType(Enum):
    """步驟類型"""
    THOUGHT = "thought"      # 思考
    ACTION = "action"        # 行動
    OBSERVATION = "observation"  # 觀察
    ANSWER = "answer"        # 最終答案


@dataclass
class TrajectoryStep:
    """軌跡步驟"""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    step_type: StepType = StepType.THOUGHT
    content: str = ""
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_output: Optional[Any] = None
    tokens_used: int = 0
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class Trajectory:
    """完整軌跡"""
    trajectory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    query: str = ""
    steps: list[TrajectoryStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    total_tokens: int = 0
    total_duration_ms: int = 0
    model: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    feedback: Optional[dict] = None  # 人工反饋

    def add_step(self, step: TrajectoryStep):
        """添加步驟"""
        self.steps.append(step)
        self.total_tokens += step.tokens_used
        self.total_duration_ms += step.duration_ms

    def get_tool_calls(self) -> list[TrajectoryStep]:
        """獲取所有工具調用"""
        return [s for s in self.steps if s.step_type == StepType.ACTION]

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "trajectory_id": self.trajectory_id,
            "task_id": self.task_id,
            "query": self.query,
            "steps": [
                {
                    "step_id": s.step_id,
                    "step_type": s.step_type.value,
                    "content": s.content,
                    "tool_name": s.tool_name,
                    "tool_input": s.tool_input,
                    "tool_output": str(s.tool_output)[:500] if s.tool_output else None,
                    "tokens_used": s.tokens_used,
                    "duration_ms": s.duration_ms,
                    "timestamp": s.timestamp.isoformat()
                }
                for s in self.steps
            ],
            "final_answer": self.final_answer,
            "success": self.success,
            "total_tokens": self.total_tokens,
            "total_duration_ms": self.total_duration_ms,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
            "feedback": self.feedback
        }
```

### 5.3.3 軌跡收集器實現

```python
import json
import os
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path


class TrajectoryCollector:
    """
    軌跡收集器

    負責收集、存儲和檢索代理人的執行軌跡
    """

    def __init__(
        self,
        storage_path: str = "./trajectories",
        auto_save: bool = True
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.auto_save = auto_save

        self.current_trajectory: Optional[Trajectory] = None
        self.trajectories: list[Trajectory] = []

        # 回調函數
        self.on_step_added: Optional[Callable] = None
        self.on_trajectory_complete: Optional[Callable] = None

    def start_trajectory(
        self,
        query: str,
        task_id: str = "",
        model: str = ""
    ) -> Trajectory:
        """開始新軌跡"""
        self.current_trajectory = Trajectory(
            query=query,
            task_id=task_id,
            model=model
        )
        return self.current_trajectory

    def add_thought(self, content: str, tokens: int = 0) -> TrajectoryStep:
        """添加思考步驟"""
        step = TrajectoryStep(
            step_type=StepType.THOUGHT,
            content=content,
            tokens_used=tokens
        )
        self._add_step(step)
        return step

    def add_action(
        self,
        tool_name: str,
        tool_input: dict,
        tokens: int = 0
    ) -> TrajectoryStep:
        """添加行動步驟"""
        step = TrajectoryStep(
            step_type=StepType.ACTION,
            content=f"調用工具: {tool_name}",
            tool_name=tool_name,
            tool_input=tool_input,
            tokens_used=tokens
        )
        self._add_step(step)
        return step

    def add_observation(
        self,
        content: str,
        tool_output: Any = None,
        duration_ms: int = 0
    ) -> TrajectoryStep:
        """添加觀察步驟"""
        step = TrajectoryStep(
            step_type=StepType.OBSERVATION,
            content=content,
            tool_output=tool_output,
            duration_ms=duration_ms
        )
        self._add_step(step)
        return step

    def add_answer(self, answer: str, tokens: int = 0) -> TrajectoryStep:
        """添加最終答案"""
        step = TrajectoryStep(
            step_type=StepType.ANSWER,
            content=answer,
            tokens_used=tokens
        )
        self._add_step(step)
        return step

    def _add_step(self, step: TrajectoryStep):
        """添加步驟到當前軌跡"""
        if self.current_trajectory is None:
            raise ValueError("No active trajectory. Call start_trajectory first.")

        self.current_trajectory.add_step(step)

        if self.on_step_added:
            self.on_step_added(step)

    def complete_trajectory(
        self,
        success: bool = True,
        final_answer: Optional[str] = None,
        error: Optional[str] = None
    ) -> Trajectory:
        """完成當前軌跡"""
        if self.current_trajectory is None:
            raise ValueError("No active trajectory.")

        self.current_trajectory.success = success
        self.current_trajectory.final_answer = final_answer
        self.current_trajectory.error = error
        self.current_trajectory.completed_at = datetime.now()

        self.trajectories.append(self.current_trajectory)

        if self.auto_save:
            self.save_trajectory(self.current_trajectory)

        if self.on_trajectory_complete:
            self.on_trajectory_complete(self.current_trajectory)

        completed = self.current_trajectory
        self.current_trajectory = None

        return completed

    def save_trajectory(self, trajectory: Trajectory):
        """保存軌跡到檔案"""
        filename = f"{trajectory.trajectory_id}.json"
        filepath = self.storage_path / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(trajectory.to_dict(), f, ensure_ascii=False, indent=2)

    def load_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """載入軌跡"""
        filepath = self.storage_path / f"{trajectory_id}.json"

        if not filepath.exists():
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 重建 Trajectory 對象
        trajectory = Trajectory(
            trajectory_id=data["trajectory_id"],
            task_id=data["task_id"],
            query=data["query"],
            final_answer=data["final_answer"],
            success=data["success"],
            total_tokens=data["total_tokens"],
            total_duration_ms=data["total_duration_ms"],
            model=data["model"]
        )

        for step_data in data["steps"]:
            step = TrajectoryStep(
                step_id=step_data["step_id"],
                step_type=StepType(step_data["step_type"]),
                content=step_data["content"],
                tool_name=step_data.get("tool_name"),
                tool_input=step_data.get("tool_input"),
                tool_output=step_data.get("tool_output"),
                tokens_used=step_data["tokens_used"],
                duration_ms=step_data["duration_ms"]
            )
            trajectory.steps.append(step)

        return trajectory

    def list_trajectories(
        self,
        success_only: bool = False,
        limit: int = 100
    ) -> list[dict]:
        """列出所有軌跡"""
        trajectories = []

        for filepath in sorted(
            self.storage_path.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if success_only and not data["success"]:
                continue

            trajectories.append({
                "trajectory_id": data["trajectory_id"],
                "query": data["query"][:50] + "...",
                "success": data["success"],
                "steps": len(data["steps"]),
                "tokens": data["total_tokens"]
            })

        return trajectories

    def get_statistics(self) -> dict:
        """獲取統計資訊"""
        total = len(list(self.storage_path.glob("*.json")))
        successful = 0
        total_tokens = 0
        total_steps = 0
        tool_usage = {}

        for filepath in self.storage_path.glob("*.json"):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if data["success"]:
                successful += 1

            total_tokens += data["total_tokens"]
            total_steps += len(data["steps"])

            for step in data["steps"]:
                if step.get("tool_name"):
                    tool_name = step["tool_name"]
                    tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

        return {
            "total_trajectories": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0,
            "avg_tokens": total_tokens / total if total > 0 else 0,
            "avg_steps": total_steps / total if total > 0 else 0,
            "tool_usage": tool_usage
        }
```

---

## 5.4 強化學習 from 環境反饋（RLEF）

MiroThinker 使用 RLEF（Reinforcement Learning from Environment Feedback）來持續改進代理人的工具使用能力。

### 5.4.1 RLEF 的核心概念

```
┌──────────────────────────────────────────────────────────────────┐
│                    RLEF 訓練流程                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    1. 軌跡收集                          │    │
│  │                                                         │    │
│  │  Agent 執行任務 ──→ 收集完整軌跡 ──→ 存入軌跡庫         │    │
│  │       ↑                                                 │    │
│  │       │                                                 │    │
│  │  ┌────┴────┐                                           │    │
│  │  │ 當前策略│                                           │    │
│  │  │   π_θ   │                                           │    │
│  │  └─────────┘                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    2. 獎勵計算                          │    │
│  │                                                         │    │
│  │  軌跡 ──→ 環境反饋 ──→ 計算獎勵信號                     │    │
│  │            │                                            │    │
│  │   ┌────────┴────────────┬───────────────┐              │    │
│  │   ▼                     ▼               ▼              │    │
│  │ 工具成功率          任務完成度      效率指標           │    │
│  │ (環境驗證)          (結果品質)     (Token 使用)        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    3. 策略優化                          │    │
│  │                                                         │    │
│  │  高獎勵軌跡 ──→ 正向強化                                │    │
│  │  低獎勵軌跡 ──→ 負向調整                                │    │
│  │                                                         │    │
│  │  θ_new = θ_old + α * ∇J(θ)                             │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │   更新後的策略   │                          │
│                    │      π_θ'       │ ────→ 部署 & 繼續收集    │
│                    └─────────────────┘                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.4.2 獎勵信號設計

獎勵信號的設計是 RLEF 成功的關鍵。MiroThinker 使用多維度的獎勵：

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class RewardSignal:
    """獎勵信號"""
    task_completion: float      # 任務完成度 (0-1)
    tool_efficiency: float      # 工具使用效率 (0-1)
    answer_quality: float       # 答案品質 (0-1)
    factual_accuracy: float     # 事實準確性 (0-1)
    token_efficiency: float     # Token 效率 (0-1)

    def total_reward(self, weights: dict = None) -> float:
        """計算總獎勵"""
        if weights is None:
            weights = {
                "task_completion": 0.3,
                "tool_efficiency": 0.2,
                "answer_quality": 0.25,
                "factual_accuracy": 0.15,
                "token_efficiency": 0.1
            }

        return (
            weights["task_completion"] * self.task_completion +
            weights["tool_efficiency"] * self.tool_efficiency +
            weights["answer_quality"] * self.answer_quality +
            weights["factual_accuracy"] * self.factual_accuracy +
            weights["token_efficiency"] * self.token_efficiency
        )


class RewardCalculator:
    """獎勵計算器"""

    def __init__(self, max_tokens: int = 10000, max_steps: int = 20):
        self.max_tokens = max_tokens
        self.max_steps = max_steps

    def calculate(
        self,
        trajectory: Trajectory,
        ground_truth: Optional[str] = None,
        human_feedback: Optional[float] = None
    ) -> RewardSignal:
        """計算軌跡的獎勵信號"""

        # 1. 任務完成度
        task_completion = 1.0 if trajectory.success else 0.0

        # 2. 工具使用效率
        tool_calls = trajectory.get_tool_calls()
        tool_efficiency = self._calculate_tool_efficiency(tool_calls)

        # 3. 答案品質
        answer_quality = self._calculate_answer_quality(
            trajectory.final_answer,
            ground_truth,
            human_feedback
        )

        # 4. 事實準確性（如果有 ground truth）
        factual_accuracy = self._calculate_factual_accuracy(
            trajectory.final_answer,
            ground_truth
        )

        # 5. Token 效率
        token_efficiency = max(0, 1 - trajectory.total_tokens / self.max_tokens)

        return RewardSignal(
            task_completion=task_completion,
            tool_efficiency=tool_efficiency,
            answer_quality=answer_quality,
            factual_accuracy=factual_accuracy,
            token_efficiency=token_efficiency
        )

    def _calculate_tool_efficiency(self, tool_calls: list) -> float:
        """計算工具使用效率"""
        if not tool_calls:
            return 0.5  # 沒有工具調用，給中等分數

        # 檢查重複調用
        unique_calls = set()
        duplicate_count = 0

        for call in tool_calls:
            key = (call.tool_name, str(call.tool_input))
            if key in unique_calls:
                duplicate_count += 1
            unique_calls.add(key)

        # 檢查失敗調用
        failed_count = sum(
            1 for call in tool_calls
            if call.tool_output and "error" in str(call.tool_output).lower()
        )

        # 計算效率分數
        total = len(tool_calls)
        efficiency = 1.0 - (duplicate_count + failed_count) / total

        # 懲罰過多的工具調用
        if total > self.max_steps:
            efficiency *= 0.8

        return max(0, efficiency)

    def _calculate_answer_quality(
        self,
        answer: Optional[str],
        ground_truth: Optional[str],
        human_feedback: Optional[float]
    ) -> float:
        """計算答案品質"""
        if answer is None:
            return 0.0

        # 如果有人工反饋，優先使用
        if human_feedback is not None:
            return human_feedback

        # 如果有 ground truth，計算相似度
        if ground_truth:
            return self._calculate_similarity(answer, ground_truth)

        # 否則使用啟發式方法
        quality = 0.5

        # 答案長度適中
        if 100 < len(answer) < 2000:
            quality += 0.2

        # 包含結構化元素
        if any(marker in answer for marker in ["1.", "•", "-", "##"]):
            quality += 0.1

        # 包含具體數據
        import re
        if re.search(r'\d+%|\d+\.\d+', answer):
            quality += 0.1

        return min(1.0, quality)

    def _calculate_factual_accuracy(
        self,
        answer: Optional[str],
        ground_truth: Optional[str]
    ) -> float:
        """計算事實準確性"""
        if answer is None or ground_truth is None:
            return 0.5  # 無法驗證，給中等分數

        return self._calculate_similarity(answer, ground_truth)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """計算文本相似度（簡化版）"""
        # 簡單的詞彙重疊計算
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        overlap = len(words1 & words2)
        total = len(words1 | words2)

        return overlap / total
```

### 5.4.3 策略更新機制

```python
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import list


class TrajectoryDataset(Dataset):
    """軌跡數據集"""

    def __init__(self, trajectories: list[Trajectory], rewards: list[RewardSignal]):
        self.trajectories = trajectories
        self.rewards = rewards

    def __len__(self):
        return len(self.trajectories)

    def __getitem__(self, idx):
        traj = self.trajectories[idx]
        reward = self.rewards[idx]

        # 將軌跡轉換為訓練格式
        return {
            "query": traj.query,
            "steps": [
                {
                    "type": step.step_type.value,
                    "content": step.content,
                    "tool_name": step.tool_name,
                    "tool_input": step.tool_input
                }
                for step in traj.steps
            ],
            "reward": reward.total_reward()
        }


class RLEFTrainer:
    """RLEF 訓練器（概念性實現）"""

    def __init__(
        self,
        model,
        learning_rate: float = 1e-5,
        batch_size: int = 4
    ):
        self.model = model
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=learning_rate
        )
        self.batch_size = batch_size

    def train_on_trajectories(
        self,
        trajectories: list[Trajectory],
        rewards: list[RewardSignal],
        epochs: int = 3
    ):
        """
        基於軌跡進行訓練

        使用類似 PPO 的策略梯度方法
        """
        dataset = TrajectoryDataset(trajectories, rewards)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        for epoch in range(epochs):
            total_loss = 0

            for batch in dataloader:
                # 計算策略梯度
                loss = self._compute_policy_gradient_loss(batch)

                # 更新參數
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

                total_loss += loss.item()

            avg_loss = total_loss / len(dataloader)
            print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")

    def _compute_policy_gradient_loss(self, batch):
        """
        計算策略梯度損失

        這是一個概念性實現，實際的 LLM 微調需要更複雜的處理
        """
        # 對於高獎勵軌跡，增加其行動的機率
        # 對於低獎勵軌跡，減少其行動的機率

        # 在實際實現中，這裡需要：
        # 1. 使用模型計算每個行動的 log probability
        # 2. 將獎勵作為權重
        # 3. 計算加權的負對數似然損失

        # 簡化示例
        rewards = torch.tensor(batch["reward"])
        baseline = rewards.mean()
        advantages = rewards - baseline

        # 假設的損失計算
        # loss = -advantages * log_probs
        loss = torch.tensor(0.0, requires_grad=True)  # 佔位符

        return loss
```

---

## 5.5 動手實作：建構工具管理系統

現在讓我們整合所有概念，建構一個完整的工具管理系統。

### 5.5.1 工具管理器

```python
"""
tool_manager.py

工具管理系統 - 負責工具的註冊、調用和追蹤
"""

import os
import json
import asyncio
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# 工具定義
# =============================================================================

@dataclass
class ToolParameter:
    """工具參數"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: list = None
    examples: list = None


@dataclass
class ToolDefinition:
    """工具定義"""
    name: str
    description: str
    parameters: list[ToolParameter]
    returns: dict = None
    examples: list[dict] = None
    category: str = "general"

    def to_openai_format(self) -> dict:
        """轉換為 OpenAI 工具格式"""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {"type": param.type, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum
            if param.examples:
                prop["examples"] = param.examples
            properties[param.name] = prop

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


@dataclass
class ToolResult:
    """工具執行結果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)


# =============================================================================
# 工具基類
# =============================================================================

class BaseTool:
    """工具基類"""

    @property
    def definition(self) -> ToolDefinition:
        """返回工具定義（子類必須實現）"""
        raise NotImplementedError

    async def execute(self, **kwargs) -> ToolResult:
        """執行工具（子類必須實現）"""
        raise NotImplementedError

    def validate(self, **kwargs) -> tuple[bool, str]:
        """驗證參數"""
        for param in self.definition.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"
        return True, ""


# =============================================================================
# 內建工具實現
# =============================================================================

class WebSearchTool(BaseTool):
    """網路搜尋工具"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="""
在網路上搜尋資訊。適用於查詢最新新聞、技術文件、公開資訊等。
建議使用 2-5 個關鍵詞，避免完整句子。
""",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="搜尋關鍵字",
                    examples=["Python async", "Tesla 財報 2024"]
                ),
                ToolParameter(
                    name="num_results",
                    type="integer",
                    description="返回結果數量",
                    required=False,
                    default=5
                )
            ],
            category="search"
        )

    async def execute(self, query: str, num_results: int = 5) -> ToolResult:
        import time
        start = time.time()

        if not self.api_key:
            # 模擬搜尋
            results = [
                {"title": f"Result {i+1} for: {query}", "snippet": f"Content about {query}...", "link": f"https://example.com/{i+1}"}
                for i in range(num_results)
            ]
            return ToolResult(
                success=True,
                data=results,
                duration_ms=int((time.time() - start) * 1000),
                metadata={"mode": "mock"}
            )

        import requests
        try:
            response = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": self.api_key},
                json={"q": query, "num": num_results}
            )
            data = response.json()
            results = [
                {"title": r["title"], "snippet": r["snippet"], "link": r["link"]}
                for r in data.get("organic", [])[:num_results]
            ]
            return ToolResult(
                success=True,
                data=results,
                duration_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CalculatorTool(BaseTool):
    """計算器工具"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculator",
            description="執行數學計算。支援基本運算、指數、對數等。",
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="數學表達式",
                    examples=["2 + 3 * 4", "sqrt(16)", "log(100, 10)"]
                )
            ],
            category="compute"
        )

    async def execute(self, expression: str) -> ToolResult:
        import math
        import time
        start = time.time()

        # 安全的數學環境
        safe_dict = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow,
            "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "pi": math.pi, "e": math.e
        }

        try:
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return ToolResult(
                success=True,
                data=result,
                duration_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PythonExecutorTool(BaseTool):
    """Python 程式碼執行工具"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="python_executor",
            description="""
執行 Python 程式碼。適用於數據分析、計算、資料處理等任務。
已預載入 math, statistics, json, datetime 模組。
""",
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python 程式碼"
                )
            ],
            category="compute"
        )

    async def execute(self, code: str) -> ToolResult:
        import io
        import sys
        import time
        from contextlib import redirect_stdout, redirect_stderr

        start = time.time()

        # 安全檢查
        forbidden = ['import os', 'import sys', 'subprocess', 'open(', '__import__']
        if any(f in code for f in forbidden):
            return ToolResult(success=False, error="Code contains forbidden operations")

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        namespace = {
            'math': __import__('math'),
            'statistics': __import__('statistics'),
            'json': __import__('json'),
            'datetime': __import__('datetime')
        }

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, namespace)

            output = stdout_capture.getvalue()
            return ToolResult(
                success=True,
                data=output if output else "Code executed successfully",
                duration_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 工具管理器
# =============================================================================

class ToolManager:
    """
    工具管理器

    負責工具的註冊、查找和執行
    """

    def __init__(self):
        self.tools: dict[str, BaseTool] = {}
        self.execution_history: list[dict] = []

        # 註冊內建工具
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """註冊內建工具"""
        self.register(WebSearchTool())
        self.register(CalculatorTool())
        self.register(PythonExecutorTool())

    def register(self, tool: BaseTool):
        """註冊工具"""
        self.tools[tool.definition.name] = tool

    def unregister(self, name: str):
        """取消註冊工具"""
        if name in self.tools:
            del self.tools[name]

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """獲取工具"""
        return self.tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """列出所有工具"""
        return [tool.definition for tool in self.tools.values()]

    def get_openai_tools(self) -> list[dict]:
        """獲取 OpenAI 格式的工具列表"""
        return [tool.definition.to_openai_format() for tool in self.tools.values()]

    async def execute(self, name: str, **kwargs) -> ToolResult:
        """執行工具"""
        tool = self.get_tool(name)
        if tool is None:
            return ToolResult(success=False, error=f"Tool not found: {name}")

        # 驗證參數
        valid, error = tool.validate(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)

        # 執行
        start_time = datetime.now()
        result = await tool.execute(**kwargs)

        # 記錄執行歷史
        self.execution_history.append({
            "tool": name,
            "input": kwargs,
            "output": result.data if result.success else result.error,
            "success": result.success,
            "timestamp": start_time.isoformat(),
            "duration_ms": result.duration_ms
        })

        return result

    def get_execution_history(self, limit: int = 50) -> list[dict]:
        """獲取執行歷史"""
        return self.execution_history[-limit:]

    def clear_history(self):
        """清除執行歷史"""
        self.execution_history.clear()


# =============================================================================
# 整合示例
# =============================================================================

async def demo():
    """演示工具管理器的使用"""
    manager = ToolManager()

    print("可用工具：")
    for tool_def in manager.list_tools():
        print(f"  - {tool_def.name}: {tool_def.description[:50]}...")

    print("\n執行搜尋：")
    result = await manager.execute("web_search", query="Python async programming")
    print(f"  結果數量: {len(result.data)}")

    print("\n執行計算：")
    result = await manager.execute("calculator", expression="sqrt(16) + pow(2, 3)")
    print(f"  計算結果: {result.data}")

    print("\n執行 Python 程式碼：")
    code = """
import math
result = sum([math.factorial(i) for i in range(1, 6)])
print(f"1! + 2! + 3! + 4! + 5! = {result}")
"""
    result = await manager.execute("python_executor", code=code)
    print(f"  輸出: {result.data}")

    print("\n執行歷史：")
    for record in manager.get_execution_history():
        print(f"  - {record['tool']}: {'成功' if record['success'] else '失敗'} ({record['duration_ms']}ms)")


if __name__ == "__main__":
    asyncio.run(demo())
```

---

## 5.6 章節總結

本章深入探討了工具調用與軌跡收集的設計與實現。

### 核心概念回顧

1. **工具描述的藝術**：清晰的名稱、詳細的描述、嚴謹的參數 Schema

2. **工具生態系統**：資訊獲取、計算分析、檔案處理、專業領域

3. **軌跡收集**：記錄 Thought-Action-Observation 的完整過程

4. **RLEF 訓練**：基於環境反饋的強化學習
   - 軌跡收集 → 獎勵計算 → 策略優化

5. **獎勵信號設計**：
   - 任務完成度
   - 工具使用效率
   - 答案品質
   - 事實準確性
   - Token 效率

### 學習檢查清單

- [ ] 理解工具描述對 LLM 理解的重要性
- [ ] 掌握 JSON Schema 的參數設計
- [ ] 能夠實現自定義工具
- [ ] 理解軌跡數據結構
- [ ] 掌握軌跡收集器的實現
- [ ] 理解 RLEF 的基本原理
- [ ] 完成 `tool_manager.py` 的運行

### 下一章預告

在第 6 章「長短時記憶管理」中，我們將深入探討如何在有限的 Context Window 中高效管理記憶：

- Context Window 的挑戰
- 記憶的分類與特性
- MiroThinker 的記憶架構
- 上下文壓縮策略
- 動手實作記憶管理器

---

## 本章程式碼清單

| 檔案 | 行數 | 說明 |
|------|------|------|
| `tool_manager.py` | ~400 | 工具管理系統 |
| `trajectory_collector.py` | ~300 | 軌跡收集器 |
| `requirements.txt` | ~15 | Python 依賴清單 |
| `.env.example` | ~10 | 環境變數範例 |
| `README.md` | ~200 | 使用說明 |

**GitHub 位置**：`code-examples/chapter-05/`
