"""
chapter-03/prompt_templates.py

RAG Prompt 範本庫

本模組提供多種 RAG 場景的 Prompt 範本，
展示如何設計有效的 Prompt 來提升答案品質。

使用方式：
    from prompt_templates import RAGPromptTemplate, PromptType
    template = RAGPromptTemplate(PromptType.CUSTOMER_SUPPORT)
    prompt = template.format(query="...", context="...")
"""

from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass


class PromptType(Enum):
    """Prompt 類型"""
    CUSTOMER_SUPPORT = "customer_support"      # 客服問答
    TECHNICAL_DOC = "technical_doc"            # 技術文件
    FACTUAL_QA = "factual_qa"                  # 事實問答
    CONVERSATIONAL = "conversational"          # 對話式


@dataclass
class PromptTemplate:
    """Prompt 範本"""
    system_prompt: str
    user_prompt_template: str
    name: str
    description: str


# 預定義的 Prompt 範本
PROMPT_TEMPLATES: Dict[PromptType, PromptTemplate] = {

    PromptType.CUSTOMER_SUPPORT: PromptTemplate(
        name="客服支援",
        description="適用於客服問答場景，強調友善和準確",
        system_prompt="""你是一個專業且友善的客服助理。你的任務是根據提供的參考文件，幫助使用者解決問題。

回答原則：
1. 使用親切、專業的語氣
2. 只根據參考文件中的資訊回答，不要編造
3. 如果文件中沒有相關資訊，誠實告知並建議其他求助方式
4. 回答要清晰、有條理，必要時使用列表
5. 如果問題涉及敏感操作（如刪除帳戶），提醒使用者注意事項""",

        user_prompt_template="""以下是相關的參考文件：

{context}

---

使用者的問題：{query}

請根據參考文件回答使用者的問題。如果文件中沒有足夠的資訊，請告知使用者。"""
    ),

    PromptType.TECHNICAL_DOC: PromptTemplate(
        name="技術文件",
        description="適用於技術文件查詢，強調準確性和完整性",
        system_prompt="""你是一個技術文件助理。你的任務是根據提供的技術文件，回答開發者的技術問題。

回答原則：
1. 使用精確的技術術語
2. 提供具體的程式碼範例（如果文件中有）
3. 說明相關的注意事項和限制
4. 如果涉及多個步驟，使用編號列表
5. 標註參考文件的來源""",

        user_prompt_template="""技術文件內容：

{context}

---

開發者問題：{query}

請根據技術文件提供詳細的回答。如果需要，請提供程式碼範例。"""
    ),

    PromptType.FACTUAL_QA: PromptTemplate(
        name="事實問答",
        description="適用於需要精確事實的問答，強調準確性",
        system_prompt="""你是一個事實查核助理。你的任務是根據提供的資料，回答事實性問題。

回答原則：
1. 只陳述資料中明確提到的事實
2. 不要做任何推測或延伸
3. 如果資料中沒有明確答案，直接說明「根據提供的資料無法確定」
4. 如果多份資料有衝突，指出這一點
5. 回答要簡潔、直接""",

        user_prompt_template="""參考資料：

{context}

---

問題：{query}

請根據上述資料提供準確的回答。如果資料中沒有相關資訊，請明確說明。"""
    ),

    PromptType.CONVERSATIONAL: PromptTemplate(
        name="對話式",
        description="適用於多輪對話，保持上下文連貫性",
        system_prompt="""你是一個友善的對話助理。你的任務是自然地與使用者對話，同時根據參考資料提供有幫助的資訊。

回答原則：
1. 保持對話的自然流暢
2. 適當使用口語化表達
3. 在回答中融入參考資料的內容，但不要生硬引用
4. 可以主動詢問以釐清需求
5. 如果不確定，用友善的方式表達""",

        user_prompt_template="""參考資料：
{context}

---

使用者說：{query}

請以自然的對話方式回應，同時融入參考資料中的相關資訊。"""
    ),
}


class RAGPromptTemplate:
    """
    RAG Prompt 範本管理器

    Example:
        >>> template = RAGPromptTemplate(PromptType.CUSTOMER_SUPPORT)
        >>> system, user = template.format(
        ...     query="密碼忘記了怎麼辦",
        ...     context="重設密碼請點擊忘記密碼連結..."
        ... )
    """

    def __init__(self, prompt_type: PromptType = PromptType.CUSTOMER_SUPPORT):
        """
        初始化 Prompt 範本

        Args:
            prompt_type: Prompt 類型
        """
        self.template = PROMPT_TEMPLATES[prompt_type]
        self.prompt_type = prompt_type

    def format(
        self,
        query: str,
        context: str,
        **kwargs
    ) -> tuple[str, str]:
        """
        格式化 Prompt

        Args:
            query: 使用者查詢
            context: 檢索到的上下文（已格式化的文件內容）
            **kwargs: 額外的模板參數

        Returns:
            (system_prompt, user_prompt) 元組
        """
        user_prompt = self.template.user_prompt_template.format(
            query=query,
            context=context,
            **kwargs
        )
        return self.template.system_prompt, user_prompt

    @staticmethod
    def format_context(
        documents: List[Dict],
        include_score: bool = True,
        max_length: int = 500
    ) -> str:
        """
        將檢索到的文件格式化為上下文字串

        Args:
            documents: 文件列表，每個文件包含 content 和可選的 score
            include_score: 是否包含相關性分數
            max_length: 每份文件的最大長度

        Returns:
            格式化的上下文字串
        """
        formatted_parts = []

        for i, doc in enumerate(documents, 1):
            content = doc.get("content", "")
            if len(content) > max_length:
                content = content[:max_length] + "..."

            if include_score and "score" in doc:
                header = f"[文件 {i}]（相關度：{doc['score']:.2f}）"
            else:
                header = f"[文件 {i}]"

            formatted_parts.append(f"{header}\n{content}")

        return "\n\n".join(formatted_parts)

    @classmethod
    def list_templates(cls) -> List[Dict]:
        """列出所有可用的 Prompt 範本"""
        return [
            {
                "type": pt.value,
                "name": PROMPT_TEMPLATES[pt].name,
                "description": PROMPT_TEMPLATES[pt].description
            }
            for pt in PromptType
        ]


def main():
    """演示 Prompt 範本用法"""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # 列出所有範本
    console.print("\n[bold]可用的 Prompt 範本：[/bold]\n")

    table = Table(title="RAG Prompt 範本")
    table.add_column("類型", style="cyan")
    table.add_column("名稱", style="green")
    table.add_column("說明", style="white")

    for template_info in RAGPromptTemplate.list_templates():
        table.add_row(
            template_info["type"],
            template_info["name"],
            template_info["description"]
        )

    console.print(table)

    # 演示格式化
    console.print("\n[bold]範例：客服支援 Prompt[/bold]\n")

    template = RAGPromptTemplate(PromptType.CUSTOMER_SUPPORT)

    # 模擬檢索結果
    mock_docs = [
        {"content": "如何重設密碼？請點擊登入頁面的「忘記密碼」連結。", "score": 0.85},
        {"content": "重設密碼連結有效期為 24 小時。", "score": 0.72},
    ]

    context = RAGPromptTemplate.format_context(mock_docs)
    system_prompt, user_prompt = template.format(
        query="密碼忘記了怎麼辦",
        context=context
    )

    console.print("[cyan]System Prompt:[/cyan]")
    console.print(system_prompt)
    console.print("\n[cyan]User Prompt:[/cyan]")
    console.print(user_prompt)


if __name__ == "__main__":
    main()
