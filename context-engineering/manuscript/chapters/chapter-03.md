# 第 3 章：不是所有 LLM 都是 Agentic

> 「選擇正確的模型，比寫出完美的 Prompt 更重要。」

---

## 本章學習目標

完成本章後，你將能夠：

- 理解 LLM 訓練方法的根本差異：RLHF vs Constitutional AI
- 區分 Oracle 模型與 Agentic 模型的設計哲學
- 解釋 Tool Use 的技術實現原理
- 解讀主流模型評測指標（HumanEval、SWE-bench、MATH）
- 說明為何 Claude Sonnet 是「追逐工具呼叫的機械松鼠」
- 設計 Oracle + Agentic 模型組合架構

---

## 3.1 從訓練方法看模型差異

要理解不同 LLM 為何展現出截然不同的行為特性，我們必須回到它們的訓練過程。現代 LLM 的訓練通常分為兩大階段：**預訓練**（Pre-training）和**對齊**（Alignment）。預訓練建立語言能力的基礎，而對齊則決定模型的「性格」。

### 3.1.1 RLHF：人類偏好的量化學習

**RLHF**（Reinforcement Learning from Human Feedback，從人類回饋中強化學習）是 OpenAI 在 2022 年提出的對齊方法，也是 ChatGPT 成功的關鍵技術。

```
┌─────────────────────────────────────────────────────────────────┐
│                    RLHF 訓練流程                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐         ┌───────────┐         ┌───────────┐
   │ 第一階段 │         │ 第二階段   │         │ 第三階段   │
   │ SFT     │   →     │ 獎勵模型   │   →     │ PPO 強化   │
   │         │         │ 訓練       │         │ 學習       │
   └─────────┘         └───────────┘         └───────────┘
        │                     │                     │
   人工標註的          人類比較回應          用獎勵模型
   高品質回應          的偏好數據            優化策略
```

**第一階段：監督式微調（SFT）**

從預訓練模型開始，使用人工標註的高品質問答對進行微調。標註者需要針對各種提示撰寫理想的回應。

**第二階段：獎勵模型訓練**

這是 RLHF 的核心創新。對於同一個提示，讓模型生成多個回應，然後由人類標註者進行排序。這些偏好數據用於訓練一個「獎勵模型」（Reward Model），它能預測人類對回應的偏好程度。

獎勵模型的目標函數可以表示為：

$$\mathcal{L}_{\text{RM}} = -\mathbb{E}_{(x, y_w, y_l) \sim D}\left[\log \sigma(r_\theta(x, y_w) - r_\theta(x, y_l))\right]$$

其中：
- $x$ 是輸入提示
- $y_w$ 是人類偏好的回應（winner）
- $y_l$ 是人類較不偏好的回應（loser）
- $r_\theta$ 是獎勵模型的輸出分數
- $\sigma$ 是 sigmoid 函數

**第三階段：策略優化**

使用 PPO（Proximal Policy Optimization）演算法，根據獎勵模型的回饋優化語言模型。目標是最大化預期獎勵，同時防止模型偏離原始分佈太遠。

**RLHF 的特性**

這種訓練方法產生的模型傾向於：
- **討好人類**：模型會學習「什麼樣的回答讓人滿意」
- **避免爭議**：傾向於給出中立、安全的回應
- **冗長詳細**：人類標註者往往偏好更詳細的回答

### 3.1.2 Constitutional AI：原則驅動的自我對齊

**Constitutional AI**（憲法式 AI）是 Anthropic 在 2022 年提出的替代方法，它大幅減少對人類標註的依賴，轉而使用一套明確的「原則」（Constitution）來指導模型行為。

```
┌─────────────────────────────────────────────────────────────────┐
│                Constitutional AI 訓練流程                        │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐         ┌───────────┐         ┌───────────┐
   │ 第一階段 │         │ 第二階段   │         │ 第三階段   │
   │ SL-CAI  │   →     │ RL-CAI    │   →     │ 迭代精煉   │
   │         │         │           │         │           │
   └─────────┘         └───────────┘         └───────────┘
        │                     │                     │
   模型自我批判          AI 生成偏好          持續改進
   並修訂回應            訓練獎勵模型          對齊效果
```

**第一階段：監督式學習 CAI（SL-CAI）**

1. 讓模型生成可能有害的初始回應
2. 提供一組「原則」，要求模型批評自己的回應
3. 根據批評修訂回應
4. 使用修訂後的回應進行微調

