# Chapter 14: 團隊協作與知識資產化

> "The best code is not the one that works, but the one that your teammates can understand and maintain." — Collaborative Development Wisdom

經過前 13 章的深入探討，我們已經掌握了 dbt 遷移的技術細節——從模式設計、增量策略到生產部署。但技術只是成功的一半，另一半在於人：如何讓團隊有效協作？如何將個人經驗轉化為組織知識資產？

M3 團隊在這個旅程中發現，真正的挑戰不是寫出能運行的 dbt 代碼，而是建立一套讓整個團隊都能理解、維護和演進的知識體系。本章將分享他們在團隊協作和知識管理方面的實踐經驗。

## 14.1 Code Review 文化建立

### 14.1.1 為什麼 Code Review 如此重要？

M3 團隊最初認為 Code Review 只是"找錯誤"，但經過一年的實踐後，他們發現了更深層的價值：

**Code Review 的三重價值**

1. **品質保障** (Quality Gate)
   - 發現邏輯錯誤、性能問題
   - 確保遵循團隊規範
   - 防止技術債累積

2. **知識傳播** (Knowledge Sharing)
   - 新人了解業務邏輯和技術模式
   - 資深工程師傳遞最佳實踐
   - 團隊成員互相學習

3. **決策記錄** (Decision Log)
   - 記錄為什麼這樣設計
   - 保存替代方案的討論
   - 未來重構時的參考依據

**真實案例**

Jerry 在一次 Code Review 中發現了一個看似正常的 SQL：

```sql
-- ❌ 問題代碼（通過了測試，但有潛在風險）
select
    order_id,
    customer_id,
    sum(amount) as total_amount
from {{ ref('stg_order_items') }}
group by 1, 2  -- 使用數字引用
```

Code Review 中的討論：

```markdown
**Reviewer (Alice)**: 👀 這裡使用數字引用 `group by 1, 2` 可能會有維護風險。
如果未來有人在 select 中間插入新欄位，分組邏輯會悄悄改變。

**Author (Jerry)**: 🤔 有道理！我改用明確的欄位名稱。

**Updated Code**:
```sql
select
    order_id,
    customer_id,
    sum(amount) as total_amount
from {{ ref('stg_order_items') }}
group by order_id, customer_id  -- 明確欄位名稱
```

這個小小的改進避免了未來可能的嚴重 bug，而且讓後續維護者更容易理解代碼意圖。

### 14.1.2 建立 Code Review 標準

M3 團隊制定了一套 "Code Review Checklist"，確保每次審查都全面且高效。

**dbt 專屬 Code Review Checklist**

```markdown
# dbt Code Review Checklist

## 📋 基礎檢查 (Must Have)

### SQL 品質
- [ ] 是否有分區過濾？（避免全表掃描）
  ```sql
  -- ✅ 好
  where partition_date >= '2024-01-01'

  -- ❌ 壞
  where customer_id = 123  -- 沒有分區過濾
  ```

- [ ] JOIN 條件是否完整？（避免笛卡爾積）
  ```sql
  -- ✅ 好
  from orders o
  join customers c
    on o.customer_id = c.customer_id
    and o.partition_date = c.partition_date  -- 分區對齊

  -- ❌ 壞
  from orders o
  join customers c
    on o.customer_id = c.customer_id  -- 缺少分區條件
  ```

- [ ] 聚合函數是否處理 NULL？
  ```sql
  -- ✅ 好
  sum(coalesce(amount, 0)) as total_amount
  count(distinct customer_id) as unique_customers

  -- ❌ 壞
  sum(amount) as total_amount  -- NULL 會被忽略
  ```

- [ ] 是否避免 SELECT *？
  ```sql
  -- ✅ 好
  select order_id, customer_id, amount
  from {{ ref('stg_orders') }}

  -- ❌ 壞
  select * from {{ ref('stg_orders') }}  -- 不明確依賴哪些欄位
  ```

### dbt 配置
- [ ] materialized 策略是否合理？
  - 小於 1GB 且每次全量計算 → `table`
  - 大於 1GB 且可增量更新 → `incremental`
  - 輕量計算且下游少 → `view`

- [ ] incremental 模型是否有正確的 unique_key？
  ```sql
  {{ config(
      materialized='incremental',
      unique_key='order_id',  -- ✅ 明確的唯一鍵
      partition_by={'field': 'order_date', 'data_type': 'date'}
  ) }}
  ```

- [ ] 分區配置是否正確？
  ```sql
  {{ config(
      partition_by={
          'field': 'event_date',
          'data_type': 'date',
          'granularity': 'day'  -- ✅ 明確粒度
      }
  ) }}
  ```

- [ ] 是否有 cluster_by？（提升查詢效能）
  ```sql
  {{ config(
      cluster_by=['customer_id', 'product_category']  -- 常用過濾條件
  ) }}
  ```

### 測試覆蓋
- [ ] 主鍵有 unique 和 not_null 測試？
  ```yaml
  columns:
    - name: order_id
      tests:
        - unique
        - not_null
  ```

- [ ] 外鍵有 relationships 測試？
  ```yaml
  - name: customer_id
    tests:
      - relationships:
          to: ref('dim_customers')
          field: customer_id
  ```

- [ ] 業務邏輯有 data test？
  ```yaml
  - name: total_amount
    tests:
      - dbt_utils.expression_is_true:
          expression: ">= 0"  -- 金額不能為負
  ```

### 文檔完整性
- [ ] 模型有 description？
- [ ] 關鍵欄位有說明？
- [ ] 複雜邏輯有注釋？

## 🎯 進階檢查 (Nice to Have)

### 效能優化
- [ ] 是否可以用 CTE 減少重複計算？
  ```sql
  -- ✅ 好：使用 CTE
  with order_summary as (
      select customer_id, sum(amount) as total
      from {{ ref('stg_orders') }}
      group by 1
  )
  select * from order_summary where total > 1000
  union all
  select * from order_summary where total <= 1000

  -- ❌ 壞：重複計算
  select customer_id, sum(amount) as total
  from {{ ref('stg_orders') }}
  group by 1
  having sum(amount) > 1000
  union all
  select customer_id, sum(amount) as total
  from {{ ref('stg_orders') }}
  group by 1
  having sum(amount) <= 1000
  ```

- [ ] 是否需要增加索引（cluster_by）？
- [ ] 查詢成本是否在可接受範圍？（< $10 per run）

### 可維護性
- [ ] 變數命名是否清晰？
  ```sql
  -- ✅ 好
  {% set reporting_start_date = '2024-01-01' %}

  -- ❌ 壞
  {% set sd = '2024-01-01' %}  -- 不清楚是什麼
  ```

- [ ] 是否使用 macro 避免重複代碼？
- [ ] 複雜邏輯是否拆分成多個 CTE？

### 安全性
- [ ] 是否有硬編碼的敏感資訊？（API key, 密碼等）
- [ ] 是否正確使用 env_var？
  ```sql
  -- ✅ 好
  where project_id = '{{ env_var("PROJECT_ID") }}'

  -- ❌ 壞
  where project_id = 'my-prod-project'  -- 硬編碼
  ```

## 💬 溝通規範

### 提供建設性反饋
- 使用問句而非命令："這裡是否可以考慮...？" vs "這裡必須改成..."
- 說明理由："建議使用分區過濾，因為可以降低成本..."
- 提供範例代碼

### 響應 Review 意見
- 及時回應：24 小時內
- 逐條討論：對每個 comment 回覆
- 不同意見時：提供替代方案或數據支持

## ✅ 批准標準

- 至少 1 位資深工程師 approve
- 所有 comments 已解決（resolved）
- CI/CD 測試全部通過
- 影響分析文檔已完成（如有 schema 變更）
```

### 14.1.3 Code Review 工具與流程

**GitHub Pull Request 模板**

M3 團隊使用標準化的 PR 模板確保信息完整：

```markdown
<!-- .github/pull_request_template.md -->

## 📝 變更摘要
<!-- 簡要描述這個 PR 的目的 -->

## 🎯 變更類型
- [ ] 🆕 新功能 (New Feature)
- [ ] 🐛 Bug 修復 (Bug Fix)
- [ ] ♻️ 重構 (Refactor)
- [ ] 📝 文檔更新 (Documentation)
- [ ] ⚡ 性能優化 (Performance)
- [ ] 🧪 測試 (Test)

## 🔍 變更詳情

### 修改的模型
- `models/staging/stg_orders.sql` - 新增 customer_segment 欄位
- `models/marts/daily_revenue.sql` - 調整分群邏輯

