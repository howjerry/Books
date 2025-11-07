# 第 3 章：Skills 核心概念與 SKILL.md 語法（詳細大綱）

## 章節概述
本章深入探討 Skills 的核心架構、完整的 SKILL.md 語法規範、三層漸進式揭露系統，以及 Skills 的完整生命週期。

## 3.1 SKILL.md 完整語法規範

### 3.1.1 基本結構
```markdown
# Skill Name

## Description
[簡短描述，1-2 句話]

## When to use
[使用時機，列表形式]

## Parameters
[參數定義，包含類型、描述、預設值]

## Returns
[返回值說明]

## Implementation
[實作說明]

## Examples
[使用範例]

## Error handling
[錯誤處理策略]

## Dependencies
[依賴套件]

## Version
[版本號]

## Tags
[標籤]
```

### 3.1.2 參數定義語法
```markdown
## Parameters
- `url` (required, string): The website URL to check
  - Format: Must be a valid HTTP/HTTPS URL
  - Example: "https://example.com"

- `timeout` (optional, integer): Maximum wait time in seconds
  - Default: 30
  - Range: 1-300
  - Example: 60

- `retry_count` (optional, integer): Number of retries on failure
  - Default: 3
  - Range: 0-10
```

### 3.1.3 返回值定義
```markdown
## Returns
Returns a dictionary with the following structure:

{
  "is_healthy": boolean,      // Whether the website is healthy
  "status_code": integer,     // HTTP status code
  "response_time_ms": float,  // Response time in milliseconds
  "page_title": string|null,  // HTML page title
  "errors": array             // List of error messages
}
```

### 3.1.4 範例定義
```markdown
## Examples

### Example 1: Basic usage
Input:
{
  "url": "https://example.com"
}

Output:
{
  "is_healthy": true,
  "status_code": 200,
  "response_time_ms": 245.67,
  "page_title": "Example Domain",
  "errors": []
}

### Example 2: With timeout
Input:
{
  "url": "https://slow-website.com",
  "timeout": 60
}
```

### 3.1.5 元數據標籤
```markdown
## Metadata
- **Author**: Your Name
- **Created**: 2025-01-15
- **Updated**: 2025-01-20
- **Stability**: stable | experimental | deprecated
- **Category**: web-testing | data-processing | api-testing

## Tags
web, health-check, monitoring, http, reliability
```

## 3.2 三層漸進式揭露系統詳解

### 3.2.1 Layer 1: 發現層（Discovery Layer）
**目的**: 幫助 Claude 快速決定是否使用此 Skill

**包含內容**:
- Skill 名稱
- 簡短描述（1-2 句）
- 使用時機
- Tags

**範例**:
```markdown
# Web Health Check

Performs comprehensive health checks on websites.

## When to use
- Verify website accessibility
- Check deployment success
- Monitor uptime

## Tags
web, monitoring, health-check
```

**設計原則**:
- 簡潔明了
- 關鍵詞豐富
- 清晰的使用場景

### 3.2.2 Layer 2: 準備層（Preparation Layer）
**目的**: 提供足夠資訊準備執行

**包含內容**:
- 完整參數定義
- 返回值說明
- 基本範例
- 依賴說明

**範例**:
```markdown
## Parameters
- `url` (required): Website URL
- `expected_status` (optional): Expected HTTP status (default: 200)
- `timeout` (optional): Timeout in seconds (default: 30)

## Returns
Health check result with status code, response time, and errors

## Dependencies
- requests
- beautifulsoup4
```

**設計原則**:
- 足夠的上下文
- 清晰的介面定義
- 最小必要資訊

### 3.2.3 Layer 3: 執行層（Execution Layer）
**目的**: 完整的實作邏輯和詳細說明

**包含內容**:
- 詳細的實作說明
- 完整的範例（包含輸入/輸出）
- 錯誤處理策略
- 邊緣案例處理
- 性能考量

