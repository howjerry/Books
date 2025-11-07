# 第 4-10 章：完整大綱與關鍵內容

## 第 4 章：Stagehand 瀏覽器自動化實戰

### 章節目標
掌握 Stagehand 框架，實現 AI 驅動的瀏覽器自動化測試。

### 4.1 認識 Stagehand

#### 4.1.1 Stagehand vs. 傳統工具
```typescript
// 傳統 Playwright
await page.click('#login-button');
await page.fill('#username', 'test@example.com');

// Stagehand (AI-驅動)
await page.act("click the login button");
await page.act("enter email", { text: "test@example.com" });
```

#### 4.1.2 核心優勢
- **自愈能力**: 44% faster execution
- **語意理解**: 不依賴脆弱選擇器
- **上下文感知**: 90% reduction in context usage
- **CDP-native**: 直接與 Chrome DevTools Protocol 通訊

### 4.2 Stagehand 四大核心 API

#### 4.2.1 act() - 執行操作
```typescript
// 安裝
npm install @stagehand/browser

// 基礎使用
import { Stagehand } from "@stagehand/browser";

const stagehand = new Stagehand({
  env: "LOCAL",
  verbose: 1,
  headless: false
});

await stagehand.init();
const page = stagehand.page;

// 導航
await page.goto("https://example.com");

// 執行操作
await page.act("click the login button");
await page.act("fill in username", { text: "user@example.com" });
await page.act("fill in password", { text: "password123" });
await page.act("click submit");
```

#### 4.2.2 extract() - 提取資訊
```typescript
// 提取結構化數據
const data = await page.extract({
  username: "the logged-in username",
  balance: "the account balance",
  lastLogin: "the last login time"
});

// 複雜提取
const products = await page.extract({
  products: [
    {
      name: "product name",
      price: "product price",
      inStock: "whether in stock"
    }
  ],
  totalCount: "total number of products"
});
```

#### 4.2.3 observe() - 等待條件
```typescript
// 等待特定狀態
await page.observe("wait for the dashboard to load");
await page.observe("wait until the loading spinner disappears");
await page.observe("wait for the success message to appear");

// 組合使用
await page.act("click submit");
await page.observe("wait for confirmation dialog");
await page.act("click confirm");
```

#### 4.2.4 agent() - 自主執行
```typescript
// AI 自主完成複雜任務
await page.agent("complete the checkout process");
// AI 會自動:
// 1. 檢查購物車
// 2. 填寫配送資訊
// 3. 選擇付款方式
// 4. 確認訂單
```

### 4.3 實作登入測試 Skill

#### 4.3.1 Skill 定義
```markdown
# Browser Login Test

## Description
Automated login testing using Stagehand AI browser automation.

## Parameters
- `url`: Login page URL
- `username`: Test username
- `password`: Test password
- `expected_url`: Expected URL after successful login

## Implementation
Uses Stagehand to:
1. Navigate to login page
2. Enter credentials
3. Submit login form
4. Verify successful login
```

#### 4.3.2 Python 實作
```python
# src/skills/browser_login_test.py
import asyncio
import json
from typing import Dict, Any
from pathlib import Path

class BrowserLoginTester:
    """瀏覽器登入測試器"""

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def test_login(
        self,
        url: str,
        username: str,
        password: str,
        expected_url: str = None
    ) -> Dict[str, Any]:
        """
        測試登入流程

        Args:
            url: 登入頁面 URL
            username: 用戶名
            password: 密碼
            expected_url: 預期的登入後 URL

        Returns:
            測試結果
        """
        # 調用 Node.js Stagehand 腳本
        script_path = Path(__file__).parent / "stagehand_login.js"

        cmd = [
            "node",
            str(script_path),
            "--url", url,
            "--username", username,
            "--password", password
        ]

        if expected_url:
            cmd.extend(["--expected-url", expected_url])

        if self.headless:
            cmd.append("--headless")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return {
                "success": False,
                "error": stderr.decode()
            }

        result = json.loads(stdout.decode())
        return result


def execute_login_test(
    url: str,
    username: str,
    password: str,
    expected_url: str = None
) -> Dict[str, Any]:
    """Skill 入口函數"""
    tester = BrowserLoginTester()
    return asyncio.run(
        tester.test_login(url, username, password, expected_url)
    )
```

