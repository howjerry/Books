#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 5 章：工具調用與軌跡收集
軌跡收集器完整實現

這個模組實現了完整的軌跡收集系統，包含：
1. 軌跡資料結構定義
2. 軌跡收集與持久化
3. 獎勵信號計算
4. RLEF 訓練資料生成

使用方式：
    python trajectory_collector.py
    python trajectory_collector.py --demo
    python trajectory_collector.py --export trajectories.jsonl
"""

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv

# 載入環境變數
load_dotenv()


# =============================================================================
# 軌跡資料結構
# =============================================================================

class StepType(Enum):
    """步驟類型"""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"


@dataclass
class TrajectoryStep:
    """
    軌跡步驟

    ‹1› 每個步驟記錄思考、行動或觀察
    ‹2› 包含時間戳和元數據
    """
    step_type: StepType
    content: Any
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step_type": self.step_type.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrajectoryStep":
        return cls(
            step_type=StepType(data["step_type"]),
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {})
        )


@dataclass
class ToolCall:
    """
    工具調用記錄

    ‹1› 記錄工具名稱和參數
    ‹2› 追蹤執行結果和時間
    """
    tool_name: str
    arguments: Dict[str, Any]
    result: Any = None
    success: bool = False
    execution_time: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "success": self.success,
            "execution_time": self.execution_time,
            "error": self.error
        }


@dataclass
class Trajectory:
    """
    完整軌跡

    ‹1› 包含所有 Thought-Action-Observation 步驟
    ‹2› 記錄任務資訊和最終結果
    ‹3› 支援獎勵信號標註
    """
    trajectory_id: str
    task_query: str
    steps: List[TrajectoryStep] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    final_answer: Optional[str] = None
    success: bool = False
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    rewards: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """計算總耗時"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def total_tokens(self) -> int:
        """估算總 token 數"""
        total = 0
        for step in self.steps:
            if isinstance(step.content, str):
                total += len(step.content) // 3
            elif isinstance(step.content, dict):
                total += len(json.dumps(step.content, ensure_ascii=False)) // 3
        return total

    def add_thought(self, content: str, **metadata) -> None:
        """添加思考步驟"""
        self.steps.append(TrajectoryStep(
            step_type=StepType.THOUGHT,
            content=content,
            metadata=metadata
        ))

    def add_action(self, tool_name: str, arguments: dict, **metadata) -> ToolCall:
        """添加行動步驟"""
        tool_call = ToolCall(
            tool_name=tool_name,
            arguments=arguments
        )
        self.tool_calls.append(tool_call)

        self.steps.append(TrajectoryStep(
            step_type=StepType.ACTION,
            content={
                "tool_name": tool_name,
                "arguments": arguments
            },
            metadata=metadata
        ))

        return tool_call

    def add_observation(self, content: Any, tool_call: Optional[ToolCall] = None, **metadata) -> None:
        """添加觀察步驟"""
        if tool_call:
            tool_call.result = content
            tool_call.success = True

        self.steps.append(TrajectoryStep(
            step_type=StepType.OBSERVATION,
            content=content,
            metadata=metadata
        ))

    def complete(self, final_answer: str, success: bool = True) -> None:
        """完成軌跡記錄"""
        self.final_answer = final_answer
        self.success = success
        self.end_time = time.time()

    def to_dict(self) -> dict:
        return {
            "trajectory_id": self.trajectory_id,
            "task_query": self.task_query,
            "steps": [step.to_dict() for step in self.steps],
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "final_answer": self.final_answer,
            "success": self.success,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "total_tokens": self.total_tokens,
            "rewards": self.rewards,
            "metadata": self.metadata
        }

    def to_training_format(self) -> dict:
        """轉換為訓練格式（RLEF 格式）"""
        return {
            "id": self.trajectory_id,
            "query": self.task_query,
            "trajectory": [step.to_dict() for step in self.steps],
            "answer": self.final_answer,
            "reward": sum(self.rewards.values()) if self.rewards else 0.0,
            "reward_breakdown": self.rewards,
            "metadata": {
                "duration": self.duration,
                "tool_count": len(self.tool_calls),
                "step_count": len(self.steps),
                "success": self.success
            }
        }


# =============================================================================
# 獎勵計算器
# =============================================================================

