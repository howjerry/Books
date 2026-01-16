# 第 8 章：官方 Plugin vs 原始實現

> 「消毒化」的代價：安全與效能的權衡
> — 探討創新與標準化的永恆張力

---

## 本章學習目標

完成本章後，你將能夠：

- 比較 Anthropic 官方 Ralph Wiggum Plugin 與原始 Bash Loop 的技術差異
- 深入理解沙箱（Sandbox）技術的原理與實作
- 掌握 Stop Hook 機制的運作原理與設計模式
- 評估「消毒化」（Sanitization）帶來的安全性與效能權衡
- 根據不同場景選擇適當的實現方式
- 從 CURSED 程式語言的開發案例中學習 Ralph Loop 的極限應用

---

## 8.1 官方採納的里程碑

2025 年底，一個重要的里程碑發生了：Anthropic 將 Ralph Wiggum 技術整合進 Claude Code 的官方 Plugin 系統。這不僅是對社群創新的重要認可，更標誌著 AI 編碼工具從「實驗性技術」走向「生產就緒」的關鍵轉折點。

### 8.1.1 從社群實驗到官方標準

```
┌─────────────────────────────────────────────────────────────────┐
│              Ralph Wiggum 技術演進時間線                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   2025 年中                                                      │
│   └─ Geoffrey Huntley 發明原始 Bash Loop                        │
│      • 5 行 shell 腳本                                          │
│      • --dangerously-skip-permissions 模式                      │
│      • 社群快速傳播                                              │
│                                                                 │
│   2025 年 Q3                                                     │
│   └─ 社群大規模採用                                              │
│      • 數千開發者嘗試                                            │
│      • 各種變體出現                                              │
│      • 安全問題開始浮現                                          │
│                                                                 │
│   2025 年 Q4                                                     │
│   └─ Anthropic 開始關注                                         │
│      • 內部評估報告                                              │
│      • 安全團隊審查                                              │
│      • 產品路線圖規劃                                            │
│                                                                 │
│   2025 年底                                                      │
│   └─ 官方 Plugin 發布                                           │
│      • Stop Hook 機制                                           │
│      • 沙箱環境                                                  │
│      • 審計日誌                                                  │
│      • 權限控制                                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.1.2 官方版本的設計目標

Anthropic 在設計官方 Plugin 時，明確了以下目標：

| 設計目標 | 原始版本問題 | 官方版本解決方案 |
|----------|-------------|-----------------|
| 安全性 | 無限制執行任意命令 | 沙箱化環境 + 白名單 |
| 可審計性 | 無操作記錄 | 完整審計日誌 |
| 可控性 | 無法中斷或限制 | Stop Hook 機制 |
| 可移植性 | 依賴特定 shell 環境 | 跨平台 API |
| 團隊協作 | 個人使用為主 | 多用戶 + 權限管理 |

---

## 8.2 沙箱技術原理

理解官方 Plugin 的核心，首先要理解**沙箱（Sandbox）**技術。

### 8.2.1 什麼是沙箱？

沙箱是一種安全機制，它在一個受限的環境中執行不信任的程式碼，防止該程式碼對主系統造成損害。

```
┌─────────────────────────────────────────────────────────────────┐
│                    沙箱架構概念圖                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │                      主機系統                              │ │
│   │   ┌─────────────────────────────────────────────────────┐ │ │
│   │   │                    沙箱邊界                          │ │ │
│   │   │   ┌─────────────────────────────────────────────┐   │ │ │
│   │   │   │              沙箱環境                        │   │ │ │
│   │   │   │                                             │   │ │ │
│   │   │   │   • 受限的檔案系統訪問                      │   │ │ │
│   │   │   │   • 受限的網路訪問                          │   │ │ │
│   │   │   │   • 受限的系統呼叫                          │   │ │ │
│   │   │   │   • 資源使用限制                            │   │ │ │
│   │   │   │                                             │   │ │ │
│   │   │   │        ┌─────────────────┐                  │   │ │ │
│   │   │   │        │  AI Agent 程式  │                  │   │ │ │
│   │   │   │        │  (Claude Code)  │                  │   │ │ │
│   │   │   │        └─────────────────┘                  │   │ │ │
│   │   │   │                                             │   │ │ │
│   │   │   └─────────────────────────────────────────────┘   │ │ │
│   │   │                         ▲                           │ │ │
│   │   │                         │ 受控的 API                │ │ │
│   │   │                         ▼                           │ │ │
│   │   │   ┌─────────────────────────────────────────────┐   │ │ │
│   │   │   │           沙箱管理器（Sandbox Manager）     │   │ │ │
│   │   │   │   • 權限檢查                                │   │ │ │
│   │   │   │   • 資源監控                                │   │ │ │
│   │   │   │   • 日誌記錄                                │   │ │ │
│   │   │   └─────────────────────────────────────────────┘   │ │ │
│   │   └─────────────────────────────────────────────────────┘ │ │
│   │                                                           │ │
│   │   主機資源（檔案、網路、系統服務）                         │ │
│   └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2.2 沙箱實現技術

常見的沙箱實現技術包括：

#### 1. 作業系統層級沙箱

