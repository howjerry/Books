# 第 3 章：環境設置與第一次嘗試

在前兩章中，我們理解了大規模遷移的挑戰，也掌握了 dbt 和 BigQuery 的核心概念。現在，是時候動手實作了。

在本章中，我們將跟隨坂元的腳步，建立完整的開發環境，並完成第一次 SQL 到 dbt 的遷移嘗試。但這不是一個完美的成功故事——我們將誠實地記錄第一次嘗試的失敗，分析問題，並從中學習。

到本章結束時，你將：

- **建立完整的 dbt 開發環境**：從安裝到配置，一步步設置
- **完成第一個 SQL 的遷移嘗試**：將實際的 SQL 檔案轉換為 dbt 模型
- **發現並分析問題**：註解遺失、邏輯改變、Schema 不完整等
- **理解為何簡單提示詞不夠**：需要更系統化的方法
- **獲得關鍵洞察**：遷移手冊 概念的誕生

讓我們開始這趟實戰之旅。

---

## 3.1 開發環境設置

在開始遷移前，我們需要建立一個完整的開發環境。這個過程可能需要 1-2 小時，但只需要做一次。

### 環境需求檢查

首先，確認你的系統滿足以下需求：

**必備**：
- **Python 3.8+**：dbt 需要 Python 環境
- **Git**：版本控制
- **終端機**：命令列介面（Mac/Linux 內建，Windows 用 PowerShell 或 WSL）
- **文字編輯器**：VS Code、Sublime Text 等

**可選但推薦**：
- **Google Cloud 帳號**：用於 BigQuery（有免費沙箱）
- **Claude Code 或 Claude API**：AI 協作工具

讓我們逐步檢查和設置。

### 步驟 1：安裝 Python 與 pip

**檢查 Python 版本**：

```bash
$ python3 --version
# 應該看到：Python 3.8.x 或更高

$ pip3 --version
# 應該看到：pip 20.x.x 或更高
```

**如果 Python 版本過舊或未安裝**：

```bash
# macOS（使用 Homebrew）
$ brew install python@3.10

# Ubuntu/Debian
$ sudo apt update
$ sudo apt install python3.10 python3-pip

# Windows
# 從 python.org 下載並安裝 Python 3.10+
```

### 步驟 2：建立 Python 虛擬環境

**為什麼需要虛擬環境？**

虛擬環境隔離專案的 Python 套件，避免不同專案間的衝突。這是 Python 開發的最佳實踐。

**建立虛擬環境**：

```bash
# 建立專案目錄
$ mkdir ~/dbt-migration-project
$ cd ~/dbt-migration-project

# 建立虛擬環境
$ python3 -m venv venv  # ‹1›

# 啟動虛擬環境
# macOS/Linux
$ source venv/bin/activate  # ‹2›

# Windows
$ venv\Scripts\activate

# 確認啟動成功（提示符前會有 (venv)）
(venv) $
```

- **‹1›** 建立名為 `venv` 的虛擬環境目錄
- **‹2›** 啟動後，所有 pip install 都只安裝到這個環境中

### 步驟 3：安裝 dbt-bigquery

**安裝 dbt 與 BigQuery 適配器**：

```bash
(venv) $ pip install dbt-bigquery  # ‹1›

# 安裝可能需要 2-5 分鐘
# 會同時安裝 dbt-core 和 BigQuery 相關依賴

# 驗證安裝
(venv) $ dbt --version  # ‹2›
```

- **‹1›** dbt-bigquery 包含 dbt-core 和 BigQuery 適配器
- **‹2›** 應該看到類似輸出：

```
installed version: 1.7.4
   latest version: 1.7.4

Up to date!

Plugins:
  - bigquery: 1.7.2
```

💡 **提示**：如果看到版本號，表示安裝成功！

### 步驟 4：設置 BigQuery 認證

要讓 dbt 連接 BigQuery，需要設置 Google Cloud 認證。

**選項 A：使用服務帳號（推薦用於生產）**

```bash
# 1. 在 Google Cloud Console 建立服務帳號
#    https://console.cloud.google.com/iam-admin/serviceaccounts

# 2. 下載 JSON 金鑰檔案（例如：my-project-key.json）

# 3. 設定環境變數
$ export GOOGLE_APPLICATION_CREDENTIALS="/path/to/my-project-key.json"

# 可以加入 ~/.bashrc 或 ~/.zshrc 使其永久生效
```

**選項 B：使用 OAuth（推薦用於開發）**

