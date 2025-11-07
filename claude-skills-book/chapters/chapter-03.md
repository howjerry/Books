# 第 3 章：Skills 核心概念與 SKILL.md 語法

> *「Simplicity is the ultimate sophistication.」 - Leonardo da Vinci*

在第 2 章中，我們創建了第一個 Skill——網站健康檢查。但那只是冰山一角。要真正掌握 Claude Code Skills 開發，你需要深入理解 Skills 的核心架構、設計原則和最佳實踐。

本章將帶你深入探討：

- **SKILL.md 完整語法規範**：如何撰寫清晰、完整的 Skill 定義
- **三層漸進式揭露系統**：Claude 如何高效發現和使用 Skills
- **Skills 生命週期**：從發現到執行的完整流程
- **參數驗證與錯誤處理**：打造健壯的生產級 Skills
- **開發最佳實踐**：經過驗證的設計模式和策略

學完本章，你將具備設計和實作專業級 Skills 的能力。

## 3.1 SKILL.md 完整語法規範

SKILL.md 是 Skills 系統的核心。它不僅是文檔，更是 Claude 理解和使用 Skill 的關鍵介面。一個設計良好的 SKILL.md 能讓 Claude 準確理解 Skill 的用途、正確準備參數、優雅處理錯誤。

### 3.1.1 基本結構

SKILL.md 遵循標準的 Markdown 格式，但有特定的章節結構：

```markdown
# Skill Name

## Description
[簡短描述，1-2 句話，清晰說明 Skill 的核心功能]

## When to use
[使用時機，列表形式，幫助 Claude 快速判斷是否適用]

## Parameters
[參數定義，包含類型、描述、預設值、範圍]

## Returns
[返回值說明，詳細描述返回數據的結構]

## Implementation
[實作說明，解釋 Skill 的執行邏輯]

## Examples
[使用範例，包含輸入和輸出]

## Error handling
[錯誤處理策略，說明各種錯誤情況的處理方式]

## Dependencies
[依賴套件，列出所有外部依賴]

## Metadata
[元數據，包含作者、版本、穩定性等資訊]

## Tags
[標籤，用於搜索和分類]
```

這個結構看似簡單，但每個章節都有其特定目的。讓我們逐一深入探討。

### 3.1.2 Description：第一印象很重要

**Description** 是 Claude 看到的第一件事。它必須在 1-2 句話內清晰傳達 Skill 的核心功能。

**好的描述範例**：

```markdown
## Description
Performs comprehensive health checks on websites, including HTTP status verification,
response time measurement, and basic HTML structure validation.
```

這個描述：
- ✅ 明確說明做什麼（health checks on websites）
- ✅ 列出關鍵功能（HTTP status, response time, HTML validation）
- ✅ 簡潔但資訊豐富

**不好的描述範例**：

```markdown
## Description
This skill checks if a website is working.
```

這個描述：
- ❌ 太模糊（"working" 是什麼意思？）
- ❌ 缺少細節（檢查什麼？如何檢查？）
- ❌ 不專業（太口語化）

### 3.1.3 When to use：精準匹配場景

**When to use** 幫助 Claude 判斷是否應該使用這個 Skill。它應該列出具體的使用場景，而非抽象的描述。

**好的範例**：

```markdown
## When to use
- Verify website accessibility after deployment
- Monitor production services uptime
- Validate HTTP endpoints in CI/CD pipelines
- Check website response time for performance monitoring
- Ensure websites return expected HTTP status codes
```

這些場景：
- ✅ 具體且可操作
- ✅ 涵蓋不同的使用情境
- ✅ 使用動詞開頭（Verify, Monitor, Validate）
- ✅ 包含上下文（deployment, CI/CD, performance）

**不好的範例**：

```markdown
## When to use
- When you want to check websites
- For testing
- Any time you need to see if a site is up
```

這些場景：
- ❌ 太模糊
- ❌ 缺少具體上下文
- ❌ 沒有幫助 Claude 做出明確判斷

### 3.1.4 Parameters：清晰的介面定義

參數定義是 Skill 介面的核心。每個參數都應該包含：

1. **名稱**：使用 snake_case
2. **必要性**：required 或 optional
3. **類型**：string, integer, boolean, array, object
4. **描述**：清晰說明用途
5. **約束**：範圍、格式、預設值
6. **範例**：具體的使用例子

**完整的參數定義範例**：

```markdown
## Parameters

### url
- **Required**: Yes
- **Type**: string
- **Description**: The website URL to check
- **Format**: Must be a valid HTTP or HTTPS URL
- **Example**: `"https://example.com"` or `"http://api.example.com/health"`

### expected_status
- **Required**: No
- **Type**: integer
- **Description**: Expected HTTP status code to validate against
- **Default**: `200`
- **Range**: 100-599 (valid HTTP status codes)
- **Example**: `200`, `201`, `204`
- **Note**: Use 200 for standard pages, 201 for resource creation endpoints

### timeout
- **Required**: No
- **Type**: integer
- **Description**: Maximum wait time in seconds before considering the request failed
- **Default**: `30`
- **Range**: 1-300 seconds
- **Example**: `60`
- **Recommendation**: Use 10-30s for fast sites, 60s+ for slower APIs

### retry_count
- **Required**: No
- **Type**: integer
- **Description**: Number of retry attempts on failure before giving up
- **Default**: `3`
- **Range**: 0-10
- **Example**: `5`
- **Note**: Retries use exponential backoff (2^n seconds between attempts)

### headers
- **Required**: No
- **Type**: object (key-value pairs)
- **Description**: Custom HTTP headers to include in the request
- **Default**: `null`
- **Example**: `{"Authorization": "Bearer token123", "User-Agent": "WebGuard/1.0"}`
- **Note**: Common use cases include authentication tokens and custom user agents
```

