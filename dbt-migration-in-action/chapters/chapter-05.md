# 第 5 章：每日完全更新資料表遷移模式

> 在本章中，我們將深入探討最常見的遷移模式：**每日完全更新資料表**（Daily Full Refresh Tables）。這種模式佔了 M3 專案中約 60% 的案例。到本章結束時，你將掌握這種模式的所有細節，建立可重用的範本，並且能夠讓 Claude Code 獨立處理 3-5 個類似的檔案，成功率達到 85% 以上。

在第 4 章中，我們建立了遷移手冊 v1.0，並用第二個 SQL 檔案驗證了它的有效性。現在，我們要進入「批量遷移」階段。關鍵策略是：**先掌握最常見的模式，建立穩定的處理方法，然後快速複製到類似案例**。

每日完全更新資料表就是這個「最常見的模式」。讓我們系統化地分析它，建立範本，然後實現自動化。

## 5.1 完全更新模式概述

### 5.1.1 什麼是每日完全更新？

**每日完全更新資料表**（Daily Full Refresh Table）是一種數據處理模式，其特徵是：

1. **完全重建**：每次執行時完全重建整個表，而不是增量更新
2. **固定週期**：通常每天執行一次
3. **CREATE OR REPLACE**：使用 `CREATE OR REPLACE TABLE` 語法
4. **無狀態**：不依賴前一次執行的結果

**典型的使用場景**：

- **彙總報表**：每日銷售彙總、用戶活動統計
- **快照表**：某個時間點的數據快照
- **小到中型表**：數據量不會太大（幾百萬到數千萬行）
- **邏輯相對簡單**：不需要複雜的增量邏輯

### 5.1.2 為何選擇完全更新？

你可能會問：「為何不用增量更新？完全重建不是很浪費資源嗎？」

這是一個好問題。讓我們看看完全更新的優勢：

| 優勢 | 說明 | 適用情況 |
|-----|------|---------|
| **邏輯簡單** | 不需要處理 UPDATE/DELETE 邏輯 | 大部分報表場景 |
| **容易除錯** | 每次都是全新數據，易於驗證 | 開發和測試階段 |
| **數據一致性** | 不會有部分更新導致的不一致 | 需要完整數據的分析 |
| **易於恢復** | 出錯只需重跑，不會污染歷史數據 | 生產環境穩定性 |

**權衡考量**：

✅ **適合完全更新的情況**：
- 數據量 < 1 億行
- 執行時間 < 10 分鐘
- 邏輯相對簡單
- 不需要保留歷史版本

❌ **不適合完全更新的情況**：
- 數據量 > 10 億行（成本太高）
- 需要保留歷史變更記錄
- 有複雜的增量邏輯
- 執行時間太長（> 30 分鐘）

在 M3 的 50 個 SQL 中，約 30 個屬於「適合完全更新」的類別，這就是我們先處理它們的原因。

### 5.1.3 BigQuery 中的實作方式

在 BigQuery 中，完全更新通常使用以下語法：

```sql
CREATE OR REPLACE TABLE `project.dataset.table_name` AS
SELECT
    -- 查詢邏輯
FROM source_tables
WHERE conditions
```

**關鍵特徵**：

**‹1› CREATE OR REPLACE TABLE**
- 如果表不存在，創建新表
- 如果表已存在，完全替換（schema 和數據）
- 原子操作：要麼成功替換，要麼保持原樣

**‹2› AS SELECT**
- 表的 schema 由 SELECT 查詢推斷
- 不需要預先定義欄位類型

**‹3› 執行時機**
- 通常由排程工具觸發（如 Airflow、Cloud Scheduler）
- 每天固定時間執行

### 5.1.4 dbt 中的對應策略

在 dbt 中，完全更新對應的是 **table materialization**：

```sql
-- models/staging/stg_example.sql
{{ config(
    materialized='table'
) }}

SELECT
    -- 查詢邏輯
FROM {{ source('raw', 'source_table') }}
```

當你執行 `dbt run -s stg_example` 時，dbt 會：

1. 執行 SELECT 查詢
2. 將結果寫入臨時表
3. 用臨時表替換目標表（原子操作）
4. 清理臨時表

**dbt table materialization 的優勢**：