#### 4.3.3 Stagehand 腳本
```javascript
// src/skills/stagehand_login.js
const { Stagehand } = require("@stagehand/browser");
const { parseArgs } = require("node:util");

async function testLogin(options) {
  const stagehand = new Stagehand({
    env: "LOCAL",
    verbose: options.verbose ? 1 : 0,
    headless: options.headless
  });

  try {
    await stagehand.init();
    const page = stagehand.page;

    // 步驟 1: 導航到登入頁面
    await page.goto(options.url);

    // 步驟 2: 填寫憑證
    await page.act("enter username", { text: options.username });
    await page.act("enter password", { text: options.password });

    // 步驟 3: 提交表單
    await page.act("click login button");

    // 步驟 4: 等待登入完成
    await page.observe("wait for page to load after login");

    // 步驟 5: 驗證登入成功
    const result = await page.extract({
      isLoggedIn: "is the user logged in?",
      currentUrl: "what is the current URL?",
      username: "what username is displayed?",
      errorMessage: "is there an error message? if so, what is it?"
    });

    // 驗證預期 URL
    if (options.expectedUrl) {
      const urlMatch = result.currentUrl.includes(options.expectedUrl);
      result.urlMatch = urlMatch;
    }

    // 擷取截圖
    const screenshot = await page.screenshot({ encoding: "base64" });
    result.screenshot = screenshot;

    console.log(JSON.stringify({
      success: result.isLoggedIn && (result.urlMatch !== false),
      ...result
    }));

  } catch (error) {
    console.error(JSON.stringify({
      success: false,
      error: error.message,
      stack: error.stack
    }));
    process.exit(1);
  } finally {
    await stagehand.close();
  }
}

// 解析命令行參數
const { values } = parseArgs({
  options: {
    url: { type: "string" },
    username: { type: "string" },
    password: { type: "string" },
    "expected-url": { type: "string" },
    headless: { type: "boolean", default: true },
    verbose: { type: "boolean", default: false }
  }
});

testLogin(values);
```

### 4.4 處理複雜 UI 互動

#### 4.4.1 動態內容處理
```javascript
// 處理載入中狀態
await page.observe("wait until loading spinner disappears");

// 處理動態表單
await page.act("fill in the form", {
  text: JSON.stringify({
    name: "John Doe",
    email: "john@example.com",
    age: "30"
  })
});

// 處理彈窗
await page.observe("wait for popup to appear");
await page.act("click accept in the popup");
```

#### 4.4.2 文件上傳
```javascript
// 上傳單個文件
await page.act("upload profile picture", {
  file: "/path/to/image.jpg"
});

// 上傳多個文件
await page.act("upload documents", {
  files: [
    "/path/to/doc1.pdf",
    "/path/to/doc2.pdf"
  ]
});
```

#### 4.4.3 拖放操作
```javascript
// Stagehand 自動處理拖放
await page.act("drag the item from source to target");
await page.act("reorder the list by dragging item 3 to position 1");
```

### 4.5 自愈機制與錯誤恢復

#### 4.5.1 自動重試
```javascript
const stagehand = new Stagehand({
  env: "LOCAL",
  retries: 3,
  retryDelay: 1000
});

// Stagehand 自動重試失敗的操作
await page.act("click submit");  // 失敗時自動重試 3 次
```

