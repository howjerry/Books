# 第 7 章
> 🎯 **進階階段**：本章探討 Skills 組合與編排。需具備 **Chapters 3-6** 的基礎，特別是 **Chapter 3** 的核心概念。
：Skills 進階模式與編排

前幾章中，我們學習了單一 Skill 的開發：瀏覽器自動化（Chapter 4）、數據處理（Chapter 5）、API 測試（Chapter 6）。但在實際場景中，複雜的自動化工作流往往需要**組合多個 Skills**：先用 API Skill 創建測試數據，再用瀏覽器 Skill 驗證 UI，最後用數據處理 Skill 生成報告。本章將探討 Skills 的編排（Orchestration）技術：順序執行、並行執行、條件分支、錯誤恢復、動態參數傳遞，以及如何設計可重用的工作流模式。

## 7.1 為什麼需要 Skill 編排？

### 7.1.1 單一 Skill 的局限性

單一 Skill 設計遵循「單一職責原則」（Single Responsibility Principle），這有優點：

- 易於測試：一個 Skill 只做一件事
- 可重用：通用的 Skill 可在多個場景使用
- 易於維護：改動範圍小

但面對複雜業務流程，單一 Skill 就不夠了。例如：

**場景：電商下單流程測試**

1. 調用 API 創建測試用戶
2. 用瀏覽器登入
3. 搜尋商品並加入購物車
4. 填寫配送地址
5. 選擇支付方式
6. 提交訂單
7. 驗證訂單確認頁面
8. 調用 API 檢查訂單狀態
9. 生成測試報告（Excel）

這需要 3 種 Skills（API、瀏覽器、數據處理）的 9 個步驟，且步驟間有依賴關係。

### 7.1.2 編排的核心價值

**Skill 編排（Orchestration）** 解決的問題：

- **順序依賴**：B Skill 需要 A Skill 的輸出作為輸入
- **並行加速**：無依賴的 Skills 可並行執行，縮短總時間
- **錯誤恢復**：某個 Skill 失敗時，執行補償操作或重試
- **條件分支**：根據 Skill 結果決定下一步（if-else 邏輯）
- **可觀測性**：記錄整個工作流的執行過程，便於調試

## 7.2 Skill 編排器（SkillOrchestrator）

### 7.2.1 基礎架構

我們設計一個通用的 Skill 編排器，支持註冊 Skills 並以多種模式執行：

