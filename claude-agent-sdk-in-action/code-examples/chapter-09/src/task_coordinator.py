"""
Task Coordinator - 協調層

負責任務調度、依賴管理、並行執行、錯誤處理
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime
import logging

from meta_agent import Task, ExecutionPlan, TaskType

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任務狀態"""
    PENDING = "pending"  # 等待執行
    READY = "ready"  # 依賴已滿足，可執行
    RUNNING = "running"  # 執行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失敗
    RETRYING = "retrying"  # 重試中


@dataclass
class TaskExecution:
    """任務執行狀態"""
    task: Task
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_attempts: int = 0
    subagent_id: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """執行時長（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def is_terminal(self) -> bool:
        """是否為終態"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]


class TaskCoordinator:
    """
    任務協調器 - 負責任務調度與執行

    核心職責：
    1. 管理任務依賴關係
    2. 調度任務執行（串行/並行）
    3. 監控任務狀態
    4. 處理錯誤與重試
    5. 收集執行結果
    """

    def __init__(
        self,
        plan: ExecutionPlan,
        max_parallel: int = 3,
        api_key: str = None
    ):
        self.plan = plan
        self.max_parallel = max_parallel
        self.api_key = api_key

        # 初始化任務執行狀態
        self.executions: Dict[str, TaskExecution] = {}
        for task in plan.tasks:
            self.executions[task.id] = TaskExecution(task=task)

        # 執行統計
        self.stats = {
            "total_tasks": len(plan.tasks),
            "completed": 0,
            "failed": 0,
            "total_time": 0,
            "start_time": None,
            "end_time": None
        }

    async def execute_plan(self) -> Dict[str, Any]:
        """
        執行整個計畫

        Returns:
            執行結果摘要
        """
        logger.info(f"開始執行計畫：{self.plan.project_name}")
        logger.info(f"總任務數：{self.stats['total_tasks']}")
        logger.info(f"最大並行數：{self.max_parallel}")

        self.stats["start_time"] = datetime.now()

        try:
            # 主執行迴圈
            iteration = 0
            while not self._all_tasks_terminal():
                iteration += 1
                logger.debug(f"執行迴圈第 {iteration} 輪")

                # 獲取可執行的任務
                ready_tasks = self._get_ready_tasks()

                if not ready_tasks:
                    # 沒有可執行任務，檢查是否有死鎖
                    running_count = sum(
                        1 for e in self.executions.values()
                        if e.status == TaskStatus.RUNNING
                    )

                    if running_count == 0 and not self._all_tasks_terminal():
                        if self._has_deadlock():
                            raise RuntimeError("偵測到任務死鎖：存在循環依賴或無法執行的任務")

                    # 等待運行中的任務完成
                    await asyncio.sleep(1)
                    continue

                # 並行執行任務（受 max_parallel 限制）
                current_running = sum(
                    1 for e in self.executions.values()
                    if e.status == TaskStatus.RUNNING
                )
                available_slots = self.max_parallel - current_running
                tasks_to_run = ready_tasks[:available_slots]

                if tasks_to_run:
                    logger.info(
                        f"準備執行 {len(tasks_to_run)} 個任務："
                        f"{', '.join(t.name for t in tasks_to_run)}"
                    )

                    # 創建並行任務
                    execution_tasks = [
                        self._execute_task(task)
                        for task in tasks_to_run
                    ]

                    # 啟動並行執行（不等待完成）
                    for task_coro in execution_tasks:
                        asyncio.create_task(task_coro)

                # 短暫等待
                await asyncio.sleep(0.5)

            # 等待所有任務真正完成
            while any(e.status == TaskStatus.RUNNING for e in self.executions.values()):
                await asyncio.sleep(0.5)

            # 計算總時間
            self.stats["end_time"] = datetime.now()
            self.stats["total_time"] = (
                self.stats["end_time"] - self.stats["start_time"]
            ).total_seconds()

            # 生成執行報告
            return self._generate_report()

        except Exception as e:
            logger.error(f"執行計畫時發生錯誤：{e}")
            raise

    def _get_ready_tasks(self) -> List[Task]:
        """
        獲取所有依賴已滿足且尚未執行的任務
        """
        ready_tasks = []

        for task_id, execution in self.executions.items():
            # 跳過已完成、運行中或失敗的任務
            if execution.status in [TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED]:
                continue

            # 檢查依賴是否都已完成
            dependencies_met = all(
                self.executions[dep_id].status == TaskStatus.COMPLETED
                for dep_id in execution.task.dependencies
                if dep_id in self.executions
            )

            if dependencies_met:
                execution.status = TaskStatus.READY
                ready_tasks.append(execution.task)

        # 按優先級排序
        ready_tasks.sort(key=lambda t: t.priority.value)

        return ready_tasks

    async def _execute_task(self, task: Task) -> None:
        """
        執行單個任務
        """
        execution = self.executions[task.id]
        execution.status = TaskStatus.RUNNING
        execution.start_time = datetime.now()

        logger.info(f"[{task.id}] 開始執行：{task.name}")

        try:
            # 創建 Subagent 執行任務
            from subagent_executor import SubagentExecutor
            executor = SubagentExecutor(api_key=self.api_key)

            result = await executor.execute(task)

            # 記錄結果
            execution.result = result
            execution.status = TaskStatus.COMPLETED
            execution.end_time = datetime.now()

            self.stats["completed"] += 1

            logger.info(
                f"[{task.id}] ✅ 完成 "
                f"({execution.duration:.1f}秒)"
            )

        except Exception as e:
            logger.error(f"[{task.id}] ❌ 執行失敗：{e}")

            # 重試邏輯
            execution.retry_attempts += 1

            if execution.retry_attempts < task.retry_count:
                execution.status = TaskStatus.RETRYING
                logger.info(
                    f"[{task.id}] 🔄 準備重試 "
                    f"({execution.retry_attempts}/{task.retry_count})"
                )

                # 指數退避
                wait_time = 2 ** execution.retry_attempts
                await asyncio.sleep(wait_time)
                await self._execute_task(task)
            else:
                # 重試次數用盡
                execution.status = TaskStatus.FAILED
                execution.error = str(e)
                execution.end_time = datetime.now()
                self.stats["failed"] += 1

                logger.error(
                    f"[{task.id}] ❌ 最終失敗（已重試 {execution.retry_attempts} 次）"
                )

    def _all_tasks_terminal(self) -> bool:
        """檢查是否所有任務都已達到終態"""
        return all(
            execution.is_terminal
            for execution in self.executions.values()
        )

    def _has_deadlock(self) -> bool:
        """
        偵測循環依賴（死鎖）

        使用拓撲排序算法檢測
        """
        # 只檢查未完成的任務
        pending_tasks = {
            task_id: execution.task
            for task_id, execution in self.executions.items()
            if not execution.is_terminal
        }

        if not pending_tasks:
            return False

        # 計算入度
        in_degree = {task_id: 0 for task_id in pending_tasks}
        for task in pending_tasks.values():
            for dep_id in task.dependencies:
                if dep_id in in_degree:
                    in_degree[dep_id] += 1

        # 找出所有入度為 0 的節點
        queue = [
            task_id
            for task_id, degree in in_degree.items()
            if degree == 0
        ]

        processed = 0
        while queue:
            current = queue.pop(0)
            processed += 1

            # 找出依賴當前節點的任務
            for task_id, task in pending_tasks.items():
                if current in task.dependencies and task_id in in_degree:
                    in_degree[task_id] -= 1
                    if in_degree[task_id] == 0:
                        queue.append(task_id)

        # 如果處理的節點數少於總節點數，存在循環依賴
        return processed < len(pending_tasks)

    def _generate_report(self) -> Dict[str, Any]:
        """
        生成執行報告
        """
        completed_tasks = [
            {
                "id": exec.task.id,
                "name": exec.task.name,
                "duration": exec.duration,
                "result": exec.result
            }
            for exec in self.executions.values()
            if exec.status == TaskStatus.COMPLETED
        ]

        failed_tasks = [
            {
                "id": exec.task.id,
                "name": exec.task.name,
                "error": exec.error,
                "retry_attempts": exec.retry_attempts
            }
            for exec in self.executions.values()
            if exec.status == TaskStatus.FAILED
        ]

        return {
            "summary": {
                "total_tasks": self.stats["total_tasks"],
                "completed": self.stats["completed"],
                "failed": self.stats["failed"],
                "success_rate": self.stats["completed"] / self.stats["total_tasks"] if self.stats["total_tasks"] > 0 else 0,
                "total_time": self.stats["total_time"],
                "estimated_time": self.plan.estimated_total_time,
                "time_efficiency": self.plan.estimated_total_time / self.stats["total_time"] if self.stats["total_time"] > 0 else 0
            },
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "critical_path_time": self._calculate_critical_path_time()
        }

    def _calculate_critical_path_time(self) -> float:
        """計算關鍵路徑實際耗時"""
        total = 0
        for task_id in self.plan.critical_path:
            execution = self.executions.get(task_id)
            if execution and execution.duration:
                total += execution.duration
        return total
