# 第 12 章：基準測試全解析

> **本章目標**：深入理解深度研究代理人的評測方法論，掌握 HLE、GAIA、BrowseComp 等標準基準測試的設計原理與實作方式。

---

## 12.1 為什麼需要基準測試？

「你的 Agent 到底有多強？」這個看似簡單的問題，其實隱藏著巨大的複雜性。

在傳統軟體開發中，我們習慣用單元測試和整合測試來驗證功能正確性。但對於深度研究代理人，情況要複雜得多：

1. **任務多樣性**：研究問題涵蓋科技、醫學、法律等各個領域
2. **答案開放性**：同一個問題可能有多個合理答案
3. **過程不確定性**：解題路徑可能有多種選擇
4. **時間敏感性**：某些問題的答案會隨時間改變

讓我們看一個具體例子：

```
問題：2024 年諾貝爾物理學獎得主是誰？

可能的回答：
A. "John J. Hopfield 和 Geoffrey E. Hinton"（正確）
B. "Hopfield 和 Hinton 因為神經網路的貢獻獲獎"（正確但更詳細）
C. "2024 年諾貝爾物理學獎尚未頒發"（如果問題在頒獎前）
D. "Geoffrey Hinton"（部分正確）
```

你看，即使是這個看似簡單的事實查詢，評估正確性就需要考慮：
- 完整性（是否包含所有得主）
- 時效性（查詢時間點）
- 細節程度（是否需要獲獎原因）

這就是為什麼我們需要精心設計的基準測試——它們為我們提供了統一的評估標準和可比較的結果。

### 12.1.1 基準測試的三個層次

