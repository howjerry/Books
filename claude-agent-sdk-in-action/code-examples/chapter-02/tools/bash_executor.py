import subprocess
import yaml
from typing import Dict, List, Optional
from pathlib import Path


class SafeBashExecutor:
    """
    安全的 Bash 命令執行器

    核心安全機制：
    1. 命令白名單：只允許預先定義的命令
    2. 參數驗證：檢查參數中的危險模式
    3. 超時保護：防止長時間執行
    4. 路徑限制：只能訪問特定目錄
    """

    def __init__(self, config_path: str = "sandbox/allowed_commands.yaml"):
        self.config = self._load_config(config_path)
        self.allowed_commands = self.config.get("allowed_commands", [])
        self.blocked_patterns = self.config.get("blocked_patterns", [])
        self.allowed_workspace = Path(self.config.get("workspace", "./workspace"))
        self.timeout = self.config.get("timeout", 30)

    def _load_config(self, config_path: str) -> Dict:
        """載入安全配置"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _validate_command(self, command: str) -> tuple[bool, Optional[str]]:
        """
        驗證命令是否安全

        檢查項目：
        1. 命令是否在白名單中
        2. 是否包含危險模式（如 rm -rf, sudo 等）
        3. 路徑是否在允許範圍內
        """
        # 提取命令名稱（第一個單字）
        cmd_name = command.split()[0] if command.strip() else ""

        # 檢查白名單
        if cmd_name not in self.allowed_commands:
            return False, f"命令 '{cmd_name}' 不在白名單中"

        # 檢查危險模式
        for pattern in self.blocked_patterns:
            if pattern in command:
                return False, f"命令包含危險模式: '{pattern}'"

        # 檢查路徑限制
        if ".." in command or "~" in command:
            return False, "不允許使用相對路徑或家目錄符號"

        return True, None

    def execute(self, command: str, working_dir: Optional[str] = None) -> Dict:
        """
        執行命令並回傳結果

        參數：
            command: 要執行的 Bash 命令
            working_dir: 工作目錄（必須在 allowed_workspace 內）

        回傳：
            {
                "success": bool,
                "stdout": str,
                "stderr": str,
                "return_code": int
            }
        """
        # 驗證命令
        is_valid, error_msg = self._validate_command(command)
        if not is_valid:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"安全檢查失敗: {error_msg}",
                "return_code": -1
            }

        # 設定工作目錄
        if working_dir:
            work_path = Path(working_dir).resolve()
            try:
                work_path.relative_to(self.allowed_workspace.resolve())
            except ValueError:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "工作目錄超出允許範圍",
                    "return_code": -1
                }
        else:
            work_path = self.allowed_workspace

        # 執行命令
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(work_path)
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"命令執行超時（>{self.timeout}秒）",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"執行錯誤: {str(e)}",
                "return_code": -1
            }

    def get_tool_definition(self) -> Dict:
        """
        回傳 Claude Tool Use 格式的工具定義
        """
        return {
            "name": "execute_bash",
            "description": f"""執行安全的 Bash 命令。

允許的命令：{', '.join(self.allowed_commands)}

使用範例：
- 查詢資料庫統計：psql -d mydb -c "SELECT COUNT(*) FROM users"
- 搜尋日誌錯誤：grep ERROR workspace/logs/app.log
- 計算檔案行數：wc -l workspace/data/users.csv

安全限制：
- 只能在 {self.allowed_workspace} 目錄內操作
- 命令執行超時時間：{self.timeout} 秒
- 禁止使用危險命令（rm -rf, sudo 等）
""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要執行的 Bash 命令"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "工作目錄（選填，必須在允許範圍內）"
                    }
                },
                "required": ["command"]
            }
        }
