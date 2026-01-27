# 第六章：上下文 (Context) — 提供完整的執行環境

**在這一章中，你將學會：**
- 如何描述技術棧與編碼規範
- 分享設計決策與處理歷史包袱
- 利用 MCP 從 Linear/Notion/Slack 取得動態上下文
- 建立團隊知識庫（`.claude/` 資料夾）
- 將隱性知識轉化為顯性文件

> 💡 **開場白**
>
> 假設你是一個新加入團隊的工程師。第一天上班，主管跟你說：「幫我修一下登入功能的 bug。」
>
> 你會需要知道什麼？
>
> - 程式碼在哪裡？
> - 用什麼語言、框架？
> - 資料庫結構長什麼樣？
> - 有沒有現有的測試？
> - 團隊的 coding style 是什麼？
> - 這個功能之前為什麼這樣設計？
>
> **AI 也需要知道這些。** 這就是 Context 的角色。

---

## 6.1 技術棧與編碼規範

Context 的第一層是「硬資訊」——那些客觀的、不會改變的技術背景。

### 技術棧清單

好的技術棧描述應該包含：

```
【技術棧】

1. 程式語言與版本
   - Python 3.11

2. 框架
   - FastAPI 0.104
   - SQLAlchemy 2.0
   - Pydantic 2.5

3. 資料庫
   - PostgreSQL 15（主資料庫）
   - Redis 7.0（快取、Session）

4. 基礎設施
   - Docker + Docker Compose
   - AWS ECS（生產環境）
   - GitHub Actions（CI/CD）

5. 套件管理
   - uv（Python 套件）
   - npm（前端，如果有的話）
```

### 編碼規範

每個團隊都有自己的 coding style。如果你不告訴 AI，它會用「通用的最佳實踐」——這可能跟你團隊的風格不同。

```
【編碼規範】

1. 程式碼風格
   - 使用 Black 格式化（行寬 88）
   - 使用 Ruff 進行 lint
   - 遵循 PEP 8

2. 命名慣例
   - 檔案名：snake_case（例：user_service.py）
   - 類別名：PascalCase（例：UserService）
   - 函數名：snake_case（例：get_user_by_id）
   - 常數：SCREAMING_SNAKE_CASE（例：MAX_RETRY_COUNT）

3. 架構慣例
   - 路由處理器放在 routers/ 目錄
   - 業務邏輯放在 services/ 目錄
   - 資料模型放在 models/ 目錄
   - 工具函數放在 utils/ 目錄

4. 註解規範
   - 所有公開函數要有 docstring（Google style）
   - 複雜邏輯要有行內註解
   - TODO 格式：# TODO(username): description

5. 測試規範
   - 測試檔案命名：test_*.py
   - 測試函數命名：test_<what>_<condition>_<expected>
   - 例：test_login_with_wrong_password_returns_401
```

> 💡 **小提示**
>
> 如果你的專案有 `.editorconfig`、`pyproject.toml`、`.eslintrc` 等設定檔，可以直接告訴 Claude Code：
>
> ```
> 請參考 pyproject.toml 中的 [tool.black] 和 [tool.ruff] 設定。
> ```

---

## 6.2 設計決策與歷史包袱

Context 的第二層是「軟資訊」——那些需要解釋「為什麼」的設計決策。

### 為什麼要記錄設計決策？

每個專案都有一些「看起來很奇怪但有原因」的設計。如果你不解釋，AI 可能會「好心」幫你「修正」這些「問題」。

**範例情境：**

你的程式碼裡有這樣一行：
```python
# 這裡故意用 sleep，不要刪除！
time.sleep(0.1)
```

如果你只說「幫我優化這段程式碼」，AI 可能會刪掉這個 sleep，因為它「看起來」是效能問題。

但實際上，這個 sleep 是為了避免打爆第三方 API 的 rate limit。

### 架構決策記錄 (ADR)

ADR（Architecture Decision Record）是一種記錄設計決策的標準格式：

```markdown
# ADR-001: 使用 Redis 作為 Session 儲存

## 狀態
已採用

## 上下文
我們需要選擇 Session 儲存方案。選項包括：
1. 資料庫（PostgreSQL）
2. 記憶體快取（Redis）
3. JWT（無狀態）

## 決策
選擇 Redis 作為 Session 儲存。

## 原因
1. 效能考量：Redis 讀取延遲 < 1ms，資料庫約 10-50ms
2. 水平擴展：多個 API 伺服器可以共享 Session
3. 過期管理：Redis 原生支援 TTL
4. 為什麼不用 JWT：
   - 我們需要支援「強制登出」功能
   - JWT 無法在伺服器端撤銷
   - Session 資料量較大（包含權限快取），不適合放在 token 裡

## 後果
- 需要維護 Redis 服務
- Session 資料有遺失風險（Redis 重啟時）
- 增加了基礎設施複雜度
```

### 在指令中引用設計決策