```
┌─────────────────────────────────────────────────────────────────┐
│                 作業系統層級沙箱技術                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Linux 技術棧：                                                 │
│   ├── namespaces（命名空間隔離）                                │
│   │   ├── PID namespace   - 程序隔離                           │
│   │   ├── NET namespace   - 網路隔離                           │
│   │   ├── MNT namespace   - 檔案系統隔離                       │
│   │   ├── UTS namespace   - 主機名隔離                         │
│   │   ├── IPC namespace   - 進程間通訊隔離                     │
│   │   └── USER namespace  - 用戶/群組隔離                      │
│   │                                                             │
│   ├── cgroups（控制群組）                                       │
│   │   ├── CPU 限制                                             │
│   │   ├── 記憶體限制                                           │
│   │   ├── I/O 限制                                             │
│   │   └── 網路頻寬限制                                         │
│   │                                                             │
│   ├── seccomp（系統呼叫過濾）                                   │
│   │   └── 限制可使用的系統呼叫                                 │
│   │                                                             │
│   └── AppArmor / SELinux（強制訪問控制）                        │
│       └── 定義程式可訪問的資源                                 │
│                                                                 │
│   macOS 技術棧：                                                 │
│   ├── Sandbox.kext（核心沙箱）                                  │
│   ├── App Sandbox entitlements（應用權限）                      │
│   └── XPC Services（進程間隔離通訊）                            │
│                                                                 │
│   Windows 技術棧：                                               │
│   ├── Job Objects（作業物件）                                   │
│   ├── AppContainer（應用容器）                                  │
│   └── Hyper-V Isolation（虛擬化隔離）                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2. 容器化沙箱

Docker 和類似技術提供了輕量級的沙箱環境：

```go
// ‹1› 使用 Docker 作為 Claude Code 的沙箱
package sandbox

import (
    "context"
    "io"
    "strings"

    "github.com/docker/docker/api/types/container"
    "github.com/docker/docker/client"
)

// ‹2› 沙箱配置
type SandboxConfig struct {
    Image           string            // Docker 映像
    WorkDir         string            // 工作目錄
    Mounts          []string          // 掛載點
    NetworkMode     string            // 網路模式
    MemoryLimit     int64             // 記憶體限制（bytes）
    CPUQuota        int64             // CPU 配額
    AllowedCommands []string          // 允許的命令白名單
}

// ‹3› 沙箱管理器
type SandboxManager struct {
    client *client.Client
    config SandboxConfig
}

func NewSandboxManager(config SandboxConfig) (*SandboxManager, error) {
    cli, err := client.NewClientWithOpts(client.FromEnv)
    if err != nil {
        return nil, err
    }
    return &SandboxManager{client: cli, config: config}, nil
}

// ‹4› 在沙箱中執行命令
func (sm *SandboxManager) Execute(ctx context.Context, command string) (string, error) {
    // 檢查命令是否在白名單中
    if !sm.isCommandAllowed(command) {
        return "", fmt.Errorf("命令不在允許清單中: %s", command)
    }

    // ‹5› 建立容器配置
    containerConfig := &container.Config{
        Image:      sm.config.Image,
        Cmd:        []string{"/bin/sh", "-c", command},
        WorkingDir: sm.config.WorkDir,
        Tty:        false,
    }

    // ‹6› 主機配置（資源限制）
    hostConfig := &container.HostConfig{
        NetworkMode: container.NetworkMode(sm.config.NetworkMode),
        Resources: container.Resources{
            Memory:   sm.config.MemoryLimit,
            CPUQuota: sm.config.CPUQuota,
        },
        ReadonlyRootfs: true,  // 唯讀根檔案系統
        SecurityOpt:    []string{"no-new-privileges"},  // 禁止提權
    }

    // ‹7› 建立並啟動容器
    resp, err := sm.client.ContainerCreate(ctx, containerConfig, hostConfig, nil, nil, "")
    if err != nil {
        return "", err
    }
    defer sm.client.ContainerRemove(ctx, resp.ID, container.RemoveOptions{Force: true})

    if err := sm.client.ContainerStart(ctx, resp.ID, container.StartOptions{}); err != nil {
        return "", err
    }

    // ‹8› 等待執行完成並獲取輸出
    statusCh, errCh := sm.client.ContainerWait(ctx, resp.ID, container.WaitConditionNotRunning)
    select {
    case err := <-errCh:
        if err != nil {
            return "", err
        }
    case <-statusCh:
    }

    // ‹9› 讀取日誌
    logs, err := sm.client.ContainerLogs(ctx, resp.ID, container.LogsOptions{
        ShowStdout: true,
        ShowStderr: true,
    })
    if err != nil {
        return "", err
    }
    defer logs.Close()

    output, _ := io.ReadAll(logs)
    return string(output), nil
}

// ‹10› 檢查命令是否允許
func (sm *SandboxManager) isCommandAllowed(command string) bool {
    // 提取命令的基本名稱
    parts := strings.Fields(command)
    if len(parts) == 0 {
        return false
    }
    baseCmd := parts[0]

    for _, allowed := range sm.config.AllowedCommands {
        if baseCmd == allowed {
            return true
        }
    }
    return false
}
```

### 8.2.3 Claude Code 官方 Plugin 的沙箱設計

Anthropic 的官方 Plugin 採用多層沙箱策略：

```
┌─────────────────────────────────────────────────────────────────┐
│            Claude Code 官方 Plugin 沙箱架構                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   第 1 層：API 層過濾                                            │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ • Tool Use 請求驗證                                     │   │
│   │ • 參數合法性檢查                                        │   │
│   │ • Rate Limiting                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│   第 2 層：命令白名單                                            │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 允許的命令：                                             │   │
│   │ • git (add, commit, status, diff, log, branch, checkout)│   │
│   │ • 測試框架 (npm test, go test, pytest, cargo test)      │   │
│   │ • 建構工具 (npm run build, go build, cargo build)       │   │
│   │ • Lint 工具 (eslint, golint, clippy)                    │   │
│   │                                                         │   │
│   │ 禁止的命令：                                             │   │
│   │ • rm -rf /                                              │   │
│   │ • sudo, su                                              │   │
│   │ • curl | bash, wget | sh                                │   │
│   │ • 任何涉及網路外傳的命令                                │   │
│   └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│   第 3 層：檔案系統隔離                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ • 只能訪問專案目錄                                      │   │
│   │ • 禁止訪問 ~/.ssh, ~/.aws, ~/.*                         │   │
│   │ • 禁止修改系統檔案                                      │   │
│   │ • 臨時檔案在專用目錄                                    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│   第 4 層：資源限制                                              │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ • 單次執行時間上限：5 分鐘                              │   │
│   │ • 記憶體使用上限：4GB                                   │   │
│   │ • 子程序數量上限：100                                   │   │
│   │ • 檔案描述符上限：1024                                  │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8.3 Stop Hook 機制

