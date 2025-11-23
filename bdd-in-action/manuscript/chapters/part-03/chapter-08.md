# Chapter 08：從可執行規格到自動化驗收測試

> 「理論上，理論和實踐沒有區別。但實踐上，是有的。」
> —— Yogi Berra

---

## 本章目標

完成本章後，你將能夠：

- 理解自動化測試金字塔與驗收測試的定位
- 設定 Java 和 TypeScript 的 Cucumber 測試環境
- 撰寫 Step Definitions 將 Gherkin 場景自動化
- 使用 Hooks 進行測試設定與清理
- 建立可重用的測試基礎設施
- 使用 Docker 建立隔離的測試環境
- 將自動化測試整合到 CI/CD 流程

---

## 讓規格動起來

在前幾章中，我們花了大量時間討論如何探索需求、如何用範例說明功能、如何撰寫表達力強的 Gherkin 場景。這些都很重要——但它們都還只是**文件**。

本章開始，我們要讓這些規格「**動起來**」。

讓我們回到 ReadMore 書店。開發團隊已經為「會員折扣」功能撰寫了完整的 Gherkin 規格。現在，是時候把這些規格變成可以自動執行的測試了。

---

## 8.1 自動化場景簡介

### 8.1.1 測試金字塔

在深入自動化之前，讓我們先理解驗收測試在整體測試策略中的位置。

```mermaid
graph TB
    subgraph 測試金字塔
        E2E[🔺 端到端測試<br/>E2E Tests<br/>────────<br/>數量：少<br/>速度：慢<br/>成本：高]
        Integration[🔷 整合測試<br/>Integration Tests<br/>────────<br/>數量：中等<br/>速度：中等<br/>成本：中等]
        Unit[🟩 單元測試<br/>Unit Tests<br/>────────<br/>數量：多<br/>速度：快<br/>成本：低]
    end

    E2E --> Integration --> Unit

    style E2E fill:#ffcdd2
    style Integration fill:#fff9c4
    style Unit fill:#c8e6c9
```

**圖 8.1：測試金字塔**

**各層測試的特點**：

| 層級 | 測試對象 | 執行速度 | 維護成本 | 數量 |
|------|---------|---------|---------|------|
| **端到端** | 完整系統流程 | 慢（分鐘級）| 高 | 少 |
| **整合** | 元件間互動 | 中等（秒級）| 中等 | 中等 |
| **單元** | 單一函數/類別 | 快（毫秒級）| 低 | 多 |

**表 8.1：測試金字塔各層特點**

### 8.1.2 驗收測試的定位

BDD 驗收測試通常位於**整合測試層**或**端到端測試層**，取決於你的自動化策略：

```mermaid
graph LR
    subgraph BDD驗收測試的兩種定位
        A[UI 驅動的驗收測試] --> E2E[端到端層]
        B[API 驅動的驗收測試] --> INT[整合測試層]
    end

    style A fill:#ffcdd2
    style B fill:#fff9c4
```

**圖 8.2：驗收測試的定位選擇**

**選擇指南**：

| 定位 | 適用場景 | 優點 | 缺點 |
|------|---------|------|------|
| **UI 驅動** | 用戶界面是核心價值 | 測試真實用戶體驗 | 速度慢、維護成本高 |
| **API 驅動** | 業務邏輯是核心價值 | 速度快、穩定性高 | 不測試 UI 層 |
| **混合** | 大多數專案 | 兼顧兩者優點 | 需要更多設計 |

**表 8.2：驗收測試定位選擇指南**

> 💡 **最佳實踐**：從 API 層開始自動化，只有在必要時才加入 UI 測試。這樣可以保持測試套件的速度和穩定性。

### 8.1.3 自動化的價值與成本

**自動化帶來的價值**：

1. **快速反饋**：每次程式碼變更都能立即驗證
2. **迴歸保護**：防止修改引入新問題
3. **動態文件**：測試即規格，永遠與程式碼同步
4. **信心提升**：團隊可以更大膽地重構

**自動化的成本**：

1. **初始投資**：需要時間建立測試基礎設施
2. **維護負擔**：測試程式碼也需要維護
3. **執行時間**：測試套件越大，執行越慢
4. **脆弱性風險**：設計不當的測試容易失敗

**投資回報分析**：

```
初期：投入 > 回報（學習曲線、基礎設施建設）
  ↓
中期：投入 ≈ 回報（開始看到效益）
  ↓
長期：投入 < 回報（自動化紅利顯現）
```

---

## 8.2 設定你的專案環境

### 8.2.1 Java 環境設定（Maven）

**步驟 1：創建 Maven 專案**

```bash
mvn archetype:generate \
  -DgroupId=com.readmore \
  -DartifactId=bdd-tests \
  -DarchetypeArtifactId=maven-archetype-quickstart \
  -DinteractiveMode=false

cd bdd-tests
```

