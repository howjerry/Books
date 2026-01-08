#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 6 章：長短時記憶管理
嵌入生成器實現

這個模組實現了文本嵌入生成功能：
1. 單文本嵌入
2. 批次嵌入
3. 快取機制
4. 相似度計算

使用方式：
    python embedder.py --demo
    python embedder.py --text "要嵌入的文本"
"""

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


@dataclass
class EmbeddingResult:
    """嵌入結果"""
    text: str
    embedding: List[float]
    model: str
    dimensions: int

    def to_numpy(self) -> np.ndarray:
        return np.array(self.embedding)


class EmbeddingGenerator:
    """
    嵌入生成器

    ‹1› 使用 OpenAI embedding API
    ‹2› 支援批次處理
    ‹3› 內建快取機制
    """

    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        model: str = "text-embedding-3-small",
        cache_enabled: bool = True
    ):
        self.client = client or AsyncOpenAI()
        self.model = model
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, List[float]] = {}

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    async def embed(self, text: str) -> EmbeddingResult:
        """生成單個文本的嵌入"""
        # 檢查快取
        if self.cache_enabled:
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                embedding = self._cache[cache_key]
                return EmbeddingResult(
                    text=text,
                    embedding=embedding,
                    model=self.model,
                    dimensions=len(embedding)
                )

        # 調用 API
        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )

        embedding = response.data[0].embedding

        # 存入快取
        if self.cache_enabled:
            self._cache[cache_key] = embedding

        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model,
            dimensions=len(embedding)
        )

    async def batch_embed(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[EmbeddingResult]:
        """批次生成嵌入"""
        all_results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # 分離已快取和未快取的
            cached_results = []
            to_embed = []

            for j, text in enumerate(batch):
                if self.cache_enabled:
                    cache_key = self._get_cache_key(text)
                    if cache_key in self._cache:
                        cached_results.append((j, EmbeddingResult(
                            text=text,
                            embedding=self._cache[cache_key],
                            model=self.model,
                            dimensions=len(self._cache[cache_key])
                        )))
                        continue
                to_embed.append((j, text))

            # 批次嵌入未快取的
            if to_embed:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=[t for _, t in to_embed]
                )

                for k, (j, text) in enumerate(to_embed):
                    embedding = response.data[k].embedding

                    if self.cache_enabled:
                        cache_key = self._get_cache_key(text)
                        self._cache[cache_key] = embedding

                    cached_results.append((j, EmbeddingResult(
                        text=text,
                        embedding=embedding,
                        model=self.model,
                        dimensions=len(embedding)
                    )))

            # 按原始順序排列
            cached_results.sort(key=lambda x: x[0])
            all_results.extend([r for _, r in cached_results])

        return all_results

    def embed_sync(self, text: str) -> List[float]:
        """同步生成嵌入（返回嵌入向量）"""
        result = asyncio.get_event_loop().run_until_complete(self.embed(text))
        return result.embedding

    def _get_cache_key(self, text: str) -> str:
        """生成快取鍵"""
        return hashlib.md5(f"{self.model}:{text}".encode()).hexdigest()

    def clear_cache(self) -> int:
        """清除快取"""
        count = len(self._cache)
        self._cache.clear()
        return count


class SimilarityCalculator:
    """
    相似度計算器

    ‹1› 餘弦相似度
    ‹2› 歐幾里得距離
    ‹3› 點積相似度
    """

    @staticmethod
    def cosine_similarity(
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """計算餘弦相似度"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    @staticmethod
    def euclidean_distance(
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """計算歐幾里得距離"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return float(np.linalg.norm(vec1 - vec2))

    @staticmethod
    def dot_product(
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """計算點積"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return float(np.dot(vec1, vec2))

    @staticmethod
    def find_most_similar(
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """找到最相似的 K 個候選"""
        query = np.array(query_embedding)
        candidates = np.array(candidate_embeddings)

        # 計算餘弦相似度
        query_norm = np.linalg.norm(query)
        candidate_norms = np.linalg.norm(candidates, axis=1)

        # 避免除以零
        valid_mask = (candidate_norms > 0) & (query_norm > 0)

        similarities = np.zeros(len(candidates))
        if query_norm > 0:
            similarities[valid_mask] = (
                np.dot(candidates[valid_mask], query) /
                (candidate_norms[valid_mask] * query_norm)
            )

        # 獲取 top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [(int(idx), float(similarities[idx])) for idx in top_indices]


# =============================================================================
# 簡單嵌入器（用於測試和離線場景）
# =============================================================================

class SimpleEmbedder:
    """
    簡單嵌入器（不需要 API）

    ‹1› 基於文本特徵生成嵌入
    ‹2› 用於測試和離線場景
    ‹3› 不具備語義理解能力
    """

    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions

    def embed(self, text: str) -> List[float]:
        """生成簡單嵌入"""
        # 基於文本特徵生成偽嵌入
        embedding = []

        # 特徵 1: 長度相關
        embedding.append(len(text) / 1000)

        # 特徵 2: 字符分布
        for c in "abcdefghijklmnopqrstuvwxyz":
            embedding.append(text.lower().count(c) / max(len(text), 1))

        # 特徵 3: 數字和標點
        embedding.append(sum(c.isdigit() for c in text) / max(len(text), 1))
        embedding.append(sum(c in ".,!?;:" for c in text) / max(len(text), 1))

        # 特徵 4: 空格（詞數估計）
        embedding.append(text.count(" ") / max(len(text), 1))

        # 填充或截斷到指定維度
        while len(embedding) < self.dimensions:
            embedding.append(0.0)

        embedding = embedding[:self.dimensions]

        # 歸一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [e / norm for e in embedding]

        return embedding

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """批次生成嵌入"""
        return [self.embed(text) for text in texts]


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範嵌入功能"""
    print("=" * 60)
    print("🔢 嵌入生成器示範")
    print("=" * 60)

    # 使用簡單嵌入器（不需要 API）
    print("\n📍 使用 SimpleEmbedder（離線模式）")
    print("-" * 40)

    simple_embedder = SimpleEmbedder(dimensions=32)
    calc = SimilarityCalculator()

    texts = [
        "NVIDIA 在 AI 晶片市場佔據主導地位",
        "AMD 正在積極追趕 NVIDIA 的市場份額",
        "Intel 正在轉型進入 AI 加速器市場",
        "蘋果公司發布了新款 iPhone"
    ]

    embeddings = [simple_embedder.embed(t) for t in texts]

    print("\n文本嵌入維度:", len(embeddings[0]))

    print("\n相似度矩陣:")
    print(" " * 10, end="")
    for i in range(len(texts)):
        print(f"  T{i+1}  ", end="")
    print()

    for i, emb_i in enumerate(embeddings):
        print(f"T{i+1}:      ", end="")
        for emb_j in embeddings:
            sim = calc.cosine_similarity(emb_i, emb_j)
            print(f"{sim:.2f}  ", end="")
        print()

    print("\n與「AI 晶片市場」最相關的文本:")
    query_embedding = simple_embedder.embed("AI 晶片市場競爭")
    top_results = calc.find_most_similar(query_embedding, embeddings, top_k=3)

    for idx, sim in top_results:
        print(f"  [{sim:.3f}] {texts[idx]}")

    # 顯示 OpenAI 嵌入器資訊
    print("\n" + "=" * 60)
    print("💡 OpenAI 嵌入器")
    print("=" * 60)
    print("""
要使用 OpenAI 嵌入器，請設置 OPENAI_API_KEY 環境變數：

    from embedder import EmbeddingGenerator

    generator = EmbeddingGenerator()
    result = await generator.embed("你的文本")
    print(f"嵌入維度: {result.dimensions}")
    print(f"模型: {result.model}")

支援的模型:
  - text-embedding-3-small (1536 維)
  - text-embedding-3-large (3072 維)
  - text-embedding-ada-002 (1536 維)
""")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="嵌入生成器")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("--text", type=str, help="要嵌入的文本")

    args = parser.parse_args()

    if args.text:
        embedder = SimpleEmbedder()
        embedding = embedder.embed(args.text)
        print(f"嵌入維度: {len(embedding)}")
        print(f"前 10 維: {embedding[:10]}")
    else:
        asyncio.run(demo())


if __name__ == "__main__":
    main()
