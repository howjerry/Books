# 第 2 章：Context Window 是陣列，不是對話

> 將 Context Window 視為有限且一次性的記憶體陣列

---

## 本章學習目標

完成本章後，你將能夠：

- 解釋為何 Context Window 更像是記憶體陣列而非對話空間
- 理解 Attention 機制中的位置編碼原理
- 分析 malloc/free 問題：為何 Context 只增不減
- 區分「廣告容量」與「實際可用容量」
- 識別自迴歸失敗（Autoregressive Failure）的徵兆
- 理解「Lost in the Middle」現象的學術背景
- 設計減少 Context 污染的策略

---

## 2.1 一個危險的隱喻

在第 1 章中，我們了解了 LLM 的基本運作原理。現在，我們要挑戰一個深植於大多數人心中的隱喻——「與 AI 對話」。

當你使用 ChatGPT、Claude 或任何 AI 聊天介面時，你看到的是一個類似即時通訊軟體的介面。你輸入一則訊息，AI 回覆一則訊息，來來回回，看起來就像是在和朋友聊天。這個設計讓 AI 變得平易近人，但它也植入了一個危險的心智模型：

**你以為你在進行一場對話，但實際上你是在管理一塊有限的記憶體。**

讓我們看看「對話」這個隱喻暗示了什麼：

| 對話隱喻暗示 | 實際情況 |
|-------------|----------|
| 對話可以無限延續 | Context Window 有固定上限 |
| 對方「記得」之前說過的話 | LLM 每次都重新「閱讀」整個歷史 |
| 可以隨時回到之前的話題 | 越早的內容，影響力可能越弱 |
| 說錯話可以澄清更正 | 錯誤的內容仍佔用 Context 空間 |
| 對話有「流動」感 | 每次推論都是獨立的快照 |

這不只是學術上的區分——理解這個差異將直接影響你使用 AI 工具的效率。

---

## 2.2 從記憶體的角度理解 Context Window

### 2.2.1 Context Window 的本質

如果你有程式設計背景，最準確的類比是：**Context Window 就像是一塊固定大小的記憶體陣列**。

```c
// 這就是 Context Window 的本質
#define MAX_TOKENS 200000
Token context_window[MAX_TOKENS];
int current_position = 0;
```

每當你輸入一則訊息，或 LLM 產生一則回應，這些內容都會被「寫入」這個陣列：

```c
void add_message(char* content) {
    int tokens_needed = tokenize_and_count(content);

    // 檢查是否還有空間
    if (current_position + tokens_needed > MAX_TOKENS) {
        // 沒有空間了！必須處理這個情況
        handle_overflow();
    }

    // 寫入 tokens
    for (int i = 0; i < tokens_needed; i++) {
        context_window[current_position++] = get_token(content, i);
    }
}
```

### 2.2.2 malloc 但沒有 free

在傳統的記憶體管理中，我們有兩個基本操作：
- **malloc**：分配記憶體
- **free**：釋放記憶體

但在 Context Window 中，你只有 malloc，**沒有 free**。

```c
// 傳統記憶體管理
char* buffer = malloc(1024);  // 分配
// ... 使用 buffer ...
free(buffer);                  // 釋放，記憶體可以重用

// Context Window 的「記憶體管理」
add_message("你好");          // 分配 2 tokens，無法釋放
add_message("請幫我寫程式");   // 再分配 5 tokens，無法釋放
// 這些 tokens 永遠佔用空間，直到 session 結束
```

這意味著：

1. **每一則訊息都會被「永久」寫入**：除非你開始新的 session
2. **工具呼叫的結果會被追加**：讀取一個大檔案？那些內容都會佔用空間
3. **錯誤和重試也會累積**：LLM 產生的錯誤回應、你的更正，全部都留在 Context 中
4. **Context 只會單調增加**：直到觸及上限

### 2.2.3 視覺化 Context 的使用

