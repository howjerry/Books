"""
TechAssist v1.0 - 語義注入器

將相關記憶注入到提示上下文中
"""

from .short_term import ShortTermMemory
from .session import SessionMemoryStore
from .long_term import LongTermMemory


class SemanticInjector:
    """語義注入器：智能檢索並注入相關上下文"""

    def __init__(
        self,
        short_term: ShortTermMemory,
        session_store: SessionMemoryStore,
        long_term: LongTermMemory
    ):
        self.short_term = short_term
        self.session_store = session_store
        self.long_term = long_term

    def inject(
        self,
        query: str,
        session_id: str,
        user_id: str | None = None,
        include_short_term: bool = True,
        include_session: bool = True,
        include_long_term: bool = True
    ) -> str:
        """根據查詢注入相關上下文

        Args:
            query: 用戶查詢
            session_id: 當前會話 ID
            user_id: 用戶 ID（用於過濾長期記憶）
            include_short_term: 是否包含短期記憶
            include_session: 是否包含會話記憶
            include_long_term: 是否包含長期記憶

        Returns:
            格式化的上下文字串
        """
        context_parts = []

        # 短期記憶：最近對話
        if include_short_term:
            recent = self.short_term.get_context_string()
            if recent:
                context_parts.append(f"【最近對話】\n{recent}")

        # 會話記憶：當前會話摘要
        if include_session:
            session = self.session_store.get(session_id)
            if session:
                if session.topic:
                    context_parts.append(f"【會話主題】\n{session.topic}")
                if session.summary:
                    context_parts.append(f"【會話摘要】\n{session.summary}")
                if session.key_decisions:
                    decisions = "\n".join(f"- {d}" for d in session.key_decisions[-5:])
                    context_parts.append(f"【關鍵決策】\n{decisions}")

        # 長期記憶：語義相關記憶
        if include_long_term:
            relevant = self.long_term.search(query, user_id=user_id)
            if relevant:
                memory_lines = []
                for mem, score in relevant:
                    if score > 0.3:  # 相關度閾值
                        date = mem.timestamp[:10]
                        memory_lines.append(f"- [{date}] {mem.content}")
                if memory_lines:
                    context_parts.append(f"【相關歷史】\n" + "\n".join(memory_lines))

        return "\n\n".join(context_parts) if context_parts else ""

    def get_relevant_memories(
        self,
        query: str,
        user_id: str | None = None,
        top_k: int = 5
    ) -> list[dict]:
        """獲取與查詢相關的記憶列表"""
        results = []

        # 長期記憶
        for mem, score in self.long_term.search(query, top_k=top_k, user_id=user_id):
            results.append({
                "content": mem.content,
                "score": score,
                "source": "long_term",
                "timestamp": mem.timestamp
            })

        return results
