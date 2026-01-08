# 第 7 章：搜尋與檢索引擎

> **本章目標**：掌握深度研究代理人的資訊獲取能力，學會建構網頁瀏覽、RAG 檢索和知識圖譜整合的完整搜尋系統。

---

## 7.1 問題：代理人如何「看見」世界？

想像你給代理人一個研究任務：「分析 2024 年 Q3 全球半導體產業的最新動態」。

代理人需要：
1. 在網路上搜尋最新資訊
2. 瀏覽相關網頁並提取內容
3. 從海量資訊中找到關鍵資料
4. 整合多個來源形成完整報告

這些能力的背後，是一套精密的**搜尋與檢索引擎**。

### MiroThinker 的資訊獲取架構

```
┌─────────────────────────────────────────────────────────────┐
│                   資訊獲取架構                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  搜尋層（Discovery）                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ 網頁搜尋 │  │ 學術搜尋 │  │ 新聞搜尋 │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  擷取層（Extraction）                │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ 網頁瀏覽 │  │ PDF 解析 │  │ 結構提取 │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  檢索層（Retrieval）                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ RAG 檢索 │  │ 向量搜尋 │  │ 知識圖譜 │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

本章將帶你實現這套完整的搜尋與檢索系統。

---

## 7.2 網頁搜尋引擎整合

### 7.2.1 搜尋 API 封裝

首先，我們需要一個統一的搜尋介面，支援多種搜尋引擎：

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import aiohttp
import asyncio


class SearchEngine(Enum):
    """支援的搜尋引擎"""
    SERPER = "serper"          # Google 搜尋 API
    TAVILY = "tavily"          # AI 原生搜尋
    BING = "bing"              # Bing 搜尋
    DUCKDUCKGO = "duckduckgo"  # DuckDuckGo（免費）


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


class BaseSearchProvider(ABC):
    """搜尋提供者基類"""

    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """執行搜尋"""
        pass


class SerperSearchProvider(BaseSearchProvider):
    """
    Serper API 搜尋提供者

    ‹1› 使用 Google Search API
    ‹2› 支援多種搜尋類型
    """

    BASE_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "search",
        country: str = "tw",
        language: str = "zh-TW"
    ) -> List[SearchResult]:
        """執行 Google 搜尋"""
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
                    raise Exception(f"搜尋失敗: {response.status}")

                data = await response.json()
                return self._parse_results(data)

    def _parse_results(self, data: dict) -> List[SearchResult]:
        """解析搜尋結果"""
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


class TavilySearchProvider(BaseSearchProvider):
    """
    Tavily AI 搜尋提供者

    ‹1› AI 優化的搜尋結果
    ‹2› 自動提取關鍵內容
    """

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(
        self,
        query: str,
        num_results: int = 10,
        search_depth: str = "advanced",
        include_answer: bool = True
    ) -> List[SearchResult]:
        """執行 Tavily 搜尋"""
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
                    raise Exception(f"搜尋失敗: {response.status}")

                data = await response.json()
                return self._parse_results(data)

    def _parse_results(self, data: dict) -> List[SearchResult]:
        """解析搜尋結果"""
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


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """
    DuckDuckGo 搜尋提供者（免費）

    ‹1› 不需要 API Key
    ‹2› 使用 HTML 解析
    """

    async def search(
        self,
        query: str,
        num_results: int = 10,
        region: str = "tw-tzh"
    ) -> List[SearchResult]:
        """執行 DuckDuckGo 搜尋"""
        # 使用 duckduckgo-search 套件
        try:
            from duckduckgo_search import AsyncDDGS
        except ImportError:
            raise ImportError("請安裝 duckduckgo-search: pip install duckduckgo-search")

        results = []
        async with AsyncDDGS() as ddgs:
            async for r in ddgs.text(
                query,
                region=region,
                max_results=num_results
            ):
                result = SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    source="duckduckgo"
                )
                results.append(result)

        return results
```

### 7.2.2 統一搜尋管理器

