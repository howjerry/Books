"""
chapter-02/semantic_search_engine.py

語義搜尋引擎 - 使用 Embedding + Qdrant 向量資料庫

本模組實作一個完整的語義搜尋引擎，展示如何使用 Embedding 技術
解決關鍵字搜尋的詞彙鴻溝問題。

使用方式：
    python semantic_search_engine.py

依賴安裝：
    pip install sentence-transformers qdrant-client rich

需要先啟動 Qdrant：
    docker run -p 6333:6333 qdrant/qdrant
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import uuid
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@dataclass
class SemanticSearchResult:
    """語義搜尋結果"""
    doc_id: str
    content: str
    score: float
    metadata: Dict


class SemanticSearchEngine:
    """
    語義搜尋引擎

    結合 Sentence Transformers 和 Qdrant 向量資料庫，
    實現基於語義理解的文件檢索。

    Attributes:
        model: Embedding 模型
        client: Qdrant 客戶端
        collection_name: 向量集合名稱
    """

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        collection_name: str = "knowledge_base",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        use_memory: bool = True
    ):
        """
        初始化語義搜尋引擎

        Args:
            model_name: Sentence Transformer 模型名稱
            collection_name: Qdrant 集合名稱
            qdrant_host: Qdrant 伺服器位址
            qdrant_port: Qdrant 連接埠
            use_memory: 是否使用記憶體模式（不需要啟動 Qdrant 服務）
        """
        console.print(f"[yellow]載入 Embedding 模型：{model_name}[/yellow]")
        self.model = SentenceTransformer(model_name)              # ‹1›
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        console.print(f"[green]✓ 模型載入完成（維度：{self.embedding_dim}）[/green]")

        # 初始化 Qdrant 客戶端
        if use_memory:
            # 記憶體模式，適合開發和測試
            self.client = QdrantClient(":memory:")                # ‹2›
            console.print("[green]✓ Qdrant 記憶體模式啟動[/green]")
        else:
            # 連接到 Qdrant 服務
            self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
            console.print(f"[green]✓ 已連接 Qdrant：{qdrant_host}:{qdrant_port}[/green]")

        self.collection_name = collection_name
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保向量集合存在"""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE                      # ‹3›
                )
            )
            console.print(f"[green]✓ 建立集合：{self.collection_name}[/green]")
        else:
            console.print(f"[blue]ℹ 集合已存在：{self.collection_name}[/blue]")

    def index_documents(
        self,
        documents: List[str],
        metadata_list: List[Dict] = None
    ) -> None:
        """
        索引文件到向量資料庫

        Args:
            documents: 文件列表
            metadata_list: 每份文件的元資料（可選）
        """
        if metadata_list is None:
            metadata_list = [{}] * len(documents)

        console.print(f"[yellow]正在索引 {len(documents)} 份文件...[/yellow]")

        # 批次編碼文件
        embeddings = self.model.encode(
            documents,
            convert_to_numpy=True,
            show_progress_bar=True
        )                                                         # ‹4›

        # 準備 Qdrant 點
        points = []
        for i, (doc, embedding, metadata) in enumerate(
            zip(documents, embeddings, metadata_list)
        ):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding.tolist(),
                payload={
                    "content": doc,
                    "doc_index": i,
                    **metadata
                }                                                 # ‹5›
            )
            points.append(point)

        # 批次上傳到 Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )                                                         # ‹6›

        console.print(f"[green]✓ 索引完成：{len(documents)} 份文件[/green]")

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> List[SemanticSearchResult]:
        """
        執行語義搜尋

        Args:
            query: 搜尋查詢
            top_k: 返回結果數量
            score_threshold: 最低相似度門檻

        Returns:
            語義搜尋結果列表
        """
        # 將查詢轉換為向量
        query_vector = self.model.encode(query).tolist()          # ‹7›

        # 執行向量搜尋
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold
        )                                                         # ‹8›

        # 轉換為結果物件
        search_results = []
        for result in results:
            search_results.append(SemanticSearchResult(
                doc_id=str(result.id),
                content=result.payload.get("content", ""),
                score=result.score,
                metadata={
                    k: v for k, v in result.payload.items()
                    if k != "content"
                }
            ))

        return search_results

    def get_collection_info(self) -> Dict:
        """取得集合資訊"""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
        }


