# Chapter 2: Prompt 工程與結構化輸出

> 「與 LLM 對話是一門藝術，但結構化輸出是一門工程。」

---

## 本章學習目標

完成本章後，你將能夠：

- 掌握進階 Prompt 技巧：Chain-of-Thought (CoT) 與 Few-Shot Learning
- 使用 Pydantic 定義嚴格的輸出結構
- 實作意圖分類器 (Intent Classifier)
- 建立 TechAssist v0.2：具備意圖理解能力的助理

---

## 2.1 場景引入：讓 TechAssist 更聰明

回顧 TechAssist v0.1，它能回答技術問題，但有個致命問題：**它把所有輸入都當成技術問題**。

想像這些場景：

| 使用者輸入 | v0.1 的反應 | 我們期望的反應 |
|------------|-------------|----------------|
| 「你好」 | 開始解釋技術概念 | 友善打招呼 |
| 「幫我重構這段程式碼：...」 | 只給出解釋 | 實際進行重構 |
| 「Python 和 Go 哪個好？」 | 給出偏頗的答案 | 客觀比較 |
| 「我很沮喪，程式一直跑不動」 | 忽略情緒 | 先同理再協助 |

要解決這個問題，TechAssist 需要：

1. **意圖分類**：判斷使用者想做什麼
2. **結構化輸出**：讓輸出可被程式解析
3. **動態路由**：根據意圖採取不同行動

讓我們從 Prompt 工程開始。

---

## 2.2 進階 Prompt 技巧

### 2.2.1 Chain-of-Thought (CoT)：讓 LLM 展示思考過程

研究顯示，讓 LLM 「先思考再回答」能顯著提升複雜任務的準確率。

**原理**：要求模型在給出最終答案前，先輸出推理步驟。

```python
from langchain_core.prompts import ChatPromptTemplate

# ❌ 直接要求答案（容易出錯）
naive_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是數學老師。"),
    ("human", "如果一個班級有 30 人，其中 40% 是女生，女生中有 1/3 戴眼鏡，有多少女生戴眼鏡？")
])

# ✅ Chain-of-Thought（逐步推理）
cot_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是數學老師。
回答問題時，請按以下步驟進行：

1. **理解問題**：重述問題的關鍵資訊
2. **列出已知條件**：提取所有數值
3. **逐步計算**：展示每一步計算過程
4. **驗證答案**：確認計算是否合理
5. **給出最終答案**：明確標示答案"""),
    ("human", "{question}")
])
```

**CoT 變體**：

| 變體 | 說明 | 適用場景 |
|------|------|----------|
| **Zero-Shot CoT** | 只加「讓我們一步一步思考」 | 快速提升推理 |
| **Few-Shot CoT** | 提供帶推理過程的範例 | 複雜邏輯任務 |
| **Self-Consistency** | 多次採樣取多數答案 | 需要高準確度 |

### 2.2.2 Few-Shot Learning：用範例教導 LLM

當任務難以用文字描述，或你需要特定的輸出風格時，Few-Shot Learning 非常有效。

```python
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate

# ‹1› 定義範例
examples = [
    {
        "input": "什麼是變數？",
        "output": """**簡答**：變數是儲存資料的容器。

**詳解**：
在程式中，變數就像一個有名字的盒子，你可以把資料放進去。

**範例**：
```python
name = "Alice"  # 字串變數
age = 25        # 整數變數
```"""
    },
    {
        "input": "解釋 for 迴圈",
        "output": """**簡答**：for 迴圈用於重複執行程式碼指定次數。

**詳解**：
當你需要對一系列元素執行相同操作時，使用 for 迴圈。

**範例**：
```python
for i in range(3):
    print(f"第 {i+1} 次")
# 輸出：
# 第 1 次
# 第 2 次
# 第 3 次
```"""
    }
]

# ‹2› 建立範例模板
example_prompt = ChatPromptTemplate.from_messages([
    ("human", "{input}"),
    ("ai", "{output}")
])

# ‹3› 建立 Few-Shot Prompt
few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=examples,
)

# ‹4› 組合完整 Prompt
final_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 TechAssist。請按照範例的格式回答技術問題。"),
    few_shot_prompt,
    ("human", "{question}")
])

# 檢視完整 Prompt
print(final_prompt.format(question="什麼是遞迴？"))
```

