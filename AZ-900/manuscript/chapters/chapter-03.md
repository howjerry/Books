# 第 3 章：連接世界的大門 (The Global Gateway)

> 「在台北按下購買按鈕，0.1 秒後收到確認。這不是魔法，是基礎設施的力量。」
> —— CloudMart 基礎設施團隊

---

## 本章學習目標

完成本章後，你將能夠：

- 解釋 DNS 如何將域名轉換為 IP 位址
- 設計多區域的 DNS 策略以提升可用性
- 說明 CDN 如何加速全球內容傳遞
- 配置防火牆規則保護網路安全
- 理解並解決 CORS 跨域問題
- 在 Azure 上配置 Front Door 和 Application Gateway

---

## 3.1 跨國用戶的痛點

2022 年春天，CloudMart 開始拓展海外市場。第一站是日本。

行銷團隊興奮地在東京投放廣告，但客服團隊很快收到大量投訴：

> 「網站太慢了，載入要等 5 秒以上！」
> 「購物車頁面常常轉圈圈。」
> 「我放棄了，你們的網站根本打不開。」

技術團隊開始調查，發現問題的根源：

```
┌─────────────────────────────────────────────────────────────────┐
│                    問題：延遲太高                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  日本用戶（東京）                                                │
│       │                                                         │
│       │  DNS 查詢 ──► 10ms                                      │
│       │                                                         │
│       │  TCP 握手 ──► 180ms (來回 x3 = 540ms)                   │
│       │                                                         │
│       │  TLS 握手 ──► 180ms (來回 x4 = 720ms)                   │
│       │                                                         │
│       │  HTTP 請求 ──► 180ms (來回)                             │
│       │                                                         │
│       ▼                                                         │
│   ═══════════════════════════════════════════════════          │
│              太平洋海底電纜（約 9,000 公里）                      │
│   ═══════════════════════════════════════════════════          │
│       │                                                         │
│       ▼                                                         │
│  CloudMart 伺服器（台北）                                        │
│       │                                                         │
│       │  處理請求 ──► 50ms                                      │
│       │                                                         │
│       │  回應資料 ──► 180ms (來回)                              │
│       │                                                         │
│       ▼                                                         │
│  日本用戶看到頁面                                                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  總延遲：10 + 540 + 720 + 180 + 50 + 180 = 1,680ms     │   │
│  │                                                         │   │
│  │  這還只是第一個 HTTP 請求！                              │   │
│  │  一個網頁通常需要 50+ 個請求（CSS, JS, 圖片...）         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**問題的核心：物理距離造成的延遲**

光速是有限的。即使是光在光纖中傳輸，台北到東京的延遲也有約 60ms（單程）。這個延遲會在每次網路往返中累積。

我們需要的解決方案：

1. **DNS**：讓用戶連到最近的伺服器
2. **CDN**：把靜態內容快取到離用戶近的地方
3. **邊緣運算**：在離用戶近的地方處理請求

---

## 3.2 DNS：網際網路的電話簿

### 3.2.1 什麼是 DNS？

**DNS（Domain Name System）** 將人類可讀的域名轉換為機器可讀的 IP 位址。

```
你輸入：www.cloudmart.com
DNS 回答：20.43.161.50

你輸入：api.cloudmart.com
DNS 回答：20.43.161.51
```

沒有 DNS，你就必須記住每個網站的 IP 位址。想像一下要記住 `142.250.196.100` 才能上 Google！

### 3.2.2 DNS 查詢過程

```
┌─────────────────────────────────────────────────────────────────┐
│                     DNS 查詢過程                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用戶瀏覽器                                                      │
│       │                                                         │
│       │ ① 查詢 www.cloudmart.com                                │
│       ▼                                                         │
│  ┌─────────────┐                                                │
│  │ 本機 DNS 快取│ ── 有快取？──► 直接回傳 IP                     │
│  └──────┬──────┘       │                                        │
│         │ 沒有         │                                        │
│         ▼              │                                        │
│  ┌─────────────┐       │                                        │
│  │ 路由器 DNS  │ ── 有快取？──► 直接回傳 IP                      │
│  └──────┬──────┘       │                                        │
│         │ 沒有         │                                        │
│         ▼              │                                        │
│  ┌─────────────────┐   │                                        │
│  │ ISP DNS 伺服器   │ ── 有快取？──► 直接回傳 IP                 │
│  │ (如中華電信)     │   │                                        │
│  └──────┬──────────┘   │                                        │
│         │ 沒有         │                                        │
│         │              │                                        │
│  ② 遞迴查詢開始        │                                        │
│         │              │                                        │
│         ▼              │                                        │
│  ┌─────────────┐       │                                        │
│  │ 根域名伺服器 │       │                                        │
│  │    (.)      │ ─────► "去問 .com 伺服器"                      │
│  └──────┬──────┘       │                                        │
│         ▼              │                                        │
│  ┌─────────────┐       │                                        │
│  │ TLD 伺服器  │       │                                        │
│  │   (.com)    │ ─────► "去問 cloudmart.com 的 NS"              │
│  └──────┬──────┘       │                                        │
│         ▼              │                                        │
│  ┌─────────────────┐   │                                        │
│  │ 權威 DNS 伺服器 │   │                                        │
│  │ (cloudmart.com) │ ──► "IP 是 20.43.161.50"                  │
│  └─────────────────┘   │                                        │
│                        │                                        │
│  ③ 快取並回傳給用戶    ◄─┘                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2.3 DNS 記錄類型

