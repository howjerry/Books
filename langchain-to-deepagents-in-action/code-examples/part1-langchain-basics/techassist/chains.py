"""Chain 定義模組"""

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from .config import settings
from .prompts import (
    get_qa_prompt,
    get_classifier_prompt,
    get_greeting_prompt,
    get_tech_qa_prompt,
    get_comparison_prompt,
    get_troubleshoot_prompt,
    get_off_topic_prompt,
)
from .intents import IntentClassification


def get_llm() -> ChatAnthropic:
    """取得 LLM 實例"""
    return ChatAnthropic(
        model=settings.model_name,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )


# ============================================================
# v0.1 Chains
# ============================================================

def create_qa_chain():
    """建立基礎問答 Chain

    Returns:
        一個接受 question 並返回回答的 Chain
    """
    chain = (
        get_qa_prompt()
        | get_llm()
        | StrOutputParser()
    )
    return chain


# ============================================================
# v0.2 Chains
# ============================================================

def create_intent_classifier():
    """建立意圖分類器

    Returns:
        一個接受 user_input 並返回 IntentClassification 的 Chain
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(IntentClassification)

    chain = get_classifier_prompt() | structured_llm
    return chain


def create_handlers() -> dict:
    """建立所有處理器

    Returns:
        處理器名稱到 Chain 的映射字典
    """
    llm = get_llm()
    parser = StrOutputParser()

    handlers = {
        "greeting_handler": get_greeting_prompt() | llm | parser,
        "farewell_handler": get_greeting_prompt() | llm | parser,
        "tech_qa_handler": get_tech_qa_prompt() | llm | parser,
        "code_review_handler": get_tech_qa_prompt() | llm | parser,
        "code_gen_handler": get_tech_qa_prompt() | llm | parser,
        "comparison_handler": get_comparison_prompt() | llm | parser,
        "troubleshoot_handler": get_troubleshoot_prompt() | llm | parser,
        "off_topic_handler": get_off_topic_prompt() | llm | parser,
        "clarification_handler": get_off_topic_prompt() | llm | parser,
        "default_handler": get_tech_qa_prompt() | llm | parser,
    }

    return handlers
