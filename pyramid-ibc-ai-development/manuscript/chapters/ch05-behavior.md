# 第五章：行為 (Behavior) — 定義可驗證的成功標準

**在這一章中，你將學會：**
- 測試驅動的行為定義方法（TDD/BDD 思維）
- 如何設定效能基準與 SLA
- API 契約測試的設計與應用
- 讓 Claude Code 自動驗證行為
- 識別並修正常見的行為定義錯誤

> 💡 **開場白**
>
> 想像你請一個廚師幫你做一道菜。你說：「做一道好吃的菜。」
>
> 廚師問：「什麼叫好吃？」
>
> 你說：「就...好吃啊。」
>
> 結果廚師端上一盤你最討厭的香菜（他覺得很好吃）。
>
> **「好吃」不是一個可驗證的標準。**
>
> 在軟體開發中，如果你不能清楚定義「什麼叫做完成」，你就永遠無法判斷 AI（或任何人）是否「做對了」。

---

## 5.1 測試驅動的行為定義 (TDD/BDD)

在傳統開發中，很多人是這樣的流程：

```
寫程式碼 → 手動測試 → 發現問題 → 修改 → 再測試 → ...
```

但有一種更有效的方法：

```
定義行為（寫測試）→ 寫程式碼 → 自動驗證 → 完成
```

這就是 **TDD（Test-Driven Development）** 或 **BDD（Behavior-Driven Development）** 的核心思想。

### TDD 的核心循環

```
    ┌─────────────────────────────────────┐
    │                                     │
    │    Red → Green → Refactor          │
    │    紅燈 → 綠燈 → 重構              │
    │                                     │
    └─────────────────────────────────────┘
            │           │           │
            ▼           ▼           ▼
       ┌────────┐  ┌────────┐  ┌────────┐
       │ 寫測試  │  │ 寫程式碼│  │  重構  │
       │(會失敗) │  │(讓測試 │  │(優化  │
       │        │  │ 通過)  │  │ 程式碼)│
       └────────┘  └────────┘  └────────┘
```

### 為什麼 TDD 對 AI 協作特別重要？

當你使用 TDD 思維與 AI 協作時，你其實是在做這件事：

**在 AI 寫程式碼之前，就先定義好「什麼叫正確」。**

這有兩個巨大的好處：

1. **AI 有明確的目標**：它知道要讓什麼測試通過
2. **你有客觀的驗收標準**：不用靠「感覺」判斷程式碼對不對

### 實際應用：先給測試，再要實作

**傳統方式（沒有用 TDD 思維）：**
```
幫我寫一個計算購物車總金額的函數
```

AI 可能會寫出一個「技術上正確」但不符合你需求的函數。比如：
- 沒有處理折扣
- 沒有處理運費
- 沒有處理數量為 0 的情況

**TDD 方式：**
```
幫我實作一個計算購物車總金額的函數，
它需要通過以下測試案例：

def test_empty_cart():
    cart = Cart()
    assert cart.get_total() == 0

def test_single_item():
    cart = Cart()
    cart.add_item(Product("Apple", price=100), quantity=2)
    assert cart.get_total() == 200

def test_multiple_items():
    cart = Cart()
    cart.add_item(Product("Apple", price=100), quantity=2)
    cart.add_item(Product("Banana", price=50), quantity=3)
    assert cart.get_total() == 350

def test_with_discount():
    cart = Cart()
    cart.add_item(Product("Apple", price=100), quantity=2)
    cart.apply_discount(percent=10)
    assert cart.get_total() == 180

def test_with_shipping():
    cart = Cart()
    cart.add_item(Product("Apple", price=100), quantity=1)
    cart.set_shipping(fee=60)
    assert cart.get_total() == 160

def test_free_shipping_threshold():
    cart = Cart()
    cart.add_item(Product("Apple", price=100), quantity=10)  # 總價 1000
    cart.set_shipping(fee=60, free_threshold=500)
    assert cart.get_total() == 1000  # 達到免運門檻，運費免除
```

現在 AI 知道：
- 空購物車要回傳 0
- 要支援折扣功能
- 要支援運費計算
- 要支援免運門檻

> 💡 **小提示**
>
> 你不需要真的先寫完所有測試。重點是用「測試案例」的格式來描述行為，讓 AI 理解你的預期。

---

## 5.2 效能基準與 SLA 設定

不是所有行為都能用「對/錯」來判斷。有時候，你需要定義的是**效能標準**。

### 常見的效能指標

| 指標 | 說明 | 範例 |
|------|------|------|
| **延遲 (Latency)** | 處理一個請求需要多少時間 | P95 < 200ms |
| **吞吐量 (Throughput)** | 每秒能處理多少請求 | > 1000 RPS |
| **錯誤率 (Error Rate)** | 請求失敗的比例 | < 0.1% |
| **可用性 (Availability)** | 系統正常運作的時間比例 | 99.9% |

### P50、P95、P99 是什麼？

```
假設 100 個請求的回應時間分布：

最快 ←─────────────────────────────────────→ 最慢

     ████████████████████████████████████████
     ↑        ↑                ↑            ↑
    P50      P75              P95          P99
   (50ms)   (80ms)          (200ms)      (500ms)
```