def create_sample_knowledge_base() -> List[str]:
    """建立範例知識庫（與第一章相同）"""
    return [
        # 帳戶相關
        "如何重設密碼？請點擊登入頁面的「忘記密碼」連結，輸入您的電子郵件地址，系統將寄送重設連結。",
        "如何變更電子郵件地址？請登入後進入「帳戶設定」>「個人資料」，即可修改電子郵件。",
        "如何啟用雙重驗證？進入「帳戶設定」>「安全性」，點擊「啟用雙重驗證」並按照指示操作。",
        "如何刪除帳戶？請聯繫客服團隊，我們將協助您處理帳戶刪除請求。請注意，刪除後資料無法恢復。",

        # 訂閱與付款
        "如何升級訂閱方案？登入後進入「訂閱管理」頁面，選擇想要的方案並完成付款即可升級。",
        "支援哪些付款方式？我們支援信用卡（Visa、MasterCard、JCB）、銀行轉帳及 PayPal。",
        "如何取消訂閱？進入「訂閱管理」>「取消訂閱」。取消後，您仍可使用服務至當期結束。",
        "發票何時寄送？發票將於付款成功後 3-5 個工作日內寄送至您的電子郵件信箱。",

        # 功能使用
        "如何匯出資料？點擊右上角的「設定」圖示，選擇「匯出資料」，可選擇 CSV 或 JSON 格式。",
        "如何建立團隊工作區？點擊左側選單的「+」按鈕，選擇「新增工作區」，輸入名稱後即可建立。",
        "檔案上傳大小限制是多少？免費版單檔上限 10MB，專業版上限 100MB，企業版無限制。",
        "如何與團隊成員共享文件？開啟文件後，點擊「分享」按鈕，輸入成員的電子郵件即可邀請。",

        # 技術問題
        "為什麼網頁載入很慢？請嘗試清除瀏覽器快取，或使用 Chrome、Firefox 等現代瀏覽器。",
        "App 閃退怎麼辦？請確認 App 已更新至最新版本，若問題持續，請嘗試重新安裝。",
        "API 請求頻率限制是多少？免費版每分鐘 60 次，專業版 600 次，企業版可依需求調整。",
        "如何取得 API 金鑰？登入後進入「開發者設定」>「API 金鑰」，點擊「建立新金鑰」。",
    ]


def display_results(query: str, results: List[SemanticSearchResult]) -> None:
    """以表格形式顯示搜尋結果"""
    table = Table(title=f"語義搜尋結果：「{query}」")
    table.add_column("排名", style="cyan", width=6)
    table.add_column("相似度", style="magenta", width=10)
    table.add_column("內容", style="white", width=70)

    for i, result in enumerate(results, 1):
        content = result.content[:65] + "..." if len(result.content) > 65 else result.content
        table.add_row(
            str(i),
            f"{result.score:.4f}",
            content
        )

    console.print(table)


def compare_bm25_vs_semantic():
    """比較 BM25 和語義搜尋的效果"""

    console.print("\n")
    console.print(Panel(
        "[bold]BM25 vs 語義搜尋 效果比較[/bold]\n\n"
        "使用相同的知識庫和查詢，比較兩種搜尋方法的結果。",
        title="對比實驗",
        border_style="blue"
    ))

    # 建立知識庫
    documents = create_sample_knowledge_base()

    # 初始化語義搜尋引擎（記憶體模式）
    engine = SemanticSearchEngine(use_memory=True)
    engine.index_documents(documents)

    # 詞彙鴻溝測試案例
    test_queries = [
        ("密碼忘記了", "精確答案在第一筆"),
        ("帳號進不去", "測試口語表達"),
        ("2FA 怎麼開", "測試縮寫"),
        ("手機版閃退", "測試同義詞"),
        ("不想用了", "測試意圖理解"),
        ("太貴了怎麼辦", "測試隱含需求"),
    ]

    for query, note in test_queries:
        console.print(f"\n[bold cyan]查詢：{query}[/bold cyan] [dim]({note})[/dim]")
        results = engine.search(query, top_k=3)
        display_results(query, results)


def main():
    """主程式"""

    console.print("\n[bold blue]════════════════════════════════════════════════[/bold blue]")
    console.print("[bold blue]              語義搜尋引擎演示                  [/bold blue]")
    console.print("[bold blue]════════════════════════════════════════════════[/bold blue]")

    # 執行對比實驗
    compare_bm25_vs_semantic()

    # 互動式搜尋（可選）
    console.print("\n[yellow]═══ 互動式搜尋 ═══[/yellow]")
    console.print("[dim]輸入查詢進行搜尋，輸入 'quit' 退出[/dim]\n")

    documents = create_sample_knowledge_base()
    engine = SemanticSearchEngine(use_memory=True)
    engine.index_documents(documents)

    while True:
        try:
            query = input("查詢 > ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            if not query:
                continue

            results = engine.search(query, top_k=3)
            display_results(query, results)

        except KeyboardInterrupt:
            break

    console.print("\n[green]感謝使用！[/green]")


if __name__ == "__main__":
    main()