- **原子替換**：確保表始終處於一致狀態
- **自動管理**：不需要手動寫 CREATE OR REPLACE
- **測試集成**：可以在建表後自動運行測試
- **文檔生成**：自動生成數據字典

💡 **關鍵洞察**：從 BigQuery SQL 到 dbt 的遷移，主要是把「顯式的 CREATE OR REPLACE」改為「dbt 的 materialized='table' 配置」。SELECT 邏輯本身幾乎不變。

## 5.2 原始 SQL 分析

在開始遷移前，讓我們深入分析一個典型的完全更新表 SQL，理解它的每個組成部分。

### 5.2.1 典型結構剖析

以下是一個真實案例（已脫敏）：

```sql
-- ===================================
-- 表名：daily_sales_summary
-- 用途：每日銷售彙總報表
-- 更新頻率：每日 02:00 (UTC+8)
-- 維護人：Data Team
-- ===================================

CREATE OR REPLACE TABLE `m3-project.analytics.daily_sales_summary` AS

WITH order_base AS (  ‹1›
    -- 訂單基礎數據
    SELECT
        order_id,
        user_id,
        DATE(order_timestamp) as order_date,
        amount,
        status
    FROM `m3-project.raw_data.orders`
    WHERE DATE(order_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)  ‹2›
        AND status IN ('completed', 'shipped')
),

user_info AS (  ‹3›
    -- 用戶基本信息
    SELECT
        user_id,
        user_name,
        user_type,  -- 'premium' 或 'regular'
        region
    FROM `m3-project.raw_data.users`
    WHERE is_active = true
)

SELECT  ‹4›
    o.order_date,  -- 訂單日期
    u.region,  -- 地區
    u.user_type,  -- 用戶類型
    COUNT(DISTINCT o.order_id) as order_count,  -- 訂單數量
    COUNT(DISTINCT o.user_id) as user_count,  -- 購買用戶數
    SUM(o.amount) as total_amount,  -- 總銷售額
    AVG(o.amount) as avg_order_amount,  -- 平均訂單金額
    -- 計算高價訂單比例
    SAFE_DIVIDE(
        COUNTIF(o.amount > 1000),  ‹5›
        COUNT(o.order_id)
    ) as high_value_order_ratio
FROM order_base o
LEFT JOIN user_info u  ‹6›
    ON o.user_id = u.user_id
GROUP BY o.order_date, u.region, u.user_type  ‹7›
```

讓我們逐一分析關鍵元素：

**‹1› CTE (Common Table Expression)**
- 使用 WITH 子句組織複雜查詢
- `order_base` 和 `user_info` 是兩個 CTE
- 提升可讀性，避免巢狀子查詢

**‹2› 時間範圍過濾**
- 只處理最近 90 天的數據
- 減少計算量，提升性能
- 使用 `CURRENT_DATE()` 確保每天自動調整

**‹3› 數據預處理**
- 在 CTE 中先過濾和轉換數據
- 只選擇需要的欄位
- 提早過濾掉不需要的記錄

**‹4› 主查詢**
- 從 CTE 中組合數據
- 進行聚合計算

**‹5› 條件聚合**
- 使用 `COUNTIF` 條件計數
- `SAFE_DIVIDE` 避免除以零錯誤

**‹6› JOIN 類型**
- `LEFT JOIN` 保留所有訂單，即使找不到用戶信息
- 這個選擇很重要，影響結果的完整性

**‹7› 分組維度**
- 按日期、地區、用戶類型三個維度聚合
- 順序與 SELECT 中的欄位對應

### 5.2.2 識別關鍵特徵

在分析任何完全更新表時，問自己這些問題：

**結構特徵**：
- [ ] 是否使用 CTE？（WITH 子句）
- [ ] 有幾個 CTE？它們的依賴關係？
- [ ] 主查詢的結構（SELECT, FROM, JOIN, WHERE, GROUP BY）

**數據來源**：
- [ ] 參照了哪些外部表？
- [ ] 這些表來自哪個 dataset/schema？
- [ ] 是否有自連接（同一個表 JOIN 自己）？

**JOIN 關係**：
- [ ] 使用了哪些類型的 JOIN？（INNER, LEFT, RIGHT, FULL OUTER）
- [ ] JOIN 的條件是什麼？
- [ ] 為何選擇這種 JOIN 類型？（業務邏輯）