```python
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
        name: str,
        provider: BaseSearchProvider,
        set_default: bool = False
    ) -> None:
        """註冊搜尋提供者"""
        self._providers[name] = provider
        if set_default or self._default_provider is None:
            self._default_provider = name

    async def search(
        self,
        query: str,
        num_results: int = 10,
        provider: Optional[str] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        執行搜尋

        ‹1› 使用指定或預設提供者
        ‹2› 失敗時自動回退
        """
        provider_name = provider or self._default_provider
        if not provider_name:
            raise ValueError("沒有可用的搜尋提供者")

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
        """
        多引擎搜尋

        ‹1› 同時使用多個引擎
        ‹2› 合併並去重結果
        """
        providers = providers or list(self._providers.keys())

        tasks = [
            self.search(query, num_results, provider=p)
            for p in providers
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
            # 正規化 URL
            url = result.url.rstrip("/").lower()
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results
```

---

## 7.3 網頁瀏覽與內容擷取

搜尋只能得到摘要，要深入了解內容，需要瀏覽網頁並擷取完整內容。

### 7.3.1 網頁瀏覽器實現

```python
import re
from typing import Tuple
from urllib.parse import urljoin, urlparse


@dataclass
class WebPage:
    """
    網頁內容

    ‹1› 包含原始 HTML 和提取後的純文字
    ‹2› 記錄提取的結構化資訊
    """
    url: str
    title: str
    content: str
    html: Optional[str] = None
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)
    status_code: int = 200

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def char_count(self) -> int:
        return len(self.content)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content[:1000] + "..." if len(self.content) > 1000 else self.content,
            "word_count": self.word_count,
            "link_count": len(self.links),
            "fetched_at": self.fetched_at.isoformat(),
            "status_code": self.status_code
        }


class WebBrowser:
    """
    網頁瀏覽器

    ‹1› 獲取網頁內容
    ‹2› 提取純文字
    ‹3› 處理各種格式（HTML, PDF 等）
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_content_length: int = 100000,
        user_agent: str = "MiroThinker/1.0 Research Agent"
    ):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.user_agent = user_agent

    async def browse(self, url: str) -> WebPage:
        """
        瀏覽網頁

        ‹1› 獲取內容
        ‹2› 提取純文字
        ‹3› 解析連結和圖片
        """
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": self.user_agent}

            try:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    status_code = response.status

                    if status_code != 200:
                        return WebPage(
                            url=url,
                            title="",
                            content=f"無法獲取網頁：HTTP {status_code}",
                            status_code=status_code
                        )

                    content_type = response.headers.get("Content-Type", "")

                    # 根據內容類型處理
                    if "application/pdf" in content_type:
                        content = await response.read()
                        return await self._process_pdf(url, content)

                    html = await response.text()

                    if len(html) > self.max_content_length:
                        html = html[:self.max_content_length]

                    return self._process_html(url, html)

            except asyncio.TimeoutError:
                return WebPage(
                    url=url,
                    title="",
                    content="網頁載入超時",
                    status_code=408
                )
            except Exception as e:
                return WebPage(
                    url=url,
                    title="",
                    content=f"獲取失敗：{str(e)}",
                    status_code=500
                )

    def _process_html(self, url: str, html: str) -> WebPage:
        """處理 HTML 內容"""
        # 提取標題
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        # 移除腳本和樣式
        html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)

        # 提取純文字
        text = re.sub(r'<[^>]+>', ' ', html_clean)
        text = re.sub(r'\s+', ' ', text).strip()

        # 提取連結
        links = []
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            link = match.group(1)
            if link.startswith("http"):
                links.append(link)
            elif link.startswith("/"):
                links.append(urljoin(url, link))

        # 提取圖片
        images = []
        for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE):
            img = match.group(1)
            if img.startswith("http"):
                images.append(img)
            elif img.startswith("/"):
                images.append(urljoin(url, img))

        return WebPage(
            url=url,
            title=title,
            content=text,
            html=html,
            links=links[:50],  # 限制連結數量
            images=images[:20],
            metadata={
                "content_type": "text/html"
            }
        )

    async def _process_pdf(self, url: str, content: bytes) -> WebPage:
        """處理 PDF 內容"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return WebPage(
                url=url,
                title="PDF 文件",
                content="需要安裝 PyMuPDF 來解析 PDF：pip install pymupdf",
                metadata={"content_type": "application/pdf"}
            )

        try:
            doc = fitz.open(stream=content, filetype="pdf")
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())

            text = "\n".join(text_parts)

            return WebPage(
                url=url,
                title=doc.metadata.get("title", "PDF 文件"),
                content=text,
                metadata={
                    "content_type": "application/pdf",
                    "page_count": len(doc),
                    "author": doc.metadata.get("author")
                }
            )
        except Exception as e:
            return WebPage(
                url=url,
                title="PDF 解析失敗",
                content=f"無法解析 PDF：{str(e)}",
                metadata={"content_type": "application/pdf"}
            )

    async def batch_browse(
        self,
        urls: List[str],
        concurrency: int = 5
    ) -> List[WebPage]:
        """批次瀏覽多個網頁"""
        semaphore = asyncio.Semaphore(concurrency)

        async def browse_one(url: str) -> WebPage:
            async with semaphore:
                return await self.browse(url)

        tasks = [browse_one(url) for url in urls]
        return await asyncio.gather(*tasks)
```