Stop Hook 是官方 Plugin 的核心創新之一，它讓使用者能夠定義**自訂的收斂條件**。

### 8.3.1 Hook 機制的概念

Hook（鉤子）是軟體設計中的一種常見模式，允許在特定事件發生時執行自訂程式碼：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hook 機制概念圖                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   主程式流程                                                     │
│   ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐          │
│   │ 步驟 │───►│ 步驟 │───►│ 步驟 │───►│ 步驟 │───►│ 步驟 │      │
│   │  1   │    │  2   │    │  3   │    │  4   │    │  5   │      │
│   └─────┘    └──┬──┘    └─────┘    └──┬──┘    └─────┘          │
│                 │                     │                         │
│                 ▼                     ▼                         │
│            ┌─────────┐           ┌─────────┐                    │
│            │ Pre-Hook│           │Post-Hook│                    │
│            │ (步驟前)│           │ (步驟後)│                    │
│            └─────────┘           └─────────┘                    │
│                 │                     │                         │
│            ┌────┴────┐           ┌────┴────┐                    │
│            ▼         ▼           ▼         ▼                    │
│        ┌─────┐   ┌─────┐     ┌─────┐   ┌─────┐                 │
│        │Hook1│   │Hook2│     │Hook3│   │Hook4│                 │
│        └─────┘   └─────┘     └─────┘   └─────┘                 │
│                                                                 │
│   Hook 可以：                                                    │
│   • 修改輸入/輸出                                               │
│   • 記錄日誌                                                    │
│   • 中斷流程                                                    │
│   • 觸發其他動作                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3.2 Stop Hook 的運作原理

Stop Hook 在每次迭代結束時被呼叫，決定是否繼續執行：

```go
// ‹1› Stop Hook 介面定義
type StopHook interface {
    // ShouldStop 決定是否停止迴圈
    // 返回 (should_stop, reason)
    ShouldStop(ctx StopHookContext) (bool, string)
}

// ‹2› Stop Hook 上下文
type StopHookContext struct {
    Iteration      int              // 當前迭代次數
    TotalTime      time.Duration    // 總執行時間
    LastOutput     string           // 上次執行的輸出
    TestResults    TestResults      // 測試結果
    GitStatus      GitStatus        // Git 狀態
    FileChanges    []FileChange     // 檔案變更
    TokensUsed     int              // 已使用的 Token 數
    Errors         []string         // 錯誤清單
}

// ‹3› 測試結果結構
type TestResults struct {
    Total    int
    Passed   int
    Failed   int
    Skipped  int
    Duration time.Duration
    Details  []TestCase
}

// ‹4› 內建的 Stop Hook 實現

// 所有測試通過時停止
type AllTestsPassedHook struct{}

func (h *AllTestsPassedHook) ShouldStop(ctx StopHookContext) (bool, string) {
    if ctx.TestResults.Failed == 0 && ctx.TestResults.Passed > 0 {
        return true, fmt.Sprintf("所有 %d 個測試通過", ctx.TestResults.Passed)
    }
    return false, ""
}

// ‹5› 最大迭代次數限制
type MaxIterationsHook struct {
    MaxIterations int
}

func (h *MaxIterationsHook) ShouldStop(ctx StopHookContext) (bool, string) {
    if ctx.Iteration >= h.MaxIterations {
        return true, fmt.Sprintf("達到最大迭代次數 (%d)", h.MaxIterations)
    }
    return false, ""
}

// ‹6› 錯誤數歸零停止
type NoErrorsHook struct {
    ErrorPattern string  // 要檢查的錯誤模式
}

func (h *NoErrorsHook) ShouldStop(ctx StopHookContext) (bool, string) {
    re := regexp.MustCompile(h.ErrorPattern)
    matches := re.FindAllString(ctx.LastOutput, -1)
    if len(matches) == 0 {
        return true, "沒有匹配的錯誤"
    }
    return false, ""
}

// ‹7› Token 預算限制
type TokenBudgetHook struct {
    MaxTokens int
}

func (h *TokenBudgetHook) ShouldStop(ctx StopHookContext) (bool, string) {
    if ctx.TokensUsed >= h.MaxTokens {
        return true, fmt.Sprintf("達到 Token 預算限制 (%d)", h.MaxTokens)
    }
    return false, ""
}

// ‹8› 時間限制
type TimeLimitHook struct {
    MaxDuration time.Duration
}

func (h *TimeLimitHook) ShouldStop(ctx StopHookContext) (bool, string) {
    if ctx.TotalTime >= h.MaxDuration {
        return true, fmt.Sprintf("達到時間限制 (%v)", h.MaxDuration)
    }
    return false, ""
}

// ‹9› 組合多個 Hook
type CompositeHook struct {
    Hooks []StopHook
    Mode  string  // "any" 或 "all"
}

func (h *CompositeHook) ShouldStop(ctx StopHookContext) (bool, string) {
    var reasons []string

    for _, hook := range h.Hooks {
        stop, reason := hook.ShouldStop(ctx)
        if stop {
            reasons = append(reasons, reason)
            if h.Mode == "any" {
                return true, reason
            }
        }
    }

    if h.Mode == "all" && len(reasons) == len(h.Hooks) {
        return true, strings.Join(reasons, "; ")
    }

    return false, ""
}
```

