# Chapter 13: QA 與生產環境部署

> "The best time to catch a bug is before it reaches production. The second best time is immediately after." — DevOps Wisdom

當我們完成了 dbt 模型的開發和測試後，下一個關鍵挑戰是如何安全、可靠地將這些變更部署到 QA 和生產環境。M3 團隊在這個階段經歷了從手動部署到自動化流程的演進，累積了寶貴的實戰經驗。

本章將深入探討多環境部署策略，從環境配置設計到藍綠部署實作，從 rollback 機制到生產監控，提供一套完整的部署最佳實踐。

## 13.1 多環境策略設計

### 13.1.1 環境架構規劃

M3 團隊採用了三層環境架構：

```
Development (dev)  → 開發環境，個人沙箱
    ↓
Quality Assurance (qa) → 測試環境，團隊共享
    ↓
Production (prod) → 生產環境，實際業務
```

**環境隔離原則**

每個環境都有獨立的：
- BigQuery dataset（例如：`dbt_dev`、`dbt_qa`、`dbt_prod`）
- 服務帳號和權限配置
- 資料來源（dev/qa 使用取樣數據，prod 使用完整數據）

讓我們看看實際的 BigQuery 專案結構：

```sql
-- 開發環境
project_id: m3-analytics-dev
dataset: dbt_dev_jerry, dbt_dev_alice  -- 每個開發者有自己的 schema
source data: raw_data_sample  -- 使用取樣數據（最近 7 天）

-- QA 環境
project_id: m3-analytics-qa
dataset: dbt_qa  -- 團隊共享
source data: raw_data_sample  -- 使用取樣數據（最近 30 天）

-- 生產環境
project_id: m3-analytics-prod
dataset: dbt_prod  -- 正式環境
source data: raw_data  -- 完整歷史數據
```

這種隔離策略的優勢：
1. **安全性**：開發環境的錯誤不會影響生產數據
2. **成本控制**：dev/qa 使用取樣數據，降低查詢成本
3. **獨立性**：每個開發者可以獨立測試，不互相干擾

### 13.1.2 profiles.yml 配置

dbt 使用 `profiles.yml` 來管理不同環境的連接配置。M3 團隊的配置示例：

```yaml
# ~/.dbt/profiles.yml
m3_migration:
  outputs:
    dev:
      type: bigquery
      method: oauth
      project: m3-analytics-dev
      dataset: "dbt_dev_{{ env_var('DBT_USER', 'default') }}"
      threads: 4
      timeout_seconds: 300
      location: asia-east1
      priority: interactive

    qa:
      type: bigquery
      method: service-account
      project: m3-analytics-qa
      dataset: dbt_qa
      threads: 8
      timeout_seconds: 600
      location: asia-east1
      priority: interactive
      keyfile: "{{ env_var('DBT_SERVICE_ACCOUNT_KEY') }}"

    prod:
      type: bigquery
      method: service-account
      project: m3-analytics-prod
      dataset: dbt_prod
      threads: 16
      timeout_seconds: 900
      location: asia-east1
      priority: batch
      keyfile: "{{ env_var('DBT_PROD_SERVICE_ACCOUNT_KEY') }}"

  target: dev  # 預設目標環境
```

**配置重點說明**

1. **認證方式**
   - dev：使用 OAuth（開發者個人帳號）
   - qa/prod：使用 Service Account（服務帳號）

2. **執行緒數調整**
   - dev: 4 threads（避免過度消耗資源）
   - qa: 8 threads（加快測試速度）
   - prod: 16 threads（充分利用資源，加快部署）

3. **查詢優先級**
   - dev/qa: `interactive`（即時互動）
   - prod: `batch`（批次處理，降低成本）

4. **動態 schema 命名**
   ```yaml
   dataset: "dbt_dev_{{ env_var('DBT_USER', 'default') }}"
   ```
   使用環境變數動態生成開發者專屬的 schema。

**使用方式**

```bash
# 開發環境（預設）
dbt run

# 明確指定 QA 環境
dbt run --target qa

# 生產環境部署
dbt run --target prod --models state:modified+

# 檢查當前使用的 profile
dbt debug --target prod
```

### 13.1.3 環境變數管理

M3 團隊使用環境變數來管理敏感資訊和環境特定配置。

**開發環境設置**

```bash
# ~/.bashrc 或 ~/.zshrc
export DBT_USER="jerry"
export DBT_PROJECT="m3-analytics-dev"

# Service account keys（不要提交到版本控制！）
export DBT_SERVICE_ACCOUNT_KEY="/path/to/qa-service-account.json"
export DBT_PROD_SERVICE_ACCOUNT_KEY="/path/to/prod-service-account.json"
```

**CI/CD 環境變數（GitHub Actions）**

```yaml
# .github/workflows/dbt-deploy.yml
name: dbt Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      DBT_PROJECT: m3-analytics-prod

    steps:
      - uses: actions/checkout@v2

      - name: Set up service account
        run: |
          echo "${{ secrets.PROD_SERVICE_ACCOUNT_KEY }}" > sa-key.json
          export DBT_PROD_SERVICE_ACCOUNT_KEY="$(pwd)/sa-key.json"

      - name: Install dbt
        run: pip install dbt-bigquery

      - name: Deploy to production
        run: |
          dbt deps
          dbt run --target prod --select state:modified+ --defer --state ./prod-manifest/
          dbt test --target prod --select state:modified+
```

**dbt_project.yml 中的環境變數**

```yaml
# dbt_project.yml
name: 'm3_migration'
version: '1.0.0'

vars:
  # 環境特定變數
  source_dataset: "{{ env_var('SOURCE_DATASET', 'raw_data_sample') }}"
  date_range_days: "{{ env_var('DATE_RANGE_DAYS', '7') | int }}"

  # 根據環境調整參數
  partition_expiration_days: >
    {{ 90 if target.name == 'prod' else 30 }}

models:
  m3_migration:
    +materialized: table
    +partition_by:
      field: event_date
      data_type: date
      granularity: day
```

**在模型中使用環境變數**

```sql
-- models/staging/stg_order_events.sql
{{ config(
    materialized='incremental',
    unique_key='order_id',
    partition_by={
        "field": "order_date",
        "data_type": "date"
    }
) }}

with source as (
    select * from {{ source('raw_data', 'order_events') }}
    where order_date >= date_sub(current_date(),
                                  interval {{ var('date_range_days') }} day)
    {% if target.name == 'prod' %}
    -- 生產環境額外過濾條件
    and is_deleted = false
    {% endif %}
),

-- ... 其餘轉換邏輯
```

### 13.1.4 環境特定配置管理

有些配置需要根據環境動態調整。M3 團隊使用以下策略：

**方法 1：使用 dbt 變數 (vars)**

