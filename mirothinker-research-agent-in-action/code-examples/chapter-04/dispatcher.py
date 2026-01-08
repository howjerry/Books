"""
dispatcher.py

深度研究代理人的核心調度器實現
支援任務分解、依賴管理、並行執行和錯誤恢復

使用方式：
    dispatcher = Dispatcher()
    result = await dispatcher.run("分析 AI 晶片市場格局")
"""

import os
import json
import asyncio
import uuid
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any
from collections import defaultdict
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


# =============================================================================
# 狀態與事件定義
# =============================================================================

class TaskState(Enum):
    """任務狀態"""
    PENDING = auto()
    PLANNING = auto()
    READY = auto()
    RUNNING = auto()
    WAITING = auto()  # 等待依賴
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class TaskEvent(Enum):
    """任務事件"""
    CREATED = "created"
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


# =============================================================================
# 資料結構
# =============================================================================

@dataclass
class Task:
    """任務資料結構"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query: str = ""
    state: TaskState = TaskState.PENDING
    priority: int = 5
    parent_id: Optional[str] = None
    children: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    result: Optional[dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "id": self.id,
            "query": self.query,
            "state": self.state.name,
            "priority": self.priority,
            "parent_id": self.parent_id,
            "children": self.children,
            "dependencies": self.dependencies,
            "retry_count": self.retry_count,
            "result": self.result,
            "error": self.error
        }


@dataclass
class ExecutionPlan:
    """執行計畫"""
    root_task_id: str
    tasks: dict[str, Task] = field(default_factory=dict)
    execution_order: list[str] = field(default_factory=list)
    dependency_graph: dict = field(default_factory=dict)


# =============================================================================
# 事件總線
# =============================================================================

class EventBus:
    """事件總線"""

    def __init__(self):
        self._handlers: dict[TaskEvent, list[Callable]] = defaultdict(list)

    def subscribe(self, event: TaskEvent, handler: Callable):
        """訂閱事件"""
        self._handlers[event].append(handler)

    def publish(self, event: TaskEvent, data: Any):
        """發布事件"""
        for handler in self._handlers[event]:
            try:
                handler(data)
            except Exception as e:
                print(f"Event handler error: {e}")

    def clear(self):
        """清除所有訂閱"""
        self._handlers.clear()


# =============================================================================
# 依賴圖
# =============================================================================

class DependencyGraph:
    """任務依賴圖"""

    def __init__(self):
        self.nodes: dict[str, set] = {}  # task_id -> set of dependencies
        self.reverse: dict[str, set] = defaultdict(set)  # task_id -> set of dependents

    def add_task(self, task_id: str, dependencies: list[str] = None):
        """添加任務"""
        deps = set(dependencies or [])
        self.nodes[task_id] = deps

        for dep_id in deps:
            self.reverse[dep_id].add(task_id)

    def remove_task(self, task_id: str):
        """移除任務"""
        if task_id in self.nodes:
            for dep_id in self.nodes[task_id]:
                self.reverse[dep_id].discard(task_id)
            del self.nodes[task_id]

        if task_id in self.reverse:
            for dependent_id in self.reverse[task_id]:
                if dependent_id in self.nodes:
                    self.nodes[dependent_id].discard(task_id)
            del self.reverse[task_id]

    def get_ready_tasks(self, completed: set[str]) -> list[str]:
        """獲取可執行的任務"""
        ready = []
        for task_id, deps in self.nodes.items():
            if task_id not in completed and deps.issubset(completed):
                ready.append(task_id)
        return ready

    def get_execution_order(self) -> list[str]:
        """獲取執行順序（拓撲排序）"""
        in_degree = {tid: len(deps) for tid, deps in self.nodes.items()}
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for dependent in self.reverse.get(current, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self.nodes):
            raise ValueError("Circular dependency detected!")

        return result


# =============================================================================
# 任務執行器
# =============================================================================

class TaskExecutor:
    """任務執行器"""

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    async def execute(self, task: Task) -> dict:
        """執行任務"""
        # 根據任務類型選擇執行策略
        task_type = task.metadata.get("type", "research")

        if task_type == "search":
            return await self._execute_search(task)
        elif task_type == "analyze":
            return await self._execute_analyze(task)
        elif task_type == "synthesize":
            return await self._execute_synthesize(task)
        else:
            return await self._execute_research(task)

    async def _execute_research(self, task: Task) -> dict:
        """執行研究任務"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": f"請研究以下問題並提供詳細分析：\n\n{task.query}"
            }],
            temperature=0.3
        )

        return {
            "type": "research",
            "content": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens if response.usage else 0
        }

    async def _execute_search(self, task: Task) -> dict:
        """執行搜尋任務（模擬）"""
        # 在實際實現中，這裡會調用搜尋 API
        await asyncio.sleep(0.5)  # 模擬網路延遲

        return {
            "type": "search",
            "content": f"搜尋結果：{task.query}",
            "sources": ["https://example.com/1", "https://example.com/2"]
        }

    async def _execute_analyze(self, task: Task) -> dict:
        """執行分析任務"""
        # 獲取依賴任務的結果
        parent_results = task.metadata.get("parent_results", [])

        context = "\n".join([
            f"資料 {i+1}：{r.get('content', '')[:500]}"
            for i, r in enumerate(parent_results)
        ])

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": f"""基於以下資料進行分析：