### 7.3.2 智能內容提取

```python
class ContentExtractor:
    """
    智能內容提取器

    ‹1› 識別主要內容區域
    ‹2› 過濾廣告和導航
    ‹3› 保留結構化資訊
    """

    # 常見的非內容元素
    NOISE_PATTERNS = [
        r'class="[^"]*(?:nav|menu|sidebar|footer|header|advertisement|ad-|banner)[^"]*"',
        r'id="[^"]*(?:nav|menu|sidebar|footer|header|advertisement|ad-|banner)[^"]*"',
    ]

    # 主要內容區域識別
    CONTENT_PATTERNS = [
        r'class="[^"]*(?:article|content|main|post|entry|story)[^"]*"',
        r'<article[^>]*>',
        r'<main[^>]*>',
    ]

    def __init__(self, min_content_length: int = 100):
        self.min_content_length = min_content_length

    def extract(self, html: str) -> str:
        """提取主要內容"""
        # 移除腳本和樣式
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

        # 嘗試識別主要內容區域
        main_content = self._find_main_content(html)

        if main_content and len(main_content) > self.min_content_length:
            return self._clean_text(main_content)

        # 回退到全文提取
        return self._clean_text(html)

    def _find_main_content(self, html: str) -> Optional[str]:
        """識別主要內容區域"""
        for pattern in self.CONTENT_PATTERNS:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                start = match.start()
                # 找到對應的結束標籤
                tag_match = re.match(r'<(\w+)', html[start:])
                if tag_match:
                    tag_name = tag_match.group(1)
                    # 簡化的標籤匹配
                    end_pattern = f'</{tag_name}>'
                    end_match = re.search(end_pattern, html[start:], re.IGNORECASE)
                    if end_match:
                        return html[start:start + end_match.end()]

        return None

    def _clean_text(self, html: str) -> str:
        """清理並提取純文字"""
        # 移除 HTML 標籤
        text = re.sub(r'<[^>]+>', ' ', html)
        # 處理 HTML 實體
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;', '"', text)
        # 正規化空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_structured(self, html: str) -> Dict[str, Any]:
        """提取結構化資訊"""
        result = {
            "title": "",
            "headings": [],
            "paragraphs": [],
            "lists": [],
            "tables": []
        }

        # 提取標題
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            result["title"] = self._clean_text(title_match.group(1))

        # 提取標題層級
        for level in range(1, 7):
            for match in re.finditer(rf'<h{level}[^>]*>(.*?)</h{level}>', html, re.IGNORECASE | re.DOTALL):
                result["headings"].append({
                    "level": level,
                    "text": self._clean_text(match.group(1))
                })

        # 提取段落
        for match in re.finditer(r'<p[^>]*>(.*?)</p>', html, re.IGNORECASE | re.DOTALL):
            text = self._clean_text(match.group(1))
            if len(text) > 20:  # 過濾太短的段落
                result["paragraphs"].append(text)

        return result
```