讓我們視覺化一個典型的 coding agent 對話 Context 是如何被使用的：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Context Window (200K tokens)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ████████ System Prompt (5,000 tokens)                           │
│                                                                  │
│ ████ Tool Definitions (3,000 tokens)                            │
│                                                                  │
│ ██ User: "幫我修復這個 bug" (50 tokens)                          │
│                                                                  │
│ ███ Assistant: "讓我先看看程式碼" (80 tokens)                     │
│                                                                  │
│ █████████████████████████████ Tool Result: read_file()          │
│                                (12,000 tokens - 大檔案！)        │
│                                                                  │
│ ████████ Assistant: "我發現問題了..." (2,000 tokens)             │
│                                                                  │
│ ██ User: "請修復它" (30 tokens)                                  │
│                                                                  │
│ ████████████████████████████████████ Tool Result: search_code() │
│                                      (15,000 tokens - 搜尋結果)  │
│                                                                  │
│ ███████████ Assistant: 分析 + 修復建議 (3,500 tokens)            │
│                                                                  │
│ ... 繼續累積 ...                                                 │
│                                                                  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 剩餘空間 │
│                                                                  │
│ 已使用: ~42,000 tokens (21%)                                     │
│ 剩餘: ~158,000 tokens                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

注意到了嗎？僅僅幾輪對話，我們就已經使用了 21% 的 Context。而且這些使用是**不可逆的**——即使你已經解決了問題，那個 12,000 token 的檔案內容仍然佔用著空間。

---

## 2.3 Attention 機制與位置編碼

要理解 Context Window 的行為，我們需要深入了解 Transformer 的 Attention 機制是如何處理「位置」資訊的。

### 2.3.1 位置編碼的必要性

回顧第 1 章，Self-Attention 機制的核心是計算每個 token 與其他所有 token 的「相關性」。但這裡有一個問題：**純粹的 Attention 計算是「位置無關」的**。

考慮這兩個句子：
- 「狗追貓」
- 「貓追狗」

如果沒有位置資訊，Attention 機制會認為這兩個句子是「相同」的——它們包含相同的詞彙，只是順序不同。但顯然，這兩個句子的意義完全不同！

因此，Transformer 需要某種方式來「告訴」模型每個 token 的位置。這就是**位置編碼（Positional Encoding）**的作用。

### 2.3.2 原始 Transformer 的正弦位置編碼

在 2017 年的原始 Transformer 論文中，研究者使用了一種基於正弦函數的位置編碼：

$$PE_{(pos, 2i)} = \sin\left(\frac{pos}{10000^{2i/d_{model}}}\right)$$

$$PE_{(pos, 2i+1)} = \cos\left(\frac{pos}{10000^{2i/d_{model}}}\right)$$

這個公式看起來複雜，但核心思想很優雅：

- **不同頻率的波**：每個維度使用不同頻率的正弦/餘弦函數
- **相對位置可計算**：任意兩個位置的編碼差異可以用簡單的線性變換表示
- **可外推**：理論上可以處理任意長度的序列

```
位置編碼視覺化（簡化）：

位置 0: [0.00, 1.00, 0.00, 1.00, ...]
位置 1: [0.84, 0.54, 0.01, 1.00, ...]
位置 2: [0.91, -0.42, 0.02, 1.00, ...]
位置 3: [0.14, -0.99, 0.03, 1.00, ...]
...
```

### 2.3.3 現代 LLM 的 RoPE 編碼

現代 LLM（如 Claude、LLaMA）通常使用更先進的位置編碼方法，最著名的是 **RoPE（Rotary Position Embedding）**。

RoPE 的核心思想是：**使用旋轉矩陣來編碼位置資訊**。

對於位置 $m$ 的 token，其 Query 和 Key 向量會乘以一個旋轉矩陣：

$$f_q(x_m, m) = R_{\Theta,m} W_q x_m$$

其中 $R_{\Theta,m}$ 是一個依賴於位置 $m$ 的旋轉矩陣。

