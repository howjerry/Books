# 第 6 章：分區資料表（Partitioned Tables）遷移

> 在本章中，我們將處理更複雜的場景：**分區資料表**（Partitioned Tables）。分區是 BigQuery 中最重要的性能優化技術之一，正確遷移分區配置對於保持查詢效率和控制成本至關重要。到本章結束時，你將掌握時間分區和整數分區的遷移方法，並將這些知識整合到遷移手冊 v2.0 中。

在前一章中，我們成功掌握了「每日完全更新」模式，並且批量遷移了 5 個檔案，效率提升了 5-7 倍。現在，讓我們進入下一個層次：分區表。

在 M3 的 50 個 SQL 中，約 10 個使用了分區表。這些表通常數據量較大（數百萬到數十億行），分區配置直接影響查詢性能和成本。

## 6.1 BigQuery 分區表基礎

### 6.1.1 什麼是分區表？

**分區表**（Partitioned Table）是將大型表按照特定欄位的值分割成較小的物理段（partitions）。每個分區獨立存儲，查詢時只需掃描相關分區，而不是整個表。

**視覺化理解**：

```
傳統表（無分區）：
┌───────────────────────────────────────────┐
│ 所有數據存在一起（100GB）                    │
│ 查詢一天的數據也要掃描整個 100GB              │
└───────────────────────────────────────────┘

分區表（按日期分區）：
┌──────────┬──────────┬──────────┬─────┬──────────┐
│2024-01-01│2024-01-02│2024-01-03│ ... │2024-12-31│
│  300MB   │  320MB   │  280MB   │     │  310MB   │
└──────────┴──────────┴──────────┴─────┴──────────┘
查詢 2024-01-01 的數據，只掃描 300MB ✅
```

### 6.1.2 分區的優勢

| 優勢 | 說明 | 實際效益 |
|-----|------|---------|
| **查詢性能** | 只掃描相關分區，減少數據量 | 查詢速度提升 10-100 倍 |
| **成本控制** | BigQuery 按掃描數據量計費 | 成本降低 90%+ |
| **數據管理** | 可以刪除或替換特定分區 | 簡化數據維護 |
| **並行處理** | 多個分區可以並行處理 | 提升 ETL 效率 |

**實際案例對比**：

```sql
-- 無分區表查詢
SELECT COUNT(*)
FROM orders  -- 掃描 100GB
WHERE order_date = '2024-01-01'
-- 掃描數據：100GB
-- 成本：$0.50
-- 執行時間：30 秒

-- 分區表查詢（按 order_date 分區）
SELECT COUNT(*)
FROM orders_partitioned  -- 只掃描 2024-01-01 分區
WHERE order_date = '2024-01-01'
-- 掃描數據：300MB
-- 成本：$0.0015
-- 執行時間：2 秒
```

成本降低了 **99.7%**，速度提升了 **15 倍**！

### 6.1.3 BigQuery 分區類型

BigQuery 支援四種分區類型：

**1. 時間單位欄位分區（Time-unit Column Partitioning）** ‹1›

按 DATE、TIMESTAMP 或 DATETIME 欄位分區：

```sql
CREATE OR REPLACE TABLE `project.dataset.orders`
PARTITION BY DATE(order_timestamp)  -- 按日期分區
AS SELECT ...
```

**分區粒度選項**：
- `HOUR`：按小時分區（適合實時數據）
- `DAY`：按天分區（最常用）
- `MONTH`：按月分區（適合歷史數據）
- `YEAR`：按年分區（適合長期存檔）

**2. 攝入時間分區（Ingestion-time Partitioning）** ‹2›

按數據寫入 BigQuery 的時間自動分區：

```sql
CREATE OR REPLACE TABLE `project.dataset.logs`
PARTITION BY _PARTITIONDATE  -- 使用內建的攝入時間
AS SELECT ...
```

**特點**：
- 不需要明確的時間欄位
- BigQuery 自動管理分區
- 適合日誌類數據

**3. 整數範圍分區（Integer Range Partitioning）** ‹3›

按整數欄位的範圍分區：

```sql
CREATE OR REPLACE TABLE `project.dataset.users`
PARTITION BY RANGE_BUCKET(user_id, GENERATE_ARRAY(0, 100000, 1000))
-- 將 user_id 按每 1000 個 ID 分區
AS SELECT ...
```

**適用場景**：
- 用戶 ID 分區
- 產品 ID 分區
- 任何有序整數欄位

**4. 無分區（特殊情況）**

某些情況下，表不需要分區：
- 數據量小（< 1GB）
- 沒有明確的分區維度
- 查詢總是全表掃描