```python
import asyncio
import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """執行模式"""
    SEQUENTIAL = "sequential"  # 順序執行
    PARALLEL = "parallel"      # 並行執行
    CONDITIONAL = "conditional"  # 條件執行


class SkillResult:
    """Skill 執行結果"""

    def __init__(
        self,
        skill_name: str,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        duration_ms: float = 0
    ):
        self.skill_name = skill_name
        self.success = success
        self.data = data
        self.error = error
        self.duration_ms = duration_ms
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }


class SkillOrchestrator:
    """
    Skill 編排器

    支持順序、並行、條件執行等多種模式
    """

    def __init__(self):
        """初始化編排器"""
        self.skills: Dict[str, Callable] = {}
        self.execution_history: List[SkillResult] = []
        self.context: Dict[str, Any] = {}  # 共享上下文

    def register(self, name: str, skill_func: Callable):
        """
        註冊 Skill

        Args:
            name: Skill 名稱（唯一標識）
            skill_func: Skill 函數（可以是同步或異步）

        Example:
            >>> orchestrator = SkillOrchestrator()
            >>> async def my_skill(**params):
            ...     return {"success": True, "data": "result"}
            >>> orchestrator.register("my_skill", my_skill)
        """
        if name in self.skills:
            logger.warning(f"Skill '{name}' 已存在，將被覆蓋")

        self.skills[name] = skill_func
        logger.info(f"已註冊 Skill: {name}")

    def set_context(self, key: str, value: Any):
        """設置共享上下文（供 Skills 間傳遞數據）"""
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """獲取共享上下文"""
        return self.context.get(key, default)

    async def execute_skill(
        self,
        skill_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        """
        執行單一 Skill

        Args:
            skill_name: Skill 名稱
            params: 參數字典

        Returns:
            SkillResult 物件
        """
        if skill_name not in self.skills:
            error_msg = f"未註冊的 Skill: {skill_name}"
            logger.error(error_msg)
            return SkillResult(
                skill_name=skill_name,
                success=False,
                error=error_msg
            )

        skill_func = self.skills[skill_name]
        params = params or {}

        # 記錄開始時間
        import time
        start_time = time.time()

        try:
            # 檢查是否為異步函數
            if asyncio.iscoroutinefunction(skill_func):
                result = await skill_func(**params)
            else:
                result = skill_func(**params)

            duration_ms = (time.time() - start_time) * 1000

            # 標準化結果格式
            if isinstance(result, dict):
                success = result.get("success", True)
                data = result.get("data", result)
                error = result.get("error")
            else:
                success = True
                data = result
                error = None

            skill_result = SkillResult(
                skill_name=skill_name,
                success=success,
                data=data,
                error=error,
                duration_ms=duration_ms
            )

            self.execution_history.append(skill_result)

            log_level = logging.INFO if success else logging.WARNING
            logger.log(
                log_level,
                f"Skill '{skill_name}' 執行完成: "
                f"{'成功' if success else '失敗'} ({duration_ms:.0f}ms)"
            )

            return skill_result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"執行異常: {str(e)}"

            logger.error(f"Skill '{skill_name}' 異常: {e}", exc_info=True)

            skill_result = SkillResult(
                skill_name=skill_name,
                success=False,
                error=error_msg,
                duration_ms=duration_ms
            )

            self.execution_history.append(skill_result)
            return skill_result

    async def execute_sequence(
        self,
        sequence: List[Dict[str, Any]],
        stop_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        順序執行 Skills

        Args:
            sequence: Skills 序列，每個元素格式：
                {
                    "skill": "skill_name",
                    "params": {...},
                    "stop_on_error": True/False  # 可選，覆蓋全局設置
                }
            stop_on_error: 遇到錯誤是否停止（全局設置）

        Returns:
            執行結果摘要

        Example:
            >>> result = await orchestrator.execute_sequence([
            ...     {"skill": "create_user", "params": {"name": "Alice"}},
            ...     {"skill": "login", "params": {"username": "Alice"}},
            ...     {"skill": "checkout", "params": {}}
            ... ])
        """
        results: List[SkillResult] = []

        for step in sequence:
            skill_name = step["skill"]
            params = step.get("params", {})
            step_stop_on_error = step.get("stop_on_error", stop_on_error)

            logger.info(f"執行步驟: {skill_name}")

            result = await self.execute_skill(skill_name, params)
            results.append(result)

            # 失敗處理
            if not result.success and step_stop_on_error:
                logger.warning(f"Skill '{skill_name}' 失敗，停止執行")
                break

        # 統計
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed

        return {
            "success": failed == 0,
            "total_steps": total,
            "passed": passed,
            "failed": failed,
            "results": [r.to_dict() for r in results]
        }

    async def execute_parallel(
        self,
        tasks: List[Dict[str, Any]],
        max_concurrency: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        並行執行 Skills（無順序依賴）

        Args:
            tasks: Skills 列表，格式同 execute_sequence
            max_concurrency: 最大並發數（None 表示不限制）

        Returns:
            執行結果摘要

        Example:
            >>> # 並行測試 3 個環境
            >>> result = await orchestrator.execute_parallel([
            ...     {"skill": "test_env", "params": {"env": "dev"}},
            ...     {"skill": "test_env", "params": {"env": "staging"}},
            ...     {"skill": "test_env", "params": {"env": "prod"}}
            ... ], max_concurrency=2)
        """
        # 創建異步任務
        async def run_task(task):
            skill_name = task["skill"]
            params = task.get("params", {})
            return await self.execute_skill(skill_name, params)

        # 使用 Semaphore 限制並發
        if max_concurrency:
            semaphore = asyncio.Semaphore(max_concurrency)

            async def run_with_limit(task):
                async with semaphore:
                    return await run_task(task)

            results = await asyncio.gather(
                *[run_with_limit(task) for task in tasks],
                return_exceptions=True
            )
        else:
            results = await asyncio.gather(
                *[run_task(task) for task in tasks],
                return_exceptions=True
            )

        # 處理異常
        skill_results = []
        for result in results:
            if isinstance(result, Exception):
                skill_results.append(
                    SkillResult(
                        skill_name="unknown",
                        success=False,
                        error=str(result)
                    )
                )
            else:
                skill_results.append(result)

        # 統計
        total = len(skill_results)
        passed = sum(1 for r in skill_results if r.success)
        failed = total - passed

        return {
            "success": failed == 0,
            "total_tasks": total,
            "passed": passed,
            "failed": failed,
            "results": [r.to_dict() for r in skill_results]
        }

    def get_execution_summary(self) -> Dict[str, Any]:
        """獲取執行摘要（基於歷史記錄）"""
        if not self.execution_history:
            return {"error": "無執行歷史"}

        total = len(self.execution_history)
        passed = sum(1 for r in self.execution_history if r.success)
        failed = total - passed

        total_duration = sum(r.duration_ms for r in self.execution_history)
        avg_duration = total_duration / total if total > 0 else 0

        return {
            "total_executions": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed / total * 100:.2f}%" if total > 0 else "0%",
            "total_duration_ms": round(total_duration, 2),
            "avg_duration_ms": round(avg_duration, 2),
            "history": [r.to_dict() for r in self.execution_history]
        }
```