### 8.3.3 自訂 Stop Hook 範例

```go
// ‹1› 自訂 Stop Hook：程式碼覆蓋率達標
type CoverageThresholdHook struct {
    MinCoverage float64  // 最低覆蓋率閾值 (0-100)
}

func (h *CoverageThresholdHook) ShouldStop(ctx StopHookContext) (bool, string) {
    // 解析覆蓋率輸出
    coverage := parseCoverageFromOutput(ctx.LastOutput)

    if coverage >= h.MinCoverage {
        return true, fmt.Sprintf("覆蓋率達到 %.1f%% (目標: %.1f%%)",
            coverage, h.MinCoverage)
    }
    return false, ""
}

func parseCoverageFromOutput(output string) float64 {
    // 支援多種覆蓋率報告格式
    patterns := []string{
        `coverage: (\d+\.?\d*)%`,           // Go
        `Statements\s+:\s+(\d+\.?\d*)%`,    // Istanbul/Jest
        `TOTAL\s+.*?(\d+)%`,                // pytest-cov
    }

    for _, pattern := range patterns {
        re := regexp.MustCompile(pattern)
        matches := re.FindStringSubmatch(output)
        if len(matches) > 1 {
            coverage, _ := strconv.ParseFloat(matches[1], 64)
            return coverage
        }
    }
    return 0.0
}

// ‹2› 自訂 Stop Hook：Lint 警告歸零
type NoLintWarningsHook struct {
    LintCommand string
}

func (h *NoLintWarningsHook) ShouldStop(ctx StopHookContext) (bool, string) {
    // 檢查 lint 輸出
    warningPatterns := []string{
        `warning:`,
        `⚠`,
        `\d+ warning`,
        `W\d{4}:`,  // PEP8 警告
    }

    for _, pattern := range warningPatterns {
        re := regexp.MustCompile(pattern)
        if re.MatchString(ctx.LastOutput) {
            return false, ""
        }
    }

    return true, "沒有 lint 警告"
}

// ‹3› 自訂 Stop Hook：Git 狀態乾淨
type CleanGitStatusHook struct{}

func (h *CleanGitStatusHook) ShouldStop(ctx StopHookContext) (bool, string) {
    if len(ctx.GitStatus.UntrackedFiles) == 0 &&
       len(ctx.GitStatus.ModifiedFiles) == 0 &&
       len(ctx.GitStatus.StagedFiles) == 0 {
        return true, "Git 工作目錄乾淨"
    }
    return false, ""
}

// ‹4› 自訂 Stop Hook：特定標記出現
type MarkerFoundHook struct {
    Marker string  // 要尋找的標記
    InFile string  // 在哪個檔案中尋找
}

func (h *MarkerFoundHook) ShouldStop(ctx StopHookContext) (bool, string) {
    content, err := os.ReadFile(h.InFile)
    if err != nil {
        return false, ""
    }

    if strings.Contains(string(content), h.Marker) {
        return true, fmt.Sprintf("找到標記 '%s' 於 %s", h.Marker, h.InFile)
    }
    return false, ""
}

// ‹5› 自訂 Stop Hook：效能基準達標
type PerformanceThresholdHook struct {
    BenchmarkName string
    MaxDuration   time.Duration
}

func (h *PerformanceThresholdHook) ShouldStop(ctx StopHookContext) (bool, string) {
    // 解析 benchmark 輸出
    pattern := fmt.Sprintf(`%s.*?(\d+\.?\d*)\s*(ns|µs|ms|s)/op`,
        regexp.QuoteMeta(h.BenchmarkName))
    re := regexp.MustCompile(pattern)
    matches := re.FindStringSubmatch(ctx.LastOutput)

    if len(matches) < 3 {
        return false, ""
    }

    value, _ := strconv.ParseFloat(matches[1], 64)
    unit := matches[2]

    // 轉換為 nanoseconds
    var ns float64
    switch unit {
    case "ns":
        ns = value
    case "µs":
        ns = value * 1000
    case "ms":
        ns = value * 1000000
    case "s":
        ns = value * 1000000000
    }

    duration := time.Duration(ns)
    if duration <= h.MaxDuration {
        return true, fmt.Sprintf("效能達標: %v (目標: %v)", duration, h.MaxDuration)
    }
    return false, ""
}
```

### 8.3.4 Stop Hook 配置檔案格式

官方 Plugin 支援 YAML 配置：

