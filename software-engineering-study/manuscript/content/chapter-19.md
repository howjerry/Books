# 第19章　軟體測試——元件層級

> 「單元測試不是找 bug 的工具，而是設計的工具。好的測試迫使你寫出好的程式碼。」

---

## 19.1 什麼是元件層級測試？

### 19.1.1 測試的層次

```
                    ┌─────────────┐
                   ╱               ╲
                  ╱    E2E 測試     ╲
                 ╱   (使用者流程)    ╲
                ╱─────────────────────╲
               ╱                       ╲
              ╱      整合測試           ╲
             ╱    (元件間互動)          ╲
            ╱───────────────────────────╲
           ╱                             ╲
          ╱          單元測試             ╲
         ╱        (最小可測試單元)         ╲
        ╱───────────────────────────────────╲
```

| 層次 | 目的 | 範圍 | 數量 |
|------|------|------|------|
| **單元測試** | 驗證最小單元 | 函式/類別 | 多 |
| **整合測試** | 驗證元件互動 | 模組間 | 中 |
| **E2E 測試** | 驗證使用者流程 | 整個系統 | 少 |

### 19.1.2 元件測試的定義

**元件測試（Component Testing）**：也稱為單元測試（Unit Testing），驗證軟體最小可測試單元的正確性。

**「單元」是什麼？**

| 語言 | 常見單元 |
|------|----------|
| 程序式 | 函式 |
| 物件導向 | 類別/方法 |
| 函數式 | 函式/模組 |

### 19.1.3 為什麼要寫單元測試？

| 好處 | 說明 |
|------|------|
| **早期發現** | 在開發階段發現問題 |
| **文件作用** | 測試即文件 |
| **設計驅動** | 迫使寫可測試的程式碼 |
| **重構信心** | 有測試才敢改 |
| **回歸預防** | 防止舊 bug 復發 |

---

## 19.2 測試驅動開發（TDD）

### 19.2.1 TDD 循環

```
┌──────────────────────────────────────────────────────────────┐
│                      TDD 循環                                 │
│                                                              │
│           ┌─────────┐                                        │
│           │   Red   │  1. 寫一個失敗的測試                    │
│           │  (紅燈)  │                                        │
│           └────┬────┘                                        │
│                │                                              │
│                ▼                                              │
│           ┌─────────┐                                        │
│           │  Green  │  2. 寫最少的程式碼讓測試通過             │
│           │  (綠燈)  │                                        │
│           └────┬────┘                                        │
│                │                                              │
│                ▼                                              │
│           ┌─────────┐                                        │
│           │Refactor │  3. 重構程式碼                          │
│           │  (重構)  │                                        │
│           └────┬────┘                                        │
│                │                                              │
│                └──────────────────────────────────────────►  │
│                              重複循環                         │
└──────────────────────────────────────────────────────────────┘
```

### 19.2.2 TDD 範例

**需求**：計算購物車總價

**Step 1: Red（寫失敗的測試）**

```python
# test_cart.py
def test_empty_cart_total_is_zero():
    cart = ShoppingCart()
    assert cart.total() == 0
```

執行測試：❌ 失敗（ShoppingCart 不存在）

**Step 2: Green（讓測試通過）**

```python
# cart.py
class ShoppingCart:
    def total(self):
        return 0
```

執行測試：✅ 通過

**Step 3: 下一個測試**

```python
def test_cart_with_one_item():
    cart = ShoppingCart()
    cart.add_item(Item("蘋果", 30))
    assert cart.total() == 30
```

執行測試：❌ 失敗

**Step 4: 實作**

```python
class ShoppingCart:
    def __init__(self):
        self.items = []

    def add_item(self, item):
        self.items.append(item)

    def total(self):
        return sum(item.price for item in self.items)
```

執行測試：✅ 通過

### 19.2.3 TDD 的好處

| 好處 | 說明 |
|------|------|
| **設計導向** | 先想介面再實作 |
| **覆蓋率高** | 每個功能都有測試 |
| **小步前進** | 降低風險 |
| **即時回饋** | 快速知道對錯 |

---

## 19.3 測試設計技術

### 19.3.1 等價類別劃分

將輸入分成等價類別，每類測一個代表值。

**範例**：年齡驗證（18-65 歲為有效）

| 類別 | 範圍 | 測試值 |
|------|------|--------|
| 無效（太小） | < 18 | 17 |
| 有效 | 18-65 | 30 |
| 無效（太大） | > 65 | 66 |
| 無效（負數） | < 0 | -1 |

```python
def test_age_validation():
    # 無效類別
    assert is_valid_age(17) == False
    assert is_valid_age(66) == False
    assert is_valid_age(-1) == False

    # 有效類別
    assert is_valid_age(30) == True
```

### 19.3.2 邊界值分析

在等價類別的邊界上測試。

**範例**：年齡驗證邊界