{context}

分析任務：{task.query}

請提供結構化的分析結果。"""
            }],
            temperature=0.3
        )

        return {
            "type": "analyze",
            "content": response.choices[0].message.content
        }

    async def _execute_synthesize(self, task: Task) -> dict:
        """執行綜合任務"""
        parent_results = task.metadata.get("parent_results", [])

        context = "\n\n".join([
            f"## 資料 {i+1}\n{r.get('content', '')}"
            for i, r in enumerate(parent_results)
        ])

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": f"""請綜合以下研究結果，生成一份完整的報告：

{context}

報告主題：{task.query}

請生成一份結構化的研究報告，包含：
1. 摘要
2. 主要發現
3. 分析
4. 結論與建議"""
            }],
            temperature=0.3
        )

        return {
            "type": "synthesize",
            "content": response.choices[0].message.content
        }


# =============================================================================
# 任務分解器
# =============================================================================

class TaskDecomposer:
    """任務分解器"""

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    async def decompose(self, task: Task) -> list[Task]:
        """分解任務為子任務"""

        prompt = f"""你是一位任務規劃專家。請將以下研究任務分解為可執行的子任務。

研究任務：{task.query}

請分解為 3-6 個子任務，每個子任務應該：
1. 具體且可獨立執行
2. 涵蓋問題的不同面向
3. 有明確的產出物

請以 JSON 格式輸出：
```json
{{
  "subtasks": [
    {{
      "id": "1",
      "query": "子任務描述",
      "type": "search|analyze|synthesize",
      "priority": 1-10,
      "dependencies": []
    }}
  ],
  "final_task": {{
    "query": "整合所有結果的最終任務描述",
    "dependencies": ["所有子任務的 id"]
  }}
}}
```"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response.choices[0].message.content

        # 解析 JSON
        import re
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            try:
                data = json.loads(content)
            except:
                # 降級：不分解，直接執行
                return []

        subtasks = []

        for st in data.get("subtasks", []):
            subtask = Task(
                id=f"{task.id}-{st['id']}",
                query=st["query"],
                priority=st.get("priority", 5),
                parent_id=task.id,
                dependencies=[f"{task.id}-{d}" for d in st.get("dependencies", [])],
                metadata={"type": st.get("type", "research")}
            )
            subtasks.append(subtask)

        # 添加最終整合任務
        final = data.get("final_task", {})
        if final:
            final_task = Task(
                id=f"{task.id}-final",
                query=final.get("query", f"整合 {task.query} 的研究結果"),
                priority=1,  # 最高優先級
                parent_id=task.id,
                dependencies=[f"{task.id}-{d}" for d in final.get("dependencies", [])],
                metadata={"type": "synthesize"}
            )
            subtasks.append(final_task)

        return subtasks


# =============================================================================
# 核心調度器
# =============================================================================

