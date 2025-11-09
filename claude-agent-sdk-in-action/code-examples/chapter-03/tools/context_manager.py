import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class ContextManager:
    """情境管理器 - 管理多使用者的對話歷史"""

    def __init__(self, context_dir: str = "./contexts"):
        self.context_dir = Path(context_dir)
        self.context_dir.mkdir(exist_ok=True)

    def save_context(self, user_id: str, messages: List[Dict]) -> None:
        """儲存對話情境"""
        context_file = self.context_dir / f"{user_id}.json"

        context = {
            "user_id": user_id,
            "last_updated": datetime.now().isoformat(),
            "messages": messages
        }

        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

    def load_context(self, user_id: str) -> List[Dict]:
        """載入對話情境"""
        context_file = self.context_dir / f"{user_id}.json"

        if not context_file.exists():
            return []

        with open(context_file, 'r', encoding='utf-8') as f:
            context = json.load(f)
            return context.get("messages", [])

    def clear_context(self, user_id: str) -> None:
        """清除對話情境"""
        context_file = self.context_dir / f"{user_id}.json"
        if context_file.exists():
            context_file.unlink()

    def list_users(self) -> List[str]:
        """列出所有使用者"""
        return [f.stem for f in self.context_dir.glob("*.json")]