這種詳細程度確保：
- Claude 能夠正確準備參數
- 用戶理解如何使用 Skill
- 自動驗證成為可能
- 錯誤訊息可以更具體

### 3.1.5 Returns：明確的輸出契約

返回值定義應該像 API 文檔一樣清晰。使用結構化格式說明返回數據的每個欄位。

**完整的返回值定義範例**：

```markdown
## Returns

Returns a JSON object with the following structure:

```json
{
  "is_healthy": boolean,
  "status_code": integer,
  "response_time_ms": float,
  "page_title": string | null,
  "errors": array of strings,
  "url": string,
  "checked_at": string (ISO 8601 timestamp)
}
```

### Field Descriptions

**is_healthy** (boolean)
- `true`: Website is accessible and returned expected status
- `false`: Website is inaccessible, returned unexpected status, or encountered errors

**status_code** (integer)
- HTTP status code received from the server
- `0` if no response was received (timeout or connection error)
- Range: 0, 100-599

**response_time_ms** (float)
- Time taken to receive the response, in milliseconds
- Measured from request initiation to first byte received
- `0` if request failed before receiving response

**page_title** (string | null)
- Title extracted from HTML `<title>` tag
- `null` if:
  - Page has no title tag
  - Response is not HTML
  - Request failed

**errors** (array of strings)
- List of error messages encountered during the check
- Empty array `[]` if no errors
- Common errors:
  - `"Connection timeout (>30s)"`
  - `"Invalid URL format"`
  - `"Unexpected status code: 404 (expected 200)"`
  - `"Failed to parse HTML"`

**url** (string)
- The URL that was checked (echoed back for confirmation)

**checked_at** (string)
- ISO 8601 timestamp of when the check was performed
- Example: `"2025-01-15T10:30:22.123Z"`
- Timezone: UTC
```

### 3.1.6 Examples：實際使用演示

範例是最有力的文檔。提供多個範例，涵蓋常見場景和邊緣案例。

**完整的範例章節**：

```markdown
## Examples

### Example 1: Basic Health Check (Success)

**Scenario**: Check if a production website is accessible

**Input**:
```json
{
  "url": "https://example.com"
}
```

**Process**:
1. Validate URL format ✓
2. Send GET request to https://example.com
3. Receive response in 245ms
4. Status code: 200 (matches default expected_status)
5. Parse HTML and extract title
6. Mark as healthy

**Output**:
```json
{
  "is_healthy": true,
  "status_code": 200,
  "response_time_ms": 245.67,
  "page_title": "Example Domain",
  "errors": [],
  "url": "https://example.com",
  "checked_at": "2025-01-15T10:30:22.123Z"
}
```

---

### Example 2: Custom Status Code and Timeout

**Scenario**: Check API endpoint that returns 201 on success

**Input**:
```json
{
  "url": "https://api.example.com/health",
  "expected_status": 201,
  "timeout": 60
}
```

**Output**:
```json
{
  "is_healthy": true,
  "status_code": 201,
  "response_time_ms": 523.89,
  "page_title": null,
  "errors": [],
  "url": "https://api.example.com/health",
  "checked_at": "2025-01-15T10:31:45.789Z"
}
```

**Note**: page_title is null because API returns JSON, not HTML

---

### Example 3: Timeout Failure with Retries

**Scenario**: Website is slow and exceeds timeout

**Input**:
```json
{
  "url": "https://very-slow-site.com",
  "timeout": 5,
  "retry_count": 3
}
```

**Process**:
1. Attempt 1: Timeout after 5s
2. Wait 2s (exponential backoff)
3. Attempt 2: Timeout after 5s
4. Wait 4s (exponential backoff)
5. Attempt 3: Timeout after 5s
6. Wait 8s (exponential backoff)
7. Attempt 4: Timeout after 5s
8. Max retries reached, mark as unhealthy

**Output**:
```json
{
  "is_healthy": false,
  "status_code": 0,
  "response_time_ms": 5000,
  "page_title": null,
  "errors": [
    "Connection timeout (>5s)",
    "Maximum retry attempts (3) reached"
  ],
  "url": "https://very-slow-site.com",
  "checked_at": "2025-01-15T10:35:47.456Z"
}
```

---

### Example 4: Invalid URL

**Scenario**: User provides malformed URL

**Input**:
```json
{
  "url": "not-a-valid-url"
}
```

**Output**:
```json
{
  "is_healthy": false,
  "status_code": 0,
  "response_time_ms": 0,
  "page_title": null,
  "errors": [
    "Invalid URL format: must start with http:// or https://"
  ],
  "url": "not-a-valid-url",
  "checked_at": "2025-01-15T10:36:12.789Z"
}
```

**Note**: Early validation prevents unnecessary network requests

---

### Example 5: Unexpected Status Code

**Scenario**: Website returns 404 but we expected 200

**Input**:
```json
{
  "url": "https://example.com/nonexistent-page",
  "expected_status": 200
}
```

**Output**:
```json
{
  "is_healthy": false,
  "status_code": 404,
  "response_time_ms": 187.23,
  "page_title": "404 - Page Not Found",
  "errors": [
    "Unexpected status code: 404 (expected 200)"
  ],
  "url": "https://example.com/nonexistent-page",
  "checked_at": "2025-01-15T10:37:33.012Z"
}
```

**Note**: Still captures response details even though status doesn't match
```

