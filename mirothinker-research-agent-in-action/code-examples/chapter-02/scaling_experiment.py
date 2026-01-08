"""
scaling_experiment.py

測量代理人交互縮放效益的實驗框架

來源：《深度研究代理人實戰》第 2 章
授權：MIT License

功能：
- 比較不同模型大小和交互次數配置的效能
- 自動追蹤 Token 消耗和時間成本
- 生成比較報告
"""

import os
import json
import time
import re
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import httpx

load_dotenv()


# ============================================================
# 資料結構
# ============================================================

@dataclass
class ExperimentConfig:
    """實驗配置"""
    name: str
    model: str
    max_interactions: int
    temperature: float = 0.1
    description: str = ""

    def __str__(self):
        return f"{self.name} ({self.model}, max={self.max_interactions})"


@dataclass
class TaskResult:
    """單一任務的執行結果"""
    task_id: str
    question: str
    answer: str
    interactions_used: int
    tokens_consumed: int
    time_seconds: float
    sources_cited: int
    search_queries: list[str] = field(default_factory=list)
    config_name: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "question": self.question,
            "answer": self.answer[:200] + "..." if len(self.answer) > 200 else self.answer,
            "interactions_used": self.interactions_used,
            "tokens_consumed": self.tokens_consumed,
            "time_seconds": round(self.time_seconds, 2),
            "sources_cited": self.sources_cited,
            "search_queries": self.search_queries,
            "config_name": self.config_name
        }


