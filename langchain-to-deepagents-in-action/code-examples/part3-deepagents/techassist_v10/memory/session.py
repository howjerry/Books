"""
TechAssist v1.0 - 會話記憶

跨對話的會話狀態管理
"""

from datetime import datetime

from ..state import SessionMemory


class SessionMemoryStore:
    """會話記憶存儲"""

    def __init__(self):
        self.sessions: dict[str, SessionMemory] = {}

    def get_or_create(self, session_id: str, user_id: str) -> SessionMemory:
        """獲取或創建會話記憶"""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionMemory(
                session_id=session_id,
                user_id=user_id
            )
        return self.sessions[session_id]

    def get(self, session_id: str) -> SessionMemory | None:
        """獲取會話記憶"""
        return self.sessions.get(session_id)

    def update_summary(self, session_id: str, summary: str) -> None:
        """更新會話摘要"""
        if session_id in self.sessions:
            self.sessions[session_id].summary = summary

    def update_topic(self, session_id: str, topic: str) -> None:
        """更新會話主題"""
        if session_id in self.sessions:
            self.sessions[session_id].topic = topic

    def add_decision(self, session_id: str, decision: str) -> None:
        """添加關鍵決策"""
        if session_id in self.sessions:
            self.sessions[session_id].key_decisions.append(decision)

    def list_sessions(self, user_id: str) -> list[SessionMemory]:
        """列出用戶的所有會話"""
        return [
            s for s in self.sessions.values()
            if s.user_id == user_id
        ]

    def delete(self, session_id: str) -> bool:
        """刪除會話"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
