#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 12 章：基準測試全解析
統一評測框架

這個模組整合多種基準測試：
1. HLE 評測
2. GAIA 評測
3. 統一結果報告
4. 視覺化儀表板

使用方式：
    from unified_evaluator import UnifiedEvaluator, EvaluationConfig
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
import json
import asyncio
import os


# =============================================================================
# 評測類型
# =============================================================================

class BenchmarkType(Enum):
    """基準測試類型"""
    HLE = "hle"
    GAIA = "gaia"
    CUSTOM = "custom"


# =============================================================================
# 配置
# =============================================================================

@dataclass
class EvaluationConfig:
    """
    評測配置
    """
    benchmarks: List[BenchmarkType]
    agent_name: str
    agent_version: str

    # 執行選項
    parallel: bool = True
    max_concurrency: int = 5
    timeout_seconds: int = 300

    # 輸出選項
    output_dir: str = "./evaluation_results"
    save_detailed: bool = True

    # 過濾選項
    difficulty_filter: Optional[List[str]] = None
    category_filter: Optional[List[str]] = None


# =============================================================================
# 評測結果
# =============================================================================

@dataclass
class EvaluationResult:
    """
    評測結果
    """
    benchmark_type: BenchmarkType
    summary: Dict[str, Any]
    detailed_results: List[Dict[str, Any]]
    started_at: datetime
    completed_at: datetime

    def to_dict(self) -> dict:
        return {
            "benchmark": self.benchmark_type.value,
            "summary": self.summary,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": (
                self.completed_at - self.started_at
            ).total_seconds(),
            "detailed_results": self.detailed_results
        }


# =============================================================================
# 統一評測器
# =============================================================================