這些範例：
- ✅ 涵蓋成功和失敗情況
- ✅ 顯示實際的輸入/輸出
- ✅ 解釋執行流程
- ✅ 包含實用的註解

### 3.1.7 Error Handling：優雅的失敗

錯誤處理章節應該說明 Skill 如何處理各種異常情況。

```markdown
## Error Handling

This skill implements comprehensive error handling with graceful degradation:

### Error Categories

**1. Validation Errors** (fail fast, no retries)
- Invalid URL format → Return immediately with clear error message
- Invalid parameter types → Return validation error
- Out-of-range values → Return constraint violation error

**2. Network Errors** (retry with exponential backoff)
- Connection timeout → Retry up to `retry_count` times
- DNS resolution failure → Retry with backoff
- SSL/TLS errors → Retry once, then report error

**3. HTTP Errors** (context-dependent)
- 4xx Client Errors (400-499) → No retry, report as unhealthy
- 5xx Server Errors (500-599) → Retry up to `retry_count` times
- Unexpected status codes → Report but don't fail completely

**4. Parsing Errors** (graceful degradation)
- Invalid HTML → Mark page_title as null, continue check
- Missing title tag → Set page_title to null, mark as healthy if status matches

### Retry Strategy

Uses **exponential backoff** for transient errors:

```
Attempt 1: Immediate
Attempt 2: Wait 2^1 = 2 seconds
Attempt 3: Wait 2^2 = 4 seconds
Attempt 4: Wait 2^3 = 8 seconds
...
Maximum wait: 60 seconds (capped)
```

### Error Message Format

All errors are returned in a structured format:

```json
{
  "is_healthy": false,
  "errors": [
    "<Error Type>: <Specific Details>",
    "<Actionable Suggestion (if applicable)>"
  ]
}
```

**Examples**:
- `"Connection timeout (>30s)"`
- `"Invalid URL format: must start with http:// or https://"`
- `"Unexpected status code: 404 (expected 200)"`
- `"Maximum retry attempts (3) reached"`

### Logging

All errors are logged with appropriate levels:
- **ERROR**: Connection failures, timeouts after retries
- **WARNING**: Unexpected status codes, parsing failures
- **INFO**: Successful retries, validation warnings
```

## 3.2 三層漸進式揭露系統詳解

Claude Code Skills 使用**三層漸進式揭露（Progressive Disclosure）**系統，這是一個經過精心設計的架構，能夠在性能、可用性和功能性之間取得完美平衡。

### 3.2.1 為什麼需要漸進式揭露？

想像一下，如果 Claude 每次需要選擇 Skill 時，都要載入所有 Skills 的完整文檔——包括詳細的實作說明、完整的範例、錯誤處理邏輯等。這會導致：

- 🐌 **性能問題**：大量不必要的 token 使用
- 💰 **成本問題**：API 調用成本顯著增加
- 😵 **決策困難**：資訊過載導致選擇困難

漸進式揭露解決了這些問題。Claude 只在需要時才載入更深層的資訊，就像你瀏覽網站時只看標題，點擊後才載入完整內容。

### 3.2.2 Layer 1: 發現層（Discovery Layer）

**目的**：幫助 Claude **快速決定**是否使用此 Skill

**包含內容**：
- Skill 名稱
- 簡短描述（1-2 句話）
- 使用時機（When to use）
- Tags（標籤）

**範例**：

```markdown
# Web Health Check

Performs comprehensive health checks on websites, including HTTP status
verification, response time measurement, and basic HTML structure validation.

## When to use
- Verify website accessibility after deployment
- Monitor production services uptime
- Validate HTTP endpoints in CI/CD pipelines

## Tags
web, monitoring, health-check, http, reliability
```

**設計原則**：

1. **簡潔明了**：
   - 每個句子都要有意義
   - 避免冗長的描述
   - 使用清晰的專業術語

2. **關鍵詞豐富**：
   - Tags 包含搜索關鍵詞
   - 描述中使用領域術語（HTTP, deployment, CI/CD）
   - 使用時機覆蓋主要場景

3. **快速掃描**：
   - 結構清晰
   - 列表格式易於閱讀
   - 視覺層次分明

**實際效果**：

當用戶說「檢查我的網站是否正常運行」時，Claude 會：
1. 掃描所有 Skills 的 Layer 1
2. 識別到 "Web Health Check" 包含關鍵詞 "website"、"monitoring"
3. 確認 "When to use" 中有 "Monitor production services uptime"
4. **決定使用這個 Skill**，進入 Layer 2

整個過程只需載入幾百個 tokens，決策速度極快。

### 3.2.3 Layer 2: 準備層（Preparation Layer）

**目的**：提供**足夠資訊**準備執行

**包含內容**：
- 完整參數定義
- 返回值說明
- 基本範例
- 依賴說明

**範例**：

```markdown
## Parameters

### url (required, string)
The website URL to check. Must be a valid HTTP/HTTPS URL.
Example: `"https://example.com"`

### expected_status (optional, integer)
Expected HTTP status code. Default: `200`. Range: 100-599.

### timeout (optional, integer)
Timeout in seconds. Default: `30`. Range: 1-300.

## Returns
```json
{
  "is_healthy": boolean,
  "status_code": integer,
  "response_time_ms": float,
  "page_title": string | null,
  "errors": array
}
```

## Dependencies
- requests>=2.31.0
- beautifulsoup4>=4.12.0

## Basic Example
```json
Input: {"url": "https://example.com"}
Output: {"is_healthy": true, "status_code": 200, ...}
```
```

