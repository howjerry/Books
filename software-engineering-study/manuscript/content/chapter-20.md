# 第20章　軟體測試——整合層級

> 「單元測試證明元件正確，整合測試證明元件能一起工作。」

---

## 20.1 什麼是整合測試？

### 20.1.1 整合測試的定義

**整合測試（Integration Testing）**：驗證多個元件組合在一起時是否正確運作。

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  單元測試          整合測試             系統測試              │
│  ┌───┐           ┌───┬───┐          ┌─────────────┐        │
│  │ A │           │ A │ B │          │ A + B + C   │        │
│  └───┘           └───┴───┘          │ + D + E + F │        │
│                                      └─────────────┘        │
│  驗證單一元件     驗證元件互動        驗證整個系統           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 20.1.2 為什麼需要整合測試？

單元測試通過不代表整合沒問題：

| 單元測試 | 整合測試 |
|----------|----------|
| A 正確 | A 和 B 能一起工作嗎？ |
| B 正確 | 介面相容嗎？ |
| C 正確 | 資料格式對嗎？ |

**常見的整合問題**：

| 問題 | 說明 |
|------|------|
| **介面不匹配** | 參數數量、型別不對 |
| **資料格式錯誤** | JSON 格式不同 |
| **時序問題** | 呼叫順序錯誤 |
| **資源衝突** | 同時存取資料庫 |
| **環境差異** | 開發環境 OK，生產環境不行 |

### 20.1.3 整合測試的層次

| 層次 | 說明 | 範例 |
|------|------|------|
| **元件整合** | 模組間整合 | Service + Repository |
| **子系統整合** | 子系統間整合 | 訂單系統 + 庫存系統 |
| **系統整合** | 和外部系統整合 | 和支付閘道整合 |

---

## 20.2 整合測試策略

### 20.2.1 Big Bang 整合

一次把所有元件組合起來測試。

```
        ┌───┐ ┌───┐ ┌───┐ ┌───┐
        │ A │ │ B │ │ C │ │ D │
        └───┘ └───┘ └───┘ └───┘
           \    |    |    /
            \   |    |   /
             \  |    |  /
              \ |    | /
               \|    |/
            ┌───────────┐
            │  整合測試  │
            └───────────┘
```

| 優點 | 缺點 |
|------|------|
| 簡單 | 難以定位問題 |
| 快速開始 | 晚期才發現問題 |
| | 難以平行開發 |

**適用**：小型系統

### 20.2.2 增量整合

逐步加入元件，每次只加一個。

**Top-Down（由上而下）**：

```
Step 1:        Step 2:        Step 3:
  ┌───┐          ┌───┐          ┌───┐
  │ A │          │ A │          │ A │
  └───┘          └─┬─┘          └─┬─┘
                   │              │
                 ┌───┐          ┌─┴─┐
                 │ B │          │ B │
                 └───┘          └─┬─┘
                 (stub)            │
                                ┌───┐
                                │ C │
                                └───┘
```

| 優點 | 缺點 |
|------|------|
| 早期驗證架構 | 需要大量 Stub |
| 重要模組先測 | 低層模組晚測 |

**Bottom-Up（由下而上）**：

```
Step 1:        Step 2:        Step 3:
  ┌───┐          ┌───┐          ┌───┐
  │ C │          │ B │          │ A │
  └───┘          └─┬─┘          └─┬─┘
                   │              │
                 ┌───┐          ┌─┴─┐
                 │ C │          │ B │
                 └───┘          └─┬─┘
                                  │
                                ┌───┐
                                │ C │
                                └───┘
```

| 優點 | 缺點 |
|------|------|
| 低層模組先穩定 | 需要 Driver |
| 不需要 Stub | 晚期才看到完整系統 |

### 20.2.3 Sandwich（三明治）整合

結合 Top-Down 和 Bottom-Up。

```
                 Top-Down
                    ↓
        ┌───┐      ┌───┐
        │ A │      │ B │  ← 高層
        └───┘      └───┘
           \        /
            \      /
             \    /
         ┌───────────┐
         │   Target  │  ← 目標層（整合點）
         └───────────┘
             /    \
            /      \
           /        \
        ┌───┐      ┌───┐
        │ D │      │ E │  ← 低層
        └───┘      └───┘
                    ↑
               Bottom-Up
```

