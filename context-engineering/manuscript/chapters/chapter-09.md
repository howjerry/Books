# 第 9 章：Prompt 工程的藝術

> 設計收斂條件：讓迴圈知道何時停止
> — 將抽象需求轉化為可執行指令的技藝

---

## 本章學習目標

完成本章後，你將能夠：

- 理解 Prompt 工程的認知科學與語言學基礎
- 運用「遊樂場」隱喻來設計有效的 PROMPT.md
- 掌握 Completion Promise 的設計原則與模式
- 設計具有明確收斂條件的迭代任務
- 運用 A/B 測試方法論優化 Prompt
- 為不同任務類型創建專用的 PROMPT.md 模板
- 避免常見的 Prompt 設計陷阱

---

## 9.1 Prompt 工程的理論基礎

Prompt 工程不僅僅是「寫指令」，它是將人類意圖轉化為 AI 可理解格式的認知橋樑。

### 9.1.1 語言學視角：從語用學到指令設計

語言學中的**語用學（Pragmatics）**研究語言在特定情境中的使用方式，這對理解 Prompt 工程至關重要。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Grice 的合作原則                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Paul Grice (1975) 提出的會話合作原則（Cooperative Principle）： │
│                                                                 │
│   1. 量的準則（Maxim of Quantity）                               │
│      ├── 提供足夠的資訊                                         │
│      └── 不提供過多的資訊                                       │
│                                                                 │
│      Prompt 應用：                                               │
│      ✅ 「修復 calculator.go 中的 Add 函數，它目前返回 a-b」    │
│      ❌ 「修復那個函數」（太少資訊）                            │
│      ❌ 「修復函數，這個函數在第 15 行，是 1952 年...」（太多） │
│                                                                 │
│   2. 質的準則（Maxim of Quality）                                │
│      ├── 不說自己認為是假的話                                   │
│      └── 不說沒有足夠證據的話                                   │
│                                                                 │
│      Prompt 應用：                                               │
│      ✅ 「測試目前有 5 個失敗」（基於實際執行結果）             │
│      ❌ 「測試應該大概有一些問題吧」（模糊不確定）              │
│                                                                 │
│   3. 關係準則（Maxim of Relation）                               │
│      └── 說話要切題                                             │
│                                                                 │
│      Prompt 應用：                                               │
│      ✅ 專注於當前任務的相關資訊                                │
│      ❌ 包含與任務無關的背景故事                                │
│                                                                 │
│   4. 方式準則（Maxim of Manner）                                 │
│      ├── 避免晦澀                                               │
│      ├── 避免歧義                                               │
│      ├── 簡潔                                                   │
│      └── 有條理                                                 │
│                                                                 │
│      Prompt 應用：                                               │
│      ✅ 使用清晰的結構（標題、列表、編號）                      │
│      ✅ 定義專有名詞                                            │
│      ❌ 使用可能有多種解讀的指令                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.1.2 認知科學視角：工作記憶與 Context Window

人類的**工作記憶（Working Memory）**有限，LLM 的 Context Window 也是如此。認知科學的研究可以指導我們設計更有效的 Prompt。

```
┌─────────────────────────────────────────────────────────────────┐
│              Miller's Law 與 Context Engineering                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   George Miller (1956) 的「魔法數字 7±2」：                      │
│   人類工作記憶一次只能保持 5-9 個資訊塊                          │
│                                                                 │
│   對 Prompt 設計的啟示：                                         │
│                                                                 │
│   ❌ 不佳的設計（一次性給予太多指令）                           │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 1. 閱讀所有測試檔案                                     │   │
│   │ 2. 分析每個測試的意圖                                   │   │
│   │ 3. 找出失敗原因                                         │   │
│   │ 4. 設計修復方案                                         │   │
│   │ 5. 實作修復                                             │   │
│   │ 6. 驗證修復                                             │   │
│   │ 7. 檢查是否有迴歸                                       │   │
│   │ 8. 更新文件                                             │   │
│   │ 9. 提交變更                                             │   │
│   │ 10. 清理暫存檔案                                        │   │
│   │ 11. 通知相關人員                                        │   │
│   │ 12. 更新追蹤系統                                        │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ✅ 改良的設計（分層 + 分組）                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ ## 工作流程                                             │   │
│   │                                                         │   │
│   │ 1. 診斷階段                                             │   │
│   │    - 執行測試，識別失敗                                 │   │
│   │    - 分析錯誤訊息                                       │   │
│   │                                                         │   │
│   │ 2. 修復階段                                             │   │
│   │    - 修改程式碼                                         │   │
│   │    - 驗證單一測試通過                                   │   │
│   │                                                         │   │
│   │ 3. 驗證階段                                             │   │
│   │    - 執行全部測試                                       │   │
│   │    - 確認無迴歸                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   認知負荷理論（Cognitive Load Theory, Sweller 1988）：           │
│   • 內在負荷：任務本身的複雜性                                  │
│   • 外在負荷：呈現方式造成的額外負擔                            │
│   • 關聯負荷：建立心智模型的努力                                │
│                                                                 │
│   好的 Prompt 應該最小化外在負荷，讓 LLM 專注於任務本身          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.1.3 指令遵循（Instruction Following）的技術背景

現代 LLM 之所以能夠遵循指令，是因為經過了特殊的訓練過程：

```
┌─────────────────────────────────────────────────────────────────┐
│                 指令微調的技術背景                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   訓練階段                                                       │
│   ────────────────────────────────────────────                   │
│                                                                 │
│   Stage 1: 預訓練（Pre-training）                                │
│   • 目標：學習語言的統計規律                                    │
│   • 資料：海量網路文本                                          │
│   • 結果：能預測下一個 Token，但不會「遵循指令」                │
│                                                                 │
│   Stage 2: 監督式微調（Supervised Fine-Tuning, SFT）             │
│   • 目標：學習指令-回應的配對模式                               │
│   • 資料：人工標註的 (指令, 回應) 對                            │
│   • 結果：開始理解「指令」的概念                                │
│                                                                 │
│   Stage 3: RLHF / Constitutional AI                              │
│   • 目標：學習人類偏好的回應風格                                │
│   • 資料：人類對回應的排名 / 憲法原則                           │
│   • 結果：更安全、更有幫助的回應                                │
│                                                                 │
│   Prompt 設計的啟示                                              │
│   ────────────────────────────────────────────                   │
│                                                                 │
│   LLM 在訓練過程中學到的模式：                                   │
│   • 指令通常在開頭                                              │
│   • 明確的格式要求會被遵循                                      │
│   • 範例（Few-shot）有助於理解意圖                              │
│   • 角色設定（Role prompting）影響回應風格                      │
│                                                                 │
│   因此，有效的 Prompt 應該：                                     │
│   ✅ 將最重要的指令放在開頭                                     │
│   ✅ 提供明確的輸出格式要求                                     │
│   ✅ 使用範例說明期望行為                                       │
│   ✅ 設定適當的角色和語氣                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9.2 遊樂場隱喻

