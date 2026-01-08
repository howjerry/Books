#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 10 章：多代理人協作系統
任務調度器

這個模組實現了智能任務調度：
1. 拓撲排序確定執行順序
2. 最大化平行度
3. 動態依賴管理

使用方式：
    python scheduler.py --demo
"""

import asyncio
import argparse
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Awaitable
from collections import defaultdict


# =============================================================================
# 資料結構
# =============================================================================

class TaskStatus(Enum):
    """任務狀態"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class SchedulableTask:
    """
    可調度任務

    ‹1› 包含調度所需的所有資訊
    ‹2› 支援優先級與依賴管理
    """
    task_id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    priority: int = 1  # 1-10，10 最高
    estimated_duration: float = 1.0  # 預估耗時（秒）
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    max_retries: int = 3

    @property
    def is_ready(self) -> bool:
        """是否就緒可執行"""
        return self.status == TaskStatus.READY

    @property
    def is_done(self) -> bool:
        """是否已完成（成功或失敗）"""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    @property
    def actual_duration(self) -> Optional[float]:
        """實際執行時間"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# =============================================================================
# 依賴圖
# =============================================================================

class DependencyGraph:
    """
    依賴圖

    ‹1› 管理任務間的依賴關係
    ‹2› 支援拓撲排序
    ‹3› 檢測循環依賴
    """

    def __init__(self):
        self._graph: Dict[str, Set[str]] = defaultdict(set)  # 任務 -> 依賴的任務
        self._reverse: Dict[str, Set[str]] = defaultdict(set)  # 任務 -> 依賴它的任務
        self._tasks: Dict[str, SchedulableTask] = {}

    def add_task(self, task: SchedulableTask):
        """添加任務"""
        self._tasks[task.task_id] = task
        for dep in task.dependencies:
            self._graph[task.task_id].add(dep)
            self._reverse[dep].add(task.task_id)

    def remove_task(self, task_id: str):
        """移除任務"""
        if task_id in self._tasks:
            del self._tasks[task_id]

        # 清理依賴關係
        if task_id in self._graph:
            del self._graph[task_id]
        if task_id in self._reverse:
            del self._reverse[task_id]

        for deps in self._graph.values():
            deps.discard(task_id)
        for deps in self._reverse.values():
            deps.discard(task_id)

    def get_dependencies(self, task_id: str) -> Set[str]:
        """獲取任務的依賴"""
        return self._graph.get(task_id, set())

    def get_dependents(self, task_id: str) -> Set[str]:
        """獲取依賴該任務的任務"""
        return self._reverse.get(task_id, set())

    def has_cycle(self) -> bool:
        """
        檢測循環依賴

        使用 DFS 檢測圖中是否存在環
        """
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self._graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for task_id in self._tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True

        return False

    def topological_sort(self) -> List[str]:
        """
        拓撲排序

        返回滿足依賴關係的執行順序
        """
        if self.has_cycle():
            raise ValueError("存在循環依賴，無法進行拓撲排序")

        in_degree = defaultdict(int)
        for task_id in self._tasks:
            in_degree[task_id] = len(self._graph.get(task_id, set()))

        # 使用優先級隊列
        queue = []
        for task_id, degree in in_degree.items():
            if degree == 0:
                task = self._tasks[task_id]
                queue.append((-task.priority, task_id))

        queue.sort()
        result = []

        while queue:
            _, task_id = queue.pop(0)
            result.append(task_id)

            for dependent in self._reverse.get(task_id, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    task = self._tasks[dependent]
                    queue.append((-task.priority, dependent))
                    queue.sort()

        return result

    def get_ready_tasks(self, completed: Set[str]) -> List[SchedulableTask]:
        """
        獲取就緒任務

        返回所有依賴已完成的待執行任務
        """
        ready = []
        for task_id, task in self._tasks.items():
            if task.status != TaskStatus.PENDING:
                continue

            deps = self._graph.get(task_id, set())
            if deps.issubset(completed):
                ready.append(task)

        # 按優先級排序
        ready.sort(key=lambda t: -t.priority)
        return ready


# =============================================================================
# 任務調度器
# =============================================================================

class TaskScheduler:
    """
    任務調度器

    ‹1› 管理任務執行順序
    ‹2› 最大化平行度
    ‹3› 處理失敗與重試
    """

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.graph = DependencyGraph()
        self.completed: Set[str] = set()
        self.running: Set[str] = set()
        self._execution_history: List[Dict] = []

    def add_task(self, task: SchedulableTask):
        """添加任務到調度器"""
        self.graph.add_task(task)

    def add_tasks(self, tasks: List[SchedulableTask]):
        """批量添加任務"""
        for task in tasks:
            self.add_task(task)

    def get_ready_tasks(self) -> List[SchedulableTask]:
        """獲取就緒任務"""
        available_slots = self.max_concurrent - len(self.running)
        if available_slots <= 0:
            return []

        ready = self.graph.get_ready_tasks(self.completed)
        return ready[:available_slots]

    def mark_running(self, task: SchedulableTask):
        """標記任務為執行中"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.running.add(task.task_id)

    def mark_completed(self, task: SchedulableTask, result: Any = None):
        """標記任務為完成"""
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.result = result
        self.running.discard(task.task_id)
        self.completed.add(task.task_id)

        self._execution_history.append({
            "task_id": task.task_id,
            "status": "completed",
            "duration": task.actual_duration,
            "timestamp": task.completed_at.isoformat()
        })

    def mark_failed(self, task: SchedulableTask, error: str):
        """標記任務為失敗"""
        task.error = error
        task.retries += 1

        if task.retries < task.max_retries:
            # 可重試，重置為待執行
            task.status = TaskStatus.PENDING
            task.started_at = None
            self.running.discard(task.task_id)
        else:
            # 超過重試次數，標記為失敗
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            self.running.discard(task.task_id)

            self._execution_history.append({
                "task_id": task.task_id,
                "status": "failed",
                "error": error,
                "retries": task.retries,
                "timestamp": task.completed_at.isoformat()
            })

    async def execute_all(
        self,
        executor: Callable[[SchedulableTask], Awaitable[Any]],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[SchedulableTask]:
        """
        執行所有任務

        ‹1› 持續檢查就緒任務
        ‹2› 平行執行
        ‹3› 處理完成與失敗
        """
        total_tasks = len(self.graph._tasks)
        start_time = datetime.now()

        while len(self.completed) < total_tasks:
            ready = self.get_ready_tasks()

            if not ready and not self.running:
                # 沒有就緒任務也沒有執行中的任務
                pending = [t for t in self.graph._tasks.values()
                          if t.status == TaskStatus.PENDING]
                if pending:
                    # 存在無法滿足的依賴
                    blocked_ids = [t.task_id for t in pending]
                    raise RuntimeError(f"任務被阻塞: {blocked_ids}")
                break

            if ready:
                # 標記為執行中並平行執行
                for task in ready:
                    self.mark_running(task)

                # 執行任務
                results = await asyncio.gather(
                    *[self._execute_task(task, executor) for task in ready],
                    return_exceptions=True
                )

                # 處理結果
                for task, result in zip(ready, results):
                    if isinstance(result, Exception):
                        self.mark_failed(task, str(result))
                    else:
                        self.mark_completed(task, result)

                # 進度回調
                if on_progress:
                    on_progress(len(self.completed), total_tasks)

            # 短暫等待以避免忙等待
            if not ready and self.running:
                await asyncio.sleep(0.01)

        # 計算統計
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n調度完成: {len(self.completed)}/{total_tasks} 任務，耗時 {duration:.2f} 秒")

        return list(self.graph._tasks.values())

    async def _execute_task(
        self,
        task: SchedulableTask,
        executor: Callable[[SchedulableTask], Awaitable[Any]]
    ) -> Any:
        """執行單一任務"""
        try:
            return await executor(task)
        except Exception as e:
            raise

    def get_execution_order(self) -> List[str]:
        """獲取執行順序（拓撲排序）"""
        return self.graph.topological_sort()

    def get_parallel_groups(self) -> List[List[str]]:
        """
        獲取可平行執行的任務組

        返回一系列可平行執行的任務列表
        """
        groups = []
        completed = set()
        remaining = set(self.graph._tasks.keys())

        while remaining:
            # 找出當前可執行的任務
            ready = []
            for task_id in remaining:
                deps = self.graph.get_dependencies(task_id)
                if deps.issubset(completed):
                    ready.append(task_id)

            if not ready:
                # 存在循環依賴
                break

            groups.append(ready)
            completed.update(ready)
            remaining -= set(ready)

        return groups

    def get_critical_path(self) -> List[str]:
        """
        獲取關鍵路徑

        返回最長的依賴鏈
        """
        memo = {}

        def longest_path(task_id: str) -> List[str]:
            if task_id in memo:
                return memo[task_id]

            deps = self.graph.get_dependencies(task_id)
            if not deps:
                memo[task_id] = [task_id]
                return memo[task_id]

            longest = []
            for dep in deps:
                path = longest_path(dep)
                if len(path) > len(longest):
                    longest = path

            memo[task_id] = longest + [task_id]
            return memo[task_id]

        all_paths = []
        for task_id in self.graph._tasks:
            all_paths.append(longest_path(task_id))

        return max(all_paths, key=len) if all_paths else []

    def get_statistics(self) -> Dict[str, Any]:
        """獲取調度統計"""
        tasks = list(self.graph._tasks.values())

        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in tasks if t.status == TaskStatus.FAILED]

        durations = [t.actual_duration for t in completed_tasks if t.actual_duration]

        return {
            "total_tasks": len(tasks),
            "completed": len(completed_tasks),
            "failed": len(failed_tasks),
            "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "parallel_groups": len(self.get_parallel_groups()),
            "critical_path_length": len(self.get_critical_path())
        }

    def reset(self):
        """重置調度器"""
        self.completed.clear()
        self.running.clear()
        for task in self.graph._tasks.values():
            task.status = TaskStatus.PENDING
            task.result = None
            task.error = None
            task.started_at = None
            task.completed_at = None
            task.retries = 0