```
┌─────────────────────────────────────────────────────────────────┐
│                    基準測試金字塔                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    ┌─────────────┐                              │
│                    │ 綜合評測    │ ← 端到端任務完成度           │
│                    │ (End-to-End)│   如：完成研究報告           │
│                    └──────┬──────┘                              │
│                           │                                     │
│              ┌────────────┴────────────┐                        │
│              │     能力評測            │ ← 特定技能測試         │
│              │  (Capability Testing)   │   如：搜尋、推理、寫作 │
│              └────────────┬────────────┘                        │
│                           │                                     │
│    ┌──────────────────────┴──────────────────────┐              │
│    │            組件評測                          │              │
│    │       (Component Testing)                   │ ← 單一功能   │
│    └─────────────────────────────────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**組件評測**：測試單一功能
- 搜尋引擎召回率
- LLM 回答準確度
- 資訊抽取品質

**能力評測**：測試複合能力
- 多步驟推理
- 工具鏈整合
- 資訊綜合

**綜合評測**：測試完整任務
- 研究報告撰寫
- 複雜問題解答
- 長程任務完成

---

## 12.2 HLE：人類水準評測

HLE（Human-Like Evaluation）是一套模擬人類專家評估標準的測試方法。它的核心理念是：**一個好的研究代理人應該達到人類研究員的水準**。

### 12.2.1 HLE 的設計原則

```python
#!/usr/bin/env python3
"""
HLE 評測框架

設計原則：
1. 模擬人類專家的評估標準
2. 考慮答案的多面向品質
3. 支援主觀與客觀指標
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json


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
```

### 12.2.2 建立 HLE 測試集

一個好的 HLE 測試集應該涵蓋多種類型的問題：

```python
class HLETestSuite:
    """
    HLE 測試套件

    包含多類型、多難度的測試案例
    """

    def __init__(self):
        self.test_cases: List[HLETestCase] = []
        self.categories = {}

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

        # === 分析推理類 ===
        suite.add_test_case(HLETestCase(
            test_id="ANALYSIS-001",
            question="比較 OpenAI 和 Anthropic 在 AI 安全領域的研究方向差異，並分析其商業策略的影響。",
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

            ## 商業策略影響
            - OpenAI：市場先發優勢，但面臨更多安全質疑
            - Anthropic：較慢進入市場，但建立安全可靠形象
            """,
            evaluation_criteria={
                "required_aspects": [
                    "OpenAI 安全方向",
                    "Anthropic 安全方向",
                    "商業策略對比"
                ],
                "depth_weight": 0.4,
                "coherence_weight": 0.3,
                "accuracy_weight": 0.3
            }
        ))

        # === 綜合研究類 ===
        suite.add_test_case(HLETestCase(
            test_id="RESEARCH-001",
            question="請分析生成式 AI 對教育行業的潛在影響，包括機會、挑戰和建議。要求至少引用 3 個可靠來源。",
            category="research",
            difficulty="hard",
            reference_answer="""
            # 生成式 AI 對教育行業的影響分析

            ## 一、主要機會

            1. **個人化學習**
               - AI 導師可根據學生程度調整教學
               - 即時答疑，24/7 可用
               - 來源：UNESCO Education Report 2024

            2. **教師賦能**
               - 自動化批改作業
               - 生成教學材料
               - 來源：McKinsey Education Insights

            3. **教育公平**
               - 降低優質教育門檻
               - 跨語言學習支援

            ## 二、主要挑戰

            1. **學術誠信**
               - 學生可能過度依賴 AI
               - 作弊檢測困難
               - 來源：Nature Education

            2. **數位落差**
               - 技術資源不均
               - 師資培訓需求

            3. **隱私與數據安全**
               - 學生數據保護
               - 算法偏見風險

            ## 三、政策建議

            1. 建立 AI 教育使用準則
            2. 投資教師 AI 素養培訓
            3. 發展 AI 輔助而非替代的教學模式
            """,
            evaluation_criteria={
                "required_sections": ["機會", "挑戰", "建議"],
                "min_sources": 3,
                "depth_weight": 0.35,
                "completeness_weight": 0.35,
                "accuracy_weight": 0.3
            }
        ))

        # === 專家級問題 ===
        suite.add_test_case(HLETestCase(
            test_id="EXPERT-001",
            question="""
            請深入分析 Transformer 架構中注意力機制的計算複雜度瓶頸，
            並比較以下優化方案的優缺點：
            1. Flash Attention
            2. Sparse Attention
            3. Linear Attention

            要求包含數學推導和實際性能數據。
            """,
            category="technical",
            difficulty="expert",
            reference_answer="""
            # Transformer 注意力機制優化分析

            ## 一、標準注意力的計算複雜度

            標準 Self-Attention 的計算複雜度為 O(n²d)，其中：
            - n: 序列長度
            - d: 隱藏維度

            計算公式：
            ```
            Attention(Q,K,V) = softmax(QK^T / √d) V
            ```

            主要瓶頸：
            1. QK^T 計算：O(n²d)
            2. Softmax：O(n²)
            3. 注意力權重乘 V：O(n²d)
            4. 記憶體需求：O(n²) 儲存注意力矩陣

            ## 二、Flash Attention

            **原理**：利用 GPU 記憶體層次結構，分塊計算注意力

            **優點**：
            - 記憶體複雜度從 O(n²) 降至 O(n)
            - 實際訓練速度提升 2-4x
            - 無精度損失

            **缺點**：
            - 需要特定硬體支援（CUDA）
            - 實現複雜度高

            **性能數據**（A100 GPU）：
            - GPT-2 訓練：2.4x 加速
            - 長序列（16K）：3.5x 加速

            ## 三、Sparse Attention

            **原理**：只計算部分位置的注意力

            **變體**：
            - Local Attention：只關注鄰近位置
            - Strided Attention：間隔採樣
            - Combination：混合策略（如 Longformer）

            **優點**：
            - 計算複雜度降至 O(n√n) 或 O(n log n)
            - 可處理超長序列

            **缺點**：
            - 可能丟失長程依賴
            - 需要預定義稀疏模式
            - 某些任務精度下降

            ## 四、Linear Attention

            **原理**：利用核函數近似 Softmax

            ```
            Attention ≈ φ(Q) × (φ(K)^T × V)
            ```

            **優點**：
            - 計算複雜度 O(n)
            - 記憶體 O(n)

            **缺點**：
            - 精度損失明顯（某些任務）
            - 核函數選擇影響大

            ## 五、對比總結

            | 方法 | 時間複雜度 | 空間複雜度 | 精度保持 | 實現難度 |
            |------|-----------|-----------|----------|----------|
            | Standard | O(n²d) | O(n²) | 100% | 低 |
            | Flash Attention | O(n²d) | O(n) | 100% | 高 |
            | Sparse Attention | O(n√n) | O(n√n) | 95%+ | 中 |
            | Linear Attention | O(nd²) | O(nd) | 90%+ | 中 |
            """,
            evaluation_criteria={
                "required_topics": [
                    "複雜度分析",
                    "Flash Attention",
                    "Sparse Attention",
                    "Linear Attention",
                    "對比總結"
                ],
                "requires_math": True,
                "requires_data": True,
                "accuracy_weight": 0.4,
                "depth_weight": 0.4,
                "completeness_weight": 0.2
            }
        ))

        return suite
