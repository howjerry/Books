"""
TechAssist v1.0 - 主圖組裝

整合 Planning、Memory、Reflexion 三大設計模式
"""

from typing import Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .config import config
from .state import TechAssistState
from .memory import ShortTermMemory, SessionMemoryStore, LongTermMemory, SemanticInjector
from .planning import create_plan, execute_step, evaluate_and_replan
from .reflexion import generate_output, evaluate_output, refine_output


# ============================================================
# 全局記憶實例
# ============================================================

short_term = ShortTermMemory()
session_store = SessionMemoryStore()
long_term = LongTermMemory()
injector = SemanticInjector(short_term, session_store, long_term)


# ============================================================
# 節點實現
# ============================================================

def memory_injection_node(state: TechAssistState) -> dict:
    """記憶注入節點：檢索相關上下文"""
    query = state["task"]
    session_id = state["session_id"]
    user_id = state["user_id"]

    context = injector.inject(query, session_id, user_id)

    return {"injected_context": context if context else None}


def task_analyzer_node(state: TechAssistState) -> dict:
    """任務分析節點：判斷任務類型和複雜度"""
    task = state["task"]

    llm = ChatAnthropic(model=config.primary_model, temperature=0)

    analysis_prompt = f"""分析以下任務，判斷其類型和複雜度。

任務：{task}

請回答：
1. 任務類型（simple/complex/code）：
   - simple: 簡單問答，可直接回答
   - complex: 需要多步驟規劃
   - code: 需要生成程式碼

2. 只回答類型，如：simple

回答："""

    response = llm.invoke([HumanMessage(content=analysis_prompt)])
    task_type = response.content.strip().lower()

    # 標準化任務類型
    if "code" in task_type or "程式" in task or "代碼" in task:
        task_type = "code"
    elif "complex" in task_type or len(task) > 100:
        task_type = "complex"
    else:
        task_type = "simple"

    return {
        "task_type": task_type,
        "phase": "plan" if task_type == "complex" else "execute"
    }


def direct_response_node(state: TechAssistState) -> dict:
    """直接回應節點：處理簡單任務"""
    task = state["task"]
    context = state.get("injected_context", "")

    llm = ChatAnthropic(model=config.primary_model, temperature=config.temperature)

    messages = [
        SystemMessage(content="你是 TechAssist，一個專業的企業技術助理。請簡潔準確地回答問題。")
    ]

    if context:
        messages.append(SystemMessage(content=f"相關上下文：\n{context}"))

    messages.append(HumanMessage(content=task))

    response = llm.invoke(messages)

    return {
        "final_response": response.content,
        "phase": "respond"
    }


def synthesize_response_node(state: TechAssistState) -> dict:
    """整合回應節點：根據執行結果生成最終回應"""
    task = state["task"]
    step_results = state.get("step_results", [])
    current_output = state.get("current_output")

    llm = ChatAnthropic(model=config.primary_model, temperature=config.temperature)

    # 收集執行結果
    if step_results:
        results_text = "\n".join([
            f"步驟 {r.step_id}: {r.output if r.success else '失敗 - ' + (r.error or '')}"
            for r in step_results
        ])
    elif current_output:
        results_text = current_output
    else:
        results_text = "無執行結果"

    response = llm.invoke([
        SystemMessage(content="你是 TechAssist。請根據任務執行結果生成完整的回應。"),
        HumanMessage(content=f"""
任務：{task}

執行結果：
{results_text}

請生成最終回應：
""")
    ])

    return {"final_response": response.content}


def memory_consolidation_node(state: TechAssistState) -> dict:
    """記憶整合節點：保存重要資訊"""
    task = state["task"]
    response = state.get("final_response", "")
    session_id = state["session_id"]
    user_id = state["user_id"]

    # 更新短期記憶
    short_term.add_user_message(task)
    short_term.add_ai_message(response[:500])

    # 評估是否需要保存到長期記憶
    llm = ChatAnthropic(model=config.primary_model, temperature=0)
    eval_response = llm.invoke([
        HumanMessage(content=f"""
評估以下對話是否包含值得長期記憶的重要資訊（用戶偏好、專案決策、技術選擇等）：

用戶：{task}
AI：{response[:300]}

只回答「是」或「否」：""")
    ])

    if "是" in eval_response.content:
        # 生成摘要並保存
        summary_response = llm.invoke([
            HumanMessage(content=f"用一句話總結這個對話的關鍵資訊：\n用戶：{task}\nAI：{response[:300]}")
        ])

        long_term.add(
            content=summary_response.content.strip(),
            importance=0.7,
            user_id=user_id,
            metadata={"session_id": session_id}
        )

        session_store.add_decision(session_id, summary_response.content.strip())

    return {"should_memorize": "是" in eval_response.content}


