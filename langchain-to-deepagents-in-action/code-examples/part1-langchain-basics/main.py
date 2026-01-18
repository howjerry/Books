#!/usr/bin/env python3
"""TechAssist 主程式入口

使用方式：
    python main.py           # 執行最新版 (v0.3)
    python main.py --v1      # 執行 v0.1 (基礎問答)
    python main.py --v2      # 執行 v0.2 (意圖分類)
    python main.py --v3      # 執行 v0.3 (工具增強)
"""

import sys
from dotenv import load_dotenv


def main():
    # 載入環境變數
    load_dotenv()

    # 解析命令列參數
    version = "v3"  # 預設版本

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("--v1", "-1", "v1"):
            version = "v1"
        elif arg in ("--v2", "-2", "v2"):
            version = "v2"
        elif arg in ("--v3", "-3", "v3"):
            version = "v3"
        elif arg in ("--help", "-h"):
            print(__doc__)
            return

    # 啟動對應版本
    from techassist.cli import run_cli_v1, run_cli_v2, run_cli_v3

    if version == "v1":
        run_cli_v1()
    elif version == "v2":
        run_cli_v2()
    else:
        run_cli_v3()


if __name__ == "__main__":
    main()
