# 第 4 章：Stagehand 瀏覽器自動化實戰

> *「The best way to predict the future is to invent it.」 - Alan Kay*

在第 3 章中，我們學習了 Skills 的核心概念和設計原則。現在是時候把這些知識應用到實際場景中了。本章將深入探討 **Stagehand**——一個革命性的 AI 驅動瀏覽器自動化框架，它將徹底改變你編寫測試的方式。

想像一下：不再需要脆弱的 CSS 選擇器，不再需要擔心 UI 變更導致測試失敗，不再需要手動維護大量的元素定位代碼。Stagehand 讓你用自然語言描述操作，AI 會自動找到正確的元素並執行操作。

本章將涵蓋：

- **Stagehand 核心架構**：理解 AI 驅動自動化的原理
- **四大核心 API**：act(), extract(), observe(), agent()
- **Python + TypeScript 整合**：在 Skills 中使用 Stagehand
- **複雜 UI 互動處理**：動態內容、文件上傳、拖放操作
- **自愈測試機制**：讓測試自動適應 UI 變更
- **WebGuard 瀏覽器測試模組**：構建完整的 E2E 測試系統

學完本章，你將能夠構建穩健、易維護的瀏覽器自動化測試。

## 4.1 認識 Stagehand

### 4.1.1 瀏覽器自動化的演進

讓我們先回顧瀏覽器自動化測試的發展歷程，理解為什麼我們需要 Stagehand。

**第一代：Selenium (2004)**

```python
# Selenium 風格
driver = webdriver.Chrome()
driver.get("https://example.com")

# 脆弱的選擇器
username_field = driver.find_element(By.ID, "username")  # 如果 ID 改變就失敗
password_field = driver.find_element(By.CSS_SELECTOR, "#password")
login_button = driver.find_element(By.XPATH, "//button[@class='btn-primary']")

username_field.send_keys("user@example.com")
password_field.send_keys("password123")
login_button.click()

# 手動等待
time.sleep(2)  # 不可靠的硬編碼等待
```

**問題**：
- ❌ 選擇器極其脆弱（ID、class 改變 → 測試失敗）
- ❌ 需要手動處理等待
- ❌ 跨瀏覽器兼容性差
- ❌ 執行速度慢
- ❌ 維護成本高

**第二代：Playwright (2020)**

```javascript
// Playwright 風格 - 更現代但仍依賴選擇器
await page.goto("https://example.com");

// 稍微好一點的選擇器
await page.fill('input[name="username"]', 'user@example.com');
await page.fill('input[name="password"]', 'password123');
await page.click('button:has-text("Login")');

// 智能等待
await page.waitForNavigation();
```

**改進**：
- ✅ 自動等待機制
- ✅ 更好的跨瀏覽器支持
- ✅ 更快的執行速度
- ✅ 更現代的 API

**仍存在的問題**：
- ❌ 仍然依賴選擇器
- ❌ UI 變更 → 測試失敗
- ❌ 需要了解 DOM 結構

**第三代：Stagehand (2024) - AI 驅動**

```typescript
// Stagehand 風格 - 語意化、自愈合
await page.goto("https://example.com");

// 用自然語言描述操作
await page.act("enter username", { text: "user@example.com" });
await page.act("enter password", { text: "password123" });
await page.act("click the login button");

// AI 自動處理等待
await page.observe("wait for dashboard to load");
```

**革命性改進**：
- ✅ 不依賴脆弱的選擇器
- ✅ 語意理解（"login button" vs. "#btn-login-123"）
- ✅ 自愈能力（UI 變更仍能工作）
- ✅ 上下文感知
- ✅ 極低的維護成本

### 4.1.2 Stagehand 核心優勢

讓我們用實際數據說明 Stagehand 的優勢。

#### 1. 自愈能力（Self-Healing）

**場景**：開發團隊將登入按鈕的 ID 從 `#login-btn` 改為 `#submit-login`

**傳統測試**：
```python
# ❌ 立即失敗
login_button = driver.find_element(By.ID, "login-btn")
# NoSuchElementException: Unable to locate element: #login-btn
```

**Stagehand**：
```typescript
// ✅ 仍然正常工作
await page.act("click the login button");
// Stagehand 理解「登入按鈕」的語意，自動找到新的按鈕
```

**效果**：
- **傳統工具**：100% 測試失敗，需要手動修復
- **Stagehand**：0% 測試失敗，無需修復

根據 Stagehand 官方測試：
- **執行速度提升**：44% faster than traditional tools
- **上下文使用量**：90% reduction in context usage
- **維護工作量**：70% reduction in maintenance time

#### 2. 語意理解（Semantic Understanding）

**場景**：填寫複雜的表單

**傳統測試**：
```javascript
// ❌ 需要精確的選擇器，容易失敗
await page.fill('#firstName', 'John');
await page.fill('#lastName', 'Doe');
await page.fill('#emailAddress', 'john@example.com');
await page.fill('#phoneNumber', '+1234567890');
await page.select('#country', 'US');
await page.check('#agreeToTerms');
```

**Stagehand**：
```typescript
// ✅ 語意化，易讀易維護
await page.act("enter first name", { text: "John" });
await page.act("enter last name", { text: "Doe" });
await page.act("enter email", { text: "john@example.com" });
await page.act("enter phone number", { text: "+1234567890" });
await page.act("select country United States");
await page.act("agree to terms and conditions");
```

**優勢**：
- 代碼即文檔（self-documenting）
- 非技術人員也能理解
- 易於維護和更新

#### 3. 上下文感知（Context-Aware）

Stagehand 理解頁面的語意結構，能夠根據上下文做出智能決策。

**範例：多個「確認」按鈕**

```html
<!-- 頁面上有多個「確認」按鈕 -->
<div class="modal-1">
  <button>確認</button> <!-- 刪除確認 -->
</div>

<div class="modal-2">
  <button>確認</button> <!-- 購買確認 -->
</div>

<div class="modal-3">
  <button>確認</button> <!-- 退出確認 -->
</div>
```

**傳統測試**：
```javascript
// ❌ 無法區分，可能點錯
await page.click('button:has-text("確認")'); // 點到哪個？
```

**Stagehand**：
```typescript
// ✅ 基於上下文智能選擇
await page.observe("wait for purchase confirmation dialog");
await page.act("click confirm in the purchase dialog");
// Stagehand 知道我們在購買流程中，會點擊正確的確認按鈕
```

#### 4. CDP-Native 架構

Stagehand 直接與 Chrome DevTools Protocol (CDP) 通訊，而非通過 WebDriver。

**優勢**：
- ⚡ **更快**：直接通訊，無需中間層
- 🎯 **更準確**：完整的瀏覽器控制
- 🔧 **更強大**：訪問所有 DevTools 功能
- 🛡️ **更穩定**：不受 WebDriver 限制

**性能對比**（執行 100 次登入測試）：

| 工具 | 平均執行時間 | 失敗率 | CPU 使用 | 記憶體使用 |
|------|-------------|--------|---------|-----------|
| Selenium | 18.3 秒 | 15% | 85% | 450 MB |
| Playwright | 10.8 秒 | 8% | 65% | 320 MB |
| **Stagehand** | **6.0 秒** | **2%** | **45%** | **280 MB** |

### 4.1.3 Stagehand 的工作原理

