# Chapter 1: 啟程——從 Chain 到 LCEL

> 「最好的學習方式是建造。」——Seymour Papert

---

## 本章學習目標

完成本章後，你將能夠：

- 理解 LangChain 的核心抽象與設計哲學
- 掌握 PromptTemplate、LLM 與 OutputParser 三大基礎元件
- 使用 LCEL (LangChain Expression Language) 組合元件
- 完成 TechAssist v0.1：一個可運行的 CLI 智能助理原型

---

## 1.1 場景引入：TechAssist 的誕生

想像你是一家科技公司的技術負責人。每天，你的團隊面臨著同樣的挑戰：

- 新進工程師不斷詢問「這個 API 怎麼用？」
- 技術文件散落在 Confluence、GitHub Wiki、Notion 各處
- 資深工程師花費大量時間回答重複性問題

你決定打造一個內部智能助理——**TechAssist**。它需要：

1. 理解工程師的自然語言問題
2. 在技術文件中找到相關答案
3. 用清晰的方式回覆

這聽起來是個 LLM 的完美應用場景。但問題來了：**如何從一個簡單的 API 調用，演進成一個可維護、可擴展的系統？**

這就是本書要帶你走的旅程。讓我們從最基礎的構件開始。

---

## 1.2 為什麼需要 LangChain？

### 1.2.1 原生 API 的侷限

讓我們先看看直接使用 LLM API 的方式：

```python
# 直接調用 Anthropic API
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "什麼是 Python 的 GIL？"}
    ]
)
print(response.content[0].text)
```

這段程式碼能運作，但當系統變複雜時，你會遇到以下問題：

| 挑戰 | 說明 |
|------|------|
| **Prompt 管理** | 如何版本控制？如何動態插入變數？ |
| **輸出解析** | 如何確保 LLM 輸出符合預期格式？ |
| **模型切換** | 想從 Claude 換成 GPT-4o 需要改多少程式碼？ |
| **鏈式調用** | 如何將多個步驟組合成流程？ |
| **錯誤處理** | 如何優雅地處理 API 錯誤與重試？ |

LangChain 正是為了解決這些問題而生。

### 1.2.2 LangChain 的設計哲學

LangChain 的核心理念是**組合性 (Composability)**。它將 LLM 應用拆解成標準化的構件，讓你能夠：

```mermaid
graph LR
    A[PromptTemplate] --> B[LLM]
    B --> C[OutputParser]
    C --> D[下一個步驟]

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#e8f5e9
```

每個構件都有明確的職責：

- **PromptTemplate**：管理提示詞模板
- **LLM/ChatModel**：封裝模型調用
- **OutputParser**：解析與驗證輸出

這種設計讓你能夠像堆疊樂高一樣組合功能。

---

## 1.3 環境準備

在開始編寫程式碼之前，讓我們設置好開發環境。

### 1.3.1 建立專案目錄

```bash
mkdir techassist && cd techassist
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 1.3.2 安裝依賴

```bash
pip install langchain langchain-anthropic langchain-openai python-dotenv
```

### 1.3.3 設定 API Key

建立 `.env` 檔案：

```bash
# .env
ANTHROPIC_API_KEY=your-api-key-here
# OPENAI_API_KEY=your-openai-key  # 備用
```

### 1.3.4 驗證安裝

```python
# verify_setup.py
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
response = llm.invoke("說 'Hello, TechAssist!'")
print(response.content)
```

如果看到回應，恭喜你，環境已準備就緒！

---

## 1.4 核心構件一：PromptTemplate

### 1.4.1 為什麼需要模板？

硬編碼的 prompt 存在幾個問題：

```python
# ❌ 不好的做法：硬編碼
prompt = f"用戶問題：{user_question}\n請用繁體中文回答。"
```

- 難以複用
- 難以測試
- 難以版本控制

PromptTemplate 解決了這些問題：

```python
# ✅ 好的做法：使用模板
from langchain_core.prompts import PromptTemplate

template = PromptTemplate.from_template(
    """你是 TechAssist，一個專業的技術助理。

用戶問題：{question}

請用繁體中文、以清晰易懂的方式回答。"""
)

# 動態填充變數
formatted = template.format(question="什麼是 REST API？")
print(formatted)
```

### 1.4.2 ChatPromptTemplate：對話場景的模板

在對話應用中，我們需要區分不同角色的訊息：

```python
from langchain_core.prompts import ChatPromptTemplate