**範例**:
```markdown
## Implementation
This skill performs the following steps:

1. **URL Validation**
   - Verify URL format
   - Check protocol (HTTP/HTTPS)
   - Return error for invalid URLs

2. **HTTP Request**
   - Send GET request with custom User-Agent
   - Implement exponential backoff retry
   - Maximum 3 retries on network errors

3. **Response Validation**
   - Check HTTP status code
   - Parse HTML structure
   - Extract page title
   - Validate basic HTML elements (head, body)

4. **Performance Measurement**
   - Record response time
   - Report in milliseconds

5. **Result Compilation**
   - Aggregate all checks
   - Generate comprehensive report
   - Include actionable error messages

## Error Handling
- **Network Timeout**: Retry with exponential backoff (2^n seconds)
- **Invalid URL**: Return immediately with error
- **Unexpected Status**: Mark as unhealthy but include details
- **Parse Error**: Report but don't fail the entire check

## Examples

### Complete Example 1: Successful Check
Input:
{
  "url": "https://example.com",
  "expected_status": 200,
  "timeout": 30
}

Process:
1. Validate URL: ✓ Valid HTTPS URL
2. Send request: ✓ Connected
3. Status code: 200 (matches expected)
4. Response time: 245ms
5. Parse HTML: ✓ Valid structure
6. Extract title: "Example Domain"

Output:
{
  "is_healthy": true,
  "status_code": 200,
  "response_time_ms": 245.67,
  "page_title": "Example Domain",
  "errors": [],
  "url": "https://example.com",
  "checked_at": "2025-01-15 10:30:22"
}

### Complete Example 2: Failed Check
Input:
{
  "url": "https://slow-site.com",
  "timeout": 5
}

Process:
1. Validate URL: ✓
2. Send request: Timeout after 5s
3. Retry 1: Timeout
4. Retry 2: Timeout
5. Retry 3: Timeout
6. Maximum retries reached

Output:
{
  "is_healthy": false,
  "status_code": 0,
  "response_time_ms": 5000,
  "page_title": null,
  "errors": ["請求超時 (>5秒)", "達到最大重試次數"],
  "url": "https://slow-site.com",
  "checked_at": "2025-01-15 10:35:47"
}
```

**設計原則**:
- 完整但不冗長
- 實際可執行
- 涵蓋邊緣案例
- 清晰的錯誤訊息

### 3.2.4 漸進式揭露的好處

**性能優化**:
- 減少不必要的 token 使用
- 加快 Skill 選擇速度
- 降低 API 成本

**可維護性**:
- 清晰的結構
- 易於更新
- 模組化設計

**可讀性**:
- 不同層級的受眾
- 快速掃描 vs. 深入閱讀
- 漸進式學習曲線

## 3.3 Skills 生命週期

### 3.3.1 階段 1: 發現（Discovery）
```
User Request
    ↓
Claude 分析意圖
    ↓
掃描可用 Skills（Layer 1）
    ↓
匹配相關 Skills
    ↓
選擇最適合的 Skill
```

**關鍵考量**:
- Tags 的重要性
- 描述的清晰度
- 使用時機的明確性

### 3.3.2 階段 2: 準備（Preparation）
```
選定的 Skill
    ↓
載入 Layer 2 資訊
    ↓
解析參數需求
    ↓
從用戶請求中提取參數
    ↓
驗證參數完整性
    ↓
準備執行環境
```

**關鍵考量**:
- 參數驗證
- 預設值處理
- 依賴檢查

### 3.3.3 階段 3: 執行（Execution）
```
參數已準備
    ↓
載入 Layer 3 實作
    ↓
初始化執行環境
    ↓
執行 Skill 邏輯
    ↓
處理錯誤和重試
    ↓
收集結果
```

**關鍵考量**:
- 錯誤處理
- 超時管理
- 資源清理

### 3.3.4 階段 4: 回報（Reporting）
```
執行完成
    ↓
格式化結果
    ↓
回傳給 Claude
    ↓
Claude 解釋結果
    ↓
生成用戶回應
```

**關鍵考量**:
- 結果格式標準化
- 錯誤訊息清晰
- 可操作的資訊

### 3.3.5 階段 5: 清理（Cleanup）
```
回報完成
    ↓
釋放資源
    ↓
記錄日誌
    ↓
更新指標
    ↓
完成
```

**關鍵考量**:
- 資源洩漏防止
- 日誌記錄
- 指標收集

## 3.4 參數定義與驗證

### 3.4.1 參數類型系統

**基本類型**:
```python
from typing import Optional, Union, List, Dict
from pydantic import BaseModel, Field, validator

class HealthCheckParams(BaseModel):
    """健康檢查參數"""

    url: str = Field(
        ...,  # required
        description="Website URL to check",
        example="https://example.com"
    )

    expected_status: int = Field(
        default=200,
        ge=100,  # >=100
        le=599,  # <=599
        description="Expected HTTP status code"
    )

    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Timeout in seconds"
    )

    retry_count: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of retries"
    )

    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom HTTP headers"
    )

    @validator('url')
    def validate_url(cls, v):
        """驗證 URL 格式"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
```

