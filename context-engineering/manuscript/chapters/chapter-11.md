# 第 11 章：企業級應用模式

> 夜間工廠：讓 Ralph 在你睡覺時工作

---

## 本章學習目標

完成本章後，你將能夠：

- 設計大規模程式碼遷移的 Ralph Loop 策略
- 實作自動化測試覆蓋率提升流程
- 建構「夜間工廠」Cron Job 系統
- 設計安全的權限控制與審計追蹤機制
- 在團隊環境中部署 Ralph Loop 工作流

---

## 11.1 企業環境的特殊挑戰

### 11.1.1 個人專案 vs 企業專案

在個人專案中使用 Ralph Loop 相對簡單——你是唯一的利害關係人，風險完全由自己承擔。但在企業環境中，情況複雜得多：

```
┌─────────────────────────────────────────────────────────────────┐
│                    企業環境特殊挑戰                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  挑戰 1：多利害關係人                                    │    │
│  │                                                          │    │
│  │  • 開發團隊：關心程式碼品質                              │    │
│  │  • 安全團隊：關心資安風險                                │    │
│  │  • 法務團隊：關心合規性                                  │    │
│  │  • 財務團隊：關心成本控制                                │    │
│  │  • 管理層：關心交付時程                                  │    │
│  │                                                          │    │
│  │  每個利害關係人都有不同的優先順序和擔憂                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  挑戰 2：規模與複雜度                                    │    │
│  │                                                          │    │
│  │  • 程式碼庫規模：數百萬行程式碼                          │    │
│  │  • 團隊規模：數十到數百人同時工作                        │    │
│  │  • 相依性：數百個內部和外部套件                          │    │
│  │  • 分支策略：複雜的 GitFlow 或 trunk-based              │    │
│  │                                                          │    │
│  │  Ralph Loop 必須能在這種複雜環境中安全運作               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  挑戰 3：合規與審計                                      │    │
│  │                                                          │    │
│  │  • SOC 2 Type II：需要完整的審計追蹤                     │    │
│  │  • GDPR/CCPA：資料處理的透明度                           │    │
│  │  • ISO 27001：資訊安全管理系統                           │    │
│  │  • 內部政策：程式碼審查、變更管理                        │    │
│  │                                                          │    │
│  │  AI 生成的程式碼必須符合這些要求                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.1.2 企業級架構設計原則

在企業環境部署 Ralph Loop 時，我們需要遵循幾個關鍵原則：

**1. 最小權限原則（Principle of Least Privilege）**

```go
// ‹1› 權限等級定義
type PermissionLevel int

const (
    // ‹2› 只讀 - 只能讀取程式碼，不能修改
    ReadOnly PermissionLevel = iota

    // ‹3› 受限寫入 - 只能修改特定檔案類型
    RestrictedWrite

    // ‹4› 標準寫入 - 可以修改程式碼，但不能修改配置
    StandardWrite

    // ‹5› 完全存取 - 可以修改任何檔案（需要額外審批）
    FullAccess
)

// ‹6› 權限配置
type PermissionConfig struct {
    Level            PermissionLevel
    AllowedPaths     []string  // 允許存取的路徑
    BlockedPaths     []string  // 禁止存取的路徑
    AllowedFileTypes []string  // 允許的檔案類型
    MaxFilesPerRun   int       // 每次運行最多修改的檔案數
}

// ‹7› 預設企業配置
func DefaultEnterpriseConfig() PermissionConfig {
    return PermissionConfig{
        Level: RestrictedWrite,
        AllowedPaths: []string{
            "src/**/*.ts",
            "src/**/*.tsx",
            "tests/**/*.ts",
        },
        BlockedPaths: []string{
            ".env*",
            "**/secrets/**",
            "**/credentials/**",
            "*.pem",
            "*.key",
        },
        AllowedFileTypes: []string{".ts", ".tsx", ".js", ".jsx"},
        MaxFilesPerRun:   50,
    }
}
```

**2. 審計追蹤（Audit Trail）**

每個操作都必須有完整的記錄，以便事後審查。

**3. 失敗安全（Fail-Safe）**

系統設計必須確保失敗時不會造成更大的損害。

**4. 漸進式部署（Gradual Rollout）**

大規模變更應該分階段進行，每階段都有驗證。

---

## 11.2 案例研究：Jest 到 Vitest 遷移

### 11.2.1 背景

這是一個真實的企業案例：一家中型軟體公司需要將他們的 React 專案從 Jest 遷移到 Vitest。

```
┌─────────────────────────────────────────────────────────────────┐
│                    專案概覽                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  專案規模：                                                      │
│  • 程式碼行數：150,000 行 TypeScript                            │
│  • 測試檔案：487 個                                             │
│  • 測試案例：3,247 個                                           │
│  • 團隊規模：12 位開發者                                        │
│                                                                  │
│  遷移原因：                                                      │
│  • Vitest 原生支援 ESM                                          │
│  • 更快的執行速度（平均快 2-3 倍）                              │
│  • 與 Vite 建構工具的整合                                       │
│  • 更好的 TypeScript 支援                                       │
│                                                                  │
│  傳統估價：                                                      │
│  • 2 位工程師 × 3 週 = 240 工時                                 │
│  • 成本：約 $36,000（含管理開銷）                               │
│  • 風險：遷移期間測試覆蓋率降低                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2.2 遷移策略設計

```
┌─────────────────────────────────────────────────────────────────┐
│                    分階段遷移策略                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  階段 0：準備（人工）                                            │
│  ─────────────────────                                          │
│  • 安裝 Vitest 及相關依賴                                       │
│  • 建立 vitest.config.ts                                        │
│  • 設置雙軌運行（Jest + Vitest 並存）                           │
│  • 時間：2 小時                                                 │
│                                                                  │
│  階段 1：核心工具遷移（Ralph Loop）                              │
│  ─────────────────────────────────                              │
│  • 遷移 setupTests.ts                                           │
│  • 遷移通用 mock 檔案                                           │
│  • 遷移測試工具函數                                             │
│  • 預計：50 次迭代                                              │
│                                                                  │
│  階段 2：模組逐一遷移（Ralph Loop × N）                         │
│  ─────────────────────────────────────                          │
│  • 按模組分批遷移                                               │
│  • 每批：約 30-50 個測試檔案                                    │
│  • 驗證：每批遷移後運行完整測試套件                             │
│  • 預計：10 批次 × 100 次迭代                                   │
│                                                                  │
│  階段 3：清理（人工 + Ralph Loop）                               │
│  ─────────────────────────────────                              │
│  • 移除 Jest 依賴                                               │
│  • 刪除 Jest 配置                                               │
│  • 更新 CI/CD 流程                                              │
│  • 時間：4 小時                                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2.3 PROMPT.md 設計

```markdown
# Jest 到 Vitest 遷移 - 批次 {{BATCH_NUMBER}}

## 情境

我們正在將專案的測試框架從 Jest 遷移到 Vitest。
這是第 {{BATCH_NUMBER}} 批次，處理 {{MODULE_NAME}} 模組。

## 當前狀態

已遷移的模組：
{{COMPLETED_MODULES}}

本批次目標檔案：
{{TARGET_FILES}}

## 任務

