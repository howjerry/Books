# 第 1 章：300 行程式碼的真相

> 揭示所有 AI 編碼工具的共同架構

---

## 本章學習目標

完成本章後，你將能夠：

- 理解大型語言模型（LLM）的基本運作原理
- 解釋 Transformer 架構如何使現代 AI 編碼工具成為可能
- 描述所有主流 AI 編碼工具（Cursor、Windsurf、Claude Code、GitHub Copilot）的共同架構本質
- 理解為何「廠商比較」是一種「追尾行為」
- 認識 Geoffrey Huntley 對 coding agent 架構的核心洞見

---

## 1.1 一個澳洲農場主的發現

2025 年的某個夜晚，在澳洲偏遠的山羊農場，Geoffrey Huntley 盯著他的螢幕，陷入了沉思。作為一位資深的軟體工程師，他已經使用過市面上幾乎所有的 AI 編碼工具——Cursor、Windsurf、Claude Code、GitHub Copilot——每一個都聲稱自己是「最強大」、「最智慧」的選擇。

但那天晚上，他做出了一個改變許多開發者世界觀的觀察：

> 「All coding agents are is just 300 lines of code running LLM tokens in a loop.」
>
> 「所有的 coding agent，不過就是 300 行程式碼在迴圈中運行 LLM tokens。」

這句話在開發者社群中引起了軒然大波。有人認為這是過度簡化，有人則如夢初醒。但無論你的第一反應如何，這個觀察揭示了一個被精美使用者介面和行銷話術掩蓋的根本事實：所有你正在使用的 AI 編碼工具，無論品牌如何華麗、功能如何繁多，其核心架構都驚人地相似。

要理解這個洞見的深刻含義，我們需要先回到基礎：什麼是大型語言模型？它是如何運作的？為什麼「300 行程式碼」就足以建構一個 coding agent？

本章將帶你踏上這段認知之旅。

---

## 1.2 理解 LLM 的基礎原理

在深入 coding agent 的架構之前，我們需要先理解它的「引擎」——大型語言模型（Large Language Model, LLM）。就像你不需要成為汽車工程師才能開車，但理解引擎的基本原理能讓你成為更好的駕駛者一樣，理解 LLM 的運作方式將幫助你更有效地使用（甚至建構）AI 編碼工具。

### 1.2.1 什麼是 Transformer？

現代大型語言模型的核心是一種稱為 **Transformer** 的神經網路架構。這個架構在 2017 年由 Google 的研究團隊在論文《Attention Is All You Need》中首次提出，從根本上改變了自然語言處理領域的面貌。

**為什麼 Transformer 如此重要？**

在 Transformer 出現之前，處理序列資料（如文字）的主流方法是循環神經網路（RNN）和長短期記憶網路（LSTM）。這些模型有一個致命的限制：它們必須**逐步處理**序列中的每個元素。想像你在閱讀一本書，但每次只能看一個字，而且必須在看下一個字之前完全處理完當前的字——這就是 RNN 的工作方式。

這種逐步處理帶來兩個問題：
1. **速度慢**：無法平行處理，即使有強大的 GPU 也難以加速
2. **長距離依賴問題**：句子開頭的資訊在處理到結尾時往往已經「遺忘」

Transformer 的革命性創新在於引入了 **Self-Attention（自注意力）機制**，讓模型能夠同時「看到」整個輸入序列的所有部分，並動態地決定每個部分對當前任務的重要性。

**Self-Attention 機制的直覺解釋**

想像你正在閱讀這個句子：

> 「這隻貓坐在墊子上，因為**牠**很累。」

當你的大腦處理「牠」這個詞時，你幾乎瞬間就知道它指的是「貓」而不是「墊子」。你的大腦如何做到這一點？它同時考慮了句子中的所有詞彙，並根據語義關係判斷哪些詞彙與「牠」最相關。

Self-Attention 機制就是這種認知過程的數學實現。對於輸入序列中的每個位置，它計算該位置與所有其他位置的「相關性分數」，然後使用這些分數來加權組合所有位置的資訊。

**數學公式（簡化版）**

Self-Attention 的核心計算可以表示為：

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

這個公式看起來可能有點嚇人，但讓我們用白話文解釋：

- **Q（Query）**：「我在尋找什麼？」——代表當前位置想要了解的資訊
- **K（Key）**：「我有什麼可以提供的？」——代表每個位置可以被查詢的特徵
- **V（Value）**：「我的實際內容是什麼？」——代表每個位置的實際資訊
- **QK^T**：計算 Query 與所有 Key 的相似度（點積）
- **softmax**：將相似度轉換為機率分布（所有值加起來等於 1）
- **除以 √d_k**：數學上的穩定性技巧，防止數值過大

