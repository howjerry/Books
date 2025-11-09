"""
Main Application - 完整應用程式重寫系統

整合 Meta Agent（規劃層）、Task Coordinator（協調層）、Subagent Executor（執行層）
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

from meta_agent import MetaAgent, ExecutionPlan
from task_coordinator import TaskCoordinator

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('application_rewrite.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ApplicationRewriteSystem:
    """
    完整應用程式重寫系統

    整合三層架構：
    - Meta Agent（規劃層）
    - Task Coordinator（協調層）
    - Subagent Executor（執行層）
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.meta_agent = MetaAgent(api_key=api_key)
        self.execution_history = []

    async def rewrite_application(
        self,
        project_description: str,
        codebase_path: str,
        output_path: str,
        max_parallel: int = 3
    ) -> Dict[str, Any]:
        """
        執行完整的應用程式重寫流程

        Args:
            project_description: 專案描述
            codebase_path: 原始程式碼路徑
            output_path: 輸出路徑
            max_parallel: 最大並行任務數

        Returns:
            完整的執行報告
        """
        logger.info("=" * 80)
        logger.info("開始應用程式重寫專案")
        logger.info("=" * 80)

        start_time = datetime.now()

        # 創建輸出目錄
        os.makedirs(output_path, exist_ok=True)

        # 階段 1：掃描程式碼庫
        logger.info("\n[階段 1/4] 掃描程式碼庫...")
        codebase_info = self._scan_codebase(codebase_path)
        logger.info(
            f"發現 {codebase_info['total_files']} 個檔案，"
            f"{codebase_info['total_lines']:,} 行程式碼"
        )

        # 儲存程式碼庫資訊
        with open(os.path.join(output_path, "codebase_analysis.json"), 'w', encoding='utf-8') as f:
            json.dump(codebase_info, f, indent=2, ensure_ascii=False)

        # 階段 2：生成執行計畫
        logger.info("\n[階段 2/4] 生成執行計畫...")
        plan = self.meta_agent.analyze_project(
            project_description,
            codebase_info
        )

        logger.info(f"計畫生成完成：")
        logger.info(f"  - 總任務數：{len(plan.tasks)}")
        logger.info(f"  - 預估時間：{plan.estimated_total_time // 60} 分鐘")
        logger.info(f"  - 關鍵路徑：{len(plan.critical_path)} 個任務")
        logger.info(f"  - 可並行組：{len(plan.parallel_groups)} 組")

        # 儲存計畫
        self._save_plan(plan, output_path)

        # 階段 3：執行計畫
        logger.info("\n[階段 3/4] 執行重寫任務...")
        logger.info(f"最大並行數：{max_parallel}")

        coordinator = TaskCoordinator(
            plan=plan,
            max_parallel=max_parallel,
            api_key=self.api_key
        )

        execution_result = await coordinator.execute_plan()

        # 階段 4：生成報告
        logger.info("\n[階段 4/4] 生成最終報告...")

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        final_report = {
            "project": {
                "name": plan.project_name,
                "objective": plan.objective,
                "codebase_path": codebase_path,
                "output_path": output_path
            },
            "codebase_info": codebase_info,
            "execution": execution_result,
            "timing": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_duration": total_duration,
                "estimated_duration": plan.estimated_total_time,
                "efficiency": (
                    plan.estimated_total_time / total_duration
                    if total_duration > 0 else 0
                )
            },
            "quality_metrics": self._calculate_quality_metrics(execution_result)
        }

        # 儲存報告
        self._save_report(final_report, output_path)

        # 列印摘要
        self._print_summary(final_report)

        return final_report

    def _scan_codebase(self, path: str) -> Dict[str, Any]:
        """
        掃描程式碼庫

        Returns:
            程式碼庫統計資訊
        """
        if not os.path.exists(path):
            logger.warning(f"路徑不存在：{path}，返回模擬數據")
            return {
                "total_files": 0,
                "total_lines": 0,
                "file_types": {},
                "path": path,
                "note": "路徑不存在，這是模擬數據"
            }

        total_files = 0
        total_lines = 0
        file_types = {}
        largest_files = []

        for root, dirs, files in os.walk(path):
            # 跳過隱藏目錄和常見的忽略目錄
            dirs[:] = [
                d for d in dirs
                if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__', 'dist', 'build']
            ]

            for file in files:
                if file.startswith('.'):
                    continue

                file_path = Path(root) / file
                suffix = file_path.suffix.lower() or 'no_extension'

                total_files += 1
                file_types[suffix] = file_types.get(suffix, 0) + 1

                # 計算行數
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = len(f.readlines())
                        total_lines += lines

                        # 記錄大檔案
                        largest_files.append({
                            "path": str(file_path),
                            "lines": lines,
                            "size_kb": file_path.stat().st_size / 1024
                        })
                except Exception as e:
                    logger.debug(f"無法讀取檔案 {file_path}: {e}")

        # 只保留前 10 大檔案
        largest_files.sort(key=lambda x: x["lines"], reverse=True)
        largest_files = largest_files[:10]

        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "file_types": file_types,
            "largest_files": largest_files,
            "path": path
        }

    def _save_plan(self, plan: ExecutionPlan, output_path: str):
        """儲存執行計畫"""
        plan_file = os.path.join(output_path, "execution_plan.json")
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 執行計畫已儲存：{plan_file}")

    def _save_report(self, report: Dict[str, Any], output_path: str):
        """儲存最終報告"""
        report_file = os.path.join(output_path, "final_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 最終報告已儲存：{report_file}")

    def _calculate_quality_metrics(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """計算品質指標"""
        summary = execution_result["summary"]

        total_cost = sum(
            task.get("result", {}).get("metrics", {}).get("total_cost", 0)
            for task in execution_result.get("completed_tasks", [])
        )

        return {
            "success_rate": summary["success_rate"],
            "time_efficiency": summary.get("time_efficiency", 0),
            "tasks_completed": summary["completed"],
            "tasks_failed": summary["failed"],
            "total_cost_usd": total_cost,
            "average_cost_per_task": (
                total_cost / summary["completed"]
                if summary["completed"] > 0 else 0
            )
        }

    def _print_summary(self, report: Dict[str, Any]):
        """列印執行摘要"""
        logger.info("\n" + "=" * 80)
        logger.info("執行摘要")
        logger.info("=" * 80)

        project = report["project"]
        execution = report["execution"]["summary"]
        timing = report["timing"]
        quality = report["quality_metrics"]

        logger.info(f"\n專案：{project['name']}")
        logger.info(f"目標：{project['objective']}")

        logger.info(f"\n執行結果：")
        logger.info(f"  ✅ 完成任務：{execution['completed']}/{execution['total_tasks']}")
        logger.info(f"  ❌ 失敗任務：{execution['failed']}")
        logger.info(f"  📊 成功率：{execution['success_rate']:.1%}")

        logger.info(f"\n時間統計：")
        logger.info(f"  ⏱️  實際耗時：{timing['total_duration'] / 60:.1f} 分鐘")
        logger.info(f"  📅 預估耗時：{timing['estimated_duration'] / 60:.1f} 分鐘")
        logger.info(f"  ⚡ 效率比：{timing['efficiency']:.2f}x")

        logger.info(f"\n品質指標：")
        logger.info(f"  💰 總成本：${quality['total_cost_usd']:.4f}")
        logger.info(f"  💵 平均成本：${quality['average_cost_per_task']:.4f}/任務")
        logger.info(f"  🎯 時間效率：{quality['time_efficiency']:.2f}x")

        logger.info("\n" + "=" * 80)


async def main():
    """主程式入口"""

    # 載入環境變數
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        logger.error("❌ 請設定 ANTHROPIC_API_KEY 環境變數")
        return

    # 創建系統
    system = ApplicationRewriteSystem(api_key=api_key)

    # 定義重寫專案
    project_description = """
將一個 8 年歷史的 PHP 單體 ERP 系統重寫為 Python 微服務架構。

## 原系統
- PHP 5.6 + MySQL
- 約 30,000 行程式碼
- 4 個核心模組：客戶管理、訂單處理、庫存管理、帳單系統
- 單體架構，所有功能在一個應用中

## 目標系統
- Python 3.11 + FastAPI
- PostgreSQL + Redis
- 微服務架構（每個模組獨立服務）
- RESTful API 設計
- Docker 容器化部署
- 完整的單元測試與整合測試（覆蓋率 > 90%）
- API 文件（OpenAPI/Swagger）
- 部署指南

## 技術要求
- 使用 Pydantic 進行資料驗證
- 使用 SQLAlchemy 進行 ORM
- 實作 JWT 認證
- Redis 快取熱資料
- 完整的錯誤處理與日誌記錄
"""

    # 執行重寫
    report = await system.rewrite_application(
        project_description=project_description,
        codebase_path="./legacy_erp",  # 原始程式碼路徑
        output_path="./output/rewritten_system",  # 輸出路徑
        max_parallel=3  # 最大並行任務數
    )

    # 顯示結果
    print("\n" + "=" * 80)
    print("✅ 重寫完成！")
    print("=" * 80)
    print(f"📁 輸出目錄：{report['project']['output_path']}")
    print(f"📊 執行計畫：{report['project']['output_path']}/execution_plan.json")
    print(f"📄 詳細報告：{report['project']['output_path']}/final_report.json")
    print(f"💰 總成本：${report['quality_metrics']['total_cost_usd']:.4f}")
    print(f"⏱️  總耗時：{report['timing']['total_duration'] / 60:.1f} 分鐘")
    print("=" * 80)


if __name__ == "__main__":
    # 運行主程式
    asyncio.run(main())