class RewardCalculator:
    """
    獎勵計算器

    ‹1› 多維度獎勵信號設計
    ‹2› 支援自訂權重
    ‹3› 提供獎勵分解報告
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "task_completion": 0.30,
            "tool_efficiency": 0.20,
            "answer_quality": 0.25,
            "factual_accuracy": 0.15,
            "token_efficiency": 0.10
        }

    def calculate(
        self,
        trajectory: Trajectory,
        ground_truth: Optional[str] = None,
        quality_score: Optional[float] = None
    ) -> Dict[str, float]:
        """
        計算軌跡的獎勵信號

        ‹1› 任務完成度：是否成功完成任務
        ‹2› 工具效率：工具使用的效率
        ‹3› 答案品質：答案的品質評估
        ‹4› 事實準確度：與真實答案的吻合度
        ‹5› Token 效率：使用的 token 數量
        """
        rewards = {}

        # 1. 任務完成度
        rewards["task_completion"] = self._calc_task_completion(trajectory)

        # 2. 工具效率
        rewards["tool_efficiency"] = self._calc_tool_efficiency(trajectory)

        # 3. 答案品質
        rewards["answer_quality"] = self._calc_answer_quality(
            trajectory, quality_score
        )

        # 4. 事實準確度
        rewards["factual_accuracy"] = self._calc_factual_accuracy(
            trajectory, ground_truth
        )

        # 5. Token 效率
        rewards["token_efficiency"] = self._calc_token_efficiency(trajectory)

        # 計算加權總分
        total = sum(
            rewards[k] * self.weights.get(k, 0)
            for k in rewards
        )
        rewards["total"] = total

        return rewards

    def _calc_task_completion(self, trajectory: Trajectory) -> float:
        """計算任務完成度"""
        if not trajectory.success:
            return 0.0

        if trajectory.final_answer:
            # 有答案得基礎分
            score = 0.6

            # 答案長度合理性
            answer_len = len(trajectory.final_answer)
            if 100 <= answer_len <= 2000:
                score += 0.2
            elif 50 <= answer_len <= 5000:
                score += 0.1

            # 有使用工具得額外分
            if trajectory.tool_calls:
                score += 0.2

            return min(score, 1.0)

        return 0.3  # 完成但無答案

    def _calc_tool_efficiency(self, trajectory: Trajectory) -> float:
        """計算工具使用效率"""
        if not trajectory.tool_calls:
            return 0.5  # 沒有使用工具，中性評價

        total_calls = len(trajectory.tool_calls)
        successful_calls = sum(1 for tc in trajectory.tool_calls if tc.success)

        # 成功率
        success_rate = successful_calls / total_calls

        # 工具多樣性（使用不同種類的工具）
        unique_tools = len(set(tc.tool_name for tc in trajectory.tool_calls))
        diversity_bonus = min(unique_tools * 0.1, 0.3)

        # 避免過度使用（超過 10 次扣分）
        overuse_penalty = max(0, (total_calls - 10) * 0.05)

        score = success_rate * 0.7 + diversity_bonus - overuse_penalty

        return max(0, min(score, 1.0))

    def _calc_answer_quality(
        self,
        trajectory: Trajectory,
        quality_score: Optional[float] = None
    ) -> float:
        """計算答案品質"""
        if quality_score is not None:
            return quality_score

        # 簡易評估（實際應使用 LLM 評估）
        if not trajectory.final_answer:
            return 0.0

        answer = trajectory.final_answer
        score = 0.0

        # 長度評估
        if len(answer) >= 100:
            score += 0.3

        # 結構評估（是否有條理）
        if any(marker in answer for marker in ['1.', '•', '-', '首先', '其次']):
            score += 0.2

        # 引用來源
        if any(marker in answer for marker in ['根據', '來源', '參考', '研究顯示']):
            score += 0.2

        # 有具體數據
        import re
        if re.search(r'\d+%|\d+\.\d+|第\d+', answer):
            score += 0.15

        # 有結論
        if any(marker in answer for marker in ['總結', '結論', '綜上所述', '因此']):
            score += 0.15

        return min(score, 1.0)

    def _calc_factual_accuracy(
        self,
        trajectory: Trajectory,
        ground_truth: Optional[str] = None
    ) -> float:
        """計算事實準確度"""
        if not ground_truth or not trajectory.final_answer:
            return 0.5  # 無法評估時給中性分數

        # 簡易文字相似度（實際應使用更複雜的評估）
        answer_words = set(trajectory.final_answer.lower().split())
        truth_words = set(ground_truth.lower().split())

        if not truth_words:
            return 0.5

        overlap = len(answer_words & truth_words)
        recall = overlap / len(truth_words)
        precision = overlap / len(answer_words) if answer_words else 0

        # F1 分數
        if precision + recall > 0:
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = 0

        return f1

    def _calc_token_efficiency(self, trajectory: Trajectory) -> float:
        """計算 Token 效率"""
        total_tokens = trajectory.total_tokens

        # 理想範圍：1000-5000 tokens
        if 1000 <= total_tokens <= 5000:
            return 1.0
        elif 500 <= total_tokens < 1000:
            return 0.8
        elif 5000 < total_tokens <= 10000:
            return 0.7
        elif 10000 < total_tokens <= 20000:
            return 0.5
        elif total_tokens < 500:
            return 0.6  # 太少可能不夠深入
        else:
            return 0.3  # 超過 20000 效率低


# =============================================================================
# 軌跡收集器
# =============================================================================

class TrajectoryCollector:
    """
    軌跡收集器

    ‹1› 管理軌跡的生命週期
    ‹2› 支援持久化存儲
    ‹3› 提供軌跡查詢和過濾
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        auto_save: bool = True
    ):
        self.storage_path = storage_path or "./trajectories"
        self.auto_save = auto_save
        self.trajectories: Dict[str, Trajectory] = {}
        self.reward_calculator = RewardCalculator()

        # 確保存儲目錄存在
        os.makedirs(self.storage_path, exist_ok=True)

    def _generate_id(self, query: str) -> str:
        """生成軌跡 ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"traj_{timestamp}_{query_hash}"

    def start_trajectory(self, query: str, **metadata) -> Trajectory:
        """
        開始新軌跡

        ‹1› 創建軌跡物件
        ‹2› 註冊到收集器
        """
        trajectory_id = self._generate_id(query)
        trajectory = Trajectory(
            trajectory_id=trajectory_id,
            task_query=query,
            metadata=metadata
        )
        self.trajectories[trajectory_id] = trajectory
        return trajectory

    def complete_trajectory(
        self,
        trajectory: Trajectory,
        final_answer: str,
        success: bool = True,
        ground_truth: Optional[str] = None,
        quality_score: Optional[float] = None
    ) -> Dict[str, float]:
        """
        完成軌跡記錄

        ‹1› 標記完成
        ‹2› 計算獎勵
        ‹3› 自動保存
        """
        trajectory.complete(final_answer, success)

        # 計算獎勵
        rewards = self.reward_calculator.calculate(
            trajectory,
            ground_truth=ground_truth,
            quality_score=quality_score
        )
        trajectory.rewards = rewards

        # 自動保存
        if self.auto_save:
            self.save_trajectory(trajectory)

        return rewards

    def save_trajectory(self, trajectory: Trajectory) -> str:
        """保存軌跡到檔案"""
        file_path = os.path.join(
            self.storage_path,
            f"{trajectory.trajectory_id}.json"
        )
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(trajectory.to_dict(), f, ensure_ascii=False, indent=2)
        return file_path

    def load_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """從檔案載入軌跡"""
        file_path = os.path.join(
            self.storage_path,
            f"{trajectory_id}.json"
        )
        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        trajectory = Trajectory(
            trajectory_id=data["trajectory_id"],
            task_query=data["task_query"],
            final_answer=data.get("final_answer"),
            success=data.get("success", False),
            start_time=data.get("start_time", time.time()),
            end_time=data.get("end_time"),
            rewards=data.get("rewards", {}),
            metadata=data.get("metadata", {})
        )

        # 重建步驟
        for step_data in data.get("steps", []):
            trajectory.steps.append(TrajectoryStep.from_dict(step_data))

        # 重建工具調用
        for tc_data in data.get("tool_calls", []):
            trajectory.tool_calls.append(ToolCall(**tc_data))

        return trajectory

    def export_for_training(
        self,
        output_path: str,
        min_reward: float = 0.0,
        format: str = "jsonl"
    ) -> int:
        """
        匯出訓練資料

        ‹1› 過濾低品質軌跡
        ‹2› 轉換為訓練格式
        ‹3› 支援 JSONL 格式
        """
        exported = 0

        with open(output_path, 'w', encoding='utf-8') as f:
            for trajectory in self.trajectories.values():
                # 過濾低品質軌跡
                total_reward = trajectory.rewards.get("total", 0)
                if total_reward < min_reward:
                    continue

                training_data = trajectory.to_training_format()

                if format == "jsonl":
                    f.write(json.dumps(training_data, ensure_ascii=False) + "\n")
                else:
                    json.dump(training_data, f, ensure_ascii=False)
                    f.write("\n")

                exported += 1

        return exported

    def get_statistics(self) -> Dict[str, Any]:
        """獲取軌跡統計"""
        if not self.trajectories:
            return {"total": 0}

        total = len(self.trajectories)
        successful = sum(1 for t in self.trajectories.values() if t.success)
        rewards = [
            t.rewards.get("total", 0)
            for t in self.trajectories.values()
            if t.rewards
        ]

        return {
            "total": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0,
            "avg_reward": sum(rewards) / len(rewards) if rewards else 0,
            "min_reward": min(rewards) if rewards else 0,
            "max_reward": max(rewards) if rewards else 0,
            "avg_steps": sum(len(t.steps) for t in self.trajectories.values()) / total,
            "avg_tools": sum(len(t.tool_calls) for t in self.trajectories.values()) / total
        }

    def filter_trajectories(
        self,
        min_reward: Optional[float] = None,
        max_reward: Optional[float] = None,
        success_only: bool = False,
        min_tools: int = 0
    ) -> List[Trajectory]:
        """過濾軌跡"""
        result = []
        for trajectory in self.trajectories.values():
            total_reward = trajectory.rewards.get("total", 0)

            if min_reward is not None and total_reward < min_reward:
                continue
            if max_reward is not None and total_reward > max_reward:
                continue
            if success_only and not trajectory.success:
                continue
            if len(trajectory.tool_calls) < min_tools:
                continue

            result.append(trajectory)

        return result


# =============================================================================
# 軌跡回放器
# =============================================================================

class TrajectoryReplayer:
    """
    軌跡回放器

    ‹1› 視覺化展示軌跡
    ‹2› 支援步驟級別回放
    """

    def replay(self, trajectory: Trajectory, delay: float = 0.5) -> None:
        """回放軌跡"""
        print("=" * 60)
        print(f"🎬 回放軌跡: {trajectory.trajectory_id}")
        print(f"📝 任務: {trajectory.task_query}")
        print("=" * 60)

        for i, step in enumerate(trajectory.steps, 1):
            time.sleep(delay)

            if step.step_type == StepType.THOUGHT:
                print(f"\n💭 [{i}] 思考")
                print(f"   {step.content[:200]}..." if len(str(step.content)) > 200 else f"   {step.content}")

            elif step.step_type == StepType.ACTION:
                content = step.content
                print(f"\n🔧 [{i}] 行動")
                print(f"   工具: {content['tool_name']}")
                print(f"   參數: {json.dumps(content['arguments'], ensure_ascii=False)[:100]}...")

            elif step.step_type == StepType.OBSERVATION:
                print(f"\n👁️ [{i}] 觀察")
                content_str = str(step.content)
                print(f"   {content_str[:200]}..." if len(content_str) > 200 else f"   {content_str}")

        print("\n" + "=" * 60)
        print("📊 軌跡摘要")
        print("=" * 60)
        print(f"   總步驟數: {len(trajectory.steps)}")
        print(f"   工具調用: {len(trajectory.tool_calls)}")
        print(f"   總耗時: {trajectory.duration:.2f}s")
        print(f"   成功: {'✅' if trajectory.success else '❌'}")

        if trajectory.rewards:
            print(f"\n📈 獎勵信號:")
            for key, value in trajectory.rewards.items():
                print(f"   • {key}: {value:.3f}")

        if trajectory.final_answer:
            print(f"\n📝 最終答案:")
            answer_preview = trajectory.final_answer[:300]
            print(f"   {answer_preview}...")


# =============================================================================
# 示範功能
# =============================================================================

def demo_trajectory_collection():
    """展示軌跡收集系統"""
    print("=" * 60)
    print("📊 軌跡收集系統示範")
    print("=" * 60)

    # 創建收集器
    collector = TrajectoryCollector(
        storage_path="./demo_trajectories",
        auto_save=True
    )

    # 模擬研究任務
    query = "分析 2024 年全球 AI 晶片市場的主要競爭格局"

    print(f"\n📝 開始記錄軌跡: {query}")

    # 開始軌跡
    trajectory = collector.start_trajectory(
        query,
        source="demo",
        model="gpt-4o-mini"
    )

    # 模擬 ReAct 循環
    print("\n🔄 模擬 ReAct 循環...")

    # 步驟 1: 思考
    trajectory.add_thought(
        "這是一個關於 AI 晶片市場的研究問題。我需要：\n"
        "1. 搜尋市場規模數據\n"
        "2. 識別主要競爭者\n"
        "3. 分析各廠商的市場份額"
    )
    print("   💭 添加思考步驟")

    # 步驟 2: 行動
    tool_call = trajectory.add_action(
        "web_search",
        {"query": "2024 AI 晶片市場規模 NVIDIA AMD Intel", "num_results": 5}
    )
    print("   🔧 添加行動步驟: web_search")

    # 步驟 3: 觀察
    trajectory.add_observation(
        {
            "results": [
                {"title": "2024 全球 AI 晶片市場報告", "snippet": "市場規模達 500 億美元..."},
                {"title": "NVIDIA 市場份額分析", "snippet": "NVIDIA 佔據 80% 以上市場..."},
            ]
        },
        tool_call
    )
    print("   👁️ 添加觀察步驟")

    # 步驟 4: 進一步思考
    trajectory.add_thought(
        "搜尋結果顯示 NVIDIA 佔主導地位。需要進一步了解：\n"
        "1. 其他競爭者的策略\n"
        "2. 新興廠商的崛起"
    )
    print("   💭 添加思考步驟")

    # 步驟 5: 另一個行動
    tool_call2 = trajectory.add_action(
        "web_browser",
        {"url": "https://example.com/ai-chip-report-2024", "extract_text": True}
    )
    print("   🔧 添加行動步驟: web_browser")

    # 步驟 6: 觀察
    trajectory.add_observation(
        "根據報告，2024 年 AI 晶片市場呈現以下格局：\n"
        "1. NVIDIA 以 80% 市場份額領先\n"
        "2. AMD 積極追趕，佔 10%\n"
        "3. Intel 正在轉型，佔 5%\n"
        "4. 其他新興廠商共佔 5%",
        tool_call2
    )
    print("   👁️ 添加觀察步驟")

    # 完成軌跡
    final_answer = """
