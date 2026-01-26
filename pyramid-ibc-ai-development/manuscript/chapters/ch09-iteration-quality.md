# 第九章：迭代修正與品質守門

**在這一章中，你將學會：**
- 三層次 Code Review 方法
- 功能驗證、效能驗證、架構驗證的實踐
- 建立實用的 Review Checklist
- 給 AI 建設性回饋的技巧
- 識別和處理常見的程式碼異味

> 💡 **開場白**
>
> AI 不是神。它產出的程式碼可能有 bug、可能效能不佳、可能不符合最佳實踐。
>
> 但這不是 AI 的錯——這是協作的本質。即使是最優秀的人類工程師，code review 也是必要的。
>
> 差別在於：**你需要學會如何有效地 review AI 的程式碼，並給出它能理解和執行的回饋。**

---

## 9.1 三層次 Code Review 方法

Review AI 產出的程式碼時，我建議採用「三層次」的方法：

```
┌─────────────────────────────────────────────────────────────┐
│                    三層次 Code Review                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  第一層：功能驗證                                            │
│  └── 程式碼做的事情對不對？                                  │
│                                                             │
│  第二層：效能驗證                                            │
│  └── 程式碼跑得夠快嗎？資源使用合理嗎？                      │
│                                                             │
│  第三層：架構驗證                                            │
│  └── 程式碼設計得好嗎？可維護嗎？可擴展嗎？                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 為什麼要分層？

因為不同層次的問題有不同的優先順序和修復成本。

| 層次 | 問題類型 | 修復成本 | 優先順序 |
|------|----------|----------|----------|
| 功能驗證 | Bug、邏輯錯誤 | 低 | 最高 |
| 效能驗證 | 效能問題、資源浪費 | 中 | 中 |
| 架構驗證 | 設計問題、技術債 | 高 | 看情況 |

**經驗法則：**
- 功能問題一定要修（不修就是 bug）
- 效能問題看嚴重程度（如果在可接受範圍內，可以之後優化）
- 架構問題要權衡（有時候「夠用」比「完美」更重要）

---

## 9.2 功能驗證、效能驗證、架構驗證

讓我們詳細看看每個層次怎麼做。

### 第一層：功能驗證

**目標：** 程式碼是否正確實作了需求？

**方法：**

1. **閱讀程式碼邏輯**
   - 主要流程是否正確？
   - 邊界情況有沒有處理？
   - 錯誤處理完整嗎？

2. **執行測試**
   ```bash
   pytest tests/ -v
   ```

3. **手動測試**
   - 正常情況
   - 邊界情況
   - 錯誤情況

**常見功能問題：**

```python
# ❌ 問題 1：沒有處理空值
def get_user_name(user):
    return user.profile.name  # 如果 profile 是 None 會爆炸

# ✅ 修正
def get_user_name(user):
    if user.profile:
        return user.profile.name
    return None

# ❌ 問題 2：邏輯錯誤
def is_adult(age):
    return age > 18  # 應該是 >= 18

# ✅ 修正
def is_adult(age):
    return age >= 18

# ❌ 問題 3：沒有處理例外
def divide(a, b):
    return a / b  # 除以零會爆炸

# ✅ 修正
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

---

### 第二層：效能驗證

**目標：** 程式碼的效能是否在可接受範圍內？

**方法：**

1. **靜態分析**
   - 時間複雜度是否合理？
   - 有沒有 N+1 查詢？
   - 有沒有不必要的迴圈？

2. **效能測試**
   ```bash
   # 使用 pytest-benchmark
   pytest tests/benchmarks/ --benchmark-only

   # 或使用 k6 做負載測試
   k6 run load_test.js
   ```

3. **Profiling**
   ```python
   # 使用 cProfile
   python -m cProfile -s cumtime your_script.py
   ```

**常見效能問題：**

```python
# ❌ 問題 1：N+1 查詢
def get_orders_with_users(order_ids):
    orders = Order.query.filter(Order.id.in_(order_ids)).all()
    for order in orders:
        print(order.user.name)  # 每次都查一次 user 表！

# ✅ 修正：使用 eager loading
def get_orders_with_users(order_ids):
    orders = Order.query.options(
        joinedload(Order.user)
    ).filter(Order.id.in_(order_ids)).all()
    for order in orders:
        print(order.user.name)  # 只查一次

# ❌ 問題 2：在迴圈中做昂貴操作
def process_items(items):
    for item in items:
        # 每次都重新連接資料庫！
        db = get_database_connection()
        db.save(item)

# ✅ 修正：批次處理
def process_items(items):
    db = get_database_connection()
    for item in items:
        db.add(item)
    db.commit()  # 一次提交

# ❌ 問題 3：沒有使用索引
# SQL: SELECT * FROM users WHERE email = 'test@example.com'
# 如果 email 欄位沒有索引，會做全表掃描

# ✅ 修正：確保有索引
# CREATE INDEX idx_users_email ON users(email);
```

---

### 第三層：架構驗證

**目標：** 程式碼的設計是否良好、可維護？

**方法：**

