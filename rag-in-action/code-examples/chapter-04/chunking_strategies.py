"""
chapter-04/chunking_strategies.py

5 種 Chunking 策略實作

本模組實作五種常見的文件切割策略：
1. 固定大小切割 (Fixed-Size Chunking)
2. 遞迴分割 (Recursive Splitting)
3. 語義切割 (Semantic Chunking)
4. 標題階層切割 (Heading-Based Chunking)
5. 程式碼解析切割 (Code-Aware Chunking)

使用方式：
    from chunking_strategies import ChunkingFactory, ChunkingStrategy
    chunker = ChunkingFactory.create(ChunkingStrategy.SEMANTIC)
    chunks = chunker.chunk(document)

依賴安裝：
    pip install sentence-transformers numpy scikit-learn tiktoken rich
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import re
import ast

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from rich.console import Console
from rich.table import Table

console = Console()


class ChunkingStrategy(Enum):
    """Chunking 策略類型"""
    FIXED_SIZE = "fixed_size"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    HEADING_BASED = "heading_based"
    CODE_AWARE = "code_aware"


@dataclass
class Chunk:
    """文件切片資料結構"""
    text: str
    index: int
    metadata: Dict = field(default_factory=dict)
    start_char: int = 0
    end_char: int = 0

    @property
    def length(self) -> int:
        return len(self.text)

    @property
    def word_count(self) -> int:
        return len(self.text.split())


class BaseChunker(ABC):
    """
    Chunker 基礎類別

    定義所有 Chunking 策略的共同介面
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        初始化 Chunker

        Args:
            chunk_size: 目標切片大小（字元數）
            chunk_overlap: 切片重疊區域大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @abstractmethod
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """
        將文字切割成多個 Chunk

        Args:
            text: 要切割的文字
            metadata: 附加的元資料

        Returns:
            Chunk 列表
        """
        pass

    def _create_chunk(
        self,
        text: str,
        index: int,
        start_char: int,
        end_char: int,
        metadata: Optional[Dict] = None
    ) -> Chunk:
        """建立 Chunk 物件"""
        return Chunk(
            text=text.strip(),
            index=index,
            metadata=metadata or {},
            start_char=start_char,
            end_char=end_char
        )


class FixedSizeChunker(BaseChunker):
    """
    策略一：固定大小切割

    最簡單的切割方式，按固定字元數分割。
    優點：實作簡單、結果可預測
    缺點：可能在句子中間切斷、不考慮語義邊界
    """

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """
        固定大小切割

        以 chunk_size 為單位切割文字，
        相鄰 chunk 有 chunk_overlap 的重疊區域
        """
        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size

            # 確保不超出文字範圍
            if end > len(text):
                end = len(text)

            chunk_text = text[start:end]

            # 只有非空白的 chunk 才加入
            if chunk_text.strip():
                chunks.append(self._create_chunk(
                    text=chunk_text,
                    index=index,
                    start_char=start,
                    end_char=end,
                    metadata=metadata
                ))
                index += 1

            # 移動到下一個起始點（考慮重疊）
            start = end - self.chunk_overlap

            # 避免無限迴圈
            if start >= len(text) - 1:
                break

        return chunks