```bash
# 安裝 gcloud CLI
$ brew install google-cloud-sdk  # macOS
# 或從 https://cloud.google.com/sdk/docs/install 下載

# 登入 Google 帳號
$ gcloud auth application-default login  # ‹1›

# 會開啟瀏覽器，完成 OAuth 認證
# 認證成功後，credentials 會存在本地
```

- **‹1›** 這個命令會為應用程式（包括 dbt）設置預設認證

**驗證認證**：

```bash
# 測試 BigQuery 連接
$ bq ls  # ‹1›

# 應該看到你的 BigQuery 資料集列表
# 如果看到錯誤，檢查認證設定
```

- **‹1›** `bq` 是 BigQuery 命令列工具，隨 gcloud SDK 安裝

### 步驟 5：初始化 dbt 專案

現在建立你的第一個 dbt 專案。

```bash
(venv) $ dbt init my_dbt_project  # ‹1›

# dbt 會詢問一些問題：
# [1] bigquery
#
# Which database would you like to use?
# [1] bigquery
#
# Enter a number: 1

# 選擇認證方式
# [1] oauth
# [2] service_account
#
# Desired authentication method option: 1  # ‹2›

# 輸入 GCP 專案 ID
# project (GCP project id): my-gcp-project  # ‹3›

# 輸入資料集名稱
# dataset (the name of your dbt dataset): dbt_dev  # ‹4›

# 輸入資料位置
# location (GCP location, e.g. US, EU): US

# 完成！
```

- **‹1›** 建立名為 `my_dbt_project` 的 dbt 專案
- **‹2›** 選擇 OAuth 認證（適合開發）
- **‹3›** 替換為你的實際 GCP 專案 ID
- **‹4›** dbt 會在這個資料集中建立開發表

**專案結構**：

```bash
$ cd my_dbt_project
$ tree -L 2  # macOS/Linux
```

```
my_dbt_project/
├── README.md
├── analyses/
├── dbt_project.yml      # ‹1› 專案配置檔案
├── macros/
├── models/              # ‹2› 模型目錄
│   └── example/
├── seeds/
├── snapshots/
├── tests/
└── profiles.yml         # ‹3› 連線配置（在 ~/.dbt/ 目錄）
```

- **‹1›** 專案設定：名稱、版本、模型路徑等
- **‹2›** 這裡放置所有 dbt 模型（.sql 檔案）
- **‹3›** 實際位置在 `~/.dbt/profiles.yml`

### 步驟 6：測試 dbt 連接

執行範例模型，確認一切正常。

```bash
# 測試連接
(venv) $ dbt debug  # ‹1›

# 應該看到所有檢查都是 OK
```

- **‹1›** 這個命令檢查連接設定

**預期輸出**：

```
Connection test: [OK connection ok]

All checks passed!
```

如果看到錯誤，檢查：
- BigQuery 認證是否正確
- `profiles.yml` 中的專案 ID 是否正確
- 網路連接是否正常

**執行範例模型**：

```bash
# 執行內建的範例模型
(venv) $ dbt run  # ‹1›

# 應該看到：
# Running with dbt=1.7.4
# Found 2 models, 4 tests...
#
# Completed successfully
```

- **‹1›** 執行 `models/example/` 中的範例模型

**查看結果**：

```bash
# 或在 BigQuery Console 查看
# 專案 > dbt_dev 資料集 > 應該看到兩個表
```

恭喜！環境設置完成。

### 步驟 7：安裝 Claude Code（可選）

如果你想完整複製 M3 的 AI 協作體驗，安裝 Claude Code。

**選項 A：Claude Code Desktop**

```bash
# 從官網下載
https://claude.ai/code

# macOS
# 下載 .dmg 並安裝

# Windows
# 下載 .exe 並安裝

# Linux
# 下載 .AppImage 並執行
```

**選項 B：使用 Claude API**

如果你是開發者，可以直接使用 API：

```python
# 安裝 anthropic SDK
pip install anthropic

# 設定 API 金鑰
export ANTHROPIC_API_KEY="your-api-key"
```

**選項 C：使用 Web 版 Claude**

最簡單的方式：直接在 https://claude.ai 使用，手動複製貼上代碼。

### 環境設置檢查清單

完成以上步驟後，確認：

- [ ] Python 3.8+ 已安裝
- [ ] 虛擬環境已建立並啟動
- [ ] dbt-bigquery 已安裝（`dbt --version` 成功）
- [ ] BigQuery 認證已設置（`bq ls` 成功）
- [ ] dbt 專案已初始化
- [ ] dbt debug 顯示所有檢查 OK
- [ ] dbt run 成功執行範例模型
- [ ] Claude Code 或其他 AI 工具已準備（可選）

