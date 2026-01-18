"""程式碼執行工具"""

import subprocess
import tempfile
import os

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class CodeInput(BaseModel):
    """程式碼執行參數"""
    code: str = Field(description="要執行的 Python 程式碼")
    timeout: int = Field(
        default=5,
        description="執行超時秒數（最大 10 秒）",
        ge=1,
        le=10
    )


# 禁止的模組和函數（安全限制）
FORBIDDEN_PATTERNS = [
    # 系統操作
    "os.system",
    "os.popen",
    "os.exec",
    "os.spawn",
    "os.remove",
    "os.unlink",
    "os.rmdir",
    "shutil.rmtree",
    # 子程序
    "subprocess",
    "Popen",
    # 動態執行
    "exec(",
    "eval(",
    "compile(",
    "__import__",
    # 檔案操作（只允許讀取）
    "open(",  # 會在下面特殊處理
    # 網路
    "socket",
    "urllib",
    "requests",
    "httpx",
]


def check_code_safety(code: str) -> tuple[bool, str]:
    """檢查程式碼是否安全

    Returns:
        (is_safe, message) 元組
    """
    code_lower = code.lower()

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in code_lower:
            # 特殊處理 open() - 允許讀取模式
            if pattern == "open(":
                # 檢查是否只用於讀取
                if "'w'" in code or '"w"' in code or "'a'" in code or '"a"' in code:
                    return False, f"安全限制：不允許寫入檔案"
                continue

            return False, f"安全限制：不允許使用 {pattern}"

    return True, "OK"


@tool(args_schema=CodeInput)
def run_python_code(code: str, timeout: int = 5) -> str:
    """在安全沙箱中執行 Python 程式碼。

    用於：
    - 驗證程式碼是否能正確執行
    - 展示程式碼輸出
    - 進行簡單的資料處理
    - 測試演算法

    安全限制：
    - 最長執行時間：10 秒
    - 禁止：系統命令、網路請求、檔案寫入
    - 允許：標準庫的大部分功能、檔案讀取

    Returns:
        程式碼的標準輸出或錯誤訊息
    """
    # 限制超時
    timeout = min(timeout, 10)

    # 安全檢查
    is_safe, message = check_code_safety(code)
    if not is_safe:
        return f"❌ {message}"

    try:
        # 建立臨時檔案
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = f.name

        # 在子程序中執行
        result = subprocess.run(
            ["python", temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 清理臨時檔案
        try:
            os.unlink(temp_path)
        except:
            pass

        # 處理結果
        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                return "✅ 執行成功（無輸出）"
            return f"✅ 執行成功：\n```\n{output}\n```"
        else:
            error = result.stderr.strip()
            # 簡化錯誤訊息（移除檔案路徑）
            error = error.replace(temp_path, "<script>")
            return f"❌ 執行錯誤：\n```\n{error}\n```"

    except subprocess.TimeoutExpired:
        # 清理臨時檔案
        try:
            os.unlink(temp_path)
        except:
            pass
        return f"❌ 執行超時：程式執行時間超過 {timeout} 秒"

    except FileNotFoundError:
        return "❌ 錯誤：找不到 Python 解釋器"

    except Exception as e:
        return f"❌ 執行錯誤：{e}"
