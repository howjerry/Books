"""
Chapter 12: A/B 測試框架

實作 RAG 系統的 A/B 測試與統計顯著性分析
"""

import random
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import math

import numpy as np
from scipy import stats


class ExperimentStatus(Enum):
    """實驗狀態"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"  # 提前終止（顯著性已達到）


@dataclass
class Variant:
    """實驗變體"""
    name: str
    weight: float = 0.5  # 流量比例
    rag_config: Dict[str, Any] = field(default_factory=dict)

    # 執行時統計
    request_count: int = 0
    success_count: int = 0
    total_latency_ms: float = 0.0
    feedback_scores: List[float] = field(default_factory=list)
    retrieval_scores: List[float] = field(default_factory=list)


@dataclass
class Experiment:
    """A/B 實驗"""
    experiment_id: str
    name: str
    description: str
    control: Variant
    treatment: Variant

    # 實驗設定
    min_sample_size: int = 1000
    max_duration_hours: int = 168  # 最長一週
    significance_level: float = 0.05
    minimum_detectable_effect: float = 0.05  # 最小可偵測效果 5%

    # 狀態
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class ABTester:
    """
    A/B 測試執行器

    功能：
    1. 流量分配
    2. 指標收集
    3. 統計顯著性分析
    4. 自動停止（達到顯著性）
    """

    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        self.user_assignments: Dict[str, str] = {}  # user_id -> variant_name

    def create_experiment(
        self,
        experiment_id: str,
        name: str,
        description: str,
        control_config: Dict[str, Any],
        treatment_config: Dict[str, Any],
        traffic_split: float = 0.5,
        min_sample_size: int = 1000
    ) -> Experiment:
        """
        建立新實驗

        Args:
            experiment_id: 實驗 ID
            name: 實驗名稱
            description: 描述
            control_config: 控制組 RAG 設定
            treatment_config: 實驗組 RAG 設定
            traffic_split: 實驗組流量比例
            min_sample_size: 最小樣本數

        Returns:
            建立的實驗
        """
        control = Variant(
            name="control",
            weight=1 - traffic_split,
            rag_config=control_config
        )

        treatment = Variant(
            name="treatment",
            weight=traffic_split,
            rag_config=treatment_config
        )

        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            control=control,
            treatment=treatment,
            min_sample_size=min_sample_size
        )

        self.experiments[experiment_id] = experiment
        return experiment

    def start_experiment(self, experiment_id: str) -> None:
        """啟動實驗"""
        exp = self.experiments.get(experiment_id)
        if exp and exp.status == ExperimentStatus.DRAFT:
            exp.status = ExperimentStatus.RUNNING
            exp.started_at = datetime.now()

    def assign_variant(
        self,
        experiment_id: str,
        user_id: str
    ) -> Optional[Variant]:
        """
        分配使用者到變體

        使用確定性雜湊確保同一使用者總是分到同一組

        Args:
            experiment_id: 實驗 ID
            user_id: 使用者 ID

        Returns:
            分配的變體
        """
        exp = self.experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return None

        # 確定性分配：使用雜湊
        assignment_key = f"{experiment_id}:{user_id}"

        if assignment_key in self.user_assignments:
            variant_name = self.user_assignments[assignment_key]
        else:
            # 使用雜湊值決定分組
            hash_value = hash(assignment_key) % 100 / 100

            if hash_value < exp.treatment.weight:
                variant_name = "treatment"
            else:
                variant_name = "control"

            self.user_assignments[assignment_key] = variant_name

        return exp.treatment if variant_name == "treatment" else exp.control

    def record_result(
        self,
        experiment_id: str,
        variant_name: str,
        success: bool,
        latency_ms: float,
        feedback_score: Optional[float] = None,
        retrieval_score: Optional[float] = None
    ) -> None:
        """
        記錄實驗結果

        Args:
            experiment_id: 實驗 ID
            variant_name: 變體名稱
            success: 是否成功
            latency_ms: 延遲毫秒
            feedback_score: 使用者回饋分數
            retrieval_score: 檢索品質分數
        """
        exp = self.experiments.get(experiment_id)
        if not exp:
            return

        variant = exp.treatment if variant_name == "treatment" else exp.control

        variant.request_count += 1
        if success:
            variant.success_count += 1
        variant.total_latency_ms += latency_ms

        if feedback_score is not None:
            variant.feedback_scores.append(feedback_score)

        if retrieval_score is not None:
            variant.retrieval_scores.append(retrieval_score)

        # 檢查是否該停止實驗
        self._check_stopping_criteria(experiment_id)

    def _check_stopping_criteria(self, experiment_id: str) -> None:
        """檢查是否達到停止條件"""
        exp = self.experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return

        # 條件 1：達到最小樣本數且統計顯著
        total_samples = exp.control.request_count + exp.treatment.request_count
        if total_samples >= exp.min_sample_size:
            analysis = self.analyze_experiment(experiment_id)
            if analysis and analysis.get("is_significant"):
                exp.status = ExperimentStatus.STOPPED
                exp.ended_at = datetime.now()
                return

        # 條件 2：達到最大時長
        if exp.started_at:
            hours_elapsed = (datetime.now() - exp.started_at).total_seconds() / 3600
            if hours_elapsed >= exp.max_duration_hours:
                exp.status = ExperimentStatus.COMPLETED
                exp.ended_at = datetime.now()

    def analyze_experiment(
        self,
        experiment_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        分析實驗結果

        執行統計顯著性檢定

        Args:
            experiment_id: 實驗 ID

        Returns:
            分析結果
        """
        exp = self.experiments.get(experiment_id)
        if not exp:
            return None

        control = exp.control
        treatment = exp.treatment

        # 基本統計
        result = {
            "experiment_id": experiment_id,
            "experiment_name": exp.name,
            "status": exp.status.value,
            "total_samples": control.request_count + treatment.request_count,
            "control": {
                "samples": control.request_count,
                "success_rate": control.success_count / max(control.request_count, 1),
                "avg_latency_ms": control.total_latency_ms / max(control.request_count, 1),
            },
            "treatment": {
                "samples": treatment.request_count,
                "success_rate": treatment.success_count / max(treatment.request_count, 1),
                "avg_latency_ms": treatment.total_latency_ms / max(treatment.request_count, 1),
            }
        }

        # 成功率的統計檢定（Z-test for proportions）
        if control.request_count >= 30 and treatment.request_count >= 30:
            z_stat, p_value = self._proportion_z_test(
                control.success_count, control.request_count,
                treatment.success_count, treatment.request_count
            )

            result["success_rate_test"] = {
                "z_statistic": z_stat,
                "p_value": p_value,
                "is_significant": p_value < exp.significance_level,
                "relative_improvement": (
                    (result["treatment"]["success_rate"] - result["control"]["success_rate"])
                    / max(result["control"]["success_rate"], 0.001) * 100
                )
            }

        # 回饋分數的統計檢定（T-test）
        if len(control.feedback_scores) >= 30 and len(treatment.feedback_scores) >= 30:
            t_stat, p_value = stats.ttest_ind(
                treatment.feedback_scores,
                control.feedback_scores
            )

            result["feedback_test"] = {
                "control_mean": np.mean(control.feedback_scores),
                "treatment_mean": np.mean(treatment.feedback_scores),
                "t_statistic": t_stat,
                "p_value": p_value,
                "is_significant": p_value < exp.significance_level,
                "effect_size": self._cohens_d(
                    treatment.feedback_scores,
                    control.feedback_scores
                )
            }

        # 整體顯著性判斷
        result["is_significant"] = any([
            result.get("success_rate_test", {}).get("is_significant", False),
            result.get("feedback_test", {}).get("is_significant", False)
        ])

        # 勝者判定
        if result["is_significant"]:
            treatment_better = (
                result["treatment"]["success_rate"] > result["control"]["success_rate"]
            )
            result["winner"] = "treatment" if treatment_better else "control"
            result["recommendation"] = (
                f"建議採用 {result['winner']} 版本"
                if result["is_significant"]
                else "需要更多樣本"
            )

        return result

    def _proportion_z_test(
        self,
        success_a: int, n_a: int,
        success_b: int, n_b: int
    ) -> tuple:
        """
        比例的 Z 檢定

        H0: p_a = p_b
        H1: p_a != p_b
        """
        p_a = success_a / n_a
        p_b = success_b / n_b

        # 合併比例
        p_pooled = (success_a + success_b) / (n_a + n_b)

        # 標準誤
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n_a + 1/n_b))

        if se == 0:
            return 0, 1.0

        z = (p_b - p_a) / se
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))  # 雙尾檢定

        return z, p_value

    def _cohens_d(self, group1: List[float], group2: List[float]) -> float:
        """計算 Cohen's d 效果量"""
        n1, n2 = len(group1), len(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

        # 合併標準差
        pooled_std = math.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))

        if pooled_std == 0:
            return 0

        return (np.mean(group1) - np.mean(group2)) / pooled_std

    def calculate_sample_size(
        self,
        baseline_rate: float,
        minimum_detectable_effect: float,
        significance_level: float = 0.05,
        power: float = 0.8
    ) -> int:
        """
        計算所需樣本數

        使用 Power Analysis

        Args:
            baseline_rate: 基準轉換率
            minimum_detectable_effect: 最小可偵測效果（相對變化）
            significance_level: 顯著水準 (α)
            power: 統計檢定力 (1-β)

        Returns:
            每組所需樣本數
        """
        # 預期的新比例
        expected_rate = baseline_rate * (1 + minimum_detectable_effect)

        # 合併比例
        p_pooled = (baseline_rate + expected_rate) / 2

        # Z 值
        z_alpha = stats.norm.ppf(1 - significance_level / 2)  # 雙尾
        z_beta = stats.norm.ppf(power)

        # 效果量
        effect = abs(expected_rate - baseline_rate)

        # 樣本數公式
        numerator = 2 * p_pooled * (1 - p_pooled) * (z_alpha + z_beta) ** 2
        denominator = effect ** 2

        return int(math.ceil(numerator / denominator))