# ‹1› 定義多角色對話模板
chat_template = ChatPromptTemplate.from_messages([
    ("system", """你是 TechAssist，一個專業的技術助理。
你的特點：
- 回答準確、簡潔
- 使用繁體中文
- 適時提供程式碼範例"""),

    ("human", "{question}")  # ‹2› 使用者輸入的佔位符
])

# ‹3› 格式化為訊息列表
messages = chat_template.format_messages(question="解釋 Python 裝飾器")
for msg in messages:
    print(f"[{msg.type}] {msg.content[:50]}...")
```

**程式碼解析：**

- ‹1› `from_messages` 接受 (角色, 內容) 元組列表
- ‹2› 花括號 `{question}` 定義變數佔位符
- ‹3› `format_messages` 返回 `BaseMessage` 物件列表，可直接傳給 ChatModel

### 1.4.3 進階模板：Few-Shot 範例

有時候，給 LLM 看幾個範例比詳細描述更有效：

```python
from langchain_core.prompts import FewShotChatMessagePromptTemplate

# 定義範例
examples = [
    {"input": "什麼是變數？", "output": "變數是用來儲存資料的容器。在 Python 中：`x = 10`"},
    {"input": "for 迴圈怎麼用？", "output": "for 迴圈用於重複執行程式碼：`for i in range(5): print(i)`"},
]

# 範例模板
example_prompt = ChatPromptTemplate.from_messages([
    ("human", "{input}"),
    ("ai", "{output}"),
])

# Few-Shot 模板
few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=examples,
)

# 組合完整模板
final_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 TechAssist，請參考以下範例的回答風格："),
    few_shot_prompt,
    ("human", "{question}"),
])
```

---

## 1.5 核心構件二：LLM 與 ChatModel

### 1.5.1 LLM vs ChatModel

LangChain 區分兩種模型介面：

| 類型 | 輸入 | 輸出 | 適用場景 |
|------|------|------|----------|
| **LLM** | 字串 | 字串 | 文本補全 |
| **ChatModel** | 訊息列表 | 訊息 | 對話應用 |

現代應用幾乎都使用 ChatModel：

```python
from langchain_anthropic import ChatAnthropic

# ‹1› 初始化 ChatModel
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20241022",
    temperature=0.7,  # ‹2› 控制創意程度
    max_tokens=1024,
)

# ‹3› 直接調用
response = llm.invoke("什麼是 Docker？")
print(response.content)
```

**參數說明：**

- ‹1› `ChatAnthropic` 封裝了 Anthropic API
- ‹2› `temperature`：0 = 確定性輸出，1 = 更有創意
- ‹3› `invoke()` 是 LangChain 的標準調用方法

### 1.5.2 模型切換的優雅方式

LangChain 的抽象讓模型切換變得簡單：

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

def get_llm(provider: str = "anthropic"):
    """工廠函數：根據配置返回對應的 LLM"""
    if provider == "anthropic":
        return ChatAnthropic(model="claude-3-5-sonnet-20241022")
    elif provider == "openai":
        return ChatOpenAI(model="gpt-4o")
    else:
        raise ValueError(f"未支援的 provider: {provider}")

# 使用
llm = get_llm("anthropic")
response = llm.invoke("Hello!")
```

這種設計讓你能夠：

- 在不同環境使用不同模型（開發用便宜的，生產用強大的）
- 實現 Fallback 機制（主模型失敗時切換備用）
- A/B 測試不同模型的效果

---

## 1.6 核心構件三：OutputParser

### 1.6.1 為什麼需要解析輸出？

LLM 的輸出是自由文本，但我們的程式需要結構化資料：

```python
# LLM 回答："Python 是一種程式語言，由 Guido van Rossum 於 1991 年創建..."
# 我們需要：{"language": "Python", "creator": "Guido van Rossum", "year": 1991}
```

OutputParser 負責將自由文本轉換成程式可用的格式。

### 1.6.2 StrOutputParser：最簡單的解析器

```python
from langchain_core.output_parsers import StrOutputParser

parser = StrOutputParser()

# 從 AIMessage 提取純文字
from langchain_core.messages import AIMessage
message = AIMessage(content="這是回答內容")
result = parser.invoke(message)
print(result)  # "這是回答內容"
print(type(result))  # <class 'str'>
```

### 1.6.3 PydanticOutputParser：結構化輸出

當你需要結構化資料時，Pydantic 解析器是最佳選擇：

```python
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# ‹1› 定義輸出結構
class TechAnswer(BaseModel):
    summary: str = Field(description="簡短摘要，不超過 50 字")
    explanation: str = Field(description="詳細解釋")
    code_example: str | None = Field(description="程式碼範例（如適用）")
    difficulty: str = Field(description="難度：初級/中級/高級")

# ‹2› 建立解析器
parser = PydanticOutputParser(pydantic_object=TechAnswer)

# ‹3› 獲取格式說明（用於 prompt）
print(parser.get_format_instructions())
```