**步驟 2：配置 pom.xml**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.readmore</groupId>
    <artifactId>bdd-tests</artifactId>
    <version>1.0-SNAPSHOT</version>
    <packaging>jar</packaging>

    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <cucumber.version>7.14.0</cucumber.version>  <!-- ‹1› -->
        <junit.version>5.10.0</junit.version>
        <assertj.version>3.24.2</assertj.version>
    </properties>

    <dependencies>
        <!-- Cucumber Core -->
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-java</artifactId>      <!-- ‹2› -->
            <version>${cucumber.version}</version>
            <scope>test</scope>
        </dependency>

        <!-- Cucumber + JUnit 5 整合 -->
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-junit-platform-engine</artifactId>  <!-- ‹3› -->
            <version>${cucumber.version}</version>
            <scope>test</scope>
        </dependency>

        <!-- JUnit 5 Platform -->
        <dependency>
            <groupId>org.junit.platform</groupId>
            <artifactId>junit-platform-suite</artifactId>
            <version>1.10.0</version>
            <scope>test</scope>
        </dependency>

        <!-- AssertJ 斷言庫 -->
        <dependency>
            <groupId>org.assertj</groupId>
            <artifactId>assertj-core</artifactId>       <!-- ‹4› -->
            <version>${assertj.version}</version>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <!-- Surefire Plugin for running tests -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.1.2</version>
                <configuration>
                    <properties>
                        <configurationParameters>
                            cucumber.junit-platform.naming-strategy=long
                        </configurationParameters>
                    </properties>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

**程式碼解析**：

- **‹1›** `cucumber.version`：統一管理 Cucumber 版本，便於升級
- **‹2›** `cucumber-java`：Cucumber 的 Java 實作，提供 @Given/@When/@Then 註解
- **‹3›** `cucumber-junit-platform-engine`：讓 JUnit 5 可以執行 Cucumber 測試
- **‹4›** `assertj-core`：流暢的斷言庫，比 JUnit 內建斷言更易讀

**步驟 3：建立專案結構**

```
bdd-tests/
├── pom.xml
└── src/
    ├── main/
    │   └── java/
    │       └── com/readmore/
    │           ├── service/
    │           │   └── DiscountService.java
    │           └── model/
    │               └── Member.java
    └── test/
        ├── java/
        │   └── com/readmore/
        │       ├── CucumberTestRunner.java     # 測試執行器
        │       └── steps/
        │           └── DiscountSteps.java      # Step Definitions
        └── resources/
            ├── features/
            │   └── discount.feature            # Gherkin 場景
            └── cucumber.properties             # Cucumber 配置
```

**步驟 4：配置 Cucumber**

```properties
# src/test/resources/cucumber.properties
cucumber.publish.quiet=true
cucumber.plugin=pretty,html:target/cucumber-reports/cucumber.html
cucumber.glue=com.readmore.steps
cucumber.features=src/test/resources/features
```

**步驟 5：建立測試執行器**

```java
// src/test/java/com/readmore/CucumberTestRunner.java
package com.readmore;

import org.junit.platform.suite.api.ConfigurationParameter;
import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

import static io.cucumber.junit.platform.engine.Constants.*;

@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
@ConfigurationParameter(key = GLUE_PROPERTY_NAME, value = "com.readmore.steps")
@ConfigurationParameter(key = PLUGIN_PROPERTY_NAME, value = "pretty")
public class CucumberTestRunner {
    // 這是測試入口點，不需要任何程式碼
}
```

### 8.2.2 TypeScript 環境設定（Node.js）

**步驟 1：初始化專案**

```bash
mkdir bdd-tests-ts && cd bdd-tests-ts
npm init -y
```

**步驟 2：安裝依賴**

```bash
# Cucumber 核心
npm install --save-dev @cucumber/cucumber

# TypeScript 支援
npm install --save-dev typescript ts-node @types/node

# 斷言庫
npm install --save-dev chai @types/chai

# 可選：Playwright（UI 測試）
npm install --save-dev @playwright/test
```

**步驟 3：配置 package.json**

```json
{
  "name": "bdd-tests-ts",
  "version": "1.0.0",
  "scripts": {
    "test": "cucumber-js",
    "test:smoke": "cucumber-js --tags '@smoke'",
    "test:report": "cucumber-js --format html:reports/cucumber.html"
  },
  "devDependencies": {
    "@cucumber/cucumber": "^10.0.1",
    "@types/chai": "^4.3.11",
    "@types/node": "^20.10.0",
    "chai": "^4.3.10",
    "ts-node": "^10.9.1",
    "typescript": "^5.3.2"
  }
}
```

