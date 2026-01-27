# 第七章：完整案例演練

**在這一章中，你將學會：**
- 案例一：用 I-B-C 框架開發 RESTful API
- 案例二：實作即時推薦系統
- 案例三：建立 WebSocket 聊天室
- 案例四：執行資料遷移與重構

> 💡 **開場白**
>
> 理論說得再多，不如動手做一次。
>
> 這一章，我們要把前面學到的所有東西整合起來。每個案例都是一個完整的 I-B-C 指令範本，你可以直接用在你的工作中。
>
> **準備好了嗎？讓我們開始實戰！**

---

## 7.1 案例一：RESTful API 開發

### 情境背景

你正在開發一個電商後台系統。PM 剛剛確認了新功能：**商品分類管理 API**。

需求很簡單：
- 可以新增、修改、刪除分類
- 分類可以有階層結構（最多三層）
- 要支援拖放排序

讓我們用 I-B-C 框架來設計指令。

### 完整 I-B-C 指令

```
【Intent（意圖）】

## User Story
作為一個電商後台管理員，
我希望能管理商品分類的階層結構，
這樣我就可以讓前台顧客更容易找到想要的商品。

## 業務背景
- 目前有約 500 個分類
- 分類結構最多三層（如：電子產品 > 手機 > 智慧型手機）
- 管理員需要能隨時調整分類順序和階層

## 優先順序
1. P0：基本 CRUD
2. P1：階層結構支援
3. P2：拖放排序

---

【Behavior（行為）】

## API 規格

### 1. 取得分類列表（含階層）
GET /api/admin/categories

Response 200:
{
  "data": [
    {
      "id": "uuid",
      "name": "電子產品",
      "slug": "electronics",
      "parent_id": null,
      "sort_order": 1,
      "depth": 0,
      "children": [
        {
          "id": "uuid",
          "name": "手機",
          "slug": "phones",
          "parent_id": "parent-uuid",
          "sort_order": 1,
          "depth": 1,
          "children": [...]
        }
      ]
    }
  ]
}

### 2. 新增分類
POST /api/admin/categories

Request:
{
  "name": "新分類",
  "parent_id": "uuid" | null,
  "slug": "new-category"  // 選填，不填會自動產生
}

Response 201:
{
  "data": { "id": "uuid", "name": "...", ... }
}

Errors:
- 400: name 為空或超過 100 字
- 400: slug 格式不正確（只能是小寫字母、數字、連字號）
- 409: slug 已存在
- 422: parent_id 不存在
- 422: 超過最大深度（3 層）

### 3. 更新分類
PUT /api/admin/categories/{id}

Request:
{
  "name": "更新的名稱",
  "slug": "updated-slug",
  "parent_id": "new-parent-uuid" | null
}

Response 200:
{
  "data": { "id": "uuid", "name": "...", ... }
}

Errors:
- 400: name 為空或超過 100 字
- 404: 分類不存在
- 409: slug 已存在
- 422: parent_id 不存在
- 422: parent_id 是自己或自己的子分類（避免循環）
- 422: 移動後超過最大深度

### 4. 刪除分類
DELETE /api/admin/categories/{id}

Response 204: (no content)

Errors:
- 404: 分類不存在
- 409: 分類下有子分類
- 409: 分類下有商品

### 5. 更新排序
PUT /api/admin/categories/reorder

Request:
{
  "items": [
    { "id": "uuid1", "sort_order": 1 },
    { "id": "uuid2", "sort_order": 2 }
  ]
}

Response 200:
{
  "data": [{ ... }, { ... }]
}

## 測試案例

def test_create_category_success():
    response = client.post("/api/admin/categories", json={
        "name": "測試分類"
    })
    assert response.status_code == 201
    assert response.json()["data"]["name"] == "測試分類"
    assert response.json()["data"]["slug"] == "ce-shi-fen-lei"  # 自動產生

def test_create_category_with_parent():
    parent = create_category("父分類")
    response = client.post("/api/admin/categories", json={
        "name": "子分類",
        "parent_id": parent.id
    })
    assert response.status_code == 201
    assert response.json()["data"]["depth"] == 1

def test_create_category_exceed_max_depth():
    # 建立三層分類
    level1 = create_category("Level 1")
    level2 = create_category("Level 2", parent_id=level1.id)
    level3 = create_category("Level 3", parent_id=level2.id)

    # 嘗試建立第四層
    response = client.post("/api/admin/categories", json={
        "name": "Level 4",
        "parent_id": level3.id
    })
    assert response.status_code == 422

def test_delete_category_with_children_fails():
    parent = create_category("父分類")
    child = create_category("子分類", parent_id=parent.id)

    response = client.delete(f"/api/admin/categories/{parent.id}")
    assert response.status_code == 409

def test_update_parent_avoid_circular():
    parent = create_category("父分類")
    child = create_category("子分類", parent_id=parent.id)

    # 嘗試把父分類移到子分類下
    response = client.put(f"/api/admin/categories/{parent.id}", json={
        "parent_id": child.id
    })
    assert response.status_code == 422

---

【Context（上下文）】

## 技術棧
- Python 3.11 + FastAPI
- SQLAlchemy 2.0 + PostgreSQL
- 現有專案結構遵循 .claude/ARCHITECTURE.md

## 現有架構
- 管理員 API 路由在 routers/admin/
- 現有的 routers/admin/products.py 可作為參考
- 使用 get_current_admin_user 作為認證依賴

## 資料庫設計

建議的 categories 表結構：
- id: UUID (PK)
- name: VARCHAR(100) NOT NULL
- slug: VARCHAR(100) UNIQUE NOT NULL
- parent_id: UUID FK(categories.id) NULLABLE
- sort_order: INTEGER DEFAULT 0
- depth: INTEGER DEFAULT 0  -- 快取深度，避免每次計算
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

建議索引：
- idx_categories_parent_id
- idx_categories_slug
- idx_categories_sort_order

## 注意事項
- slug 要支援中文轉拼音（使用 pypinyin 套件）
- 刪除前要檢查 products 表是否有關聯
- 所有寫入操作要記錄 audit log（呼叫 utils/audit.log_action）

## 檔案清單
請新增/修改以下檔案：
1. models/category.py - 資料模型
2. schemas/category.py - Pydantic schemas
3. services/category_service.py - 業務邏輯
4. routers/admin/categories.py - API 路由
5. tests/admin/test_categories.py - 測試

## 驗證要求
完成後請執行：
1. pytest tests/admin/test_categories.py -v
2. mypy src/
3. ruff check src/
```

