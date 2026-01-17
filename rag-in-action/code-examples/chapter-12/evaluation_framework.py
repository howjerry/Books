"""
Chapter 12: RAG 自動化評估框架

實作多維度評估指標：檢索評估 + 生成評估
"""

import json
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import math

import numpy as np
from rouge_score import rouge_scorer


# ═══════════════════════════════════════════════════════════════
# 測試集資料結構
# ═══════════════════════════════════════════════════════════════

@dataclass
class TestCase:
    """單一測試案例"""
    query_id: str
    query: str
    relevant_doc_ids: List[str]         # 相關文件 ID（檢索評估用）
    expected_answer: Optional[str] = None  # 預期答案（生成評估用）
    category: str = "general"           # 問題類別
    difficulty: str = "medium"          # 難度：easy/medium/hard
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSet:
    """測試集"""
    name: str
    version: str
    test_cases: List[TestCase]
    created_at: str

    @classmethod
    def from_json(cls, path: str) -> "TestSet":
        """從 JSON 載入測試集"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cases = [TestCase(**tc) for tc in data["test_cases"]]
        return cls(
            name=data["name"],
            version=data["version"],
            test_cases=cases,
            created_at=data["created_at"]
        )

    def to_json(self, path: str) -> None:
        """儲存測試集為 JSON"""
        data = {
            "name": self.name,
            "version": self.version,
            "created_at": self.created_at,
            "test_cases": [
                {
                    "query_id": tc.query_id,
                    "query": tc.query,
                    "relevant_doc_ids": tc.relevant_doc_ids,
                    "expected_answer": tc.expected_answer,
                    "category": tc.category,
                    "difficulty": tc.difficulty,
                    "metadata": tc.metadata
                }
                for tc in self.test_cases
            ]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════
# 檢索階段評估
# ═══════════════════════════════════════════════════════════════

class RetrievalEvaluator:
    """
    檢索評估器

    指標：
    - Precision@K：前 K 個結果中相關的比例
    - Recall@K：找到的相關文件佔全部相關文件的比例
    - MRR：第一個相關結果的排名倒數
    - NDCG@K：考慮排名的正規化折損累積增益
    """

    def precision_at_k(
        self,
        retrieved_ids: List[str],
        relevant_ids: Set[str],
        k: int
    ) -> float:
        """
        計算 Precision@K

        Args:
            retrieved_ids: 檢索到的文件 ID 列表（已排序）
            relevant_ids: 相關文件 ID 集合
            k: 評估的前 K 個結果

        Returns:
            Precision@K 分數
        """
        if k == 0:
            return 0.0

        top_k = retrieved_ids[:k]
        relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in relevant_ids)

        return relevant_in_top_k / k

    def recall_at_k(
        self,
        retrieved_ids: List[str],
        relevant_ids: Set[str],
        k: int
    ) -> float:
        """
        計算 Recall@K

        Args:
            retrieved_ids: 檢索到的文件 ID 列表
            relevant_ids: 相關文件 ID 集合
            k: 評估的前 K 個結果

        Returns:
            Recall@K 分數
        """
        if len(relevant_ids) == 0:
            return 0.0

        top_k = retrieved_ids[:k]
        relevant_found = sum(1 for doc_id in top_k if doc_id in relevant_ids)

        return relevant_found / len(relevant_ids)

    def mrr(
        self,
        retrieved_ids: List[str],
        relevant_ids: Set[str]
    ) -> float:
        """
        計算 MRR (Mean Reciprocal Rank)

        Args:
            retrieved_ids: 檢索到的文件 ID 列表
            relevant_ids: 相關文件 ID 集合

        Returns:
            MRR 分數（單一查詢的 Reciprocal Rank）
        """
        for rank, doc_id in enumerate(retrieved_ids, start=1):
            if doc_id in relevant_ids:
                return 1.0 / rank
        return 0.0

    def ndcg_at_k(
        self,
        retrieved_ids: List[str],
        relevant_ids: Set[str],
        k: int
    ) -> float:
        """
        計算 NDCG@K

        Args:
            retrieved_ids: 檢索到的文件 ID 列表
            relevant_ids: 相關文件 ID 集合
            k: 評估的前 K 個結果

        Returns:
            NDCG@K 分數
        """
        # 計算 DCG
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids[:k]):
            if doc_id in relevant_ids:
                # 使用二元相關性（相關=1，不相關=0）
                dcg += 1.0 / math.log2(i + 2)  # +2 因為 i 從 0 開始

        # 計算 IDCG（理想情況：所有相關文件排在最前面）
        ideal_length = min(len(relevant_ids), k)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_length))

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def evaluate_single(
        self,
        retrieved_ids: List[str],
        relevant_ids: List[str],
        k_values: List[int] = [1, 3, 5, 10]
    ) -> Dict[str, float]:
        """
        評估單一查詢

        Args:
            retrieved_ids: 檢索結果
            relevant_ids: 相關文件
            k_values: 要評估的 K 值列表

        Returns:
            各指標分數
        """
        relevant_set = set(relevant_ids)
        results = {"mrr": self.mrr(retrieved_ids, relevant_set)}

        for k in k_values:
            results[f"precision@{k}"] = self.precision_at_k(
                retrieved_ids, relevant_set, k
            )
            results[f"recall@{k}"] = self.recall_at_k(
                retrieved_ids, relevant_set, k
            )
            results[f"ndcg@{k}"] = self.ndcg_at_k(
                retrieved_ids, relevant_set, k
            )

        return results

    def evaluate_batch(
        self,
        results: List[Dict[str, Any]],
        k_values: List[int] = [1, 3, 5, 10]
    ) -> Dict[str, float]:
        """
        批次評估多個查詢

        Args:
            results: 查詢結果列表，每個包含 retrieved_ids 和 relevant_ids
            k_values: 要評估的 K 值列表

        Returns:
            平均分數
        """
        all_scores = defaultdict(list)

        for result in results:
            scores = self.evaluate_single(
                result["retrieved_ids"],
                result["relevant_ids"],
                k_values
            )
            for metric, value in scores.items():
                all_scores[metric].append(value)

        # 計算平均值
        return {
            metric: np.mean(values)
            for metric, values in all_scores.items()
        }


# ═══════════════════════════════════════════════════════════════
# 生成階段評估
# ═══════════════════════════════════════════════════════════════

class GenerationEvaluator:
    """
    生成評估器

    指標：
    - ROUGE：文字重疊度
    - Answer Relevance：答案與問題的相關性
    - Faithfulness：答案是否忠於來源文件
    - Answer Completeness：答案完整性
    """

    def __init__(self):
        self.rouge_scorer = rouge_scorer.RougeScorer(
            ['rouge1', 'rouge2', 'rougeL'],
            use_stemmer=True
        )

    def rouge_scores(
        self,
        generated: str,
        reference: str
    ) -> Dict[str, float]:
        """
        計算 ROUGE 分數

        Args:
            generated: 生成的答案
            reference: 參考答案

        Returns:
            ROUGE-1, ROUGE-2, ROUGE-L F1 分數
        """
        scores = self.rouge_scorer.score(reference, generated)

        return {
            "rouge1": scores["rouge1"].fmeasure,
            "rouge2": scores["rouge2"].fmeasure,
            "rougeL": scores["rougeL"].fmeasure,
        }

    def answer_length_ratio(
        self,
        generated: str,
        reference: str
    ) -> float:
        """
        答案長度比率

        過短可能不完整，過長可能有冗餘
        理想值接近 1.0
        """
        if len(reference) == 0:
            return 0.0
        return len(generated) / len(reference)

    def keyword_coverage(
        self,
        generated: str,
        keywords: List[str]
    ) -> float:
        """
        關鍵字覆蓋率

        Args:
            generated: 生成的答案
            keywords: 必須包含的關鍵字

        Returns:
            覆蓋比例
        """
        if not keywords:
            return 1.0

        generated_lower = generated.lower()
        covered = sum(1 for kw in keywords if kw.lower() in generated_lower)

        return covered / len(keywords)

    def evaluate_single(
        self,
        generated: str,
        reference: str,
        keywords: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        評估單一答案

        Args:
            generated: 生成的答案
            reference: 參考答案
            keywords: 必要關鍵字

        Returns:
            各指標分數
        """
        results = self.rouge_scores(generated, reference)
        results["length_ratio"] = self.answer_length_ratio(generated, reference)

        if keywords:
            results["keyword_coverage"] = self.keyword_coverage(
                generated, keywords
            )

        return results

    def evaluate_batch(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        批次評估多個答案

        Args:
            results: 包含 generated, reference, keywords 的列表

        Returns:
            平均分數
        """
        all_scores = defaultdict(list)

        for result in results:
            scores = self.evaluate_single(
                result["generated"],
                result["reference"],
                result.get("keywords")
            )
            for metric, value in scores.items():
                all_scores[metric].append(value)

        return {
            metric: np.mean(values)
            for metric, values in all_scores.items()
        }


# ═══════════════════════════════════════════════════════════════
# 整合評估框架
# ═══════════════════════════════════════════════════════════════

@dataclass
class EvaluationResult:
    """評估結果"""
    retrieval_metrics: Dict[str, float]
    generation_metrics: Dict[str, float]
    category_breakdown: Dict[str, Dict[str, float]]
    difficulty_breakdown: Dict[str, Dict[str, float]]
    total_cases: int
    passed_cases: int

    @property
    def pass_rate(self) -> float:
        """通過率"""
        if self.total_cases == 0:
            return 0.0
        return self.passed_cases / self.total_cases

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "retrieval_metrics": self.retrieval_metrics,
            "generation_metrics": self.generation_metrics,
            "category_breakdown": self.category_breakdown,
            "difficulty_breakdown": self.difficulty_breakdown,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "pass_rate": self.pass_rate
        }


class RAGEvaluator:
    """
    RAG 系統整合評估器

    結合檢索與生成評估，支援分類分析
    """

    def __init__(
        self,
        retrieval_threshold: float = 0.6,  # Recall@5 門檻
        generation_threshold: float = 0.4  # ROUGE-L 門檻
    ):
        self.retrieval_evaluator = RetrievalEvaluator()
        self.generation_evaluator = GenerationEvaluator()
        self.retrieval_threshold = retrieval_threshold
        self.generation_threshold = generation_threshold

    def evaluate(
        self,
        test_set: TestSet,
        rag_fn,  # 接收 query，返回 {retrieved_ids, answer}
        k_values: List[int] = [1, 3, 5, 10]
    ) -> EvaluationResult:
        """
        執行完整評估

        Args:
            test_set: 測試集
            rag_fn: RAG 函數，接收查詢返回結果
            k_values: 評估的 K 值列表

        Returns:
            評估結果
        """
        retrieval_results = []
        generation_results = []
        category_scores = defaultdict(lambda: defaultdict(list))
        difficulty_scores = defaultdict(lambda: defaultdict(list))
        passed_cases = 0

        for test_case in test_set.test_cases:
            # 執行 RAG
            result = rag_fn(test_case.query)
            retrieved_ids = result.get("retrieved_ids", [])
            generated_answer = result.get("answer", "")

            # 檢索評估
            retrieval_result = {
                "retrieved_ids": retrieved_ids,
                "relevant_ids": test_case.relevant_doc_ids
            }
            retrieval_results.append(retrieval_result)

            retrieval_scores = self.retrieval_evaluator.evaluate_single(
                retrieved_ids,
                test_case.relevant_doc_ids,
                k_values
            )

            # 生成評估（如果有預期答案）
            generation_scores = {}
            if test_case.expected_answer:
                generation_result = {
                    "generated": generated_answer,
                    "reference": test_case.expected_answer,
                    "keywords": test_case.metadata.get("keywords")
                }
                generation_results.append(generation_result)
                generation_scores = self.generation_evaluator.evaluate_single(
                    generated_answer,
                    test_case.expected_answer,
                    test_case.metadata.get("keywords")
                )

            # 判斷是否通過
            recall_5 = retrieval_scores.get("recall@5", 0)
            rouge_l = generation_scores.get("rougeL", 1.0)  # 沒有預期答案視為通過

            if recall_5 >= self.retrieval_threshold and rouge_l >= self.generation_threshold:
                passed_cases += 1

            # 按類別和難度分組
            for metric, value in retrieval_scores.items():
                category_scores[test_case.category][metric].append(value)
                difficulty_scores[test_case.difficulty][metric].append(value)

            for metric, value in generation_scores.items():
                category_scores[test_case.category][metric].append(value)
                difficulty_scores[test_case.difficulty][metric].append(value)

        # 計算整體指標
        overall_retrieval = self.retrieval_evaluator.evaluate_batch(
            retrieval_results, k_values
        )

        overall_generation = {}
        if generation_results:
            overall_generation = self.generation_evaluator.evaluate_batch(
                generation_results
            )

        # 計算分組平均
        category_breakdown = {
            cat: {metric: np.mean(values) for metric, values in scores.items()}
            for cat, scores in category_scores.items()
        }

        difficulty_breakdown = {
            diff: {metric: np.mean(values) for metric, values in scores.items()}
            for diff, scores in difficulty_scores.items()
        }

        return EvaluationResult(
            retrieval_metrics=overall_retrieval,
            generation_metrics=overall_generation,
            category_breakdown=category_breakdown,
            difficulty_breakdown=difficulty_breakdown,
            total_cases=len(test_set.test_cases),
            passed_cases=passed_cases
        )


# ═══════════════════════════════════════════════════════════════
# 示範用法
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 建立範例測試集
    test_cases = [
        TestCase(
            query_id="Q001",
            query="如何重設密碼？",
            relevant_doc_ids=["DOC001", "DOC002"],
            expected_answer="您可以透過登入頁面的「忘記密碼」連結來重設密碼。",
            category="account",
            difficulty="easy",
            metadata={"keywords": ["重設", "密碼", "忘記"]}
        ),
        TestCase(
            query_id="Q002",
            query="退貨流程是什麼？",
            relevant_doc_ids=["DOC010", "DOC011", "DOC012"],
            expected_answer="退貨流程：1. 登入帳號 2. 進入訂單頁面 3. 選擇退貨 4. 填寫原因 5. 等待審核",
            category="order",
            difficulty="medium",
            metadata={"keywords": ["退貨", "流程", "訂單"]}
        ),
    ]

    test_set = TestSet(
        name="AskBot 基準測試集",
        version="1.0",
        test_cases=test_cases,
        created_at="2024-01-15"
    )

    # 儲存測試集
    test_set.to_json("test_set.json")
    print("測試集已儲存")

    # 檢索評估示範
    retrieval_eval = RetrievalEvaluator()

    retrieved = ["DOC001", "DOC003", "DOC002", "DOC004", "DOC005"]
    relevant = ["DOC001", "DOC002"]

    scores = retrieval_eval.evaluate_single(retrieved, relevant)
    print("\n檢索評估結果：")
    for metric, value in scores.items():
        print(f"  {metric}: {value:.4f}")

    # 生成評估示範
    generation_eval = GenerationEvaluator()

    generated = "您可以點擊登入頁面的忘記密碼連結來重新設定密碼。"
    reference = "您可以透過登入頁面的「忘記密碼」連結來重設密碼。"

    gen_scores = generation_eval.evaluate_single(
        generated, reference, ["重設", "密碼"]
    )
    print("\n生成評估結果：")
    for metric, value in gen_scores.items():
        print(f"  {metric}: {value:.4f}")
