#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 12 章：基準測試全解析
GAIA 基準測試框架

這個模組實現了 GAIA 風格的測試：
1. 客觀可驗證的答案
2. 多步驟推理
3. 工具使用能力
4. 三級難度分層

使用方式：
    from gaia_benchmark import GAIABenchmark, GAIAQuestion
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
import re
import json
import asyncio
from datetime import datetime


# =============================================================================
# GAIA 難度等級
# =============================================================================

class GAIALevel(Enum):
    """GAIA 難度等級"""
    LEVEL_1 = 1  # 簡單：1-2 步驟
    LEVEL_2 = 2  # 中等：3-5 步驟，需要多工具
    LEVEL_3 = 3  # 困難：5+ 步驟，複雜推理


# =============================================================================
# GAIA 測試問題
# =============================================================================

@dataclass
class GAIAQuestion:
    """
    GAIA 測試問題

    ‹1› 強調答案的客觀性和可驗證性
    """
    question_id: str
    question: str
    level: GAIALevel
    expected_answer: str
    answer_type: str  # number, string, list, boolean

    # 驗證函數
    validator: Optional[Callable[[str, str], bool]] = None

    # 需要的能力
    required_capabilities: List[str] = field(default_factory=list)

    # 附件（某些問題需要處理文件）
    attachments: List[str] = field(default_factory=list)

    # 預期工具調用
    expected_tools: List[str] = field(default_factory=list)

    def validate_answer(self, candidate: str) -> bool:
        """
        驗證候選答案

        ‹2› 支援自定義驗證器和預設驗證
        """
        if self.validator:
            return self.validator(candidate, self.expected_answer)

        # 預設驗證邏輯
        return self._default_validate(candidate)

    def _default_validate(self, candidate: str) -> bool:
        """預設驗證：根據答案類型處理"""
        candidate = candidate.strip().lower()
        expected = self.expected_answer.strip().lower()

        if self.answer_type == "number":
            return self._validate_number(candidate, expected)
        elif self.answer_type == "boolean":
            return self._validate_boolean(candidate, expected)
        elif self.answer_type == "list":
            return self._validate_list(candidate, expected)
        else:
            return self._validate_string(candidate, expected)

    def _validate_number(self, candidate: str, expected: str) -> bool:
        """數字驗證：允許一定誤差"""
        try:
            # 提取數字
            cand_nums = re.findall(r"[\d.]+", candidate)
            exp_nums = re.findall(r"[\d.]+", expected)

            if not cand_nums or not exp_nums:
                return False

            cand_num = float(cand_nums[0])
            exp_num = float(exp_nums[0])

            # 允許 1% 誤差
            return abs(cand_num - exp_num) / max(abs(exp_num), 1e-10) < 0.01
        except (IndexError, ValueError):
            return False

    def _validate_boolean(self, candidate: str, expected: str) -> bool:
        """布爾驗證"""
        true_words = {"yes", "true", "是", "對", "正確"}
        false_words = {"no", "false", "否", "不對", "錯誤"}

        cand_bool = any(w in candidate for w in true_words)
        exp_bool = any(w in expected for w in true_words)

        if not cand_bool:
            cand_bool = not any(w in candidate for w in false_words)

        return cand_bool == exp_bool

    def _validate_list(self, candidate: str, expected: str) -> bool:
        """列表驗證：元素匹配"""
        try:
            # 嘗試解析 JSON 列表
            if "[" in candidate:
                cand_list = json.loads(candidate)
            else:
                cand_list = [x.strip() for x in candidate.split(",")]

            if "[" in expected:
                exp_list = json.loads(expected)
            else:
                exp_list = [x.strip() for x in expected.split(",")]

            # 標準化
            cand_set = {str(x).strip().lower() for x in cand_list}
            exp_set = {str(x).strip().lower() for x in exp_list}

            return cand_set == exp_set
        except Exception:
            return candidate == expected

    def _validate_string(self, candidate: str, expected: str) -> bool:
        """字串驗證：包含關鍵詞"""
        # 精確匹配
        if candidate == expected:
            return True

        # 關鍵詞匹配
        exp_words = set(expected.split())
        cand_words = set(candidate.split())

        # 至少 80% 關鍵詞匹配
        if not exp_words:
            return False
        overlap = len(exp_words & cand_words)
        return overlap / len(exp_words) >= 0.8