### 這個指令的特點

1. **Intent** 清楚說明了業務背景和優先順序
2. **Behavior** 包含完整的 API 規格和測試案例
3. **Context** 提供了技術棧、資料庫設計、和需要注意的事項

---

## 7.2 案例二：即時推薦系統

### 情境背景

PM 說：「我們想在商品頁面顯示『看過這個商品的人也看了』的推薦。」

這是一個相對複雜的功能，涉及資料收集、演算法、和效能優化。

### 完整 I-B-C 指令

```
【Intent（意圖）】

## User Story
作為一個電商網站的顧客，
我希望在瀏覽商品時能看到「相關推薦」，
這樣我就可以發現更多我可能感興趣的商品。

## 業務目標
- 提升商品頁面的轉換率（目標：+15%）
- 增加用戶瀏覽深度（目標：平均瀏覽頁數 +2）

## 技術目標
- 推薦結果要「即時」更新（不是每日批次）
- 回應時間 < 100ms
- 推薦演算法初期先用協同過濾

---

【Behavior（行為）】

## 功能規格

### 1. 記錄瀏覽行為
當用戶瀏覽商品頁面時，記錄瀏覽事件。

觸發條件：
- 用戶停留在商品頁面超過 3 秒
- 同一用戶對同一商品，24 小時內只記錄一次

記錄資料：
- user_id（登入用戶）或 session_id（訪客）
- product_id
- timestamp
- source（從哪裡來：search, category, recommendation, direct）

### 2. 取得推薦商品
GET /api/products/{product_id}/recommendations?limit=6

Response 200:
{
  "data": [
    {
      "id": "uuid",
      "name": "商品名稱",
      "price": 1000,
      "image_url": "...",
      "score": 0.85  // 相關度分數
    }
  ],
  "meta": {
    "algorithm": "collaborative_filtering",
    "generated_at": "2026-01-27T10:00:00Z"
  }
}

### 3. 推薦演算法

使用 Item-Item Collaborative Filtering：

1. 建立商品共現矩陣
   - 如果用戶 A 看過商品 X 和商品 Y，則 X-Y 的共現次數 +1

2. 計算相似度
   - 使用餘弦相似度
   - similarity(X, Y) = count(X ∩ Y) / sqrt(count(X) * count(Y))

3. 取得推薦
   - 對於商品 X，找出相似度最高的 N 個商品
   - 排除已下架的商品
   - 排除庫存為 0 的商品

### 效能要求

| 指標 | 目標 |
|------|------|
| API 回應時間 | P95 < 100ms |
| 推薦新鮮度 | 最新瀏覽行為在 1 分鐘內反映 |
| 資料量支援 | 100 萬商品、1 億次瀏覽記錄 |

### 測試案例

def test_get_recommendations_success():
    # 模擬瀏覽歷史
    user1 = create_user()
    record_view(user1, product_a)
    record_view(user1, product_b)
    record_view(user1, product_c)

    user2 = create_user()
    record_view(user2, product_a)
    record_view(user2, product_b)

    # 取得 product_a 的推薦
    response = client.get(f"/api/products/{product_a.id}/recommendations")
    assert response.status_code == 200
    recommendations = response.json()["data"]

    # product_b 應該排名較高（兩個用戶都看過 a 和 b）
    assert recommendations[0]["id"] == product_b.id

def test_recommendations_exclude_out_of_stock():
    # 設定 product_b 庫存為 0
    product_b.stock = 0
    db.commit()

    response = client.get(f"/api/products/{product_a.id}/recommendations")
    product_ids = [p["id"] for p in response.json()["data"]]

    assert product_b.id not in product_ids

def test_recommendations_performance():
    # 產生大量測試資料
    generate_view_history(users=1000, products=10000, views_per_user=50)

    start = time.time()
    response = client.get(f"/api/products/{random_product.id}/recommendations")
    elapsed = time.time() - start

    assert response.status_code == 200
    assert elapsed < 0.1  # 100ms

---

【Context（上下文）】

## 技術選型

### 資料儲存
- 瀏覽記錄：使用 Redis Stream（適合高寫入、時間序列資料）
- 共現矩陣：使用 Redis Sorted Set
- 相似度快取：使用 Redis Hash

### 為什麼選 Redis？
1. 高寫入吞吐量（瀏覽記錄）
2. Sorted Set 天然適合相似度排序
3. 記憶體存取速度快，滿足 100ms 要求
4. 我們已有 Redis 基礎設施

### 不選 PostgreSQL 的原因
1. 高頻寫入會造成 WAL 壓力
2. 相似度計算需要大量 JOIN，效能不佳
3. 100ms 的延遲要求對關聯式資料庫是挑戰

## 架構設計

```
[用戶瀏覽] → [記錄服務] → [Redis Stream]
                              ↓
                    [背景任務：更新共現矩陣]
                              ↓
                    [Redis Sorted Set: 相似度]
                              ↓
