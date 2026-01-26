# 第十章：CI/CD 自動化整合

**在這一章中，你將學會：**
- 自動化 Code Review 的設定與實踐
- 讓 AI 自動補充測試覆蓋
- 效能回歸檢測機制
- 安全性掃描整合
- 建立團隊的品質守門機制

> 💡 **開場白**
>
> 恭喜你來到最後一章！
>
> 到目前為止，我們學了很多「手動」的技巧——設計指令、review 程式碼、給回饋。但在真實的開發流程中，你不可能每一次都手動檢查所有東西。
>
> **解決方案：把品質檢查自動化，整合到 CI/CD 流程中。**
>
> 這樣，不管是人類還是 AI 寫的程式碼，都會通過同樣的品質守門。

---

## 10.1 自動化 Code Review

### 傳統 CI/CD vs AI-Native CI/CD

**傳統 CI/CD：**
```
Push → Build → Test → Deploy
```

**AI-Native CI/CD：**
```
Push → Lint → Type Check → Test → AI Review → Security Scan → Performance Test → Deploy
                                     ↑
                               新增這一層！
```

### 設定自動化 Code Review

**使用 GitHub Actions + Claude Code：**

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get changed files
        id: changed
        run: |
          echo "files=$(git diff --name-only origin/main...HEAD | tr '\n' ' ')" >> $GITHUB_OUTPUT

      - name: AI Code Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # 取得變更的程式碼
          git diff origin/main...HEAD > changes.diff

          # 使用 Claude API 進行 review
          claude-code review \
            --diff changes.diff \
            --checklist .claude/review-checklist.md \
            --output review-result.md

      - name: Post Review Comment
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const review = fs.readFileSync('review-result.md', 'utf8');

            github.rest.pulls.createReview({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: context.issue.number,
              body: review,
              event: 'COMMENT'
            });
```

### Review Checklist 檔案

```markdown
<!-- .claude/review-checklist.md -->
# AI Code Review Checklist

## 必須檢查項目

### 功能正確性
- [ ] 主要邏輯是否正確？
- [ ] 邊界情況是否處理？
- [ ] 錯誤處理是否完整？

### 效能
- [ ] 是否有 N+1 查詢？
- [ ] 是否有不必要的迴圈？
- [ ] 資料庫查詢是否使用索引？

### 安全性
- [ ] 是否有 SQL injection 風險？
- [ ] 是否有 XSS 風險？
- [ ] 敏感資料是否正確處理？

### 程式碼品質
- [ ] 命名是否清晰？
- [ ] 函數是否過長（> 30 行）？
- [ ] 是否有重複程式碼？

## 輸出格式

請按以下格式輸出 review 結果：

### Summary
整體評價和主要發現

### Issues Found
- 🔴 **Critical**: [描述]
- 🟡 **Warning**: [描述]
- 🔵 **Suggestion**: [描述]

### Recommendations
具體的修改建議
```

---

## 10.2 自動補充測試覆蓋

AI 不只能寫程式碼，還能自動補充測試！

### 測試覆蓋檢查

```yaml
# .github/workflows/test-coverage.yml
name: Test Coverage

on: [push, pull_request]

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install pytest pytest-cov

      - name: Run tests with coverage
        run: |
          pytest --cov=src --cov-report=xml --cov-fail-under=80

      - name: Check coverage decrease
        run: |
          # 如果覆蓋率下降，標記為失敗
          python scripts/check_coverage_decrease.py
```

### 讓 AI 自動補充測試

當測試覆蓋率不足時，讓 AI 自動產生測試：

```yaml
  auto-generate-tests:
    needs: coverage
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Identify uncovered code
        run: |
          # 找出沒有測試覆蓋的程式碼
          python scripts/find_uncovered.py > uncovered.txt

      - name: Generate tests with AI
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          claude-code generate-tests \
            --uncovered uncovered.txt \
            --output tests/auto_generated/

      - name: Create PR with new tests
        uses: peter-evans/create-pull-request@v5
        with:
          title: "test: Auto-generated tests for uncovered code"
          body: "This PR adds tests for previously uncovered code."
          branch: auto-tests-${{ github.sha }}
```

### 測試產生的 I-B-C 指令

```
【Intent】
為以下沒有測試覆蓋的函數產生單元測試。