# =============================================================================
# 優先級調度器
# =============================================================================

class PriorityScheduler(TaskScheduler):
    """
    優先級調度器

    ‹1› 基於優先級的任務調度
    ‹2› 支援動態優先級調整
    ‹3› 支援任務搶佔
    """

    def __init__(self, max_concurrent: int = 10):
        super().__init__(max_concurrent)
        self._priority_adjustments: Dict[str, int] = {}

    def adjust_priority(self, task_id: str, adjustment: int):
        """
        調整任務優先級

        正數增加優先級，負數降低優先級
        """
        if task_id in self.graph._tasks:
            task = self.graph._tasks[task_id]
            task.priority = max(1, min(10, task.priority + adjustment))
            self._priority_adjustments[task_id] = adjustment

    def boost_blocked_dependencies(self, task_id: str, boost: int = 2):
        """
        提升阻塞任務依賴的優先級

        當高優先級任務被低優先級依賴阻塞時使用
        """
        deps = self.graph.get_dependencies(task_id)
        for dep_id in deps:
            if dep_id in self.graph._tasks:
                dep_task = self.graph._tasks[dep_id]
                if dep_task.status == TaskStatus.PENDING:
                    self.adjust_priority(dep_id, boost)

    def get_ready_tasks(self) -> List[SchedulableTask]:
        """獲取就緒任務（優先級排序）"""
        available_slots = self.max_concurrent - len(self.running)
        if available_slots <= 0:
            return []

        ready = self.graph.get_ready_tasks(self.completed)

        # 按優先級和預估時間排序（短任務優先）
        ready.sort(key=lambda t: (-t.priority, t.estimated_duration))

        return ready[:available_slots]


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範任務調度器"""
    print("=" * 60)
    print("  任務調度器示範")
    print("=" * 60)

    # 建立任務
    tasks = [
        SchedulableTask(
            task_id="collect_data",
            description="收集資料",
            priority=5,
            estimated_duration=1.0
        ),
        SchedulableTask(
            task_id="analyze_industry",
            description="產業分析",
            dependencies=["collect_data"],
            priority=4,
            estimated_duration=2.0
        ),
        SchedulableTask(
            task_id="analyze_tech",
            description="技術分析",
            dependencies=["collect_data"],
            priority=4,
            estimated_duration=1.5
        ),
        SchedulableTask(
            task_id="analyze_finance",
            description="財務分析",
            dependencies=["collect_data"],
            priority=4,
            estimated_duration=1.5
        ),
        SchedulableTask(
            task_id="integrate_results",
            description="整合結果",
            dependencies=["analyze_industry", "analyze_tech", "analyze_finance"],
            priority=5,
            estimated_duration=1.0
        ),
        SchedulableTask(
            task_id="generate_report",
            description="生成報告",
            dependencies=["integrate_results"],
            priority=5,
            estimated_duration=0.5
        )
    ]

    # 建立調度器
    scheduler = TaskScheduler(max_concurrent=3)
    scheduler.add_tasks(tasks)

    # 顯示依賴關係
    print("\n任務依賴關係:")
    for task in tasks:
        deps = ", ".join(task.dependencies) if task.dependencies else "(無)"
        print(f"  {task.task_id} ← {deps}")

    # 顯示執行順序
    print("\n拓撲排序結果:")
    order = scheduler.get_execution_order()
    print(f"  {' → '.join(order)}")

    # 顯示平行組
    print("\n平行執行組:")
    groups = scheduler.get_parallel_groups()
    for i, group in enumerate(groups, 1):
        print(f"  第 {i} 波: {', '.join(group)}")

    # 顯示關鍵路徑
    print("\n關鍵路徑:")
    critical = scheduler.get_critical_path()
    print(f"  {' → '.join(critical)}")

    # 執行任務
    print("\n執行任務:")

    async def mock_executor(task: SchedulableTask) -> str:
        """模擬任務執行"""
        print(f"  [執行] {task.task_id} (預估 {task.estimated_duration}s)")
        await asyncio.sleep(task.estimated_duration * 0.1)  # 加速執行
        return f"結果: {task.task_id}"

    def on_progress(completed: int, total: int):
        print(f"  [進度] {completed}/{total} ({completed/total*100:.0f}%)")

    results = await scheduler.execute_all(mock_executor, on_progress)

    # 顯示統計
    print("\n執行統計:")
    stats = scheduler.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


async def demo_priority():
    """示範優先級調度"""
    print("\n" + "=" * 60)
    print("  優先級調度器示範")
    print("=" * 60)

    tasks = [
        SchedulableTask(task_id="low_1", description="低優先級 1", priority=2),
        SchedulableTask(task_id="low_2", description="低優先級 2", priority=2),
        SchedulableTask(task_id="high_1", description="高優先級 1", priority=8),
        SchedulableTask(task_id="high_2", description="高優先級 2", priority=8, dependencies=["low_1"]),
    ]

    scheduler = PriorityScheduler(max_concurrent=2)
    scheduler.add_tasks(tasks)

    print("\n初始優先級:")
    for task in tasks:
        print(f"  {task.task_id}: 優先級 {task.priority}")

    # 提升被阻塞的依賴
    print("\n提升 high_2 的阻塞依賴優先級...")
    scheduler.boost_blocked_dependencies("high_2")

    print("\n調整後優先級:")
    for task_id, task in scheduler.graph._tasks.items():
        print(f"  {task_id}: 優先級 {task.priority}")


def main():
    parser = argparse.ArgumentParser(description="任務調度器")
    parser.add_argument("--demo", action="store_true", help="執行示範")

    args = parser.parse_args()
    asyncio.run(demo())
    asyncio.run(demo_priority())


if __name__ == "__main__":
    main()
