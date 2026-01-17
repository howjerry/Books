"""
Chapter 13: 持續學習 Pipeline

實作自動化的 RAG 系統持續優化流程
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 重訓練觸發條件
# ═══════════════════════════════════════════════════════════════

class TriggerType(Enum):
    """觸發類型"""
    SCHEDULED = "scheduled"           # 定期觸發
    PERFORMANCE_DEGRADATION = "performance_degradation"  # 效能下降
    DATA_DRIFT = "data_drift"         # 資料漂移
    FEEDBACK_VOLUME = "feedback_volume"  # 回饋量達標
    MANUAL = "manual"                 # 手動觸發


@dataclass
class TriggerCondition:
    """觸發條件配置"""
    # 定期觸發
    schedule_interval_days: int = 7

    # 效能下降觸發
    performance_threshold: float = 0.05  # 下降 5% 觸發
    performance_metric: str = "recall@5"

    # 回饋量觸發
    min_feedback_count: int = 1000

    # 資料漂移觸發
    drift_threshold: float = 0.1


class RetrainingTrigger:
    """
    重訓練觸發器

    監控系統狀態，判斷是否需要重訓練
    """

    def __init__(self, config: TriggerCondition):
        self.config = config
        self.last_training_time: Optional[datetime] = None
        self.baseline_metrics: Dict[str, float] = {}

    def check_scheduled_trigger(self) -> bool:
        """檢查定期觸發"""
        if self.last_training_time is None:
            return False

        days_since_last = (datetime.now() - self.last_training_time).days
        return days_since_last >= self.config.schedule_interval_days

    def check_performance_trigger(
        self,
        current_metrics: Dict[str, float]
    ) -> bool:
        """
        檢查效能下降觸發

        Args:
            current_metrics: 當前評估指標

        Returns:
            是否觸發
        """
        if not self.baseline_metrics:
            return False

        metric_name = self.config.performance_metric
        baseline = self.baseline_metrics.get(metric_name, 0)
        current = current_metrics.get(metric_name, 0)

        if baseline > 0:
            degradation = (baseline - current) / baseline
            if degradation >= self.config.performance_threshold:
                logger.warning(
                    f"效能下降觸發：{metric_name} 從 {baseline:.3f} "
                    f"降至 {current:.3f}（下降 {degradation:.1%}）"
                )
                return True

        return False

    def check_feedback_volume_trigger(
        self,
        new_feedback_count: int
    ) -> bool:
        """
        檢查回饋量觸發

        Args:
            new_feedback_count: 新增回饋數量

        Returns:
            是否觸發
        """
        if new_feedback_count >= self.config.min_feedback_count:
            logger.info(
                f"回饋量觸發：收集到 {new_feedback_count} 條新回饋"
            )
            return True
        return False

    def should_retrain(
        self,
        current_metrics: Dict[str, float],
        new_feedback_count: int
    ) -> tuple:
        """
        綜合判斷是否需要重訓練

        Returns:
            (是否觸發, 觸發類型)
        """
        # 優先級：效能下降 > 回饋量 > 定期
        if self.check_performance_trigger(current_metrics):
            return True, TriggerType.PERFORMANCE_DEGRADATION

        if self.check_feedback_volume_trigger(new_feedback_count):
            return True, TriggerType.FEEDBACK_VOLUME

        if self.check_scheduled_trigger():
            return True, TriggerType.SCHEDULED

        return False, None


# ═══════════════════════════════════════════════════════════════
# 訓練資料準備
# ═══════════════════════════════════════════════════════════════

@dataclass
class TrainingPair:
    """訓練資料對"""
    query: str
    positive_doc: str        # 正樣本
    negative_docs: List[str]  # 負樣本
    source: str              # 資料來源：feedback/click/synthetic


class TrainingDataPreparer:
    """
    訓練資料準備器

    從回饋資料生成訓練樣本
    """

    def __init__(
        self,
        hard_negative_ratio: float = 0.5,
        max_negatives_per_query: int = 5
    ):
        self.hard_negative_ratio = hard_negative_ratio
        self.max_negatives = max_negatives_per_query

    def prepare_from_feedback(
        self,
        feedback_data: List[Dict[str, Any]],
        retrieval_fn
    ) -> List[TrainingPair]:
        """
        從使用者回饋準備訓練資料

        Args:
            feedback_data: 回饋資料列表
            retrieval_fn: 檢索函數（用於生成 hard negatives）

        Returns:
            訓練資料對列表
        """
        pairs = []

        for fb in feedback_data:
            query = fb["query"]
            feedback_type = fb["feedback_type"]

            if feedback_type == "positive":
                # 正面回饋：用戶點讚的答案來源作為正樣本
                positive_doc = fb.get("answer_source", "")
                if not positive_doc:
                    continue

                # 生成負樣本
                negatives = self._generate_negatives(
                    query, positive_doc, retrieval_fn
                )

                pairs.append(TrainingPair(
                    query=query,
                    positive_doc=positive_doc,
                    negative_docs=negatives,
                    source="feedback"
                ))

            elif feedback_type == "negative":
                # 負面回饋：用戶標記的正確答案作為正樣本
                correct_doc = fb.get("correct_source", "")
                if not correct_doc:
                    continue

                # 原本錯誤的答案來源作為 hard negative
                wrong_doc = fb.get("answer_source", "")
                negatives = [wrong_doc] if wrong_doc else []

                # 補充其他負樣本
                additional = self._generate_negatives(
                    query, correct_doc, retrieval_fn,
                    exclude=[wrong_doc]
                )
                negatives.extend(additional[:self.max_negatives - len(negatives)])

                pairs.append(TrainingPair(
                    query=query,
                    positive_doc=correct_doc,
                    negative_docs=negatives,
                    source="feedback"
                ))

        return pairs

    def _generate_negatives(
        self,
        query: str,
        positive_doc: str,
        retrieval_fn,
        exclude: List[str] = None
    ) -> List[str]:
        """
        生成負樣本

        混合 hard negatives（檢索到但不正確）和 random negatives
        """
        exclude = exclude or []
        negatives = []

        # Hard negatives：從檢索結果中取排名靠前但不是正樣本的
        num_hard = int(self.max_negatives * self.hard_negative_ratio)
        retrieved = retrieval_fn(query, top_k=20)

        for doc in retrieved:
            if doc != positive_doc and doc not in exclude:
                negatives.append(doc)
                if len(negatives) >= num_hard:
                    break

        # Random negatives：從全域隨機抽取
        # （實際實作中從文件庫隨機抽取）

        return negatives[:self.max_negatives]

    def prepare_from_clicks(
        self,
        click_data: List[Dict[str, Any]]
    ) -> List[TrainingPair]:
        """
        從點擊資料準備訓練資料

        點擊的文件視為正樣本
        """
        pairs = []

        for click in click_data:
            query = click["query"]
            clicked_doc = click["clicked_doc"]
            shown_docs = click["shown_docs"]

            # 未點擊的文件作為負樣本
            negatives = [d for d in shown_docs if d != clicked_doc]

            pairs.append(TrainingPair(
                query=query,
                positive_doc=clicked_doc,
                negative_docs=negatives[:self.max_negatives],
                source="click"
            ))

        return pairs


# ═══════════════════════════════════════════════════════════════
# Re-Ranker 重訓練
# ═══════════════════════════════════════════════════════════════

@dataclass
class TrainingConfig:
    """訓練配置"""
    base_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    epochs: int = 3
    batch_size: int = 16
    learning_rate: float = 2e-5
    warmup_ratio: float = 0.1
    output_dir: str = "./models"


class ReRankerTrainer:
    """
    Re-Ranker 重訓練器

    使用新收集的資料微調 Cross-Encoder
    """

    def __init__(self, config: TrainingConfig):
        self.config = config

    def train(
        self,
        training_pairs: List[TrainingPair],
        validation_pairs: List[TrainingPair]
    ) -> Dict[str, Any]:
        """
        執行訓練

        Args:
            training_pairs: 訓練資料
            validation_pairs: 驗證資料

        Returns:
            訓練結果（包含模型路徑、指標等）
        """
        logger.info(f"開始訓練，訓練樣本數：{len(training_pairs)}")

        # 準備訓練資料格式
        train_samples = self._prepare_samples(training_pairs)
        val_samples = self._prepare_samples(validation_pairs)

        # 實際訓練代碼（使用 sentence-transformers）
        # from sentence_transformers import CrossEncoder
        # model = CrossEncoder(self.config.base_model)
        # model.fit(
        #     train_dataloader=...,
        #     epochs=self.config.epochs,
        #     ...
        # )

        # 模擬訓練結果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = f"{self.config.output_dir}/reranker_{timestamp}"

        result = {
            "model_path": model_path,
            "training_samples": len(training_pairs),
            "validation_samples": len(validation_pairs),
            "epochs": self.config.epochs,
            "timestamp": timestamp,
            "metrics": {
                "train_loss": 0.15,
                "val_loss": 0.18,
                "val_mrr": 0.85
            }
        }

        logger.info(f"訓練完成，模型儲存於：{model_path}")
        return result

    def _prepare_samples(
        self,
        pairs: List[TrainingPair]
    ) -> List[Dict[str, Any]]:
        """將訓練對轉換為模型輸入格式"""
        samples = []

        for pair in pairs:
            # 正樣本
            samples.append({
                "query": pair.query,
                "document": pair.positive_doc,
                "label": 1
            })

            # 負樣本
            for neg_doc in pair.negative_docs:
                samples.append({
                    "query": pair.query,
                    "document": neg_doc,
                    "label": 0
                })

        return samples


# ═══════════════════════════════════════════════════════════════
# 模型版本管理
# ═══════════════════════════════════════════════════════════════

@dataclass
class ModelVersion:
    """模型版本"""
    version_id: str
    model_path: str
    created_at: datetime
    metrics: Dict[str, float]
    status: str = "candidate"  # candidate / production / archived
    trigger_type: Optional[TriggerType] = None
    training_samples: int = 0


class ModelRegistry:
    """
    模型註冊表

    管理模型版本，支援回滾
    """

    def __init__(self, registry_path: str = "./model_registry"):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.versions: List[ModelVersion] = []
        self._load_registry()

    def _load_registry(self):
        """載入註冊表"""
        registry_file = self.registry_path / "registry.json"
        if registry_file.exists():
            with open(registry_file) as f:
                data = json.load(f)
                self.versions = [
                    ModelVersion(
                        version_id=v["version_id"],
                        model_path=v["model_path"],
                        created_at=datetime.fromisoformat(v["created_at"]),
                        metrics=v["metrics"],
                        status=v["status"],
                        trigger_type=TriggerType(v["trigger_type"]) if v.get("trigger_type") else None,
                        training_samples=v.get("training_samples", 0)
                    )
                    for v in data["versions"]
                ]

    def _save_registry(self):
        """儲存註冊表"""
        registry_file = self.registry_path / "registry.json"
        data = {
            "versions": [
                {
                    "version_id": v.version_id,
                    "model_path": v.model_path,
                    "created_at": v.created_at.isoformat(),
                    "metrics": v.metrics,
                    "status": v.status,
                    "trigger_type": v.trigger_type.value if v.trigger_type else None,
                    "training_samples": v.training_samples
                }
                for v in self.versions
            ]
        }
        with open(registry_file, "w") as f:
            json.dump(data, f, indent=2)

    def register(
        self,
        model_path: str,
        metrics: Dict[str, float],
        trigger_type: TriggerType,
        training_samples: int
    ) -> ModelVersion:
        """
        註冊新模型版本

        Args:
            model_path: 模型路徑
            metrics: 評估指標
            trigger_type: 觸發類型
            training_samples: 訓練樣本數

        Returns:
            新版本
        """
        version_id = f"v{len(self.versions) + 1}"

        version = ModelVersion(
            version_id=version_id,
            model_path=model_path,
            created_at=datetime.now(),
            metrics=metrics,
            status="candidate",
            trigger_type=trigger_type,
            training_samples=training_samples
        )

        self.versions.append(version)
        self._save_registry()

        logger.info(f"註冊新版本：{version_id}")
        return version

    def promote_to_production(self, version_id: str) -> bool:
        """
        將版本升級為生產版本

        Args:
            version_id: 版本 ID

        Returns:
            是否成功
        """
        # 找到要升級的版本
        target = None
        for v in self.versions:
            if v.version_id == version_id:
                target = v
                break

        if not target:
            logger.error(f"版本不存在：{version_id}")
            return False

        # 將當前生產版本降級
        for v in self.versions:
            if v.status == "production":
                v.status = "archived"
                logger.info(f"版本 {v.version_id} 已歸檔")

        # 升級目標版本
        target.status = "production"
        self._save_registry()

        logger.info(f"版本 {version_id} 已升級為生產版本")
        return True

    def rollback(self) -> Optional[ModelVersion]:
        """
        回滾到上一個生產版本

        Returns:
            回滾後的版本
        """
        # 找到最近的歸檔版本
        archived = [v for v in self.versions if v.status == "archived"]
        if not archived:
            logger.error("沒有可回滾的版本")
            return None

        # 按時間排序，取最近的
        archived.sort(key=lambda v: v.created_at, reverse=True)
        rollback_target = archived[0]

        # 降級當前生產版本
        for v in self.versions:
            if v.status == "production":
                v.status = "candidate"  # 標記為待觀察

        # 升級回滾目標
        rollback_target.status = "production"
        self._save_registry()

        logger.warning(f"已回滾到版本 {rollback_target.version_id}")
        return rollback_target

    def get_production_version(self) -> Optional[ModelVersion]:
        """取得當前生產版本"""
        for v in self.versions:
            if v.status == "production":
                return v
        return None


# ═══════════════════════════════════════════════════════════════
# 灰度發布
# ═══════════════════════════════════════════════════════════════

class CanaryDeployment:
    """
    灰度發布管理器

    逐步將流量切換到新版本
    """

    def __init__(
        self,
        initial_percentage: float = 5.0,
        increment: float = 10.0,
        success_threshold: float = 0.95
    ):
        self.initial_percentage = initial_percentage
        self.increment = increment
        self.success_threshold = success_threshold
        self.current_percentage = 0.0
        self.metrics_history: List[Dict[str, Any]] = []

    def start_canary(self, new_version_id: str):
        """開始灰度發布"""
        self.current_percentage = self.initial_percentage
        self.metrics_history = []
        logger.info(
            f"開始灰度發布 {new_version_id}，"
            f"初始流量 {self.current_percentage}%"
        )

    def record_metrics(
        self,
        success_rate: float,
        latency_p99: float,
        error_rate: float
    ):
        """記錄灰度期間的指標"""
        self.metrics_history.append({
            "timestamp": datetime.now().isoformat(),
            "percentage": self.current_percentage,
            "success_rate": success_rate,
            "latency_p99": latency_p99,
            "error_rate": error_rate
        })

    def should_increase_traffic(self) -> bool:
        """
        判斷是否應該增加流量

        基於最近的指標判斷
        """
        if not self.metrics_history:
            return False

        # 檢查最近 3 個時間點的指標
        recent = self.metrics_history[-3:]
        avg_success = np.mean([m["success_rate"] for m in recent])

        return avg_success >= self.success_threshold

    def should_rollback(self) -> bool:
        """
        判斷是否應該回滾

        錯誤率過高或成功率驟降
        """
        if not self.metrics_history:
            return False

        recent = self.metrics_history[-3:]
        avg_success = np.mean([m["success_rate"] for m in recent])
        avg_error = np.mean([m["error_rate"] for m in recent])

        return avg_success < 0.8 or avg_error > 0.1

    def increase_traffic(self) -> float:
        """增加流量比例"""
        self.current_percentage = min(
            100.0,
            self.current_percentage + self.increment
        )
        logger.info(f"流量增加至 {self.current_percentage}%")
        return self.current_percentage

    def complete_rollout(self) -> bool:
        """完成全量發布"""
        if self.current_percentage >= 100.0:
            logger.info("灰度發布完成，全量切換")
            return True
        return False


# ═══════════════════════════════════════════════════════════════
# 持續學習 Pipeline 整合
# ═══════════════════════════════════════════════════════════════

class ContinuousLearningPipeline:
    """
    持續學習 Pipeline

    整合所有元件，實現端到端自動化
    """

    def __init__(
        self,
        trigger: RetrainingTrigger,
        data_preparer: TrainingDataPreparer,
        trainer: ReRankerTrainer,
        registry: ModelRegistry,
        canary: CanaryDeployment,
        evaluator  # 評估器（來自第 12 章）
    ):
        self.trigger = trigger
        self.data_preparer = data_preparer
        self.trainer = trainer
        self.registry = registry
        self.canary = canary
        self.evaluator = evaluator

    def run(
        self,
        current_metrics: Dict[str, float],
        feedback_data: List[Dict[str, Any]],
        retrieval_fn,
        test_set
    ) -> Dict[str, Any]:
        """
        執行持續學習流程

        Args:
            current_metrics: 當前系統指標
            feedback_data: 新收集的回饋資料
            retrieval_fn: 檢索函數
            test_set: 測試集

        Returns:
            執行結果
        """
        result = {
            "triggered": False,
            "trigger_type": None,
            "trained": False,
            "deployed": False,
            "version_id": None
        }

        # Step 1: 判斷是否觸發
        should_train, trigger_type = self.trigger.should_retrain(
            current_metrics,
            len(feedback_data)
        )

        if not should_train:
            logger.info("未達觸發條件，跳過訓練")
            return result

        result["triggered"] = True
        result["trigger_type"] = trigger_type.value

        # Step 2: 準備訓練資料
        training_pairs = self.data_preparer.prepare_from_feedback(
            feedback_data, retrieval_fn
        )

        if len(training_pairs) < 100:
            logger.warning(f"訓練資料不足：{len(training_pairs)} 對")
            return result

        # 分割訓練/驗證集
        split_idx = int(len(training_pairs) * 0.9)
        train_pairs = training_pairs[:split_idx]
        val_pairs = training_pairs[split_idx:]

        # Step 3: 訓練模型
        train_result = self.trainer.train(train_pairs, val_pairs)
        result["trained"] = True

        # Step 4: 評估新模型
        # new_metrics = self.evaluator.evaluate(test_set, new_rag_fn)

        # 模擬評估結果
        new_metrics = {
            "recall@5": current_metrics.get("recall@5", 0.7) + 0.03,
            "mrr": current_metrics.get("mrr", 0.6) + 0.02,
            "latency_p99": 150
        }

        # Step 5: 註冊新版本
        new_version = self.registry.register(
            model_path=train_result["model_path"],
            metrics=new_metrics,
            trigger_type=trigger_type,
            training_samples=len(training_pairs)
        )
        result["version_id"] = new_version.version_id

        # Step 6: 決策是否部署
        current_production = self.registry.get_production_version()

        if current_production:
            # 比較指標
            improvement = (
                new_metrics["recall@5"] -
                current_production.metrics.get("recall@5", 0)
            )

            if improvement > 0.01:  # 至少 1% 提升才部署
                logger.info(
                    f"新版本指標提升 {improvement:.1%}，開始灰度發布"
                )
                self.canary.start_canary(new_version.version_id)
                result["deployed"] = True
            else:
                logger.info("新版本未顯著優於現有版本，暫不部署")
        else:
            # 沒有生產版本，直接部署
            self.registry.promote_to_production(new_version.version_id)
            result["deployed"] = True

        # 更新 baseline
        self.trigger.baseline_metrics = new_metrics
        self.trigger.last_training_time = datetime.now()

        return result


# ═══════════════════════════════════════════════════════════════
# 示範用法
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 初始化各元件
    trigger = RetrainingTrigger(TriggerCondition(
        schedule_interval_days=7,
        performance_threshold=0.05,
        min_feedback_count=500
    ))

    data_preparer = TrainingDataPreparer()
    trainer = ReRankerTrainer(TrainingConfig())
    registry = ModelRegistry()
    canary = CanaryDeployment()

    # 模擬回饋資料
    mock_feedback = [
        {
            "query": "如何重設密碼？",
            "feedback_type": "positive",
            "answer_source": "DOC001"
        },
        {
            "query": "退貨流程是什麼？",
            "feedback_type": "negative",
            "answer_source": "DOC010",
            "correct_source": "DOC011"
        }
    ] * 300  # 模擬 600 條回饋

    # 模擬當前指標
    current_metrics = {
        "recall@5": 0.72,
        "mrr": 0.65
    }

    # 設定 baseline（模擬之前的表現）
    trigger.baseline_metrics = {"recall@5": 0.75, "mrr": 0.68}

    # 模擬檢索函數
    def mock_retrieval(query: str, top_k: int = 10) -> List[str]:
        return [f"DOC{i:03d}" for i in range(top_k)]

    print("=== 持續學習 Pipeline Demo ===\n")

    # 檢查觸發條件
    should_train, trigger_type = trigger.should_retrain(
        current_metrics, len(mock_feedback)
    )

    if should_train:
        print(f"觸發重訓練，原因：{trigger_type.value}")

        # 準備訓練資料
        pairs = data_preparer.prepare_from_feedback(
            mock_feedback, mock_retrieval
        )
        print(f"準備了 {len(pairs)} 組訓練資料")

        # 執行訓練
        result = trainer.train(pairs[:int(len(pairs)*0.9)], pairs[int(len(pairs)*0.9):])
        print(f"訓練完成：{result['model_path']}")

        # 註冊版本
        version = registry.register(
            model_path=result["model_path"],
            metrics={"recall@5": 0.76, "mrr": 0.69},
            trigger_type=trigger_type,
            training_samples=len(pairs)
        )
        print(f"註冊新版本：{version.version_id}")

        # 升級為生產
        registry.promote_to_production(version.version_id)
        print(f"已部署到生產環境")
    else:
        print("未觸發重訓練")