如果全部打勾，你已經準備好開始遷移了！

---

## 3.2 創建遷移專案結構

在開始實際遷移前，我們需要組織專案結構。這個結構將貫穿整個遷移過程。

### M3 的專案結構

讓我們模仿 M3 的做法，建立一個清晰的專案結構。

```bash
# 在 dbt 專案內建立目錄
$ cd my_dbt_project

# 建立 sources 目錄（存放原始 SQL）
$ mkdir -p sources/original_sql

# 建立 models 分層結構
$ mkdir -p models/staging
$ mkdir -p models/intermediate
$ mkdir -p models/marts

# 建立文檔目錄
$ mkdir -p docs

# 建立驗證腳本目錄
$ mkdir -p scripts/validation
```

**完整結構**：

```
my_dbt_project/
├── dbt_project.yml
├── models/
│   ├── staging/          # 第一層：清理和標準化
│   │   ├── sources.yml  # ‹1› Sources 定義
│   │   └── stg_*.sql
│   ├── intermediate/     # 第二層：業務邏輯
│   │   └── int_*.sql
│   └── marts/           # 第三層：最終產出
│       ├── schema.yml   # ‹2› Models 定義
│       └── *.sql
├── sources/
│   └── original_sql/    # ‹3› 原始 SQL 檔案
│       └── *.sql
├── docs/
│   └── migration_log.md # ‹4› 遷移記錄
└── scripts/
    └── validation/      # ‹5› 驗證腳本
        └── *.py
```

- **‹1›** 所有外部資料來源的定義
- **‹2›** 所有 dbt 模型的 Schema 和測試定義
- **‹3›** 保留原始 SQL 以便對照
- **‹4›** 記錄每次遷移的經驗
- **‹5›** 數據一致性驗證腳本

### 配置 dbt_project.yml

更新專案配置，設定模型的預設行為。

```yaml
# dbt_project.yml
name: 'my_dbt_project'
version: '1.0.0'
config-version: 2

profile: 'my_dbt_project'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

clean-targets:
  - "target"
  - "dbt_packages"

models:
  my_dbt_project:
    # 設定預設物化策略
    staging:
      +materialized: view  # ‹1›
      +schema: staging     # ‹2›
    intermediate:
      +materialized: view
      +schema: intermediate
    marts:
      +materialized: table  # ‹3›
      +schema: marts
```

- **‹1›** staging 層用 view（輕量，每次查詢時執行）
- **‹2›** staging 模型會建立在 `project.staging` 資料集中
- **‹3›** marts 層用 table（最終產出，需要持久化）

### 準備第一個原始 SQL

為了模擬 M3 的場景，我們需要一個實際的 SQL 檔案來遷移。

**建立範例原始 SQL**：

```sql
-- sources/original_sql/daily_sales_summary.sql
-- 每日銷售彙總表
-- 更新頻率：每天凌晨 2:00
-- 負責人：數據團隊
-- 最後更新：2024-01-15

CREATE OR REPLACE TABLE `my-project.analytics.daily_sales_summary`
PARTITION BY sale_date
OPTIONS(
  description="每日銷售彙總，包含產品類別和地區維度",
  partition_expiration_days=730,
  require_partition_filter=true
)
AS
SELECT
  DATE(order_timestamp) as sale_date,
  product_category,
  product_subcategory,
  region_name,
  country_code,
  COUNT(DISTINCT order_id) as order_count,
  COUNT(DISTINCT customer_id) as customer_count,
  SUM(amount) as total_amount,
  AVG(amount) as avg_order_amount,
  SUM(quantity) as total_quantity
FROM `my-project.raw_data.orders` o
LEFT JOIN `my-project.raw_data.products` p
  ON o.product_id = p.product_id
LEFT JOIN `my-project.raw_data.regions` r
  ON o.region_id = r.region_id
WHERE
  order_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
  AND o.status = 'completed'
  AND o.is_deleted = FALSE
GROUP BY
  sale_date,
  product_category,
  product_subcategory,
  region_name,
  country_code;
```

這個 SQL 包含：
- 完整的 CREATE TABLE 語句
- 分區配置
- 多表 JOIN
- WHERE 過濾條件
- GROUP BY 聚合
- 註解和文檔

這是一個典型的「中等複雜度」SQL，非常適合作為第一個遷移目標。

### 建立遷移記錄模板

建立一個 Markdown 檔案來記錄每次遷移的經驗。