[API 請求] → [推薦服務] → [取得 Top N]
```

## 現有程式碼參考
- Redis 連線：utils/redis_client.py
- 背景任務：使用 Celery（tasks/）
- 商品模型：models/product.py

## 檔案清單
1. services/recommendation_service.py - 推薦邏輯
2. services/view_tracking_service.py - 瀏覽追蹤
3. tasks/update_recommendations.py - 背景更新任務
4. routers/products.py - 新增推薦端點
5. tests/test_recommendations.py - 測試

## 注意事項
- 訪客（未登入）用 session_id 追蹤，需要處理 session 過期
- 共現矩陣更新是背景任務，不要阻塞 API 請求
- 考慮冷啟動問題（新商品沒有瀏覽記錄時的處理）
```

---

## 7.3 案例三：WebSocket 聊天室

### 情境背景

產品團隊要在電商 App 中加入「即時客服聊天」功能。

### 完整 I-B-C 指令

```
【Intent（意圖）】

## User Story
作為一個電商網站的顧客，
我希望能與客服即時文字聊天，
這樣我就可以快速解決購物過程中遇到的問題。

## 業務背景
- 目前客服只有電話和 email，回應時間長
- 目標是將客服回應時間從 2 小時縮短到 5 分鐘
- 預估同時在線聊天數：100 個

## 使用場景
1. 顧客發起聊天，等待客服接線
2. 客服看到等待列表，選擇接線
3. 雙方即時文字對話
4. 任一方可結束對話
5. 對話結束後，顧客可評分

---

【Behavior（行為）】

## WebSocket 協定

### 連線建立
ws://api.example.com/ws/chat?token={jwt_token}

認證：
- 顧客：使用顧客 JWT
- 客服：使用客服 JWT（包含 is_support_agent claim）

### 訊息格式

所有訊息都是 JSON 格式：

```json
{
  "type": "message_type",
  "payload": { ... },
  "timestamp": "2026-01-27T10:00:00Z"
}
```

### 顧客端訊息類型

1. 發起聊天
{
  "type": "start_chat",
  "payload": {
    "topic": "訂單問題",      // 選填
    "order_id": "uuid"        // 選填，關聯訂單
  }
}

2. 發送訊息
{
  "type": "send_message",
  "payload": {
    "content": "你好，我想問一下...",
    "message_type": "text"    // text, image
  }
}

3. 結束聊天
{
  "type": "end_chat",
  "payload": {
    "rating": 5,              // 1-5，選填
    "feedback": "服務很好"     // 選填
  }
}

### 客服端訊息類型

1. 接受聊天
{
  "type": "accept_chat",
  "payload": {
    "chat_id": "uuid"
  }
}

2. 發送訊息（同顧客）

3. 轉接
{
  "type": "transfer_chat",
  "payload": {
    "chat_id": "uuid",
    "to_agent_id": "uuid"
  }
}

### 伺服器推送訊息類型

1. 聊天狀態更新
{
  "type": "chat_status",
  "payload": {
    "chat_id": "uuid",
    "status": "waiting" | "active" | "ended",
    "agent": { "id": "uuid", "name": "客服小美" }  // 接線後
  }
}

2. 收到訊息
{
  "type": "new_message",
  "payload": {
    "chat_id": "uuid",
    "message_id": "uuid",
    "sender_type": "customer" | "agent",
    "content": "...",
    "timestamp": "..."
  }
}

3. 對方正在輸入
{
  "type": "typing",
  "payload": {
    "chat_id": "uuid",
    "is_typing": true
  }
}

4. 錯誤
{
  "type": "error",
  "payload": {
    "code": "CHAT_NOT_FOUND",
    "message": "聊天室不存在"
  }
}

## 效能與可靠性

| 指標 | 目標 |
|------|------|
| 訊息延遲 | < 200ms |
| 同時連線數 | 支援 1000 個 WebSocket 連線 |
| 訊息送達率 | 99.9% |
| 重連機制 | 斷線後 5 秒內自動重連，恢復聊天狀態 |

## 測試案例

async def test_customer_start_chat():
    async with websocket_client(customer_token) as ws:
        await ws.send_json({
            "type": "start_chat",
            "payload": {"topic": "訂單問題"}
        })

        response = await ws.receive_json()
        assert response["type"] == "chat_status"
        assert response["payload"]["status"] == "waiting"

async def test_agent_accept_and_message():
    # 顧客發起聊天
    customer_ws = await connect(customer_token)
    await customer_ws.send_json({"type": "start_chat", "payload": {}})
    status = await customer_ws.receive_json()
    chat_id = status["payload"]["chat_id"]

    # 客服接線
    agent_ws = await connect(agent_token)
    await agent_ws.send_json({
        "type": "accept_chat",
        "payload": {"chat_id": chat_id}
    })

    # 客服發訊息
    await agent_ws.send_json({
        "type": "send_message",
        "payload": {"content": "您好，有什麼可以幫您？"}
    })

    # 顧客收到訊息
    message = await customer_ws.receive_json()
    assert message["type"] == "new_message"
    assert message["payload"]["content"] == "您好，有什麼可以幫您？"

async def test_reconnect_restore_chat():
    # 建立聊天
    ws1 = await connect(customer_token)
    await ws1.send_json({"type": "start_chat", "payload": {}})
    status = await ws1.receive_json()
    chat_id = status["payload"]["chat_id"]

    # 斷線
    await ws1.close()

    # 重連
    ws2 = await connect(customer_token)
    # 伺服器應自動推送未完成的聊天狀態
    restored = await ws2.receive_json()
    assert restored["type"] == "chat_status"
    assert restored["payload"]["chat_id"] == chat_id

---

【Context（上下文）】

## 技術選型

### WebSocket 實作
- 使用 FastAPI 的 WebSocket 支援
- 使用 Redis Pub/Sub 做跨伺服器訊息傳遞（支援多實例部署）

### 資料儲存
- 聊天狀態：Redis Hash（即時存取）
- 聊天記錄：PostgreSQL（持久化）

### 架構圖

```
[顧客 App] ←──WebSocket──→ [API Server 1]
                                ↓
                          [Redis Pub/Sub] ←→ [API Server 2]
                                ↓