```

### 12.2.3 執行 HLE 評測

```python
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
        import asyncio
        from datetime import datetime

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
        start_time,
        end_time
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
```

---

## 12.3 GAIA 基準測試

GAIA（General AI Assistants）是 Meta AI 提出的一套測試 AI 助手通用能力的基準。它的設計目標是**測試 AI 在真實世界任務中的實用性**。

### 12.3.1 GAIA 的設計理念

```
┌─────────────────────────────────────────────────────────────────┐
│                    GAIA 基準測試特點                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. 問題來自真實世界                                       │  │
│  │     - 不是人工構造的謎題                                   │  │
│  │     - 需要多步驟推理和工具使用                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  2. 答案客觀明確                                           │  │
│  │     - 有且只有一個正確答案                                 │  │
│  │     - 可以自動化驗證                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  3. 人類容易，AI 困難                                       │  │
│  │     - 人類可以在幾分鐘內完成                               │  │
│  │     - 對 AI 需要複雜的推理和工具使用                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  4. 三級難度分層                                           │  │
│  │     - Level 1：簡單，少量步驟                               │  │
│  │     - Level 2：中等，需要多個工具                           │  │
│  │     - Level 3：困難，複雜推理鏈                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 12.3.2 GAIA 測試實作

```python
#!/usr/bin/env python3
"""
GAIA 基準測試框架

實現 GAIA 風格的測試，強調：
1. 客觀可驗證的答案
2. 多步驟推理
3. 工具使用能力
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
import re
import json


class GAIALevel(Enum):
    """GAIA 難度等級"""
    LEVEL_1 = 1  # 簡單：1-2 步驟
    LEVEL_2 = 2  # 中等：3-5 步驟，需要多工具
    LEVEL_3 = 3  # 困難：5+ 步驟，複雜推理


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
            cand_num = float(re.findall(r"[\d.]+", candidate)[0])
            exp_num = float(re.findall(r"[\d.]+", expected)[0])

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
            cand_list = json.loads(candidate) if "[" in candidate else candidate.split(",")
            exp_list = json.loads(expected) if "[" in expected else expected.split(",")

            # 標準化
            cand_set = {str(x).strip().lower() for x in cand_list}
            exp_set = {str(x).strip().lower() for x in exp_list}

            return cand_set == exp_set
        except:
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
        overlap = len(exp_words & cand_words)
        return overlap / len(exp_words) >= 0.8 if exp_words else False


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

    @classmethod
    def create_sample_benchmark(cls) -> "GAIABenchmark":
        """
        創建示例基準測試

        ‹3› 包含三個難度等級的示例問題
        """
        benchmark = cls()

        # Level 1：簡單問題
        benchmark.questions.append(GAIAQuestion(
            question_id="L1-001",
            question="蘋果公司的現任 CEO 是誰？",
            level=GAIALevel.LEVEL_1,
            expected_answer="Tim Cook",
            answer_type="string",
            required_capabilities=["web_search"],
            expected_tools=["search"]
        ))

        benchmark.questions.append(GAIAQuestion(
            question_id="L1-002",
            question="Python 語言是在哪一年首次發布的？",
            level=GAIALevel.LEVEL_1,
            expected_answer="1991",
            answer_type="number",
            required_capabilities=["web_search"],
            expected_tools=["search"]
        ))

        # Level 2：中等問題
        benchmark.questions.append(GAIAQuestion(
            question_id="L2-001",
            question="""
            計算以下公司的市值總和（以十億美元為單位，取整數）：
            - Apple
            - Microsoft
            - Google (Alphabet)

            請使用最新的股價數據。
            """,
            level=GAIALevel.LEVEL_2,
            expected_answer="8500",  # 大約值，會隨時間變化
            answer_type="number",
            required_capabilities=["web_search", "calculation"],
            expected_tools=["search", "calculator"],
            validator=lambda c, e: abs(
                float(re.findall(r"[\d.]+", c)[0]) -
                float(re.findall(r"[\d.]+", e)[0])
            ) < 1000  # 允許 1000 億美元誤差
        ))

        benchmark.questions.append(GAIAQuestion(
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
        benchmark.questions.append(GAIAQuestion(
            question_id="L3-001",
            question="""
            分析以下數據並回答：

            假設你是一家 AI 創業公司的 CFO，公司目前的數據如下：
            - 月營收：$500,000
            - 月增長率：15%
            - 營運成本：$400,000/月
            - 現金儲備：$2,000,000
            - 計劃融資：$10,000,000（預計 3 個月後到位）

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
        import time
        from datetime import datetime

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
        start_time,
        end_time
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
```

---

## 12.4 BrowseComp：網頁瀏覽能力測試