```markdown
<!-- docs/migration_log.md -->
# 遷移記錄

## 遷移 #1: daily_sales_summary

**日期**: 2024-01-20
**原始檔案**: sources/original_sql/daily_sales_summary.sql
**負責人**: [你的名字]

### 遷移前分析

- **表格類型**: 分區表（按日期分區）
- **數據來源**: orders, products, regions
- **複雜度**: 中等（多表 JOIN + 聚合）
- **預估時間**: 30-45 分鐘

### 遷移過程

[記錄遷移步驟...]

### 遇到的問題

[記錄問題...]

### 解決方案

[記錄如何解決...]

### 經驗教訓

[記錄學到的東西...]

---
```

這個模板將幫助我們系統化地記錄每次遷移的經驗。

---

## 3.3 第一次嘗試：簡單的請求

現在，環境已經準備好，專案結構也建立了。讓我們開始第一次實際的遷移嘗試。

### 坂元的第一次請求

還記得第 1 章提到的嗎？坂元的第一次嘗試非常直接：

> 「請將 xxx.sql 轉換為 dbt」

讓我們複製這個過程。打開 Claude Code（或 Claude Web），輸入以下提示詞：

```
請將以下 SQL 轉換為 dbt 模型：

[貼上 daily_sales_summary.sql 的完整內容]
```

### Claude Code 的快速回應

在幾秒鐘內，Claude Code 生成了結果：

**生成的 dbt 模型**（`models/marts/daily_sales_summary.sql`）：

```sql
{{ config(
    materialized='table',
    partition_by={
      "field": "sale_date",
      "data_type": "date"
    }
) }}

SELECT
  DATE(order_timestamp) as sale_date,
  product_category,
  product_subcategory,
  region_name,
  country_code,
  COUNT(DISTINCT order_id) as order_count,
  COUNT(DISTINCT customer_id) as customer_count,
  SUM(amount) as total_amount,
  AVG(amount) as avg_order_amount,
  SUM(quantity) as total_quantity
FROM {{ source('raw_data', 'orders') }} o
INNER JOIN {{ source('raw_data', 'products') }} p  -- ⚠️ 問題 1
  ON o.product_id = p.product_id
INNER JOIN {{ source('raw_data', 'regions') }} r  -- ⚠️ 問題 2
  ON o.region_id = r.region_id
WHERE
  order_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
  AND o.status = 'completed'
GROUP BY  -- ⚠️ 問題 3
  sale_date,
  product_category,
  product_subcategory,
  region_name,
  country_code
```

**生成的 sources.yml**：

```yaml
# models/staging/sources.yml
version: 2

sources:
  - name: raw_data
    tables:
      - name: orders
      - name: products
      - name: regions
```

看起來很完美！讓我們執行看看：

```bash
$ dbt run --select daily_sales_summary
```

**執行成功！** 🎉

表格建立了，沒有 SQL 錯誤。第一次嘗試就成功了嗎？

### 但是...等等

坂元在這時做了一件關鍵的事：**仔細檢查生成的代碼**。

他打開原始 SQL 和生成的 dbt 模型，逐行對照。很快，他發現了問題。

---

## 3.4 發現問題

讓我們像坂元一樣，仔細分析生成的代碼。

### 問題 1：註解全部消失了

**原始 SQL**：
```sql
-- daily_sales_summary.sql
-- 每日銷售彙總表
-- 更新頻率：每天凌晨 2:00
-- 負責人：數據團隊
-- 最後更新：2024-01-15

CREATE OR REPLACE TABLE ...
```

**生成的 dbt 模型**：
```sql
{{ config(...) }}

SELECT
  DATE(order_timestamp) as sale_date,
  ...
```

❌ **所有註解都不見了**！

這些註解包含重要的資訊：
- 更新頻率
- 負責人
- 最後更新日期
- 業務邏輯說明

在團隊協作中，這些資訊非常重要。遺失它們會導致：
- 新成員不了解表格的用途
- 不清楚更新頻率和 SLA
- 不知道遇到問題該找誰

**影響嚴重性**: 🔴 高

### 問題 2：JOIN 類型被改變了

**原始 SQL**：
```sql
FROM `my-project.raw_data.orders` o
LEFT JOIN `my-project.raw_data.products` p  -- LEFT JOIN
  ON o.product_id = p.product_id
LEFT JOIN `my-project.raw_data.regions` r  -- LEFT JOIN
  ON o.region_id = r.region_id
```

**生成的 dbt 模型**：
```sql
FROM {{ source('raw_data', 'orders') }} o
INNER JOIN {{ source('raw_data', 'products') }} p  -- 變成 INNER JOIN！
  ON o.product_id = p.product_id
INNER JOIN {{ source('raw_data', 'regions') }} r  -- 變成 INNER JOIN！
  ON o.region_id = r.region_id
```

