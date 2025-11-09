from anthropic import Anthropic
from typing import Dict, List
import os
from dotenv import load_dotenv
import json

# 載入工具
from tools.bash_executor import SafeBashExecutor
from tools.file_operations import FileOperations
from tools.script_runner import PythonScriptRunner

load_dotenv()


class ReportCoordinator:
    """
    報表協調器 - 主 Agent

    職責：
    1. 理解報表需求
    2. 規劃執行步驟
    3. 呼叫工具完成任務
    4. 生成最終報表
    """

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"

        # 初始化工具
        self.bash_executor = SafeBashExecutor()
        self.file_ops = FileOperations()
        self.script_runner = PythonScriptRunner()

        # 系統提示詞
        self.system_prompt = """你是一個專業的報表生成助理。

你的任務是：
1. 理解使用者的報表需求
2. 規劃資料收集與處理流程
3. 使用提供的工具完成任務：
   - execute_bash: 執行資料查詢（SQL、日誌搜尋等）
   - read_file: 讀取資料檔案
   - write_file: 寫入報表內容
   - run_python_script: 生成圖表
   - list_directory: 查看可用檔案

4. 生成專業的報表文件（Markdown 格式）

報表結構建議：
```markdown
# [報表標題]

## 執行摘要
[2-3 句話總結關鍵發現]

## 資料分析

### 1. [分析主題 1]
- 資料來源：...
- 關鍵發現：...
- 視覺化：![圖表](../charts/xxx.png)

### 2. [分析主題 2]
...

## 建議與後續行動
1. ...
2. ...

---
報表生成時間：[timestamp]
```

注意事項：
- 所有檔案操作都在 workspace/ 目錄內
- 圖表儲存在 workspace/charts/
- 最終報表儲存在 workspace/reports/
- 使用清晰、專業的語言
"""

    def _get_all_tools(self) -> List[Dict]:
        """收集所有工具定義"""
        tools = []
        tools.append(self.bash_executor.get_tool_definition())
        tools.extend(self.file_ops.get_tool_definitions())
        tools.append(self.script_runner.get_tool_definition())
        return tools

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> Dict:
        """
        執行工具並回傳結果
        """
        if tool_name == "execute_bash":
            return self.bash_executor.execute(
                command=tool_input["command"],
                working_dir=tool_input.get("working_dir")
            )

        elif tool_name == "read_file":
            return self.file_ops.read_file(
                file_path=tool_input["file_path"],
                file_type=tool_input.get("file_type", "text")
            )

        elif tool_name == "write_file":
            return self.file_ops.write_file(
                file_path=tool_input["file_path"],
                content=tool_input["content"],
                file_type=tool_input.get("file_type", "text")
            )

        elif tool_name == "list_directory":
            return self.file_ops.list_directory(
                dir_path=tool_input.get("dir_path", ".")
            )

        elif tool_name == "run_python_script":
            return self.script_runner.run_script(
                script_name=tool_input["script_name"],
                args=tool_input.get("args")
            )

        else:
            return {"error": f"未知工具: {tool_name}"}

    def generate_report(self, request: str, max_iterations: int = 15) -> Dict:
        """
        生成報表（主要入口）

        參數：
            request: 報表需求描述
            max_iterations: 最大迭代次數（防止無限循環）

        回傳：
            {
                "success": bool,
                "report_path": str,
                "message": str,
                "steps": List[str]  # 執行步驟記錄
            }
        """
        messages = [{"role": "user", "content": request}]
        steps = []

        for iteration in range(max_iterations):
            # 呼叫 Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self._get_all_tools(),
                messages=messages
            )

            # 檢查是否完成
            if response.stop_reason == "end_turn":
                # Agent 已完成任務
                final_message = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_message += block.text

                return {
                    "success": True,
                    "message": final_message,
                    "steps": steps
                }

            # 處理工具呼叫
            if response.stop_reason == "tool_use":
                # 將 Assistant 的回應加入對話
                messages.append({"role": "assistant", "content": response.content})

                # 執行所有工具呼叫
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input

                        # 記錄步驟
                        step_desc = f"[{iteration + 1}] 執行工具: {tool_name}"
                        if tool_name == "execute_bash":
                            step_desc += f" - {tool_input['command']}"
                        elif tool_name in ["read_file", "write_file"]:
                            step_desc += f" - {tool_input['file_path']}"
                        steps.append(step_desc)
                        print(f"  {step_desc}")

                        # 執行工具
                        result = self._execute_tool(tool_name, tool_input)

                        # 加入結果
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })

                # 將工具結果加入對話
                messages.append({"role": "user", "content": tool_results})

            else:
                # 意外的停止原因
                return {
                    "success": False,
                    "message": f"意外的停止原因: {response.stop_reason}",
                    "steps": steps
                }

        # 達到最大迭代次數
        return {
            "success": False,
            "message": f"達到最大迭代次數 ({max_iterations})",
            "steps": steps
        }