最終結果是：每個位置都獲得了一個「上下文感知」的表示，融合了整個序列中與它最相關的資訊。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Transformer 架構簡圖                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    輸入：「這隻貓坐在墊子上」                                      │
│           ↓                                                      │
│    ┌─────────────────────────────────────────┐                  │
│    │         Tokenization（分詞）             │                  │
│    │   [這] [隻] [貓] [坐] [在] [墊] [子] [上]  │                  │
│    └─────────────────────────────────────────┘                  │
│           ↓                                                      │
│    ┌─────────────────────────────────────────┐                  │
│    │         Embedding（向量化）              │                  │
│    │   每個 token 變成高維向量                │                  │
│    └─────────────────────────────────────────┘                  │
│           ↓                                                      │
│    ┌─────────────────────────────────────────┐                  │
│    │    Self-Attention Layers × N           │                  │
│    │    每個 token 都能「看到」其他所有 token  │                  │
│    └─────────────────────────────────────────┘                  │
│           ↓                                                      │
│    ┌─────────────────────────────────────────┐                  │
│    │         Feed-Forward Network            │                  │
│    │         進一步處理每個位置的表示          │                  │
│    └─────────────────────────────────────────┘                  │
│           ↓                                                      │
│    輸出：下一個 token 的機率分布                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Transformer 的規模**

現代 LLM 的威力來自於規模。Claude、GPT-4 等模型通常包含：
- **數千億個參數**（可調整的數值）
- **數十層** Self-Attention 和 Feed-Forward 層
- 在**數兆個 token** 的文字資料上訓練

這種規模帶來了一個令人驚訝的結果：**湧現能力（Emergent Abilities）**。當模型規模超過某個閾值時，它突然展現出訓練時未明確教導的能力，如邏輯推理、程式碼生成、多步驟問題解決等。

### 1.2.2 Token 是什麼？

在上一節中，我們多次提到「token」這個詞。理解 token 的概念對於掌握 Context Engineering 至關重要，因為它直接關係到你能「餵給」LLM 多少資訊。

**Token 不等於字元，也不等於詞彙**

一個常見的誤解是將 token 等同於字元或單詞。實際上，token 是介於兩者之間的概念。現代 LLM 使用的分詞演算法（如 BPE、SentencePiece）會根據訓練資料中的統計模式，將文字切分成「子詞單元」。

讓我們看一個例子：

| 原始文字 | Token 切分 |
|----------|-----------|
| `Hello` | `Hello` (1 token) |
| `unhappiness` | `un` + `happiness` (2 tokens) |
| `supercalifragilisticexpialidocious` | 多個 tokens |
| `你好` | 可能是 1-2 tokens |
| `defenestration` | `def` + `en` + `est` + `ration` |

**BPE（Byte Pair Encoding）演算法簡介**

BPE 是最常用的分詞演算法之一。它的核心思想非常優雅：

1. 從單個字元開始（字典包含所有可能的字元）
2. 統計訓練資料中哪兩個相鄰 token 最常一起出現
3. 將這對 token 合併成一個新 token，加入字典
4. 重複步驟 2-3，直到字典達到預定大小

這個過程的結果是：
- **常見詞彙**（如 `the`、`and`）成為單一 token
- **罕見詞彙**被拆分成更小的子詞
- **未見過的詞彙**仍能被處理（拆成已知的子詞）

**為什麼 Token 計數如此重要？**

LLM 的「記憶」——Context Window——是以 token 為單位計算的。當廠商宣稱「200K token context window」時，這意味著模型一次最多能處理 200,000 個 token。

一個實用的估算規則：
- **英文**：1 token ≈ 4 個字元 ≈ 0.75 個單詞
- **程式碼**：通常比自然語言消耗更多 token（因為變數名稱、符號等）
- **中文**：1 個漢字通常是 1-2 個 token

這意味著：
- 200K token ≈ 15 萬英文單詞 ≈ 一本中等長度的書
- 但如果你的程式碼檔案平均每個消耗 1,000 token，你只能同時「看到」200 個檔案

### 1.2.3 自迴歸生成的本質

LLM 生成文字的方式是**自迴歸（Autoregressive）**的——它一次只產生一個 token，然後將這個新 token 加入輸入，再產生下一個 token。