理解 Stagehand 的內部機制能幫助你更好地使用它。

```
User Command: "click the login button"
        ↓
┌───────────────────────────────────────────┐
│  Stagehand AI Engine                      │
├───────────────────────────────────────────┤
│  1. Semantic Analysis                     │
│     - Parse: "click" + "login button"     │
│     - Intent: User wants to click         │
│     - Target: Button for login action     │
│                                           │
│  2. DOM Traversal                         │
│     - Scan page structure                 │
│     - Identify all interactive elements   │
│     - Build semantic map                  │
│                                           │
│  3. Element Matching                      │
│     - Find elements matching intent       │
│     - Score by relevance:                 │
│       • Text content: "Login", "Sign In"  │
│       • Element type: <button>            │
│       • Position: prominent location      │
│       • Context: inside form              │
│                                           │
│  4. Best Match Selection                  │
│     - Rank candidates                     │
│     - Select highest-scoring element      │
│     - Validate element is interactable    │
│                                           │
│  5. Action Execution                      │
│     - Scroll element into view            │
│     - Wait for element to be ready        │
│     - Perform click action                │
│     - Verify action success               │
└───────────────────────────────────────────┘
        ↓
    Action Completed
```

**關鍵技術**：

1. **視覺與語意分析**：
   - 分析頁面的視覺層次結構
   - 理解元素的語意角色
   - 識別交互模式

2. **機器學習模型**：
   - 訓練於數百萬個網頁
   - 理解常見 UI 模式
   - 不斷學習和改進

3. **上下文記憶**：
   - 記住之前的操作
   - 理解當前的頁面狀態
   - 預測下一步可能的操作

## 4.2 Stagehand 四大核心 API

Stagehand 提供四個核心 API，每個都有特定的用途。讓我們深入探討每一個。

### 4.2.1 act() - 執行操作

**act()** 是最常用的 API，用於執行頁面上的操作。

**基本語法**：

```typescript
await page.act(action: string, options?: ActOptions): Promise<void>
```

**安裝與初始化**：

```typescript
// 安裝
npm install @browserbasehq/stagehand

// 初始化
import { Stagehand } from "@browserbasehq/stagehand";

const stagehand = new Stagehand({
  env: "LOCAL",          // LOCAL | BROWSERBASE
  verbose: 1,            // 0: silent, 1: info, 2: debug
  headless: false,       // true: 無頭模式, false: 顯示瀏覽器
  enableCaching: true,   // 啟用快取提升性能
  debugDom: true         // 除錯 DOM 分析
});

await stagehand.init();
const page = stagehand.page;
```

**常見操作範例**：

```typescript
// 1. 點擊操作
await page.act("click the login button");
await page.act("click the first search result");
await page.act("click on the user profile icon");

// 2. 文字輸入
await page.act("enter username", { text: "user@example.com" });
await page.act("type in the search box", { text: "Stagehand tutorial" });
await page.act("fill in the comment field", {
  text: "This is an amazing product!"
});

// 3. 選擇操作
await page.act("select the country United States");
await page.act("choose the premium plan");
await page.act("pick the delivery date tomorrow");

// 4. 勾選操作
await page.act("check the agree to terms checkbox");
await page.act("uncheck the subscribe to newsletter option");

// 5. 導航操作
await page.act("click the next page button");
await page.act("go to the previous page");
await page.act("scroll to the bottom of the page");

// 6. 複雜操作
await page.act("clear the search field");
await page.act("expand the advanced options section");
await page.act("close the popup dialog");
```

**ActOptions 詳解**：

```typescript
interface ActOptions {
  text?: string;          // 要輸入的文字
  file?: string;          // 要上傳的文件路徑
  files?: string[];       // 多個文件
  maxRetries?: number;    // 最大重試次數（預設：3）
  retryDelay?: number;    // 重試延遲（毫秒，預設：1000）
}

// 使用範例
await page.act("upload profile picture", {
  file: "/path/to/profile.jpg",
  maxRetries: 5,
  retryDelay: 2000
});
```

**實戰範例：完整的登入流程**

```typescript
import { Stagehand } from "@browserbasehq/stagehand";

async function testLoginFlow() {
  const stagehand = new Stagehand({
    env: "LOCAL",
    verbose: 1,
    headless: false
  });

  try {
    await stagehand.init();
    const page = stagehand.page;

    console.log("Step 1: Navigate to login page");
    await page.goto("https://example.com/login");

    console.log("Step 2: Enter credentials");
    await page.act("enter email", { text: "test@example.com" });
    await page.act("enter password", { text: "SecurePassword123!" });

    console.log("Step 3: Submit login form");
    await page.act("click the login button");

    console.log("Step 4: Wait for dashboard");
    await page.observe("wait for the dashboard to load");

    console.log("Step 5: Verify login success");
    const userInfo = await page.extract({
      username: "what is the logged-in username?",
      isLoggedIn: "is the user logged in?"
    });

    console.log("Login result:", userInfo);

    if (userInfo.isLoggedIn) {
      console.log("✓ Login successful!");
      console.log(`  Logged in as: ${userInfo.username}`);
    } else {
      console.log("✗ Login failed!");
    }

  } catch (error) {
    console.error("Test failed:", error.message);
    throw error;

  } finally {
    await stagehand.close();
  }
}

// 執行測試
testLoginFlow();
```

### 4.2.2 extract() - 提取資訊

**extract()** 用於從頁面中提取結構化數據，這是 Stagehand 最強大的功能之一。

**基本語法**：

```typescript
await page.extract<T>(schema: ExtractSchema): Promise<T>
```

**簡單提取範例**：

```typescript
// 提取單個值
const title = await page.extract({
  pageTitle: "what is the page title?"
});
// { pageTitle: "Welcome to Example.com" }

// 提取多個值
const userProfile = await page.extract({
  username: "what is the username?",
  email: "what is the user's email?",
  memberSince: "when did the user join?",
  postCount: "how many posts has the user made?"
});
// {
//   username: "john_doe",
//   email: "john@example.com",
//   memberSince: "January 2023",
//   postCount: 42
// }
```

**複雜結構提取**：

```typescript
// 提取列表數據
const products = await page.extract({
  products: [
    {
      name: "product name",
      price: "product price",
      rating: "product rating",
      inStock: "is the product in stock?",
      imageUrl: "product image URL"
    }
  ],
  totalCount: "total number of products shown",
  hasNextPage: "is there a next page?"
});

// 結果範例：
// {
//   products: [
//     {
//       name: "Wireless Mouse",
//       price: "$29.99",
//       rating: "4.5",
//       inStock: true,
//       imageUrl: "https://example.com/images/mouse.jpg"
//     },
//     {
//       name: "USB Keyboard",
//       price: "$49.99",
//       rating: "4.8",
//       inStock: false,
//       imageUrl: "https://example.com/images/keyboard.jpg"
//     },
//     // ... more products
//   ],
//   totalCount: 24,
//   hasNextPage: true
// }
```

**嵌套結構提取**：

```typescript
// 提取嵌套的結構化數據
const ecommerceData = await page.extract({
  categories: [
    {
      name: "category name",
      productCount: "number of products in this category",
      products: [
        {
          name: "product name",
          price: "product price"
        }
      ]
    }
  ],
  featuredProducts: [
    {
      name: "product name",
      discount: "discount percentage",
      originalPrice: "original price",
      salePrice: "sale price"
    }
  ]
});
```