❌ **LEFT JOIN 被改成 INNER JOIN**！

**這會改變結果數據**：

- **LEFT JOIN**：保留所有訂單，即使產品或地區資訊缺失
- **INNER JOIN**：只保留產品和地區資訊都存在的訂單

假設有 10,000 筆訂單：
- 原始 SQL (LEFT JOIN)：返回 10,000 筆
- 生成的 dbt (INNER JOIN)：返回 9,200 筆（800 筆訂單的產品或地區資訊缺失）

**這是災難性的錯誤**！業務報表的數字會完全不對。

**影響嚴重性**: 🔴 極高

### 問題 3：WHERE 條件被部分遺漏

**原始 SQL**：
```sql
WHERE
  order_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
  AND o.status = 'completed'
  AND o.is_deleted = FALSE  -- 這個條件
```

**生成的 dbt 模型**：
```sql
WHERE
  order_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
  AND o.status = 'completed'
  -- is_deleted = FALSE 不見了！
```

❌ **`is_deleted = FALSE` 條件遺失**！

這意味著已刪除的訂單也會被計入，導致數字錯誤。

**影響嚴重性**: 🔴 高

### 問題 4：Schema 描述不完整

**生成的 sources.yml**：
```yaml
sources:
  - name: raw_data
    tables:
      - name: orders
      - name: products
      - name: regions
```

❌ **沒有 description**，沒有欄位定義！

理想的 sources.yml 應該是：

```yaml
sources:
  - name: raw_data
    database: my-project
    schema: raw_data
    description: 原始數據來源
    tables:
      - name: orders
        description: 原始訂單資料
        columns:
          - name: order_id
            description: 訂單唯一識別碼
          - name: order_timestamp
            description: 訂單時間戳
          # ... 其他欄位
```

**影響嚴重性**: 🟡 中等

### 問題 5：沒有生成 schema.yml

Claude Code 根本沒有生成 `schema.yml` 來定義模型的欄位和測試！

理想的 schema.yml：

```yaml
models:
  - name: daily_sales_summary
    description: 每日銷售彙總，包含產品類別和地區維度
    columns:
      - name: sale_date
        description: 銷售日期
        tests:
          - not_null
          - unique
      - name: order_count
        description: 訂單數量
        tests:
          - not_null
      # ... 其他欄位
```

**影響嚴重性**: 🟡 中等

### 問題 6：分區選項不完整

**原始 SQL**：
```sql
PARTITION BY sale_date
OPTIONS(
  description="...",
  partition_expiration_days=730,  -- 2 年後自動刪除
  require_partition_filter=true   -- 強制使用分區過濾
)
```

**生成的 dbt 模型**：
```sql
{{ config(
    materialized='table',
    partition_by={
      "field": "sale_date",
      "data_type": "date"
    }
    -- partition_expiration_days 和 require_partition_filter 不見了！
) }}
```

完整的 config 應該是：

```sql
{{ config(
    materialized='table',
    partition_by={
      "field": "sale_date",
      "data_type": "date",
      "expiration_ms": 63072000000,  -- 730 天
      "require_partition_filter": true
    }
) }}
```

**影響嚴重性**: 🟡 中等（影響成本和查詢限制）

### 問題彙總表

| # | 問題 | 嚴重性 | 影響 |
|---|------|--------|------|
| 1 | 註解全部消失 | 🔴 高 | 文檔遺失，團隊協作困難 |
| 2 | LEFT JOIN → INNER JOIN | 🔴 極高 | **數據錯誤**，結果不一致 |
| 3 | WHERE 條件遺漏 | 🔴 高 | **數據錯誤**，包含已刪除記錄 |
| 4 | Sources 描述不完整 | 🟡 中等 | 缺乏文檔 |
| 5 | 沒有生成 schema.yml | 🟡 中等 | 缺乏測試和文檔 |
| 6 | 分區選項不完整 | 🟡 中等 | 成本優化缺失 |

**6 個問題中，3 個是嚴重的數據正確性問題**。

如果我們沒有仔細檢查就直接使用，業務報表會出現嚴重錯誤。這就是為什麼「簡單地丟給 AI」是危險的。

---

## 3.5 手動修正：痛苦的過程

發現問題後，坂元開始手動修正。讓我們體驗這個過程。

### 修正步驟 1：恢復註解

