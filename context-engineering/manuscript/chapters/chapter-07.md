# 第 7 章：Ralph Wiggum：五行程式碼的革命

> 確定性的失敗勝過非確定性的成功
> — Geoffrey Huntley

---

## 本章學習目標

完成本章後，你將能夠：

- 描述 Ralph Wiggum Loop 的起源與設計哲學
- 理解迭代學習的理論基礎與強化學習概念
- 解釋為何「確定性的失敗勝過非確定性的成功」
- 理解 Git 作為 AI 記憶層的角色及其學術背景
- 分析 Ralph Loop 的收斂性條件
- 從零實作你的第一個 Ralph Loop
- 設計有效的收斂條件並避免常見陷阱

---

## 7.1 澳洲山羊農場的頓悟

2025 年中的某個清晨，Geoffrey Huntley 在他位於澳洲鄉村的山羊農場上，一邊餵養山羊，一邊思考一個困擾他許久的問題：

> 「為什麼我們總是期待 AI 一次就做對？人類學習任何技能不都是透過不斷嘗試和失敗嗎？」

這個看似簡單的問題，催生了一個改變許多開發者工作方式的技術——Ralph Wiggum Loop。

### 7.1.1 靈感來源：為何叫 Ralph Wiggum？

這個名字來自《辛普森家庭》中的角色 Ralph Wiggum——一個常常說出看似愚蠢但偶爾極富洞察力的話的孩子。Huntley 選擇這個名字，是因為：

```
┌─────────────────────────────────────────────────────────────────┐
│                   Ralph Wiggum 的啟示                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   "我的貓咪的呼吸聞起來像貓糧"                                   │
│        — Ralph Wiggum                                           │
│                                                                 │
│   看似無意義的話語，背後卻有邏輯：                               │
│   貓吃貓糧 → 呼吸聞起來像貓糧                                    │
│                                                                 │
│   Ralph Loop 的哲學：                                           │
│   看似「愚蠢」的無限嘗試，其實是最可靠的學習方式                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

傳統的 AI 使用模式追求「一次成功」——精心設計 Prompt，期待模型產出完美結果。但現實是，即使是最強大的 LLM，在複雜任務上也難以一次做對。Ralph Wiggum Loop 的革命性在於：**接受失敗作為常態，並將其轉化為學習機會**。

### 7.1.2 最初的實驗

Huntley 的第一個實驗是讓 Claude 自動修復一個有 127 個測試失敗的舊專案。他沒有精心設計複雜的 Prompt，而是簡單地：

```bash
# Huntley 的第一個 Ralph Loop 實驗
while true; do
    claude --prompt "修復測試。執行 npm test，分析失敗原因，修改程式碼。重複直到所有測試通過。" \
           --dangerously-skip-permissions
    git add -A && git commit -m "checkpoint"
done
```

結果令人驚訝：經過 47 次迭代，所有 127 個測試都通過了。每次迭代 Claude 都會：
1. 執行測試，看到失敗
2. 分析錯誤訊息
3. 嘗試修復
4. 提交變更
5. 重複

這個簡單的實驗揭示了一個深刻的道理：**迭代比完美更重要**。

---

## 7.2 迭代學習的理論基礎

要理解 Ralph Wiggum Loop 為什麼有效，我們需要從機器學習的理論基礎談起。

### 7.2.1 強化學習（Reinforcement Learning）概述

Ralph Loop 的運作原理與強化學習（Reinforcement Learning, RL）有深刻的關聯。在 RL 中，一個 **Agent** 透過與 **環境** 互動來學習，核心概念包括：

```
┌─────────────────────────────────────────────────────────────────┐
│              強化學習的基本框架（Sutton & Barto, 2018）           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    ┌─────────────────┐                          │
│                    │    Agent        │                          │
│                    │  (學習者/決策者) │                          │
│                    └────────┬────────┘                          │
│                             │                                   │
│              動作 at        │         狀態 st, 獎勵 rt          │
│                    ┌────────┴────────┐                          │
│                    ▼                 ▲                          │
│            ┌─────────────────────────────────┐                  │
│            │          Environment            │                  │
│            │           (環境)                │                  │
│            └─────────────────────────────────┘                  │
│                                                                 │
│   目標：找到策略 π(a|s) 以最大化累積獎勵                         │
│                                                                 │
│   J(π) = E[Σ γᵗ rₜ]                                            │
│                                                                 │
│   其中 γ ∈ [0,1] 是折扣因子                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

在 Ralph Loop 的情境中：

| RL 概念 | Ralph Loop 對應 |
|---------|-----------------|
| Agent | Claude（或其他 LLM） |
| Environment | 程式碼庫 + 測試框架 + 編譯器 |
| State | 當前程式碼狀態 + 錯誤訊息 |
| Action | 程式碼修改 |
| Reward | 測試通過數量、錯誤減少數量 |
| Episode | 一次完整的迭代（從修改到 commit） |

### 7.2.2 探索與利用的權衡（Exploration vs. Exploitation）

強化學習中最核心的挑戰之一是**探索與利用的權衡**（Exploration-Exploitation Tradeoff）：

- **利用（Exploitation）**：選擇目前已知最佳的行動
- **探索（Exploration）**：嘗試新的、未知的行動，希望發現更好的策略