```
【上下文 - 設計決策】

1. Session 使用 Redis（參考 docs/adr/ADR-001.md）
   - 不要改成 JWT 或資料庫儲存

2. 用戶密碼用 bcrypt（cost=12）
   - 不要改成其他雜湊演算法
   - 這是資安團隊的規定

3. API 回應格式遵循 JSON:API 規範
   - 不要用其他格式
   - 前端已經依賴這個格式

4. 歷史包袱注意
   - `legacy_user_id` 欄位是舊系統遷移過來的
   - 有些舊用戶的 email 可能是空的（歷史資料問題）
   - users 表的 `status` 欄位有五種狀態，但 `suspended` 已棄用
```

> ⚠️ **注意**
>
> 歷史包袱不是恥辱，而是現實。誠實告訴 AI 這些限制，比讓它發現後再處理好得多。

---

## 6.3 利用 MCP 從外部工具取得動態上下文

在第四章，我們介紹了用 MCP 獲取需求。MCP 同樣可以用來獲取上下文資訊。

### 從 Notion 獲取設計文件

```
請從 Notion 頁面 "Backend API 設計規範" 讀取我們的 API 設計標準，
然後實作以下功能。確保符合文件中的規範。

【功能需求】
...
```

### 從 Slack 獲取討論歷史

```
在實作之前，請搜尋 Slack #backend 頻道中
過去一個月關於 "認證" 或 "登入" 的討論，
總結相關的設計決策和注意事項。
```

### 從 GitHub 獲取 PR 評論和 Issue

```
請看一下 GitHub Issue #234 的討論，
理解這個 bug 的完整脈絡，
然後提出修復方案。
```

### 動態上下文 vs 靜態上下文

| 類型 | 來源 | 更新頻率 | 範例 |
|------|------|----------|------|
| 靜態上下文 | 本地檔案 | 很少改變 | 技術棧、編碼規範、ADR |
| 動態上下文 | 外部工具 | 經常改變 | 最新需求、討論、設計稿 |

> 🎯 **實戰技巧**
>
> 靜態上下文放在專案的 `.claude/` 或 `docs/` 目錄中。
> 動態上下文用 MCP 即時獲取。
> 這樣可以確保 AI 同時擁有穩定的背景知識和最新的資訊。

---

## 6.4 建立團隊知識庫（.claude/ 資料夾）

這是本章最實用的技巧之一：建立一個專門給 AI 閱讀的知識庫。

### .claude/ 資料夾結構

```
your-project/
├── .claude/
│   ├── README.md           # AI 使用指南
│   ├── CONVENTIONS.md      # 編碼規範
│   ├── ARCHITECTURE.md     # 架構說明
│   ├── DECISIONS.md        # 設計決策摘要
│   ├── GLOSSARY.md         # 專有名詞解釋
│   └── COMMON_TASKS.md     # 常見任務範本
├── src/
├── tests/
└── ...
```

### .claude/README.md 範例

```markdown
# AI 協作指南

歡迎！這個資料夾包含了與 AI 協作時需要的上下文資訊。

## 快速開始

1. 先閱讀 CONVENTIONS.md 了解編碼規範
2. 查看 ARCHITECTURE.md 了解專案架構
3. 遇到專有名詞請查 GLOSSARY.md

## 常見任務

- 新增 API：參考 COMMON_TASKS.md#新增API
- 資料庫遷移：參考 COMMON_TASKS.md#資料庫遷移
- 新增測試：參考 COMMON_TASKS.md#測試

## 注意事項

- 所有 API 都要有對應的測試
- 不要直接修改 migrations/ 中的舊檔案
- 敏感資訊請用環境變數
```

### .claude/ARCHITECTURE.md 範例

```markdown
# 專案架構

## 目錄結構

\`\`\`
src/
├── main.py              # FastAPI 應用進入點
├── config.py            # 設定管理
├── routers/             # API 路由
│   ├── __init__.py
│   ├── auth.py          # 認證相關
│   ├── users.py         # 用戶管理
│   └── products.py      # 商品管理
├── services/            # 業務邏輯
│   ├── auth_service.py
│   ├── user_service.py
│   └── product_service.py
├── models/              # SQLAlchemy 模型
│   ├── user.py
│   └── product.py
├── schemas/             # Pydantic schemas
│   ├── user.py
│   └── product.py
└── utils/               # 工具函數
    ├── security.py      # 加密、JWT
    └── pagination.py    # 分頁工具
\`\`\`

## 資料流

\`\`\`
Request → Router → Service → Model → Database
                      ↓
               Response (Schema)
\`\`\`

## 依賴注入

我們使用 FastAPI 的 Depends 進行依賴注入：
- 資料庫 Session：\`get_db()\`
- 當前用戶：\`get_current_user()\`
- 分頁參數：\`get_pagination()\`
```

### .claude/GLOSSARY.md 範例

```markdown
# 專有名詞對照表

| 術語 | 說明 |
|------|------|
| SKU | Stock Keeping Unit，商品庫存單位 |
| PV | Page View，頁面瀏覽次數 |
| UV | Unique Visitor，獨立訪客數 |
| GMV | Gross Merchandise Volume，商品交易總額 |
| AOV | Average Order Value，平均訂單金額 |
| DAU | Daily Active Users，日活躍用戶 |
| MAU | Monthly Active Users，月活躍用戶 |
| LTV | Lifetime Value，用戶生命週期價值 |

## 專案特定術語

| 術語 | 說明 |
|------|------|
| Super User | 擁有所有權限的管理員 |
| Soft Delete | 軟刪除，設 deleted_at 而非真的刪除 |
| Flash Sale | 限時特賣活動 |
```

