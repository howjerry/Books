"""
Chapter 8: 記憶模式 (The Memory Pattern) - 獨立範例

三層記憶架構 + 語義注入實現
"""

import os
import json
import hashlib
from datetime import datetime
from typing import TypedDict, Annotated, Literal
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.embeddings import Embeddings
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


# ============================================================
# 1. 記憶資料結構
# ============================================================

@dataclass
class MemoryEntry:
    """記憶條目"""
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    importance: float = 0.5
    access_count: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SessionMemory:
    """會話記憶"""
    session_id: str
    user_id: str
    topic: str = ""
    summary: str = ""
    key_decisions: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class RetrievedMemory(BaseModel):
    """檢索到的記憶"""
    content: str
    relevance_score: float
    source: Literal["short_term", "session", "long_term"]
    timestamp: str


# ============================================================
# 2. 記憶管理器
# ============================================================

class SimpleEmbeddings:
    """簡化的嵌入實現（用於演示）"""

    def embed_query(self, text: str) -> list[float]:
        """生成簡單的文本哈希作為嵌入向量"""
        # 實際應用中應使用真正的嵌入模型
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_bytes[:64]]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]


class ShortTermMemory:
    """‹1› 短期記憶：當前對話上下文"""

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self.messages: list[BaseMessage] = []

    def add(self, message: BaseMessage) -> None:
        self.messages.append(message)
        # 滑動窗口
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_recent(self, n: int = 10) -> list[BaseMessage]:
        return self.messages[-n:]

    def get_context_string(self) -> str:
        return "\n".join([
            f"{'用戶' if isinstance(m, HumanMessage) else 'AI'}: {m.content}"
            for m in self.messages[-5:]
        ])


class SessionMemoryStore:
    """‹2› 會話記憶：跨對話的會話狀態"""

    def __init__(self):
        self.sessions: dict[str, SessionMemory] = {}

    def get_or_create(self, session_id: str, user_id: str) -> SessionMemory:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionMemory(
                session_id=session_id,
                user_id=user_id
            )
        return self.sessions[session_id]

    def update_summary(self, session_id: str, summary: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].summary = summary
            self.sessions[session_id].updated_at = datetime.now().isoformat()

    def add_decision(self, session_id: str, decision: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].key_decisions.append(decision)


class LongTermMemory:
    """‹3› 長期記憶：向量化的持久記憶"""

    def __init__(self, embeddings: SimpleEmbeddings | None = None):
        self.embeddings = embeddings or SimpleEmbeddings()
        self.memories: list[MemoryEntry] = []
        self.vectors: list[list[float]] = []

    def add(self, content: str, importance: float = 0.5, metadata: dict | None = None) -> None:
        entry = MemoryEntry(
            content=content,
            importance=importance,
            metadata=metadata or {}
        )
        self.memories.append(entry)
        self.vectors.append(self.embeddings.embed_query(content))
        print(f"  💾 保存長期記憶：{content[:50]}...")

    def search(self, query: str, top_k: int = 3) -> list[tuple[MemoryEntry, float]]:
        """語義搜尋相關記憶"""
        if not self.memories:
            return []

        query_vector = self.embeddings.embed_query(query)

        # 計算餘弦相似度
        scores = []
        for vec in self.vectors:
            dot_product = sum(a * b for a, b in zip(query_vector, vec))
            norm_q = sum(a * a for a in query_vector) ** 0.5
            norm_v = sum(b * b for b in vec) ** 0.5
            similarity = dot_product / (norm_q * norm_v) if norm_q * norm_v > 0 else 0
            scores.append(similarity)

        # 結合相似度和重要性排序
        scored_memories = [
            (mem, score * 0.7 + mem.importance * 0.3)
            for mem, score in zip(self.memories, scores)
        ]
        scored_memories.sort(key=lambda x: x[1], reverse=True)

        # 更新訪問計數
        for mem, _ in scored_memories[:top_k]:
            mem.access_count += 1

        return scored_memories[:top_k]


# ============================================================
# 3. 語義注入器
# ============================================================