| 記錄類型 | 用途 | 範例 |
|----------|------|------|
| **A** | 將域名指向 IPv4 位址 | `cloudmart.com → 20.43.161.50` |
| **AAAA** | 將域名指向 IPv6 位址 | `cloudmart.com → 2001:db8::1` |
| **CNAME** | 將域名指向另一個域名 | `www → cloudmart.com` |
| **MX** | 郵件伺服器 | `mail.cloudmart.com (優先級 10)` |
| **TXT** | 文字記錄（驗證、SPF 等） | `v=spf1 include:_spf.google.com` |
| **NS** | 指定權威 DNS 伺服器 | `ns1.azure-dns.com` |
| **SOA** | 區域的起始授權 | 包含主要 NS、管理員信箱等 |
| **PTR** | 反向查詢（IP → 域名） | `50.161.43.20 → cloudmart.com` |

### 3.2.4 CloudMart 的 DNS 配置

```
; CloudMart DNS Zone 設定
; 託管於 Azure DNS

$ORIGIN cloudmart.com.
$TTL 300

; SOA 記錄（區域起始授權）
@   IN  SOA  ns1-01.azure-dns.com. admin.cloudmart.com. (
            2024011501  ; Serial
            3600        ; Refresh
            600         ; Retry
            604800      ; Expire
            300         ; Minimum TTL
            )

; NS 記錄（指定 Azure DNS 伺服器）
@       IN  NS    ns1-01.azure-dns.com.
@       IN  NS    ns2-01.azure-dns.net.
@       IN  NS    ns3-01.azure-dns.org.
@       IN  NS    ns4-01.azure-dns.info.

; A 記錄（主網站）
@       IN  A     20.43.161.50
www     IN  A     20.43.161.50

; CNAME 記錄（CDN）
static  IN  CNAME cloudmart.azureedge.net.
images  IN  CNAME cloudmart.azureedge.net.

; API 子域名（不同的伺服器）
api     IN  A     20.43.161.51
api     IN  A     20.43.161.52

; 郵件伺服器
@       IN  MX    10 cloudmart-com.mail.protection.outlook.com.

; SPF 記錄（防止郵件偽造）
@       IN  TXT   "v=spf1 include:spf.protection.outlook.com -all"

; DKIM 記錄（郵件簽名驗證）
selector1._domainkey  IN  CNAME  selector1-cloudmart-com._domainkey.cloudmart.onmicrosoft.com.
```

### 3.2.5 TTL（Time To Live）的重要性

**TTL** 決定了 DNS 記錄可以被快取多久。