### 7.2.2 使用範例：順序執行

```python
import asyncio


# 定義 Skills
async def create_test_user(**params):
    """創建測試用戶（API Skill）"""
    username = params.get('username')
    # 模擬 API 調用
    await asyncio.sleep(0.5)
    return {
        "success": True,
        "data": {"user_id": 12345, "username": username}
    }


async def browser_login(**params):
    """瀏覽器登入（Stagehand Skill）"""
    username = params.get('username')
    # 模擬瀏覽器操作
    await asyncio.sleep(1.0)
    return {
        "success": True,
        "data": {"session_id": "sess_abc123"}
    }


async def generate_report(**params):
    """生成測試報告（數據處理 Skill）"""
    await asyncio.sleep(0.3)
    return {
        "success": True,
        "data": {"report_path": "test_results.xlsx"}
    }


# 使用編排器
async def main():
    orchestrator = SkillOrchestrator()

    # 註冊 Skills
    orchestrator.register("create_user", create_test_user)
    orchestrator.register("login", browser_login)
    orchestrator.register("report", generate_report)

    # 定義工作流
    workflow = [
        {"skill": "create_user", "params": {"username": "alice"}},
        {"skill": "login", "params": {"username": "alice"}},
        {"skill": "report", "params": {}}
    ]

    # 執行
    result = await orchestrator.execute_sequence(workflow)

    print(f"執行結果: {'成功' if result['success'] else '失敗'}")
    print(f"通過: {result['passed']}/{result['total_steps']}")

    # 查看摘要
    summary = orchestrator.get_execution_summary()
    print(f"總耗時: {summary['total_duration_ms']:.0f}ms")


asyncio.run(main())
```


## 7.3 動態參數傳遞（Data Flow）

### 7.3.1 問題場景

實際工作流中，後續 Skill 常需要前一個 Skill 的輸出：

```
create_user (返回 user_id) → login (需要 user_id) → checkout (需要 session_id)
```

如果每個 Skill 都手動傳參，會非常繁瑣。我們需要**自動數據流**機制。

### 7.3.2 實作：支持數據流的編排器

擴展 `SkillOrchestrator`：

