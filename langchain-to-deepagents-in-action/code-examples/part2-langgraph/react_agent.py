#!/usr/bin/env python3
"""ReAct Agent 範例 (Chapter 4)

展示如何使用 LangGraph 實現經典的 ReAct (Reasoning + Acting) Agent。
"""

from typing import TypedDict, Annotated
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# 1. 定義狀態
# ============================================================

class AgentState(TypedDict):
    """ReAct Agent 的狀態"""
    messages: Annotated[list, add_messages]
    iteration: int


# ============================================================
# 2. 定義工具
# ============================================================

@tool
def search(query: str) -> str:
    """搜尋技術文件

    Args:
        query: 搜尋關鍵字
    """
    # 模擬搜尋結果
    mock_results = {
        "python asyncio": "asyncio 是 Python 的異步 I/O 框架，支援 async/await 語法...",
        "docker": "Docker 是容器化平台，用於打包和部署應用程式...",
        "kubernetes": "Kubernetes (K8s) 是容器編排系統...",
    }

    for key, value in mock_results.items():
        if key in query.lower():
            return f"搜尋結果：{value}"

    return f"搜尋 '{query}'：找到相關技術文件，包含基本概念和使用方法。"


@tool
def calculator(expression: str) -> str:
    """計算數學表達式

    Args:
        expression: 數學表達式，如 '2 + 2' 或 '2 ** 10'
    """
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"計算結果：{result}"
    except Exception as e:
        return f"計算錯誤：{e}"


tools = [search, calculator]


# ============================================================
# 3. 定義節點
# ============================================================

llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState) -> dict:
    """Agent 思考節點：決定下一步行動"""
    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response],
        "iteration": state["iteration"] + 1
    }


# 工具執行節點（使用預建的 ToolNode）
tool_node = ToolNode(tools)


# ============================================================
# 4. 定義路由
# ============================================================

def should_continue(state: AgentState) -> str:
    """判斷是否繼續執行工具"""
    # 檢查迭代次數限制
    if state["iteration"] >= 10:
        return "end"

    # 檢查最後一條訊息是否有工具調用
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "end"


# ============================================================
# 5. 組裝 Graph
# ============================================================

def create_react_agent():
    """創建 ReAct Agent"""
    graph = StateGraph(AgentState)

    # 添加節點
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    # 添加邊
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    graph.add_edge("tools", "agent")  # 工具執行後回到 agent

    return graph.compile()


# ============================================================
# 6. 執行
# ============================================================

def run_agent(question: str):
    """運行 ReAct Agent"""
    agent = create_react_agent()

    initial_state = {
        "messages": [HumanMessage(content=question)],
        "iteration": 0
    }

    print(f"問題：{question}\n")
    print("執行過程：")
    print("-" * 50)

    for event in agent.stream(initial_state):
        for node_name, output in event.items():
            print(f"[{node_name}]")
            if "messages" in output:
                for msg in output["messages"]:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            print(f"  🔧 調用工具：{tc['name']}({tc['args']})")
                    elif hasattr(msg, "content") and msg.content:
                        content = msg.content
                        if len(content) > 200:
                            content = content[:200] + "..."
                        print(f"  📝 {content}")
        print()

    # 獲取最終結果
    final_state = agent.invoke(initial_state)
    return final_state["messages"][-1].content


def main():
    """主函數"""
    print("=" * 60)
    print("ReAct Agent 範例")
    print("=" * 60)

    # 測試案例
    test_cases = [
        "搜尋 Python asyncio 的用法",
        "計算 2^10 + 100",
        "先搜尋 Docker 是什麼，然後計算 3.14 * 10",
    ]

    for question in test_cases:
        print("\n" + "=" * 60)
        result = run_agent(question)
        print("\n最終回答：")
        print(result)
        print("=" * 60)


if __name__ == "__main__":
    main()