**聚合邏輯**：
- [ ] 有哪些聚合函數？（SUM, COUNT, AVG, MAX, MIN）
- [ ] 分組維度是什麼？（GROUP BY 的欄位）
- [ ] 是否有條件聚合？（COUNTIF, SUMIF）

**時間處理**：
- [ ] 如何過濾時間範圍？
- [ ] 使用絕對時間還是相對時間？（如 CURRENT_DATE()）
- [ ] 時區考量？

**BigQuery 特定語法**：
- [ ] 是否使用 BigQuery 特有函數？（如 SAFE_DIVIDE, DATE_SUB）
- [ ] 是否有 STRUCT 或 ARRAY？
- [ ] 是否有 UDF（用戶自定義函數）？

📝 **實戰建議**：在開始遷移前，花 5-10 分鐘完整分析原始 SQL。理解越深，遷移越順利。

### 5.2.3 常見模式變體

完全更新表雖然結構相似，但有一些常見變體：

**變體 1：簡單聚合（無 CTE）**
```sql
CREATE OR REPLACE TABLE `project.dataset.simple_summary` AS
SELECT
    DATE(timestamp) as date,
    category,
    COUNT(*) as count,
    SUM(amount) as total
FROM `project.dataset.source`
GROUP BY date, category
```

**變體 2：多層 CTE**
```sql
WITH step1 AS (...),
     step2 AS (SELECT ... FROM step1 ...),  -- 依賴 step1
     step3 AS (SELECT ... FROM step2 ...)   -- 依賴 step2
SELECT ... FROM step3
```

**變體 3：UNION 合併多個來源**
```sql
CREATE OR REPLACE TABLE `project.dataset.combined` AS
SELECT * FROM `project.dataset.source_a`
UNION ALL
SELECT * FROM `project.dataset.source_b`
```

**變體 4：窗口函數**
```sql
SELECT
    user_id,
    order_date,
    amount,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date) as order_seq,
    SUM(amount) OVER (PARTITION BY user_id ORDER BY order_date) as cumulative_amount
FROM orders
```

💡 **關鍵**：無論哪種變體，遷移策略都是一樣的：保持 SELECT 邏輯不變，只替換表參照和配置方式。

## 5.3 dbt 遷移實作

現在讓我們實際遷移前面的 `daily_sales_summary` 範例。

### 5.3.1 Step 1: 建立 Sources 定義

首先識別所有外部表：
- `m3-project.raw_data.orders`
- `m3-project.raw_data.users`

在 `models/sources.yml` 中定義：

```yaml
# models/sources.yml
version: 2

sources:
  - name: raw_data  ‹1›
    description: "原始數據來源，來自業務系統的同步"
    database: m3-project  ‹2›
    schema: raw_data
    tables:
      - name: orders  ‹3›
        description: "訂單交易記錄表"
        columns:
          - name: order_id
            description: "訂單唯一識別碼"
          - name: user_id
            description: "下單用戶ID"
          - name: order_timestamp
            description: "訂單建立時間"
          - name: amount
            description: "訂單金額"
          - name: status
            description: "訂單狀態（completed, shipped, cancelled 等）"

      - name: users  ‹4›
        description: "用戶主檔表"
        columns:
          - name: user_id
            description: "用戶唯一識別碼"
          - name: user_name
            description: "用戶名稱"
          - name: user_type
            description: "用戶類型（premium/regular）"
          - name: region
            description: "用戶所在地區"
          - name: is_active
            description: "是否為活躍用戶"
```

**‹1›** source 名稱可以簡化，這裡用 `raw_data` 而不是完整的 `m3-project.raw_data`

**‹2›** `database` 是 GCP 專案 ID，`schema` 是 BigQuery dataset 名稱

**‹3›** 為 orders 表定義所有使用到的欄位及其描述

**‹4›** 同樣為 users 表定義欄位

💡 **最佳實踐**：即使是 sources，也應該為欄位提供描述。這有助於團隊理解數據來源。

### 5.3.2 Step 2: 建立 dbt 模型 SQL

創建 `models/marts/daily_sales_summary.sql`：