將目標檔案從 Jest 語法遷移到 Vitest 語法。

## 遷移規則

### Import 語句
```typescript
// Jest（前）
import { render, screen } from '@testing-library/react';

// Vitest（後）
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
```

### Mock 函數
```typescript
// Jest（前）
jest.fn()
jest.mock('./module')
jest.spyOn(obj, 'method')

// Vitest（後）
vi.fn()
vi.mock('./module')
vi.spyOn(obj, 'method')
```

### Timer Mock
```typescript
// Jest（前）
jest.useFakeTimers()
jest.advanceTimersByTime(1000)
jest.runAllTimers()

// Vitest（後）
vi.useFakeTimers()
vi.advanceTimersByTime(1000)
vi.runAllTimers()
```

### 模組 Mock
```typescript
// Jest（前）
jest.mock('./api', () => ({
  fetchData: jest.fn()
}));

// Vitest（後）
vi.mock('./api', () => ({
  fetchData: vi.fn()
}));
```

## 完成條件

1. [ ] 所有目標檔案已遷移至 Vitest 語法
2. [ ] `npm run test:vitest -- --run {{MODULE_PATH}}` 通過
3. [ ] 沒有 Jest 相關的 import 語句
4. [ ] 沒有 `jest.` 呼叫

## 工作流程

1. 執行 `npm run test:vitest -- --run {{MODULE_PATH}}` 查看當前狀態
2. 分析錯誤訊息，識別需要修改的檔案
3. 應用遷移規則修改檔案
4. 重新執行測試驗證
5. 重複直到所有測試通過

## 約束

- 只修改測試檔案，不要修改原始碼
- 保留所有現有的測試案例和斷言
- 如果遇到無法自動處理的情況，記錄在 migration-notes.md
```

### 11.2.4 批次協調器實現

```go
package migration

import (
    "context"
    "encoding/json"
    "fmt"
    "os"
    "os/exec"
    "path/filepath"
    "strings"
    "time"
)

// ‹1› 遷移批次
type MigrationBatch struct {
    Number         int
    ModuleName     string
    TargetFiles    []string
    Status         BatchStatus
    StartTime      time.Time
    EndTime        time.Time
    Iterations     int
    TokensUsed     int64
    ErrorCount     int
}

type BatchStatus string

const (
    BatchPending    BatchStatus = "pending"
    BatchInProgress BatchStatus = "in_progress"
    BatchCompleted  BatchStatus = "completed"
    BatchFailed     BatchStatus = "failed"
)

// ‹2› 遷移協調器
type MigrationCoordinator struct {
    ProjectRoot    string
    Batches        []MigrationBatch
    CurrentBatch   int
    PromptTemplate string

    // 配置
    MaxIterations  int
    CostLimit      float64

    // 狀態追蹤
    TotalTokens    int64
    TotalCost      float64
}

// ‹3› 建立新的協調器
func NewMigrationCoordinator(projectRoot string) (*MigrationCoordinator, error) {
    // 讀取專案結構，規劃批次
    batches, err := planBatches(projectRoot)
    if err != nil {
        return nil, fmt.Errorf("failed to plan batches: %w", err)
    }

    template, err := os.ReadFile(filepath.Join(projectRoot, ".ralph/migration-prompt.md"))
    if err != nil {
        return nil, fmt.Errorf("failed to read prompt template: %w", err)
    }

    return &MigrationCoordinator{
        ProjectRoot:    projectRoot,
        Batches:        batches,
        CurrentBatch:   0,
        PromptTemplate: string(template),
        MaxIterations:  200,
        CostLimit:      100.0,
    }, nil
}

// ‹4› 規劃批次
func planBatches(projectRoot string) ([]MigrationBatch, error) {
    var batches []MigrationBatch

    // 掃描測試目錄結構
    modules, err := identifyModules(projectRoot)
    if err != nil {
        return nil, err
    }

    // 按模組建立批次
    for i, module := range modules {
        files, err := findTestFiles(projectRoot, module)
        if err != nil {
            return nil, err
        }

        batches = append(batches, MigrationBatch{
            Number:      i + 1,
            ModuleName:  module,
            TargetFiles: files,
            Status:      BatchPending,
        })
    }

    return batches, nil
}

// ‹5› 識別模組
func identifyModules(projectRoot string) ([]string, error) {
    srcDir := filepath.Join(projectRoot, "src")

    var modules []string
    entries, err := os.ReadDir(srcDir)
    if err != nil {
        return nil, err
    }

    for _, entry := range entries {
        if entry.IsDir() {
            modules = append(modules, entry.Name())
        }
    }

    return modules, nil
}

// ‹6› 執行遷移
func (c *MigrationCoordinator) Run(ctx context.Context) error {
    for c.CurrentBatch < len(c.Batches) {
        batch := &c.Batches[c.CurrentBatch]

        // 檢查成本限制
        if c.TotalCost >= c.CostLimit {
            return fmt.Errorf("cost limit reached: $%.2f", c.TotalCost)
        }

        // 執行批次
        if err := c.runBatch(ctx, batch); err != nil {
            batch.Status = BatchFailed
            return fmt.Errorf("batch %d failed: %w", batch.Number, err)
        }

        // 驗證批次結果
        if err := c.verifyBatch(ctx, batch); err != nil {
            batch.Status = BatchFailed
            return fmt.Errorf("batch %d verification failed: %w", batch.Number, err)
        }

        batch.Status = BatchCompleted
        batch.EndTime = time.Now()

        // 記錄進度
        c.saveProgress()

        c.CurrentBatch++
    }

    return nil
}

// ‹7› 執行單一批次
func (c *MigrationCoordinator) runBatch(ctx context.Context, batch *MigrationBatch) error {
    batch.Status = BatchInProgress
    batch.StartTime = time.Now()

    // 生成批次專用的 PROMPT.md
    prompt := c.generateBatchPrompt(batch)

    promptPath := filepath.Join(c.ProjectRoot, ".ralph/PROMPT.md")
    if err := os.WriteFile(promptPath, []byte(prompt), 0644); err != nil {
        return err
    }

    // 執行 Ralph Loop
    for iteration := 0; iteration < c.MaxIterations; iteration++ {
        batch.Iterations++

        // 檢查收斂條件
        converged, err := c.checkConvergence(ctx, batch)
        if err != nil {
            return err
        }

        if converged {
            return nil
        }

        // 執行一次迭代
        tokens, err := c.runIteration(ctx, batch)
        if err != nil {
            batch.ErrorCount++
            if batch.ErrorCount > 10 {
                return fmt.Errorf("too many errors in batch")
            }
            continue
        }

        batch.TokensUsed += tokens
        c.TotalTokens += tokens
        c.TotalCost = c.calculateCost(c.TotalTokens)
    }

    return fmt.Errorf("max iterations reached without convergence")
}

