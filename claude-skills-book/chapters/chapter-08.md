# 第 8 章
> 🔄 **系統整合**：CI/CD 是將前面章節的 Skills 整合到開發流程的關鍵。部署架構見 **Chapter 9-10**。
：測試自動化與 CI/CD 整合

在本地開發環境中手動執行測試只是第一步，真正的價值在於將測試整合到持續整合/持續部署（CI/CD）流水線中，實現**自動化**、**持續**、**可靠**的測試執行。本章將探討如何將 Claude Code Skills 測試系統整合到主流 CI/CD 平台：GitHub Actions、GitLab CI、Jenkins，涵蓋環境配置、密鑰管理、定時任務、測試報告生成、失敗通知等企業級實踐。

## 8.1 CI/CD 基礎：為什麼需要持續測試？

### 8.1.1 什麼是 CI/CD？

**持續整合（Continuous Integration, CI）**：
- 開發者頻繁（每天多次）將代碼合併到主分支
- 每次合併觸發自動化構建和測試
- 快速發現整合問題

**持續部署（Continuous Deployment, CD）**：
- 通過所有測試的代碼自動部署到生產環境
- 減少手動操作，加速交付

### 8.1.2 測試自動化的價值

| 場景 | 手動測試 | 自動化測試（CI/CD） |
|------|----------|---------------------|
| 執行頻率 | 每週 1-2 次 | 每次代碼提交 |
| 回饋時間 | 數小時到數天 | 10-30 分鐘 |
| 覆蓋率 | 受時間限制，通常只測核心流程 | 全面測試 |
| 一致性 | 人為因素導致不穩定 | 完全一致 |
| 成本 | 人力成本高 | 初期投入後幾乎為零 |

**典型 CI/CD 工作流：**

```
Developer Push Code
    ↓
GitHub/GitLab 觸發 CI
    ↓
[CI Pipeline]
  1. 構建環境（Install dependencies）
  2. 運行單元測試
  3. 運行 API 測試
  4. 運行瀏覽器 E2E 測試
  5. 生成測試報告
  6. 代碼覆蓋率檢查
    ↓
All Tests Pass → Deploy to Staging → Deploy to Production
    ↓
Any Test Fails → Notify Team (Slack/Email) → Block Deployment
```

### 8.1.3 測試金字塔與 CI 策略

**測試金字塔：**

```
        /\
       /  \  E2E Tests (10%)
      /────\  - 慢、脆弱、高價值
     /      \
    / Integ. \ Integration Tests (30%)
   /  Tests  \  - 中速、API 測試
  /──────────\
 /            \
/   Unit Tests \ Unit Tests (60%)
───────────────── - 快、穩定、低級別
```

**CI 執行策略：**

- **每次 Push**：運行單元測試 + 關鍵 API 測試（5-10 分鐘）
- **每次 PR**：運行完整測試套件（30 分鐘）
- **每日定時**：運行 E2E 測試 + 性能測試（1-2 小時）
- **部署前**：運行冒煙測試（Smoke Tests）（2-3 分鐘）


## 8.2 GitHub Actions 整合

GitHub Actions 是 GitHub 內建的 CI/CD 平台，配置簡單、與 GitHub 倉庫無縫整合。

### 8.2.1 基礎配置：WebGuard 測試工作流

創建 `.github/workflows/webguard-tests.yml`：