**設計原則**：

1. **足夠的上下文**：
   - 參數說明清楚但不冗長
   - 提供必要的約束資訊
   - 包含一個基本範例

2. **清晰的介面定義**：
   - 明確區分 required/optional
   - 說明預設值和範圍
   - 返回值結構清晰

3. **最小必要資訊**：
   - 不包含詳細實作邏輯
   - 不包含所有邊緣案例
   - 只提供準備執行所需的資訊

**實際效果**：

Claude 已經決定使用這個 Skill，現在需要準備參數：
1. 載入 Layer 2
2. 解析用戶請求：「檢查 https://example.com 是否正常」
3. 提取參數：`url = "https://example.com"`
4. 查看其他參數是否需要：timeout? expected_status?
5. 使用預設值：`timeout=30, expected_status=200`
6. **準備就緒**，進入執行階段

### 3.2.4 Layer 3: 執行層（Execution Layer）

**目的**：提供**完整的實作邏輯**和詳細說明

**包含內容**：
- 詳細的實作說明（Implementation）
- 完整的範例（包含多種場景）
- 錯誤處理策略
- 邊緣案例處理
- 性能考量
- 故障排除指南

**範例**：

```markdown
## Implementation

This skill performs health checks through the following steps:

### Step 1: URL Validation
- Verify URL starts with http:// or https://
- Parse URL structure using urllib.parse
- Return early if URL is invalid (no network request)

**Code snippet**:
```python
from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except:
        return False
```

### Step 2: HTTP Request with Retry
- Create HTTP session with connection pooling
- Send GET request with custom User-Agent
- Implement exponential backoff retry (max 3 attempts)
- Handle timeouts gracefully

**Retry Logic**:
```python
for attempt in range(retry_count + 1):
    try:
        response = session.get(url, timeout=timeout)
        break  # Success
    except requests.Timeout:
        if attempt == retry_count:
            raise  # Max retries reached
        wait_time = 2 ** attempt
        time.sleep(wait_time)
```

### Step 3: Response Validation
- Check HTTP status code
- Measure response time (first byte)
- Parse HTML structure (if content-type is text/html)
- Extract page title from <title> tag

### Step 4: Health Assessment
Mark as healthy if:
- ✓ Response received (not timeout)
- ✓ Status code matches expected_status
- ✓ HTML is parseable (if applicable)

Mark as unhealthy if:
- ✗ Timeout after all retries
- ✗ Status code doesn't match expected
- ✗ Connection error

## Error Handling

[詳細的錯誤處理策略，如前所述]

## Complete Examples

[5+ 個完整範例，涵蓋各種場景]

## Performance Considerations

- Uses connection pooling to reduce overhead
- Implements request timeout to prevent hanging
- Limits retry attempts to avoid excessive delays
- Caches DNS lookups (handled by requests library)

**Typical execution time**:
- Fast websites (<100ms): Total ~200-300ms
- Normal websites (100-500ms): Total ~500-800ms
- Slow websites (>500ms): Up to timeout limit

## Troubleshooting

**Problem**: "Connection timeout" errors
- **Solution**: Increase timeout value or check network connectivity

**Problem**: "Invalid URL format" error
- **Solution**: Ensure URL starts with http:// or https://

**Problem**: False negatives (healthy site marked unhealthy)
- **Solution**: Check expected_status matches actual server response
```

**設計原則**：

1. **完整但不冗長**：
   - 涵蓋所有重要細節
   - 使用結構化格式
   - 避免過度解釋基礎概念

2. **實際可執行**：
   - 提供真實的代碼片段
   - 展示實際的執行流程
   - 包含性能數據

3. **涵蓋邊緣案例**：
   - 列出各種失敗場景
   - 提供故障排除指南
   - 解釋設計決策

**實際效果**：

執行階段，Claude 可能需要：
- 理解為什麼執行失敗
- 調整參數重試
- 解釋結果給用戶

這時 Layer 3 提供所有必要的深度資訊。

### 3.2.5 漸進式揭露的量化效益

讓我們用數據說話：

**場景**：100 個 Skills，用戶請求需要選擇 1 個

| 方式 | Layer 1 | Layer 2 | Layer 3 | 總計 |
|------|---------|---------|---------|------|
| **一次載入全部** | - | - | - | ~500,000 tokens |
| **漸進式揭露** | ~20,000 | ~1,500 | ~5,000 | ~26,500 tokens |

**節省**：95% 的 token 使用量！

**時間節省**：
- 一次載入：~30 秒（處理大量資訊）
- 漸進式：~3 秒（只處理必要資訊）

**成本節省**（基於 Claude API 定價）：
- 一次載入：~$0.15 每次請求
- 漸進式：~$0.008 每次請求

對於每天處理 1000 次請求的系統：
- 一次載入：$150/天 = $4,500/月
- 漸進式：$8/天 = $240/月

**年度節省：$51,120** 🎉

## 3.3 Skills 生命週期

理解 Skills 的完整生命週期，能幫助你設計更健壯、更高效的 Skills。一個 Skill 從被發現到執行完成，經歷五個關鍵階段。

### 3.3.1 階段 1: 發現（Discovery）