### 6.1.4 分區表的 BigQuery 語法

**創建時間分區表**：

```sql
CREATE OR REPLACE TABLE `project.dataset.sales`
PARTITION BY DATE(sale_timestamp)  ‹1›
OPTIONS(
    partition_expiration_days = 90,  ‹2›
    require_partition_filter = true  ‹3›
)
AS
SELECT
    sale_id,
    sale_timestamp,
    amount
FROM source_table
```

**‹1›** 指定分區欄位，使用 DATE() 函數從 TIMESTAMP 提取日期

**‹2›** 自動刪除 90 天前的分區（節省儲存成本）

**‹3›** 強制查詢必須包含分區過濾條件（防止意外全表掃描）

**創建整數分區表**：

```sql
CREATE OR REPLACE TABLE `project.dataset.user_segments`
PARTITION BY RANGE_BUCKET(
    user_id,
    GENERATE_ARRAY(0, 1000000, 10000)  ‹1›
)
AS
SELECT
    user_id,
    segment,
    value
FROM source_table
```

**‹1›** 按 user_id 每 10,000 個 ID 創建一個分區（0-9999, 10000-19999, ...）

### 6.1.5 分區表查詢最佳實踐

**✅ 好的查詢（利用分區裁剪）**：

```sql
SELECT *
FROM orders
WHERE order_date = '2024-01-01'  -- 明確指定分區條件
  AND amount > 1000
-- 只掃描 2024-01-01 分區
```

**❌ 不好的查詢（全表掃描）**：

```sql
SELECT *
FROM orders
WHERE amount > 1000  -- 沒有分區條件
-- 掃描所有分區
```

**⚠️ 常見陷阱**：

```sql
-- 陷阱 1：對分區欄位進行函數操作
WHERE EXTRACT(YEAR FROM order_date) = 2024  -- ❌ 無法使用分區裁剪
WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01'  -- ✅ 可以

-- 陷阱 2：隱式類型轉換
WHERE order_date = 20240101  -- ❌ 整數，需要轉換
WHERE order_date = '2024-01-01'  -- ✅ 字符串自動轉換為 DATE

-- 陷阱 3：OR 條件
WHERE order_date = '2024-01-01' OR amount > 1000  -- ❌ 可能全表掃描
WHERE order_date = '2024-01-01' AND amount > 1000  -- ✅ 使用分區裁剪
```

💡 **關鍵洞察**：分區表的價值在於「分區裁剪」（Partition Pruning）。查詢必須包含分區欄位的過濾條件才能發揮作用。

## 6.2 時間分區表遷移

現在讓我們實際遷移一個時間分區表。

### 6.2.1 原始 SQL 分析

以下是一個真實的時間分區表範例（已脫敏）：

```sql
-- ===================================
-- 表名：user_daily_transactions
-- 用途：用戶每日交易記錄
-- 分區：按 transaction_date（DATE）
-- 更新策略：每日增量更新（只更新昨天的分區）
-- ===================================

CREATE OR REPLACE TABLE `m3-project.analytics.user_daily_transactions`
PARTITION BY transaction_date  ‹1›
OPTIONS(
    partition_expiration_days = 365,  ‹2›
    require_partition_filter = true
)
AS
SELECT
    user_id,
    transaction_id,
    transaction_timestamp,
    DATE(transaction_timestamp) as transaction_date,  ‹3›
    amount,
    payment_method,
    status
FROM `m3-project.raw_data.transactions`
WHERE DATE(transaction_timestamp) = CURRENT_DATE() - 1  ‹4›
  AND status = 'completed'
```

**關鍵特徵分析**：

**‹1› PARTITION BY transaction_date**
- 使用 DATE 類型欄位分區
- 粒度為「天」
- transaction_date 必須是 SELECT 的欄位之一

**‹2› partition_expiration_days = 365**
- 自動刪除 365 天前的分區
- 節省儲存成本
- 符合業務需求（只保留一年數據）

**‹3› 分區欄位的計算**
- 從 TIMESTAMP 類型的 transaction_timestamp 提取 DATE
- 分區欄位必須出現在 SELECT 中

**‹4› 增量更新邏輯**
- 只處理昨天的數據（`CURRENT_DATE() - 1`）
- 每次執行只替換一個分區
- 不影響其他分區的數據

### 6.2.2 dbt 遷移策略

對於時間分區表，dbt 提供了兩種策略：

**策略 1：Table materialization + 分區配置**（完全重建）

適用於：
- 每次重建整個表
- 數據量不太大（< 1 億行）
- 邏輯簡單