Geoffrey Huntley 用一個生動的比喻描述 Ralph Loop 的運作方式：

> 「把 agent 放進一個遊樂場。讓它建構、失敗、看到失敗的標誌、然後重來。」

### 9.2.1 隱喻解析

```
┌─────────────────────────────────────────────────────────────────┐
│                    遊樂場隱喻詳解                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   遊樂場元素              Ralph Loop 對應                        │
│   ────────────────────────────────────────────────────────────   │
│                                                                 │
│   遊樂場的圍欄            約束條件（Constraints）                │
│   └─ 定義活動範圍         └─ 「只修改 src/ 目錄」                │
│   └─ 防止走失             └─ 「不要修改測試檔案」                │
│                                                                 │
│   遊樂設施                可用工具（Tools）                      │
│   └─ 溜滑梯、鞦韆等       └─ Read, Write, Bash, Edit             │
│   └─ 每個都有特定用途     └─ 每個工具有明確功能                  │
│                                                                 │
│   其他孩子                現有程式碼                            │
│   └─ 要與他們互動         └─ 要與現有程式碼整合                  │
│   └─ 可能需要輪流         └─ 不能破壞現有功能                    │
│                                                                 │
│   失敗的標誌              錯誤訊息                              │
│   └─ 「這裡太高，小心！」 └─ 「Test failed: expected 5, got -1」│
│   └─ 清楚指出問題         └─ 清楚指出哪裡錯了                    │
│                                                                 │
│   成功的獎勵              收斂條件                              │
│   └─ 「你到達終點了！」   └─ 「所有測試通過」                    │
│   └─ 明確的成功標準       └─ 可機器驗證的條件                    │
│                                                                 │
│   遊戲規則                工作流程                              │
│   └─ 先排隊，再玩         └─ 先執行測試，再修改程式碼            │
│   └─ 規則讓遊戲公平       └─ 流程讓迭代有效                      │
│                                                                 │
│   時間限制                迭代上限                              │
│   └─ 「5 點要回家」       └─ 「最多 100 次迭代」                 │
│   └─ 防止無限玩下去       └─ 防止無限迴圈                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2.2 設計遊樂場的原則

根據遊樂場隱喻，有效的 PROMPT.md 應該具備：

```
┌─────────────────────────────────────────────────────────────────┐
│                 有效遊樂場的設計原則                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   原則 1：明確的邊界                                             │
│   ────────────────────                                           │
│   孩子需要知道遊樂場的範圍在哪裡                                 │
│                                                                 │
│   ✅ 好的邊界定義：                                              │
│   「你只能修改 src/ 目錄下的檔案」                               │
│   「不要修改 package.json」                                      │
│   「不要刪除任何測試」                                           │
│                                                                 │
│   ❌ 模糊的邊界：                                                │
│   「注意不要改太多東西」                                         │
│   「盡量保守一點」                                               │
│                                                                 │
│   原則 2：可見的回饋                                             │
│   ────────────────────                                           │
│   孩子需要能夠「看到」自己的行動結果                             │
│                                                                 │
│   ✅ 好的回饋設計：                                              │
│   「每次修改後執行 npm test，觀察輸出」                          │
│   「失敗的測試會顯示期望值和實際值」                             │
│                                                                 │
│   ❌ 看不見的回饋：                                              │
│   「改好之後我會檢查」（Agent 看不到結果）                       │
│   「如果有問題我會告訴你」                                       │
│                                                                 │
│   原則 3：可重複的嘗試                                           │
│   ────────────────────                                           │
│   孩子可以不斷嘗試，直到成功                                     │
│                                                                 │
│   ✅ 好的重試設計：                                              │
│   「如果測試失敗，分析錯誤，修改，再試一次」                     │
│   「Git 會記錄你的每次嘗試」                                     │
│                                                                 │
│   ❌ 阻礙重試的設計：                                            │
│   「只有一次機會」                                               │
│   「改錯了就沒辦法了」                                           │
│                                                                 │
│   原則 4：漸進的挑戰                                             │
│   ────────────────────                                           │
│   好的遊樂場有不同難度的設施                                     │
│                                                                 │
│   ✅ 好的挑戰設計：                                              │
│   「先修復簡單的語法錯誤」                                       │
│   「然後處理邏輯錯誤」                                           │
│   「最後優化效能」                                               │
│                                                                 │
│   ❌ 不合理的挑戰：                                              │
│   「一次性解決所有問題」                                         │
│   「在不知道現狀的情況下就開始修改」                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9.3 Completion Promise：完成條件設計

Completion Promise 是告訴 Agent「何時算完成」的明確承諾。這是 Ralph Loop 能夠收斂的關鍵。

### 9.3.1 Completion Promise 的結構

