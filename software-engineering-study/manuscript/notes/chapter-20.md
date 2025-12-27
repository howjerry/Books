# 第20章　軟體測試——整合層級 — 學習筆記

> **狀態**：✅ 已完成
> **閱讀日期**：2025-12-27
> **教材位置**：[content/chapter-20.md](../content/chapter-20.md)

---

## 章前預測（5 分鐘）

### 這章應該回答什麼問題？

1. 為什麼單元測試不夠？
2. 整合測試有哪些策略？
3. 如何管理測試環境？
4. 整合測試放在 CI 哪個位置？

### 我現在的理解是什麼？

閱讀前，我的理解：
- 整合測試 = 測兩個東西一起用
- 直接連真實資料庫測
- 整合測試很慢，少測

### 我遇過哪些相關痛點？

1. **單元測試通過，整合時壞掉**：介面不相容
2. **整合測試不穩定**：有時過有時不過
3. **環境差異**：本機 OK，CI 失敗

---

## 本章一句話

> **整合測試驗證元件能一起工作。使用增量整合策略（Top-Down 或 Bottom-Up）降低風險。用 Docker Compose 管理測試環境，確保測試隔離和可重複。**

---

## 3 個關鍵概念

### 概念 1：整合策略選擇

**書中定義**：

| 策略 | 說明 |
|------|------|
| Big Bang | 全部一起測 |
| Top-Down | 從高層往下整合 |
| Bottom-Up | 從低層往上整合 |
| Sandwich | 雙向同時整合 |

**我的理解**：

選擇策略要看專案特性：

| 情境 | 建議策略 |
|------|----------|
| 小專案 | Big Bang（快） |
| 控制流程重要 | Top-Down |
| 資料處理重要 | Bottom-Up |
| 大型專案 | Sandwich |

**實際考量**：

```
我的專案：電商系統

高層：訂單 Controller
中層：訂單 Service、庫存 Service
低層：Repository、支付閘道

策略：Sandwich
- 從上往下：Controller → Service
- 從下往上：Repository → Service
- 在 Service 層交會
```

**經驗法則**：
> 「先整合最有風險的部分。」

---

### 概念 2：測試環境隔離

**書中定義**：

每個測試應該在乾淨的環境中執行，不受其他測試影響。

| 隔離面向 | 做法 |
|----------|------|
| 資料庫 | 每次測試清空或 Rollback |
| 外部服務 | 使用 Mock Server |
| 檔案系統 | 使用臨時目錄 |
| 環境變數 | 使用測試專用設定 |

**我的理解**：

測試不穩定的主要原因就是隔離不夠。

**隔離實踐**：

```python
# 使用 fixture 確保隔離
@pytest.fixture
def db_session():
    session = create_session()
    yield session
    session.rollback()  # 每次測試後 rollback
    session.close()
```

**Docker Compose 隔離**：

```yaml
services:
  db:
    image: postgres:13
    # 每次 CI 都是乾淨的容器
```

**經驗法則**：
> 「測試要能以任何順序執行，結果都一樣。」

---

### 概念 3：Contract Testing

**書中定義**：

驗證服務間的「合約」是否被遵守。

```
Consumer              Contract              Provider
(訂單服務)    ←───────────────────►    (支付服務)
          "POST /charge 回傳 200"
```

**我的理解**：

傳統做法：Mock 支付服務

問題：Mock 可能和真實行為不一致

Contract Testing：
1. Consumer 定義期望（合約）
2. Provider 驗證符合合約
3. 如果 Provider 改了，合約測試會失敗

**工具**：Pact

**何時用**：
- 微服務架構
- 團隊分開開發
- API 會變動

**經驗法則**：
> 「如果 Mock 和真實不一致，整合時一定會出問題。」

---

## 原則、方法、護欄

### 整合測試速查表

| 情境 | 做法 |
|------|------|
| 測 API | 用 TestClient 呼叫端點 |
| 測資料庫 | 用 In-Memory DB 或容器 |
| 測外部服務 | Mock Server 或 Contract |
| 測訊息佇列 | 使用測試容器 |

---

### 護欄（Guardrail）

| 危險信號 | 可能的問題 | 修正方式 |
|----------|-----------|----------|
| 測試不穩定 | 隔離不足 | 加強隔離 |
| 測試很慢 | 太多整合測試 | 下移到單元測試 |
| 只測 happy path | 缺少錯誤處理測試 | 加錯誤情境 |
| Mock 和真實不同 | Mock 過期 | Contract Testing |
| 本機 OK CI 失敗 | 環境不一致 | 用容器統一環境 |

---

## 1 個決策點

### 決策情境

**用真實服務還是 Mock？**

### 選項對比