**策略 2：Incremental materialization**（增量更新）

適用於：
- 只更新特定分區
- 數據量很大（> 1 億行）
- 需要保留歷史分區

在我們的案例中，原始 SQL 使用增量更新邏輯（只處理昨天的數據），因此使用 **Incremental materialization**。

### 6.2.3 Step 1: 建立 dbt Incremental 模型

創建 `models/marts/user_daily_transactions.sql`：

```sql
-- models/marts/user_daily_transactions.sql
-- ===================================
-- 表名：user_daily_transactions
-- 用途：用戶每日交易記錄
-- 分區：按 transaction_date（DATE）
-- 更新策略：每日增量更新（只更新昨天的分區）
-- ===================================

{{
    config(
        materialized='incremental',  ‹1›
        partition_by={  ‹2›
            'field': 'transaction_date',
            'data_type': 'date',
            'granularity': 'day'
        },
        cluster_by=['user_id', 'payment_method'],  ‹3›
        incremental_strategy='insert_overwrite',  ‹4›
        partition_expiration_days=365,  ‹5›
        require_partition_filter=true
    )
}}

SELECT
    user_id,
    transaction_id,
    transaction_timestamp,
    DATE(transaction_timestamp) as transaction_date,  ‹6›
    amount,
    payment_method,
    status
FROM {{ source('raw_data', 'transactions') }}
WHERE DATE(transaction_timestamp) = CURRENT_DATE() - 1
  AND status = 'completed'

{% if is_incremental() %}  ‹7›
    -- 在增量模式下，只處理新數據
    AND DATE(transaction_timestamp) > (
        SELECT MAX(transaction_date)
        FROM {{ this }}
    )
{% endif %}
```

讓我們逐一解釋關鍵配置：

**‹1› materialized='incremental'**
- 使用增量物化策略
- 首次運行：建立完整表
- 後續運行：只更新新數據

**‹2› partition_by 配置**
```python
partition_by={
    'field': 'transaction_date',  # 分區欄位名稱
    'data_type': 'date',           # 欄位數據類型
    'granularity': 'day'           # 分區粒度（hour/day/month/year）
}
```

**‹3› cluster_by（額外優化）**
- 在分區內按 user_id 和 payment_method 排序
- 進一步提升查詢性能
- 可選，但強烈推薦

**‹4› incremental_strategy='insert_overwrite'**
- 使用「插入覆蓋」策略
- 替換整個分區的數據
- 適合每日完全重建分區的場景

**‹5› partition_expiration_days 和 require_partition_filter**
- 直接在 dbt 配置中設定 BigQuery 表選項
- 與原始 SQL 的 OPTIONS 對應

**‹6› 分區欄位**
- 必須出現在 SELECT 中
- 與原始 SQL 完全一致

**‹7› is_incremental() 區塊**
- dbt 的 Jinja 條件判斷
- 首次運行時為 False，執行完整查詢
- 增量運行時為 True，加入增量過濾條件

### 6.2.4 理解 Incremental 策略

dbt 的 incremental materialization 運作流程：

**首次運行**（`dbt run -s user_daily_transactions`）：

```mermaid
graph LR
    A[執行完整 SELECT] --> B[創建分區表]
    B --> C[插入所有數據]
```

**增量運行**（再次執行 `dbt run -s user_daily_transactions`）：

```mermaid
graph LR
    A[檢查 is_incremental = True] --> B[執行 SELECT<br/>with 增量條件]
    B --> C[使用 insert_overwrite<br/>替換相應分區]
```

**insert_overwrite 策略的行為**：

```sql
-- 假設今天是 2024-01-02，昨天是 2024-01-01

-- dbt 實際執行（簡化版）：
-- 1. 查詢新數據
WITH new_data AS (
    SELECT ...
    FROM source
    WHERE DATE(timestamp) = '2024-01-01'
)
-- 2. 替換分區
INSERT INTO target
PARTITION (transaction_date = '2024-01-01')
OVERWRITE
SELECT * FROM new_data
```

結果：
- ✅ 2024-01-01 分區的數據被完全替換
- ✅ 其他分區（2023-12-31, 2024-01-02, ...）不受影響
- ✅ 保證分區數據的一致性

### 6.2.5 Step 2: Schema 定義

創建 `models/marts/schema.yml`：

