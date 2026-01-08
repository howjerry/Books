#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 12 章：基準測試全解析
HLE（Human-Like Evaluation）評測框架

這個模組實現了人類水準評測系統：
1. 多維度品質評估
2. LLM 驅動的評分
3. 標準測試套件
4. 結果彙總與分析

使用方式：
    from hle_evaluator import HLEEvaluator, HLETestSuite
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import asyncio
from datetime import datetime


# =============================================================================
# 品質評估維度
# =============================================================================

class QualityDimension(Enum):
    """
    品質評估維度

    ‹1› 六個核心維度，對應人類專家評估標準
    """
    ACCURACY = "accuracy"           # 準確性
    COMPLETENESS = "completeness"   # 完整性
    RELEVANCE = "relevance"         # 相關性
    COHERENCE = "coherence"         # 連貫性
    DEPTH = "depth"                 # 深度
    TIMELINESS = "timeliness"       # 時效性


# =============================================================================
# 評分結果
# =============================================================================

@dataclass
class HLEScore:
    """
    HLE 評分結果

    ‹2› 包含各維度分數和總分
    """
    dimension_scores: Dict[QualityDimension, float]
    overall_score: float
    confidence: float
    evaluator_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "dimensions": {
                dim.value: score
                for dim, score in self.dimension_scores.items()
            },
            "overall": self.overall_score,
            "confidence": self.confidence,
            "notes": self.evaluator_notes
        }

    @property
    def passed(self) -> bool:
        """是否通過（總分 >= 60）"""
        return self.overall_score >= 60


# =============================================================================
# 測試案例
# =============================================================================

@dataclass
class HLETestCase:
    """
    HLE 測試案例

    ‹3› 定義問題、參考答案和評估標準
    """
    test_id: str
    question: str
    category: str
    difficulty: str  # easy, medium, hard, expert
    reference_answer: str
    evaluation_criteria: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 可選的人類專家評分
    human_baseline: Optional[HLEScore] = None


# =============================================================================
# HLE 評測器
# =============================================================================

class HLEEvaluator:
    """
    HLE 評測器

    ‹4› 使用 LLM 模擬人類專家評估
    """

    # 評估提示模板
    EVALUATION_PROMPT = """你是一位嚴格的研究品質評估專家。請評估以下研究回答的品質。

## 問題
{question}

## 參考答案
{reference_answer}

## 待評估答案
{candidate_answer}

## 評估標準
{evaluation_criteria}

請從以下六個維度進行評分（0-100分）：

1. **準確性 (Accuracy)**：事實是否正確，無錯誤資訊
2. **完整性 (Completeness)**：是否涵蓋所有重要面向
3. **相關性 (Relevance)**：內容是否與問題高度相關
4. **連貫性 (Coherence)**：邏輯是否清晰，論述是否流暢
5. **深度 (Depth)**：分析是否深入，見解是否獨到
6. **時效性 (Timeliness)**：資訊是否最新，來源是否可靠

請以 JSON 格式回覆：
```json
{{
    "accuracy": <分數>,
    "completeness": <分數>,
    "relevance": <分數>,
    "coherence": <分數>,
    "depth": <分數>,
    "timeliness": <分數>,
    "overall": <總分>,
    "confidence": <評估信心 0-1>,
    "notes": "<評估說明>"
}}
```"""

    def __init__(self, llm_client):
        """
        初始化評測器

        Args:
            llm_client: LLM 客戶端（用於評估）
        """
        self.llm_client = llm_client

    async def evaluate(
        self,
        test_case: HLETestCase,
        candidate_answer: str
    ) -> HLEScore:
        """
        評估候選答案

        ‹5› 使用 LLM 進行多維度評估
        """
        # 構建評估提示
        prompt = self.EVALUATION_PROMPT.format(
            question=test_case.question,
            reference_answer=test_case.reference_answer,
            candidate_answer=candidate_answer,
            evaluation_criteria=json.dumps(
                test_case.evaluation_criteria,
                ensure_ascii=False,
                indent=2
            )
        )

        # 調用 LLM 評估
        response = await self.llm_client.generate(prompt)

        # 解析評估結果
        return self._parse_evaluation(response)

    def _parse_evaluation(self, response: str) -> HLEScore:
        """解析 LLM 評估回應"""
        try:
            # 提取 JSON 部分
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            json_str = response[json_start:json_end]

            data = json.loads(json_str)

            dimension_scores = {
                QualityDimension.ACCURACY: data.get("accuracy", 0),
                QualityDimension.COMPLETENESS: data.get("completeness", 0),
                QualityDimension.RELEVANCE: data.get("relevance", 0),
                QualityDimension.COHERENCE: data.get("coherence", 0),
                QualityDimension.DEPTH: data.get("depth", 0),
                QualityDimension.TIMELINESS: data.get("timeliness", 0),
            }

            return HLEScore(
                dimension_scores=dimension_scores,
                overall_score=data.get("overall", 0),
                confidence=data.get("confidence", 0.5),
                evaluator_notes=data.get("notes", "")
            )

        except (json.JSONDecodeError, KeyError) as e:
            # 解析失敗，返回零分
            return HLEScore(
                dimension_scores={dim: 0 for dim in QualityDimension},
                overall_score=0,
                confidence=0,
                evaluator_notes=f"評估解析失敗: {str(e)}"
            )