**RoPE 的優勢**：

1. **相對位置感知**：兩個 token 的 attention 分數只依賴於它們的相對位置
2. **更好的外推性**：對於訓練時未見過的位置，表現更穩定
3. **計算效率**：可以融入 Attention 計算，不增加額外開銷

### 2.3.4 位置編碼與「Lost in the Middle」現象

2023 年的一篇重要論文《Lost in the Middle: How Language Models Use Long Contexts》揭示了一個令人驚訝的發現：

> 當相關資訊位於 Context 的**中間**位置時，LLM 的效能顯著下降。

研究者進行了一系列實驗，將關鍵資訊放在 Context 的不同位置，發現：

```
┌─────────────────────────────────────────────────────────────────┐
│           LLM 對不同位置資訊的利用效率                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  效能                                                            │
│   ▲                                                             │
│   │  ██                                              ████████   │
│   │  ████                                          ██████████   │
│   │  ██████                                      ████████████   │
│   │  ████████                                  ██████████████   │
│   │  ██████████            ████████          ████████████████   │
│   │  ████████████        ████████████      ██████████████████   │
│   │  ██████████████    ████████████████  ████████████████████   │
│   │  ████████████████████████████████████████████████████████   │
│   └──────────────────────────────────────────────────────────►  │
│      開頭          中間位置                              結尾    │
│                                                                  │
│  U 型曲線：開頭和結尾的資訊被利用得更好                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**這對 Context Engineering 的啟示**：

1. **重要資訊放在開頭或結尾**：System Prompt 放開頭是對的
2. **避免把關鍵指令埋在中間**：如果你有重要的限制條件，考慮在對話的最後再次強調
3. **Context 長度不是越長越好**：即使你有 200K 的 Context，中間的內容可能被「忽略」

---

## 2.4 「200K Tokens」的真相

### 2.4.1 廣告容量 vs 實際可用容量

當廠商宣傳「200K token context window」時，這是**理論上的最大容量**。但就像一個 1TB 的硬碟出廠時只有 930GB 可用一樣，Context Window 的實際可用空間也遠小於標稱值。

讓我們做一個實際的預算計算：

```
┌─────────────────────────────────────────────────────────────────┐
│              Context Window 預算分析                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 總容量：200,000 tokens                                           │
│                                                                  │
│ ═══════════════════════════════════════════════════════════════ │
│                                                                  │
│ 固定開銷：                                                       │
│   System Prompt              5,000 - 15,000 tokens              │
│   工具定義（假設 10 個工具）   5,000 - 20,000 tokens              │
│   預留輸出空間                4,000 - 8,000 tokens               │
│   ─────────────────────────────────────────                     │
│   小計                       14,000 - 43,000 tokens              │
│                                                                  │
│ ═══════════════════════════════════════════════════════════════ │
│                                                                  │
│ 實際可用於對話的空間：                                            │
│   最佳情況                   186,000 tokens                      │
│   典型情況                   ~160,000 tokens                     │
│   工具密集型任務              ~120,000 tokens                     │
│                                                                  │
│ ═══════════════════════════════════════════════════════════════ │
│                                                                  │
│ 結論：實際可用空間約為標稱值的 60-80%                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4.2 工具呼叫的隱藏成本

每次工具呼叫都有「隱藏的」Context 成本：

```python
# 一次 read_file 呼叫的 Context 成本分解

# 1. LLM 輸出的工具呼叫指令
tool_call_cost = 150  # tokens

# 2. 工具返回的結果（這是最大的變數）
file_content_cost = len(file_content) / 4  # 平均每 4 字元 1 token

# 3. 包裝工具結果的格式開銷
wrapper_cost = 50  # tokens

# 總成本
total_cost = tool_call_cost + file_content_cost + wrapper_cost
```

**實際案例**：

假設你讓 agent 搜尋程式碼庫中的某個函數：