class SemanticInjector:
    """‹4› 語義注入器：將相關記憶注入提示"""

    def __init__(
        self,
        short_term: ShortTermMemory,
        session_store: SessionMemoryStore,
        long_term: LongTermMemory
    ):
        self.short_term = short_term
        self.session_store = session_store
        self.long_term = long_term

    def inject(self, query: str, session_id: str) -> str:
        """根據查詢注入相關上下文"""
        context_parts = []

        # ‹5› 短期記憶：最近對話
        recent_context = self.short_term.get_context_string()
        if recent_context:
            context_parts.append(f"【最近對話】\n{recent_context}")

        # ‹6› 會話記憶：當前會話摘要
        if session_id in self.session_store.sessions:
            session = self.session_store.sessions[session_id]
            if session.summary:
                context_parts.append(f"【會話摘要】\n{session.summary}")
            if session.key_decisions:
                decisions = "\n".join(f"- {d}" for d in session.key_decisions[-3:])
                context_parts.append(f"【關鍵決策】\n{decisions}")

        # ‹7› 長期記憶：語義相關記憶
        relevant_memories = self.long_term.search(query, top_k=3)
        if relevant_memories:
            memory_text = "\n".join([
                f"- [{mem.timestamp[:10]}] {mem.content}"
                for mem, score in relevant_memories
                if score > 0.3  # 相關度閾值
            ])
            if memory_text:
                context_parts.append(f"【相關歷史】\n{memory_text}")

        if not context_parts:
            return ""

        return "\n\n".join(context_parts)


# ============================================================
# 4. 狀態定義
# ============================================================

class MemoryState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    session_id: str
    current_query: str
    injected_context: str | None
    response: str | None
    should_memorize: bool


# ============================================================
# 5. 節點實現
# ============================================================

# 全局記憶實例（實際應用中應使用依賴注入）
short_term_memory = ShortTermMemory()
session_memory_store = SessionMemoryStore()
long_term_memory = LongTermMemory()
semantic_injector = SemanticInjector(
    short_term_memory,
    session_memory_store,
    long_term_memory
)

llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0)


def memory_injection_node(state: MemoryState) -> dict:
    """‹8› 記憶注入節點：檢索並注入相關上下文"""
    query = state["current_query"]
    session_id = state["session_id"]

    print(f"\n🔍 檢索相關記憶...")
    injected_context = semantic_injector.inject(query, session_id)

    if injected_context:
        print(f"  ✅ 注入上下文：{len(injected_context)} 字符")
    else:
        print(f"  ℹ️ 無相關上下文")

    return {"injected_context": injected_context}


def response_generation_node(state: MemoryState) -> dict:
    """‹9› 回應生成節點：基於注入上下文生成回應"""
    query = state["current_query"]
    context = state["injected_context"]

    system_prompt = """你是 TechAssist，一個具有記憶能力的企業助理。

你可以記住之前的對話和重要資訊，請基於提供的上下文給出連貫的回應。

如果用戶提到之前討論過的內容，請適當引用。"""

    messages = [SystemMessage(content=system_prompt)]

    if context:
        messages.append(SystemMessage(content=f"相關上下文：\n{context}"))

    messages.append(HumanMessage(content=query))

    response = llm.invoke(messages)

    # 更新短期記憶
    short_term_memory.add(HumanMessage(content=query))
    short_term_memory.add(AIMessage(content=response.content))

    return {"response": response.content}


def importance_evaluation_node(state: MemoryState) -> dict:
    """‹10› 重要性評估節點：決定是否需要長期記憶"""
    query = state["current_query"]
    response = state["response"]

    # 使用 LLM 評估對話重要性
    evaluation_prompt = f"""評估以下對話是否包含值得長期記憶的重要資訊：

用戶：{query}
AI：{response[:500]}

重要資訊包括：
- 用戶偏好
- 專案決策
- 技術選擇
- 業務規則
- 重要事實

只回答 "是" 或 "否"。"""

    result = llm.invoke([HumanMessage(content=evaluation_prompt)])
    should_memorize = "是" in result.content

    if should_memorize:
        print("  📌 標記為重要，將保存到長期記憶")

    return {"should_memorize": should_memorize}


