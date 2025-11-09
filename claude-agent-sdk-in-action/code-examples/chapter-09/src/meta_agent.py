"""
Meta Agent - 規劃層

負責分析複雜任務、制定執行計畫、動態調整策略
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import anthropic
import json
import re
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任務類型"""
    ANALYSIS = "analysis"  # 分析型任務
    GENERATION = "generation"  # 生成型任務
    TRANSFORMATION = "transformation"  # 轉換型任務
    VALIDATION = "validation"  # 驗證型任務


class TaskPriority(Enum):
    """任務優先級"""
    CRITICAL = 1  # 關鍵路徑
    HIGH = 2  # 高優先級
    MEDIUM = 3  # 中等優先級
    LOW = 4  # 低優先級


@dataclass
class Task:
    """任務定義"""
    id: str
    name: str
    description: str
    task_type: TaskType
    priority: TaskPriority
    dependencies: List[str] = field(default_factory=list)
    estimated_time: int = 300  # 預估時間（秒）
    retry_count: int = 3  # 最大重試次數
    tools: List[str] = field(default_factory=list)  # 需要的工具
    output_format: str = "json"  # 輸出格式
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "estimated_time": self.estimated_time,
            "retry_count": self.retry_count,
            "tools": self.tools,
            "output_format": self.output_format,
            "metadata": self.metadata
        }


@dataclass
class ExecutionPlan:
    """執行計畫"""
    project_name: str
    objective: str
    tasks: List[Task]
    estimated_total_time: int
    critical_path: List[str]  # 關鍵路徑
    parallel_groups: List[List[str]] = field(default_factory=list)  # 並行組
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "project_name": self.project_name,
            "objective": self.objective,
            "tasks": [task.to_dict() for task in self.tasks],
            "estimated_total_time": self.estimated_total_time,
            "critical_path": self.critical_path,
            "parallel_groups": self.parallel_groups,
            "metadata": self.metadata
        }


class MetaAgent:
    """
    Meta Agent - 負責規劃與決策

    核心職責：
    1. 分析複雜任務需求
    2. 制定詳細執行計畫
    3. 識別任務依賴關係
    4. 計算關鍵路徑
    5. 監控執行進度
    6. 動態調整計畫
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-20250514",
        temperature: float = 0.3  # 較低溫度確保計畫一致性
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.conversation_history = []

    def analyze_project(
        self,
        project_description: str,
        codebase_info: Dict[str, Any]
    ) -> ExecutionPlan:
        """
        分析專案需求，生成執行計畫

        Args:
            project_description: 專案描述
            codebase_info: 程式碼庫資訊

        Returns:
            ExecutionPlan: 詳細執行計畫
        """
        # 構建分析 Prompt
        analysis_prompt = f"""
你是一個專業的軟體架構師和專案經理，負責規劃一個複雜的應用程式重寫專案。

## 專案描述
{project_description}

## 現有程式碼庫資訊
```json
{json.dumps(codebase_info, indent=2, ensure_ascii=False)}
```

## 你的任務
請分析這個重寫專案，並制定詳細的執行計畫。計畫應包含：

1. **任務分解**：將專案拆分為 6-10 個具體任務
2. **依賴關係**：明確標註哪些任務必須在其他任務完成後才能執行
3. **優先級**：根據重要性和依賴關係設定優先級（1=CRITICAL, 2=HIGH, 3=MEDIUM, 4=LOW）
4. **時間估算**：預估每個任務的執行時間（秒）
5. **工具需求**：列出每個任務需要的工具（如 bash, read, write, grep, glob, edit 等）
6. **關鍵路徑**：識別影響總時間的關鍵任務序列
7. **並行機會**：找出可以同時執行的任務組

## 輸出格式
請以 JSON 格式輸出計畫，結構如下：

```json
{{
  "project_name": "專案名稱",
  "objective": "專案目標（一句話描述）",
  "tasks": [
    {{
      "id": "task_1",
      "name": "任務名稱",
      "description": "詳細描述任務要做什麼",
      "task_type": "analysis|generation|transformation|validation",
      "priority": 1,
      "dependencies": [],
      "estimated_time": 600,
      "retry_count": 3,
      "tools": ["read", "grep", "glob"],
      "output_format": "json",
      "metadata": {{
        "target_files": "*.php",
        "focus_areas": ["database", "api"]
      }}
    }}
  ],
  "estimated_total_time": 7200,
  "critical_path": ["task_1", "task_3", "task_5"],
  "parallel_groups": [
    ["task_2", "task_4"],
    ["task_6", "task_7"]
  ],
  "metadata": {{
    "complexity": "high",
    "risk_level": "medium"
  }}
}}
```