```yaml
# dbt_project.yml
vars:
  # 開發環境使用小批次測試
  dev:
    batch_size: 1000
    enable_full_refresh: true

  # QA 環境使用中等批次
  qa:
    batch_size: 10000
    enable_full_refresh: true

  # 生產環境使用大批次
  prod:
    batch_size: 100000
    enable_full_refresh: false  # 防止意外全量刷新
```

在模型中使用：

```sql
-- models/marts/daily_order_summary.sql
{% set batch_size = var('batch_size', 10000) %}

with orders as (
    select * from {{ ref('stg_orders') }}
    limit {{ batch_size if target.name != 'prod' else none }}
),
-- ...
```

**方法 2：環境特定的 seeds 文件**

```
seeds/
├── dev/
│   └── currency_rates.csv  -- 測試用假數據
├── qa/
│   └── currency_rates.csv  -- QA 環境數據
└── prod/
    └── currency_rates.csv  -- 生產環境實際匯率
```

```yaml
# dbt_project.yml
seeds:
  m3_migration:
    +enabled: true
    +schema: config
    +database: "{{ target.project }}"

  # 根據環境載入不同的 seed
  m3_migration:
    dev:
      +enabled: "{{ target.name == 'dev' }}"
    qa:
      +enabled: "{{ target.name == 'qa' }}"
    prod:
      +enabled: "{{ target.name == 'prod' }}"
```

**方法 3：使用 dbt Packages 的環境管理**

```yaml
# packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.1.1
  - package: calogica/dbt_expectations
    version: 0.9.0
```

```sql
-- macros/get_env_config.sql
{% macro get_refresh_strategy() %}
    {% if target.name == 'dev' %}
        {{ return('table') }}  -- 開發環境快速迭代
    {% elif target.name == 'qa' %}
        {{ return('incremental') }}  -- QA 測試增量邏輯
    {% else %}
        {{ return('incremental') }}  -- 生產環境增量更新
    {% endif %}
{% endmacro %}
```

### 13.1.5 環境切換檢查清單

在切換環境時，M3 團隊使用以下檢查清單確保配置正確：

```bash
#!/bin/bash
# scripts/check_env.sh - 環境配置檢查腳本

ENV=$1  # dev, qa, or prod

echo "🔍 檢查環境配置: $ENV"
echo "================================"

# 1. 檢查 dbt profile
echo "1. 檢查 dbt profile..."
dbt debug --target $ENV | grep "Connection test: OK" || {
    echo "❌ dbt 連接失敗"
    exit 1
}

# 2. 檢查環境變數
echo "2. 檢查環境變數..."
if [ "$ENV" == "prod" ]; then
    if [ -z "$DBT_PROD_SERVICE_ACCOUNT_KEY" ]; then
        echo "❌ 缺少 DBT_PROD_SERVICE_ACCOUNT_KEY"
        exit 1
    fi
fi

# 3. 檢查 BigQuery 權限
echo "3. 檢查 BigQuery 權限..."
bq ls --project_id=$(dbt debug --target $ENV 2>/dev/null | grep "project" | awk '{print $2}') > /dev/null || {
    echo "❌ BigQuery 權限不足"
    exit 1
}

# 4. 檢查 git 分支（生產環境）
if [ "$ENV" == "prod" ]; then
    BRANCH=$(git branch --show-current)
    if [ "$BRANCH" != "main" ]; then
        echo "⚠️  警告: 當前不在 main 分支 (當前: $BRANCH)"
        read -p "是否繼續? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

echo "================================"
echo "✅ 環境配置檢查通過"
```

使用方式：

```bash
# 部署前檢查
./scripts/check_env.sh prod

# 輸出:
# 🔍 檢查環境配置: prod
# ================================
# 1. 檢查 dbt profile...
# Connection test: OK
# 2. 檢查環境變數...
# 3. 檢查 BigQuery 權限...
# 4. 檢查 git 分支...
# ================================
# ✅ 環境配置檢查通過
```

## 13.2 部署前檢查清單

在正式部署到 QA 或生產環境之前，M3 團隊建立了一套嚴格的檢查流程，確保代碼品質和部署安全。

### 13.2.1 代碼審查要點

**1. SQL 邏輯審查**

審查者需要檢查以下方面：

```sql
-- ❌ 不好的實踐：沒有分區過濾
select * from {{ source('raw_data', 'events') }}
where user_id = 12345

-- ✅ 好的實踐：使用分區過濾
select * from {{ source('raw_data', 'events') }}
where event_date = current_date()
  and user_id = 12345
```

**檢查要點清單**

```markdown
### SQL 品質檢查

- [ ] 是否使用了分區過濾？（避免全表掃描）
- [ ] JOIN 條件是否正確？（避免笛卡爾積）
- [ ] 是否有重複計算？（可以用 CTE 或臨時表優化）
- [ ] 聚合函數是否正確？（COUNT, SUM, AVG 等）
- [ ] 日期處理是否正確？（時區、格式轉換）
- [ ] NULL 值處理是否完善？（COALESCE, IFNULL）

### dbt 配置檢查

- [ ] materialized 策略是否合理？（table vs incremental vs view）
- [ ] incremental 模型是否有正確的 unique_key？
- [ ] partition_by 配置是否正確？
- [ ] cluster_by 是否有助於查詢效能？
- [ ] schema 和 alias 是否符合命名規範？

### 測試覆蓋率

- [ ] 是否有 not_null 測試？
- [ ] 是否有 unique 測試？
- [ ] 是否有 relationships 測試？
- [ ] 是否有自定義 data test？
- [ ] 測試覆蓋關鍵欄位嗎？（至少 70% 覆蓋率）

### 文檔完整性

- [ ] 模型是否有 description？
- [ ] 關鍵欄位是否有說明？
- [ ] 是否有使用範例？
- [ ] 是否更新了 CHANGELOG？
```

**2. Pull Request 檢查腳本**

M3 團隊使用自動化腳本輔助代碼審查：

