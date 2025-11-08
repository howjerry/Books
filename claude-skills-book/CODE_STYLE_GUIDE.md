# Claude Code Skills 技術書 - 代碼風格指南

## 目標

確保全書代碼範例：
- ✅ 一致性：統一的格式和命名
- ✅ 可讀性：清晰的結構和註釋
- ✅ 可執行性：讀者可以直接複製使用
- ✅ 專業性：符合業界最佳實踐

---

## Python 代碼規範

### 1. 格式化工具

- **Black**: 自動格式化（line length: 88）
- **Ruff**: Linting 和快速檢查
- **isort**: Import 排序

### 2. 命名規範

```python
# ✅ 正確命名
class HealthChecker:                    # PascalCase for classes
    def check_website(self, url: str):  # snake_case for functions
        max_retries = 3                 # snake_case for variables
        API_TIMEOUT = 30                # UPPER_SNAKE_CASE for constants

# ❌ 錯誤命名
class healthChecker:                    # Wrong: should be PascalCase
    def CheckWebsite(self, URL):        # Wrong: should be snake_case
        MaxRetries = 3                  # Wrong: should be lowercase
```

### 3. 類型註解

```python
# ✅ 完整類型註解
from typing import Dict, List, Optional

def execute_skill(
    url: str,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """執行 Skill 並返回結果"""
    pass

# ❌ 缺少類型註解
def execute_skill(url, timeout=30, headers=None):  # Wrong: no type hints
    pass
```

### 4. Docstring 格式

```python
def health_check(url: str, timeout: int = 30) -> Dict[str, Any]:
    """
    檢查網站健康狀態

    Args:
        url: 要檢查的網站 URL
        timeout: 請求超時時間（秒）

    Returns:
        包含健康狀態的字典：
        {
            "status": "ok" | "error",
            "response_time": float,
            "status_code": int
        }

    Raises:
        ValueError: 如果 URL 格式無效
        TimeoutError: 如果請求超時

    Example:
        >>> result = health_check("https://example.com")
        >>> print(result["status"])
        'ok'
    """
    pass
```

### 5. Import 順序

```python
# 1. 標準庫
import os
import sys
from typing import Dict, List

# 2. 第三方庫
import requests
from pydantic import BaseModel

# 3. 本地模組
from src.core.executor import SkillExecutor
from src.utils.logger import setup_logger
```

### 6. 錯誤處理

```python
# ✅ 具體的異常處理
try:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
except requests.Timeout:
    logger.error(f"Request timeout for {url}")
    raise TimeoutError(f"Request to {url} timed out after {timeout}s")
except requests.HTTPError as e:
    logger.error(f"HTTP error: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise RuntimeError(f"Failed to check {url}: {str(e)}")

# ❌ 過於寬泛的異常處理
try:
    response = requests.get(url)
except Exception:  # Too broad!
    pass  # Silent failure!
```

### 7. 上下文管理器

```python
# ✅ 使用上下文管理器
async with Stagehand() as stagehand:
    page = await stagehand.page()
    result = await page.extract(...)
    # 自動清理資源

# ✅ 自定義上下文管理器
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_browser(headless: bool = True):
    browser = await launch_browser(headless=headless)
    try:
        yield browser
    finally:
        await browser.close()
```

---

## TypeScript/JavaScript 代碼規範

### 1. 格式化工具

- **Prettier**: 自動格式化
- **ESLint**: 代碼檢查

### 2. 命名規範

```typescript
// ✅ 正確命名
class StagehandLogger {              // PascalCase for classes
  logAction(action: string): void {  // camelCase for methods
    const startTime = Date.now();   // camelCase for variables
    const MAX_RETRIES = 3;           // UPPER_SNAKE_CASE for constants
  }
}

// ❌ 錯誤命名
class stagehand_logger {             // Wrong: should be PascalCase
  LogAction(Action: string) {        // Wrong: should be camelCase
    const StartTime = Date.now();    // Wrong: should be camelCase
  }
}
```

### 3. 類型定義

```typescript
// ✅ 明確的類型定義
interface LoginTestOptions {
  url: string;
  username: string;
  password: string;
  timeout?: number;
  headless?: boolean;
}

async function testLogin(options: LoginTestOptions): Promise<TestResult> {
  // Implementation
}

// ❌ 缺少類型定義
async function testLogin(options) {  // Wrong: missing type
  // Implementation
}
```