```
User Request: "檢查我的網站 https://example.com 是否正常"
    ↓
Claude 分析意圖
    ↓
識別關鍵詞: "檢查"、"網站"、"正常"
    ↓
掃描所有 Skills 的 Layer 1 (發現層)
    ↓
匹配相關 Skills:
  - ✓ Web Health Check (匹配: website, check, monitoring)
  - ✓ Website Screenshot (匹配: website)
  - ✗ Excel Data Processor (不匹配)
    ↓
根據相關度排序
    ↓
選擇最佳匹配: Web Health Check
```

**關鍵因素**：

1. **Tags 的重要性**：
   - 使用領域相關的關鍵詞
   - 包含同義詞（website, web, site）
   - 涵蓋不同的使用場景

2. **描述的清晰度**：
   - 使用精確的術語
   - 避免模糊的詞彙
   - 突出核心功能

3. **When to use 的明確性**：
   - 列出具體場景
   - 使用動詞開頭
   - 涵蓋常見需求

**優化建議**：

```markdown
# 好的 Tags
web, monitoring, health-check, uptime, availability, http, https, endpoint

# 不好的 Tags
utility, helper, tool, misc

# 好的 When to use
- Verify website accessibility after deployment
- Monitor production services uptime
- Check API endpoint health in microservices

# 不好的 When to use
- When you need to test something
- For checking stuff
- General purpose testing
```

### 3.3.2 階段 2: 準備（Preparation）

```
選定的 Skill: Web Health Check
    ↓
載入 Layer 2 資訊（參數定義）
    ↓
解析用戶請求中的參數:
  - url: "https://example.com" ✓
  - expected_status: 未提及 → 使用預設值 200
  - timeout: 未提及 → 使用預設值 30
    ↓
驗證參數:
  - url 格式正確? ✓
  - expected_status 在範圍內? ✓
  - timeout 在範圍內? ✓
    ↓
檢查依賴:
  - requests 已安裝? ✓
  - beautifulsoup4 已安裝? ✓
    ↓
參數準備完成
```

**關鍵考量**：

1. **參數驗證**：
   ```python
   # 使用 Pydantic 進行驗證
   from pydantic import BaseModel, Field, validator

   class HealthCheckParams(BaseModel):
       url: str = Field(..., description="Website URL")
       expected_status: int = Field(default=200, ge=100, le=599)
       timeout: int = Field(default=30, ge=1, le=300)

       @validator('url')
       def validate_url(cls, v):
           if not v.startswith(('http://', 'https://')):
               raise ValueError('URL must start with http:// or https://')
           return v
   ```

2. **預設值處理**：
   ```python
   # 智能預設值
   class SkillConfig(BaseModel):
       # 基於環境的預設值
       timeout: int = Field(
           default_factory=lambda: int(os.getenv('DEFAULT_TIMEOUT', '30'))
       )

       # 基於條件的預設值
       retry_count: int = Field(
           default_factory=lambda: 5 if os.getenv('ENV') == 'production' else 3
       )
   ```

3. **依賴檢查**：
   ```python
   def check_dependencies():
       """檢查所有依賴是否已安裝"""
       required = ['requests', 'beautifulsoup4']
       missing = []

       for package in required:
           try:
               __import__(package)
           except ImportError:
               missing.append(package)

       if missing:
           raise RuntimeError(
               f"Missing required packages: {', '.join(missing)}. "
               f"Install with: pip install {' '.join(missing)}"
           )
   ```

### 3.3.3 階段 3: 執行（Execution）

```
參數已準備: {url: "https://example.com", expected_status: 200, timeout: 30}
    ↓
載入 Layer 3 實作
    ↓
初始化執行環境:
  - 創建 HTTP session
  - 設置 timeout
  - 準備 retry 邏輯
    ↓
執行 Skill 邏輯:
  Step 1: 驗證 URL ✓
  Step 2: 發送 HTTP 請求 ✓
  Step 3: 測量回應時間 (245ms) ✓
  Step 4: 解析 HTML ✓
  Step 5: 提取 title "Example Domain" ✓
    ↓
處理錯誤和重試:
  - 無錯誤發生 ✓
    ↓
收集結果:
  {
    "is_healthy": true,
    "status_code": 200,
    "response_time_ms": 245.67,
    "page_title": "Example Domain",
    "errors": []
  }
```

**關鍵考量**：

1. **錯誤處理**：
   ```python
   def execute_with_retry(func, max_retries=3):
       """執行函數並處理錯誤"""
       for attempt in range(max_retries + 1):
           try:
               return func()
           except TransientError as e:
               if attempt == max_retries:
                   raise
               wait_time = 2 ** attempt
               logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
               time.sleep(wait_time)
           except PermanentError as e:
               # 不重試永久性錯誤
               logger.error(f"Permanent error: {e}")
               raise
   ```

2. **超時管理**：
   ```python
   import signal

   class TimeoutError(Exception):
       pass

   def timeout_handler(signum, frame):
       raise TimeoutError("Operation timed out")

   def execute_with_timeout(func, timeout_seconds):
       """在指定時間內執行函數"""
       signal.signal(signal.SIGALRM, timeout_handler)
       signal.alarm(timeout_seconds)
       try:
           result = func()
           signal.alarm(0)  # 取消 alarm
           return result
       except TimeoutError:
           logger.error(f"Operation timed out after {timeout_seconds}s")
           raise
   ```