// ‹8› 生成批次提示詞
func (c *MigrationCoordinator) generateBatchPrompt(batch *MigrationBatch) string {
    // 收集已完成的模組
    var completedModules []string
    for _, b := range c.Batches[:c.CurrentBatch] {
        if b.Status == BatchCompleted {
            completedModules = append(completedModules, b.ModuleName)
        }
    }

    prompt := c.PromptTemplate
    prompt = strings.ReplaceAll(prompt, "{{BATCH_NUMBER}}", fmt.Sprintf("%d", batch.Number))
    prompt = strings.ReplaceAll(prompt, "{{MODULE_NAME}}", batch.ModuleName)
    prompt = strings.ReplaceAll(prompt, "{{COMPLETED_MODULES}}", strings.Join(completedModules, "\n"))
    prompt = strings.ReplaceAll(prompt, "{{TARGET_FILES}}", strings.Join(batch.TargetFiles, "\n"))
    prompt = strings.ReplaceAll(prompt, "{{MODULE_PATH}}", fmt.Sprintf("src/%s", batch.ModuleName))

    return prompt
}

// ‹9› 檢查收斂條件
func (c *MigrationCoordinator) checkConvergence(ctx context.Context, batch *MigrationBatch) (bool, error) {
    // 執行 Vitest 檢查
    cmd := exec.CommandContext(ctx, "npm", "run", "test:vitest", "--",
        "--run", fmt.Sprintf("src/%s", batch.ModuleName))
    cmd.Dir = c.ProjectRoot

    output, err := cmd.CombinedOutput()
    if err != nil {
        // 測試失敗，還沒收斂
        return false, nil
    }

    // 檢查是否還有 Jest 語法
    hasJest, err := c.hasJestSyntax(batch)
    if err != nil {
        return false, err
    }

    return !hasJest && string(output) != "", nil
}

// ‹10› 檢查 Jest 語法
func (c *MigrationCoordinator) hasJestSyntax(batch *MigrationBatch) (bool, error) {
    patterns := []string{
        "jest.fn",
        "jest.mock",
        "jest.spyOn",
        "from 'jest'",
        "jest.useFakeTimers",
    }

    for _, file := range batch.TargetFiles {
        content, err := os.ReadFile(filepath.Join(c.ProjectRoot, file))
        if err != nil {
            continue
        }

        for _, pattern := range patterns {
            if strings.Contains(string(content), pattern) {
                return true, nil
            }
        }
    }

    return false, nil
}

// ‹11› 驗證批次
func (c *MigrationCoordinator) verifyBatch(ctx context.Context, batch *MigrationBatch) error {
    // 執行完整測試套件
    cmd := exec.CommandContext(ctx, "npm", "run", "test:vitest", "--", "--run")
    cmd.Dir = c.ProjectRoot

    output, err := cmd.CombinedOutput()
    if err != nil {
        return fmt.Errorf("test suite failed: %s", string(output))
    }

    // 確認測試數量沒有減少
    // （可以通過解析 Vitest 輸出來檢查）

    return nil
}

// ‹12› 儲存進度
func (c *MigrationCoordinator) saveProgress() {
    progress := struct {
        Batches      []MigrationBatch `json:"batches"`
        CurrentBatch int              `json:"current_batch"`
        TotalCost    float64          `json:"total_cost"`
        TotalTokens  int64            `json:"total_tokens"`
    }{
        Batches:      c.Batches,
        CurrentBatch: c.CurrentBatch,
        TotalCost:    c.TotalCost,
        TotalTokens:  c.TotalTokens,
    }

    data, _ := json.MarshalIndent(progress, "", "  ")
    os.WriteFile(
        filepath.Join(c.ProjectRoot, ".ralph/migration-progress.json"),
        data,
        0644,
    )
}
```

### 11.2.5 實際執行結果

```
┌─────────────────────────────────────────────────────────────────┐
│                    遷移結果報告                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  執行摘要                                                        │
│  ─────────                                                      │
│  總執行時間：14 小時 23 分鐘                                    │
│  總迭代次數：1,247 次                                           │
│  總 Token 消耗：31,423,000                                      │
│  總成本：$157.12                                                │
│                                                                  │
│  批次統計                                                        │
│  ─────────                                                      │
│  批次   模組           檔案數  迭代數  成本     狀態             │
│  ────────────────────────────────────────────────────────────   │
│  1      auth           42      87      $12.34   ✅ 完成          │
│  2      dashboard      65      134     $21.45   ✅ 完成          │
│  3      users          38      72      $10.23   ✅ 完成          │
│  4      products       71      156     $24.67   ✅ 完成          │
│  5      orders         54      112     $17.89   ✅ 完成          │
│  6      payments       43      98      $15.43   ✅ 完成          │
│  7      notifications  35      67      $9.87    ✅ 完成          │
│  8      settings       29      54      $7.65    ✅ 完成          │
│  9      reports        58      124     $19.34   ✅ 完成          │
│  10     shared         52      343     $18.25   ✅ 完成          │
│                                                                  │
│  成本比較                                                        │
│  ─────────                                                      │
│  傳統方式估價：$36,000                                          │
│  Ralph Loop 實際成本：                                          │
│    • API 費用：$157.12                                          │
│    • 人力監督（8 小時 × $80）：$640                             │
│    • 設置與收尾（6 小時 × $80）：$480                           │
│    • 總計：$1,277.12                                            │
│                                                                  │
│  節省：$34,722.88（96.5%）                                      │
│  ROI：2,718%                                                    │
│                                                                  │
│  品質指標                                                        │
│  ─────────                                                      │
│  遷移前測試數：3,247                                            │
│  遷移後測試數：3,247（100% 保留）                               │
│  測試執行時間：                                                  │
│    • Jest：4 分 32 秒                                           │
│    • Vitest：1 分 47 秒（快 2.5 倍）                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11.3 測試覆蓋率自動提升

### 11.3.1 場景分析

測試覆蓋率是衡量程式碼品質的重要指標。許多企業設定了覆蓋率目標（如 80%），但達到這個目標往往需要大量人力。

```
┌─────────────────────────────────────────────────────────────────┐
│                    覆蓋率提升挑戰                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  典型情況：                                                      │
│                                                                  │
│  • 當前覆蓋率：62%                                              │
│  • 目標覆蓋率：80%                                              │
│  • 需要覆蓋的程式碼：~27,000 行                                 │
│                                                                  │
│  傳統方式的問題：                                                │
│                                                                  │
│  1. 撰寫測試是「無聊」的工作                                    │
│     • 開發者不喜歡補測試                                        │
│     • 優先級總是被其他任務擠掉                                  │
│                                                                  │
│  2. 邊際成本遞增                                                │
│     • 從 60% 到 70% 相對容易                                    │
│     • 從 70% 到 80% 需要更多努力                                │
│     • 剩餘的 20% 通常是最難測試的程式碼                        │
│                                                                  │
│  3. 時間壓力                                                     │
│     • 功能開發優先於測試                                        │
│     • 覆蓋率目標往往被忽略                                      │
│                                                                  │
│  Ralph Loop 的優勢：                                            │
│                                                                  │
│  • 機械化任務非常適合自動化                                     │
│  • 可以在夜間運行，不佔用工作時間                               │
│  • 覆蓋率報告提供明確的收斂條件                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.3.2 覆蓋率提升 PROMPT.md

```markdown
# 任務：測試覆蓋率提升

## 情境

專案的測試覆蓋率需要從 {{CURRENT_COVERAGE}}% 提升到 {{TARGET_COVERAGE}}%。

覆蓋率報告位置：coverage/lcov-report/index.html