```bash
#!/bin/bash
# scripts/pr_check.sh - Pull Request 自動檢查

echo "🔍 開始 Pull Request 檢查..."

# 1. 檢查修改的模型
MODIFIED_MODELS=$(git diff --name-only origin/main | grep "models/.*\.sql$")

if [ -z "$MODIFIED_MODELS" ]; then
    echo "✅ 沒有模型變更"
    exit 0
fi

echo "📝 檢測到以下模型變更:"
echo "$MODIFIED_MODELS"
echo ""

# 2. 編譯檢查
echo "🔨 Step 1: 編譯檢查..."
dbt compile --select state:modified --state ./prod-manifest/ || {
    echo "❌ 編譯失敗"
    exit 1
}
echo "✅ 編譯通過"

# 3. 測試檢查
echo "🧪 Step 2: 測試檢查..."
dbt test --select state:modified+ --state ./prod-manifest/ || {
    echo "❌ 測試失敗"
    exit 1
}
echo "✅ 測試通過"

# 4. 文檔檢查
echo "📖 Step 3: 文檔檢查..."
for model in $MODIFIED_MODELS; do
    if ! grep -q "description:" "$model"; then
        echo "⚠️  警告: $model 缺少 description"
    fi
done

# 5. SQL 風格檢查（使用 sqlfluff）
if command -v sqlfluff &> /dev/null; then
    echo "🎨 Step 4: SQL 風格檢查..."
    sqlfluff lint $MODIFIED_MODELS --dialect bigquery || {
        echo "⚠️  SQL 風格檢查有警告（不阻斷部署）"
    }
fi

# 6. 生成影響分析報告
echo "📊 Step 5: 影響分析..."
dbt ls --select state:modified+ --state ./prod-manifest/ --output json > /tmp/impact_analysis.json

echo ""
echo "================================"
echo "✅ Pull Request 檢查完成"
echo "================================"
echo "變更影響範圍:"
dbt ls --select state:modified+ --state ./prod-manifest/ | wc -l | xargs echo "受影響模型數:"
```

**3. 人工審查重點**

除了自動化檢查，還需要人工審查以下項目：

```python
# scripts/review_checklist.py
# 生成人工審查清單

import json
import sys

def generate_review_checklist(impact_analysis_file):
    """根據影響分析生成審查清單"""

    with open(impact_analysis_file) as f:
        models = [json.loads(line) for line in f]

    print("# 人工審查清單")
    print("")

    # 1. 高風險變更
    print("## 🔴 高風險變更（需要特別注意）")
    high_risk = [m for m in models if 'mart' in m['path'] or 'prod_' in m['name']]
    if high_risk:
        for model in high_risk:
            print(f"- [ ] {model['name']} (路徑: {model['path']})")
            print(f"  - 原因: 影響下游業務報表")
            print(f"  - 建議: 測試數據一致性，通知下游用戶")
    else:
        print("- 無高風險變更")
    print("")

    # 2. 增量模型變更
    print("## 🟡 增量模型變更（需要測試增量邏輯）")
    incremental = [m for m in models if m.get('config', {}).get('materialized') == 'incremental']
    if incremental:
        for model in incremental:
            print(f"- [ ] {model['name']}")
            print(f"  - 檢查 unique_key 是否正確")
            print(f"  - 測試增量運行是否正常")
            print(f"  - 確認 merge 邏輯無誤")
    else:
        print("- 無增量模型變更")
    print("")

    # 3. Schema 變更
    print("## 🟢 Schema 變更（需要通知下游）")
    print("- [ ] 檢查是否有欄位新增/刪除")
    print("- [ ] 檢查資料類型是否變更")
    print("- [ ] 更新下游依賴文檔")
    print("")

    # 4. 效能影響
    print("## ⚡ 效能影響評估")
    print("- [ ] 查詢成本是否在可接受範圍？（< $10 per run）")
    print("- [ ] 執行時間是否合理？（< 10 minutes）")
    print("- [ ] 是否需要增加 cluster_by？")
    print("")

if __name__ == "__main__":
    generate_review_checklist("/tmp/impact_analysis.json")
```

輸出示例：

```markdown
# 人工審查清單

## 🔴 高風險變更（需要特別注意）
- [ ] daily_revenue_summary (路徑: models/marts/finance/)
  - 原因: 影響下游業務報表
  - 建議: 測試數據一致性，通知下游用戶

## 🟡 增量模型變更（需要測試增量邏輯）
- [ ] stg_order_events
  - 檢查 unique_key 是否正確
  - 測試增量運行是否正常
  - 確認 merge 邏輯無誤

## 🟢 Schema 變更（需要通知下游）
- [ ] 檢查是否有欄位新增/刪除
- [ ] 檢查資料類型是否變更
- [ ] 更新下游依賴文檔

## ⚡ 效能影響評估
- [ ] 查詢成本是否在可接受範圍？（< $10 per run）
- [ ] 執行時間是否合理？（< 10 minutes）
- [ ] 是否需要增加 cluster_by？
```

### 13.2.2 測試驗證流程

**1. 本地測試（開發環境）**

開發者在提交 PR 之前需要完成：

```bash
# Step 1: 完整編譯
dbt clean
dbt deps
dbt compile

# Step 2: 運行修改的模型（包含上游依賴）
dbt run --select +my_new_model

# Step 3: 運行所有相關測試
dbt test --select my_new_model+

# Step 4: 生成並檢查文檔
dbt docs generate
dbt docs serve  # 在瀏覽器中檢查文檔

# Step 5: 檢查查詢成本（可選）
dbt run-operation query_cost --args '{model: my_new_model}'
```

**2. QA 環境測試**

PR 合併到 develop 分支後，自動觸發 QA 環境部署：

```yaml
# .github/workflows/deploy-qa.yml
name: Deploy to QA

on:
  push:
    branches: [develop]

jobs:
  deploy-qa:
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

      - name: Deploy to QA
        env:
          DBT_SERVICE_ACCOUNT_KEY: ${{ secrets.QA_SERVICE_ACCOUNT_KEY }}
        run: |
          # 設置服務帳號
          echo "$DBT_SERVICE_ACCOUNT_KEY" > sa-key.json
          export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/sa-key.json"

          # 運行變更的模型
          dbt run --target qa --select state:modified+ --defer --state ./manifests/prod/

          # 運行測試
          dbt test --target qa --select state:modified+

      - name: Data Quality Check
        run: |
          # 執行自定義數據品質檢查
          python scripts/qa_validation.py

      - name: Notify Team
        if: failure()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'QA 部署失敗，請檢查'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

**3. 數據一致性驗證**

```python
# scripts/qa_validation.py
# QA 環境數據驗證

from google.cloud import bigquery
import sys

def validate_data_consistency():
    """驗證 QA 環境數據一致性"""

    client = bigquery.Client(project='m3-analytics-qa')

    checks = [
        {
            'name': '記錄數檢查',
            'query': '''
                select
                    count(*) as qa_count,
                    (select count(*) from `m3-analytics-dev.dbt_dev_jerry.stg_orders`) as dev_count
                from `m3-analytics-qa.dbt_qa.stg_orders`
            ''',
            'validation': lambda row: abs(row.qa_count - row.dev_count) / row.dev_count < 0.01  # 允許 1% 誤差
        },
        {
            'name': '數據新鮮度檢查',
            'query': '''
                select max(order_date) as latest_date
                from `m3-analytics-qa.dbt_qa.stg_orders`
            ''',
            'validation': lambda row: (datetime.now().date() - row.latest_date).days <= 1
        },
        {
            'name': 'NULL 值比例檢查',
            'query': '''
                select
                    countif(customer_id is null) / count(*) as null_ratio
                from `m3-analytics-qa.dbt_qa.stg_orders`
            ''',
            'validation': lambda row: row.null_ratio < 0.05  # NULL 值不超過 5%
        }
    ]

    print("🔍 開始數據一致性驗證...")
    all_passed = True

    for check in checks:
        print(f"\n檢查: {check['name']}")
        result = client.query(check['query']).result()
        row = next(result)

        if check['validation'](row):
            print(f"✅ {check['name']} 通過")
        else:
            print(f"❌ {check['name']} 失敗")
            print(f"   結果: {dict(row)}")
            all_passed = False

    if not all_passed:
        sys.exit(1)

    print("\n✅ 所有數據驗證通過")