```yaml
# models/marts/schema.yml
version: 2

models:
  - name: user_daily_transactions
    description: |
      用戶每日交易記錄（分區表）

      **分區配置**：
      - 分區欄位：transaction_date（DATE）
      - 分區粒度：每日
      - 過期時間：365 天

      **更新策略**：
      - 每日增量更新
      - 只替換昨天的分區
      - 使用 insert_overwrite 策略

      **性能優化**：
      - 按 user_id 和 payment_method cluster
      - 強制要求分區過濾條件

    columns:
      - name: user_id
        description: "用戶唯一識別碼"
        tests:
          - not_null
          - relationships:
              to: source('raw_data', 'users')
              field: user_id

      - name: transaction_id
        description: "交易唯一識別碼"
        tests:
          - unique
          - not_null

      - name: transaction_timestamp
        description: "交易時間戳記（精確到秒）"
        tests:
          - not_null

      - name: transaction_date  # 分區欄位
        description: "交易日期（從 transaction_timestamp 提取，用於分區）"
        tests:
          - not_null

      - name: amount
        description: "交易金額（單位：元）"
        tests:
          - not_null

      - name: payment_method
        description: "支付方式（credit_card/debit_card/paypal/bank_transfer）"
        tests:
          - not_null
          - accepted_values:
              values: ['credit_card', 'debit_card', 'paypal', 'bank_transfer']

      - name: status
        description: "交易狀態（全部為 completed，因為只導入已完成交易）"
        tests:
          - accepted_values:
              values: ['completed']
```

💡 **文檔最佳實踐**：對於分區表，應在模型描述中明確說明：
- 分區配置（欄位、粒度、過期時間）
- 更新策略（全量/增量）
- 性能優化（clustering）

### 6.2.6 Step 3: 執行與驗證

**首次運行（建立表）**：

```bash
dbt run -s user_daily_transactions --full-refresh
```

`--full-refresh` 標誌強制重建整個表（忽略增量邏輯）。

**預期輸出**：

```
Running with dbt=1.5.0
Found 1 model, 7 tests

1 of 1 START sql incremental model analytics.user_daily_transactions ... [RUN]
1 of 1 OK created sql incremental model analytics.user_daily_transactions  [CREATE TABLE (15234 rows, 1.2GB) in 45.3s]

Finished running 1 incremental model in 0 hours 0 minutes and 47 seconds.

Completed successfully
```

**增量運行（更新分區）**：

第二天再次執行（不使用 --full-refresh）：

```bash
dbt run -s user_daily_transactions
```

**預期輸出**：

```
1 of 1 START sql incremental model analytics.user_daily_transactions ... [RUN]
1 of 1 OK created sql incremental model analytics.user_daily_transactions  [INSERT OVERWRITE (543 rows) in 8.2s]

Completed successfully
```

注意：
- 第一次是 `CREATE TABLE`
- 第二次是 `INSERT OVERWRITE`
- 第二次只處理新分區，時間大幅縮短（45s → 8s）

**驗證分區配置**：

在 BigQuery Console 執行：

```sql
-- 檢查分區信息
SELECT
    partition_id,
    total_rows,
    total_logical_bytes
FROM `m3-project.analytics.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name = 'user_daily_transactions'
ORDER BY partition_id DESC
LIMIT 10;
```

預期輸出：

```
partition_id    total_rows  total_logical_bytes
2024-01-02      543         87234
2024-01-01      521         84123
2023-12-31      498         80234
...
```

每個日期一個分區 ✅

### 6.2.7 時間分區的常見變體

**變體 1：按小時分區（實時數據）**

```sql
{{
    config(
        materialized='incremental',
        partition_by={
            'field': 'event_timestamp',
            'data_type': 'timestamp',  ‹1›
            'granularity': 'hour'  ‹2›
        },
        incremental_strategy='insert_overwrite'
    )
}}

SELECT
    event_id,
    event_timestamp,  -- TIMESTAMP 類型
    event_type,
    user_id
FROM {{ source('raw_data', 'events') }}
WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
```

**‹1›** data_type 為 'timestamp'（不是 'date'）
**‹2›** 粒度為 'hour'

適用場景：
- 實時日誌數據
- 事件追蹤
- IoT 數據流

**變體 2：按月分區（歷史數據）**

```sql
{{
    config(
        materialized='table',  ‹1›
        partition_by={
            'field': 'report_month',
            'data_type': 'date',
            'granularity': 'month'
        }
    )
}}

SELECT
    DATE_TRUNC(transaction_date, MONTH) as report_month,  ‹2›
    region,
    SUM(amount) as total_amount