```yaml
name: WebGuard Tests

# 觸發條件
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    # 每天 UTC 2:00 (台北時間 10:00)
    - cron: '0 2 * * *'
  workflow_dispatch:  # 允許手動觸發

# 環境變數（全局）
env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 45  # 防止卡死

    # 服務容器（PostgreSQL, Redis）
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: webguard_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      # 1. 檢出代碼
      - name: Checkout code
        uses: actions/checkout@v4

      # 2. 設置 Python
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'  # 快取 pip 依賴

      # 3. 設置 Node.js（Stagehand 需要）
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      # 4. 安裝系統依賴（瀏覽器）
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            libnss3 \
            libatk-bridge2.0-0 \
            libx11-xcb1 \
            libxcomposite1 \
            libxdamage1 \
            libxrandr2 \
            libgbm1 \
            libasound2

      # 5. 安裝 Python 依賴
      - name: Install Python dependencies
        run: |
          pip install poetry
          poetry config virtualenvs.create false
          poetry install --no-interaction

      # 6. 安裝 Node.js 依賴
      - name: Install Node.js dependencies
        run: npm ci  # 'ci' 比 'install' 更快且可重複

      # 7. 數據庫遷移
      - name: Run database migrations
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/webguard_test
        run: |
          poetry run alembic upgrade head

      # 8. 運行測試
      - name: Run WebGuard tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/webguard_test
          REDIS_URL: redis://localhost:6379/0
          CI: true  # 某些測試可能需要判斷是否在 CI 環境
        run: |
          poetry run pytest tests/ \
            -v \
            --tb=short \
            --cov=src \
            --cov-report=xml \
            --cov-report=html \
            --junitxml=test-results/junit.xml \
            --maxfail=5  # 失敗 5 個測試後停止

      # 9. 上傳代碼覆蓋率到 Codecov
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: false  # 不因 Codecov 失敗而中斷 CI

      # 10. 生成 Allure 測試報告
      - name: Generate Allure report
        if: always()  # 即使測試失敗也生成報告
        run: |
          poetry run pytest tests/ \
            --alluredir=allure-results \
            --clean-alluredir
          poetry run allure generate allure-results -o allure-report --clean

      # 11. 上傳測試報告
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: |
            test-results/
            allure-report/
            htmlcov/
          retention-days: 30

      # 12. 測試失敗通知（Slack）
      - name: Notify on failure
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: 'C12345678'  # 替換為實際 channel ID
          payload: |
            {
              "text": "❌ WebGuard 測試失敗",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*WebGuard Tests Failed*\n\n*Branch:* ${{ github.ref_name }}\n*Commit:* ${{ github.sha }}\n*Author:* ${{ github.actor }}\n\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Details>"
                  }
                }
              ]
            }
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

### 8.2.2 Secrets 管理

敏感信息（API Key、密碼）不應寫死在代碼中，使用 GitHub Secrets：

**設置 Secrets：**

1. GitHub 倉庫 → Settings → Secrets and variables → Actions
2. 新增 Secrets：
   - `ANTHROPIC_API_KEY`: Claude API 金鑰
   - `SLACK_BOT_TOKEN`: Slack 通知 Token
   - `DATABASE_PASSWORD`: 數據庫密碼（如需連接外部數據庫）

**在工作流中使用：**

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### 8.2.3 矩陣測試（Matrix Strategy）

測試多個 Python 版本或操作系統：

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.10', '3.11', '3.12']
      fail-fast: false  # 一個失敗不中斷其他組合

    steps:
      - uses: actions/checkout@v4
      - name: Setup Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      # ... 其他步驟
```

這會創建 3 × 3 = 9 個並行任務。

### 8.2.4 快取優化（加速構建）

**快取 Poetry 依賴：**

```yaml
- name: Cache Poetry dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pypoetry
      .venv
    key: poetry-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}
    restore-keys: |
      poetry-${{ runner.os }}-

- name: Install dependencies
  run: poetry install
```

**快取瀏覽器二進制：**

```yaml
- name: Cache Playwright browsers
  uses: actions/cache@v4
  with:
    path: ~/.cache/ms-playwright
    key: playwright-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}

- name: Install Playwright
  run: npx playwright install chromium
```


## 8.3 GitLab CI/CD 整合

GitLab CI/CD 使用 `.gitlab-ci.yml` 配置文件。

### 8.3.1 基礎配置

```yaml
# .gitlab-ci.yml
image: python:3.11

stages:
  - prepare
  - test
  - report
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  POSTGRES_DB: webguard_test
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres
  DATABASE_URL: "postgresql://postgres:postgres@postgres:5432/webguard_test"

# 服務容器
services:
  - postgres:15
  - redis:7-alpine

# 快取
cache:
  paths:
    - .cache/pip
    - .venv/
    - node_modules/

# 階段 1: 準備環境
prepare:
  stage: prepare
  script:
    - pip install poetry
    - poetry config virtualenvs.in-project true
    - poetry install
    - npm ci
  artifacts:
    paths:
      - .venv/
      - node_modules/
    expire_in: 1 hour

# 階段 2: 執行測試
test:unit:
  stage: test
  dependencies:
    - prepare
  script:
    - poetry run pytest tests/unit/ -v --junitxml=report-unit.xml
  artifacts:
    when: always
    reports:
      junit: report-unit.xml
  only:
    - merge_requests
    - main

test:api:
  stage: test
  dependencies:
    - prepare
  script:
    - poetry run pytest tests/api/ -v --junitxml=report-api.xml
  artifacts:
    when: always
    reports:
      junit: report-api.xml

test:e2e:
  stage: test
  dependencies:
    - prepare
  before_script:
    - apt-get update && apt-get install -y libnss3 libatk-bridge2.0-0
  script:
    - poetry run pytest tests/e2e/ -v --junitxml=report-e2e.xml
  artifacts:
    when: always
    paths:
      - screenshots/
      - allure-results/
    reports:
      junit: report-e2e.xml
  only:
    - schedules  # 只在定時任務中運行 E2E
    - main

# 階段 3: 生成報告
allure-report:
  stage: report
  dependencies:
    - test:e2e
  script:
    - poetry run allure generate allure-results -o allure-report --clean
  artifacts:
    paths:
      - allure-report/
    expire_in: 7 days
  only:
    - main

# 定時任務配置（GitLab UI 設置）
# Settings → CI/CD → Schedules
# Cron: 0 2 * * * (每天 2:00 AM)
```