[客服後台] ←──WebSocket──→ [API Server 2]
```

## 現有程式碼
- JWT 驗證：utils/jwt.py
- Redis 連線：utils/redis_client.py

## 資料庫設計

### chats 表
- id: UUID PK
- customer_id: UUID FK(users)
- agent_id: UUID FK(users) NULLABLE
- status: ENUM('waiting', 'active', 'ended')
- topic: VARCHAR(200)
- order_id: UUID FK(orders) NULLABLE
- rating: INTEGER NULLABLE
- feedback: TEXT NULLABLE
- started_at: TIMESTAMP
- ended_at: TIMESTAMP NULLABLE

### chat_messages 表
- id: UUID PK
- chat_id: UUID FK(chats)
- sender_type: ENUM('customer', 'agent', 'system')
- sender_id: UUID
- content: TEXT
- message_type: ENUM('text', 'image', 'system')
- created_at: TIMESTAMP

## 檔案清單
1. models/chat.py - 資料模型
2. services/chat_service.py - 聊天業務邏輯
3. websockets/chat_handler.py - WebSocket 處理器
4. tasks/chat_cleanup.py - 清理過期聊天
5. tests/test_chat_websocket.py - WebSocket 測試
```

---

## 7.4 案例四：資料遷移與重構

### 情境背景

