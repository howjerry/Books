#!/usr/bin/env python3
"""多 Agent 系統範例 (Chapter 6)

展示如何使用 LangGraph 實現 Supervisor Pattern 多 Agent 協作。
"""

from typing import TypedDict, Annotated, Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# 1. Worker 定義
# ============================================================

WORKERS = {
    "coder": {
        "description": "專門編寫和修改程式碼",
        "system_prompt": """你是專業的程式碼工程師。
你的任務是編寫高品質、可維護的程式碼。
只回覆程式碼和必要的說明，不要處理其他任務。
使用繁體中文說明。"""
    },
    "reviewer": {
        "description": "專門審查程式碼品質",
        "system_prompt": """你是嚴格的程式碼審查員。
檢查：程式碼風格、潛在 bug、效能問題、安全漏洞。
給出具體的改進建議。
使用繁體中文。"""
    },
    "researcher": {
        "description": "專門搜尋和整理技術資訊",
        "system_prompt": """你是技術研究員。
搜尋最新的技術資訊、最佳實踐、文件。
整理成清晰的摘要。
使用繁體中文。"""
    },
    "explainer": {
        "description": "用清晰易懂的方式解釋技術概念",
        "system_prompt": """你是技術教育專家。
用以下方式解釋技術概念：
- 使用類比和比喻
- 從簡單到複雜
- 提供具體範例

使用繁體中文，讓初學者也能理解。"""
    },
}


def get_worker_descriptions() -> str:
    """獲取 Worker 描述"""
    lines = []
    for name, config in WORKERS.items():
        lines.append(f"- {name}: {config['description']}")
    return "\n".join(lines)


# ============================================================
# 2. 狀態定義
# ============================================================

class MultiAgentState(TypedDict):
    """多 Agent 系統狀態"""
    messages: Annotated[list, add_messages]
    current_task: str
    subtasks: list[dict]  # [{worker, task, status, result}]
    next_worker: str | None
    iteration: int
    max_iterations: int
    final_answer: str | None


# ============================================================
# 3. Supervisor 實現
# ============================================================

class RouteDecision(BaseModel):
    """Supervisor 的路由決策"""
    next_worker: Literal["coder", "reviewer", "researcher", "explainer", "FINISH"] = Field(
        description="下一個要執行的 Worker 名稱，或 'FINISH' 表示完成"
    )
    task_for_worker: str = Field(
        description="分配給 Worker 的具體任務描述"
    )
    reasoning: str = Field(
        description="選擇這個 Worker 的原因"
    )


SUPERVISOR_PROMPT = f"""你是一個任務協調者 (Supervisor)。

你管理以下專業團隊成員：
{get_worker_descriptions()}

你的職責：
1. 分析用戶的請求
2. 決定需要哪些團隊成員協助
3. 分配具體任務
4. 當所有必要工作完成後，選擇 'FINISH'

決策原則：
- 簡單的概念問題：讓 explainer 解釋
- 需要技術資訊：先讓 researcher 搜尋
- 程式碼相關：讓 coder 處理
- 需要審查：讓 reviewer 檢查

每次只選擇一個 Worker。
任務完成後選擇 'FINISH'。"""


llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")


def supervisor_node(state: MultiAgentState) -> dict:
    """Supervisor 決策節點"""
    structured_llm = llm.with_structured_output(RouteDecision)

    messages = [
        SystemMessage(content=SUPERVISOR_PROMPT),
        *state["messages"]
    ]

    # 添加已完成的子任務資訊
    if state["subtasks"]:
        completed = [t for t in state["subtasks"] if t["status"] == "completed"]
        if completed:
            summary = "\n".join([
                f"- {t['worker']} 完成了：{t['result'][:100]}..."
                for t in completed
            ])
            messages.append(SystemMessage(
                content=f"已完成的子任務：\n{summary}\n\n現在決定下一步。"
            ))

    decision = structured_llm.invoke(messages)

    updates = {
        "iteration": state["iteration"] + 1
    }

    if decision.next_worker == "FINISH":
        updates["next_worker"] = None
    else:
        updates["next_worker"] = decision.next_worker
        new_subtask = {
            "worker": decision.next_worker,
            "task": decision.task_for_worker,
            "status": "pending",
            "result": None
        }
        updates["subtasks"] = state["subtasks"] + [new_subtask]
        updates["messages"] = [AIMessage(
            content=f"[Supervisor] 分配任務給 {decision.next_worker}：{decision.task_for_worker}"
        )]

    return updates