```sql
-- models/marts/daily_sales_summary.sql

-- 每日銷售彙總表  ‹1›
-- 更新頻率：每天凌晨 2:00
-- 負責人：數據團隊
-- 最後更新：2024-01-15
--
-- 業務邏輯：
-- - 彙總最近 90 天的已完成訂單
-- - 按日期、產品類別、地區維度聚合
-- - 使用 LEFT JOIN 保留所有訂單（即使產品/地區資訊缺失）

{{ config(
    materialized='table',
    partition_by={
      "field": "sale_date",
      "data_type": "date"
    }
) }}

SELECT
  ...
```

- **‹1›** 手動將原始 SQL 的註解複製過來

**耗時**: ~5 分鐘

### 修正步驟 2：修正 JOIN 類型

```sql
FROM {{ source('raw_data', 'orders') }} o
LEFT JOIN {{ source('raw_data', 'products') }} p  -- ‹1› 改回 LEFT JOIN
  ON o.product_id = p.product_id
LEFT JOIN {{ source('raw_data', 'regions') }} r  -- ‹1› 改回 LEFT JOIN
  ON o.region_id = r.region_id
```

- **‹1›** 將 INNER JOIN 改回 LEFT JOIN

**耗時**: ~2 分鐘

### 修正步驟 3：補充 WHERE 條件

```sql
WHERE
  order_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
  AND o.status = 'completed'
  AND o.is_deleted = FALSE  -- ‹1› 補充遺漏的條件
```

- **‹1›** 加回 is_deleted 過濾條件

**耗時**: ~2 分鐘

### 修正步驟 4：完善 sources.yml

```yaml
# models/staging/sources.yml
version: 2

sources:
  - name: raw_data
    database: my-project
    schema: raw_data
    description: 原始數據來源

    tables:
      - name: orders
        description: 原始訂單資料
        columns:
          - name: order_id
            description: 訂單唯一識別碼
          - name: order_timestamp
            description: 訂單時間戳
          - name: product_id
            description: 產品 ID
          - name: region_id
            description: 地區 ID
          - name: amount
            description: 訂單金額
          - name: quantity
            description: 訂單數量
          - name: status
            description: 訂單狀態
          - name: is_deleted
            description: 是否已刪除

      - name: products
        description: 產品主檔
        columns:
          - name: product_id
            description: 產品 ID
          - name: product_category
            description: 產品類別
          - name: product_subcategory
            description: 產品子類別

      - name: regions
        description: 地區主檔
        columns:
          - name: region_id
            description: 地區 ID
          - name: region_name
            description: 地區名稱
          - name: country_code
            description: 國家代碼
```

**耗時**: ~15 分鐘（需要查詢 BigQuery 的 INFORMATION_SCHEMA）

### 修正步驟 5：建立 schema.yml

```yaml
# models/marts/schema.yml
version: 2

models:
  - name: daily_sales_summary
    description: |
      每日銷售彙總表

      **更新頻率**: 每天凌晨 2:00
      **數據範圍**: 最近 90 天
      **SLA**: T+1

    columns:
      - name: sale_date
        description: 銷售日期（基於訂單時間戳）
        tests:
          - not_null
          - unique
      - name: product_category
        description: 產品類別
      - name: product_subcategory
        description: 產品子類別
      - name: region_name
        description: 地區名稱
      - name: country_code
        description: 國家代碼
      - name: order_count
        description: 訂單數量
        tests:
          - not_null
      - name: customer_count
        description: 獨立客戶數
        tests:
          - not_null
      - name: total_amount
        description: 總銷售金額
        tests:
          - not_null
      - name: avg_order_amount
        description: 平均訂單金額
      - name: total_quantity
        description: 總銷售數量
        tests:
          - not_null
```

**耗時**: ~10 分鐘

### 修正步驟 6：完善分區配置

```sql
{{ config(
    materialized='table',
    partition_by={
      "field": "sale_date",
      "data_type": "date",
      "granularity": "day"
    },
    partition_expiration_days=730,  -- ‹1› 補充
    require_partition_filter=true,  -- ‹2› 補充
    cluster_by=["product_category", "region_name"]  -- ‹3› 優化
) }}
```

- **‹1›** 730 天後自動刪除分區
- **‹2›** 要求查詢必須包含 sale_date 過濾條件
- **‹3›** 在分區內按類別和地區 clustering（進一步優化）

**耗時**: ~5 分鐘

### 總修正時間

| 修正項目 | 耗時 |
|---------|------|
| 恢復註解 | 5 分鐘 |
| 修正 JOIN | 2 分鐘 |
| 補充 WHERE | 2 分鐘 |
| 完善 sources.yml | 15 分鐘 |
| 建立 schema.yml | 10 分鐘 |
| 完善分區配置 | 5 分鐘 |
| **總計** | **~40 分鐘** |