公司併購了另一家電商，需要將他們的用戶資料遷移到我們的系統。

### 完整 I-B-C 指令

```
【Intent（意圖）】

## 業務背景
我們併購了「好物商城」，需要將他們的 30 萬用戶資料遷移到我們的系統。

## 目標
1. 遷移所有用戶基本資料
2. 保留用戶的購買歷史（用於分析）
3. 不影響現有系統運作
4. 用戶遷移後可以用原本的帳號密碼登入

## 限制
- 遷移必須在週末進行（低流量時段）
- 不能有任何資料遺失
- 需要可以回滾

## 時程
- 遷移窗口：週六 02:00 - 06:00（4 小時）
- 資料量：30 萬用戶、200 萬筆訂單

---

【Behavior（行為）】

## 遷移流程

### Phase 1: 資料驗證（遷移前）
1. 連接來源資料庫
2. 統計來源資料量
3. 驗證資料完整性（必填欄位、格式）
4. 產生驗證報告

### Phase 2: 資料轉換
1. 讀取來源用戶資料
2. 欄位映射（見下方對照表）
3. 資料清洗
   - email 標準化（小寫）
   - 電話號碼格式統一
   - 處理空值
4. 處理衝突（email 已存在）

### Phase 3: 資料匯入
1. 批次寫入目標資料庫
2. 建立來源 ID 對照表
3. 遷移訂單資料（使用對照表）
4. 驗證匯入數量

### Phase 4: 驗證（遷移後）
1. 比對來源和目標的記錄數
2. 隨機抽樣 100 筆驗證資料正確性
3. 測試登入功能
4. 產生遷移報告

## 欄位映射

| 來源欄位 | 目標欄位 | 轉換規則 |
|----------|----------|----------|
| user_id | legacy_user_id | 直接對應 |
| (新產生) | id | UUID |
| email | email | 轉小寫 |
| pwd_hash | password_hash | 直接對應（兩邊都用 bcrypt） |
| name | full_name | 直接對應 |
| mobile | phone | 格式化為 +886xxxxxxxxx |
| create_time | created_at | timestamp 轉換 |
| status | status | 1→active, 0→inactive |

## 衝突處理規則

當 email 已存在時：
1. 如果兩邊的 password_hash 相同 → 視為同一用戶，建立關聯
2. 如果不同 → 標記為衝突，人工處理
3. 衝突記錄輸出到 conflicts.csv

## 效能要求

| 指標 | 目標 |
|------|------|
| 用戶遷移速度 | > 10,000 筆/分鐘 |
| 訂單遷移速度 | > 50,000 筆/分鐘 |
| 記憶體使用 | < 2GB |
| 資料庫連線 | < 20 個 |

## 測試案例

def test_email_normalization():
    source = {"email": "Test@Example.COM"}
    result = transform_user(source)
    assert result["email"] == "test@example.com"

def test_phone_format():
    # 各種輸入格式
    assert format_phone("0912345678") == "+886912345678"
    assert format_phone("886912345678") == "+886912345678"
    assert format_phone("+886912345678") == "+886912345678"
    assert format_phone("09-1234-5678") == "+886912345678"

def test_conflict_detection():
    # 目標資料庫已有用戶
    existing_user = create_user(email="test@example.com", password_hash="hash_a")

    # 來源有相同 email 但不同密碼
    source_user = {"email": "test@example.com", "pwd_hash": "hash_b"}

    result = migrate_user(source_user)
    assert result["status"] == "conflict"
    assert "conflicts.csv" has entry for this user

def test_migration_can_rollback():
    # 執行遷移
    run_migration()
    assert get_user_count() == original_count + migrated_count

    # 執行回滾
    rollback_migration()
    assert get_user_count() == original_count

---

【Context（上下文）】

## 資料庫連線

### 來源資料庫（好物商城）
- PostgreSQL 12
- Host: legacy-db.internal
- Database: haowu_production
- 只讀權限

### 目標資料庫（我們的系統）
- PostgreSQL 15
- Host: main-db.internal
- Database: our_production

## 來源資料庫結構

```sql
-- 來源用戶表
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    pwd_hash VARCHAR(255),
    name VARCHAR(100),
    mobile VARCHAR(20),
    status SMALLINT,
    create_time TIMESTAMP
);