| 優點 | 缺點 |
|------|------|
| 平衡 | 複雜 |
| 平行開發 | 需要協調 |
| 早期發現問題 | |

### 20.2.4 策略比較

| 策略 | 適用 | 風險 |
|------|------|------|
| Big Bang | 小系統 | 高（晚發現問題） |
| Top-Down | 控制流程重要 | 中（需要 Stub） |
| Bottom-Up | 資料處理重要 | 中（需要 Driver） |
| Sandwich | 大型複雜系統 | 低（但複雜） |

---

## 20.3 整合測試類型

### 20.3.1 API 整合測試

測試 API 端點的行為。

```python
# 測試 REST API
def test_create_order():
    # Arrange
    client = TestClient(app)
    order_data = {
        "customer_id": "123",
        "items": [{"product_id": "P001", "quantity": 2}]
    }

    # Act
    response = client.post("/orders", json=order_data)

    # Assert
    assert response.status_code == 201
    assert "order_id" in response.json()

def test_get_order():
    client = TestClient(app)

    response = client.get("/orders/123")

    assert response.status_code == 200
    assert response.json()["customer_id"] == "123"
```

### 20.3.2 資料庫整合測試

測試和資料庫的互動。

```python
import pytest
from sqlalchemy import create_engine

@pytest.fixture
def db_session():
    """每個測試使用獨立的資料庫"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()

def test_save_order(db_session):
    # Arrange
    order = Order(customer_id="123", total=1000)

    # Act
    db_session.add(order)
    db_session.commit()

    # Assert
    saved = db_session.query(Order).filter_by(customer_id="123").first()
    assert saved is not None
    assert saved.total == 1000

def test_update_order(db_session):
    # Arrange
    order = Order(customer_id="123", total=1000)
    db_session.add(order)
    db_session.commit()

    # Act
    order.total = 2000
    db_session.commit()

    # Assert
    updated = db_session.query(Order).filter_by(customer_id="123").first()
    assert updated.total == 2000
```

### 20.3.3 外部服務整合測試

使用 Test Double 或 Contract Testing。

**方法一：使用 Mock Server**

```python
import responses

@responses.activate
def test_payment_gateway():
    # 設定 Mock 回應
    responses.add(
        responses.POST,
        "https://api.payment.com/charge",
        json={"success": True, "transaction_id": "TX123"},
        status=200
    )

    # 執行測試
    result = payment_service.charge(amount=100, card="4111...")

    # 驗證
    assert result.success == True
    assert result.transaction_id == "TX123"
```

**方法二：Contract Testing**

```yaml
# pact contract
provider: PaymentService
consumer: OrderService
interactions:
  - description: successful charge
    request:
      method: POST
      path: /charge
      body:
        amount: 100
    response:
      status: 200
      body:
        success: true
```

---

## 20.4 測試環境管理

### 20.4.1 環境類型

| 環境 | 用途 | 資料 |
|------|------|------|
| **開發** | 開發者本機 | 假資料 |
| **CI** | 自動化測試 | 測試資料 |
| **Staging** | 類生產驗證 | 脫敏資料 |
| **生產** | 正式運作 | 真實資料 |

### 20.4.2 測試資料管理

| 策略 | 說明 | 適用 |
|------|------|------|
| **Fixture** | 預設測試資料 | 小規模 |
| **Factory** | 動態產生資料 | 靈活需求 |
| **Seed Data** | 預載資料 | 需要真實資料 |
| **快照** | 複製生產資料 | 大規模整合 |

**Factory 範例**：

```python
from factory import Factory, Faker

class OrderFactory(Factory):
    class Meta:
        model = Order

    customer_id = Faker('uuid4')
    total = Faker('random_int', min=100, max=10000)
    status = 'pending'

# 使用
def test_order_processing():
    order = OrderFactory.create(total=500)
    assert order.total == 500
```

### 20.4.3 測試隔離

```python
import pytest

@pytest.fixture(autouse=True)
def clean_database(db_session):
    """每個測試後清理資料庫"""
    yield
    db_session.rollback()
    db_session.query(Order).delete()
    db_session.commit()

@pytest.fixture
def isolated_redis():
    """使用獨立的 Redis 資料庫"""
    redis = Redis(db=15)  # 使用測試專用 DB
    yield redis
    redis.flushdb()
```

