from anthropic import Anthropic
from typing import Dict, List
import os
from dotenv import load_dotenv
import json

from tools.claude_md_parser import ClaudeMDParser
from tools.context_manager import ContextManager

load_dotenv()


class KnowledgeAgent:
    """知識管理 Agent"""

    def __init__(self, claude_md_path: str = "./CLAUDE.md"):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"
        self.parser = ClaudeMDParser(claude_md_path)
        self.context_manager = ContextManager()
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        overview = self.parser.get_project_overview()

        prompt = f"""你是 {overview.get('專案名稱', '本專案')} 的知識管理助理。

你的任務是：
1. 幫助新成員快速了解專案
2. 回答關於架構、設計決策的問題
3. 提供開發指引和最佳實踐
4. 提醒重要的注意事項

## 專案基本資訊
"""
        for key, value in overview.items():
            prompt += f"- **{key}**: {value}\n"

        prompt += """

## 工具使用
你可以使用 `query_knowledge_base` 工具來搜尋 CLAUDE.md 中的詳細資訊。

## 回答風格
- 使用友善、專業的語氣
- 提供清晰的解釋（包含「為什麼」）
- 引用具體的文件章節
- 如果不確定，建議查閱相關文件或詢問團隊
"""
        return prompt

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> Dict:
        if tool_name == "query_knowledge_base":
            query = tool_input["query"]
            results = self.parser.search(query)
            return {"result": results[:5]}
        return {"error": f"未知工具: {tool_name}"}

    def chat(self, user_message: str, conversation_history: List[Dict] = None) -> Dict:
        if conversation_history is None:
            conversation_history = []

        messages = conversation_history + [
            {"role": "user", "content": user_message}
        ]

        max_iterations = 10
        sources = []

        for iteration in range(max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=[self.parser.get_tool_definition()],
                messages=messages
            )

            if response.stop_reason == "end_turn":
                final_response = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_response += block.text

                messages.append({"role": "assistant", "content": response.content})

                return {
                    "response": final_response,
                    "sources": sources,
                    "history": messages
                }

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)

                        if "result" in result and isinstance(result["result"], list):
                            for item in result["result"]:
                                if isinstance(item, dict) and "section" in item:
                                    sources.append(item["section"])

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })

                messages.append({"role": "user", "content": tool_results})

        return {
            "response": "抱歉，我遇到了問題。請重新提問。",
            "sources": sources,
            "history": messages
        }

    def chat_with_context(self, user_id: str, user_message: str) -> Dict:
        """使用持久化情境的對話"""
        conversation_history = self.context_manager.load_context(user_id)
        result = self.chat(user_message, conversation_history)
        self.context_manager.save_context(user_id, result["history"])
        return result
