"""
Subagent Executor - 執行層

負責創建並管理專門化的 Subagents，執行具體任務
"""

from typing import Dict, Any
import anthropic
import os
import logging
import re
import json

from meta_agent import Task, TaskType

logger = logging.getLogger(__name__)


class SubagentExecutor:
    """
    Subagent 執行器 - 創建並管理專門化的 Subagents

    職責：
    1. 根據任務類型創建合適的 Subagent
    2. 配置 Subagent 的 Context 與工具
    3. 執行任務並收集結果
    4. 處理執行過程中的錯誤
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)

        # Subagent 配置模板
        self.agent_configs = {
            TaskType.ANALYSIS: {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "temperature": 0.3
            },
            TaskType.GENERATION: {
                "model": "claude-opus-4-20250514",
                "max_tokens": 8192,
                "temperature": 0.5
            },
            TaskType.TRANSFORMATION: {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 6144,
                "temperature": 0.4
            },
            TaskType.VALIDATION: {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "temperature": 0.2
            }
        }

    async def execute(self, task: Task) -> Dict[str, Any]:
        """
        執行任務

        Args:
            task: 要執行的任務

        Returns:
            執行結果
        """
        logger.info(f"創建 Subagent 執行任務：{task.name}")

        # 獲取配置
        config = self.agent_configs.get(
            task.task_type,
            self.agent_configs[TaskType.ANALYSIS]
        )

        # 構建 System Prompt（Context）
        system_prompt = self._build_system_prompt(task)

        # 構建任務 Prompt
        task_prompt = self._build_task_prompt(task)

        logger.debug(f"使用模型：{config['model']}")
        logger.debug(f"System Prompt 長度：{len(system_prompt)} 字元")
        logger.debug(f"Task Prompt 長度：{len(task_prompt)} 字元")

        # 執行
        try:
            response = self.client.messages.create(
                model=config["model"],
                max_tokens=config["max_tokens"],
                temperature=config["temperature"],
                system=system_prompt,
                messages=[
                    {"role": "user", "content": task_prompt}
                ]
            )

            # 解析結果
            response_text = response.content[0].text
            parsed_result = self._parse_result(response_text, task.output_format)

            # 記錄使用量
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_cost": self._calculate_cost(
                    config["model"],
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )
            }

            logger.info(
                f"任務完成 - "
                f"輸入: {usage['input_tokens']} tokens, "
                f"輸出: {usage['output_tokens']} tokens, "
                f"成本: ${usage['total_cost']:.4f}"
            )

            return {
                "status": "success",
                "output": parsed_result,
                "raw_response": response_text,
                "model": config["model"],
                "metrics": usage
            }

        except Exception as e:
            logger.error(f"Subagent 執行失敗：{e}")
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _build_system_prompt(self, task: Task) -> str:
        """構建 System Prompt（根據任務類型）"""

        base_context = f"""
你是一個專業的軟體工程師，負責執行以下任務：

## 任務資訊
- 名稱：{task.name}
- 類型：{task.task_type.value}
- 優先級：{task.priority.name}

## 任務描述
{task.description}
"""

        # 根據任務類型添加專門指引
        if task.task_type == TaskType.ANALYSIS:
            return base_context + """

## 你的專長
你是一個程式碼分析專家，擅長：
1. 讀取和理解程式碼結構
2. 識別設計模式和架構
3. 提取關鍵資訊和依賴關係
4. 評估程式碼複雜度和品質

## 工作方式
- 仔細閱讀所有相關檔案
- 識別核心邏輯和資料流
- 記錄重要的發現
- 以結構化方式輸出分析結果

## 輸出要求
- 全面：不遺漏重要資訊
- 準確：確保分析正確無誤
- 結構化：使用清晰的格式
"""

        elif task.task_type == TaskType.GENERATION:
            return base_context + """

## 你的專長
你是一個程式碼生成專家，擅長：
1. 設計清晰的架構
2. 編寫高品質程式碼
3. 遵循最佳實踐
4. 創建完整的文件

## 程式碼品質要求
- **可讀性**：清晰的命名、適當的註解
- **可維護性**：模組化設計、低耦合高內聚
- **健壯性**：完整的錯誤處理
- **可測試性**：易於單元測試
- **效能**：考慮時間和空間複雜度

## 最佳實踐
- 遵循 PEP 8（Python）或相應語言的編碼規範
- 使用型別提示（Type Hints）
- 編寫 docstring 文件
- 處理邊界條件和錯誤情況
- 避免硬編碼，使用配置
"""

        elif task.task_type == TaskType.TRANSFORMATION:
            return base_context + """

## 你的專長
你是一個程式碼轉換專家，擅長：
1. 保持原有邏輯不變
2. 提升程式碼品質
3. 適配目標語言慣例
4. 優化效能和結構

## 轉換原則
- **等價性**：確保轉換前後邏輯完全一致
- **慣例性**：遵循目標語言的最佳實踐
- **完整性**：不遺漏任何功能
- **清晰性**：提升程式碼可讀性
"""

        elif task.task_type == TaskType.VALIDATION:
            return base_context + """

## 你的專長
你是一個 QA 工程師，擅長：
1. 驗證功能正確性
2. 測試邊界條件
3. 檢查錯誤處理
4. 評估程式碼品質

## 驗證重點
- **功能性**：是否實現了所有需求
- **正確性**：邏輯是否正確無誤
- **健壯性**：錯誤處理是否完整
- **效能**：是否有明顯瓶頸
- **安全性**：是否存在安全風險
"""

        return base_context

    def _build_task_prompt(self, task: Task) -> str:
        """構建任務 Prompt"""
        prompt = f"""
請執行任務：{task.name}

## 任務描述
{task.description}
"""

        # 添加元數據
        if task.metadata:
            prompt += "\n## 額外資訊\n"
            for key, value in task.metadata.items():
                prompt += f"- **{key}**：{value}\n"

        # 添加輸出格式要求
        prompt += f"\n## 輸出格式\n"
        if task.output_format == "json":
            prompt += """
請以 JSON 格式輸出結果，包含在程式碼塊中：

```json
{
  "summary": "任務摘要",
  "details": {
    // 詳細結果
  },
  "findings": [
    // 重要發現
  ],
  "recommendations": [
    // 建議
  ]
}
```
"""
        else:
            prompt += f"請以 {task.output_format} 格式輸出結果。\n"

        prompt += "\n請開始執行任務。"

        return prompt

    def _parse_result(self, text: str, output_format: str) -> Any:
        """解析 Subagent 的輸出"""
        if output_format == "json":
            # 從文字中提取 JSON
            json_match = re.search(
                r'```(?:json)?\s*(\{.*?\})\s*```',
                text,
                re.DOTALL
            )

            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON 解析失敗：{e}")
                    return {"raw_output": text, "parse_error": str(e)}

            # 嘗試直接解析
            try:
                # 尋找第一個 { 到最後一個 }
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass

            # 無法解析，返回原始文字
            return {"raw_output": text}

        # 其他格式直接返回文字
        return text

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """計算 API 成本（USD）"""

        # 模型價格（每百萬 tokens）
        pricing = {
            "claude-haiku-3-20250307": {"input": 0.25, "output": 1.25},
            "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
            "claude-opus-4-20250514": {"input": 15.00, "output": 75.00}
        }

        if model not in pricing:
            logger.warning(f"未知模型 {model}，使用 Sonnet 價格估算")
            model = "claude-sonnet-4-20250514"

        cost = (
            input_tokens / 1_000_000 * pricing[model]["input"] +
            output_tokens / 1_000_000 * pricing[model]["output"]
        )

        return cost
