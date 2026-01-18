"""
TechAssist v1.0 - Replanner 組件
"""

from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import config
from ..state import Step, Plan, TechAssistState


class ReplanDecision(BaseModel):
    """重規劃決策"""
    should_replan: bool
    reason: str
    new_steps: list[Step] | None = None


def evaluate_and_replan(state: TechAssistState) -> dict:
    """評估執行進度並決定是否重規劃"""
    plan = state["plan"]
    step_results = state["step_results"]
    current_index = state["current_step_index"]

    # 計算失敗率
    failed_count = sum(1 for r in step_results if not r.success)
    total_count = len(step_results)

    if total_count == 0 or failed_count / total_count < config.replan_threshold:
        return {}  # 無需重規劃

    llm = ChatAnthropic(model=config.primary_model, temperature=0)
    structured_llm = llm.with_structured_output(ReplanDecision)

    context = f"""
原始目標：{plan.goal}

已執行步驟：
{chr(10).join(f"- 步驟 {r.step_id}: {'成功' if r.success else '失敗 - ' + (r.error or '')}" for r in step_results)}

剩餘步驟：
{chr(10).join(f"- 步驟 {s.id}: {s.action}" for s in plan.steps[current_index:])}
"""

    decision = structured_llm.invoke([
        SystemMessage(content="你是任務重規劃專家。分析執行情況並決定是否需要調整計劃。"),
        HumanMessage(content=context)
    ])

    if decision.should_replan and decision.new_steps:
        completed_steps = plan.steps[:current_index]
        new_plan = Plan(
            goal=plan.goal,
            steps=completed_steps + decision.new_steps,
            reasoning=f"重規劃：{decision.reason}"
        )
        return {"plan": new_plan}

    return {}