優先處理的模組（覆蓋率低於平均）：
{{LOW_COVERAGE_MODULES}}

## 目標

1. 將整體測試覆蓋率從 {{CURRENT_COVERAGE}}% 提升至 {{TARGET_COVERAGE}}%
2. 為低覆蓋率的檔案新增有意義的測試
3. 確保新增的測試都能通過
4. 測試要涵蓋邊界條件和錯誤處理

## 約束

- 只新增測試，不修改原始碼（除非發現真正的 bug）
- 測試要有意義，不是為了覆蓋率而覆蓋
- 遵循專案現有的測試風格
- 每個測試檔案對應一個原始碼檔案

## 完成條件

當以下所有條件都滿足時，此任務視為完成：

1. [ ] 覆蓋率達到目標：`npm run coverage` 顯示 >= {{TARGET_COVERAGE}}%
2. [ ] 所有測試通過：`npm test` 返回 exit code 0
3. [ ] 沒有 skipped 或 pending 的測試

## 工作流程

1. **分析覆蓋率報告**
   ```bash
   npm run coverage
   # 查看哪些檔案覆蓋率最低
   ```

2. **識別低覆蓋檔案**
   - 列出覆蓋率低於平均的檔案
   - 優先處理核心業務邏輯

3. **逐檔案新增測試**
   對於每個低覆蓋檔案：
   a. 閱讀原始碼，理解功能
   b. 識別未被測試的分支/函數
   c. 撰寫測試案例
   d. 執行測試確認通過
   e. 重新生成覆蓋率報告

4. **驗證整體覆蓋率**
   ```bash
   npm run coverage
   # 確認達到目標
   ```

## 測試撰寫指南

### 好的測試

```typescript
describe('calculateTotal', () => {
  it('should return sum of all items', () => {
    const items = [{ price: 10 }, { price: 20 }];
    expect(calculateTotal(items)).toBe(30);
  });

  it('should return 0 for empty array', () => {
    expect(calculateTotal([])).toBe(0);
  });

  it('should handle negative prices', () => {
    const items = [{ price: -10 }, { price: 20 }];
    expect(calculateTotal(items)).toBe(10);
  });
});
```

### 要避免的測試

```typescript
// ❌ 沒有意義的測試
it('should exist', () => {
  expect(calculateTotal).toBeDefined();
});

// ❌ 測試實作細節
it('should call internal method', () => {
  // 不應該測試私有方法
});
```

## 注意事項

- 優先測試公開的 API，而非內部實作
- 邊界條件（空陣列、null、極大/極小值）要涵蓋
- 錯誤處理路徑也需要測試
- 避免過度 mock，可能導致測試與實際行為脫節
```

### 11.3.3 覆蓋率監控器

```go
package coverage

import (
    "encoding/json"
    "fmt"
    "os"
    "os/exec"
    "path/filepath"
    "regexp"
    "strconv"
    "strings"
)

// ‹1› 覆蓋率報告
type CoverageReport struct {
    Total      float64                      `json:"total"`
    ByFile     map[string]FileCoverage      `json:"by_file"`
    Timestamp  string                       `json:"timestamp"`
}

type FileCoverage struct {
    Statements float64 `json:"statements"`
    Branches   float64 `json:"branches"`
    Functions  float64 `json:"functions"`
    Lines      float64 `json:"lines"`
}

// ‹2› 覆蓋率監控器
type CoverageMonitor struct {
    ProjectRoot     string
    TargetCoverage  float64
    History         []CoverageReport
}

// ‹3› 獲取當前覆蓋率
func (m *CoverageMonitor) GetCurrentCoverage() (*CoverageReport, error) {
    // 執行覆蓋率命令
    cmd := exec.Command("npm", "run", "coverage", "--", "--json")
    cmd.Dir = m.ProjectRoot

    output, err := cmd.Output()
    if err != nil {
        return nil, fmt.Errorf("failed to run coverage: %w", err)
    }

    // 解析覆蓋率報告
    report, err := m.parseCoverageOutput(output)
    if err != nil {
        return nil, err
    }

    m.History = append(m.History, *report)
    return report, nil
}

// ‹4› 解析覆蓋率輸出
func (m *CoverageMonitor) parseCoverageOutput(output []byte) (*CoverageReport, error) {
    // 簡化版解析 - 實際實現需要根據工具輸出格式調整
    report := &CoverageReport{
        ByFile: make(map[string]FileCoverage),
    }

    // 解析總覆蓋率
    re := regexp.MustCompile(`All files\s*\|\s*([\d.]+)`)
    matches := re.FindSubmatch(output)
    if len(matches) > 1 {
        total, _ := strconv.ParseFloat(string(matches[1]), 64)
        report.Total = total
    }

    return report, nil
}

// ‹5› 獲取低覆蓋率檔案
func (m *CoverageMonitor) GetLowCoverageFiles(threshold float64) ([]string, error) {
    report, err := m.GetCurrentCoverage()
    if err != nil {
        return nil, err
    }

    var lowFiles []string
    for file, cov := range report.ByFile {
        if cov.Lines < threshold {
            lowFiles = append(lowFiles, file)
        }
    }

    return lowFiles, nil
}

// ‹6› 檢查是否達到目標
func (m *CoverageMonitor) IsTargetMet() (bool, float64, error) {
    report, err := m.GetCurrentCoverage()
    if err != nil {
        return false, 0, err
    }

    return report.Total >= m.TargetCoverage, report.Total, nil
}

// ‹7› 計算進展速度
func (m *CoverageMonitor) GetProgressRate() float64 {
    if len(m.History) < 2 {
        return 0
    }

    // 計算最近 5 次的平均進展
    count := min(5, len(m.History)-1)
    var totalProgress float64

    for i := len(m.History) - count; i < len(m.History); i++ {
        progress := m.History[i].Total - m.History[i-1].Total
        totalProgress += progress
    }

    return totalProgress / float64(count)
}

// ‹8› 預估完成時間
func (m *CoverageMonitor) EstimateIterationsToComplete() int {
    met, current, err := m.IsTargetMet()
    if err != nil || met {
        return 0
    }

    rate := m.GetProgressRate()
    if rate <= 0 {
        return -1 // 無法估計（沒有進展或倒退）
    }

    remaining := m.TargetCoverage - current
    return int(remaining / rate)
}
```

---

## 11.4 夜間工廠模式

### 11.4.1 概念介紹

「夜間工廠」（Night Factory）是一種利用非工作時間讓 AI 自動處理積壓任務的模式。就像工廠在夜間持續運作一樣，Ralph Loop 可以在你睡覺時完成工作。

```
┌─────────────────────────────────────────────────────────────────┐
│                    夜間工廠概念                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  傳統工作流程                                                    │
│  ──────────────                                                 │
│                                                                  │
│  09:00 ─────────────────────────────────────────────── 18:00    │
│         │ 開發者工作                                      │     │
│         │ ──────────────────────────────────────────────  │     │
│         │ • 功能開發                                      │     │
│         │ • Bug 修復                                      │     │
│         │ • 程式碼審查                                    │     │
│         └──────────────────────────────────────────────────     │
│                                                                  │
│  18:00 ─────────────────────────────────────────────── 09:00    │
│         │ 系統閒置                                        │     │
│         │ ──────────────────────────────────────────────  │     │
│         │ • CI/CD 偶爾運行                                │     │
│         │ • 監控系統                                      │     │
│         │ • 大量算力閒置                                  │     │
│         └──────────────────────────────────────────────────     │
│                                                                  │
│  夜間工廠工作流程                                                │
│  ──────────────────                                             │
│                                                                  │
│  09:00 ─────────────────────────────────────────────── 18:00    │
│         │ 開發者工作 + 定義夜間任務                        │     │
│         │ ──────────────────────────────────────────────  │     │
│         │ • 功能開發                                      │     │
│         │ • 編寫 PROMPT.md                                │     │
│         │ • 審查夜間工廠產出                              │     │
│         └──────────────────────────────────────────────────     │
│                                                                  │
│  23:00 ─────────────────────────────────────────────── 07:00    │
│         │ Ralph Loop 自動運行                             │     │
│         │ ──────────────────────────────────────────────  │     │
│         │ • 程式碼格式化                                  │     │
│         │ • 依賴更新                                      │     │
│         │ • 測試覆蓋率提升                                │     │
│         │ • 技術債務清理                                  │     │
│         └──────────────────────────────────────────────────     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.4.2 適合夜間工廠的任務