```
┌─────────────────────────────────────────────────────────────────┐
│                探索與利用的權衡                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   純利用風險：                      純探索風險：                 │
│   ┌─────────────────┐              ┌─────────────────┐          │
│   │ 陷入局部最優    │              │ 效率極低        │          │
│   │ 錯過更好的解法  │              │ 永遠不收斂      │          │
│   └─────────────────┘              └─────────────────┘          │
│                                                                 │
│   最佳策略：隨時間調整探索率                                     │
│                                                                 │
│   ε-greedy 策略：                                               │
│   - 以機率 ε 探索（隨機選擇動作）                                │
│   - 以機率 1-ε 利用（選擇目前最佳動作）                          │
│   - ε 隨時間遞減：εₜ = max(ε_min, ε₀ × decay^t)                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Ralph Loop 如何處理這個權衡？

1. **天然探索**：LLM 的隨機性（temperature > 0）提供自然的探索
2. **錯誤引導**：錯誤訊息提供環境回饋，引導利用
3. **Git 記憶**：成功的修改被保留（利用），失敗可回溯（探索新方向）

### 7.2.3 經驗回放（Experience Replay）

在 Deep Q-Learning 中，一個關鍵技術是**經驗回放**（Experience Replay，Mnih et al., 2015）：

```
┌─────────────────────────────────────────────────────────────────┐
│                    經驗回放機制                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   傳統在線學習：                                                 │
│   [經驗1] → 學習 → 丟棄 → [經驗2] → 學習 → 丟棄 → ...          │
│                                                                 │
│   問題：                                                         │
│   1. 經驗只使用一次                                              │
│   2. 連續經驗高度相關（破壞 i.i.d. 假設）                        │
│   3. 無法從過去學習                                              │
│                                                                 │
│   經驗回放：                                                     │
│   ┌──────────────────────────────────┐                          │
│   │     Replay Buffer               │                          │
│   │   ┌─────┬─────┬─────┬─────┐    │                          │
│   │   │ e₁  │ e₂  │ e₃  │ ... │    │    隨機採樣               │
│   │   └─────┴─────┴─────┴─────┘    │ ───────────→ 訓練        │
│   │        ↑                        │                          │
│   │      新經驗                      │                          │
│   └──────────────────────────────────┘                          │
│                                                                 │
│   Ralph Loop 的經驗回放 = Git History                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

在 Ralph Loop 中，**Git 就是經驗回放的 Buffer**：
- 每次 commit 記錄一次「經驗」
- Claude 可以回顧 git log 看到過去的嘗試
- 失敗的嘗試也被記錄，避免重複相同錯誤
- `git diff` 讓 Agent 理解「什麼改變導致什麼結果」

### 7.2.4 策略梯度與 Credit Assignment

強化學習的另一個核心挑戰是**Credit Assignment Problem**——當一系列動作後才得到獎勵時，如何判斷是哪個動作導致了成功或失敗？

```
┌─────────────────────────────────────────────────────────────────┐
│                    Credit Assignment 問題                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   動作序列：   a₁    →    a₂    →    a₃    →    獎勵 +10        │
│                                                                 │
│   問題：a₁、a₂、a₃ 各自的貢獻是多少？                           │
│                                                                 │
│   解法：                                                         │
│   1. 時序差分學習（TD Learning）                                 │
│      V(sₜ) ← V(sₜ) + α[rₜ + γV(sₜ₊₁) - V(sₜ)]                  │
│                                                                 │
│   2. Monte Carlo 回報計算                                       │
│      G = Σ γᵏ rₜ₊ₖ₊₁                                           │
│                                                                 │
│   Ralph Loop 的解法：細粒度 Commit                               │
│   - 每個小變更都 commit                                          │
│   - 測試結果與特定 commit 直接關聯                               │
│   - 失敗可精確追溯到特定修改                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Ralph Loop 透過**頻繁的 git commit** 解決 Credit Assignment：
- 每次迭代只做一件事
- 立即執行測試，獲得即時回饋
- 如果測試失敗，清楚知道是這次修改造成的
- 可以 `git revert` 回到上一個穩定狀態

---

## 7.3 Git 作為記憶層：學術背景與實作

Git 在 Ralph Loop 中扮演的角色，遠比一般認知的「版本控制」更為深刻。

### 7.3.1 版本控制系統的演進

版本控制系統（Version Control System, VCS）的歷史可以追溯到 1970 年代：

```
┌─────────────────────────────────────────────────────────────────┐
│               版本控制系統演進史                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1972: SCCS (Source Code Control System)                       │
│         └─ Bell Labs, 單檔案版本控制                            │
│                                                                 │
│   1982: RCS (Revision Control System)                           │
│         └─ GNU, 改進 SCCS 的效率                                │
│                                                                 │
│   1986: CVS (Concurrent Versions System)                        │
│         └─ 多人協作, Client-Server 架構                         │
│                                                                 │
│   2000: SVN (Subversion)                                        │
│         └─ 改進 CVS 的缺點, 原子提交                            │
│                                                                 │
│   2005: Git                                                     │
│         └─ Linus Torvalds, 分散式, 非線性歷史                   │
│                                                                 │
│   Git 的革命性創新：                                             │
│   • 每個 commit 是完整快照，不是差異                            │
│   • SHA-1 雜湊確保完整性                                        │
│   • 分支和合併極為高效                                          │
│   • 完全分散式，本地即完整歷史                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3.2 Git 的內部結構