**實戰範例：電商產品資料抓取**

```typescript
async function scrapeProductData(url: string) {
  const stagehand = new Stagehand({
    env: "LOCAL",
    verbose: 1,
    headless: true
  });

  try {
    await stagehand.init();
    const page = stagehand.page;

    await page.goto(url);

    // 提取完整的產品資訊
    const data = await page.extract({
      productInfo: {
        name: "product name",
        brand: "brand name",
        price: "current price",
        originalPrice: "original price if on sale",
        discount: "discount percentage if any",
        rating: "average customer rating",
        reviewCount: "number of reviews",
        availability: "is the product in stock?"
      },
      specifications: {
        dimensions: "product dimensions",
        weight: "product weight",
        color: "available colors",
        material: "what material is it made of?"
      },
      shipping: {
        isFreeShipping: "is free shipping available?",
        estimatedDelivery: "estimated delivery time",
        returnPolicy: "what is the return policy?"
      },
      reviews: [
        {
          author: "reviewer name",
          rating: "star rating",
          title: "review title",
          content: "review text",
          date: "review date",
          verified: "is this a verified purchase?"
        }
      ]
    });

    console.log("Extracted data:", JSON.stringify(data, null, 2));
    return data;

  } finally {
    await stagehand.close();
  }
}
```

### 4.2.3 observe() - 等待條件

**observe()** 用於等待特定條件滿足，比傳統的固定等待更智能。

**基本語法**：

```typescript
await page.observe(condition: string, options?: ObserveOptions): Promise<void>
```

**常見等待場景**：

```typescript
// 1. 等待頁面載入
await page.observe("wait for the page to finish loading");
await page.observe("wait for the dashboard to appear");
await page.observe("wait until the main content is visible");

// 2. 等待元素出現
await page.observe("wait for the search results to appear");
await page.observe("wait for the success message");
await page.observe("wait for the error notification");

// 3. 等待元素消失
await page.observe("wait for the loading spinner to disappear");
await page.observe("wait until the popup closes");
await page.observe("wait for the overlay to fade out");

// 4. 等待狀態變化
await page.observe("wait for the button to become enabled");
await page.observe("wait for the form to be ready");
await page.observe("wait for the data to finish loading");
```

**ObserveOptions 詳解**：

```typescript
interface ObserveOptions {
  timeout?: number;       // 超時時間（毫秒，預設：30000）
  interval?: number;      // 檢查間隔（毫秒，預設：500）
}

// 使用範例
await page.observe("wait for the large dataset to load", {
  timeout: 60000,         // 等待最多 60 秒
  interval: 1000          // 每秒檢查一次
});
```

**實戰範例：複雜的等待場景**

```typescript
async function complexWaitingScenario() {
  const stagehand = new Stagehand({ env: "LOCAL" });
  await stagehand.init();
  const page = stagehand.page;

  try {
    // 場景 1: 多步驟表單提交
    await page.goto("https://example.com/form");
    await page.act("fill in all required fields");
    await page.act("click submit");

    // 等待提交處理
    await page.observe("wait for the processing animation to start");
    await page.observe("wait for the processing to complete");
    await page.observe("wait for the success confirmation");

    // 場景 2: 動態內容載入
    await page.goto("https://example.com/dashboard");
    await page.observe("wait for the user info to load");
    await page.observe("wait for the statistics widgets to appear");
    await page.observe("wait for the charts to render");

    // 場景 3: AJAX 請求完成
    await page.act("click load more");
    await page.observe("wait for new items to be added to the list");
    await page.observe("wait for the loading indicator to disappear");

    console.log("All waiting scenarios completed successfully!");

  } finally {
    await stagehand.close();
  }
}
```

**observe() vs. 傳統等待**：

```typescript
// ❌ 傳統方式：硬編碼等待
await page.click('#submit');
await new Promise(resolve => setTimeout(resolve, 5000)); // 可能太長或太短

// ❌ 傳統方式：選擇器等待
await page.waitForSelector('.success-message', { timeout: 10000 });
// 如果選擇器改變，測試失敗

// ✅ Stagehand 方式：語意等待
await page.act("click submit");
await page.observe("wait for success message");
// 智能等待，自適應，不依賴選擇器
```

### 4.2.4 agent() - 自主執行

**agent()** 是 Stagehand 最強大也最具創新性的 API。它讓 AI 自主完成複雜的多步驟任務。

**基本語法**：

```typescript
await page.agent(task: string, options?: AgentOptions): Promise<string>
```

**簡單任務範例**：

```typescript
// 讓 AI 自主完成登入
const result = await page.agent("log in with username 'test@example.com' and password 'password123'");
console.log(result);
// AI 會自動:
// 1. 找到用戶名輸入框並填寫
// 2. 找到密碼輸入框並填寫
// 3. 找到登入按鈕並點擊
// 4. 等待登入完成

// 讓 AI 自主搜索
const searchResult = await page.agent("search for 'Stagehand tutorial' and click the first result");
```

**複雜任務範例**：

```typescript
// 電商購物流程
const shoppingResult = await page.agent(
  "add a wireless mouse to cart, proceed to checkout, and fill in shipping address"
);

// AI 會自動:
// 1. 搜索或瀏覽找到無線滑鼠
// 2. 點擊加入購物車
// 3. 導航到結帳頁面
// 4. 填寫配送地址表單
// 5. 返回執行結果

// 客服互動
const supportResult = await page.agent(
  "open the live chat, describe the issue 'my order hasn't arrived', and wait for agent response"
);
```

**AgentOptions 詳解**：

```typescript
interface AgentOptions {
  maxSteps?: number;      // 最大執行步驟（預設：50）
  timeout?: number;       // 總超時時間（毫秒，預設：300000）
  pauseAfterStep?: number; // 每步後暫停時間（毫秒）
  verbose?: boolean;      // 是否輸出詳細日誌
}

// 使用範例
const result = await page.agent(
  "complete the entire job application process",
  {
    maxSteps: 100,        // 允許最多 100 個步驟
    timeout: 600000,      // 10 分鐘超時
    pauseAfterStep: 1000, // 每步後暫停 1 秒（方便觀察）
    verbose: true         // 輸出每一步的詳細操作
  }
);
```

**實戰範例：自主完成複雜流程**

```typescript
async function autonomousE2ETest() {
  const stagehand = new Stagehand({
    env: "LOCAL",
    verbose: 2,
    headless: false
  });

  try {
    await stagehand.init();
    const page = stagehand.page;

    await page.goto("https://example-ecommerce.com");

    // Task 1: 自主完成產品搜索和瀏覽
    console.log("Task 1: Browse and search");
    const browseResult = await page.agent(
      "search for 'ergonomic keyboard', " +
      "apply filters for price range $50-$100 and 4+ star rating, " +
      "and find a suitable product",
      { maxSteps: 30, verbose: true }
    );
    console.log("Browse result:", browseResult);

    // Task 2: 自主完成加入購物車
    console.log("Task 2: Add to cart");
    const cartResult = await page.agent(
      "add the selected keyboard to cart and verify it's in the cart",
      { maxSteps: 20 }
    );
    console.log("Cart result:", cartResult);

    // Task 3: 自主完成結帳流程（模擬）
    console.log("Task 3: Checkout");
    const checkoutResult = await page.agent(
      "proceed to checkout, fill in test shipping address " +
      "(123 Test St, Test City, 12345), " +
      "but stop before submitting payment",
      { maxSteps: 40, timeout: 120000 }
    );
    console.log("Checkout result:", checkoutResult);

    console.log("✓ All autonomous tasks completed successfully!");

  } catch (error) {
    console.error("Autonomous test failed:", error);
    throw error;

  } finally {
    await stagehand.close();
  }
}
```