這個過程可以用以下虛擬碼表示：

```python
def generate_text(prompt, max_tokens):
    tokens = tokenize(prompt)

    for _ in range(max_tokens):
        # ‹1› 模型預測下一個 token 的機率分布
        probabilities = model.predict_next_token(tokens)

        # ‹2› 根據機率分布選擇一個 token
        next_token = sample_from(probabilities)

        # ‹3› 將新 token 加入序列
        tokens.append(next_token)

        # ‹4› 如果遇到結束符號，停止生成
        if next_token == END_OF_TEXT:
            break

    return detokenize(tokens)
```

**機率與「溫度」**

在步驟 ‹2› 中，「根據機率分布選擇」有多種策略：

| 策略 | 說明 | 效果 |
|------|------|------|
| **Greedy**（溫度 = 0）| 總是選擇機率最高的 token | 確定性輸出，但可能單調 |
| **Sampling**（溫度 > 0）| 根據機率隨機選擇 | 更有創意，但可能不穩定 |
| **Top-K** | 只從前 K 個最可能的 token 中選擇 | 平衡創意與可靠性 |
| **Top-P (Nucleus)** | 從累積機率達到 P 的 token 中選擇 | 動態調整候選範圍 |

這解釋了為什麼你用相同的提示詞多次詢問 LLM，可能會得到略有不同的回答——因為每次生成都涉及隨機抽樣。

**自迴歸的含義**

「自迴歸」這個詞暗示了一個重要特性：**模型的輸出會影響它的下一步輸出**。這有深遠的影響：

1. **錯誤會累積**：如果模型在某一步產生了錯誤的 token，這個錯誤會成為後續生成的「事實」，可能導致整個回應偏離正軌。

2. **Context 只增不減**：每生成一個新 token，Context 就消耗一個位置。這就是為什麼長對話最終會「爆掉」。

3. **順序很重要**：模型只能「看到」已生成的 token，無法預見未來。這就是為什麼「先思考再回答」（Chain of Thought）的提示技巧有效——它讓模型在給出最終答案前，先把推理過程「寫出來」。

---

## 1.3 解剖一個 Coding Agent

現在我們理解了 LLM 的基本原理，讓我們回到 Geoffrey Huntley 的觀察：「300 行程式碼」如何將一個 LLM 變成一個 coding agent？

### 1.3.1 Agent 的四大組件

一個 coding agent 的核心架構可以分解為四個主要組件：

```
┌─────────────────────────────────────────────────────────────────┐
│                     Coding Agent 架構                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌───────────────────────────────────────────────────────┐     │
│   │              1. Harness Prompt                        │     │
│   │                 （系統提示詞）                          │     │
│   │   定義 agent 的角色、能力、行為準則                      │     │
│   └───────────────────────────────────────────────────────┘     │
│                              ↓                                   │
│   ┌───────────────────────────────────────────────────────┐     │
│   │              2. Inference Loop                        │     │
│   │                 （推論迴圈）                            │     │
│   │   輸入 → LLM 推論 → 判斷 → 執行/輸出 → 回饋 → 再推論    │     │
│   └───────────────────────────────────────────────────────┘     │
│                              ↓                                   │
│   ┌───────────────────────────────────────────────────────┐     │
│   │              3. Tool Registry                         │     │
│   │                 （工具註冊表）                          │     │
│   │   定義 agent 可以使用的「技能」：讀檔、執行命令等         │     │
│   └───────────────────────────────────────────────────────┘     │
│                              ↓                                   │
│   ┌───────────────────────────────────────────────────────┐     │
│   │              4. Context Management                    │     │
│   │                 （情境管理）                            │     │
│   │   追蹤對話歷史、工具結果、避免超過 token 上限           │     │
│   └───────────────────────────────────────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

讓我們逐一深入了解每個組件。

### 1.3.2 Harness Prompt：定義 Agent 的「人格」

Harness Prompt（有時也稱為 System Prompt）是你與 LLM 對話時設定的「背景說明」。它告訴 LLM：
- 你是誰（角色）
- 你能做什麼（能力）
- 你應該如何行為（準則）
- 你的輸出應該是什麼格式（規範）

一個典型的 coding agent Harness Prompt 結構如下：

```markdown
你是一個專業的軟體工程 AI 助手。

## 角色
你是一位經驗豐富的 senior 軟體工程師，擅長：
- 閱讀和理解複雜的程式碼庫
- 編寫高品質、可維護的程式碼
- 除錯和問題排解