加上發現問題的時間（~10 分鐘），**總共約 50 分鐘**。

這還只是**一個檔案**。如果有 50 個檔案，即使 AI 生成了初版，仍需要 **40-50 小時的手動修正工作**。

更糟的是，這些錯誤很多是**不容易發現的**（特別是 JOIN 類型改變）。如果沒有仔細檢查，錯誤會潛入生產環境。

---

## 3.6 反思與頓悟

修正完成後，坂元坐在椅子上，思考剛才發生的事情。

### 為何簡單的提示詞不夠？

「請將 xxx.sql 轉換為 dbt」這個提示詞有什麼問題？

**問題不在於 AI 不夠聰明**。Claude Code 確實理解 SQL 和 dbt，也能正確生成語法。

**問題在於缺乏上下文**：

1. **AI 不知道你的標準**
   - 是否應該保留註解？
   - 是否應該改變 JOIN 類型？
   - 如何處理 WHERE 條件？

   AI 只能「猜測」，而猜測可能錯誤。

2. **AI 不知道你的專案結構**
   - Sources 應該放在哪裡？
   - Schema 檔案如何組織？
   - 命名慣例是什麼？

3. **AI 不知道你的需求完整性**
   - 需要生成 sources.yml 嗎？
   - 需要生成 schema.yml 嗎？
   - 需要哪些測試？

4. **AI 沒有「記憶」**
   - 這次修正的錯誤，下次還會重複
   - 無法從經驗中學習

### 關鍵洞察

坂元在這時有了一個關鍵洞察：

> 「如果我雇用一位新工程師來做這個任務，我不會只說『把這個 SQL 轉成 dbt』。我會提供：
> - 詳細的 SOP（標準作業程序）
> - 專案的命名慣例和結構
> - 常見錯誤清單
> - 檢查清單
> - 實際範例
>
> AI 協作也應該如此。我需要一份『手冊』來傳遞這些知識。」

這就是 **遷移手冊** 概念誕生的時刻。

### 「手冊」的概念

坂元決定請求 Claude Code 製作一份手冊：

```
請活用這次作業所獲得的知識，製作對未來作業有幫助的手冊。

這份手冊應該包含：
- 完整的遷移步驟
- 需要注意的事項
- 常見錯誤與如何避免
- 檢查清單
```

幾分鐘後，Claude Code 生成了第一版手冊：

```markdown
# dbt 模型遷移手冊 v1.0

## 1. 確認遷移來源的 SQL 檔案

在開始遷移前，先確認原始 SQL 檔案的結構：
- 檔案位置
- CREATE TABLE 語法類型（標準表/分區表/分片表）
- SELECT 邏輯複雜度
- 是否使用 UDF
- 註解和文檔內容

## 2. 建立參照外部 schema 資料表的 sources 定義

在 `models/staging/sources.yml` 中定義所有外部資料來源：

```yaml
version: 2
sources:
  - name: [schema_name]
    database: [project_id]
    schema: [schema_name]
    description: [描述]
    tables:
      - name: [table_name]
        description: [描述]
        columns: [列出主要欄位]
```

**注意事項**：
- 必須包含 database 和 schema
- 每個表和欄位都要有 description
- 參照時使用 {{ source('schema_name', 'table_name') }}

## 3. 建立 dbt 模型的 SQL 檔案（每日完全更新資料表版）

在 `models/marts/` 建立模型檔案：

**關鍵原則**：
✅ **保留所有原始註解**
✅ **不要改變 SQL 邏輯**（特別是 JOIN 類型）
✅ **不要遺漏 WHERE 條件**
✅ **將表名替換為 source() 或 ref()**

範例結構：
```sql
-- [原始註解完整保留]

{{ config(
    materialized='table',
    partition_by={...} if needed
) }}

SELECT
  [保持與原始 SQL 完全相同的邏輯]
FROM {{ source('...', '...') }}
WHERE [保持所有條件]
```

## 4. 建立模型檔案時的注意事項

**關鍵錯誤清單**（請務必避免）：
- ❌ 不要刪除註解
- ❌ 不要將 LEFT JOIN 改成 INNER JOIN
- ❌ 不要遺漏 WHERE 條件（特別是 is_deleted、status 等）
- ❌ 不要改變聚合函數（COUNT DISTINCT vs COUNT）
- ❌ 不要改變 GROUP BY 欄位

## 5. 建立 dbt 模型的 schema 檔案

在 `models/marts/schema.yml` 定義模型：

```yaml
models:
  - name: [model_name]
    description: [詳細描述，包含更新頻率、負責人等]
    columns:
      - name: [column_name]
        description: [描述]
        tests: [根據原始表的約束加入測試]