# ============================================================
# 路由函數
# ============================================================

def route_after_analysis(state: TechAssistState) -> Literal["plan", "execute", "direct"]:
    """任務分析後的路由"""
    task_type = state.get("task_type", "simple")

    if task_type == "simple":
        return "direct"
    elif task_type == "complex":
        return "plan"
    else:  # code
        return "execute"


def route_after_execute(state: TechAssistState) -> Literal["execute", "replan", "evaluate", "synthesize"]:
    """執行後的路由"""
    plan = state.get("plan")
    current_index = state.get("current_step_index", 0)
    task_type = state.get("task_type")

    # 如果是程式碼任務，進入評估
    if task_type == "code":
        return "evaluate"

    # 如果沒有計劃（簡單任務），直接整合
    if not plan:
        return "synthesize"

    # 檢查是否所有步驟都已執行
    if current_index >= len(plan.steps):
        # 檢查失敗率
        step_results = state.get("step_results", [])
        failed = sum(1 for r in step_results if not r.success)
        if failed > 0 and failed < len(step_results) // 2:
            return "replan"
        return "synthesize"

    return "execute"


def route_after_evaluate(state: TechAssistState) -> Literal["refine", "synthesize"]:
    """評估後的路由"""
    evaluation = state.get("evaluation")
    iteration = state.get("iteration", 0)

    if evaluation and evaluation.passed:
        return "synthesize"

    if iteration >= config.max_iterations:
        return "synthesize"

    return "refine"


# ============================================================
# 構建主圖
# ============================================================

def build_techassist_graph():
    """構建 TechAssist v1.0 主圖"""
    graph = StateGraph(TechAssistState)

    # 添加節點
    graph.add_node("inject_memory", memory_injection_node)
    graph.add_node("analyze_task", task_analyzer_node)
    graph.add_node("direct_response", direct_response_node)
    graph.add_node("create_plan", create_plan)
    graph.add_node("execute_step", execute_step)
    graph.add_node("replan", evaluate_and_replan)
    graph.add_node("generate", generate_output)
    graph.add_node("evaluate", evaluate_output)
    graph.add_node("refine", refine_output)
    graph.add_node("synthesize", synthesize_response_node)
    graph.add_node("consolidate_memory", memory_consolidation_node)

    # 定義流程
    graph.add_edge(START, "inject_memory")
    graph.add_edge("inject_memory", "analyze_task")

    # 任務分析後的路由
    graph.add_conditional_edges(
        "analyze_task",
        route_after_analysis,
        {
            "direct": "direct_response",
            "plan": "create_plan",
            "execute": "generate"
        }
    )

    # 直接回應 -> 記憶整合
    graph.add_edge("direct_response", "consolidate_memory")

    # 計劃 -> 執行
    graph.add_edge("create_plan", "execute_step")

    # 執行後的路由
    graph.add_conditional_edges(
        "execute_step",
        route_after_execute,
        {
            "execute": "execute_step",
            "replan": "replan",
            "evaluate": "evaluate",
            "synthesize": "synthesize"
        }
    )

    # 重規劃 -> 執行
    graph.add_edge("replan", "execute_step")

    # 生成 -> 評估
    graph.add_edge("generate", "evaluate")

    # 評估後的路由
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "refine": "refine",
            "synthesize": "synthesize"
        }
    )

    # 修正 -> 重新生成
    graph.add_edge("refine", "generate")

    # 整合 -> 記憶整合
    graph.add_edge("synthesize", "consolidate_memory")

    # 記憶整合 -> 結束
    graph.add_edge("consolidate_memory", END)

    # 編譯
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# 全局應用實例
app = build_techassist_graph()