### 2.2.3 Prompt 優化檢查清單

在設計 Prompt 時，使用這個檢查清單：

| 項目 | 問題 | 優化方向 |
|------|------|----------|
| **角色定義** | LLM 知道自己是誰嗎？ | 明確定義角色與專長 |
| **任務描述** | 目標清楚嗎？ | 使用動詞開頭描述期望行為 |
| **輸出格式** | 輸出結構明確嗎？ | 提供格式範例或 Schema |
| **限制條件** | 有沒有明確的禁止事項？ | 列出「不要做什麼」 |
| **範例** | 需要 Few-Shot 嗎？ | 提供 2-5 個代表性範例 |
| **思考引導** | 需要 CoT 嗎？ | 加入「請先思考再回答」 |

---

## 2.3 結構化輸出：用 Pydantic 馴服 LLM

### 2.3.1 為什麼需要結構化輸出？

自由文本輸出有幾個問題：

```python
# LLM 可能這樣回答：
response_1 = "難度是中等"
response_2 = "這是一個中等難度的問題"
response_3 = "Difficulty: Medium"
```

這三個回答都表達同樣的意思，但程式很難統一處理。

**結構化輸出**讓 LLM 按照預定義的 Schema 輸出：

```python
{
    "difficulty": "medium",
    "confidence": 0.85
}
```

### 2.3.2 使用 PydanticOutputParser

Pydantic 是 Python 最流行的資料驗證庫，LangChain 深度整合了它：

```python
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from enum import Enum

# ‹1› 定義難度等級
class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

# ‹2› 定義輸出 Schema
class TechExplanation(BaseModel):
    """技術概念的結構化解釋"""

    concept: str = Field(description="概念名稱")
    one_liner: str = Field(description="一句話解釋，不超過 30 字")
    explanation: str = Field(description="詳細解釋，150-300 字")
    use_cases: list[str] = Field(description="3-5 個實際使用場景")
    code_example: str | None = Field(
        default=None,
        description="程式碼範例（如適用）"
    )
    difficulty: DifficultyLevel = Field(description="難度等級")
    related_concepts: list[str] = Field(description="相關概念，2-4 個")

# ‹3› 建立解析器
parser = PydanticOutputParser(pydantic_object=TechExplanation)

# ‹4› 查看格式說明
print(parser.get_format_instructions())
```

輸出的格式說明（簡化）：

```
The output should be formatted as a JSON instance that conforms to the JSON schema below.

{
    "concept": "string",
    "one_liner": "string",
    "explanation": "string",
    "use_cases": ["string"],
    "code_example": "string or null",
    "difficulty": "beginner|intermediate|advanced",
    "related_concepts": ["string"]
}
```

### 2.3.3 整合到 Chain

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

# ‹1› 建立包含格式說明的 Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """你是 TechAssist，專業的技術教育專家。
請按照指定的 JSON 格式輸出你的解釋。