class ABTestRunner:
    """
    A/B 測試執行器

    整合 RAG 系統執行 A/B 測試
    """

    def __init__(
        self,
        tester: ABTester,
        rag_factory: Callable[[Dict[str, Any]], Callable]
    ):
        """
        Args:
            tester: A/B 測試器
            rag_factory: RAG 函數工廠，接收 config 返回 RAG 函數
        """
        self.tester = tester
        self.rag_factory = rag_factory
        self.rag_instances: Dict[str, Callable] = {}

    def handle_request(
        self,
        experiment_id: str,
        user_id: str,
        query: str
    ) -> Dict[str, Any]:
        """
        處理請求並記錄 A/B 測試結果

        Args:
            experiment_id: 實驗 ID
            user_id: 使用者 ID
            query: 查詢

        Returns:
            RAG 回應
        """
        # 分配變體
        variant = self.tester.assign_variant(experiment_id, user_id)

        if not variant:
            # 實驗不存在或未運行，使用預設設定
            return {"error": "Experiment not running"}

        # 取得或建立 RAG 實例
        variant_key = f"{experiment_id}:{variant.name}"
        if variant_key not in self.rag_instances:
            self.rag_instances[variant_key] = self.rag_factory(variant.rag_config)

        rag_fn = self.rag_instances[variant_key]

        # 執行並計時
        start_time = time.time()
        try:
            result = rag_fn(query)
            success = True
        except Exception as e:
            result = {"error": str(e)}
            success = False

        latency_ms = (time.time() - start_time) * 1000

        # 記錄結果
        self.tester.record_result(
            experiment_id=experiment_id,
            variant_name=variant.name,
            success=success,
            latency_ms=latency_ms,
            retrieval_score=result.get("retrieval_score")
        )

        # 附加實驗資訊到回應
        result["_experiment"] = {
            "experiment_id": experiment_id,
            "variant": variant.name
        }

        return result