#### 4.5.2 錯誤恢復策略
```javascript
async function robustBrowserTest(page) {
  try {
    // 主要流程
    await page.act("complete the form");

  } catch (error) {
    // 嘗試恢復
    console.log("Primary flow failed, trying alternative...");

    // 截圖當前狀態
    await page.screenshot({ path: "error-state.png" });

    // 嘗試替代方案
    await page.act("cancel and restart the form");

    // 重試
    await page.act("complete the form");
  }
}
```

### 4.6 WebGuard 瀏覽器測試模組

#### 4.6.1 模組架構
```
webguard/
├── src/
│   └── skills/
│       ├── browser/
│       │   ├── __init__.py
│       │   ├── login_test.py
│       │   ├── navigation_test.py
│       │   ├── form_test.py
│       │   └── e2e_test.py
│       └── stagehand/
│           ├── login.js
│           ├── navigation.js
│           ├── form.js
│           └── e2e.js
```

#### 4.6.2 完整 E2E 測試示例
```python
# src/skills/browser/e2e_test.py
class E2ETestSuite:
    """端對端測試套件"""

    async def test_complete_shopping_flow(
        self,
        base_url: str
    ) -> Dict[str, Any]:
        """測試完整購物流程"""

        results = {
            "steps": [],
            "overall_success": True
        }

        # 步驟 1: 登入
        login_result = await self.test_login(
            f"{base_url}/login",
            "test@example.com",
            "password123"
        )
        results["steps"].append(("login", login_result))

        if not login_result["success"]:
            results["overall_success"] = False
            return results

        # 步驟 2: 瀏覽產品
        browse_result = await self.test_product_browse(base_url)
        results["steps"].append(("browse", browse_result))

        # 步驟 3: 加入購物車
        cart_result = await self.test_add_to_cart()
        results["steps"].append(("add_to_cart", cart_result))

        # 步驟 4: 結帳
        checkout_result = await self.test_checkout()
        results["steps"].append(("checkout", checkout_result))

        # 步驟 5: 確認訂單
        confirm_result = await self.test_order_confirmation()
        results["steps"].append(("confirm", confirm_result))

        # 檢查所有步驟是否成功
        results["overall_success"] = all(
            step[1]["success"] for step in results["steps"]
        )

        return results
```

---

## 第 5 章：數據與文件處理自動化

### 5.1 Excel/CSV 數據處理 Skills

#### 5.1.1 Excel 處理
```python
import pandas as pd
from openpyxl import load_workbook
from typing import Dict, List, Any

class ExcelProcessor:
    """Excel 處理器"""

    def read_test_data(self, file_path: str) -> List[Dict]:
        """讀取測試數據"""
        df = pd.read_excel(file_path)
        return df.to_dict('records')

    def write_results(
        self,
        results: List[Dict],
        output_path: str
    ):
        """寫入測試結果"""
        df = pd.DataFrame(results)
        df.to_excel(output_path, index=False, engine='openpyxl')

    def validate_data(
        self,
        file_path: str,
        schema: Dict
    ) -> Dict[str, Any]:
        """驗證數據格式"""
        df = pd.read_excel(file_path)

        errors = []

        # 檢查必要欄位
        for col in schema.get('required_columns', []):
            if col not in df.columns:
                errors.append(f"缺少欄位: {col}")

        # 檢查數據類型
        for col, dtype in schema.get('column_types', {}).items():
            if col in df.columns:
                if not df[col].dtype == dtype:
                    errors.append(
                        f"欄位 {col} 類型錯誤: "
                        f"期望 {dtype}, 實際 {df[col].dtype}"
                    )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "row_count": len(df),
            "column_count": len(df.columns)
        }
```

### 5.2 PDF 文件處理與驗證

```python
import PyPDF2
from pdfminer.high_level import extract_text
from typing import Dict, Any

class PDFValidator:
    """PDF 驗證器"""

    def extract_text(self, pdf_path: str) -> str:
        """提取 PDF 文本"""
        return extract_text(pdf_path)

    def validate_content(
        self,
        pdf_path: str,
        expected_content: List[str]
    ) -> Dict[str, Any]:
        """驗證 PDF 內容"""
        text = self.extract_text(pdf_path)

        results = {
            "all_found": True,
            "missing": [],
            "found": []
        }

        for content in expected_content:
            if content in text:
                results["found"].append(content)
            else:
                results["missing"].append(content)
                results["all_found"] = False

        return results
```