```python
class DataFlowOrchestrator(SkillOrchestrator):
    """支持數據流的編排器"""

    async def execute_sequence_with_flow(
        self,
        sequence: List[Dict[str, Any]],
        stop_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        順序執行 Skills，並支持數據流

        數據流語法：
        - 參數值以 "$" 開頭表示從上下文或前一步結果提取
        - 例如：{"user_id": "$previous.data.user_id"}

        Example:
            >>> workflow = [
            ...     {
            ...         "skill": "create_user",
            ...         "params": {"username": "alice"},
            ...         "output_to_context": {"user_id": "data.user_id"}
            ...     },
            ...     {
            ...         "skill": "login",
            ...         "params": {"user_id": "$context.user_id"}
            ...     }
            ... ]
        """
        results: List[SkillResult] = []
        previous_result = None

        for step in sequence:
            skill_name = step["skill"]
            params_template = step.get("params", {})

            # 解析參數（替換數據流變量）
            params = self._resolve_params(params_template, previous_result)

            logger.info(f"執行步驟: {skill_name} (參數: {params})")

            result = await self.execute_skill(skill_name, params)
            results.append(result)

            # 將結果寫入上下文
            output_mapping = step.get("output_to_context", {})
            if result.success and output_mapping:
                self._write_to_context(result.data, output_mapping)

            # 失敗處理
            if not result.success and step.get("stop_on_error", stop_on_error):
                logger.warning(f"Skill '{skill_name}' 失敗，停止執行")
                break

            previous_result = result

        # 統計
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed

        return {
            "success": failed == 0,
            "total_steps": total,
            "passed": passed,
            "failed": failed,
            "results": [r.to_dict() for r in results],
            "final_context": self.context
        }

    def _resolve_params(
        self,
        params_template: Dict[str, Any],
        previous_result: Optional[SkillResult]
    ) -> Dict[str, Any]:
        """
        解析參數模板，替換數據流變量

        支持的變量：
        - $context.key: 從共享上下文提取
        - $previous.data.key: 從前一步結果提取
        """
        resolved = {}

        for key, value in params_template.items():
            if isinstance(value, str) and value.startswith("$"):
                # 解析變量路徑
                path = value[1:]  # 移除 "$"

                if path.startswith("context."):
                    # 從上下文提取
                    context_key = path.replace("context.", "")
                    resolved[key] = self.get_context(context_key)

                elif path.startswith("previous."):
                    # 從前一步結果提取
                    if previous_result is None:
                        logger.warning(f"無前一步結果，無法解析 {value}")
                        resolved[key] = None
                    else:
                        data_path = path.replace("previous.data.", "")
                        resolved[key] = self._extract_nested(
                            previous_result.data,
                            data_path
                        )
                else:
                    logger.warning(f"未知變量路徑: {value}")
                    resolved[key] = value
            else:
                resolved[key] = value

        return resolved

    def _extract_nested(self, data: Any, path: str) -> Any:
        """從嵌套字典中提取值（如 user.address.city）"""
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _write_to_context(
        self,
        data: Any,
        mapping: Dict[str, str]
    ):
        """
        將 Skill 結果寫入上下文

        Args:
            data: Skill 返回的數據
            mapping: 映射規則，如 {"user_id": "data.user_id"}
        """
        for context_key, data_path in mapping.items():
            value = self._extract_nested({"data": data}, data_path)
            if value is not None:
                self.set_context(context_key, value)
                logger.debug(f"寫入上下文: {context_key} = {value}")
```

### 7.3.3 使用範例：完整的數據流

```python
async def main():
    orchestrator = DataFlowOrchestrator()

    # 註冊 Skills
    orchestrator.register("create_user", create_test_user)
    orchestrator.register("login", browser_login)
    orchestrator.register("get_user_profile", get_user_profile)

    # 定義帶數據流的工作流
    workflow = [
        {
            "skill": "create_user",
            "params": {"username": "alice", "email": "alice@example.com"},
            "output_to_context": {
                "user_id": "data.user_id",
                "username": "data.username"
            }
        },
        {
            "skill": "login",
            "params": {
                "username": "$context.username"  # 從上下文提取
            },
            "output_to_context": {
                "session_id": "data.session_id"
            }
        },
        {
            "skill": "get_user_profile",
            "params": {
                "user_id": "$context.user_id",
                "session_id": "$context.session_id"
            }
        }
    ]

    result = await orchestrator.execute_sequence_with_flow(workflow)

    print(f"工作流執行: {'成功' if result['success'] else '失敗'}")
    print(f"最終上下文: {result['final_context']}")
```


## 7.4 錯誤處理與重試策略

### 7.4.1 常見錯誤場景

自動化測試中，錯誤不可避免：

- **網絡錯誤**：API 請求超時
- **UI 變動**：瀏覽器找不到元素
- **數據問題**：Excel 檔案格式錯誤
- **環境問題**：測試資料庫連接失敗

需要不同的處理策略：

| 錯誤類型 | 策略 | 範例 |
|----------|------|------|
| 瞬時錯誤 | 重試 | 網絡超時、元素載入慢 |
| 數據錯誤 | 跳過並繼續 | 單筆測試數據格式錯誤 |
| 致命錯誤 | 停止工作流 | 登入失敗（後續依賴登入狀態） |
| 可補償錯誤 | 執行補償操作 | 創建用戶失敗 → 使用已存在用戶 |

### 7.4.2 實作：重試與補償機制

