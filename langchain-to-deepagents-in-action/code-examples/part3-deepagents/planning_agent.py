"""
Chapter 7: 規劃模式 (The Planning Pattern) - 獨立範例

Planner-Executor-Replanner 架構實現
"""

import os
from typing import TypedDict, Annotated, Literal
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


# ============================================================
# 1. 結構化輸出定義
# ============================================================

class Step(BaseModel):
    """計劃中的單一步驟"""
    id: int = Field(description="步驟編號")
    action: str = Field(description="要執行的動作")
    tool: str | None = Field(default=None, description="需要使用的工具")
    expected_output: str = Field(description="預期輸出")
    dependencies: list[int] = Field(default_factory=list, description="依賴的步驟 ID")


class Plan(BaseModel):
    """完整的執行計劃"""
    goal: str = Field(description="最終目標")
    steps: list[Step] = Field(description="執行步驟列表")
    reasoning: str = Field(description="規劃理由")


class StepResult(BaseModel):
    """步驟執行結果"""
    step_id: int
    success: bool
    output: str
    error: str | None = None


class ReplanDecision(BaseModel):
    """重規劃決策"""
    should_replan: bool = Field(description="是否需要重規劃")
    reason: str = Field(description="決策理由")
    new_steps: list[Step] | None = Field(default=None, description="新的步驟")


# ============================================================
# 2. 狀態定義
# ============================================================

class PlanningState(TypedDict):
    messages: Annotated[list, add_messages]
    task: str
    plan: Plan | None
    current_step_index: int
    step_results: list[StepResult]
    final_answer: str | None


# ============================================================
# 3. 節點實現
# ============================================================

# ‹1› 初始化 LLM
llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0)


def planner_node(state: PlanningState) -> dict:
    """‹2› Planner 節點：生成執行計劃"""
    task = state["task"]

    system_prompt = """你是一位專業的任務規劃專家。

給定一個任務，請制定詳細的執行計劃。每個步驟應該：
1. 具體且可執行
2. 有明確的預期輸出
3. 標註依賴關係

可用工具：
- search: 搜尋文檔或網路
- calculate: 數學計算
- code_execute: 執行程式碼
- api_call: 調用 API

請以結構化格式輸出計劃。"""

    structured_llm = llm.with_structured_output(Plan)
    plan = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"任務：{task}")
    ])

    print(f"\n📋 生成計劃：{plan.goal}")
    for step in plan.steps:
        deps = f" (依賴: {step.dependencies})" if step.dependencies else ""
        print(f"  {step.id}. {step.action}{deps}")

    return {
        "plan": plan,
        "current_step_index": 0,
        "step_results": []
    }


def executor_node(state: PlanningState) -> dict:
    """‹3› Executor 節點：執行當前步驟"""
    plan = state["plan"]
    current_index = state["current_step_index"]
    step_results = state["step_results"]

    if current_index >= len(plan.steps):
        return {}

    current_step = plan.steps[current_index]
    print(f"\n⚙️ 執行步驟 {current_step.id}: {current_step.action}")

    # ‹4› 檢查依賴是否滿足
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
                error=f"依賴步驟 {dep_id} 未完成或失敗"
            )
            return {
                "step_results": [result],
                "current_step_index": current_index + 1
            }

    # ‹5› 模擬工具執行
    try:
        if current_step.tool == "calculate":
            output = f"計算結果：42"
        elif current_step.tool == "search":
            output = f"搜尋結果：找到 3 個相關文檔"
        elif current_step.tool == "code_execute":
            output = f"程式碼執行成功，輸出：Hello World"
        elif current_step.tool == "api_call":
            output = f"API 回應：status=200, data={{...}}"
        else:
            # 使用 LLM 執行一般步驟
            response = llm.invoke([
                SystemMessage(content="你是一個執行助手，請執行以下步驟並給出結果。"),
                HumanMessage(content=f"步驟：{current_step.action}\n預期輸出：{current_step.expected_output}")
            ])
            output = response.content

        result = StepResult(
            step_id=current_step.id,
            success=True,
            output=output[:500]  # 截斷過長輸出
        )
        print(f"  ✅ 完成：{output[:100]}...")

    except Exception as e:
        result = StepResult(
            step_id=current_step.id,
            success=False,
            output="",
            error=str(e)
        )
        print(f"  ❌ 失敗：{e}")

    return {
        "step_results": [result],
        "current_step_index": current_index + 1
    }


