"""意圖定義模組"""

from enum import Enum
from pydantic import BaseModel, Field


class Intent(str, Enum):
    """使用者意圖類型"""
    GREETING = "greeting"
    FAREWELL = "farewell"
    TECH_QUESTION = "tech_question"
    CODE_REVIEW = "code_review"
    CODE_GENERATION = "code_generation"
    COMPARISON = "comparison"
    TROUBLESHOOTING = "troubleshooting"
    OFF_TOPIC = "off_topic"
    UNCLEAR = "unclear"


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


# 意圖到處理器的映射
INTENT_HANDLER_MAP = {
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