# =============================================================================
# 測試套件
# =============================================================================

class HLETestSuite:
    """
    HLE 測試套件

    包含多類型、多難度的測試案例
    """

    def __init__(self):
        self.test_cases: List[HLETestCase] = []
        self.categories: Dict[str, List[HLETestCase]] = {}

    def add_test_case(self, test_case: HLETestCase):
        """添加測試案例"""
        self.test_cases.append(test_case)

        # 按類別組織
        category = test_case.category
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(test_case)

    def get_by_difficulty(self, difficulty: str) -> List[HLETestCase]:
        """按難度獲取測試案例"""
        return [tc for tc in self.test_cases if tc.difficulty == difficulty]

    def get_by_category(self, category: str) -> List[HLETestCase]:
        """按類別獲取測試案例"""
        return self.categories.get(category, [])

    @classmethod
    def create_standard_suite(cls) -> "HLETestSuite":
        """
        創建標準測試套件

        包含五大類、四個難度等級的測試案例
        """
        suite = cls()

        # === 事實查詢類 ===
        suite.add_test_case(HLETestCase(
            test_id="FACT-001",
            question="2024 年全球半導體市場規模是多少？主要增長驅動力是什麼？",
            category="factual",
            difficulty="easy",
            reference_answer="""
            2024 年全球半導體市場規模約為 5,950 億美元，較 2023 年增長約 16%。

            主要增長驅動力包括：
            1. AI 晶片需求激增（GPU、NPU）
            2. 資料中心擴張
            3. 消費電子復甦
            4. 汽車電子化加速
            """,
            evaluation_criteria={
                "required_facts": [
                    "市場規模數字",
                    "增長率",
                    "至少 2 個驅動力"
                ],
                "accuracy_weight": 0.4,
                "completeness_weight": 0.3,
                "timeliness_weight": 0.3
            }
        ))

        suite.add_test_case(HLETestCase(
            test_id="FACT-002",
            question="GPT-4 是由哪家公司開發的？使用了什麼架構？",
            category="factual",
            difficulty="easy",
            reference_answer="""
            GPT-4 是由 OpenAI 開發的大型語言模型。

            架構特點：
            1. 基於 Transformer 解碼器架構
            2. 多模態能力（文字和圖像）
            3. 預估參數規模超過 1 兆
            4. 使用 RLHF 進行對齊訓練
            """,
            evaluation_criteria={
                "required_facts": ["OpenAI", "Transformer"],
                "accuracy_weight": 0.5,
                "completeness_weight": 0.5
            }
        ))

        # === 分析推理類 ===
        suite.add_test_case(HLETestCase(
            test_id="ANALYSIS-001",
            question="比較 OpenAI 和 Anthropic 在 AI 安全領域的研究方向差異。",
            category="analysis",
            difficulty="medium",
            reference_answer="""
            ## OpenAI 的 AI 安全方向
            - 重視能力與對齊的平衡發展
            - RLHF（人類反饋強化學習）為核心技術
            - 透過產品迭代收集真實世界數據
            - 較為激進的發布策略

            ## Anthropic 的 AI 安全方向
            - Constitutional AI 憲法式 AI
            - 強調可解釋性研究
            - 較為謹慎的發布策略
            - 關注長期 AI 風險

            ## 主要差異
            - OpenAI：市場先發優勢，但面臨更多安全質疑
            - Anthropic：較慢進入市場，但建立安全可靠形象
            """,
            evaluation_criteria={
                "required_aspects": [
                    "OpenAI 安全方向",
                    "Anthropic 安全方向",
                    "對比分析"
                ],
                "depth_weight": 0.4,
                "coherence_weight": 0.3,
                "accuracy_weight": 0.3
            }
        ))

        # === 綜合研究類 ===
        suite.add_test_case(HLETestCase(
            test_id="RESEARCH-001",
            question="請分析生成式 AI 對教育行業的潛在影響，包括機會、挑戰和建議。",
            category="research",
            difficulty="hard",
            reference_answer="""
            # 生成式 AI 對教育行業的影響分析

            ## 一、主要機會
            1. 個人化學習：AI 導師可根據學生程度調整教學
            2. 教師賦能：自動化批改作業、生成教學材料
            3. 教育公平：降低優質教育門檻

            ## 二、主要挑戰
            1. 學術誠信：學生可能過度依賴 AI
            2. 數位落差：技術資源不均
            3. 隱私與數據安全

            ## 三、政策建議
            1. 建立 AI 教育使用準則
            2. 投資教師 AI 素養培訓
            3. 發展 AI 輔助而非替代的教學模式
            """,
            evaluation_criteria={
                "required_sections": ["機會", "挑戰", "建議"],
                "depth_weight": 0.35,
                "completeness_weight": 0.35,
                "accuracy_weight": 0.3
            }
        ))

        # === 專家級問題 ===
        suite.add_test_case(HLETestCase(
            test_id="EXPERT-001",
            question="分析 Transformer 注意力機制的計算複雜度瓶頸及優化方案。",
            category="technical",
            difficulty="expert",
            reference_answer="""
            # Transformer 注意力機制優化分析

            ## 一、標準注意力的計算複雜度
            標準 Self-Attention 的計算複雜度為 O(n²d)
            主要瓶頸：QK^T 計算和記憶體需求

            ## 二、優化方案比較

            1. Flash Attention
               - 記憶體從 O(n²) 降至 O(n)
               - 無精度損失
               - 需要特定硬體支援

            2. Sparse Attention
               - 計算複雜度 O(n√n)
               - 可能丟失長程依賴

            3. Linear Attention
               - 計算複雜度 O(n)
               - 精度損失較明顯
            """,
            evaluation_criteria={
                "required_topics": [
                    "複雜度分析",
                    "至少 2 種優化方案"
                ],
                "requires_math": True,
                "accuracy_weight": 0.4,
                "depth_weight": 0.4,
                "completeness_weight": 0.2
            }
        ))

        return suite


