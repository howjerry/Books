"""
chapter-08/prompt_ab_testing.py

Prompt A/B 測試框架

本模組實作 Prompt 策略的 A/B 測試框架，
用於系統化評估不同 Prompt 的效果。

使用方式：
    from prompt_ab_testing import PromptABTester
    tester = PromptABTester(strategies)
    results = tester.run_test(test_cases)

依賴安裝：
    pip install anthropic pandas rich
"""

from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import time
import json
import os

from anthropic import Anthropic
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from prompt_templates import PromptStrategy, create_prompt, Context

console = Console()


@dataclass
class TestCase:
    """測試案例"""
    query: str
    contexts: List[Context]
    expected_keywords: List[str] = field(default_factory=list)
    expected_answer: str = ""
    category: str = "general"


@dataclass
class TestResult:
    """單一測試結果"""
    strategy: PromptStrategy
    test_case: TestCase
    answer: str
    latency_ms: float
    token_count: int
    keyword_coverage: float
    has_citation: bool
    hallucination_risk: float


@dataclass
class StrategyReport:
    """策略評估報告"""
    strategy: PromptStrategy
    total_tests: int
    avg_latency_ms: float
    avg_token_count: float
    avg_keyword_coverage: float
    citation_rate: float
    avg_hallucination_risk: float
    overall_score: float