輸出的格式說明會指導 LLM 輸出正確的 JSON 格式。

### 1.6.4 整合解析器到 Prompt

```python
from langchain_core.prompts import ChatPromptTemplate

template = ChatPromptTemplate.from_messages([
    ("system", """你是 TechAssist 技術助理。
請按照以下格式回答：

{format_instructions}"""),
    ("human", "{question}")
])

# 將格式說明注入模板
prompt_with_parser = template.partial(
    format_instructions=parser.get_format_instructions()
)
```

---

## 1.7 LCEL：組合的藝術

### 1.7.1 什麼是 LCEL？

**LCEL (LangChain Expression Language)** 是 LangChain 的聲明式組合語法。它使用管道運算符 `|` 將元件串連：

```python
chain = prompt | llm | parser
```

這行程式碼表示：將 prompt 的輸出傳給 llm，再將 llm 的輸出傳給 parser。

### 1.7.2 LCEL 的優勢

| 特性 | 說明 |
|------|------|
| **可讀性** | 資料流清晰可見 |
| **標準介面** | 所有元件都支援 `invoke()`, `stream()`, `batch()` |
| **自動串流** | 支援逐 token 輸出 |
| **並行處理** | 可批次處理多個請求 |
| **追蹤整合** | 自動支援 LangSmith 追蹤 |

### 1.7.3 第一個 LCEL Chain

讓我們將前面學到的元件組合起來：

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ‹1› 定義元件
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 TechAssist，專業的技術助理。用繁體中文回答。"),
    ("human", "{question}")
])

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

parser = StrOutputParser()

# ‹2› 使用 LCEL 組合
chain = prompt | llm | parser

# ‹3› 調用 Chain
answer = chain.invoke({"question": "什麼是 API？"})
print(answer)
```

**執行流程：**

1. `prompt` 接收 `{"question": "什麼是 API？"}`，輸出格式化的訊息列表
2. `llm` 接收訊息列表，輸出 `AIMessage`
3. `parser` 接收 `AIMessage`，輸出純文字字串

### 1.7.4 串流輸出

LCEL 內建串流支援，讓使用者體驗更好：

```python
# 串流輸出（逐 token）
for chunk in chain.stream({"question": "解釋物件導向程式設計"}):
    print(chunk, end="", flush=True)
```

### 1.7.5 批次處理

當你有多個問題需要處理：

```python
questions = [
    {"question": "什麼是 REST API？"},
    {"question": "什麼是 GraphQL？"},
    {"question": "REST 和 GraphQL 的差異？"},
]

# 批次調用（自動並行）
answers = chain.batch(questions)
for q, a in zip(questions, answers):
    print(f"Q: {q['question']}\nA: {a[:100]}...\n")
```

---

## 1.8 實作：TechAssist v0.1

現在，讓我們把所有學到的知識整合，打造 TechAssist 的第一個版本。

### 1.8.1 專案結構

```
techassist/
├── .env                    # API Keys
├── requirements.txt        # 依賴
├── techassist/
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   ├── prompts.py         # Prompt 模板
│   ├── chains.py          # Chain 定義
│   └── cli.py             # CLI 介面
└── main.py                # 入口
```

### 1.8.2 配置管理

```python
# techassist/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """應用配置"""
    anthropic_api_key: str
    model_name: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 1024

    class Config:
        env_file = ".env"

settings = Settings()
```

### 1.8.3 Prompt 模板

```python
# techassist/prompts.py
from langchain_core.prompts import ChatPromptTemplate

# TechAssist 系統 Prompt
SYSTEM_PROMPT = """你是 TechAssist，一個專業的技術助理。

## 你的特點
- 精通各種程式語言和技術概念
- 回答準確、簡潔、實用
- 使用繁體中文
- 適時提供程式碼範例

## 回答原則
1. 先給出簡短的直接回答
2. 再提供必要的詳細解釋
3. 如有程式碼範例，確保可直接運行
4. 如果不確定，誠實說明

## 格式要求
- 使用 Markdown 格式
- 程式碼使用語法高亮標記"""

def get_qa_prompt() -> ChatPromptTemplate:
    """取得問答 Prompt 模板"""
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}")
    ])
```

### 1.8.4 Chain 定義

```python
# techassist/chains.py
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from .config import settings
from .prompts import get_qa_prompt