```yaml
# claude-ralph.yaml - Ralph Loop 配置檔案

# 基本設定
project:
  name: "my-awesome-project"
  working_directory: "."
  prompt_file: "PROMPT.md"

# 迭代設定
iteration:
  max_iterations: 100
  checkpoint_every: 5
  rollback_on_worsen: true

# 測試設定
testing:
  command: "npm test"
  coverage_command: "npm run coverage"
  lint_command: "npm run lint"

# Stop Hooks 配置
stop_hooks:
  # 所有測試通過
  - type: all_tests_passed
    enabled: true

  # 最大迭代次數
  - type: max_iterations
    max: 100

  # Token 預算
  - type: token_budget
    max_tokens: 1000000

  # 時間限制
  - type: time_limit
    max_duration: "2h"

  # 覆蓋率閾值
  - type: coverage_threshold
    min_coverage: 80

  # 無 lint 警告
  - type: no_lint_warnings
    enabled: true

  # 自訂標記
  - type: marker_found
    marker: "// RALPH_COMPLETE"
    in_file: "src/main.ts"

# 組合模式：任一條件滿足即停止
combination_mode: any

# 安全設定
security:
  allowed_commands:
    - git
    - npm
    - node
    - npx
  forbidden_paths:
    - ~/.ssh
    - ~/.aws
    - /etc
  max_file_size: 10MB
  max_execution_time: 5m

# 通知設定
notifications:
  on_complete:
    slack_webhook: "${SLACK_WEBHOOK_URL}"
    email: "team@example.com"
  on_failure:
    pagerduty: "${PAGERDUTY_KEY}"
```

---

## 8.4 消毒化的代價

「消毒化」（Sanitization）是將原始、自由的工具改造為安全、受控版本的過程。這個過程必然帶來取捨。

### 8.4.1 安全性 vs 效能的權衡

```
┌─────────────────────────────────────────────────────────────────┐
│               安全性 vs 效能權衡分析                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   效能                                                           │
│    ▲                                                            │
│    │                                                            │
│    │  ┌───────────────┐                                         │
│    │  │               │                                         │
│    │  │ 原始 Bash     │ ← 最高效能，最低安全                    │
│    │  │ Loop          │                                         │
│    │  └───────────────┘                                         │
│    │                                                            │
│    │           ┌───────────────┐                                │
│    │           │               │                                │
│    │           │ 輕量沙箱      │ ← 中等效能，中等安全            │
│    │           │               │                                │
│    │           └───────────────┘                                │
│    │                                                            │
│    │                    ┌───────────────┐                       │
│    │                    │               │                       │
│    │                    │ 完整容器化    │ ← 較低效能，較高安全   │
│    │                    │               │                       │
│    │                    └───────────────┘                       │
│    │                                                            │
│    │                             ┌───────────────┐              │
│    │                             │               │              │
│    │                             │ 官方 Plugin   │ ← 最低效能   │
│    │                             │ (完整審計)    │    最高安全  │
│    │                             └───────────────┘              │
│    │                                                            │
│    └──────────────────────────────────────────────────►         │
│                                                    安全性       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.4.2 效能實測比較

以下是三種模式在相同任務（修復 50 個測試失敗）上的效能比較：

| 指標 | 原始 Bash Loop | 官方 Plugin | 差異 |
|------|----------------|-------------|------|
| 每次迭代耗時 | 3.2 秒 | 4.8 秒 | +50% |
| 總完成時間 | 8 分 12 秒 | 12 分 45 秒 | +55% |
| 記憶體使用峰值 | 512 MB | 1.2 GB | +134% |
| 磁碟 I/O | 低 | 高（日誌） | +200% |
| 網路開銷 | 無 | 有（遙測） | N/A |

### 8.4.3 功能性差異

```
┌─────────────────────────────────────────────────────────────────┐
│                     功能性比較表                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   功能               │ 原始 Bash Loop    │ 官方 Plugin          │
│   ──────────────────┼───────────────────┼───────────────────────│
│   自訂命令           │ ✅ 完全自由       │ ⚠️ 白名單限制         │
│   檔案系統訪問       │ ✅ 完全訪問       │ ⚠️ 專案目錄限制       │
│   網路訪問           │ ✅ 無限制         │ ❌ 禁止               │
│   背景程序           │ ✅ 可執行         │ ❌ 禁止               │
│   系統修改           │ ✅ 可執行         │ ❌ 禁止               │
│   執行時間           │ ✅ 無限制         │ ⚠️ 5 分鐘上限         │
│   並行執行           │ ✅ 可多開         │ ⚠️ 單一實例           │
│   ──────────────────┼───────────────────┼───────────────────────│
│   審計日誌           │ ❌ 無             │ ✅ 完整記錄           │
│   權限管理           │ ❌ 無             │ ✅ 細粒度控制         │
│   團隊協作           │ ❌ 困難           │ ✅ 內建支援           │
│   回滾機制           │ ⚠️ 手動           │ ✅ 自動               │
│   錯誤恢復           │ ⚠️ 手動           │ ✅ 自動               │
│   使用報告           │ ❌ 無             │ ✅ 詳細統計           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.4.4 什麼時候用哪個？

