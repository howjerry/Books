# Chapter 1 系統架構圖

## 1. 整體系統架構

```mermaid
graph TB
    subgraph "開發者互動"
        A[開發者編輯檔案]
        B[開發者輸入提示]
    end

    subgraph "Claude Code"
        C[Edit/Write 工具]
        D[使用者提示處理]
    end

    subgraph "Hook 系統"
        E[PostToolUse Hook]
        F[UserPromptSubmit Hook]
    end

    subgraph "規則引擎"
        G[路徑匹配器]
        H[關鍵字分析器]
        I[優先級排序器]
    end

    subgraph "技能庫"
        J[skill-rules.json]
        K[backend-dev-guidelines]
        L[frontend-dev-guidelines]
        M[其他技能...]
    end

    subgraph "輸出"
        N[主動建議]
        O[技能內容載入]
    end

    A -->|觸發| C
    B -->|觸發| D
    C -->|執行後| E
    D -->|提交時| F

    E -->|調用| G
    F -->|調用| H

    G -->|讀取| J
    H -->|讀取| J

    G -->|匹配| K
    G -->|匹配| L
    H -->|匹配| K
    H -->|匹配| L

    G --> I
    H --> I

    I -->|生成| N
    N -->|載入| O
    O -->|回饋| A
    O -->|回饋| B

    style E fill:#e1f5ff
    style F fill:#e1f5ff
    style G fill:#fff3e0
    style H fill:#fff3e0
    style I fill:#fff3e0
    style J fill:#f3e5f5
    style K fill:#f3e5f5
    style L fill:#f3e5f5
```

## 2. PostToolUse Hook 工作流程

```mermaid
sequenceDiagram
    participant Dev as 開發者
    participant Claude as Claude Code
    participant Hook as post-tool-use-tracker.sh
    participant Engine as 規則引擎
    participant Skills as 技能庫

    Dev->>Claude: 編輯 user.controller.ts
    Claude->>Claude: 執行 Edit 工具
    Claude->>Hook: 觸發 PostToolUse Hook
    Hook->>Hook: 記錄活動日誌
    Hook->>Engine: 傳入檔案路徑
    Engine->>Engine: 解析 skill-rules.json
    Engine->>Engine: 匹配路徑模式
    Engine->>Skills: 查詢技能資訊
    Skills-->>Engine: 返回技能詳情
    Engine-->>Hook: 返回匹配結果
    Hook-->>Claude: 顯示技能建議
    Claude-->>Dev: 💡 建議激活 backend-dev-guidelines
```

## 3. UserPromptSubmit Hook 工作流程

```mermaid
sequenceDiagram
    participant Dev as 開發者
    participant Claude as Claude Code
    participant Hook as skill-activation-prompt.sh
    participant Engine as 規則引擎
    participant Skills as 技能庫

    Dev->>Claude: 輸入「創建 API controller」
    Claude->>Hook: 觸發 UserPromptSubmit Hook
    Hook->>Engine: 傳入提示內容
    Engine->>Engine: 關鍵字匹配 (API, controller)
    Engine->>Engine: 意圖匹配 (create.*controller)
    Engine->>Skills: 查詢相關技能
    Skills-->>Engine: 返回技能清單
    Engine->>Engine: 優先級排序
    Engine-->>Hook: 返回排序後的技能
    Hook-->>Claude: 顯示技能建議
    Claude-->>Dev: 💡 建議激活 backend-dev-guidelines
    Claude->>Claude: 自動載入技能內容
    Claude-->>Dev: 根據技能指導生成程式碼
```

## 4. 規則引擎內部邏輯

```mermaid
flowchart TD
    Start[輸入: 檔案路徑或提示] --> LoadConfig[載入 skill-rules.json]
    LoadConfig --> CheckCache{快取有效?}
    CheckCache -->|是| UseCache[使用快取配置]
    CheckCache -->|否| ReadFile[讀取配置檔案]
    ReadFile --> ParseJSON[解析 JSON]
    ParseJSON --> UpdateCache[更新快取]

    UseCache --> MatchType{匹配類型?}
    UpdateCache --> MatchType

    MatchType -->|路徑| PathMatch[路徑模式匹配]
    MatchType -->|提示| PromptMatch[關鍵字/意圖匹配]

    PathMatch --> CheckExclusion{檢查排除規則}
    CheckExclusion -->|已排除| Skip[跳過該技能]
    CheckExclusion -->|未排除| AddToList[添加到匹配清單]

    PromptMatch --> AddToList
    Skip --> NextSkill{還有技能?}
    AddToList --> NextSkill

    NextSkill -->|是| MatchType
    NextSkill -->|否| SortByPriority[按優先級排序]

    SortByPriority --> Return[返回技能清單]
    Return --> End[結束]

    style LoadConfig fill:#e1f5ff
    style PathMatch fill:#fff3e0
    style PromptMatch fill:#fff3e0
    style SortByPriority fill:#c8e6c9
```

## 5. 技能規則配置結構