3. **資源清理**：
   ```python
   class HealthCheckSession:
       """管理健康檢查會話"""

       def __init__(self):
           self.session = None

       def __enter__(self):
           self.session = requests.Session()
           return self

       def __exit__(self, exc_type, exc_val, exc_tb):
           if self.session:
               self.session.close()
           return False

   # 使用
   with HealthCheckSession() as session:
       result = session.check_url("https://example.com")
   # session 自動關閉
   ```

### 3.3.4 階段 4: 回報（Reporting）

```
執行完成
    ↓
格式化結果:
  - 確保所有必要欄位存在
  - 驗證資料類型
  - 添加時間戳
    ↓
回傳給 Claude:
  {
    "is_healthy": true,
    "status_code": 200,
    "response_time_ms": 245.67,
    "page_title": "Example Domain",
    "errors": [],
    "url": "https://example.com",
    "checked_at": "2025-01-15T10:30:22.123Z"
  }
    ↓
Claude 解釋結果:
  "您的網站 https://example.com 運行正常！
   - HTTP 狀態碼: 200 ✓
   - 回應時間: 246 毫秒 (快速)
   - 頁面標題: Example Domain

   網站健康，無發現問題。"
    ↓
生成用戶回應
```

**關鍵考量**：

1. **結果格式標準化**：
   ```python
   from pydantic import BaseModel
   from datetime import datetime

   class HealthCheckResult(BaseModel):
       """健康檢查結果"""
       is_healthy: bool
       status_code: int
       response_time_ms: float
       page_title: Optional[str]
       errors: List[str]
       url: str
       checked_at: datetime = Field(default_factory=datetime.utcnow)

       class Config:
           json_encoders = {
               datetime: lambda v: v.isoformat()
           }
   ```

2. **錯誤訊息清晰**：
   ```python
   # ✅ 好的錯誤訊息
   {
       "error": "Connection timeout",
       "details": "Unable to connect to https://example.com within 30 seconds",
       "suggestion": "Check network connectivity or increase timeout value",
       "error_code": "TIMEOUT_ERROR"
   }

   # ❌ 不好的錯誤訊息
   {
       "error": "Failed",
       "message": "Something went wrong"
   }
   ```

3. **可操作的資訊**：
   ```python
   def generate_actionable_report(result: HealthCheckResult) -> dict:
       """生成可操作的報告"""
       report = result.dict()

       # 添加建議
       if not result.is_healthy:
           report['suggestions'] = []

           if result.status_code == 0:
               report['suggestions'].append("Check if the website is accessible from your network")
           elif 400 <= result.status_code < 500:
               report['suggestions'].append("Verify the URL is correct")
           elif result.status_code >= 500:
               report['suggestions'].append("Website server error - try again later")

       # 添加性能評估
       if result.response_time_ms < 200:
           report['performance'] = "Excellent"
       elif result.response_time_ms < 500:
           report['performance'] = "Good"
       elif result.response_time_ms < 1000:
           report['performance'] = "Fair"
       else:
           report['performance'] = "Slow"

       return report
   ```

### 3.3.5 階段 5: 清理（Cleanup）

```
回報完成
    ↓
釋放資源:
  - 關閉 HTTP session ✓
  - 釋放記憶體 ✓
  - 清除暫存檔案 ✓
    ↓
記錄日誌:
  - INFO: Health check completed for https://example.com
  - Duration: 0.25s
  - Status: healthy
    ↓
更新指標:
  - health_checks_total: +1
  - health_checks_success: +1
  - response_time_histogram: add(245.67)
    ↓
完成
```

**關鍵考量**：

1. **防止資源洩漏**：
   ```python
   class ResourceManager:
       """資源管理器"""

       def __init__(self):
           self.resources = []

       def register(self, resource):
           """註冊需要清理的資源"""
           self.resources.append(resource)

       def cleanup(self):
           """清理所有資源"""
           for resource in self.resources:
               try:
                   if hasattr(resource, 'close'):
                       resource.close()
                   elif hasattr(resource, '__exit__'):
                       resource.__exit__(None, None, None)
               except Exception as e:
                   logger.warning(f"Failed to cleanup resource: {e}")

       def __enter__(self):
           return self

       def __exit__(self, exc_type, exc_val, exc_tb):
           self.cleanup()
           return False
   ```

2. **日誌記錄**：
   ```python
   import logging
   import time

   logger = logging.getLogger(__name__)

   def log_skill_execution(skill_name: str):
       """記錄 Skill 執行"""
       def decorator(func):
           def wrapper(*args, **kwargs):
               start_time = time.time()
               logger.info(f"Starting {skill_name} with args={args}, kwargs={kwargs}")

               try:
                   result = func(*args, **kwargs)
                   duration = time.time() - start_time
                   logger.info(f"{skill_name} completed successfully in {duration:.2f}s")
                   return result
               except Exception as e:
                   duration = time.time() - start_time
                   logger.error(f"{skill_name} failed after {duration:.2f}s: {e}", exc_info=True)
                   raise

           return wrapper
       return decorator

   # 使用
   @log_skill_execution("web_health_check")
   def execute_health_check(url: str) -> dict:
       # ...
       pass
   ```

3. **指標收集**：
   ```python
   from prometheus_client import Counter, Histogram

   # 定義指標
   skill_executions = Counter(
       'skill_executions_total',
       'Total skill executions',
       ['skill_name', 'status']
   )

   skill_duration = Histogram(
       'skill_execution_duration_seconds',
       'Skill execution duration',
       ['skill_name']
   )

   def track_metrics(skill_name: str):
       """追蹤指標"""
       def decorator(func):
           def wrapper(*args, **kwargs):
               with skill_duration.labels(skill_name=skill_name).time():
                   try:
                       result = func(*args, **kwargs)
                       skill_executions.labels(skill_name=skill_name, status='success').inc()
                       return result
                   except Exception as e:
                       skill_executions.labels(skill_name=skill_name, status='failure').inc()
                       raise
           return wrapper
       return decorator
   ```