def memory_consolidation_node(state: MemoryState) -> dict:
    """‹11› 記憶整合節點：保存重要資訊到長期記憶"""
    if not state["should_memorize"]:
        return {}

    query = state["current_query"]
    response = state["response"]
    session_id = state["session_id"]
    user_id = state["user_id"]

    # 生成記憶摘要
    summary_prompt = f"""請用一句話總結以下對話中的關鍵資訊（用於長期記憶）：

用戶：{query}
AI：{response[:500]}

摘要："""

    summary_result = llm.invoke([HumanMessage(content=summary_prompt)])
    memory_content = summary_result.content.strip()

    # 保存到長期記憶
    long_term_memory.add(
        content=memory_content,
        importance=0.7,
        metadata={
            "user_id": user_id,
            "session_id": session_id,
            "original_query": query[:100]
        }
    )

    # 更新會話記憶
    session = session_memory_store.get_or_create(session_id, user_id)
    session_memory_store.add_decision(session_id, memory_content)

    return {}


# ============================================================
# 6. 構建圖
# ============================================================

def build_memory_graph() -> StateGraph:
    """構建記憶模式圖"""
    graph = StateGraph(MemoryState)

    # 添加節點
    graph.add_node("inject_memory", memory_injection_node)
    graph.add_node("generate_response", response_generation_node)
    graph.add_node("evaluate_importance", importance_evaluation_node)
    graph.add_node("consolidate_memory", memory_consolidation_node)

    # 添加邊
    graph.add_edge(START, "inject_memory")
    graph.add_edge("inject_memory", "generate_response")
    graph.add_edge("generate_response", "evaluate_importance")
    graph.add_edge("evaluate_importance", "consolidate_memory")
    graph.add_edge("consolidate_memory", END)

    return graph.compile()


# ============================================================
# 7. 主程式
# ============================================================

def main():
    """執行記憶模式範例"""
    print("=" * 60)
    print("Chapter 8: 記憶模式 (The Memory Pattern)")
    print("=" * 60)

    # 構建圖
    app = build_memory_graph()

    # 預設一些長期記憶（模擬歷史）
    long_term_memory.add(
        "用戶偏好使用 Python 進行開發",
        importance=0.8,
        metadata={"type": "preference"}
    )
    long_term_memory.add(
        "專案使用 PostgreSQL 作為主資料庫",
        importance=0.9,
        metadata={"type": "decision"}
    )
    long_term_memory.add(
        "團隊決定採用微服務架構",
        importance=0.85,
        metadata={"type": "decision"}
    )

    # 模擬多輪對話
    user_id = "user_001"
    session_id = "session_001"

    conversations = [
        "我們專案現在需要添加一個新的服務，你有什麼建議？",
        "這個服務需要處理大量的數據查詢，效能很重要",
        "之前我們是怎麼決定架構的來著？",
        "好的，那就按照你的建議，使用 Redis 做快取吧",
    ]

    for i, query in enumerate(conversations, 1):
        print(f"\n{'='*60}")
        print(f"對話 {i}")
        print("=" * 60)
        print(f"👤 用戶：{query}")

        initial_state = {
            "messages": [],
            "user_id": user_id,
            "session_id": session_id,
            "current_query": query,
            "injected_context": None,
            "response": None,
            "should_memorize": False
        }

        result = app.invoke(initial_state)

        print(f"\n🤖 TechAssist：{result['response']}")

        if i < len(conversations):
            input("\n按 Enter 繼續下一輪對話...")

    # 顯示記憶狀態
    print("\n" + "=" * 60)
    print("記憶狀態摘要")
    print("=" * 60)
    print(f"短期記憶：{len(short_term_memory.messages)} 條訊息")
    print(f"長期記憶：{len(long_term_memory.memories)} 條記憶")

    if session_id in session_memory_store.sessions:
        session = session_memory_store.sessions[session_id]
        print(f"會話決策：{len(session.key_decisions)} 項")
        for d in session.key_decisions:
            print(f"  - {d}")


if __name__ == "__main__":
    main()