## 重要提示
- 任務 ID 必須唯一（task_1, task_2, ...）
- dependencies 中的任務 ID 必須存在
- 關鍵路徑應從第一個任務到最後一個任務
- 並行組中的任務不應互相依賴

請開始分析並生成執行計畫。
"""

        logger.info("正在分析專案並生成執行計畫...")

        # 呼叫 Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=self.temperature,
            messages=[
                {"role": "user", "content": analysis_prompt}
            ]
        )

        # 解析回應
        response_text = response.content[0].text
        plan_json = self._extract_json(response_text)

        # 轉換為 ExecutionPlan 物件
        execution_plan = self._parse_execution_plan(plan_json)

        # 儲存對話歷史
        self.conversation_history.append({
            "role": "user",
            "content": analysis_prompt
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })

        logger.info(f"執行計畫生成完成：{len(execution_plan.tasks)} 個任務")

        return execution_plan

    def adjust_plan(
        self,
        current_plan: ExecutionPlan,
        execution_results: List[Dict[str, Any]],
        issues: List[str]
    ) -> ExecutionPlan:
        """
        根據執行結果動態調整計畫

        這是 Meta Agent 的核心能力：自適應決策

        Args:
            current_plan: 當前執行計畫
            execution_results: 已完成任務的結果
            issues: 發現的問題列表

        Returns:
            ExecutionPlan: 調整後的計畫
        """
        adjustment_prompt = f"""
## 當前執行計畫
```json
{json.dumps(current_plan.to_dict(), indent=2, ensure_ascii=False)}
```

## 已完成任務的執行結果
```json
{json.dumps(execution_results, indent=2, ensure_ascii=False)}
```

## 發現的問題
{chr(10).join(f"- {issue}" for issue in issues)}

## 你的任務
請評估當前情況，並決定是否需要調整計畫。可能的調整包括：

1. **添加新任務**：發現遺漏的步驟
2. **修改依賴**：根據實際情況調整順序
3. **調整優先級**：應對緊急問題
4. **增加重試**：提高容錯性
5. **移除任務**：如果某些任務已不需要
6. **修改估時**：根據實際執行情況調整

請輸出調整後的完整計畫（JSON 格式，結構與原計畫相同）。

如果不需要調整，請返回原計畫。
"""

        logger.info("正在根據執行結果調整計畫...")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=self.temperature,
            messages=self.conversation_history + [
                {"role": "user", "content": adjustment_prompt}
            ]
        )

        response_text = response.content[0].text
        adjusted_plan_json = self._extract_json(response_text)
        adjusted_plan = self._parse_execution_plan(adjusted_plan_json)

        # 更新對話歷史
        self.conversation_history.append({
            "role": "user",
            "content": adjustment_prompt
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })

        logger.info("計畫調整完成")

        return adjusted_plan

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """從文字中提取 JSON"""
        # 嘗試找到 JSON 程式碼塊
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 嘗試直接解析整個文字
            json_str = text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # 如果解析失敗，嘗試找到第一個 { 到最後一個 }
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end+1])
                except json.JSONDecodeError:
                    pass

            logger.error(f"無法從回應中提取有效的 JSON: {e}")
            logger.debug(f"回應文字: {text[:500]}...")
            raise ValueError("無法從回應中提取有效的 JSON")

    def _parse_execution_plan(self, plan_json: Dict[str, Any]) -> ExecutionPlan:
        """解析 JSON 為 ExecutionPlan 物件"""
        tasks = []
        for task_data in plan_json.get("tasks", []):
            task = Task(
                id=task_data["id"],
                name=task_data["name"],
                description=task_data["description"],
                task_type=TaskType(task_data["task_type"]),
                priority=TaskPriority(task_data["priority"]),
                dependencies=task_data.get("dependencies", []),
                estimated_time=task_data.get("estimated_time", 300),
                retry_count=task_data.get("retry_count", 3),
                tools=task_data.get("tools", []),
                output_format=task_data.get("output_format", "json"),
                metadata=task_data.get("metadata", {})
            )
            tasks.append(task)

        return ExecutionPlan(
            project_name=plan_json["project_name"],
            objective=plan_json["objective"],
            tasks=tasks,
            estimated_total_time=plan_json.get("estimated_total_time", 0),
            critical_path=plan_json.get("critical_path", []),
            parallel_groups=plan_json.get("parallel_groups", []),
            metadata=plan_json.get("metadata", {})
        )