原則範例：
```
「請根據以下原則修訂你的回應：
1. 選擇最有幫助、誠實、無害的回應
2. 選擇不會協助犯罪活動的回應
3. 選擇展現對人類尊重的回應
...
修訂後的回應：」
```

**第二階段：強化學習 CAI（RL-CAI）**

關鍵創新是使用 AI 而非人類來生成偏好數據：

1. 讓模型針對同一提示生成多個回應
2. 讓**另一個 AI**根據原則選擇更好的回應
3. 使用這些 AI 生成的偏好訓練獎勵模型
4. 用獎勵模型進行強化學習

**Constitutional AI 的特性**

這種方法產生的模型傾向於：
- **原則導向**：行為受明確原則約束，而非模糊的人類偏好
- **透明可解釋**：拒絕的理由可以追溯到具體原則
- **主動性**：在符合原則的前提下，更願意採取行動

### 3.1.3 訓練方法與模型行為的關聯

理解這兩種訓練方法的差異，有助於預測模型在實際應用中的表現：

| 特性 | RLHF | Constitutional AI |
|------|------|-------------------|
| **回應風格** | 傾向冗長詳細 | 傾向簡潔直接 |
| **拒絕行為** | 可能過度謹慎 | 有原則地拒絕 |
| **工具使用** | 較為保守 | 較為積極 |
| **可預測性** | 依賴標註者偏好 | 依賴原則設計 |
| **擴展性** | 需要大量人類標註 | AI 輔助可擴展 |

Claude 模型使用 Constitutional AI 訓練，這是它在 Agentic 任務中表現出色的重要原因之一。

---

## 3.2 LLM 分類學：Oracle vs Agentic

並非所有 LLM 都適合在 Agentic 情境中使用。根據模型的設計目標和行為特性，我們可以將它們分為兩大類。

### 3.2.1 Oracle 模型：深思熟慮的顧問

**Oracle 模型**（神諭模型）的設計目標是**單次回應的品質最大化**。它們像古希臘德爾菲神廟的神諭一樣——你提問一次，得到一個深思熟慮的答案。

**特徵**：
- 傾向於全面分析問題
- 回應詳盡完整
- 較少主動要求工具呼叫
- 更擅長需要深度推理的任務

**代表模型**：
- Claude Opus（Claude 3.5 Opus、Claude Opus 4）
- GPT-4 Turbo
- Gemini Ultra

**適用場景**：
- 複雜數學推理
- 法律文件分析
- 學術論文撰寫
- 架構設計評審

### 3.2.2 Agentic 模型：行動派的執行者

**Agentic 模型**的設計目標是**工具使用與多步驟任務執行**。它們被訓練成積極使用工具、快速迭代的「行動派」。

**特徵**：
- 積極發起工具呼叫
- 傾向於「做了再說」
- 回應相對簡潔
- 善於多步驟任務編排

**代表模型**：
- Claude Sonnet（Claude 3.5 Sonnet、Claude Sonnet 4）
- GPT-4o
- Gemini Flash

**適用場景**：
- 程式碼生成與除錯
- 檔案操作與搜尋
- API 整合任務
- 自動化工作流程

### 3.2.3 機械松鼠現象

Geoffrey Huntley 在他的 Coding Agent 研究中，對 Claude Sonnet 有一個生動的描述：

> 「Claude Sonnet 就像一隻機械松鼠——它總是急於追逐下一個工具呼叫，彷彿工具呼叫就是它的橡果。」

這個比喻精確捕捉了 Agentic 模型的行為模式：

```python
# 典型的 Sonnet 行為模式（偽代碼）
def sonnet_reasoning(task):
    """
    Sonnet 的推理模式：
    1. 快速理解任務
    2. 立即識別可用工具
    3. 發起工具呼叫
    4. 根據結果決定下一步
    """
    understanding = quick_analysis(task)  # 快速分析

    while not task_completed:
        tool = identify_useful_tool(understanding)  # 識別工具
        result = call_tool(tool)                     # 🐿️ 追逐橡果！
        understanding = update_understanding(result)

    return synthesize_results()
```

**機械松鼠的優勢**：
- 高效率：不會在分析階段過度停留
- 快速回饋：使用者能看到進度
- 適應性強：根據工具結果動態調整

**機械松鼠的限制**：
- 可能跳過重要的前置分析
- 工具呼叫不一定總是最佳策略
- 在需要深度思考的場景可能表現不佳

---

## 3.3 Tool Use 的技術實現

要理解 Agentic 模型的工作原理，我們需要深入了解 Tool Use（工具使用）的技術實現。