if __name__ == "__main__":
    validate_data_consistency()
```

### 13.2.3 文檔更新要求

每次部署前都需要確保文檔是最新的：

**1. 模型文檔（schema.yml）**

```yaml
# models/staging/schema.yml
version: 2

models:
  - name: stg_orders
    description: |
      訂單事件 staging 層模型

      **數據來源**: raw_data.order_events
      **更新頻率**: 每小時
      **數據保留**: 90 天

      **變更歷史**:
      - 2024-01-15: 新增 customer_segment 欄位
      - 2024-01-10: 修改增量邏輯，改用 order_updated_at

    columns:
      - name: order_id
        description: 訂單唯一識別碼
        tests:
          - unique
          - not_null

      - name: customer_id
        description: |
          客戶 ID，關聯到 dim_customers
          **注意**: 2024-01-01 之前的訂單可能為 NULL
        tests:
          - not_null
          - relationships:
              to: ref('dim_customers')
              field: customer_id

      - name: customer_segment
        description: |
          客戶分群標籤（2024-01-15 新增）
          - 'VIP': 年消費 > $10,000
          - 'Regular': 年消費 $1,000 - $10,000
          - 'New': 首次購買
```

**2. CHANGELOG 維護**

```markdown
# CHANGELOG.md

## [Unreleased]

### Added
- 新增 `customer_segment` 欄位到 `stg_orders` 模型
- 新增 `daily_customer_retention` mart 模型

### Changed
- 優化 `stg_orders` 增量邏輯，改用 `order_updated_at` 取代 `order_created_at`
- 調整 `dim_customers` 的 cluster_by 配置，提升查詢效能

### Fixed
- 修復 `stg_payments` 中重複記錄的問題（#234）
- 修正 `daily_revenue` 時區轉換錯誤（#245）

## [1.2.0] - 2024-01-10

### Added
- 實作藍綠部署機制
- 新增自動化數據驗證流程

...
```

**3. 部署說明文檔**

```markdown
# docs/deployment/deploy-to-prod.md

# 生產環境部署指南

## 前置檢查

- [ ] 所有測試通過
- [ ] Code review 完成（至少 2 位 approver）
- [ ] QA 環境驗證通過
- [ ] CHANGELOG 已更新
- [ ] 影響分析文檔已完成
- [ ] 下游用戶已通知（如有 schema 變更）

## 部署步驟

1. **確認分支**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **執行部署前檢查**
   ```bash
   ./scripts/check_env.sh prod
   ./scripts/pr_check.sh
   ```

3. **部署到生產環境**
   ```bash
   dbt run --target prod --select state:modified+ --defer --state ./manifests/prod/
   ```

4. **運行測試**
   ```bash
   dbt test --target prod --select state:modified+
   ```

5. **更新 manifest**
   ```bash
   dbt docs generate --target prod
   cp target/manifest.json manifests/prod/
   git add manifests/prod/manifest.json
   git commit -m "Update prod manifest after deployment"
   git push
   ```

## Rollback 流程

如果部署後發現問題，立即執行：

```bash
./scripts/rollback.sh --version previous
```