```sql
-- models/marts/daily_sales_summary.sql
-- ===================================
-- 表名：daily_sales_summary
-- 用途：每日銷售彙總報表
-- 更新頻率：每日 02:00 (UTC+8)
-- 維護人：Data Team
-- ===================================

{{ config(
    materialized='table',  ‹1›
    description='每日銷售彙總報表，按日期、地區、用戶類型三個維度統計銷售指標'
) }}

WITH order_base AS (
    -- 訂單基礎數據
    SELECT
        order_id,
        user_id,
        DATE(order_timestamp) as order_date,
        amount,
        status
    FROM {{ source('raw_data', 'orders') }}  ‹2›
    WHERE DATE(order_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
        AND status IN ('completed', 'shipped')
),

user_info AS (
    -- 用戶基本信息
    SELECT
        user_id,
        user_name,
        user_type,  -- 'premium' 或 'regular'
        region
    FROM {{ source('raw_data', 'users') }}  ‹3›
    WHERE is_active = true
)

SELECT
    o.order_date,  -- 訂單日期
    u.region,  -- 地區
    u.user_type,  -- 用戶類型
    COUNT(DISTINCT o.order_id) as order_count,  -- 訂單數量
    COUNT(DISTINCT o.user_id) as user_count,  -- 購買用戶數
    SUM(o.amount) as total_amount,  -- 總銷售額
    AVG(o.amount) as avg_order_amount,  -- 平均訂單金額
    -- 計算高價訂單比例
    SAFE_DIVIDE(
        COUNTIF(o.amount > 1000),
        COUNT(o.order_id)
    ) as high_value_order_ratio
FROM order_base o
LEFT JOIN user_info u
    ON o.user_id = u.user_id
GROUP BY o.order_date, u.region, u.user_type
```

**關鍵變更對比**：

| 原始 SQL | dbt 模型 | 說明 |
|---------|---------|------|
| `CREATE OR REPLACE TABLE` | `{{ config(materialized='table') }}` | dbt 配置替代 |
| `` `m3-project.raw_data.orders` `` | `{{ source('raw_data', 'orders') }}` | 使用 source 函數 |
| `` `m3-project.raw_data.users` `` | `{{ source('raw_data', 'users') }}` | 使用 source 函數 |
| （其他部分） | （完全保持不變） | 保持邏輯一致性 |

**‹1›** config block 設定 materialization 類型和模型描述

**‹2›** 使用 `{{ source() }}` 替換硬編碼的表名

**‹3›** 同樣使用 `{{ source() }}` 函數

⚠️ **重要檢查**：
- ✅ 所有註解都保留了
- ✅ CTE 結構完全一致
- ✅ SELECT 欄位順序沒有改變
- ✅ JOIN 類型仍然是 LEFT JOIN
- ✅ WHERE、GROUP BY 條件完全相同

### 5.3.3 Step 3: 建立 Schema 定義

創建或更新 `models/marts/schema.yml`：

```yaml
# models/marts/schema.yml
version: 2

models:
  - name: daily_sales_summary  ‹1›
    description: |  ‹2›
      每日銷售彙總報表

      **業務用途**：
      - 分析每日銷售趨勢
      - 對比不同地區和用戶類型的表現
      - 監控高價訂單比例

      **更新頻率**：每日 02:00 (UTC+8)

      **數據範圍**：最近 90 天的已完成訂單

    columns:
      - name: order_date  ‹3›
        description: "訂單日期（從 order_timestamp 轉換而來）"
        tests:
          - not_null  ‹4›

      - name: region
        description: "用戶所在地區"
        tests:
          - not_null

      - name: user_type
        description: "用戶類型（premium: 高級會員, regular: 普通會員）"
        tests:
          - not_null
          - accepted_values:  ‹5›
              values: ['premium', 'regular']

      - name: order_count
        description: "該日期、地區、用戶類型組合下的訂單數量（不重複計算）"
        tests:
          - not_null

      - name: user_count
        description: "購買用戶數量（不重複計算）"
        tests:
          - not_null

      - name: total_amount
        description: "總銷售額（所有訂單金額的總和）"
        tests:
          - not_null

      - name: avg_order_amount
        description: "平均訂單金額（total_amount / order_count）"

      - name: high_value_order_ratio
        description: |
          高價訂單比例（金額 > 1000 的訂單數 / 總訂單數）
          使用 SAFE_DIVIDE 避免除以零錯誤
```