| 操作 | Token 消耗 |
|------|-----------|
| 你的請求：「找到 handleLogin 函數」 | ~20 tokens |
| Agent 分析並決定搜尋 | ~100 tokens |
| 搜尋工具呼叫 | ~50 tokens |
| 搜尋結果（假設找到 10 個檔案的摘要）| ~3,000 tokens |
| Agent 分析搜尋結果 | ~500 tokens |
| Agent 決定讀取最相關的檔案 | ~100 tokens |
| read_file 工具呼叫 | ~30 tokens |
| 檔案內容 | ~2,000 tokens |
| Agent 最終回應 | ~500 tokens |
| **總計** | **~6,300 tokens** |

僅僅一個「找函數」的任務，就消耗了超過 6,000 tokens！

### 2.4.3 Token 計數的實用技巧

不同類型的內容有不同的 token 效率：

| 內容類型 | Token 效率 | 說明 |
|----------|-----------|------|
| 英文散文 | ~0.75 words/token | 最高效 |
| 英文程式碼 | ~0.5 words/token | 符號較多 |
| 中文文字 | ~0.5-0.7 字/token | 取決於常用程度 |
| JSON 資料 | ~0.3 words/token | 結構開銷大 |
| Base64 編碼 | ~0.2 chars/token | 非常低效 |

**實用建議**：

1. **壓縮 JSON 輸出**：移除不必要的空白和縮排
2. **摘要而非全文**：讓工具返回摘要而非完整內容
3. **分批處理**：如果需要處理多個檔案，分批進行而非一次載入

---

## 2.5 自迴歸失敗的陷阱

### 2.5.1 什麼是自迴歸失敗？

當 Context 變得過長、過於混亂，或包含相互矛盾的資訊時，LLM 的輸出品質會顯著下降。這種現象稱為**自迴歸失敗（Autoregressive Failure）**。

回顧第 1 章，LLM 的生成是自迴歸的——每個新 token 都依賴於之前所有 token。這意味著：

```
生成過程：

Context: [System Prompt] [對話歷史...] [最新問題]
                ↓
          LLM 處理整個 Context
                ↓
          產生 Token 1 → 加入 Context
                ↓
          LLM 處理 Context + Token 1
                ↓
          產生 Token 2 → 加入 Context
                ↓
               ...
```

當 Context 出現問題時，錯誤會**累積和放大**。

### 2.5.2 自迴歸失敗的徵兆

以下是常見的自迴歸失敗徵兆：

**1. 重複內容**

```
Agent: 我會先讀取 config.json 檔案。
Agent: 讓我讀取 config.json 檔案來查看配置。
Agent: 我需要讀取 config.json 來了解當前配置。
```

LLM 陷入了重複的模式，因為 Context 中已經有類似的內容，模型傾向於生成相似的輸出。

**2. 遺忘早期指令**

```
User: 請用 TypeScript 撰寫，不要使用 any 類型。
...（很多對話後）...
Agent: 這是程式碼：
       function process(data: any) { ... }  // 使用了 any！
```

早期的指令被「淹沒」在大量的 Context 中。

**3. 自相矛盾**

```
Agent: 這個函數應該返回 Promise<string>。
...（稍後）...
Agent: 這個函數應該返回 string（同步）。
```

Context 中包含了不一致的資訊，LLM 在不同時間點可能「注意到」不同的部分。

**4. 工具呼叫異常**

```
Agent: <tool_call>{"name": "read_file", "params": {"path": "src/
Agent: I'll read the file now.
Agent: <tool_call>{"name": "read_
```

工具呼叫的格式變得不穩定，可能是因為 Context 中有太多不同格式的範例。

### 2.5.3 為什麼會發生自迴歸失敗？

從技術角度分析：

**1. Attention 分散**

當 Context 很長時，Attention 機制需要在更多位置之間分配「注意力」。這可能導致關鍵資訊獲得的 attention 權重降低。

```
短 Context：重要資訊獲得 15% 的 attention 權重
長 Context：重要資訊獲得 3% 的 attention 權重
```