```
┌─────────────────────────────────────────────────────────────────┐
│               Completion Promise 結構模板                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ## 完成條件                                                    │
│                                                                 │
│   當以下【所有/任一】條件都滿足時，此任務視為完成：              │
│                                                                 │
│   ### 必要條件（全部必須滿足）                                   │
│   1. [ ] [可機器驗證的條件 1]                                   │
│   2. [ ] [可機器驗證的條件 2]                                   │
│   3. [ ] [可機器驗證的條件 3]                                   │
│                                                                 │
│   ### 充分條件（滿足其一即可觸發提前完成）                       │
│   - [ ] [特殊情況 1]                                            │
│   - [ ] [特殊情況 2]                                            │
│                                                                 │
│   ### 驗證命令                                                   │
│   每個條件都應該有對應的驗證方式：                               │
│   - 條件 1: `npm test` 返回 exit code 0                         │
│   - 條件 2: `npm run lint` 沒有錯誤輸出                         │
│   - 條件 3: `git status` 顯示工作目錄乾淨                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3.2 可機器驗證 vs 不可機器驗證

```
┌─────────────────────────────────────────────────────────────────┐
│            條件類型：可機器驗證 vs 不可機器驗證                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   可機器驗證（適合 Ralph Loop）                                  │
│   ────────────────────────────────────────────                   │
│                                                                 │
│   ✅ 測試通過/失敗                                               │
│      驗證: exit code 0/1                                        │
│                                                                 │
│   ✅ 編譯成功/失敗                                               │
│      驗證: 編譯器輸出                                           │
│                                                                 │
│   ✅ 錯誤數量歸零                                                │
│      驗證: grep -c "error" output                               │
│                                                                 │
│   ✅ 檔案存在/不存在                                             │
│      驗證: test -f filename                                     │
│                                                                 │
│   ✅ 特定字串出現/消失                                           │
│      驗證: grep "pattern" file                                  │
│                                                                 │
│   ✅ 效能指標達標                                                │
│      驗證: benchmark 輸出                                       │
│                                                                 │
│   ✅ 覆蓋率達標                                                  │
│      驗證: coverage report                                      │
│                                                                 │
│   ────────────────────────────────────────────                   │
│                                                                 │
│   不可機器驗證（需要人類判斷）                                   │
│   ────────────────────────────────────────────                   │
│                                                                 │
│   ❌ 「程式碼品質良好」                                          │
│      問題: 「良好」沒有定義                                     │
│      改進: 「eslint 零警告」                                    │
│                                                                 │
│   ❌ 「設計合理」                                                │
│      問題: 「合理」是主觀判斷                                   │
│      改進: 「符合 SOLID 原則」（仍需細化）                       │
│                                                                 │
│   ❌ 「看起來正確」                                              │
│      問題: 外觀無法程式化檢查                                   │
│      改進: 「輸出與 expected.txt 相同」                          │
│                                                                 │
│   ❌ 「使用者體驗好」                                            │
│      問題: UX 需要人類測試                                      │
│      改進: 「Lighthouse 分數 > 90」                              │
│                                                                 │
│   ❌ 「夠快」                                                    │
│      問題: 「夠」沒有定義                                       │
│      改進: 「響應時間 < 100ms」                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3.3 設計 Completion Promise 的步驟

```go
// ‹1› Completion Promise 設計框架
type CompletionPromise struct {
    RequiredConditions []Condition  // 必要條件（AND）
    OptionalConditions []Condition  // 可選條件
    EarlyExitConditions []Condition // 提前退出條件（OR）
}

// ‹2› 單一條件的結構
type Condition struct {
    Description     string   // 人類可讀的描述
    VerifyCommand   string   // 驗證命令
    ExpectedOutput  string   // 期望輸出（可選）
    ExpectedExitCode int     // 期望的 exit code
    IsNegative      bool     // 是否是否定條件（期望失敗）
}

// ‹3› 設計步驟函數
func DesignCompletionPromise(taskDescription string) CompletionPromise {
    promise := CompletionPromise{}

    // Step 1: 識別成功的定義
    // 問自己：「什麼情況下這個任務算成功？」
    successDefinitions := identifySuccessDefinitions(taskDescription)

    // Step 2: 將成功定義轉化為可驗證條件
    for _, def := range successDefinitions {
        condition := convertToVerifiableCondition(def)
        if condition.IsVerifiable() {
            promise.RequiredConditions = append(promise.RequiredConditions, condition)
        } else {
            // 無法驗證的條件需要重新設計
            refinedConditions := refineCondition(condition)
            promise.RequiredConditions = append(promise.RequiredConditions, refinedConditions...)
        }
    }

    // Step 3: 設計提前退出條件
    // 例如：如果發現無法完成的情況，應該停止
    promise.EarlyExitConditions = designEarlyExitConditions(taskDescription)

    // Step 4: 驗證條件的可行性
    validateConditions(&promise)

    return promise
}

// ‹4› 條件驗證
func (c *Condition) IsVerifiable() bool {
    // 有明確的驗證命令
    if c.VerifyCommand == "" {
        return false
    }

    // 有明確的期望結果
    if c.ExpectedOutput == "" && c.ExpectedExitCode == 0 {
        return false
    }

    return true
}

// ‹5› 將 Completion Promise 轉化為 Markdown
func (cp *CompletionPromise) ToMarkdown() string {
    var sb strings.Builder

    sb.WriteString("## 完成條件\n\n")
    sb.WriteString("當以下所有條件都滿足時，此任務視為完成：\n\n")

    for i, cond := range cp.RequiredConditions {
        sb.WriteString(fmt.Sprintf("%d. [ ] %s\n", i+1, cond.Description))
        sb.WriteString(fmt.Sprintf("   驗證: `%s`\n", cond.VerifyCommand))
        if cond.ExpectedOutput != "" {
            sb.WriteString(fmt.Sprintf("   期望: %s\n", cond.ExpectedOutput))
        }
    }

    if len(cp.EarlyExitConditions) > 0 {
        sb.WriteString("\n### 提前退出條件\n\n")
        sb.WriteString("如果以下任一條件滿足，應停止並報告：\n\n")
        for _, cond := range cp.EarlyExitConditions {
            sb.WriteString(fmt.Sprintf("- [ ] %s\n", cond.Description))
        }
    }

    return sb.String()
}
```

---

## 9.4 控制流程設計

好的 PROMPT.md 不僅告訴 Agent「做什麼」，還要告訴它「怎麼做」的流程。

### 9.4.1 流程設計的形式化方法