# =============================================================================
# 評測執行器
# =============================================================================

class HLERunner:
    """
    HLE 評測執行器

    負責運行測試並收集結果
    """

    def __init__(
        self,
        agent,
        evaluator: HLEEvaluator,
        test_suite: HLETestSuite
    ):
        self.agent = agent
        self.evaluator = evaluator
        self.test_suite = test_suite
        self.results: List[Dict[str, Any]] = []

    async def run_all(self, concurrency: int = 5) -> Dict[str, Any]:
        """
        運行所有測試

        Args:
            concurrency: 並行執行數

        Returns:
            彙總結果
        """
        start_time = datetime.now()

        # ‹1› 分批執行測試
        test_cases = self.test_suite.test_cases
        batches = [
            test_cases[i:i+concurrency]
            for i in range(0, len(test_cases), concurrency)
        ]

        for batch in batches:
            tasks = [self._run_single(tc) for tc in batch]
            batch_results = await asyncio.gather(*tasks)
            self.results.extend(batch_results)

        end_time = datetime.now()

        # ‹2› 計算彙總統計
        return self._compute_summary(start_time, end_time)

    async def _run_single(self, test_case: HLETestCase) -> Dict[str, Any]:
        """運行單個測試案例"""
        import time

        start = time.time()

        try:
            # ‹3› 讓 Agent 回答問題
            agent_response = await self.agent.research(test_case.question)

            # ‹4› 評估答案
            score = await self.evaluator.evaluate(
                test_case,
                agent_response.answer if hasattr(agent_response, 'answer')
                else str(agent_response)
            )

            elapsed = time.time() - start

            return {
                "test_id": test_case.test_id,
                "category": test_case.category,
                "difficulty": test_case.difficulty,
                "score": score.to_dict(),
                "elapsed_seconds": elapsed,
                "status": "success"
            }

        except Exception as e:
            return {
                "test_id": test_case.test_id,
                "category": test_case.category,
                "difficulty": test_case.difficulty,
                "score": None,
                "error": str(e),
                "status": "error"
            }

    def _compute_summary(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """計算彙總統計"""
        successful = [r for r in self.results if r["status"] == "success"]

        # 各維度平均分
        dimension_averages = {}
        for dim in QualityDimension:
            scores = [
                r["score"]["dimensions"][dim.value]
                for r in successful
                if r["score"] and dim.value in r["score"]["dimensions"]
            ]
            dimension_averages[dim.value] = (
                sum(scores) / len(scores) if scores else 0
            )

        # 按類別統計
        category_scores = {}
        for category in self.test_suite.categories:
            cat_results = [
                r for r in successful
                if r["category"] == category
            ]
            if cat_results:
                category_scores[category] = {
                    "count": len(cat_results),
                    "average": sum(
                        r["score"]["overall"] for r in cat_results
                    ) / len(cat_results)
                }

        # 按難度統計
        difficulty_scores = {}
        for difficulty in ["easy", "medium", "hard", "expert"]:
            diff_results = [
                r for r in successful
                if r["difficulty"] == difficulty
            ]
            if diff_results:
                difficulty_scores[difficulty] = {
                    "count": len(diff_results),
                    "average": sum(
                        r["score"]["overall"] for r in diff_results
                    ) / len(diff_results)
                }

        return {
            "summary": {
                "total_tests": len(self.results),
                "successful": len(successful),
                "failed": len(self.results) - len(successful),
                "overall_average": (
                    sum(r["score"]["overall"] for r in successful) /
                    len(successful) if successful else 0
                ),
                "duration_seconds": (end_time - start_time).total_seconds()
            },
            "dimensions": dimension_averages,
            "by_category": category_scores,
            "by_difficulty": difficulty_scores,
            "detailed_results": self.results
        }


# =============================================================================
# 示範
# =============================================================================

def demo():
    """示範 HLE 評測"""
    print("=" * 60)
    print("  HLE 評測框架示範")
    print("=" * 60)

    # 創建標準測試套件
    suite = HLETestSuite.create_standard_suite()

    print(f"\n測試套件統計：")
    print(f"  總測試案例數：{len(suite.test_cases)}")
    print(f"  類別：{list(suite.categories.keys())}")

    print("\n測試案例預覽：")
    for tc in suite.test_cases[:3]:
        print(f"\n  [{tc.test_id}] {tc.difficulty}")
        print(f"  問題：{tc.question[:50]}...")
        print(f"  類別：{tc.category}")

    # 按難度統計
    print("\n難度分布：")
    for difficulty in ["easy", "medium", "hard", "expert"]:
        count = len(suite.get_by_difficulty(difficulty))
        print(f"  {difficulty}: {count} 題")


if __name__ == "__main__":
    demo()