### 3.3.1 Function Calling 的 API 設計

現代 LLM 的工具使用是通過 **Function Calling**（函數呼叫）機制實現的。當你向 API 發送請求時，除了提示詞，還可以附帶工具定義。

```json
{
  "model": "claude-sonnet-4-20250514",
  "messages": [
    {"role": "user", "content": "幫我搜尋專案中的 TODO 註解"}
  ],
  "tools": [
    {
      "name": "grep_search",
      "description": "在程式碼庫中搜尋符合模式的文字",
      "input_schema": {
        "type": "object",
        "properties": {
          "pattern": {
            "type": "string",
            "description": "要搜尋的正則表達式模式"
          },
          "path": {
            "type": "string",
            "description": "搜尋的目錄路徑"
          }
        },
        "required": ["pattern"]
      }
    }
  ]
}
```

### 3.3.2 模型如何「學會」使用工具

Tool Use 能力的獲得有兩個關鍵環節：

**1. 格式學習**

在訓練過程中，模型學習了特定的輸出格式來表示工具呼叫。例如，Claude 使用結構化的 JSON 區塊：

```json
{
  "type": "tool_use",
  "id": "toolu_01A09q90qw90lq917835lhl",
  "name": "grep_search",
  "input": {
    "pattern": "TODO|FIXME|HACK",
    "path": "./src"
  }
}
```

**2. 時機判斷**

更重要的是，模型需要學習**何時**應該使用工具。這是通過大量的訓練數據實現的，這些數據展示了在什麼情境下工具呼叫是有幫助的。

```
訓練數據範例：

提示：「目前時間是幾點？」
✓ 正確行為：呼叫 get_current_time 工具
✗ 錯誤行為：編造一個時間

提示：「解釋相對論」
✓ 正確行為：直接回答（不需要工具）
✗ 錯誤行為：嘗試呼叫搜尋工具
```

### 3.3.3 Tool Use 的概率機制

從技術角度看，工具呼叫是模型的一種特殊輸出 token 序列。模型在生成過程中，需要決定：

1. **是否呼叫工具**：生成工具呼叫標記 vs 生成普通文字
2. **呼叫哪個工具**：從可用工具列表中選擇
3. **傳入什麼參數**：生成符合 schema 的參數

這個決策過程可以用條件概率來描述：

$$P(\text{tool\_call} | \text{context}, \text{tools}) = \prod_{i} P(t_i | t_{<i}, \text{context}, \text{tools})$$

其中每個 token $t_i$ 的生成都基於前面的 token、上下文和可用工具列表。

### 3.3.4 Parallel Tool Use

Claude 的一個重要特性是**並行工具呼叫**（Parallel Tool Use）。在單次回應中，模型可以發起多個獨立的工具呼叫：

```json
{
  "content": [
    {
      "type": "text",
      "text": "讓我同時搜尋這三個模式："
    },
    {
      "type": "tool_use",
      "name": "grep_search",
      "input": {"pattern": "TODO"}
    },
    {
      "type": "tool_use",
      "name": "grep_search",
      "input": {"pattern": "FIXME"}
    },
    {
      "type": "tool_use",
      "name": "grep_search",
      "input": {"pattern": "HACK"}
    }
  ]
}
```

這種能力大幅提升了 Agentic 任務的效率——模型可以「同時處理多件事」，而不是線性地一件一件來。

---

## 3.4 模型評測指標解讀

選擇合適的模型需要理解各種評測指標的含義。以下是常見評測基準及其解讀。

### 3.4.1 HumanEval：程式碼生成能力

**HumanEval** 是 OpenAI 在 2021 年提出的程式碼生成基準測試，包含 164 個手寫的 Python 程式設計問題。

**測試方式**：
1. 提供函數簽名和文檔字符串（docstring）
2. 要求模型生成函數實現
3. 使用測試案例驗證正確性

**範例問題**：
```python
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """
    Check if in given list of numbers, are any two numbers closer
    to each other than given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
```

**指標解讀**：
- **pass@1**：一次生成就正確的比例
- **pass@10**：生成 10 次中有一次正確的比例
- **pass@100**：生成 100 次中有一次正確的比例

**2025 年主流模型表現**：

| 模型 | pass@1 |
|------|--------|
| Claude Opus 4 | 92.3% |
| Claude Sonnet 4 | 90.1% |
| GPT-4o | 90.2% |
| Gemini Ultra | 87.5% |

### 3.4.2 SWE-bench：真實軟體工程任務