**2. 訊噪比下降**

Context 中的每一段內容都是「訊號」，但不是所有訊號都與當前任務相關。當 Context 增長：

$$\text{訊噪比} = \frac{\text{相關資訊}}{\text{總 Context 長度}} \downarrow$$

**3. 機率累積偏差**

自迴歸生成中，每一步都有微小的錯誤機率。這些錯誤會累積：

$$P(\text{整體正確}) = \prod_{i=1}^{n} P(\text{第 } i \text{ 步正確})$$

如果每步正確率是 99%，經過 100 步後，整體正確率只有約 37%。

---

## 2.6 實驗：觀察 Context 污染

讓我們設計一個實驗，親眼見證 Context 污染如何影響輸出品質。

### 2.6.1 實驗設計

**實驗目標**：比較「乾淨 Context」與「污染 Context」對 LLM 回應品質的影響。

**實驗設置**：

```
實驗 A（乾淨 Context）：
┌────────────────────────────────────────┐
│ System: 你是一個程式設計助手。          │
│ User: 請用 Python 寫一個快速排序函數。  │
└────────────────────────────────────────┘

實驗 B（污染 Context）：
┌────────────────────────────────────────┐
│ System: 你是一個程式設計助手。          │
│ User: 什麼是氣泡排序？                  │
│ Assistant: [氣泡排序的詳細解釋]         │
│ User: 請用 JavaScript 實作              │
│ Assistant: [JavaScript 氣泡排序程式碼]  │
│ User: 這個有 bug，請修復               │
│ Assistant: [修復後的程式碼]             │
│ User: 改用遞迴實作                      │
│ Assistant: [遞迴版本，但其實不適合氣泡] │
│ User: 請用 Python 寫一個快速排序函數。  │
└────────────────────────────────────────┘
```

### 2.6.2 預期結果

| 實驗 | 預期品質 | 原因 |
|------|----------|------|
| A（乾淨）| 高 | LLM 專注於單一任務 |
| B（污染）| 中低 | Context 中有干擾因素 |

實驗 B 可能出現的問題：
1. 混淆排序演算法（可能「借用」氣泡排序的邏輯）
2. 混淆程式語言（可能出現 JavaScript 語法）
3. 不必要的遞迴（受「改用遞迴」的影響）
4. 引用之前對話中的變數名稱

### 2.6.3 實驗的啟示

這個實驗展示了一個重要原則：

> **Context 不是免費的。每一則訊息都有成本——不只是 token 數量的成本，還有「注意力干擾」的成本。**

實用建議：
1. **新任務開新 session**：不要在一個 session 中做太多不相關的事
2. **清晰的任務邊界**：明確告訴 LLM「現在開始新任務」
3. **必要時重述關鍵資訊**：在長對話中定期重申重要的限制條件

---

## 2.7 Context Engineering 的核心原則

### 2.7.1 精簡優先原則

> **只載入必要的資訊，不多也不少。**

```python
# ❌ 不好的做法
def get_context_for_bug_fix():
    # 載入整個專案的所有檔案
    return read_entire_project()

# ✅ 好的做法
def get_context_for_bug_fix(bug_report):
    relevant_files = identify_relevant_files(bug_report)
    return [read_file(f) for f in relevant_files[:5]]  # 只讀最相關的 5 個
```

### 2.7.2 結構化輸入原則

> **讓 LLM 更容易解析和理解你的輸入。**

```markdown
❌ 不好的輸入：
幫我看看這個程式碼有什麼問題它應該要計算總和但是好像算錯了這是程式碼 function sum(arr) { let total = 0; for (let i = 0; i <= arr.length; i++) { total += arr[i]; } return total; }

✅ 好的輸入：
## 問題描述
函數應該計算陣列的總和，但返回 NaN。

## 程式碼
```javascript
function sum(arr) {
    let total = 0;
    for (let i = 0; i <= arr.length; i++) {
        total += arr[i];
    }
    return total;
}
```

## 測試案例
- sum([1, 2, 3]) 應返回 6，實際返回 NaN
```