- **P50（中位數）**：50% 的請求在這個時間內完成
- **P95**：95% 的請求在這個時間內完成
- **P99**：99% 的請求在這個時間內完成

> ⚠️ **注意**
>
> 如果你只看「平均值」，你會忽略那些極端慢的請求。
> P95 和 P99 更能反映「大多數用戶」的體驗。

### 如何在指令中定義效能標準

**不好的定義：**
```
API 要快一點
```

**好的定義：**
```
【效能要求】

1. 延遲標準
   - P50 < 50ms
   - P95 < 200ms
   - P99 < 500ms

2. 吞吐量
   - 需支援 500 RPS（峰值）
   - 平均負載約 100 RPS

3. 資源限制
   - 單一請求記憶體使用 < 100MB
   - 資料庫查詢數 < 3 次

4. 測試條件
   - 測試資料量：100 萬筆商品
   - 併發用戶數：100
```

---

## 5.3 API 契約測試

當你的功能是一個 API 時，「行為」最好用 **API 契約** 來定義。

### 什麼是 API 契約？

API 契約是對 API 行為的完整描述，包括：
- 請求格式（URL、方法、參數）
- 回應格式（狀態碼、資料結構）
- 錯誤處理（各種錯誤情況的回應）

### OpenAPI 規格

OpenAPI（以前叫 Swagger）是定義 API 契約的標準格式：

```yaml
openapi: 3.0.0
info:
  title: 購物車 API
  version: 1.0.0

paths:
  /api/cart/{user_id}:
    get:
      summary: 取得用戶的購物車
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Cart'
        '404':
          description: 用戶不存在

components:
  schemas:
    Cart:
      type: object
      properties:
        user_id:
          type: string
          format: uuid
        items:
          type: array
          items:
            $ref: '#/components/schemas/CartItem'
        total:
          type: number
          format: float
```

### 在指令中使用 API 契約

```
請實作以下 API，並確保符合這個 OpenAPI 規格：

【API 契約】

POST /api/cart/{user_id}/items
- 新增商品到購物車
- 請求 body: { "product_id": string, "quantity": integer }
- 成功回應 (201): { "cart_id": string, "items": [...], "total": float }
- 錯誤回應:
  - 400: quantity < 1 或 > 99
  - 404: product_id 不存在
  - 409: 庫存不足

DELETE /api/cart/{user_id}/items/{product_id}
- 從購物車移除商品
- 成功回應 (200): { "cart_id": string, "items": [...], "total": float }
- 錯誤回應:
  - 404: 商品不在購物車中

GET /api/cart/{user_id}
- 取得購物車內容
- 成功回應 (200): { "cart_id": string, "items": [...], "total": float }
- 錯誤回應:
  - 404: 用戶不存在
```

> 🎯 **實戰技巧**
>
> 如果你的專案已經有 OpenAPI 規格檔，可以直接告訴 Claude Code：
>
> ```
> 請參考 docs/openapi.yaml 的規格，
> 實作 /api/cart 相關的三個端點。
> ```

---

## 5.4 讓 Claude Code 自動驗證行為

這是本章最強大的技巧：**讓 Claude Code 自己驗證它的產出**。

### 自動驗證流程

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  你的指令                                               │
│  ├── Intent: 實作購物車功能                              │
│  ├── Behavior: [測試案例 + API 契約 + 效能標準]          │
│  └── Context: [技術棧 + 現有架構]                        │
│                                                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Claude Code                                            │
│  1. 閱讀規格                                             │
│  2. 寫程式碼                                             │
│  3. 執行測試 ← 自動驗證！                                │
│  4. 如果測試失敗，自動修正                               │
│  5. 測試通過後才回報完成                                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 如何啟用自動驗證

在你的指令中加入「驗證步驟」：

```
【行為定義】
（你的測試案例和 API 契約）

【驗證要求】
完成實作後，請執行以下驗證：

1. 單元測試
   $ pytest tests/test_cart.py -v
   - 所有測試必須通過

2. 類型檢查
   $ mypy src/services/cart.py
   - 不能有類型錯誤

3. 程式碼風格
   $ ruff check src/services/cart.py
   - 不能有 lint 錯誤

4. 效能測試（如果適用）
   $ locust -f tests/load_test.py --headless -u 100 -r 10 -t 30s
   - P95 延遲 < 200ms

如果任何驗證失敗，請自動修正並重新驗證。
```

### 實際範例

```
【目標】
實作用戶登入 API

【行為定義 - 測試案例】

def test_login_success():
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "correct_password"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password():
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrong_password"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

def test_login_user_not_found():
    response = client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "any_password"
    })
    # 安全考量：不應洩漏 email 是否存在
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

def test_login_invalid_email_format():
    response = client.post("/api/auth/login", json={
        "email": "not_an_email",
        "password": "any_password"
    })
    assert response.status_code == 422

【驗證要求】
1. 先在 tests/test_auth.py 新增以上測試
2. 實作 API
3. 執行 pytest tests/test_auth.py -v
4. 如果有測試失敗，分析原因並修正
5. 全部測試通過後，執行 mypy 和 ruff 確保程式碼品質
```