---

## 7.4 RAG 檢索系統

RAG（Retrieval-Augmented Generation）是深度研究代理人的核心能力——從大量文件中找到相關資訊。

### 7.4.1 文件分塊器

```python
@dataclass
class DocumentChunk:
    """
    文件片段

    ‹1› 包含原始內容和來源資訊
    ‹2› 支援向量嵌入
    """
    content: str
    source_url: str
    chunk_index: int
    total_chunks: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        url_hash = hashlib.md5(self.source_url.encode()).hexdigest()[:8]
        return f"chunk_{url_hash}_{self.chunk_index}"


class DocumentChunker:
    """
    文件分塊器

    ‹1› 支援多種分塊策略
    ‹2› 保持語義完整性
    ‹3› 處理重疊以避免資訊丟失
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", ".", " "]

    def chunk(
        self,
        text: str,
        source_url: str = "",
        **metadata
    ) -> List[DocumentChunk]:
        """
        將文件分割成片段

        ‹1› 嘗試在自然邊界分割
        ‹2› 保持片段大小一致
        ‹3› 添加重疊以保持上下文
        """
        if not text.strip():
            return []

        chunks = []
        current_pos = 0
        chunk_index = 0

        while current_pos < len(text):
            # 計算片段結束位置
            end_pos = current_pos + self.chunk_size

            if end_pos >= len(text):
                # 最後一個片段
                chunk_text = text[current_pos:].strip()
                if chunk_text:
                    chunks.append(DocumentChunk(
                        content=chunk_text,
                        source_url=source_url,
                        chunk_index=chunk_index,
                        total_chunks=0,  # 稍後更新
                        metadata=metadata
                    ))
                break

            # 尋找最佳分割點
            best_split = end_pos
            for separator in self.separators:
                # 在目標位置附近尋找分隔符
                search_start = max(current_pos + self.chunk_size // 2, current_pos)
                sep_pos = text.rfind(separator, search_start, end_pos + 50)
                if sep_pos > current_pos:
                    best_split = sep_pos + len(separator)
                    break

            chunk_text = text[current_pos:best_split].strip()
            if chunk_text:
                chunks.append(DocumentChunk(
                    content=chunk_text,
                    source_url=source_url,
                    chunk_index=chunk_index,
                    total_chunks=0,
                    metadata=metadata
                ))
                chunk_index += 1

            # 移動到下一個位置（考慮重疊）
            current_pos = best_split - self.chunk_overlap

        # 更新總片段數
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks


class SemanticChunker:
    """
    語義分塊器

    ‹1› 基於語義相似度分塊
    ‹2› 保持語義完整的段落
    """

    def __init__(
        self,
        embedder,
        similarity_threshold: float = 0.5,
        max_chunk_size: int = 1000
    ):
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.max_chunk_size = max_chunk_size

    async def chunk(
        self,
        text: str,
        source_url: str = ""
    ) -> List[DocumentChunk]:
        """語義分塊"""
        # 先按段落分割
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if not paragraphs:
            return []

        # 計算段落嵌入
        embeddings = await self._batch_embed(paragraphs)

        # 基於相似度合併相鄰段落
        chunks = []
        current_chunk = paragraphs[0]
        current_embedding = embeddings[0]

        for i in range(1, len(paragraphs)):
            # 計算與當前片段的相似度
            similarity = self._cosine_similarity(current_embedding, embeddings[i])

            if similarity > self.similarity_threshold and len(current_chunk) + len(paragraphs[i]) < self.max_chunk_size:
                # 合併
                current_chunk += "\n\n" + paragraphs[i]
                # 更新嵌入（簡單平均）
                current_embedding = [
                    (a + b) / 2
                    for a, b in zip(current_embedding, embeddings[i])
                ]
            else:
                # 開始新片段
                chunks.append(current_chunk)
                current_chunk = paragraphs[i]
                current_embedding = embeddings[i]

        chunks.append(current_chunk)

        return [
            DocumentChunk(
                content=chunk,
                source_url=source_url,
                chunk_index=i,
                total_chunks=len(chunks)
            )
            for i, chunk in enumerate(chunks)
        ]

    async def _batch_embed(self, texts: List[str]) -> List[List[float]]:
        """批次計算嵌入"""
        return [await self.embedder.embed(t) for t in texts]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """計算餘弦相似度"""
        import numpy as np
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-8))
```