BrowseComp 是一套專門測試 AI 代理人網頁瀏覽和資訊抽取能力的基準測試。它模擬了真實世界中需要從網頁獲取資訊的場景。

### 12.4.1 BrowseComp 設計原理

```
┌─────────────────────────────────────────────────────────────────┐
│                  BrowseComp 能力分層                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Level 5: 多輪對話式瀏覽                                        │
│           ├── 記住上下文                                        │
│           └── 動態調整策略                                       │
│                                                                 │
│  Level 4: 多網站綜合                                            │
│           ├── 跨站比對                                          │
│           └── 資訊整合                                          │
│                                                                 │
│  Level 3: 複雜頁面處理                                          │
│           ├── 動態載入內容                                      │
│           ├── 表格/列表抽取                                     │
│           └── 表單填寫                                          │
│                                                                 │
│  Level 2: 基礎導航                                              │
│           ├── 連結點擊                                          │
│           ├── 搜尋框使用                                        │
│           └── 分頁處理                                          │
│                                                                 │
│  Level 1: 靜態頁面讀取                                          │
│           ├── 文本抽取                                          │
│           └── 基礎定位                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 12.4.2 BrowseComp 測試實作

```python
#!/usr/bin/env python3
"""
BrowseComp 基準測試框架

測試 AI 代理人的網頁瀏覽能力
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json


class BrowseTaskType(Enum):
    """瀏覽任務類型"""
    EXTRACT_INFO = "extract_info"       # 資訊抽取
    NAVIGATE = "navigate"               # 頁面導航
    FILL_FORM = "fill_form"            # 表單填寫
    COMPARE = "compare"                 # 多源比對
    MONITOR = "monitor"                 # 變化監控


@dataclass
class BrowseTask:
    """
    瀏覽任務定義
    """
    task_id: str
    task_type: BrowseTaskType
    description: str
    start_url: str
    expected_result: Dict[str, Any]
    difficulty: int  # 1-5

    # 任務約束
    max_steps: int = 10
    max_time_seconds: int = 60

    # 評估標準
    evaluation_criteria: Dict[str, float] = field(default_factory=dict)


class BrowseCompBenchmark:
    """
    BrowseComp 基準測試
    """

    def __init__(self):
        self.tasks: List[BrowseTask] = []
        self.results: List[Dict[str, Any]] = []

    @classmethod
    def create_standard_benchmark(cls) -> "BrowseCompBenchmark":
        """創建標準測試集"""
        benchmark = cls()

        # Level 1：靜態頁面讀取
        benchmark.tasks.append(BrowseTask(
            task_id="BC-L1-001",
            task_type=BrowseTaskType.EXTRACT_INFO,
            description="從維基百科獲取 Python 程式語言的創建者和首次發布年份",
            start_url="https://en.wikipedia.org/wiki/Python_(programming_language)",
            expected_result={
                "creator": "Guido van Rossum",
                "first_release": "1991"
            },
            difficulty=1,
            evaluation_criteria={
                "accuracy": 0.5,
                "completeness": 0.5
            }
        ))

        # Level 2：基礎導航
        benchmark.tasks.append(BrowseTask(
            task_id="BC-L2-001",
            task_type=BrowseTaskType.NAVIGATE,
            description="在 GitHub 上搜尋 'LangChain'，找到官方倉庫並獲取星標數量",
            start_url="https://github.com",
            expected_result={
                "repo_url": "https://github.com/langchain-ai/langchain",
                "stars": "dynamic"  # 動態值，只檢查格式
            },
            difficulty=2,
            max_steps=5,
            evaluation_criteria={
                "correct_repo": 0.6,
                "got_stars": 0.4
            }
        ))

        # Level 3：複雜頁面處理
        benchmark.tasks.append(BrowseTask(
            task_id="BC-L3-001",
            task_type=BrowseTaskType.EXTRACT_INFO,
            description="""
            從 arXiv 獲取最新的 10 篇 AI 相關論文：
            1. 訪問 arXiv
            2. 搜尋 'artificial intelligence'
            3. 抽取每篇論文的標題、作者、摘要
            """,
            start_url="https://arxiv.org",
            expected_result={
                "papers_count": 10,
                "required_fields": ["title", "authors", "abstract"]
            },
            difficulty=3,
            max_steps=15,
            max_time_seconds=120,
            evaluation_criteria={
                "correct_count": 0.3,
                "complete_fields": 0.4,
                "valid_data": 0.3
            }
        ))

        # Level 4：多網站綜合
        benchmark.tasks.append(BrowseTask(
            task_id="BC-L4-001",
            task_type=BrowseTaskType.COMPARE,
            description="""
            比較 iPhone 15 Pro 在以下三個網站的價格：
            1. Apple 官網
            2. Amazon
            3. Best Buy

            找出最低價格和價差。
            """,
            start_url="https://www.apple.com",
            expected_result={
                "sites_checked": 3,
                "price_comparison": "dynamic"
            },
            difficulty=4,
            max_steps=20,
            max_time_seconds=180,
            evaluation_criteria={
                "sites_coverage": 0.4,
                "price_accuracy": 0.4,
                "comparison_quality": 0.2
            }
        ))

        # Level 5：多輪對話式瀏覽
        benchmark.tasks.append(BrowseTask(
            task_id="BC-L5-001",
            task_type=BrowseTaskType.MONITOR,
            description="""
            監控並分析：
            1. 訪問 Hacker News
            2. 記錄當前首頁前 5 篇文章
            3. 等待 30 秒
            4. 再次檢查，報告變化
            5. 分析熱門趨勢
            """,
            start_url="https://news.ycombinator.com",
            expected_result={
                "initial_articles": 5,
                "tracked_changes": True,
                "trend_analysis": True
            },
            difficulty=5,
            max_steps=30,
            max_time_seconds=300,
            evaluation_criteria={
                "initial_capture": 0.3,
                "change_detection": 0.3,
                "analysis_quality": 0.4
            }
        ))

        return benchmark

    async def run(
        self,
        browser_agent,
        difficulty_filter: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        運行基準測試

        Args:
            browser_agent: 具備瀏覽能力的 Agent
            difficulty_filter: 難度篩選
        """
        import time
        from datetime import datetime

        start_time = datetime.now()

        tasks = self.tasks
        if difficulty_filter:
            tasks = [t for t in tasks if t.difficulty in difficulty_filter]

        self.results = []

        for task in tasks:
            result = await self._run_task(browser_agent, task)
            self.results.append(result)

        end_time = datetime.now()

        return self._compute_summary(start_time, end_time)

    async def _run_task(
        self,
        agent,
        task: BrowseTask
    ) -> Dict[str, Any]:
        """執行單個任務"""
        import time
        import asyncio

        start = time.time()

        try:
            # 設置超時
            result = await asyncio.wait_for(
                self._execute_browse_task(agent, task),
                timeout=task.max_time_seconds
            )

            elapsed = time.time() - start

            # 評估結果
            score = self._evaluate_result(task, result)

            return {
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "difficulty": task.difficulty,
                "result": result,
                "score": score,
                "elapsed_seconds": elapsed,
                "status": "success"
            }

        except asyncio.TimeoutError:
            return {
                "task_id": task.task_id,
                "difficulty": task.difficulty,
                "error": "Timeout",
                "status": "timeout"
            }
        except Exception as e:
            return {
                "task_id": task.task_id,
                "difficulty": task.difficulty,
                "error": str(e),
                "status": "error"
            }

    async def _execute_browse_task(
        self,
        agent,
        task: BrowseTask
    ) -> Dict[str, Any]:
        """執行瀏覽任務"""
        # 呼叫 Agent 的瀏覽方法
        response = await agent.browse(
            task=task.description,
            start_url=task.start_url,
            max_steps=task.max_steps
        )

        return response.data if hasattr(response, 'data') else response

    def _evaluate_result(
        self,
        task: BrowseTask,
        result: Dict[str, Any]
    ) -> float:
        """評估任務結果"""
        total_score = 0.0

        for criterion, weight in task.evaluation_criteria.items():
            criterion_score = self._evaluate_criterion(
                criterion,
                task.expected_result,
                result
            )
            total_score += criterion_score * weight

        return total_score

    def _evaluate_criterion(
        self,
        criterion: str,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> float:
        """評估單個標準"""
        # 簡化的評估邏輯
        if criterion == "accuracy":
            return self._check_accuracy(expected, actual)
        elif criterion == "completeness":
            return self._check_completeness(expected, actual)
        elif criterion == "correct_count":
            exp_count = expected.get("papers_count", 0)
            act_count = len(actual.get("papers", []))
            return min(act_count / exp_count, 1.0) if exp_count else 0
        else:
            # 默認：存在即給分
            return 1.0 if actual else 0.0

    def _check_accuracy(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> float:
        """檢查準確性"""
        matches = 0
        total = 0

        for key, exp_value in expected.items():
            if exp_value == "dynamic":
                # 動態值只檢查存在性
                if key in actual and actual[key]:
                    matches += 1
            else:
                act_value = actual.get(key)
                if str(act_value).lower() == str(exp_value).lower():
                    matches += 1
            total += 1

        return matches / total if total else 0

    def _check_completeness(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> float:
        """檢查完整性"""
        required = expected.get("required_fields", list(expected.keys()))
        present = sum(1 for f in required if f in actual and actual[f])
        return present / len(required) if required else 0

    def _compute_summary(
        self,
        start_time,
        end_time
    ) -> Dict[str, Any]:
        """計算彙總"""
        successful = [r for r in self.results if r.get("status") == "success"]

        # 按難度統計
        difficulty_stats = {}
        for diff in range(1, 6):
            diff_results = [
                r for r in successful
                if r.get("difficulty") == diff
            ]
            if diff_results:
                avg_score = sum(r["score"] for r in diff_results) / len(diff_results)
                difficulty_stats[f"level_{diff}"] = {
                    "count": len(diff_results),
                    "average_score": avg_score
                }

        return {
            "summary": {
                "total_tasks": len(self.results),
                "successful": len(successful),
                "timeouts": sum(1 for r in self.results if r.get("status") == "timeout"),
                "errors": sum(1 for r in self.results if r.get("status") == "error"),
                "average_score": (
                    sum(r["score"] for r in successful) / len(successful)
                    if successful else 0
                ),
                "duration_seconds": (end_time - start_time).total_seconds()
            },
            "by_difficulty": difficulty_stats,
            "detailed_results": self.results
        }
```

---

## 12.5 建構自己的評測系統

在實際項目中，你可能需要建構專門針對你的使用場景的評測系統。以下是一個完整的評測框架：

### 12.5.1 統一評測框架

```python
#!/usr/bin/env python3
"""
統一評測框架

整合 HLE、GAIA、BrowseComp 等多種基準測試
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
import json
import asyncio


class BenchmarkType(Enum):
    """基準測試類型"""
    HLE = "hle"
    GAIA = "gaia"
    BROWSECOMP = "browsecomp"
    CUSTOM = "custom"


@dataclass
class EvaluationConfig:
    """
    評測配置
    """
    benchmarks: List[BenchmarkType]
    agent_name: str
    agent_version: str

    # 執行選項
    parallel: bool = True
    max_concurrency: int = 5
    timeout_seconds: int = 300

    # 輸出選項
    output_dir: str = "./evaluation_results"
    save_detailed: bool = True

    # 過濾選項
    difficulty_filter: Optional[List[int]] = None
    category_filter: Optional[List[str]] = None


@dataclass
class EvaluationResult:
    """
    評測結果
    """
    benchmark_type: BenchmarkType
    summary: Dict[str, Any]
    detailed_results: List[Dict[str, Any]]
    started_at: datetime
    completed_at: datetime

    def to_dict(self) -> dict:
        return {
            "benchmark": self.benchmark_type.value,
            "summary": self.summary,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": (
                self.completed_at - self.started_at
            ).total_seconds(),
            "detailed_results": self.detailed_results
        }


class UnifiedEvaluator:
    """
    統一評測器

    ‹1› 整合多種基準測試
    ‹2› 提供統一的報告格式
    """

    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.results: Dict[BenchmarkType, EvaluationResult] = {}

    async def evaluate(self, agent) -> Dict[str, Any]:
        """
        執行完整評測

        Args:
            agent: 待評測的 Agent

        Returns:
            完整評測報告
        """
        overall_start = datetime.now()

        for benchmark_type in self.config.benchmarks:
            result = await self._run_benchmark(agent, benchmark_type)
            self.results[benchmark_type] = result

        overall_end = datetime.now()

        # 生成報告
        report = self._generate_report(overall_start, overall_end)

        # 保存結果
        if self.config.save_detailed:
            self._save_results(report)

        return report

    async def _run_benchmark(
        self,
        agent,
        benchmark_type: BenchmarkType
    ) -> EvaluationResult:
        """運行單個基準測試"""
        start = datetime.now()

        if benchmark_type == BenchmarkType.HLE:
            result = await self._run_hle(agent)
        elif benchmark_type == BenchmarkType.GAIA:
            result = await self._run_gaia(agent)
        elif benchmark_type == BenchmarkType.BROWSECOMP:
            result = await self._run_browsecomp(agent)
        else:
            result = {"error": "Unknown benchmark type"}

        end = datetime.now()

        return EvaluationResult(
            benchmark_type=benchmark_type,
            summary=result.get("summary", {}),
            detailed_results=result.get("detailed_results", []),
            started_at=start,
            completed_at=end
        )

    async def _run_hle(self, agent) -> Dict[str, Any]:
        """運行 HLE 評測"""
        # 創建測試套件和評測器
        suite = HLETestSuite.create_standard_suite()

        # 需要一個 LLM 客戶端來評估
        evaluator = HLEEvaluator(agent.llm_client)

        runner = HLERunner(agent, evaluator, suite)
        return await runner.run_all(self.config.max_concurrency)

    async def _run_gaia(self, agent) -> Dict[str, Any]:
        """運行 GAIA 評測"""
        benchmark = GAIABenchmark.create_sample_benchmark()

        levels = None
        if self.config.difficulty_filter:
            levels = [
                GAIALevel(d) for d in self.config.difficulty_filter
                if 1 <= d <= 3
            ]

        return await benchmark.run(agent, levels)

    async def _run_browsecomp(self, agent) -> Dict[str, Any]:
        """運行 BrowseComp 評測"""
        benchmark = BrowseCompBenchmark.create_standard_benchmark()
        return await benchmark.run(agent, self.config.difficulty_filter)

    def _generate_report(
        self,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """生成評測報告"""
        # 收集所有分數
        scores = {}
        for benchmark_type, result in self.results.items():
            if "overall_average" in result.summary:
                scores[benchmark_type.value] = result.summary["overall_average"]
            elif "overall_accuracy" in result.summary:
                scores[benchmark_type.value] = result.summary["overall_accuracy"]
            elif "average_score" in result.summary:
                scores[benchmark_type.value] = result.summary["average_score"]

        # 計算綜合分數
        overall_score = sum(scores.values()) / len(scores) if scores else 0

        return {
            "agent": {
                "name": self.config.agent_name,
                "version": self.config.agent_version
            },
            "evaluation": {
                "started_at": start.isoformat(),
                "completed_at": end.isoformat(),
                "duration_seconds": (end - start).total_seconds(),
                "benchmarks_run": [bt.value for bt in self.config.benchmarks]
            },
            "scores": {
                "overall": overall_score,
                "by_benchmark": scores
            },
            "detailed_results": {
                bt.value: result.to_dict()
                for bt, result in self.results.items()
            }
        }

    def _save_results(self, report: Dict[str, Any]):
        """保存評測結果"""
        import os

        os.makedirs(self.config.output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config.agent_name}_{timestamp}.json"
        filepath = os.path.join(self.config.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"評測結果已保存至: {filepath}")


# ===== 使用示例 =====

async def demo_evaluation():
    """示範評測流程"""
    from research_agent import ResearchAgent  # 假設存在

    # 創建評測配置
    config = EvaluationConfig(
        benchmarks=[
            BenchmarkType.HLE,
            BenchmarkType.GAIA,
            BenchmarkType.BROWSECOMP
        ],
        agent_name="MiroThinker",
        agent_version="1.0.0",
        parallel=True,
        max_concurrency=5,
        output_dir="./evaluation_results"
    )

    # 創建 Agent
    agent = ResearchAgent()

    # 創建評測器並執行
    evaluator = UnifiedEvaluator(config)
    report = await evaluator.evaluate(agent)

    # 輸出摘要
    print("\n" + "=" * 60)
    print("評測摘要")
    print("=" * 60)
    print(f"Agent: {report['agent']['name']} v{report['agent']['version']}")
    print(f"總體分數: {report['scores']['overall']:.2f}")
    print("\n各基準分數:")
    for benchmark, score in report['scores']['by_benchmark'].items():
        print(f"  - {benchmark}: {score:.2f}")
    print("=" * 60)

    return report
```

---

## 12.6 評測結果分析與優化

### 12.6.1 視覺化儀表板

```python
#!/usr/bin/env python3
"""
評測結果視覺化

生成評測報告的視覺化圖表
"""

from typing import Dict, List, Any
import json


class EvaluationDashboard:
    """
    評測儀表板

    生成 HTML 格式的視覺化報告
    """

    def __init__(self, report: Dict[str, Any]):
        self.report = report

    def generate_html(self) -> str:
        """生成 HTML 報告"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>評測報告 - {self.report['agent']['name']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px;
                 box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .score-big {{ font-size: 48px; font-weight: bold; }}
        .chart-container {{ height: 300px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; }}
        .pass {{ color: #28a745; }}
        .fail {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 評測報告</h1>
            <p>Agent: {self.report['agent']['name']} v{self.report['agent']['version']}</p>
            <p>評測時間: {self.report['evaluation']['completed_at']}</p>
        </div>

        <div class="grid">
            <div class="card">
                <h2>總體分數</h2>
                <div class="score-big">{self.report['scores']['overall']:.1f}%</div>
            </div>

            <div class="card">
                <h2>各基準分數</h2>
                <div class="chart-container">
                    <canvas id="benchmarkChart"></canvas>
                </div>
            </div>
        </div>

        {self._generate_detailed_tables()}

    </div>

    <script>
        {self._generate_chart_script()}
    </script>
</body>
</html>
"""

    def _generate_detailed_tables(self) -> str:
        """生成詳細結果表格"""
        tables = []

        for benchmark, data in self.report.get('detailed_results', {}).items():
            results = data.get('detailed_results', [])
            if not results:
                continue

            rows = ""
            for r in results[:20]:  # 限制顯示數量
                status = "pass" if r.get('is_correct') or r.get('status') == 'success' else "fail"
                score = r.get('score', {})
                if isinstance(score, dict):
                    score_display = f"{score.get('overall', 0):.1f}"
                else:
                    score_display = f"{score:.1f}" if score else "N/A"

                rows += f"""
                <tr>
                    <td>{r.get('test_id', r.get('task_id', r.get('question_id', 'N/A')))}</td>
                    <td>{r.get('difficulty', r.get('level', 'N/A'))}</td>
                    <td>{score_display}</td>
                    <td class="{status}">{'✓' if status == 'pass' else '✗'}</td>
                </tr>
                """

            tables.append(f"""
            <div class="card">
                <h2>{benchmark.upper()} 詳細結果</h2>
                <table>
                    <thead>
                        <tr>
                            <th>測試 ID</th>
                            <th>難度</th>
                            <th>分數</th>
                            <th>狀態</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
            """)

        return "\n".join(tables)

    def _generate_chart_script(self) -> str:
        """生成圖表腳本"""
        benchmarks = list(self.report['scores']['by_benchmark'].keys())
        scores = [self.report['scores']['by_benchmark'][b] * 100 for b in benchmarks]

        return f"""
        new Chart(document.getElementById('benchmarkChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(benchmarks)},
                datasets: [{{
                    label: '分數 (%)',
                    data: {json.dumps(scores)},
                    backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#f5576c'],
                    borderRadius: 5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});
        """

    def save(self, filepath: str):
        """保存 HTML 報告"""
        html = self.generate_html()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"報告已保存至: {filepath}")
```

### 12.6.2 持續改進策略

```
┌─────────────────────────────────────────────────────────────────┐
│                  評測驅動的持續改進循環                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    ┌──────────┐                      ┌──────────┐              │
│    │  評測    │◀─────────────────────│  部署    │              │
│    │  Evaluate │                      │  Deploy  │              │
│    └────┬─────┘                      └────▲─────┘              │
│         │                                  │                    │
│         ▼                                  │                    │
│    ┌──────────┐                      ┌──────────┐              │
│    │  分析    │─────────────────────▶│  優化    │              │
│    │  Analyze │                      │  Optimize│              │
│    └──────────┘                      └──────────┘              │
│                                                                 │
│    每次迭代：                                                   │
│    1. 運行基準測試                                              │
│    2. 分析弱項區域                                              │
│    3. 針對性優化                                                │
│    4. 驗證改進效果                                              │
│    5. 部署更新版本                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12.7 章節總結

本章深入探討了深度研究代理人的評測方法論：

### 核心概念

1. **HLE（Human-Like Evaluation）**
   - 模擬人類專家評估標準
   - 六維度評分：準確性、完整性、相關性、連貫性、深度、時效性
   - 支援主觀與客觀指標

2. **GAIA 基準測試**
   - 強調客觀可驗證的答案
   - 三級難度分層
   - 測試多步驟推理和工具使用

3. **BrowseComp**
   - 測試網頁瀏覽能力
   - 五級能力分層
   - 涵蓋靜態讀取到多輪對話

### 關鍵實作

- 統一評測框架整合多種基準
- 自動化評估流程
- 視覺化報告生成
- 持續改進策略

### 檢查清單

- [ ] 理解三種基準測試的設計原理
- [ ] 能夠建構自定義測試案例
- [ ] 掌握評測結果分析方法
- [ ] 了解評測驅動的優化流程

---

## 12.8 下一章預告

在下一章「幻覺處理與事實查核」中，我們將深入探討：

- 幻覺（Hallucination）的類型與成因
- 時序敏感訓練方法
- 因果律約束機制
- 自動事實查核系統
- 來源可信度評估

這些技術將幫助你的研究代理人產生更加可靠、準確的研究結果。
