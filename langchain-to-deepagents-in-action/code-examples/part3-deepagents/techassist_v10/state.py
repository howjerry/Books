"""
TechAssist v1.0 統一狀態定義
"""

from typing import TypedDict, Annotated, Literal
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


# ============================================================
# 規劃相關結構
# ============================================================

class Step(BaseModel):
    """計劃步驟"""
    id: int
    action: str
    tool: str | None = None
    expected_output: str
    dependencies: list[int] = Field(default_factory=list)


class Plan(BaseModel):
    """執行計劃"""
    goal: str
    steps: list[Step]
    reasoning: str


class StepResult(BaseModel):
    """步驟結果"""
    step_id: int
    success: bool
    output: str
    error: str | None = None


# ============================================================
# 記憶相關結構
# ============================================================

@dataclass
class SessionMemory:
    """會話記憶"""
    session_id: str
    user_id: str
    topic: str = ""
    summary: str = ""
    key_decisions: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class RetrievedMemory(BaseModel):
    """檢索到的記憶"""
    content: str
    relevance_score: float
    source: Literal["short_term", "session", "long_term"]


# ============================================================
# 評估相關結構
# ============================================================

class QualityDimension(BaseModel):
    """品質維度"""
    name: str
    score: float = Field(ge=0, le=1)
    feedback: str


class EvaluationResult(BaseModel):
    """評估結果"""
    overall_score: float = Field(ge=0, le=1)
    dimensions: list[QualityDimension]
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    passed: bool


# ============================================================
# 統一狀態
# ============================================================

class TechAssistState(TypedDict):
    """TechAssist v1.0 統一狀態"""

    # 基礎狀態
    messages: Annotated[list, add_messages]
    user_id: str
    session_id: str

    # 任務狀態
    task: str
    task_type: Literal["simple", "complex", "code"]
    phase: Literal["analyze", "plan", "execute", "evaluate", "refine", "respond"]

    # 規劃狀態
    plan: Plan | None
    current_step_index: int
    step_results: list[StepResult]

    # 記憶狀態
    injected_context: str | None
    should_memorize: bool

    # 自我修正狀態
    current_output: str | None
    evaluation: EvaluationResult | None
    reflections: list[str]
    iteration: int

    # 最終輸出
    final_response: str | None