```python
from typing import Callable, Optional


class ResilientOrchestrator(DataFlowOrchestrator):
    """支持錯誤處理與重試的編排器"""

    async def execute_skill_with_retry(
        self,
        skill_name: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay_s: float = 1.0,
        fallback_skill: Optional[str] = None
    ) -> SkillResult:
        """
        執行 Skill 並支持重試

        Args:
            skill_name: Skill 名稱
            params: 參數
            max_retries: 最大重試次數
            retry_delay_s: 重試延遲（秒，指數退避）
            fallback_skill: 失敗後的備用 Skill

        Returns:
            SkillResult
        """
        attempt = 0

        while attempt <= max_retries:
            logger.info(
                f"執行 Skill '{skill_name}' "
                f"(嘗試 {attempt + 1}/{max_retries + 1})"
            )

            result = await self.execute_skill(skill_name, params)

            if result.success:
                return result

            # 失敗處理
            attempt += 1

            if attempt <= max_retries:
                delay = retry_delay_s * (2 ** (attempt - 1))  # 指數退避
                logger.warning(
                    f"Skill '{skill_name}' 失敗，"
                    f"{delay}秒後重試 ({attempt}/{max_retries})"
                )
                await asyncio.sleep(delay)

        # 所有重試都失敗，嘗試 fallback
        if fallback_skill and fallback_skill in self.skills:
            logger.info(f"執行備用 Skill: {fallback_skill}")
            return await self.execute_skill(fallback_skill, params)

        # 最終失敗
        logger.error(f"Skill '{skill_name}' 執行失敗（已重試 {max_retries} 次）")
        return result

    async def execute_with_compensation(
        self,
        workflow: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        執行工作流並支持補償（Compensation）

        如果 Skill 失敗，執行對應的補償操作（如回滾）

        Workflow 格式：
        [
            {
                "skill": "create_user",
                "params": {...},
                "compensation": "delete_user"  # 失敗時執行
            },
            ...
        ]
        """
        results: List[SkillResult] = []
        compensation_stack: List[str] = []  # 已執行的補償 Skills

        for step in workflow:
            skill_name = step["skill"]
            params = step.get("params", {})

            result = await self.execute_skill(skill_name, params)
            results.append(result)

            if result.success:
                # 成功：記錄補償操作（以備後續失敗時回滾）
                compensation = step.get("compensation")
                if compensation:
                    compensation_stack.append(compensation)
            else:
                # 失敗：執行所有已記錄的補償操作（反向）
                logger.warning(
                    f"Skill '{skill_name}' 失敗，"
                    f"執行 {len(compensation_stack)} 個補償操作"
                )

                for comp_skill in reversed(compensation_stack):
                    logger.info(f"補償操作: {comp_skill}")
                    await self.execute_skill(comp_skill, params)

                break

        # 統計
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed

        return {
            "success": failed == 0,
            "total_steps": total,
            "passed": passed,
            "failed": failed,
            "compensations_executed": len(compensation_stack),
            "results": [r.to_dict() for r in results]
        }
```

### 7.4.3 使用範例：重試與補償

```python
async def main():
    orchestrator = ResilientOrchestrator()

    orchestrator.register("create_user", create_test_user)
    orchestrator.register("delete_user", delete_test_user)
    orchestrator.register("send_email", send_welcome_email)

    # 工作流（帶補償）
    workflow = [
        {
            "skill": "create_user",
            "params": {"username": "alice"},
            "compensation": "delete_user"  # 如果後續失敗，刪除用戶
        },
        {
            "skill": "send_email",
            "params": {"to": "alice@example.com"},
            "compensation": None
        }
    ]

    result = await orchestrator.execute_with_compensation(workflow)

    print(f"工作流執行: {'成功' if result['success'] else '失敗'}")
    print(f"執行了 {result['compensations_executed']} 個補償操作")
```


## 7.5 條件執行與分支邏輯

### 7.5.1 if-else 邏輯

有時需要根據 Skill 結果決定下一步：

```
test_login() → 成功 → test_checkout()
             → 失敗 → retry_login() → test_checkout()
```

### 7.5.2 實作：條件執行器

