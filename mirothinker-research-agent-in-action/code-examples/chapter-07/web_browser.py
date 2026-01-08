#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 7 章：搜尋與檢索引擎
網頁瀏覽器實現

這個模組實現了網頁內容獲取與提取：
1. HTTP 請求與內容獲取
2. HTML 解析與純文字提取
3. 結構化內容提取

使用方式：
    python web_browser.py --demo
    python web_browser.py --url "https://example.com"
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# 資料結構
# =============================================================================

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
            "char_count": self.char_count,
            "link_count": len(self.links),
            "image_count": len(self.images),
            "fetched_at": self.fetched_at.isoformat(),
            "status_code": self.status_code
        }


# =============================================================================
# 網頁瀏覽器
# =============================================================================

class WebBrowser:
    """
    網頁瀏覽器

    ‹1› 獲取網頁內容
    ‹2› 提取純文字
    ‹3› 處理各種格式
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
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    allow_redirects=True
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
                        return WebPage(
                            url=url,
                            title="PDF 文件",
                            content="PDF 解析需要額外套件（PyMuPDF）",
                            status_code=status_code,
                            metadata={"content_type": "application/pdf"}
                        )

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
        html_clean = re.sub(r'<!--.*?-->', '', html_clean, flags=re.DOTALL)

        # 提取純文字
        text = re.sub(r'<[^>]+>', ' ', html_clean)
        text = self._decode_html_entities(text)
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
            links=links[:50],
            images=images[:20],
            metadata={"content_type": "text/html"}
        )

    def _decode_html_entities(self, text: str) -> str:
        """解碼 HTML 實體"""
        entities = {
            "&nbsp;": " ",
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&#39;": "'",
            "&apos;": "'",
        }
        for entity, char in entities.items():
            text = text.replace(entity, char)
        return text

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


# =============================================================================
# 內容提取器
# =============================================================================

class ContentExtractor:
    """
    智能內容提取器

    ‹1› 識別主要內容區域
    ‹2› 過濾廣告和導航
    ‹3› 保留結構化資訊
    """

    CONTENT_PATTERNS = [
        r'<article[^>]*>(.*?)</article>',
        r'<main[^>]*>(.*?)</main>',
        r'class="[^"]*(?:article|content|main|post|entry|story)[^"]*"[^>]*>(.*?)</div>',
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

        return self._clean_text(html)

    def _find_main_content(self, html: str) -> Optional[str]:
        """識別主要內容區域"""
        for pattern in self.CONTENT_PATTERNS:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        return None

    def _clean_text(self, html: str) -> str:
        """清理並提取純文字"""
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;', '"', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_structured(self, html: str) -> Dict[str, Any]:
        """提取結構化資訊"""
        result = {
            "title": "",
            "headings": [],
            "paragraphs": [],
            "lists": []
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
            if len(text) > 20:
                result["paragraphs"].append(text)

        return result


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範瀏覽功能"""
    print("=" * 60)
    print("🌐 網頁瀏覽器示範")
    print("=" * 60)

    browser = WebBrowser()
    extractor = ContentExtractor()

    # 測試 URL
    test_url = "https://httpbin.org/html"

    print(f"\n📍 瀏覽: {test_url}")
    print("-" * 40)

    page = await browser.browse(test_url)

    print(f"標題: {page.title}")
    print(f"狀態碼: {page.status_code}")
    print(f"內容長度: {page.char_count} 字符")
    print(f"連結數: {len(page.links)}")
    print(f"圖片數: {len(page.images)}")

    print(f"\n內容預覽:")
    print(page.content[:500] + "..." if len(page.content) > 500 else page.content)

    # 結構化提取
    if page.html:
        print("\n" + "-" * 40)
        print("📋 結構化提取")
        structured = extractor.extract_structured(page.html)
        print(f"標題: {structured['title']}")
        print(f"標題數: {len(structured['headings'])}")
        print(f"段落數: {len(structured['paragraphs'])}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="網頁瀏覽器")
    parser.add_argument("--demo", action="store_true", help="執行示範")
    parser.add_argument("--url", type=str, help="要瀏覽的 URL")

    args = parser.parse_args()

    if args.url:
        async def browse_url():
            browser = WebBrowser()
            page = await browser.browse(args.url)
            print(f"標題: {page.title}")
            print(f"內容長度: {page.char_count} 字符")
            print(f"\n{page.content[:1000]}...")

        asyncio.run(browse_url())
    else:
        asyncio.run(demo())


if __name__ == "__main__":
    main()