詳見 [Rollback 機制](#rollback-mechanism)。

## 監控

部署後持續監控 30 分鐘：
- BigQuery 查詢成本
- dbt 運行時間
- 數據新鮮度
- 下游報表異常告警

監控面板: https://datastudio.google.com/monitoring-dashboard
```

---

**小結**

第 1-2 節建立了完整的多環境管理和部署前檢查體系：

1. **環境架構**: dev/qa/prod 三層隔離，確保安全和成本控制
2. **配置管理**: 使用 profiles.yml 和環境變數靈活管理不同環境
3. **代碼審查**: 自動化 + 人工審查，確保代碼品質
4. **測試驗證**: 本地 → QA → 生產，逐層驗證
5. **文檔維護**: 模型文檔、CHANGELOG、部署指南保持同步

這些準備工作為安全可靠的生產部署奠定了基礎。接下來，我們將深入探討藍綠部署和 rollback 機制的實作細節。

## 13.3 藍綠部署實作

藍綠部署（Blue-Green Deployment）是一種零停機部署策略，通過維護兩套完全相同的生產環境來實現無縫切換。M3 團隊在 dbt 遷移中成功應用了這種模式。

### 13.3.1 藍綠部署原理

**基本概念**

```
生產環境分為兩套：
- 藍環境（Blue）: 當前正在服務的版本
- 綠環境（Green）: 新版本部署測試環境

部署流程：
1. 綠環境部署新版本
2. 驗證綠環境數據正確性
3. 切換流量到綠環境
4. 藍環境變成下次部署的候選環境
```

**在 dbt 中的實現**

M3 團隊使用 BigQuery schema 來實現藍綠部署：

```sql
-- 當前生產環境
dbt_prod_blue   (藍環境，正在服務中)
dbt_prod_green  (綠環境，準備部署)

-- 外部視圖指向當前活躍環境
dbt_prod        → 指向 dbt_prod_blue（當前）
```

### 13.3.2 實作細節

**1. 環境配置**

```yaml
# profiles.yml - 藍綠環境配置
m3_migration:
  outputs:
    prod_blue:
      type: bigquery
      project: m3-analytics-prod
      dataset: dbt_prod_blue
      threads: 16
      keyfile: "{{ env_var('DBT_PROD_SERVICE_ACCOUNT_KEY') }}"

    prod_green:
      type: bigquery
      project: m3-analytics-prod
      dataset: dbt_prod_green
      threads: 16
      keyfile: "{{ env_var('DBT_PROD_SERVICE_ACCOUNT_KEY') }}"

    prod:  # 指向當前活躍環境
      type: bigquery
      project: m3-analytics-prod
      dataset: dbt_prod
      threads: 16
      keyfile: "{{ env_var('DBT_PROD_SERVICE_ACCOUNT_KEY') }}"
```

**2. 部署腳本**

```bash
#!/bin/bash
# scripts/blue_green_deploy.sh - 藍綠部署主腳本

set -e  # 遇到錯誤立即退出

# 檢測當前活躍環境
CURRENT_ENV=$(bq query --project_id=m3-analytics-prod --use_legacy_sql=false \
  "SELECT schema_name FROM \`m3-analytics-prod.INFORMATION_SCHEMA.SCHEMATA\`
   WHERE schema_name = 'dbt_prod'" | grep dbt_prod | awk '{print $1}')

# 確定目標部署環境
if [ "$CURRENT_ENV" == "dbt_prod_blue" ]; then
    TARGET_ENV="green"
    TARGET_SCHEMA="dbt_prod_green"
    echo "🔵 當前環境: Blue, 部署到: Green"
else
    TARGET_ENV="blue"
    TARGET_SCHEMA="dbt_prod_blue"
    echo "🟢 當前環境: Green, 部署到: Blue"
fi

echo "================================"
echo "開始藍綠部署流程"
echo "目標環境: $TARGET_ENV ($TARGET_SCHEMA)"
echo "================================"

# Step 1: 部署到目標環境
echo ""
echo "📦 Step 1: 部署新版本到 $TARGET_ENV 環境..."
dbt run --target prod_$TARGET_ENV --full-refresh

# Step 2: 運行測試
echo ""
echo "🧪 Step 2: 運行測試驗證..."
dbt test --target prod_$TARGET_ENV

# Step 3: 數據一致性驗證
echo ""
echo "🔍 Step 3: 數據一致性驗證..."
python scripts/validate_blue_green.py --target $TARGET_ENV || {
    echo "❌ 數據驗證失敗，取消部署"
    exit 1
}

# Step 4: 切換流量
echo ""
echo "🔄 Step 4: 準備切換流量..."
read -p "數據驗證通過，是否切換到 $TARGET_ENV 環境？ (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ 部署已取消"
    exit 0
fi

# 執行流量切換
./scripts/switch_environment.sh $TARGET_ENV

echo ""
echo "================================"
echo "✅ 藍綠部署完成！"
echo "當前活躍環境: $TARGET_ENV"
echo "================================"
```

**3. 數據驗證腳本**

```python
# scripts/validate_blue_green.py
# 藍綠環境數據一致性驗證

import argparse
from google.cloud import bigquery
import sys

def compare_environments(target_env):
    """比較藍綠環境的數據一致性"""

    client = bigquery.Client(project='m3-analytics-prod')

    # 確定比較對象
    source_env = 'blue' if target_env == 'green' else 'green'

    # 關鍵模型列表
    critical_models = [
        'daily_revenue_summary',
        'customer_retention_cohort',
        'product_performance_metrics'
    ]

    print(f"🔍 比較環境: {source_env} vs {target_env}")
    print("=" * 50)

    all_passed = True

    for model in critical_models:
        print(f"\n檢查模型: {model}")

        # 1. 記錄數比較
        query = f"""
        SELECT
            (SELECT COUNT(*) FROM `m3-analytics-prod.dbt_prod_{source_env}.{model}`) as source_count,
            (SELECT COUNT(*) FROM `m3-analytics-prod.dbt_prod_{target_env}.{model}`) as target_count
        """

        result = client.query(query).result()
        row = next(result)

        diff_pct = abs(row.source_count - row.target_count) / row.source_count * 100 if row.source_count > 0 else 0

        if diff_pct > 1:  # 允許 1% 誤差
            print(f"  ❌ 記錄數差異過大: {source_env}={row.source_count}, {target_env}={row.target_count} (差異: {diff_pct:.2f}%)")
            all_passed = False
        else:
            print(f"  ✅ 記錄數一致: {row.target_count} 筆 (差異: {diff_pct:.2f}%)")

        # 2. 關鍵指標比較（以 daily_revenue_summary 為例）
        if model == 'daily_revenue_summary':
            query = f"""
            SELECT
                ABS(
                    (SELECT SUM(total_revenue) FROM `m3-analytics-prod.dbt_prod_{source_env}.{model}` WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)) -
                    (SELECT SUM(total_revenue) FROM `m3-analytics-prod.dbt_prod_{target_env}.{model}` WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
                ) / (SELECT SUM(total_revenue) FROM `m3-analytics-prod.dbt_prod_{source_env}.{model}` WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)) * 100 as revenue_diff_pct
            """

            result = client.query(query).result()
            row = next(result)

            if row.revenue_diff_pct > 0.1:  # 營收差異不超過 0.1%
                print(f"  ❌ 營收數據差異: {row.revenue_diff_pct:.4f}%")
                all_passed = False
            else:
                print(f"  ✅ 營收數據一致 (差異: {row.revenue_diff_pct:.4f}%)")

    print("\n" + "=" * 50)

    if all_passed:
        print("✅ 所有驗證通過，可以安全切換")
        return 0
    else:
        print("❌ 驗證失敗，請檢查數據差異")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True, choices=['blue', 'green'])
    args = parser.parse_args()

    sys.exit(compare_environments(args.target))
```

**4. 流量切換腳本**

```bash
#!/bin/bash
# scripts/switch_environment.sh - 切換活躍環境

TARGET_ENV=$1  # blue or green

echo "🔄 開始切換流量到 $TARGET_ENV 環境..."

# 1. 更新視圖指向新環境
bq mk --force --view "
SELECT * FROM \`m3-analytics-prod.dbt_prod_${TARGET_ENV}.*\`
" m3-analytics-prod:dbt_prod

# 2. 使用 authorized views 確保下游訪問權限
for table in daily_revenue_summary customer_retention_cohort product_performance_metrics; do
    bq mk --force --use_legacy_sql=false --view \
        "SELECT * FROM \`m3-analytics-prod.dbt_prod_${TARGET_ENV}.${table}\`" \
        m3-analytics-prod:dbt_prod.${table}

    echo "  ✅ 已切換: $table → dbt_prod_${TARGET_ENV}.${table}"
done

# 3. 記錄切換事件
bq query --use_legacy_sql=false --project_id=m3-analytics-prod \
  "INSERT INTO \`m3-analytics-prod.dbt_metadata.deployment_log\`
   VALUES (CURRENT_TIMESTAMP(), '$TARGET_ENV', 'switch', 'success')"

echo "✅ 流量切換完成！"
```

### 13.3.3 切換流程與驗證

**完整部署時間軸**

```
T0  : 開始部署到綠環境
T+10: 部署完成，開始測試
T+15: 測試通過，開始數據驗證
T+20: 驗證通過，準備切換
T+21: 執行流量切換（< 1 分鐘）
T+22: 開始監控新環境
T+52: 監控 30 分鐘無異常，部署成功
```

**部署檢查清單**

```markdown
## 藍綠部署檢查清單

### 部署前
- [ ] 確認目標環境（藍或綠）
- [ ] 備份當前 manifest.json
- [ ] 通知下游用戶計劃切換時間
- [ ] 準備回滾腳本

### 部署中
- [ ] dbt run 執行成功
- [ ] dbt test 全部通過
- [ ] 數據一致性驗證通過（< 1% 差異）
- [ ] 關鍵指標驗證通過（營收、用戶數等）

### 切換後
- [ ] 驗證視圖指向正確環境
- [ ] 檢查下游報表是否正常
- [ ] 監控查詢性能（延遲、成本）
- [ ] 持續監控 30 分鐘
- [ ] 記錄部署日誌
```

**監控指標**

```python
# scripts/monitor_deployment.py
# 部署後監控

from google.cloud import bigquery, monitoring_v3
import time

def monitor_post_deployment(duration_minutes=30):
    """部署後持續監控"""

    client = bigquery.Client(project='m3-analytics-prod')
    monitoring_client = monitoring_v3.MetricServiceClient()

    print(f"🔍 開始監控 {duration_minutes} 分鐘...")

    start_time = time.time()
    check_interval = 60  # 每分鐘檢查一次

    while time.time() - start_time < duration_minutes * 60:
        print(f"\n⏰ {int((time.time() - start_time) / 60)} 分鐘...")

        # 1. 查詢成本監控
        query = """
        SELECT
            SUM(total_bytes_processed) / POW(10, 12) as tb_processed,
            COUNT(*) as query_count
        FROM `m3-analytics-prod.region-asia-east1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
        WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)
          AND statement_type = 'SELECT'
        """
        result = client.query(query).result()
        row = next(result)

        cost = row.tb_processed * 5  # BigQuery $5 per TB
        print(f"  💰 查詢成本: ${cost:.2f} ({row.query_count} queries, {row.tb_processed:.2f} TB)")

        # 2. 錯誤率監控
        query = """
        SELECT
            COUNTIF(error_result IS NOT NULL) / COUNT(*) * 100 as error_rate
        FROM `m3-analytics-prod.region-asia-east1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
        WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)
        """
        result = client.query(query).result()
        row = next(result)

        if row.error_rate > 5:  # 錯誤率超過 5%
            print(f"  ❌ 錯誤率過高: {row.error_rate:.2f}%")
            return False
        else:
            print(f"  ✅ 錯誤率正常: {row.error_rate:.2f}%")

        time.sleep(check_interval)

    print("\n✅ 監控完成，無異常")
    return True

if __name__ == "__main__":
    if not monitor_post_deployment(30):
        print("⚠️  監控發現異常，建議回滾")
        sys.exit(1)
```