{format_instructions}"""),
    ("human", "請解釋：{concept}")
])

# ‹2› 注入格式說明
prompt_with_format = prompt.partial(
    format_instructions=parser.get_format_instructions()
)

# ‹3› 建立 Chain
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

chain = prompt_with_format | llm | parser

# ‹4› 調用並獲得結構化輸出
result = chain.invoke({"concept": "依賴注入"})

# result 是 TechExplanation 物件
print(f"概念：{result.concept}")
print(f"一句話：{result.one_liner}")
print(f"難度：{result.difficulty.value}")
print(f"使用場景：{', '.join(result.use_cases)}")
```

### 2.3.4 處理解析錯誤

LLM 有時候會輸出不符合格式的內容，我們需要優雅地處理：

```python
from langchain_core.output_parsers import PydanticOutputParser
from langchain.output_parsers import OutputFixingParser

# ‹1› 原始解析器
base_parser = PydanticOutputParser(pydantic_object=TechExplanation)

# ‹2› 包裝成自動修復解析器
fixing_parser = OutputFixingParser.from_llm(
    parser=base_parser,
    llm=llm
)

# 當解析失敗時，OutputFixingParser 會：
# 1. 捕獲錯誤
# 2. 將錯誤和原始輸出發送給 LLM
# 3. 請求 LLM 修正輸出格式
```

### 2.3.5 使用 with_structured_output（推薦）

Claude 和 GPT-4 都支援原生的結構化輸出功能，更加可靠：

```python
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

class TechExplanation(BaseModel):
    concept: str
    one_liner: str
    difficulty: str

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

# ‹1› 使用 with_structured_output
structured_llm = llm.with_structured_output(TechExplanation)

# ‹2› 直接調用，輸出已經是 Pydantic 物件
result = structured_llm.invoke("解釋什麼是 API")
print(result.concept)  # 直接存取屬性
```

這種方式的優點：

- 更可靠：模型原生支援
- 更簡潔：不需要在 Prompt 中加入格式說明
- 更快速：減少 token 消耗

---

## 2.4 實作：意圖分類器

現在，讓我們建立一個意圖分類器，讓 TechAssist 能夠判斷使用者想做什麼。

### 2.4.1 定義意圖類型

```python
# techassist/intents.py
from enum import Enum
from pydantic import BaseModel, Field

class Intent(str, Enum):
    """使用者意圖類型"""
    GREETING = "greeting"           # 打招呼
    FAREWELL = "farewell"           # 道別
    TECH_QUESTION = "tech_question" # 技術問題
    CODE_REVIEW = "code_review"     # 程式碼審查
    CODE_GENERATION = "code_generation"  # 程式碼生成
    COMPARISON = "comparison"       # 技術比較
    TROUBLESHOOTING = "troubleshooting"  # 問題排解
    OFF_TOPIC = "off_topic"         # 非技術話題
    UNCLEAR = "unclear"             # 不清楚


class IntentClassification(BaseModel):
    """意圖分類結果"""

    intent: Intent = Field(description="判斷的意圖類型")
    confidence: float = Field(
        description="信心分數，0.0-1.0",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        description="判斷理由，簡短說明為什麼是這個意圖"
    )
    extracted_topic: str | None = Field(
        default=None,
        description="提取的主題（如適用）"
    )
    suggested_action: str = Field(
        description="建議的下一步行動"
    )
```

### 2.4.2 建立分類器 Chain

```python
# techassist/classifier.py
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from .intents import IntentClassification, Intent

# ‹1› 分類器 Prompt
CLASSIFIER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是 TechAssist 的意圖分類模組。

## 任務
分析使用者的輸入，判斷其意圖類型。

## 意圖類型說明
- greeting: 打招呼、問候（如：你好、Hi、早安）
- farewell: 道別（如：再見、拜拜、感謝）
- tech_question: 詢問技術概念（如：什麼是 API？）
- code_review: 請求審查程式碼（如：幫我看看這段程式碼）
- code_generation: 請求生成程式碼（如：幫我寫一個函數）
- comparison: 比較技術選項（如：Python 和 Java 哪個好？）
- troubleshooting: 排解問題（如：我的程式報錯了）
- off_topic: 與技術無關的話題
- unclear: 無法判斷意圖

## 判斷原則
1. 優先考慮明確的意圖指示詞
2. 如果包含程式碼，考慮是 code_review 或 troubleshooting
3. 如果有「好」、「優」、「選」等詞，考慮是 comparison
4. 信心分數反映確定程度，模糊時給較低分數

## 建議行動
根據意圖給出具體的處理建議。"""),
    ("human", "請分析這個輸入的意圖：\n\n{user_input}")
])


def create_intent_classifier():
    """建立意圖分類器"""
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

    # ‹2› 使用 with_structured_output
    structured_llm = llm.with_structured_output(IntentClassification)

    # ‹3› 組合 Chain
    chain = CLASSIFIER_PROMPT | structured_llm

    return chain