class UnifiedEvaluator:
    """
    統一評測器

    ‹1› 整合多種基準測試
    ‹2› 提供統一的報告格式
    """

    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.results: Dict[BenchmarkType, EvaluationResult] = {}

    async def evaluate(self, agent) -> Dict[str, Any]:
        """
        執行完整評測

        Args:
            agent: 待評測的 Agent

        Returns:
            完整評測報告
        """
        overall_start = datetime.now()

        for benchmark_type in self.config.benchmarks:
            result = await self._run_benchmark(agent, benchmark_type)
            self.results[benchmark_type] = result

        overall_end = datetime.now()

        # 生成報告
        report = self._generate_report(overall_start, overall_end)

        # 保存結果
        if self.config.save_detailed:
            self._save_results(report)

        return report

    async def _run_benchmark(
        self,
        agent,
        benchmark_type: BenchmarkType
    ) -> EvaluationResult:
        """運行單個基準測試"""
        start = datetime.now()

        if benchmark_type == BenchmarkType.HLE:
            result = await self._run_hle(agent)
        elif benchmark_type == BenchmarkType.GAIA:
            result = await self._run_gaia(agent)
        else:
            result = {"summary": {}, "detailed_results": []}

        end = datetime.now()

        return EvaluationResult(
            benchmark_type=benchmark_type,
            summary=result.get("summary", {}),
            detailed_results=result.get("detailed_results", []),
            started_at=start,
            completed_at=end
        )

    async def _run_hle(self, agent) -> Dict[str, Any]:
        """運行 HLE 評測"""
        from hle_evaluator import HLETestSuite, HLEEvaluator, HLERunner

        # 創建測試套件
        suite = HLETestSuite.create_standard_suite()

        # 需要一個 LLM 客戶端來評估
        evaluator = HLEEvaluator(agent.llm_client)

        runner = HLERunner(agent, evaluator, suite)
        return await runner.run_all(self.config.max_concurrency)

    async def _run_gaia(self, agent) -> Dict[str, Any]:
        """運行 GAIA 評測"""
        from gaia_benchmark import GAIABenchmark, GAIALevel

        benchmark = GAIABenchmark.create_sample_benchmark()

        levels = None
        if self.config.difficulty_filter:
            level_map = {"easy": 1, "medium": 2, "hard": 3}
            levels = [
                GAIALevel(level_map.get(d, int(d)))
                for d in self.config.difficulty_filter
                if d in level_map or d.isdigit()
            ]

        return await benchmark.run(agent, levels)

    def _generate_report(
        self,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """生成評測報告"""
        # 收集所有分數
        scores = {}
        for benchmark_type, result in self.results.items():
            summary = result.summary
            if "overall_average" in summary:
                scores[benchmark_type.value] = summary["overall_average"] / 100
            elif "overall_accuracy" in summary:
                scores[benchmark_type.value] = summary["overall_accuracy"]
            elif "average_score" in summary:
                scores[benchmark_type.value] = summary["average_score"]

        # 計算綜合分數
        overall_score = sum(scores.values()) / len(scores) if scores else 0

        return {
            "agent": {
                "name": self.config.agent_name,
                "version": self.config.agent_version
            },
            "evaluation": {
                "started_at": start.isoformat(),
                "completed_at": end.isoformat(),
                "duration_seconds": (end - start).total_seconds(),
                "benchmarks_run": [bt.value for bt in self.config.benchmarks]
            },
            "scores": {
                "overall": overall_score,
                "by_benchmark": scores
            },
            "detailed_results": {
                bt.value: result.to_dict()
                for bt, result in self.results.items()
            }
        }

    def _save_results(self, report: Dict[str, Any]):
        """保存評測結果"""
        os.makedirs(self.config.output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config.agent_name}_{timestamp}.json"
        filepath = os.path.join(self.config.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"評測結果已保存至: {filepath}")


# =============================================================================
# 視覺化儀表板
# =============================================================================

class EvaluationDashboard:
    """
    評測儀表板

    生成 HTML 格式的視覺化報告
    """

    def __init__(self, report: Dict[str, Any]):
        self.report = report

    def generate_html(self) -> str:
        """生成 HTML 報告"""
        overall_score = self.report['scores']['overall'] * 100

        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>評測報告 - {self.report['agent']['name']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', 'Microsoft JhengHei', sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .score-big {{
            font-size: 48px;
            font-weight: bold;
            color: {'#28a745' if overall_score >= 70 else '#dc3545' if overall_score < 50 else '#ffc107'};
        }}
        .chart-container {{
            height: 300px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
        }}
        .pass {{ color: #28a745; }}
        .fail {{ color: #dc3545; }}
        .metric {{
            text-align: center;
            padding: 20px;
        }}
        .metric-value {{
            font-size: 36px;
            font-weight: bold;
        }}
        .metric-label {{
            color: #666;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 評測報告</h1>
            <p>Agent: {self.report['agent']['name']} v{self.report['agent']['version']}</p>
            <p>評測時間: {self.report['evaluation']['completed_at']}</p>
            <p>總耗時: {self.report['evaluation']['duration_seconds']:.1f} 秒</p>
        </div>

        <div class="grid">
            <div class="card">
                <h2>總體分數</h2>
                <div class="score-big">{overall_score:.1f}%</div>
            </div>

            <div class="card">
                <h2>各基準分數</h2>
                <div class="chart-container">
                    <canvas id="benchmarkChart"></canvas>
                </div>
            </div>
        </div>

        <div class="grid">
            {self._generate_metric_cards()}
        </div>

        {self._generate_detailed_tables()}
    </div>

    <script>
        {self._generate_chart_script()}
    </script>
</body>
</html>
"""

    def _generate_metric_cards(self) -> str:
        """生成指標卡片"""
        cards = []

        for benchmark, data in self.report.get('detailed_results', {}).items():
            summary = data.get('summary', {})

            total = summary.get('total_tests', summary.get('total_questions', 0))
            success = summary.get('successful', summary.get('correct_answers', 0))
            duration = data.get('duration_seconds', 0)

            cards.append(f"""
            <div class="card">
                <h3>{benchmark.upper()}</h3>
                <div class="grid" style="grid-template-columns: repeat(3, 1fr);">
                    <div class="metric">
                        <div class="metric-value">{total}</div>
                        <div class="metric-label">總測試數</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{success}</div>
                        <div class="metric-label">通過數</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{duration:.1f}s</div>
                        <div class="metric-label">耗時</div>
                    </div>
                </div>
            </div>
            """)

        return "\n".join(cards)

    def _generate_detailed_tables(self) -> str:
        """生成詳細結果表格"""
        tables = []

        for benchmark, data in self.report.get('detailed_results', {}).items():
            results = data.get('detailed_results', [])
            if not results:
                continue

            rows = ""
            for r in results[:20]:  # 限制顯示數量
                is_success = r.get('is_correct') or r.get('status') == 'success'
                status = "pass" if is_success else "fail"

                score = r.get('score', {})
                if isinstance(score, dict):
                    score_display = f"{score.get('overall', 0):.1f}"
                elif score is not None:
                    score_display = f"{score:.1f}"
                else:
                    score_display = "N/A"

                test_id = r.get('test_id', r.get('question_id', 'N/A'))
                difficulty = r.get('difficulty', r.get('level', 'N/A'))

                rows += f"""
                <tr>
                    <td>{test_id}</td>
                    <td>{difficulty}</td>
                    <td>{score_display}</td>
                    <td class="{status}">{'✓ 通過' if status == 'pass' else '✗ 失敗'}</td>
                </tr>
                """

            tables.append(f"""
            <div class="card">
                <h2>{benchmark.upper()} 詳細結果</h2>
                <table>
                    <thead>
                        <tr>
                            <th>測試 ID</th>
                            <th>難度</th>
                            <th>分數</th>
                            <th>狀態</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
            """)

        return "\n".join(tables)

    def _generate_chart_script(self) -> str:
        """生成圖表腳本"""
        benchmarks = list(self.report['scores']['by_benchmark'].keys())
        scores = [self.report['scores']['by_benchmark'][b] * 100 for b in benchmarks]

        return f"""
        new Chart(document.getElementById('benchmarkChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(benchmarks)},
                datasets: [{{
                    label: '分數 (%)',
                    data: {json.dumps(scores)},
                    backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#f5576c'],
                    borderRadius: 5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }}
            }}
        }});
        """

    def save(self, filepath: str):
        """保存 HTML 報告"""
        html = self.generate_html()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML 報告已保存至: {filepath}")


# =============================================================================
# 結果比較器
# =============================================================================

class ResultComparator:
    """
    評測結果比較器

    用於比較不同版本或不同配置的評測結果
    """

    def __init__(self):
        self.reports: List[Dict[str, Any]] = []

    def load_report(self, filepath: str):
        """載入評測報告"""
        with open(filepath, 'r', encoding='utf-8') as f:
            report = json.load(f)
            self.reports.append(report)

    def compare(self) -> Dict[str, Any]:
        """比較所有載入的報告"""
        if len(self.reports) < 2:
            return {"error": "需要至少 2 個報告進行比較"}

        comparison = {
            "reports": [],
            "overall_scores": [],
            "benchmark_scores": {},
            "improvements": {}
        }

        for report in self.reports:
            agent_info = f"{report['agent']['name']} v{report['agent']['version']}"
            overall = report['scores']['overall']

            comparison["reports"].append(agent_info)
            comparison["overall_scores"].append(overall)

            for benchmark, score in report['scores']['by_benchmark'].items():
                if benchmark not in comparison["benchmark_scores"]:
                    comparison["benchmark_scores"][benchmark] = []
                comparison["benchmark_scores"][benchmark].append(score)

        # 計算改進幅度（相對於第一個報告）
        baseline = comparison["overall_scores"][0]
        for i, score in enumerate(comparison["overall_scores"][1:], 1):
            improvement = (score - baseline) / baseline * 100 if baseline else 0
            comparison["improvements"][comparison["reports"][i]] = {
                "overall": improvement,
                "absolute": score - baseline
            }

        return comparison

    def generate_comparison_report(self) -> str:
        """生成比較報告"""
        comparison = self.compare()

        if "error" in comparison:
            return comparison["error"]

        lines = [
            "=" * 60,
            "評測結果比較報告",
            "=" * 60,
            "",
            "總體分數比較：",
        ]

        for i, (report, score) in enumerate(zip(
            comparison["reports"],
            comparison["overall_scores"]
        )):
            marker = "(基準)" if i == 0 else ""
            lines.append(f"  {report}: {score*100:.1f}% {marker}")

        lines.append("")
        lines.append("各基準分數比較：")

        for benchmark, scores in comparison["benchmark_scores"].items():
            lines.append(f"\n  {benchmark.upper()}:")
            for i, (report, score) in enumerate(zip(
                comparison["reports"],
                scores
            )):
                lines.append(f"    {report}: {score*100:.1f}%")

        if comparison["improvements"]:
            lines.append("")
            lines.append("改進幅度（相對於基準）：")
            for report, data in comparison["improvements"].items():
                sign = "+" if data["overall"] >= 0 else ""
                lines.append(f"  {report}: {sign}{data['overall']:.1f}%")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


# =============================================================================
# 示範
# =============================================================================

def demo():
    """示範統一評測框架"""
    print("=" * 60)
    print("  統一評測框架示範")
    print("=" * 60)

    # 創建配置
    config = EvaluationConfig(
        benchmarks=[BenchmarkType.HLE, BenchmarkType.GAIA],
        agent_name="MiroThinker",
        agent_version="1.0.0",
        parallel=True,
        max_concurrency=5,
        output_dir="./evaluation_results"
    )

    print(f"\n評測配置：")
    print(f"  Agent: {config.agent_name} v{config.agent_version}")
    print(f"  基準測試: {[b.value for b in config.benchmarks]}")
    print(f"  並行數: {config.max_concurrency}")
    print(f"  輸出目錄: {config.output_dir}")

    # 模擬報告
    sample_report = {
        "agent": {
            "name": "MiroThinker",
            "version": "1.0.0"
        },
        "evaluation": {
            "started_at": "2024-01-15T10:00:00",
            "completed_at": "2024-01-15T10:15:00",
            "duration_seconds": 900,
            "benchmarks_run": ["hle", "gaia"]
        },
        "scores": {
            "overall": 0.75,
            "by_benchmark": {
                "hle": 0.72,
                "gaia": 0.78
            }
        },
        "detailed_results": {
            "hle": {
                "summary": {
                    "total_tests": 10,
                    "successful": 8
                },
                "detailed_results": [
                    {"test_id": "FACT-001", "difficulty": "easy", "score": {"overall": 85}, "status": "success"},
                    {"test_id": "FACT-002", "difficulty": "easy", "score": {"overall": 78}, "status": "success"},
                ],
                "duration_seconds": 450
            },
            "gaia": {
                "summary": {
                    "total_questions": 7,
                    "correct_answers": 5
                },
                "detailed_results": [
                    {"question_id": "L1-001", "level": 1, "is_correct": True, "status": "success"},
                    {"question_id": "L2-001", "level": 2, "is_correct": True, "status": "success"},
                ],
                "duration_seconds": 450
            }
        }
    }

    # 生成儀表板
    print("\n" + "-" * 40)
    print("生成評測儀表板...")

    dashboard = EvaluationDashboard(sample_report)

    # 預覽 HTML 片段
    html = dashboard.generate_html()
    print(f"\n生成的 HTML 長度: {len(html)} 字元")
    print("\nHTML 預覽（前 500 字元）：")
    print(html[:500] + "...")


if __name__ == "__main__":
    demo()