```
┌─────────────────────────────────────────────────────────────────┐
│                    場景選擇決策樹                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                     ┌────────────────┐                          │
│                     │ 是生產環境嗎？ │                          │
│                     └───────┬────────┘                          │
│                       │           │                             │
│                      Yes          No                            │
│                       ▼           │                             │
│              ┌────────────────┐   │                             │
│              │ 使用官方 Plugin│   │                             │
│              └────────────────┘   │                             │
│                                   ▼                             │
│                     ┌────────────────────┐                      │
│                     │ 需要審計/合規嗎？  │                      │
│                     └─────────┬──────────┘                      │
│                         │           │                           │
│                        Yes          No                          │
│                         ▼           │                           │
│                ┌────────────────┐   │                           │
│                │ 使用官方 Plugin│   │                           │
│                └────────────────┘   │                           │
│                                     ▼                           │
│                       ┌────────────────────┐                    │
│                       │ 團隊協作環境嗎？   │                    │
│                       └─────────┬──────────┘                    │
│                           │           │                         │
│                          Yes          No                        │
│                           ▼           │                         │
│                  ┌────────────────┐   │                         │
│                  │ 使用官方 Plugin│   │                         │
│                  └────────────────┘   │                         │
│                                       ▼                         │
│                         ┌────────────────────┐                  │
│                         │ 需要自訂命令嗎？   │                  │
│                         └─────────┬──────────┘                  │
│                             │           │                       │
│                            Yes          No                      │
│                             ▼           │                       │
│               ┌────────────────────┐   │                        │
│               │ 使用原始 Bash Loop │   ▼                        │
│               │ (確保可信任環境)   │ ┌────────────────────┐     │
│               └────────────────────┘ │ 都可以，看個人偏好│     │
│                                      └────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**使用官方 Plugin 的情況**：
- 企業/團隊環境
- 需要合規審計
- 處理敏感程式碼
- 需要權限控制
- CI/CD 整合

**使用原始 Bash Loop 的情況**：
- 個人實驗專案
- 需要自訂命令（如特殊建構工具）
- 追求最大效能
- 可信任的隔離環境
- 需要訪問系統資源

---

## 8.5 案例研究：CURSED 程式語言的開發

Geoffrey Huntley 使用原始 Ralph Loop 花費三個月開發了 CURSED 程式語言。這個案例是 Ralph Loop 極限應用的最佳示範。

### 8.5.1 CURSED 專案背景

CURSED 是一個「故意設計得很難用」的程式語言，用於：
- 教育目的（理解語言設計的反面教材）
- 程式碼混淆
- 挑戰 AI 編碼工具的能力

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURSED 語言特性                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   // 正常的程式碼                    // CURSED 版本             │
│   function add(a, b) {              ⒻⓊⓃⒸⓉⒾⓄⓃ ⓐⓓⓓ(α, β) ⟨ │
│       return a + b;                     ⓡⓔⓣⓤⓡⓝ α ⊕ β;         │
│   }                                 ⟩                           │
│                                                                 │
│   特性：                                                         │
│   • 使用 Unicode 圈圈字母作為關鍵字                             │
│   • 使用希臘字母作為變數名                                      │
│   • 使用數學符號作為運算子                                      │
│   • 隨機改變語法規則                                            │
│   • 錯誤訊息故意混淆                                            │
│                                                                 │
│   開發規模：                                                     │
│   • 核心解析器：~15,000 行                                      │
│   • 標準函式庫：~8,000 行                                       │
│   • 測試案例：~3,000 個                                         │
│   • 文件：~200 頁                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.5.2 開發過程數據

```
┌─────────────────────────────────────────────────────────────────┐
│                   CURSED 開發統計                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   時間維度                                                       │
│   ────────────────────────────────────────────                   │
│   總開發時間：     3 個月                                        │
│   總迭代次數：     4,287 次                                      │
│   平均每天迭代：   47 次                                         │
│   最長單次迭代：   23 分鐘                                       │
│   最短單次迭代：   8 秒                                          │
│                                                                 │
│   Git 統計                                                       │
│   ────────────────────────────────────────────                   │
│   總 Commit 數：   4,287                                         │
│   有效 Commit：    3,891 (90.8%)                                 │
│   回滾 Commit：    396 (9.2%)                                    │
│   最大回滾深度：   12 次連續回滾                                 │
│                                                                 │
│   Token 消耗                                                     │
│   ────────────────────────────────────────────                   │
│   總輸入 Token：   127,483,291                                   │
│   總輸出 Token：   43,827,156                                    │
│   總成本：         ~$2,847 USD                                   │
│   每次迭代成本：   ~$0.66 USD                                    │
│                                                                 │
│   收斂模式分析                                                   │
│   ────────────────────────────────────────────                   │
│   第一階段（月 1）：頻繁失敗，學習語言結構                       │
│   第二階段（月 2）：穩定進展，核心功能完成                       │
│   第三階段（月 3）：收尾工作，邊緣案例修復                       │
│                                                                 │
│   ┌────────────────────────────────────────────────────┐        │
│   │ 失敗測試數                                          │        │
│   │                                                    │        │
│   │ 3000 ┤▓▓▓▓▓▓                                       │        │
│   │      │      ▓▓▓▓▓                                  │        │
│   │ 2000 ┤            ▓▓▓▓                              │        │
│   │      │                ▓▓▓▓                          │        │
│   │ 1000 ┤                    ▓▓▓▓                      │        │
│   │      │                        ▓▓▓▓▓▓▓▓▓▓           │        │
│   │    0 ┼────────────────────────────────────▓▓▓▓─────│        │
│   │      0     1000    2000    3000    4000  迭代次數   │        │
│   └────────────────────────────────────────────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.5.3 PROMPT.md 設計

Huntley 使用的 PROMPT.md 經過多次迭代優化：