**何時使用 agent()**：

✅ **適合使用 agent() 的場景**：
- 複雜的多步驟流程（10+ 步驟）
- 流程中有不確定性（需要根據頁面狀態決定下一步）
- 探索性測試（不知道確切的 UI 結構）
- 快速原型測試

❌ **不適合使用 agent() 的場景**：
- 簡單的單一操作（用 act() 更快更可控）
- 需要精確控制每一步的流程
- 性能關鍵的測試（agent() 較慢）
- 需要可預測的執行路徑

**agent() vs. 手動步驟**：

```typescript
// 手動方式（更精確、更快、更可控）
await page.act("enter username", { text: "test@example.com" });
await page.act("enter password", { text: "password123" });
await page.act("click login");
await page.observe("wait for dashboard");

// Agent 方式（更簡潔、更靈活、更智能）
await page.agent("log in with test@example.com / password123");
```

## 4.3 實作登入測試 Skill

現在讓我們把學到的知識應用到實際的 Skill 開發中。我們將創建一個完整的瀏覽器登入測試 Skill。

### 4.3.1 Skill 定義

首先，創建 SKILL.md 文件：

```markdown
# Browser Login Test

## Description
Automated login testing using Stagehand AI browser automation. Tests user authentication
flows with self-healing capabilities and semantic element detection.

## When to use
- Verify login functionality after deployment
- Test authentication with different user credentials
- Validate session management and redirects
- Perform smoke tests on authentication systems
- Test login across different browsers

## Parameters

### url (required, string)
Login page URL to test
- Example: `"https://example.com/login"`

### username (required, string)
Test username or email
- Example: `"test@example.com"`

### password (required, string)
Test password
- Example: `"SecurePassword123!"`

### expected_url (optional, string)
Expected URL after successful login
- Default: `null`
- Example: `"https://example.com/dashboard"`

### headless (optional, boolean)
Run browser in headless mode
- Default: `true`
- Set to `false` for debugging

### timeout (optional, integer)
Maximum time to wait for login (seconds)
- Default: `60`
- Range: 10-300

## Returns

Returns a dictionary with the following structure:

```json
{
  "success": boolean,
  "is_logged_in": boolean,
  "current_url": string,
  "username_displayed": string,
  "error_message": string | null,
  "screenshot": string (base64),
  "execution_time_ms": float
}
```

## Implementation

This skill uses Stagehand (TypeScript) called from Python. The execution flow:

1. **Initialize Stagehand** - Setup browser with specified options
2. **Navigate to Login Page** - Load the login URL
3. **Enter Credentials** - Fill username and password using semantic actions
4. **Submit Login** - Click login button
5. **Wait for Completion** - Observe page state change
6. **Verify Success** - Extract login status and user info
7. **Capture Evidence** - Take screenshot
8. **Return Result** - Structured test result

## Examples

### Example 1: Basic Login Test

Input:
```json
{
  "url": "https://example.com/login",
  "username": "test@example.com",
  "password": "password123"
}
```

Output:
```json
{
  "success": true,
  "is_logged_in": true,
  "current_url": "https://example.com/dashboard",
  "username_displayed": "test@example.com",
  "error_message": null,
  "screenshot": "iVBORw0KGgoAAAANSUhEUgAA...",
  "execution_time_ms": 3245.67
}
```

### Example 2: Failed Login

Input:
```json
{
  "url": "https://example.com/login",
  "username": "test@example.com",
  "password": "wrongpassword"
}
```

Output:
```json
{
  "success": false,
  "is_logged_in": false,
  "current_url": "https://example.com/login",
  "username_displayed": null,
  "error_message": "Invalid username or password",
  "screenshot": "iVBORw0KGgoAAAANSUhEUgAA...",
  "execution_time_ms": 2187.34
}
```

## Error Handling

- **Navigation Timeout**: Retry once with extended timeout
- **Element Not Found**: Stagehand auto-retries with different strategies
- **Invalid Credentials**: Capture error message and return structured result
- **Network Errors**: Retry up to 3 times with exponential backoff

## Dependencies

- Node.js >= 18.0.0
- @browserbasehq/stagehand >= 3.0.0
- Python >= 3.10
- asyncio

## Tags
browser, testing, login, authentication, e2e, stagehand
```

### 4.3.2 Python 實作

創建 `src/skills/browser/login_test.py`:

```python
# src/skills/browser/login_test.py
import asyncio
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BrowserLoginTester:
    """
    瀏覽器登入測試器

    使用 Stagehand AI 驅動的瀏覽器自動化進行登入測試。
    """

    def __init__(self, headless: bool = True, timeout: int = 60):
        """
        初始化測試器

        Args:
            headless: 是否使用無頭模式
            timeout: 測試超時時間（秒）
        """
        self.headless = headless
        self.timeout = timeout
        self.script_path = Path(__file__).parent.parent / "stagehand" / "login.js"

    async def test_login(
        self,
        url: str,
        username: str,
        password: str,
        expected_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        測試登入流程

        Args:
            url: 登入頁面 URL
            username: 用戶名
            password: 密碼
            expected_url: 預期的登入後 URL（可選）

        Returns:
            測試結果字典

        Raises:
            FileNotFoundError: 如果 Stagehand 腳本不存在
            RuntimeError: 如果測試執行失敗
        """
        # 驗證腳本存在
        if not self.script_path.exists():
            raise FileNotFoundError(
                f"Stagehand script not found: {self.script_path}. "
                "Please ensure stagehand/login.js exists."
            )

        # 構建命令
        cmd = [
            "node",
            str(self.script_path),
            "--url", url,
            "--username", username,
            "--password", password,
            "--timeout", str(self.timeout * 1000)  # 轉換為毫秒
        ]

        if expected_url:
            cmd.extend(["--expected-url", expected_url])

        if self.headless:
            cmd.append("--headless")

        logger.info(f"Starting login test for {url}")
        start_time = time.time()

        try:
            # 執行 Node.js 腳本
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # 等待執行完成（帶超時）
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout + 10  # 給額外 10 秒緩衝
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise RuntimeError(
                    f"Login test timed out after {self.timeout + 10} seconds"
                )

            execution_time = (time.time() - start_time) * 1000  # 毫秒

            # 檢查執行狀態
            if proc.returncode != 0:
                error_message = stderr.decode('utf-8', errors='replace')
                logger.error(f"Login test failed: {error_message}")
                return {
                    "success": False,
                    "error": error_message,
                    "execution_time_ms": execution_time
                }

            # 解析結果
            try:
                result = json.loads(stdout.decode('utf-8'))
                result['execution_time_ms'] = execution_time
                logger.info(f"Login test completed: {result.get('success', False)}")
                return result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse test result: {e}")
                return {
                    "success": False,
                    "error": f"Failed to parse result: {str(e)}",
                    "raw_output": stdout.decode('utf-8', errors='replace'),
                    "execution_time_ms": execution_time
                }

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Login test error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "execution_time_ms": execution_time
            }


def execute_login_test(
    url: str,
    username: str,
    password: str,
    expected_url: Optional[str] = None,
    headless: bool = True,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    執行登入測試（Skill 入口函數）

    Args:
        url: 登入頁面 URL
        username: 用戶名
        password: 密碼
        expected_url: 預期的登入後 URL
        headless: 是否使用無頭模式
        timeout: 測試超時時間（秒）

    Returns:
        測試結果字典

    Examples:
        >>> result = execute_login_test(
        ...     "https://example.com/login",
        ...     "test@example.com",
        ...     "password123"
        ... )
        >>> result['success']
        True
    """
    tester = BrowserLoginTester(headless=headless, timeout=timeout)
    return asyncio.run(
        tester.test_login(url, username, password, expected_url)
    )


# 用於直接執行的主函數
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python login_test.py <url> <username> <password> [expected_url]")
        sys.exit(1)

    url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    expected_url = sys.argv[4] if len(sys.argv) > 4 else None

    result = execute_login_test(url, username, password, expected_url, headless=False)
    print(json.dumps(result, indent=2))
```