## 3.4 參數定義與驗證

參數驗證是 Skills 開發中最容易被忽視，卻最關鍵的部分。良好的參數驗證能夠：
- 在早期捕獲錯誤
- 提供清晰的錯誤訊息
- 避免不必要的資源浪費
- 提高 Skill 的可靠性

### 3.4.1 使用 Pydantic 進行參數驗證

Pydantic 是 Python 中最強大的資料驗證庫。它使用 Python 類型提示來定義資料結構，並自動進行驗證。

**基本範例**：

```python
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator, HttpUrl
from datetime import datetime

class HealthCheckParams(BaseModel):
    """健康檢查參數"""

    url: HttpUrl = Field(
        ...,  # ... 表示必要欄位
        description="Website URL to check",
        example="https://example.com"
    )

    expected_status: int = Field(
        default=200,
        ge=100,  # greater than or equal (>=100)
        le=599,  # less than or equal (<=599)
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
        description="Number of retries on failure"
    )

    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom HTTP headers"
    )

    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates"
    )

    @validator('timeout')
    def timeout_must_be_reasonable(cls, v):
        """驗證 timeout 是否合理"""
        if v > 120:
            import warnings
            warnings.warn(
                f"Timeout of {v}s is very long. Consider using a shorter timeout.",
                UserWarning
            )
        return v

    @validator('headers')
    def headers_must_be_valid(cls, v):
        """驗證 headers 格式"""
        if v is not None:
            # 檢查是否有敏感資訊
            sensitive_keys = ['password', 'secret', 'token']
            for key in v.keys():
                if any(s in key.lower() for s in sensitive_keys):
                    logger.warning(f"Header '{key}' may contain sensitive information")
        return v

    class Config:
        # 生成 JSON Schema
        schema_extra = {
            "examples": [
                {
                    "url": "https://example.com",
                    "expected_status": 200,
                    "timeout": 30
                }
            ]
        }
```

**使用範例**：

```python
def execute_health_check(**kwargs) -> Dict[str, Any]:
    """執行健康檢查"""

    # 步驟 1: 驗證參數
    try:
        params = HealthCheckParams(**kwargs)
    except ValidationError as e:
        # Pydantic 提供結構化的錯誤訊息
        error_details = []
        for error in e.errors():
            field = error['loc'][0]
            message = error['msg']
            error_details.append(f"{field}: {message}")

        return {
            "is_healthy": False,
            "errors": error_details,
            "error_type": "VALIDATION_ERROR"
        }

    # 步驟 2: 執行檢查（參數已驗證）
    checker = WebHealthChecker(timeout=params.timeout)
    return checker.check(
        url=str(params.url),  # HttpUrl 需要轉換為 str
        expected_status=params.expected_status,
        retry_count=params.retry_count,
        headers=params.headers,
        verify_ssl=params.verify_ssl
    )
```

### 3.4.2 複雜參數類型

有時候參數不只是簡單的字串或數字，而是嵌套的結構。Pydantic 完全支援複雜類型。

**範例：批次健康檢查**

```python
class HealthCheckTarget(BaseModel):
    """單個檢查目標"""
    url: HttpUrl
    expected_status: int = 200
    name: Optional[str] = None  # 可選的名稱

class BatchHealthCheckParams(BaseModel):
    """批次健康檢查參數"""

    targets: List[HealthCheckTarget] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of targets to check"
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

    stop_on_first_failure: bool = Field(
        default=False,
        description="Stop execution if any check fails"
    )

    @validator('max_workers')
    def validate_max_workers(cls, v, values):
        """驗證 max_workers 與 targets 數量的關係"""
        if 'targets' in values:
            target_count = len(values['targets'])
            if v > target_count:
                # 自動調整
                return target_count
        return v
```

## 3.5 錯誤處理策略

專業的 Skills 能夠優雅地處理錯誤。讓我們深入探討如何設計健壯的錯誤處理機制。

### 3.5.1 錯誤分類

不是所有錯誤都應該被同等對待。根據錯誤的性質，我們可以採取不同的策略。

```python
from enum import Enum

class ErrorType(Enum):
    TRANSIENT = "transient"      # 可重試
    PERMANENT = "permanent"      # 不可重試
    PARTIAL = "partial"          # 部分失敗

class SkillError(Exception):
    """Skill 錯誤基類"""

    def __init__(self, message: str, error_type: ErrorType, details: dict = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}

class TransientError(SkillError):
    """暫時性錯誤（應重試）"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorType.TRANSIENT, details)

class PermanentError(SkillError):
    """永久性錯誤（不應重試）"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ErrorType.PERMANENT, details)
```

### 3.5.2 智能重試策略

```python
import time
import random
from typing import Callable, TypeVar
from functools import wraps

T = TypeVar('T')

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (TransientError,)
):
    """
    帶指數退避的重試裝飾器

    Args:
        max_retries: 最大重試次數
        base_delay: 基礎延遲時間（秒）
        max_delay: 最大延遲時間（秒）
        exponential_base: 指數基數（通常是 2）
        jitter: 是否添加隨機抖動
        exceptions: 需要重試的異常類型
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) reached for {func.__name__}. "
                            f"Last error: {e}"
                        )
                        raise

                    # 計算延遲時間
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    # 添加隨機抖動
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    time.sleep(delay)

                except Exception as e:
                    logger.error(f"Non-retryable error: {e}")
                    raise

            raise last_exception

        return wrapper
    return decorator
```