| 選項 | 優點 | 缺點 |
|------|------|------|
| 真實服務 | 最真實 | 慢、不穩定、有成本 |
| Mock | 快、穩定 | 可能和真實不同 |
| Contract | 平衡 | 需要維護合約 |

### 決策準則

| 情境 | 建議 |
|------|------|
| 內部服務 | 儘量用真實（容器） |
| 付費外部 API | 用 Mock |
| 關鍵整合點 | Contract Testing |
| CI 環境 | 容器化服務 |
| 本機開發 | Mock（快速回饋） |

**經驗法則**：
> 「內部服務用真實，外部服務用 Mock + Contract。」

---

## 1 個反模式（Anti-pattern）

### 反模式名稱

**「測試依賴順序」症候群**

### 錯誤做法

測試結果依賴執行順序：

```python
# Test A 建立資料
def test_create_user():
    db.create_user("alice")

# Test B 依賴 Test A 的資料
def test_get_user():
    user = db.get_user("alice")  # 假設已存在
    assert user is not None
```

問題：
- 單獨跑 Test B 會失敗
- 調換順序會失敗
- 平行執行會失敗

### 後果

1. **不穩定**：有時過有時不過
2. **難以診斷**：不知道為什麼失敗
3. **無法平行**：只能循序執行

### 正確做法

**每個測試自己準備資料**：

```python
def test_create_user():
    db.create_user("test_user_1")
    # ...

def test_get_user():
    # 自己準備資料
    db.create_user("test_user_2")

    user = db.get_user("test_user_2")
    assert user is not None
```

**使用 Fixture**：

```python
@pytest.fixture
def sample_user():
    user = db.create_user("fixture_user")
    yield user
    db.delete_user(user.id)  # 清理

def test_get_user(sample_user):
    user = db.get_user(sample_user.id)
    assert user is not None
```

**檢驗標準**：
> 「這個測試可以單獨執行嗎？」

---

## 可落地 Checklist（至少 5 條）

寫整合測試時檢查：

- [x] **隔離**：測試間互相獨立嗎？
- [x] **清理**：測試後有清理資料嗎？
- [x] **環境**：測試環境和 CI 一致嗎？
- [x] **資料**：測試資料有管理嗎（Factory/Fixture）？
- [x] **速度**：整合測試夠快嗎？
- [x] **覆蓋**：關鍵整合點都測了嗎？
- [x] **錯誤**：錯誤情境測了嗎？

---

## 章後練習

### 練習：設計整合測試策略

> 目標：為你的專案設計整合測試策略

**我的專案架構**：

```
┌─────────────┐
│ API Gateway │
└──────┬──────┘
       │
┌──────┴──────┐
│ Order API   │
└──────┬──────┘
       │
┌──────┴──────┬──────────────┐
│             │              │
│ Order DB    │ Inventory    │ Payment
│             │ Service      │ Gateway
└─────────────┴──────────────┴──────────
```

**整合測試策略**：

| 整合點 | 策略 | 做法 |
|--------|------|------|
| API ↔ Service | Top-Down | TestClient |
| Service ↔ DB | Bottom-Up | 測試容器 |
| Service ↔ Inventory | Contract | Pact |
| Service ↔ Payment | Mock | Mock Server |

**CI 配置**：

```yaml
services:
  postgres:
    image: postgres:13
  redis:
    image: redis:6

steps:
  - run: pytest tests/unit
  - run: pytest tests/integration
```

---

## 延伸思考

### 整合測試應該占多少比例？

**測試金字塔建議**：

| 類型 | 比例 |
|------|------|
| 單元測試 | 50-70% |
| 整合測試 | 20-30% |
| E2E 測試 | 10-20% |

**我的實踐**：

整合測試重點：
1. **API 層**：確保 HTTP 行為正確
2. **資料庫**：確保 Query 正確
3. **外部服務**：確保介面正確

不需要整合測試：
- 純業務邏輯（單元測試夠）
- UI 元件（E2E 測試處理）

### 如何處理整合測試太慢的問題？

**我的策略**：

1. **平行執行**
   - `pytest -n auto`
   - 確保測試獨立

2. **共享資料庫容器**
   - 用交易 Rollback 而非重建
   - 減少啟動時間

3. **選擇性執行**
   - 只跑受影響的測試
   - 使用 `pytest --lf`（只跑失敗的）

4. **層級分離**
   - 快的放 CI（每次 commit）
   - 慢的放 Nightly Build

---

## 完成確認

- [x] 完成章前預測
- [x] 讀完本章
- [x] 填寫本章一句話
- [x] 填寫 3 個關鍵概念
- [x] 填寫原則、方法、護欄
- [x] 填寫 1 個決策點
- [x] 填寫 1 個反模式
- [x] 填寫 Checklist
- [x] 完成章後練習
- [x] 完成延伸思考

**完成日期**：2025-12-27