### 7.4.2 向量索引

```python
import numpy as np


class VectorIndex:
    """
    向量索引

    ‹1› 高效的相似度搜尋
    ‹2› 支援增量更新
    ‹3› 可持久化
    """

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self._chunks: List[DocumentChunk] = []
        self._embeddings: Optional[np.ndarray] = None

    def add(self, chunk: DocumentChunk) -> None:
        """添加片段"""
        if chunk.embedding is None:
            raise ValueError("片段必須包含嵌入向量")

        self._chunks.append(chunk)

        embedding = np.array(chunk.embedding).reshape(1, -1)
        if self._embeddings is None:
            self._embeddings = embedding
        else:
            self._embeddings = np.vstack([self._embeddings, embedding])

    def add_batch(self, chunks: List[DocumentChunk]) -> None:
        """批次添加片段"""
        for chunk in chunks:
            self.add(chunk)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        搜尋最相關的片段

        ‹1› 使用餘弦相似度
        ‹2› 返回分數和片段
        """
        if self._embeddings is None or len(self._chunks) == 0:
            return []

        query = np.array(query_embedding)

        # 計算相似度
        norms = np.linalg.norm(self._embeddings, axis=1)
        query_norm = np.linalg.norm(query)

        if query_norm == 0:
            return []

        similarities = np.dot(self._embeddings, query) / (norms * query_norm + 1e-8)

        # 獲取 top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= min_score:
                results.append((self._chunks[idx], score))

        return results

    @property
    def size(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        """清空索引"""
        self._chunks = []
        self._embeddings = None


class RAGRetriever:
    """
    RAG 檢索器

    ‹1› 整合分塊、索引和檢索
    ‹2› 支援多種檢索策略
    ‹3› 提供上下文增強
    """

    def __init__(
        self,
        embedder,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.embedder = embedder
        self.chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.index = VectorIndex()

    async def add_document(
        self,
        content: str,
        source_url: str = "",
        **metadata
    ) -> int:
        """
        添加文件到索引

        ‹1› 分塊
        ‹2› 計算嵌入
        ‹3› 加入索引
        """
        chunks = self.chunker.chunk(content, source_url, **metadata)

        for chunk in chunks:
            embedding = await self.embedder.embed(chunk.content)
            chunk.embedding = embedding
            self.index.add(chunk)

        return len(chunks)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Tuple[DocumentChunk, float]]:
        """檢索相關片段"""
        query_embedding = await self.embedder.embed(query)
        return self.index.search(query_embedding, top_k, min_score)

    async def retrieve_with_context(
        self,
        query: str,
        top_k: int = 5,
        context_window: int = 1
    ) -> str:
        """
        檢索並生成上下文

        ‹1› 檢索相關片段
        ‹2› 包含相鄰片段
        ‹3› 格式化為 prompt
        """
        results = await self.retrieve(query, top_k)

        if not results:
            return "未找到相關資訊。"

        context_parts = []
        for chunk, score in results:
            context_parts.append(f"[來源: {chunk.source_url}]\n[相關度: {score:.2f}]\n{chunk.content}")

        return "\n\n---\n\n".join(context_parts)
```