### 2.7.3 適時清理原則

> **定期開啟新 session，而非無限延續。**

經驗法則：
- **Token 使用超過 50%**：考慮開始新 session
- **任務類型轉變**：從寫程式碼轉到寫文件時，開新 session
- **出現自迴歸失敗徵兆**：立即開新 session

### 2.7.4 監控消耗原則

> **追蹤 token 使用量，建立預算意識。**

```python
class ContextBudget:
    def __init__(self, max_tokens=200000):
        self.max_tokens = max_tokens
        self.used_tokens = 0
        self.warning_threshold = 0.7  # 70% 時發出警告

    def add(self, content):
        tokens = count_tokens(content)
        self.used_tokens += tokens

        if self.used_tokens / self.max_tokens > self.warning_threshold:
            print(f"⚠️ Context 使用率: {self.used_tokens}/{self.max_tokens} ({self.usage_percent}%)")
            print("建議：考慮開始新的 session")

    @property
    def usage_percent(self):
        return round(self.used_tokens / self.max_tokens * 100, 1)
```

---

## 本章小結

### 核心概念回顧

| 概念 | 定義 | 重要性 |
|------|------|--------|
| **Context Window** | LLM 一次能處理的最大 token 數 | 決定了對話的「記憶容量」 |
| **位置編碼** | 讓 Transformer 理解 token 順序的機制 | 影響長序列的處理能力 |
| **Lost in the Middle** | 中間位置資訊被忽略的現象 | 指導重要資訊的放置策略 |
| **自迴歸失敗** | Context 問題導致的輸出品質下降 | 需要主動監控和預防 |
| **Context 污染** | 無關資訊累積導致的效能下降 | 需要精簡和清理策略 |

### 關鍵洞見

1. **Context Window 是記憶體，不是對話**：採用記憶體管理的心智模型
2. **200K token 不等於 200K 可用**：考慮固定開銷後，實際可用約 60-80%
3. **位置很重要**：重要資訊放開頭或結尾，避免中間位置
4. **工具呼叫有隱藏成本**：每次呼叫都會消耗顯著的 Context 空間
5. **預防勝於治療**：主動管理 Context，而非等到問題發生

### 練習題

1. **預算計算**：假設你的 System Prompt 有 8,000 tokens，定義了 15 個工具（每個平均 1,500 tokens），Context Window 是 128K tokens。計算實際可用於對話的 token 數量。

2. **優化策略**：你正在使用一個 coding agent 處理一個大型專案。在對話進行了 30 分鐘後，你注意到 agent 開始重複之前的建議。你應該怎麼做？列出三個可能的解決方案。

3. **實驗設計**：設計一個實驗來測量不同位置編碼（正弦 vs RoPE）對長序列理解能力的影響。你會使用什麼指標？

4. **批判思考**：有人說「Context Window 越大越好，200K 總比 32K 強」。根據本章內容，評價這個觀點的正確性和局限性。

---

## 延伸閱讀

### 學術論文
- Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" (2023)
- Su et al., "RoFormer: Enhanced Transformer with Rotary Position Embedding" (2021)
- Press et al., "Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation" (2022)

### 技術文件
- Anthropic Claude Context Window Documentation
- OpenAI Token Counting Guide

---

## 下一章預告

在第 3 章，我們將探討一個關鍵區分：不是所有 LLM 都適合作為 Agent。你將學到：

- Oracle vs Agentic 模型的根本差異
- RLHF 和 Constitutional AI 如何影響模型行為
- Claude Sonnet 的「機械松鼠」特性
- 如何為不同任務選擇正確的模型
- 將 Oracle 模型作為工具註冊給 Agentic 模型的進階技巧

這些知識將幫助你更有策略地選擇和組合不同的模型，最大化 AI 工具的效能。
