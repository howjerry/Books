#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 9 章：建構你的第一個研究代理人
會話管理

這個模組實現了研究會話管理：
1. 多輪對話式研究
2. 會話匯出
3. 歷史追蹤

使用方式：
    python session.py --demo
"""

import asyncio
import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# 導入研究代理人
from research_agent import DeepResearchAgent, ResearchReport

load_dotenv()


# =============================================================================
# 會話管理
# =============================================================================

@dataclass
class ResearchSession:
    """
    研究會話

    ‹1› 管理多輪研究
    ‹2› 追蹤研究歷史
    ‹3› 提供會話匯出
    """
    agent: DeepResearchAgent
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    reports: List[ResearchReport] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    async def ask(self, question: str) -> ResearchReport:
        """
        提問

        ‹1› 判斷是否為追問
        ‹2› 執行研究
        ‹3› 保存報告
        """
        if self.reports:
            report = await self.agent.follow_up(question)
        else:
            report = await self.agent.research(question)

        self.reports.append(report)
        return report

    def get_context(self, max_reports: int = 3) -> str:
        """
        獲取累積的研究上下文

        用於追問時提供背景資訊
        """
        context_parts = []
        for report in self.reports[-max_reports:]:
            context_parts.append(f"Q: {report.query.question}")
            context_parts.append(f"A: {report.summary}")
        return "\n\n".join(context_parts)

    def export_session(self, format: str = "markdown") -> str:
        """
        匯出會話

        支援格式：markdown, json
        """
        if format == "json":
            return self._export_json()
        return self._export_markdown()

    def _export_markdown(self) -> str:
        """匯出為 Markdown 格式"""
        lines = [
            f"# 研究會話 {self.session_id}",
            f"",
            f"**建立時間**: {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"**研究問題數**: {len(self.reports)}",
            f"",
            "---",
            ""
        ]

        for i, report in enumerate(self.reports, 1):
            lines.append(f"## 問題 {i}")
            lines.append(f"")
            lines.append(report.to_markdown())
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _export_json(self) -> str:
        """匯出為 JSON 格式"""
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "reports_count": len(self.reports),
            "reports": [report.to_dict() for report in self.reports]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def get_statistics(self) -> Dict[str, Any]:
        """獲取會話統計"""
        if not self.reports:
            return {
                "total_questions": 0,
                "total_sources": 0,
                "avg_confidence": 0
            }

        return {
            "total_questions": len(self.reports),
            "total_sources": sum(len(r.sources) for r in self.reports),
            "avg_confidence": sum(r.confidence_score for r in self.reports) / len(self.reports),
            "total_findings": sum(r.metadata.get("findings_count", 0) for r in self.reports),
            "total_tool_calls": sum(r.metadata.get("tool_calls", 0) for r in self.reports)
        }


# =============================================================================
# 會話管理器
# =============================================================================

class SessionManager:
    """
    會話管理器

    ‹1› 管理多個會話
    ‹2› 會話持久化
    ‹3› 會話恢復
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self._sessions: Dict[str, ResearchSession] = {}
        self._active_session: Optional[str] = None

    def create_session(self, agent: Optional[DeepResearchAgent] = None) -> ResearchSession:
        """創建新會話"""
        agent = agent or DeepResearchAgent()
        session = ResearchSession(agent=agent)

        self._sessions[session.session_id] = session
        self._active_session = session.session_id

        return session

    def get_session(self, session_id: str) -> Optional[ResearchSession]:
        """獲取會話"""
        return self._sessions.get(session_id)

    def get_active_session(self) -> Optional[ResearchSession]:
        """獲取當前活躍會話"""
        if self._active_session:
            return self._sessions.get(self._active_session)
        return None

    def set_active_session(self, session_id: str) -> bool:
        """設置活躍會話"""
        if session_id in self._sessions:
            self._active_session = session_id
            return True
        return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有會話"""
        return [
            {
                "session_id": sid,
                "created_at": session.created_at.isoformat(),
                "questions_count": len(session.reports),
                "is_active": sid == self._active_session
            }
            for sid, session in self._sessions.items()
        ]

    def delete_session(self, session_id: str) -> bool:
        """刪除會話"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._active_session == session_id:
                self._active_session = None
            return True
        return False

    def save_sessions(self) -> bool:
        """保存所有會話（持久化）"""
        if not self.storage_path:
            return False

        try:
            data = {
                "active_session": self._active_session,
                "sessions": {
                    sid: session.export_session("json")
                    for sid, session in self._sessions.items()
                }
            }

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"保存失敗: {e}")
            return False


