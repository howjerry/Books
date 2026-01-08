"""
cognitive_research_agent.py

具備認知框架的深度研究代理人
遵循 ISP 模型（資訊搜尋過程）進行系統性研究

使用方式：
    agent = CognitiveResearchAgent()
    report = agent.research("量子計算對金融業的影響")
"""

import os
import json
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# =============================================================================
# 研究階段定義
# =============================================================================

class ResearchPhase(Enum):
    """研究階段枚舉"""
    INIT = "init"              # 初始化：接收任務
    DECOMPOSE = "decompose"    # 分解：拆分問題
    EXPLORE = "explore"        # 探索：廣泛蒐集
    FOCUS = "focus"            # 聚焦：深入驗證
    SYNTHESIZE = "synthesize"  # 綜合：整合知識
    REPORT = "report"          # 報告：產出結果


@dataclass
class PhaseConfig:
    """階段配置"""
    max_iterations: int = 5
    min_sources: int = 2
    confidence_threshold: float = 0.7
    allowed_tools: list = field(default_factory=lambda: ["search"])


# 各階段的預設配置
PHASE_CONFIGS = {
    ResearchPhase.DECOMPOSE: PhaseConfig(
        max_iterations=2,
        min_sources=0,
        confidence_threshold=0.8,
        allowed_tools=[]  # 純推理，不需工具
    ),
    ResearchPhase.EXPLORE: PhaseConfig(
        max_iterations=10,
        min_sources=3,
        confidence_threshold=0.5,
        allowed_tools=["search", "browse"]
    ),
    ResearchPhase.FOCUS: PhaseConfig(
        max_iterations=8,
        min_sources=2,
        confidence_threshold=0.7,
        allowed_tools=["search", "browse", "academic_search"]
    ),
    ResearchPhase.SYNTHESIZE: PhaseConfig(
        max_iterations=3,
        min_sources=0,
        confidence_threshold=0.8,
        allowed_tools=[]  # 純推理，不需工具
    ),
}


# =============================================================================
# 證據系統
# =============================================================================

class SourceType(Enum):
    """來源類型"""
    ACADEMIC = "academic"    # 學術論文
    OFFICIAL = "official"    # 官方機構
    INDUSTRY = "industry"    # 產業報告
    NEWS = "news"           # 新聞媒體
    SOCIAL = "social"       # 社群媒體
    UNKNOWN = "unknown"     # 未知


class EvidenceStrength(Enum):
    """證據強度"""
    STRONG = 3
    MODERATE = 2
    WEAK = 1


@dataclass
class Evidence:
    """證據資料結構"""
    claim: str                      # 聲明內容
    source_url: str                 # 來源網址
    source_type: SourceType         # 來源類型
    strength: EvidenceStrength      # 證據強度
    timestamp: str = ""             # 資料時間
    author: str = ""                # 作者

    def calculate_weight(self) -> float:
        """計算證據權重"""
        type_weights = {
            SourceType.ACADEMIC: 1.0,
            SourceType.OFFICIAL: 0.9,
            SourceType.INDUSTRY: 0.7,
            SourceType.NEWS: 0.5,
            SourceType.SOCIAL: 0.2,
            SourceType.UNKNOWN: 0.3
        }

        strength_multiplier = {
            EvidenceStrength.STRONG: 1.5,
            EvidenceStrength.MODERATE: 1.0,
            EvidenceStrength.WEAK: 0.5
        }

        base = type_weights.get(self.source_type, 0.3)
        multiplier = strength_multiplier.get(self.strength, 1.0)

        return base * multiplier


@dataclass
class Conclusion:
    """研究結論"""
    statement: str
    confidence: float
    supporting_evidence: list = field(default_factory=list)
    conflicting_evidence: list = field(default_factory=list)


# =============================================================================
# 搜尋工具
# =============================================================================

class SearchTool:
    """網路搜尋工具"""

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")

    def search(self, query: str, num_results: int = 5) -> list[dict]:
        """執行搜尋"""
        if not self.api_key:
            return self._mock_search(query)

        import requests

        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": self.api_key},
            json={"q": query, "num": num_results}
        )

        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("organic", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", "")
                })
            return results

        return self._mock_search(query)

    def _mock_search(self, query: str) -> list[dict]:
        """模擬搜尋（用於測試）"""
        return [
            {
                "title": f"搜尋結果 1：{query}",
                "snippet": f"這是關於 {query} 的模擬搜尋結果。在實際環境中，這裡會顯示真實的搜尋結果。",
                "link": "https://example.com/result1"
            },
            {
                "title": f"搜尋結果 2：{query} 詳解",
                "snippet": f"深入分析 {query} 的各個面向，提供專業見解和數據支持。",
                "link": "https://example.com/result2"
            },
            {
                "title": f"搜尋結果 3：{query} 最新發展",
                "snippet": f"追蹤 {query} 的最新趨勢和發展動態，提供前瞻性觀點。",
                "link": "https://example.com/result3"
            }
        ]