```
┌─────────────────────────────────────────────────────────────────┐
│                流程控制的形式化方法                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   狀態機模型（Finite State Machine）                             │
│   ──────────────────────────────────                             │
│                                                                 │
│   Ralph Loop 的流程可以建模為狀態機：                            │
│                                                                 │
│   狀態集合 S = {初始, 診斷, 修復, 驗證, 完成, 失敗}              │
│                                                                 │
│   轉換函數 δ:                                                    │
│   - δ(初始, 讀取任務) → 診斷                                    │
│   - δ(診斷, 發現問題) → 修復                                    │
│   - δ(診斷, 無問題) → 完成                                      │
│   - δ(修復, 修復成功) → 驗證                                    │
│   - δ(修復, 修復失敗) → 診斷                                    │
│   - δ(驗證, 測試通過) → 完成                                    │
│   - δ(驗證, 測試失敗) → 診斷                                    │
│   - δ(*, 超時) → 失敗                                           │
│                                                                 │
│   圖示：                                                         │
│                                                                 │
│   ┌────────┐   讀取任務   ┌────────┐                            │
│   │  初始  │─────────────►│  診斷  │◄─────────────┐            │
│   └────────┘              └────┬───┘              │            │
│                                │                   │            │
│                   發現問題 ────┼──── 無問題       │            │
│                                │         │        │            │
│                                ▼         │        │            │
│                           ┌────────┐    │        │            │
│                           │  修復  │    │        │            │
│                           └────┬───┘    │        │            │
│                                │        │        │            │
│                   修復成功 ────┤        │        │            │
│                                │        │        │ 測試失敗   │
│                                ▼        │        │            │
│                           ┌────────┐    │        │            │
│                           │  驗證  │────┼────────┘            │
│                           └────┬───┘    │                      │
│                                │        │                      │
│                   測試通過 ────┘        │                      │
│                                │        │                      │
│                                ▼        ▼                      │
│                           ┌────────────────┐                   │
│                           │     完成       │                   │
│                           └────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.4.2 流程指令的最佳實踐

```markdown
## 工作流程

### 階段 1：診斷（Diagnosis）

在開始修改任何程式碼之前，先理解問題：

1. **執行測試**
   ```bash
   npm test 2>&1 | tee test-output.log
   ```

2. **分析失敗原因**
   - 閱讀錯誤訊息
   - 識別失敗的測試名稱
   - 找出期望值與實際值的差異

3. **確定修復優先級**
   - 優先修復導致最多其他測試失敗的問題
   - 優先修復簡單的問題

### 階段 2：修復（Fix）

每次只修復一個問題：

1. **定位問題程式碼**
   - 根據錯誤訊息找到相關檔案
   - 閱讀相關函數的實作

2. **設計修復方案**
   - 理解期望行為
   - 考慮邊界條件
   - 避免引入新問題

3. **實施修復**
   - 最小化修改範圍
   - 保持程式碼風格一致
   - 加入必要的註解

### 階段 3：驗證（Verify）

確保修復有效且無副作用：

1. **執行單一測試**
   ```bash
   npm test -- --grep "測試名稱"
   ```

2. **如果通過，執行全部測試**
   ```bash
   npm test
   ```

3. **如果有新的失敗**
   - 判斷是否是修復引起的迴歸
   - 如果是，回滾並嘗試其他方案
   - 如果不是，記錄並繼續

### 階段 4：迭代（Iterate）

重複以上步驟，直到所有測試通過。

**重要提醒**：
- 每次修復後都要驗證
- 不要累積太多修改再驗證
- 如果連續 5 次修復同一個問題都失敗，停下來重新分析
```

---

## 9.5 A/B 測試方法論

好的 Prompt 不是一次寫成的，需要透過實驗和迭代來優化。

### 9.5.1 Prompt A/B 測試框架

```
┌─────────────────────────────────────────────────────────────────┐
│                 Prompt A/B 測試框架                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   實驗設計                                                       │
│   ────────────────────────────────────────────                   │
│                                                                 │
│   變數：                                                         │
│   • 獨立變數：Prompt 的變體（A 版本 vs B 版本）                  │
│   • 因變數：收斂次數、成功率、Token 消耗                        │
│   • 控制變數：同樣的任務、同樣的模型、同樣的環境                │
│                                                                 │
│   實驗流程：                                                     │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │ 1. 定義假設                                               │ │
│   │    H₀: Prompt A 和 Prompt B 的收斂次數沒有顯著差異        │ │
│   │    H₁: Prompt B 的收斂次數顯著低於 Prompt A               │ │
│   │                                                           │ │
│   │ 2. 準備測試任務                                           │ │
│   │    選擇 10-20 個標準化測試任務                            │ │
│   │                                                           │ │
│   │ 3. 執行實驗                                               │ │
│   │    每個 Prompt 變體執行 N 次（N ≥ 30 for 統計顯著性）      │ │
│   │                                                           │ │
│   │ 4. 收集數據                                               │ │
│   │    記錄：收斂次數、總耗時、Token 消耗、成功/失敗          │ │
│   │                                                           │ │
│   │ 5. 統計分析                                               │ │
│   │    使用 t 檢定或 Mann-Whitney U 檢定                      │ │
│   │                                                           │ │
│   │ 6. 得出結論                                               │ │
│   │    如果 p < 0.05，拒絕 H₀                                 │ │
│   └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.5.2 A/B 測試實作

