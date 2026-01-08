#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 7 章：搜尋與檢索引擎
搜尋引擎整合實現

這個模組實現了多搜尋引擎整合：
1. Serper (Google Search API)
2. Tavily (AI 原生搜尋)
3. DuckDuckGo (免費)

使用方式：
    python search_engine.py --demo
    python search_engine.py -q "AI 晶片市場"
"""

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# 資料結構
# =============================================================================

class SearchEngine(Enum):
    """支援的搜尋引擎"""
    SERPER = "serper"
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"


@dataclass
class SearchResult:
    """
    搜尋結果

    ‹1› 統一的結果格式
    ‹2› 包含來源評估資訊
    """
    title: str
    url: str
    snippet: str
    source: str
    published_date: Optional[datetime] = None
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata
        }


# =============================================================================
# 搜尋提供者基類
# =============================================================================

class BaseSearchProvider(ABC):
    """搜尋提供者基類"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        pass


# =============================================================================
# Serper (Google Search API)
# =============================================================================

class SerperSearchProvider(BaseSearchProvider):
    """
    Serper API 搜尋提供者

    ‹1› 使用 Google Search API
    ‹2› 支援多種搜尋類型
    """

    BASE_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")

    @property
    def name(self) -> str:
        return "serper"

    async def search(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "search",
        country: str = "tw",
        language: str = "zh-TW"
    ) -> List[SearchResult]:
        """執行 Google 搜尋"""
        if not self.api_key:
            raise ValueError("SERPER_API_KEY 未設置")

        async with aiohttp.ClientSession() as session:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }

            payload = {
                "q": query,
                "num": num_results,
                "gl": country,
                "hl": language
            }

            async with session.post(
                self.BASE_URL,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    raise Exception(f"Serper 搜尋失敗: {response.status}")

                data = await response.json()
                return self._parse_results(data)

    def _parse_results(self, data: dict) -> List[SearchResult]:
        results = []
        for item in data.get("organic", []):
            result = SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                source="google",
                metadata={
                    "position": item.get("position"),
                    "sitelinks": item.get("sitelinks", [])
                }
            )
            results.append(result)
        return results


# =============================================================================
# Tavily (AI 原生搜尋)
# =============================================================================

class TavilySearchProvider(BaseSearchProvider):
    """
    Tavily AI 搜尋提供者

    ‹1› AI 優化的搜尋結果
    ‹2› 自動提取關鍵內容
    """

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")

    @property
    def name(self) -> str:
        return "tavily"

    async def search(
        self,
        query: str,
        num_results: int = 10,
        search_depth: str = "advanced",
        include_answer: bool = True
    ) -> List[SearchResult]:
        """執行 Tavily 搜尋"""
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY 未設置")

        async with aiohttp.ClientSession() as session:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": num_results,
                "search_depth": search_depth,
                "include_answer": include_answer
            }

            async with session.post(self.BASE_URL, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Tavily 搜尋失敗: {response.status}")

                data = await response.json()
                return self._parse_results(data)

    def _parse_results(self, data: dict) -> List[SearchResult]:
        results = []
        for item in data.get("results", []):
            result = SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                source="tavily",
                relevance_score=item.get("score", 0.0),
                metadata={
                    "raw_content": item.get("raw_content"),
                    "answer": data.get("answer")
                }
            )
            results.append(result)
        return results


# =============================================================================
# DuckDuckGo (免費)
# =============================================================================

class DuckDuckGoSearchProvider(BaseSearchProvider):
    """
    DuckDuckGo 搜尋提供者（免費）

    ‹1› 不需要 API Key
    ‹2› 使用 duckduckgo-search 套件
    """

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "duckduckgo"

    async def search(
        self,
        query: str,
        num_results: int = 10,
        region: str = "tw-tzh"
    ) -> List[SearchResult]:
        """執行 DuckDuckGo 搜尋"""
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            raise ImportError("請安裝 duckduckgo-search: pip install duckduckgo-search")

        results = []

        # 使用同步 API 並包裝
        def sync_search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, region=region, max_results=num_results))

        loop = asyncio.get_event_loop()
        raw_results = await loop.run_in_executor(None, sync_search)

        for r in raw_results:
            result = SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
                source="duckduckgo"
            )
            results.append(result)

        return results


# =============================================================================
# 模擬搜尋提供者（用於測試）
# =============================================================================