## 13.4 Rollback 機制

即使有完善的測試和驗證，生產環境仍可能出現意外情況。完善的 rollback 機制是部署安全的最後一道防線。

### 13.4.1 回滾策略

**回滾觸發條件**

```markdown
## 何時需要回滾？

🔴 **立即回滾**（Critical）
- 數據準確性問題（營收、用戶數等關鍵指標異常）
- 下游報表完全無法訪問
- 查詢錯誤率 > 10%
- 重大安全漏洞

🟡 **評估後回滾**（High）
- 查詢性能下降 > 50%
- 部分報表數據異常
- 查詢成本增加 > 3倍

🟢 **監控觀察**（Medium）
- 輕微性能下降 (< 20%)
- 個別非關鍵報表異常
- 查詢成本增加 < 2倍
```

**M3 團隊的回滾決策流程**

```python
# scripts/rollback_decision.py
# 自動回滾決策

def should_rollback(metrics):
    """根據指標自動判斷是否需要回滾"""

    critical_issues = []
    high_issues = []

    # 1. 數據準確性檢查
    if metrics.get('revenue_diff_pct', 0) > 5:
        critical_issues.append(f"營收數據異常: 差異 {metrics['revenue_diff_pct']}%")

    # 2. 錯誤率檢查
    if metrics.get('error_rate', 0) > 10:
        critical_issues.append(f"錯誤率過高: {metrics['error_rate']}%")

    # 3. 性能檢查
    if metrics.get('latency_increase_pct', 0) > 50:
        high_issues.append(f"查詢延遲增加: {metrics['latency_increase_pct']}%")

    # 4. 成本檢查
    if metrics.get('cost_increase_pct', 0) > 300:
        high_issues.append(f"查詢成本增加: {metrics['cost_increase_pct']}%")

    # 決策邏輯
    if critical_issues:
        print("🔴 發現嚴重問題，建議立即回滾:")
        for issue in critical_issues:
            print(f"  - {issue}")
        return True, "CRITICAL"

    if len(high_issues) >= 2:
        print("🟡 發現多個高優先級問題，建議回滾:")
        for issue in high_issues:
            print(f"  - {issue}")
        return True, "HIGH"

    print("🟢 未發現需要回滾的問題")
    return False, "OK"
```

### 13.4.2 快速回滾實作

**1. 藍綠環境快速切換**

```bash
#!/bin/bash
# scripts/rollback.sh - 快速回滾到上一版本

set -e

echo "🔄 開始回滾流程..."

# 檢測當前環境
CURRENT_ENV=$(bq query --project_id=m3-analytics-prod --use_legacy_sql=false \
  "SELECT table_schema FROM \`m3-analytics-prod.dbt_prod.INFORMATION_SCHEMA.TABLES\` LIMIT 1" \
  | grep dbt_prod | awk -F'.' '{print $2}')

# 切換到另一個環境
if [[ "$CURRENT_ENV" == *"blue"* ]]; then
    ROLLBACK_TO="green"
    echo "🔵 當前: Blue → 回滾到: Green"
else
    ROLLBACK_TO="blue"
    echo "🟢 當前: Green → 回滾到: Blue"
fi

# 執行切換
./scripts/switch_environment.sh $ROLLBACK_TO

# 記錄回滾事件
bq query --use_legacy_sql=false --project_id=m3-analytics-prod \
  "INSERT INTO \`m3-analytics-prod.dbt_metadata.deployment_log\`
   VALUES (CURRENT_TIMESTAMP(), '$ROLLBACK_TO', 'rollback', 'success')"

echo "✅ 回滾完成！當前環境: $ROLLBACK_TO"
echo "⚠️  請立即檢查數據和報表"
```

**執行時間**：< 2 分鐘

**2. Manifest 版本回滾**

如果沒有使用藍綠部署，可以使用 dbt manifest 進行版本回滾：

```bash
#!/bin/bash
# scripts/rollback_manifest.sh - 基於 manifest 的回滾

VERSION=${1:-"previous"}  # 默認回滾到上一版本

echo "📦 回滾到版本: $VERSION"

# 1. 恢復舊版 manifest
if [ "$VERSION" == "previous" ]; then
    cp manifests/prod/manifest.json.backup manifests/prod/manifest.json
else
    cp manifests/prod/manifest.json.$VERSION manifests/prod/manifest.json
fi

# 2. 重新部署舊版本模型
dbt run --target prod --state manifests/prod/

# 3. 驗證
dbt test --target prod

echo "✅ Manifest 回滾完成"
```

