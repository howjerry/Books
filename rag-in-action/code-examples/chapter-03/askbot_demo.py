"""
chapter-03/askbot_demo.py

AskBot v1.0 - 企業客服知識庫 AI 助理

這是本書的核心專案第一版，整合了前面章節的所有技術：
- 語義搜尋（Embedding + Qdrant）
- RAG Pipeline（檢索 + 生成）
- Prompt Engineering

使用方式：
    python askbot_demo.py

依賴安裝：
    pip install sentence-transformers qdrant-client anthropic python-dotenv rich fastapi uvicorn

環境變數：
    ANTHROPIC_API_KEY=your_api_key
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import os
import json
from datetime import datetime

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()


@dataclass
class AskBotConfig:
    """AskBot 配置"""
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    llm_model: str = "claude-3-haiku-20240307"
    collection_name: str = "askbot_v1"
    top_k: int = 3
    score_threshold: float = 0.3
    max_tokens: int = 1024


@dataclass
class ConversationTurn:
    """對話輪次"""
    query: str
    answer: str
    sources: List[Dict]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AskBot:
    """
    AskBot v1.0 - 企業客服 AI 助理

    核心功能：
    1. 索引知識庫文件
    2. 語義檢索相關文件
    3. 使用 LLM 生成回答
    4. 追蹤對話歷史

    版本演進：
    - v1.0: 基礎 RAG Pipeline（本章）
    - v2.0: 加入 Hybrid Search 和 Re-Ranking（第 7 章）
    - v3.0: 生產級部署（第 10 章）
    - v4.0: 持續學習（第 13 章）
    """

    def __init__(self, config: Optional[AskBotConfig] = None):
        """初始化 AskBot"""
        self.config = config or AskBotConfig()
        self.conversation_history: List[ConversationTurn] = []

        self._init_components()

    def _init_components(self) -> None:
        """初始化各元件"""
        console.print("[bold blue]═══ AskBot v1.0 初始化 ═══[/bold blue]\n")

        # Embedding 模型
        console.print("載入 Embedding 模型...")
        self.embedding_model = SentenceTransformer(self.config.embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        console.print(f"  ✓ {self.config.embedding_model} (維度: {self.embedding_dim})")

        # 向量資料庫
        console.print("連接向量資料庫...")
        self.vector_db = QdrantClient(":memory:")
        self._ensure_collection()
        console.print("  ✓ Qdrant (記憶體模式)")

        # LLM
        console.print("初始化 LLM...")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("請設定 ANTHROPIC_API_KEY 環境變數")
        self.llm = anthropic.Anthropic(api_key=api_key)
        console.print(f"  ✓ {self.config.llm_model}")

        console.print("\n[green]✓ AskBot v1.0 就緒！[/green]\n")

    def _ensure_collection(self) -> None:
        """確保集合存在"""
        collections = self.vector_db.get_collections().collections
        if not any(c.name == self.config.collection_name for c in collections):
            self.vector_db.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )

    def load_knowledge_base(
        self,
        documents: List[str],
        metadata_list: Optional[List[Dict]] = None
    ) -> None:
        """
        載入知識庫

        Args:
            documents: 文件列表
            metadata_list: 元資料列表
        """
        if metadata_list is None:
            metadata_list = [{"source": "default"} for _ in documents]

        console.print(f"索引 {len(documents)} 份文件...")

        # 編碼文件
        embeddings = self.embedding_model.encode(
            documents,
            show_progress_bar=True
        )

        # 上傳到向量資料庫
        import uuid
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding.tolist(),
                payload={"content": doc, **meta}
            )
            for doc, embedding, meta in zip(documents, embeddings, metadata_list)
        ]

        self.vector_db.upsert(
            collection_name=self.config.collection_name,
            points=points
        )

        console.print(f"[green]✓ 知識庫載入完成（{len(documents)} 份文件）[/green]")

    def _retrieve(self, query: str) -> List[Dict]:
        """檢索相關文件"""
        query_vector = self.embedding_model.encode(query).tolist()

        results = self.vector_db.search(
            collection_name=self.config.collection_name,
            query_vector=query_vector,
            limit=self.config.top_k,
            score_threshold=self.config.score_threshold
        )

        return [
            {
                "id": str(r.id),
                "content": r.payload.get("content", ""),
                "score": r.score,
                "metadata": {k: v for k, v in r.payload.items() if k != "content"}
            }
            for r in results
        ]

    def _generate(self, query: str, context_docs: List[Dict]) -> str:
        """生成回答"""
        # 建構上下文
        context = "\n\n".join([
            f"[來源 {i+1}]（相關度：{doc['score']:.0%}）\n{doc['content']}"
            for i, doc in enumerate(context_docs)
        ])

        system_prompt = """你是 TechCorp 的 AI 客服助理「AskBot」。你的職責是根據知識庫內容，專業且友善地回答客戶問題。

回答準則：
1. 只根據提供的知識庫內容回答，絕對不要編造資訊
2. 使用清晰、有條理的語言
3. 如果知識庫沒有相關資訊，誠實告知並建議聯繫人工客服
4. 涉及重要操作時（如刪除帳戶），提醒注意事項
5. 保持專業但友善的語氣"""

        user_message = f"""知識庫內容：
{context}

---

客戶問題：{query}