```

### 2.4.3 測試分類器

```python
# test_classifier.py
from techassist.classifier import create_intent_classifier

classifier = create_intent_classifier()

test_cases = [
    "你好！",
    "什麼是 REST API？",
    "幫我看看這段程式碼有沒有問題：def foo(): pass",
    "Python 和 Go 哪個效能比較好？",
    "我的程式一直報 TypeError，怎麼辦？",
    "今天天氣真好",
    "asdfghjkl",
]

for user_input in test_cases:
    result = classifier.invoke({"user_input": user_input})
    print(f"\n輸入：{user_input}")
    print(f"意圖：{result.intent.value}")
    print(f"信心：{result.confidence:.2f}")
    print(f"理由：{result.reasoning}")
    print(f"建議：{result.suggested_action}")
    print("-" * 50)
```

預期輸出：

```
輸入：你好！
意圖：greeting
信心：0.98
理由：這是一個標準的中文問候語
建議：回覆問候，並詢問有什麼可以幫助的

--------------------------------------------------

輸入：什麼是 REST API？
意圖：tech_question
信心：0.95
理由：使用「什麼是」句型詢問技術概念
建議：提供 REST API 的清晰解釋，包含定義、特點和範例

--------------------------------------------------

輸入：Python 和 Go 哪個效能比較好？
意圖：comparison
信心：0.92
理由：使用「哪個...比較好」的比較句型
建議：客觀比較兩種語言的效能特點，避免偏頗
```

### 2.4.4 建立意圖路由器

根據意圖，我們可以將請求路由到不同的處理器：

```python
# techassist/router.py
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from .intents import Intent, IntentClassification
from .classifier import create_intent_classifier

def route_by_intent(classification: IntentClassification) -> str:
    """根據意圖返回對應的處理器名稱"""
    routing_map = {
        Intent.GREETING: "greeting_handler",
        Intent.FAREWELL: "farewell_handler",
        Intent.TECH_QUESTION: "tech_qa_handler",
        Intent.CODE_REVIEW: "code_review_handler",
        Intent.CODE_GENERATION: "code_gen_handler",
        Intent.COMPARISON: "comparison_handler",
        Intent.TROUBLESHOOTING: "troubleshoot_handler",
        Intent.OFF_TOPIC: "off_topic_handler",
        Intent.UNCLEAR: "clarification_handler",
    }
    return routing_map.get(classification.intent, "default_handler")


def create_routing_chain():
    """建立路由 Chain"""
    classifier = create_intent_classifier()

    chain = (
        {"user_input": RunnablePassthrough()}
        | classifier
        | RunnableLambda(lambda x: {
            "classification": x,
            "handler": route_by_intent(x)
        })
    )

    return chain
```

---

## 2.5 實作：TechAssist v0.2

現在，讓我們將意圖分類整合到 TechAssist 中。

### 2.5.1 處理器模組

```python
# techassist/handlers.py
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
parser = StrOutputParser()

# ‹1› 問候處理器
greeting_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 TechAssist。用戶在打招呼，請友善回應並詢問有什麼可以幫助的。保持簡短（2-3 句話）。"),
    ("human", "{user_input}")
])
greeting_handler = greeting_prompt | llm | parser

# ‹2› 技術問答處理器
tech_qa_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是 TechAssist，專業的技術助理。

回答時請：
1. 先給一句話總結
2. 再詳細解釋（100-200 字）
3. 如適用，提供程式碼範例
4. 使用繁體中文"""),
    ("human", "{user_input}")
])
tech_qa_handler = tech_qa_prompt | llm | parser

# ‹3› 比較處理器
comparison_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是 TechAssist，專業的技術顧問。

比較技術選項時：
1. 保持客觀，不要有偏見
2. 列出各自的優缺點
3. 說明適用場景
4. 如果適合，給出建議
5. 使用表格呈現比較結果"""),
    ("human", "{user_input}")
])
comparison_handler = comparison_prompt | llm | parser