@dataclass
class ExperimentResult:
    """實驗總結果"""
    config: ExperimentConfig
    task_results: list[TaskResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def avg_interactions(self) -> float:
        if not self.task_results:
            return 0
        return sum(r.interactions_used for r in self.task_results) / len(self.task_results)

    @property
    def avg_time(self) -> float:
        if not self.task_results:
            return 0
        return sum(r.time_seconds for r in self.task_results) / len(self.task_results)

    @property
    def total_tokens(self) -> int:
        return sum(r.tokens_consumed for r in self.task_results)

    @property
    def avg_sources(self) -> float:
        if not self.task_results:
            return 0
        return sum(r.sources_cited for r in self.task_results) / len(self.task_results)

    @property
    def total_time(self) -> float:
        return sum(r.time_seconds for r in self.task_results)

    def to_dict(self) -> dict:
        return {
            "config": str(self.config),
            "task_count": len(self.task_results),
            "avg_interactions": round(self.avg_interactions, 2),
            "avg_time": round(self.avg_time, 2),
            "total_tokens": self.total_tokens,
            "avg_sources": round(self.avg_sources, 2),
            "total_time": round(self.total_time, 2)
        }


# ============================================================
# 搜尋工具
# ============================================================

class SearchTool:
    """搜尋工具（支援真實 API 和模擬模式）"""

    def __init__(self, use_mock: bool = False):
        self.api_key = os.getenv("SERPER_API_KEY")
        self.use_mock = use_mock or not self.api_key
        self.base_url = "https://google.serper.dev/search"

        if self.use_mock:
            print("⚠️ 搜尋工具使用模擬模式")

    def search(self, query: str, num_results: int = 3) -> str:
        if self.use_mock:
            return self._mock_search(query)

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {"q": query, "num": num_results}

        try:
            response = httpx.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", [])[:num_results]:
                results.append(
                    f"標題: {item.get('title', 'N/A')}\n"
                    f"摘要: {item.get('snippet', 'N/A')}"
                )

            return "\n---\n".join(results) if results else "未找到相關結果"

        except Exception as e:
            return f"搜尋錯誤: {str(e)}"

    def _mock_search(self, query: str) -> str:
        """模擬搜尋結果"""
        return f"""標題: 關於「{query}」的搜尋結果
摘要: 這是模擬的搜尋結果。包含與「{query}」相關的資訊。在實際使用中，這裡會顯示真實的網路搜尋結果。

---

標題: {query} - 相關資料
摘要: 更多關於此主題的詳細資訊。模擬模式下無法獲取真實數據，但可以測試代理人的基本流程。"""


# ============================================================
# 可配置的代理人
# ============================================================

class ConfigurableAgent:
    """
    可配置的代理人，用於縮放實驗

    特點：
    - 可配置最大交互次數
    - 追蹤 Token 消耗
    - 記錄搜尋查詢
    """

    def __init__(self, config: ExperimentConfig, search_tool: SearchTool):
        self.config = config
        self.client = OpenAI()
        self.search_tool = search_tool
        self.interaction_count = 0
        self.token_count = 0
        self.search_queries: list[str] = []

    def reset_counters(self):
        """重置計數器"""
        self.interaction_count = 0
        self.token_count = 0
        self.search_queries = []

    def _build_system_prompt(self) -> str:
        """構建系統提示詞"""
        return f"""你是一個研究助理代理人，使用 ReAct 模式工作。

## 交互限制
- 你最多可以進行 {self.config.max_interactions} 次搜尋
- 請高效使用搜尋次數，避免重複查詢
- 如果資訊足夠，儘早給出答案

## 可用工具

### search
搜尋網路獲取資訊
格式：Action: search[搜尋關鍵字]

## 回應格式

搜尋時：
```
Thought: [分析當前狀態，說明為何需要搜尋]
Action: search[精確的搜尋關鍵字]
```

回答時：
```
Thought: [總結已獲得的資訊]
Answer: [完整的答案]
引用來源數：[數字]
```

## 重要原則
1. 每次只執行一個搜尋
2. 搜尋關鍵字要精確，避免過於寬泛
3. 答案要基於搜尋結果
4. 如果資訊不足但已達到搜尋上限，誠實說明
5. 使用繁體中文回答
"""

    def run(self, question: str) -> tuple[str, int]:
        """
        執行代理人

        Returns:
            (答案, 引用來源數量)
        """
        self.reset_counters()

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": f"請研究並回答以下問題：\n\n{question}"}
        ]

        while self.interaction_count < self.config.max_interactions + 10:  # +10 for non-search iterations
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=1500
                )
            except Exception as e:
                return f"API 錯誤: {str(e)}", 0

            self.token_count += response.usage.total_tokens
            content = response.choices[0].message.content
            messages.append({"role": "assistant", "content": content})

            # 解析回應
            if "Answer:" in content:
                # 提取答案
                answer_match = re.search(r'Answer:\s*(.+?)(?=引用來源數|$)', content, re.DOTALL)
                answer = answer_match.group(1).strip() if answer_match else content

                # 提取引用數量
                source_match = re.search(r'引用來源數[：:]\s*(\d+)', content)
                sources = int(source_match.group(1)) if source_match else len(self.search_queries)

                return answer, sources

            elif "Action: search[" in content:
                # 檢查是否達到搜尋上限
                if self.interaction_count >= self.config.max_interactions:
                    messages.append({
                        "role": "user",
                        "content": f"已達到搜尋上限（{self.config.max_interactions} 次）。請根據現有資訊給出答案，格式：Answer: [答案]\n引用來源數：[數字]"
                    })
                    continue

                # 提取搜尋查詢
                match = re.search(r'Action: search\[(.+?)\]', content)
                if match:
                    query = match.group(1)
                    self.search_queries.append(query)
                    self.interaction_count += 1

                    # 執行搜尋
                    result = self.search_tool.search(query)
                    messages.append({
                        "role": "user",
                        "content": f"Observation:\n{result}\n\n（已使用 {self.interaction_count}/{self.config.max_interactions} 次搜尋）"
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": "無法解析搜尋格式，請使用：Action: search[關鍵字]"
                    })

            else:
                # 提示格式
                messages.append({
                    "role": "user",
                    "content": "請使用正確格式：\n- 搜尋：Action: search[關鍵字]\n- 回答：Answer: [答案]"
                })

        return "達到迭代上限", len(self.search_queries)


# ============================================================
# 實驗執行器
# ============================================================

