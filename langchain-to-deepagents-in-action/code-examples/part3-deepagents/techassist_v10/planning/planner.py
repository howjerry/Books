"""
TechAssist v1.0 - Planner 組件
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import config
from ..state import Plan, TechAssistState


PLANNER_SYSTEM_PROMPT = """你是 TechAssist 的任務規劃專家。

根據用戶任務和上下文，制定詳細的執行計劃。每個步驟應該：
1. 具體且可執行
2. 有明確的預期輸出
3. 標註依賴關係

可用工具：
- search: 搜尋文檔或知識庫
- calculate: 數學計算
- code_execute: 執行程式碼
- api_call: 調用外部 API
- database_query: 資料庫查詢

請以結構化格式輸出計劃。"""


def create_plan(state: TechAssistState) -> dict:
    """生成執行計劃"""
    task = state["task"]
    context = state.get("injected_context", "")

    llm = ChatAnthropic(
        model=config.primary_model,
        temperature=0
    )
    structured_llm = llm.with_structured_output(Plan)

    messages = [SystemMessage(content=PLANNER_SYSTEM_PROMPT)]

    if context:
        messages.append(SystemMessage(content=f"相關上下文：\n{context}"))

    messages.append(HumanMessage(content=f"任務：{task}"))

    plan = structured_llm.invoke(messages)

    # 限制步驟數量
    if len(plan.steps) > config.max_plan_steps:
        plan.steps = plan.steps[:config.max_plan_steps]

    return {
        "plan": plan,
        "current_step_index": 0,
        "step_results": [],
        "phase": "execute"
    }
