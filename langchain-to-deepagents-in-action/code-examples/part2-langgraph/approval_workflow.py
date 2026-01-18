#!/usr/bin/env python3
"""審批工作流範例 (Chapter 5)

展示如何使用 LangGraph 實現 Human-in-the-Loop 審批流程。
"""

from typing import TypedDict, Annotated, Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import NodeInterrupt
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# 1. 狀態定義
# ============================================================

class ApprovalState(TypedDict):
    """審批工作流狀態"""
    messages: Annotated[list, add_messages]

    # 請求資訊
    request_type: str
    request_details: dict

    # 風險評估
    risk_level: Literal["low", "medium", "high"]
    is_sensitive: bool

    # 審批資訊
    approval_status: Literal["pending", "approved", "rejected"] | None
    approver: str | None
    approval_reason: str | None

    # 執行結果
    execution_result: str | None


# ============================================================
# 2. 節點實現
# ============================================================

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")


def analyze_request(state: ApprovalState) -> dict:
    """分析請求並評估風險"""
    user_request = state["messages"][-1].content

    # 使用 LLM 分析
    analysis_prompt = f"""分析以下請求的風險等級：

請求：{user_request}

回覆格式（只回覆這三行）：
風險等級：[low/medium/high]
是否敏感：[yes/no]
原因：[簡短說明]
"""

    response = llm.invoke([HumanMessage(content=analysis_prompt)])
    content = response.content.lower()

    # 簡單解析
    risk_level = "high" if "high" in content else ("medium" if "medium" in content else "low")
    is_sensitive = "yes" in content or "敏感" in content or risk_level == "high"

    return {
        "request_type": "general",
        "risk_level": risk_level,
        "is_sensitive": is_sensitive,
        "messages": [AIMessage(content=f"📊 風險評估完成：{risk_level} 風險")]
    }


def request_approval(state: ApprovalState) -> dict:
    """請求人工審批"""
    # 如果已有審批結果，跳過
    if state.get("approval_status") in ("approved", "rejected"):
        return {}

    # 使用 NodeInterrupt 中斷執行
    raise NodeInterrupt(
        f"⚠️ 需要人工審批\n\n"
        f"風險等級：{state['risk_level']}\n"
        f"請求內容：{state['messages'][0].content}\n\n"
        f"請管理員審核後設置 approval_status 為 'approved' 或 'rejected'"
    )


def execute_request(state: ApprovalState) -> dict:
    """執行請求"""
    result = f"已成功處理請求：{state.get('request_details', {})}"
    return {
        "execution_result": result,
        "messages": [AIMessage(content=f"✅ {result}")]
    }


def reject_request(state: ApprovalState) -> dict:
    """拒絕請求"""
    reason = state.get("approval_reason", "未提供原因")
    return {
        "execution_result": "rejected",
        "messages": [AIMessage(content=f"❌ 請求已被拒絕。原因：{reason}")]
    }


def auto_execute(state: ApprovalState) -> dict:
    """自動執行（低風險）"""
    return {
        "execution_result": "auto_executed",
        "messages": [AIMessage(content="✅ 低風險請求，已自動處理。")]
    }


# ============================================================
# 3. 路由函數
# ============================================================

def route_after_analysis(state: ApprovalState) -> str:
    """分析後路由"""
    if state["is_sensitive"]:
        return "request_approval"
    return "auto_execute"


def route_after_approval(state: ApprovalState) -> str:
    """審批後路由"""
    status = state.get("approval_status")
    if status == "approved":
        return "execute"
    elif status == "rejected":
        return "reject"
    return "wait"


# ============================================================
# 4. 組裝 Graph
# ============================================================

def create_approval_workflow():
    """創建審批工作流"""
    graph = StateGraph(ApprovalState)

    # 添加節點
    graph.add_node("analyze", analyze_request)
    graph.add_node("request_approval", request_approval)
    graph.add_node("execute", execute_request)
    graph.add_node("reject", reject_request)
    graph.add_node("auto_execute", auto_execute)

    # 添加邊
    graph.add_edge(START, "analyze")

    graph.add_conditional_edges(
        "analyze",
        route_after_analysis,
        {
            "request_approval": "request_approval",
            "auto_execute": "auto_execute"
        }
    )

    graph.add_conditional_edges(
        "request_approval",
        route_after_approval,
        {
            "execute": "execute",
            "reject": "reject",
            "wait": "request_approval"
        }
    )

    graph.add_edge("execute", END)
    graph.add_edge("reject", END)
    graph.add_edge("auto_execute", END)

    # 使用 MemorySaver 持久化
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ============================================================
# 5. 演示
# ============================================================

def run_approval_demo():
    """演示審批流程"""
    app = create_approval_workflow()
    thread_id = "approval-demo-001"
    config = {"configurable": {"thread_id": thread_id}}

    # 初始狀態
    initial = {
        "messages": [HumanMessage(content="請刪除所有測試用戶資料")],
        "request_type": "",
        "request_details": {"action": "delete_test_users"},
        "risk_level": "low",
        "is_sensitive": False,
        "approval_status": None,
        "approver": None,
        "approval_reason": None,
        "execution_result": None,
    }

    print("=" * 60)
    print("審批工作流演示")
    print("=" * 60)

    # 第一次執行：會在敏感操作處中斷
    print("\n步驟 1：提交請求並分析風險")
    try:
        for event in app.stream(initial, config=config):
            for node, output in event.items():
                print(f"  [{node}] {output.get('messages', [{}])[-1].content if output.get('messages') else ''}")
    except Exception as e:
        print(f"\n⏸️ 流程已中斷：\n{e}")

    # 檢查狀態
    snapshot = app.get_state(config)
    print(f"\n當前狀態：")
    print(f"  風險等級：{snapshot.values.get('risk_level')}")
    print(f"  需要審批：{snapshot.values.get('is_sensitive')}")
    print(f"  下一步：{snapshot.next}")

    # 模擬管理員審批
    print("\n" + "-" * 40)
    print("步驟 2：管理員審批中...")
    app.update_state(
        config,
        {
            "approval_status": "approved",
            "approver": "admin@company.com",
            "approval_reason": "已確認是測試環境，批准執行"
        }
    )
    print("  ✅ 已批准")

    # 繼續執行
    print("\n步驟 3：繼續執行...")
    for event in app.stream(None, config=config):
        for node, output in event.items():
            if output.get("messages"):
                print(f"  [{node}] {output['messages'][-1].content}")

    # 獲取最終結果
    final = app.get_state(config)
    print(f"\n最終結果：{final.values.get('execution_result')}")


def run_low_risk_demo():
    """演示低風險自動處理"""
    app = create_approval_workflow()
    config = {"configurable": {"thread_id": "low-risk-001"}}

    initial = {
        "messages": [HumanMessage(content="查詢今天的系統日誌")],
        "request_type": "",
        "request_details": {"action": "query_logs"},
        "risk_level": "low",
        "is_sensitive": False,
        "approval_status": None,
        "approver": None,
        "approval_reason": None,
        "execution_result": None,
    }

    print("\n" + "=" * 60)
    print("低風險請求演示（自動處理）")
    print("=" * 60)

    for event in app.stream(initial, config=config):
        for node, output in event.items():
            if output.get("messages"):
                print(f"  [{node}] {output['messages'][-1].content}")


def main():
    """主函數"""
    run_approval_demo()
    run_low_risk_demo()


if __name__ == "__main__":
    main()