def create_qa_chain():
    """建立問答 Chain

    Returns:
        一個接受 question 並返回回答的 Chain
    """
    # ‹1› 初始化 LLM
    llm = ChatAnthropic(
        model=settings.model_name,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )

    # ‹2› 組合 Chain
    chain = (
        get_qa_prompt()  # Prompt 模板
        | llm            # LLM 調用
        | StrOutputParser()  # 輸出解析
    )

    return chain
```

### 1.8.5 CLI 介面

```python
# techassist/cli.py
import sys
from .chains import create_qa_chain

def run_cli():
    """執行 CLI 互動介面"""
    print("=" * 50)
    print("🤖 TechAssist v0.1 - 技術助理")
    print("=" * 50)
    print("輸入技術問題，我會為你解答。")
    print("輸入 'quit' 或 'exit' 離開。")
    print("-" * 50)

    chain = create_qa_chain()

    while True:
        try:
            question = input("\n📝 你的問題：").strip()

            if not question:
                continue

            if question.lower() in ('quit', 'exit', 'q'):
                print("\n👋 感謝使用 TechAssist，再見！")
                break

            print("\n💭 思考中...\n")

            # 串流輸出
            print("📖 回答：")
            for chunk in chain.stream({"question": question}):
                print(chunk, end="", flush=True)
            print("\n")

        except KeyboardInterrupt:
            print("\n\n👋 感謝使用 TechAssist，再見！")
            break
        except Exception as e:
            print(f"\n❌ 發生錯誤：{e}")

if __name__ == "__main__":
    run_cli()
```

### 1.8.6 主程式入口

```python
# main.py
from dotenv import load_dotenv

def main():
    # 載入環境變數
    load_dotenv()

    # 啟動 CLI
    from techassist.cli import run_cli
    run_cli()

if __name__ == "__main__":
    main()
```

### 1.8.7 執行測試

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行
python main.py
```

測試對話範例：

```
📝 你的問題：什麼是 Python 的列表推導式？

💭 思考中...

📖 回答：
列表推導式（List Comprehension）是 Python 中一種簡潔優雅的語法，
用於快速建立列表。

## 基本語法
```python
[expression for item in iterable if condition]
```

## 範例
```python
# 建立 1-10 的平方數列表
squares = [x**2 for x in range(1, 11)]
# 結果：[1, 4, 9, 16, 25, 36, 49, 64, 81, 100]

# 篩選偶數
evens = [x for x in range(10) if x % 2 == 0]
# 結果：[0, 2, 4, 6, 8]
```

相比傳統 for 迴圈，列表推導式更簡潔，通常也更快。
```

---

## 1.9 本章回顧

在本章中，我們學習了：

### 核心概念

| 元件 | 職責 | 關鍵方法 |
|------|------|----------|
| **PromptTemplate** | 管理提示詞模板 | `format()`, `format_messages()` |
| **ChatModel** | 封裝 LLM 調用 | `invoke()`, `stream()`, `batch()` |
| **OutputParser** | 解析輸出格式 | `invoke()`, `get_format_instructions()` |
| **LCEL** | 組合元件 | `\|` (管道運算符) |

### 設計原則

1. **組合優於繼承**：使用 LCEL 將小元件組合成大功能
2. **關注點分離**：每個元件只做一件事
3. **可測試性**：每個元件可以獨立測試

### TechAssist 里程碑

- ✅ v0.1：基於 Chain 的簡單問答機器人

---

## 1.10 下一章預告

TechAssist v0.1 能回答問題，但它有明顯的不足：

- 無法控制輸出格式（有時太長，有時太短）
- 無法分類使用者意圖（是技術問題？還是閒聊？）
- 輸出結構化程度不夠（難以被其他系統消費）

在下一章，我們將深入 **Prompt 工程與結構化輸出**，學習如何：

- 使用進階 Prompt 技巧（Chain-of-Thought, Few-Shot）
- 用 Pydantic 強制 LLM 輸出結構化資料
- 建立意圖分類器，讓 TechAssist 更聰明

---

## 練習題

1. **基礎練習**：修改 TechAssist 的系統 Prompt，讓它專注於 Python 領域的問題。

2. **進階練習**：新增一個 `/help` 指令，當使用者輸入時，顯示可用指令列表。

3. **挑戰練習**：實作對話歷史功能，讓 TechAssist 能記住之前的對話（提示：修改 Prompt 模板，加入 `MessagesPlaceholder`）。

---

## 延伸閱讀

- [LangChain 官方文件：LCEL](https://python.langchain.com/docs/expression_language/)
- [Anthropic Claude API 文件](https://docs.anthropic.com/)
- [Pydantic 官方文件](https://docs.pydantic.dev/)