FROM {{ ref('user_daily_transactions') }}
GROUP BY 1, 2
```

**‹1›** 使用 table materialization（每次完全重建）
**‹2›** 使用 DATE_TRUNC 提取月份

適用場景：
- 月度報表
- 長期存檔數據
- 分析較大時間跨度的趨勢

**變體 3：攝入時間分區**

```sql
{{
    config(
        materialized='incremental',
        partition_by={
            'field': '_PARTITIONDATE',  ‹1›
            'data_type': 'date',
            'granularity': 'day'
        }
    )
}}

SELECT
    log_id,
    message,
    severity,
    timestamp
FROM {{ source('raw_data', 'application_logs') }}
WHERE _PARTITIONDATE = CURRENT_DATE() - 1
```

**‹1›** 使用 BigQuery 內建的 `_PARTITIONDATE` 偽欄位

適用場景：
- 日誌數據（沒有明確的業務時間欄位）
- 數據攝入時間就是分區維度

## 6.3 整數範圍分區表遷移

整數範圍分區較少見，但在某些場景下非常有用。

### 6.3.1 整數分區的使用場景

**典型場景 1：用戶 ID 分區**

當你需要按用戶查詢數據，且用戶數量巨大時：

```sql
-- 查詢特定用戶的數據
SELECT *
FROM user_activities
WHERE user_id = 12345
  AND activity_date >= '2024-01-01'
```

如果只按 activity_date 分區，還是要掃描很多分區。如果加上 user_id 範圍分區，可以進一步裁剪數據。

**典型場景 2：產品 ID、訂單 ID 分區**

類似用戶 ID，任何有序的整數 ID 都可以用於分區。

### 6.3.2 原始 SQL 分析

以下是一個整數分區表範例：

```sql
-- ===================================
-- 表名：user_lifetime_metrics
-- 用途：用戶生命週期指標
-- 分區：按 user_id（整數範圍分區）
-- 範圍：每 10,000 個 user_id 一個分區
-- ===================================

CREATE OR REPLACE TABLE `m3-project.analytics.user_lifetime_metrics`
PARTITION BY RANGE_BUCKET(
    user_id,
    GENERATE_ARRAY(0, 1000000, 10000)  ‹1›
)
CLUSTER BY registration_date  ‹2›
AS
SELECT
    user_id,
    registration_date,
    total_orders,
    total_amount_spent,
    last_order_date,
    user_segment
FROM `m3-project.raw_data.user_summary`
WHERE is_active = true
```

**‹1› RANGE_BUCKET 配置**

```sql
RANGE_BUCKET(user_id, GENERATE_ARRAY(0, 1000000, 10000))
```

解析：
- `user_id`：分區欄位
- `GENERATE_ARRAY(0, 1000000, 10000)`：生成範圍邊界 [0, 10000, 20000, ..., 1000000]
- 結果：創建 100 個分區
  - 分區 0：user_id 0-9999
  - 分區 1：user_id 10000-19999
  - ...
  - 分區 99：user_id 990000-999999

**‹2› CLUSTER BY**

在分區內按 registration_date 排序，進一步優化查詢。

### 6.3.3 dbt 遷移實作

創建 `models/marts/user_lifetime_metrics.sql`：

```sql
-- models/marts/user_lifetime_metrics.sql
-- ===================================
-- 表名：user_lifetime_metrics
-- 用途：用戶生命週期指標
-- 分區：按 user_id（整數範圍分區）
-- ===================================

{{
    config(
        materialized='table',
        partition_by={
            'field': 'user_id',
            'data_type': 'int64',  ‹1›
            'range': {  ‹2›
                'start': 0,
                'end': 1000000,
                'interval': 10000
            }
        },
        cluster_by=['registration_date']
    )
}}

SELECT
    user_id,
    registration_date,
    total_orders,
    total_amount_spent,
    last_order_date,
    user_segment
FROM {{ source('raw_data', 'user_summary') }}
WHERE is_active = true
```

**‹1› data_type: 'int64'**

指定為整數類型分區。

**‹2› range 配置**

```python
'range': {
    'start': 0,       # 起始值
    'end': 1000000,   # 結束值
    'interval': 10000 # 每個分區的範圍
}
```

對應原始 SQL 的 `GENERATE_ARRAY(0, 1000000, 10000)`。

### 6.3.4 整數分區的查詢優化

**✅ 好的查詢（利用分區裁剪）**：

```sql
SELECT *
FROM user_lifetime_metrics
WHERE user_id BETWEEN 10000 AND 19999  -- 只掃描分區 1
  AND total_orders > 10
