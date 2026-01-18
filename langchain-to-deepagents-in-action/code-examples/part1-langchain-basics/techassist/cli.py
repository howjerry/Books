"""TechAssist CLI 介面"""

import sys
from .chains import create_qa_chain, create_intent_classifier, create_handlers
from .intents import INTENT_HANDLER_MAP


def run_cli_v1():
    """執行 TechAssist v0.1 CLI（基礎問答）"""
    print("=" * 60)
    print("🤖 TechAssist v0.1 - 技術助理")
    print("=" * 60)
    print("輸入技術問題，我會為你解答。")
    print("輸入 'quit' 或 'exit' 離開。")
    print("-" * 60)

    chain = create_qa_chain()

    while True:
        try:
            question = input("\n📝 你的問題：").strip()

            if not question:
                continue

            if question.lower() in ('quit', 'exit', 'q'):
                print("\n👋 感謝使用 TechAssist，再見！")
                break

            print("\n💭 思考中...\n")

            # 串流輸出
            print("📖 回答：")
            for chunk in chain.stream({"question": question}):
                print(chunk, end="", flush=True)
            print("\n")

        except KeyboardInterrupt:
            print("\n\n👋 感謝使用 TechAssist，再見！")
            break
        except Exception as e:
            print(f"\n❌ 發生錯誤：{e}")


def run_cli_v2():
    """執行 TechAssist v0.2 CLI（意圖分類）"""
    print("=" * 60)
    print("🤖 TechAssist v0.2 - 智能意圖識別版")
    print("=" * 60)
    print("我現在能更好地理解你的問題了！")
    print("輸入 'quit' 離開。")
    print("-" * 60)

    classifier = create_intent_classifier()
    handlers = create_handlers()

    while True:
        try:
            user_input = input("\n📝 你的問題：").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\n👋 感謝使用 TechAssist，再見！")
                break

            print("\n🔍 分析中...")

            # 分類意圖
            classification = classifier.invoke({"user_input": user_input})
            print(f"📊 意圖：{classification.intent.value} (信心：{classification.confidence:.0%})")

            # 路由到處理器
            handler_name = INTENT_HANDLER_MAP.get(
                classification.intent,
                "default_handler"
            )
            handler = handlers.get(handler_name, handlers["default_handler"])

            # 串流輸出
            print("\n📖 回答：")
            for chunk in handler.stream({"user_input": user_input}):
                print(chunk, end="", flush=True)
            print("\n")

        except KeyboardInterrupt:
            print("\n\n👋 感謝使用 TechAssist，再見！")
            break
        except Exception as e:
            print(f"\n❌ 發生錯誤：{e}")


def run_cli_v3():
    """執行 TechAssist v0.3 CLI（工具增強）"""
    from langchain_anthropic import ChatAnthropic
    from .tools import TECHASSIST_TOOLS
    from .config import settings
    from .prompts import SYSTEM_PROMPT_V3

    print("=" * 60)
    print("🤖 TechAssist v0.3 - 工具增強版")
    print("=" * 60)
    print("我現在可以搜尋文件、計算和執行程式碼了！")
    print("指令：'quit' 離開, 'clear' 清除對話歷史")
    print("-" * 60)

    # 初始化
    llm = ChatAnthropic(
        model=settings.model_name,
        temperature=settings.temperature,
    )
    llm_with_tools = llm.bind_tools(TECHASSIST_TOOLS)
    tool_map = {t.name: t for t in TECHASSIST_TOOLS}

    messages = []

    while True:
        try:
            user_input = input("\n📝 你的問題：").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\n👋 感謝使用 TechAssist，再見！")
                break

            if user_input.lower() == 'clear':
                messages = []
                print("✨ 對話歷史已清除")
                continue

            print("\n💭 處理中...\n")

            # 建立訊息列表
            current_messages = [
                {"role": "system", "content": SYSTEM_PROMPT_V3},
                *messages,
                {"role": "user", "content": user_input}
            ]

            # 調用 LLM
            response = llm_with_tools.invoke(current_messages)

            # 處理工具調用
            while response.tool_calls:
                # 執行工具
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]

                    print(f"  🔧 調用工具：{tool_name}")
                    print(f"     參數：{tool_args}")

                    tool = tool_map[tool_name]
                    result = tool.invoke(tool_args)

                    print(f"     結果：{result[:100]}...")

                    # 記錄工具結果
                    current_messages.append({
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [tool_call]
                    })
                    current_messages.append({
                        "role": "tool",
                        "content": result,
                        "tool_call_id": tool_id
                    })

                # 繼續對話
                response = llm_with_tools.invoke(current_messages)

            # 輸出最終回應
            print(f"\n📖 回答：\n{response.content}")

            # 保存對話歷史
            messages.append({"role": "user", "content": user_input})
            messages.append({"role": "assistant", "content": response.content})

        except KeyboardInterrupt:
            print("\n\n👋 感謝使用 TechAssist，再見！")
            break
        except Exception as e:
            print(f"\n❌ 發生錯誤：{e}")


if __name__ == "__main__":
    # 預設執行最新版本
    run_cli_v3()
