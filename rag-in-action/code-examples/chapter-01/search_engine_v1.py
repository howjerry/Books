"""
chapter-01/search_engine_v1.py

BM25 關鍵字搜尋引擎 - 第一版

本模組實作一個基礎的 BM25 搜尋引擎，用於展示傳統資訊檢索的工作原理與侷限性。

使用方式：
    python search_engine_v1.py

依賴安裝：
    pip install rank-bm25 jieba pandas rich
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import math
import jieba
from rank_bm25 import BM25Okapi
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class SearchResult:
    """搜尋結果資料結構"""
    doc_id: int
    content: str
    score: float
    matched_terms: List[str]


class BM25SearchEngine:
    """
    BM25 關鍵字搜尋引擎

    BM25 (Best Matching 25) 是一種基於機率的排序函數，
    廣泛應用於搜尋引擎中計算文件與查詢的相關性。

    核心公式：
    score(D, Q) = Σ IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))

    其中：
    - f(qi, D): 詞彙 qi 在文件 D 中的詞頻
    - |D|: 文件 D 的長度
    - avgdl: 所有文件的平均長度
    - k1: 詞頻飽和參數（通常 1.2 ~ 2.0）
    - b: 長度正規化參數（通常 0.75）

    Attributes:
        documents: 原始文件列表
        doc_ids: 文件 ID 列表
        tokenized_docs: 分詞後的文件列表
        bm25: BM25 索引物件

    Example:
        >>> engine = BM25SearchEngine(documents)
        >>> results = engine.search("如何重設密碼", top_k=5)
        >>> for r in results:
        ...     print(f"{r.score:.4f} - {r.content}")
    """

    def __init__(
        self,
        documents: List[str],
        doc_ids: Optional[List[int]] = None,
        k1: float = 1.5,
        b: float = 0.75
    ):
        """
        初始化 BM25 搜尋引擎

        Args:
            documents: 要索引的文件列表
            doc_ids: 文件 ID 列表（可選，預設使用索引）
            k1: 詞頻飽和參數，控制詞頻對分數的影響程度
            b: 長度正規化參數，控制文件長度對分數的影響程度
        """
        self.documents = documents                              # ‹1›
        self.doc_ids = doc_ids or list(range(len(documents)))
        self.k1 = k1
        self.b = b

        # 使用 jieba 進行中文分詞
        self.tokenized_docs = [
            list(jieba.cut(doc)) for doc in documents           # ‹2›
        ]

        # 建立 BM25 索引
        self.bm25 = BM25Okapi(
            self.tokenized_docs,
            k1=k1,
            b=b
        )                                                       # ‹3›

        console.print(f"[green]✓ 索引建立完成：{len(documents)} 份文件[/green]")

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> List[SearchResult]:
        """
        執行搜尋

        Args:
            query: 搜尋查詢字串
            top_k: 返回結果數量
            score_threshold: 最低分數門檻

        Returns:
            排序後的搜尋結果列表
        """
        # 對查詢進行分詞
        query_tokens = list(jieba.cut(query))                   # ‹4›

        # 計算每份文件的 BM25 分數
        scores = self.bm25.get_scores(query_tokens)             # ‹5›

        # 找出匹配的詞彙
        query_set = set(query_tokens)

        # 組合結果
        results = []
        for idx, (doc_id, doc, score) in enumerate(
            zip(self.doc_ids, self.documents, scores)
        ):
            if score > score_threshold:
                # 找出在該文件中實際匹配到的詞彙
                doc_tokens = set(self.tokenized_docs[idx])
                matched = list(query_set & doc_tokens)

                results.append(SearchResult(
                    doc_id=doc_id,
                    content=doc,
                    score=score,
                    matched_terms=matched
                ))

        # 按分數降序排序並取 top_k
        results.sort(key=lambda x: x.score, reverse=True)       # ‹6›
        return results[:top_k]

    def explain_score(self, query: str, doc_idx: int) -> Dict:
        """
        解釋特定文件的 BM25 分數計算過程

        Args:
            query: 搜尋查詢
            doc_idx: 文件索引

        Returns:
            包含分數分解的字典
        """
        query_tokens = list(jieba.cut(query))
        doc_tokens = self.tokenized_docs[doc_idx]

        # 計算平均文件長度
        avgdl = sum(len(d) for d in self.tokenized_docs) / len(self.tokenized_docs)

        explanation = {
            "query_tokens": query_tokens,
            "doc_length": len(doc_tokens),
            "avg_doc_length": avgdl,
            "k1": self.k1,
            "b": self.b,
            "term_scores": {}
        }

        total_score = 0
        for term in query_tokens:
            # 計算 IDF
            doc_freq = sum(1 for d in self.tokenized_docs if term in d)
            if doc_freq == 0:
                idf = 0
            else:
                n = len(self.tokenized_docs)
                idf = math.log((n - doc_freq + 0.5) / (doc_freq + 0.5) + 1)

            # 計算詞頻
            tf = doc_tokens.count(term)

            # 計算分數
            dl = len(doc_tokens)
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * dl / avgdl)
            term_score = idf * numerator / denominator if denominator > 0 else 0

            explanation["term_scores"][term] = {
                "tf": tf,
                "df": doc_freq,
                "idf": round(idf, 4),
                "score": round(term_score, 4)
            }
            total_score += term_score

        explanation["total_score"] = round(total_score, 4)
        return explanation


def create_sample_knowledge_base() -> List[str]:
    """
    建立範例知識庫 - 模擬 TechCorp 的客服文件

    Returns:
        客服常見問題文件列表
    """
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


def display_results(query: str, results: List[SearchResult]) -> None:
    """
    以表格形式顯示搜尋結果

    Args:
        query: 搜尋查詢
        results: 搜尋結果列表
    """
    table = Table(title=f"搜尋結果：「{query}」")
    table.add_column("排名", style="cyan", width=6)
    table.add_column("分數", style="magenta", width=8)
    table.add_column("匹配詞", style="green", width=20)
    table.add_column("內容", style="white", width=60)

    for i, result in enumerate(results, 1):
        matched = ", ".join(result.matched_terms) if result.matched_terms else "無"
        content = result.content[:55] + "..." if len(result.content) > 55 else result.content
        table.add_row(
            str(i),
            f"{result.score:.4f}",
            matched,
            content
        )

    console.print(table)


def main():
    """主程式：演示 BM25 搜尋引擎"""

    console.print("\n[bold blue]═══ BM25 關鍵字搜尋引擎演示 ═══[/bold blue]\n")

    # 建立知識庫
    documents = create_sample_knowledge_base()

    # 初始化搜尋引擎
    console.print("[yellow]正在建立搜尋索引...[/yellow]")
    engine = BM25SearchEngine(documents, k1=1.5, b=0.75)

    # 測試查詢
    test_queries = [
        "如何重設密碼",      # 精確匹配
        "密碼忘記了怎麼辦",  # 詞彙鴻溝問題
        "付款方式有哪些",    # 部分匹配
        "檔案太大無法上傳",  # 詞彙鴻溝問題
    ]

    for query in test_queries:
        console.print(f"\n[bold]查詢：{query}[/bold]")
        results = engine.search(query, top_k=3)

        if results:
            display_results(query, results)
        else:
            console.print("[red]沒有找到相關結果[/red]")

    # 展示分數計算過程
    console.print("\n[bold blue]═══ BM25 分數計算解析 ═══[/bold blue]\n")

    query = "如何重設密碼"
    explanation = engine.explain_score(query, 0)

    console.print(f"查詢：「{query}」")
    console.print(f"查詢分詞：{explanation['query_tokens']}")
    console.print(f"文件長度：{explanation['doc_length']} 詞")
    console.print(f"平均文件長度：{explanation['avg_doc_length']:.2f} 詞")
    console.print(f"參數 k1={explanation['k1']}, b={explanation['b']}")
    console.print("\n各詞彙分數：")

    for term, scores in explanation["term_scores"].items():
        console.print(
            f"  「{term}」: TF={scores['tf']}, "
            f"DF={scores['df']}, IDF={scores['idf']}, "
            f"得分={scores['score']}"
        )

    console.print(f"\n[green]總分：{explanation['total_score']}[/green]")


if __name__ == "__main__":
    main()