```

**✅ 好的查詢（單一 user_id）**：

```sql
SELECT *
FROM user_lifetime_metrics
WHERE user_id = 12345  -- 只掃描分區 1（10000-19999）
```

**❌ 不好的查詢（全表掃描）**：

```sql
SELECT *
FROM user_lifetime_metrics
WHERE total_orders > 10  -- 沒有 user_id 條件，掃描所有分區
```

### 6.3.5 選擇合適的分區範圍

選擇 `interval` 時的考量：

| interval 大小 | 分區數量 | 優點 | 缺點 | 適用場景 |
|--------------|---------|------|------|---------|
| 1,000 | 1,000 個 | 精細分區，高效裁剪 | 分區過多，管理複雜 | user_id 範圍小（< 100 萬）|
| 10,000 | 100 個 | 平衡的分區數量 | 每個分區稍大 | user_id 範圍中等（100 萬-1000 萬）|
| 100,000 | 10 個 | 分區少，易管理 | 裁剪效果較弱 | user_id 範圍大（> 1000 萬）|

💡 **經驗法則**：
- 分區數量控制在 10-1000 之間
- 每個分區的數據量在 100MB-10GB 之間
- 根據查詢模式調整（經常查詢單一用戶 vs 查詢範圍）

### 6.3.6 整數分區 + 時間分區（組合分區）

BigQuery 不支援多欄位分區，但可以組合 partition + cluster：

```sql
{{
    config(
        materialized='incremental',
        partition_by={
            'field': 'activity_date',  ‹1›
            'data_type': 'date',
            'granularity': 'day'
        },
        cluster_by=['user_id'],  ‹2›
        incremental_strategy='insert_overwrite'
    )
}}

SELECT
    user_id,
    activity_date,
    activity_type,
    activity_count
FROM {{ source('raw_data', 'user_activities') }}
WHERE activity_date = CURRENT_DATE() - 1
```

**‹1›** 主分區：按日期
**‹2›** 次級排序：在分區內按 user_id cluster

查詢優化效果：

```sql
SELECT *
FROM user_activities
WHERE activity_date = '2024-01-01'  -- 分區裁剪到一個分區
  AND user_id = 12345               -- cluster 裁剪到相關區塊

-- 雙重優化，性能最佳！
```

## 6.4 分區表測試與驗證

分區表的遷移不僅要保證邏輯正確，還要驗證分區配置是否生效。

### 6.4.1 驗證檢查清單

**1. 分區結構驗證**

```sql
-- 查詢分區元數據
SELECT
    partition_id,
    total_rows,
    total_logical_bytes / (1024*1024) as size_mb
FROM `m3-project.analytics.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name = 'user_daily_transactions'
ORDER BY partition_id DESC
LIMIT 20;
```

檢查項目：
- [ ] 分區數量符合預期
- [ ] 每個分區的 partition_id 正確（日期格式或整數範圍）
- [ ] 分區大小合理（沒有過大或過小的分區）

**2. 分區裁剪驗證**

使用 `EXPLAIN` 檢查查詢是否使用分區裁剪：

```sql
-- 在 BigQuery Console 執行
EXPLAIN
SELECT COUNT(*)
FROM `m3-project.analytics.user_daily_transactions`
WHERE transaction_date = '2024-01-01';
```

查看執行計劃中的 "partitions scanned"：

```
Query Statistics:
- Partitions scanned: 1 / 365
- Bytes processed: 87 KB / 1.2 GB
```

✅ 只掃描 1 個分區，說明分區裁剪生效！

**3. 性能對比測試**

對比原始表和 dbt 模型的查詢性能：

```sql
-- 測試查詢
SET @@query_label = 'partition_test_original';
SELECT COUNT(*), SUM(amount)
FROM `m3-project.analytics.user_daily_transactions_original`  -- 原始表
WHERE transaction_date BETWEEN '2024-01-01' AND '2024-01-07';

SET @@query_label = 'partition_test_dbt';
SELECT COUNT(*), SUM(amount)
FROM `m3-project.analytics.user_daily_transactions`  -- dbt 模型
WHERE transaction_date BETWEEN '2024-01-01' AND '2024-01-07';
```

在 BigQuery Console 的 "Query History" 中對比：
- Bytes processed（掃描數據量）
- Execution time（執行時間）
- Slot time（計算資源消耗）

應該相近或更優 ✅

**4. 數據一致性驗證**

確保遷移後數據與原始表一致：

```sql
-- Row count 比對
SELECT
    'original' as source,
    transaction_date,
    COUNT(*) as row_count,
    SUM(amount) as total_amount
FROM `m3-project.analytics.user_daily_transactions_original`
GROUP BY transaction_date
ORDER BY transaction_date

EXCEPT DISTINCT

SELECT
    'dbt' as source,
    transaction_date,
    COUNT(*) as row_count,
    SUM(amount) as total_amount
FROM `m3-project.analytics.user_daily_transactions`
GROUP BY transaction_date
ORDER BY transaction_date;
```