### 資料影響範圍
<!-- dbt ls --select state:modified+ --output json 的結果 -->
- 直接修改: 2 個模型
- 下游影響: 5 個模型
- 預估查詢成本: $5.20 per run

## 🧪 測試結果

### 本地測試
```bash
$ dbt run --select +stg_orders
Running with dbt=1.5.0
Completed successfully

$ dbt test --select stg_orders+
Completed successfully, 12 tests passed
```

### QA 環境驗證
- [x] 數據一致性檢查通過
- [x] 效能測試通過（執行時間 < 5 min）
- [x] 下游報表驗證通過

## 📸 截圖/數據示例
<!-- 如有 UI 變更或數據格式變更，提供截圖或示例 -->

| customer_id | customer_segment | total_orders |
|-------------|------------------|--------------|
| 12345       | VIP              | 150          |
| 67890       | Regular          | 25           |

## 🚀 部署計劃

- [ ] 已通知下游用戶（如有 schema 變更）
- [ ] 已更新 CHANGELOG
- [ ] 已準備 rollback 腳本
- [ ] 預定部署時間: 2024-01-15 14:00 (非業務高峰)

## 📋 Checklist

- [ ] 代碼遵循團隊規範
- [ ] 添加了必要的測試
- [ ] 更新了相關文檔
- [ ] 本地測試全部通過
- [ ] QA 環境驗證通過
- [ ] 影響分析已完成
- [ ] Code Review Checklist 已自查

## 🔗 相關資源

- Issue: #123
- 設計文檔: [link]
- 性能分析: [link]

---

<!-- 自動生成的影響分析（由 CI/CD 填充） -->
### 自動影響分析
```json
{
  "modified_models": ["stg_orders"],
  "downstream_models": 5,
  "estimated_cost": "$5.20",
  "test_coverage": "85%"
}
```
```

**自動化 Code Review 輔助**

```yaml
# .github/workflows/pr_review.yml
# 自動運行 Code Review 檢查

name: PR Review Checks

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  auto-review:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install dbt-bigquery sqlfluff
          dbt deps

      - name: SQL Linting
        run: |
          # 檢查修改的 SQL 文件
          FILES=$(git diff --name-only origin/main | grep "\.sql$")
          if [ -n "$FILES" ]; then
              sqlfluff lint $FILES --dialect bigquery --format github-annotation
          fi

      - name: dbt Compile Check
        run: |
          dbt compile --select state:modified --state ./manifests/prod/

      - name: dbt Test
        run: |
          dbt test --select state:modified+ --state ./manifests/prod/

      - name: Impact Analysis
        run: |
          # 生成影響分析報告
          python scripts/generate_impact_analysis.py > impact_analysis.md

      - name: Post Comment
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const impact = fs.readFileSync('impact_analysis.md', 'utf8');

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 🤖 自動影響分析\n\n${impact}`
            });

      - name: Check Test Coverage
        run: |
          # 檢查測試覆蓋率
          python scripts/check_test_coverage.py --threshold 70
```

**影響分析腳本**