# =============================================================================
# 互動式研究
# =============================================================================

class InteractiveResearch:
    """
    互動式研究介面

    提供命令列互動體驗
    """

    def __init__(self):
        self.manager = SessionManager()
        self.session: Optional[ResearchSession] = None

    async def start(self):
        """啟動互動式研究"""
        print("=" * 60)
        print("🔬 互動式深度研究代理人")
        print("=" * 60)
        print("\n指令:")
        print("  /new       - 創建新會話")
        print("  /history   - 查看研究歷史")
        print("  /export    - 匯出會話")
        print("  /stats     - 查看統計")
        print("  /quit      - 退出")
        print("\n輸入問題開始研究...\n")

        self.session = self.manager.create_session()

        while True:
            try:
                user_input = input("研究問題> ").strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                else:
                    await self._do_research(user_input)

            except KeyboardInterrupt:
                print("\n\n再見！")
                break
            except EOFError:
                break

    async def _handle_command(self, command: str):
        """處理指令"""
        cmd = command.lower()

        if cmd == "/new":
            self.session = self.manager.create_session()
            print("✓ 已創建新會話")

        elif cmd == "/history":
            if self.session and self.session.reports:
                print("\n研究歷史:")
                for i, report in enumerate(self.session.reports, 1):
                    print(f"  {i}. {report.query.question}")
            else:
                print("尚無研究歷史")

        elif cmd == "/export":
            if self.session:
                export = self.session.export_session()
                filename = f"research_{self.session.session_id}.md"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(export)
                print(f"✓ 已匯出到 {filename}")
            else:
                print("無活躍會話")

        elif cmd == "/stats":
            if self.session:
                stats = self.session.get_statistics()
                print("\n會話統計:")
                for key, value in stats.items():
                    if isinstance(value, float):
                        print(f"  {key}: {value:.2f}")
                    else:
                        print(f"  {key}: {value}")
            else:
                print("無活躍會話")

        elif cmd == "/quit":
            raise KeyboardInterrupt

        else:
            print(f"未知指令: {command}")

    async def _do_research(self, question: str):
        """執行研究"""
        if not self.session:
            self.session = self.manager.create_session()

        report = await self.session.ask(question)

        print("\n" + "=" * 40)
        print("📄 研究結果")
        print("=" * 40)
        print(f"\n摘要: {report.summary}")
        print(f"\n關鍵發現:")
        for i, finding in enumerate(report.key_findings, 1):
            print(f"  {i}. {finding}")
        print(f"\n信心分數: {report.confidence_score:.0%}")
        print()


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範會話管理功能"""
    print("=" * 60)
    print("📚 會話管理示範")
    print("=" * 60)

    # 創建代理人和會話
    agent = DeepResearchAgent()
    session = ResearchSession(agent=agent)

    # 執行多輪研究
    questions = [
        "什麼是深度學習？",
        "深度學習有哪些主要架構？",
        "Transformer 架構的優勢是什麼？"
    ]

    print("\n執行多輪研究...")

    for q in questions:
        print(f"\n{'='*40}")
        print(f"問題: {q}")
        report = await session.ask(q)
        print(f"摘要: {report.summary[:200]}...")

    # 顯示統計
    print("\n" + "-" * 40)
    print("📊 會話統計")
    print("-" * 40)

    stats = session.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    # 匯出會話
    print("\n" + "-" * 40)
    print("📤 會話匯出（前 500 字符）")
    print("-" * 40)

    export = session.export_session()
    print(export[:500] + "...")


async def demo_interactive():
    """互動式示範"""
    research = InteractiveResearch()
    await research.start()


def main():
    parser = argparse.ArgumentParser(description="會話管理")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("--interactive", action="store_true", help="互動模式")

    args = parser.parse_args()

    if args.interactive:
        asyncio.run(demo_interactive())
    else:
        asyncio.run(demo())


if __name__ == "__main__":
    main()