### 13.4.3 數據恢復策略

**1. 時間旅行（Time Travel）**

BigQuery 支援 7 天內的歷史數據查詢：

```sql
-- 恢復 2 小時前的數據
CREATE OR REPLACE TABLE `m3-analytics-prod.dbt_prod.daily_revenue_summary` AS
SELECT * FROM `m3-analytics-prod.dbt_prod.daily_revenue_summary`
FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR);

-- 驗證恢復的數據
SELECT
    COUNT(*) as recovered_rows,
    MAX(updated_at) as last_update
FROM `m3-analytics-prod.dbt_prod.daily_revenue_summary`;
```

**2. 快照恢復**

M3 團隊定期創建關鍵表的快照：

```bash
#!/bin/bash
# scripts/create_snapshot.sh - 創建快照

TABLES=(
    "daily_revenue_summary"
    "customer_retention_cohort"
    "product_performance_metrics"
)

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

for table in "${TABLES[@]}"; do
    echo "📸 創建快照: $table"

    bq cp -f \
        m3-analytics-prod:dbt_prod.$table \
        m3-analytics-prod:dbt_snapshots.${table}_${TIMESTAMP}

    echo "  ✅ 快照已創建: ${table}_${TIMESTAMP}"
done

# 清理 30 天前的快照
bq ls --max_results=1000 m3-analytics-prod:dbt_snapshots | \
    grep "_20" | \
    awk -v date=$(date -d '30 days ago' +%Y%m%d) '$1 < date {print $1}' | \
    xargs -I {} bq rm -f m3-analytics-prod:dbt_snapshots.{}
```

**使用快照恢復**：

```bash
# 恢復到指定快照
bq cp -f \
    m3-analytics-prod:dbt_snapshots.daily_revenue_summary_20240115_093000 \
    m3-analytics-prod:dbt_prod.daily_revenue_summary
```

**3. 增量模型回滾**

對於增量模型，需要特別處理：

```bash
#!/bin/bash
# scripts/rollback_incremental.sh

MODEL=$1
ROLLBACK_DATE=$2  # YYYY-MM-DD

echo "🔄 回滾增量模型: $MODEL 到日期: $ROLLBACK_DATE"

# 1. 刪除回滾日期之後的數據
bq query --use_legacy_sql=false --project_id=m3-analytics-prod "
DELETE FROM \`m3-analytics-prod.dbt_prod.$MODEL\`
WHERE _dbt_updated_at >= TIMESTAMP('$ROLLBACK_DATE')
"

# 2. 重新運行該日期之後的增量邏輯
dbt run --target prod --select $MODEL --vars "{'start_date': '$ROLLBACK_DATE'}"

echo "✅ 增量模型回滾完成"
```

## 13.5 監控與告警

完善的監控系統是及時發現問題、減少故障影響的關鍵。

### 13.5.1 監控指標體系

M3 團隊建立了四層監控指標：

**1. 基礎設施層**

```python
# scripts/monitor_infrastructure.py
# 基礎設施監控

from google.cloud import monitoring_v3
import time

def monitor_bigquery_metrics():
    """監控 BigQuery 基礎指標"""

    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/m3-analytics-prod"

    # 查詢 slot 使用率
    now = time.time()
    interval = monitoring_v3.TimeInterval({
        "end_time": {"seconds": int(now)},
        "start_time": {"seconds": int(now - 300)},  # 最近 5 分鐘
    })

    results = client.list_time_series(
        request={
            "name": project_name,
            "filter": 'metric.type = "bigquery.googleapis.com/slots/total_allocated"',
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        }
    )

    for result in results:
        print(f"Slot 使用率: {result.points[0].value.int64_value} slots")

        if result.points[0].value.int64_value > 1000:
            send_alert("BigQuery slot 使用率過高", "HIGH")
```

**監控指標**：
- BigQuery slot 使用率
- 查詢隊列長度
- 儲存空間使用量
- API 請求延遲

**2. dbt 執行層**

```yaml
# dbt-cloud/monitor_config.yml
# 或使用 dbt Core + 自定義監控

monitors:
  - name: dbt_run_duration
    metric: run_duration_seconds
    threshold: 600  # 10 分鐘
    severity: HIGH

  - name: dbt_run_failure_rate
    metric: failed_runs / total_runs
    threshold: 0.05  # 5%
    severity: CRITICAL

  - name: dbt_test_failure_rate
    metric: failed_tests / total_tests
    threshold: 0.02  # 2%
    severity: HIGH
```

**自定義 dbt 監控**：

```python
# scripts/monitor_dbt_runs.py

import json
from datetime import datetime, timedelta
from google.cloud import bigquery

def monitor_dbt_runs():
    """監控 dbt 運行狀態"""

    client = bigquery.Client(project='m3-analytics-prod')

    # 分析最近 1 小時的 dbt 運行日誌
    query = """
    WITH recent_runs AS (
        SELECT
            run_id,
            status,
            TIMESTAMP_DIFF(completed_at, started_at, SECOND) as duration_seconds,
            model_count,
            failed_models
        FROM `m3-analytics-prod.dbt_metadata.run_results`
        WHERE started_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
    )
    SELECT
        COUNT(*) as total_runs,
        COUNTIF(status = 'success') as successful_runs,
        COUNTIF(status = 'failed') as failed_runs,
        AVG(duration_seconds) as avg_duration,
        MAX(duration_seconds) as max_duration
    FROM recent_runs
    """

    result = client.query(query).result()
    row = next(result)

    # 檢查失敗率
    failure_rate = row.failed_runs / row.total_runs if row.total_runs > 0 else 0

    if failure_rate > 0.1:
        send_alert(
            title=f"dbt 運行失敗率過高: {failure_rate:.1%}",
            message=f"最近 1 小時內 {row.failed_runs}/{row.total_runs} 次運行失敗",
            severity="CRITICAL"
        )

    # 檢查執行時間
    if row.max_duration > 1800:  # 30 分鐘
        send_alert(
            title=f"dbt 運行時間過長",
            message=f"最長執行時間: {row.max_duration/60:.1f} 分鐘",
            severity="HIGH"
        )

    print(f"✅ dbt 運行監控: {row.successful_runs}/{row.total_runs} 成功")
```

**3. 數據品質層**