**步驟 4：配置 TypeScript**

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "declaration": true
  },
  "include": ["src/**/*", "features/**/*"],
  "exclude": ["node_modules"]
}
```

**步驟 5：配置 Cucumber**

```javascript
// cucumber.js
module.exports = {
  default: {
    requireModule: ['ts-node/register'],
    require: ['features/step-definitions/**/*.ts'],
    format: [
      'progress-bar',
      'html:reports/cucumber-report.html'
    ],
    formatOptions: {
      snippetInterface: 'async-await'
    }
  }
};
```

**步驟 6：建立專案結構**

```
bdd-tests-ts/
├── package.json
├── tsconfig.json
├── cucumber.js
├── features/
│   ├── discount.feature
│   └── step-definitions/
│       ├── discount.steps.ts
│       └── hooks.ts
├── src/
│   ├── services/
│   │   └── DiscountService.ts
│   └── models/
│       └── Member.ts
└── reports/
```

### 8.2.3 IDE 整合

**VS Code 擴充套件**：

```json
// .vscode/extensions.json
{
  "recommendations": [
    "cucumber.cucumber-official",
    "alexkrechik.cucumberautocomplete"
  ]
}
```

**Cucumber Autocomplete 設定**：

```json
// .vscode/settings.json
{
  "cucumberautocomplete.steps": [
    "features/step-definitions/**/*.ts",
    "features/step-definitions/**/*.js"
  ],
  "cucumberautocomplete.syncfeatures": "features/**/*.feature"
}
```

**IntelliJ IDEA**：

1. 安裝 "Cucumber for Java" 和 "Gherkin" 插件
2. 在 Settings → Languages & Frameworks → Cucumber 配置 Glue 路徑

---

## 8.3 執行 Cucumber 場景

### 8.3.1 撰寫第一個 Feature 檔案

讓我們從 ReadMore 書店的「會員折扣」功能開始：

```gherkin
# features/discount.feature
@discount @smoke
Feature: 會員折扣計算
  作為一個 ReadMore 書店的會員
  我想要在購物時自動獲得折扣
  以便享受會員專屬的購物優惠

  Background:
    Given 系統已載入標準折扣規則

  Rule: 一般會員滿 500 享 5% 折扣

    @critical
    Scenario: 訂單達到折扣門檻
      Given 我是一般會員
      When 我的訂單金額是 600 元
      Then 我應該獲得 5% 的折扣
      And 實付金額應該是 570 元

    Scenario: 訂單未達折扣門檻
      Given 我是一般會員
      When 我的訂單金額是 400 元
      Then 我應該獲得 0% 的折扣
      And 實付金額應該是 400 元

  Rule: VIP 會員享有進階折扣

    Scenario: VIP 會員基本折扣
      Given 我是 VIP 會員
      When 我的訂單金額是 400 元
      Then 我應該獲得 5% 的折扣
      And 實付金額應該是 380 元
```

### 8.3.2 第一次執行：生成 Step Snippets

當你第一次執行測試，Cucumber 會提示你缺少 Step Definitions：

**執行命令**：

```bash
# Java (Maven)
mvn test

# TypeScript (npm)
npm test
```

**輸出結果**：

```
Scenario: 訂單達到折扣門檻
  Given 系統已載入標準折扣規則
      # TODO: Write code here that turns the phrase above into concrete actions

  Given 我是一般會員
      # TODO: Write code here that turns the phrase above into concrete actions

  When 我的訂單金額是 600 元
      # TODO: Write code here that turns the phrase above into concrete actions

You can implement missing steps with these snippets:

@Given("系統已載入標準折扣規則")
public void 系統已載入標準折扣規則() {
    // Write code here that turns the phrase above into concrete actions
    throw new io.cucumber.java.PendingException();
}

@Given("我是一般會員")
public void 我是一般會員() {
    // Write code here that turns the phrase above into concrete actions
    throw new io.cucumber.java.PendingException();
}

// ... 更多 snippets
```

這是 Cucumber 自動生成的程式碼骨架——你的起點！

### 8.3.3 命令列執行選項

**基本執行**：

```bash
# 執行所有測試
npm test                    # Node.js
mvn test                    # Java

# 執行特定標籤
npm test -- --tags "@smoke"
mvn test -Dcucumber.filter.tags="@smoke"

# 執行特定 Feature 檔案
npm test -- features/discount.feature
mvn test -Dcucumber.features="src/test/resources/features/discount.feature"
```

**執行過濾選項**：

| 選項 | 說明 | 範例 |
|------|------|------|
| `--tags` | 依標籤篩選 | `--tags "@smoke and not @slow"` |
| `--name` | 依場景名稱篩選 | `--name "VIP.*折扣"` |
| Feature 路徑 | 指定 Feature 檔案 | `features/discount.feature` |
| 行號 | 執行特定場景 | `features/discount.feature:15` |

**表 8.3：Cucumber 命令列選項**

---

## 8.4 撰寫 Glue Code（Step Definitions）

### 8.4.1 Step Definitions 基礎

Step Definitions 是連接 Gherkin 場景與實際程式碼的橋樑。

```mermaid
graph LR
    G[Gherkin 場景<br/>────────<br/>Given 我是一般會員<br/>When 訂單金額是 600 元<br/>Then 折扣應該是 5%]

    SD[Step Definitions<br/>────────<br/>@Given 我是一般會員<br/>→ createMember(REGULAR)<br/><br/>@When 訂單金額是 {int} 元<br/>→ createOrder(amount)<br/><br/>@Then 折扣應該是 {int}%<br/>→ verifyDiscount(percent)]

    APP[應用程式<br/>────────<br/>DiscountService<br/>MemberService<br/>OrderService]

    G --> SD --> APP

    style G fill:#e3f2fd
    style SD fill:#fff3e0
    style APP fill:#e8f5e9