```go
// ‹1› A/B 測試框架
package prompt_testing

import (
    "fmt"
    "math"
    "sort"
    "time"
)

// ‹2› 實驗結果
type ExperimentResult struct {
    PromptVersion  string
    TaskID         string
    Iterations     int
    TotalTime      time.Duration
    TokensUsed     int
    Success        bool
    FinalOutput    string
}

// ‹3› 實驗配置
type ExperimentConfig struct {
    TaskIDs           []string
    PromptA           string
    PromptB           string
    RepetitionsPerTask int
    MaxIterations     int
}

// ‹4› A/B 測試執行器
type ABTestRunner struct {
    config    ExperimentConfig
    resultsA  []ExperimentResult
    resultsB  []ExperimentResult
}

func NewABTestRunner(config ExperimentConfig) *ABTestRunner {
    return &ABTestRunner{
        config:   config,
        resultsA: make([]ExperimentResult, 0),
        resultsB: make([]ExperimentResult, 0),
    }
}

// ‹5› 執行 A/B 測試
func (r *ABTestRunner) Run() error {
    for _, taskID := range r.config.TaskIDs {
        for i := 0; i < r.config.RepetitionsPerTask; i++ {
            // 執行 Prompt A
            resultA := r.runSingleExperiment(r.config.PromptA, taskID, "A")
            r.resultsA = append(r.resultsA, resultA)

            // 執行 Prompt B
            resultB := r.runSingleExperiment(r.config.PromptB, taskID, "B")
            r.resultsB = append(r.resultsB, resultB)

            fmt.Printf("Task %s, Rep %d: A=%d iters, B=%d iters\n",
                taskID, i+1, resultA.Iterations, resultB.Iterations)
        }
    }
    return nil
}

// ‹6› 執行單次實驗
func (r *ABTestRunner) runSingleExperiment(prompt, taskID, version string) ExperimentResult {
    start := time.Now()

    // 執行 Ralph Loop
    loop := NewRalphLoop(RalphConfig{
        MaxIterations: r.config.MaxIterations,
        PromptContent: prompt,
    })

    result := loop.RunForTask(taskID)

    return ExperimentResult{
        PromptVersion: version,
        TaskID:        taskID,
        Iterations:    result.Iterations,
        TotalTime:     time.Since(start),
        TokensUsed:    result.TokensUsed,
        Success:       result.Success,
    }
}

// ‹7› 統計分析
type StatisticalAnalysis struct {
    MeanA, MeanB       float64
    StdDevA, StdDevB   float64
    TStatistic         float64
    PValue             float64
    EffectSize         float64  // Cohen's d
    Significant        bool
}

func (r *ABTestRunner) Analyze() StatisticalAnalysis {
    // 收集迭代次數數據
    dataA := make([]float64, len(r.resultsA))
    dataB := make([]float64, len(r.resultsB))

    for i, res := range r.resultsA {
        dataA[i] = float64(res.Iterations)
    }
    for i, res := range r.resultsB {
        dataB[i] = float64(res.Iterations)
    }

    // ‹8› 計算統計量
    meanA := mean(dataA)
    meanB := mean(dataB)
    stdDevA := stdDev(dataA, meanA)
    stdDevB := stdDev(dataB, meanB)

    // ‹9› 獨立樣本 t 檢定
    nA := float64(len(dataA))
    nB := float64(len(dataB))

    // 合併標準差
    pooledVar := ((nA-1)*stdDevA*stdDevA + (nB-1)*stdDevB*stdDevB) / (nA + nB - 2)
    pooledStd := math.Sqrt(pooledVar)

    // t 統計量
    tStat := (meanA - meanB) / (pooledStd * math.Sqrt(1/nA+1/nB))

    // ‹10› Cohen's d 效果量
    effectSize := (meanA - meanB) / pooledStd

    // 自由度
    df := nA + nB - 2

    // P 值（使用近似公式，實際應用應使用統計函式庫）
    pValue := approximatePValue(tStat, df)

    return StatisticalAnalysis{
        MeanA:      meanA,
        MeanB:      meanB,
        StdDevA:    stdDevA,
        StdDevB:    stdDevB,
        TStatistic: tStat,
        PValue:     pValue,
        EffectSize: effectSize,
        Significant: pValue < 0.05,
    }
}

// ‹11› 生成報告
func (r *ABTestRunner) GenerateReport() string {
    analysis := r.Analyze()

    report := fmt.Sprintf(`
# Prompt A/B 測試報告

## 實驗配置
- 測試任務數: %d
- 每任務重複次數: %d
- 總樣本數: %d (A) vs %d (B)

## 結果摘要

### Prompt A
- 平均迭代次數: %.2f
- 標準差: %.2f
- 成功率: %.1f%%

### Prompt B
- 平均迭代次數: %.2f
- 標準差: %.2f
- 成功率: %.1f%%