**‹1›** 模型名稱必須與檔案名一致（不含 .sql）

**‹2›** 使用 `|` 符號支援多行描述，提供完整的業務背景

**‹3›** 每個欄位都有清楚的描述

**‹4›** 加入 `not_null` 測試確保數據品質

**‹5›** 對有限值的欄位加入 `accepted_values` 測試

### 5.3.4 Step 4: 配置 dbt_project.yml

在 `dbt_project.yml` 中設定模型的配置：

```yaml
# dbt_project.yml
name: 'm3_analytics'
version: '1.0.0'
config-version: 2

models:
  m3_analytics:
    # Staging models: 資料清理和標準化
    staging:
      +materialized: view  # staging 使用 view
      +schema: staging

    # Marts models: 業務邏輯和彙總
    marts:
      +materialized: table  # marts 使用 table ‹1›
      +schema: analytics  # 輸出到 analytics dataset ‹2›
```

**‹1›** marts 資料夾下的模型預設使用 table materialization

**‹2›** 輸出到 `m3-project.analytics` dataset

💡 **資料夾組織最佳實踐**：
```
models/
├── staging/        # 清理和標準化（使用 view）
├── intermediate/   # 中間處理步驟（使用 view）
└── marts/          # 最終業務表（使用 table）
```

### 5.3.5 Step 5: 執行與驗證

現在執行 dbt 模型：

```bash
# 執行單一模型
dbt run -s daily_sales_summary

# 執行並顯示詳細日誌
dbt run -s daily_sales_summary --log-level debug

# 執行測試
dbt test -s daily_sales_summary
```

**預期輸出**：

```
Running with dbt=1.5.0
Found 1 model, 8 tests, 0 snapshots, 0 analyses, 0 macros, 0 operations, 2 sources

Concurrency: 4 threads (target='dev')

1 of 1 START sql table model analytics.daily_sales_summary .......... [RUN]
1 of 1 OK created sql table model analytics.daily_sales_summary ..... [CREATE TABLE (1234 rows) in 15.2s]

Finished running 1 table model in 0 hours 0 minutes and 16.8 seconds (16.8s).

Completed successfully

Done. PASS=1 WARN=0 ERROR=0 SKIP=0 TOTAL=1
```

執行測試：

```bash
dbt test -s daily_sales_summary
```

**預期輸出**：

```
Running with dbt=1.5.0
Found 1 model, 8 tests

1 of 8 START test not_null_daily_sales_summary_order_date ........... [RUN]
1 of 8 PASS not_null_daily_sales_summary_order_date ................. [PASS in 2.1s]
2 of 8 START test not_null_daily_sales_summary_region ............... [RUN]
2 of 8 PASS not_null_daily_sales_summary_region ..................... [PASS in 1.9s]
3 of 8 START test not_null_daily_sales_summary_user_type ............ [RUN]
3 of 8 PASS not_null_daily_sales_summary_user_type .................. [PASS in 2.0s]
4 of 8 START test accepted_values_daily_sales_summary_user_type ..... [RUN]
4 of 8 PASS accepted_values_daily_sales_summary_user_type ........... [PASS in 2.2s]
...

Completed successfully

Done. PASS=8 WARN=0 ERROR=0 SKIP=0 TOTAL=8
```

✅ **驗證檢查清單**：
- ✅ 模型成功建立
- ✅ Row count 合理（與原始表比對）
- ✅ 所有測試通過
- ✅ 執行時間可接受（< 10 分鐘）

## 5.4 Schema 與約束處理

Schema 定義是遷移中最容易被忽略，但又非常重要的部分。讓我們深入探討。

### 5.4.1 從 BigQuery 提取 Schema

如果原始表已經有 schema 定義，我們可以從 BigQuery 提取：

**方法 1：使用 BigQuery Console**

```sql
-- 在 BigQuery 中執行
SELECT
    column_name,
    data_type,
    is_nullable,
    description
FROM `m3-project.analytics`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'daily_sales_summary'
ORDER BY ordinal_position;
```

**方法 2：使用 bq 命令列工具**

```bash
bq show --schema --format=prettyjson \
  m3-project:analytics.daily_sales_summary
```

輸出範例：