```mermaid
graph LR
    subgraph "skill-rules.json"
        A[技能清單] --> B[backend-dev-guidelines]
        A --> C[frontend-dev-guidelines]
        A --> D[其他技能...]
    end

    subgraph "技能配置"
        B --> B1[type: domain]
        B --> B2[enforcement: suggest]
        B --> B3[priority: high]
        B --> B4[pathPatterns]
        B --> B5[promptTriggers]
        B --> B6[exclusions]
    end

    subgraph "pathPatterns"
        B4 --> P1["src/api/**/*.ts"]
        B4 --> P2["**/*.controller.ts"]
        B4 --> P3["**/routes/**/*.ts"]
    end

    subgraph "promptTriggers"
        B5 --> T1[keywords]
        B5 --> T2[intents]
        T1 --> T1a["controller"]
        T1 --> T1b["API"]
        T2 --> T2a["create.*controller"]
    end

    subgraph "exclusions"
        B6 --> E1["**/*.test.ts"]
        B6 --> E2["**/*.spec.ts"]
    end

    style A fill:#f3e5f5
    style B fill:#e1f5ff
    style B4 fill:#fff3e0
    style B5 fill:#fff3e0
    style B6 fill:#ffebee
```

## 6. 資料流程圖

```mermaid
flowchart LR
    subgraph "輸入來源"
        A1[檔案編輯事件]
        A2[使用者提示]
    end

    subgraph "Hook 層"
        B1[post-tool-use-tracker.sh]
        B2[skill-activation-prompt.sh]
    end

    subgraph "處理層"
        C1[check-skills.ts]
        C2[skill-activation-prompt.ts]
        C3[rule-engine.ts]
    end

    subgraph "資料層"
        D1[skill-rules.json]
        D2[SKILL.md 檔案]
        D3[activity.log]
    end

    subgraph "輸出"
        E1[技能建議]
        E2[技能內容]
    end

    A1 --> B1
    A2 --> B2
    B1 --> C1
    B2 --> C2
    C1 --> C3
    C2 --> C3
    C3 --> D1
    C3 --> D2
    B1 --> D3
    C3 --> E1
    E1 --> E2

    style B1 fill:#e1f5ff
    style B2 fill:#e1f5ff
    style C3 fill:#fff3e0
    style D1 fill:#f3e5f5
    style E1 fill:#c8e6c9
```

## 7. 決策樹：技能激活邏輯

```mermaid
flowchart TD
    Start[事件觸發] --> EventType{事件類型?}

    EventType -->|PostToolUse| CheckTool{工具類型?}
    EventType -->|UserPromptSubmit| ExtractPrompt[提取提示內容]

    CheckTool -->|Edit/Write/MultiEdit| ExtractPath[提取檔案路徑]
    CheckTool -->|其他| End1[不處理]

    ExtractPath --> MatchPath[路徑模式匹配]
    ExtractPrompt --> MatchKeywords[關鍵字匹配]

    MatchPath --> HasMatch1{有匹配?}
    MatchKeywords --> HasMatch2{有匹配?}

    HasMatch1 -->|是| CheckExclude[檢查排除規則]
    HasMatch1 -->|否| End2[不顯示建議]

    HasMatch2 -->|是| CombineContext[結合檔案上下文]
    HasMatch2 -->|否| End3[不顯示建議]

    CheckExclude -->|已排除| End4[不顯示建議]
    CheckExclude -->|未排除| SortPriority1[排序技能]

    CombineContext --> SortPriority2[排序技能]

    SortPriority1 --> Display1[顯示技能建議]
    SortPriority2 --> Display2[顯示技能建議]

    Display1 --> LoadSkill1[載入技能內容]
    Display2 --> LoadSkill2[載入技能內容]

    LoadSkill1 --> End5[完成]
    LoadSkill2 --> End6[完成]

    style MatchPath fill:#fff3e0
    style MatchKeywords fill:#fff3e0
    style SortPriority1 fill:#c8e6c9
    style SortPriority2 fill:#c8e6c9
    style Display1 fill:#e1f5ff
    style Display2 fill:#e1f5ff
```

## 8. 系統組件關係圖

```mermaid
graph TB
    subgraph "外層：Claude Code 環境"
        CC[Claude Code IDE]
    end

    subgraph "Hook 層"
        H1[post-tool-use-tracker.sh]
        H2[skill-activation-prompt.sh]
    end

    subgraph "邏輯層"
        L1[check-skills.ts]
        L2[skill-activation-prompt.ts]
        L3[rule-engine.ts]
    end

    subgraph "配置層"
        C1[settings.json]
        C2[skill-rules.json]
    end

    subgraph "內容層"
        K1[技能目錄]
        K2[SKILL.md]
        K3[resources/*.md]
    end

    CC ---|配置| C1
    C1 ---|註冊| H1
    C1 ---|註冊| H2
    H1 ---|調用| L1
    H2 ---|調用| L2
    L1 ---|使用| L3
    L2 ---|使用| L3
    L3 ---|讀取| C2
    L3 ---|查詢| K1
    K1 ---|包含| K2
    K1 ---|包含| K3

    style CC fill:#bbdefb
    style H1 fill:#e1f5ff
    style H2 fill:#e1f5ff
    style L3 fill:#fff3e0
    style C2 fill:#f3e5f5
    style K1 fill:#f3e5f5
```

## 圖表說明

### 圖 1: 整體系統架構
展示從開發者互動到技能激活的完整流程，包含所有主要組件及其關係。

### 圖 2-3: Hook 工作流程
詳細說明兩個 Hook 的序列圖，展示時序和資料流動。

### 圖 4: 規則引擎內部邏輯
展示規則引擎的決策流程，包含快取機制、匹配邏輯和優先級排序。

### 圖 5: 技能規則配置結構
展示 `skill-rules.json` 的資料結構和各個欄位的關係。

### 圖 6: 資料流程圖
從輸入到輸出的資料流動，突顯關鍵處理步驟。

### 圖 7: 決策樹
展示系統如何決定是否激活技能以及激活哪些技能。

### 圖 8: 系統組件關係圖
展示所有組件的層次關係和依賴關係。