【Behavior】
- 每個函數至少要有 3 個測試案例
- 測試要涵蓋：正常情況、邊界情況、錯誤情況
- 使用 pytest 風格
- 測試命名：test_{function_name}_{scenario}_{expected}

【Context】
- 專案使用 pytest
- Mock 使用 pytest-mock
- 資料庫測試使用 fixtures（參考 conftest.py）

【未覆蓋的函數】
{貼上未覆蓋的程式碼}
```

---

## 10.3 效能回歸檢測

效能問題往往是在不知不覺中引入的。自動化檢測可以及早發現。

### 效能基準測試

```yaml
# .github/workflows/performance.yml
name: Performance Regression

on:
  pull_request:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run benchmarks
        run: |
          pytest tests/benchmarks/ --benchmark-json=benchmark.json

      - name: Compare with baseline
        run: |
          python scripts/compare_benchmarks.py \
            --current benchmark.json \
            --baseline benchmarks/baseline.json \
            --threshold 10  # 允許 10% 的效能波動

      - name: Alert on regression
        if: failure()
        run: |
          echo "⚠️ Performance regression detected!"
          echo "Please review the benchmark results."
```

### 負載測試

```yaml
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start application
        run: |
          docker-compose up -d
          sleep 30  # 等待啟動

      - name: Run k6 load test
        run: |
          k6 run tests/load/main.js \
            --out json=load-results.json

      - name: Check SLA
        run: |
          python scripts/check_sla.py \
            --results load-results.json \
            --p95-latency 200 \
            --error-rate 0.01
```

### 效能報告範本

```javascript
// tests/load/main.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // 暖機
    { duration: '3m', target: 100 },  // 正常負載
    { duration: '1m', target: 200 },  // 壓力測試
    { duration: '1m', target: 0 },    // 恢復
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'], // 95% 的請求要在 200ms 內
    http_req_failed: ['rate<0.01'],   // 錯誤率 < 1%
  },
};

export default function () {
  const res = http.get('http://localhost:8000/api/products');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
  });
  sleep(1);
}
```

---

## 10.4 安全性掃描整合

安全性是不能妥協的。讓 AI 幫你找出潛在的安全問題。

### 靜態安全掃描

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Python 安全掃描
      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-report.json

      # 依賴套件漏洞檢查
      - name: Run Safety
        run: |
          pip install safety
          safety check --json > safety-report.json

      # 密碼洩漏檢查
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      # AI 安全審查
      - name: AI Security Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          claude-code security-review \
            --bandit bandit-report.json \
            --safety safety-report.json \
            --output security-summary.md
```

### 安全審查的 I-B-C 指令

```
【Intent】
審查這段程式碼的安全性，找出潛在的安全漏洞。

【Behavior】
檢查以下安全問題：

1. 注入攻擊
   - SQL injection
   - Command injection
   - XSS

2. 認證與授權
   - 硬編碼密碼
   - 不安全的認證機制
   - 權限繞過

3. 資料保護
   - 敏感資料明文傳輸
   - 不安全的加密方式
   - 資料洩漏

4. 輸入驗證
   - 缺乏輸入驗證
   - 不安全的反序列化

輸出格式：
- 🔴 Critical: 必須立即修復
- 🟡 High: 應該修復
- 🔵 Medium: 建議修復
- ⚪ Low: 參考

【Context】
- 這是一個 Python FastAPI 應用
- 使用 SQLAlchemy ORM
- 敏感資料包括用戶密碼、信用卡號

【程式碼】
{貼上要審查的程式碼}
```

---

## 10.5 建立團隊的品質守門機制

把所有檢查整合成一個完整的「品質守門」。

### 完整的 CI/CD Pipeline

```yaml
# .github/workflows/quality-gate.yml
name: Quality Gate

on:
  pull_request:
    branches: [main]

jobs:
  # Stage 1: 基本檢查
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check src/

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install mypy
      - run: mypy src/

  # Stage 2: 測試
  unit-test:
    needs: [lint, type-check]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest tests/unit/ --cov=src --cov-fail-under=80

  integration-test:
    needs: [lint, type-check]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker-compose up -d
      - run: pytest tests/integration/

  # Stage 3: AI 審查
  ai-review:
    needs: [unit-test, integration-test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: AI Review
        run: |
          claude-code review --diff $(git diff origin/main...HEAD)

  # Stage 4: 安全與效能
  security-scan:
    needs: [ai-review]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bandit -r src/
      - run: safety check

  performance-test:
    needs: [ai-review]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest tests/benchmarks/

  # Stage 5: 最終守門
  quality-gate:
    needs: [security-scan, performance-test]
    runs-on: ubuntu-latest
    steps:
      - name: All checks passed
        run: echo "✅ Quality gate passed!"
```