# ‹4› 問題排解處理器
troubleshoot_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是 TechAssist，專業的除錯專家。

排解問題時：
1. 確認錯誤訊息和症狀
2. 列出可能的原因（從最常見開始）
3. 提供逐步的解決方案
4. 如有程式碼，分析可能的問題點"""),
    ("human", "{user_input}")
])
troubleshoot_handler = troubleshoot_prompt | llm | parser

# ‹5› 非技術話題處理器
off_topic_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是 TechAssist，專業的技術助理。
用戶的問題不是技術相關。請禮貌地告知你專注於技術問題，並詢問是否有技術問題需要幫助。保持友善，不要讓用戶感到被拒絕。"""),
    ("human", "{user_input}")
])
off_topic_handler = off_topic_prompt | llm | parser

# ‹6› 處理器映射
HANDLERS = {
    "greeting_handler": greeting_handler,
    "farewell_handler": greeting_handler,  # 使用相同處理器
    "tech_qa_handler": tech_qa_handler,
    "code_review_handler": tech_qa_handler,  # 後續章節會專門實作
    "code_gen_handler": tech_qa_handler,     # 後續章節會專門實作
    "comparison_handler": comparison_handler,
    "troubleshoot_handler": troubleshoot_handler,
    "off_topic_handler": off_topic_handler,
    "clarification_handler": off_topic_handler,
    "default_handler": tech_qa_handler,
}
```

### 2.5.2 整合主流程

```python
# techassist/core.py
from .classifier import create_intent_classifier
from .router import route_by_intent
from .handlers import HANDLERS

class TechAssistV2:
    """TechAssist v0.2 - 具備意圖理解能力"""

    def __init__(self):
        self.classifier = create_intent_classifier()

    def process(self, user_input: str) -> dict:
        """處理使用者輸入

        Args:
            user_input: 使用者的輸入文字

        Returns:
            包含分類結果和回應的字典
        """
        # ‹1› 分類意圖
        classification = self.classifier.invoke({"user_input": user_input})

        # ‹2› 路由到處理器
        handler_name = route_by_intent(classification)
        handler = HANDLERS.get(handler_name, HANDLERS["default_handler"])

        # ‹3› 生成回應
        response = handler.invoke({"user_input": user_input})

        return {
            "intent": classification.intent.value,
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
            "response": response
        }

    def stream_process(self, user_input: str):
        """串流處理使用者輸入"""
        # 先分類
        classification = self.classifier.invoke({"user_input": user_input})

        # 路由並串流回應
        handler_name = route_by_intent(classification)
        handler = HANDLERS.get(handler_name, HANDLERS["default_handler"])

        yield {
            "type": "classification",
            "intent": classification.intent.value,
            "confidence": classification.confidence
        }

        for chunk in handler.stream({"user_input": user_input}):
            yield {"type": "content", "content": chunk}
```

### 2.5.3 更新 CLI

```python
# techassist/cli_v2.py
from .core import TechAssistV2

def run_cli_v2():
    """執行 TechAssist v0.2 CLI"""
    print("=" * 60)
    print("🤖 TechAssist v0.2 - 智能意圖識別版")
    print("=" * 60)
    print("我現在能更好地理解你的問題了！")
    print("輸入 'quit' 離開。")
    print("-" * 60)

    assistant = TechAssistV2()

    while True:
        try:
            user_input = input("\n📝 你的問題：").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\n👋 感謝使用 TechAssist，再見！")
                break

            print("\n🔍 分析中...")

            # 串流處理
            first_chunk = True
            for item in assistant.stream_process(user_input):
                if item["type"] == "classification":
                    print(f"📊 意圖：{item['intent']} (信心：{item['confidence']:.0%})")
                    print("\n📖 回答：")
                elif item["type"] == "content":
                    print(item["content"], end="", flush=True)

            print("\n")

        except KeyboardInterrupt:
            print("\n\n👋 感謝使用 TechAssist，再見！")
            break
        except Exception as e:
            print(f"\n❌ 發生錯誤：{e}")
