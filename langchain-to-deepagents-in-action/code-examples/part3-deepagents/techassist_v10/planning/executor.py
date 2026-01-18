"""
TechAssist v1.0 - Executor 組件
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import config
from ..state import StepResult, TechAssistState


def execute_step(state: TechAssistState) -> dict:
    """執行當前計劃步驟"""
    plan = state["plan"]
    current_index = state["current_step_index"]
    step_results = list(state["step_results"])

    if current_index >= len(plan.steps):
        return {"phase": "evaluate"}

    current_step = plan.steps[current_index]

    # 檢查依賴
    for dep_id in current_step.dependencies:
        dep_result = next(
            (r for r in step_results if r.step_id == dep_id),
            None
        )
        if not dep_result or not dep_result.success:
            result = StepResult(
                step_id=current_step.id,
                success=False,
                output="",
                error=f"依賴步驟 {dep_id} 未完成"
            )
            return {
                "step_results": step_results + [result],
                "current_step_index": current_index + 1
            }

    # 執行步驟
    try:
        output = _execute_tool(current_step.tool, current_step.action, state)
        result = StepResult(
            step_id=current_step.id,
            success=True,
            output=output[:1000]
        )
    except Exception as e:
        result = StepResult(
            step_id=current_step.id,
            success=False,
            output="",
            error=str(e)
        )

    return {
        "step_results": step_results + [result],
        "current_step_index": current_index + 1
    }


def _execute_tool(tool: str | None, action: str, state: TechAssistState) -> str:
    """執行工具調用"""
    llm = ChatAnthropic(model=config.primary_model, temperature=0)

    if tool == "calculate":
        return "計算結果：已完成數學運算"
    elif tool == "search":
        return "搜尋結果：找到相關文檔"
    elif tool == "code_execute":
        return "程式碼執行成功"
    elif tool == "api_call":
        return "API 調用成功，返回數據"
    elif tool == "database_query":
        return "資料庫查詢完成，返回結果"
    else:
        # 使用 LLM 處理一般步驟
        response = llm.invoke([
            SystemMessage(content="你是一個任務執行助手。請執行以下步驟。"),
            HumanMessage(content=f"執行：{action}")
        ])
        return response.content