理解 Git 如何作為「記憶層」，需要了解其內部資料結構：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Git 物件模型                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   .git/objects/ 目錄下的四種物件：                               │
│                                                                 │
│   1. Blob（檔案內容）                                            │
│      ┌────────────────────┐                                     │
│      │ blob 1234567890ab  │ ← SHA-1 雜湊                        │
│      │ 檔案實際內容       │                                     │
│      └────────────────────┘                                     │
│                                                                 │
│   2. Tree（目錄結構）                                            │
│      ┌────────────────────────────────────────┐                 │
│      │ tree 0987654321cd                       │                │
│      │ 100644 blob a1b2c3  README.md          │                │
│      │ 040000 tree d4e5f6  src/               │                │
│      └────────────────────────────────────────┘                 │
│                                                                 │
│   3. Commit（提交記錄）                                          │
│      ┌────────────────────────────────────────┐                 │
│      │ commit abc123def456                     │                │
│      │ tree 0987654321cd                       │                │
│      │ parent 111222333444                     │                │
│      │ author ...                              │                │
│      │ message: "修復登入 bug"                 │                │
│      └────────────────────────────────────────┘                 │
│                                                                 │
│   4. Tag（標籤）                                                 │
│      ┌────────────────────┐                                     │
│      │ tag v1.0.0         │                                     │
│      │ object abc123...   │                                     │
│      └────────────────────┘                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3.3 Git 作為 Content-Addressable Storage

Git 的設計本質上是一個**內容可定址儲存系統**（Content-Addressable Storage, CAS）：

```go
// ‹1› Git 的核心概念：內容即地址
func computeGitHash(content []byte, objectType string) string {
    // ‹2› Git 物件格式: "{type} {size}\0{content}"
    header := fmt.Sprintf("%s %d\x00", objectType, len(content))
    data := append([]byte(header), content...)

    // ‹3› SHA-1 雜湊產生 40 字元的十六進位字串
    hash := sha1.Sum(data)
    return hex.EncodeToString(hash[:])
}

// 範例：
// content = "Hello, World!"
// hash = computeGitHash([]byte(content), "blob")
// => "b45ef6fec89518d314f546fd6c3025367b721684"
```

**關鍵性質**：
- 相同內容 → 相同雜湊 → 自動去重
- 任何修改 → 不同雜湊 → 完整保留歷史
- 雜湊可驗證 → 確保資料完整性

### 7.3.4 為何 Git 適合作為 AI 記憶層？

```
┌─────────────────────────────────────────────────────────────────┐
│            Git 作為 AI 記憶層的優勢                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. 完整性（Integrity）                                        │
│      └─ SHA-1 雜湊確保記憶不被竄改                              │
│                                                                 │
│   2. 可追溯性（Traceability）                                   │
│      └─ 每個狀態都有父指標，可回溯完整歷史                      │
│                                                                 │
│   3. 原子性（Atomicity）                                        │
│      └─ Commit 是原子操作，狀態轉換要嘛成功要嘛失敗             │
│                                                                 │
│   4. 可分支性（Branchability）                                  │
│      └─ 可以嘗試多個方向，最後選擇最佳路徑                      │
│                                                                 │
│   5. 可合併性（Mergeability）                                   │
│      └─ 不同嘗試的成果可以合併                                  │
│                                                                 │
│   6. 效率（Efficiency）                                         │
│      └─ Delta compression, packfiles 確保空間效率               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

與其他記憶機制的比較：

| 記憶機制 | 持久性 | 可追溯 | 可分支 | 可合併 | 效率 |
|----------|--------|--------|--------|--------|------|
| 對話歷史 | ❌ | ❌ | ❌ | ❌ | 低 |
| 檔案系統快照 | ✅ | ❌ | ❌ | ❌ | 低 |
| 資料庫 | ✅ | ⚠️ | ❌ | ❌ | 中 |
| Git | ✅ | ✅ | ✅ | ✅ | 高 |

---

## 7.4 確定性的失敗 vs 非確定性的成功

Ralph Wiggum Loop 的核心哲學是：

> **「確定性的失敗勝過非確定性的成功」**

這句話乍聽矛盾，但蘊含深刻的道理。

### 7.4.1 什麼是非確定性的成功？

傳統 AI 使用模式的問題：

```
┌─────────────────────────────────────────────────────────────────┐
│                非確定性的成功：傳統模式                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   精心設計的 Prompt                                              │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────────────────────────────────┐                   │
│   │              LLM 推論                    │                   │
│   │  （黑箱，無法完全控制輸出）              │                   │
│   └──────────────┬──────────────────────────┘                   │
│                  │                                              │
│         ┌───────┴───────┐                                       │
│         ▼               ▼                                       │
│   ┌──────────┐    ┌──────────┐                                  │
│   │   成功   │    │   失敗   │                                  │
│   │  (70%?)  │    │  (30%?)  │                                  │
│   └──────────┘    └──────────┘                                  │
│                        │                                        │
│                        ▼                                        │
│                  重新開始...                                     │
│                 （失去所有進度）                                 │
│                                                                 │
│   問題：                                                         │
│   1. 成功與否不可預測                                            │
│   2. 失敗時沒有累積                                              │
│   3. 無法從失敗中學習                                            │
│   4. 每次嘗試都是獨立的                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.4.2 什麼是確定性的失敗？

Ralph Loop 的模式：