## 統計分析
- t 統計量: %.3f
- p 值: %.4f
- 效果量 (Cohen's d): %.3f
- 統計顯著 (p < 0.05): %v

## 結論
%s
`,
        len(r.config.TaskIDs),
        r.config.RepetitionsPerTask,
        len(r.resultsA), len(r.resultsB),
        analysis.MeanA, analysis.StdDevA, r.successRate(r.resultsA)*100,
        analysis.MeanB, analysis.StdDevB, r.successRate(r.resultsB)*100,
        analysis.TStatistic,
        analysis.PValue,
        analysis.EffectSize,
        analysis.Significant,
        r.generateConclusion(analysis),
    )

    return report
}

func (r *ABTestRunner) generateConclusion(analysis StatisticalAnalysis) string {
    if !analysis.Significant {
        return "結果不顯著，兩個 Prompt 版本沒有顯著差異。"
    }

    var effectDesc string
    absEffect := math.Abs(analysis.EffectSize)
    switch {
    case absEffect < 0.2:
        effectDesc = "極小"
    case absEffect < 0.5:
        effectDesc = "小"
    case absEffect < 0.8:
        effectDesc = "中等"
    default:
        effectDesc = "大"
    }

    if analysis.MeanB < analysis.MeanA {
        return fmt.Sprintf(
            "Prompt B 顯著優於 Prompt A，平均減少 %.1f 次迭代（效果量：%s）。建議採用 Prompt B。",
            analysis.MeanA-analysis.MeanB, effectDesc,
        )
    } else {
        return fmt.Sprintf(
            "Prompt A 顯著優於 Prompt B，平均減少 %.1f 次迭代（效果量：%s）。建議保留 Prompt A。",
            analysis.MeanB-analysis.MeanA, effectDesc,
        )
    }
}

// 輔助函數
func mean(data []float64) float64 {
    sum := 0.0
    for _, v := range data {
        sum += v
    }
    return sum / float64(len(data))
}

func stdDev(data []float64, mean float64) float64 {
    sum := 0.0
    for _, v := range data {
        diff := v - mean
        sum += diff * diff
    }
    return math.Sqrt(sum / float64(len(data)-1))
}

func (r *ABTestRunner) successRate(results []ExperimentResult) float64 {
    successes := 0
    for _, res := range results {
        if res.Success {
            successes++
        }
    }
    return float64(successes) / float64(len(results))
}
```

### 9.5.3 常見的 Prompt 優化方向

```
┌─────────────────────────────────────────────────────────────────┐
│                常見的 Prompt 優化方向                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. 結構優化                                                    │
│   ────────────────────────────────────────────                   │
│   Before: 純文字描述                                             │
│   After:  Markdown 結構（標題、列表、程式碼區塊）                │
│   效果:  通常減少 10-20% 迭代次數                                │
│                                                                 │
│   2. 範例優化                                                    │
│   ────────────────────────────────────────────                   │
│   Before: 無範例                                                 │
│   After:  1-3 個具體範例                                        │
│   效果:  在複雜任務上可減少 30-50% 迭代次數                      │
│                                                                 │
│   3. 約束明確化                                                  │
│   ────────────────────────────────────────────                   │
│   Before: 「不要改太多」                                        │
│   After:  「只修改 src/ 目錄，不修改 tests/」                    │
│   效果:  減少無效修改，提高成功率                               │
│                                                                 │
│   4. 驗證命令顯式化                                              │
│   ────────────────────────────────────────────                   │
│   Before: 「確保測試通過」                                      │
│   After:  「執行 `npm test`，確認 exit code 為 0」               │
│   效果:  減少模糊判斷，加速收斂                                 │
│                                                                 │
│   5. 流程分解                                                    │
│   ────────────────────────────────────────────                   │
│   Before: 「修復所有問題」                                      │
│   After:  「1. 診斷 2. 修復一個 3. 驗證 4. 重複」                │
│   效果:  減少一次性失敗，提高漸進成功率                         │
│                                                                 │
│   6. 提前退出條件                                                │
│   ────────────────────────────────────────────                   │
│   Before: 無                                                     │
│   After:  「如果連續 5 次沒有進展，停止並報告」                  │
│   效果:  避免無限迴圈，節省資源                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9.6 PROMPT.md 模板庫

以下提供針對不同任務類型的 PROMPT.md 模板。

### 9.6.1 模板：Bug 修復

```markdown
# 任務：Bug 修復

## 情境

[描述 bug 的現象和影響]

重現步驟：
1. [步驟 1]
2. [步驟 2]
3. [觀察到的錯誤行為]

期望行為：[描述應該發生什麼]

相關檔案：
- [檔案 1]
- [檔案 2]

## 目標

修復上述 bug，確保程式行為符合期望。

## 約束

- 只修改必要的程式碼，最小化變更範圍
- 不要引入新的依賴
- 保持向後相容
- 不要修改測試檔案（除非測試本身有問題）

## 完成條件

當以下所有條件都滿足時，此任務視為完成：

1. [ ] 原本的 bug 不再出現（可通過重現步驟驗證）
2. [ ] 相關測試通過：`npm test -- --grep "[相關測試名稱]"`
3. [ ] 所有測試通過：`npm test` 返回 exit code 0
4. [ ] 沒有引入新的 lint 警告：`npm run lint`

## 工作流程

1. **重現 Bug**
   - 執行重現步驟，確認 bug 存在
   - 理解 bug 的表現形式

2. **定位原因**
   - 閱讀相關程式碼
   - 使用 debugger 或 console.log 追蹤執行流程
   - 找出導致 bug 的具體程式碼行

3. **設計修復方案**
   - 思考多種可能的修復方式
   - 選擇最小化影響的方案
   - 考慮邊界條件

4. **實施修復**
   - 修改程式碼
   - 加入必要的註解說明修復邏輯

5. **驗證修復**
   - 執行重現步驟，確認 bug 已修復
   - 執行相關測試
   - 執行全部測試，確認無迴歸

## 注意事項

- 優先考慮根本原因，而非症狀處理
- 如果 bug 源於設計問題，記錄但不擴大修改範圍
- 修復後考慮是否需要新增測試案例
```

### 9.6.2 模板：功能實作

```markdown
# 任務：新功能實作

## 情境

[描述功能的背景和用途]

需求描述：
- [需求 1]
- [需求 2]
- [需求 3]

相關檔案：
- [參考的現有實作]
- [需要修改的檔案]

## 目標

實作上述功能，確保：
1. 功能正確運作
2. 與現有程式碼風格一致
3. 有適當的錯誤處理
4. 有對應的測試

## 約束

- 遵循專案的程式碼風格
- 使用現有的工具函數，不重複造輪子
- 保持函數/類別的單一職責
- 新增的測試覆蓋主要使用場景

## 完成條件

當以下所有條件都滿足時，此任務視為完成：

1. [ ] 功能按需求正確運作（可通過測試驗證）
2. [ ] 新增的測試通過：`npm test -- --grep "[功能名稱]"`
3. [ ] 所有測試通過：`npm test` 返回 exit code 0
4. [ ] 程式碼符合 lint 規則：`npm run lint`
5. [ ] 程式碼覆蓋率不下降：`npm run coverage`

## 工作流程

1. **理解需求**
   - 閱讀需求描述
   - 釐清任何模糊之處
   - 確定輸入、輸出、邊界條件

2. **設計 API**
   - 定義函數/方法的簽名
   - 設計資料結構
   - 考慮錯誤處理策略

3. **撰寫測試（TDD）**
   - 先寫測試案例
   - 涵蓋正常情況和邊界情況
   - 測試應該先失敗

4. **實作功能**
   - 逐步實作，讓測試逐個通過
   - 保持程式碼簡潔
   - 適時重構

5. **整合驗證**
   - 確保與現有程式碼正確整合
   - 執行全部測試
   - 檢查程式碼品質

## 注意事項

- 不要過度設計，只實作需求中要求的功能
- 如果發現需求有問題，先記錄再繼續
- 優先可讀性，其次效能（除非效能是需求的一部分）
```

### 9.6.3 模板：程式碼重構

```markdown
# 任務：程式碼重構

## 情境

[描述為什麼需要重構]

現有問題：
- [問題 1：例如程式碼重複]
- [問題 2：例如職責不清]
- [問題 3：例如效能問題]

涉及檔案：
- [檔案 1]
- [檔案 2]

## 目標

在不改變外部行為的前提下，改善程式碼的內部結構。

重構目標：
1. [目標 1：例如消除重複]
2. [目標 2：例如提取類別]
3. [目標 3：例如改善命名]

## 約束

- **行為不變**：所有現有測試必須繼續通過
- 每次只做一種重構
- 每次重構後都要執行測試
- 不順便添加新功能

## 完成條件

當以下所有條件都滿足時，此任務視為完成：

1. [ ] 所有測試通過：`npm test` 返回 exit code 0
2. [ ] 程式碼符合 lint 規則：`npm run lint`
3. [ ] 重複程式碼減少：[具體指標，如 DRY 分數]
4. [ ] 沒有 TODO 或 FIXME 標記：`grep -r "TODO\|FIXME" src/`

## 工作流程

1. **建立安全網**
   - 確認所有測試通過
   - 如果覆蓋率不足，先補充測試

2. **識別重構機會**
   - 使用工具分析程式碼品質
   - 列出可以改善的點

3. **一次一個重構**
   對於每個重構：
   a. 理解要改變什麼
   b. 執行重構
   c. 執行測試
   d. 如果測試失敗，回滾
   e. 如果測試通過，commit

4. **驗證最終結果**
   - 所有測試通過
   - 程式碼品質指標改善
   - 行為沒有改變

## 常見重構手法

- **提取函數（Extract Function）**：將重複的程式碼提取為函數
- **內聯函數（Inline Function）**：將只被呼叫一次的小函數展開
- **提取變數（Extract Variable）**：為複雜表達式命名
- **重新命名（Rename）**：改善命名以提高可讀性
- **移動函數（Move Function）**：將函數移到更適當的模組
- **提取類別（Extract Class）**：將相關的資料和行為封裝

## 注意事項

- 不要在重構時修復 bug（除非 bug 與重構直接相關）
- 不要在重構時優化效能
- 保持每次 commit 的原子性
- 如果不確定某個改動是否安全，先不要做
```

### 9.6.4 模板：測試撰寫

```markdown
# 任務：測試覆蓋率提升

## 情境

專案的測試覆蓋率需要提升。目前覆蓋率為 [X]%，目標是達到 [Y]%。

覆蓋率報告位置：
[coverage/lcov-report/index.html 或其他位置]

優先處理的模組：
- [覆蓋率最低或最重要的模組 1]
- [模組 2]

## 目標

1. 將整體測試覆蓋率從 [X]% 提升至 [Y]%
2. 為低覆蓋率的檔案新增有意義的測試
3. 確保新增的測試都能通過
4. 測試要涵蓋邊界條件和錯誤處理

## 約束

- 只新增測試，不修改原始碼（除非發現 bug）
- 測試要有意義，不是為了覆蓋率而覆蓋
- 遵循專案現有的測試風格
- 每個測試檔案對應一個原始碼檔案

## 完成條件

當以下所有條件都滿足時，此任務視為完成：

1. [ ] 覆蓋率達到目標：`npm run coverage` 顯示 >= [Y]%
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

### 9.6.5 模板：文件生成

```markdown
# 任務：API 文件生成

## 情境

專案需要為 [模組/API] 生成技術文件。

涉及檔案：
- [原始碼檔案]

文件輸出位置：
- [docs/api/xxx.md]

## 目標

為指定的 API 生成完整的技術文件，包含：
1. 函數/類別說明
2. 參數說明
3. 返回值說明
4. 使用範例
5. 注意事項

## 約束

- 使用 Markdown 格式
- 範例程式碼要可執行
- 保持與現有文件風格一致
- 不要編造不存在的 API

## 完成條件

當以下所有條件都滿足時，此任務視為完成：

1. [ ] 文件檔案存在且格式正確
2. [ ] 所有公開 API 都有文件說明
3. [ ] 範例程式碼可以通過 lint 檢查
4. [ ] 無拼寫錯誤（可用 `npx cspell "docs/**/*.md"` 檢查）

## 工作流程

1. **閱讀原始碼**
   - 識別所有公開的 API
   - 理解每個 API 的用途

2. **生成文件框架**
   - 為每個 API 建立文件區塊
   - 包含標準的標題結構

3. **撰寫詳細說明**
   - 為每個參數加上類型和說明
   - 說明返回值
   - 加入使用範例

4. **驗證文件品質**
   - 檢查範例程式碼是否正確
   - 檢查是否有遺漏的 API
   - 檢查拼寫和格式

## 文件模板

```markdown
## functionName

簡短說明函數的用途。

### 語法

```typescript
functionName(param1: Type1, param2?: Type2): ReturnType
```

### 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| param1 | Type1 | 是 | 參數說明 |
| param2 | Type2 | 否 | 參數說明，預設值為 xxx |

### 返回值

`ReturnType` - 返回值說明

### 範例

```typescript
// 基本使用
const result = functionName('hello', 123);

// 使用可選參數
const result2 = functionName('world');
```

### 注意事項

- 注意事項 1
- 注意事項 2
```
```

### 9.6.6 模板：效能優化

```markdown
# 任務：效能優化

## 情境

[描述效能問題的現象]

當前效能指標：
- [指標 1]：[當前值]
- [指標 2]：[當前值]

目標效能指標：
- [指標 1]：[目標值]
- [指標 2]：[目標值]

涉及檔案：
- [檔案 1]
- [檔案 2]

## 目標

在不改變功能的前提下，提升效能以達到目標指標。

## 約束

- 所有測試必須繼續通過
- 不犧牲可讀性換取過度的效能提升
- 優化要有可測量的效果
- 加入效能測試以防止未來的迴歸

## 完成條件

當以下所有條件都滿足時，此任務視為完成：

1. [ ] 效能指標達標：[具體的 benchmark 命令]
2. [ ] 所有測試通過：`npm test` 返回 exit code 0
3. [ ] 效能測試存在且通過

## 工作流程

1. **建立基準線**
   ```bash
   npm run benchmark > baseline.txt
   ```

2. **效能分析**
   - 使用 profiler 找出熱點
   - 識別可優化的區域

3. **逐步優化**
   對於每個優化：
   a. 明確優化目標
   b. 實施優化
   c. 執行測試確認功能正確
   d. 執行 benchmark 確認效能提升
   e. 如果效能下降或功能錯誤，回滾

4. **驗證最終結果**
   ```bash
   npm run benchmark > after.txt
   diff baseline.txt after.txt
   ```

## 常見優化手法

- **快取計算結果**：避免重複計算
- **惰性載入**：延遲載入不立即需要的資源
- **批次處理**：將多次操作合併為一次
- **資料結構優化**：選擇適當的資料結構
- **演算法優化**：使用更高效的演算法
- **平行化**：利用多核心處理

## 注意事項

- 先量測，再優化
- 不要過早優化
- 確保優化是針對真正的瓶頸
- 記錄優化的理由和效果
```

---

## 9.7 常見陷阱與解決方案

### 9.7.1 陷阱清單

```
┌─────────────────────────────────────────────────────────────────┐
│                    常見 Prompt 設計陷阱                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   陷阱 1：模糊的完成條件                                        │
│   ──────────────────────                                         │
│   症狀：迴圈無限運行或過早停止                                  │
│   原因：Agent 無法判斷何時算「完成」                            │
│   解決：使用可機器驗證的條件，附帶具體的驗證命令               │
│                                                                 │
│   ❌ 「修好就可以了」                                           │
│   ✅ 「`npm test` 返回 exit code 0」                             │
│                                                                 │
│   陷阱 2：過於嚴格的約束                                        │
│   ──────────────────────                                         │
│   症狀：Agent 無法進展，反覆嘗試同樣的失敗路徑                  │
│   原因：約束條件互相矛盾或不可能同時滿足                       │
│   解決：檢查約束的合理性，放寬非關鍵限制                       │
│                                                                 │
│   ❌ 「不要修改任何現有程式碼」（修 bug 時）                    │
│   ✅ 「最小化修改，只改必要的部分」                             │
│                                                                 │
│   陷阱 3：缺乏回饋機制                                          │
│   ──────────────────────                                         │
│   症狀：Agent 重複同樣的錯誤                                    │
│   原因：Agent 看不到自己行動的結果                              │
│   解決：明確要求執行驗證命令並觀察輸出                         │
│                                                                 │
│   ❌ 「修改後讓我知道」                                         │
│   ✅ 「修改後執行 `npm test`，分析輸出」                        │
│                                                                 │
│   陷阱 4：資訊過載                                              │
│   ──────────────────────                                         │
│   症狀：Agent 忽略重要指令，或混淆不同指令                      │
│   原因：Prompt 包含太多資訊，超過有效處理能力                   │
│   解決：精簡內容，使用層級結構，突出重點                       │
│                                                                 │
│   ❌ 長達 50 頁的詳細規範                                       │
│   ✅ 精簡的核心指令 + 「詳情見 docs/spec.md」                   │
│                                                                 │
│   陷阱 5：隱含假設                                              │
│   ──────────────────────                                         │
│   症狀：Agent 的理解與預期不符                                  │
│   原因：Prompt 中有未明說的假設                                 │
│   解決：明確說明所有假設和前提條件                             │
│                                                                 │
│   ❌ 「更新用戶資料」（假設 Agent 知道用戶資料結構）            │
│   ✅ 「更新 users 表的 email 欄位，結構見 schema.sql」          │
│                                                                 │
│   陷阱 6：缺乏提前退出機制                                      │
│   ──────────────────────                                         │
│   症狀：遇到無法解決的問題時無限嘗試                            │
│   原因：沒有定義何時應該停止並尋求幫助                         │
│   解決：設定提前退出條件和最大迭代次數                         │
│                                                                 │
│   ❌ 「持續嘗試直到成功」                                       │
│   ✅ 「如果連續 10 次沒有進展，停止並報告問題」                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9.8 本章小結

本章深入探討了 Prompt 工程的理論基礎與實踐技巧，從認知科學到具體模板設計。

### 關鍵要點

1. **理論基礎**
   - Grice 的合作原則指導 Prompt 撰寫
   - 認知負荷理論指導資訊組織
   - 指令微調背景影響 Prompt 結構

2. **遊樂場隱喻**
   - 明確邊界
   - 可見回饋
   - 可重複嘗試
   - 漸進挑戰

3. **Completion Promise**
   - 可機器驗證的條件
   - 明確的驗證命令
   - 提前退出機制

4. **控制流程**
   - 狀態機模型
   - 分階段設計
   - 迭代優先

5. **A/B 測試**
   - 科學方法論
   - 統計顯著性
   - 持續優化

6. **模板庫**
   - Bug 修復
   - 功能實作
   - 程式碼重構
   - 測試撰寫
   - 文件生成
   - 效能優化

### 練習題

1. **基礎練習**：將以下模糊需求轉化為 Completion Promise：「讓網站載入更快一點」。

2. **應用練習**：使用 Bug 修復模板，為你手邊的一個實際 bug 撰寫 PROMPT.md。

3. **進階練習**：設計一個 A/B 測試，比較「有範例」vs「無範例」的 Prompt 在特定任務上的效果。

4. **分析練習**：找出以下 Prompt 的三個問題並改進：
   ```
   把程式碼弄好，要快一點，不要有 bug。
   改完告訴我。
   ```

---

## 學術參考文獻

1. Grice, H. P. (1975). Logic and conversation. In *Syntax and Semantics*, Vol. 3, Speech Acts. Academic Press.

2. Miller, G. A. (1956). The magical number seven, plus or minus two. *Psychological Review*, 63(2), 81-97.

3. Sweller, J. (1988). Cognitive load during problem solving. *Cognitive Science*, 12(2), 257-285.

4. Ouyang, L., et al. (2022). Training language models to follow instructions with human feedback. *arXiv preprint arXiv:2203.02155*.

5. Wei, J., et al. (2022). Chain-of-thought prompting elicits reasoning in large language models. *NeurIPS 2022*.

---

## 下一章預告

掌握了 Prompt 工程後，我們進入第四部分：實戰應用。第 10 章將探討 Ralph Loop 的適用場景與成本經濟學，包括 Token 定價模型、ROI 計算，以及那個用 $297 完成 $50,000 合約的傳奇案例。