# ============================================================
# 4. Worker 節點
# ============================================================

def create_worker_node(worker_name: str):
    """工廠函數：創建 Worker 節點"""
    config = WORKERS[worker_name]

    def worker_node(state: MultiAgentState) -> dict:
        # 獲取當前任務
        current_task = None
        task_index = -1
        for i, task in enumerate(state["subtasks"]):
            if task["worker"] == worker_name and task["status"] == "pending":
                current_task = task
                task_index = i
                break

        if not current_task:
            return {}

        # 執行任務
        messages = [
            SystemMessage(content=config["system_prompt"]),
            HumanMessage(content=current_task["task"])
        ]

        response = llm.invoke(messages)

        # 更新子任務
        updated_subtasks = state["subtasks"].copy()
        updated_subtasks[task_index] = {
            **current_task,
            "status": "completed",
            "result": response.content
        }

        return {
            "subtasks": updated_subtasks,
            "messages": [AIMessage(
                content=f"[{worker_name}] 完成任務"
            )]
        }

    return worker_node


# ============================================================
# 5. 最終整合節點
# ============================================================

def finalize_node(state: MultiAgentState) -> dict:
    """整合所有結果"""
    subtasks = state.get("subtasks", [])
    completed = [t for t in subtasks if t["status"] == "completed"]

    if not completed:
        return {"final_answer": "抱歉，無法處理您的請求。"}

    # 整合結果
    results_summary = "\n\n".join([
        f"## {t['worker']} 的貢獻\n{t['result']}"
        for t in completed
    ])

    # 使用 LLM 生成最終回答
    synthesis_prompt = f"""請整合以下團隊成員的工作結果，給用戶一個完整、連貫的回答：

{results_summary}

原始請求：{state['messages'][0].content}

請用繁體中文回答，保持專業但友善的語氣。"""

    response = llm.invoke([HumanMessage(content=synthesis_prompt)])

    return {
        "final_answer": response.content,
        "messages": [AIMessage(content=response.content)]
    }


# ============================================================
# 6. 路由
# ============================================================

def route_supervisor(state: MultiAgentState) -> str:
    """Supervisor 路由"""
    if state["iteration"] >= state["max_iterations"]:
        return "finalize"

    next_worker = state.get("next_worker")
    if next_worker is None:
        return "finalize"

    return next_worker


# ============================================================
# 7. 組裝 Graph
# ============================================================

def create_multi_agent_system():
    """創建多 Agent 系統"""
    graph = StateGraph(MultiAgentState)

    # 添加節點
    graph.add_node("supervisor", supervisor_node)
    for worker_name in WORKERS:
        graph.add_node(worker_name, create_worker_node(worker_name))
    graph.add_node("finalize", finalize_node)

    # 添加邊
    graph.add_edge(START, "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            **{name: name for name in WORKERS},
            "finalize": "finalize"
        }
    )

    for worker_name in WORKERS:
        graph.add_edge(worker_name, "supervisor")

    graph.add_edge("finalize", END)

    return graph.compile()


# ============================================================
# 8. 演示
# ============================================================

def run_demo(query: str):
    """運行演示"""
    app = create_multi_agent_system()

    initial = {
        "messages": [HumanMessage(content=query)],
        "current_task": query,
        "subtasks": [],
        "next_worker": None,
        "iteration": 0,
        "max_iterations": 10,
        "final_answer": None,
    }

    print(f"\n{'=' * 60}")
    print(f"問題：{query}")
    print("=" * 60)
    print("\n🔄 團隊協作中...\n")

    for event in app.stream(initial):
        for node, output in event.items():
            if node == "supervisor":
                next_w = output.get("next_worker")
                if next_w:
                    print(f"  📋 Supervisor → {next_w}")
            elif node in WORKERS:
                print(f"  ✅ {node} 完成任務")
            elif node == "finalize":
                pass  # 最後輸出

    # 獲取最終結果
    result = app.invoke(initial)
    print(f"\n📖 最終回答：\n{'-' * 40}")
    print(result["final_answer"])


def main():
    """主函數"""
    print("=" * 60)
    print("多 Agent 系統演示 (Supervisor Pattern)")
    print("=" * 60)

    # 測試案例
    test_cases = [
        "什麼是 REST API？請簡單解釋。",
        "幫我寫一個 Python 函數來計算階乘",
        "比較 Docker 和 Kubernetes 的差異",
    ]

    for query in test_cases:
        run_demo(query)
        print("\n")


if __name__ == "__main__":
    main()