```
┌─────────────────────────────────────────────────────────────────┐
│                確定性的失敗：Ralph Loop 模式                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   PROMPT.md + 當前狀態                                           │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────────────────────────────────┐                   │
│   │              LLM 推論                    │                   │
│   │    嘗試解決問題（可能失敗）              │                   │
│   └──────────────┬──────────────────────────┘                   │
│                  │                                              │
│                  ▼                                              │
│   ┌──────────────────────────────────────────┐                  │
│   │          git add && git commit           │                  │
│   │        （無論成功失敗都記錄）            │                  │
│   └──────────────┬───────────────────────────┘                  │
│                  │                                              │
│         ┌───────┴───────┐                                       │
│         ▼               ▼                                       │
│   ┌──────────┐    ┌──────────────┐                              │
│   │   成功   │    │    失敗      │                              │
│   │  (停止)  │    │ (記錄 + 下次迭代) │                         │
│   └──────────┘    └──────────────┘                              │
│                        │                                        │
│                        ▼                                        │
│            錯誤訊息成為下次輸入                                  │
│           （累積學習，不斷進步）                                 │
│                                                                 │
│   特性：                                                         │
│   1. 每次失敗都被預期且記錄                                      │
│   2. 失敗資訊作為學習素材                                        │
│   3. 進度持續累積                                                │
│   4. 最終必定收斂（有正確收斂條件的前提下）                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.4.3 數學上的保證

讓我們用機率來分析兩種模式：

**傳統模式**：
- 單次成功機率：p = 0.7
- n 次嘗試至少一次成功的機率：P(success) = 1 - (1-p)ⁿ
- 問題：即使成功，不知道「為什麼成功」

**Ralph Loop 模式**：
- 假設每次迭代有 10% 機會修復一個問題
- 假設總共有 k 個問題需要修復
- 每次迭代後，剩餘問題數為：E[problems_t+1] = E[problems_t] × 0.9
- 經過 t 次迭代：E[problems_t] = k × 0.9^t
- 問題歸零的期望迭代次數：O(k × log(k))

```
┌─────────────────────────────────────────────────────────────────┐
│                    收斂性數學分析                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   假設：                                                         │
│   - 初始問題數 k = 100                                          │
│   - 每次迭代修復機率 p = 0.1                                    │
│                                                                 │
│   期望剩餘問題數：                                               │
│                                                                 │
│   迭代  │ 期望剩餘問題                                          │
│   ──────┼─────────────────                                       │
│     0   │    100                                                 │
│    10   │    100 × 0.9¹⁰ ≈ 35                                   │
│    20   │    100 × 0.9²⁰ ≈ 12                                   │
│    30   │    100 × 0.9³⁰ ≈  4                                   │
│    40   │    100 × 0.9⁴⁰ ≈  1                                   │
│    50   │    100 × 0.9⁵⁰ ≈ 0.5                                  │
│                                                                 │
│   收斂速度：指數衰減 O(e^{-pt})                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7.5 收斂性分析

Ralph Loop 是否總是會收斂？什麼條件下會收斂？這是一個關鍵問題。

### 7.5.1 收斂的必要條件

```
┌─────────────────────────────────────────────────────────────────┐
│               Ralph Loop 收斂的必要條件                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   條件 1：問題可分解（Decomposability）                          │
│   ───────────────────────────────────────                        │
│   複雜問題可以分解為獨立子問題                                   │
│   ✅ 127 個測試 → 127 個獨立的失敗原因                          │
│   ❌ 高度耦合的系統，修一個破另一個                             │
│                                                                 │
│   條件 2：回饋可觀察（Observable Feedback）                      │
│   ─────────────────────────────────────────                      │
│   Agent 能夠看到自己行動的結果                                   │
│   ✅ 測試輸出明確顯示哪些通過/失敗                              │
│   ❌ 「這個設計好不好看？」（主觀，無法自動驗證）               │
│                                                                 │
│   條件 3：狀態空間有限（Finite State Space）                     │
│   ────────────────────────────────────────────                   │
│   可能的程式碼狀態數量有限                                       │
│   ✅ 修復已知 bug（有限的修改可能）                             │
│   ❌ 「寫一個完美的 AI」（無限的可能性）                        │
│                                                                 │
│   條件 4：正向進展概率 > 0（Positive Progress）                  │
│   ─────────────────────────────────────────────                  │
│   每次迭代有非零機會向目標前進                                   │
│   P(improvement | current_state) > 0                             │
│                                                                 │
│   條件 5：無無限迴圈（No Infinite Loops）                        │
│   ─────────────────────────────────────────                      │
│   不會在固定的狀態集合中無限循環                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.5.2 收斂定理（非正式陳述）

**定理**：若 Ralph Loop 滿足以下條件，則幾乎必然在有限時間內收斂：

1. 任務有明確的成功狀態 S*
2. 從任意狀態 s，存在長度有限的路徑到達 S*
3. LLM 在每一步有非零機率選擇正確路徑上的動作
4. Git 正確記錄所有狀態轉換

**直覺證明**：
- 每個狀態到 S* 都有非零機率的轉換序列
- 經過足夠多次嘗試，該序列必然會被執行
- 這是隨機遊走（Random Walk）在吸收態問題的經典結果

### 7.5.3 不收斂的情況

```
┌─────────────────────────────────────────────────────────────────┐
│                  不收斂的常見原因                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. 循環依賴（Circular Dependencies）                           │
│   ┌────────────────────────────────────────┐                    │
│   │   修復 A → 破壞 B → 修復 B → 破壞 A → ...                  │
│   │                                                            │
│   │   狀態空間：A ↔ B ↔ A ↔ B ...                              │
│   └────────────────────────────────────────┘                    │
│   解決方案：一次性重構，而非逐個修復                             │
│                                                                 │
│   2. 目標不可達（Unreachable Goal）                              │
│   ┌────────────────────────────────────────┐                    │
│   │   「讓程式執行速度提升 1000 倍」                            │
│   │   物理上可能不可行                                          │
│   └────────────────────────────────────────┘                    │
│   解決方案：設定可達成的目標                                     │
│                                                                 │
│   3. 回饋不明確（Ambiguous Feedback）                            │
│   ┌────────────────────────────────────────┐                    │
│   │   測試：「輸出應該看起來正確」                              │
│   │   Agent 無法判斷是否成功                                    │
│   └────────────────────────────────────────┘                    │
│   解決方案：使用可機器驗證的條件                                 │
│                                                                 │
│   4. 狀態空間爆炸（State Space Explosion）                       │
│   ┌────────────────────────────────────────┐                    │
│   │   每個修改打開更多可能性                                    │
│   │   搜索空間指數增長                                          │
│   └────────────────────────────────────────┘                    │
│   解決方案：限制每次修改的範圍                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.5.4 收斂速度分析