1. **程式碼結構**
   - 函數長度是否適當？（建議 < 30 行）
   - 職責是否單一？
   - 命名是否清晰？

2. **設計模式**
   - 是否遵循 SOLID 原則？
   - 是否有適當的抽象？
   - 是否易於測試？

3. **可維護性**
   - 新人能看懂嗎？
   - 修改一個功能需要改多少地方？
   - 有沒有「魔法數字」或「魔法字串」？

**常見架構問題：**

```python
# ❌ 問題 1：上帝函數（做太多事）
def process_order(order_data):
    # 驗證
    if not order_data.get('user_id'):
        raise ValueError("Missing user_id")
    if not order_data.get('items'):
        raise ValueError("Missing items")
    # ...驗證邏輯 50 行...

    # 計算價格
    total = 0
    for item in order_data['items']:
        product = get_product(item['product_id'])
        total += product.price * item['quantity']
    # ...價格計算 30 行...

    # 套用折扣
    discount = get_user_discount(order_data['user_id'])
    total = total * (1 - discount)
    # ...折扣邏輯 20 行...

    # 建立訂單
    order = Order(...)
    db.save(order)
    # ...訂單建立 20 行...

    # 發送通知
    send_email(...)
    send_push_notification(...)
    # ...通知邏輯 20 行...

    return order

# ✅ 修正：拆分成小函數
def process_order(order_data):
    validate_order_data(order_data)
    total = calculate_order_total(order_data['items'])
    total = apply_discount(total, order_data['user_id'])
    order = create_order(order_data, total)
    send_order_notifications(order)
    return order

# ❌ 問題 2：魔法數字
def calculate_shipping(distance):
    if distance < 10:
        return 60
    elif distance < 50:
        return 100
    else:
        return 150

# ✅ 修正：使用常數
SHIPPING_ZONES = {
    'local': {'max_distance': 10, 'fee': 60},
    'regional': {'max_distance': 50, 'fee': 100},
    'national': {'max_distance': float('inf'), 'fee': 150},
}

def calculate_shipping(distance):
    for zone in SHIPPING_ZONES.values():
        if distance < zone['max_distance']:
            return zone['fee']

# ❌ 問題 3：緊耦合
class OrderService:
    def create_order(self, data):
        # 直接依賴具體實作
        email_service = SmtpEmailService()
        email_service.send(...)

# ✅ 修正：依賴注入
class OrderService:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    def create_order(self, data):
        self.email_service.send(...)
```

---

## 9.3 建立 Review Checklist

把上面的驗證點整理成一個 checklist，可以幫助你系統化地 review。

### 通用 Review Checklist

```markdown
## Code Review Checklist

### 功能驗證
- [ ] 主要功能是否正確實作？
- [ ] 邊界情況是否處理？
  - [ ] 空值
  - [ ] 空陣列
  - [ ] 極大/極小值
- [ ] 錯誤處理是否完整？
  - [ ] 輸入驗證
  - [ ] 例外捕獲
  - [ ] 錯誤訊息清晰
- [ ] 測試是否通過？
- [ ] 測試覆蓋率是否足夠？

### 效能驗證
- [ ] 時間複雜度是否合理？
- [ ] 沒有 N+1 查詢？
- [ ] 沒有在迴圈中做昂貴操作？
- [ ] 適當使用快取？
- [ ] 資料庫查詢有使用索引？

### 架構驗證
- [ ] 函數長度 < 30 行？
- [ ] 單一職責原則？
- [ ] 命名清晰易懂？
- [ ] 沒有魔法數字/字串？
- [ ] 適當的註解和文件？
- [ ] 符合團隊的 coding style？

### 安全性
- [ ] 沒有 SQL injection 風險？
- [ ] 沒有 XSS 風險？
- [ ] 敏感資料有加密？
- [ ] 權限檢查正確？
```

### 讓 AI 自我 Review

你可以讓 Claude Code 用這個 checklist 檢查自己的程式碼：

```
請用以下 checklist 檢查你剛才寫的程式碼：

[貼上你的 checklist]

對於每一項，請說明：
1. 是否通過（✅/❌）
2. 如果沒通過，問題是什麼
3. 如何修正
```

---

## 9.4 給 AI 建設性回饋的技巧

當你發現 AI 產出的程式碼有問題時，如何有效地溝通？

### 錯誤的回饋方式

```
❌ "這個不對"
❌ "重寫"
❌ "再試一次"
```

這些回饋的問題：
- 沒有說明**哪裡**不對
- 沒有說明**為什麼**不對
- 沒有說明**怎麼**改

### 正確的回饋方式

**結構化回饋模板：**

```
【問題】
描述問題是什麼

【位置】
問題在哪裡（檔案、行數、函數名）

【原因】
為什麼這是問題

【期望】
你期望的正確行為

【建議】
（可選）你建議的修正方向
```

**實際範例：**