---

## 7.5 知識圖譜整合

知識圖譜可以捕捉實體之間的關係，提供結構化的知識表示。

### 7.5.1 知識圖譜建構

```python
@dataclass
class Entity:
    """實體"""
    name: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.name, self.entity_type))

    def __eq__(self, other):
        return self.name == other.name and self.entity_type == other.entity_type


@dataclass
class Relation:
    """關係"""
    source: Entity
    target: Entity
    relation_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """
    知識圖譜

    ‹1› 存儲實體和關係
    ‹2› 支援路徑查詢
    ‹3› 提供知識推理
    """

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._relations: List[Relation] = []
        self._adjacency: Dict[str, List[Tuple[str, Relation]]] = {}

    def add_entity(self, entity: Entity) -> None:
        """添加實體"""
        key = f"{entity.entity_type}:{entity.name}"
        self._entities[key] = entity
        if key not in self._adjacency:
            self._adjacency[key] = []

    def add_relation(self, relation: Relation) -> None:
        """添加關係"""
        # 確保實體存在
        source_key = f"{relation.source.entity_type}:{relation.source.name}"
        target_key = f"{relation.target.entity_type}:{relation.target.name}"

        if source_key not in self._entities:
            self.add_entity(relation.source)
        if target_key not in self._entities:
            self.add_entity(relation.target)

        self._relations.append(relation)
        self._adjacency[source_key].append((target_key, relation))

    def get_entity(self, name: str, entity_type: str) -> Optional[Entity]:
        """獲取實體"""
        key = f"{entity_type}:{name}"
        return self._entities.get(key)

    def get_relations(
        self,
        source: Optional[Entity] = None,
        target: Optional[Entity] = None,
        relation_type: Optional[str] = None
    ) -> List[Relation]:
        """查詢關係"""
        results = []
        for relation in self._relations:
            if source and relation.source != source:
                continue
            if target and relation.target != target:
                continue
            if relation_type and relation.relation_type != relation_type:
                continue
            results.append(relation)
        return results

    def find_path(
        self,
        source: Entity,
        target: Entity,
        max_depth: int = 3
    ) -> Optional[List[Relation]]:
        """
        查找兩個實體之間的路徑

        ‹1› 使用 BFS 搜尋
        ‹2› 返回最短路徑
        """
        from collections import deque

        source_key = f"{source.entity_type}:{source.name}"
        target_key = f"{target.entity_type}:{target.name}"

        if source_key not in self._entities or target_key not in self._entities:
            return None

        # BFS
        queue = deque([(source_key, [])])
        visited = {source_key}

        while queue:
            current, path = queue.popleft()

            if current == target_key:
                return path

            if len(path) >= max_depth:
                continue

            for next_key, relation in self._adjacency.get(current, []):
                if next_key not in visited:
                    visited.add(next_key)
                    queue.append((next_key, path + [relation]))

        return None

    def get_neighbors(
        self,
        entity: Entity,
        relation_type: Optional[str] = None
    ) -> List[Tuple[Entity, Relation]]:
        """獲取相鄰實體"""
        key = f"{entity.entity_type}:{entity.name}"
        neighbors = []

        for next_key, relation in self._adjacency.get(key, []):
            if relation_type and relation.relation_type != relation_type:
                continue
            neighbors.append((self._entities[next_key], relation))

        return neighbors

    def to_prompt(self, max_triples: int = 20) -> str:
        """轉換為 prompt 格式"""
        lines = ["[知識圖譜]"]

        for i, relation in enumerate(self._relations[:max_triples]):
            line = f"({relation.source.name}) --[{relation.relation_type}]--> ({relation.target.name})"
            lines.append(line)

        if len(self._relations) > max_triples:
            lines.append(f"... 還有 {len(self._relations) - max_triples} 個關係")

        return "\n".join(lines)

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def relation_count(self) -> int:
        return len(self._relations)
```