影響收斂速度的因素：

| 因素 | 影響 | 優化策略 |
|------|------|----------|
| 問題複雜度 | 問題越多，收斂越慢 | 分階段處理 |
| 回饋品質 | 回饋越精確，收斂越快 | 改進錯誤訊息 |
| LLM 能力 | 模型越強，收斂越快 | 使用更強的模型 |
| Prompt 品質 | Prompt 越好，收斂越快 | 最佳化 PROMPT.md |
| 初始狀態 | 離目標越近，收斂越快 | 手動修復明顯問題 |

---

## 7.6 實作：你的第一個 Ralph Loop

現在讓我們從零開始建構一個完整的 Ralph Loop。

### 7.6.1 環境準備

```bash
# ‹1› 建立專案目錄
mkdir ralph-demo && cd ralph-demo

# ‹2› 初始化 Git 儲存庫
git init

# ‹3› 建立一個有問題的程式碼（故意有 bug）
cat > calculator.go << 'EOF'
package main

import "fmt"

// Add returns the sum of two numbers
func Add(a, b int) int {
    return a - b  // Bug: should be a + b
}

// Subtract returns the difference of two numbers
func Subtract(a, b int) int {
    return a + b  // Bug: should be a - b
}

// Multiply returns the product of two numbers
func Multiply(a, b int) int {
    return a + b  // Bug: should be a * b
}

// Divide returns the quotient of two numbers
func Divide(a, b int) int {
    return a * b  // Bug: should be a / b
}

func main() {
    fmt.Println("Calculator ready")
}
EOF

# ‹4› 建立測試檔案
cat > calculator_test.go << 'EOF'
package main

import "testing"

func TestAdd(t *testing.T) {
    result := Add(2, 3)
    if result != 5 {
        t.Errorf("Add(2, 3) = %d; want 5", result)
    }
}

func TestSubtract(t *testing.T) {
    result := Subtract(5, 3)
    if result != 2 {
        t.Errorf("Subtract(5, 3) = %d; want 2", result)
    }
}

func TestMultiply(t *testing.T) {
    result := Multiply(4, 3)
    if result != 12 {
        t.Errorf("Multiply(4, 3) = %d; want 12", result)
    }
}

func TestDivide(t *testing.T) {
    result := Divide(10, 2)
    if result != 5 {
        t.Errorf("Divide(10, 2) = %d; want 5", result)
    }
}
EOF

# ‹5› 初始化 Go 模組
go mod init calculator

# ‹6› 執行測試確認有問題
go test -v
# 應該會看到 4 個測試失敗
```

### 7.6.2 建立 PROMPT.md

```markdown
# 任務：修復計算器程式的 Bug

## 情境

`calculator.go` 是一個簡單的計算器程式，包含四個基本運算函數。
但目前所有函數都有 bug，無法正確運算。

## 目標

修復所有 bug，讓所有測試都能通過。

## 約束

- 只修改 `calculator.go`，不要修改測試檔案
- 每次只修復一個函數
- 修復後執行測試確認

## 完成條件

當以下所有條件都滿足時，此任務視為完成：

1. [ ] 執行 `go test` 返回 exit code 0
2. [ ] 所有 4 個測試都顯示 PASS
3. [ ] 沒有任何編譯錯誤

## 工作流程

1. 執行 `go test -v` 查看哪些測試失敗
2. 閱讀失敗的測試，理解期望行為
3. 閱讀 `calculator.go`，找出 bug
4. 修復一個函數
5. 重新執行測試
6. 重複直到所有測試通過

## 注意事項

- Add 應該是加法（+）
- Subtract 應該是減法（-）
- Multiply 應該是乘法（*）
- Divide 應該是整數除法（/）
```

### 7.6.3 Ralph Loop 腳本

```bash
#!/bin/bash
# ralph-loop.sh - 基本的 Ralph Wiggum Loop 實作

# ‹1› 設定迭代上限（安全機制）
MAX_ITERATIONS=50
ITERATION=0

# ‹2› 記錄開始時間
START_TIME=$(date +%s)

echo "=== Ralph Wiggum Loop 開始 ==="
echo "最大迭代次數: $MAX_ITERATIONS"

# ‹3› 主迴圈
while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    echo ""
    echo "=== 迭代 #$ITERATION ==="

    # ‹4› 檢查收斂條件（測試是否全部通過）
    if go test > /dev/null 2>&1; then
        echo "✅ 所有測試通過！"
        echo "=== Ralph Loop 成功收斂 ==="
        echo "總迭代次數: $ITERATION"
        END_TIME=$(date +%s)
        echo "總耗時: $((END_TIME - START_TIME)) 秒"

        # ‹5› 最終 commit
        git add -A
        git commit -m "Ralph Loop 完成: 所有測試通過" --allow-empty
        exit 0
    fi

    # ‹6› 執行 Claude 進行修復嘗試
    echo "執行 Claude..."
    claude --print "$(cat PROMPT.md)

當前測試結果：
$(go test -v 2>&1)

請分析失敗原因並修復。" --dangerously-skip-permissions

    # ‹7› 記錄這次迭代的結果
    git add -A
    git commit -m "Ralph iteration #$ITERATION: 嘗試修復"

    # ‹8› 顯示當前狀態
    echo "本次迭代完成，測試結果："
    go test -v 2>&1 | tail -10
done

# ‹9› 達到最大迭代次數
echo "⚠️ 達到最大迭代次數 ($MAX_ITERATIONS)，未能收斂"
exit 1
```