def replanner_node(state: PlanningState) -> dict:
    """‹6› Replanner 節點：評估進度並決定是否重規劃"""
    plan = state["plan"]
    step_results = state["step_results"]

    # 收集失敗的步驟
    failed_steps = [r for r in step_results if not r.success]

    if not failed_steps:
        return {}  # 無需重規劃

    system_prompt = """你是一位任務重規劃專家。

當前計劃執行遇到問題，請分析並決定：
1. 是否需要調整計劃
2. 如何修改後續步驟來達成目標

請以結構化格式輸出決策。"""

    context = f"""
原始目標：{plan.goal}

已執行步驟：
{chr(10).join(f"- 步驟 {r.step_id}: {'成功' if r.success else '失敗 - ' + (r.error or '')}" for r in step_results)}

失敗步驟詳情：
{chr(10).join(f"- 步驟 {r.step_id}: {r.error}" for r in failed_steps)}

剩餘步驟：
{chr(10).join(f"- 步驟 {s.id}: {s.action}" for s in plan.steps if s.id > state["current_step_index"])}
"""

    structured_llm = llm.with_structured_output(ReplanDecision)
    decision = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=context)
    ])

    if decision.should_replan and decision.new_steps:
        print(f"\n🔄 重規劃：{decision.reason}")
        # 更新計劃中的剩餘步驟
        completed_steps = plan.steps[:state["current_step_index"]]
        new_plan = Plan(
            goal=plan.goal,
            steps=completed_steps + decision.new_steps,
            reasoning=f"重規劃：{decision.reason}"
        )
        return {"plan": new_plan}

    return {}


def synthesizer_node(state: PlanningState) -> dict:
    """‹7› Synthesizer 節點：整合所有結果生成最終答案"""
    plan = state["plan"]
    step_results = state["step_results"]

    system_prompt = """你是一位結果整合專家。

請根據任務目標和所有執行結果，生成一個完整、專業的最終回答。"""

    results_summary = "\n".join([
        f"步驟 {r.step_id}: {r.output if r.success else '失敗 - ' + (r.error or '')}"
        for r in step_results
    ])

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""
任務目標：{plan.goal}

執行結果：
{results_summary}

請整合以上結果，生成最終回答。
""")
    ])

    return {"final_answer": response.content}


# ============================================================
# 4. 路由函數
# ============================================================

def should_continue_execution(state: PlanningState) -> Literal["executor", "replanner", "synthesizer"]:
    """‹8› 決定下一步：繼續執行、重規劃或整合結果"""
    plan = state["plan"]
    current_index = state["current_step_index"]
    step_results = state["step_results"]

    # 檢查是否所有步驟都已執行
    if current_index >= len(plan.steps):
        # 檢查是否有失敗需要重規劃
        failed_count = sum(1 for r in step_results if not r.success)
        if failed_count > 0 and failed_count < len(plan.steps) // 2:
            return "replanner"
        return "synthesizer"

    # 繼續執行下一步
    return "executor"


# ============================================================
# 5. 構建圖
# ============================================================

def build_planning_graph() -> StateGraph:
    """構建規劃模式圖"""
    graph = StateGraph(PlanningState)

    # 添加節點
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("replanner", replanner_node)
    graph.add_node("synthesizer", synthesizer_node)

    # 添加邊
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor",
        should_continue_execution,
        {
            "executor": "executor",
            "replanner": "replanner",
            "synthesizer": "synthesizer"
        }
    )
    graph.add_edge("replanner", "executor")
    graph.add_edge("synthesizer", END)

    return graph.compile()


# ============================================================
# 6. 主程式
# ============================================================

def main():
    """執行規劃模式範例"""
    print("=" * 60)
    print("Chapter 7: 規劃模式 (The Planning Pattern)")
    print("=" * 60)

    # 構建圖
    app = build_planning_graph()

    # 測試任務
    tasks = [
        "分析我們公司上季度的銷售數據，找出銷售最好的產品類別，並給出下季度的改進建議",
        "幫我寫一個 Python 函數來計算費波那契數列的第 N 項，並測試它的正確性",
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n{'='*60}")
        print(f"任務 {i}: {task}")
        print("=" * 60)

        initial_state = {
            "messages": [],
            "task": task,
            "plan": None,
            "current_step_index": 0,
            "step_results": [],
            "final_answer": None
        }

        # 執行圖
        result = app.invoke(initial_state)

        print(f"\n📝 最終答案：")
        print("-" * 40)
        print(result["final_answer"])

        if i < len(tasks):
            input("\n按 Enter 繼續下一個任務...")


if __name__ == "__main__":
    main()
