#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 6 章：長短時記憶管理
情節壓縮器實現

這個模組實現了多層級的情節壓縮策略：
1. 輕度壓縮：保留 80% 細節
2. 中度壓縮：保留 50% 細節
3. 重度壓縮：只保留關鍵結論

使用方式：
    python compressor.py --demo
    python compressor.py --text "要壓縮的內容"
"""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class CompressionLevel(Enum):
    """壓縮級別"""
    LIGHT = "light"      # 輕度壓縮
    MEDIUM = "medium"    # 中度壓縮
    HEAVY = "heavy"      # 重度壓縮


@dataclass
class CompressionResult:
    """壓縮結果"""
    original: str
    compressed: str
    level: CompressionLevel
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "compression_ratio": self.compression_ratio
        }


class ProgressiveCompressor:
    """
    漸進式壓縮器

    ‹1› 根據記憶年齡調整壓縮程度
    ‹2› 越舊的記憶壓縮越狠
    ‹3› 支援批次壓縮
    """

    COMPRESSION_PROMPTS = {
        CompressionLevel.LIGHT: """請輕度壓縮以下內容，保留 80% 的細節。
保留：所有數據、主要發現、重要引用
省略：重複的描述、過渡語句

原始內容：
{content}

壓縮後（約 100 字）：""",

        CompressionLevel.MEDIUM: """請中度壓縮以下內容，保留 50% 的細節。
保留：關鍵數據、主要結論
省略：過程描述、次要細節

原始內容：
{content}

壓縮後（約 50 字）：""",

        CompressionLevel.HEAVY: """請重度壓縮以下內容，只保留核心結論。
保留：最關鍵的 1-2 個結論
省略：所有細節和過程

原始內容：
{content}

壓縮後（約 20 字）："""
    }

    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        model: str = "gpt-4o-mini"
    ):
        self.client = client or AsyncOpenAI()
        self.model = model
        self._cache: Dict[str, str] = {}

    def get_compression_level(self, age_hours: float) -> CompressionLevel:
        """根據年齡決定壓縮級別"""
        if age_hours < 1:
            return CompressionLevel.LIGHT
        elif age_hours < 4:
            return CompressionLevel.MEDIUM
        else:
            return CompressionLevel.HEAVY

    async def compress(
        self,
        content: str,
        level: Optional[CompressionLevel] = None,
        age_hours: Optional[float] = None
    ) -> CompressionResult:
        """
        壓縮內容

        ‹1› 如果提供年齡，自動決定壓縮級別
        ‹2› 使用快取避免重複壓縮
        """
        # 決定壓縮級別
        if level is None:
            if age_hours is not None:
                level = self.get_compression_level(age_hours)
            else:
                level = CompressionLevel.MEDIUM

        # 檢查快取
        cache_key = hashlib.md5(f"{content}:{level.value}".encode()).hexdigest()
        if cache_key in self._cache:
            compressed = self._cache[cache_key]
        else:
            # 執行壓縮
            prompt = self.COMPRESSION_PROMPTS[level].format(content=content)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )

            compressed = response.choices[0].message.content.strip()
            self._cache[cache_key] = compressed

        # 計算統計
        original_tokens = len(content) // 3
        compressed_tokens = len(compressed) // 3
        ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

        return CompressionResult(
            original=content,
            compressed=compressed,
            level=level,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=ratio
        )

    async def batch_compress(
        self,
        contents: List[str],
        ages_hours: Optional[List[float]] = None,
        concurrency: int = 5
    ) -> List[CompressionResult]:
        """批次壓縮"""
        semaphore = asyncio.Semaphore(concurrency)

        async def compress_one(content: str, age: Optional[float]) -> CompressionResult:
            async with semaphore:
                return await self.compress(content, age_hours=age)

        if ages_hours is None:
            ages_hours = [None] * len(contents)

        tasks = [
            compress_one(content, age)
            for content, age in zip(contents, ages_hours)
        ]

        return await asyncio.gather(*tasks)

    def compress_sync(
        self,
        content: str,
        level: Optional[CompressionLevel] = None
    ) -> str:
        """同步壓縮（返回壓縮後的文字）"""
        result = asyncio.get_event_loop().run_until_complete(
            self.compress(content, level=level)
        )
        return result.compressed


class AdaptiveCompressor:
    """
    自適應壓縮器

    ‹1› 根據內容類型調整壓縮策略
    ‹2› 數據密集型內容保留更多數字
    ‹3› 敘述型內容保留結構
    """

    CONTENT_TYPE_PROMPTS = {
        "data": """請壓縮以下數據密集型內容，優先保留所有數字和百分比。