```
【問題】
get_user_orders 函數有 N+1 查詢問題

【位置】
services/order_service.py 第 45-50 行

【原因】
目前的實作在迴圈中逐個查詢 user，當有 100 個訂單時會產生 101 次資料庫查詢。
這會嚴重影響效能。

【期望】
一次查詢就取得所有需要的 user 資料，或使用 SQLAlchemy 的 eager loading。

【建議】
使用 joinedload 或 selectinload 來預先載入 user 關聯。
```

### 批量回饋

如果有多個問題，整理成清單：

```
我 review 了你剛才的程式碼，發現以下問題：

1. 【重要】N+1 查詢問題
   - 位置：services/order_service.py:45
   - 說明：迴圈中查詢 user，應該用 eager loading

2. 【建議】命名不清晰
   - 位置：services/order_service.py:20
   - 說明：`d` 應該改成 `discount_percentage`

3. 【建議】缺少錯誤處理
   - 位置：services/order_service.py:60
   - 說明：沒有處理 user_id 不存在的情況

請依照優先順序修正這些問題。
```

---

## 9.5 常見的程式碼異味與重構建議

**程式碼異味**（Code Smell）是指程式碼雖然「能跑」，但設計上有問題的跡象。

### 異味 1：重複程式碼

```python
# ❌ 異味
def get_admin_users():
    users = User.query.filter(User.role == 'admin').all()
    result = []
    for user in users:
        result.append({
            'id': user.id,
            'name': user.name,
            'email': user.email
        })
    return result

def get_regular_users():
    users = User.query.filter(User.role == 'user').all()
    result = []
    for user in users:
        result.append({
            'id': user.id,
            'name': user.name,
            'email': user.email
        })
    return result

# ✅ 重構
def get_users_by_role(role: str):
    users = User.query.filter(User.role == role).all()
    return [serialize_user(user) for user in users]

def serialize_user(user):
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email
    }
```

### 異味 2：過長的參數列表

```python
# ❌ 異味
def create_order(user_id, product_id, quantity, shipping_address,
                 billing_address, payment_method, coupon_code,
                 notes, gift_wrap, delivery_date):
    ...

# ✅ 重構：使用資料類
@dataclass
class OrderRequest:
    user_id: str
    product_id: str
    quantity: int
    shipping_address: Address
    billing_address: Address
    payment_method: str
    coupon_code: str = None
    notes: str = None
    gift_wrap: bool = False
    delivery_date: date = None

def create_order(request: OrderRequest):
    ...
```

### 異味 3：布林參數

```python
# ❌ 異味
def get_users(include_inactive=False, include_deleted=False,
              include_admins=False, sort_by_name=False):
    ...

# 呼叫時很難讀
users = get_users(True, False, True, True)  # 這什麼意思？

# ✅ 重構：使用 Enum 或配置物件
class UserFilter:
    include_inactive: bool = False
    include_deleted: bool = False
    include_admins: bool = False

class UserSort(Enum):
    CREATED_AT = 'created_at'
    NAME = 'name'

def get_users(filter: UserFilter = None, sort_by: UserSort = None):
    ...

# 呼叫時更清楚
filter = UserFilter(include_admins=True)
users = get_users(filter=filter, sort_by=UserSort.NAME)
```

### 異味 4：註解掉的程式碼

```python
# ❌ 異味
def calculate_price(product, quantity):
    price = product.base_price * quantity

    # 舊的折扣邏輯，2023/05 棄用
    # if product.on_sale:
    #     price = price * 0.9
    #
    # if quantity > 10:
    #     price = price * 0.95

    return apply_current_discount(price)

# ✅ 重構：直接刪除
# 如果需要追蹤歷史，用 Git
def calculate_price(product, quantity):
    price = product.base_price * quantity
    return apply_current_discount(price)
```

---

## 本章重點回顧

- **要點 1**：用三層次方法 review——功能驗證、效能驗證、架構驗證。

- **要點 2**：建立 Review Checklist，系統化地檢查程式碼品質。

- **要點 3**：給 AI 建設性回饋，說明問題、位置、原因、期望。

- **要點 4**：識別程式碼異味，及時重構避免技術債累積。

---

## 大腦體操 🧠

**問題 1：**
以下程式碼有什麼問題？屬於三個層次中的哪一層？

```python
def get_user_orders(user_id):
    user = User.query.get(user_id)
    orders = Order.query.filter(Order.user_id == user_id).all()
    for order in orders:
        order.user_name = user.name
    return orders
```

**問題 2：**
設計一個針對「API 開發」的 Review Checklist，至少包含 10 個檢查項目。

**問題 3：**
以下回饋有什麼問題？如何改進？
```
這段程式碼太慢了，改一下
```

---

## 下一章預告

你已經學會了如何 review 和修正 AI 的產出。但如果每次都要手動檢查，效率還是有限。

在下一章（也是最後一章），我們將學習如何把這些品質檢查**自動化**——整合到 CI/CD 流程中，讓 AI 的每一次產出都自動通過品質守門。

準備好建立你的自動化品質防線了嗎？

---

> 📝 **讀者筆記區**
>
> 你在 review AI 程式碼時最常發現什麼問題？
>
> _________________________________
>
> 你的團隊有 Review Checklist 嗎？有哪些項目？
>
> _________________________________
