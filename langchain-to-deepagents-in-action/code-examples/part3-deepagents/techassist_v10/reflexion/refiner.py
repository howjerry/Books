"""
TechAssist v1.0 - Refiner 組件

反思問題並生成改進策略
"""

from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from ..config import config
from ..state import TechAssistState


class Reflection(BaseModel):
    """反思結果"""
    what_went_wrong: str = Field(description="問題分析")
    root_cause: str = Field(description="根本原因")
    improvement_strategy: str = Field(description="改進策略")


def refine_output(state: TechAssistState) -> dict:
    """Refiner 節點：反思並生成改進策略"""
    evaluation = state["evaluation"]
    current_output = state["current_output"]
    task = state["task"]
    iteration = state["iteration"]

    # 檢查是否達到最大迭代次數
    if iteration >= config.max_iterations:
        return {
            "phase": "respond"
        }

    llm = ChatAnthropic(
        model=config.primary_model,
        temperature=0
    )
    structured_llm = llm.with_structured_output(Reflection)

    reflection_prompt = f"""作為品質審查專家，請反思以下輸出的問題並提出改進策略。

任務：{task}

當前輸出：
{current_output[:2000]}

評估結果：
- 綜合評分：{evaluation.overall_score:.2f}
- 問題：{', '.join(evaluation.issues) if evaluation.issues else '無'}
- 建議：{', '.join(evaluation.suggestions) if evaluation.suggestions else '無'}

各維度評分：
{chr(10).join(f"- {d.name}: {d.score:.2f} - {d.feedback}" for d in evaluation.dimensions)}

請進行深度反思，分析問題原因並提出具體改進策略。"""

    reflection = structured_llm.invoke([HumanMessage(content=reflection_prompt)])

    reflection_text = f"""
問題：{reflection.what_went_wrong}
原因：{reflection.root_cause}
策略：{reflection.improvement_strategy}
""".strip()

    # 獲取現有反思列表並添加新反思
    existing_reflections = list(state.get("reflections", []))
    existing_reflections.append(reflection_text)

    return {
        "reflections": existing_reflections,
        "iteration": iteration + 1,
        "phase": "execute"  # 回到生成階段重新生成
    }
