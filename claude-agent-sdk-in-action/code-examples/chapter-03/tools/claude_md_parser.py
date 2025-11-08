from pathlib import Path
from typing import Dict, List, Optional
import re


class ClaudeMDParser:
    """CLAUDE.md 解析器"""

    def __init__(self, claude_md_path: str = "./CLAUDE.md"):
        self.path = Path(claude_md_path)
        self.content = self._load_content()
        self.sections = self._parse_sections()

    def _load_content(self) -> str:
        if not self.path.exists():
            raise FileNotFoundError(f"CLAUDE.md 不存在: {self.path}")
        with open(self.path, 'r', encoding='utf-8') as f:
            return f.read()

    def _parse_sections(self) -> Dict[str, str]:
        sections = {}
        current_section = None
        current_content = []

        for line in self.content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line[3:].strip()
                current_section = re.sub(r'[^\w\s\-\(\)]', '', current_section).strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def get_section(self, section_name: str) -> Optional[str]:
        for key, value in self.sections.items():
            if section_name.lower() in key.lower():
                return value
        return None

    def get_project_overview(self) -> Dict:
        overview = self.get_section("專案概覽") or self.get_section("Project Overview")
        if not overview:
            return {}

        info = {}
        for line in overview.split('\n'):
            if line.startswith('- **'):
                match = re.match(r'- \*\*(.+?)\*\*:\s*(.+)', line)
                if match:
                    key, value = match.groups()
                    info[key] = value
        return info

    def search(self, query: str) -> List[Dict]:
        results = []
        query_lower = query.lower()

        for section_name, content in self.sections.items():
            if query_lower in content.lower():
                paragraphs = content.split('\n\n')
                for para in paragraphs:
                    if query_lower in para.lower():
                        results.append({
                            "section": section_name,
                            "content": para.strip(),
                            "relevance": para.lower().count(query_lower)
                        })

        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results

    def get_tool_definition(self) -> Dict:
        return {
            "name": "query_knowledge_base",
            "description": """查詢專案知識庫 (CLAUDE.md)。

可查詢的資訊：
- 專案概覽（技術棧、團隊規模）
- 架構決策記錄 (ADRs)
- 重要提醒（地雷、最佳實踐）
- 專案結構
- 開發環境設定
- 常見問題 (FAQ)

使用範例：
- query_knowledge_base("專案使用什麼資料庫？")
- query_knowledge_base("為什麼選擇 FastAPI？")
""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查詢問題或關鍵字"
                    }
                },
                "required": ["query"]
            }
        }
