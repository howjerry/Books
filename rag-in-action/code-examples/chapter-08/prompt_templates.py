"""
chapter-08/prompt_templates.py

RAG Prompt 範本集合

本模組實作 5 種經過驗證的 RAG Prompt 策略，
從基礎範本到進階的強制引用和結構化輸出。

使用方式：
    from prompt_templates import PromptStrategy, create_prompt
    prompt = create_prompt(PromptStrategy.CHAIN_OF_THOUGHT, query, contexts)

依賴安裝：
    pip install jinja2 pydantic
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from jinja2 import Template
from pydantic import BaseModel


class PromptStrategy(Enum):
    """Prompt 策略類型"""
    BASIC = "basic"                         # 基礎範本
    CHAIN_OF_THOUGHT = "chain_of_thought"   # 思維鏈範本
    FORCED_CITATION = "forced_citation"     # 強制引用範本
    SELF_REFLECTION = "self_reflection"     # 自我反思範本
    STRUCTURED_OUTPUT = "structured_output" # 結構化輸出範本


@dataclass
class Context:
    """檢索到的上下文"""
    content: str
    source: str = ""
    score: float = 0.0
    doc_id: str = ""


# ═══════════════════════════════════════════════════════════════
# 策略一：基礎範本
# ═══════════════════════════════════════════════════════════════

BASIC_TEMPLATE = """你是一個專業的客服助理。請根據以下知識庫內容回答使用者的問題。

## 知識庫內容

{% for ctx in contexts %}
{{ ctx.content }}

---
{% endfor %}

## 使用者問題

{{ query }}

## 回答要求

1. 只根據知識庫內容回答，不要編造資訊
2. 如果知識庫沒有相關資訊，請誠實說「我在知識庫中找不到相關資訊」
3. 回答要簡潔明瞭，使用繁體中文

## 你的回答"""                                                          # ‹1›


# ═══════════════════════════════════════════════════════════════
# 策略二：思維鏈範本（Chain of Thought）
# ═══════════════════════════════════════════════════════════════

CHAIN_OF_THOUGHT_TEMPLATE = """你是一個專業的客服助理。請根據知識庫內容，一步步分析並回答使用者問題。

## 知識庫內容

{% for ctx in contexts %}
[文件 {{ loop.index }}]
{{ ctx.content }}

{% endfor %}

## 使用者問題

{{ query }}

## 請按照以下步驟回答

### 步驟 1：理解問題
首先，分析使用者真正想知道什麼。

### 步驟 2：檢索相關資訊
從知識庫中找出與問題相關的關鍵資訊。

### 步驟 3：整合答案
根據找到的資訊，組織一個完整的答案。

### 步驟 4：最終回答
提供簡潔明瞭的最終答案。

## 開始分析"""                                                          # ‹2›


# ═══════════════════════════════════════════════════════════════
# 策略三：強制引用範本（Forced Citation）
# ═══════════════════════════════════════════════════════════════

FORCED_CITATION_TEMPLATE = """你是一個專業的客服助理。回答問題時，你必須引用知識庫中的具體來源。

## 知識庫內容

{% for ctx in contexts %}
[來源 {{ loop.index }}] {{ ctx.source if ctx.source else "文件 " ~ loop.index }}
{{ ctx.content }}

{% endfor %}

## 使用者問題

{{ query }}

## 回答規則

1. 每個陳述都必須標注來源，格式：「...內容... [來源 X]」
2. 如果多個來源支持同一陳述，標注所有相關來源
3. 如果知識庫沒有相關資訊，明確說明「知識庫中沒有這方面的資訊」
4. 不要編造任何不在知識庫中的資訊

## 範例格式

使用者問題：如何重設密碼？
回答：您可以點擊登入頁面的「忘記密碼」連結來重設密碼 [來源 1]。系統會發送重設連結到您的電子郵件 [來源 1]。請注意，重設連結的有效期為 24 小時 [來源 2]。

## 你的回答（請務必標注來源）"""                                         # ‹3›


# ═══════════════════════════════════════════════════════════════
# 策略四：自我反思範本（Self Reflection）
# ═══════════════════════════════════════════════════════════════

SELF_REFLECTION_TEMPLATE = """你是一個專業的客服助理。在回答問題後，你需要自我檢查答案的品質。

## 知識庫內容

{% for ctx in contexts %}
[文件 {{ loop.index }}]
{{ ctx.content }}

{% endfor %}

## 使用者問題

{{ query }}

## 回答流程

### 第一步：初步回答
根據知識庫內容，提供你的答案。

### 第二步：自我檢查
檢查你的答案：
- [ ] 答案是否完全基於知識庫內容？
- [ ] 是否有遺漏的重要資訊？
- [ ] 是否有編造或假設的內容？
- [ ] 答案是否直接回答了使用者的問題？

### 第三步：修正與最終答案
根據檢查結果，提供修正後的最終答案。

## 開始回答"""                                                          # ‹4›