---

## 第 6 章：API 測試與整合驗證

### 6.1 REST API 測試 Skills

```python
import requests
from typing import Dict, Any, Optional

class APITester:
    """API 測試器"""

    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url
        self.session = requests.Session()

        if auth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {auth_token}'
            })

    def test_endpoint(
        self,
        method: str,
        endpoint: str,
        expected_status: int = 200,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """測試 API 端點"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        response = self.session.request(
            method=method.upper(),
            url=url,
            json=json_data,
            params=params,
            timeout=30
        )

        return {
            "success": response.status_code == expected_status,
            "status_code": response.status_code,
            "response_time_ms": response.elapsed.total_seconds() * 1000,
            "response_body": response.json() if response.content else None
        }
```

---

## 第 7 章：Skills 進階模式與組合技巧

### 7.1 Skill 組合模式

```python
from typing import List, Dict, Any

class SkillOrchestrator:
    """Skill 編排器"""

    def __init__(self):
        self.skills = {}

    def register(self, name: str, skill_func):
        """註冊 Skill"""
        self.skills[name] = skill_func

    async def execute_sequence(
        self,
        sequence: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """順序執行 Skills"""
        results = []

        for step in sequence:
            skill_name = step["skill"]
            params = step.get("params", {})

            if skill_name not in self.skills:
                raise ValueError(f"未知 Skill: {skill_name}")

            result = await self.skills[skill_name](**params)
            results.append({
                "skill": skill_name,
                "result": result
            })

            # 如果失敗且設置了 stop_on_error
            if not result.get("success") and step.get("stop_on_error"):
                break

        return results

    async def execute_parallel(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """並行執行 Skills"""
        import asyncio

        async def run_task(task):
            skill_name = task["skill"]
            params = task.get("params", {})
            return await self.skills[skill_name](**params)

        results = await asyncio.gather(
            *[run_task(task) for task in tasks],
            return_exceptions=True
        )

        return results
```

---

## 第 8 章：測試自動化與 CI/CD 整合

### 8.1 GitHub Actions 配置

```yaml
# .github/workflows/webguard-tests.yml
name: WebGuard Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 */6 * * *'  # 每 6 小時

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
          npm install

      - name: Run WebGuard tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          DATABASE_URL: postgresql://postgres:postgres@localhost/webguard
        run: |
          poetry run pytest tests/ -v --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

      - name: Generate Allure report
        if: always()
        run: |
          poetry run pytest tests/ --alluredir=allure-results
          allure generate allure-results -o allure-report

      - name: Upload Allure report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: allure-report
          path: allure-report
```

---

## 第 9 章：完整測試系統架構（WebGuard）

### 9.1 四層架構設計

```
┌─────────────────────────────────────────────────────────┐
│              編排層 (Orchestration Layer)               │
│  - Task Scheduler (APScheduler)                        │
│  - Queue Manager (Celery + Redis)                     │
│  - Resource Allocator                                  │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              執行層 (Execution Layer)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │  Browser     │ │  API         │ │  Data        │   │
│  │  Skills      │ │  Skills      │ │  Skills      │   │
│  └──────────────┘ └──────────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              存儲層 (Storage Layer)                     │
│  - PostgreSQL (測試結果、配置)                         │
│  - Redis (快取、佇列)                                  │
│  - MinIO/S3 (截圖、日誌、報告)                        │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              報告層 (Reporting Layer)                   │
│  - Allure (測試報告)                                   │
│  - Grafana (儀表板)                                    │
│  - Prometheus (指標)                                   │
│  - Notification (Slack/Email)                          │
└─────────────────────────────────────────────────────────┘
```