# ═══════════════════════════════════════════════════════════════
# 示範用法
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 建立 A/B 測試器
    tester = ABTester()

    # 計算所需樣本數
    sample_size = tester.calculate_sample_size(
        baseline_rate=0.7,  # 基準成功率 70%
        minimum_detectable_effect=0.05,  # 想偵測 5% 的提升
        significance_level=0.05,
        power=0.8
    )
    print(f"所需樣本數（每組）：{sample_size}")

    # 建立實驗
    experiment = tester.create_experiment(
        experiment_id="exp_rerank_001",
        name="Re-Ranking 模型對比",
        description="比較 Cross-Encoder 與 Bi-Encoder Re-Ranking",
        control_config={
            "reranker": "bi-encoder",
            "model": "all-MiniLM-L6-v2"
        },
        treatment_config={
            "reranker": "cross-encoder",
            "model": "cross-encoder/ms-marco-MiniLM-L-6-v2"
        },
        traffic_split=0.5,
        min_sample_size=sample_size
    )

    # 啟動實驗
    tester.start_experiment("exp_rerank_001")

    # 模擬請求
    random.seed(42)
    for i in range(200):
        user_id = f"user_{i % 50}"
        variant = tester.assign_variant("exp_rerank_001", user_id)

        if variant:
            # 模擬結果（treatment 稍好）
            if variant.name == "treatment":
                success = random.random() < 0.75  # 75% 成功率
                feedback = random.uniform(3.5, 5.0)
            else:
                success = random.random() < 0.70  # 70% 成功率
                feedback = random.uniform(3.0, 4.5)

            latency = random.uniform(100, 300)

            tester.record_result(
                experiment_id="exp_rerank_001",
                variant_name=variant.name,
                success=success,
                latency_ms=latency,
                feedback_score=feedback
            )

    # 分析結果
    analysis = tester.analyze_experiment("exp_rerank_001")

    print("\n實驗分析結果：")
    print(f"  實驗名稱：{analysis['experiment_name']}")
    print(f"  總樣本數：{analysis['total_samples']}")
    print(f"\n  控制組：")
    print(f"    樣本數：{analysis['control']['samples']}")
    print(f"    成功率：{analysis['control']['success_rate']:.2%}")
    print(f"    平均延遲：{analysis['control']['avg_latency_ms']:.1f}ms")
    print(f"\n  實驗組：")
    print(f"    樣本數：{analysis['treatment']['samples']}")
    print(f"    成功率：{analysis['treatment']['success_rate']:.2%}")
    print(f"    平均延遲：{analysis['treatment']['avg_latency_ms']:.1f}ms")

    if "success_rate_test" in analysis:
        test = analysis["success_rate_test"]
        print(f"\n  成功率檢定：")
        print(f"    Z 統計量：{test['z_statistic']:.3f}")
        print(f"    P 值：{test['p_value']:.4f}")
        print(f"    統計顯著：{'是' if test['is_significant'] else '否'}")
        print(f"    相對提升：{test['relative_improvement']:.1f}%")

    if analysis.get("is_significant"):
        print(f"\n  結論：{analysis['recommendation']}")