```sql
-- 創建數據品質監控視圖
CREATE OR REPLACE VIEW `m3-analytics-prod.dbt_monitoring.data_quality_metrics` AS

WITH freshness_check AS (
    SELECT
        'daily_revenue_summary' as table_name,
        MAX(date) as latest_date,
        DATE_DIFF(CURRENT_DATE(), MAX(date), DAY) as days_stale
    FROM `m3-analytics-prod.dbt_prod.daily_revenue_summary`
),

completeness_check AS (
    SELECT
        'stg_orders' as table_name,
        COUNTIF(customer_id IS NULL) / COUNT(*) * 100 as null_pct
    FROM `m3-analytics-prod.dbt_prod.stg_orders`
    WHERE order_date = CURRENT_DATE()
)

SELECT * FROM freshness_check
UNION ALL
SELECT
    table_name,
    null_pct,
    CASE WHEN null_pct > 5 THEN 1 ELSE 0 END as alert_flag
FROM completeness_check;
```

**監控腳本**：

```python
# scripts/monitor_data_quality.py

def check_data_freshness():
    """檢查數據新鮮度"""

    client = bigquery.Client(project='m3-analytics-prod')

    query = """
    SELECT
        table_name,
        latest_date,
        days_stale
    FROM `m3-analytics-prod.dbt_monitoring.data_quality_metrics`
    WHERE days_stale > 1
    """

    stale_tables = list(client.query(query).result())

    if stale_tables:
        message = "以下表格數據不新鮮:\n"
        for table in stale_tables:
            message += f"- {table.table_name}: 最後更新 {table.days_stale} 天前\n"

        send_alert("數據新鮮度告警", message, "HIGH")
```

**4. 業務指標層**

```python
# scripts/monitor_business_metrics.py
# 業務指標異常檢測

def detect_anomalies():
    """檢測業務指標異常"""

    client = bigquery.Client(project='m3-analytics-prod')

    # 使用移動平均和標準差檢測異常
    query = """
    WITH daily_metrics AS (
        SELECT
            date,
            total_revenue,
            AVG(total_revenue) OVER (
                ORDER BY date
                ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
            ) as avg_revenue_7d,
            STDDEV(total_revenue) OVER (
                ORDER BY date
                ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
            ) as stddev_revenue_7d
        FROM `m3-analytics-prod.dbt_prod.daily_revenue_summary`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    )
    SELECT
        date,
        total_revenue,
        avg_revenue_7d,
        ABS(total_revenue - avg_revenue_7d) / NULLIF(stddev_revenue_7d, 0) as z_score
    FROM daily_metrics
    WHERE date = CURRENT_DATE()
    """

    result = client.query(query).result()
    row = next(result)

    # Z-score > 3 表示異常（超過 3 個標準差）
    if row.z_score > 3:
        change_pct = (row.total_revenue - row.avg_revenue_7d) / row.avg_revenue_7d * 100

        send_alert(
            title="營收異常波動",
            message=f"""
            今日營收: ${row.total_revenue:,.0f}
            7日平均: ${row.avg_revenue_7d:,.0f}
            變化: {change_pct:+.1f}%
            異常分數: {row.z_score:.2f}
            """,
            severity="CRITICAL"
        )
```

### 13.5.2 告警配置

**告警優先級定義**

```python
# config/alert_levels.py

ALERT_LEVELS = {
    'CRITICAL': {
        'channels': ['pagerduty', 'slack', 'email'],
        'response_time': '15 minutes',
        'escalation': True
    },
    'HIGH': {
        'channels': ['slack', 'email'],
        'response_time': '1 hour',
        'escalation': False
    },
    'MEDIUM': {
        'channels': ['slack'],
        'response_time': '4 hours',
        'escalation': False
    },
    'LOW': {
        'channels': ['email'],
        'response_time': '24 hours',
        'escalation': False
    }
}
```

**Slack 告警整合**

```python
# scripts/alerting.py

import requests
import json

def send_alert(title, message, severity='HIGH'):
    """發送告警到 Slack"""

    webhook_url = os.getenv('SLACK_WEBHOOK_URL')

    color_map = {
        'CRITICAL': '#FF0000',
        'HIGH': '#FFA500',
        'MEDIUM': '#FFFF00',
        'LOW': '#00FF00'
    }

    payload = {
        "attachments": [{
            "color": color_map.get(severity, '#808080'),
            "title": f"[{severity}] {title}",
            "text": message,
            "footer": "M3 dbt Monitoring",
            "ts": int(time.time())
        }]
    }

    response = requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code != 200:
        print(f"❌ 告警發送失敗: {response.text}")
    else:
        print(f"✅ 告警已發送: {title}")
```

### 13.5.3 監控儀表板

M3 團隊使用 Looker Studio (Data Studio) 建立監控儀表板：

**儀表板結構**

```markdown
## dbt 生產監控儀表板

### 第一區塊：執行概況
- 今日 dbt 運行次數：12 次
- 成功率：100%
- 平均執行時間：8.5 分鐘
- 處理數據量：125 GB

### 第二區塊：數據新鮮度
- ✅ daily_revenue_summary: 1 小時前
- ✅ customer_retention_cohort: 2 小時前
- ⚠️  product_performance_metrics: 25 小時前

### 第三區塊：測試結果
- 總測試數：284
- 通過：284 (100%)
- 失敗：0
- 警告：2

### 第四區塊：成本分析
- 今日查詢成本：$45.20
- 本月累計：$1,234.50
- 預算使用率：61.7%

### 第五區塊：業務指標
- 今日營收：$125,450 (+2.3%)
- 新用戶：1,234 (+5.1%)
- 訂單數：5,678 (-1.2%)
```

**儀表板 SQL**

```sql
-- dbt 運行統計
CREATE OR REPLACE VIEW `m3-analytics-prod.dbt_monitoring.run_summary` AS
SELECT
    DATE(started_at) as run_date,
    COUNT(*) as total_runs,
    COUNTIF(status = 'success') as successful_runs,
    AVG(TIMESTAMP_DIFF(completed_at, started_at, SECOND)) as avg_duration_seconds,
    SUM(bytes_processed) / POW(10, 9) as total_gb_processed
FROM `m3-analytics-prod.dbt_metadata.run_results`
WHERE started_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY 1
ORDER BY 1 DESC;
```

---

**本章小結**

第 13 章系統性地介紹了 dbt 的 QA 與生產環境部署實踐：

1. **多環境策略**：dev/qa/prod 三層架構，使用 profiles.yml 和環境變數靈活管理
2. **部署檢查**：自動化 + 人工審查的雙重保障機制
3. **藍綠部署**：零停機部署，快速切換和驗證
4. **Rollback 機制**：多種回滾策略，確保部署安全
5. **監控告警**：四層監控體系，從基礎設施到業務指標全面覆蓋

這些實踐確保了 M3 團隊能夠安全、可靠地將 dbt 變更部署到生產環境，同時最小化業務風險。下一章將探討團隊協作與知識資產化，幫助組織更好地規模化 dbt 實踐。