### 7.6.4 進階：帶有檢查點回滾的 Ralph Loop

```go
// ralph-loop.go - 進階 Ralph Loop 實作（Go 語言版本）
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "os"
    "os/exec"
    "strings"
    "time"
)

// ‹1› Ralph Loop 配置
type RalphConfig struct {
    MaxIterations    int           `json:"max_iterations"`
    CheckpointEvery  int           `json:"checkpoint_every"`
    RollbackOnWorsen bool          `json:"rollback_on_worsen"`
    PromptFile       string        `json:"prompt_file"`
    TestCommand      string        `json:"test_command"`
    APIKey           string        `json:"-"`
}

// ‹2› 迭代狀態
type IterationState struct {
    Iteration     int       `json:"iteration"`
    FailingTests  int       `json:"failing_tests"`
    PassingTests  int       `json:"passing_tests"`
    CommitHash    string    `json:"commit_hash"`
    Timestamp     time.Time `json:"timestamp"`
}

// ‹3› Ralph Loop 主結構
type RalphLoop struct {
    config   RalphConfig
    history  []IterationState
    bestState IterationState
}

func NewRalphLoop(config RalphConfig) *RalphLoop {
    return &RalphLoop{
        config:  config,
        history: make([]IterationState, 0),
    }
}

// ‹4› 執行測試並計算結果
func (r *RalphLoop) runTests() (int, int, string) {
    cmd := exec.Command("sh", "-c", r.config.TestCommand)
    output, _ := cmd.CombinedOutput()

    // 解析測試輸出（以 Go test 為例）
    outputStr := string(output)
    passing := strings.Count(outputStr, "--- PASS")
    failing := strings.Count(outputStr, "--- FAIL")

    return passing, failing, outputStr
}

// ‹5› 建立 Git checkpoint
func (r *RalphLoop) createCheckpoint(message string) string {
    exec.Command("git", "add", "-A").Run()
    exec.Command("git", "commit", "-m", message, "--allow-empty").Run()

    hashOutput, _ := exec.Command("git", "rev-parse", "HEAD").Output()
    return strings.TrimSpace(string(hashOutput))
}

// ‹6› 回滾到指定 commit
func (r *RalphLoop) rollback(commitHash string) error {
    cmd := exec.Command("git", "reset", "--hard", commitHash)
    return cmd.Run()
}

// ‹7› 呼叫 Claude API
func (r *RalphLoop) callClaude(prompt string, testOutput string) (string, error) {
    fullPrompt := fmt.Sprintf("%s\n\n當前測試結果：\n%s\n\n請分析並修復問題。",
        prompt, testOutput)

    requestBody, _ := json.Marshal(map[string]interface{}{
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "messages": []map[string]string{
            {"role": "user", "content": fullPrompt},
        },
    })

    req, _ := http.NewRequest("POST",
        "https://api.anthropic.com/v1/messages",
        bytes.NewBuffer(requestBody))
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("x-api-key", r.config.APIKey)
    req.Header.Set("anthropic-version", "2023-06-01")

    client := &http.Client{Timeout: 60 * time.Second}
    resp, err := client.Do(req)
    if err != nil {
        return "", err
    }
    defer resp.Body.Close()

    body, _ := io.ReadAll(resp.Body)

    var result struct {
        Content []struct {
            Text string `json:"text"`
        } `json:"content"`
    }
    json.Unmarshal(body, &result)

    if len(result.Content) > 0 {
        return result.Content[0].Text, nil
    }
    return "", fmt.Errorf("empty response")
}

// ‹8› 主要執行迴圈
func (r *RalphLoop) Run() error {
    // 讀取 Prompt
    promptBytes, err := os.ReadFile(r.config.PromptFile)
    if err != nil {
        return fmt.Errorf("無法讀取 PROMPT.md: %w", err)
    }
    prompt := string(promptBytes)

    // 建立初始 checkpoint
    r.bestState.CommitHash = r.createCheckpoint("Ralph Loop 開始")

    fmt.Println("=== Ralph Wiggum Loop 開始 ===")
    fmt.Printf("最大迭代次數: %d\n", r.config.MaxIterations)

    for i := 1; i <= r.config.MaxIterations; i++ {
        fmt.Printf("\n=== 迭代 #%d ===\n", i)

        // ‹9› 執行測試
        passing, failing, testOutput := r.runTests()

        // 記錄狀態
        state := IterationState{
            Iteration:    i,
            PassingTests: passing,
            FailingTests: failing,
            Timestamp:    time.Now(),
        }

        fmt.Printf("測試結果: %d 通過, %d 失敗\n", passing, failing)

        // ‹10› 檢查收斂條件
        if failing == 0 {
            fmt.Println("\n✅ 所有測試通過！Ralph Loop 成功收斂")
            state.CommitHash = r.createCheckpoint(
                fmt.Sprintf("Ralph Loop 完成: 所有測試通過 (迭代 #%d)", i))
            r.history = append(r.history, state)
            return nil
        }

        // ‹11› 檢查是否退步，需要回滾
        if r.config.RollbackOnWorsen && len(r.history) > 0 {
            lastState := r.history[len(r.history)-1]
            if failing > lastState.FailingTests {
                fmt.Printf("⚠️ 測試退步 (%d → %d 失敗)，回滾到上一個檢查點\n",
                    lastState.FailingTests, failing)
                r.rollback(lastState.CommitHash)
                continue
            }
        }

        // ‹12› 更新最佳狀態
        if failing < r.bestState.FailingTests || r.bestState.FailingTests == 0 {
            r.bestState = state
        }

        // ‹13› 呼叫 Claude 進行修復
        fmt.Println("呼叫 Claude 進行分析...")
        response, err := r.callClaude(prompt, testOutput)
        if err != nil {
            fmt.Printf("Claude API 錯誤: %v\n", err)
            continue
        }

        // 這裡假設 Claude 會自動執行工具呼叫來修改程式碼
        // 實際實作中需要處理 tool_use 回應
        fmt.Printf("Claude 回應長度: %d 字元\n", len(response))

        // ‹14› 建立 checkpoint
        state.CommitHash = r.createCheckpoint(
            fmt.Sprintf("Ralph iteration #%d: %d 通過, %d 失敗",
                i, passing, failing))
        r.history = append(r.history, state)

        // ‹15› 定期建立重要檢查點
        if i%r.config.CheckpointEvery == 0 {
            fmt.Printf("📌 建立第 %d 次檢查點\n", i)
        }
    }

    return fmt.Errorf("達到最大迭代次數 (%d)，未能收斂", r.config.MaxIterations)
}

// ‹16› 輸出執行報告
func (r *RalphLoop) PrintReport() {
    fmt.Println("\n=== Ralph Loop 執行報告 ===")
    fmt.Printf("總迭代次數: %d\n", len(r.history))

    if len(r.history) > 0 {
        first := r.history[0]
        last := r.history[len(r.history)-1]

        fmt.Printf("初始失敗測試: %d\n", first.FailingTests)
        fmt.Printf("最終失敗測試: %d\n", last.FailingTests)
        fmt.Printf("總執行時間: %v\n", last.Timestamp.Sub(first.Timestamp))
    }

    fmt.Printf("最佳狀態: %d 通過, %d 失敗\n",
        r.bestState.PassingTests, r.bestState.FailingTests)
}

func main() {
    config := RalphConfig{
        MaxIterations:    50,
        CheckpointEvery:  5,
        RollbackOnWorsen: true,
        PromptFile:       "PROMPT.md",
        TestCommand:      "go test -v",
        APIKey:           os.Getenv("ANTHROPIC_API_KEY"),
    }

    ralph := NewRalphLoop(config)
    err := ralph.Run()

    ralph.PrintReport()

    if err != nil {
        fmt.Printf("錯誤: %v\n", err)
        os.Exit(1)
    }
}
```