## 可用工具
你可以使用以下工具來完成任務：
- read_file(path): 讀取指定檔案的內容
- write_file(path, content): 寫入內容到指定檔案
- execute_command(command): 執行終端命令
- search_code(pattern): 在程式碼庫中搜尋

## 行為準則
1. 在修改程式碼之前，先閱讀相關檔案以理解上下文
2. 解釋你的推理過程
3. 一次只做一件事
4. 如果不確定，先詢問而非假設

## 輸出格式
當你需要使用工具時，使用以下格式：
<tool_call>
{"name": "工具名稱", "parameters": {...}}
</tool_call>
```

這個 Harness Prompt 做了幾件關鍵的事：
1. **設定期望**：讓 LLM 知道它應該表現得像一個專業工程師
2. **定義能力邊界**：明確列出可用的工具
3. **建立行為框架**：提供決策的指導原則
4. **規範輸出格式**：確保 LLM 的輸出可以被程式解析

### 1.3.3 推論迴圈：Agent 的心跳

推論迴圈是 coding agent 的核心——Geoffrey Huntley 所說的「300 行程式碼」主要就是實現這個迴圈。

```go
// ‹1› 最簡化的推論迴圈實現
func InferenceLoop(client *LLMClient, systemPrompt string, tools []Tool) {
    // ‹2› 初始化對話歷史
    messages := []Message{
        {Role: "system", Content: systemPrompt},
    }

    for {
        // ‹3› 獲取使用者輸入
        userInput := getUserInput()
        messages = append(messages, Message{Role: "user", Content: userInput})

        // ‹4› 呼叫 LLM API
        response := client.CreateMessage(messages, tools)

        // ‹5› 判斷回應類型
        if response.HasToolCall() {
            // ‹6› 執行工具呼叫
            toolResult := executeToolCall(response.ToolCall)

            // ‹7› 將結果加入對話歷史
            messages = append(messages, Message{
                Role:    "assistant",
                Content: response.Content,
            })
            messages = append(messages, Message{
                Role:    "tool",
                Content: toolResult,
            })
            // 繼續迴圈，讓 LLM 處理工具結果
        } else {
            // ‹8› 純文字回應，顯示給使用者
            fmt.Println(response.Content)
            messages = append(messages, Message{
                Role:    "assistant",
                Content: response.Content,
            })
            // 等待下一次使用者輸入
        }
    }
}
```

這個迴圈的關鍵洞見是：

1. **LLM 不直接執行動作**：它只是「建議」要做什麼（透過工具呼叫）
2. **執行由外部程式碼處理**：你的程式碼負責實際執行工具並返回結果
3. **迴圈持續直到任務完成**：LLM 可以連續多次呼叫工具，逐步完成複雜任務

### 1.3.4 工具註冊：讓 LLM「看見」你的函數

Tool Use（或 Function Calling）是讓 LLM 能夠與外部世界互動的機制。當你「註冊」一個工具時，你實際上是在告訴 LLM：

1. 這個工具叫什麼名字
2. 它能做什麼
3. 它需要什麼參數

工具定義通常使用 JSON Schema 格式：

```json
{
  "name": "read_file",
  "description": "讀取指定路徑的檔案內容。適用於需要查看程式碼、配置文件或任何文字檔案的情況。",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "要讀取的檔案的完整路徑"
      }
    },
    "required": ["path"]
  }
}
```

**工具定義的藝術**

一個好的工具定義需要：
- **清晰的名稱**：動詞 + 名詞的格式（如 `read_file`、`execute_command`）
- **詳細的描述**：告訴 LLM「何時」應該使用這個工具
- **精確的參數定義**：使用 JSON Schema 規範參數類型和限制

工具描述的品質直接影響 LLM 選擇正確工具的能力。這就是為什麼 Geoffrey Huntley 說 MCP（Model Context Protocol）本質上是「帶有廣告牌的函數」——工具的描述就是它的「廣告」。

---

## 1.4 主流工具的架構比較

現在你已經理解了 coding agent 的基本架構，讓我們看看主流工具如何實現這個架構。

### 架構比較表

| 特性 | Cursor | Windsurf | Claude Code | GitHub Copilot |
|------|--------|----------|-------------|----------------|
| **底層 LLM** | Claude/GPT-4 | Claude/GPT | Claude | GPT-4/Codex |
| **推論迴圈** | ✓ 自建 | ✓ 自建 | ✓ 自建 | ✓ 自建 |
| **工具系統** | 內建 + 自訂 | 內建 + 自訂 | 內建 + MCP | 有限 |
| **Context 管理** | 自動 | 自動 | 自動 + 手動 | 自動 |
| **開放性** | 封閉 | 封閉 | 部分開源 | 封閉 |

**核心洞見：它們都是同一個模式的變體**

當你撇開 UI 差異和行銷話術，這些工具的核心都是：

```
System Prompt + LLM API + Tool Loop + Context Manager
```

這就是為什麼 Geoffrey Huntley 說「廠商比較是追尾行為」——你比較的不是本質差異，而是表面實現。真正重要的差異在於：

1. **Harness Prompt 的品質**：如何引導 LLM 行為
2. **工具集的設計**：提供哪些能力、如何定義
3. **Context 管理策略**：如何處理有限的記憶空間
4. **使用者體驗**：如何呈現結果、處理錯誤

---

## 1.5 從消費者到生產者

理解了這些原理後，你站在一個重要的十字路口：

**消費者心態**
- 被動等待工具更新
- 依賴廠商的功能設計
- 在工具比較中迷失
- 無法解決工具沒有提供的功能

**生產者心態**
- 理解底層原理，能夠判斷工具的真正價值
- 能夠自行擴展、修改、甚至創建工具
- 知道如何最大化利用現有工具
- 面對新工具時能快速評估其本質

本書的目標是將你從消費者轉變為生產者。在接下來的章節中，我們將：

- 深入理解 Context Window 的本質（第 2 章）
- 學習如何為不同任務選擇模型（第 3 章）
- 從零建構一個完整的 coding agent（第 4-6 章）
- 掌握 Ralph Wiggum Loop 的自主迭代技術（第 7-9 章）
- 在企業環境中應用這些知識（第 10-12 章）

---

## 本章小結

### 核心概念回顧

| 概念 | 定義 | 重要性 |
|------|------|--------|
| **Transformer** | 基於 Self-Attention 的神經網路架構 | LLM 的基礎技術 |
| **Token** | LLM 處理的最小文字單位 | 決定 Context 容量 |
| **自迴歸生成** | 逐一產生 token 的生成方式 | 理解 LLM 的行為模式 |
| **Harness Prompt** | 定義 agent 行為的系統提示詞 | agent 的「人格」 |
| **推論迴圈** | 輸入→推論→執行→回饋的核心流程 | agent 的「心跳」 |
| **Tool Use** | 讓 LLM 呼叫外部函數的機制 | agent 的「能力」 |

### 關鍵洞見

1. **所有 coding agent 共享相同的基本架構**：System Prompt + LLM + Tool Loop
2. **「300 行程式碼」不是誇張**：核心邏輯確實很簡潔
3. **理解原理比比較工具更重要**：原理讓你能夠評估、擴展、甚至創建工具
4. **Token 是稀缺資源**：理解 token 計數對有效使用 LLM 至關重要

### 練習題

1. **概念檢驗**：解釋為什麼 Self-Attention 機制比 RNN 更適合處理長序列？

2. **Token 計算**：估算以下程式碼片段大約消耗多少 token：
   ```python
   def fibonacci(n):
       if n <= 1:
           return n
       return fibonacci(n-1) + fibonacci(n-2)
   ```

3. **架構設計**：如果你要設計一個 coding agent 來自動修復 bug，你會定義哪些工具？為什麼？

4. **批判思考**：Geoffrey Huntley 說「你的同事會取代你的工作，不是 AI」。結合本章內容，你如何理解這句話？

---

## 延伸閱讀

### 學術論文
- Vaswani et al., "Attention Is All You Need" (2017) - Transformer 架構的原始論文
- Sennrich et al., "Neural Machine Translation of Rare Words with Subword Units" (2016) - BPE 演算法

### 技術文件
- Anthropic Claude API Documentation
- OpenAI Function Calling Guide

### 社群資源
- Geoffrey Huntley 的原始 Twitter/X 討論串
- Claude Code 開源部分的原始碼

---

## 下一章預告

在第 2 章，我們將深入探討 Context Window 的真正本質。你將學到：
- 為什麼 Context Window 更像記憶體陣列而非對話空間
- 「200K token」的真相：廣告容量 vs 實際可用容量
- 自迴歸失敗（Autoregressive Failure）的徵兆與預防
- Context Engineering 的核心原則

這些知識將幫助你更有效地使用任何 AI 編碼工具，並為後續章節的實作打下基礎。