### 4. 註釋規範

```typescript
/**
 * 執行登入測試
 *
 * @param options - 測試選項
 * @param options.url - 登入頁面 URL
 * @param options.username - 測試用戶名
 * @param options.password - 測試密碼
 * @returns 測試結果對象
 * @throws {Error} 當測試執行失敗時
 *
 * @example
 * ```typescript
 * const result = await testLogin({
 *   url: "https://example.com/login",
 *   username: "test@example.com",
 *   password: "password123"
 * });
 * ```
 */
async function testLogin(options: LoginTestOptions): Promise<TestResult> {
  // Implementation
}
```

### 5. Async/Await 使用

```typescript
// ✅ 正確的 async/await
async function performTest(): Promise<void> {
  try {
    await page.goto(url);
    await page.act("click login");
    const result = await page.extract({ ... });
  } catch (error) {
    console.error("Test failed:", error);
    throw error;
  } finally {
    await cleanup();
  }
}

// ❌ 錯誤的 Promise 處理
function performTest() {
  page.goto(url).then(() => {
    return page.act("click login");
  }).then(() => {
    return page.extract({ ... });
  });  // Wrong: Promise chain instead of async/await
}
```

### 6. 錯誤處理

```typescript
// ✅ 具體的錯誤類型
class TestTimeoutError extends Error {
  constructor(message: string, public readonly timeout: number) {
    super(message);
    this.name = "TestTimeoutError";
  }
}

async function runTest(): Promise<TestResult> {
  try {
    const result = await executeTest();
    return result;
  } catch (error) {
    if (error instanceof TestTimeoutError) {
      logger.error(`Test timed out after ${error.timeout}ms`);
      throw error;
    } else if (error instanceof NetworkError) {
      logger.error("Network error:", error);
      throw error;
    } else {
      logger.error("Unexpected error:", error);
      throw new Error(`Test failed: ${error.message}`);
    }
  }
}
```

---

## 共通規範

### 1. 註釋風格

```python
# ✅ 清晰的註釋
# 檢查 URL 格式是否有效
if not url.startswith(("http://", "https://")):
    raise ValueError(f"Invalid URL format: {url}")

# ❌ 無用的註釋
# 這是一個 if 語句
if not url.startswith(("http://", "https://")):
    raise ValueError(f"Invalid URL format: {url}")
```

### 2. 魔法數字

```python
# ✅ 使用常數
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
BATCH_SIZE = 100

def check_website(url: str, timeout: int = DEFAULT_TIMEOUT):
    for attempt in range(MAX_RETRIES):
        ...

# ❌ 魔法數字
def check_website(url: str, timeout: int = 30):  # What's 30?
    for attempt in range(3):  # Why 3?
        ...
```

### 3. 函數長度

```python
# ✅ 適當的函數長度（< 50 行）
def execute_health_check(url: str) -> Dict[str, Any]:
    """執行健康檢查"""
    validate_url(url)
    response = send_request(url)
    metrics = calculate_metrics(response)
    return format_result(metrics)

# ❌ 過長的函數（> 100 行）
def execute_health_check(url: str):
    # ... 200 lines of code ...
    # Should be split into smaller functions!
```

### 4. 代碼組織

```python
# ✅ 良好的組織
class HealthChecker:
    """網站健康檢查器"""

    # 1. 類變數
    DEFAULT_TIMEOUT = 30

    # 2. 初始化
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout

    # 3. 公開方法
    def check(self, url: str) -> Dict[str, Any]:
        """執行檢查"""
        return self._execute_check(url)

    # 4. 私有方法
    def _execute_check(self, url: str) -> Dict[str, Any]:
        """內部執行邏輯"""
        pass

    # 5. 靜態方法
    @staticmethod
    def validate_url(url: str) -> bool:
        """驗證 URL 格式"""
        pass
```

---

## 代碼範例模板

### Python Skill 範例模板