### 7.6.5 執行結果範例

```
=== Ralph Wiggum Loop 開始 ===
最大迭代次數: 50

=== 迭代 #1 ===
測試結果: 0 通過, 4 失敗
呼叫 Claude 進行分析...
Claude 回應長度: 2341 字元
📝 修改 calculator.go: 修復 Add 函數

=== 迭代 #2 ===
測試結果: 1 通過, 3 失敗
呼叫 Claude 進行分析...
Claude 回應長度: 1876 字元
📝 修改 calculator.go: 修復 Subtract 函數

=== 迭代 #3 ===
測試結果: 2 通過, 2 失敗
呼叫 Claude 進行分析...
Claude 回應長度: 1654 字元
📝 修改 calculator.go: 修復 Multiply 函數

=== 迭代 #4 ===
測試結果: 3 通過, 1 失敗
呼叫 Claude 進行分析...
Claude 回應長度: 1432 字元
📝 修改 calculator.go: 修復 Divide 函數

=== 迭代 #5 ===
測試結果: 4 通過, 0 失敗

✅ 所有測試通過！Ralph Loop 成功收斂

=== Ralph Loop 執行報告 ===
總迭代次數: 5
初始失敗測試: 4
最終失敗測試: 0
總執行時間: 2m34s
最佳狀態: 4 通過, 0 失敗
```

---

## 7.7 進階技巧與最佳實踐

### 7.7.1 分層收斂策略

對於複雜專案，可以採用分層收斂：

```
┌─────────────────────────────────────────────────────────────────┐
│                    分層收斂策略                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   第一層：編譯通過                                               │
│   ┌─────────────────────────────────────────────┐               │
│   │ while [ compile_errors > 0 ]; do           │               │
│   │     claude "修復編譯錯誤"                   │               │
│   │ done                                        │               │
│   └─────────────────────────────────────────────┘               │
│                           │                                     │
│                           ▼                                     │
│   第二層：單元測試通過                                           │
│   ┌─────────────────────────────────────────────┐               │
│   │ while [ unit_test_failures > 0 ]; do       │               │
│   │     claude "修復單元測試"                   │               │
│   │ done                                        │               │
│   └─────────────────────────────────────────────┘               │
│                           │                                     │
│                           ▼                                     │
│   第三層：整合測試通過                                           │
│   ┌─────────────────────────────────────────────┐               │
│   │ while [ integration_failures > 0 ]; do     │               │
│   │     claude "修復整合測試"                   │               │
│   │ done                                        │               │
│   └─────────────────────────────────────────────┘               │
│                           │                                     │
│                           ▼                                     │
│   第四層：Lint/靜態分析通過                                      │
│   ┌─────────────────────────────────────────────┐               │
│   │ while [ lint_warnings > 0 ]; do            │               │
│   │     claude "修復程式碼品質問題"             │               │
│   │ done                                        │               │
│   └─────────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.7.2 平行 Ralph Loop

對於可獨立處理的多個模組，可以執行平行 Ralph Loop：

```bash
#!/bin/bash
# parallel-ralph.sh - 平行執行多個 Ralph Loop