```
┌─────────────────────────────────────────────────────────────────┐
│                     TTL 策略考量                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TTL 設定較長（例如 86400 秒 = 24 小時）                         │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ ✅ 優點：                                                  │ │
│  │    • DNS 查詢次數減少                                      │ │
│  │    • 用戶端延遲降低                                        │ │
│  │    • DNS 伺服器負載減輕                                    │ │
│  │                                                           │ │
│  │ ❌ 缺點：                                                  │ │
│  │    • 變更生效慢（最多要等 24 小時）                        │ │
│  │    • 災難復原時間長                                        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  TTL 設定較短（例如 60 秒 = 1 分鐘）                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ ✅ 優點：                                                  │ │
│  │    • 變更快速生效                                          │ │
│  │    • 快速切換伺服器                                        │ │
│  │    • 適合動態負載平衡                                      │ │
│  │                                                           │ │
│  │ ❌ 缺點：                                                  │ │
│  │    • DNS 查詢次數增加                                      │ │
│  │    • 每次查詢都有額外延遲                                  │ │
│  │    • DNS 伺服器負載增加                                    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  CloudMart 的策略：                                              │
│  • 平時 TTL = 300 秒（5 分鐘）                                  │
│  • 計畫變更前，先降低 TTL 到 60 秒                              │
│  • 變更完成後，等待 1 小時再恢復 TTL                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3.3 CDN：內容分發網路

### 3.3.1 什麼是 CDN？

**CDN（Content Delivery Network）** 是一個分散在全球各地的伺服器網路，用來快取和傳遞內容。

```
┌─────────────────────────────────────────────────────────────────┐
│                       CDN 運作原理                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                        沒有 CDN                                  │
│                                                                 │
│   東京用戶 ─────── 9,000km ───────► 台北伺服器                  │
│   延遲：180ms                                                   │
│                                                                 │
│   紐約用戶 ─────── 15,000km ──────► 台北伺服器                  │
│   延遲：280ms                                                   │
│                                                                 │
│   ════════════════════════════════════════════════════════     │
│                                                                 │
│                        使用 CDN                                  │
│                                                                 │
│                    ┌──────────────┐                             │
│                    │  台北原站    │                              │
│                    │ (Origin)     │                              │
│                    └──────┬───────┘                             │
│                           │ 同步快取                             │
│            ┌──────────────┼──────────────┐                      │
│            │              │              │                      │
│            ▼              ▼              ▼                      │
│     ┌──────────┐   ┌──────────┐   ┌──────────┐                 │
│     │ 東京 POP │   │ 香港 POP │   │ 紐約 POP │                  │
│     │   節點   │   │   節點   │   │   節點   │                  │
│     └────┬─────┘   └──────────┘   └────┬─────┘                 │
│          │                              │                       │
│          ▼                              ▼                       │
│     東京用戶                        紐約用戶                     │
│     延遲：5ms                       延遲：10ms                   │
│                                                                 │
│   POP = Point of Presence（接入點）                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3.2 CDN 快取策略

```
┌─────────────────────────────────────────────────────────────────┐
│                     CDN 快取決策流程                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用戶請求                                                        │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────┐                        │
│  │ 檢查 CDN 節點是否有快取            │                         │
│  └─────────────────┬───────────────────┘                        │
│           有快取 ──┴── 沒有快取                                  │
│           │              │                                      │
│           ▼              ▼                                      │
│  ┌────────────┐   ┌────────────────┐                            │
│  │ 快取過期？ │   │ 向原站請求內容 │                             │
│  └─────┬──────┘   └───────┬────────┘                            │
│    是 ─┴─ 否              │                                     │
│    │      │              │                                      │
│    │      ▼              │                                      │
│    │  直接回傳           │                                      │
│    │  (Cache HIT)        │                                      │
│    │                     │                                      │
│    ▼                     ▼                                      │
│  ┌─────────────────────────────────────┐                        │
│  │ 向原站驗證（If-Modified-Since）    │                         │
│  └─────────────────┬───────────────────┘                        │
│      未修改(304) ──┴── 已修改(200)                               │
│           │              │                                      │
│           ▼              ▼                                      │
│      使用舊快取      更新快取                                    │
│                      回傳新內容                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3.3 快取控制標頭

```http
# CloudMart 的快取策略

# 靜態資源（CSS, JS, 圖片）- 長期快取
Cache-Control: public, max-age=31536000, immutable
# 說明：
# - public: CDN 可以快取
# - max-age=31536000: 快取 1 年
# - immutable: 內容不會變（檔名包含 hash）

# HTML 頁面 - 短期快取
Cache-Control: public, max-age=300, must-revalidate
# 說明：
# - max-age=300: 快取 5 分鐘
# - must-revalidate: 過期後必須驗證

# API 回應 - 不快取
Cache-Control: no-store, no-cache, must-revalidate, private
# 說明：
# - no-store: 不要儲存任何快取
# - private: 只有用戶瀏覽器可以快取，CDN 不行