### 品質守門規則

```markdown
# 品質守門規則

## 必須通過（Blocking）
- [ ] Lint 檢查通過（零錯誤）
- [ ] Type 檢查通過（零錯誤）
- [ ] 單元測試通過（100%）
- [ ] 測試覆蓋率 >= 80%
- [ ] 無 Critical 安全漏洞
- [ ] 效能無明顯回歸（< 10%）

## 建議通過（Non-blocking）
- [ ] AI Review 無 Critical/High 問題
- [ ] 整合測試通過
- [ ] 無 Medium 安全漏洞

## 豁免流程
如需豁免某項檢查，請：
1. 在 PR 說明中解釋原因
2. 標記為 `skip-{check-name}`
3. 獲得 Tech Lead 核准
```

### 視覺化品質報告

```yaml
  generate-report:
    needs: [quality-gate]
    runs-on: ubuntu-latest
    steps:
      - name: Generate Quality Report
        run: |
          cat << EOF > quality-report.md
          # Quality Report

          ## Summary
          | Check | Status |
          |-------|--------|
          | Lint | ✅ |
          | Type Check | ✅ |
          | Unit Tests | ✅ (Coverage: 85%) |
          | Integration Tests | ✅ |
          | AI Review | ✅ (0 critical, 2 suggestions) |
          | Security | ✅ (0 vulnerabilities) |
          | Performance | ✅ (P95: 150ms) |

          ## Details
          ...
          EOF

      - name: Post report to PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('quality-report.md', 'utf8');
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: report
            });
```

---

## 本章重點回顧

- **要點 1**：把 AI Code Review 整合到 CI/CD，自動檢查每一個 PR。

- **要點 2**：讓 AI 自動補充測試覆蓋，確保程式碼品質。

- **要點 3**：效能回歸檢測可以及早發現效能問題。

- **要點 4**：安全性掃描是不能跳過的品質守門。

- **要點 5**：完整的品質守門機制整合所有檢查，確保只有高品質的程式碼能夠合併。

---

## 大腦體操 🧠

**問題 1：**
為什麼 AI Review 應該放在單元測試之後，而不是之前？

**問題 2：**
設計一個效能回歸檢測的判斷邏輯：什麼情況下應該阻止合併？

**問題 3：**
你的團隊目前的 CI/CD 流程是什麼？可以加入本章哪些檢查？

---

## 全書總結

恭喜你完成了這本書！讓我們回顧一下你學到了什麼：

### 第一部：思維重塑
- AI 時代的開發者需要從「程式員」轉變為「AI 工作流程架構師」
- 金字塔原則：結論先行、結構清晰
- I-B-C 框架：Intent、Behavior、Context

### 第二部：實戰技法
- Intent：用 User Story 表達意圖
- Behavior：用測試案例定義完成標準
- Context：提供完整的執行環境

### 第三部：高階整合
- 從 PRD 到任務清單的拆解方法
- 迭代修正與品質守門
- CI/CD 自動化整合

### 行動建議

1. **今天就開始**：選一個小任務，用 I-B-C 框架寫指令
2. **建立 .claude/ 資料夾**：整理你的專案知識庫
3. **設計你的 Review Checklist**：系統化品質把關
4. **逐步自動化**：把檢查整合到 CI/CD

### 最後的話

AI 不會取代工程師——但會使用 AI 的工程師會取代不會使用的。

你已經學會了如何成為一個「AI 工作流程架構師」。現在，去實踐吧！

**祝你 coding 愉快！**

---

> 📝 **讀者筆記區**
>
> 這本書對你最有價值的是哪個部分？
>
> _________________________________
>
> 你打算在工作中首先應用哪個技巧？
>
> _________________________________
>
> 還有什麼問題是這本書沒有回答的？
>
> _________________________________