```markdown
# 任務：開發 CURSED 程式語言

## 情境

CURSED 是一個「反直覺」的程式語言，故意設計得難以使用。
你正在開發這個語言的編譯器/解譯器。

## 當前狀態

請執行 `./run_tests.sh` 查看當前測試狀態。

## 目標

1. 讓所有測試通過
2. 保持程式碼品質
3. 遵循專案的設計原則

## 設計原則

CURSED 的設計原則（必須遵守）：
1. 關鍵字使用 Unicode 圈圈字母（Ⓐ-Ⓩ）
2. 變數名使用希臘字母
3. 運算子使用數學符號
4. 每個功能都要有「cursed」版本的行為

## 約束

- 不要簡化語言設計（那會違背專案目的）
- 不要修改測試案例
- 保持向後相容
- 程式碼要有適當註解

## 完成條件

當以下所有條件都滿足時，此任務視為完成：

1. [ ] `./run_tests.sh` 返回 exit code 0
2. [ ] 沒有編譯警告
3. [ ] 程式碼覆蓋率 > 80%
4. [ ] 所有 TODO 都已處理

## 工作流程

1. 執行測試，識別失敗原因
2. 閱讀相關的測試案例，理解期望行為
3. 實作或修復功能
4. 確認單一測試通過
5. 執行全部測試，確保沒有迴歸
6. 繼續下一個失敗的測試

## 常見陷阱

- Unicode 正規化問題：使用 NFC 正規化
- 希臘字母大小寫：某些希臘字母沒有大寫形式
- 數學符號的 Unicode 碼點：有多個看起來相似的符號
```

### 8.5.4 關鍵技術挑戰與解決方案

| 挑戰 | 問題描述 | Ralph Loop 如何解決 |
|------|----------|---------------------|
| Unicode 解析 | 圈圈字母的編碼複雜 | 多次迭代嘗試不同解析策略 |
| 語法衝突 | 某些數學符號有多重含義 | 逐案例修復，建立優先級規則 |
| 效能優化 | 初版效能很差 | 持續優化，每次迭代改進 1-5% |
| 邊緣案例 | 大量奇怪的輸入組合 | 隨機測試 + 逐一修復 |

### 8.5.5 學到的教訓

```
┌─────────────────────────────────────────────────────────────────┐
│                   CURSED 開發的關鍵教訓                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. PROMPT.md 的重要性                                         │
│   ───────────────────────────────────────────                    │
│   • 好的 PROMPT.md 讓迭代效率提升 3-5 倍                        │
│   • 明確的設計原則減少「創意性破壞」                            │
│   • 完成條件必須可機器驗證                                      │
│                                                                 │
│   2. Git 分支策略                                               │
│   ───────────────────────────────────────────                    │
│   • 每個主要功能用獨立分支                                      │
│   • 頻繁合併回主分支，避免偏移太遠                              │
│   • 保留「已知良好」的標籤                                      │
│                                                                 │
│   3. 測試驅動                                                   │
│   ───────────────────────────────────────────                    │
│   • 先寫測試，再讓 Ralph Loop 修復                              │
│   • 測試是 Agent 的「眼睛」                                     │
│   • 模糊的測試 = 模糊的方向                                     │
│                                                                 │
│   4. 人機協作                                                   │
│   ───────────────────────────────────────────                    │
│   • 人類負責設計決策                                            │
│   • AI 負責實作細節                                             │
│   • 定期審查 AI 的工作，及時糾正                                │
│                                                                 │
│   5. 成本管理                                                   │
│   ───────────────────────────────────────────                    │
│   • 設定每日/每週 Token 預算                                    │
│   • 簡單問題不需要強模型                                        │
│   • 監控成本趨勢，及時調整                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8.6 混合使用策略

最佳實踐往往是根據開發階段選擇不同的工具。

### 8.6.1 開發生命週期中的工具選擇

```
┌─────────────────────────────────────────────────────────────────┐
│                 開發階段 vs 工具選擇                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   開發階段          推薦工具              原因                   │
│   ─────────────────────────────────────────────────────────────  │
│                                                                 │
│   原型開發          原始 Bash Loop        • 快速迭代            │
│                                           • 自由實驗            │
│                                           • 低開銷              │
│                                                                 │
│   功能開發          原始 Bash Loop        • 高效率              │
│                     (本地環境)            • 自訂命令            │
│                                           • 即時回饋            │
│                                                                 │
│   程式碼審查        官方 Plugin           • 審計追蹤            │
│                                           • 安全邊界            │
│                                           • 團隊協作            │
│                                                                 │
│   CI/CD 整合        官方 Plugin           • 安全性              │
│                                           • 可重現性            │
│                                           • 錯誤恢復            │
│                                                                 │
│   生產部署          官方 Plugin           • 合規要求            │
│                     (嚴格配置)            • 審計日誌            │
│                                           • 權限控制            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.6.2 漸進式遷移策略

如果團隊目前使用原始 Bash Loop，可以採用漸進式遷移：

```
┌─────────────────────────────────────────────────────────────────┐
│                   漸進式遷移路線圖                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   階段 1：共存（1-2 週）                                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ • 安裝官方 Plugin，但不強制使用                         │   │
│   │ • 在非關鍵任務上試用                                    │   │
│   │ • 收集團隊回饋                                          │   │
│   │ • 識別需要原始 Loop 的特殊場景                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│   階段 2：配置優化（1 週）                                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ • 根據團隊需求配置官方 Plugin                           │   │
│   │ • 加入必要的自訂 Stop Hooks                             │   │
│   │ • 配置白名單滿足特殊需求                               │   │
│   │ • 建立團隊共用配置檔                                   │   │
│   └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│   階段 3：默認切換（2 週）                                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ • 將官方 Plugin 設為默認                                │   │
│   │ • 原始 Loop 需要特別申請                               │   │
│   │ • 建立使用指南和最佳實踐                               │   │
│   │ • 監控使用情況和問題                                   │   │
│   └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│   階段 4：完全遷移（持續）                                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ • 逐步淘汰原始 Loop 使用                               │   │
│   │ • 將特殊需求提交給 Anthropic                           │   │
│   │ • 持續優化配置                                         │   │
│   │ • 定期審查安全設定                                     │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.6.3 混合架構實作

```go
// ‹1› 混合模式 Ralph Loop
package ralph