class PromptABTester:
    """
    Prompt A/B 測試器

    對多種 Prompt 策略進行系統化評估。
    """

    def __init__(
        self,
        strategies: List[PromptStrategy] = None,
        api_key: str = None,
        model: str = "claude-3-haiku-20240307"
    ):
        """
        初始化測試器

        Args:
            strategies: 要測試的策略列表
            api_key: Anthropic API Key
            model: 使用的模型
        """
        self.strategies = strategies or list(PromptStrategy)
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model
        self.results: List[TestResult] = []

    def _call_llm(self, prompt: str) -> tuple:
        """
        呼叫 LLM

        Returns:
            (回答, 延遲ms, token數)
        """
        start = time.time()

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        latency = (time.time() - start) * 1000
        answer = response.content[0].text
        token_count = response.usage.output_tokens

        return answer, latency, token_count                            # ‹1›

    def _evaluate_answer(
        self,
        answer: str,
        test_case: TestCase
    ) -> Dict:
        """
        評估回答品質

        Args:
            answer: LLM 回答
            test_case: 測試案例

        Returns:
            評估指標字典
        """
        answer_lower = answer.lower()

        # 關鍵字覆蓋率
        if test_case.expected_keywords:
            matched = sum(
                1 for kw in test_case.expected_keywords
                if kw.lower() in answer_lower
            )
            keyword_coverage = matched / len(test_case.expected_keywords)
        else:
            keyword_coverage = 1.0

        # 是否有引用
        has_citation = any(
            marker in answer
            for marker in ["[來源", "[文件", "[參考", "來源 ", "文件 "]
        )                                                              # ‹2›

        # 幻覺風險（簡單檢查）
        hallucination_indicators = [
            "可能", "也許", "我認為", "通常", "一般來說",
            "根據官方", "專家表示", "研究顯示"
        ]
        indicator_count = sum(
            1 for ind in hallucination_indicators
            if ind in answer
        )
        hallucination_risk = min(indicator_count * 0.15, 1.0)

        return {
            "keyword_coverage": keyword_coverage,
            "has_citation": has_citation,
            "hallucination_risk": hallucination_risk
        }

    def run_single_test(
        self,
        strategy: PromptStrategy,
        test_case: TestCase
    ) -> TestResult:
        """
        執行單一測試

        Args:
            strategy: Prompt 策略
            test_case: 測試案例

        Returns:
            TestResult 測試結果
        """
        # 建立 Prompt
        prompt = create_prompt(strategy, test_case.query, test_case.contexts)

        # 呼叫 LLM
        answer, latency, token_count = self._call_llm(prompt)

        # 評估回答
        evaluation = self._evaluate_answer(answer, test_case)

        return TestResult(
            strategy=strategy,
            test_case=test_case,
            answer=answer,
            latency_ms=latency,
            token_count=token_count,
            keyword_coverage=evaluation["keyword_coverage"],
            has_citation=evaluation["has_citation"],
            hallucination_risk=evaluation["hallucination_risk"]
        )

    def run_test(
        self,
        test_cases: List[TestCase],
        show_progress: bool = True
    ) -> List[TestResult]:
        """
        執行完整 A/B 測試

        Args:
            test_cases: 測試案例列表
            show_progress: 是否顯示進度

        Returns:
            所有測試結果
        """
        total_tests = len(self.strategies) * len(test_cases)
        self.results = []

        with Progress() as progress:
            task = progress.add_task("A/B 測試進行中...", total=total_tests)

            for strategy in self.strategies:
                for test_case in test_cases:
                    result = self.run_single_test(strategy, test_case)
                    self.results.append(result)
                    progress.update(task, advance=1)

        return self.results                                            # ‹3›

    def generate_report(self) -> List[StrategyReport]:
        """
        生成策略評估報告

        Returns:
            各策略的評估報告
        """
        reports = []

        for strategy in self.strategies:
            strategy_results = [
                r for r in self.results
                if r.strategy == strategy
            ]

            if not strategy_results:
                continue

            # 計算各項指標
            avg_latency = sum(r.latency_ms for r in strategy_results) / len(strategy_results)
            avg_tokens = sum(r.token_count for r in strategy_results) / len(strategy_results)
            avg_keyword = sum(r.keyword_coverage for r in strategy_results) / len(strategy_results)
            citation_rate = sum(1 for r in strategy_results if r.has_citation) / len(strategy_results)
            avg_hallucination = sum(r.hallucination_risk for r in strategy_results) / len(strategy_results)

            # 計算綜合分數（可調整權重）
            overall_score = (
                avg_keyword * 0.3 +
                citation_rate * 0.25 +
                (1 - avg_hallucination) * 0.25 +
                (1 - min(avg_latency / 5000, 1)) * 0.1 +
                (1 - min(avg_tokens / 500, 1)) * 0.1
            )                                                          # ‹4›

            reports.append(StrategyReport(
                strategy=strategy,
                total_tests=len(strategy_results),
                avg_latency_ms=avg_latency,
                avg_token_count=avg_tokens,
                avg_keyword_coverage=avg_keyword,
                citation_rate=citation_rate,
                avg_hallucination_risk=avg_hallucination,
                overall_score=overall_score
            ))

        # 按綜合分數排序
        reports.sort(key=lambda r: r.overall_score, reverse=True)

        return reports

    def display_report(self, reports: List[StrategyReport] = None):
        """顯示評估報告"""
        if reports is None:
            reports = self.generate_report()

        table = Table(title="Prompt 策略 A/B 測試報告")
        table.add_column("策略", style="cyan")
        table.add_column("測試數", justify="right")
        table.add_column("延遲 (ms)", justify="right")
        table.add_column("Token 數", justify="right")
        table.add_column("關鍵字覆蓋", justify="right")
        table.add_column("引用率", justify="right")
        table.add_column("幻覺風險", justify="right")
        table.add_column("綜合分數", justify="right", style="green")

        for r in reports:
            table.add_row(
                r.strategy.value,
                str(r.total_tests),
                f"{r.avg_latency_ms:.0f}",
                f"{r.avg_token_count:.0f}",
                f"{r.avg_keyword_coverage:.1%}",
                f"{r.citation_rate:.1%}",
                f"{r.avg_hallucination_risk:.1%}",
                f"{r.overall_score:.3f}"
            )

        console.print(table)

        # 推薦最佳策略
        best = reports[0]
        console.print(f"\n[bold green]推薦策略：{best.strategy.value}[/bold green]")
        console.print(f"綜合分數：{best.overall_score:.3f}")

    def export_results(self, path: str = "ab_test_results.json"):
        """匯出測試結果"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "results": [
                {
                    "strategy": r.strategy.value,
                    "query": r.test_case.query,
                    "answer": r.answer,
                    "latency_ms": r.latency_ms,
                    "token_count": r.token_count,
                    "keyword_coverage": r.keyword_coverage,
                    "has_citation": r.has_citation,
                    "hallucination_risk": r.hallucination_risk
                }
                for r in self.results
            ]
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        console.print(f"[green]✓ 結果已匯出至 {path}[/green]")


def create_sample_test_cases() -> List[TestCase]:
    """建立範例測試案例"""
    return [
        TestCase(
            query="我忘記密碼了，該怎麼辦？",
            contexts=[
                Context(
                    content="如何重設密碼？請點擊登入頁面的「忘記密碼」連結，輸入您的電子郵件地址。",
                    source="FAQ-001"
                ),
                Context(
                    content="密碼重設連結有效期為 24 小時。如果連結過期，請重新申請。",
                    source="FAQ-002"
                ),
            ],
            expected_keywords=["忘記密碼", "連結", "電子郵件", "24 小時"],
            category="account"
        ),
        TestCase(
            query="你們支援哪些付款方式？",
            contexts=[
                Context(
                    content="支援的付款方式包括：信用卡（Visa、MasterCard）、銀行轉帳、PayPal。",
                    source="FAQ-010"
                ),
            ],
            expected_keywords=["信用卡", "Visa", "MasterCard", "PayPal"],
            category="payment"
        ),
        TestCase(
            query="如何取消訂閱？",
            contexts=[
                Context(
                    content="如何取消訂閱？進入「訂閱管理」>「取消訂閱」。取消後仍可使用至當期結束。",
                    source="FAQ-020"
                ),
            ],
            expected_keywords=["訂閱管理", "取消", "當期"],
            category="subscription"
        ),
    ]


def demo_ab_testing():
    """演示 A/B 測試"""
    console.print("\n[bold]═══ Prompt A/B 測試演示 ═══[/bold]\n")

    # 建立測試案例
    test_cases = create_sample_test_cases()
    console.print(f"測試案例數：{len(test_cases)}")

    # 選擇要測試的策略
    strategies = [
        PromptStrategy.BASIC,
        PromptStrategy.FORCED_CITATION,
        PromptStrategy.CHAIN_OF_THOUGHT,
    ]
    console.print(f"測試策略數：{len(strategies)}")
    console.print(f"總測試次數：{len(test_cases) * len(strategies)}\n")

    # 執行測試（需要 API Key）
    if os.getenv("ANTHROPIC_API_KEY"):
        tester = PromptABTester(strategies=strategies)
        tester.run_test(test_cases)

        # 顯示報告
        tester.display_report()

        # 匯出結果
        tester.export_results()
    else:
        console.print("[yellow]請設定 ANTHROPIC_API_KEY 環境變數以執行測試[/yellow]")


if __name__ == "__main__":
    demo_ab_testing()
