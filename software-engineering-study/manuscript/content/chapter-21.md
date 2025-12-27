# 第21章　軟體測試——行動裝置與特定領域的測試

> 「通用的測試方法是基礎，但每個領域都有自己的特殊考量。」

---

## 21.1 行動應用測試

### 21.1.1 行動測試的挑戰

| 挑戰 | 說明 |
|------|------|
| **裝置多樣** | 數千種裝置、螢幕、OS 版本 |
| **網路變化** | WiFi、4G、弱網、斷網 |
| **資源限制** | 電池、記憶體、CPU |
| **中斷處理** | 來電、通知、背景切換 |
| **感應器** | GPS、相機、陀螺儀 |

### 21.1.2 行動測試類型

```
┌──────────────────────────────────────────────────────────────┐
│                     行動測試金字塔                            │
│                                                              │
│                    ┌─────────────┐                          │
│                   ╱               ╲                         │
│                  ╱   真機測試      ╲     少量               │
│                 ╱   (關鍵路徑)     ╲                        │
│                ╱─────────────────────╲                      │
│               ╱                       ╲                     │
│              ╱      UI 自動化          ╲   中量             │
│             ╱     (主要流程)           ╲                    │
│            ╱───────────────────────────╲                   │
│           ╱                             ╲                  │
│          ╱         單元測試              ╲  大量            │
│         ╱        (業務邏輯)              ╲                  │
│        ╱───────────────────────────────────╲               │
└──────────────────────────────────────────────────────────────┘
```

| 類型 | 說明 | 工具 |
|------|------|------|
| **單元測試** | 業務邏輯測試 | XCTest, JUnit |
| **UI 測試** | 介面自動化 | Espresso, XCUITest |
| **效能測試** | 啟動、記憶體、電池 | Instruments, Profiler |
| **網路測試** | 弱網、離線 | Charles, 網路限速 |
| **真機測試** | 實際裝置驗證 | Device Farm |

### 21.1.3 裝置覆蓋策略

不可能測試所有裝置，需要策略性選擇：

| 維度 | 策略 |
|------|------|
| **市佔率** | 覆蓋 Top 10 裝置 |
| **OS 版本** | 最新 + 前兩個版本 |
| **螢幕尺寸** | 小、中、大 代表 |
| **製造商** | 主流品牌各一 |

**範例覆蓋矩陣**：

| 裝置 | OS | 螢幕 | 優先級 |
|------|-----|------|--------|
| iPhone 14 Pro | iOS 17 | 大 | P0 |
| iPhone SE | iOS 16 | 小 | P1 |
| Samsung S23 | Android 14 | 大 | P0 |
| Pixel 6 | Android 13 | 中 | P1 |
| 小米 12 | Android 12 | 中 | P2 |

### 21.1.4 特殊情境測試

| 情境 | 測試內容 |
|------|----------|
| **弱網** | 2G/3G 環境下的行為 |
| **斷網** | 離線時的處理 |
| **來電中斷** | 通話後恢復 |
| **背景切換** | 切到背景再回來 |
| **低電量** | 省電模式下的行為 |
| **記憶體不足** | 被系統殺掉後恢復 |
| **螢幕旋轉** | 直橫切換 |
| **深色模式** | 深色主題顯示 |

---

## 21.2 Web 應用測試

### 21.2.1 跨瀏覽器測試

| 瀏覽器 | 市佔率 | 優先級 |
|--------|--------|--------|
| Chrome | ~65% | P0 |
| Safari | ~20% | P0 |
| Firefox | ~5% | P1 |
| Edge | ~5% | P1 |

### 21.2.2 響應式設計測試

| 斷點 | 寬度 | 代表裝置 |
|------|------|----------|
| Mobile | < 768px | 手機 |
| Tablet | 768-1024px | 平板 |
| Desktop | > 1024px | 桌機 |

### 21.2.3 可及性測試（Accessibility）

| 項目 | 說明 | 工具 |
|------|------|------|
| **螢幕閱讀** | 能用螢幕閱讀器嗎？ | VoiceOver, NVDA |
| **鍵盤操作** | 只用鍵盤能操作嗎？ | 手動測試 |
| **顏色對比** | 對比度足夠嗎？ | axe, Lighthouse |
| **替代文字** | 圖片有 alt 嗎？ | axe |

**WCAG 2.1 等級**：

| 等級 | 說明 |
|------|------|
| A | 最低要求 |
| AA | 推薦標準 |
| AAA | 最高標準 |

---

## 21.3 API 測試

### 21.3.1 API 測試類型

| 類型 | 說明 |
|------|------|
| **功能測試** | API 行為正確嗎？ |
| **驗證測試** | 回應格式正確嗎？ |
| **錯誤處理** | 錯誤情況正確處理嗎？ |
| **安全測試** | 有安全漏洞嗎？ |
| **效能測試** | 效能足夠嗎？ |

### 21.3.2 API 測試案例設計

```python
# 功能測試
def test_create_user_success():
    response = client.post("/users", json={"name": "Alice"})
    assert response.status_code == 201
    assert response.json()["name"] == "Alice"

# 驗證測試
def test_response_schema():
    response = client.get("/users/1")
    assert "id" in response.json()
    assert "name" in response.json()
    assert "email" in response.json()

# 錯誤處理
def test_not_found():
    response = client.get("/users/9999")
    assert response.status_code == 404

# 驗證測試
def test_invalid_input():
    response = client.post("/users", json={"name": ""})
    assert response.status_code == 400
```

### 21.3.3 API 效能測試

