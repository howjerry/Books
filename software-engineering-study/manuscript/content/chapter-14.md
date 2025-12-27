# 第14章　以樣式（Pattern）為基礎的設計

> 「設計模式不是發明，而是發現。它們是經過驗證的解決方案，幫助我們站在巨人的肩膀上。」

---

## 14.1 什麼是設計模式？

### 14.1.1 模式的定義

**設計模式（Design Pattern）**：對常見問題的可重用解決方案的描述。

模式的結構：

| 元素 | 說明 |
|------|------|
| **名稱** | 溝通的詞彙 |
| **問題** | 什麼情境下使用 |
| **解決方案** | 如何解決 |
| **結果** | 權衡和後果 |

### 14.1.2 模式的層次

```
┌─────────────────────────────────────────┐
│           架構模式                       │
│    (MVC, Microservices, Event-Driven)   │
├─────────────────────────────────────────┤
│           設計模式                       │
│    (Factory, Strategy, Observer)        │
├─────────────────────────────────────────┤
│           慣用語                        │
│    (語言特定的實作技巧)                  │
└─────────────────────────────────────────┘
```

### 14.1.3 模式的價值

| 價值 | 說明 |
|------|------|
| **溝通** | 共同詞彙，快速表達設計意圖 |
| **經驗** | 站在前人的經驗上 |
| **品質** | 經過驗證的解決方案 |
| **學習** | 學習優秀的設計思維 |

---

## 14.2 GoF 設計模式

Gang of Four（四人幫）的 23 個經典設計模式。

### 14.2.1 創建型模式

**目的**：物件如何被建立。

| 模式 | 問題 | 解決方案 |
|------|------|----------|
| **Factory Method** | 建立物件的邏輯和使用分離 | 定義介面，子類決定建立什麼 |
| **Abstract Factory** | 建立一系列相關物件 | 工廠的工廠 |
| **Builder** | 建立複雜物件 | 分步驟建立 |
| **Prototype** | 建立相似物件 | 複製現有物件 |
| **Singleton** | 只有一個實例 | 全域存取點 |

**Factory Method 範例**：

```python
# 不用模式
def create_notification(type):
    if type == "email":
        return EmailNotification()
    elif type == "sms":
        return SmsNotification()
    elif type == "push":
        return PushNotification()

# 用 Factory Method
class NotificationFactory:
    def create(self) -> Notification:
        raise NotImplementedError

class EmailNotificationFactory(NotificationFactory):
    def create(self) -> Notification:
        return EmailNotification()

class SmsNotificationFactory(NotificationFactory):
    def create(self) -> Notification:
        return SmsNotification()
```

**Builder 範例**：

```python
# 建立複雜物件
user = UserBuilder() \
    .with_name("Alice") \
    .with_email("alice@example.com") \
    .with_role("admin") \
    .with_permissions(["read", "write"]) \
    .build()
```

### 14.2.2 結構型模式

**目的**：物件如何組合。

| 模式 | 問題 | 解決方案 |
|------|------|----------|
| **Adapter** | 介面不相容 | 包裝成相容介面 |
| **Bridge** | 抽象和實作分離 | 兩個獨立繼承體系 |
| **Composite** | 樹狀結構 | 統一處理葉子和容器 |
| **Decorator** | 動態添加功能 | 包裝物件 |
| **Facade** | 簡化複雜系統 | 提供簡單介面 |
| **Flyweight** | 共用物件 | 分離內在/外在狀態 |
| **Proxy** | 控制存取 | 代理物件 |

**Adapter 範例**：

```python
# 第三方支付 API（無法修改）
class StripeAPI:
    def charge(self, amount_cents, card_token):
        pass

# 我們的介面
class PaymentGateway:
    def pay(self, amount: Money, card: Card):
        raise NotImplementedError

# Adapter
class StripeAdapter(PaymentGateway):
    def __init__(self, stripe: StripeAPI):
        self.stripe = stripe

    def pay(self, amount: Money, card: Card):
        self.stripe.charge(
            amount.to_cents(),
            card.get_token()
        )
```