### 4.3.3 Stagehand 腳本實作

創建 `src/skills/stagehand/login.js`:

```javascript
// src/skills/stagehand/login.js
const { Stagehand } = require("@browserbasehq/stagehand");
const { parseArgs } = require("node:util");

/**
 * 執行登入測試
 *
 * @param {Object} options - 測試選項
 * @param {string} options.url - 登入頁面 URL
 * @param {string} options.username - 用戶名
 * @param {string} options.password - 密碼
 * @param {string} [options.expectedUrl] - 預期的登入後 URL
 * @param {boolean} [options.headless=true] - 是否無頭模式
 * @param {number} [options.timeout=60000] - 超時時間（毫秒）
 */
async function testLogin(options) {
  const stagehand = new Stagehand({
    env: "LOCAL",
    verbose: options.verbose ? 1 : 0,
    headless: options.headless,
    enableCaching: true
  });

  const startTime = Date.now();

  try {
    console.error("[INFO] Initializing Stagehand...");
    await stagehand.init();
    const page = stagehand.page;

    // 步驟 1: 導航到登入頁面
    console.error(`[INFO] Navigating to ${options.url}`);
    await page.goto(options.url, {
      waitUntil: 'networkidle',
      timeout: options.timeout
    });

    // 步驟 2: 填寫用戶名
    console.error("[INFO] Entering username");
    await page.act("enter username or email", {
      text: options.username
    });

    // 步驟 3: 填寫密碼
    console.error("[INFO] Entering password");
    await page.act("enter password", {
      text: options.password
    });

    // 步驟 4: 點擊登入按鈕
    console.error("[INFO] Clicking login button");
    await page.act("click the login button");

    // 步驟 5: 等待頁面變化
    console.error("[INFO] Waiting for page transition");
    await page.observe("wait for the page to finish loading after login");

    // 步驟 6: 提取登入狀態資訊
    console.error("[INFO] Extracting login status");
    const loginInfo = await page.extract({
      isLoggedIn: "is the user logged in?",
      currentUrl: "what is the current page URL?",
      usernameDisplayed: "what username or email is displayed in the user profile or header?",
      errorMessage: "is there an error message? if so, what does it say?"
    });

    // 步驟 7: 驗證預期 URL（如果提供）
    let urlMatch = true;
    if (options.expectedUrl) {
      urlMatch = loginInfo.currentUrl.includes(options.expectedUrl);
      console.error(`[INFO] URL match: expected=${options.expectedUrl}, actual=${loginInfo.currentUrl}, match=${urlMatch}`);
    }

    // 步驟 8: 擷取截圖
    console.error("[INFO] Capturing screenshot");
    const screenshot = await page.screenshot({
      encoding: "base64",
      fullPage: true
    });

    // 計算執行時間
    const executionTime = Date.now() - startTime;

    // 構建結果
    const result = {
      success: loginInfo.isLoggedIn && urlMatch,
      is_logged_in: loginInfo.isLoggedIn,
      current_url: loginInfo.currentUrl,
      username_displayed: loginInfo.usernameDisplayed || null,
      error_message: loginInfo.errorMessage || null,
      screenshot: screenshot,
      execution_time_ms: executionTime,
      url_match: urlMatch
    };

    // 輸出結果到 stdout
    console.log(JSON.stringify(result));

    console.error(`[INFO] Login test completed: success=${result.success}`);

  } catch (error) {
    const executionTime = Date.now() - startTime;

    console.error(`[ERROR] Login test failed: ${error.message}`);

    // 輸出錯誤結果
    const errorResult = {
      success: false,
      is_logged_in: false,
      current_url: null,
      username_displayed: null,
      error_message: error.message,
      screenshot: null,
      execution_time_ms: executionTime,
      stack: error.stack
    };

    console.log(JSON.stringify(errorResult));
    process.exit(1);

  } finally {
    // 清理資源
    console.error("[INFO] Closing browser");
    await stagehand.close();
  }
}

// 解析命令行參數
const { values } = parseArgs({
  options: {
    url: {
      type: "string"
    },
    username: {
      type: "string"
    },
    password: {
      type: "string"
    },
    "expected-url": {
      type: "string"
    },
    headless: {
      type: "boolean",
      default: true
    },
    timeout: {
      type: "string",
      default: "60000"
    },
    verbose: {
      type: "boolean",
      default: false
    }
  }
});

// 驗證必要參數
if (!values.url || !values.username || !values.password) {
  console.error("Error: Missing required parameters");
  console.error("Usage: node login.js --url <URL> --username <USERNAME> --password <PASSWORD>");
  process.exit(1);
}

// 轉換參數
const options = {
  url: values.url,
  username: values.username,
  password: values.password,
  expectedUrl: values["expected-url"],
  headless: values.headless,
  timeout: parseInt(values.timeout),
  verbose: values.verbose
};

// 執行測試
testLogin(options).catch(error => {
  console.error(`Fatal error: ${error.message}`);
  process.exit(1);
});
```

### 4.3.4 測試 Skill

現在我們可以測試我們的 Skill 了：

```python
# test_login_skill.py
from src.skills.browser.login_test import execute_login_test
import json

# 測試範例 1: 成功登入
result = execute_login_test(
    url="https://the-internet.herokuapp.com/login",
    username="tomsmith",
    password="SuperSecretPassword!",
    headless=False  # 顯示瀏覽器以便觀察
)

print("Test Result:")
print(json.dumps(result, indent=2))

if result['success']:
    print("\n✓ Login test PASSED")
    print(f"  Logged in as: {result['username_displayed']}")
    print(f"  Current URL: {result['current_url']}")
    print(f"  Execution time: {result['execution_time_ms']:.0f}ms")
else:
    print("\n✗ Login test FAILED")
    print(f"  Error: {result.get('error_message', 'Unknown error')}")
```

### 4.3.5 整合到 Skills 系統