| 邊界 | 測試值 |
|------|--------|
| 最小有效 | 18 |
| 最小有效-1 | 17 |
| 最大有效 | 65 |
| 最大有效+1 | 66 |

```python
def test_age_boundaries():
    # 邊界
    assert is_valid_age(17) == False  # 邊界外
    assert is_valid_age(18) == True   # 邊界上
    assert is_valid_age(65) == True   # 邊界上
    assert is_valid_age(66) == False  # 邊界外
```

### 19.3.3 決策表測試

當有多個條件組合時使用。

**範例**：折扣計算

| VIP會員 | 購買金額 > 1000 | 折扣 |
|---------|-----------------|------|
| N | N | 0% |
| N | Y | 5% |
| Y | N | 10% |
| Y | Y | 15% |

```python
def test_discount_combinations():
    # 非VIP + 低金額
    assert calculate_discount(is_vip=False, amount=500) == 0

    # 非VIP + 高金額
    assert calculate_discount(is_vip=False, amount=1500) == 0.05

    # VIP + 低金額
    assert calculate_discount(is_vip=True, amount=500) == 0.10

    # VIP + 高金額
    assert calculate_discount(is_vip=True, amount=1500) == 0.15
```

### 19.3.4 狀態轉換測試

測試狀態機的轉換。

**範例**：訂單狀態

```
┌────────┐  付款成功  ┌────────┐  出貨   ┌────────┐
│ 待付款 │──────────►│ 已付款 │───────►│ 已出貨 │
└────────┘           └────────┘        └────────┘
    │                                       │
    │ 取消                                  │ 送達
    ▼                                       ▼
┌────────┐                            ┌────────┐
│ 已取消 │                            │ 已完成 │
└────────┘                            └────────┘
```

```python
def test_order_state_transitions():
    order = Order()

    assert order.state == "pending"

    order.pay()
    assert order.state == "paid"

    order.ship()
    assert order.state == "shipped"

    order.deliver()
    assert order.state == "completed"

def test_order_cancellation():
    order = Order()
    order.cancel()
    assert order.state == "cancelled"

def test_cannot_ship_unpaid_order():
    order = Order()
    with pytest.raises(InvalidStateError):
        order.ship()
```

---

## 19.4 測試替身（Test Doubles）

### 19.4.1 為什麼需要測試替身？

當被測試單元依賴外部資源時：
- 資料庫
- 網路 API
- 檔案系統
- 時間

需要用「替身」隔離這些依賴。

### 19.4.2 測試替身類型

| 類型 | 說明 | 用途 |
|------|------|------|
| **Dummy** | 佔位，不使用 | 填補參數 |
| **Stub** | 回傳預設值 | 控制依賴輸出 |
| **Spy** | 記錄呼叫 | 驗證互動 |
| **Mock** | 預設期望 | 驗證行為 |
| **Fake** | 簡化實作 | 替代複雜依賴 |

### 19.4.3 Stub 範例

```python
# 被測試的程式碼
class WeatherService:
    def get_temperature(self, city):
        # 呼叫真實 API
        response = requests.get(f"https://api.weather.com/{city}")
        return response.json()["temp"]

class Recommendation:
    def __init__(self, weather_service):
        self.weather = weather_service

    def suggest(self, city):
        temp = self.weather.get_temperature(city)
        if temp > 30:
            return "建議穿短袖"
        return "建議穿長袖"
```

```python
# 測試用 Stub
class StubWeatherService:
    def __init__(self, temp):
        self.temp = temp

    def get_temperature(self, city):
        return self.temp

def test_hot_weather_suggestion():
    stub = StubWeatherService(35)
    rec = Recommendation(stub)
    assert rec.suggest("Taipei") == "建議穿短袖"

def test_cold_weather_suggestion():
    stub = StubWeatherService(20)
    rec = Recommendation(stub)
    assert rec.suggest("Taipei") == "建議穿長袖"
```

### 19.4.4 Mock 範例

```python
from unittest.mock import Mock

def test_notification_sent():
    # Mock 郵件服務
    email_service = Mock()

    order = Order(email_service)
    order.complete()

    # 驗證郵件服務被呼叫
    email_service.send.assert_called_once_with(
        to=order.customer_email,
        subject="訂單完成",
        body="您的訂單已完成"
    )
```

---

## 19.5 測試的 F.I.R.S.T 原則

| 原則 | 說明 |
|------|------|
| **F**ast | 快速：毫秒級執行 |
| **I**ndependent | 獨立：測試間不依賴 |
| **R**epeatable | 可重複：任何環境都能跑 |
| **S**elf-validating | 自我驗證：通過或失敗，沒有手動檢查 |
| **T**imely | 及時：在程式碼之前或同時寫 |

### 19.5.1 Fast（快速）