# =============================================================================
# Prompt 模板
# =============================================================================

DECOMPOSITION_PROMPT = """你是一位研究策略專家。請將以下複雜問題分解為可管理的子問題。

研究問題：{query}

請遵循以下步驟：

1. **識別核心概念**：找出問題中的 3-5 個關鍵術語

2. **分解子問題**：將問題拆分為 3-6 個具體的子問題
   - 每個子問題應該可以獨立研究
   - 子問題應該涵蓋問題的各個面向

3. **確定優先級**：標註哪些問題應該先回答

請以 JSON 格式輸出：
```json
{{
  "core_concepts": ["概念1", "概念2", ...],
  "sub_questions": [
    {{
      "id": "Q1",
      "question": "子問題描述",
      "priority": 1,
      "search_queries": ["建議的搜尋關鍵字"]
    }}
  ],
  "research_strategy": "簡述研究策略"
}}
```"""

EXPLORATION_PROMPT = """你是一位資深研究員，正在進行探索階段的研究。

研究問題：{query}
當前子問題：{sub_question}

你需要廣泛蒐集相關資訊。以下是搜尋結果：

{search_results}

請分析這些結果：

1. **關鍵發現**：提取 3-5 個重要的事實或觀點

2. **資訊缺口**：識別還需要進一步研究的方面

3. **矛盾之處**：標註任何矛盾或不一致的資訊

4. **下一步**：建議接下來的搜尋方向

請以 JSON 格式輸出：
```json
{{
  "key_findings": [
    {{
      "finding": "發現內容",
      "source": "來源",
      "confidence": 0.8
    }}
  ],
  "information_gaps": ["缺口1", "缺口2"],
  "contradictions": ["矛盾1"],
  "next_searches": ["下一個搜尋詞"]
}}
```"""

VERIFICATION_PROMPT = """你是一位事實查核專家，正在驗證研究發現。

原始聲明：{claim}

已蒐集的證據：
{evidence_list}

請進行嚴格驗證：

1. **證據評估**：評估每條證據的可信度和相關性

2. **交叉驗證**：不同來源是否支持相同結論？

3. **矛盾分析**：如有矛盾，分析可能原因

4. **置信度判定**：給出最終置信度（0-1）

請以 JSON 格式輸出：
```json
{{
  "verification_result": "confirmed" | "partially_confirmed" | "unconfirmed" | "contradicted",
  "confidence": 0.75,
  "reasoning": "驗證推理過程",
  "verified_claim": "經驗證後的聲明（可能與原始有修正）"
}}
```"""

SYNTHESIS_PROMPT = """你是一位知識綜合專家，正在整合研究成果。

研究問題：{query}

已驗證的發現：
{verified_findings}

請進行知識綜合：

1. **核心論點**：提煉 3-5 個核心結論

2. **關係梳理**：這些結論之間有什麼關聯？

3. **不確定性**：明確標註仍不確定的部分

4. **建議**：基於研究結果提出建議

請以 JSON 格式輸出：
```json
{{
  "core_conclusions": [
    {{
      "conclusion": "結論內容",
      "confidence": 0.8,
      "supporting_evidence": ["證據1", "證據2"]
    }}
  ],
  "relationships": "結論之間的關係說明",
  "uncertainties": ["不確定點1", "不確定點2"],
  "recommendations": ["建議1", "建議2"]
}}
```"""

REPORT_PROMPT = """你是一位專業報告撰寫者。請基於研究結果撰寫結構化報告。

研究問題：{query}

研究結論：
{conclusions}

請撰寫一份專業的研究報告，包含：

1. **摘要**（100-150 字）：概述主要發現

2. **研究背景**：說明問題的重要性

3. **主要發現**：詳細說明核心結論
   - 每個發現需標註置信度
   - 提供支持證據

4. **討論**：分析發現的意義和局限

5. **結論與建議**：總結並提出行動建議

6. **參考來源**：列出主要資訊來源

請直接輸出 Markdown 格式的報告。"""


# =============================================================================
# 認知研究代理人
# =============================================================================

