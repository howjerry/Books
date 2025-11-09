"""
簡單範例：使用 Meta Agent 系統分析和重構小型專案
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from meta_agent import MetaAgent
from task_coordinator import TaskCoordinator
from dotenv import load_dotenv


async def simple_refactoring_example():
    """
    簡單範例：分析並重構一個 Python 專案
    """
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("❌ 請設定 ANTHROPIC_API_KEY 環境變數")
        return

    # 步驟 1：創建 Meta Agent
    print("=" * 60)
    print("步驟 1：創建 Meta Agent")
    print("=" * 60)

    meta_agent = MetaAgent(api_key=api_key)

    # 步驟 2：定義專案
    project_description = """
重構一個 Python Flask 應用程式，提升程式碼品質。

目標：
1. 提取重複的邏輯到共用函式
2. 改善錯誤處理
3. 添加型別提示
4. 編寫單元測試
5. 更新文件
"""

    codebase_info = {
        "total_files": 5,
        "total_lines": 850,
        "languages": {"python": 1.0},
        "files": [
            {"name": "app.py", "lines": 320},
            {"name": "models.py", "lines": 180},
            {"name": "utils.py", "lines": 120},
            {"name": "config.py", "lines": 80},
            {"name": "tests.py", "lines": 150}
        ]
    }

    # 步驟 3：生成執行計畫
    print("\n" + "=" * 60)
    print("步驟 2：生成執行計畫")
    print("=" * 60)

    plan = meta_agent.analyze_project(project_description, codebase_info)

    print(f"\n專案：{plan.project_name}")
    print(f"目標：{plan.objective}")
    print(f"\n任務列表（{len(plan.tasks)} 個）：")

    for i, task in enumerate(plan.tasks, 1):
        deps = f" [依賴: {', '.join(task.dependencies)}]" if task.dependencies else ""
        print(f"  {i}. {task.name} ({task.task_type.value}){deps}")
        print(f"     預估時間：{task.estimated_time // 60} 分鐘")

    print(f"\n關鍵路徑：{' → '.join(plan.critical_path)}")

    if plan.parallel_groups:
        print(f"\n可並行執行：")
        for i, group in enumerate(plan.parallel_groups, 1):
            print(f"  組 {i}：{', '.join(group)}")

    # 步驟 4：執行計畫（示範模式，不實際執行）
    print("\n" + "=" * 60)
    print("步驟 3：執行計畫（示範模式）")
    print("=" * 60)
    print("\n在真實場景中，TaskCoordinator 將會：")
    print("  1. 創建專門的 Subagents")
    print("  2. 根據依賴關係調度任務")
    print("  3. 並行執行獨立任務")
    print("  4. 收集結果並生成報告")

    print("\n若要實際執行，請使用：")
    print("  coordinator = TaskCoordinator(plan, max_parallel=3, api_key=api_key)")
    print("  result = await coordinator.execute_plan()")

    print("\n" + "=" * 60)
    print("✅ 範例完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(simple_refactoring_example())