```
┌─────────────────────────────────────────────────────────────────┐
│                    夜間工廠適用任務                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ 高度適合                                                    │
│  ──────────                                                     │
│  • 程式碼格式化與 Linting 修復                                  │
│  • 依賴更新（npm update, security patches）                     │
│  • 測試覆蓋率提升                                               │
│  • 文件生成（JSDoc、README 更新）                               │
│  • 程式碼風格統一                                               │
│  • 棄用 API 遷移                                                │
│                                                                  │
│  ⚠️ 需要謹慎                                                    │
│  ────────────                                                   │
│  • 大規模重構（需要人工審查輸出）                               │
│  • 新功能開發（需要產品決策）                                   │
│  • 效能優化（需要驗證不影響功能）                               │
│                                                                  │
│  ❌ 不適合                                                      │
│  ──────────                                                     │
│  • 涉及生產環境的操作                                           │
│  • 需要外部審批的變更                                           │
│  • 安全敏感的修改                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.4.3 夜間工廠排程系統

```go
package nightfactory

import (
    "context"
    "encoding/json"
    "fmt"
    "log"
    "os"
    "os/exec"
    "path/filepath"
    "time"
)

// ‹1› 任務定義
type NightTask struct {
    ID          string        `json:"id"`
    Name        string        `json:"name"`
    PromptPath  string        `json:"prompt_path"`
    Priority    int           `json:"priority"`     // 1-10，數字越大優先級越高
    MaxCost     float64       `json:"max_cost"`     // 成本上限
    MaxDuration time.Duration `json:"max_duration"` // 時間上限
    Enabled     bool          `json:"enabled"`
    Schedule    string        `json:"schedule"`     // cron 表達式
}

// ‹2› 任務結果
type TaskResult struct {
    TaskID      string        `json:"task_id"`
    StartTime   time.Time     `json:"start_time"`
    EndTime     time.Time     `json:"end_time"`
    Status      string        `json:"status"`  // success, failed, timeout, cost_exceeded
    Iterations  int           `json:"iterations"`
    TokensUsed  int64         `json:"tokens_used"`
    Cost        float64       `json:"cost"`
    Output      string        `json:"output"`
    Error       string        `json:"error,omitempty"`
}

// ‹3› 夜間工廠
type NightFactory struct {
    ProjectRoot string
    Tasks       []NightTask
    Results     []TaskResult

    // 全局限制
    GlobalMaxCost     float64
    GlobalMaxDuration time.Duration
    CurrentCost       float64
}

// ‹4› 載入配置
func LoadNightFactory(projectRoot string) (*NightFactory, error) {
    configPath := filepath.Join(projectRoot, ".ralph/night-factory.json")

    data, err := os.ReadFile(configPath)
    if err != nil {
        return nil, fmt.Errorf("failed to read config: %w", err)
    }

    var config struct {
        Tasks             []NightTask   `json:"tasks"`
        GlobalMaxCost     float64       `json:"global_max_cost"`
        GlobalMaxDuration string        `json:"global_max_duration"`
    }

    if err := json.Unmarshal(data, &config); err != nil {
        return nil, fmt.Errorf("failed to parse config: %w", err)
    }

    duration, _ := time.ParseDuration(config.GlobalMaxDuration)

    return &NightFactory{
        ProjectRoot:       projectRoot,
        Tasks:             config.Tasks,
        GlobalMaxCost:     config.GlobalMaxCost,
        GlobalMaxDuration: duration,
    }, nil
}

// ‹5› 執行夜間工廠
func (f *NightFactory) Run(ctx context.Context) error {
    startTime := time.Now()

    // 按優先級排序任務
    f.sortTasksByPriority()

    log.Printf("Night Factory started with %d tasks", len(f.Tasks))

    for _, task := range f.Tasks {
        // 檢查是否應該停止
        if f.shouldStop(ctx, startTime) {
            log.Printf("Night Factory stopping: global limits reached")
            break
        }

        if !task.Enabled {
            continue
        }

        // 執行任務
        result := f.runTask(ctx, task)
        f.Results = append(f.Results, result)
        f.CurrentCost += result.Cost

        // 記錄結果
        log.Printf("Task %s completed: status=%s, cost=$%.2f",
            task.Name, result.Status, result.Cost)
    }

    // 生成報告
    f.generateReport()

    return nil
}

// ‹6› 檢查是否應該停止
func (f *NightFactory) shouldStop(ctx context.Context, startTime time.Time) bool {
    // 檢查 context 取消
    select {
    case <-ctx.Done():
        return true
    default:
    }

    // 檢查全局成本限制
    if f.CurrentCost >= f.GlobalMaxCost {
        return true
    }

    // 檢查全局時間限制
    if time.Since(startTime) >= f.GlobalMaxDuration {
        return true
    }

    return false
}

// ‹7› 執行單一任務
func (f *NightFactory) runTask(ctx context.Context, task NightTask) TaskResult {
    result := TaskResult{
        TaskID:    task.ID,
        StartTime: time.Now(),
    }

    // 建立任務 context，有時間和成本限制
    taskCtx, cancel := context.WithTimeout(ctx, task.MaxDuration)
    defer cancel()

    // 複製 PROMPT.md 到工作目錄
    promptContent, err := os.ReadFile(filepath.Join(f.ProjectRoot, task.PromptPath))
    if err != nil {
        result.Status = "failed"
        result.Error = fmt.Sprintf("failed to read prompt: %v", err)
        result.EndTime = time.Now()
        return result
    }

    workDir := filepath.Join(f.ProjectRoot, ".ralph/work", task.ID)
    os.MkdirAll(workDir, 0755)
    os.WriteFile(filepath.Join(workDir, "PROMPT.md"), promptContent, 0644)

    // 執行 Ralph Loop
    cmd := exec.CommandContext(taskCtx, "claude", "code", "--yes",
        "--max-cost", fmt.Sprintf("%.2f", task.MaxCost))
    cmd.Dir = f.ProjectRoot

    output, err := cmd.CombinedOutput()
    result.Output = string(output)
    result.EndTime = time.Now()

    if err != nil {
        if taskCtx.Err() == context.DeadlineExceeded {
            result.Status = "timeout"
        } else {
            result.Status = "failed"
            result.Error = err.Error()
        }
    } else {
        result.Status = "success"
    }

    // 解析 Token 使用量和成本
    result.TokensUsed, result.Cost = f.parseUsageFromOutput(output)

    return result
}