class Dispatcher:
    """
    核心調度器

    負責任務的接收、分解、調度和監控
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_concurrent: int = 5,
        task_timeout: float = 300.0,
        verbose: bool = True
    ):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.max_concurrent = max_concurrent
        self.task_timeout = task_timeout
        self.verbose = verbose

        # 組件
        self.executor = TaskExecutor(self.client, model)
        self.decomposer = TaskDecomposer(self.client, model)
        self.event_bus = EventBus()

        # 狀態
        self.tasks: dict[str, Task] = {}
        self.dependency_graph = DependencyGraph()
        self.completed_tasks: set[str] = set()
        self.failed_tasks: set[str] = set()

        # 並發控制
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # 統計
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_retries": 0,
            "start_time": None,
            "end_time": None
        }

        # 設置事件處理
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """設置事件處理器"""
        self.event_bus.subscribe(
            TaskEvent.COMPLETED,
            lambda data: self._log(f"✅ 任務完成：{data['task_id']}")
        )
        self.event_bus.subscribe(
            TaskEvent.FAILED,
            lambda data: self._log(f"❌ 任務失敗：{data['task_id']} - {data.get('error', 'Unknown')}")
        )
        self.event_bus.subscribe(
            TaskEvent.RETRYING,
            lambda data: self._log(f"🔄 重試任務：{data['task_id']} (第 {data['retry_count']} 次)")
        )

    async def run(self, query: str) -> dict:
        """
        執行研究任務

        Args:
            query: 研究問題

        Returns:
            研究結果字典
        """
        self.stats["start_time"] = datetime.now()

        self._log(f"\n{'='*60}")
        self._log(f"🚀 開始調度：{query}")
        self._log(f"{'='*60}\n")

        try:
            # 1. 創建根任務
            root_task = Task(query=query)
            self.tasks[root_task.id] = root_task
            self.stats["total_tasks"] += 1

            # 2. 任務分解
            await self._plan_task(root_task)

            # 3. 執行任務
            await self._execute_all()

            # 4. 收集結果
            result = self._collect_results(root_task.id)

            self.stats["end_time"] = datetime.now()

            self._log(f"\n{'='*60}")
            self._log(f"✅ 調度完成")
            self._log(self._format_stats())
            self._log(f"{'='*60}\n")

            return result

        except Exception as e:
            self._log(f"❌ 調度失敗：{e}")
            raise

    async def _plan_task(self, task: Task):
        """規劃任務"""
        task.state = TaskState.PLANNING
        self._log(f"📋 規劃任務：{task.query[:50]}...")

        # 分解任務
        subtasks = await self.decomposer.decompose(task)

        if not subtasks:
            # 不需要分解，直接執行
            self.dependency_graph.add_task(task.id, [])
            task.state = TaskState.READY
            return

        # 添加子任務
        for subtask in subtasks:
            self.tasks[subtask.id] = subtask
            self.stats["total_tasks"] += 1
            self.dependency_graph.add_task(subtask.id, subtask.dependencies)
            task.children.append(subtask.id)

        self._log(f"   📊 分解為 {len(subtasks)} 個子任務")

        # 打印執行順序
        order = self.dependency_graph.get_execution_order()
        self._log(f"   📝 執行順序：{' → '.join(order)}")

        task.state = TaskState.WAITING

    async def _execute_all(self):
        """執行所有任務"""
        self._log("\n📍 開始執行任務")

        while True:
            # 獲取可執行的任務
            ready = self.dependency_graph.get_ready_tasks(self.completed_tasks)
            ready = [tid for tid in ready if tid not in self.failed_tasks]

            if not ready:
                # 檢查是否還有未完成的任務
                pending = set(self.dependency_graph.nodes.keys()) - self.completed_tasks - self.failed_tasks
                if not pending:
                    break
                # 有任務但無法執行（可能是依賴失敗）
                self._log("⚠️ 部分任務因依賴失敗而無法執行")
                break

            # 並行執行
            await self._execute_batch(ready)

    async def _execute_batch(self, task_ids: list[str]):
        """批次執行任務"""
        self._log(f"\n   🔄 並行執行 {len(task_ids)} 個任務")

        async def execute_single(task_id: str):
            async with self.semaphore:
                return await self._execute_task(task_id)

        results = await asyncio.gather(
            *[execute_single(tid) for tid in task_ids],
            return_exceptions=True
        )

        for task_id, result in zip(task_ids, results):
            if isinstance(result, Exception):
                self._log(f"      ❌ {task_id}: {result}")
            else:
                self._log(f"      ✅ {task_id}: 完成")

    async def _execute_task(self, task_id: str) -> dict:
        """執行單個任務"""
        task = self.tasks[task_id]
        task.state = TaskState.RUNNING
        task.started_at = datetime.now()

        # 收集依賴任務的結果
        if task.dependencies:
            parent_results = []
            for dep_id in task.dependencies:
                if dep_id in self.tasks:
                    dep_result = self.tasks[dep_id].result
                    if dep_result:
                        parent_results.append(dep_result)
            task.metadata["parent_results"] = parent_results

        try:
            # 執行任務
            result = await asyncio.wait_for(
                self.executor.execute(task),
                timeout=self.task_timeout
            )

            task.result = result
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.now()
            self.completed_tasks.add(task_id)
            self.stats["completed_tasks"] += 1

            self.event_bus.publish(TaskEvent.COMPLETED, {"task_id": task_id})

            return result

        except asyncio.TimeoutError:
            return await self._handle_task_failure(task, "Task timeout")

        except Exception as e:
            return await self._handle_task_failure(task, str(e))

    async def _handle_task_failure(self, task: Task, error: str) -> dict:
        """處理任務失敗"""
        task.error = error
        task.retry_count += 1
        self.stats["total_retries"] += 1

        if task.retry_count <= task.max_retries:
            # 重試
            self.event_bus.publish(TaskEvent.RETRYING, {
                "task_id": task.id,
                "retry_count": task.retry_count,
                "error": error
            })

            # 指數退避
            await asyncio.sleep(2 ** task.retry_count)

            return await self._execute_task(task.id)

        else:
            # 標記失敗
            task.state = TaskState.FAILED
            self.failed_tasks.add(task.id)
            self.stats["failed_tasks"] += 1

            self.event_bus.publish(TaskEvent.FAILED, {
                "task_id": task.id,
                "error": error
            })

            return {"error": error}

    def _collect_results(self, root_task_id: str) -> dict:
        """收集結果"""
        root_task = self.tasks[root_task_id]

        # 找到最終任務
        final_task_id = f"{root_task_id}-final"
        if final_task_id in self.tasks:
            final_task = self.tasks[final_task_id]
            if final_task.result:
                return {
                    "success": True,
                    "content": final_task.result.get("content", ""),
                    "subtask_count": len(root_task.children),
                    "stats": self.stats
                }

        # 如果沒有最終任務，收集所有子任務結果
        contents = []
        for child_id in root_task.children:
            if child_id in self.tasks:
                child = self.tasks[child_id]
                if child.result:
                    contents.append(child.result.get("content", ""))

        return {
            "success": len(self.failed_tasks) == 0,
            "content": "\n\n---\n\n".join(contents) if contents else "No results",
            "subtask_count": len(root_task.children),
            "stats": self.stats
        }

    def _format_stats(self) -> str:
        """格式化統計資訊"""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        return f"""
   📊 執行統計
   ├── 總任務數：{self.stats['total_tasks']}
   ├── 完成任務：{self.stats['completed_tasks']}
   ├── 失敗任務：{self.stats['failed_tasks']}
   ├── 總重試次數：{self.stats['total_retries']}
   └── 總耗時：{duration:.1f} 秒"""

    def _log(self, message: str):
        """輸出日誌"""
        if self.verbose:
            print(message)

    def get_task_tree(self, task_id: str = None) -> dict:
        """獲取任務樹（用於可視化）"""
        if task_id is None:
            # 找到根任務
            root_tasks = [t for t in self.tasks.values() if t.parent_id is None]
            if not root_tasks:
                return {}
            task_id = root_tasks[0].id

        task = self.tasks.get(task_id)
        if not task:
            return {}

        return {
            "id": task.id,
            "query": task.query[:50] + "..." if len(task.query) > 50 else task.query,
            "state": task.state.name,
            "children": [self.get_task_tree(cid) for cid in task.children]
        }


# =============================================================================
# 主程式
# =============================================================================

async def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description="深度研究調度器")
    parser.add_argument("-q", "--query", type=str, help="研究問題")
    parser.add_argument("--model", default="gpt-4o-mini", help="使用的模型")
    parser.add_argument("--max-concurrent", type=int, default=5, help="最大並發數")
    parser.add_argument("-o", "--output", type=str, help="輸出檔案")

    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 請設定 OPENAI_API_KEY 環境變數")
        return

    dispatcher = Dispatcher(
        model=args.model,
        max_concurrent=args.max_concurrent,
        verbose=True
    )

    query = args.query or "分析 2024 年全球 AI 晶片市場格局，包括主要玩家和技術趨勢"

    result = await dispatcher.run(query)

    print("\n" + "="*60)
    print("📄 研究報告")
    print("="*60)
    print(result.get("content", "No content"))

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result.get("content", ""))
        print(f"\n📄 報告已保存至：{args.output}")


if __name__ == "__main__":
    asyncio.run(main())