class CognitiveResearchAgent:
    """
    具備認知框架的深度研究代理人

    實現 ISP（資訊搜尋過程）模型的六個階段：
    初始化 → 問題分解 → 探索 → 聚焦驗證 → 綜合 → 報告
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        verbose: bool = True
    ):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.verbose = verbose
        self.search_tool = SearchTool()

        # 研究狀態
        self.current_phase = ResearchPhase.INIT
        self.query = ""
        self.sub_questions = []
        self.findings = []
        self.evidence_pool = []
        self.conclusions = []
        self.interaction_count = 0

    def research(self, query: str) -> str:
        """
        執行完整研究流程

        Args:
            query: 研究問題

        Returns:
            結構化研究報告（Markdown 格式）
        """
        start_time = time.time()
        self.query = query

        self._log(f"\n{'='*60}")
        self._log(f"🔬 開始研究：{query}")
        self._log(f"{'='*60}\n")

        try:
            # 階段 1：問題分解
            self._phase_decompose()

            # 階段 2：探索
            self._phase_explore()

            # 階段 3：聚焦驗證
            self._phase_focus()

            # 階段 4：綜合
            self._phase_synthesize()

            # 階段 5：生成報告
            report = self._phase_report()

            elapsed = time.time() - start_time
            self._log(f"\n{'='*60}")
            self._log(f"✅ 研究完成")
            self._log(f"⏱️  總耗時：{elapsed:.1f} 秒")
            self._log(f"🔄 總交互次數：{self.interaction_count}")
            self._log(f"{'='*60}\n")

            return report

        except Exception as e:
            self._log(f"❌ 研究過程發生錯誤：{e}")
            raise

    def _phase_decompose(self):
        """問題分解階段"""
        self.current_phase = ResearchPhase.DECOMPOSE
        self._log_phase("問題分解", "將複雜問題拆分為可管理的子問題")

        response = self._call_llm(
            DECOMPOSITION_PROMPT.format(query=self.query)
        )

        try:
            # 嘗試解析 JSON
            result = self._extract_json(response)
            self.sub_questions = result.get("sub_questions", [])

            self._log(f"   📋 核心概念：{result.get('core_concepts', [])}")
            self._log(f"   📋 子問題數量：{len(self.sub_questions)}")

            for i, sq in enumerate(self.sub_questions, 1):
                self._log(f"      Q{i}: {sq.get('question', '')}")

        except Exception as e:
            self._log(f"   ⚠️ 解析失敗，使用原始問題：{e}")
            self.sub_questions = [{
                "id": "Q1",
                "question": self.query,
                "priority": 1,
                "search_queries": [self.query]
            }]

    def _phase_explore(self):
        """探索階段：廣泛蒐集資訊"""
        self.current_phase = ResearchPhase.EXPLORE
        self._log_phase("探索階段", "廣泛蒐集相關資訊")

        config = PHASE_CONFIGS[ResearchPhase.EXPLORE]

        for sq in self.sub_questions[:3]:  # 最多處理 3 個子問題
            question = sq.get("question", "")
            search_queries = sq.get("search_queries", [question])

            self._log(f"\n   🔍 探索子問題：{question}")

            for search_query in search_queries[:2]:  # 每個子問題最多 2 次搜尋
                # 執行搜尋
                results = self.search_tool.search(search_query)
                self.interaction_count += 1

                # 分析結果
                results_text = self._format_search_results(results)

                analysis = self._call_llm(
                    EXPLORATION_PROMPT.format(
                        query=self.query,
                        sub_question=question,
                        search_results=results_text
                    )
                )

                try:
                    result = self._extract_json(analysis)
                    findings = result.get("key_findings", [])
                    self.findings.extend(findings)

                    self._log(f"      ✅ 發現 {len(findings)} 項")

                except Exception as e:
                    self._log(f"      ⚠️ 分析失敗：{e}")

    def _phase_focus(self):
        """聚焦驗證階段"""
        self.current_phase = ResearchPhase.FOCUS
        self._log_phase("聚焦驗證", "交叉驗證關鍵發現")

        verified_findings = []

        for i, finding in enumerate(self.findings[:5]):  # 最多驗證 5 項
            claim = finding.get("finding", "") if isinstance(finding, dict) else str(finding)

            self._log(f"\n   🔎 驗證：{claim[:50]}...")

            # 搜尋驗證資料
            verify_results = self.search_tool.search(f"verify {claim[:50]}")
            self.interaction_count += 1

            evidence_text = self._format_search_results(verify_results)

            # 驗證
            verification = self._call_llm(
                VERIFICATION_PROMPT.format(
                    claim=claim,
                    evidence_list=evidence_text
                )
            )

            try:
                result = self._extract_json(verification)
                confidence = result.get("confidence", 0.5)

                if confidence >= 0.6:
                    verified_findings.append({
                        "claim": result.get("verified_claim", claim),
                        "confidence": confidence,
                        "reasoning": result.get("reasoning", "")
                    })
                    self._log(f"      ✅ 已驗證（置信度：{confidence:.0%}）")
                else:
                    self._log(f"      ⚠️ 未通過驗證（置信度：{confidence:.0%}）")

            except Exception as e:
                self._log(f"      ❌ 驗證失敗：{e}")

        self.findings = verified_findings
        self._log(f"\n   📊 驗證通過：{len(verified_findings)} 項")

    def _phase_synthesize(self):
        """綜合階段：整合研究成果"""
        self.current_phase = ResearchPhase.SYNTHESIZE
        self._log_phase("知識綜合", "整合研究成果形成結論")

        findings_text = json.dumps(self.findings, ensure_ascii=False, indent=2)

        synthesis = self._call_llm(
            SYNTHESIS_PROMPT.format(
                query=self.query,
                verified_findings=findings_text
            )
        )

        try:
            result = self._extract_json(synthesis)
            self.conclusions = result.get("core_conclusions", [])

            self._log(f"   📝 形成 {len(self.conclusions)} 個核心結論")

            for i, c in enumerate(self.conclusions, 1):
                conclusion = c.get("conclusion", "")
                confidence = c.get("confidence", 0)
                self._log(f"      {i}. {conclusion[:50]}... (置信度：{confidence:.0%})")

        except Exception as e:
            self._log(f"   ⚠️ 綜合失敗：{e}")
            self.conclusions = [{
                "conclusion": f"關於「{self.query}」的研究結論需要進一步分析",
                "confidence": 0.5,
                "supporting_evidence": [f.get("claim", "") for f in self.findings]
            }]

    def _phase_report(self) -> str:
        """報告生成階段"""
        self.current_phase = ResearchPhase.REPORT
        self._log_phase("生成報告", "撰寫結構化研究報告")

        conclusions_text = json.dumps(self.conclusions, ensure_ascii=False, indent=2)

        report = self._call_llm(
            REPORT_PROMPT.format(
                query=self.query,
                conclusions=conclusions_text
            )
        )

        # 添加元資料
        report += f"\n\n---\n\n"
        report += f"**研究統計**\n\n"
        report += f"- 研究問題：{self.query}\n"
        report += f"- 子問題數：{len(self.sub_questions)}\n"
        report += f"- 已驗證發現：{len(self.findings)}\n"
        report += f"- 核心結論：{len(self.conclusions)}\n"
        report += f"- 總交互次數：{self.interaction_count}\n"
        report += f"- 使用模型：{self.model}\n"

        return report

    def _call_llm(self, prompt: str) -> str:
        """呼叫 LLM"""
        self.interaction_count += 1

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        return response.choices[0].message.content

    def _extract_json(self, text: str) -> dict:
        """從文字中提取 JSON"""
        import re

        # 嘗試找到 JSON 區塊
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json.loads(json_match.group(1))

        # 嘗試直接解析
        try:
            return json.loads(text)
        except:
            pass

        # 返回空字典
        return {}

    def _format_search_results(self, results: list[dict]) -> str:
        """格式化搜尋結果"""
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"{i}. **{r.get('title', '')}**\n"
                f"   {r.get('snippet', '')}\n"
                f"   來源：{r.get('link', '')}"
            )
        return "\n\n".join(formatted)

    def _log(self, message: str):
        """輸出日誌"""
        if self.verbose:
            print(message)

    def _log_phase(self, phase_name: str, description: str):
        """輸出階段資訊"""
        self._log(f"\n📍 {phase_name}")
        self._log(f"   {description}")
        self._log(f"   {'─'*40}")


# =============================================================================
# 主程式
# =============================================================================

def main():
    """主程式入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="認知研究代理人 - 具備認知框架的深度研究工具"
    )
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="研究問題"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="互動模式"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="使用的模型 (預設: gpt-4o-mini)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="輸出報告到檔案"
    )

    args = parser.parse_args()

    # 檢查 API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 錯誤：請設定 OPENAI_API_KEY 環境變數")
        print("   複製 .env.example 為 .env 並填入你的 API Key")
        return

    # 建立代理人
    agent = CognitiveResearchAgent(
        model=args.model,
        verbose=True
    )

    if args.interactive:
        # 互動模式
        print("\n🔬 認知研究代理人 - 互動模式")
        print("輸入研究問題，或輸入 'quit' 退出\n")

        while True:
            query = input("📝 研究問題：").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 再見！")
                break

            if query:
                report = agent.research(query)
                print(f"\n{report}\n")

                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(report)
                    print(f"📄 報告已保存至：{args.output}")

    elif args.query:
        # 指定問題模式
        report = agent.research(args.query)
        print(f"\n{report}")

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n📄 報告已保存至：{args.output}")

    else:
        # 示範模式
        demo_query = "人工智慧對軟體工程師就業市場的影響是什麼？"
        print(f"\n🎯 示範研究問題：{demo_query}\n")

        report = agent.research(demo_query)
        print(f"\n{report}")


if __name__ == "__main__":
    main()