class RecursiveChunker(BaseChunker):
    """
    策略二：遞迴分割

    使用多層級分隔符號遞迴切割。
    優先使用段落分隔，若段落仍太大，再用句子分隔，以此類推。

    分隔符號層級：
    1. 段落 (\\n\\n)
    2. 換行 (\\n)
    3. 句號 (。.!?)
    4. 逗號 (，,)
    5. 空白
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.separators = separators or [
            "\n\n",   # 段落
            "\n",     # 換行
            "。",     # 中文句號
            ".",      # 英文句號
            "！",     # 中文驚嘆號
            "!",      # 英文驚嘆號
            "？",     # 中文問號
            "?",      # 英文問號
            "；",     # 中文分號
            ";",      # 英文分號
            "，",     # 中文逗號
            ",",      # 英文逗號
            " ",      # 空白
            ""        # 最後手段：字元切割
        ]

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """遞迴分割文字"""
        raw_chunks = self._recursive_split(text, self.separators)

        # 合併過小的 chunk，分割過大的 chunk
        merged_chunks = self._merge_small_chunks(raw_chunks)

        # 建立 Chunk 物件
        chunks = []
        current_pos = 0

        for i, chunk_text in enumerate(merged_chunks):
            start = text.find(chunk_text, current_pos)
            if start == -1:
                start = current_pos
            end = start + len(chunk_text)

            chunks.append(self._create_chunk(
                text=chunk_text,
                index=i,
                start_char=start,
                end_char=end,
                metadata=metadata
            ))

            current_pos = start + 1

        return chunks

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        """遞迴分割核心邏輯"""
        if not text:
            return []

        if not separators:
            # 最後手段：字元切割
            return [text[i:i+self.chunk_size]
                    for i in range(0, len(text), self.chunk_size)]

        separator = separators[0]
        remaining_separators = separators[1:]

        if separator == "":
            # 空字串分隔符 = 字元切割
            splits = list(text)
        else:
            splits = text.split(separator)

        result = []
        for split in splits:
            split = split.strip()
            if not split:
                continue

            if len(split) <= self.chunk_size:
                result.append(split)
            else:
                # 需要進一步分割
                result.extend(
                    self._recursive_split(split, remaining_separators)
                )

        return result

    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """合併過小的 chunk"""
        if not chunks:
            return []

        merged = []
        current = chunks[0]

        for chunk in chunks[1:]:
            combined = current + " " + chunk

            if len(combined) <= self.chunk_size:
                current = combined
            else:
                if current.strip():
                    merged.append(current.strip())
                current = chunk

        if current.strip():
            merged.append(current.strip())

        return merged


class SemanticChunker(BaseChunker):
    """
    策略三：語義切割

    使用 Embedding 模型判斷語義邊界。
    當相鄰句子的語義相似度低於閾值時，在該處切割。

    這是最智慧的切割方式，能保持語義完整性。
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
        similarity_threshold: float = 0.5,
        min_chunk_size: int = 100
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size

        console.print(f"載入 Embedding 模型: {embedding_model}...")
        self.model = SentenceTransformer(embedding_model)

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """語義切割文字"""
        # 1. 先用句子分割
        sentences = self._split_sentences(text)

        if len(sentences) <= 1:
            return [self._create_chunk(text, 0, 0, len(text), metadata)]

        # 2. 計算句子 Embedding
        embeddings = self.model.encode(sentences)                        # ‹1›

        # 3. 計算相鄰句子的相似度
        similarities = self._compute_adjacent_similarity(embeddings)     # ‹2›

        # 4. 找出語義邊界（相似度低於閾值的位置）
        breakpoints = self._find_breakpoints(similarities)               # ‹3›

        # 5. 根據邊界切割
        chunks = self._split_by_breakpoints(
            sentences, breakpoints, text, metadata
        )

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """將文字分割成句子"""
        # 使用正則表達式匹配句子結尾
        pattern = r'[。！？.!?]+'
        sentences = re.split(pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def _compute_adjacent_similarity(
        self,
        embeddings: np.ndarray
    ) -> List[float]:
        """計算相鄰句子的餘弦相似度"""
        similarities = []

        for i in range(len(embeddings) - 1):
            sim = cosine_similarity(
                embeddings[i].reshape(1, -1),
                embeddings[i + 1].reshape(1, -1)
            )[0][0]
            similarities.append(sim)

        return similarities

    def _find_breakpoints(self, similarities: List[float]) -> List[int]:
        """找出語義邊界點"""
        breakpoints = []

        for i, sim in enumerate(similarities):
            if sim < self.similarity_threshold:
                breakpoints.append(i + 1)  # 在句子 i 之後切割

        return breakpoints

    def _split_by_breakpoints(
        self,
        sentences: List[str],
        breakpoints: List[int],
        original_text: str,
        metadata: Optional[Dict]
    ) -> List[Chunk]:
        """根據邊界點切割文字"""
        chunks = []
        start_idx = 0

        # 加入最後一個邊界點（文件結尾）
        all_breakpoints = breakpoints + [len(sentences)]

        for i, end_idx in enumerate(all_breakpoints):
            chunk_sentences = sentences[start_idx:end_idx]
            chunk_text = "。".join(chunk_sentences)

            if len(chunk_text) < self.min_chunk_size and chunks:
                # 太小的 chunk 合併到前一個
                prev_chunk = chunks[-1]
                new_text = prev_chunk.text + "。" + chunk_text
                chunks[-1] = self._create_chunk(
                    text=new_text,
                    index=prev_chunk.index,
                    start_char=prev_chunk.start_char,
                    end_char=prev_chunk.end_char + len(chunk_text) + 1,
                    metadata=metadata
                )
            elif chunk_text.strip():
                # 計算在原文中的位置
                try:
                    start_char = original_text.find(chunk_sentences[0])
                    end_char = start_char + len(chunk_text)
                except:
                    start_char, end_char = 0, len(chunk_text)

                chunks.append(self._create_chunk(
                    text=chunk_text,
                    index=len(chunks),
                    start_char=start_char,
                    end_char=end_char,
                    metadata=metadata
                ))

            start_idx = end_idx

        return chunks


class HeadingBasedChunker(BaseChunker):
    """
    策略四：標題階層切割

    根據 Markdown 標題結構切割文件。
    保持標題與其內容在同一個 chunk 中。

    適用於結構化文件（如技術文件、FAQ）。
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        heading_levels: List[int] = None
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.heading_levels = heading_levels or [1, 2, 3]

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """根據標題切割文字"""
        # 1. 解析標題結構
        sections = self._parse_headings(text)

        # 2. 建立 chunk
        chunks = []
        for i, section in enumerate(sections):
            section_text = section["text"]

            # 如果 section 太大，進行子切割
            if len(section_text) > self.chunk_size:
                sub_chunks = self._split_large_section(section_text)
                for j, sub_text in enumerate(sub_chunks):
                    chunk_metadata = {
                        **(metadata or {}),
                        "heading": section.get("heading", ""),
                        "heading_level": section.get("level", 0),
                        "sub_chunk": j
                    }
                    chunks.append(self._create_chunk(
                        text=sub_text,
                        index=len(chunks),
                        start_char=section["start"],
                        end_char=section["end"],
                        metadata=chunk_metadata
                    ))
            else:
                chunk_metadata = {
                    **(metadata or {}),
                    "heading": section.get("heading", ""),
                    "heading_level": section.get("level", 0)
                }
                chunks.append(self._create_chunk(
                    text=section_text,
                    index=len(chunks),
                    start_char=section["start"],
                    end_char=section["end"],
                    metadata=chunk_metadata
                ))

        return chunks

    def _parse_headings(self, text: str) -> List[Dict]:
        """解析 Markdown 標題"""
        # 匹配 Markdown 標題
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        lines = text.split('\n')

        sections = []
        current_section = {
            "heading": "",
            "level": 0,
            "text": "",
            "start": 0,
            "end": 0
        }

        current_pos = 0

        for line in lines:
            match = re.match(heading_pattern, line)

            if match:
                level = len(match.group(1))

                # 如果這個標題層級在我們關注的範圍內
                if level in self.heading_levels:
                    # 儲存前一個 section
                    if current_section["text"].strip():
                        current_section["end"] = current_pos
                        sections.append(current_section)

                    # 開始新的 section
                    current_section = {
                        "heading": match.group(2),
                        "level": level,
                        "text": line + "\n",
                        "start": current_pos,
                        "end": 0
                    }
                else:
                    current_section["text"] += line + "\n"
            else:
                current_section["text"] += line + "\n"

            current_pos += len(line) + 1

        # 儲存最後一個 section
        if current_section["text"].strip():
            current_section["end"] = current_pos
            sections.append(current_section)

        return sections

    def _split_large_section(self, text: str) -> List[str]:
        """將過大的 section 進一步切割"""
        # 使用遞迴切割器處理大段落
        recursive_chunker = RecursiveChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        chunks = recursive_chunker.chunk(text)
        return [chunk.text for chunk in chunks]


class CodeAwareChunker(BaseChunker):
    """
    策略五：程式碼解析切割

    專門處理程式碼文件的切割器。
    使用 AST（抽象語法樹）解析程式碼結構，
    確保函數、類別等邏輯單元不被切斷。

    支援語言：Python（可擴展到其他語言）
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        include_docstrings: bool = True
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.include_docstrings = include_docstrings

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """解析程式碼並切割"""
        try:
            # 嘗試 Python AST 解析
            tree = ast.parse(text)
            return self._chunk_python(text, tree, metadata)
        except SyntaxError:
            # 如果不是有效的 Python，改用一般切割
            console.print("[yellow]無法解析為 Python，改用遞迴切割[/yellow]")
            fallback_chunker = RecursiveChunker(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            return fallback_chunker.chunk(text, metadata)

    def _chunk_python(
        self,
        text: str,
        tree: ast.AST,
        metadata: Optional[Dict]
    ) -> List[Chunk]:
        """切割 Python 程式碼"""
        chunks = []
        lines = text.split('\n')

        # 收集所有頂層定義
        definitions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # 取得定義的範圍
                start_line = node.lineno - 1
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1

                # 取得完整程式碼
                code_lines = lines[start_line:end_line]
                code_text = '\n'.join(code_lines)

                definitions.append({
                    "type": type(node).__name__,
                    "name": node.name,
                    "start_line": start_line,
                    "end_line": end_line,
                    "text": code_text,
                    "docstring": ast.get_docstring(node) if self.include_docstrings else None
                })

        # 如果沒有定義，使用一般切割
        if not definitions:
            fallback_chunker = RecursiveChunker(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            return fallback_chunker.chunk(text, metadata)

        # 排序並合併
        definitions.sort(key=lambda x: x["start_line"])

        for i, defn in enumerate(definitions):
            chunk_metadata = {
                **(metadata or {}),
                "code_type": defn["type"],
                "code_name": defn["name"],
                "has_docstring": defn["docstring"] is not None
            }

            # 計算字元位置
            start_char = sum(len(lines[j]) + 1 for j in range(defn["start_line"]))
            end_char = start_char + len(defn["text"])

            chunks.append(self._create_chunk(
                text=defn["text"],
                index=i,
                start_char=start_char,
                end_char=end_char,
                metadata=chunk_metadata
            ))

        return chunks


class ChunkingFactory:
    """
    Chunking 策略工廠

    提供統一的介面來建立不同類型的 Chunker

    Example:
        >>> chunker = ChunkingFactory.create(ChunkingStrategy.SEMANTIC)
        >>> chunks = chunker.chunk("文件內容...")
    """

    @staticmethod
    def create(
        strategy: ChunkingStrategy,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        **kwargs
    ) -> BaseChunker:
        """
        建立指定策略的 Chunker

        Args:
            strategy: Chunking 策略類型
            chunk_size: 目標切片大小
            chunk_overlap: 切片重疊區域大小
            **kwargs: 策略特定的參數

        Returns:
            對應策略的 Chunker 實例
        """
        chunkers = {
            ChunkingStrategy.FIXED_SIZE: FixedSizeChunker,
            ChunkingStrategy.RECURSIVE: RecursiveChunker,
            ChunkingStrategy.SEMANTIC: SemanticChunker,
            ChunkingStrategy.HEADING_BASED: HeadingBasedChunker,
            ChunkingStrategy.CODE_AWARE: CodeAwareChunker,
        }

        chunker_class = chunkers.get(strategy)
        if not chunker_class:
            raise ValueError(f"不支援的策略: {strategy}")

        return chunker_class(chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs)

    @staticmethod
    def list_strategies() -> List[Dict]:
        """列出所有可用的策略"""
        return [
            {
                "strategy": ChunkingStrategy.FIXED_SIZE,
                "name": "固定大小切割",
                "description": "按固定字元數分割，簡單但可能切斷句子",
                "use_case": "結構化資料、日誌檔案"
            },
            {
                "strategy": ChunkingStrategy.RECURSIVE,
                "name": "遞迴分割",
                "description": "使用多層級分隔符號，保持段落完整性",
                "use_case": "一般文字文件、網頁內容"
            },
            {
                "strategy": ChunkingStrategy.SEMANTIC,
                "name": "語義切割",
                "description": "使用 Embedding 判斷語義邊界",
                "use_case": "需要高語義完整性的場景"
            },
            {
                "strategy": ChunkingStrategy.HEADING_BASED,
                "name": "標題階層切割",
                "description": "根據 Markdown 標題結構切割",
                "use_case": "技術文件、FAQ、Wiki"
            },
            {
                "strategy": ChunkingStrategy.CODE_AWARE,
                "name": "程式碼解析切割",
                "description": "使用 AST 解析，保持程式碼結構完整",
                "use_case": "程式碼庫、API 文件"
            },
        ]


def display_chunks(chunks: List[Chunk], strategy_name: str) -> None:
    """美化顯示 chunk 結果"""
    console.print(f"\n[bold blue]━━━ {strategy_name} ━━━[/bold blue]")
    console.print(f"共產生 [green]{len(chunks)}[/green] 個 chunk\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", width=4)
    table.add_column("長度", width=6)
    table.add_column("內容預覽", width=60)
    table.add_column("元資料", width=20)

    for chunk in chunks[:5]:  # 只顯示前 5 個
        preview = chunk.text[:50].replace('\n', '↵') + "..."
        meta_str = ", ".join(f"{k}={v}" for k, v in list(chunk.metadata.items())[:2])
        table.add_row(
            str(chunk.index),
            str(chunk.length),
            preview,
            meta_str or "-"
        )

    console.print(table)

    if len(chunks) > 5:
        console.print(f"[dim]... 還有 {len(chunks) - 5} 個 chunk 未顯示[/dim]")


def main():
    """演示各種 Chunking 策略"""
    console.print("\n[bold]═══ Chunking 策略演示 ═══[/bold]\n")

    # 測試文件
    sample_text = """# 如何使用 AskBot API

## 概述

AskBot 是一個企業級的 AI 問答系統。它結合了語義搜尋和大型語言模型，能夠準確回答使用者的問題。

## 快速開始

### 安裝

使用 pip 安裝 AskBot SDK：

```bash
pip install askbot-sdk
```

### 基本用法

以下是一個簡單的範例，展示如何使用 AskBot API：

```python
from askbot import AskBot

bot = AskBot(api_key="your_api_key")
response = bot.ask("如何重設密碼？")
print(response.answer)
```

## API 參考

### ask() 方法

`ask(query: str, top_k: int = 3) -> Response`

發送問題到 AskBot 並獲取回答。

參數：
- query: 使用者的問題
- top_k: 檢索的文件數量（預設為 3）

返回：
- Response 物件，包含 answer 和 sources 屬性

### 錯誤處理

當 API 金鑰無效時，會拋出 AuthenticationError。建議使用 try-except 處理：

```python
try:
    response = bot.ask("問題")
except AuthenticationError:
    print("API 金鑰無效")
```

## 常見問題

### Q: 支援哪些語言？

A: AskBot 支援中文和英文，未來會加入更多語言支援。

### Q: 有免費方案嗎？

A: 有的，免費方案每月可發送 1000 次查詢。
"""

    # 測試每種策略
    strategies_to_test = [
        (ChunkingStrategy.FIXED_SIZE, {}),
        (ChunkingStrategy.RECURSIVE, {}),
        (ChunkingStrategy.HEADING_BASED, {}),
    ]

    for strategy, kwargs in strategies_to_test:
        chunker = ChunkingFactory.create(
            strategy,
            chunk_size=300,
            chunk_overlap=30,
            **kwargs
        )
        chunks = chunker.chunk(sample_text)
        display_chunks(chunks, f"{strategy.value} 策略")

    # 顯示策略清單
    console.print("\n[bold]═══ 可用策略清單 ═══[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("策略", width=20)
    table.add_column("說明", width=35)
    table.add_column("適用場景", width=25)

    for info in ChunkingFactory.list_strategies():
        table.add_row(
            info["name"],
            info["description"],
            info["use_case"]
        )

    console.print(table)


if __name__ == "__main__":
    main()