2024 年全球 AI 晶片市場競爭格局分析：

## 市場規模
全球 AI 晶片市場規模約 500 億美元，年增長率超過 30%。

## 主要競爭者
1. **NVIDIA（約 80%）**：憑藉 CUDA 生態系統和 GPU 架構優勢，牢牢佔據市場主導地位。
2. **AMD（約 10%）**：通過 MI300 系列積極追趕，在性價比方面有優勢。
3. **Intel（約 5%）**：正在從 CPU 向 AI 加速器轉型，推出 Gaudi 系列。
4. **其他（約 5%）**：包括華為昇騰、Google TPU 等。

## 趨勢分析
- 雲端訓練市場 NVIDIA 佔絕對優勢
- 邊緣推理市場競爭更加激烈
- 開放標準（如 OpenAI Triton）可能改變格局
"""

    rewards = collector.complete_trajectory(
        trajectory,
        final_answer=final_answer,
        success=True
    )

    print("\n✅ 軌跡完成")

    # 顯示獎勵
    print("\n" + "=" * 60)
    print("📈 獎勵信號")
    print("=" * 60)
    for key, value in rewards.items():
        bar = "█" * int(value * 20)
        print(f"   {key:20s}: {value:.3f} {bar}")

    # 統計
    print("\n" + "=" * 60)
    print("📊 收集器統計")
    print("=" * 60)
    stats = collector.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.3f}")
        else:
            print(f"   {key}: {value}")

    # 回放
    print("\n")
    replayer = TrajectoryReplayer()
    replayer.replay(trajectory, delay=0.3)

    # 匯出訓練資料
    export_path = "./demo_trajectories/training_data.jsonl"
    count = collector.export_for_training(export_path, min_reward=0.3)
    print(f"\n📤 已匯出 {count} 條訓練資料到 {export_path}")


# =============================================================================
# 主程式
# =============================================================================

def main():
    """主程式入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="軌跡收集器 - 第 5 章範例"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="執行示範模式"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="匯出訓練資料到指定路徑"
    )

    args = parser.parse_args()

    if args.export:
        collector = TrajectoryCollector()
        count = collector.export_for_training(args.export)
        print(f"已匯出 {count} 條訓練資料")
    else:
        demo_trajectory_collection()


if __name__ == "__main__":
    main()