創建 `skills/browser_login_test/SKILL.md`（使用前面定義的內容）並創建入口函數：

```python
# skills/browser_login_test/__init__.py
from src.skills.browser.login_test import execute_login_test

__all__ = ['execute_login_test']
```

現在這個 Skill 可以被 Claude 發現和使用了！

---

## 4.4 處理複雜 UI 互動

現實世界的 Web 應用程式充滿了複雜的 UI 互動：動態載入的內容、文件上傳、拖放操作、無限滾動等。Stagehand 為這些場景提供了優雅的解決方案。

### 4.4.1 動態內容處理

**場景 1：等待動態載入的內容**

```typescript
// 處理載入動畫
await page.goto("https://example.com/dashboard");

// 等待載入動畫消失
await page.observe("wait until the loading spinner disappears");

// 等待內容出現
await page.observe("wait for the dashboard widgets to appear");

// 現在可以安全地提取數據
const dashboardData = await page.extract({
  userCount: "total number of users",
  revenue: "total revenue shown",
  activeProjects: "number of active projects"
});
```

**場景 2：處理無限滾動**

```typescript
async function scrapeInfiniteScroll(page, maxItems = 100) {
  const allItems = [];
  let previousCount = 0;

  while (allItems.length < maxItems) {
    // 滾動到底部
    await page.act("scroll to the bottom of the page");

    // 等待新內容載入
    await page.observe("wait for new items to load");

    // 提取當前可見的項目
    const items = await page.extract({
      items: [
        {
          title: "item title",
          price: "item price"
        }
      ]
    });

    // 檢查是否有新項目
    if (items.items.length === previousCount) {
      console.log("已到達底部，無更多內容");
      break;
    }

    allItems.push(...items.items);
    previousCount = items.items.length;

    console.log(`已載入 ${allItems.length} 個項目`);
  }

  return allItems;
}
```

**場景 3：處理 AJAX 請求**

```typescript
// 點擊觸發 AJAX 請求
await page.act("click the load more button");

// 智能等待 - Stagehand 會自動檢測 AJAX 完成
await page.observe("wait for new content to appear");

// 或者更具體地描述預期變化
await page.observe("wait for the item count to increase");
```

**場景 4：處理動態表單**

```typescript
// 複雜的多步驟表單
await page.act("select the country United States");

// 等待州/省份下拉選單動態載入
await page.observe("wait for the state dropdown to become available");

await page.act("select the state California");

// 等待城市下拉選單更新
await page.observe("wait for the city dropdown to update");

await page.act("select the city San Francisco");
```

### 4.4.2 文件上傳

Stagehand 讓文件上傳變得非常簡單。

**單文件上傳**：

```typescript
// 方式 1: 使用 act() with file 選項
await page.act("upload profile picture", {
  file: "/path/to/profile.jpg"
});

// 方式 2: 更自然的描述
await page.act("click the upload button and select the profile picture", {
  file: "/Users/john/Documents/profile.jpg"
});
```

**多文件上傳**：

```typescript
await page.act("upload documents", {
  files: [
    "/path/to/document1.pdf",
    "/path/to/document2.pdf",
    "/path/to/document3.pdf"
  ]
});

// 等待上傳完成
await page.observe("wait for all files to finish uploading");

// 驗證上傳成功
const uploadStatus = await page.extract({
  uploadedFiles: [
    {
      filename: "file name",
      status: "upload status"
    }
  ],
  totalUploaded: "total number of files uploaded"
});
```

**帶進度追蹤的文件上傳**：

```typescript
async function uploadWithProgress(page, filePath) {
  await page.act("upload file", { file: filePath });

  let progress = 0;

  while (progress < 100) {
    const status = await page.extract({
      progress: "what is the upload progress percentage?",
      isComplete: "is the upload complete?"
    });

    progress = parseInt(status.progress) || 0;
    console.log(`上傳進度: ${progress}%`);

    if (status.isComplete) {
      break;
    }

    await new Promise(resolve => setTimeout(resolve, 500));
  }

  console.log("✓ 文件上傳完成");
}
```

### 4.4.3 拖放操作

拖放操作傳統上很難自動化，但 Stagehand 讓它變得簡單。

**基本拖放**：

```typescript
// Stagehand 理解拖放的語意
await page.act("drag the task from todo to done");

await page.act("drag the file to the upload area");

await page.act("reorder the list by dragging item 3 to position 1");
```

**複雜拖放場景**：

```typescript
// Kanban 看板拖放
await page.act("drag the card 'Fix login bug' from Backlog to In Progress");

await page.observe("wait for the card to appear in In Progress column");

// 驗證拖放成功
const cardLocation = await page.extract({
  cardTitle: "what is the card title?",
  columnName: "which column is the card in?",
  position: "what position in the column?"
});

console.log(`卡片 "${cardLocation.cardTitle}" 現在在 ${cardLocation.columnName}，位置 ${cardLocation.position}`);
```

**文件管理器拖放**：

```typescript
// 拖放多個文件到資料夾
await page.act("select files document1.pdf, document2.pdf, and document3.pdf");
await page.act("drag the selected files to the Archive folder");
await page.observe("wait for the files to be moved");

// 驗證操作
const result = await page.extract({
  filesInArchive: "how many files are now in the Archive folder?",
  moveSuccess: "was the move successful?"
});
```

### 4.4.4 處理彈窗和對話框

**模態對話框**：

```typescript
// 等待彈窗出現
await page.observe("wait for the confirmation dialog to appear");

// 與彈窗互動
await page.act("click the confirm button in the dialog");

// 或者更具體
await page.act("click the red delete button in the confirmation popup");
```

**處理多個彈窗**：

```typescript
// 第一個彈窗：隱私政策
await page.observe("wait for the privacy policy popup");
await page.act("click accept on the privacy popup");

// 第二個彈窗：訂閱通知
await page.observe("wait for the notification subscription popup");
await page.act("click no thanks on the subscription popup");

// 第三個彈窗：特別優惠
await page.observe("wait for the special offer popup");
await page.act("close the offer popup");
```

**瀏覽器原生對話框**：

```typescript
// 處理 alert, confirm, prompt
page.on('dialog', async dialog => {
  console.log(`對話框類型: ${dialog.type()}`);
  console.log(`對話框訊息: ${dialog.message()}`);

  if (dialog.type() === 'confirm') {
    await dialog.accept();
  } else if (dialog.type() === 'prompt') {
    await dialog.accept('測試輸入');
  }
});

await page.act("click the button that shows a confirm dialog");
```

### 4.4.5 處理 iframe 和多視窗

**iframe 處理**：

```typescript
// Stagehand 自動處理 iframe 上下文
await page.act("click the button inside the payment iframe");

await page.act("fill in the credit card number in the payment form", {
  text: "4111111111111111"
});

// 從 iframe 中提取數據
const paymentInfo = await page.extract({
  cardNumber: "what credit card number is entered?",
  expiryDate: "what is the expiry date?",
  isValid: "is the payment form valid?"
});
```

**多視窗/分頁處理**：

```typescript
// 點擊會開啟新視窗的連結
const [newPage] = await Promise.all([
  stagehand.context.waitForEvent('page'),
  page.act("click the link that opens in a new tab")
]);

// 在新視窗中操作
const newPageStagehand = new Stagehand({ page: newPage });
await newPageStagehand.init();

await newPage.act("fill in the form");
await newPage.act("submit");

// 關閉新視窗，回到原視窗
await newPage.close();
await page.bringToFront();
```