### 7.5.2 實體關係提取

```python
class EntityRelationExtractor:
    """
    實體關係提取器

    ‹1› 使用 LLM 提取實體和關係
    ‹2› 支援自訂實體類型
    """

    EXTRACTION_PROMPT = """從以下文本中提取實體和關係。

實體類型：
- COMPANY: 公司、組織
- PERSON: 人物
- PRODUCT: 產品、技術
- LOCATION: 地點
- EVENT: 事件
- METRIC: 數據指標

輸出格式（JSON）：
{{
    "entities": [
        {{"name": "實體名稱", "type": "實體類型"}}
    ],
    "relations": [
        {{"source": "來源實體", "target": "目標實體", "relation": "關係類型"}}
    ]
}}

文本：
{text}

JSON："""

    def __init__(self, client: Optional[AsyncOpenAI] = None):
        self.client = client or AsyncOpenAI()

    async def extract(self, text: str) -> Tuple[List[Entity], List[Relation]]:
        """從文本提取實體和關係"""
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": self.EXTRACTION_PROMPT.format(text=text)
            }],
            response_format={"type": "json_object"},
            max_tokens=1000
        )

        try:
            data = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return [], []

        entities = []
        entity_map = {}

        for e in data.get("entities", []):
            entity = Entity(
                name=e.get("name", ""),
                entity_type=e.get("type", "UNKNOWN")
            )
            entities.append(entity)
            entity_map[entity.name] = entity

        relations = []
        for r in data.get("relations", []):
            source_name = r.get("source", "")
            target_name = r.get("target", "")

            if source_name in entity_map and target_name in entity_map:
                relation = Relation(
                    source=entity_map[source_name],
                    target=entity_map[target_name],
                    relation_type=r.get("relation", "RELATED")
                )
                relations.append(relation)

        return entities, relations
```

---

## 7.6 整合：完整的搜尋檢索系統

現在讓我們將所有組件整合成一個完整的系統：

```python
class SearchRetrievalSystem:
    """
    搜尋檢索系統

    ‹1› 整合搜尋、瀏覽、RAG、知識圖譜
    ‹2› 提供統一的查詢介面
    ‹3› 支援多模態資訊整合
    """

    def __init__(
        self,
        search_manager: SearchManager,
        browser: WebBrowser,
        rag_retriever: RAGRetriever,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        client: Optional[AsyncOpenAI] = None
    ):
        self.search_manager = search_manager
        self.browser = browser
        self.rag = rag_retriever
        self.kg = knowledge_graph or KnowledgeGraph()
        self.client = client or AsyncOpenAI()
        self.extractor = EntityRelationExtractor(client=self.client)

    async def research(
        self,
        query: str,
        num_search_results: int = 5,
        browse_top_n: int = 3,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        執行完整研究流程

        ‹1› 搜尋相關網頁
        ‹2› 瀏覽並擷取內容
        ‹3› 建立 RAG 索引
        ‹4› 提取知識圖譜
        ‹5› 生成研究結果
        """
        result = {
            "query": query,
            "search_results": [],
            "pages_browsed": [],
            "chunks_indexed": 0,
            "entities_extracted": 0,
            "relations_extracted": 0,
            "context": ""
        }

        # 1. 搜尋
        if verbose:
            print(f"🔍 搜尋: {query}")

        search_results = await self.search_manager.search(query, num_search_results)
        result["search_results"] = [r.to_dict() for r in search_results]

        if verbose:
            print(f"   找到 {len(search_results)} 個結果")

        # 2. 瀏覽
        if verbose:
            print(f"🌐 瀏覽前 {browse_top_n} 個網頁")

        urls = [r.url for r in search_results[:browse_top_n]]
        pages = await self.browser.batch_browse(urls)

        for page in pages:
            if page.status_code == 200:
                result["pages_browsed"].append(page.to_dict())

                # 3. 建立 RAG 索引
                chunks_added = await self.rag.add_document(
                    page.content,
                    page.url
                )
                result["chunks_indexed"] += chunks_added

                # 4. 提取知識圖譜
                entities, relations = await self.extractor.extract(page.content[:5000])
                for entity in entities:
                    self.kg.add_entity(entity)
                for relation in relations:
                    self.kg.add_relation(relation)

                result["entities_extracted"] += len(entities)
                result["relations_extracted"] += len(relations)

        if verbose:
            print(f"   瀏覽 {len(result['pages_browsed'])} 個網頁")
            print(f"   索引 {result['chunks_indexed']} 個片段")
            print(f"   提取 {result['entities_extracted']} 個實體")

        # 5. 生成研究上下文
        rag_context = await self.rag.retrieve_with_context(query, top_k=5)
        kg_context = self.kg.to_prompt(max_triples=10)

        result["context"] = f"{rag_context}\n\n{kg_context}"

        return result

    async def answer(
        self,
        query: str,
        use_rag: bool = True,
        use_kg: bool = True
    ) -> str:
        """
        回答問題

        ‹1› 檢索相關資訊
        ‹2› 生成答案
        """
        context_parts = []

        if use_rag:
            rag_context = await self.rag.retrieve_with_context(query, top_k=5)
            if rag_context:
                context_parts.append(f"[檢索到的資訊]\n{rag_context}")

        if use_kg:
            kg_context = self.kg.to_prompt(max_triples=10)
            if kg_context:
                context_parts.append(kg_context)

        context = "\n\n".join(context_parts)

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "你是一個研究助理，請基於提供的上下文回答問題。如果上下文中沒有足夠的資訊，請說明。"
                },
                {
                    "role": "user",
                    "content": f"上下文：\n{context}\n\n問題：{query}"
                }
            ],
            temperature=0.7
        )

        return response.choices[0].message.content
```