class MockSearchProvider(BaseSearchProvider):
    """模擬搜尋提供者（用於測試）"""

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "mock"

    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """返回模擬結果"""
        await asyncio.sleep(0.1)  # 模擬網路延遲

        results = []
        for i in range(min(num_results, 5)):
            results.append(SearchResult(
                title=f"關於「{query}」的搜尋結果 {i+1}",
                url=f"https://example.com/result/{i+1}",
                snippet=f"這是關於「{query}」的詳細介紹...",
                source="mock",
                relevance_score=1.0 - i * 0.1
            ))

        return results


# =============================================================================
# 搜尋管理器
# =============================================================================

class SearchManager:
    """
    搜尋管理器

    ‹1› 統一管理多個搜尋提供者
    ‹2› 支援結果聚合和去重
    ‹3› 提供容錯機制
    """

    def __init__(self):
        self._providers: Dict[str, BaseSearchProvider] = {}
        self._default_provider: Optional[str] = None

    def register_provider(
        self,
        provider: BaseSearchProvider,
        set_default: bool = False
    ) -> None:
        """註冊搜尋提供者"""
        self._providers[provider.name] = provider
        if set_default or self._default_provider is None:
            self._default_provider = provider.name

    async def search(
        self,
        query: str,
        num_results: int = 10,
        provider: Optional[str] = None,
        **kwargs
    ) -> List[SearchResult]:
        """執行搜尋"""
        provider_name = provider or self._default_provider
        if not provider_name:
            raise ValueError("沒有可用的搜尋提供者")

        if provider_name not in self._providers:
            raise ValueError(f"未知的搜尋提供者: {provider_name}")

        try:
            provider_instance = self._providers[provider_name]
            return await provider_instance.search(query, num_results, **kwargs)
        except Exception as e:
            # 嘗試回退到其他提供者
            for name, p in self._providers.items():
                if name != provider_name:
                    try:
                        return await p.search(query, num_results, **kwargs)
                    except:
                        continue
            raise e

    async def multi_search(
        self,
        query: str,
        num_results: int = 10,
        providers: Optional[List[str]] = None,
        deduplicate: bool = True
    ) -> List[SearchResult]:
        """多引擎搜尋"""
        providers = providers or list(self._providers.keys())

        tasks = [
            self.search(query, num_results, provider=p)
            for p in providers if p in self._providers
        ]

        all_results = []
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        for results in results_list:
            if isinstance(results, Exception):
                continue
            all_results.extend(results)

        if deduplicate:
            all_results = self._deduplicate(all_results)

        return all_results

    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """去重結果"""
        seen_urls = set()
        unique_results = []

        for result in results:
            url = result.url.rstrip("/").lower()
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results

    @property
    def available_providers(self) -> List[str]:
        return list(self._providers.keys())


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範搜尋功能"""
    print("=" * 60)
    print("🔍 搜尋引擎示範")
    print("=" * 60)

    # 創建搜尋管理器
    manager = SearchManager()

    # 註冊模擬提供者（用於演示）
    manager.register_provider(MockSearchProvider(), set_default=True)

    # 嘗試註冊真實提供者
    if os.getenv("SERPER_API_KEY"):
        manager.register_provider(SerperSearchProvider())
        print("✅ Serper 已註冊")

    if os.getenv("TAVILY_API_KEY"):
        manager.register_provider(TavilySearchProvider())
        print("✅ Tavily 已註冊")

    # 嘗試 DuckDuckGo
    try:
        manager.register_provider(DuckDuckGoSearchProvider())
        print("✅ DuckDuckGo 已註冊")
    except ImportError:
        print("⚠️ DuckDuckGo 需要安裝 duckduckgo-search")

    print(f"\n可用提供者: {manager.available_providers}")

    # 執行搜尋
    query = "2024 AI 晶片市場趨勢"
    print(f"\n🔎 搜尋: {query}")
    print("-" * 40)

    results = await manager.search(query, num_results=5)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   URL: {result.url}")
        print(f"   來源: {result.source}")
        if result.snippet:
            print(f"   摘要: {result.snippet[:100]}...")

    print(f"\n共找到 {len(results)} 個結果")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="搜尋引擎")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("-q", "--query", type=str, help="搜尋查詢")

    args = parser.parse_args()

    if args.query:
        async def search_query():
            manager = SearchManager()
            manager.register_provider(MockSearchProvider(), set_default=True)
            results = await manager.search(args.query, num_results=5)
            for r in results:
                print(f"• {r.title}: {r.url}")

        asyncio.run(search_query())
    else:
        asyncio.run(demo())


if __name__ == "__main__":
    main()