// ‹8› 生成報告
func (f *NightFactory) generateReport() {
    report := struct {
        RunTime     time.Time     `json:"run_time"`
        TotalCost   float64       `json:"total_cost"`
        TotalTasks  int           `json:"total_tasks"`
        Successful  int           `json:"successful"`
        Failed      int           `json:"failed"`
        Results     []TaskResult  `json:"results"`
    }{
        RunTime:    time.Now(),
        TotalCost:  f.CurrentCost,
        TotalTasks: len(f.Results),
        Results:    f.Results,
    }

    for _, r := range f.Results {
        if r.Status == "success" {
            report.Successful++
        } else {
            report.Failed++
        }
    }

    // 儲存報告
    data, _ := json.MarshalIndent(report, "", "  ")
    reportPath := filepath.Join(f.ProjectRoot,
        fmt.Sprintf(".ralph/reports/night-factory-%s.json",
            time.Now().Format("2006-01-02")))
    os.MkdirAll(filepath.Dir(reportPath), 0755)
    os.WriteFile(reportPath, data, 0644)

    // 發送通知（可選）
    f.sendNotification(report)
}

// ‹9› 發送通知
func (f *NightFactory) sendNotification(report interface{}) {
    // 可以整合 Slack、Email 或其他通知系統
    // 這裡只是示意
    log.Printf("Night Factory report generated")
}
```

### 11.4.4 配置範例

```json
{
  "tasks": [
    {
      "id": "lint-fix",
      "name": "ESLint 自動修復",
      "prompt_path": ".ralph/prompts/lint-fix.md",
      "priority": 10,
      "max_cost": 5.0,
      "max_duration": "1h",
      "enabled": true,
      "schedule": "0 23 * * 1-5"
    },
    {
      "id": "coverage-boost",
      "name": "測試覆蓋率提升",
      "prompt_path": ".ralph/prompts/coverage-boost.md",
      "priority": 8,
      "max_cost": 20.0,
      "max_duration": "4h",
      "enabled": true,
      "schedule": "0 23 * * 1-5"
    },
    {
      "id": "dep-update",
      "name": "依賴更新",
      "prompt_path": ".ralph/prompts/dep-update.md",
      "priority": 6,
      "max_cost": 10.0,
      "max_duration": "2h",
      "enabled": true,
      "schedule": "0 23 * * 0"
    },
    {
      "id": "doc-gen",
      "name": "文件生成",
      "prompt_path": ".ralph/prompts/doc-gen.md",
      "priority": 4,
      "max_cost": 15.0,
      "max_duration": "3h",
      "enabled": true,
      "schedule": "0 23 * * 5"
    }
  ],
  "global_max_cost": 50.0,
  "global_max_duration": "8h"
}
```

---

## 11.5 安全性與審計

### 11.5.1 安全架構

在企業環境中，安全性是首要考量。我們需要從多個層面保護系統：

```
┌─────────────────────────────────────────────────────────────────┐
│                    安全架構層級                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  第 1 層：存取控制                                       │    │
│  │                                                          │    │
│  │  • API Key 管理（輪換、範圍限制）                        │    │
│  │  • 最小權限原則                                          │    │
│  │  • 基於角色的存取控制 (RBAC)                             │    │
│  │  • 多因素認證 (MFA)                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  第 2 層：執行環境                                       │    │
│  │                                                          │    │
│  │  • 沙箱隔離（Docker/VM）                                 │    │
│  │  • 網路隔離（只能存取必要資源）                          │    │
│  │  • 檔案系統限制（只能存取工作目錄）                      │    │
│  │  • 資源限制（CPU、記憶體、磁碟）                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  第 3 層：輸入/輸出驗證                                  │    │
│  │                                                          │    │
│  │  • 敏感資料過濾（不傳送到 AI API）                       │    │
│  │  • 輸出掃描（惡意程式碼偵測）                            │    │
│  │  • 變更驗證（不超出預期範圍）                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  第 4 層：審計追蹤                                       │    │
│  │                                                          │    │
│  │  • 完整的操作日誌                                        │    │
│  │  • 變更追蹤（Git commit）                                │    │
│  │  • 成本追蹤                                              │    │
│  │  • 異常偵測                                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.5.2 敏感資料保護

```go
package security

import (
    "os"
    "path/filepath"
    "regexp"
    "strings"
)

// ‹1› 敏感資料偵測器
type SensitiveDataDetector struct {
    patterns []SensitivePattern
}

type SensitivePattern struct {
    Name        string
    Pattern     *regexp.Regexp
    Description string
}

// ‹2› 建立偵測器
func NewSensitiveDataDetector() *SensitiveDataDetector {
    return &SensitiveDataDetector{
        patterns: []SensitivePattern{
            {
                Name:        "AWS Access Key",
                Pattern:     regexp.MustCompile(`AKIA[0-9A-Z]{16}`),
                Description: "AWS Access Key ID",
            },
            {
                Name:        "AWS Secret Key",
                Pattern:     regexp.MustCompile(`[A-Za-z0-9/+=]{40}`),
                Description: "AWS Secret Access Key",
            },
            {
                Name:        "Private Key",
                Pattern:     regexp.MustCompile(`-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----`),
                Description: "Private Key File",
            },
            {
                Name:        "API Key",
                Pattern:     regexp.MustCompile(`(?i)(api[_-]?key|apikey)\s*[:=]\s*['""]?[A-Za-z0-9_\-]{20,}`),
                Description: "Generic API Key",
            },
            {
                Name:        "Password",
                Pattern:     regexp.MustCompile(`(?i)(password|passwd|pwd)\s*[:=]\s*['""]?[^\s'"",]+`),
                Description: "Password in code",
            },
            {
                Name:        "JWT Token",
                Pattern:     regexp.MustCompile(`eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*`),
                Description: "JWT Token",
            },
            {
                Name:        "Connection String",
                Pattern:     regexp.MustCompile(`(?i)(mongodb|postgres|mysql|redis):\/\/[^\s]+`),
                Description: "Database Connection String",
            },
        },
    }
}

// ‹3› 掃描內容
func (d *SensitiveDataDetector) ScanContent(content string) []SensitiveMatch {
    var matches []SensitiveMatch

    for _, pattern := range d.patterns {
        found := pattern.Pattern.FindAllStringIndex(content, -1)
        for _, loc := range found {
            matches = append(matches, SensitiveMatch{
                PatternName: pattern.Name,
                StartPos:    loc[0],
                EndPos:      loc[1],
                Preview:     maskContent(content[loc[0]:loc[1]]),
            })
        }
    }

    return matches
}

type SensitiveMatch struct {
    PatternName string
    StartPos    int
    EndPos      int
    Preview     string
}