# ‹1› 定義要處理的模組
MODULES=("auth" "payment" "notification" "reporting")

# ‹2› 為每個模組建立分支並執行 Ralph Loop
for module in "${MODULES[@]}"; do
    (
        # ‹3› 建立工作分支
        git checkout -b "ralph-$module"

        # ‹4› 執行模組特定的 Ralph Loop
        ./ralph-loop.sh "PROMPT-$module.md"

        # ‹5› 完成後標記
        touch ".ralph-done-$module"
    ) &
done

# ‹6› 等待所有平行任務完成
wait

# ‹7› 合併所有分支
git checkout main
for module in "${MODULES[@]}"; do
    git merge "ralph-$module" --no-edit
done

echo "所有模組處理完成"
```

### 7.7.3 智能回滾策略

```go
// ‹1› 智能回滾決策
func (r *RalphLoop) shouldRollback(current, previous IterationState) bool {
    // 策略 1：失敗測試增加
    if current.FailingTests > previous.FailingTests {
        return true
    }

    // 策略 2：連續 N 次沒有進展
    if r.countNoProgressIterations() >= 5 {
        // 回滾到最佳狀態而非上一個狀態
        r.rollback(r.bestState.CommitHash)
        return false  // 已經處理了回滾
    }

    // 策略 3：程式碼大小異常增長（可能是錯誤的生成）
    currentSize := r.getCodebaseSize()
    previousSize := r.previousCodebaseSize
    if currentSize > previousSize * 2 {
        return true
    }

    return false
}

// ‹2› 計算無進展迭代次數
func (r *RalphLoop) countNoProgressIterations() int {
    if len(r.history) < 2 {
        return 0
    }

    count := 0
    for i := len(r.history) - 1; i > 0; i-- {
        if r.history[i].FailingTests >= r.history[i-1].FailingTests {
            count++
        } else {
            break
        }
    }
    return count
}
```

---

## 7.8 本章小結

本章深入探討了 Ralph Wiggum Loop 的理論基礎與實作細節。讓我們回顧核心概念：

### 關鍵要點

1. **哲學基礎**
   - 「確定性的失敗勝過非確定性的成功」
   - 接受失敗作為學習過程的一部分
   - 每次迭代都是進步的機會

2. **理論基礎**
   - 強化學習中的探索與利用
   - 經驗回放（Git 作為 Replay Buffer）
   - Credit Assignment（透過細粒度 commit）

3. **Git 作為記憶層**
   - 完整性、可追溯性、原子性
   - 可分支、可合併、高效率
   - 內容可定址儲存的優勢

4. **收斂性分析**
   - 必要條件：可分解、可觀察、有限狀態
   - 不收斂情況：循環依賴、目標不可達
   - 收斂速度：指數衰減 O(e^{-pt})

5. **實作要點**
   - 明確的收斂條件
   - 頻繁的 checkpoint
   - 智能回滾策略
   - 分層收斂方法

### 練習題

1. **基礎練習**：使用本章提供的程式碼，建立一個有 10 個 bug 的計算器程式，執行 Ralph Loop 修復。記錄收斂所需的迭代次數。

2. **進階練習**：實作一個具有「智能回滾」功能的 Ralph Loop，當連續 3 次迭代沒有進展時，自動回滾到最佳狀態。

3. **理論練習**：證明或反證：如果 LLM 在每次迭代有固定機率 p > 0 修復一個問題，且問題之間獨立，則 Ralph Loop 的期望收斂時間是 O(k/p)，其中 k 是初始問題數。

4. **實驗練習**：比較不同 temperature 設定（0, 0.5, 1.0）對 Ralph Loop 收斂速度的影響。形成你的假設並用實驗驗證。

---

## 學術參考文獻

1. Sutton, R. S., & Barto, A. G. (2018). *Reinforcement Learning: An Introduction* (2nd ed.). MIT Press.

2. Mnih, V., et al. (2015). Human-level control through deep reinforcement learning. *Nature*, 518(7540), 529-533.

3. Chacon, S., & Straub, B. (2014). *Pro Git* (2nd ed.). Apress.

4. Huntley, G. (2025). Ralph Wiggum: Deterministic Failure over Non-deterministic Success. Blog post.

5. Silver, D., et al. (2016). Mastering the game of Go with deep neural networks and tree search. *Nature*, 529(7587), 484-489.

---

## 下一章預告

Ralph Wiggum 技術在 2025 年底被 Anthropic 官方採納為 Claude Code Plugin。第 8 章將比較官方 Plugin 與原始 Bash Loop 實現的差異，深入分析「消毒化」的代價，以及如何根據場景選擇適當的實現方式。我們還將透過 CURSED 程式語言的開發案例，展示 Ralph Loop 在大型專案中的實際應用。