| 指標 | 說明 | 目標 |
|------|------|------|
| **延遲** | 回應時間 | P99 < 500ms |
| **吞吐量** | 每秒請求數 | > 1000 RPS |
| **錯誤率** | 失敗比例 | < 0.1% |

---

## 21.4 資料庫測試

### 21.4.1 資料庫測試面向

| 面向 | 測試內容 |
|------|----------|
| **CRUD** | 建立、讀取、更新、刪除 |
| **約束** | 唯一、外鍵、檢查約束 |
| **交易** | ACID 屬性 |
| **效能** | 查詢效能、索引 |
| **遷移** | Schema 變更 |

### 21.4.2 資料庫測試範例

```python
def test_unique_constraint():
    """測試唯一約束"""
    db.create_user(email="alice@example.com")

    with pytest.raises(IntegrityError):
        db.create_user(email="alice@example.com")

def test_foreign_key():
    """測試外鍵約束"""
    with pytest.raises(IntegrityError):
        db.create_order(user_id=9999)  # 不存在的用戶

def test_transaction_rollback():
    """測試交易回滾"""
    try:
        with db.transaction():
            db.create_order(...)
            db.update_inventory(...)  # 失敗
    except Exception:
        pass

    assert db.get_order(...) is None  # 應該回滾

def test_cascade_delete():
    """測試級聯刪除"""
    user = db.create_user(...)
    order = db.create_order(user_id=user.id)

    db.delete_user(user.id)

    assert db.get_order(order.id) is None  # 應該一起刪除
```

---

## 21.5 效能測試

### 21.5.1 效能測試類型

| 類型 | 目的 | 情境 |
|------|------|------|
| **負載測試** | 驗證正常負載 | 預期用戶數 |
| **壓力測試** | 找出極限 | 超過正常負載 |
| **耐久測試** | 長期穩定性 | 持續運行數小時 |
| **尖峰測試** | 突發流量 | 突然增加負載 |

### 21.5.2 效能測試工具

| 工具 | 說明 |
|------|------|
| **JMeter** | Java 負載測試工具 |
| **k6** | 現代化負載測試 |
| **Locust** | Python 負載測試 |
| **Gatling** | Scala 負載測試 |

### 21.5.3 效能測試範例（k6）

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 100 },  // 增加到 100 用戶
    { duration: '5m', target: 100 },  // 維持 100 用戶
    { duration: '1m', target: 0 },    // 降到 0
  ],
  thresholds: {
    http_req_duration: ['p(99)<500'],  // 99% 請求 < 500ms
    http_req_failed: ['rate<0.01'],    // 失敗率 < 1%
  },
};

export default function () {
  let response = http.get('https://api.example.com/users');

  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1);
}
```

---

## 21.6 安全測試

### 21.6.1 安全測試類型

| 類型 | 說明 | 工具 |
|------|------|------|
| **SAST** | 靜態程式碼分析 | SonarQube, Checkmarx |
| **DAST** | 動態應用測試 | OWASP ZAP, Burp |
| **SCA** | 依賴漏洞掃描 | Snyk, Dependabot |
| **滲透測試** | 人工攻擊模擬 | 安全專家 |

### 21.6.2 常見安全測試案例

| 漏洞 | 測試方法 |
|------|----------|
| SQL Injection | 嘗試 `' OR 1=1 --` |
| XSS | 嘗試 `<script>alert(1)</script>` |
| CSRF | 驗證 Token 機制 |
| 認證繞過 | 驗證未認證存取 |
| 權限提升 | 驗證越權存取 |

---

## 21.7 特定領域測試

### 21.7.1 金融系統測試

| 面向 | 測試重點 |
|------|----------|
| **精確度** | 金額計算不能有浮點誤差 |
| **交易完整** | ACID 嚴格遵守 |
| **稽核** | 所有操作可追溯 |
| **合規** | 符合法規要求 |

### 21.7.2 醫療系統測試

| 面向 | 測試重點 |
|------|----------|
| **資料正確** | 患者資料不能錯 |
| **隱私** | HIPAA 合規 |
| **可用性** | 高可用性要求 |
| **可及性** | 醫護人員容易使用 |

### 21.7.3 即時系統測試

| 面向 | 測試重點 |
|------|----------|
| **延遲** | 嚴格的時間要求 |
| **可靠性** | 不能當機 |
| **資源** | 固定的資源使用 |
| **並發** | 並發處理正確 |

---

## 21.8 本章總結

### 核心概念

| 概念 | 一句話解釋 |
|------|-----------|
| 行動測試 | 考慮裝置多樣性、網路變化 |
| 跨瀏覽器 | 主流瀏覽器都要測 |
| 可及性 | 確保所有人能使用 |
| 效能測試 | 驗證系統效能 |
| 安全測試 | 發現安全漏洞 |

### 領域測試 Checklist

| 領域 | 檢查項目 |
|------|----------|
| 行動 | 裝置覆蓋、網路情境、中斷處理 |
| Web | 跨瀏覽器、響應式、可及性 |
| API | 功能、錯誤、效能、安全 |
| 資料庫 | CRUD、約束、交易、效能 |
| 效能 | 負載、壓力、耐久、尖峰 |
| 安全 | SAST、DAST、SCA、滲透 |

### 下一章預告

測試需要管理程式碼版本和配置。下一章我們將學習「軟體組態管理」。

---

## 延伸思考

1. 你的行動 App 覆蓋多少裝置？足夠嗎？

2. 你做過可及性測試嗎？

3. 效能測試多久做一次？

---

*下一章：第22章　軟體組態管理*