```python
# ❌ 慢的測試
def test_with_real_db():
    db = connect_to_database()  # 慢
    user = db.query("SELECT * FROM users")
    assert user is not None

# ✅ 快的測試
def test_with_stub():
    db = InMemoryDatabase()  # 快
    user = db.query("SELECT * FROM users")
    assert user is not None
```

### 19.5.2 Independent（獨立）

```python
# ❌ 相依的測試
class TestCart:
    cart = None  # 共享狀態！

    def test_add_item(self):
        TestCart.cart = ShoppingCart()
        TestCart.cart.add_item(item)
        assert len(TestCart.cart.items) == 1

    def test_total(self):
        # 依賴上一個測試的狀態
        assert TestCart.cart.total() == 30

# ✅ 獨立的測試
class TestCart:
    def test_add_item(self):
        cart = ShoppingCart()  # 每個測試自己建立
        cart.add_item(item)
        assert len(cart.items) == 1

    def test_total(self):
        cart = ShoppingCart()  # 每個測試自己建立
        cart.add_item(Item("蘋果", 30))
        assert cart.total() == 30
```

### 19.5.3 Repeatable（可重複）

```python
# ❌ 不可重複（依賴時間）
def test_is_morning():
    assert is_morning() == True  # 下午跑會失敗

# ✅ 可重複（注入時間）
def test_is_morning():
    fake_clock = FakeClock(hour=9)
    assert is_morning(clock=fake_clock) == True

def test_is_not_morning():
    fake_clock = FakeClock(hour=15)
    assert is_morning(clock=fake_clock) == False
```

---

## 19.6 測試覆蓋率

### 19.6.1 覆蓋率類型

| 類型 | 說明 |
|------|------|
| **行覆蓋率** | 執行過的程式碼行數比例 |
| **分支覆蓋率** | 執行過的分支比例 |
| **條件覆蓋率** | 每個條件的真假都測過 |
| **路徑覆蓋率** | 執行過的路徑比例 |

### 19.6.2 覆蓋率的限制

```python
def divide(a, b):
    return a / b

def test_divide():
    assert divide(10, 2) == 5

# 行覆蓋率 100%，但沒測試 b=0 的情況！
```

**覆蓋率高 ≠ 測試品質好**

| 問題 | 說明 |
|------|------|
| 邊界沒測 | 只測正常路徑 |
| 斷言不足 | 執行了但沒驗證 |
| 語意遺漏 | 技術上覆蓋，邏輯上遺漏 |

### 19.6.3 合理的覆蓋率目標

| 情境 | 建議覆蓋率 |
|------|-----------|
| 核心業務邏輯 | > 90% |
| 一般功能 | > 80% |
| UI 程式碼 | > 60% |
| 整體 | > 80% |

---

## 19.7 測試的組織

### 19.7.1 測試結構（AAA）

```python
def test_add_item_to_cart():
    # Arrange（準備）
    cart = ShoppingCart()
    item = Item("蘋果", 30)

    # Act（執行）
    cart.add_item(item)

    # Assert（驗證）
    assert len(cart.items) == 1
    assert cart.items[0].name == "蘋果"
```

### 19.7.2 測試命名

```python
# ❌ 不好的命名
def test_1():
def test_cart():

# ✅ 好的命名
def test_empty_cart_returns_zero_total():
def test_add_item_increases_count_by_one():
def test_remove_nonexistent_item_raises_error():
```

**命名格式**：`test_[被測功能]_[情境]_[預期結果]`

### 19.7.3 測試檔案組織

```
project/
├── src/
│   ├── cart.py
│   ├── order.py
│   └── payment.py
└── tests/
    ├── test_cart.py
    ├── test_order.py
    └── test_payment.py
```

---

## 19.8 本章總結

### 核心概念

| 概念 | 一句話解釋 |
|------|-----------|
| 單元測試 | 驗證最小可測試單元 |
| TDD | 先寫測試再寫程式碼 |
| 等價類別 | 分類輸入，每類測一個 |
| 邊界值 | 測試邊界上的值 |
| 測試替身 | 隔離外部依賴 |
| FIRST | 快速、獨立、可重複、自驗證、及時 |

### 單元測試 Checklist

| 項目 | 問題 |
|------|------|
| 獨立性 | 測試間是否獨立？ |
| 速度 | 是否毫秒級執行？ |
| 可重複 | 任何環境都能跑嗎？ |
| 邊界 | 邊界值測了嗎？ |
| 替身 | 外部依賴有隔離嗎？ |
| 命名 | 能從名稱知道測什麼嗎？ |

### 下一章預告

單元測試驗證個別元件，但元件之間如何互動？下一章我們將學習「軟體測試——整合層級」。

---

## 延伸思考

1. 你的團隊有做 TDD 嗎？效果如何？

2. 你的測試覆蓋率是多少？足夠嗎？

3. 你遇過「測試通過但生產環境出問題」的情況嗎？為什麼？

---

*下一章：第20章　軟體測試——整合層級*