# 用戶資料 - 私有快取
Cache-Control: private, max-age=0
# 說明：
# - private: 包含用戶個人資料，不可被 CDN 快取
```

### 3.3.4 CloudMart 的 CDN 配置（Azure CDN）

```json
// Azure CDN 設定
{
  "name": "cloudmart-cdn-profile",
  "sku": {
    "name": "Standard_Microsoft"
  },
  "endpoints": [
    {
      "name": "cloudmart-static",
      "originHostName": "cloudmartstatic.blob.core.windows.net",
      "isHttpAllowed": false,
      "isHttpsAllowed": true,
      "optimizationType": "GeneralWebDelivery",
      "cachingRules": [
        {
          "matchCondition": {
            "matchVariable": "UrlFileExtension",
            "operator": "Equal",
            "matchValue": ["js", "css", "woff2", "woff", "ttf"]
          },
          "cacheExpirationAction": {
            "cacheBehavior": "Override",
            "cacheType": "All",
            "cacheDuration": "365.00:00:00"
          }
        },
        {
          "matchCondition": {
            "matchVariable": "UrlFileExtension",
            "operator": "Equal",
            "matchValue": ["jpg", "jpeg", "png", "gif", "webp", "svg"]
          },
          "cacheExpirationAction": {
            "cacheBehavior": "Override",
            "cacheType": "All",
            "cacheDuration": "30.00:00:00"
          }
        }
      ],
      "geoFilters": [
        {
          "relativePath": "/",
          "action": "Allow",
          "countryCodes": ["TW", "JP", "HK", "SG", "US"]
        }
      ]
    }
  ]
}
```

### 3.3.5 Azure Front Door：進階 CDN 解決方案

**Azure Front Door** 不只是 CDN，還提供：

- 全球負載平衡
- SSL 卸載
- WAF（Web Application Firewall）
- URL 路由
- 健康檢查

```
┌─────────────────────────────────────────────────────────────────┐
│                   Azure Front Door 架構                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                         網際網路                                 │
│                            │                                    │
│                            ▼                                    │
│              ┌─────────────────────────┐                        │
│              │    Azure Front Door     │                        │
│              │                         │                        │
│              │  ┌───────────────────┐  │                        │
│              │  │       WAF         │  │◄── 過濾惡意請求         │
│              │  └───────────────────┘  │                        │
│              │  ┌───────────────────┐  │                        │
│              │  │   SSL 終止        │  │◄── HTTPS 解密          │
│              │  └───────────────────┘  │                        │
│              │  ┌───────────────────┐  │                        │
│              │  │   URL 路由        │  │◄── 根據路徑分流         │
│              │  └───────────────────┘  │                        │
│              │  ┌───────────────────┐  │                        │
│              │  │   健康檢查        │  │◄── 自動故障轉移         │
│              │  └───────────────────┘  │                        │
│              └───────────┬─────────────┘                        │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 東亞區域    │  │ 美國東部    │  │ 歐洲西部    │              │
│  │ (台北/東京) │  │ (維吉尼亞) │  │ (阿姆斯特丹)│              │
│  │             │  │             │  │             │              │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │              │
│  │ │ Web App │ │  │ │ Web App │ │  │ │ Web App │ │              │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │              │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  路由規則：                                                      │
│  • /api/* → 最近的 API 伺服器                                   │
│  • /static/* → CDN 快取                                         │
│  • /* → 最近的 Web App                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3.4 防火牆：網路的守門員

### 3.4.1 什麼是防火牆？

**防火牆（Firewall）** 監控並控制網路流量，根據預設的安全規則允許或拒絕流量。

```
┌─────────────────────────────────────────────────────────────────┐
│                     防火牆運作原理                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                         網際網路                                 │
│                            │                                    │
│    正常用戶請求 ───────────┼───────────── 惡意攻擊               │
│         ✓                  │                  ✗                 │
│                            ▼                                    │
│              ┌─────────────────────────┐                        │
│              │        防火牆           │                        │
│              │                         │                        │
│              │  規則 1: 允許 TCP 443   │ ──► HTTPS 流量 ✓       │
│              │  規則 2: 允許 TCP 80    │ ──► HTTP 流量 ✓        │
│              │  規則 3: 拒絕 TCP 22    │ ──► SSH 來自外部 ✗     │
│              │  規則 4: 拒絕 TCP 3306  │ ──► MySQL 來自外部 ✗   │
│              │  規則 5: 拒絕所有其他   │ ──► 預設拒絕 ✗         │
│              │                         │                        │
│              └───────────┬─────────────┘                        │
│                          │                                      │
│                          ▼                                      │
│                   ┌─────────────┐                               │
│                   │  內部網路   │                                │
│                   │  伺服器群   │                                │
│                   └─────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4.2 防火牆規則的組成

每條防火牆規則通常包含：

| 元素 | 說明 | 範例 |
|------|------|------|
| **優先級** | 規則的處理順序 | 100（數字越小優先級越高） |
| **名稱** | 規則的識別名稱 | Allow-HTTPS |
| **來源** | 流量來源 | Any / 特定 IP / IP 範圍 |
| **來源連接埠** | 來源埠號 | * (任何) |
| **目的地** | 流量目的地 | 10.0.1.0/24 |
| **目的連接埠** | 目的埠號 | 443 |
| **協定** | 網路協定 | TCP / UDP / ICMP / Any |
| **動作** | 允許或拒絕 | Allow / Deny |

### 3.4.3 Azure 網路安全組（NSG）

**NSG（Network Security Group）** 是 Azure 提供的基本防火牆功能。

```json
// CloudMart Web 伺服器 NSG 設定
{
  "name": "cloudmart-web-nsg",
  "securityRules": [
    {
      "name": "Allow-HTTPS-Inbound",
      "priority": 100,
      "direction": "Inbound",
      "access": "Allow",
      "protocol": "Tcp",
      "sourceAddressPrefix": "*",
      "sourcePortRange": "*",
      "destinationAddressPrefix": "*",
      "destinationPortRange": "443"
    },
    {
      "name": "Allow-HTTP-Inbound",
      "priority": 110,
      "direction": "Inbound",
      "access": "Allow",
      "protocol": "Tcp",
      "sourceAddressPrefix": "*",
      "sourcePortRange": "*",
      "destinationAddressPrefix": "*",
      "destinationPortRange": "80"
    },
    {
      "name": "Allow-SSH-from-Bastion",
      "priority": 200,
      "direction": "Inbound",
      "access": "Allow",
      "protocol": "Tcp",
      "sourceAddressPrefix": "10.0.0.0/24",
      "sourcePortRange": "*",
      "destinationAddressPrefix": "*",
      "destinationPortRange": "22"
    },
    {
      "name": "Deny-All-Inbound",
      "priority": 4096,
      "direction": "Inbound",
      "access": "Deny",
      "protocol": "*",
      "sourceAddressPrefix": "*",
      "sourcePortRange": "*",
      "destinationAddressPrefix": "*",
      "destinationPortRange": "*"
    }
  ]
}
```

### 3.4.4 CloudMart 多層防火牆架構

```
┌─────────────────────────────────────────────────────────────────┐
│                 CloudMart 深度防禦架構                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  網際網路                                                        │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 第一層：Azure DDoS Protection                           │   │
│  │ • 自動偵測並緩解 DDoS 攻擊                               │   │
│  │ • 流量清洗                                               │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                    │
│                           ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 第二層：Azure Front Door WAF                            │   │
│  │ • SQL Injection 防護                                    │   │
│  │ • XSS 防護                                              │   │
│  │ • Bot 偵測                                              │   │
│  │ • Rate Limiting                                         │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                    │
│                           ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 第三層：Azure Firewall                                  │   │
│  │ • 應用層過濾                                            │   │
│  │ • FQDN 過濾                                             │   │
│  │ • 威脅情報                                              │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                    │
│                           ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 第四層：Network Security Group (NSG)                    │   │
│  │ • 子網路層級控制                                        │   │
│  │ • VM 層級控制                                           │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                    │
│                           ▼                                    │
│               ┌─────────────────────┐                          │
│               │    CloudMart VM     │                          │
│               └─────────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4.5 WAF 規則範例

```json
// Azure WAF 自訂規則
{
  "name": "cloudmart-waf-policy",
  "managedRules": {
    "managedRuleSets": [
      {
        "ruleSetType": "OWASP",
        "ruleSetVersion": "3.2"
      }
    ]
  },
  "customRules": [
    {
      "name": "BlockBadBots",
      "priority": 1,
      "ruleType": "MatchRule",
      "matchConditions": [
        {
          "matchVariables": [
            {
              "variableName": "RequestHeaders",
              "selector": "User-Agent"
            }
          ],
          "operator": "Contains",
          "matchValues": ["sqlmap", "nikto", "nessus", "havij"]
        }
      ],
      "action": "Block"
    },
    {
      "name": "RateLimitByIP",
      "priority": 2,
      "ruleType": "RateLimitRule",
      "rateLimitThreshold": 100,
      "rateLimitDurationInMinutes": 1,
      "matchConditions": [
        {
          "matchVariables": [
            {
              "variableName": "RequestUri"
            }
          ],
          "operator": "Contains",
          "matchValues": ["/api/"]
        }
      ],
      "action": "Block"
    },
    {
      "name": "BlockSuspiciousCountries",
      "priority": 3,
      "ruleType": "MatchRule",
      "matchConditions": [
        {
          "matchVariables": [
            {
              "variableName": "RemoteAddr"
            }
          ],
          "operator": "GeoMatch",
          "matchValues": ["XX", "YY"]
        }
      ],
      "action": "Block"
    }
  ]
}
```

---

## 3.5 CORS：跨域資源共享

### 3.5.1 什麼是同源政策？

**同源政策（Same-Origin Policy）** 是瀏覽器的安全機制，限制來自不同來源的腳本存取資源。

**什麼是「同源」？**

三個條件都必須相同：
1. 協定（http / https）
2. 域名（www.cloudmart.com）
3. 連接埠（:443）

```
┌─────────────────────────────────────────────────────────────────┐
│                     同源判斷範例                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  基準 URL: https://www.cloudmart.com/products                   │
│                                                                 │
│  URL                                          同源？   原因     │
│  ─────────────────────────────────────────────────────────────  │
│  https://www.cloudmart.com/orders             ✓        路徑不同 │
│  https://www.cloudmart.com:443/cart           ✓        預設埠   │
│  http://www.cloudmart.com/products            ✗        協定不同 │
│  https://api.cloudmart.com/products           ✗        域名不同 │
│  https://www.cloudmart.com:8080/products      ✗        埠號不同 │
│  https://cloudmart.com/products               ✗        域名不同 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5.2 為什麼需要 CORS？

CloudMart 的前端是單頁應用程式（SPA），託管在 `www.cloudmart.com`。
但 API 伺服器在 `api.cloudmart.com`。

這是不同的「來源」，所以瀏覽器會阻擋請求。

```
┌─────────────────────────────────────────────────────────────────┐
│                   CORS 問題情境                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用戶瀏覽器                                                      │
│       │                                                         │
│       │ ① 載入網頁                                              │
│       ▼                                                         │
│  ┌───────────────────────────┐                                  │
│  │ https://www.cloudmart.com │ ◄── 前端 SPA                     │
│  └────────────┬──────────────┘                                  │
│               │                                                 │
│               │ ② JavaScript 發送 API 請求                      │
│               ▼                                                 │
│  ┌───────────────────────────┐                                  │
│  │ https://api.cloudmart.com │ ◄── API 伺服器                   │
│  └────────────┬──────────────┘                                  │
│               │                                                 │
│               │ ③ 瀏覽器檢查：這是跨域請求！                     │
│               │                                                 │
│               ▼                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 如果伺服器沒有正確設定 CORS 標頭：                         │ │
│  │                                                           │ │
│  │ 🔴 Access to XMLHttpRequest at 'https://api.cloudmart.com'│ │
│  │    from origin 'https://www.cloudmart.com' has been       │ │
│  │    blocked by CORS policy: No 'Access-Control-Allow-      │ │
│  │    Origin' header is present on the requested resource.   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5.3 CORS 的運作方式

**簡單請求（Simple Request）：**

```
┌─────────────────────────────────────────────────────────────────┐
│                   簡單請求流程                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  瀏覽器                                           API 伺服器    │
│                                                                 │
│       │  GET /api/products HTTP/1.1                │            │
│       │  Host: api.cloudmart.com                   │            │
│       │  Origin: https://www.cloudmart.com         │            │
│       │ ──────────────────────────────────────────►│            │
│       │                                            │            │
│       │  HTTP/1.1 200 OK                           │            │
│       │  Access-Control-Allow-Origin: https://www.cloudmart.com │
│       │  Content-Type: application/json            │            │
│       │  {...}                                     │            │
│       │ ◄──────────────────────────────────────────│            │
│                                                                 │
│  簡單請求的條件：                                                │
│  • 方法：GET, HEAD, POST                                        │
│  • 標頭：只有 Accept, Accept-Language, Content-Language,       │
│          Content-Type (text/plain, multipart/form-data,        │
│          application/x-www-form-urlencoded)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**預檢請求（Preflight Request）：**

```
┌─────────────────────────────────────────────────────────────────┐
│                   預檢請求流程                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  瀏覽器                                           API 伺服器    │
│                                                                 │
│  ① 預檢請求 (OPTIONS)                                           │
│       │  OPTIONS /api/orders HTTP/1.1              │            │
│       │  Host: api.cloudmart.com                   │            │
│       │  Origin: https://www.cloudmart.com         │            │
│       │  Access-Control-Request-Method: POST       │            │
│       │  Access-Control-Request-Headers: Content-Type, Authorization │
│       │ ──────────────────────────────────────────►│            │
│       │                                            │            │
│       │  HTTP/1.1 204 No Content                   │            │
│       │  Access-Control-Allow-Origin: https://www.cloudmart.com │
│       │  Access-Control-Allow-Methods: GET, POST, PUT, DELETE   │
│       │  Access-Control-Allow-Headers: Content-Type, Authorization │
│       │  Access-Control-Max-Age: 86400             │            │
│       │ ◄──────────────────────────────────────────│            │
│       │                                            │            │
│  ② 實際請求                                                     │
│       │  POST /api/orders HTTP/1.1                 │            │
│       │  Host: api.cloudmart.com                   │            │
│       │  Origin: https://www.cloudmart.com         │            │
│       │  Content-Type: application/json            │            │
│       │  Authorization: Bearer eyJhbG...           │            │
│       │  {"product_id": "ABC123"}                  │            │
│       │ ──────────────────────────────────────────►│            │
│       │                                            │            │
│       │  HTTP/1.1 201 Created                      │            │
│       │  Access-Control-Allow-Origin: https://www.cloudmart.com │
│       │  {"order_id": "ORD-001"}                   │            │
│       │ ◄──────────────────────────────────────────│            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5.4 CloudMart API 的 CORS 設定

```javascript
// Express.js CORS 設定
const cors = require('cors');

const corsOptions = {
  // 允許的來源
  origin: [
    'https://www.cloudmart.com',
    'https://admin.cloudmart.com',
    'http://localhost:3000' // 開發環境
  ],

  // 允許的 HTTP 方法
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],

  // 允許的標頭
  allowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Request-ID',
    'X-Correlation-ID'
  ],

  // 允許客戶端讀取的回應標頭
  exposedHeaders: [
    'X-Request-ID',
    'X-RateLimit-Remaining'
  ],

  // 是否允許攜帶 Cookie
  credentials: true,

  // 預檢請求的快取時間（秒）
  maxAge: 86400,

  // 預檢請求成功時的狀態碼
  optionsSuccessStatus: 204
};

app.use(cors(corsOptions));
```

```nginx
# Nginx CORS 設定
server {
    listen 443 ssl;
    server_name api.cloudmart.com;

    location /api/ {
        # 檢查來源是否允許
        if ($http_origin ~* (https://www\.cloudmart\.com|https://admin\.cloudmart\.com)) {
            set $cors_origin $http_origin;
        }

        # 預檢請求處理
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' $cors_origin always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization, X-Request-ID' always;
            add_header 'Access-Control-Max-Age' 86400 always;
            add_header 'Content-Length' 0;
            return 204;
        }

        # 實際請求
        add_header 'Access-Control-Allow-Origin' $cors_origin always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
        add_header 'Access-Control-Expose-Headers' 'X-Request-ID' always;

        proxy_pass http://backend;
    }
}
```

---

## 3.6 動手實作：配置 Azure Front Door

### 3.6.1 建立 Front Door 設定檔

```bash
# 建立資源群組
az group create \
    --name CloudMart-Network \
    --location eastasia

# 建立 Front Door 設定檔
az afd profile create \
    --resource-group CloudMart-Network \
    --profile-name cloudmart-frontdoor \
    --sku Premium_AzureFrontDoor

# 建立端點
az afd endpoint create \
    --resource-group CloudMart-Network \
    --profile-name cloudmart-frontdoor \
    --endpoint-name cloudmart \
    --enabled-state Enabled
```

### 3.6.2 設定後端來源群組

```bash
# 建立來源群組
az afd origin-group create \
    --resource-group CloudMart-Network \
    --profile-name cloudmart-frontdoor \
    --origin-group-name cloudmart-origins \
    --probe-request-type GET \
    --probe-protocol Https \
    --probe-path /health \
    --probe-interval-in-seconds 30 \
    --sample-size 4 \
    --successful-samples-required 3

# 新增台北來源
az afd origin create \
    --resource-group CloudMart-Network \
    --profile-name cloudmart-frontdoor \
    --origin-group-name cloudmart-origins \
    --origin-name taipei-origin \
    --host-name cloudmart-taipei.azurewebsites.net \
    --origin-host-header cloudmart-taipei.azurewebsites.net \
    --http-port 80 \
    --https-port 443 \
    --priority 1 \
    --weight 1000 \
    --enabled-state Enabled

# 新增東京來源
az afd origin create \
    --resource-group CloudMart-Network \
    --profile-name cloudmart-frontdoor \
    --origin-group-name cloudmart-origins \
    --origin-name tokyo-origin \
    --host-name cloudmart-tokyo.azurewebsites.net \
    --origin-host-header cloudmart-tokyo.azurewebsites.net \
    --http-port 80 \
    --https-port 443 \
    --priority 1 \
    --weight 1000 \
    --enabled-state Enabled
```

### 3.6.3 設定路由規則

```bash
# 建立路由規則
az afd route create \
    --resource-group CloudMart-Network \
    --profile-name cloudmart-frontdoor \
    --endpoint-name cloudmart \
    --route-name default-route \
    --origin-group cloudmart-origins \
    --supported-protocols Https \
    --patterns "/*" \
    --forwarding-protocol HttpsOnly \
    --https-redirect Enabled \
    --enabled-state Enabled
```

### 3.6.4 設定 WAF 策略

```bash
# 建立 WAF 策略
az network front-door waf-policy create \
    --resource-group CloudMart-Network \
    --name cloudmartwafpolicy \
    --sku Premium_AzureFrontDoor \
    --mode Prevention

# 啟用受管規則集（OWASP）
az network front-door waf-policy managed-rule-definition list

az network front-door waf-policy managed-rules add \
    --resource-group CloudMart-Network \
    --policy-name cloudmartwafpolicy \
    --type Microsoft_DefaultRuleSet \
    --version 2.1 \
    --action Block

# 新增自訂規則：限制 IP 請求速率
az network front-door waf-policy rule create \
    --resource-group CloudMart-Network \
    --policy-name cloudmartwafpolicy \
    --name RateLimitRule \
    --priority 100 \
    --action Block \
    --rule-type RateLimitRule \
    --rate-limit-threshold 100 \
    --rate-limit-duration-in-minutes 1

# 將 WAF 策略關聯到 Front Door
az afd security-policy create \
    --resource-group CloudMart-Network \
    --profile-name cloudmart-frontdoor \
    --security-policy-name cloudmart-waf \
    --waf-policy /subscriptions/{subscription-id}/resourceGroups/CloudMart-Network/providers/Microsoft.Network/FrontDoorWebApplicationFirewallPolicies/cloudmartwafpolicy \
    --domains /subscriptions/{subscription-id}/resourceGroups/CloudMart-Network/providers/Microsoft.Cdn/profiles/cloudmart-frontdoor/afdEndpoints/cloudmart
```

---

## 3.7 效能優化成果

經過 DNS 優化、CDN 部署和防火牆配置後，CloudMart 的全球存取體驗大幅改善：

```
┌─────────────────────────────────────────────────────────────────┐
│                     效能改善對比                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  地區          優化前        優化後        改善幅度              │
│  ─────────────────────────────────────────────────────────────  │
│  台北          200ms         50ms          -75%                 │
│  東京          1,680ms       120ms         -93%                 │
│  新加坡        800ms         100ms         -88%                 │
│  舊金山        2,200ms       150ms         -93%                 │
│  法蘭克福      2,800ms       180ms         -94%                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    優化措施                              │   │
│  │                                                         │   │
│  │  ✓ DNS：使用 Azure Traffic Manager 地理路由             │   │
│  │  ✓ CDN：靜態資源快取在 200+ 全球節點                    │   │
│  │  ✓ 多區域部署：台北、東京、新加坡、美西                  │   │
│  │  ✓ 連線優化：HTTP/2、TLS 1.3、連線重用                  │   │
│  │  ✓ 壓縮：Brotli 壓縮、圖片最佳化                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  業務影響：                                                      │
│  • 日本市場跳出率：-45%                                         │
│  • 全球轉換率：+23%                                             │
│  • 客訴減少：-67%                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3.8 章節總結

### 核心概念回顧

| 概念 | 說明 | Azure 服務 |
|------|------|-----------|
| **DNS** | 將域名轉換為 IP | Azure DNS |
| **CDN** | 快取並加速內容傳遞 | Azure CDN / Front Door |
| **防火牆** | 過濾網路流量 | NSG / Azure Firewall / WAF |
| **CORS** | 允許跨域請求 | 應用程式設定 |
| **負載平衡** | 分散流量到多個伺服器 | Azure Load Balancer / Front Door |

### AZ-900 考試重點

1. **DNS 記錄類型**：A、AAAA、CNAME、MX、TXT
2. **CDN 的優點**：降低延遲、減少原站負載、提高可用性
3. **NSG vs. Azure Firewall**：知道各自的使用場景
4. **WAF**：了解它如何防禦 Web 攻擊

### 學習檢查清單

完成本章後，請確認你可以：

- [ ] 解釋 DNS 查詢的過程
- [ ] 區分不同 DNS 記錄類型的用途
- [ ] 說明 CDN 如何加速內容傳遞
- [ ] 設計適當的快取策略
- [ ] 配置基本的防火牆規則
- [ ] 理解 CORS 的運作方式並解決跨域問題
- [ ] 在 Azure 上配置 Front Door

---

## 3.9 下一章預告

在下一章「解構單體架構」中，我們將探討：

- 為什麼 CloudMart 的單體應用程式無法應對流量高峰？
- 如何將單體應用拆分為微服務？
- Docker 容器化如何簡化部署？
- Kubernetes 如何管理大規模的容器叢集？

這些知識將幫助你理解現代雲端應用程式的架構設計。

---

## 延伸閱讀

- [Azure DNS 文件](https://docs.microsoft.com/azure/dns/)
- [Azure Front Door 文件](https://docs.microsoft.com/azure/frontdoor/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)

---

**上一章：[第 2 章：透視網路傳輸](./chapter-02.md)**

**下一章：[第 4 章：解構單體架構](./chapter-04.md)**