```python
class ConditionalOrchestrator(ResilientOrchestrator):
    """支持條件執行的編排器"""

    async def execute_conditional(
        self,
        condition_skill: str,
        condition_params: Optional[Dict[str, Any]] = None,
        on_success: Optional[List[Dict[str, Any]]] = None,
        on_failure: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        條件執行（if-else）

        Args:
            condition_skill: 條件 Skill 名稱
            condition_params: 條件 Skill 參數
            on_success: 成功時執行的 Skill 序列
            on_failure: 失敗時執行的 Skill 序列

        Example:
            >>> result = await orchestrator.execute_conditional(
            ...     condition_skill="check_environment",
            ...     on_success=[
            ...         {"skill": "run_tests", "params": {}}
            ...     ],
            ...     on_failure=[
            ...         {"skill": "setup_environment", "params": {}},
            ...         {"skill": "run_tests", "params": {}}
            ...     ]
            ... )
        """
        # 執行條件 Skill
        condition_result = await self.execute_skill(
            condition_skill,
            condition_params or {}
        )

        # 根據結果選擇分支
        if condition_result.success:
            logger.info(f"條件 '{condition_skill}' 成功，執行 on_success 分支")
            branch = on_success or []
        else:
            logger.info(f"條件 '{condition_skill}' 失敗，執行 on_failure 分支")
            branch = on_failure or []

        # 執行選中的分支
        if branch:
            branch_result = await self.execute_sequence(branch)
            return {
                "condition_success": condition_result.success,
                "branch_executed": "on_success" if condition_result.success else "on_failure",
                "branch_result": branch_result
            }
        else:
            return {
                "condition_success": condition_result.success,
                "branch_executed": None,
                "message": "無對應分支"
            }
```


## 7.6 實戰案例：端到端測試工作流

### 7.6.1 場景：電商下單流程

整合前幾章的 Skills，構建完整的 E2E 測試：

```python
async def e2e_checkout_workflow():
    """電商下單端到端測試工作流"""
    orchestrator = ResilientOrchestrator()

    # 註冊所有 Skills
    orchestrator.register("api_create_user", api_create_test_user)
    orchestrator.register("browser_login", stagehand_login)
    orchestrator.register("browser_add_to_cart", stagehand_add_to_cart)
    orchestrator.register("browser_checkout", stagehand_checkout)
    orchestrator.register("api_verify_order", api_verify_order)
    orchestrator.register("excel_generate_report", excel_generate_report)
    orchestrator.register("api_cleanup", api_delete_test_user)

    # 定義工作流
    workflow = [
        # 1. API: 創建測試用戶
        {
            "skill": "api_create_user",
            "params": {"username": "test_user_001", "email": "test@example.com"},
            "output_to_context": {
                "user_id": "data.user_id",
                "username": "data.username",
                "password": "data.password"
            },
            "compensation": "api_cleanup"
        },

        # 2. 瀏覽器: 登入
        {
            "skill": "browser_login",
            "params": {
                "username": "$context.username",
                "password": "$context.password",
                "url": "https://example.com/login"
            },
            "output_to_context": {
                "session_id": "data.session_id"
            },
            "retry": 3  # 登入可能因網絡問題失敗，重試 3 次
        },

        # 3. 瀏覽器: 加入購物車（並行測試多個商品）
        # 注意：這裡使用並行執行
        {
            "skill": "parallel",
            "tasks": [
                {"skill": "browser_add_to_cart", "params": {"product_id": "P001"}},
                {"skill": "browser_add_to_cart", "params": {"product_id": "P002"}},
                {"skill": "browser_add_to_cart", "params": {"product_id": "P003"}}
            ]
        },

        # 4. 瀏覽器: 結帳
        {
            "skill": "browser_checkout",
            "params": {
                "payment_method": "credit_card",
                "shipping_address": "123 Test St"
            },
            "output_to_context": {
                "order_id": "data.order_id"
            }
        },

        # 5. API: 驗證訂單狀態
        {
            "skill": "api_verify_order",
            "params": {
                "order_id": "$context.order_id",
                "expected_status": "confirmed"
            }
        },

        # 6. 數據處理: 生成測試報告
        {
            "skill": "excel_generate_report",
            "params": {
                "test_name": "E2E Checkout Test",
                "user_id": "$context.user_id",
                "order_id": "$context.order_id"
            }
        }
    ]

    # 執行工作流
    result = await orchestrator.execute_with_compensation(workflow)

    return result


# 執行
result = asyncio.run(e2e_checkout_workflow())
print(f"E2E 測試: {'通過' if result['success'] else '失敗'}")
```

### 7.6.2 工作流可視化

使用 ASCII 圖表示工作流：