---

## 7.7 章節總結

### 核心收穫

1. **搜尋層**
   - 多引擎整合（Google, Tavily, DuckDuckGo）
   - 結果聚合與去重
   - 容錯與回退機制

2. **擷取層**
   - 網頁內容瀏覽
   - 智能內容提取
   - PDF 解析

3. **檢索層**
   - 文件分塊策略
   - 向量索引
   - RAG 檢索

4. **知識圖譜**
   - 實體關係提取
   - 路徑查詢
   - 知識整合

### 檢查清單

- [ ] 實現多引擎搜尋整合
- [ ] 建立網頁瀏覽器
- [ ] 實現文件分塊器
- [ ] 建立向量索引
- [ ] 整合知識圖譜
- [ ] 測試完整研究流程

### 本章產出物

| 類型 | 內容 |
|------|------|
| **搜尋提供者** | SerperSearchProvider, TavilySearchProvider, DuckDuckGoSearchProvider |
| **瀏覽器** | WebBrowser, ContentExtractor |
| **RAG** | DocumentChunker, VectorIndex, RAGRetriever |
| **知識圖譜** | KnowledgeGraph, EntityRelationExtractor |
| **整合系統** | SearchRetrievalSystem |

---

## 7.8 下一章預告

**第 8 章：環境搭建與部署**

在下一章中，我們將進入工程實踐部分：

- 8B 到 72B 模型的部署策略
- vLLM 和 TensorRT-LLM 推理優化
- Docker 容器化部署
- 效能調優技巧

你將學會如何在生產環境中部署深度研究代理人。

---

## 本章程式碼

**GitHub 位置**：`code-examples/chapter-07/`

| 檔案 | 行數 | 說明 |
|------|------|------|
| `search_engine.py` | ~400 | 搜尋引擎整合 |
| `web_browser.py` | ~250 | 網頁瀏覽器 |
| `rag_retriever.py` | ~350 | RAG 檢索系統 |
| `knowledge_graph.py` | ~200 | 知識圖譜 |
| `requirements.txt` | - | 依賴清單 |
| `.env.example` | - | 環境變數範例 |