```

**圖 8.3：Step Definitions 的橋接作用**

### 8.4.2 Java Step Definitions 實作

```java
// src/test/java/com/readmore/steps/DiscountSteps.java
package com.readmore.steps;

import com.readmore.model.Member;
import com.readmore.model.MemberType;
import com.readmore.model.Order;
import com.readmore.service.DiscountService;
import io.cucumber.java.zh_tw.假設;
import io.cucumber.java.zh_tw.當;
import io.cucumber.java.zh_tw.那麼;
import static org.assertj.core.api.Assertions.assertThat;

public class DiscountSteps {

    private DiscountService discountService;    // ‹1›
    private Member currentMember;
    private Order currentOrder;
    private double calculatedDiscount;

    @假設("系統已載入標準折扣規則")        // ‹2›
    public void 系統已載入標準折扣規則() {
        discountService = new DiscountService();
        discountService.loadStandardRules();
    }

    @假設("我是一般會員")
    public void 我是一般會員() {
        currentMember = new Member(MemberType.REGULAR);
    }

    @假設("我是 VIP 會員")
    public void 我是VIP會員() {
        currentMember = new Member(MemberType.VIP);
    }

    @當("我的訂單金額是 {int} 元")       // ‹3›
    public void 我的訂單金額是_元(int amount) {
        currentOrder = new Order(currentMember, amount);
        calculatedDiscount = discountService.calculateDiscount(currentOrder);
    }

    @那麼("我應該獲得 {int}% 的折扣")    // ‹4›
    public void 我應該獲得_的折扣(int expectedPercent) {
        double expectedDiscount = expectedPercent / 100.0;
        assertThat(calculatedDiscount)
            .as("折扣百分比")
            .isEqualTo(expectedDiscount);
    }

    @那麼("實付金額應該是 {int} 元")
    public void 實付金額應該是_元(int expectedAmount) {
        double actualAmount = currentOrder.getAmount() * (1 - calculatedDiscount);
        assertThat(actualAmount)
            .as("實付金額")
            .isEqualTo(expectedAmount);
    }
}
```

**程式碼解析**：

- **‹1›** 實例變數用於在步驟間共享狀態
- **‹2›** `@假設` 是 `@Given` 的中文版本，Cucumber 支援多語言
- **‹3›** `{int}` 是參數佔位符，Cucumber 自動擷取數值
- **‹4›** 使用 AssertJ 的流暢斷言，錯誤訊息更清楚

### 8.4.3 TypeScript Step Definitions 實作

```typescript
// features/step-definitions/discount.steps.ts
import { Given, When, Then, Before } from '@cucumber/cucumber';
import { expect } from 'chai';
import { DiscountService } from '../../src/services/DiscountService';
import { Member, MemberType } from '../../src/models/Member';
import { Order } from '../../src/models/Order';

// 測試上下文
interface TestContext {
    discountService: DiscountService;
    currentMember?: Member;
    currentOrder?: Order;
    calculatedDiscount: number;
}

let context: TestContext;

// 每個場景前重置上下文
Before(function() {
    context = {
        discountService: new DiscountService(),
        calculatedDiscount: 0
    };
});

Given('系統已載入標準折扣規則', function() {
    context.discountService.loadStandardRules();
});

Given('我是一般會員', function() {
    context.currentMember = new Member(MemberType.REGULAR);
});

Given('我是 VIP 會員', function() {
    context.currentMember = new Member(MemberType.VIP);
});

When('我的訂單金額是 {int} 元', function(amount: number) {   // ‹1›
    if (!context.currentMember) {
        throw new Error('會員未設定');
    }
    context.currentOrder = new Order(context.currentMember, amount);
    context.calculatedDiscount = context.discountService
        .calculateDiscount(context.currentOrder);
});

Then('我應該獲得 {int}% 的折扣', function(expectedPercent: number) {
    const expectedDiscount = expectedPercent / 100;
    expect(context.calculatedDiscount)
        .to.equal(expectedDiscount, `預期折扣 ${expectedPercent}%`);  // ‹2›
});

Then('實付金額應該是 {int} 元', function(expectedAmount: number) {
    if (!context.currentOrder) {
        throw new Error('訂單未建立');
    }
    const actualAmount = context.currentOrder.amount * (1 - context.calculatedDiscount);
    expect(actualAmount).to.equal(expectedAmount);
});
```

**程式碼解析**：

- **‹1›** `{int}` 佔位符自動轉型為 `number`
- **‹2›** Chai 的 `expect` 斷言，第二個參數是錯誤訊息

### 8.4.4 參數類型與 Cucumber Expressions

Cucumber 支援多種參數類型：

| 表達式 | 匹配範例 | TypeScript 類型 | Java 類型 |
|--------|---------|-----------------|-----------|
| `{int}` | 100, -5 | `number` | `int` |
| `{float}` | 3.14, -2.5 | `number` | `double` |
| `{word}` | hello（無空格）| `string` | `String` |
| `{string}` | "hello world" | `string` | `String` |
| `{}` | 任意文字 | `string` | `String` |

**表 8.4：Cucumber Expression 參數類型**

**自訂參數類型**：

```java
// Java - 自訂 MemberType 參數
@ParameterType("一般|VIP|白金")
public MemberType memberType(String type) {
    return switch (type) {
        case "一般" -> MemberType.REGULAR;
        case "VIP" -> MemberType.VIP;
        case "白金" -> MemberType.PLATINUM;
        default -> throw new IllegalArgumentException("未知會員類型: " + type);
    };
}