```
┌─────────────────────────────────────────────────────────┐
│                  E2E Checkout Workflow                  │
└─────────────────────────────────────────────────────────┘

1. [API] create_user
   │  output: user_id, username, password
   │  compensation: delete_user
   ↓

2. [Browser] login
   │  input: username, password
   │  output: session_id
   │  retry: 3 times
   ↓

3. [Browser Parallel] add_to_cart (P001, P002, P003)
   │  (並行執行，加速測試)
   ↓

4. [Browser] checkout
   │  output: order_id
   ↓

5. [API] verify_order
   │  input: order_id
   ↓

6. [Data] generate_report
   │  input: user_id, order_id
   │  output: report_path
   ↓

[END] Success / Failure
   (如失敗，執行補償操作 delete_user)
```


## 7.7 最佳實踐與設計模式

### 7.7.1 Skill 編排的黃金法則

1. **單一職責**：每個 Skill 只做一件事，編排器負責組合
2. **冪等性**：Skill 應設計為可重複執行（如 GET 請求、創建用戶時檢查是否已存在）
3. **明確契約**：Skill 的輸入輸出格式要清晰文檔化
4. **錯誤分類**：區分瞬時錯誤（可重試）與永久錯誤（停止工作流）
5. **可觀測性**：記錄每個 Skill 的執行時間、參數、結果

### 7.7.2 常見編排模式

**模式 1：Fork-Join（分叉-合併）**

```python
# 並行執行多個測試，最後合併結果
workflow = [
    {
        "skill": "parallel",
        "tasks": [
            {"skill": "test_api_endpoint", "params": {"endpoint": "/users"}},
            {"skill": "test_api_endpoint", "params": {"endpoint": "/orders"}},
            {"skill": "test_api_endpoint", "params": {"endpoint": "/products"}}
        ]
    },
    {
        "skill": "aggregate_results",  # 合併所有 API 測試結果
        "params": {}
    }
]
```

**模式 2：Pipeline（流水線）**

```python
# 數據在 Skills 間流動
workflow = [
    {"skill": "fetch_data", "output_to_context": {"raw_data": "data"}},
    {"skill": "clean_data", "params": {"data": "$context.raw_data"}, "output_to_context": {"clean_data": "data"}},
    {"skill": "validate_data", "params": {"data": "$context.clean_data"}},
    {"skill": "save_data", "params": {"data": "$context.clean_data"}}
]
```

**模式 3：Saga（長事務補償）**

```python
# 每個步驟都有補償操作，失敗時自動回滾
workflow = [
    {"skill": "reserve_inventory", "compensation": "release_inventory"},
    {"skill": "charge_payment", "compensation": "refund_payment"},
    {"skill": "send_confirmation", "compensation": "cancel_order"}
]
```

### 7.7.3 性能優化

**並行 vs 順序：**

```python
# ❌ 順序執行（慢）：總時間 = t1 + t2 + t3 = 6 秒
await execute_sequence([
    {"skill": "test_env_dev"},     # 2s
    {"skill": "test_env_staging"}, # 2s
    {"skill": "test_env_prod"}     # 2s
])

# ✅ 並行執行（快）：總時間 = max(t1, t2, t3) = 2 秒
await execute_parallel([
    {"skill": "test_env_dev"},
    {"skill": "test_env_staging"},
    {"skill": "test_env_prod"}
])
```

**限制並發：**

```python
# 避免過度並發導致資源耗盡
await execute_parallel(tasks, max_concurrency=5)
```


## 7.8 本章總結

本章深入探討了 Skill 編排的高級技術：

**核心能力：**

- **SkillOrchestrator**：通用編排器，支持註冊、順序、並行執行
- **數據流（Data Flow）**：自動傳遞 Skill 間的參數，減少手動配置
- **錯誤處理**：重試、補償、條件分支，構建健壯的工作流
- **編排模式**：Fork-Join、Pipeline、Saga 等實戰模式

**設計思想：**

- **組合優於繼承**：小 Skills 組合成大工作流
- **聲明式配置**：工作流用 JSON/YAML 配置，代碼只負責執行
- **可觀測性**：完整的執行歷史，便於調試和優化

**下一章預告：**

掌握 Skill 編排後，第 8 章將探討 **CI/CD 整合**：如何將 Skills 工作流整合到 GitHub Actions、GitLab CI、Jenkins 等 CI/CD 系統，實現自動化測試的持續執行、定時任務、測試報告生成。這將把我們的自動化能力從本地開發提升到企業級 DevOps 流程。