> 💡 **小提示**
>
> 在指令中可以直接引用這些檔案：
>
> ```
> 請參考 .claude/CONVENTIONS.md 的編碼規範，
> 實作一個新的商品分類 API。
> ```

---

## 6.5 隱性知識的顯性化技巧

最後，讓我們談談如何把「腦袋裡的知識」轉化為「AI 能理解的文件」。

### 什麼是隱性知識？

隱性知識是那些「你知道但沒寫下來」的東西：
- 「這個函數要先呼叫那個函數」
- 「這個欄位雖然叫 X 但其實是 Y 的意思」
- 「這種情況我們通常這樣處理」
- 「這段程式碼不要動，上次改了就出事」

### 顯性化的技巧

**技巧 1：寫程式碼時順便寫註解**

```python
class OrderService:
    def cancel_order(self, order_id: str):
        """
        取消訂單。

        注意事項：
        1. 只有「待付款」和「待出貨」狀態的訂單可以取消
        2. 取消後要觸發退款流程（如果已付款）
        3. 要釋放庫存（呼叫 inventory_service.release）
        4. 要發送取消通知給用戶

        歷史決策：
        - 我們曾經考慮過讓「已出貨」的訂單也能取消，
          但物流合作方不支援，所以目前不開放。
        """
        pass
```

**技巧 2：建立決策日誌**

每次做出重要決策時，花 2 分鐘記錄下來：

```markdown
## 2026-01-15：選擇 Redis Sorted Set 做排行榜

### 決策
使用 Redis 的 Sorted Set 來實作商品銷量排行榜。

### 原因
1. 需要即時更新（每次購買後）
2. 需要高效率取得 Top N
3. Redis Sorted Set 的 ZADD/ZRANGE 複雜度都是 O(log N)

### 捨棄的方案
- PostgreSQL 排序：每次查詢都要 ORDER BY + LIMIT，太慢
- 每小時批次計算：不夠即時
- Elasticsearch：太重了，只是個簡單排行榜
```

**技巧 3：Code Review 時捕捉知識**

當你在 Code Review 時寫下「這裡應該要...」或「為什麼不用...」，這些都是隱性知識的展現。把它們整理到文件中。

**技巧 4：新人提問是知識的來源**

當新人問「為什麼這樣設計」時，你的回答就是隱性知識。記錄下來！

```markdown
## FAQ：為什麼用戶表有兩個 email 欄位？

Q: 為什麼 users 表有 email 和 verified_email 兩個欄位？

A: 這是因為我們允許用戶在驗證前就註冊。
   - email：用戶輸入的 email（可能未驗證）
   - verified_email：通過驗證的 email（用於重要通知）

   歷史原因：早期版本不需要驗證，後來加入驗證機制時
   為了向後相容才加入 verified_email 欄位。

   注意：登入時應該用 email 欄位檢查，但發送重要通知（如訂單確認）
   應該用 verified_email（如果有的話）。
```

---

## 本章重點回顧

- **要點 1**：技術棧和編碼規範是 Context 的「硬資訊」，確保 AI 產出符合你的環境。

- **要點 2**：設計決策和歷史包袱是 Context 的「軟資訊」，解釋「為什麼」可以避免 AI 誤改重要設計。

- **要點 3**：MCP 可以從 Notion、Slack、GitHub 等工具獲取動態上下文。

- **要點 4**：`.claude/` 資料夾是給 AI 閱讀的團隊知識庫，包含規範、架構、術語等。

- **要點 5**：把隱性知識顯性化，讓 AI（和新人）都能快速理解專案。

---

## 大腦體操 🧠

**問題 1：**
為什麼「歷史包袱」要主動告訴 AI，而不是等它問？

**問題 2：**
你的專案中有哪些「大家都知道但沒寫下來」的規則？列出三個。

**問題 3：**
設計一個 `.claude/COMMON_TASKS.md` 的「新增 API」章節，包含：
- 需要修改哪些檔案
- 要遵循什麼規範
- 要注意什麼事項

---

## 下一章預告

恭喜！你已經完整學習了 I-B-C 框架的三根支柱。

在下一章，我們將把所有學到的東西整合起來，通過**四個完整的實戰案例**——RESTful API 開發、即時推薦系統、WebSocket 聊天室、資料遷移與重構——讓你真正掌握 I-B-C 框架的應用。

準備好進入實戰了嗎？

---

> 📝 **讀者筆記區**
>
> 你的專案目前有哪些「AI 需要知道但可能猜不到」的上下文？
>
> _________________________________
>
> 如果要建立 .claude/ 資料夾，你會優先寫哪些檔案？
>
> _________________________________
>
> 找一個你專案中「看起來奇怪但有原因」的設計，寫一個簡短的 ADR：
>
> _________________________________