```

---

## 2.6 進階技巧：動態 Few-Shot

有時候，你需要根據輸入動態選擇相關的範例：

```python
from langchain_core.prompts import FewShotChatMessagePromptTemplate
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# ‹1› 定義範例池
examples = [
    {"input": "什麼是 REST API？", "output": "REST API 是..."},
    {"input": "Python 列表怎麼用？", "output": "Python 列表是..."},
    {"input": "Docker 是什麼？", "output": "Docker 是..."},
    {"input": "如何使用 Git？", "output": "Git 是版本控制工具..."},
    {"input": "什麼是微服務？", "output": "微服務是一種架構模式..."},
    # ... 更多範例
]

# ‹2› 建立語義相似度選擇器
example_selector = SemanticSimilarityExampleSelector.from_examples(
    examples,
    OpenAIEmbeddings(),
    FAISS,
    k=2  # 選擇最相似的 2 個範例
)

# ‹3› 建立動態 Few-Shot Prompt
example_prompt = ChatPromptTemplate.from_messages([
    ("human", "{input}"),
    ("ai", "{output}")
])

dynamic_few_shot = FewShotChatMessagePromptTemplate(
    example_selector=example_selector,
    example_prompt=example_prompt,
)

# ‹4› 使用
final_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是技術助理。請參考類似問題的回答風格。"),
    dynamic_few_shot,
    ("human", "{question}")
])

# 當問「Kubernetes 是什麼？」時，
# 會自動選擇「Docker 是什麼？」和「什麼是微服務？」作為範例
```

---

## 2.7 本章回顧

### 核心技巧

| 技巧 | 用途 | 何時使用 |
|------|------|----------|
| **Chain-of-Thought** | 提升推理能力 | 複雜邏輯、數學問題 |
| **Few-Shot Learning** | 指導輸出風格 | 特定格式、特定語氣 |
| **Pydantic 結構化輸出** | 確保格式一致 | 需要程式解析輸出時 |
| **with_structured_output** | 原生結構化輸出 | 模型支援時優先使用 |
| **動態 Few-Shot** | 上下文相關範例 | 範例池大、需要精準匹配 |

### 設計原則

1. **明確勝過隱晦**：在 Prompt 中明確說明期望
2. **結構化資料流**：使用 Pydantic 確保資料一致性
3. **失敗優雅處理**：使用 OutputFixingParser 處理解析錯誤

### TechAssist 里程碑

- ✅ v0.1：基於 Chain 的簡單問答
- ✅ v0.2：具備意圖分類與動態路由

---

## 2.8 下一章預告

TechAssist v0.2 能理解意圖，但它仍然只能「說」不能「做」。當使用者說「幫我查一下 Python 3.12 的新功能」，它只能根據訓練資料回答，無法存取最新資訊。

在下一章，我們將學習 **Tool Use——賦予 AI 手腳**：

- 理解 Function Calling 的原理
- 實作自定義工具（網頁搜尋、API 調用、文件讀取）
- 建立 TechAssist v0.3：能夠搜尋文件的智能助理

---

## 練習題

1. **基礎練習**：為意圖分類器新增一個 `feedback` 意圖，用於識別使用者的讚美或抱怨。

2. **進階練習**：實作一個 `CodeReviewResult` Pydantic 模型，包含以下欄位：
   - `issues`: 問題列表（包含行號、問題描述、嚴重程度）
   - `suggestions`: 改進建議
   - `overall_score`: 整體評分（1-10）

3. **挑戰練習**：實作動態 Few-Shot 選擇器，根據問題的技術領域（前端/後端/DevOps）選擇相關範例。

---

## 延伸閱讀

- [Pydantic 官方文件：Model Configuration](https://docs.pydantic.dev/latest/concepts/config/)
- [LangChain：Structured Output](https://python.langchain.com/docs/how_to/structured_output/)
- [Chain-of-Thought Prompting 論文](https://arxiv.org/abs/2201.11903)
