# 第 2 章：開發環境設置與第一個 Skill

*本章內容*
- 設置完整的開發環境
- 配置 Claude API 和認證
- 創建第一個 Skill：網站健康檢查
- 建立 WebGuard 專案的基礎結構
- 運行和調試你的 Skill

---

理論已經足夠，現在是動手實作的時候了。在這一章，你將設置完整的開發環境，並創建你的第一個 Claude Skill。到本章結束時，你將擁有一個可運行的 Skill，並看到 AI 自動化的實際效果。

記住：學習新技術最好的方式是動手實作。不要只是閱讀代碼——實際運行它、修改它、破壞它，然後修復它。這個過程會讓你真正理解 Skills 的工作原理。

## 2.1 開發環境設置

### 2.1.1 系統需求檢查

在開始之前，確認你的系統符合以下需求：

**硬體需求**
- CPU：多核處理器（推薦 4 核心以上）
- RAM：最少 8GB（推薦 16GB）
- 儲存空間：至少 10GB 可用空間
- 網路：穩定的網際網路連接

**作業系統**
- macOS 10.15 (Catalina) 或更新
- Ubuntu 20.04 LTS 或更新
- Windows 10/11 with WSL2

💡 **提示**：本書的範例在 macOS 和 Linux 上測試。Windows 用戶建議使用 WSL2 以獲得最佳體驗。

**檢查你的系統**

```bash
# macOS/Linux
uname -a
free -h  # 檢查記憶體
df -h    # 檢查儲存空間

# Windows (PowerShell)
systeminfo
```

### 2.1.2 安裝 Python

Claude Skills 主要使用 Python。我們需要 Python 3.10 或更新版本。

**檢查現有 Python 版本**

```bash
python3 --version
# 應該顯示 Python 3.10.x 或更新
```

**安裝 Python（如果需要）**

**macOS（使用 Homebrew）**
```bash
# 安裝 Homebrew（如果尚未安裝）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝 Python
brew install python@3.11
```

**Ubuntu/Debian**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

**驗證安裝**
```bash
python3 --version
pip3 --version
```

### 2.1.3 安裝 Node.js

雖然 Skills 可以純粹用 Python 開發，但許多工具（特別是 Stagehand）需要 Node.js。

**推薦使用 nvm（Node Version Manager）**

```bash
# 安裝 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# 重新載入 shell 配置
source ~/.bashrc  # 或 ~/.zshrc (macOS)

# 安裝 Node.js LTS
nvm install --lts
nvm use --lts

# 驗證安裝
node --version  # 應該 >= 18.0
npm --version   # 應該 >= 9.0
```

**直接安裝（替代方案）**

**macOS**
```bash
brew install node
```

**Ubuntu**
```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2.1.4 配置 Claude API

要使用 Claude Skills，你需要 Anthropic API 金鑰。

**步驟 1：註冊 Anthropic 帳號**

1. 訪問 https://console.anthropic.com
2. 註冊新帳號或登入
3. 完成電子郵件驗證

**步驟 2：獲取 API 金鑰**

1. 進入 Console 後，點擊 "API Keys"
2. 點擊 "Create Key"
3. 給金鑰一個描述性名稱（如 "WebGuard Development"）
4. 複製生成的 API 金鑰（以 `sk-ant-` 開頭）

⚠️ **安全提醒**：
- 永遠不要將 API 金鑰提交到版本控制
- 不要在代碼中硬編碼金鑰
- 定期輪換金鑰
- 為不同環境使用不同的金鑰

**步驟 3：配置環境變數**

創建一個環境配置檔案：

```bash
# 在你的 home 目錄創建 .anthropic 配置
mkdir -p ~/.anthropic
touch ~/.anthropic/config
```

編輯配置檔案：

```bash
# ~/.anthropic/config
export ANTHROPIC_API_KEY="sk-ant-your-actual-key-here"
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"
```

將配置載入到你的 shell：

```bash
# 將這行加入到 ~/.bashrc 或 ~/.zshrc
source ~/.anthropic/config

# 立即生效
source ~/.bashrc  # 或 ~/.zshrc
```

**驗證 API 配置**

```bash
# 測試 API 金鑰是否正確設置
python3 << EOF
import os
key = os.environ.get('ANTHROPIC_API_KEY')
if key:
    print(f"✓ API Key 已設置: {key[:10]}...")
else:
    print("✗ API Key 未設置")
EOF
```

**步驟 4：安裝 Anthropic SDK**

```bash
pip3 install anthropic
```

**測試 API 連接**

創建一個簡單的測試腳本：

```python
# test_api.py
import anthropic
import os