### 9.2 PostgreSQL Schema

```sql
-- 測試執行記錄
CREATE TABLE test_executions (
    id SERIAL PRIMARY KEY,
    test_suite_id INTEGER NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    total_tests INTEGER,
    passed_tests INTEGER,
    failed_tests INTEGER,
    skipped_tests INTEGER,
    execution_time_ms INTEGER,
    triggered_by VARCHAR(100),
    CONSTRAINT fk_test_suite
        FOREIGN KEY (test_suite_id)
        REFERENCES test_suites(id)
);

-- 測試結果詳情
CREATE TABLE test_results (
    id SERIAL PRIMARY KEY,
    execution_id INTEGER NOT NULL,
    test_name VARCHAR(255) NOT NULL,
    skill_name VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    execution_time_ms INTEGER,
    screenshot_url VARCHAR(500),
    log_url VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_execution
        FOREIGN KEY (execution_id)
        REFERENCES test_executions(id)
);

-- 創建索引
CREATE INDEX idx_test_executions_started ON test_executions(started_at DESC);
CREATE INDEX idx_test_results_execution ON test_results(execution_id);
CREATE INDEX idx_test_results_status ON test_results(status);
```

---

## 第 10 章：企業部署、安全與 MCP 生態

### 10.1 安全性最佳實踐

```python
# 密鑰管理
from cryptography.fernet import Fernet
import os

class SecureConfig:
    """安全配置管理"""

    def __init__(self):
        self.cipher = Fernet(os.environ['ENCRYPTION_KEY'].encode())

    def encrypt(self, value: str) -> str:
        """加密敏感數據"""
        return self.cipher.encrypt(value.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """解密數據"""
        return self.cipher.decrypt(encrypted.encode()).decode()

# API 金鑰輪換
class APIKeyRotator:
    """API 金鑰輪換器"""

    def rotate_key(self):
        """輪換 API 金鑰"""
        # 1. 生成新金鑰
        # 2. 更新環境變數
        # 3. 重啟服務
        # 4. 撤銷舊金鑰
        pass
```

### 10.2 MCP 整合

```python
# MCP Server 範例
from mcp import Server, Tool

class WebGuardMCPServer(Server):
    """WebGuard MCP Server"""

    def __init__(self):
        super().__init__("webguard", "1.0.0")

    @Tool(
        name="run_health_check",
        description="Run website health check"
    )
    async def run_health_check(self, url: str) -> dict:
        """執行健康檢查"""
        from src.skills.web_health_check import execute_health_check
        return execute_health_check(url)

    @Tool(
        name="run_e2e_test",
        description="Run end-to-end test"
    )
    async def run_e2e_test(self, test_suite: str) -> dict:
        """執行 E2E 測試"""
        # 實作...
        pass
```

---

## 附錄大綱

### 附錄 A：MCP 完整規範
- A.1 MCP 協定概述
- A.2 Server 實作指南
- A.3 Client 整合
- A.4 完整範例

### 附錄 B：Docker 配置
- B.1 Dockerfile 優化
- B.2 Docker Compose 完整配置
- B.3 Kubernetes 部署
- B.4 生產環境清單

### 附錄 C：測試工具對比
| 工具 | 類型 | 優勢 | 劣勢 | 適用場景 |
|------|------|------|------|----------|
| Stagehand | AI 驅動 | 自愈、語意理解 | 新工具 | 複雜 UI |
| Playwright | 傳統 | 成熟、快速 | 脆弱 | API 測試 |
| Selenium | 傳統 | 廣泛支持 | 慢、脆弱 | 舊專案 |

### 附錄 D：最佳實踐清單
- [ ] Skills 設計檢查清單
- [ ] 安全審查清單
- [ ] 性能優化清單
- [ ] 部署前檢查清單
- [ ] 監控配置清單

---

**所有章節狀態**: 大綱完成，待完整撰寫