@Given("我是 {memberType} 會員")
public void 我是某類型會員(MemberType type) {
    currentMember = new Member(type);
}
```

```typescript
// TypeScript - 自訂參數類型
import { defineParameterType } from '@cucumber/cucumber';

defineParameterType({
    name: 'memberType',
    regexp: /一般|VIP|白金/,
    transformer: (type: string) => {
        const mapping: Record<string, MemberType> = {
            '一般': MemberType.REGULAR,
            'VIP': MemberType.VIP,
            '白金': MemberType.PLATINUM
        };
        return mapping[type];
    }
});

Given('我是 {memberType} 會員', function(type: MemberType) {
    context.currentMember = new Member(type);
});
```

### 8.4.5 處理 Data Tables

當 Gherkin 步驟包含表格時，Step Definition 需要處理 DataTable：

**Gherkin**：

```gherkin
Scenario: 批量計算多筆訂單折扣
  Given 系統中有以下會員:
    | 帳號   | 等級 |
    | alice  | 一般 |
    | bob    | VIP  |
  When 計算以下訂單的折扣:
    | 會員帳號 | 訂單金額 |
    | alice    | 600      |
    | bob      | 400      |
  Then 折扣結果應該是:
    | 會員帳號 | 原價 | 折扣率 | 實付 |
    | alice    | 600  | 5%     | 570  |
    | bob      | 400  | 5%     | 380  |
```

**Java 處理 DataTable**：

```java
@Given("系統中有以下會員:")
public void 系統中有以下會員(DataTable dataTable) {
    List<Map<String, String>> rows = dataTable.asMaps();  // ‹1›
    for (Map<String, String> row : rows) {
        String account = row.get("帳號");
        MemberType type = parseMemberType(row.get("等級"));
        memberService.createMember(account, type);
    }
}

@When("計算以下訂單的折扣:")
public void 計算以下訂單的折扣(DataTable dataTable) {
    List<Map<String, String>> rows = dataTable.asMaps();
    for (Map<String, String> row : rows) {
        String account = row.get("會員帳號");
        int amount = Integer.parseInt(row.get("訂單金額"));
        // 處理每筆訂單...
    }
}

@Then("折扣結果應該是:")
public void 折扣結果應該是(DataTable expected) {
    List<Map<String, String>> expectedRows = expected.asMaps();
    // 驗證每筆結果...
}
```

**TypeScript 處理 DataTable**：

```typescript
import { DataTable } from '@cucumber/cucumber';

Given('系統中有以下會員:', function(dataTable: DataTable) {
    const rows = dataTable.hashes();  // ‹1›
    for (const row of rows) {
        const account = row['帳號'];
        const type = parseMemberType(row['等級']);
        memberService.createMember(account, type);
    }
});
```

**‹1›** `asMaps()` / `hashes()` 將表格轉換為物件陣列，以欄位名稱為 key。

---

## 8.5 使用 Background 與 Hooks 來進行設定與清除

### 8.5.1 Background vs. Hooks

兩者都用於設定測試前置條件，但有不同的適用場景：

| 特性 | Background | Hooks |
|------|------------|-------|
| **定義位置** | Feature 檔案中 | 程式碼中 |
| **可見性** | 業務人員可見 | 只有開發者可見 |
| **適用內容** | 業務相關的前置條件 | 技術設定（資料庫、瀏覽器）|
| **條件執行** | 不支援 | 支援（透過標籤）|
| **範圍** | 單一 Feature | 全域或條件式 |

**表 8.5：Background 與 Hooks 的比較**

**使用 Background**（業務前置條件）：

```gherkin
Feature: 會員購物

  Background:
    Given 系統中存在以下商品:
      | 名稱 | 價格 |
      | BDD 實戰 | 500 |
      | Clean Code | 600 |
    And 我已登入為一般會員
```

**使用 Hooks**（技術前置條件）：

```java
// Java Hooks
public class TestHooks {

    @Before
    public void setUp() {
        // 每個場景前：初始化 WebDriver、清理資料庫
        driver = WebDriverFactory.createDriver();
        DatabaseHelper.cleanTestData();
    }