# =============================================================================
# GAIA 基準測試
# =============================================================================

class GAIABenchmark:
    """
    GAIA 基準測試執行器
    """

    def __init__(self):
        self.questions: List[GAIAQuestion] = []
        self.results: List[Dict[str, Any]] = []

    def load_questions(self, questions: List[GAIAQuestion]):
        """載入測試問題"""
        self.questions = questions

    def add_question(self, question: GAIAQuestion):
        """添加單個問題"""
        self.questions.append(question)

    @classmethod
    def create_sample_benchmark(cls) -> "GAIABenchmark":
        """
        創建示例基準測試

        ‹3› 包含三個難度等級的示例問題
        """
        benchmark = cls()

        # Level 1：簡單問題
        benchmark.add_question(GAIAQuestion(
            question_id="L1-001",
            question="蘋果公司的現任 CEO 是誰？",
            level=GAIALevel.LEVEL_1,
            expected_answer="Tim Cook",
            answer_type="string",
            required_capabilities=["web_search"],
            expected_tools=["search"]
        ))

        benchmark.add_question(GAIAQuestion(
            question_id="L1-002",
            question="Python 語言是在哪一年首次發布的？",
            level=GAIALevel.LEVEL_1,
            expected_answer="1991",
            answer_type="number",
            required_capabilities=["web_search"],
            expected_tools=["search"]
        ))

        benchmark.add_question(GAIAQuestion(
            question_id="L1-003",
            question="Linux 作業系統的創建者是誰？",
            level=GAIALevel.LEVEL_1,
            expected_answer="Linus Torvalds",
            answer_type="string",
            required_capabilities=["web_search"],
            expected_tools=["search"]
        ))

        # Level 2：中等問題
        benchmark.add_question(GAIAQuestion(
            question_id="L2-001",
            question="""
            計算以下公司的市值總和（以十億美元為單位，取整數）：
            - Apple
            - Microsoft
            - Google (Alphabet)

            請使用最新的股價數據。
            """,
            level=GAIALevel.LEVEL_2,
            expected_answer="8500",
            answer_type="number",
            required_capabilities=["web_search", "calculation"],
            expected_tools=["search", "calculator"],
            validator=lambda c, e: abs(
                float(re.findall(r"[\d.]+", c)[0]) -
                float(re.findall(r"[\d.]+", e)[0])
            ) < 1000  # 允許 1000 億美元誤差
        ))

        benchmark.add_question(GAIAQuestion(
            question_id="L2-002",
            question="""
            列出 2024 年 AI 領域獲得最多風險投資的前 3 家公司
            （按融資金額排序）。
            """,
            level=GAIALevel.LEVEL_2,
            expected_answer="OpenAI, Anthropic, xAI",
            answer_type="list",
            required_capabilities=["web_search", "data_extraction"],
            expected_tools=["search", "browser"]
        ))

        # Level 3：困難問題
        benchmark.add_question(GAIAQuestion(
            question_id="L3-001",
            question="""
            假設你是一家 AI 創業公司的 CFO，公司目前的數據如下：
            - 月營收：$500,000
            - 月增長率：15%
            - 營運成本：$400,000/月
            - 現金儲備：$2,000,000

            問題：在不進行裁員的情況下，公司需要多少個月才能達到盈虧平衡？
            假設成本保持不變，營收按月複利增長。
            """,
            level=GAIALevel.LEVEL_3,
            expected_answer="6",
            answer_type="number",
            required_capabilities=["calculation", "reasoning"],
            expected_tools=["calculator", "code_interpreter"],
            validator=lambda c, e: abs(
                int(re.findall(r"\d+", c)[0]) - int(e)
            ) <= 1  # 允許 1 個月誤差
        ))

        benchmark.add_question(GAIAQuestion(
            question_id="L3-002",
            question="""
            比較 GPT-4、Claude 3 和 Gemini Pro 在以下方面的差異：
            1. 上下文窗口大小
            2. 多模態能力
            3. 定價策略

            請提供具體數據和簡要分析。
            """,
            level=GAIALevel.LEVEL_3,
            expected_answer="structured_comparison",
            answer_type="string",
            required_capabilities=["web_search", "comparison", "analysis"],
            expected_tools=["search", "browser"],
            validator=lambda c, e: all(
                keyword in c.lower()
                for keyword in ["context", "multimodal", "pric"]
            )
        ))

        return benchmark

    async def run(
        self,
        agent,
        levels: Optional[List[GAIALevel]] = None
    ) -> Dict[str, Any]:
        """
        運行基準測試

        Args:
            agent: 待測試的 Agent
            levels: 要測試的難度等級（默認全部）

        Returns:
            測試結果
        """
        start_time = datetime.now()

        # 篩選問題
        questions = self.questions
        if levels:
            questions = [q for q in questions if q.level in levels]

        self.results = []

        for question in questions:
            result = await self._run_single(agent, question)
            self.results.append(result)

        end_time = datetime.now()

        return self._compute_summary(start_time, end_time)

    async def _run_single(
        self,
        agent,
        question: GAIAQuestion
    ) -> Dict[str, Any]:
        """運行單個問題"""
        import time

        start = time.time()

        try:
            # 獲取 Agent 回答
            response = await agent.research(question.question)
            answer = response.answer if hasattr(response, 'answer') else str(response)

            # 驗證答案
            is_correct = question.validate_answer(answer)

            # 檢查工具使用
            tools_used = getattr(response, 'tools_used', [])
            expected_tools_used = all(
                tool in tools_used
                for tool in question.expected_tools
            )

            elapsed = time.time() - start

            return {
                "question_id": question.question_id,
                "level": question.level.value,
                "is_correct": is_correct,
                "expected_answer": question.expected_answer,
                "actual_answer": answer,
                "expected_tools_used": expected_tools_used,
                "tools_used": tools_used,
                "elapsed_seconds": elapsed,
                "status": "success"
            }

        except Exception as e:
            return {
                "question_id": question.question_id,
                "level": question.level.value,
                "is_correct": False,
                "error": str(e),
                "status": "error"
            }

    def _compute_summary(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """計算彙總"""
        # 按等級統計
        level_stats = {}
        for level in GAIALevel:
            level_results = [
                r for r in self.results
                if r.get("level") == level.value
            ]
            if level_results:
                correct = sum(1 for r in level_results if r.get("is_correct"))
                level_stats[f"level_{level.value}"] = {
                    "total": len(level_results),
                    "correct": correct,
                    "accuracy": correct / len(level_results)
                }

        # 總體統計
        total = len(self.results)
        correct = sum(1 for r in self.results if r.get("is_correct"))
        errors = sum(1 for r in self.results if r.get("status") == "error")

        return {
            "summary": {
                "total_questions": total,
                "correct_answers": correct,
                "errors": errors,
                "overall_accuracy": correct / total if total else 0,
                "duration_seconds": (end_time - start_time).total_seconds()
            },
            "by_level": level_stats,
            "detailed_results": self.results
        }


# =============================================================================
# 示範
# =============================================================================

def demo():
    """示範 GAIA 基準測試"""
    print("=" * 60)
    print("  GAIA 基準測試示範")
    print("=" * 60)

    # 創建示例基準
    benchmark = GAIABenchmark.create_sample_benchmark()

    print(f"\n測試問題數量：{len(benchmark.questions)}")

    # 按難度統計
    print("\n難度分布：")
    for level in GAIALevel:
        count = len([q for q in benchmark.questions if q.level == level])
        print(f"  Level {level.value}: {count} 題")

    # 預覽問題
    print("\n問題預覽：")
    for q in benchmark.questions[:3]:
        print(f"\n  [{q.question_id}] Level {q.level.value}")
        print(f"  問題：{q.question[:60]}...")
        print(f"  答案類型：{q.answer_type}")
        print(f"  需要工具：{q.expected_tools}")

    # 測試驗證邏輯
    print("\n" + "-" * 40)
    print("驗證邏輯測試：")

    test_q = benchmark.questions[0]  # Tim Cook 問題
    test_cases = [
        ("Tim Cook", True),
        ("tim cook", True),
        ("Tim Cook is the CEO", True),
        ("Steve Jobs", False),
    ]

    for answer, expected in test_cases:
        result = test_q.validate_answer(answer)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{answer}' -> {result} (期望 {expected})")


if __name__ == "__main__":
    demo()