請根據知識庫內容回答客戶的問題。"""

        response = self.llm.messages.create(
            model=self.config.llm_model,
            max_tokens=self.config.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        return response.content[0].text

    def ask(self, query: str) -> Dict:
        """
        處理使用者提問

        Args:
            query: 使用者問題

        Returns:
            包含答案和來源的字典
        """
        # 1. 檢索
        sources = self._retrieve(query)

        # 2. 生成
        if sources:
            answer = self._generate(query, sources)
        else:
            answer = "抱歉，我在知識庫中找不到與您問題相關的資訊。建議您聯繫人工客服：support@techcorp.com"

        # 3. 記錄對話
        turn = ConversationTurn(
            query=query,
            answer=answer,
            sources=sources
        )
        self.conversation_history.append(turn)

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "timestamp": turn.timestamp
        }

    def get_conversation_history(self) -> List[Dict]:
        """取得對話歷史"""
        return [
            {
                "query": turn.query,
                "answer": turn.answer,
                "sources_count": len(turn.sources),
                "timestamp": turn.timestamp
            }
            for turn in self.conversation_history
        ]


def get_techcorp_knowledge_base() -> List[str]:
    """取得 TechCorp 知識庫"""
    return [
        "如何重設密碼？請點擊登入頁面的「忘記密碼」連結，輸入您的電子郵件地址，系統將寄送重設連結。重設連結有效期為 24 小時。",
        "如何變更電子郵件地址？請登入後進入「帳戶設定」>「個人資料」，即可修改電子郵件。修改後需要重新驗證新郵件地址。",
        "如何啟用雙重驗證（2FA）？進入「帳戶設定」>「安全性」，點擊「啟用雙重驗證」。我們支援 Google Authenticator 和簡訊驗證兩種方式。",
        "如何刪除帳戶？請聯繫客服團隊 support@techcorp.com，我們將在 5 個工作日內處理。請注意，刪除後所有資料將無法恢復。",
        "支援哪些付款方式？我們支援信用卡（Visa、MasterCard、JCB）、銀行轉帳、PayPal 及 Apple Pay。企業客戶可申請月結付款。",
        "如何取消訂閱？進入「訂閱管理」>「取消訂閱」。取消後，您仍可使用服務至當期結束，不會退還已付款項。",
        "檔案上傳大小限制是多少？免費版單檔上限 10MB，專業版上限 100MB，企業版上限 500MB。所有方案都支援 PDF、Word、Excel 等常見格式。",
        "App 閃退怎麼辦？請確認 App 已更新至最新版本。若問題持續，請嘗試：1) 清除快取 2) 重新安裝 App 3) 聯繫技術支援。",
        "API 請求頻率限制是多少？免費版每分鐘 60 次，專業版 600 次，企業版 6000 次。超過限制會收到 429 錯誤。",
        "如何取得 API 金鑰？登入後進入「開發者設定」>「API 金鑰」，點擊「建立新金鑰」。請妥善保管金鑰，不要分享給他人。",
        "資料存放在哪裡？所有資料都儲存在 AWS 東京區域的伺服器，符合 ISO 27001 和 SOC 2 認證。我們提供每日自動備份。",
        "如何聯繫客服？您可以透過以下方式聯繫我們：1) Email: support@techcorp.com 2) 線上客服（週一至週五 9:00-18:00）3) 電話：02-1234-5678",
    ]


def display_response(response: Dict) -> None:
    """美化顯示回應"""
    # 答案
    console.print(Panel(
        response["answer"],
        title="[bold green]AskBot 回答[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))

    # 來源
    if response["sources"]:
        console.print("\n[bold cyan]參考來源：[/bold cyan]")
        for i, source in enumerate(response["sources"], 1):
            score = source["score"]
            color = "green" if score > 0.7 else "yellow" if score > 0.5 else "red"
            console.print(f"  [{color}]{i}. ({score:.0%})[/{color}] {source['content'][:50]}...")


def main():
    """主程式"""
    console.print("\n")
    console.print(Panel(
        "[bold]AskBot v1.0[/bold]\n\n"
        "企業客服知識庫 AI 助理\n\n"
        "[dim]基於 RAG 技術，整合語義搜尋與 LLM 生成[/dim]",
        title="TechCorp",
        border_style="blue",
        padding=(1, 4)
    ))

    try:
        # 初始化 AskBot
        bot = AskBot()

        # 載入知識庫
        kb = get_techcorp_knowledge_base()
        bot.load_knowledge_base(kb)

        # 測試問答
        console.print("\n[bold]═══ 功能測試 ═══[/bold]\n")

        test_questions = [
            "密碼忘記了怎麼辦？",
            "2FA 怎麼設定？",
            "你們支援哪些付款方式？",
            "API 有流量限制嗎？",
        ]

        for q in test_questions:
            console.print(f"\n[bold yellow]Q: {q}[/bold yellow]")
            response = bot.ask(q)
            display_response(response)

        # 互動模式
        console.print("\n[bold]═══ 互動模式 ═══[/bold]")
        console.print("[dim]輸入問題與 AskBot 對話，輸入 'quit' 退出[/dim]\n")

        while True:
            try:
                query = input("\n[您] > ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                if not query:
                    continue

                console.print()
                response = bot.ask(query)
                display_response(response)

            except KeyboardInterrupt:
                break

        # 顯示對話統計
        history = bot.get_conversation_history()
        console.print(f"\n[dim]本次對話：{len(history)} 輪[/dim]")

    except ValueError as e:
        console.print(f"\n[red]錯誤：{e}[/red]")
        console.print("[yellow]請確認已設定 ANTHROPIC_API_KEY 環境變數[/yellow]")

    console.print("\n[green]感謝使用 AskBot！[/green]\n")


if __name__ == "__main__":
    main()