**Decorator 範例**：

```python
# 基本功能
class Coffee:
    def cost(self): return 50

# Decorator
class MilkDecorator:
    def __init__(self, coffee):
        self.coffee = coffee

    def cost(self):
        return self.coffee.cost() + 10

class SugarDecorator:
    def __init__(self, coffee):
        self.coffee = coffee

    def cost(self):
        return self.coffee.cost() + 5

# 使用
coffee = SugarDecorator(MilkDecorator(Coffee()))
print(coffee.cost())  # 65
```

### 14.2.3 行為型模式

**目的**：物件如何互動。

| 模式 | 問題 | 解決方案 |
|------|------|----------|
| **Chain of Responsibility** | 多個處理者 | 鏈式處理 |
| **Command** | 封裝請求 | 請求變物件 |
| **Iterator** | 遍歷集合 | 統一遍歷介面 |
| **Mediator** | 多對多通訊 | 中介者協調 |
| **Memento** | 儲存狀態 | 快照物件 |
| **Observer** | 一對多通知 | 發布-訂閱 |
| **State** | 狀態相關行為 | 狀態物件 |
| **Strategy** | 演算法替換 | 策略介面 |
| **Template Method** | 演算法骨架 | 抽象步驟 |
| **Visitor** | 添加操作 | 雙重分派 |

**Strategy 範例**：

```python
# 策略介面
class SortStrategy:
    def sort(self, data):
        raise NotImplementedError

class QuickSort(SortStrategy):
    def sort(self, data):
        # 快速排序實作
        pass

class MergeSort(SortStrategy):
    def sort(self, data):
        # 合併排序實作
        pass

# 使用
class Sorter:
    def __init__(self, strategy: SortStrategy):
        self.strategy = strategy

    def sort(self, data):
        return self.strategy.sort(data)

# 動態切換
sorter = Sorter(QuickSort())
sorter.strategy = MergeSort()  # 切換策略
```

**Observer 範例**：

```python
class Subject:
    def __init__(self):
        self.observers = []

    def attach(self, observer):
        self.observers.append(observer)

    def notify(self, data):
        for observer in self.observers:
            observer.update(data)

class EmailObserver:
    def update(self, data):
        print(f"發送郵件：{data}")

class LogObserver:
    def update(self, data):
        print(f"記錄日誌：{data}")

# 使用
subject = Subject()
subject.attach(EmailObserver())
subject.attach(LogObserver())
subject.notify("訂單已建立")  # 兩個 observer 都會收到
```

---

## 14.3 架構模式

### 14.3.1 MVC

```
┌─────────┐     ┌─────────────┐     ┌─────────┐
│  View   │◄────│ Controller  │────►│  Model  │
│  介面   │     │   控制器    │     │  資料   │
└────┬────┘     └─────────────┘     └────┬────┘
     │                                    │
     └────────────────────────────────────┘
                    通知
```

| 元素 | 職責 |
|------|------|
| Model | 資料和業務邏輯 |
| View | 展示 |
| Controller | 處理輸入，協調 |

### 14.3.2 Repository

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Service   │────►│  Repository  │────►│  Database   │
└─────────────┘     └──────────────┘     └─────────────┘
```

| 好處 | 說明 |
|------|------|
| 隔離 | 業務邏輯不知道資料來源 |
| 測試 | 可以 mock Repository |
| 替換 | 可以換資料庫 |

### 14.3.3 CQRS

```
                    ┌─────────────┐
            ┌──────►│  Read Model │
            │       └─────────────┘
┌───────┐   │
│ Query │───┘
└───────┘