### 8.3.2 GitLab CI 特色功能

**1. 並行測試（Parallel Execution）：**

```yaml
test:parallel:
  stage: test
  parallel: 5  # 創建 5 個並行任務
  script:
    - poetry run pytest tests/ --splits 5 --group $CI_NODE_INDEX
```

**2. 動態子管道（Dynamic Child Pipelines）：**

```yaml
generate-tests:
  stage: prepare
  script:
    - python scripts/generate_ci_pipeline.py > child-pipeline.yml
  artifacts:
    paths:
      - child-pipeline.yml

trigger-tests:
  stage: test
  trigger:
    include:
      - artifact: child-pipeline.yml
        job: generate-tests
    strategy: depend
```

## 8.4 Jenkins 整合

Jenkins 是企業中最常用的 CI/CD 工具，支持 Jenkinsfile 配置。

### 8.4.1 Declarative Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any

    environment {
        PYTHON_VERSION = '3.11'
        DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/webguard_test'
        ANTHROPIC_API_KEY = credentials('anthropic-api-key')
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/company/webguard.git'
            }
        }

        stage('Setup') {
            parallel {
                stage('Python Setup') {
                    steps {
                        sh '''
                            python -m venv .venv
                            . .venv/bin/activate
                            pip install poetry
                            poetry install
                        '''
                    }
                }
                stage('Node.js Setup') {
                    steps {
                        sh 'npm ci'
                    }
                }
            }
        }

        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        sh '''
                            . .venv/bin/activate
                            poetry run pytest tests/unit/ -v --junitxml=results-unit.xml
                        '''
                    }
                }
                stage('API Tests') {
                    steps {
                        sh '''
                            . .venv/bin/activate
                            poetry run pytest tests/api/ -v --junitxml=results-api.xml
                        '''
                    }
                }
            }
        }

        stage('E2E Tests') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                sh '''
                    . .venv/bin/activate
                    poetry run pytest tests/e2e/ -v --junitxml=results-e2e.xml
                '''
            }
        }

        stage('Generate Reports') {
            steps {
                sh '''
                    . .venv/bin/activate
                    poetry run allure generate allure-results -o allure-report --clean
                '''

                // 發布 Allure 報告
                allure([
                    includeProperties: false,
                    jdk: '',
                    properties: [],
                    reportBuildPolicy: 'ALWAYS',
                    results: [[path: 'allure-results']]
                ])
            }
        }
    }

    post {
        always {
            junit '**/results-*.xml'
            archiveArtifacts artifacts: 'allure-report/**', allowEmptyArchive: true
        }

        failure {
            emailext(
                subject: "❌ WebGuard Build Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: """
                    Build failed: ${env.BUILD_URL}

                    Check console output for details.
                """,
                to: 'team@company.com'
            )
        }

        success {
            echo '✅ All tests passed!'
        }
    }
}
```

### 8.4.2 Jenkins Shared Library（可重用配置）

創建共享庫 `vars/webguardPipeline.groovy`：

```groovy
def call(Map config = [:]) {
    pipeline {
        agent any

        stages {
            stage('Test') {
                steps {
                    script {
                        def testTypes = config.tests ?: ['unit', 'api', 'e2e']

                        testTypes.each { testType ->
                            sh """
                                poetry run pytest tests/${testType}/ -v
                            """
                        }
                    }
                }
            }
        }
    }
}
```

**使用：**

```groovy
// Jenkinsfile
@Library('webguard-shared-lib') _

webguardPipeline(
    tests: ['unit', 'api']  # 只運行單元和 API 測試
)
```


## 8.5 測試報告與可視化

### 8.5.1 Allure 測試報告

**Allure** 是最流行的測試報告框架，支持 pytest、JUnit、TestNG。

**安裝與配置：**

```bash
pip install allure-pytest
```

**在測試中添加 Allure 註解：**

```python
import allure
import pytest


@allure.feature('User Management')
@allure.story('User Login')
@allure.severity(allure.severity_level.CRITICAL)
def test_user_login():
    """測試用戶登入功能"""

    with allure.step('打開登入頁面'):
        driver.get('https://example.com/login')

    with allure.step('輸入用戶名和密碼'):
        driver.find_element(By.ID, 'username').send_keys('testuser')
        driver.find_element(By.ID, 'password').send_keys('password123')

    with allure.step('點擊登入按鈕'):
        driver.find_element(By.ID, 'login-btn').click()

    with allure.step('驗證登入成功'):
        assert driver.current_url == 'https://example.com/dashboard'
        allure.attach(
            driver.get_screenshot_as_png(),
            name='登入成功截圖',
            attachment_type=allure.attachment_type.PNG
        )


@pytest.mark.parametrize('username,password,expected', [
    ('valid_user', 'valid_pass', 'success'),
    ('invalid_user', 'wrong_pass', 'failure'),
])
def test_login_variations(username, password, expected):
    """測試不同登入組合"""
    allure.dynamic.title(f'登入測試: {username}')
    allure.dynamic.description(f'測試用戶 {username} 的登入行為')

    # 測試邏輯...
```

**生成報告：**

```bash
# 執行測試並生成 Allure 數據
pytest tests/ --alluredir=allure-results

# 生成 HTML 報告
allure generate allure-results -o allure-report --clean

# 啟動 Allure 伺服器查看報告
allure serve allure-results
```

**Allure 報告特性：**

- **可視化趨勢**：歷史測試結果對比
- **分類統計**：按 Feature、Story、Severity 分類
- **失敗分析**：自動分類失敗原因（Product Bug, Test Bug, System Issue）
- **附件支持**：截圖、日誌、視頻

### 8.5.2 代碼覆蓋率（Code Coverage）

**配置 pytest-cov：**

```bash
pip install pytest-cov
```

**執行測試並生成覆蓋率報告：**

```bash
pytest tests/ \
    --cov=src \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-fail-under=80  # 覆蓋率低於 80% 則失敗
```

**與 Codecov 整合（CI 中自動上傳）：**

```yaml
# GitHub Actions
- name: Upload to Codecov
  uses: codecov/codecov-action@v4
  with:
    file: ./coverage.xml
    flags: unittests
    name: codecov-umbrella
```

**設置覆蓋率目標：**

```ini
# .coveragerc
[run]
source = src
omit =
    */tests/*
    */migrations/*
    */venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

### 8.5.3 性能測試報告（JMeter/Locust）

**Locust 性能測試整合：**

```python
# locustfile.py（參見 Chapter 6）
from locust import HttpUser, task, between


class WebGuardUser(HttpUser):
    wait_time = between(1, 3)
    host = "https://api.example.com"

    @task
    def health_check(self):
        self.client.get("/health")
```

**CI 中執行性能測試：**

```yaml
- name: Run performance tests
  run: |
    locust -f locustfile.py \
      --headless \
      --users 100 \
      --spawn-rate 10 \
      --run-time 5m \
      --html performance-report.html

- name: Upload performance report
  uses: actions/upload-artifact@v4
  with:
    name: performance-report
    path: performance-report.html
```


## 8.6 定時任務與健康監控

### 8.6.1 Cron 定時測試

**GitHub Actions 定時任務：**

```yaml
on:
  schedule:
    # 每天 2:00 AM UTC
    - cron: '0 2 * * *'
    # 每週一 8:00 AM UTC
    - cron: '0 8 * * 1'
    # 每小時（用於健康檢查）
    - cron: '0 * * * *'
```

**GitLab 定時管道：**

GitLab UI → CI/CD → Schedules → New Schedule

**Jenkins Cron：**

```groovy
triggers {
    cron('H 2 * * *')  # 'H' 表示 hash，避免所有任務同時執行
}
```

### 8.6.2 健康檢查 Skill

創建專門的健康檢查 Skill：

**SKILL.md：**

```markdown
---
name: health-check
description: Monitor critical services and endpoints
parameters:
  - name: services
    description: List of services to check
    type: array
    required: true
---

# Health Check Skill

Monitors service availability and performance.
```

**skill.py：**

```python
import asyncio
from api_tester import APITester


async def health_check(services: list) -> dict:
    """健康檢查所有服務"""
    tester = APITester(base_url="https://api.example.com")

    results = []
    for service in services:
        result = tester.test_endpoint(
            method="GET",
            endpoint=service['endpoint'],
            expected_status=service.get('expected_status', 200)
        )

        # 性能閾值檢查
        if result.get('response_time_ms', 0) > service.get('max_response_time_ms', 5000):
            result['warning'] = f"響應時間超標: {result['response_time_ms']}ms"

        results.append({
            'service': service['name'],
            'status': 'healthy' if result['success'] else 'unhealthy',
            'response_time_ms': result.get('response_time_ms'),
            'warning': result.get('warning')
        })

    # 統計
    healthy_count = sum(1 for r in results if r['status'] == 'healthy')

    return {
        "success": healthy_count == len(services),
        "total_services": len(services),
        "healthy": healthy_count,
        "unhealthy": len(services) - healthy_count,
        "results": results
    }
```

**定時執行（每小時）：**

```yaml
on:
  schedule:
    - cron: '0 * * * *'

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run health check
        run: |
          python -m skills.health_check \
            --services api,database,redis,cache

      - name: Alert on failure
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "⚠️ 健康檢查失敗！請立即檢查服務狀態。"
            }
```


## 8.7 失敗通知與告警

### 8.7.1 Slack 通知

**使用 Slack Incoming Webhook：**

```python
import requests


def send_slack_notification(webhook_url: str, message: str):
    """發送 Slack 通知"""
    payload = {
        "text": message,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
    }

    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200
```

**GitHub Actions 整合：**

```yaml
- name: Notify Slack
  if: failure()
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
      -H 'Content-Type: application/json' \
      -d '{
        "text": "❌ CI Failed",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Build Failed*\nBranch: ${{ github.ref_name }}\nCommit: ${{ github.sha }}"
            }
          }
        ]
      }'
```

### 8.7.2 Email 通知

**Jenkins Email Extension：**

```groovy
post {
    failure {
        emailext(
            subject: "Build Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: """
                <h2>Build Failed</h2>
                <p><strong>Job:</strong> ${env.JOB_NAME}</p>
                <p><strong>Build Number:</strong> ${env.BUILD_NUMBER}</p>
                <p><strong>Build URL:</strong> <a href="${env.BUILD_URL}">${env.BUILD_URL}</a></p>
                <p><strong>Console Output:</strong> <a href="${env.BUILD_URL}console">${env.BUILD_URL}console</a></p>
            """,
            mimeType: 'text/html',
            to: 'team@company.com',
            attachLog: true
        )
    }
}
```


## 8.8 最佳實踐

### 8.8.1 測試執行策略

| 測試類型 | 執行時機 | 並行數 | 超時 |
|----------|----------|--------|------|
| 單元測試 | 每次 Push | 高（10+） | 5 min |
| API 測試 | 每次 Push | 中（5） | 15 min |
| E2E 測試 | PR + 定時 | 低（2-3） | 45 min |
| 性能測試 | 定時（每日） | 1 | 30 min |

### 8.8.2 快速反饋原則

- **失敗快速（Fail Fast）**：第一個測試失敗立即通知
- **並行執行**：充分利用 CI 並行能力
- **增量測試**：只測試變更相關的模組（需要依賴分析）

### 8.8.3 成本優化

**GitHub Actions 成本：**

- 公開倉庫：免費
- 私有倉庫：2000 分鐘/月（免費額度）
- 超額：$0.008/分鐘

**優化策略：**

1. **快取依賴**：節省 50-70% 構建時間
2. **並行限制**：避免過度並行消耗額度
3. **按需測試**：不是每次 Push 都跑 E2E
4. **自託管 Runner**：大規模使用時考慮自建


## 8.9 本章總結

本章深入探討了 CI/CD 整合的完整體系：

**核心能力：**

- **多平台整合**：GitHub Actions、GitLab CI、Jenkins 完整配置
- **測試報告**：Allure 報告、代碼覆蓋率、性能測試報告
- **定時任務**：Cron 定時執行、健康監控
- **失敗通知**：Slack、Email 實時告警
- **最佳實踐**：測試策略、快速反饋、成本優化

**企業級視角：**

CI/CD 不只是「自動運行測試」，而是：

- **質量門禁（Quality Gate）**：不合格代碼無法合併
- **持續反饋**：開發者 10 分鐘內知道測試結果
- **可觀測性**：完整的測試歷史、趨勢分析
- **可靠性**：自動化消除人為錯誤

**下一章預告：**

掌握 CI/CD 整合後，第 9 章將呈現 **WebGuard 完整系統架構**：四層架構設計（編排層、執行層、存儲層、報告層）、微服務化部署、高可用性設計、監控告警系統。這是前 8 章所有技術的綜合應用，構建企業級測試平台。