    @After
    public void tearDown(Scenario scenario) {
        // 每個場景後：截圖（如果失敗）、關閉瀏覽器
        if (scenario.isFailed()) {
            takeScreenshot(scenario);
        }
        driver.quit();
    }
}
```

### 8.5.2 Hooks 的類型與執行順序

```mermaid
graph TB
    subgraph 執行順序
        BF[BeforeAll] --> B1[Before Hook 1]
        B1 --> B2[Before Hook 2]
        B2 --> BG[Background Steps]
        BG --> SC[Scenario Steps]
        SC --> A1[After Hook 1]
        A1 --> A2[After Hook 2]
        A2 --> AF[AfterAll]
    end

    style BF fill:#e3f2fd
    style AF fill:#e3f2fd
    style B1 fill:#fff3e0
    style B2 fill:#fff3e0
    style A1 fill:#ffcdd2
    style A2 fill:#ffcdd2
```

**圖 8.4：Hooks 執行順序**

**Java Hooks 範例**：

```java
public class TestHooks {

    private static WebDriver driver;
    private static DatabaseHelper db;

    @BeforeAll
    public static void globalSetUp() {
        // 整個測試套件執行一次
        db = new DatabaseHelper();
        db.initializeSchema();
    }

    @AfterAll
    public static void globalTearDown() {
        // 整個測試套件結束後執行一次
        db.close();
    }

    @Before
    public void setUp() {
        driver = WebDriverFactory.createDriver();
    }

    @Before(order = 10)  // ‹1› 控制執行順序
    public void prepareTestData() {
        db.insertTestData();
    }

    @After
    public void tearDown(Scenario scenario) {
        if (scenario.isFailed()) {
            byte[] screenshot = ((TakesScreenshot) driver).getScreenshotAs(OutputType.BYTES);
            scenario.attach(screenshot, "image/png", "failure-screenshot");  // ‹2›
        }
        driver.quit();
    }

    @After(order = 10)
    public void cleanUpTestData() {
        db.cleanTestData();
    }
}
```

**程式碼解析**：

- **‹1›** `order` 參數控制執行順序，數字小的先執行
- **‹2›** `scenario.attach()` 將截圖附加到測試報告

**TypeScript Hooks 範例**：

```typescript
// features/step-definitions/hooks.ts
import { Before, After, BeforeAll, AfterAll, Status } from '@cucumber/cucumber';
import { chromium, Browser, Page } from '@playwright/test';

let browser: Browser;
let page: Page;

BeforeAll(async function() {
    browser = await chromium.launch();
});

AfterAll(async function() {
    await browser.close();
});

Before(async function() {
    page = await browser.newPage();
    this.page = page;  // 存入 World 物件
});

After(async function({ pickle, result }) {
    if (result?.status === Status.FAILED) {
        const screenshot = await page.screenshot();
        this.attach(screenshot, 'image/png');
    }
    await page.close();
});
```

### 8.5.3 條件式 Hooks（Tagged Hooks）

只對特定標籤的場景執行 Hooks：

```java
// Java - 只對 @database 標籤執行
@Before("@database")
public void setUpDatabase() {
    DatabaseHelper.reset();
    DatabaseHelper.seedTestData();
}

@After("@database")
public void cleanUpDatabase() {
    DatabaseHelper.clean();
}

// 排除特定標籤
@Before("not @skip-auth")
public void setUpAuthentication() {
    AuthHelper.createTestUser();
}
```

```typescript
// TypeScript - Tagged Hooks
Before({ tags: '@database' }, async function() {
    await DatabaseHelper.reset();
    await DatabaseHelper.seedTestData();
});

Before({ tags: '@ui' }, async function() {
    this.page = await browser.newPage();
});

Before({ tags: 'not @skip-auth' }, async function() {
    await AuthHelper.createTestUser();
});
```

---

## 8.6 使用 Hooks 來準備測試環境

### 8.6.1 測試資料準備策略

有效的測試資料管理是穩定測試的基礎：

```mermaid
graph TB
    subgraph 測試資料策略
        A[策略選擇] --> B[每次重建]
        A --> C[交易回滾]
        A --> D[資料快照]
        A --> E[隨機資料]
    end

    B --> B1[優點：乾淨隔離<br/>缺點：速度慢]
    C --> C1[優點：速度快<br/>缺點：需支援交易]
    D --> D1[優點：速度快<br/>缺點：維護成本]
    E --> E1[優點：發現邊界<br/>缺點：難以重現]
```

**圖 8.5：測試資料準備策略**

**策略 1：每次重建**

```java
@Before
public void resetDatabase() {
    DatabaseHelper.dropAllTables();
    DatabaseHelper.runMigrations();
    DatabaseHelper.seedBaseData();
}
```

**策略 2：交易回滾**

```java
@Before
public void beginTransaction() {
    transaction = entityManager.getTransaction();
    transaction.begin();
}

@After
public void rollbackTransaction() {
    if (transaction.isActive()) {
        transaction.rollback();
    }
}
```

**策略 3：已知測試資料（Personas）**

```java
// 預定義的測試角色
public class TestPersonas {
    public static final Member ALICE = Member.builder()
        .id("test-alice")
        .name("Alice")
        .type(MemberType.REGULAR)
        .points(1000)
        .build();

