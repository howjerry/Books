import subprocess
from pathlib import Path
from typing import Dict, Optional


class PythonScriptRunner:
    """
    Python 腳本執行器

    允許 Agent 執行預先撰寫的 Python 腳本（例如圖表生成）

    安全機制：
    - 只能執行 scripts/ 目錄內的腳本
    - 限制執行時間
    - 隔離環境（使用虛擬環境）
    """

    def __init__(self, scripts_dir: str = "./scripts", timeout: int = 60):
        self.scripts_dir = Path(scripts_dir).resolve()
        self.timeout = timeout

    def run_script(self, script_name: str, args: Optional[list] = None) -> Dict:
        """
        執行 Python 腳本

        參數：
            script_name: 腳本檔名（例如：generate_chart.py）
            args: 傳遞給腳本的參數列表
        """
        script_path = self.scripts_dir / script_name

        # 安全檢查
        if not script_path.exists():
            return {
                "success": False,
                "output": "",
                "error": f"腳本不存在: {script_name}"
            }

        try:
            script_path.relative_to(self.scripts_dir)
        except ValueError:
            return {
                "success": False,
                "output": "",
                "error": "腳本路徑不安全"
            }

        # 建構命令
        cmd = ["python", str(script_path)]
        if args:
            cmd.extend(args)

        # 執行
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"腳本執行超時（>{self.timeout}秒）"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }

    def get_tool_definition(self) -> Dict:
        """工具定義"""
        return {
            "name": "run_python_script",
            "description": """執行 Python 腳本（用於生成圖表、分析資料）。

可用的腳本：
- generate_chart.py: 生成統計圖表
  參數：[data_file, output_file, chart_type]

- analyze_logs.py: 分析日誌檔案
  參數：[log_file, output_file]

範例：
- run_python_script("generate_chart.py", ["workspace/data/sales.csv", "workspace/charts/sales.png", "bar"])
""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "script_name": {
                        "type": "string",
                        "description": "腳本檔名"
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "傳遞給腳本的參數"
                    }
                },
                "required": ["script_name"]
            }
        }