> 💡 **小提示**
>
> Claude Code 會真的去執行這些命令！如果你的專案已經設定好測試環境，這個流程可以完全自動化。

---

## 5.5 行為定義的常見錯誤

讓我們來看看一些常見的錯誤，以及如何避免。

### 錯誤 1：只描述「正常情況」

**問題指令：**
```
用戶輸入帳號密碼，系統驗證後回傳 token
```

**遺漏了什麼？**
- 密碼錯誤會怎樣？
- 帳號不存在會怎樣？
- 帳號被鎖定會怎樣？
- 輸入格式錯誤會怎樣？

**改進版本：**
```
【成功情況】
- 帳密正確：回傳 200 + access_token

【錯誤情況】
- 密碼錯誤：回傳 401 "Invalid credentials"
- 帳號不存在：回傳 401 "Invalid credentials"（不洩漏帳號存在與否）
- 帳號被鎖定：回傳 403 "Account locked"
- 輸入格式錯誤：回傳 422 + 具體的欄位錯誤訊息

【邊界情況】
- 連續 5 次失敗後鎖定帳號 30 分鐘
- Token 有效期 24 小時
```

---

### 錯誤 2：行為太模糊

**問題指令：**
```
搜尋結果要相關
```

**為什麼這是問題？**
「相關」是主觀的。AI 沒辦法驗證「相關性」。

**改進版本：**
```
【搜尋行為規格】

1. 搜尋範圍
   - 搜尋欄位：商品名稱、描述、SKU、分類名稱
   - 支援中文和英文

2. 排序規則（優先順序）
   a. 名稱完全匹配 > 名稱部分匹配 > 描述匹配
   b. 同等匹配度時，按銷量降序
   c. 同銷量時，按上架時間降序

3. 測試案例
   - 搜尋 "iPhone" 時，"iPhone 15" 要排在 "iPhone 保護殼" 前面
   - 搜尋 "藍牙耳機" 時，名稱含 "藍牙耳機" 的商品要排在描述含 "藍牙" 的前面
```

---

### 錯誤 3：效能標準不可測量

**問題指令：**
```
要處理得快一點，不能太慢
```

**改進版本：**
```
【效能標準】
- 單次查詢回應時間 < 100ms（在 100 萬筆資料量下）
- 必須使用資料庫索引（禁止全表掃描）
- 執行計劃必須是 Index Scan 或 Index Only Scan
```

---

### 錯誤 4：沒有考慮併發情況

**問題指令：**
```
用戶可以購買商品，購買後庫存減少
```

**遺漏了什麼？**
如果兩個用戶同時購買最後一件商品呢？

**改進版本：**
```
【庫存扣減行為】

1. 原子性操作
   - 檢查庫存和扣減必須是原子操作
   - 使用資料庫 transaction 或分散式鎖

2. 併發情況處理
   - 庫存不足時回傳 409 "Insufficient stock"
   - 不能出現「超賣」（庫存變成負數）

3. 測試案例
   test_concurrent_purchase():
       # 庫存只有 1 件
       # 10 個用戶同時購買
       # 預期結果：只有 1 個成功，其他 9 個失敗
       # 最終庫存 = 0（不是負數）
```

---

## 本章重點回顧

- **要點 1**：用 TDD/BDD 思維，在 AI 寫程式碼之前就定義好「什麼叫正確」。

- **要點 2**：效能標準要用可測量的指標（P95、RPS、錯誤率），不要用「快」、「好」這種模糊詞彙。

- **要點 3**：API 契約是定義 API 行為的最佳格式，包含請求/回應格式和所有錯誤情況。

- **要點 4**：讓 Claude Code 自動執行測試來驗證自己的產出，可以大幅提高效率和品質。

- **要點 5**：好的行為定義要涵蓋正常情況、錯誤情況、邊界情況、併發情況。

---

## 大腦體操 🧠

**問題 1：**
為什麼 P95 延遲比「平均延遲」更能反映真實用戶體驗？

**問題 2：**
以下行為定義缺少了什麼？請補充完整。
```
用戶可以修改個人資料，修改後儲存到資料庫
```

**問題 3：**
設計三個測試案例來驗證「購物車折扣碼功能」的行為。

---

## 下一章預告

你已經學會如何定義「做完是什麼樣子」。但 AI 要真正「做對」，還需要知道「在什麼環境下做」。

在下一章，我們將深入 **Context（上下文）**——如何提供完整的執行環境。你會學到如何描述技術棧、如何分享設計決策、以及如何建立團隊知識庫讓 AI 持續學習你的專案風格。

準備好打造 AI 的「工作環境」了嗎？

---

> 📝 **讀者筆記區**
>
> 你目前的專案有寫測試嗎？測試覆蓋率大約是多少？
>
> _________________________________
>
> 找一個你最近寫的 API，用本章學到的方式定義它的完整行為：
>
> 正常情況：_______________________
>
> 錯誤情況：_______________________
>
> 邊界情況：_______________________