// ‹4› 遮蔽敏感內容
func maskContent(content string) string {
    if len(content) <= 8 {
        return strings.Repeat("*", len(content))
    }
    return content[:4] + strings.Repeat("*", len(content)-8) + content[len(content)-4:]
}

// ‹5› 掃描檔案
func (d *SensitiveDataDetector) ScanFile(path string) ([]SensitiveMatch, error) {
    content, err := os.ReadFile(path)
    if err != nil {
        return nil, err
    }

    return d.ScanContent(string(content)), nil
}

// ‹6› 掃描目錄
func (d *SensitiveDataDetector) ScanDirectory(root string) (map[string][]SensitiveMatch, error) {
    results := make(map[string][]SensitiveMatch)

    err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
        if err != nil {
            return err
        }

        // 跳過目錄和二進位檔案
        if info.IsDir() || !isTextFile(path) {
            return nil
        }

        // 跳過忽略的路徑
        if shouldIgnore(path) {
            return nil
        }

        matches, err := d.ScanFile(path)
        if err != nil {
            return nil // 繼續掃描其他檔案
        }

        if len(matches) > 0 {
            results[path] = matches
        }

        return nil
    })

    return results, err
}

// ‹7› 檢查是否為文字檔
func isTextFile(path string) bool {
    textExtensions := map[string]bool{
        ".ts": true, ".tsx": true, ".js": true, ".jsx": true,
        ".json": true, ".yaml": true, ".yml": true,
        ".env": true, ".md": true, ".txt": true,
        ".go": true, ".py": true, ".rb": true,
        ".sh": true, ".bash": true,
    }

    ext := filepath.Ext(path)
    return textExtensions[ext]
}

// ‹8› 檢查是否應該忽略
func shouldIgnore(path string) bool {
    ignorePaths := []string{
        "node_modules",
        ".git",
        "vendor",
        "dist",
        "build",
        ".next",
    }

    for _, ignore := range ignorePaths {
        if strings.Contains(path, ignore) {
            return true
        }
    }

    return false
}
```

### 11.5.3 審計日誌

```go
package audit

import (
    "encoding/json"
    "fmt"
    "os"
    "sync"
    "time"
)

// ‹1› 審計事件
type AuditEvent struct {
    Timestamp   time.Time              `json:"timestamp"`
    EventType   string                 `json:"event_type"`
    Actor       string                 `json:"actor"`       // 誰觸發的（user/system/ralph-loop）
    Action      string                 `json:"action"`      // 具體動作
    Resource    string                 `json:"resource"`    // 受影響的資源
    Details     map[string]interface{} `json:"details"`     // 額外資訊
    Outcome     string                 `json:"outcome"`     // success/failure
    RiskLevel   string                 `json:"risk_level"`  // low/medium/high
    SessionID   string                 `json:"session_id"`  // Ralph Loop 會話 ID
}

// ‹2› 審計日誌系統
type AuditLogger struct {
    mu       sync.Mutex
    logFile  *os.File
    filepath string
}

// ‹3› 建立審計日誌系統
func NewAuditLogger(logPath string) (*AuditLogger, error) {
    file, err := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
    if err != nil {
        return nil, err
    }

    return &AuditLogger{
        logFile:  file,
        filepath: logPath,
    }, nil
}

// ‹4› 記錄事件
func (l *AuditLogger) Log(event AuditEvent) error {
    l.mu.Lock()
    defer l.mu.Unlock()

    event.Timestamp = time.Now().UTC()

    data, err := json.Marshal(event)
    if err != nil {
        return err
    }

    _, err = l.logFile.WriteString(string(data) + "\n")
    return err
}

// ‹5› 預定義事件類型
const (
    EventTypeFileRead    = "file_read"
    EventTypeFileWrite   = "file_write"
    EventTypeFileDelete  = "file_delete"
    EventTypeBashCommand = "bash_command"
    EventTypeAPICall     = "api_call"
    EventTypeIteration   = "iteration"
    EventTypeCompletion  = "completion"
    EventTypeError       = "error"
)

// ‹6› 便捷方法
func (l *AuditLogger) LogFileWrite(sessionID, path string, linesChanged int) error {
    return l.Log(AuditEvent{
        EventType: EventTypeFileWrite,
        Actor:     "ralph-loop",
        Action:    "write_file",
        Resource:  path,
        Details: map[string]interface{}{
            "lines_changed": linesChanged,
        },
        Outcome:   "success",
        RiskLevel: classifyFileRisk(path),
        SessionID: sessionID,
    })
}

func (l *AuditLogger) LogBashCommand(sessionID, command string, exitCode int) error {
    return l.Log(AuditEvent{
        EventType: EventTypeBashCommand,
        Actor:     "ralph-loop",
        Action:    "execute_command",
        Resource:  command,
        Details: map[string]interface{}{
            "exit_code": exitCode,
        },
        Outcome:   outcomeFromExitCode(exitCode),
        RiskLevel: classifyCommandRisk(command),
        SessionID: sessionID,
    })
}

func (l *AuditLogger) LogIteration(sessionID string, iteration int, tokens int64, cost float64) error {
    return l.Log(AuditEvent{
        EventType: EventTypeIteration,
        Actor:     "ralph-loop",
        Action:    "iteration",
        Resource:  fmt.Sprintf("iteration-%d", iteration),
        Details: map[string]interface{}{
            "iteration":   iteration,
            "tokens_used": tokens,
            "cost":        cost,
        },
        Outcome:   "success",
        RiskLevel: "low",
        SessionID: sessionID,
    })
}

// ‹7› 風險分類
func classifyFileRisk(path string) string {
    highRiskPatterns := []string{
        ".env", "credentials", "secrets", ".pem", ".key",
    }

    for _, pattern := range highRiskPatterns {
        if contains(path, pattern) {
            return "high"
        }
    }

    mediumRiskPatterns := []string{
        "config", "settings", "package.json",
    }

    for _, pattern := range mediumRiskPatterns {
        if contains(path, pattern) {
            return "medium"
        }
    }

    return "low"
}

func classifyCommandRisk(command string) string {
    highRiskCommands := []string{
        "rm -rf", "sudo", "chmod 777", "curl | sh",
        "eval", "exec", "kill -9",
    }

    for _, pattern := range highRiskCommands {
        if contains(command, pattern) {
            return "high"
        }
    }

    return "low"
}
```

---

## 11.6 團隊協作工作流

### 11.6.1 共享模板庫

```
┌─────────────────────────────────────────────────────────────────┐
│                    團隊模板庫結構                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  .ralph/                                                        │
│  ├── prompts/                    # 團隊共享的提示詞模板         │
│  │   ├── migration/                                             │
│  │   │   ├── jest-to-vitest.md                                 │
│  │   │   ├── class-to-function.md                              │
│  │   │   └── commonjs-to-esm.md                                │
│  │   ├── quality/                                               │
│  │   │   ├── coverage-boost.md                                 │
│  │   │   ├── lint-fix.md                                       │
│  │   │   └── type-strict.md                                    │
│  │   ├── maintenance/                                           │
│  │   │   ├── dep-update.md                                     │
│  │   │   ├── security-patch.md                                 │
│  │   │   └── deprecation-fix.md                                │
│  │   └── documentation/                                         │
│  │       ├── jsdoc-gen.md                                      │
│  │       ├── readme-update.md                                  │
│  │       └── api-docs.md                                       │
│  │                                                              │
│  ├── configs/                    # 配置檔案                     │
│  │   ├── night-factory.json                                    │
│  │   ├── permissions.json                                      │
│  │   └── cost-limits.json                                      │
│  │                                                              │
│  ├── hooks/                      # Git hooks 整合               │
│  │   ├── pre-commit                                            │
│  │   └── post-merge                                            │
│  │                                                              │
│  └── reports/                    # 執行報告                     │
│      └── .gitkeep                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.6.2 Pull Request 整合

