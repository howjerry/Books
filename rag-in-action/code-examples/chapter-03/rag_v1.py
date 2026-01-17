"""
chapter-03/rag_v1.py

RAG Pipeline 第一版 - 最小可行版本

本模組實作一個完整的 RAG（Retrieval-Augmented Generation）系統，
整合語義搜尋與 LLM 生成，產出可靠的答案。

使用方式：
    python rag_v1.py

依賴安裝：
    pip install sentence-transformers qdrant-client anthropic python-dotenv rich

環境變數：
    ANTHROPIC_API_KEY=your_api_key
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import os
from datetime import datetime

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()
console = Console()


@dataclass
class RetrievedDocument:
    """檢索到的文件"""
    doc_id: str
    content: str
    score: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class RAGResponse:
    """RAG 系統回應"""
    answer: str
    sources: List[RetrievedDocument]
    query: str
    model: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RAGPipeline:
    """
    RAG Pipeline 第一版

    整合三個核心元件：
    1. Embedding 模型：將文字轉換為向量
    2. 向量資料庫：儲存和檢索文件向量
    3. LLM：根據檢索結果生成答案

    Attributes:
        embedding_model: Sentence Transformer 模型
        vector_db: Qdrant 客戶端
        llm_client: Anthropic API 客戶端
    """

    def __init__(
        self,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
        collection_name: str = "askbot_kb",
        llm_model: str = "claude-3-haiku-20240307",
        use_memory_db: bool = True
    ):
        """
        初始化 RAG Pipeline

        Args:
            embedding_model: Embedding 模型名稱
            collection_name: Qdrant 集合名稱
            llm_model: Claude 模型名稱
            use_memory_db: 是否使用記憶體模式
        """
        console.print("[yellow]正在初始化 RAG Pipeline...[/yellow]")

        # 1. 載入 Embedding 模型
        self.embedding_model = SentenceTransformer(embedding_model)  # ‹1›
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        console.print(f"  ✓ Embedding 模型載入完成（維度：{self.embedding_dim}）")

        # 2. 初始化向量資料庫
        if use_memory_db:
            self.vector_db = QdrantClient(":memory:")                # ‹2›
        else:
            self.vector_db = QdrantClient(host="localhost", port=6333)
        self.collection_name = collection_name
        self._ensure_collection()
        console.print("  ✓ 向量資料庫連接完成")

        # 3. 初始化 LLM 客戶端
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            console.print("[red]  ✗ 未設定 ANTHROPIC_API_KEY[/red]")
            raise ValueError("請設定 ANTHROPIC_API_KEY 環境變數")

        self.llm_client = anthropic.Anthropic(api_key=api_key)       # ‹3›
        self.llm_model = llm_model
        console.print(f"  ✓ LLM 客戶端初始化完成（模型：{llm_model}）")

        console.print("[green]✓ RAG Pipeline 初始化完成[/green]\n")

    def _ensure_collection(self) -> None:
        """確保向量集合存在"""
        collections = self.vector_db.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.vector_db.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )

    def index_documents(
        self,
        documents: List[str],
        metadata_list: Optional[List[Dict]] = None
    ) -> int:
        """
        索引文件到知識庫

        Args:
            documents: 文件列表
            metadata_list: 元資料列表

        Returns:
            成功索引的文件數量
        """
        if metadata_list is None:
            metadata_list = [{}] * len(documents)

        console.print(f"[yellow]正在索引 {len(documents)} 份文件...[/yellow]")

        # 批次編碼
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
                payload={
                    "content": doc,
                    "doc_index": i,
                    **meta
                }
            )
            for i, (doc, embedding, meta) in enumerate(
                zip(documents, embeddings, metadata_list)
            )
        ]

        self.vector_db.upsert(
            collection_name=self.collection_name,
            points=points
        )

        console.print(f"[green]✓ 成功索引 {len(documents)} 份文件[/green]")
        return len(documents)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.3
    ) -> List[RetrievedDocument]:
        """
        檢索相關文件

        Args:
            query: 使用者查詢
            top_k: 返回文件數量
            score_threshold: 最低相似度門檻

        Returns:
            檢索到的文件列表
        """
        # 編碼查詢
        query_vector = self.embedding_model.encode(query).tolist()   # ‹4›

        # 向量搜尋
        results = self.vector_db.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold
        )

        # 轉換為文件物件
        documents = [
            RetrievedDocument(
                doc_id=str(r.id),
                content=r.payload.get("content", ""),
                score=r.score,
                metadata={k: v for k, v in r.payload.items() if k != "content"}
            )
            for r in results
        ]

        return documents

    def generate(
        self,
        query: str,
        context_docs: List[RetrievedDocument],
        max_tokens: int = 1024
    ) -> str:
        """
        根據檢索結果生成答案

        Args:
            query: 使用者查詢
            context_docs: 檢索到的文件
            max_tokens: 最大輸出 token 數

        Returns:
            生成的答案
        """
        # 建構 Prompt
        context = "\n\n".join([
            f"[文件 {i+1}]（相關度：{doc.score:.2f}）\n{doc.content}"
            for i, doc in enumerate(context_docs)
        ])                                                           # ‹5›

        system_prompt = """你是一個專業的客服助理。請根據提供的參考文件回答使用者的問題。

