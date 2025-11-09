from knowledge_agent import KnowledgeAgent
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()


def main():
    console.print(Panel.fit(
        "📚 專案知識管理 Agent",
        style="bold magenta"
    ))

    # 初始化 Agent
    try:
        agent = KnowledgeAgent(claude_md_path="./CLAUDE.md")
        console.print("✅ 知識庫載入成功\n", style="green")
    except FileNotFoundError:
        console.print("❌ 找不到 CLAUDE.md，請先建立專案知識庫", style="red")
        console.print("\n提示：複製 CLAUDE.md.example 並修改內容", style="yellow")
        return

    # 使用者 ID（可自訂）
    user_id = "user_001"

    # 開始對話
    console.print(f"[bold cyan]開始對話（輸入 'exit' 離開，'clear' 清除歷史）[/bold cyan]\n")
    console.print(f"[dim]使用者 ID: {user_id}[/dim]\n")

    while True:
        # 使用者輸入
        console.print("[bold yellow]你:[/bold yellow] ", end="")
        user_input = input()

        if user_input.lower() in ['exit', 'quit', 'bye']:
            console.print("\n👋 再見！", style="bold green")
            break

        if user_input.lower() == 'clear':
            agent.context_manager.clear_context(user_id)
            console.print("✅ 對話歷史已清除\n", style="green")
            continue

        if not user_input.strip():
            continue

        # Agent 回應
        console.print("\n[bold magenta]Agent:[/bold magenta] ", end="")
        console.print("[dim]思考中...[/dim]", end="\r")

        result = agent.chat_with_context(user_id, user_input)

        # 顯示回應
        console.print(" " * 20, end="\r")
        console.print(Markdown(result["response"]))

        # 顯示來源
        if result["sources"]:
            console.print(f"\n[dim]📖 參考來源: {', '.join(set(result['sources']))}[/dim]")

        console.print()


if __name__ == "__main__":
    main()