---

## 20.5 持續整合中的整合測試

### 20.5.1 CI Pipeline 中的位置

```
┌──────────────────────────────────────────────────────────────┐
│                        CI Pipeline                           │
│                                                              │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐ │
│  │ Build  │─►│  Unit  │─►│ Integ  │─►│  E2E   │─►│ Deploy │ │
│  │        │  │  Test  │  │  Test  │  │  Test  │  │        │ │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘ │
│                              │                               │
│                              ▼                               │
│                    ┌──────────────────┐                     │
│                    │ 需要 DB, Redis,  │                     │
│                    │ 外部服務模擬     │                     │
│                    └──────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

### 20.5.2 Docker Compose 測試環境

```yaml
# docker-compose.test.yml
version: '3'
services:
  app:
    build: .
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://test:test@db/test
      - REDIS_URL=redis://redis:6379

  db:
    image: postgres:13
    environment:
      - POSTGRES_USER=test
      - POSTGRES_PASSWORD=test
      - POSTGRES_DB=test

  redis:
    image: redis:6
```

```bash
# 執行整合測試
docker-compose -f docker-compose.test.yml up -d
docker-compose -f docker-compose.test.yml run app pytest tests/integration
docker-compose -f docker-compose.test.yml down
```

### 20.5.3 GitHub Actions 範例

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432

      redis:
        image: redis:6
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run integration tests
        run: pytest tests/integration
        env:
          DATABASE_URL: postgresql://postgres:test@localhost/postgres
          REDIS_URL: redis://localhost:6379
```

---

## 20.6 整合測試最佳實踐

### 20.6.1 測試金字塔

```
                    ┌─────────────┐
                   ╱    E2E       ╲     少
                  ╱   (10-20%)    ╲
                 ╱─────────────────╲
                ╱                   ╲
               ╱     整合測試        ╲    中
              ╱     (20-30%)        ╲
             ╱───────────────────────╲
            ╱                         ╲
           ╱        單元測試           ╲  多
          ╱        (50-70%)           ╲
         ╱─────────────────────────────╲
```

### 20.6.2 什麼該整合測試？

| 應該測 | 不應該測 |
|--------|----------|
| 元件間介面 | 已單元測過的邏輯 |
| 資料流 | 純粹的業務邏輯 |
| 錯誤處理 | UI 細節 |
| 交易 | 第三方庫的功能 |

### 20.6.3 速度優化

| 技術 | 說明 |
|------|------|
| **平行執行** | 測試平行跑 |
| **共享資源** | 重用資料庫連線 |
| **最小資料** | 只建必要的測試資料 |
| **選擇執行** | 只跑受影響的測試 |

```python
# pytest.ini
[pytest]
addopts = -n auto  # 平行執行
```

---

## 20.7 本章總結

### 核心概念

| 概念 | 一句話解釋 |
|------|-----------|
| 整合測試 | 驗證元件能一起工作 |
| Big Bang | 全部一起測（風險高） |
| 增量整合 | 逐步加入元件 |
| Top-Down | 從高層開始整合 |
| Bottom-Up | 從低層開始整合 |
| Contract Testing | 驗證服務間合約 |

### 整合測試 Checklist

| 項目 | 問題 |
|------|------|
| 策略選擇 | 選了適合的整合策略嗎？ |
| 環境隔離 | 測試環境獨立嗎？ |
| 資料管理 | 測試資料有管理嗎？ |
| 清理機制 | 測試後有清理嗎？ |
| CI 整合 | 整合測試在 CI 中嗎？ |
| 速度 | 整合測試夠快嗎？ |

### 下一章預告

通用的測試策略之外，行動裝置和特定領域有什麼特殊考量？下一章我們將學習「軟體測試——行動裝置與特定領域」。

---

## 延伸思考

1. 你的專案用什麼整合策略？適合嗎？

2. 整合測試環境和生產環境有多相似？

3. 整合測試多久執行一次？夠頻繁嗎？

---

*下一章：第21章　軟體測試——行動裝置與特定領域的測試*