import (
    "context"
    "fmt"
)

// ‹2› 執行模式枚舉
type ExecutionMode string

const (
    ModeRawBash   ExecutionMode = "raw_bash"
    ModePlugin    ExecutionMode = "plugin"
    ModeHybrid    ExecutionMode = "hybrid"
)

// ‹3› 混合 Ralph Loop 配置
type HybridConfig struct {
    DefaultMode    ExecutionMode
    SensitivePaths []string  // 敏感路徑強制使用 Plugin
    FreeZones      []string  // 自由區域允許使用 Raw Bash
    TeamMembers    map[string]ExecutionMode  // 成員級別配置
}

// ‹4› 混合執行器
type HybridExecutor struct {
    rawExecutor    *RawBashExecutor
    pluginExecutor *PluginExecutor
    config         HybridConfig
}

func NewHybridExecutor(config HybridConfig) *HybridExecutor {
    return &HybridExecutor{
        rawExecutor:    NewRawBashExecutor(),
        pluginExecutor: NewPluginExecutor(),
        config:         config,
    }
}

// ‹5› 根據上下文選擇執行模式
func (h *HybridExecutor) SelectMode(ctx ExecutionContext) ExecutionMode {
    // 檢查是否在敏感路徑
    for _, sensitivePath := range h.config.SensitivePaths {
        if ctx.WorkingDir.HasPrefix(sensitivePath) {
            return ModePlugin
        }
    }

    // 檢查是否在自由區域
    for _, freeZone := range h.config.FreeZones {
        if ctx.WorkingDir.HasPrefix(freeZone) {
            return ModeRawBash
        }
    }

    // 檢查用戶級別配置
    if mode, ok := h.config.TeamMembers[ctx.UserID]; ok {
        return mode
    }

    // 返回默認模式
    return h.config.DefaultMode
}

// ‹6› 執行迭代
func (h *HybridExecutor) Execute(ctx context.Context, task Task) (Result, error) {
    execCtx := ExtractExecutionContext(ctx)
    mode := h.SelectMode(execCtx)

    switch mode {
    case ModeRawBash:
        return h.rawExecutor.Execute(ctx, task)
    case ModePlugin:
        return h.pluginExecutor.Execute(ctx, task)
    case ModeHybrid:
        // 混合模式：非敏感操作用 Raw，敏感操作用 Plugin
        if task.IsSensitive() {
            return h.pluginExecutor.Execute(ctx, task)
        }
        return h.rawExecutor.Execute(ctx, task)
    default:
        return Result{}, fmt.Errorf("未知執行模式: %s", mode)
    }
}

// ‹7› 敏感操作判斷
func (t Task) IsSensitive() bool {
    sensitivePatterns := []string{
        "rm -rf",
        "sudo",
        "curl.*|.*sh",
        "wget.*|.*bash",
        "chmod 777",
        "> /dev/",
    }

    for _, pattern := range sensitivePatterns {
        if regexp.MustCompile(pattern).MatchString(t.Command) {
            return true
        }
    }
    return false
}
```

---

## 8.7 本章小結

本章深入探討了官方 Plugin 與原始 Bash Loop 的差異，以及如何根據場景選擇適當的工具。

### 關鍵要點

1. **沙箱技術**
   - 作業系統層級隔離（namespaces, cgroups, seccomp）
   - 容器化沙箱（Docker）
   - 多層防護架構

2. **Stop Hook 機制**
   - 可程式化的收斂條件
   - 內建多種常用 Hook
   - 支援自訂 Hook 開發

3. **消毒化的代價**
   - 效能損失 ~50%
   - 功能受限
   - 換取安全性和可審計性

4. **選擇準則**
   - 生產環境 → 官方 Plugin
   - 個人實驗 → 原始 Bash Loop
   - 團隊協作 → 官方 Plugin
   - 需要自訂 → 原始 Bash Loop

5. **CURSED 案例啟示**
   - 極限應用的可行性
   - PROMPT.md 設計的重要性
   - 人機協作的最佳實踐

### 練習題

1. **基礎練習**：配置一個 claude-ralph.yaml 檔案，設定以下 Stop Hooks：所有測試通過、最大 50 次迭代、覆蓋率達到 70%。

2. **進階練習**：實作一個自訂 Stop Hook，當 TypeScript 的型別錯誤數量歸零時停止。

3. **架構練習**：設計一個混合架構，讓開發環境使用原始 Loop，但 CI/CD 環境自動切換到官方 Plugin。

4. **分析練習**：分析 CURSED 開發案例，列出五個可以改進的地方，並說明如何改進。

---

## 學術參考文獻

1. Goldberg, I., et al. (1996). A secure environment for untrusted helper applications. *USENIX Security Symposium*.

2. Berman, A., Bourassa, V., & Selberg, E. (1995). TRON: Process-Specific File Protection for the UNIX Operating System. *USENIX Winter Conference*.

3. Prevelakis, V., & Spinellis, D. (2001). Sandboxing Applications. *USENIX Annual Technical Conference*.

4. Docker, Inc. (2021). Docker Security Documentation. https://docs.docker.com/engine/security/

5. Anthropic. (2025). Claude Code Plugin Security Architecture. Internal Documentation.

---

## 下一章預告

無論使用哪種實現，Ralph Loop 的效果都高度依賴 PROMPT.md 的設計品質。第 9 章將深入 Prompt 工程的藝術，教你設計能讓迴圈有效收斂的提示詞模板，包括「遊樂場」隱喻、Completion Promise 設計原則，以及針對不同任務類型的專用模板。