如果沒有結果返回，說明數據完全一致 ✅

### 6.4.2 自動化驗證腳本

建立 Python 腳本自動驗證分區配置：

```python
# scripts/validate_partitions.py
"""
驗證 dbt 模型的分區配置
"""

from google.cloud import bigquery
import sys

def validate_partition_config(project_id, dataset_id, table_id, expected_config):
    """
    驗證分區配置是否符合預期

    Args:
        expected_config: {
            'type': 'time' or 'range',
            'field': 'partition_field_name',
            'granularity': 'DAY' or 'HOUR' etc (for time partition)
        }
    """
    client = bigquery.Client(project=project_id)
    table = client.get_table(f"{project_id}.{dataset_id}.{table_id}")

    # 檢查是否有分區
    if table.time_partitioning is None and table.range_partitioning is None:
        print(f"❌ 表 {table_id} 沒有分區配置")
        return False

    # 驗證時間分區
    if expected_config['type'] == 'time':
        if table.time_partitioning is None:
            print(f"❌ 預期時間分區，但表沒有時間分區配置")
            return False

        tp = table.time_partitioning
        if tp.field != expected_config['field']:
            print(f"❌ 分區欄位不符：預期 {expected_config['field']}，實際 {tp.field}")
            return False

        if tp.type_ != expected_config.get('granularity', 'DAY'):
            print(f"❌ 分區粒度不符：預期 {expected_config['granularity']}，實際 {tp.type_}")
            return False

        print(f"✅ 時間分區配置正確")
        print(f"   - 欄位: {tp.field}")
        print(f"   - 粒度: {tp.type_}")
        print(f"   - 過期天數: {tp.expiration_ms / (1000*60*60*24) if tp.expiration_ms else '無'}")
        return True

    # 驗證整數分區
    elif expected_config['type'] == 'range':
        if table.range_partitioning is None:
            print(f"❌ 預期整數分區，但表沒有整數分區配置")
            return False

        rp = table.range_partitioning
        if rp.field != expected_config['field']:
            print(f"❌ 分區欄位不符：預期 {expected_config['field']}，實際 {rp.field}")
            return False

        print(f"✅ 整數分區配置正確")
        print(f"   - 欄位: {rp.field}")
        print(f"   - 範圍: {rp.range_.start} to {rp.range_.end}, interval {rp.range_.interval}")
        return True

# 使用範例
if __name__ == '__main__':
    # 驗證時間分區表
    validate_partition_config(
        'm3-project',
        'analytics',
        'user_daily_transactions',
        {
            'type': 'time',
            'field': 'transaction_date',
            'granularity': 'DAY'
        }
    )

    # 驗證整數分區表
    validate_partition_config(
        'm3-project',
        'analytics',
        'user_lifetime_metrics',
        {
            'type': 'range',
            'field': 'user_id'
        }
    )
```

執行驗證：

```bash
python scripts/validate_partitions.py
```

預期輸出：

```
✅ 時間分區配置正確
   - 欄位: transaction_date
   - 粒度: DAY
   - 過期天數: 365.0

✅ 整數分區配置正確
   - 欄位: user_id
   - 範圍: 0 to 1000000, interval 10000
```

### 6.4.3 成本分析

分區表的一大優勢是降低成本。讓我們驗證實際節省：

```python
# scripts/analyze_query_cost.py
"""
分析查詢成本節省
"""

from google.cloud import bigquery

def estimate_query_cost(sql, table_name):
    """
    估算查詢成本（不實際執行）
    """
    client = bigquery.Client()

    # 使用 dry_run 估算
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    query_job = client.query(sql, job_config=job_config)

    # BigQuery 計費：$5 per TB
    bytes_processed = query_job.total_bytes_processed
    cost = (bytes_processed / (1024**4)) * 5  # 轉換為 TB 並計算成本

    print(f"表: {table_name}")
    print(f"掃描數據: {bytes_processed / (1024**3):.2f} GB")
    print(f"估算成本: ${cost:.4f}")
    print()

    return bytes_processed, cost

# 對比原始表和分區表
original_sql = """
SELECT COUNT(*), SUM(amount)
FROM `m3-project.analytics.transactions_original`
WHERE DATE(timestamp) = '2024-01-01'
"""

partitioned_sql = """
SELECT COUNT(*), SUM(amount)
FROM `m3-project.analytics.user_daily_transactions`
WHERE transaction_date = '2024-01-01'
"""

bytes_original, cost_original = estimate_query_cost(original_sql, "原始表（無分區）")
bytes_partitioned, cost_partitioned = estimate_query_cost(partitioned_sql, "分區表")

# 計算節省
savings_bytes = bytes_original - bytes_partitioned
savings_cost = cost_original - cost_partitioned
savings_pct = (savings_bytes / bytes_original) * 100

print(f"節省數據掃描: {savings_bytes / (1024**3):.2f} GB ({savings_pct:.1f}%)")
print(f"節省成本: ${savings_cost:.4f}")
```