def test_claude_connection():
    """測試 Claude API 連接"""
    try:
        client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Hello, WebGuard!' in one sentence."
                }
            ]
        )

        print(f"✓ API 連接成功!")
        print(f"Claude 回應: {message.content[0].text}")
        return True

    except Exception as e:
        print(f"✗ API 連接失敗: {str(e)}")
        return False

if __name__ == "__main__":
    test_claude_connection()
```

執行測試：

```bash
python3 test_api.py
```

預期輸出：
```
✓ API 連接成功!
Claude 回應: Hello, WebGuard!
```

### 2.1.5 安裝開發工具

**必要工具**

```bash
# Git（版本控制）
# macOS
brew install git

# Ubuntu
sudo apt install git

# 驗證
git --version
```

**推薦 IDE / 編輯器**

選擇以下其一：

1. **VS Code**（推薦）
   ```bash
   # macOS
   brew install --cask visual-studio-code

   # 安裝推薦擴充套件
   code --install-extension ms-python.python
   code --install-extension anthropic.claude-vscode
   ```

2. **PyCharm Community Edition**
   ```bash
   brew install --cask pycharm-ce
   ```

3. **Cursor**（AI 輔助編輯器）
   - 下載自 https://cursor.sh

**虛擬環境管理**

```bash
# 安裝 pipx（用於管理 Python 工具）
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# 安裝 poetry（依賴管理）
pipx install poetry
```

### 2.1.6 驗證完整環境

創建一個驗證腳本確保所有工具正確安裝：

```python
# verify_environment.py
import sys
import subprocess
import os

def check_command(command, min_version=None):
    """檢查命令是否可用"""
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True
        )
        version = result.stdout.strip() or result.stderr.strip()
        print(f"✓ {command}: {version.split()[0]}")
        return True
    except FileNotFoundError:
        print(f"✗ {command}: 未安裝")
        return False

def check_python_package(package):
    """檢查 Python 套件是否安裝"""
    try:
        __import__(package)
        print(f"✓ Python 套件 '{package}': 已安裝")
        return True
    except ImportError:
        print(f"✗ Python 套件 '{package}': 未安裝")
        return False

def check_env_var(var_name):
    """檢查環境變數"""
    value = os.environ.get(var_name)
    if value:
        # 隱藏完整金鑰
        display = f"{value[:10]}..." if len(value) > 10 else value
        print(f"✓ 環境變數 {var_name}: {display}")
        return True
    else:
        print(f"✗ 環境變數 {var_name}: 未設置")
        return False

def main():
    print("=" * 50)
    print("WebGuard 開發環境驗證")
    print("=" * 50)

    results = []

    print("\n【基礎工具】")
    results.append(check_command("python3"))
    results.append(check_command("pip3"))
    results.append(check_command("node"))
    results.append(check_command("npm"))
    results.append(check_command("git"))

    print("\n【Python 套件】")
    results.append(check_python_package("anthropic"))

    print("\n【環境變數】")
    results.append(check_env_var("ANTHROPIC_API_KEY"))

    print("\n" + "=" * 50)
    success_count = sum(results)
    total_count = len(results)

    if success_count == total_count:
        print(f"✓ 所有檢查通過! ({success_count}/{total_count})")
        print("你已經準備好開始開發 Skills 了!")
        return 0
    else:
        print(f"⚠ 部分檢查失敗 ({success_count}/{total_count})")
        print("請參考本章節內容安裝缺少的工具")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

執行驗證：

```bash
python3 verify_environment.py
```

如果所有檢查都通過，你就準備好了！

## 2.2 創建 WebGuard 專案

### 2.2.1 專案結構規劃

讓我們建立 WebGuard 專案的目錄結構。良好的專案組織是成功的基礎。

**最終專案結構預覽**

```
webguard/
├── .claude/                    # Claude Skills 配置
│   └── skills/                 # Skills 定義
│       ├── web_health_check/
│       ├── browser_test/
│       └── api_test/
├── src/                        # 源代碼
│   ├── core/                   # 核心邏輯
│   ├── skills/                 # Skill 實作
│   ├── reporters/              # 報告生成器
│   └── utils/                  # 工具函數
├── tests/                      # 測試代碼
├── config/                     # 配置檔案
├── data/                       # 測試數據
├── reports/                    # 測試報告輸出
├── docker/                     # Docker 配置
├── docs/                       # 文檔
├── pyproject.toml              # Python 依賴管理
├── package.json                # Node.js 依賴管理
├── .env.example                # 環境變數範本
├── .gitignore                  # Git 忽略規則
└── README.md                   # 專案說明
```

### 2.2.2 初始化專案

**步驟 1：創建專案目錄**