```json
[
  {
    "name": "order_date",
    "type": "DATE",
    "mode": "REQUIRED",
    "description": "訂單日期"
  },
  {
    "name": "region",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "用戶所在地區"
  },
  ...
]
```

### 5.4.2 欄位描述遷移策略

**策略 1：完整遷移（推薦）**

將所有欄位描述都遷移到 dbt schema.yml：

```yaml
columns:
  - name: order_date
    description: "訂單日期（從 order_timestamp 轉換而來）"
    # 如果原始描述是「訂單日期」，可以擴充為更詳細的說明
```

**策略 2：擴充描述**

原始描述可能過於簡單，在 dbt 中可以擴充：

| 原始描述 | dbt 擴充描述 | 改進點 |
|---------|------------|-------|
| "訂單數量" | "該日期、地區、用戶類型組合下的訂單數量（不重複計算）" | 說明聚合維度和去重邏輯 |
| "總金額" | "總銷售額（所有訂單金額的總和，單位：元）" | 說明計算邏輯和單位 |
| "比例" | "高價訂單比例（金額 > 1000 的訂單數 / 總訂單數）" | 說明計算公式 |

💡 **原則**：dbt 的 schema.yml 不只是技術文檔，更是業務文檔。應該讓非技術人員也能理解。

### 5.4.3 約束條件遷移

BigQuery 支援的約束（雖然大部分是 metadata，不強制執行）：

1. **NOT NULL**
2. **PRIMARY KEY**（metadata only）
3. **FOREIGN KEY**（metadata only）

在 dbt 中，我們用 tests 來驗證這些約束：

**NOT NULL 遷移**：

```yaml
# 原始表定義
CREATE TABLE ... (
    order_date DATE NOT NULL,
    ...
)

# dbt schema.yml
columns:
  - name: order_date
    tests:
      - not_null
```

**UNIQUE / PRIMARY KEY 遷移**：

```yaml
# 原始表定義
CREATE TABLE ... (
    order_id STRING PRIMARY KEY,
    ...
)

# dbt schema.yml
columns:
  - name: order_id
    tests:
      - unique
      - not_null
```

**FOREIGN KEY 遷移**：

```yaml
# 原始表定義：user_id 參照 users.user_id

# dbt schema.yml
columns:
  - name: user_id
    tests:
      - relationships:  ‹1›
          to: source('raw_data', 'users')
          field: user_id
```

**‹1›** relationships test 驗證外鍵關係的完整性

### 5.4.4 數據類型處理

BigQuery 和 dbt 的數據類型對應：

| BigQuery 類型 | dbt 處理 | 注意事項 |
|--------------|---------|---------|
| INT64 | 自動推斷 | 無需特殊處理 |
| FLOAT64 | 自動推斷 | 無需特殊處理 |
| STRING | 自動推斷 | 無需特殊處理 |
| DATE | 自動推斷 | 確保使用 DATE() 函數 |
| TIMESTAMP | 自動推斷 | 注意時區 |
| BOOL | 自動推斷 | 無需特殊處理 |
| STRUCT | 保持原樣 | 在 schema.yml 中詳細描述結構 |
| ARRAY | 保持原樣 | 說明陣列元素類型 |
| GEOGRAPHY | 保持原樣 | BigQuery 特有類型 |

**特殊類型範例**：

```yaml
# STRUCT 類型
columns:
  - name: user_info
    description: "用戶信息結構（包含 name, email, phone）"
    # 可以進一步描述內部欄位

# ARRAY 類型
columns:
  - name: tag_list
    description: "標籤列表（STRING ARRAY）"
```

### 5.4.5 自動化 Schema 生成

為了提升效率，我們可以建立腳本自動生成 schema.yml 的骨架：

```python
# scripts/generate_schema.py
"""
從 BigQuery 表自動生成 dbt schema.yml 骨架
"""

from google.cloud import bigquery
import yaml

def generate_schema(project_id, dataset_id, table_id):
    client = bigquery.Client(project=project_id)
    table = client.get_table(f"{project_id}.{dataset_id}.{table_id}")

    # 建立 schema 結構
    model_schema = {
        'name': table_id,
        'description': table.description or 'TODO: 加入描述',
        'columns': []
    }

    # 遍歷所有欄位
    for field in table.schema:
        column = {
            'name': field.name,
            'description': field.description or 'TODO: 加入描述',
            'tests': []
        }

        # 根據 mode 加入 not_null test
        if field.mode == 'REQUIRED':
            column['tests'].append('not_null')

        model_schema['columns'].append(column)

    # 輸出 YAML
    output = {
        'version': 2,
        'models': [model_schema]
    }

    print(yaml.dump(output, allow_unicode=True, default_flow_style=False))

# 使用範例
generate_schema('m3-project', 'analytics', 'daily_sales_summary')
```