規則：
1. 只使用參考文件中的資訊回答，不要編造
2. 如果參考文件沒有相關資訊，誠實告知「根據現有資料無法回答」
3. 回答要簡潔、直接、有幫助
4. 如果需要，可以引用文件來源"""

        user_prompt = f"""參考文件：
{context}

使用者問題：{query}

請根據上述參考文件回答使用者的問題。"""                            # ‹6›

        # 呼叫 LLM
        response = self.llm_client.messages.create(
            model=self.llm_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )                                                            # ‹7›

        return response.content[0].text

    def ask(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.3,
        max_tokens: int = 1024
    ) -> RAGResponse:
        """
        完整的 RAG 問答流程

        Args:
            query: 使用者查詢
            top_k: 檢索文件數量
            score_threshold: 相似度門檻
            max_tokens: 最大輸出 token 數

        Returns:
            RAG 回應（包含答案和來源）
        """
        # Step 1: Retrieve - 檢索相關文件
        retrieved_docs = self.retrieve(
            query,
            top_k=top_k,
            score_threshold=score_threshold
        )                                                            # ‹8›

        if not retrieved_docs:
            return RAGResponse(
                answer="抱歉，在知識庫中找不到與您問題相關的資訊。請嘗試換個方式描述問題。",
                sources=[],
                query=query,
                model=self.llm_model
            )

        # Step 2: Augment & Generate - 增強並生成答案
        answer = self.generate(
            query,
            retrieved_docs,
            max_tokens=max_tokens
        )                                                            # ‹9›

        return RAGResponse(
            answer=answer,
            sources=retrieved_docs,
            query=query,
            model=self.llm_model
        )


def create_sample_knowledge_base() -> List[str]:
    """建立範例知識庫"""
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


def display_response(response: RAGResponse) -> None:
    """美化顯示 RAG 回應"""
    # 顯示答案
    console.print(Panel(
        Markdown(response.answer),
        title="[bold green]回答[/bold green]",
        border_style="green"
    ))

    # 顯示來源
    if response.sources:
        console.print("\n[bold cyan]參考來源：[/bold cyan]")
        for i, doc in enumerate(response.sources, 1):
            score_color = "green" if doc.score > 0.7 else "yellow" if doc.score > 0.5 else "red"
            console.print(f"  [{score_color}]{i}. (相關度: {doc.score:.2f})[/{score_color}] {doc.content[:60]}...")


def main():
    """主程式：演示 RAG Pipeline"""

    console.print("\n[bold blue]═══════════════════════════════════════════════[/bold blue]")
    console.print("[bold blue]         AskBot v1.0 - RAG Pipeline 演示         [/bold blue]")
    console.print("[bold blue]═══════════════════════════════════════════════[/bold blue]\n")

    # 初始化 RAG Pipeline
    try:
        rag = RAGPipeline(use_memory_db=True)
    except ValueError as e:
        console.print(f"[red]初始化失敗：{e}[/red]")
        console.print("[yellow]提示：請設定 ANTHROPIC_API_KEY 環境變數[/yellow]")
        return

    # 索引知識庫
    documents = create_sample_knowledge_base()
    rag.index_documents(documents)

    # 測試問答
    test_queries = [
        "密碼忘記了怎麼辦",
        "2FA 怎麼設定",
        "可以用 Visa 付款嗎",
        "API 有使用限制嗎",
    ]

    for query in test_queries:
        console.print(f"\n[bold]使用者問題：{query}[/bold]")
        response = rag.ask(query, top_k=3)
        display_response(response)
        console.print("\n" + "─" * 50)

    # 互動模式
    console.print("\n[yellow]═══ 互動模式 ═══[/yellow]")
    console.print("[dim]輸入問題進行問答，輸入 'quit' 退出[/dim]\n")

    while True:
        try:
            query = input("您的問題 > ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            if not query:
                continue

            response = rag.ask(query)
            display_response(response)

        except KeyboardInterrupt:
            break

    console.print("\n[green]感謝使用 AskBot！[/green]")


if __name__ == "__main__":
    main()