**複雜類型**:
```python
class TestScenario(BaseModel):
    """測試場景"""
    name: str
    steps: List[str]
    expected_outcome: Dict[str, Any]

class BatchHealthCheckParams(BaseModel):
    """批次健康檢查參數"""
    urls: List[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of URLs to check"
    )

    concurrent: bool = Field(
        default=True,
        description="Execute checks concurrently"
    )

    max_workers: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum concurrent workers"
    )
```

### 3.4.2 參數驗證策略

**早期驗證**:
```python
def execute_health_check(
    url: str,
    expected_status: int = 200,
    timeout: int = 30
) -> Dict[str, Any]:
    """執行健康檢查"""

    # 步驟 1: 驗證參數
    try:
        params = HealthCheckParams(
            url=url,
            expected_status=expected_status,
            timeout=timeout
        )
    except ValidationError as e:
        return {
            "is_healthy": False,
            "errors": [f"參數驗證失敗: {str(e)}"]
        }

    # 步驟 2: 執行檢查
    checker = WebHealthChecker(timeout=params.timeout)
    return checker.check(params.url, params.expected_status)
```

**運行時驗證**:
```python
def check_url(self, url: str) -> HealthCheckResult:
    """檢查 URL（帶運行時驗證）"""

    # 驗證 URL 可訪問性
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError("Invalid URL: missing netloc")
    except Exception as e:
        return HealthCheckResult(
            is_healthy=False,
            errors=[f"URL 驗證失敗: {str(e)}"]
        )

    # 執行檢查...
```

### 3.4.3 預設值策略

**智能預設值**:
```python
class SkillConfig(BaseModel):
    """Skill 配置"""

    # 環境相關預設值
    timeout: int = Field(
        default_factory=lambda: int(os.getenv('DEFAULT_TIMEOUT', '30'))
    )

    # 動態計算預設值
    max_retries: int = Field(
        default_factory=lambda: 5 if os.getenv('ENV') == 'production' else 3
    )

    # 基於其他參數的預設值
    @validator('max_workers', always=True)
    def default_max_workers(cls, v, values):
        if v is None:
            # 基於 CPU 核心數
            import multiprocessing
            return min(multiprocessing.cpu_count(), 10)
        return v
```

## 3.5 錯誤處理策略

### 3.5.1 錯誤分類

**可恢復錯誤**:
- 網路暫時性故障 → 重試
- 超時 → 增加超時時間重試
- 速率限制 → 延遲後重試

**不可恢復錯誤**:
- 無效參數 → 立即返回錯誤
- 認證失敗 → 通知並停止
- 資源不存在 → 記錄並返回

**部分失敗**:
- 批次操作中的個別失敗 → 繼續並報告
- 可選功能失敗 → 降級執行

### 3.5.2 重試策略

**指數退避**:
```python
import time
from typing import Callable, Any

def retry_with_exponential_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """帶指數退避的重試裝飾器"""

    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            if attempt == max_retries:
                raise

            # 計算延遲時間
            delay = min(base_delay * (2 ** attempt), max_delay)

            logger.warning(
                f"第 {attempt + 1}/{max_retries} 次重試失敗: {str(e)}. "
                f"{delay}秒後重試..."
            )

            time.sleep(delay)
```

**使用範例**:
```python
def make_request(url: str) -> requests.Response:
    """發送請求（帶重試）"""

    return retry_with_exponential_backoff(
        lambda: requests.get(url, timeout=30),
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.RequestException,)
    )
```

### 3.5.3 錯誤訊息設計

**好的錯誤訊息**:
```python
# ✅ 清晰、可操作
{
    "error": "連接超時",
    "details": "無法在 30 秒內連接到 https://example.com",
    "suggestion": "檢查網路連接或增加超時時間",
    "retry_after": 60,
    "error_code": "TIMEOUT_ERROR"
}
```

**不好的錯誤訊息**:
```python
# ❌ 模糊、無幫助
{
    "error": "操作失敗",
    "details": "發生錯誤"
}
```

## 3.6 Skills 開發最佳實踐

### 3.6.1 單一職責原則

**好的設計**:
```python
# ✅ 每個 Skill 專注一個任務
- web_health_check: 檢查網站健康
- screenshot_capture: 擷取截圖
- performance_test: 性能測試
```

**不好的設計**:
```python
# ❌ 一個 Skill 做太多事
- website_everything: 健康檢查 + 截圖 + 性能測試 + SEO 分析
```

### 3.6.2 可組合性

**設計可組合的 Skills**:
```python
# 基礎 Skill
def fetch_webpage(url: str) -> str:
    """獲取網頁內容"""
    pass

def parse_html(html: str) -> Dict:
    """解析 HTML"""
    pass

def extract_links(parsed_html: Dict) -> List[str]:
    """提取連結"""
    pass

# 組合成高階 Skill
def crawl_website(url: str, max_depth: int = 2) -> Dict:
    """爬取網站"""
    html = fetch_webpage(url)
    parsed = parse_html(html)
    links = extract_links(parsed)
    # ...
```