**SWE-bench**（Software Engineering Benchmark）是 2024 年提出的更具挑戰性的評測，使用真實 GitHub issue 來測試模型解決實際軟體問題的能力。

**測試方式**：
1. 從知名開源專案（Django、Flask、NumPy 等）收集已解決的 issue
2. 提供程式碼庫和 issue 描述
3. 要求模型生成修復該問題的程式碼補丁
4. 使用專案的測試套件驗證修復是否正確

**為何 SWE-bench 更能反映 Agentic 能力**：
- 需要理解大型程式碼庫
- 需要定位問題檔案
- 需要理解測試失敗原因
- 需要生成符合專案風格的程式碼

**2025 年主流模型表現（SWE-bench Verified）**：

| 模型 | 解決率 |
|------|--------|
| Claude Sonnet 4 + Agent | 72.7% |
| Claude Opus 4 | 68.5% |
| GPT-4o + Agent | 65.2% |
| Gemini 2.0 | 58.3% |

注意：加上 Agent 框架（如 Claude Code）的模型表現明顯優於單純的 API 呼叫，這凸顯了 Agentic 架構的價值。

### 3.4.3 MATH：數學推理能力

**MATH** 基準測試包含 12,500 道競賽級數學題，涵蓋代數、幾何、數論等領域。

**測試範例**：
```
問題：Find the number of integers n such that
      1 + ⌊(100n)/101⌋ = ⌈(99n)/100⌉

答案：10100
```

**為何 MATH 評測重要**：
數學推理能力與模型的邏輯推理、問題分解能力高度相關，這些都是 Agentic 任務的基礎。

### 3.4.4 Agentic 評測的新趨勢

傳統評測主要關注單次回應的品質，但 Agentic 能力需要新的評測方法：

**多輪對話評測**：
- 評估模型在多輪互動中保持一致性的能力
- 評估模型利用先前工具結果的能力

**任務完成評測**：
- 不只看「答案是否正確」，還要看「任務是否完成」
- 例如：「幫我重構這個函數」——評估最終程式碼品質

**效率評測**：
- Token 消耗 / 任務複雜度
- 工具呼叫次數 / 任務完成率

---

## 3.5 Safety 軸向的考量

除了 Oracle/Agentic 軸向，還需要考慮模型的安全性設定。不同的安全等級適合不同的應用場景。

### 3.5.1 Safety 分類框架

```
                    High Safety
                         │
           ┌─────────────┼─────────────┐
           │             │             │
    ┌──────▼──────┐     │     ┌───────▼──────┐
    │   Oracle    │     │     │   Agentic    │
    │  High-Safe  │     │     │  High-Safe   │
    │             │     │     │              │
    │ 面向用戶的  │     │     │ 生產環境     │
    │ 問答系統    │     │     │ Agent        │
    └─────────────┘     │     └──────────────┘
Oracle ─────────────────┼───────────────────── Agentic
    ┌─────────────┐     │     ┌──────────────┐
    │   Oracle    │     │     │   Agentic    │
    │  Low-Safe   │     │     │  Low-Safe    │
    │             │     │     │              │
    │ 內部研究    │     │     │ 實驗性       │
    │ 紅隊測試    │     │     │ Agent        │
    └─────────────┘     │     └──────────────┘
           │             │             │
           └─────────────┼─────────────┘
                         │
                    Low Safety
```

### 3.5.2 各象限的適用場景

| 象限 | 特性 | 適用場景 |
|------|------|----------|
| **Oracle + High Safety** | 謹慎、詳盡、避免爭議 | 客服機器人、教育工具 |
| **Agentic + High Safety** | 積極行動但有防護 | 生產環境的 Coding Agent |
| **Oracle + Low Safety** | 深度分析、較少限制 | 安全研究、紅隊測試 |
| **Agentic + Low Safety** | 快速迭代、實驗性強 | 開發階段的原型測試 |

### 3.5.3 Safety 設定的技術實現

Claude API 提供多種方式控制安全行為：

**1. 系統提示詞調整**
```
你是一個專業的程式碼審查助手。
在提供建議時，請直接指出問題，不需要過度謹慎的免責聲明。
```

**2. API 參數設定**
```json
{
  "model": "claude-sonnet-4-20250514",
  "metadata": {
    "user_id": "internal-research-team"
  }
}
```

**3. 使用原則（Constitution）調整**

對於企業用戶，Anthropic 提供自訂原則的選項，允許在特定場景下調整模型行為。

---