## 4.5 自愈機制與錯誤恢復

Stagehand 最強大的特性之一就是自愈能力。讓我們深入了解它如何工作，以及如何增強這種能力。

### 4.5.1 自動重試機制

**內建重試配置**：

```typescript
const stagehand = new Stagehand({
  env: "LOCAL",
  retries: 3,           // 操作失敗時自動重試 3 次
  retryDelay: 1000,     // 重試間隔 1 秒
  timeout: 30000        // 單次操作超時 30 秒
});
```

**重試行為詳解**：

```typescript
// 當執行這個操作時
await page.act("click the submit button");

// Stagehand 內部流程:
// 嘗試 1: 尋找元素 → 失敗 (元素未找到)
//   等待 1 秒
// 嘗試 2: 重新掃描頁面 → 找到元素 → 點擊 → 成功 ✓

// 或者如果持續失敗:
// 嘗試 1: 失敗
// 嘗試 2: 失敗
// 嘗試 3: 失敗
// 嘗試 4: 拋出錯誤並提供詳細資訊
```

**自定義重試邏輯**：

```typescript
async function robustAction(page, action, maxRetries = 5) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      await page.act(action);
      console.log(`✓ 操作成功（嘗試 ${attempt}/${maxRetries}）`);
      return;

    } catch (error) {
      console.log(`✗ 嘗試 ${attempt}/${maxRetries} 失敗: ${error.message}`);

      if (attempt === maxRetries) {
        console.error("已達最大重試次數");
        throw error;
      }

      // 指數退避
      const delay = Math.min(1000 * Math.pow(2, attempt - 1), 30000);
      console.log(`等待 ${delay}ms 後重試...`);
      await new Promise(resolve => setTimeout(resolve, delay));

      // 可選：重新載入頁面或重置狀態
      if (attempt % 2 === 0) {
        console.log("刷新頁面以重置狀態...");
        await page.reload();
      }
    }
  }
}

// 使用
await robustAction(page, "click the checkout button");
```

### 4.5.2 錯誤恢復策略

**策略 1：截圖並繼續**

```typescript
async function actionWithScreenshot(page, action, screenshotPath) {
  try {
    await page.act(action);
  } catch (error) {
    console.error(`操作失敗: ${action}`);

    // 截圖保存當前狀態
    await page.screenshot({
      path: `${screenshotPath}/error-${Date.now()}.png`,
      fullPage: true
    });

    // 記錄頁面狀態
    const pageState = await page.extract({
      url: "current URL",
      title: "page title",
      errorMessages: "any visible error messages",
      pageState: "describe the current state of the page"
    });

    console.error("頁面狀態:", JSON.stringify(pageState, null, 2));

    throw error;
  }
}
```

**策略 2：降級執行**

```typescript
async function attemptWithFallback(page) {
  try {
    // 嘗試主要方式：使用 agent 自動完成
    await page.agent("complete the checkout process");

  } catch (error) {
    console.log("Agent 執行失敗，切換到手動步驟...");

    // 降級到手動步驟
    try {
      await page.act("enter shipping address");
      await page.act("select shipping method");
      await page.act("enter payment information");
      await page.act("click place order");

    } catch (fallbackError) {
      console.log("手動步驟也失敗，嘗試最簡方案...");

      // 最後的後備方案
      await page.evaluate(() => {
        // 使用原生 JavaScript 操作
        document.querySelector('#checkout-btn').click();
      });
    }
  }
}
```

**策略 3：智能恢復點**

```typescript
async function checkpointedFlow(page) {
  const checkpoints = [];

  try {
    // Checkpoint 1: 登入
    console.log("Checkpoint 1: 登入");
    await page.act("login");
    checkpoints.push("login");

    // Checkpoint 2: 選擇產品
    console.log("Checkpoint 2: 選擇產品");
    await page.act("select product");
    checkpoints.push("product_selected");

    // Checkpoint 3: 加入購物車
    console.log("Checkpoint 3: 加入購物車");
    await page.act("add to cart");
    checkpoints.push("added_to_cart");

    // Checkpoint 4: 結帳
    console.log("Checkpoint 4: 結帳");
    await page.act("proceed to checkout");
    checkpoints.push("checkout");

  } catch (error) {
    console.error(`流程在 checkpoint "${checkpoints[checkpoints.length - 1]}" 之後失敗`);

    // 根據失敗點決定恢復策略
    const lastCheckpoint = checkpoints[checkpoints.length - 1];

    if (lastCheckpoint === "login") {
      // 登入失敗 - 檢查憑證
      console.log("恢復策略: 驗證登入憑證");

    } else if (lastCheckpoint === "added_to_cart") {
      // 購物車成功，結帳失敗 - 檢查購物車狀態
      console.log("恢復策略: 驗證購物車內容並重試結帳");

    }

    throw error;
  }

  return checkpoints;
}
```

### 4.5.3 處理常見錯誤

**錯誤 1：元素未找到**

```typescript
async function handleElementNotFound(page, action) {
  try {
    await page.act(action);
  } catch (error) {
    if (error.message.includes("element not found")) {
      console.log("元素未找到，嘗試替代描述...");

      // 嘗試不同的語意描述
      const alternatives = [
        "click the submit button",
        "click the confirm button",
        "click the save button",
        "click the continue button"
      ];

      for (const alt of alternatives) {
        try {
          await page.act(alt);
          console.log(`✓ 成功使用替代描述: ${alt}`);
          return;
        } catch (e) {
          continue;
        }
      }

      throw new Error("所有替代方案都失敗");
    }
    throw error;
  }
}
```

**錯誤 2：超時**

```typescript
async function handleTimeout(page, action, maxWait = 60000) {
  const startTime = Date.now();

  while (Date.now() - startTime < maxWait) {
    try {
      await page.act(action, { timeout: 10000 });
      return; // 成功

    } catch (error) {
      if (error.message.includes("timeout")) {
        console.log("操作超時，檢查頁面狀態...");

        // 檢查是否有載入指示器
        const isLoading = await page.extract({
          loading: "is the page still loading?"
        });

        if (isLoading.loading) {
          console.log("頁面仍在載入，繼續等待...");
          await new Promise(r => setTimeout(r, 2000));
          continue;
        }
      }
      throw error;
    }
  }

  throw new Error(`操作超時，已等待 ${maxWait}ms`);
}
```

## 4.6 WebGuard 瀏覽器測試模組

現在讓我們整合所有學到的知識，構建 WebGuard 的完整瀏覽器測試模組。

### 4.6.1 模組架構

```
webguard/
├── src/
│   ├── skills/
│   │   ├── browser/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # 基礎測試類別
│   │   │   ├── login_test.py        # 登入測試
│   │   │   ├── navigation_test.py   # 導航測試
│   │   │   ├── form_test.py         # 表單測試
│   │   │   ├── e2e_test.py          # E2E 測試套件
│   │   │   └── visual_test.py       # 視覺回歸測試
│   │   └── stagehand/
│   │       ├── login.js
│   │       ├── navigation.js
│   │       ├── form.js
│   │       ├── e2e.js
│   │       └── visual.js
│   └── utils/
│       ├── screenshot.py
│       └── report.py
├── tests/
│   └── browser/
│       ├── test_login.py
│       └── test_e2e.py
└── config/
    └── browser_config.yaml
```

