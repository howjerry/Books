"""
TechAssist v1.0 - CLI 介面

互動式命令列介面
"""

import uuid
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

from .graph import app, short_term, session_store, long_term
from .state import TechAssistState


console = Console()


def create_initial_state(
    task: str,
    user_id: str,
    session_id: str
) -> TechAssistState:
    """創建初始狀態"""
    return {
        "messages": [],
        "user_id": user_id,
        "session_id": session_id,
        "task": task,
        "task_type": "simple",
        "phase": "analyze",
        "plan": None,
        "current_step_index": 0,
        "step_results": [],
        "injected_context": None,
        "should_memorize": False,
        "current_output": None,
        "evaluation": None,
        "reflections": [],
        "iteration": 0,
        "final_response": None
    }


def display_welcome():
    """顯示歡迎訊息"""
    welcome_text = """
# TechAssist v1.0

**DeepAgents 設計模式整合版**

整合三大設計模式：
- 🎯 **規劃模式**: 動態任務分解與執行
- 🧠 **記憶模式**: 三層記憶架構
- 🔄 **自我修正**: 品質驅動的迭代改進

輸入 `quit` 或 `exit` 退出
輸入 `memory` 查看記憶狀態
輸入 `clear` 清空短期記憶
"""
    console.print(Panel(Markdown(welcome_text), title="歡迎", border_style="blue"))


def display_memory_status():
    """顯示記憶狀態"""
    console.print("\n[bold]📊 記憶狀態[/bold]")
    console.print(f"  短期記憶: {len(short_term)} 條訊息")
    console.print(f"  長期記憶: {len(long_term)} 條記憶")
    console.print(f"  活躍會話: {len(session_store.sessions)} 個")

    if long_term.memories:
        console.print("\n  [dim]最近長期記憶:[/dim]")
        for mem in long_term.memories[-3:]:
            console.print(f"    - {mem.content[:50]}...")


def process_query(
    task: str,
    user_id: str,
    session_id: str,
    thread_id: str
) -> str:
    """處理用戶查詢"""
    initial_state = create_initial_state(task, user_id, session_id)

    config = {"configurable": {"thread_id": thread_id}}

    # 執行圖
    with console.status("[bold green]思考中...[/bold green]"):
        result = app.invoke(initial_state, config)

    return result.get("final_response", "抱歉，無法生成回應。")


def main():
    """主程式入口"""
    display_welcome()

    # 初始化會話
    user_id = "cli_user"
    session_id = str(uuid.uuid4())[:8]
    thread_id = f"thread_{session_id}"

    # 確保會話記憶存在
    session_store.get_or_create(session_id, user_id)

    console.print(f"\n[dim]會話 ID: {session_id}[/dim]\n")

    while True:
        try:
            # 獲取用戶輸入
            user_input = Prompt.ask("[bold cyan]你[/bold cyan]")

            if not user_input.strip():
                continue

            # 特殊命令
            if user_input.lower() in ["quit", "exit", "q"]:
                console.print("\n[yellow]再見！[/yellow]")
                break

            if user_input.lower() == "memory":
                display_memory_status()
                continue

            if user_input.lower() == "clear":
                short_term.clear()
                console.print("[green]短期記憶已清空[/green]")
                continue

            # 處理查詢
            response = process_query(user_input, user_id, session_id, thread_id)

            # 顯示回應
            console.print()
            console.print(Panel(
                Markdown(response),
                title="[bold green]TechAssist[/bold green]",
                border_style="green"
            ))
            console.print()

        except KeyboardInterrupt:
            console.print("\n\n[yellow]再見！[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]錯誤: {e}[/red]\n")


if __name__ == "__main__":
    main()