## 3.6 模型選擇決策樹

根據任務特性選擇模型的實用指南：

```
                    ┌────────────────────┐
                    │ 任務需要工具呼叫嗎？│
                    └─────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              │ 是            │               │ 否
              ▼               │               ▼
    ┌─────────────────┐       │     ┌─────────────────┐
    │ 需要多少輪工具   │       │     │ 需要深度分析嗎？│
    │ 呼叫？          │       │     └────────┬────────┘
    └────────┬────────┘       │              │
             │                │    ┌─────────┼─────────┐
    ┌────────┼────────┐       │    │ 是      │         │ 否
    │        │        │       │    ▼         │         ▼
    │ 1-3輪  │ >3輪   │       │ Oracle      │      Agentic
    ▼        ▼        │       │ (Opus)      │      (任一)
  任一     Agentic   │       │             │
  模型     (Sonnet)  │       └─────────────┘
                      │
                      │
    ┌─────────────────┴─────────────────┐
    │            細化選擇                │
    └───────────────────────────────────┘

    速度優先 → Claude Sonnet / GPT-4o / Gemini Flash
    品質優先 → Claude Opus / GPT-4 Turbo
    成本優先 → Claude Haiku / GPT-4o-mini
```

### 3.6.1 任務類型與模型匹配

| 任務類型 | 推薦模型 | 原因 |
|----------|----------|------|
| 程式碼生成 | Sonnet | 需要快速迭代、工具整合 |
| 程式碼審查 | Opus | 需要深度分析、考量周全 |
| Bug 修復 | Sonnet | 需要頻繁讀取/編輯檔案 |
| 架構設計 | Opus | 需要全面考量權衡 |
| 重構大型專案 | Sonnet + Opus | Sonnet 執行，Opus 規劃 |
| 文檔撰寫 | Opus | 需要完整、詳盡的內容 |
| 測試生成 | Sonnet | 需要理解程式碼並批量生成 |

---

## 3.7 進階模式：Oracle 作為工具

一個強大的架構模式是讓 Agentic 模型作為協調者，將需要深度分析的子任務委派給 Oracle 模型。

### 3.7.1 架構設計

```
┌─────────────────────────────────────────────────────────────┐
│                   使用者介面                                 │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 協調層（Sonnet）                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 推論迴圈                              │   │
│  │  1. 接收任務                                         │   │
│  │  2. 分析需要的工具                                    │   │
│  │  3. 呼叫工具（包括 Oracle 分析）                      │   │
│  │  4. 綜合結果                                         │   │
│  │  5. 決定下一步或完成                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                              │
└──────────────────────────────┼──────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
   ┌───────────┐        ┌───────────┐        ┌───────────┐
   │ 檔案工具   │        │ 搜尋工具   │        │ Oracle    │
   │           │        │           │        │ 分析工具   │
   │ Read      │        │ Grep      │        │           │
   │ Write     │        │ Glob      │        │ (Opus)    │
   │ List      │        │           │        │           │
   └───────────┘        └───────────┘        └───────────┘
```

### 3.7.2 Oracle 工具定義

```json
{
  "name": "deep_analysis",
  "description": "將複雜問題委派給 Oracle 模型進行深度分析。適用於需要全面考量、權衡多方面因素的決策。",
  "input_schema": {
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "需要深度分析的問題"
      },
      "context": {
        "type": "string",
        "description": "相關背景資訊"
      },
      "constraints": {
        "type": "array",
        "items": {"type": "string"},
        "description": "需要考量的限制條件"
      }
    },
    "required": ["question"]
  }
}
```

### 3.7.3 實作範例

```go
// ‹1› Oracle 工具的實作
func (h *OracleToolHandler) Execute(input map[string]interface{}) (string, error) {
    question := input["question"].(string)
    context := input["context"].(string)

    // ‹2› 使用 Opus 模型進行深度分析
    response, err := h.opusClient.CreateMessage(claude.MessageRequest{
        Model: "claude-opus-4-20250514",
        Messages: []claude.Message{
            {
                Role: "user",
                Content: fmt.Sprintf(`
請對以下問題進行深度分析：

問題：%s

背景：%s

請提供：
1. 問題的核心本質
2. 可能的解決方案及其優缺點
3. 推薦的方案及理由
`, question, context),
            },
        },
        MaxTokens: 4096,
    })

    if err != nil {
        return "", err
    }

    // ‹3› 返回分析結果給協調層
    return response.Content[0].Text, nil
}
```

### 3.7.4 適用場景