┌─────────┐       ┌─────────────┐       ┌─────────────┐
│ Command │──────►│   Domain    │──────►│ Write Model │
└─────────┘       └─────────────┘       └─────────────┘
```

| 好處 | 說明 |
|------|------|
| 優化 | 讀寫分別優化 |
| 擴展 | 讀寫分別擴展 |
| 簡化 | 讀模型可以很簡單 |

---

## 14.4 何時使用模式

### 14.4.1 使用模式的時機

**適合使用**：

| 時機 | 說明 |
|------|------|
| 問題常見 | 這個問題別人也遇過 |
| 需要靈活 | 未來會有變化 |
| 團隊溝通 | 需要共同語言 |
| 程式碼審查 | 解釋設計意圖 |

**不適合使用**：

| 時機 | 說明 |
|------|------|
| 問題簡單 | 直接解決更快 |
| 一次性 | 不會重複 |
| 過度設計 | 增加不必要的複雜度 |

### 14.4.2 模式選擇指南

| 如果你需要... | 考慮使用... |
|--------------|-------------|
| 建立複雜物件 | Builder |
| 建立物件家族 | Abstract Factory |
| 只有一個實例 | Singleton |
| 轉換介面 | Adapter |
| 動態添加功能 | Decorator |
| 簡化複雜系統 | Facade |
| 動態切換演算法 | Strategy |
| 一對多通知 | Observer |
| 狀態相關行為 | State |
| 封裝請求 | Command |

### 14.4.3 模式的陷阱

| 陷阱 | 說明 | 避免方式 |
|------|------|----------|
| **過度使用** | 到處都是模式 | 只在需要時用 |
| **錯誤使用** | 問題和模式不匹配 | 先理解問題 |
| **過早使用** | 還不確定就用 | 先簡單實作，重構時引入 |
| **教條式** | 完全照書實作 | 根據實際調整 |

---

## 14.5 重構到模式

### 14.5.1 從簡單開始

```
第一版：簡單實作
    │
    ▼ 發現需要變化
    │
第二版：if-else 處理
    │
    ▼ 變化變多
    │
第三版：重構到模式
```

### 14.5.2 重構範例：到 Strategy

**第一版**：

```python
def calculate_price(order, discount_type):
    total = order.subtotal
    if discount_type == "none":
        return total
    elif discount_type == "percentage":
        return total * 0.9
    elif discount_type == "fixed":
        return total - 100
    elif discount_type == "vip":
        return total * 0.8
```

**第二版（重構到 Strategy）**：

```python
class DiscountStrategy:
    def apply(self, total):
        raise NotImplementedError

class NoDiscount(DiscountStrategy):
    def apply(self, total):
        return total

class PercentageDiscount(DiscountStrategy):
    def __init__(self, percent):
        self.percent = percent

    def apply(self, total):
        return total * (1 - self.percent)

class FixedDiscount(DiscountStrategy):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, total):
        return total - self.amount

# 使用
def calculate_price(order, strategy: DiscountStrategy):
    return strategy.apply(order.subtotal)
```

---

## 14.6 本章總結

### 核心概念

| 概念 | 一句話解釋 |
|------|-----------|
| 設計模式 | 常見問題的可重用解決方案 |
| 創建型模式 | 物件如何建立 |
| 結構型模式 | 物件如何組合 |
| 行為型模式 | 物件如何互動 |
| 架構模式 | 系統層級的結構模式 |

### 常用模式速查表

| 模式 | 用途 | 一句話 |
|------|------|--------|
| Factory | 建立物件 | 隱藏建立邏輯 |
| Builder | 複雜物件 | 分步驟建立 |
| Singleton | 單一實例 | 全域存取點 |
| Adapter | 介面轉換 | 包裝相容 |
| Decorator | 動態功能 | 包裝添加 |
| Facade | 簡化介面 | 隱藏複雜 |
| Strategy | 演算法替換 | 策略介面 |
| Observer | 一對多通知 | 發布訂閱 |
| Repository | 資料存取 | 隔離資料來源 |

### Part 2 總結預告

Part 2（建模）完成！下一步是 Part 2 總結，包括：
- 需求三層模板
- 架構決策記錄 ADR 模板
- 設計品質檢查清單

---

## 延伸思考

1. 你最常用的設計模式是什麼？為什麼？

2. 你有過度使用模式的經驗嗎？

3. 如何在團隊中推廣設計模式的使用？

---

*Part 2 完成！*