# ═══════════════════════════════════════════════════════════════
# 策略五：結構化輸出範本（Structured Output）
# ═══════════════════════════════════════════════════════════════

STRUCTURED_OUTPUT_TEMPLATE = """你是一個專業的客服助理。請以結構化 JSON 格式回答問題。

## 知識庫內容

{% for ctx in contexts %}
[來源 {{ loop.index }}]
{{ ctx.content }}

{% endfor %}

## 使用者問題

{{ query }}

## 輸出格式

請以下列 JSON 格式回答：

```json
{
    "answer": "你的回答內容",
    "confidence": "high/medium/low",
    "sources_used": [1, 2],
    "key_points": [
        "要點 1",
        "要點 2"
    ],
    "follow_up_suggestions": [
        "可能的後續問題 1"
    ],
    "unable_to_answer": false,
    "reason_if_unable": ""
}
```

## 欄位說明

- answer: 完整的回答內容
- confidence: 根據知識庫覆蓋程度評估信心度
- sources_used: 使用了哪些來源（來源編號列表）
- key_points: 回答中的關鍵要點
- follow_up_suggestions: 使用者可能想進一步了解的問題
- unable_to_answer: 如果無法回答，設為 true
- reason_if_unable: 無法回答的原因

## 你的 JSON 回答"""                                                     # ‹5›


# ═══════════════════════════════════════════════════════════════
# Prompt 工廠
# ═══════════════════════════════════════════════════════════════

TEMPLATES = {
    PromptStrategy.BASIC: BASIC_TEMPLATE,
    PromptStrategy.CHAIN_OF_THOUGHT: CHAIN_OF_THOUGHT_TEMPLATE,
    PromptStrategy.FORCED_CITATION: FORCED_CITATION_TEMPLATE,
    PromptStrategy.SELF_REFLECTION: SELF_REFLECTION_TEMPLATE,
    PromptStrategy.STRUCTURED_OUTPUT: STRUCTURED_OUTPUT_TEMPLATE,
}


def create_prompt(
    strategy: PromptStrategy,
    query: str,
    contexts: List[Context],
    **kwargs
) -> str:
    """
    建立 Prompt

    Args:
        strategy: Prompt 策略
        query: 使用者查詢
        contexts: 檢索到的上下文列表
        **kwargs: 額外參數

    Returns:
        完整的 Prompt 字串
    """
    template_str = TEMPLATES[strategy]
    template = Template(template_str)

    return template.render(
        query=query,
        contexts=contexts,
        **kwargs
    )


class PromptBuilder:
    """
    Prompt 建構器

    提供更靈活的 Prompt 客製化能力。
    """

    def __init__(self, base_strategy: PromptStrategy = PromptStrategy.BASIC):
        self.base_strategy = base_strategy
        self.system_prompt = ""
        self.additional_rules = []
        self.examples = []

    def set_system_prompt(self, prompt: str) -> "PromptBuilder":
        """設定系統提示"""
        self.system_prompt = prompt
        return self

    def add_rule(self, rule: str) -> "PromptBuilder":
        """新增規則"""
        self.additional_rules.append(rule)
        return self

    def add_example(self, query: str, answer: str) -> "PromptBuilder":
        """新增範例"""
        self.examples.append({"query": query, "answer": answer})
        return self

    def build(self, query: str, contexts: List[Context]) -> str:
        """建構最終 Prompt"""
        base_prompt = create_prompt(self.base_strategy, query, contexts)

        # 加入額外規則
        if self.additional_rules:
            rules_text = "\n".join(f"- {r}" for r in self.additional_rules)
            base_prompt = base_prompt.replace(
                "## 你的回答",
                f"## 額外規則\n\n{rules_text}\n\n## 你的回答"
            )

        # 加入範例
        if self.examples:
            examples_text = "\n\n".join(
                f"問：{e['query']}\n答：{e['answer']}"
                for e in self.examples
            )
            base_prompt = base_prompt.replace(
                "## 你的回答",
                f"## 參考範例\n\n{examples_text}\n\n## 你的回答"
            )

        return base_prompt


def demo_all_strategies():
    """演示所有 Prompt 策略"""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    # 模擬上下文
    contexts = [
        Context(
            content="如何重設密碼？請點擊登入頁面的「忘記密碼」連結，輸入您的電子郵件地址。",
            source="FAQ-001",
            score=0.92
        ),
        Context(
            content="密碼重設連結有效期為 24 小時。如果連結過期，請重新申請。",
            source="FAQ-002",
            score=0.85
        ),
    ]

    query = "我忘記密碼了，該怎麼辦？"

    console.print("\n[bold]═══ RAG Prompt 策略演示 ═══[/bold]\n")

    for strategy in PromptStrategy:
        prompt = create_prompt(strategy, query, contexts)

        console.print(Panel(
            prompt[:500] + "..." if len(prompt) > 500 else prompt,
            title=f"策略：{strategy.value}",
            border_style="blue"
        ))
        console.print()


if __name__ == "__main__":
    demo_all_strategies()