class ScalingExperiment:
    """
    縮放實驗執行器

    用於比較不同配置下代理人的表現
    """

    def __init__(self, tasks: list[str], use_mock_search: bool = False):
        self.tasks = tasks
        self.search_tool = SearchTool(use_mock=use_mock_search)
        self.results: list[ExperimentResult] = []

    def run_config(self, config: ExperimentConfig, verbose: bool = True) -> ExperimentResult:
        """執行單一配置的實驗"""
        if verbose:
            print(f"\n{'='*60}")
            print(f"🔬 執行配置: {config.name}")
            print(f"   模型: {config.model}")
            print(f"   最大交互: {config.max_interactions}")
            print(f"{'='*60}")

        agent = ConfigurableAgent(config, self.search_tool)
        experiment_result = ExperimentResult(config=config)

        for i, task in enumerate(self.tasks, 1):
            if verbose:
                print(f"\n📝 任務 {i}/{len(self.tasks)}: {task[:50]}...")

            start_time = time.time()
            answer, sources = agent.run(task)
            elapsed = time.time() - start_time

            result = TaskResult(
                task_id=f"task_{i}",
                question=task,
                answer=answer,
                interactions_used=agent.interaction_count,
                tokens_consumed=agent.token_count,
                time_seconds=elapsed,
                sources_cited=sources,
                search_queries=agent.search_queries.copy(),
                config_name=config.name
            )

            experiment_result.task_results.append(result)

            if verbose:
                print(f"   ⏱️  耗時: {elapsed:.2f}s")
                print(f"   🔄 搜尋次數: {agent.interaction_count}")
                print(f"   📚 引用來源: {sources}")
                print(f"   💰 Token: {agent.token_count}")

        experiment_result.end_time = datetime.now()
        self.results.append(experiment_result)
        return experiment_result

    def run_all(self, configs: list[ExperimentConfig], verbose: bool = True) -> list[ExperimentResult]:
        """執行所有配置的實驗"""
        print(f"\n🚀 開始縮放實驗")
        print(f"   配置數量: {len(configs)}")
        print(f"   任務數量: {len(self.tasks)}")

        for config in configs:
            self.run_config(config, verbose)

        return self.results

    def generate_report(self) -> str:
        """生成 Markdown 格式的比較報告"""
        lines = []
        lines.append("# 縮放實驗結果報告")
        lines.append(f"\n生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 實驗概覽
        lines.append("\n## 實驗概覽")
        lines.append(f"- 測試任務數量: {len(self.tasks)}")
        lines.append(f"- 配置數量: {len(self.results)}")

        # 配置比較表
        lines.append("\n## 配置比較")
        lines.append("\n| 配置 | 模型 | 最大交互 | 平均交互 | 平均耗時 | 總 Token | 平均引用 |")
        lines.append("|------|------|----------|----------|----------|----------|----------|")

        for result in self.results:
            lines.append(
                f"| {result.config.name} | {result.config.model} | "
                f"{result.config.max_interactions} | {result.avg_interactions:.1f} | "
                f"{result.avg_time:.1f}s | {result.total_tokens:,} | {result.avg_sources:.1f} |"
            )

        # 成本效益分析
        lines.append("\n## 成本效益分析")

        # 模型價格（每 1K tokens，輸入+輸出平均）
        cost_per_1k = {
            "gpt-4o-mini": 0.0003,
            "gpt-4o": 0.0075,
            "gpt-4-turbo": 0.015,
            "gpt-3.5-turbo": 0.001,
        }

        lines.append("\n| 配置 | 總 Token | 估算成本 | 成本/任務 |")
        lines.append("|------|----------|----------|-----------|")

        for result in self.results:
            model = result.config.model
            rate = cost_per_1k.get(model, 0.001)
            total_cost = result.total_tokens / 1000 * rate
            cost_per_task = total_cost / len(self.tasks) if self.tasks else 0

            lines.append(
                f"| {result.config.name} | {result.total_tokens:,} | "
                f"${total_cost:.4f} | ${cost_per_task:.4f} |"
            )

        # 詳細結果
        lines.append("\n## 詳細結果")

        for result in self.results:
            lines.append(f"\n### {result.config.name}")
            lines.append(f"\n| 任務 | 搜尋次數 | 耗時 | Token | 引用 |")
            lines.append("|------|----------|------|-------|------|")

            for tr in result.task_results:
                lines.append(
                    f"| {tr.task_id} | {tr.interactions_used} | "
                    f"{tr.time_seconds:.1f}s | {tr.tokens_consumed:,} | {tr.sources_cited} |"
                )

        # 結論
        lines.append("\n## 結論")

        if len(self.results) >= 2:
            # 找出最有效率的配置
            sorted_results = sorted(self.results, key=lambda r: r.avg_sources / max(r.avg_time, 0.1), reverse=True)
            best = sorted_results[0]
            lines.append(f"\n- **最佳效率配置**: {best.config.name}")
            lines.append(f"  - 平均引用: {best.avg_sources:.1f} 來源/任務")
            lines.append(f"  - 平均耗時: {best.avg_time:.1f} 秒/任務")

            # 找出成本最低的配置
            sorted_by_cost = sorted(self.results, key=lambda r: r.total_tokens)
            cheapest = sorted_by_cost[0]
            lines.append(f"\n- **最低成本配置**: {cheapest.config.name}")
            lines.append(f"  - 總 Token: {cheapest.total_tokens:,}")

        return "\n".join(lines)

    def save_results(self, filepath: str):
        """儲存結果為 JSON"""
        data = {
            "tasks": self.tasks,
            "results": [
                {
                    "config": str(r.config),
                    "summary": r.to_dict(),
                    "task_results": [tr.to_dict() for tr in r.task_results]
                }
                for r in self.results
            ]
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ 結果已儲存至 {filepath}")


# ============================================================
# 預設測試任務
# ============================================================

DEFAULT_TASKS = [
    "2024 年全球電動車銷量排名前五的品牌是哪些？請提供具體數據。",
    "比較 OpenAI GPT-4o 和 Anthropic Claude 3.5 Sonnet 的主要差異",
    "台積電 2024 年第三季的營收和獲利表現如何？",
    "解釋 MiroThinker 的 Interactive Scaling 概念",
    "最近一個月內，美國聯準會做出了哪些重要決策？"
]


# ============================================================
# 主程式
# ============================================================

def main():
    """執行縮放實驗示範"""

    print("\n" + "="*60)
    print("📊 代理人縮放效益實驗")
    print("="*60)

    # 檢查 API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 錯誤：請設定 OPENAI_API_KEY 環境變數")
        return

    # 使用較少的任務進行示範
    demo_tasks = DEFAULT_TASKS[:3]

    # 實驗配置
    configs = [
        ExperimentConfig(
            name="少交互",
            model="gpt-4o-mini",
            max_interactions=3,
            description="模擬大模型少交互場景"
        ),
        ExperimentConfig(
            name="中交互",
            model="gpt-4o-mini",
            max_interactions=10,
            description="平衡的交互次數"
        ),
        ExperimentConfig(
            name="多交互",
            model="gpt-4o-mini",
            max_interactions=25,
            description="充分利用交互能力"
        ),
    ]

    # 執行實驗（使用模擬搜尋以避免 API 成本）
    use_mock = not os.getenv("SERPER_API_KEY")
    if use_mock:
        print("\n⚠️ 未設定 SERPER_API_KEY，使用模擬搜尋模式")

    experiment = ScalingExperiment(demo_tasks, use_mock_search=use_mock)
    experiment.run_all(configs)

    # 生成報告
    report = experiment.generate_report()
    print("\n" + report)

    # 儲存結果
    report_path = "scaling_experiment_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📄 報告已儲存至 {report_path}")

    # 儲存 JSON 結果
    experiment.save_results("scaling_experiment_results.json")


if __name__ == "__main__":
    main()