```go
package pr

import (
    "context"
    "fmt"
    "strings"
)

// ‹1› PR 建立器
type PRCreator struct {
    ProjectRoot string
    GitHubToken string
    RepoOwner   string
    RepoName    string
}

// ‹2› 為 Ralph Loop 結果建立 PR
func (c *PRCreator) CreatePR(ctx context.Context, result RalphResult) (*PullRequest, error) {
    // 建立分支
    branchName := fmt.Sprintf("ralph/%s-%s", result.TaskType, result.SessionID[:8])

    if err := c.createBranch(branchName); err != nil {
        return nil, err
    }

    // 提交變更
    if err := c.commitChanges(result); err != nil {
        return nil, err
    }

    // 推送分支
    if err := c.pushBranch(branchName); err != nil {
        return nil, err
    }

    // 建立 PR
    pr, err := c.createGitHubPR(ctx, branchName, result)
    if err != nil {
        return nil, err
    }

    return pr, nil
}

// ‹3› 生成 PR 描述
func (c *PRCreator) generatePRDescription(result RalphResult) string {
    var sb strings.Builder

    sb.WriteString("## Summary\n\n")
    sb.WriteString(fmt.Sprintf("This PR was generated by Ralph Loop for task: **%s**\n\n", result.TaskType))

    sb.WriteString("## Changes\n\n")
    sb.WriteString(fmt.Sprintf("- Files modified: %d\n", len(result.ModifiedFiles)))
    sb.WriteString(fmt.Sprintf("- Iterations: %d\n", result.Iterations))
    sb.WriteString(fmt.Sprintf("- Total cost: $%.2f\n\n", result.Cost))

    sb.WriteString("## Modified Files\n\n")
    for _, file := range result.ModifiedFiles {
        sb.WriteString(fmt.Sprintf("- `%s`\n", file))
    }

    sb.WriteString("\n## Verification\n\n")
    sb.WriteString("- [ ] Code review completed\n")
    sb.WriteString("- [ ] Tests pass\n")
    sb.WriteString("- [ ] No security issues\n")

    sb.WriteString("\n---\n")
    sb.WriteString("*Generated by Ralph Loop*\n")

    return sb.String()
}

// ‹4› PR 審查清單
type PRReviewChecklist struct {
    CodeQuality      bool
    TestsPassing     bool
    NoSecurityIssues bool
    NoRegressions    bool
    DocumentationOK  bool
}

func (c *PRReviewChecklist) IsApproved() bool {
    return c.CodeQuality && c.TestsPassing && c.NoSecurityIssues &&
           c.NoRegressions && c.DocumentationOK
}
```

### 11.6.3 CI/CD 整合

```yaml
# .github/workflows/ralph-loop.yml
name: Ralph Loop CI

on:
  push:
    branches:
      - 'ralph/**'
  workflow_dispatch:
    inputs:
      task:
        description: 'Task to run'
        required: true
        type: choice
        options:
          - coverage-boost
          - lint-fix
          - dep-update

jobs:
  validate:
    name: Validate Ralph Changes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Check code coverage
        run: npm run coverage

      - name: Security scan
        run: npm audit --audit-level=high

      - name: Lint check
        run: npm run lint

  security-review:
    name: Security Review
    runs-on: ubuntu-latest
    needs: validate
    steps:
      - uses: actions/checkout@v4

      - name: Check for sensitive data
        run: |
          # 使用 trufflehog 或類似工具掃描敏感資料
          docker run --rm -v "$(pwd):/repo" trufflesecurity/trufflehog:latest \
            filesystem /repo --fail

      - name: Static analysis
        run: |
          # 使用 semgrep 進行靜態分析
          docker run --rm -v "$(pwd):/src" returntocorp/semgrep:latest \
            semgrep --config=auto /src

  auto-merge:
    name: Auto Merge (if approved)
    runs-on: ubuntu-latest
    needs: [validate, security-review]
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/heads/ralph/')
    steps:
      - name: Auto-approve for low-risk changes
        uses: hmarr/auto-approve-action@v3
        if: ${{ needs.security-review.outputs.risk_level == 'low' }}
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Enable auto-merge
        uses: peter-evans/enable-pull-request-automerge@v3
        if: ${{ needs.security-review.outputs.risk_level == 'low' }}
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          merge-method: squash
```

---

## 11.7 本章小結

本章我們探討了 Ralph Loop 在企業環境中的應用模式：

**企業級挑戰**：
- 多利害關係人的平衡
- 規模與複雜度的管理
- 合規與審計的要求

**大規模遷移**：
- Jest 到 Vitest 遷移案例
- 分階段執行策略
- 批次協調器實現

**測試覆蓋率提升**：
- 自動化識別低覆蓋區域
- 有意義的測試生成
- 進度監控與報告

**夜間工廠模式**：
- 利用非工作時間
- 任務排程與優先級
- 成本與時間控制

**安全與審計**：
- 敏感資料保護
- 完整的審計追蹤
- 多層安全架構

**團隊協作**：
- 共享模板庫
- PR 整合工作流
- CI/CD 自動化

---

## 練習題

### 練習 11.1：遷移策略設計

你的團隊需要將一個 100,000 行的 JavaScript 專案從 CommonJS 遷移到 ES Modules。

**問題**：
1. 設計分階段遷移策略
2. 寫出核心的 PROMPT.md
3. 如何設計收斂條件？
4. 預估成本和時間

### 練習 11.2：夜間工廠配置

設計一個夜間工廠配置，處理以下任務：
- 每日：Lint 修復、測試覆蓋率提升
- 每週：依賴更新、安全掃描
- 每月：文件更新、廢棄 API 清理

### 練習 11.3：安全審計

你的團隊計劃在 CI/CD 中整合 Ralph Loop。設計一個安全審計框架，包括：
1. 敏感資料偵測規則
2. 變更範圍限制
3. 審計日誌格式
4. 異常偵測邏輯

---

## 延伸閱讀

1. **企業級 DevOps**
   - "Continuous Delivery" by Jez Humble (2010)
   - "Accelerate" by Nicole Forsgren (2018)

2. **安全最佳實踐**
   - OWASP Secure Coding Practices
   - SOC 2 Type II Compliance Guide

3. **自動化測試**
   - "Test Driven Development" by Kent Beck (2002)
   - "Growing Object-Oriented Software" by Steve Freeman (2009)

---

## 下一章預告

本書的最後一章將展望未來：Subagents 架構如何解決 Context 溢出問題、KTLO 自動化的「Roomba 夢想」，以及 Human-on-the-Loop 模式的發展。我們將探討 2027 年的技術地圖，幫助你規劃未來的學習路徑。