這種組合架構特別適合以下場景：

1. **大型重構專案**
   - Sonnet 負責瀏覽檔案、執行修改
   - Opus 負責設計重構策略、審查關鍵決策

2. **複雜 Bug 調查**
   - Sonnet 負責收集日誌、執行測試
   - Opus 負責分析根本原因、設計修復方案

3. **程式碼審查流程**
   - Sonnet 負責自動化檢查、格式驗證
   - Opus 負責深度程式碼審查、架構評估

---

## 3.8 實務建議

### 3.8.1 模型選擇的常見錯誤

**錯誤 1：總是選擇「最強」的模型**
```
❌ 錯誤思維：「Opus 最強，所以什麼都用 Opus」
✓ 正確思維：「這個任務需要什麼特性？選擇匹配的模型」
```

**錯誤 2：忽略成本考量**
```
❌ 錯誤做法：10 輪工具呼叫都用 Opus
✓ 正確做法：Sonnet 執行，關鍵決策點用 Opus
```

**錯誤 3：過度依賴單一模型**
```
❌ 錯誤架構：所有任務都由同一模型處理
✓ 正確架構：根據子任務特性分派給不同模型
```

### 3.8.2 建立模型選擇策略

```python
# 模型選擇策略範例
def select_model(task: Task) -> str:
    """
    根據任務特性選擇合適的模型
    """
    # 需要深度分析的任務
    if task.requires_deep_analysis:
        return "claude-opus-4-20250514"

    # 多步驟工具操作任務
    if task.tool_calls_expected > 3:
        return "claude-sonnet-4-20250514"

    # 簡單快速任務
    if task.complexity == "low":
        return "claude-3-5-haiku-20241022"

    # 預設使用 Sonnet
    return "claude-sonnet-4-20250514"
```

---

## 本章小結

本章深入探討了 LLM 的分類學，這是建構有效 Coding Agent 的知識基礎。

**核心要點**：

1. **訓練方法決定模型性格**
   - RLHF 產生討好人類的模型
   - Constitutional AI 產生原則導向的模型

2. **Oracle vs Agentic 是關鍵分類**
   - Oracle 模型：深思熟慮，適合複雜分析
   - Agentic 模型：積極行動，適合工具操作

3. **Tool Use 有其技術原理**
   - Function Calling 是 API 層級的設計
   - 模型學習何時、如何使用工具

4. **評測指標各有側重**
   - HumanEval 測試程式碼生成
   - SWE-bench 測試真實工程能力
   - Agentic 評測需要新方法

5. **模型組合是強大模式**
   - Agentic 模型做協調
   - Oracle 模型做深度分析

---

## 練習題

### 練習 3.1：模型分類
對以下模型進行 Oracle/Agentic 分類，並說明理由：
- GPT-3.5 Turbo
- Claude 3 Haiku
- Gemini Pro
- Llama 3 70B

### 練習 3.2：場景分析
針對以下場景，選擇最適合的模型配置：
1. 建構一個回答法律問題的聊天機器人
2. 自動化遷移 100 個 JavaScript 檔案到 TypeScript
3. 分析公司年度財報並產出摘要

### 練習 3.3：架構設計
設計一個「程式碼審查機器人」的架構，需要：
- 自動執行靜態分析工具
- 深度審查關鍵程式碼路徑
- 生成審查報告

說明你會如何組合不同模型。

---

## 延伸閱讀

1. **"Training language models to follow instructions with human feedback"** (Ouyang et al., 2022)
   - RLHF 的原始論文，OpenAI 發表

2. **"Constitutional AI: Harmlessness from AI Feedback"** (Bai et al., 2022)
   - Constitutional AI 的原始論文，Anthropic 發表

3. **"Toolformer: Language Models Can Teach Themselves to Use Tools"** (Schick et al., 2023)
   - 工具使用能力的自學習方法

4. **"SWE-bench: Can Language Models Resolve Real-World GitHub Issues?"** (Jimenez et al., 2024)
   - SWE-bench 評測基準的論文

5. **Claude Model Card** (Anthropic)
   - Claude 模型的官方技術文件
   - https://www.anthropic.com/claude

---

## 下一章預告

完成第一部分的認知革命後，我們將進入第二部分：核心技能。第 4 章《推論迴圈的解剖學》將帶你深入 Coding Agent 的心臟——理解那個不斷跳動的「輸入→推論→工具呼叫→再推論」迴圈是如何運作的，並用 Go 語言從零建構一個完整的聊天介面。