```python
# scripts/generate_impact_analysis.py
# 生成 PR 影響分析報告

import json
import subprocess
from google.cloud import bigquery

def generate_impact_analysis():
    """生成詳細的影響分析報告"""

    # 1. 獲取修改的模型
    result = subprocess.run(
        ['dbt', 'ls', '--select', 'state:modified+', '--state', './manifests/prod/', '--output', 'json'],
        capture_output=True,
        text=True
    )

    models = [json.loads(line) for line in result.stdout.strip().split('\n') if line]

    print("# 影響分析報告\n")

    # 2. 模型影響範圍
    print("## 📊 變更範圍\n")
    print(f"- **直接修改**: {len([m for m in models if 'modified' in m.get('tags', [])])} 個模型")
    print(f"- **下游影響**: {len(models)} 個模型（包含上游依賴）\n")

    # 3. 按類型分類
    print("## 🏷️ 模型分類\n")
    staging = [m for m in models if 'staging' in m['path']]
    marts = [m for m in models if 'marts' in m['path']]

    print(f"- Staging 層: {len(staging)} 個")
    print(f"- Marts 層: {len(marts)} 個\n")

    # 4. 高風險模型
    print("## ⚠️  高風險變更\n")
    high_risk = [m for m in models if 'mart' in m['path'] or 'prod_' in m['name']]

    if high_risk:
        print("以下模型影響業務報表，需要特別注意：\n")
        for model in high_risk:
            print(f"- `{model['name']}` ({model['path']})")
    else:
        print("無高風險變更\n")

    # 5. 成本估算
    print("\n## 💰 成本估算\n")
    client = bigquery.Client()

    total_cost = 0
    for model in models:
        # 查詢歷史運行成本
        query = f"""
        SELECT AVG(total_bytes_processed) / POW(10, 12) * 5 as avg_cost
        FROM `{project_id}.region-asia-east1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
        WHERE referenced_tables LIKE '%{model['name']}%'
          AND creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        LIMIT 10
        """

        try:
            result = client.query(query).result()
            row = next(result)
            cost = row.avg_cost if row.avg_cost else 0
            total_cost += cost
        except:
            pass

    print(f"- 預估單次運行成本: **${total_cost:.2f}**")
    print(f"- 每日運行成本（假設 4 次）: **${total_cost * 4:.2f}**\n")

    # 6. 測試覆蓋率
    print("## 🧪 測試覆蓋率\n")

    test_result = subprocess.run(
        ['dbt', 'test', '--select', 'state:modified+', '--state', './manifests/prod/', '--output', 'json'],
        capture_output=True,
        text=True
    )

    tests = [json.loads(line) for line in test_result.stdout.strip().split('\n') if line]
    passed = len([t for t in tests if t.get('status') == 'pass'])
    total = len(tests)

    coverage = (passed / total * 100) if total > 0 else 0

    print(f"- 總測試數: {total}")
    print(f"- 通過: {passed}")
    print(f"- 覆蓋率: **{coverage:.1f}%**\n")

    if coverage < 70:
        print("⚠️  警告: 測試覆蓋率低於 70%，建議增加測試\n")

    # 7. 建議操作
    print("## ✅ 建議操作\n")

    if high_risk:
        print("- [ ] 通知下游用戶（業務報表可能受影響）")

    if total_cost > 10:
        print("- [ ] 成本較高，考慮優化查詢")

    if coverage < 70:
        print("- [ ] 增加測試覆蓋率")

    print("- [ ] QA 環境驗證數據一致性")
    print("- [ ] 準備 rollback 計劃")

if __name__ == "__main__":
    generate_impact_analysis()
```

輸出示例：

```markdown
# 影響分析報告

## 📊 變更範圍

- **直接修改**: 2 個模型
- **下游影響**: 7 個模型（包含上游依賴）

## 🏷️ 模型分類

- Staging 層: 2 個
- Marts 層: 5 個

## ⚠️  高風險變更

以下模型影響業務報表，需要特別注意：

- `daily_revenue_summary` (models/marts/finance/daily_revenue_summary.sql)
- `customer_retention_cohort` (models/marts/marketing/customer_retention_cohort.sql)

## 💰 成本估算

- 預估單次運行成本: **$6.50**
- 每日運行成本（假設 4 次）: **$26.00**

## 🧪 測試覆蓋率

- 總測試數: 18
- 通過: 18
- 覆蓋率: **100%**

## ✅ 建議操作

- [ ] 通知下游用戶（業務報表可能受影響）
- [ ] QA 環境驗證數據一致性
- [ ] 準備 rollback 計劃
```

### 14.1.4 高效 Code Review 技巧

**對於 Reviewer**

1. **優先級排序**
   - P0: 邏輯錯誤、安全問題、性能嚴重問題
   - P1: 代碼品質、可維護性問題
   - P2: 風格、命名建議

2. **使用建議模式 (Suggestion Mode)**

   GitHub 支援直接在 comment 中提供代碼建議：

   ```markdown
   建議使用明確的欄位名稱:

   ```suggestion
   group by order_id, customer_id
   ```
   ```

   作者可以直接點擊 "Commit suggestion" 應用修改。

3. **區分 Blocker 和 Non-blocker**

   ```markdown
   🚫 **Blocker**: 這個 JOIN 條件會導致笛卡爾積，必須修復

   💡 **Suggestion**: 可以考慮用 COALESCE 處理 NULL，但不強制要求
   ```

**對於 Author**

1. **小步提交 (Small Commits)**
   - 一個 PR 只做一件事
   - 避免 "大雜燴" PR（難以 review）
   - 理想大小：< 400 行代碼變更

2. **自我 Review**
   - 提交 PR 前先自己過一遍 Code Review Checklist
   - 使用 GitHub 的 "Draft PR" 功能進行自查

3. **響應速度**
   - 24 小時內響應 review comments
   - 不清楚的地方主動詢問

## 14.2 文檔即知識

### 14.2.1 為什麼文檔如此重要？

M3 團隊在遷移初期忽視了文檔，結果導致：

**痛苦案例**

```
情境: 新成員 Bob 加入團隊，需要理解 daily_revenue_summary 的邏輯

Bob: "這個 customer_segment 是怎麼計算的？"
Jerry: "呃...我記得是按年消費金額分的..."
Alice: "不對，我記得還考慮了購買頻率"
[翻了半小時代碼才確認邏輯...]

損失: 半小時 × 3人 = 1.5 小時
```

如果有文檔：

```yaml
# models/marts/schema.yml
models:
  - name: daily_revenue_summary
    description: |
      每日營收匯總表

      **業務邏輯**:
      - customer_segment 分群規則:
        - VIP: 年消費 > $10,000 且購買次數 > 20
        - Regular: 年消費 $1,000 - $10,000
        - New: 首次購買用戶

      **數據來源**: stg_orders, stg_customers
      **更新頻率**: 每小時
      **負責人**: @jerry

    columns:
      - name: customer_segment
        description: |
          客戶分群（基於過去 365 天的消費行為）

          計算邏輯見 macros/calculate_customer_segment.sql

          **注意**: 2024-01-01 之前的數據使用舊分群邏輯
```

Bob 可以在 2 分鐘內找到答案，節省了 1.5 小時。

### 14.2.2 dbt 文檔最佳實踐

**1. 模型文檔結構**

```yaml
# models/staging/schema.yml
version: 2

models:
  - name: stg_orders
    description: |
      訂單事件 staging 層模型

      ## 業務背景
      處理來自電商平台的訂單數據，包含訂單基本信息、金額、狀態等。

      ## 數據來源
      - **來源表**: `raw_data.order_events`
      - **更新頻率**: 實時（事件驅動）
      - **數據保留期**: 90 天

      ## 轉換邏輯
      1. 過濾測試訂單（order_id 前綴為 'TEST_'）
      2. 標準化狀態碼（pending → PENDING, complete → COMPLETED）
      3. 計算訂單總金額（含稅）
      4. 轉換時區（UTC → Asia/Taipei）

      ## 已知問題
      - ⚠️  2024-01-01 之前的訂單可能缺少 customer_email
      - ⚠️  部分歷史訂單的 tax_amount 為 NULL

      ## 變更歷史
      - 2024-01-15: 新增 customer_segment 欄位 (#123)
      - 2024-01-10: 修改增量邏輯，改用 updated_at (#115)
      - 2024-01-01: 初始版本

      ## 相關資源
      - 業務文檔: [訂單系統說明](link)
      - API 文檔: [Order API](link)
      - 負責人: @jerry, @alice

    config:
      materialized: incremental
      unique_key: order_id
      partition_by:
        field: order_date
        data_type: date

    columns:
      - name: order_id
        description: |
          訂單唯一識別碼

          **格式**: ORD_{timestamp}_{random}
          **範例**: ORD_20240115_A1B2C3
        tests:
          - unique
          - not_null

      - name: customer_id
        description: |
          客戶 ID，關聯到 {{ ref('dim_customers') }}

          **注意**:
          - 2024-01-01 之前的訂單可能為 NULL（訪客結帳）
          - 需要處理 NULL 值的下游模型請使用 COALESCE
        tests:
          - not_null:
              where: "order_date >= '2024-01-01'"  -- 只檢查新數據
          - relationships:
              to: ref('dim_customers')
              field: customer_id
              where: "customer_id is not null"

      - name: order_date
        description: |
          訂單日期（分區鍵）

          **時區**: Asia/Taipei
          **格式**: DATE
        tests:
          - not_null

      - name: status
        description: |
          訂單狀態

          **可能值**:
          - `PENDING`: 待處理
          - `CONFIRMED`: 已確認
          - `SHIPPED`: 已出貨
          - `DELIVERED`: 已送達
          - `CANCELLED`: 已取消
          - `REFUNDED`: 已退款
        tests:
          - accepted_values:
              values: ['PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED']

      - name: total_amount
        description: |
          訂單總金額（含稅）

          **單位**: TWD
          **計算**: item_amount + tax_amount + shipping_fee
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"  -- 金額不能為負

      - name: customer_segment
        description: |
          客戶分群標籤（2024-01-15 新增）

          **分群邏輯**:
          - `VIP`: 年消費 > $10,000 且購買次數 > 20
          - `Regular`: 年消費 $1,000 - $10,000
          - `New`: 首次購買用戶
          - `NULL`: 無法分群（訪客或數據不足）

          **計算邏輯**: 見 `macros/calculate_customer_segment.sql`
```

**2. Macro 文檔**

```sql
-- macros/calculate_customer_segment.sql

{% docs calculate_customer_segment %}
# 計算客戶分群

根據客戶過去 365 天的消費行為計算分群標籤。

## 使用方式

```sql
select
    customer_id,
    {{ calculate_customer_segment('customer_id', 'order_date') }} as segment
from {{ ref('stg_orders') }}
```

## 參數

- `customer_id_column`: 客戶 ID 欄位名稱（字串）
- `date_column`: 日期欄位名稱（字串）

## 分群規則

| 分群 | 條件 |
|------|------|
| VIP | 年消費 > $10,000 且購買次數 > 20 |
| Regular | 年消費 $1,000 - $10,000 |
| New | 首次購買用戶（< 30 天） |
| NULL | 無法分群（訪客或數據不足） |

## 範例輸出

| customer_id | segment |
|-------------|---------|
| 12345       | VIP     |
| 67890       | Regular |
| 11111       | New     |
| NULL        | NULL    |

## 性能考量

- 此 macro 會進行子查詢，建議在已聚合的數據上使用
- 避免在大表上直接調用（> 1M 行）

## 變更歷史

- 2024-01-15: 初始版本 (#123)

{% enddocs %}

{% macro calculate_customer_segment(customer_id_column, date_column) %}
case
    when annual_spend > 10000 and order_count > 20 then 'VIP'
    when annual_spend between 1000 and 10000 then 'Regular'
    when days_since_first_order < 30 then 'New'
    else null
end
{% endmacro %}
```

**3. 內嵌文檔（Doc Blocks）**

```sql
-- models/marts/daily_revenue.sql

{{ config(materialized='incremental', unique_key='date') }}

{% docs __daily_revenue_logic__ %}
## 計算邏輯

1. **基礎數據**: 從 stg_orders 聚合每日訂單
2. **排除規則**:
   - 測試訂單（order_id 前綴 'TEST_'）
   - 已取消訂單（status = 'CANCELLED'）
   - 已退款訂單（status = 'REFUNDED'）
3. **分群計算**: 使用 calculate_customer_segment macro
4. **聚合維度**: date, customer_segment

## 業務規則

- 營收以訂單「確認時間」為準（confirmed_at），非下單時間
- 部分退款的訂單計入營收，全額退款的訂單不計入
- 跨日訂單歸屬到確認日（而非下單日）

## 數據品質檢查

- 每日營收應 > 0（否則觸發告警）
- 每日訂單數應 > 100（低於此值可能是數據延遲）
- VIP 客群營收佔比應在 30-50% 之間

{% enddocs %}

with orders as (
    select
        date(confirmed_at) as date,
        {{ calculate_customer_segment('customer_id', 'order_date') }} as segment,
        sum(total_amount) as revenue,
        count(distinct order_id) as order_count
    from {{ ref('stg_orders') }}
    where status not in ('CANCELLED', 'REFUNDED')
      and order_id not like 'TEST_%'
    group by 1, 2
)

select * from orders
```

在 schema.yml 中引用：

```yaml
models:
  - name: daily_revenue
    description: |
      每日營收統計（按客群分）

      {{ doc('__daily_revenue_logic__') }}
```

**4. 生成並託管文檔**

```bash
# 生成文檔
dbt docs generate

# 本地預覽
dbt docs serve --port 8080

# 瀏覽器打開: http://localhost:8080
```

**託管文檔到內網**

```yaml
# .github/workflows/deploy-docs.yml
# 自動部署 dbt docs 到內部網站

name: Deploy dbt Docs

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Install dbt
        run: pip install dbt-bigquery

      - name: Generate docs
        run: |
          dbt deps
          dbt docs generate --target prod

      - name: Deploy to GCS
        run: |
          # 上傳到 Google Cloud Storage
          gsutil -m cp -r target/*.json target/*.html gs://m3-dbt-docs/

      - name: Notify team
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: '📚 dbt docs 已更新: https://dbt-docs.m3-internal.com'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

團隊成員可以隨時訪問最新文檔：`https://dbt-docs.m3-internal.com`

### 14.2.3 文檔維護策略

**文檔即代碼 (Docs as Code)**

M3 團隊將文檔維護納入 Code Review 流程：

```markdown
## Code Review Checklist

### 文檔檢查
- [ ] 新模型是否有 description？
- [ ] 新欄位是否有說明？
- [ ] 複雜邏輯是否有注釋或 doc block？
- [ ] CHANGELOG 是否更新？
- [ ] 如有 breaking change，是否有遷移指南？
```

**定期審查與更新**

```python
# scripts/check_doc_coverage.py
# 檢查文檔覆蓋率

import json

def check_doc_coverage():
    """檢查模型和欄位的文檔覆蓋率"""

    # 解析 manifest.json
    with open('target/manifest.json') as f:
        manifest = json.load(f)

    models = manifest['nodes']

    total_models = 0
    documented_models = 0
    total_columns = 0
    documented_columns = 0

    for node_id, node in models.items():
        if node['resource_type'] != 'model':
            continue

        total_models += 1

        # 檢查模型文檔
        if node.get('description'):
            documented_models += 1

        # 檢查欄位文檔
        for column_name, column in node.get('columns', {}).items():
            total_columns += 1
            if column.get('description'):
                documented_columns += 1

    model_coverage = documented_models / total_models * 100 if total_models > 0 else 0
    column_coverage = documented_columns / total_columns * 100 if total_columns > 0 else 0

    print(f"📊 文檔覆蓋率報告")
    print(f"")
    print(f"模型文檔覆蓋率: {documented_models}/{total_models} ({model_coverage:.1f}%)")
    print(f"欄位文檔覆蓋率: {documented_columns}/{total_columns} ({column_coverage:.1f}%)")

    # 設定門檻
    if model_coverage < 80:
        print(f"\n⚠️  警告: 模型文檔覆蓋率低於 80%")
        return 1

    if column_coverage < 60:
        print(f"\n⚠️  警告: 欄位文檔覆蓋率低於 60%")
        return 1

    print(f"\n✅ 文檔覆蓋率達標")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(check_doc_coverage())
```

整合到 CI/CD：

```yaml
# .github/workflows/ci.yml
- name: Check Documentation Coverage
  run: |
    dbt docs generate
    python scripts/check_doc_coverage.py
```

## 14.3 知識傳承機制

###  14.3.1 Onboarding 新成員

M3 團隊建立了系統性的新人培訓流程：

**Week 1: 環境設置與基礎概念**

```markdown
# 新人 Onboarding Checklist - Week 1

## Day 1: 環境設置
- [ ] 獲取 Google Cloud 訪問權限
- [ ] 安裝 dbt-bigquery (`pip install dbt-bigquery`)
- [ ] Clone 代碼倉庫
- [ ] 設置 profiles.yml（使用個人 OAuth）
- [ ] 運行 `dbt debug` 驗證連接
- [ ] 成功運行 `dbt run --select stg_orders`（第一個模型）

## Day 2: dbt 基礎
- [ ] 閱讀：dbt 官方文檔 - Core Concepts
- [ ] 閱讀：M3 團隊的 dbt 規範文檔
- [ ] 理解項目結構：staging / intermediate / marts
- [ ] 理解 ref() 和 source() 的區別

## Day 3: 實戰練習
- [ ] 任務 1: 在 dev 環境運行完整 pipeline
  ```bash
  dbt run --target dev
  dbt test --target dev
  ```

- [ ] 任務 2: 查看 dbt docs
  ```bash
  dbt docs generate
  dbt docs serve
  ```

- [ ] 任務 3: 理解 DAG（數據血緣圖）
  - 找到 `daily_revenue` 的上游依賴
  - 找到 `stg_orders` 的下游影響

## Day 4-5: Code Reading
- [ ] 閱讀 3 個 staging 模型（stg_orders, stg_customers, stg_products）
- [ ] 閱讀 2 個 marts 模型（daily_revenue, customer_cohort）
- [ ] 理解增量模型的運作方式
- [ ] 理解測試的配置（schema.yml）

## Week 1 結束：驗收
- [ ] 能夠獨立運行本地 dev 環境
- [ ] 能夠閱讀和理解現有模型
- [ ] 能夠使用 dbt docs 查找信息
- [ ] 完成第一個 PR（文檔修正或小 bug 修復）
```

**Week 2: 實戰與深入**

```markdown
# 新人 Onboarding Checklist - Week 2

## Day 1-2: 第一個功能開發
任務：為 `stg_orders` 添加新欄位 `is_first_purchase`

- [ ] 理解需求：標記是否為客戶的首次購買
- [ ] 查看相關模型和數據
- [ ] 實現邏輯（使用窗口函數 ROW_NUMBER）
- [ ] 添加測試（data test）
- [ ] 更新文檔（schema.yml）
- [ ] 提交 PR，經過 Code Review

## Day 3-4: 增量模型實作
任務：創建新的增量模型 `user_activity_daily`

- [ ] 理解增量模型的配置
  ```sql
  {{ config(
      materialized='incremental',
      unique_key='user_id || activity_date'
  ) }}
  ```

- [ ] 實現增量邏輯（過濾新數據）
- [ ] 測試全量刷新（--full-refresh）
- [ ] 測試增量運行
- [ ] 驗證數據一致性

## Day 5: 性能優化
- [ ] 使用 BigQuery 查看查詢計劃
- [ ] 理解分區（partition_by）的作用
- [ ] 理解聚類（cluster_by）的作用
- [ ] 優化一個慢查詢（> 1分鐘）

## Week 2 結束：驗收
- [ ] 能夠獨立開發新功能
- [ ] 理解增量模型的運作機制
- [ ] 能夠進行基本的性能優化
- [ ] 完成至少 2 個 PR 並合併
```

**Buddy System（導師制度）**

每個新人配對一位資深工程師作為 mentor：

```markdown
## Mentor 職責

### Week 1-2
- 每日 15 分鐘 check-in（回答問題，解決阻礙）
- Review 新人的第一個 PR（詳細指導）
- 分享團隊最佳實踐

### Week 3-4
- 每週 2 次 check-in
- Code Review 新人的 PR（逐漸提高標準）
- 介紹業務背景和數據流

### Month 2-3
- 每週 1 次 check-in
- 鼓勵新人主動提問和分享
- 逐步放手，讓新人獨立完成任務

## 新人職責

- 主動提問（沒有「笨問題」）
- 記錄學習筆記（FAQ 文檔）
- 完成 Onboarding Checklist
- 第一個月內至少提交 5 個 PR
```

**知識分享會（每週五下午)**

```markdown
## 技術分享會

### 格式
- 時間：每週五 14:00-15:00
- 形式：1 人分享（20 分鐘） + Q&A（10 分鐘）+ 自由討論（30 分鐘）

### 主題範例
- Week 1: "dbt 增量模型最佳實踐" - Jerry
- Week 2: "BigQuery 成本優化技巧" - Alice
- Week 3: "數據品質測試策略" - Bob
- Week 4: "新人分享：我在 M3 學到的 dbt 技巧" - 新人 Charlie

### 分享素材
- 放在 /docs/tech-sharing/ 目錄
- 鼓勵代碼示例和實戰案例
- 會後整理成文檔（知識庫）
```

### 14.3.2 FAQ 文檔累積

M3 團隊維護了一份活文檔，持續收集常見問題：

```markdown
# M3 dbt FAQ

> 本文檔由團隊共同維護，遇到新問題請及時補充！

## 基礎概念

### Q: ref() 和 source() 有什麼區別？

**A**:
- `source()`: 引用原始數據（raw data）
  ```sql
  select * from {{ source('raw_data', 'orders') }}
  ```

- `ref()`: 引用 dbt 模型（其他 dbt 轉換後的表）
  ```sql
  select * from {{ ref('stg_orders') }}
  ```

**最佳實踐**:
- Staging 層使用 `source()` 讀取原始數據
- 其他層使用 `ref()` 引用上游模型

---

### Q: 什麼時候用 table？什麼時候用 incremental？

**A**:

| 場景 | 建議 |
|------|------|
| 數據量 < 1GB | `table`（全量刷新） |
| 數據量 > 1GB 且可增量 | `incremental` |
| 輕量計算且下游少 | `view` |
| 臨時性分析 | `ephemeral` |

**判斷標準**:
1. 數據量大小
2. 是否可以增量更新（有時間戳或遞增 ID）
3. 查詢頻率（經常查詢 → table/incremental，偶爾查詢 → view）

---

### Q: 增量模型的 unique_key 如何選擇？

**A**:

**單欄位唯一鍵**:
```sql
{{ config(
    materialized='incremental',
    unique_key='order_id'  -- 單一主鍵
) }}
```

**複合唯一鍵**:
```sql
{{ config(
    materialized='incremental',
    unique_key='user_id || "-" || activity_date'  -- 組合鍵
) }}
```

**陣列形式（dbt 1.6+）**:
```sql
{{ config(
    materialized='incremental',
    unique_key=['user_id', 'activity_date']  -- 陣列形式
) }}
```

**最佳實踐**:
- 確保 unique_key 真的唯一（否則數據會重複）
- 測試 unique_key: `dbt test` 中加入 `unique` 測試

---

## 常見錯誤

### Q: "Compilation Error: Model 'xxx' depends on a node named 'yyy' which was not found"

**原因**:
- ref() 中的模型名稱錯誤
- 該模型尚未創建或被刪除

**解決**:
```sql
-- ❌ 錯誤
select * from {{ ref('stg_order') }}  -- 缺少 's'

-- ✅ 正確
select * from {{ ref('stg_orders') }}
```

---

### Q: 增量模型運行後數據重複了

**原因**:
- unique_key 配置錯誤或缺失
- unique_key 實際上不唯一

**診斷**:
```sql
-- 檢查是否有重複
select
    unique_key_column,
    count(*) as cnt
from {{ ref('your_model') }}
group by 1
having count(*) > 1
```

**解決**:
1. 確認 unique_key 配置正確
2. 如果數據本身有重複，先去重：
   ```sql
   {{ config(unique_key='order_id') }}

   with deduplicated as (
       select *,
              row_number() over (partition by order_id order by updated_at desc) as rn
       from {{ source('raw', 'orders') }}
   )
   select * from deduplicated where rn = 1
   ```

---

## 性能優化

### Q: 查詢很慢，如何優化？

**診斷步驟**:

1. **檢查是否有分區過濾**
   ```sql
   -- ❌ 慢：全表掃描
   select * from {{ ref('stg_orders') }}
   where customer_id = 12345

   -- ✅ 快：分區過濾
   select * from {{ ref('stg_orders') }}
   where order_date >= '2024-01-01'
     and customer_id = 12345
   ```

2. **添加 cluster_by**
   ```sql
   {{ config(
       partition_by={'field': 'order_date', 'data_type': 'date'},
       cluster_by=['customer_id', 'product_id']  -- 常用過濾條件
   ) }}
   ```

3. **檢查 JOIN 條件**
   ```sql
   -- ❌ 慢：笛卡爾積
   from orders o
   join customers c on o.customer_id = c.customer_id

   -- ✅ 快：分區對齊
   from orders o
   join customers c
     on o.customer_id = c.customer_id
     and o.partition_date = c.partition_date
   ```

---

### Q: BigQuery 成本太高，如何降低？

**成本優化技巧**:

1. **使用分區表** → 減少掃描數據量
2. **使用 cluster_by** → 進一步減少掃描
3. **避免 SELECT *** → 只選擇需要的欄位
4. **使用增量模型** → 避免全量刷新
5. **設置查詢優先級**:
   ```yaml
   # profiles.yml
   prod:
     priority: batch  # 降低優先級，使用更便宜的 slot
   ```

**監控成本**:
```sql
-- 查詢最近 7 天的成本
SELECT
    user_email,
    SUM(total_bytes_processed) / POW(10, 12) * 5 as cost_usd
FROM `project.region.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY 1
ORDER BY 2 DESC
```

---

## 測試相關

### Q: 如何測試增量模型？

**測試流程**:

```bash
# 1. 全量刷新
dbt run --select my_incremental_model --full-refresh

# 2. 記錄行數
ROW_COUNT_1=$(bq query --format=csv --use_legacy_sql=false \
  "SELECT COUNT(*) FROM \`project.dataset.my_incremental_model\`")

# 3. 增量運行
dbt run --select my_incremental_model

# 4. 驗證行數增加
ROW_COUNT_2=$(bq query --format=csv --use_legacy_sql=false \
  "SELECT COUNT(*) FROM \`project.dataset.my_incremental_model\`")

# 5. 檢查是否有重複
bq query --use_legacy_sql=false \
  "SELECT unique_key, COUNT(*) as cnt
   FROM \`project.dataset.my_incremental_model\`
   GROUP BY 1 HAVING COUNT(*) > 1"
```

---

## 部署相關

### Q: 如何回滾生產環境的變更？

**快速回滾（藍綠部署）**:
```bash
# 切換到上一個環境
./scripts/rollback.sh

# 執行時間: < 2 分鐘
```

**數據回滾（Time Travel）**:
```sql
-- 恢復 2 小時前的數據
CREATE OR REPLACE TABLE `project.dataset.table` AS
SELECT * FROM `project.dataset.table`
FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR);
```

詳見: [Chapter 13: Rollback 機制](chapter-13.md#rollback)

---

## 如何貢獻

遇到新問題？請補充到這份文檔！

1. Fork 這份文檔
2. 添加你的 Q&A
3. 提交 PR
4. Review 通過後合併

維護者: @jerry, @alice
最後更新: 2024-01-15
```

---

**小結**

第 14 章的前 3 節建立了完整的團隊協作框架：

1. **Code Review 文化**: 不只找錯誤，更是知識傳播和決策記錄
2. **文檔即知識**: 系統性的文檔規範，確保知識可見可用
3. **知識傳承**: Onboarding流程、Buddy制度、FAQ累積，讓經驗沉澱為組織資產

接下來的兩節將探討最佳實踐總結和全書總結，為整個 dbt 遷移之旅畫上完美句號。

## 14.4 dbt 遷移最佳實踐總結

經過 M3 團隊一年的實戰經驗，我們總結出一套經過驗證的最佳實踐。這些原則不僅適用於從 SQL 到 dbt 的遷移，也適用於任何數據轉換專案。

### 14.4.1 技術層面的最佳實踐

**1. 模型設計原則**

```markdown
## 分層架構 (Layered Architecture)

### Staging 層
**目的**: 清洗和標準化原始數據
**規則**:
- 1:1 對應原始表
- 只做基礎清洗（去除測試數據、標準化命名、類型轉換）
- 不做業務邏輯
- 所有下游模型都應該從 staging 層讀取，而非直接讀原始數據

✅ 好的例子:
```sql
-- models/staging/stg_orders.sql
select
    order_id,
    lower(trim(customer_email)) as customer_email,  -- 標準化
    cast(order_date as date) as order_date,
    amount / 100.0 as amount  -- 單位轉換（分 → 元）
from {{ source('raw', 'orders') }}
where order_id not like 'TEST_%'  -- 過濾測試數據
```

❌ 壞的例子:
```sql
-- staging 層不應該有複雜業務邏輯
select
    order_id,
    case
        when total_amount > 10000 then 'VIP'  -- ❌ 業務邏輯應在 marts 層
        when total_amount > 1000 then 'Regular'
        else 'Normal'
    end as customer_segment
from {{ source('raw', 'orders') }}
```

### Intermediate 層
**目的**: 可重用的中間邏輯
**規則**:
- 複雜計算和轉換
- 可被多個 marts 模型引用
- 通常配置為 ephemeral 或 view

✅ 好的例子:
```sql
-- models/intermediate/int_customer_metrics.sql
{{ config(materialized='ephemeral') }}

select
    customer_id,
    count(distinct order_id) as lifetime_orders,
    sum(amount) as lifetime_revenue,
    max(order_date) as last_order_date
from {{ ref('stg_orders') }}
group by 1
```

### Marts 層
**目的**: 業務邏輯和最終報表
**規則**:
- 面向業務場景（finance, marketing, operations）
- 包含業務邏輯和指標計算
- 通常配置為 table 或 incremental

✅ 好的例子:
```sql
-- models/marts/finance/daily_revenue_by_segment.sql
with customer_metrics as (
    select * from {{ ref('int_customer_metrics') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
)

select
    date(order_date) as date,
    case
        when cm.lifetime_revenue > 10000 then 'VIP'
        when cm.lifetime_revenue > 1000 then 'Regular'
        else 'New'
    end as customer_segment,
    sum(o.amount) as revenue,
    count(distinct o.order_id) as orders
from orders o
left join customer_metrics cm using (customer_id)
group by 1, 2
```
```

**2. 配置策略**

```yaml
# dbt_project.yml - 推薦的配置模板

models:
  your_project:
    # Staging 層
    staging:
      +materialized: view  # 輕量，快速
      +schema: staging
      +tags: ['staging']

    # Intermediate 層
    intermediate:
      +materialized: ephemeral  # 不實體化，減少儲存
      +schema: intermediate
      +tags: ['intermediate']

    # Marts 層
    marts:
      +materialized: table  # 預設為 table
      +schema: marts
      +tags: ['marts']

      # Finance 子目錄：高價值表用 incremental
      finance:
        +partition_by:
          field: date
          data_type: date
        +cluster_by: ['customer_segment']

        # 大表用增量
        daily_revenue:
          +materialized: incremental
          +unique_key: date || '-' || customer_segment

      # Marketing 子目錄
      marketing:
        +partition_by:
          field: event_date
          data_type: date
```

**3. 測試策略**

```yaml
# 推薦的測試配置

models:
  - name: stg_orders
    description: "訂單 staging 表"

    columns:
      # 主鍵: unique + not_null
      - name: order_id
        tests:
          - unique
          - not_null

      # 外鍵: relationships
      - name: customer_id
        tests:
          - not_null
          - relationships:
              to: ref('stg_customers')
              field: customer_id

      # 業務規則: accepted_values
      - name: status
        tests:
          - accepted_values:
              values: ['PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED']

      # 數值約束: expression_is_true
      - name: amount
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"

# 自定義 data test
tests:
  - name: test_daily_revenue_positive
    description: "每日營收應為正數"
    columns:
      - name: revenue
        tests:
          - dbt_utils.expression_is_true:
              expression: "> 0"
```

**測試覆蓋率目標**:
- Staging 層: 100%（所有主鍵和外鍵都有測試）
- Intermediate 層: 80%
- Marts 層: 90%（業務關鍵表 100%）

**4. 性能優化 Checklist**

```markdown
## 性能優化檢查清單

### BigQuery 特定優化

#### 分區 (Partition)
- [ ] 所有大表（> 1GB）都有分區
- [ ] 分區欄位是查詢中常用的過濾條件（通常是日期）
- [ ] 所有查詢都包含分區過濾

範例:
```yaml
{{ config(
    partition_by={
        'field': 'order_date',
        'data_type': 'date',
        'granularity': 'day'
    }
) }}
```

#### 聚類 (Clustering)
- [ ] 分區表添加了 cluster_by（最多 4 個欄位）
- [ ] cluster_by 欄位是查詢中常用的過濾/JOIN 條件
- [ ] cluster_by 欄位按基數從高到低排序

範例:
```yaml
{{ config(
    cluster_by=['customer_id', 'product_category', 'region']
    # customer_id: 基數最高（百萬級）
    # product_category: 基數中等（百級）
    # region: 基數最低（十級）
) }}
```

#### 查詢優化
- [ ] 避免 SELECT *，只選擇需要的欄位
- [ ] JOIN 條件包含分區欄位對齊
- [ ] 使用 CTE 避免重複計算
- [ ] 大表 JOIN 小表時，小表在右側（BigQuery 會自動優化，但明確更好）

#### 成本控制
- [ ] 設置查詢優先級為 `batch`（生產環境）
- [ ] 使用 `--dry-run` 預估查詢成本
- [ ] 設置成本告警（每日/每月預算）
```

### 14.4.2 流程層面的最佳實踐

**1. Git Workflow**

```markdown
## 推薦的 Git 分支策略

### 分支結構
```
main (生產環境)
  ↑
develop (QA 環境)
  ↑
feature/xxx (開發分支)
```

### 開發流程

1. **創建 feature 分支**
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/add-customer-segment
   ```

2. **本地開發與測試**
   ```bash
   # 運行修改的模型
   dbt run --select +my_model

   # 運行測試
   dbt test --select my_model+

   # 自我 review
   git diff
   ```

3. **提交前檢查**
   ```bash
   # 編譯檢查
   dbt compile --select state:modified

   # SQL 風格檢查
   sqlfluff lint models/

   # 文檔檢查
   python scripts/check_doc_coverage.py
   ```

4. **提交 Pull Request**
   - 使用 PR 模板
   - 填寫變更摘要和影響分析
   - 請求 Code Review

5. **合併後部署**
   - 合併到 develop → 自動部署到 QA
   - 合併到 main → 自動部署到生產（需手動 approve）

### Commit Message 規範

格式: `<type>(<scope>): <subject>`

**Type**:
- `feat`: 新功能
- `fix`: Bug 修復
- `refactor`: 重構
- `docs`: 文檔更新
- `test`: 測試相關
- `perf`: 性能優化

**範例**:
```
feat(staging): add customer_segment to stg_orders

- Add calculation logic using macro
- Add tests for new column
- Update documentation

Closes #123
```
```

**2. CI/CD Pipeline**

```yaml
# 推薦的 CI/CD 配置

# PR 階段
on: pull_request
  jobs:
    - lint: SQL 風格檢查
    - compile: dbt 編譯檢查
    - test: 運行測試（只測試變更的模型）
    - impact-analysis: 生成影響分析報告
    - doc-coverage: 檢查文檔覆蓋率

# Merge to develop 階段
on: push to develop
  jobs:
    - deploy-qa: 部署到 QA 環境
    - data-validation: QA 數據驗證
    - notify: Slack 通知團隊

# Merge to main 階段
on: push to main
  jobs:
    - manual-approval: 需要手動批准
    - deploy-prod: 部署到生產環境（藍綠部署）
    - monitor: 部署後監控（30 分鐘）
    - update-docs: 更新 dbt docs 網站
    - notify: Slack 通知 + 記錄到部署日誌
```

**3. 監控與告警**

```markdown
## 監控指標分層

### L1: 基礎設施層（每 5 分鐘）
- BigQuery slot 使用率
- 查詢隊列長度
- API 錯誤率

### L2: dbt 執行層（每次運行）
- dbt run 成功率
- dbt test 通過率
- 執行時間

### L3: 數據品質層（每小時）
- 數據新鮮度（最後更新時間）
- NULL 值比例
- 記錄數異常（與歷史對比）

### L4: 業務指標層（每日）
- 關鍵業務指標異常檢測（營收、用戶數等）
- 同比/環比變化
- 異常值告警

## 告警優先級

| 優先級 | 響應時間 | 通知渠道 | 示例 |
|--------|----------|----------|------|
| P0 (Critical) | 15 分鐘 | PagerDuty + Slack + Email | 生產環境 dbt run 失敗 |
| P1 (High) | 1 小時 | Slack + Email | 數據新鮮度超過 4 小時 |
| P2 (Medium) | 4 小時 | Slack | 查詢成本增加 50% |
| P3 (Low) | 24 小時 | Email | 文檔覆蓋率下降 |
```

### 14.4.3 團隊協作的最佳實踐

**1. 角色與職責**

```markdown
## dbt 團隊角色定義

### dbt Champion (1-2人)
**職責**:
- 制定 dbt 技術規範和最佳實踐
- Code Review 質量把關
- 技術難題攻關
- 新技術調研和引入

**要求**:
- 深入理解 dbt 和 BigQuery
- 有架構設計能力
- 至少 1 年 dbt 實戰經驗

### dbt Developer (團隊大部分成員)
**職責**:
- 開發和維護 dbt 模型
- 編寫測試和文檔
- 參與 Code Review
- 解決日常數據問題

**要求**:
- 熟練使用 SQL
- 理解 dbt 基礎概念
- 能夠獨立完成功能開發

### Data Analyst (數據分析師)
**職責**:
- 提出數據需求
- 驗證數據正確性
- 使用 dbt 生成的數據進行分析
- 反饋數據品質問題

**要求**:
- 理解業務邏輯
- 基礎 SQL 能力
- 能夠閱讀 dbt 模型（不一定能寫）
```

**2. 溝通機制**

```markdown
## 團隊溝通節奏

### 每日 (Daily)
- **早會 Stand-up** (15 分鐘)
  - 昨天完成了什麼
  - 今天計劃做什麼
  - 有什麼阻礙

- **Slack #dbt 頻道**
  - 技術問題討論
  - 部署通知
  - 告警信息

### 每週 (Weekly)
- **技術分享會** (週五下午 1 小時)
  - 1 人分享（20 分鐘）
  - Q&A 和討論（40 分鐘）

- **Code Review 積壓檢查**
  - 清理超過 2 天未 review 的 PR
  - 指派 reviewer

### 每月 (Monthly)
- **回顧會議** (Retrospective)
  - 回顧本月問題和改進
  - 更新最佳實踐文檔
  - 規劃下月重點

- **成本和性能回顧**
  - 分析 BigQuery 成本趨勢
  - 識別性能瓶頸
  - 制定優化計劃

### 每季 (Quarterly)
- **技術架構 Review**
  - 評估當前架構是否滿足需求
  - 規劃大型重構或升級
  - OKR 設定和回顧
```

**3. 知識管理**

```markdown
## 知識資產體系

### 1. 文檔庫 (Documentation Hub)
```
docs/
├── architecture/          # 架構設計
│   ├── data-flow.md      # 數據流向圖
│   ├── naming-convention.md  # 命名規範
│   └── layered-architecture.md
│
├── guides/               # 操作指南
│   ├── getting-started.md     # 新人入門
│   ├── local-development.md   # 本地開發
│   ├── deployment.md          # 部署流程
│   └── troubleshooting.md     # 疑難排解
│
├── best-practices/       # 最佳實踐
│   ├── model-design.md
│   ├── performance.md
│   └── testing.md
│
├── tech-sharing/         # 技術分享
│   ├── 2024-01-12-incremental-models.md
│   └── 2024-01-19-bigquery-optimization.md
│
└── faq.md                # 常見問題
```

### 2. Code Examples (代碼示例庫)
```
examples/
├── incremental_model.sql      # 增量模型模板
├── complex_join.sql           # 複雜 JOIN 範例
├── custom_test.sql            # 自定義測試範例
└── macro_examples/            # Macro 使用範例
```

### 3. Video Tutorials (視頻教程)
- 新人 Onboarding 系列（3 集）
- 高級技巧系列（按需錄製）
- 疑難問題解決過程（Screen Recording）

### 4. Internal Wiki (內部 Wiki)
- Confluence 或 Notion
- 每個重大項目的 Post-mortem
- 重要決策的 ADR (Architecture Decision Record)
```

### 14.4.4 常見陷阱與避坑指南

M3 團隊踩過的坑，讓你不必再踩一次：

**陷阱 1: 過早優化**

```markdown
❌ 錯誤做法:
- 一開始就把所有模型配置為 incremental
- 花大量時間優化一個只運行一次的查詢

✅ 正確做法:
1. 先讓它跑起來（table 就夠用）
2. 測量瓶頸（哪些模型慢？成本高？）
3. 針對性優化（只優化 Top 20% 的問題）

**經驗法則**:
- 小於 10GB: 用 table
- 大於 10GB: 考慮 incremental
- 查詢成本 < $10: 不優化
- 執行時間 < 10 分鐘: 不優化
```

**陷阱 2: 忽略測試**

```markdown
❌ 錯誤做法:
"測試太麻煩，我手動驗證一下就好"

💥 **後果**:
- 某次修改導致主鍵重複，下游報表數字翻倍
- 損失: 2 小時修復 + 向業務方道歉

✅ 正確做法:
- 所有主鍵都有 unique + not_null 測試
- 所有外鍵都有 relationships 測試
- 關鍵業務邏輯有 data test

**投資回報**:
- 寫測試: 10 分鐘
- 不寫測試導致的問題修復: 2 小時
- ROI: 1200%
```

**陷阱 3: 文檔更新滯後**

```markdown
❌ 錯誤做法:
"先把功能做出來，文檔等有空再補"

💥 **後果**:
- 3 個月後沒人知道這個欄位什麼意思
- 新人花 1 小時問「這個邏輯是什麼」
- 最後只能翻 Git history

✅ 正確做法:
- 文檔和代碼同步更新（作為 Code Review 要求）
- PR 模板強制檢查文檔
- CI/CD 檢查文檔覆蓋率

**原則**: "今天不寫文檔,明天就是技術債"
```

**陷阱 4: 大雜燴 PR**

```markdown
❌ 錯誤做法:
一個 PR 包含:
- 5 個模型的修改
- 2 個 bug 修復
- 1 個重構
- 文檔更新
→ 1500 行代碼變更

💥 **後果**:
- Reviewer 看到就想跑
- Review 質量低下
- 出問題難以回滾

✅ 正確做法:
- 一個 PR 只做一件事
- 理想大小: < 400 行代碼變更
- 大功能拆分成多個小 PR

**經驗法則**:
- 如果 PR description 用了"並且"、"還有"，就該拆分
```

**陷阱 5: 忽視成本**

```markdown
❌ 錯誤做法:
"反正公司付錢，查詢慢點無所謂"

💥 **後果（真實案例）**:
- 一個未優化的查詢每天成本 $500
- 一個月後: $15,000
- CFO 找上門...

✅ 正確做法:
- 設置成本監控和預算告警
- 每月 Review BigQuery 成本
- 優化 Top 10 最貴的查詢

**節省成本的快捷鍵**:
1. 使用分區過濾（成本降 95%）
2. 避免 SELECT *（成本降 50-80%）
3. 使用 cluster_by（成本降 30-50%）
```

## 14.5 結語：從遷移到演進

### 14.5.1 M3 團隊的一年回顧

一年前，M3 團隊面對著 50+ 個複雜的 SQL 腳本，每次修改都如履薄冰，數據問題頻發，新人上手困難。今天，他們已經：

**量化成果**

```markdown
## M3 團隊一年成績單

### 技術指標
- ✅ 遷移模型數: 50 → 120+（增長 140%）
- ✅ 測試覆蓋率: 0% → 85%
- ✅ 部署頻率: 每月 1 次 → 每天 3-5 次
- ✅ 部署時間: 4 小時 → 15 分鐘（降低 94%）
- ✅ 數據故障率: 每月 8 次 → 每月 0.5 次（降低 94%)

### 成本與效能
- ✅ BigQuery 成本: 優化 35%（透過分區和 cluster）
- ✅ 平均查詢時間: 降低 60%
- ✅ 數據新鮮度: 從 T+1 到 T+1小時

### 團隊效能
- ✅ 新人 Onboarding: 2 週 → 5 天
- ✅ Code Review 週期: 3 天 → 1 天
- ✅ 團隊規模: 3 人 → 8 人（生產力未降低）
- ✅ 工程師滿意度: 6.5/10 → 8.9/10
```

**質性變化**

但更重要的是質性的變化：

```markdown
## 團隊文化轉變

### 之前 (Before)
- 😰 "別碰這個 SQL，改了會出事"
- 🤷 "我也不知道這邏輯為什麼這樣寫"
- 😫 "又要熬夜修數據了..."
- 🚫 "新需求？至少要等 2 週"

### 之後 (After)
- 😊 "這個邏輯很清晰，我可以安全修改"
- 📚 "文檔裡有說明，我去看看"
- 🛡️ "測試會幫我把關，不用擔心"
- ⚡ "小需求明天就能上線"
```

**關鍵轉折點**

M3 團隊的 Tech Lead Jerry 回憶：

> "真正的轉折點不是技術，而是心態。
>
> 從'這是我的代碼'到'這是團隊的資產'，
> 從'寫文檔太麻煩'到'沒文檔的代碼不完整'，
> 從'測試浪費時間'到'測試節省時間'。
>
> dbt 只是工具，真正改變我們的是建立在工具之上的協作文化。"

### 14.5.2 dbt 遷移的三個階段

回顧 M3 團隊的旅程，我們可以總結出 dbt 遷移的三個階段：

**階段 1: 工具化（Months 1-3）**

```markdown
## 目標: 讓 dbt 跑起來

### 關鍵任務
- ✅ 環境搭建（dev/qa/prod）
- ✅ 遷移第一批模型（20-30%）
- ✅ 建立基礎規範

### 成功標誌
- dbt run 可以成功運行
- CI/CD pipeline 建立
- 團隊成員都會基本操作

### 常見挑戰
- SQL 轉換為 dbt 模型的困難
- 增量邏輯的理解
- 團隊抵觸情緒

### 應對策略
- 從簡單模型開始
- Pair Programming 帶新人
- 快速展示成果（build trust）
```

**階段 2: 規範化（Months 4-6）**

```markdown
## 目標: 建立標準和流程

### 關鍵任務
- ✅ 完成大部分模型遷移（80%+）
- ✅ 建立 Code Review 文化
- ✅ 文檔覆蓋率 > 70%
- ✅ 測試覆蓋率 > 60%

### 成功標誌
- 有明確的開發規範
- Code Review 成為習慣
- 新人可以獨立開發

### 常見挑戰
- 技術債累積（早期快速開發的後果）
- 規範執行困難
- 性能問題開始顯現

### 應對策略
- 定期重構（每月 20% 時間）
- CI/CD 自動檢查規範
- 針對性性能優化
```

**階段 3: 演進化（Months 7-12+）**

```markdown
## 目標: 持續優化和創新

### 關鍵任務
- ✅ 全部模型遷移完成
- ✅ 建立監控和告警體系
- ✅ 探索高級特性（dbt Mesh, Python models）
- ✅ 知識體系化

### 成功標誌
- 系統穩定運行
- 團隊自驅優化
- 成為組織的數據基礎設施

### 常見挑戰
- 如何持續改進？
- 如何避免停滯？
- 如何應對新需求？

### 應對策略
- 定期技術 Review
- 鼓勵實驗和創新
- 與社群保持聯繫
```

### 14.5.3 超越遷移：dbt 的長期價值

dbt 遷移的終點不是"把 SQL 改成 dbt"，而是開啟了數據工程的新可能：

**1. 數據即產品 (Data as Product)**

```markdown
## dbt 讓數據產品化

### Before: 數據是副產品
- 臨時拼湊的 SQL
- 沒有文檔和測試
- 不知道誰在用、怎麼用

### After: 數據是正式產品
- 有清晰的 SLA（數據新鮮度、準確性）
- 有文檔和使用指南
- 有 owner 負責維護
- 有版本控制和 changelog

### 範例: M3 的 daily_revenue 表

```yaml
# Product Spec for daily_revenue

**Owner**: Data Team (jerry@m3.com)

**SLA**:
- Freshness: < 2 hours
- Accuracy: > 99.9%
- Availability: > 99.5%

**Consumers**:
- Finance Team (daily revenue report)
- CEO Dashboard
- Marketing Analytics

**Documentation**: https://dbt-docs.m3.com/#!/model/model.daily_revenue

**Support**: #data-support Slack channel
```

**2. 數據血緣與影響分析**

dbt 的 DAG 讓數據血緣可視化：

```markdown
## 影響分析案例

**場景**: 需要修改 stg_orders 的邏輯

**Before dbt**:
- 😰 不知道會影響哪些下游
- 🎲 改了再說，出問題再修
- 📞 接到業務方電話："報表數字怎麼變了？"

**After dbt**:
```bash
# 查看下游影響
dbt ls --select stg_orders+

# 輸出:
# - int_customer_metrics
# - daily_revenue
# - customer_cohort
# - marketing_dashboard
# ... 共 12 個下游模型

# 自動通知受影響的團隊
python scripts/notify_downstream_owners.py stg_orders
```

**3. 資料治理 (Data Governance)**

dbt 提供了治理的基礎設施：

```markdown
## 資料治理框架

### 數據目錄 (Data Catalog)
- dbt docs 自動生成
- 包含血緣、文檔、測試結果
- 可搜索、可追溯

### 資料品質監控
- dbt test 作為品質門檻
- 自動化數據品質報告
- SLA 監控和告警

### 存取控制
- 通過 BigQuery 權限控制
- dbt 模型 meta 標記敏感數據
- 自動化 GDPR 合規檢查

### 成本歸屬
- 按 dbt 模型追蹤成本
- 按團隊/專案分攤
- 成本優化建議
```

### 14.5.4 給正在遷移的你的建議

如果你正在考慮或進行 dbt 遷移，M3 團隊的建議是：

**1. 開始之前**

```markdown
## 自我評估清單

### 你的團隊準備好了嗎？

- [ ] 至少有 1 位工程師願意成為 dbt Champion
- [ ] 管理層支持（給予時間和資源）
- [ ] 團隊有基本的 Git 使用能力
- [ ] 有測試和 QA 環境

### 你的業務準備好了嗎？

- [ ] 願意接受短期生產力下降（1-2 個月）
- [ ] 有明確的痛點（數據質量、部署效率等）
- [ ] 不是因為"別人都在用"才遷移

### 你的技術準備好了嗎？

- [ ] 數據倉庫支持 dbt（BigQuery, Snowflake, Redshift等）
- [ ] 有CI/CD 基礎設施
- [ ] SQL 邏輯相對清晰（不是一團亂）
```

**2. 開始之後**

```markdown
## 避免常見錯誤

❌ **錯誤 1**: 想一次性遷移所有內容
✅ **正確做法**: 從 20% 開始，證明價值，再逐步擴展

❌ **錯誤 2**: 忽視團隊培訓
✅ **正確做法**: 投資 Onboarding，建立 Buddy 制度

❌ **錯誤 3**: 完美主義
✅ **正確做法**: 先讓它work，再讓它好，最後讓它完美

❌ **錯誤 4**: 孤島式開發
✅ **正確做法**: Code Review, 文檔, 分享會 —— 協作優先

❌ **錯誤 5**: 忘記慶祝
✅ **正確做法**: 每個里程碑都要慶祝（遷移 10 個模型、測試覆蓋率 50% 等）
```

**3. 持續演進**

```markdown
## 遷移完成後做什麼？

### 短期（1-3 個月）
- 🔧 技術債清理
- 📊 性能優化
- 📚 文檔補全
- 🎓 團隊培訓提升

### 中期（3-6 個月）
- 🚀 探索高級特性（dbt Mesh, Semantic Layer）
- 🤖 更深度的自動化（自動化測試生成、異常檢測）
- 📈 數據可觀測性（Data Observability）
- 🏛️ 資料治理強化

### 長期（6-12 個月）
- 🌐 跨團隊推廣（從一個團隊到整個組織）
- 🔄 持續改進文化
- 🎨 創新實驗（新技術、新模式）
- 🌟 成為行業標杆
```

### 14.5.5 最後的話

> "The best time to start was yesterday. The second best time is now."

M3 團隊的故事告訴我們，dbt 遷移不只是技術升級，更是團隊文化和工作方式的轉型。這個過程會有挑戰，會有挫折，但最終的收穫遠超預期。

**記住這些原則**：

1. **以人為本**: 技術服務於人，不是人服務於技術
2. **小步快跑**: 不要追求一次性完美，持續迭代更重要
3. **知識共享**: 個人英雄主義不可持續，團隊協作才是長久之計
4. **擁抱變化**: dbt 在演進，你的實踐也應該隨之演進
5. **享受過程**: 這是一場馬拉松，不是百米衝刺

最後，借用 dbt 創始人 Tristan Handy 的話：

> "Analytics is a mess. Let's fix it together."

數據分析工程的道路還很長，但有了 dbt 這樣的工具，有了社群的集體智慧，有了像你一樣願意改變現狀的實踐者，我們正在讓它變得更好。

**祝你的 dbt 遷移之旅順利！**

---

## 附錄

### A. 術語表

| 術語 | 英文 | 說明 |
|------|------|------|
| 遷移手冊 | Migration Playbook | AI 輔助的 SQL 轉 dbt 指導文檔 |
| 物化策略 | Materialization | dbt 模型的實現方式（table, view, incremental等） |
| 分區 | Partition | BigQuery 數據分區，用於優化查詢性能和成本 |
| 聚類 | Clustering | BigQuery 數據聚類，進一步優化查詢 |
| 藍綠部署 | Blue-Green Deployment | 零停機部署策略 |
| 數據血緣 | Data Lineage | 數據流向和依賴關係 |
| DAG | Directed Acyclic Graph | 有向無環圖，dbt 模型依賴關係圖 |

### B. 延伸閱讀

**官方資源**
- dbt 官方文檔: https://docs.getdbt.com/
- dbt 社群論壇: https://discourse.getdbt.com/
- dbt Slack: https://community.getdbt.com/

**推薦書籍**
- "The dbt Guidebook" - dbt Labs
- "Data Engineering with dbt" - Packt Publishing
- "The Data Warehouse Toolkit" - Ralph Kimball

**技術部落格**
- dbt Blog: https://blog.getdbt.com/
- Locally Optimistic: https://locallyoptimistic.com/
- Data Engineering Weekly: https://www.dataengineeringweekly.com/

### C. M3 團隊開源資源

M3 團隊將部分實踐開源，供社群參考：

```
m3-dbt-migration/
├── scripts/                    # 自動化腳本
│   ├── impact_analysis.py     # 影響分析
│   ├── check_doc_coverage.py  # 文檔覆蓋率
│   └── blue_green_deploy.sh   # 藍綠部署
│
├── macros/                     # 自定義 Macros
│   ├── generate_schema_name.sql
│   └── custom_tests.sql
│
├── .github/workflows/          # CI/CD 模板
│   ├── pr_check.yml
│   └── deploy_prod.yml
│
└── docs/                       # 文檔模板
    ├── pr_template.md
    └── onboarding_checklist.md
```

GitHub: https://github.com/m3-data/dbt-migration-toolkit

---

**《dbt Migration in Action: 從 SQL 到 dbt 的實戰之旅》全書完**

感謝您的閱讀！如有任何問題或建議，歡迎透過 GitHub Issues 與我們交流。

---

**作者**: M3 Data Team
**出版**: Manning Publications
**系列**: In Action Series
**版本**: 1.0
**最後更新**: 2024-01-15