執行後生成的骨架：

```yaml
version: 2
models:
- name: daily_sales_summary
  description: 'TODO: 加入描述'
  columns:
  - name: order_date
    description: 訂單日期
    tests:
    - not_null
  - name: region
    description: TODO: 加入描述
    tests: []
  ...
```

然後手動補充和優化描述。

## 5.5 讓 Claude 獨立作業

現在是真正的考驗：讓 Claude Code 獨立處理 3-5 個類似的檔案，驗證遷移手冊的穩定性。

### 5.5.1 準備測試案例

我們選擇以下 5 個每日完全更新表：

1. **daily_user_activity** - 用戶每日活動統計
2. **daily_product_performance** - 產品每日表現
3. **daily_region_summary** - 地區每日彙總
4. **daily_campaign_metrics** - 行銷活動每日指標
5. **daily_customer_segments** - 客戶分群每日快照

這些檔案都符合「每日完全更新」模式，但各有特點：

| 檔案 | 特點 | 測試重點 |
|-----|------|---------|
| daily_user_activity | 有窗口函數 | 複雜 SQL 邏輯保持 |
| daily_product_performance | 有多個 CTE | CTE 結構正確遷移 |
| daily_region_summary | 有 UNION ALL | UNION 邏輯保持 |
| daily_campaign_metrics | 有條件聚合 | COUNTIF/SUMIF 保持 |
| daily_customer_segments | 有 CASE WHEN | 複雜條件邏輯保持 |

### 5.5.2 標準化提示詞

我們建立一個標準化的提示詞模板：

```markdown
請參考遷移手冊 v1.0 將 {SQL_FILE_NAME} 遷移到 dbt 模型。

[貼上完整的遷移手冊 v1.0]

**原始檔案**：{SQL_FILE_PATH}

[貼上原始 SQL 內容]

**請產出**：
1. dbt 模型 SQL 檔案（models/marts/{MODEL_NAME}.sql）
2. sources.yml 更新（如需要新的 sources）
3. schema.yml 中此模型的定義

**特別注意**：
- 保留所有註解
- 不要改變任何 SQL 邏輯
- 所有欄位都要有描述
```

### 5.5.3 實際測試結果

讓我們看看 Claude Code 的表現：

**案例 1: daily_user_activity**

```
提示：[使用標準化提示詞]

Claude 輸出：
✅ 模型 SQL - 正確
✅ Sources - 正確
✅ Schema.yml - 正確
⚠️ 發現小問題：窗口函數的註解位置略有調整

修正時間：2 分鐘

結果：成功
```

**案例 2: daily_product_performance**

```
提示：[使用標準化提示詞]

Claude 輸出：
✅ 模型 SQL - 正確
✅ Sources - 正確
✅ Schema.yml - 正確

修正時間：0 分鐘

結果：完美成功
```

**案例 3: daily_region_summary**

```
提示：[使用標準化提示詞]

Claude 輸出：
✅ 模型 SQL - 正確
✅ Sources - 正確
⚠️ Schema.yml - 聚合欄位描述不夠詳細

修正時間：3 分鐘

結果：成功（需小幅修正）
```

**案例 4: daily_campaign_metrics**

```
提示：[使用標準化提示詞]

Claude 輸出：
✅ 模型 SQL - 正確
✅ Sources - 正確
✅ Schema.yml - 正確

修正時間：0 分鐘

結果：完美成功
```

**案例 5: daily_customer_segments**

```
提示：[使用標準化提示詞]

Claude 輸出：
✅ 模型 SQL - 正確
✅ Sources - 正確
✅ Schema.yml - 正確

修正時間：0 分鐘

結果：完美成功
```

### 5.5.4 成功率分析

讓我們統計結果：