    public static final Member BOB_VIP = Member.builder()
        .id("test-bob")
        .name("Bob")
        .type(MemberType.VIP)
        .points(5000)
        .build();
}

// 在 Hooks 中使用
@Before("@with-test-members")
public void createTestMembers() {
    memberRepository.save(TestPersonas.ALICE);
    memberRepository.save(TestPersonas.BOB_VIP);
}
```

### 8.6.2 外部服務模擬

真實環境中，你的應用可能依賴外部服務（支付閘道、郵件服務、第三方 API）。測試時需要模擬這些服務：

```java
// 使用 WireMock 模擬外部 API
@Before("@external-api")
public void setUpMockServer() {
    wireMockServer = new WireMockServer(8089);
    wireMockServer.start();

    // 模擬支付閘道
    wireMockServer.stubFor(
        post(urlEqualTo("/api/payment"))
            .willReturn(aResponse()
                .withStatus(200)
                .withBody("{\"status\":\"success\",\"transactionId\":\"TXN123\"}")
            )
    );
}

@After("@external-api")
public void tearDownMockServer() {
    wireMockServer.stop();
}
```

```typescript
// TypeScript - 使用 MSW (Mock Service Worker)
import { setupServer } from 'msw/node';
import { rest } from 'msw';

const server = setupServer(
    rest.post('/api/payment', (req, res, ctx) => {
        return res(
            ctx.json({ status: 'success', transactionId: 'TXN123' })
        );
    })
);

BeforeAll(() => server.listen());
AfterAll(() => server.close());
Before(() => server.resetHandlers());
```

---

## 8.7 使用 Docker 建立虛擬測試環境

### 8.7.1 為什麼使用 Docker？

| 好處 | 說明 |
|------|------|
| **環境一致性** | 本機、CI、生產環境完全相同 |
| **隔離性** | 每次測試都是乾淨的環境 |
| **可重現性** | 任何人都能重現測試結果 |
| **平行化** | 可以同時跑多組測試 |

**表 8.6：使用 Docker 的好處**

### 8.7.2 Docker Compose 測試環境

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  # 被測試的應用程式
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgres://test:test@db:5432/testdb
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  # 測試資料庫
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: testdb
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d testdb"]
      interval: 5s
      timeout: 5s
      retries: 5

  # 快取服務
  redis:
    image: redis:7-alpine

  # 測試執行器
  tests:
    build:
      context: .
      dockerfile: Dockerfile.test
    environment:
      - APP_URL=http://app:3000
      - DATABASE_URL=postgres://test:test@db:5432/testdb
    depends_on:
      - app
    volumes:
      - ./reports:/app/reports
```

### 8.7.3 Testcontainers 整合

Testcontainers 讓你可以在程式碼中動態啟動 Docker 容器：

**Java + Testcontainers**：

```java
// 使用 Testcontainers 管理測試資料庫
@Testcontainers
public class DatabaseIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @BeforeAll
    static void setUp() {
        // 容器自動啟動
        System.setProperty("DB_URL", postgres.getJdbcUrl());
        System.setProperty("DB_USER", postgres.getUsername());
        System.setProperty("DB_PASSWORD", postgres.getPassword());
    }
}
```

**TypeScript + Testcontainers**：

```typescript
import { PostgreSqlContainer, StartedPostgreSqlContainer } from '@testcontainers/postgresql';

let postgresContainer: StartedPostgreSqlContainer;

BeforeAll(async function() {
    postgresContainer = await new PostgreSqlContainer()
        .withDatabase('testdb')
        .withUsername('test')
        .withPassword('test')
        .start();

    process.env.DATABASE_URL = postgresContainer.getConnectionUri();
});

AfterAll(async function() {
    await postgresContainer.stop();
});
```

### 8.7.4 CI/CD 整合

**GitHub Actions 範例**：

```yaml
# .github/workflows/bdd-tests.yml
name: BDD Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run BDD tests
        run: npm test
        env:
          DATABASE_URL: postgres://test:test@localhost:5432/testdb

      - name: Upload test reports
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: cucumber-reports
          path: reports/
```

---

## 核心產出物

### 產出物 1：專案配置範本

**Maven pom.xml 精簡版**：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>bdd-project</artifactId>
    <version>1.0-SNAPSHOT</version>

    <properties>
        <cucumber.version>7.14.0</cucumber.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-java</artifactId>
            <version>${cucumber.version}</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-junit-platform-engine</artifactId>
            <version>${cucumber.version}</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.junit.platform</groupId>
            <artifactId>junit-platform-suite</artifactId>
            <version>1.10.0</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
```

**package.json 精簡版**：

```json
{
  "name": "bdd-project",
  "scripts": {
    "test": "cucumber-js",
    "test:smoke": "cucumber-js --tags '@smoke'"
  },
  "devDependencies": {
    "@cucumber/cucumber": "^10.0.1",
    "ts-node": "^10.9.1",
    "typescript": "^5.3.2"
  }
}
```

### 產出物 2：Step Definitions 範本

```java
// Java Step Definitions 範本
package com.example.steps;

