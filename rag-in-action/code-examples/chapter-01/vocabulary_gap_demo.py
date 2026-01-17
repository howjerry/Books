"""
chapter-01/vocabulary_gap_demo.py

詞彙鴻溝問題演示

本模組展示傳統關鍵字搜尋的致命缺陷：當使用者和文件使用不同的詞彙
表達相同概念時，關鍵字搜尋將完全失效。

使用方式：
    python vocabulary_gap_demo.py

依賴安裝：
    pip install rank-bm25 jieba pandas rich
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import jieba
from rank_bm25 import BM25Okapi
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


@dataclass
class VocabularyGapExample:
    """詞彙鴻溝範例"""
    user_query: str           # 使用者查詢
    document: str             # 知識庫文件
    expected_match: bool      # 期望應該匹配
    reason: str               # 詞彙鴻溝原因


def create_vocabulary_gap_examples() -> List[VocabularyGapExample]:
    """
    建立詞彙鴻溝範例集

    這些範例展示了關鍵字搜尋在實際場景中的失敗案例。

    Returns:
        詞彙鴻溝範例列表
    """
    return [
        # 同義詞問題
        VocabularyGapExample(
            user_query="密碼忘記了",
            document="如何重設密碼？請點擊「忘記密碼」連結。",
            expected_match=True,
            reason="同義詞：使用者說「忘記」，文件說「重設」"
        ),
        VocabularyGapExample(
            user_query="我的帳號進不去",
            document="登入失敗時，請確認帳號密碼是否正確。",
            expected_match=True,
            reason="同義詞：「進不去」vs「登入失敗」"
        ),
        VocabularyGapExample(
            user_query="要怎麼付錢",
            document="我們支援信用卡、銀行轉帳及 PayPal 付款。",
            expected_match=True,
            reason="口語 vs 書面語：「付錢」vs「付款」"
        ),

        # 上下位詞問題
        VocabularyGapExample(
            user_query="可以用 Visa 嗎",
            document="支援信用卡付款（Visa、MasterCard、JCB）。",
            expected_match=True,
            reason="上下位詞：「Visa」是「信用卡」的下位詞"
        ),
        VocabularyGapExample(
            user_query="手機版閃退",
            document="App 閃退時，請嘗試重新安裝應用程式。",
            expected_match=True,
            reason="上下位詞：「手機版」vs「App」"
        ),

        # 縮寫與全稱
        VocabularyGapExample(
            user_query="2FA 怎麼開",
            document="如何啟用雙重驗證？進入安全性設定即可啟用。",
            expected_match=True,
            reason="縮寫：「2FA」vs「雙重驗證」"
        ),
        VocabularyGapExample(
            user_query="MFA 設定",
            document="多因素驗證可在帳戶安全性頁面啟用。",
            expected_match=True,
            reason="縮寫：「MFA」vs「多因素驗證」"
        ),

        # 否定式查詢
        VocabularyGapExample(
            user_query="檔案傳不上去",
            document="檔案上傳大小限制：免費版單檔上限 10MB。",
            expected_match=True,
            reason="否定式：使用者描述問題，文件描述規則"
        ),
        VocabularyGapExample(
            user_query="網頁打不開",
            document="網頁載入緩慢時，請清除瀏覽器快取。",
            expected_match=True,
            reason="否定式：「打不開」vs「載入緩慢」"
        ),

        # 意圖理解
        VocabularyGapExample(
            user_query="不想用了",
            document="如何取消訂閱？進入訂閱管理頁面。",
            expected_match=True,
            reason="意圖理解：「不想用了」暗示想取消訂閱"
        ),
        VocabularyGapExample(
            user_query="太貴了",
            document="如何降級訂閱方案？可在訂閱管理頁面更改。",
            expected_match=True,
            reason="意圖理解：「太貴」暗示想降級"
        ),

        # 多語言混用
        VocabularyGapExample(
            user_query="login 不了",
            document="登入失敗時，請確認帳號密碼是否正確。",
            expected_match=True,
            reason="多語言：英文「login」vs 中文「登入」"
        ),
        VocabularyGapExample(
            user_query="export 資料",
            document="如何匯出資料？點擊設定圖示選擇匯出。",
            expected_match=True,
            reason="多語言：英文「export」vs 中文「匯出」"
        ),
    ]


def tokenize_chinese(text: str) -> List[str]:
    """中文分詞"""
    return list(jieba.cut(text))


def check_keyword_overlap(query: str, document: str) -> Tuple[float, List[str]]:
    """
    檢查查詢與文件的關鍵字重疊程度

    Args:
        query: 查詢字串
        document: 文件字串

    Returns:
        (重疊率, 重疊詞彙列表)
    """
    query_tokens = set(tokenize_chinese(query))
    doc_tokens = set(tokenize_chinese(document))

    # 移除常見停用詞
    stopwords = {'的', '是', '了', '嗎', '？', '。', '，', '、', '請', '如何'}
    query_tokens = query_tokens - stopwords
    doc_tokens = doc_tokens - stopwords

    overlap = query_tokens & doc_tokens
    overlap_rate = len(overlap) / len(query_tokens) if query_tokens else 0

    return overlap_rate, list(overlap)


def run_bm25_search(
    query: str,
    documents: List[str]
) -> List[Tuple[int, float, str]]:
    """
    執行 BM25 搜尋

    Args:
        query: 查詢
        documents: 文件列表

    Returns:
        [(文件索引, 分數, 文件內容), ...]
    """
    tokenized_docs = [tokenize_chinese(doc) for doc in documents]
    bm25 = BM25Okapi(tokenized_docs)

    query_tokens = tokenize_chinese(query)
    scores = bm25.get_scores(query_tokens)

    results = [(i, score, doc) for i, (score, doc) in enumerate(zip(scores, documents))]
    results.sort(key=lambda x: x[1], reverse=True)

    return results


def analyze_vocabulary_gap():
    """分析詞彙鴻溝問題"""

    console.print("\n")
    console.print(Panel(
        "[bold]詞彙鴻溝問題分析[/bold]\n\n"
        "當使用者和知識庫使用不同的詞彙表達相同的概念時，\n"
        "傳統的關鍵字搜尋將無法找到正確的答案。\n\n"
        "這是 RAG 系統需要使用語義搜尋的核心原因。",
        title="Vocabulary Gap",
        border_style="blue"
    ))

    examples = create_vocabulary_gap_examples()

    # 統計表
    table = Table(title="詞彙鴻溝案例分析", box=box.ROUNDED)
    table.add_column("查詢", style="cyan", width=20)
    table.add_column("文件片段", style="white", width=30)
    table.add_column("重疊率", style="magenta", width=10)
    table.add_column("匹配詞", style="green", width=15)
    table.add_column("問題類型", style="yellow", width=25)

    failed_count = 0
    total_count = len(examples)

    for example in examples:
        overlap_rate, overlap_words = check_keyword_overlap(
            example.user_query,
            example.document
        )

        # 判斷搜尋是否會失敗（重疊率低於 30% 視為失敗）
        search_failed = overlap_rate < 0.3
        if search_failed:
            failed_count += 1

        rate_str = f"{overlap_rate:.0%}"
        if search_failed:
            rate_str = f"[red]{rate_str}[/red]"
        else:
            rate_str = f"[green]{rate_str}[/green]"

        matched_str = ", ".join(overlap_words) if overlap_words else "[red]無[/red]"

        table.add_row(
            example.user_query,
            example.document[:28] + "...",
            rate_str,
            matched_str,
            example.reason
        )

    console.print(table)

    # 總結
    failure_rate = failed_count / total_count
    console.print(f"\n[bold]統計結果：[/bold]")
    console.print(f"  總案例數：{total_count}")
    console.print(f"  搜尋失敗：[red]{failed_count}[/red] ({failure_rate:.0%})")
    console.print(f"  搜尋成功：[green]{total_count - failed_count}[/green] ({1-failure_rate:.0%})")


def demonstrate_search_failure():
    """展示搜尋失敗案例"""

    console.print("\n")
    console.print(Panel(
        "[bold]實際搜尋測試[/bold]\n\n"
        "使用 BM25 演算法對詞彙鴻溝案例進行實際搜尋，\n"
        "觀察關鍵字搜尋在語義理解上的侷限性。",
        title="Search Demo",
        border_style="yellow"
    ))

    # 建立小型知識庫
    knowledge_base = [
        "如何重設密碼？請點擊登入頁面的「忘記密碼」連結。",
        "如何升級訂閱方案？登入後進入「訂閱管理」頁面。",
        "支援信用卡付款（Visa、MasterCard、JCB）。",
        "如何啟用雙重驗證？進入「安全性」設定。",
        "App 閃退時，請嘗試重新安裝應用程式。",
        "檔案上傳大小限制：免費版單檔上限 10MB。",
        "如何匯出資料？點擊設定圖示選擇匯出格式。",
        "如何取消訂閱？進入訂閱管理頁面操作。",
    ]

    # 測試查詢
    test_cases = [
        ("密碼忘記了", 0, "詞彙鴻溝：「忘記」vs「重設」"),
        ("要怎麼付錢", 2, "口語 vs 書面語"),
        ("2FA 怎麼開", 3, "縮寫問題"),
        ("手機版閃退", 4, "「手機版」vs「App」"),
        ("不想用了", 7, "意圖理解"),
    ]

    for query, expected_idx, issue in test_cases:
        console.print(f"\n[bold cyan]查詢：[/bold cyan]{query}")
        console.print(f"[dim]問題類型：{issue}[/dim]")
        console.print(f"[dim]期望答案：{knowledge_base[expected_idx][:40]}...[/dim]")

        results = run_bm25_search(query, knowledge_base)

        # 顯示前 3 名結果
        console.print("\n[bold]BM25 搜尋結果：[/bold]")
        for rank, (idx, score, doc) in enumerate(results[:3], 1):
            if score > 0:
                if idx == expected_idx:
                    console.print(f"  {rank}. [green]✓ {score:.2f}[/green] - {doc[:50]}...")
                else:
                    console.print(f"  {rank}. [yellow]{score:.2f}[/yellow] - {doc[:50]}...")
            else:
                console.print(f"  {rank}. [red]0.00[/red] - {doc[:50]}...")

        # 檢查是否找到正確答案
        top_result_idx = results[0][0]
        if top_result_idx != expected_idx:
            console.print("[red]  ✗ 未找到正確答案[/red]")


def show_statistics():
    """顯示詞彙鴻溝問題的統計數據"""

    console.print("\n")
    console.print(Panel(
        "[bold]詞彙鴻溝問題的普遍性[/bold]\n\n"
        "根據資訊檢索研究，在企業知識庫場景中，\n"
        "約 40-60% 的搜尋失敗是由詞彙鴻溝造成的。",
        title="Statistics",
        border_style="green"
    ))

    stats_table = Table(title="詞彙鴻溝問題分類統計", box=box.SIMPLE)
    stats_table.add_column("問題類型", style="cyan")
    stats_table.add_column("佔比", style="magenta")
    stats_table.add_column("範例", style="white")

    stats = [
        ("同義詞", "25-30%", "「忘記」vs「重設」、「付錢」vs「付款」"),
        ("上下位詞", "15-20%", "「Visa」vs「信用卡」、「App」vs「手機版」"),
        ("縮寫/全稱", "10-15%", "「2FA」vs「雙重驗證」、「API」vs「程式介面」"),
        ("口語/書面語", "15-20%", "「進不去」vs「登入失敗」"),
        ("意圖理解", "10-15%", "「太貴了」暗示「降級方案」"),
        ("多語言混用", "5-10%", "「login」vs「登入」、「export」vs「匯出」"),
    ]

    for problem_type, percentage, example in stats:
        stats_table.add_row(problem_type, percentage, example)

    console.print(stats_table)


def main():
    """主程式"""

    console.print("\n[bold blue]═══════════════════════════════════════════════════════[/bold blue]")
    console.print("[bold blue]           詞彙鴻溝（Vocabulary Gap）問題演示           [/bold blue]")
    console.print("[bold blue]═══════════════════════════════════════════════════════[/bold blue]")

    # 1. 分析詞彙鴻溝案例
    analyze_vocabulary_gap()

    # 2. 展示實際搜尋失敗
    demonstrate_search_failure()

    # 3. 顯示統計數據
    show_statistics()

    # 結論
    console.print("\n")
    console.print(Panel(
        "[bold]結論[/bold]\n\n"
        "傳統關鍵字搜尋依賴精確的詞彙匹配，\n"
        "無法理解詞彙背後的語義。\n\n"
        "這正是我們需要引入 [bold cyan]語義搜尋[/bold cyan] 的原因——\n"
        "透過 Embedding 技術將文字轉換為向量，\n"
        "讓搜尋系統能夠理解「意思」而非只比對「字面」。\n\n"
        "[dim]下一章，我們將探索 Embedding 如何解決這個問題。[/dim]",
        title="下一步",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