### 3.6.3 測試性

**可測試的 Skill**:
```python
class WebHealthChecker:
    """可測試的健康檢查器"""

    def __init__(
        self,
        http_client=None,  # 可注入的依賴
        timeout: int = 30
    ):
        self.http_client = http_client or requests
        self.timeout = timeout

    def check(self, url: str) -> HealthCheckResult:
        """執行檢查"""
        response = self.http_client.get(url, timeout=self.timeout)
        # ...

# 測試
def test_health_checker():
    """測試健康檢查器"""

    # 使用 mock HTTP client
    mock_client = Mock()
    mock_client.get.return_value = Mock(
        status_code=200,
        text="<html><head><title>Test</title></head><body></body></html>"
    )

    checker = WebHealthChecker(http_client=mock_client)
    result = checker.check("https://test.com")

    assert result.is_healthy
    assert result.status_code == 200
```

### 3.6.4 文檔化

**完整的文檔**:
```python
def execute_health_check(
    url: str,
    expected_status: int = 200,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    執行網站健康檢查

    此函數檢查指定網站的可訪問性、回應時間和基本內容驗證。

    Args:
        url: 要檢查的網站 URL。必須是有效的 HTTP/HTTPS URL。
        expected_status: 預期的 HTTP 狀態碼。預設為 200。
            常用值: 200 (OK), 201 (Created), 204 (No Content)
        timeout: 最大等待時間（秒）。預設為 30 秒。
            建議範圍: 10-60 秒

    Returns:
        包含以下鍵值的字典:
        - is_healthy (bool): 網站是否健康
        - status_code (int): HTTP 狀態碼
        - response_time_ms (float): 回應時間（毫秒）
        - page_title (str|None): 頁面標題
        - errors (List[str]): 錯誤訊息列表
        - url (str): 檢查的 URL
        - checked_at (str): 檢查時間（ISO 8601 格式）

    Raises:
        ValueError: 如果 URL 格式無效
        TimeoutError: 如果超過最大重試次數後仍超時

    Examples:
        >>> result = execute_health_check("https://example.com")
        >>> result['is_healthy']
        True

        >>> result = execute_health_check(
        ...     "https://api.example.com",
        ...     expected_status=201,
        ...     timeout=60
        ... )

    Note:
        - 使用指數退避重試策略（最多 3 次）
        - 自動處理重定向
        - 驗證基本 HTML 結構

    See Also:
        - batch_health_check: 批次檢查多個 URL
        - WebHealthChecker: 底層檢查器類別
    """
    # 實作...
```

### 3.6.5 性能考量

**優化策略**:
```python
# 1. 使用連接池
session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=100
)
session.mount('http://', adapter)
session.mount('https://', adapter)

# 2. 並行執行
from concurrent.futures import ThreadPoolExecutor

def batch_check(urls: List[str]) -> List[Dict]:
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_url, url) for url in urls]
        return [f.result() for f in futures]

# 3. 快取結果
from functools import lru_cache

@lru_cache(maxsize=128)
def check_url_cached(url: str) -> Dict:
    return check_url(url)

# 4. 超時控制
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("操作超時")

# 使用
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30 秒超時
try:
    result = long_running_operation()
finally:
    signal.alarm(0)  # 取消超時
```

## 3.7 本章總結

### 關鍵要點

✅ **SKILL.md 語法**:
- 結構化定義
- 完整的參數和返回值說明
- 豐富的範例

✅ **三層漸進式揭露**:
- Layer 1: 快速發現
- Layer 2: 準備執行
- Layer 3: 完整實作

✅ **生命週期管理**:
- 發現 → 準備 → 執行 → 回報 → 清理
- 每個階段的職責清晰

✅ **最佳實踐**:
- 單一職責
- 可組合性
- 可測試性
- 完整文檔
- 性能優化

### 檢查點

- [ ] 理解 SKILL.md 的完整語法
- [ ] 掌握三層漸進式揭露的設計原理
- [ ] 能夠設計完整的 Skills 生命週期
- [ ] 實作健壯的參數驗證
- [ ] 應用錯誤處理最佳實踐

### 下一章預告

第 4 章將深入 Stagehand 瀏覽器自動化，這是 WebGuard 最重要的模組之一。你將學習如何使用 AI 驅動的瀏覽器自動化來創建穩定、自適應的測試。

---

*「Good design is as little design as possible.」 - Dieter Rams*