import io.cucumber.java.Before;
import io.cucumber.java.After;
import io.cucumber.java.zh_tw.假設;
import io.cucumber.java.zh_tw.當;
import io.cucumber.java.zh_tw.那麼;
import static org.assertj.core.api.Assertions.assertThat;

public class ExampleSteps {

    // 測試上下文
    private Object result;

    @Before
    public void setUp() {
        // 每個場景前執行
    }

    @After
    public void tearDown() {
        // 每個場景後執行
    }

    @假設("前置條件 {string}")
    public void 設定前置條件(String condition) {
        // 設定測試狀態
    }

    @當("執行動作 {string}")
    public void 執行動作(String action) {
        // 執行被測試的行為
    }

    @那麼("結果應該是 {string}")
    public void 驗證結果(String expected) {
        assertThat(result).isEqualTo(expected);
    }
}
```

```typescript
// TypeScript Step Definitions 範本
import { Given, When, Then, Before, After } from '@cucumber/cucumber';
import { expect } from 'chai';

interface TestContext {
    result?: any;
}

let context: TestContext;

Before(function() {
    context = {};
});

After(function() {
    // 清理資源
});

Given('前置條件 {string}', function(condition: string) {
    // 設定測試狀態
});

When('執行動作 {string}', function(action: string) {
    // 執行被測試的行為
});

Then('結果應該是 {string}', function(expected: string) {
    expect(context.result).to.equal(expected);
});
```

### 產出物 3：Hooks 配置範本

```java
// Java Hooks 完整範本
package com.example.hooks;

import io.cucumber.java.*;

public class TestHooks {

    @BeforeAll
    public static void globalSetUp() {
        System.out.println("=== 測試套件開始 ===");
        // 初始化共用資源（資料庫連線池等）
    }

    @AfterAll
    public static void globalTearDown() {
        System.out.println("=== 測試套件結束 ===");
        // 釋放共用資源
    }

    @Before(order = 0)
    public void logScenarioStart(Scenario scenario) {
        System.out.println("場景開始: " + scenario.getName());
    }

    @Before(order = 10, value = "@database")
    public void setUpDatabase() {
        // 只對 @database 標籤的場景執行
    }

    @After(order = 10)
    public void captureScreenshotOnFailure(Scenario scenario) {
        if (scenario.isFailed()) {
            // 截圖並附加到報告
        }
    }

    @After(order = 0)
    public void logScenarioEnd(Scenario scenario) {
        System.out.println("場景結束: " + scenario.getName() +
            " - " + scenario.getStatus());
    }
}
```

---

## 8.8 章節總結

### 本章重點回顧

```mermaid
mindmap
  root((Chapter 08<br/>自動化驗收測試))
    測試策略
      測試金字塔
      驗收測試定位
      投資回報分析
    環境設定
      Java + Maven
      TypeScript + npm
      IDE 整合
    Step Definitions
      基礎語法
      參數類型
      DataTable 處理
    Hooks
      Before/After
      BeforeAll/AfterAll
      Tagged Hooks
    測試環境
      資料準備策略
      外部服務模擬
      Docker 整合
```

**圖 8.6：本章知識架構**

### 關鍵概念總結

| 概念 | 說明 |
|------|------|
| **測試金字塔** | 單元測試多、整合測試中、端到端測試少 |
| **Step Definitions** | 連接 Gherkin 與程式碼的橋樑 |
| **Cucumber Expressions** | `{int}`, `{string}` 等參數佔位符 |
| **Hooks** | Before/After 用於設定與清理 |
| **Tagged Hooks** | 對特定標籤執行的條件式 Hooks |
| **DataTable** | 處理 Gherkin 表格數據 |
| **Testcontainers** | 程式化管理 Docker 容器 |

**表 8.7：本章關鍵概念**

### 實踐清單

完成本章學習後，你應該能夠：

- [ ] 設定 Java 或 TypeScript 的 Cucumber 環境
- [ ] 撰寫能正確匹配 Gherkin 步驟的 Step Definitions
- [ ] 使用 Before/After Hooks 管理測試生命週期
- [ ] 處理 Gherkin 表格數據
- [ ] 使用標籤篩選要執行的測試
- [ ] 整合 Docker 建立隔離的測試環境
- [ ] 將測試整合到 CI/CD 流程

---

## 下一章預告

在本章中，我們學會了如何將 Gherkin 規格自動化。但隨著測試數量增加，你會遇到新的挑戰：測試變得脆弱、難以維護、執行緩慢。

在下一章「**撰寫穩固的自動化驗收測試**」中，我們將：

- 學習「人物設定」（Personas）模式管理測試資料
- 設計三層抽象架構提升可維護性
- 掌握讓測試更穩定的技巧
- 建立可擴展的測試架構

準備好打造產業級強度的測試了嗎？讓我們繼續前進！

---

**本章字數**：約 28,000 字
**建議閱讀時間**：100 分鐘
**動手實作時間**：180 分鐘