```bash
# 創建主目錄
mkdir -p ~/projects/webguard
cd ~/projects/webguard

# 創建子目錄
mkdir -p .claude/skills
mkdir -p src/{core,skills,reporters,utils}
mkdir -p tests
mkdir -p config
mkdir -p data
mkdir -p reports
mkdir -p docker
mkdir -p docs
```

**步驟 2：初始化 Git**

```bash
git init
git branch -M main
```

**步驟 3：創建 .gitignore**

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 環境變數
.env
.env.local
.env.*.local

# 報告和數據
reports/*.html
reports/*.json
data/*.db
data/*.sqlite

# 臨時檔案
*.log
*.tmp
.DS_Store

# 敏感資訊
config/secrets.yml
*.key
*.pem
EOF
```

**步驟 4：初始化 Python 專案**

```bash
poetry init
```

按照提示填寫資訊：

```
Package name [webguard]: webguard
Version [0.1.0]: 0.1.0
Description []: AI-powered web testing and monitoring system
Author: [Your Name]
License []: MIT
Compatible Python versions [^3.11]: ^3.10

Would you like to define your main dependencies interactively? (yes/no) [yes] no
Would you like to define your development dependencies interactively? (yes/no) [yes] no
```

**步驟 5：添加依賴套件**

```bash
# 核心依賴
poetry add anthropic
poetry add python-dotenv
poetry add pydantic
poetry add requests
poetry add beautifulsoup4
poetry add lxml

# 開發依賴
poetry add --group dev pytest
poetry add --group dev pytest-asyncio
poetry add --group dev black
poetry add --group dev flake8
poetry add --group dev mypy
```

**步驟 6：初始化 Node.js 專案**

```bash
npm init -y
npm install --save-dev @stagehand/browser
```

**步驟 7：創建環境變數範本**

```bash
cat > .env.example << 'EOF'
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Application
APP_ENV=development
LOG_LEVEL=INFO

# Database (後續章節會用到)
DATABASE_URL=postgresql://localhost/webguard

# Browserbase (選用)
BROWSERBASE_API_KEY=
BROWSERBASE_PROJECT_ID=
EOF
```

複製並編輯實際的 .env 檔案：

```bash
cp .env.example .env
# 編輯 .env 填入你的實際 API 金鑰
```

### 2.2.3 創建基礎配置

**config/settings.py**

```python
"""
WebGuard 配置管理
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """應用程式設定"""

    # Anthropic API
    anthropic_api_key: str
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # 應用程式
    app_env: str = "development"
    log_level: str = "INFO"

    # 路徑
    reports_dir: Path = PROJECT_ROOT / "reports"
    data_dir: Path = PROJECT_ROOT / "data"

    # 測試配置
    default_timeout: int = 30
    max_retries: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全域設定實例
settings = Settings()


def ensure_directories():
    """確保必要目錄存在"""
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)


# 初始化時創建目錄
ensure_directories()
```

**src/utils/logger.py**

```python
"""
日誌工具
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """設置日誌記錄器"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 如果已經有 handlers，不要重複添加
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger
```

**步驟 8：創建主 README**

```bash
cat > README.md << 'EOF'
# WebGuard

AI-powered web testing and monitoring system built with Claude Skills.

## Features

- 🤖 AI-driven browser automation
- 🔍 Intelligent web health checks
- 📊 Comprehensive test reporting
- 🐳 Docker support
- 🔄 CI/CD ready

## Quick Start

1. Install dependencies:
   ```bash
   poetry install
   npm install
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. Run your first test:
   ```bash
   poetry run python examples/health_check.py
   ```

## Documentation

See `docs/` directory for detailed documentation.

## License

MIT
EOF
```

**步驟 9：初始提交**

```bash
git add .
git commit -m "Initial WebGuard project setup"
```

## 2.3 創建第一個 Skill
> 💡 **進階閱讀**：本節介紹基礎 Skill 結構。關於 SKILL.md 的完整語法規範、參數驗證、錯誤處理等進階主題，詳見 **Chapter 3**。
：網站健康檢查

現在環境已經準備好，讓我們創建第一個真正的 Skill！

### 2.3.1 Skill 設計

我們的第一個 Skill 將執行基本的網站健康檢查：

**功能需求**：
1. 檢查網站是否可訪問
2. 測量回應時間
3. 驗證 HTTP 狀態碼
4. 檢查頁面標題
5. 驗證關鍵元素存在

**輸入參數**：
- `url`：要檢查的網站網址
- `expected_status`：預期的 HTTP 狀態碼（預設 200）
- `timeout`：最大等待時間（秒）

**輸出**：
- 健康狀態（健康/不健康）
- 詳細檢查結果
- 效能指標

### 2.3.2 創建 Skill 定義

Claude Skills 使用 `.claude/skills/` 目錄來組織 Skills。每個 Skill 通常包含：
- `SKILL.md`：Skill 定義和說明
- `skill.py` 或 `skill.js`：實際執行邏輯

**創建目錄結構**

```bash
mkdir -p .claude/skills/web_health_check
```

**創建 SKILL.md**

```.claude/skills/web_health_check/SKILL.md
# Web Health Check Skill

## Description
Performs comprehensive health checks on websites, including accessibility, response time, HTTP status, and basic content validation.

## When to use
- Verify website is accessible
- Check website performance
- Validate deployment success
- Monitor website uptime
- Pre-test website before running detailed tests

## Parameters
- `url` (required): The website URL to check
- `expected_status` (optional): Expected HTTP status code (default: 200)
- `timeout` (optional): Maximum wait time in seconds (default: 30)

## Returns
- `is_healthy`: Boolean indicating if the website is healthy
- `status_code`: HTTP status code
- `response_time_ms`: Response time in milliseconds
- `page_title`: The HTML page title
- `errors`: List of any errors encountered

## Implementation
This skill uses the following approach:
1. Send HTTP request to the URL
2. Measure response time
3. Validate status code
4. Parse HTML to extract title and verify basic structure
5. Return comprehensive health report

## Examples

### Example 1: Basic health check
```yaml
url: "https://example.com"
```

Expected output:
```json
{
  "is_healthy": true,
  "status_code": 200,
  "response_time_ms": 245,
  "page_title": "Example Domain",
  "errors": []
}
```

### Example 2: Check with custom status code
```yaml
url: "https://example.com/api"
expected_status: 201
timeout: 10
```

## Error handling
- Network errors: Retry up to 3 times with exponential backoff
- Timeout errors: Report timeout and partial results if available
- Invalid URL: Return error immediately without retry
- Unexpected status code: Mark as unhealthy but return full details

## Dependencies
- requests library for HTTP calls
- beautifulsoup4 for HTML parsing
- Standard library time module for timing

## Version
1.0.0

## Tags
web, health-check, monitoring, http
```

### 2.3.3 實作 Skill 執行邏輯

創建 Python 實作檔案：

**src/skills/web_health_check.py**

```python
"""
Web Health Check Skill Implementation
"""
import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urlparse

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class HealthCheckResult:
    """健康檢查結果"""
    is_healthy: bool
    status_code: int
    response_time_ms: float
    page_title: Optional[str]
    errors: List[str]
    url: str
    checked_at: str

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "is_healthy": self.is_healthy,
            "status_code": self.status_code,
            "response_time_ms": round(self.response_time_ms, 2),
            "page_title": self.page_title,
            "errors": self.errors,
            "url": self.url,
            "checked_at": self.checked_at
        }


class WebHealthChecker:
    """網站健康檢查器"""

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries

    def _validate_url(self, url: str) -> bool:
        """驗證 URL 格式"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _make_request(
        self,
        url: str,
        retry_count: int = 0
    ) -> Optional[requests.Response]:
        """發送 HTTP 請求，帶重試機制"""
        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                headers={
                    'User-Agent': 'WebGuard/1.0 Health Checker'
                }
            )
            return response

        except requests.Timeout:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count  # 指數退避
                logger.warning(
                    f"請求超時，{wait_time}秒後重試 "
                    f"(第 {retry_count + 1}/{self.max_retries} 次)"
                )
                time.sleep(wait_time)
                return self._make_request(url, retry_count + 1)
            raise

        except requests.RequestException as e:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.warning(
                    f"請求失敗: {str(e)}，{wait_time}秒後重試"
                )
                time.sleep(wait_time)
                return self._make_request(url, retry_count + 1)
            raise

    def _extract_page_info(self, html: str) -> Dict[str, Any]:
        """從 HTML 提取頁面資訊"""
        try:
            soup = BeautifulSoup(html, 'lxml')

            # 提取標題
            title_tag = soup.find('title')
            title = title_tag.string.strip() if title_tag else None

            # 檢查基本元素
            has_body = soup.find('body') is not None
            has_head = soup.find('head') is not None

            return {
                "title": title,
                "has_body": has_body,
                "has_head": has_head,
                "is_valid_html": has_body and has_head
            }

        except Exception as e:
            logger.error(f"解析 HTML 失敗: {str(e)}")
            return {
                "title": None,
                "has_body": False,
                "has_head": False,
                "is_valid_html": False
            }

    def check(
        self,
        url: str,
        expected_status: int = 200
    ) -> HealthCheckResult:
        """
        執行網站健康檢查

        Args:
            url: 要檢查的網站 URL
            expected_status: 預期的 HTTP 狀態碼

        Returns:
            HealthCheckResult: 檢查結果
        """
        errors = []
        start_time = time.time()
        checked_at = time.strftime('%Y-%m-%d %H:%M:%S')

        # 驗證 URL
        if not self._validate_url(url):
            return HealthCheckResult(
                is_healthy=False,
                status_code=0,
                response_time_ms=0,
                page_title=None,
                errors=["無效的 URL 格式"],
                url=url,
                checked_at=checked_at
            )

        logger.info(f"開始健康檢查: {url}")

        try:
            # 發送請求
            response = self._make_request(url)

            if response is None:
                raise Exception("無法獲取回應")

            # 計算回應時間
            response_time_ms = (time.time() - start_time) * 1000

            # 檢查狀態碼
            status_code = response.status_code
            if status_code != expected_status:
                errors.append(
                    f"狀態碼不符: 期望 {expected_status}, "
                    f"實際 {status_code}"
                )

            # 解析頁面內容
            page_info = self._extract_page_info(response.text)

            if not page_info["is_valid_html"]:
                errors.append("HTML 結構不完整")

            if not page_info["title"]:
                errors.append("缺少頁面標題")

            # 判斷是否健康
            is_healthy = (
                status_code == expected_status and
                len(errors) == 0 and
                page_info["is_valid_html"]
            )

            result = HealthCheckResult(
                is_healthy=is_healthy,
                status_code=status_code,
                response_time_ms=response_time_ms,
                page_title=page_info["title"],
                errors=errors,
                url=url,
                checked_at=checked_at
            )

            # 記錄結果
            if is_healthy:
                logger.info(
                    f"✓ 健康檢查通過: {url} "
                    f"({response_time_ms:.0f}ms)"
                )
            else:
                logger.warning(
                    f"⚠ 健康檢查失敗: {url} - {', '.join(errors)}"
                )

            return result

        except requests.Timeout:
            errors.append(f"請求超時 (>{self.timeout}秒)")
            logger.error(f"✗ 健康檢查失敗: {url} - 超時")

        except requests.RequestException as e:
            errors.append(f"網路錯誤: {str(e)}")
            logger.error(f"✗ 健康檢查失敗: {url} - {str(e)}")

        except Exception as e:
            errors.append(f"未知錯誤: {str(e)}")
            logger.error(f"✗ 健康檢查失敗: {url} - {str(e)}")

        # 返回失敗結果
        return HealthCheckResult(
            is_healthy=False,
            status_code=0,
            response_time_ms=(time.time() - start_time) * 1000,
            page_title=None,
            errors=errors,
            url=url,
            checked_at=checked_at
        )


def execute_health_check(
    url: str,
    expected_status: int = 200,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Skill 入口函數

    Args:
        url: 要檢查的網站 URL
        expected_status: 預期的 HTTP 狀態碼
        timeout: 超時時間（秒）

    Returns:
        Dict: 健康檢查結果
    """
    checker = WebHealthChecker(timeout=timeout)
    result = checker.check(url, expected_status)
    return result.to_dict()


# CLI 接口（方便測試）
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("使用方式: python web_health_check.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    result = execute_health_check(url)
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

### 2.3.4 測試你的 Skill

創建一個測試腳本：

**examples/test_health_check.py**

```python
"""
測試 Web Health Check Skill
"""
import sys
from pathlib import Path

# 將專案根目錄加入 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.skills.web_health_check import execute_health_check


def test_single_url():
    """測試單一 URL"""
    print("=" * 60)
    print("測試 1: 檢查 example.com")
    print("=" * 60)

    result = execute_health_check("https://example.com")

    print(f"\n狀態: {'✓ 健康' if result['is_healthy'] else '✗ 不健康'}")
    print(f"HTTP 狀態碼: {result['status_code']}")
    print(f"回應時間: {result['response_time_ms']}ms")
    print(f"頁面標題: {result['page_title']}")

    if result['errors']:
        print(f"錯誤: {', '.join(result['errors'])}")


def test_multiple_urls():
    """測試多個 URL"""
    print("\n" + "=" * 60)
    print("測試 2: 檢查多個網站")
    print("=" * 60)

    test_urls = [
        "https://example.com",
        "https://httpbin.org/status/200",
        "https://httpbin.org/delay/2",  # 慢速回應
        "https://httpbin.org/status/404",  # 404 錯誤
    ]

    for url in test_urls:
        result = execute_health_check(url, timeout=10)
        status = "✓" if result['is_healthy'] else "✗"
        print(f"\n{status} {url}")
        print(f"   狀態碼: {result['status_code']}, "
              f"回應時間: {result['response_time_ms']:.0f}ms")
        if result['errors']:
            print(f"   錯誤: {', '.join(result['errors'])}")


def test_invalid_url():
    """測試無效 URL"""
    print("\n" + "=" * 60)
    print("測試 3: 無效 URL 處理")
    print("=" * 60)

    result = execute_health_check("not-a-valid-url")
    print(f"\n狀態: {'✓ 健康' if result['is_healthy'] else '✗ 不健康'}")
    print(f"錯誤: {', '.join(result['errors'])}")


if __name__ == "__main__":
    test_single_url()
    test_multiple_urls()
    test_invalid_url()

    print("\n" + "=" * 60)
    print("所有測試完成!")
    print("=" * 60)
```

創建 examples 目錄並運行測試：

```bash
mkdir -p examples
python3 examples/test_health_check.py
```

預期輸出：

```
============================================================
測試 1: 檢查 example.com
============================================================
2025-01-15 10:30:22 - __main__ - INFO - 開始健康檢查: https://example.com
2025-01-15 10:30:22 - __main__ - INFO - ✓ 健康檢查通過: https://example.com (245ms)

狀態: ✓ 健康
HTTP 狀態碼: 200
回應時間: 245.67ms
頁面標題: Example Domain

============================================================
測試 2: 檢查多個網站
============================================================

✓ https://example.com
   狀態碼: 200, 回應時間: 250ms

✓ https://httpbin.org/status/200
   狀態碼: 200, 回應時間: 450ms

✓ https://httpbin.org/delay/2
   狀態碼: 200, 回應時間: 2150ms

✗ https://httpbin.org/status/404
   狀態碼: 404, 回應時間: 380ms
   錯誤: 狀態碼不符: 期望 200, 實際 404

============================================================
測試 3: 無效 URL 處理
============================================================

狀態: ✗ 不健康
錯誤: 無效的 URL 格式

============================================================
所有測試完成!
============================================================
```

🎉 恭喜！你已經成功創建並運行了第一個 Claude Skill！

## 2.4 與 Claude 整合

現在 Skill 能獨立運行，讓我們將它與 Claude 整合，看看 AI 如何使用你的 Skill。

### 2.4.1 創建 Claude Skill 包裝器

Claude 需要特定的方式來發現和調用 Skills。我們創建一個包裝器：

**src/core/skill_executor.py**

```python
"""
Claude Skill 執行器
"""
import anthropic
import os
import json
from typing import Dict, Any, List, Callable
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SkillExecutor:
    """Claude Skill 執行器"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.skills: Dict[str, Callable] = {}

    def register_skill(
        self,
        name: str,
        function: Callable,
        description: str
    ):
        """註冊一個 Skill"""
        self.skills[name] = {
            "function": function,
            "description": description
        }
        logger.info(f"註冊 Skill: {name}")

    def execute_with_claude(
        self,
        prompt: str,
        max_tokens: int = 4096
    ) -> str:
        """
        使用 Claude 執行任務，可能會調用註冊的 Skills

        Args:
            prompt: 用戶提示
            max_tokens: 最大 token 數

        Returns:
            Claude 的回應
        """
        logger.info(f"執行 Claude 請求: {prompt[:100]}...")

        # 構建 tools 定義
        tools = self._build_tools_definition()

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                tools=tools,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # 處理 tool 調用
            if response.stop_reason == "tool_use":
                return self._handle_tool_use(response, prompt)

            # 提取回應文本
            return response.content[0].text

        except Exception as e:
            logger.error(f"Claude 執行失敗: {str(e)}")
            raise

    def _build_tools_definition(self) -> List[Dict]:
        """構建 tools 定義供 Claude 使用"""
        tools = []

        for name, skill in self.skills.items():
            # 這裡簡化了，實際應該從 SKILL.md 解析
            tools.append({
                "name": name,
                "description": skill["description"],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to check"
                        },
                        "expected_status": {
                            "type": "integer",
                            "description": "Expected HTTP status code",
                            "default": 200
                        }
                    },
                    "required": ["url"]
                }
            })

        return tools

    def _handle_tool_use(
        self,
        response: Any,
        original_prompt: str
    ) -> str:
        """處理 tool 調用"""
        # 提取 tool 使用
        tool_use = None
        for block in response.content:
            if block.type == "tool_use":
                tool_use = block
                break

        if not tool_use:
            return "未找到 tool 調用"

        # 執行對應的 skill
        skill_name = tool_use.name
        skill_input = tool_use.input

        logger.info(f"Claude 調用 Skill: {skill_name}")
        logger.debug(f"Skill 輸入: {json.dumps(skill_input, indent=2)}")

        if skill_name not in self.skills:
            return f"未知的 Skill: {skill_name}"

        # 執行 skill
        skill_function = self.skills[skill_name]["function"]
        result = skill_function(**skill_input)

        logger.info(f"Skill 執行完成")
        logger.debug(f"結果: {json.dumps(result, indent=2)}")

        # 將結果回傳給 Claude
        continue_response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": original_prompt
                },
                {
                    "role": "assistant",
                    "content": response.content
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result)
                        }
                    ]
                }
            ]
        )

        return continue_response.content[0].text
```

### 2.4.2 創建 Claude 整合範例

**examples/claude_integration.py**

```python
"""
Claude 整合範例
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.skill_executor import SkillExecutor
from src.skills.web_health_check import execute_health_check


def main():
    """主函數"""
    print("=" * 60)
    print("Claude Skills 整合示範")
    print("=" * 60)

    # 創建執行器
    executor = SkillExecutor()

    # 註冊 health check skill
    executor.register_skill(
        name="web_health_check",
        function=execute_health_check,
        description="Check if a website is healthy and accessible"
    )

    # 測試 1: 讓 Claude 使用 Skill 檢查網站
    print("\n【測試 1】: 讓 Claude 檢查 example.com")
    print("-" * 60)

    result = executor.execute_with_claude(
        "Please check if https://example.com is healthy and working properly. "
        "Give me a summary of the results."
    )

    print(f"\nClaude 的回應:\n{result}")

    # 測試 2: 多個網站比較
    print("\n\n【測試 2】: 讓 Claude 比較多個網站")
    print("-" * 60)

    result = executor.execute_with_claude(
        "Please check these websites and tell me which one is fastest:\n"
        "1. https://example.com\n"
        "2. https://httpbin.org/delay/1\n"
        "3. https://google.com\n"
        "\nProvide a comparison of their response times."
    )

    print(f"\nClaude 的回應:\n{result}")


if __name__ == "__main__":
    main()
```

運行整合示範：

```bash
python3 examples/claude_integration.py
```

這會展示 Claude 如何自動調用你的 Skill！

## 2.5 完善與調試

### 2.5.1 添加單元測試

良好的測試是專業開發的標誌。創建單元測試：

**tests/test_web_health_check.py**

```python
"""
Web Health Check Skill 單元測試
"""
import pytest
from src.skills.web_health_check import (
    WebHealthChecker,
    execute_health_check
)


class TestWebHealthChecker:
    """WebHealthChecker 測試類"""

    def test_valid_url(self):
        """測試有效 URL"""
        checker = WebHealthChecker(timeout=10)
        result = checker.check("https://example.com")

        assert result.is_healthy
        assert result.status_code == 200
        assert result.page_title is not None
        assert len(result.errors) == 0

    def test_invalid_url(self):
        """測試無效 URL"""
        checker = WebHealthChecker()
        result = checker.check("not-a-url")

        assert not result.is_healthy
        assert result.status_code == 0
        assert "無效的 URL 格式" in result.errors

    def test_404_status(self):
        """測試 404 狀態"""
        checker = WebHealthChecker(timeout=10)
        result = checker.check("https://httpbin.org/status/404")

        assert not result.is_healthy
        assert result.status_code == 404
        assert any("狀態碼不符" in error for error in result.errors)

    def test_timeout(self):
        """測試超時處理"""
        checker = WebHealthChecker(timeout=1, max_retries=1)
        result = checker.check("https://httpbin.org/delay/5")

        assert not result.is_healthy
        assert any("超時" in error for error in result.errors)

    def test_execute_health_check_function(self):
        """測試入口函數"""
        result = execute_health_check("https://example.com")

        assert isinstance(result, dict)
        assert "is_healthy" in result
        assert "status_code" in result
        assert "response_time_ms" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

運行測試：

```bash
poetry run pytest tests/ -v
```

### 2.5.2 添加日誌和錯誤處理

確保 Skill 有完善的日誌記錄，方便調試。

**示範：啟用詳細日誌**

```python
# examples/debug_health_check.py
import logging
from src.utils.logger import setup_logger
from src.skills.web_health_check import execute_health_check

# 啟用調試級別日誌
logger = setup_logger(__name__, "DEBUG")

# 測試
result = execute_health_check("https://example.com")
print(f"結果: {result}")
```

### 2.5.3 性能優化

**範例：批次檢查**

```python
# src/skills/web_health_check.py (添加)

import concurrent.futures
from typing import List

def batch_health_check(
    urls: List[str],
    max_workers: int = 5
) -> List[Dict[str, Any]]:
    """
    批次健康檢查（並行執行）

    Args:
        urls: URL 列表
        max_workers: 最大並行執行數

    Returns:
        List[Dict]: 檢查結果列表
    """
    checker = WebHealthChecker()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(checker.check, url): url for url in urls}
        results = []

        for future in concurrent.futures.as_completed(futures):
            url = futures[future]
            try:
                result = future.result()
                results.append(result.to_dict())
            except Exception as e:
                logger.error(f"批次檢查失敗 - {url}: {str(e)}")
                results.append({
                    "url": url,
                    "is_healthy": False,
                    "errors": [str(e)]
                })

        return results
```

## 2.6 本章總結

### 2.6.1 你學到了什麼

在這一章，你完成了許多重要的里程碑：

✅ **環境設置**
- 安裝和配置 Python、Node.js
- 設置 Claude API 認證
- 建立開發工具鏈

✅ **專案初始化**
- 創建 WebGuard 專案結構
- 配置依賴管理
- 設置版本控制

✅ **第一個 Skill**
- 理解 Skill 的結構
- 實作完整的健康檢查功能
- 測試和驗證 Skill

✅ **Claude 整合**
- 創建 Skill 執行器
- 看到 AI 如何調用 Skill
- 理解 AI 驅動自動化的實際運作

✅ **專業實踐**
- 編寫單元測試
- 添加日誌記錄
- 性能優化考量

### 2.6.2 關鍵要點

💡 **核心概念**
- Skill 由定義（SKILL.md）和實作（Python/JS）組成
- 良好的錯誤處理和重試機制是關鍵
- Claude 能夠理解 Skill 的用途並自主決定何時調用

⚠️ **注意事項**
- 永遠不要硬編碼 API 金鑰
- 為網路操作設置合理的超時
- 詳細的日誌記錄能大幅加速調試

🔍 **最佳實踐**
- 單一 Skill 應該專注於一個明確的任務
- 提供清晰的錯誤訊息
- 編寫可測試的代碼
- 文檔和代碼同步更新

### 2.6.3 檢查點

確認你已經：

- [ ] 成功安裝所有必要工具
- [ ] 配置 Claude API 並驗證連接
- [ ] 創建 WebGuard 專案結構
- [ ] 實作並測試 web_health_check Skill
- [ ] 看到 Claude 成功調用你的 Skill
- [ ] 運行單元測試並全部通過

### 2.6.4 故障排除

**常見問題**

**問題 1：API 金鑰無法識別**
```bash
# 檢查環境變數
echo $ANTHROPIC_API_KEY

# 如果為空，重新載入配置
source ~/.bashrc  # 或 ~/.zshrc
```

**問題 2：Python 套件安裝失敗**
```bash
# 更新 pip
python3 -m pip install --upgrade pip

# 清除快取
poetry cache clear --all pypi

# 重新安裝
poetry install
```

**問題 3：測試失敗（網路相關）**
```bash
# 測試網路連接
curl -I https://example.com

# 使用更長的超時
python3 examples/test_health_check.py  # 腳本內調整 timeout
```

### 2.6.5 延伸練習

**練習 1：擴展健康檢查**
在現有 Skill 中添加：
- 檢查 SSL 憑證有效性
- 檢測頁面載入時間
- 驗證特定文本存在

**練習 2：創建第二個 Skill**
創建一個 "screenshot" Skill：
- 擷取網站截圖
- 儲存到本地檔案
- 返回檔案路徑

**練習 3：批次操作**
修改健康檢查以支持：
- 從檔案讀取 URL 列表
- 並行檢查所有 URL
- 生成 CSV 報告

## 2.7 下一章預告

現在你已經能夠創建基本的 Skill，在**第 3 章**，我們將深入探討：

1. **完整的 SKILL.md 語法**
   - 所有可用的配置選項
   - 參數類型和驗證
   - 進階元數據

2. **Skills 生命週期**
   - 發現階段
   - 準備階段
   - 執行階段
   - 清理和錯誤恢復

3. **Skills 開發最佳實踐**
   - 設計原則
   - 常見模式
   - 反模式警告

準備好深入 Skills 的核心概念了嗎？第 3 章見！

---

**章節總結**

這一章是從理論到實踐的關鍵轉折點。你不僅設置了完整的開發環境，還親手創建並運行了第一個 Claude Skill。更重要的是，你看到了 AI 如何理解和使用你的 Skill——這是 AI 驅動自動化的精髓。

WebGuard 的基礎已經奠定。從下一章開始，我們將在這個基礎上構建越來越強大的功能。記住：最好的學習方式是實作。不要害怕實驗和犯錯——每個錯誤都是學習的機會。

*"The only way to learn a new programming language is by writing programs in it." - Dennis Ritchie*