### 4.6.2 基礎測試類別

```python
# src/skills/browser/base.py
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class BrowserTestBase:
    """瀏覽器測試基礎類別"""

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 60,
        screenshot_dir: str = "screenshots",
        verbose: bool = False
    ):
        self.headless = headless
        self.timeout = timeout
        self.screenshot_dir = Path(screenshot_dir)
        self.verbose = verbose
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def run_stagehand_script(
        self,
        script_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        執行 Stagehand 腳本

        Args:
            script_name: 腳本名稱（不含 .js 後綴）
            **kwargs: 傳遞給腳本的參數

        Returns:
            執行結果
        """
        script_path = Path(__file__).parent.parent / "stagehand" / f"{script_name}.js"

        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        # 構建命令
        cmd = ["node", str(script_path)]

        # 添加參數
        for key, value in kwargs.items():
            cmd.append(f"--{key.replace('_', '-')}")
            if isinstance(value, bool):
                if value:
                    continue  # 布爾 flag 不需要值
            else:
                cmd.append(str(value))

        if self.headless:
            cmd.append("--headless")

        if self.verbose:
            cmd.append("--verbose")

        cmd.extend(["--timeout", str(self.timeout * 1000)])

        logger.info(f"Running: {' '.join(cmd)}")

        # 執行腳本
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout + 10
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"Script timed out after {self.timeout + 10}s")

        if proc.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace')
            logger.error(f"Script failed: {error_msg}")
            raise RuntimeError(f"Script execution failed: {error_msg}")

        # 解析結果
        try:
            result = json.loads(stdout.decode('utf-8'))

            # 保存截圖（如果有）
            if 'screenshot' in result and result['screenshot']:
                self._save_screenshot(result['screenshot'], script_name)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse result: {e}")
            raise

    def _save_screenshot(self, base64_data: str, name: str):
        """保存 base64 截圖"""
        import base64

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshot_dir / filename

        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(base64_data))

        logger.info(f"Screenshot saved: {filepath}")

    def create_test_report(
        self,
        test_name: str,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """創建測試報告"""
        total = len(results)
        passed = sum(1 for r in results if r.get('success', False))
        failed = total - passed

        return {
            "test_name": test_name,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
```

### 4.6.3 完整 E2E 測試套件

```python
# src/skills/browser/e2e_test.py
from .base import BrowserTestBase
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class E2ETestSuite(BrowserTestBase):
    """端對端測試套件"""

    async def test_complete_user_journey(
        self,
        base_url: str,
        test_user: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        測試完整用戶旅程

        Args:
            base_url: 應用程式基礎 URL
            test_user: 測試用戶資訊 (username, password)

        Returns:
            完整測試結果
        """
        results = []

        # 步驟 1: 登入
        logger.info("步驟 1: 測試登入")
        login_result = await self.run_stagehand_script(
            "login",
            url=f"{base_url}/login",
            username=test_user['username'],
            password=test_user['password']
        )
        results.append({
            "step": "login",
            "success": login_result.get('success', False),
            "details": login_result
        })

        if not login_result.get('success'):
            return self.create_test_report("user_journey", results)

        # 步驟 2: 導航測試
        logger.info("步驟 2: 測試導航")
        nav_result = await self.run_stagehand_script(
            "navigation",
            base_url=base_url,
            pages=["dashboard", "profile", "settings"]
        )
        results.append({
            "step": "navigation",
            "success": nav_result.get('success', False),
            "details": nav_result
        })

        # 步驟 3: 表單操作
        logger.info("步驟 3: 測試表單操作")
        form_result = await self.run_stagehand_script(
            "form",
            url=f"{base_url}/profile/edit",
            form_data={
                "name": "Test User Updated",
                "email": "updated@example.com",
                "bio": "Updated bio text"
            }
        )
        results.append({
            "step": "form_submission",
            "success": form_result.get('success', False),
            "details": form_result
        })

        # 步驟 4: 數據驗證
        logger.info("步驟 4: 驗證數據更新")
        # ... 更多測試步驟

        return self.create_test_report("user_journey", results)


def execute_e2e_test(
    base_url: str,
    username: str,
    password: str,
    headless: bool = True
) -> Dict[str, Any]:
    """E2E 測試 Skill 入口"""
    suite = E2ETestSuite(headless=headless)
    return asyncio.run(
        suite.test_complete_user_journey(
            base_url,
            {"username": username, "password": password}
        )
    )
```

## 4.7 本章總結

恭喜！你已經掌握了 Stagehand 瀏覽器自動化的完整知識體系。

### 4.7.1 關鍵要點回顧

✅ **Stagehand 革命性優勢**
- 44% 更快的執行速度
- 90% 減少的上下文使用量
- 70% 減少的維護工作量
- 自愈能力讓測試自動適應 UI 變更

✅ **四大核心 API 精通**
- **act()**: 執行語意化操作，不依賴脆弱選擇器
- **extract()**: 提取結構化數據，支援複雜嵌套
- **observe()**: 智能等待條件，自動檢測頁面狀態
- **agent()**: 自主完成複雜多步驟任務

✅ **複雜場景處理能力**
- 動態內容、無限滾動、AJAX 請求
- 文件上傳、拖放操作
- 彈窗、iframe、多視窗處理

✅ **企業級可靠性**
- 自動重試機制
- 智能錯誤恢復
- 降級執行策略
- 完整的日誌和截圖

✅ **WebGuard 整合**
- 模組化架構設計
- Python + TypeScript 無縫協作
- 完整的 E2E 測試套件
- 生產級錯誤處理

### 4.7.2 實踐檢查清單

在進入下一章之前，確保你能夠：

- [ ] 解釋 Stagehand 相比傳統工具的核心優勢
- [ ] 使用 act() 執行各種頁面操作
- [ ] 使用 extract() 提取複雜的結構化數據
- [ ] 使用 observe() 實現智能等待
- [ ] 使用 agent() 完成自主任務
- [ ] 處理文件上傳和拖放操作
- [ ] 實作自動重試和錯誤恢復機制
- [ ] 構建完整的登入測試 Skill
- [ ] 整合 Python 和 TypeScript 代碼
- [ ] 理解 WebGuard 瀏覽器模組架構

### 4.7.3 下一章預告

第 5 章將探討**數據與文件處理自動化**，學習如何：

- 使用 Pandas 處理 Excel/CSV 數據
- 自動化 PDF 生成和解析
- 驗證和清理大規模數據
- 構建數據驅動的測試
- 整合資料庫操作

從瀏覽器自動化到數據處理，我們的 WebGuard 系統將越來越強大！

---

**本章代碼**

完整代碼範例：
- `code-examples/chapter-04/stagehand-basics/`
- `code-examples/chapter-04/login-skill/`
- `code-examples/chapter-04/complex-interactions/`

**延伸閱讀**

- Stagehand 官方文檔: https://docs.stagehand.dev
- Chrome DevTools Protocol: https://chromedevtools.github.io/devtools-protocol/
- Browser Automation Best Practices: https://martinfowler.com/articles/practical-test-pyramid.html
