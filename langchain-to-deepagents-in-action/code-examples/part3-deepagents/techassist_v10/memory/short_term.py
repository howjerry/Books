"""
TechAssist v1.0 - 短期記憶

滑動窗口機制管理對話上下文
"""

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from ..config import config


class ShortTermMemory:
    """短期記憶：當前對話的滑動窗口"""

    def __init__(self, max_messages: int | None = None):
        self.max_messages = max_messages or config.short_term_window
        self.messages: list[BaseMessage] = []

    def add(self, message: BaseMessage) -> None:
        """添加訊息到記憶"""
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def add_user_message(self, content: str) -> None:
        """添加用戶訊息"""
        self.add(HumanMessage(content=content))

    def add_ai_message(self, content: str) -> None:
        """添加 AI 訊息"""
        self.add(AIMessage(content=content))

    def get_recent(self, n: int = 10) -> list[BaseMessage]:
        """獲取最近 n 條訊息"""
        return self.messages[-n:]

    def get_context_string(self) -> str:
        """獲取上下文字串"""
        return "\n".join([
            f"{'用戶' if isinstance(m, HumanMessage) else 'AI'}: {m.content}"
            for m in self.messages[-5:]
        ])

    def clear(self) -> None:
        """清空記憶"""
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)
