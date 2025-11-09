from pathlib import Path
from typing import Dict, Optional
import json
import csv


class FileOperations:
    """
    檔案操作工具集

    支援的操作：
    1. 讀取檔案（TXT, JSON, CSV）
    2. 寫入檔案（TXT, JSON, Markdown）
    3. 列出目錄內容

    安全機制：
    - 路徑限制：只能在 workspace/ 內操作
    - 檔案大小限制：防止讀取超大檔案
    """

    def __init__(self, workspace: str = "./workspace"):
        self.workspace = Path(workspace).resolve()
        self.max_file_size = 10 * 1024 * 1024  # 10 MB

    def _validate_path(self, file_path: str) -> tuple[bool, Optional[Path]]:
        """驗證路徑是否安全"""
        try:
            full_path = (self.workspace / file_path).resolve()

            # 檢查是否在 workspace 內
            full_path.relative_to(self.workspace)

            return True, full_path
        except (ValueError, Exception):
            return False, None

    def read_file(self, file_path: str, file_type: str = "text") -> Dict:
        """
        讀取檔案內容

        參數：
            file_path: 相對於 workspace 的檔案路徑
            file_type: 檔案類型（text, json, csv）
        """
        is_valid, full_path = self._validate_path(file_path)
        if not is_valid:
            return {
                "success": False,
                "content": None,
                "error": "路徑不安全或超出工作範圍"
            }

        if not full_path.exists():
            return {
                "success": False,
                "content": None,
                "error": f"檔案不存在: {file_path}"
            }

        # 檢查檔案大小
        if full_path.stat().st_size > self.max_file_size:
            return {
                "success": False,
                "content": None,
                "error": f"檔案過大（>{self.max_file_size / 1024 / 1024} MB）"
            }

        try:
            if file_type == "json":
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
            elif file_type == "csv":
                with open(full_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    content = list(reader)
            else:  # text
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            return {
                "success": True,
                "content": content,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "content": None,
                "error": f"讀取失敗: {str(e)}"
            }

    def write_file(self, file_path: str, content: str, file_type: str = "text") -> Dict:
        """
        寫入檔案

        參數：
            file_path: 相對於 workspace 的檔案路徑
            content: 要寫入的內容
            file_type: 檔案類型（text, json）
        """
        is_valid, full_path = self._validate_path(file_path)
        if not is_valid:
            return {
                "success": False,
                "error": "路徑不安全或超出工作範圍"
            }

        # 確保目錄存在
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if file_type == "json":
                with open(full_path, 'w', encoding='utf-8') as f:
                    json.dump(json.loads(content), f, indent=2, ensure_ascii=False)
            else:  # text, markdown
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            return {
                "success": True,
                "path": str(full_path.relative_to(self.workspace)),
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"寫入失敗: {str(e)}"
            }

    def list_directory(self, dir_path: str = ".") -> Dict:
        """
        列出目錄內容
        """
        is_valid, full_path = self._validate_path(dir_path)
        if not is_valid:
            return {
                "success": False,
                "files": [],
                "error": "路徑不安全"
            }

        if not full_path.is_dir():
            return {
                "success": False,
                "files": [],
                "error": "不是目錄"
            }

        try:
            files = []
            for item in full_path.iterdir():
                files.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })

            return {
                "success": True,
                "files": files,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "files": [],
                "error": f"列表失敗: {str(e)}"
            }

    def get_tool_definitions(self) -> list[Dict]:
        """
        回傳所有檔案操作工具的定義
        """
        return [
            {
                "name": "read_file",
                "description": """讀取檔案內容。

支援的檔案類型：
- text: 純文字檔案（.txt, .md, .log）
- json: JSON 格式
- csv: CSV 表格

範例：
- read_file("logs/app.log", "text")
- read_file("data/users.json", "json")
- read_file("data/sales.csv", "csv")
""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "檔案路徑（相對於 workspace）"
                        },
                        "file_type": {
                            "type": "string",
                            "enum": ["text", "json", "csv"],
                            "description": "檔案類型"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "write_file",
                "description": """寫入檔案。

支援的格式：
- text: 純文字、Markdown
- json: JSON 格式（會自動格式化）

範例：
- write_file("reports/summary.md", "# 週報...", "text")
- write_file("data/config.json", '{"key": "value"}', "json")
""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "檔案路徑"
                        },
                        "content": {
                            "type": "string",
                            "description": "要寫入的內容"
                        },
                        "file_type": {
                            "type": "string",
                            "enum": ["text", "json"],
                            "description": "檔案類型"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "list_directory",
                "description": """列出目錄內容。

回傳目錄中的所有檔案和子目錄。

範例：
- list_directory("data")
- list_directory("reports")
""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "dir_path": {
                            "type": "string",
                            "description": "目錄路徑（預設為根目錄）"
                        }
                    },
                    "required": []
                }
            }
        ]