原始內容：
{content}

壓縮後（保留所有數字）：""",

        "narrative": """請壓縮以下敘述型內容，保留主要觀點和結構。

原始內容：
{content}

壓縮後（保留主要觀點）：""",

        "technical": """請壓縮以下技術型內容，保留術語和因果關係。

原始內容：
{content}

壓縮後（保留技術要點）："""
    }

    def __init__(self, client: Optional[AsyncOpenAI] = None):
        self.client = client or AsyncOpenAI()

    def classify_content(self, content: str) -> str:
        """分類內容類型"""
        # 簡單規則判斷
        digit_ratio = sum(c.isdigit() for c in content) / len(content) if content else 0
        has_percentage = "%" in content

        if digit_ratio > 0.05 or has_percentage:
            return "data"
        elif any(kw in content.lower() for kw in ["函數", "類別", "api", "實現", "架構"]):
            return "technical"
        else:
            return "narrative"

    async def compress(self, content: str) -> str:
        """自適應壓縮"""
        content_type = self.classify_content(content)
        prompt = self.CONTENT_TYPE_PROMPTS[content_type].format(content=content)

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3
        )

        return response.choices[0].message.content.strip()


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範壓縮功能"""
    print("=" * 60)
    print("🗜️ 情節壓縮器示範")
    print("=" * 60)

    compressor = ProgressiveCompressor()

    # 測試內容
    test_content = """
    [步驟 5]
    思考：根據搜尋結果，我需要深入了解 NVIDIA 的 GPU 架構優勢。
    主要關注 CUDA 生態系統、Tensor Core 技術、以及與競爭對手的對比。

    行動：調用 web_browser

    觀察：NVIDIA 的 GPU 架構優勢主要體現在三個方面：
    1. CUDA 生態系統：超過 400 萬開發者，10+ 年積累
    2. Tensor Core：專為 AI 優化的計算單元，FP8 精度支援
    3. 軟體棧：cuDNN、TensorRT、Triton 推理伺服器
    與 AMD 相比，NVIDIA 的軟體生態更成熟，但 AMD 在性價比上有優勢。
    """

    print(f"\n原始內容長度: {len(test_content)} 字符")

    # 測試不同壓縮級別
    for level in CompressionLevel:
        print(f"\n{'='*40}")
        print(f"📊 {level.value.upper()} 壓縮")
        print("=" * 40)

        result = await compressor.compress(test_content, level=level)

        print(f"壓縮後: {result.compressed}")
        print(f"壓縮比: {result.compression_ratio*100:.1f}%")
        print(f"Token: {result.original_tokens} → {result.compressed_tokens}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="情節壓縮器")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("--text", type=str, help="要壓縮的文字")
    parser.add_argument(
        "--level",
        choices=["light", "medium", "heavy"],
        default="medium",
        help="壓縮級別"
    )

    args = parser.parse_args()

    if args.text:
        compressor = ProgressiveCompressor()
        level = CompressionLevel(args.level)
        result = asyncio.run(compressor.compress(args.text, level=level))
        print(f"壓縮後: {result.compressed}")
        print(f"壓縮比: {result.compression_ratio*100:.1f}%")
    else:
        asyncio.run(demo())


if __name__ == "__main__":
    main()