```python
#!/usr/bin/env python3
"""
Skill Name: [技能名稱]
Description: [簡短描述]
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SkillNameExecutor:
    """[技能] 執行器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化執行器

        Args:
            config: 可選的配置參數
        """
        self.config = config or {}

    async def execute(self, **params: Any) -> Dict[str, Any]:
        """
        執行技能

        Args:
            **params: 技能參數

        Returns:
            執行結果

        Raises:
            ValueError: 參數驗證失敗
            RuntimeError: 執行失敗
        """
        try:
            # 1. 驗證參數
            self._validate_params(params)

            # 2. 執行主邏輯
            result = await self._execute_main_logic(params)

            # 3. 格式化結果
            return self._format_result(result)

        except Exception as e:
            logger.error(f"Skill execution failed: {e}", exc_info=True)
            raise

    def _validate_params(self, params: Dict[str, Any]) -> None:
        """驗證參數"""
        pass

    async def _execute_main_logic(self, params: Dict[str, Any]) -> Any:
        """主要執行邏輯"""
        pass

    def _format_result(self, result: Any) -> Dict[str, Any]:
        """格式化結果"""
        return {"success": True, "data": result}


def execute_skill(**params: Any) -> Dict[str, Any]:
    """
    Skill 入口函數

    這是 Claude 調用的主要函數
    """
    import asyncio
    executor = SkillNameExecutor()
    return asyncio.run(executor.execute(**params))


if __name__ == "__main__":
    # 測試代碼
    result = execute_skill(param1="value1")
    print(result)
```

### TypeScript Stagehand 範例模板

```typescript
/**
 * Skill Name: [技能名稱]
 * Description: [簡短描述]
 */
import { Stagehand } from "@browserbasehq/stagehand";

interface SkillOptions {
  url: string;
  timeout?: number;
  headless?: boolean;
}

interface SkillResult {
  success: boolean;
  data?: any;
  error?: string;
}

/**
 * 執行 [技能名稱]
 *
 * @param options - 技能選項
 * @returns 執行結果
 */
async function executeSkill(options: SkillOptions): Promise<SkillResult> {
  const stagehand = new Stagehand({
    env: "LOCAL",
    headless: options.headless ?? true,
    verbose: 0
  });

  try {
    // 1. 初始化
    await stagehand.init();
    const page = stagehand.page;

    // 2. 主要邏輯
    await page.goto(options.url);
    const result = await performMainLogic(page);

    // 3. 返回結果
    return {
      success: true,
      data: result
    };

  } catch (error) {
    console.error("Skill execution failed:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error)
    };

  } finally {
    // 4. 清理
    await stagehand.close();
  }
}

async function performMainLogic(page: any): Promise<any> {
  // 實作主要邏輯
  return {};
}

// 導出主函數
export { executeSkill };
```

---

## 代碼審查檢查清單

在提交代碼前，確認：

### Python
- [ ] 使用 Black 格式化（`black .`）
- [ ] 通過 Ruff 檢查（`ruff check .`）
- [ ] 使用 isort 排序 imports（`isort .`）
- [ ] 所有函數有類型註解
- [ ] 所有公開函數有 docstring
- [ ] 無 `# type: ignore` 註釋（除非必要）
- [ ] 錯誤處理具體且有意義

### TypeScript
- [ ] 使用 Prettier 格式化（`prettier --write .`）
- [ ] 通過 ESLint 檢查（`eslint .`）
- [ ] 所有函數有類型定義
- [ ] 所有導出函數有 JSDoc 註釋
- [ ] 使用 async/await 而非 Promise chains
- [ ] 錯誤類型明確

### 共通
- [ ] 無魔法數字（使用命名常數）
- [ ] 函數長度合理（< 50 行）
- [ ] 變數命名清晰
- [ ] 註釋有意義（解釋為什麼，而非是什麼）
- [ ] 可以直接執行（無語法錯誤）

---

## 工具配置

### pyproject.toml

```toml
[tool.black]
line-length = 88
target-version = ['py310', 'py311']

[tool.isort]
profile = "black"
line_length = 88

[tool.ruff]
line-length = 88
target-version = "py310"
select = ["E", "F", "I", "N", "W", "UP"]
```

### .prettierrc.json

```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

---

**版本**: 1.0.0
**最後更新**: 2025-11-08
**維護者**: Claude (總編輯)