預期輸出：

```
表: 原始表（無分區）
掃描數據: 1250.45 GB
估算成本: $0.0061

表: 分區表
掃描數據: 3.42 GB
估算成本: $0.00002

節省數據掃描: 1247.03 GB (99.7%)
節省成本: $0.00608
```

對於單一查詢節省不多，但如果每天執行 1000 次查詢，一年節省：

```
$0.00608 × 1000 queries/day × 365 days = $2,219 / 年
```

非常可觀！

## 本章總結

在本章中，我們完成了分區表遷移的完整實踐：

✅ **理解了 BigQuery 分區表的原理**，包括四種分區類型和使用場景
✅ **掌握了時間分區表的遷移**，使用 dbt 的 incremental materialization
✅ **學習了整數範圍分區**，處理 user_id 等整數欄位分區
✅ **建立了完整的驗證流程**，包括分區結構、性能、成本分析

### 核心收穫

**關於分區表**：
- 分區是 BigQuery 最重要的性能優化技術
- 正確配置可以將查詢成本降低 90%+
- 必須在查詢中使用分區過濾條件才能發揮作用

**關於 dbt 遷移**：
- 時間分區使用 `partition_by` 配置
- 增量更新使用 `materialized='incremental'` + `insert_overwrite`
- 整數分區使用 `range` 配置

**關於驗證**：
- 不僅要驗證邏輯正確，還要驗證分區配置生效
- 使用 EXPLAIN 檢查分區裁剪
- 對比成本確認優化效果

### 更新遷移手冊

我們將分區表模式加入遷移手冊 v2.0：

```markdown
## 5-b. 建立 dbt 模型的 SQL 檔案（時間分區表版）

### 配置 partition_by

時間分區配置：
```python
{{
    config(
        materialized='incremental',
        partition_by={
            'field': 'partition_field_name',
            'data_type': 'date',  # or 'timestamp'
            'granularity': 'day'  # or 'hour', 'month', 'year'
        },
        incremental_strategy='insert_overwrite'
    )
}}
```

### 增量邏輯

必須包含 is_incremental() 區塊：
```sql
{% if is_incremental() %}
    AND date_field > (SELECT MAX(date_field) FROM {{ this }})
{% endif %}
```

### 檢查清單

- [ ] partition_by 配置正確
- [ ] 分區欄位出現在 SELECT 中
- [ ] 增量邏輯正確（if is_incremental）
- [ ] incremental_strategy 設為 'insert_overwrite'
```

### 實戰統計

經過本章實踐，我們的遷移進度：

| 模式類型 | 數量 | 已遷移 | 成功率 | 狀態 |
|---------|------|-------|-------|------|
| 每日完全更新 | 30 | 7 | 100% | ✅ 穩定 |
| 分區表 | 10 | 2 | 100% | ✅ 穩定 |
| 分片表 | 10 | 0 | - | ⏳ 待處理 |
| **總計** | **50** | **9** | **100%** | **18% 完成** |

### 下一章預告

在第 7 章，我們將處理最複雜的場景：**分片資料表（Sharded Tables）**。

分片表的特點：
- 使用日期後綴命名（table_20240101, table_20240102, ...）
- 是舊的數據組織方式（BigQuery 早期沒有分區功能）
- 需要遷移為分區表（現代最佳實踐）
- 涉及歷史數據回填

我們將：
- 理解分片表的歷史背景
- 設計分片到分區的轉換策略
- 處理歷史數據遷移
- 建立回填腳本

這將是技術難度最高的一章。準備好了嗎？讓我們繼續！

---

**本章產出物清單**：
- ✅ 分區表完整分析（4 種類型）
- ✅ 時間分區遷移完整範例
- ✅ 整數分區遷移範例
- ✅ 自動化驗證腳本（分區配置、性能、成本）
- ✅ 遷移手冊 v2.0（新增分區表章節）

**下一步行動**：
1. 遷移剩餘的分區表（約 8 個）
2. 驗證所有分區配置
3. 準備進入第 7 章：分片表遷移