## 3.6 Skills 開發最佳實踐

經過多年的實踐，我們總結出以下最佳實踐。遵循這些原則，你的 Skills 將更健壯、更易維護。

### 3.6.1 單一職責原則（Single Responsibility Principle）

每個 Skill 應該只做一件事，並把它做好。

**✅ 好的設計**：

```python
# 分成多個專注的 Skills

def web_health_check(url: str) -> dict:
    """只做健康檢查"""
    return check_health(url)

def web_performance_test(url: str) -> dict:
    """只做性能測試"""
    return run_performance_test(url)

def seo_analyzer(url: str) -> dict:
    """只做 SEO 分析"""
    return analyze_seo(url)
```

### 3.6.2 可組合性（Composability）

設計可以互相組合的 Skills，創造更強大的功能。

```python
# 基礎 Skills（構建塊）

def fetch_webpage(url: str) -> str:
    """獲取網頁內容"""
    response = requests.get(url)
    return response.text

def parse_html(html: str) -> BeautifulSoup:
    """解析 HTML"""
    return BeautifulSoup(html, 'html.parser')

def extract_links(soup: BeautifulSoup) -> List[str]:
    """提取所有連結"""
    return [a['href'] for a in soup.find_all('a', href=True)]

# 組合成高階 Skills
def get_all_links(url: str) -> List[str]:
    """獲取頁面所有連結"""
    html = fetch_webpage(url)
    soup = parse_html(html)
    return extract_links(soup)
```

### 3.6.3 可測試性（Testability）

設計易於測試的 Skills。

```python
import pytest
from unittest.mock import Mock

class WebHealthChecker:
    """可測試的健康檢查器"""

    def __init__(self, http_client=None, timeout: int = 30):
        self.http_client = http_client or requests
        self.timeout = timeout

    def check(self, url: str) -> dict:
        """執行檢查"""
        response = self.http_client.get(url, timeout=self.timeout)
        return {
            'is_healthy': response.status_code == 200,
            'status_code': response.status_code
        }

# 測試
def test_health_checker_success():
    """測試成功情況"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_client.get.return_value = mock_response

    checker = WebHealthChecker(http_client=mock_client)
    result = checker.check("https://test.com")

    assert result['is_healthy'] is True
    assert result['status_code'] == 200
```

## 3.7 本章總結

恭喜！你已經掌握了 Claude Code Skills 的核心概念。讓我們回顧關鍵要點：

### 3.7.1 關鍵要點

✅ **SKILL.md 是核心**
- 結構化、完整的文檔
- 清晰的參數和返回值定義
- 豐富的範例和錯誤處理說明

✅ **三層漸進式揭露**
- Layer 1（發現層）：快速決策
- Layer 2（準備層）：參數準備
- Layer 3（執行層）：完整實作
- 節省 95% token 使用、降低成本、提升性能

✅ **完整的生命週期**
- 發現 → 準備 → 執行 → 回報 → 清理
- 每個階段有明確職責
- 理解流程有助於設計更好的 Skills

✅ **參數驗證**
- 使用 Pydantic 進行自動驗證
- 早期捕獲錯誤
- 提供清晰的錯誤訊息

✅ **錯誤處理**
- 分類錯誤（可恢復 vs. 永久性）
- 智能重試（指數退避 + 抖動）
- 結構化錯誤訊息

✅ **最佳實踐**
- 單一職責原則
- 可組合性設計
- 可測試性（依賴注入）
- 完整文檔

### 3.7.2 實踐檢查清單

在開始下一章之前，確保你能夠：

- [ ] 撰寫完整的 SKILL.md（包含所有必要章節）
- [ ] 理解三層漸進式揭露的設計原理和好處
- [ ] 說明 Skills 生命週期的五個階段
- [ ] 使用 Pydantic 實作參數驗證
- [ ] 設計錯誤分類和重試策略
- [ ] 編寫結構化、可操作的錯誤訊息
- [ ] 應用單一職責原則設計 Skills
- [ ] 創建可組合的 Skills
- [ ] 編寫可測試的代碼（使用依賴注入）
- [ ] 撰寫完整的 docstrings

### 3.7.3 下一章預告

第 4 章將深入探討 **Stagehand 瀏覽器自動化**——WebGuard 最重要的組件之一。你將學習：

- Stagehand 的 AI 驅動架構
- 自愈測試（self-healing tests）的原理
- 如何使用自然語言編寫測試
- 與傳統工具（Playwright, Selenium）的整合
- 實作複雜的瀏覽器自動化場景

Stagehand 是革命性的工具，它將 AI 的力量帶入瀏覽器自動化領域。準備好迎接令人興奮的旅程！

---

**本章代碼**

本章的完整代碼範例可在以下位置找到：
- `code-examples/chapter-03/parameter-validation/`
- `code-examples/chapter-03/error-handling/`
- `code-examples/chapter-03/best-practices/`

**延伸閱讀**

- Pydantic 文檔: https://docs.pydantic.dev
- Python 類型提示 (PEP 484): https://peps.python.org/pep-0484/
- 錯誤處理最佳實踐: https://docs.python-guide.org/writing/structure/

---

> *「The best error message is the one that never shows up.」 - Thomas Fuchs*