| 指標 | 結果 | 目標 | 達標？ |
|-----|------|------|-------|
| 完美成功率 | 3/5 (60%) | > 50% | ✅ |
| 成功率（含小修正）| 5/5 (100%) | > 80% | ✅ |
| 平均修正時間 | 1 分鐘 | < 10 分鐘 | ✅ |
| Critical 錯誤 | 0 | < 5% | ✅ |

**結論**：遷移手冊 v1.0 對於「每日完全更新表」模式已經相當穩定！

### 5.5.5 發現的改進點

雖然成功率很高，但我們仍然發現一些小問題：

**問題 1：聚合欄位描述不夠詳細**

```yaml
# Claude 生成的
- name: total_amount
  description: "總金額"

# 理想的
- name: total_amount
  description: "總銷售額（所有訂單金額的總和，單位：元）"
```

**改進方向**：在 Playbook 中加入「聚合欄位描述應包含計算邏輯和單位」

**問題 2：窗口函數註解位置**

窗口函數的註解有時會被調整到不同行，雖然不影響功能，但稍微影響可讀性。

**改進方向**：在 Playbook 中強調「註解位置應與原始 SQL 完全一致」

### 5.5.6 效率對比

讓我們對比手動遷移和使用 Claude Code 的效率：

**手動遷移 5 個檔案**：
- 每個檔案 20-30 分鐘
- 總計：100-150 分鐘（約 2-2.5 小時）

**使用 Claude Code + Playbook**：
- Claude 生成：每個 3 分鐘 × 5 = 15 分鐘
- 檢查修正：每個 1 分鐘 × 5 = 5 分鐘
- 總計：20 分鐘

**效率提升**：約 **5-7 倍**！

而且，隨著 Playbook 的持續改進，這個效率還會繼續提升。

## 本章總結

在本章中，我們完成了重要的實踐：

✅ **深入理解了每日完全更新模式**，包括其特徵、適用場景和實作方式
✅ **系統化分析了原始 SQL 的結構**，建立了分析檢查清單
✅ **完整演示了 dbt 遷移流程**，從 sources 定義到 schema 配置
✅ **掌握了 Schema 和約束處理**，建立了自動化工具
✅ **驗證了批量遷移的可行性**，5 個檔案全部成功，效率提升 5-7 倍

### 核心收穫

**關於遷移模式**：
- 每日完全更新是最常見、最簡單的模式（佔 60% 案例）
- 關鍵是「保持 SELECT 邏輯不變」
- dbt 的 table materialization 對應原始的 CREATE OR REPLACE TABLE

**關於批量處理**：
- 標準化的提示詞模板很重要
- 遷移手冊使批量遷移成為可能
- 小問題可以在過程中持續改進

**關於效率提升**：
- 從手動 2-2.5 小時降到 20 分鐘
- 完美成功率 60%，整體成功率 100%
- 隨著 Playbook 改進，效率還會提升

### 實戰統計

經過本章實踐，我們的遷移進度：

| 模式類型 | 數量 | 已遷移 | 成功率 | 狀態 |
|---------|------|-------|-------|------|
| 每日完全更新 | 30 | 7 | 100% | ✅ 穩定 |
| 分區表 | 10 | 0 | - | ⏳ 待處理 |
| 分片表 | 10 | 0 | - | ⏳ 待處理 |
| **總計** | **50** | **7** | **100%** | **14% 完成** |

### 下一章預告

在第 6 章，我們將處理更複雜的場景：**分區資料表（Partitioned Tables）**。

分區表的特點：
- 需要配置 `partition_by`
- 可能有增量更新邏輯
- 性能和成本考量更重要

我們將：
- 理解 BigQuery 分區表的原理
- 掌握時間分區和整數分區的遷移
- 將分區表模式加入遷移手冊
- 達到手冊 v2.0

這將是遷移手冊的第一次重大演進。準備好了嗎？讓我們繼續！

---

**本章產出物清單**：
- ✅ 完全更新模式完整分析
- ✅ dbt 遷移完整範例（daily_sales_summary）
- ✅ Schema 自動生成腳本
- ✅ 標準化提示詞模板
- ✅ 5 個成功遷移案例

**下一步行動**：
1. 繼續遷移剩餘的每日完全更新表（約 23 個）
2. 記錄任何新發現的問題
3. 準備進入第 6 章：分區表遷移