-- 來源訂單表
CREATE TABLE orders (
    order_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    total_amount DECIMAL(10,2),
    status VARCHAR(20),
    create_time TIMESTAMP
);
```

## 目標資料庫結構

（參考現有的 models/user.py 和 models/order.py）

新增欄位：
- users.legacy_user_id: BIGINT（追蹤來源用戶 ID）
- users.migrated_at: TIMESTAMP（遷移時間）
- users.source_system: VARCHAR(50)（來源系統標識）

## 程式碼組織

```
scripts/migration/
├── config.py           # 資料庫連線設定
├── validators.py       # 資料驗證
├── transformers.py     # 欄位轉換
├── migrator.py         # 主遷移邏輯
├── rollback.py         # 回滾腳本
└── reports.py          # 報告產生
```

## 執行方式

```bash
# 驗證（不實際遷移）
python -m scripts.migration.migrator --dry-run

# 正式遷移
python -m scripts.migration.migrator --batch-size=1000

# 回滾
python -m scripts.migration.rollback --migration-id=xxx
```

## 注意事項
- 使用 batch insert 而非逐筆 insert
- 使用 transaction，每 10,000 筆 commit 一次
- 遷移過程要有詳細的 log
- 密碼 hash 不需要重新加密（兩邊都用 bcrypt）
- 所有時間都要轉成 UTC
```

---

## 本章重點回顧

- **要點 1**：完整的 I-B-C 指令讓 AI 可以「一次做對」，減少來回修正。

- **要點 2**：不同類型的任務（CRUD、即時系統、WebSocket、資料遷移）有不同的關注點，但都可以套用 I-B-C 框架。

- **要點 3**：測試案例是 Behavior 的核心，讓 AI 有明確的驗收標準。

- **要點 4**：Context 要包含技術選型的原因，幫助 AI 做出正確的決策。

---

## 大腦體操 🧠

**問題 1：**
在案例一中，為什麼要用 `depth` 欄位快取深度，而不是每次計算？

**問題 2：**
在案例二的推薦系統中，「冷啟動問題」是什麼？你會怎麼處理？

**問題 3：**
選擇一個你目前正在做的功能，用 I-B-C 框架寫一個完整的指令。

---

## 下一章預告

你已經學會了如何用 I-B-C 框架設計單一任務的指令。但在真實專案中，你面對的往往是一整個 PRD（產品需求文件）。

在下一章，我們將學習如何**從 PRD 到可執行任務清單**——把大需求拆解成小任務，讓 AI 可以逐步完成。

準備好處理更大的挑戰了嗎？

---

> 📝 **讀者筆記區**
>
> 四個案例中，哪一個最接近你目前的工作？
>
> _________________________________
>
> 嘗試為那個案例增加一個你實際需要的功能點：
>
> _________________________________