```

**測試建議**：
- 主鍵：unique + not_null
- 外鍵：relationships
- 重要欄位：not_null
- 數值欄位：檢查範圍（如 >= 0）

## 6. 整體共通注意事項

- 保持與原始 SQL 的功能完全等價
- 所有變更都要有明確理由
- 遷移後必須驗證數據一致性
- 文檔和測試不是可選，而是必需
```

這份手冊還很粗糙，但它包含了坂元從第一次失敗中學到的所有教訓。

### 測試手冊：第二個檔案

坂元決定用這份手冊來遷移第二個 SQL 檔案。

他的新提示詞：

```
請將以下 SQL 轉換為 dbt 模型。

對應方法請參考以下手冊：
[貼上 遷移手冊 v1.0 的完整內容]

原始 SQL：
[貼上第二個 SQL 檔案]
```

這次的結果**明顯更好**：
- ✅ 註解被保留了
- ✅ JOIN 類型正確
- ✅ WHERE 條件完整
- ✅ 生成了 sources.yml
- ✅ 生成了 schema.yml

仍然有一些小問題（如某個欄位描述不夠詳細），但**大幅改善**了。

最重要的是，坂元找到了方向：

> **通過持續更新手冊，AI 的能力會不斷提升**。

---

## 本章總結

讓我們回顧本章的核心要點。

### 核心收穫

✅ **環境設置**
- Python 虛擬環境 + dbt-bigquery 安裝
- BigQuery 認證配置（OAuth 或 Service Account）
- dbt 專案初始化與測試
- 專案結構組織

✅ **第一次嘗試（失敗）**
- 簡單的提示詞：「請將 xxx.sql 轉換為 dbt」
- 快速生成，看似成功
- 但仔細檢查發現 6 個問題（3 個嚴重）

✅ **發現的問題**
1. 註解全部消失（文檔遺失）
2. LEFT JOIN → INNER JOIN（數據錯誤）
3. WHERE 條件遺漏（數據錯誤）
4. Sources 描述不完整
5. 沒有生成 schema.yml
6. 分區選項不完整

✅ **手動修正的痛苦**
- 單個檔案需要 40-50 分鐘修正
- 50 個檔案 = 40-50 小時
- 錯誤難以發現，容易潛入生產環境

✅ **關鍵洞察**
- 問題不是 AI 不夠聰明，而是缺乏上下文
- 需要像培訓新人一樣，提供詳細的 SOP
- **遷移手冊 概念誕生**

### 關鍵洞察

💡 **AI 協作 ≠ AI 使用**

簡單地「使用」AI（丟個請求，期待完美結果）是不夠的。真正有效的是「與 AI 協作」：
- 提供結構化的知識（Playbook）
- 建立迭代改進的循環
- 從錯誤中學習並更新知識

💡 **失敗是學習的機會**

第一次嘗試的失敗不是終點，而是起點。通過系統化地記錄問題和解決方案，我們建立了 Playbook 的基礎。

💡 **檢查永遠重要**

即使有 AI 協助，人工審查仍然不可或缺。特別是涉及數據正確性的關鍵邏輯（JOIN 類型、WHERE 條件），必須仔細檢查。

### 你現在擁有的

完成本章後，你已經：
- ✅ 建立了完整的 dbt 開發環境
- ✅ 完成了第一次實際的遷移嘗試
- ✅ 經歷了失敗並從中學習
- ✅ 理解了為何需要 遷移手冊
- ✅ 看到了 Playbook 的初版（v1.0）

### 下一步

在第 4 章，我們將：
- 系統化地設計 遷移手冊 的結構
- 補充 v1.0 遺漏的內容
- 用 Playbook 指導 Claude Code 完成更多遷移
- 建立迭代改進的機制
- 看著 Playbook 從 v1.0 成長到 v2.0

這是知識演進的開始！

---

## 下一章預告

在第 4 章《建立遷移手冊（遷移手冊）》中，我們將：

- **設計 Playbook 結構**：如何組織知識才最有效？
- **建立完整的 v1.0**：補充所有必要的章節
- **測試 Playbook**：用它指導第 2-5 個檔案的遷移
- **記錄新問題**：第一版不會完美，記錄遇到的新問題
- **迭代到 v2.0**：根據實際經驗改進手冊

你將學會如何建立一個「會學習的 AI 協作系統」。

準備好了嗎？讓我們開始建立 遷移手冊！

---

**下一章：第 4 章 - 建立遷移手冊（遷移手冊）** →
