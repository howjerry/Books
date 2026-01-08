# 第 7 章：搜尋與檢索引擎 - 程式碼範例

本目錄包含第 7 章「搜尋與檢索引擎」的完整程式碼範例。

## 檔案結構

```
chapter-07/
├── search_engine.py      # 多搜尋引擎整合
├── web_browser.py        # 網頁瀏覽與內容提取
├── rag_retriever.py      # RAG 檢索系統
├── knowledge_graph.py    # 知識圖譜實現
├── requirements.txt      # Python 依賴套件
├── .env.example          # 環境變數範例
└── README.md             # 本文件
```

## 快速開始

### 1. 安裝依賴

```bash
cd chapter-07
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入你的 API 金鑰
```

### 3. 執行示範

```bash
# 搜尋引擎示範
python search_engine.py --demo

# 執行搜尋
python search_engine.py -q "AI 晶片市場趨勢"

# 網頁瀏覽器示範
python web_browser.py --demo

# 瀏覽指定網頁
python web_browser.py --url "https://example.com"

# RAG 檢索系統示範
python rag_retriever.py --demo

# 知識圖譜示範
python knowledge_graph.py --demo
```

## 模組說明

### 搜尋引擎 (search_engine.py)

整合多個搜尋引擎的統一介面：

- **Serper**: Google Search API，高品質結果
- **Tavily**: AI 原生搜尋，自動提取關鍵內容
- **DuckDuckGo**: 免費搜尋，不需要 API 金鑰

```python
from search_engine import SearchManager, MockSearchProvider

# 創建搜尋管理器
manager = SearchManager()
manager.register_provider(MockSearchProvider(), set_default=True)

# 執行搜尋
results = await manager.search("AI 晶片", num_results=5)

# 多引擎搜尋（去重）
results = await manager.multi_search("AI 晶片", providers=["serper", "tavily"])
```

### 網頁瀏覽器 (web_browser.py)

網頁內容獲取與提取：

```python
from web_browser import WebBrowser, ContentExtractor

# 瀏覽網頁
browser = WebBrowser()
page = await browser.browse("https://example.com")

print(f"標題: {page.title}")
print(f"內容: {page.content[:500]}")
print(f"連結數: {len(page.links)}")

# 批次瀏覽
pages = await browser.batch_browse(urls, concurrency=5)

# 結構化提取
extractor = ContentExtractor()
structured = extractor.extract_structured(page.html)
```

### RAG 檢索器 (rag_retriever.py)

完整的 RAG（檢索增強生成）系統：

```python
from rag_retriever import RAGRetriever, SimpleEmbedder

# 創建 RAG 檢索器
rag = RAGRetriever(
    embedder=SimpleEmbedder(dimensions=128),
    chunk_size=500,
    chunk_overlap=50
)

# 添加文件
await rag.add_document(content, source_url="https://example.com")

# 檢索相關片段
results = await rag.retrieve("NVIDIA 市場份額", top_k=5)

# 生成上下文（用於 LLM）
context = await rag.retrieve_with_context("AI 晶片競爭")
```

### 知識圖譜 (knowledge_graph.py)

實體關係存儲與查詢：

```python
from knowledge_graph import KnowledgeGraph, Entity, Relation

# 創建知識圖譜
kg = KnowledgeGraph()

# 添加實體
nvidia = Entity("NVIDIA", "COMPANY", {"market_share": 0.8})
h100 = Entity("H100", "PRODUCT", {"type": "GPU"})
kg.add_entity(nvidia)
kg.add_entity(h100)

# 添加關係
kg.add_relation(Relation(nvidia, h100, "PRODUCES"))

# 查詢相鄰實體
neighbors = kg.get_neighbors(nvidia)

# 路徑查詢
path = kg.find_path(amd, cuda, max_depth=3)

# 統計資訊
stats = kg.get_statistics()
```

## 架構概覽

```
┌─────────────────────────────────────────────────────────────┐
│                     深度研究代理人                           │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐│
│  │  Serper   │  │  Tavily   │  │ DuckDuckGo│  │ WebBrowser││
│  │  (Google) │  │ (AI原生)  │  │   (免費)  │  │ (網頁獲取)││
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘│
│        │              │              │              │      │
│        └──────────────┼──────────────┼──────────────┘      │
│                       ▼                                    │
│              ┌─────────────────┐                          │
│              │  SearchManager  │                          │
│              │   (統一管理)    │                          │
│              └────────┬────────┘                          │
│                       │                                    │
│        ┌──────────────┼──────────────┐                    │
│        ▼              ▼              ▼                    │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐             │
│  │   RAG     │  │ Knowledge │  │  Content  │             │
│  │ Retriever │  │   Graph   │  │ Extractor │             │
│  └───────────┘  └───────────┘  └───────────┘             │
└─────────────────────────────────────────────────────────────┘
```

## 核心概念

### 1. 多引擎搜尋策略

```
查詢 ──▶ 並行搜尋 ──▶ 結果聚合 ──▶ 去重 ──▶ 排序
           │            │           │         │
           ▼            ▼           ▼         ▼
        Serper       Tavily     URL去重   相關度排序
        DuckDuckGo
```

### 2. RAG 工作流程

```
文件 ──▶ 分塊 ──▶ 嵌入 ──▶ 索引
                            │
查詢 ──▶ 嵌入 ──▶ 相似度搜尋 ──▶ 排序 ──▶ 上下文
```

### 3. 知識圖譜結構

```
實體 ──關係──▶ 實體
  │              │
  └──屬性        └──屬性
```

## 設定選項

### 搜尋引擎設定

| 參數 | 預設值 | 說明 |
|------|--------|------|
| num_results | 10 | 每次搜尋返回結果數 |
| country | tw | 搜尋地區 |
| language | zh-TW | 搜尋語言 |

### RAG 設定

| 參數 | 預設值 | 說明 |
|------|--------|------|
| chunk_size | 500 | 分塊大小（字符） |
| chunk_overlap | 50 | 分塊重疊（字符） |
| top_k | 5 | 返回相關片段數 |
| min_score | 0.3 | 最低相關度閾值 |

### 瀏覽器設定

| 參數 | 預設值 | 說明 |
|------|--------|------|
| timeout | 30.0 | 請求超時（秒） |
| max_content_length | 100000 | 最大內容長度 |
| concurrency | 5 | 批次瀏覽並發數 |

## 依賴套件

### 必需

| 套件 | 版本 | 用途 |
|------|------|------|
| aiohttp | ≥3.9.0 | 異步 HTTP 客戶端 |
| python-dotenv | ≥1.0.0 | 環境變數管理 |
| numpy | ≥1.24.0 | 向量運算 |

### 可選

| 套件 | 版本 | 用途 |
|------|------|------|
| openai | ≥1.3.0 | 嵌入生成（API） |
| duckduckgo-search | ≥4.0 | 免費搜尋 |

## 學習要點

完成本章後，你將掌握：

1. **多搜尋引擎整合**
   - 統一的搜尋介面設計
   - 結果聚合與去重策略
   - 容錯與回退機制

2. **網頁內容處理**
   - HTTP 請求與內容獲取
   - HTML 解析與純文字提取
   - 結構化資訊提取

3. **RAG 檢索系統**
   - 文件分塊策略
   - 向量索引與相似度搜尋
   - 上下文增強生成

4. **知識圖譜**
   - 實體和關係存儲
   - 圖查詢與路徑搜尋
   - 知識推理基礎

## 下一步

完成本章範例後，建議：

1. 嘗試整合真實的搜尋 API（Serper 或 Tavily）
2. 使用 OpenAI Embedding API 替換 SimpleEmbedder
3. 擴展知識圖譜支援更複雜的推理

## 相關章節

- **第 6 章**：長短時記憶管理（與 RAG 配合使用）
- **第 8 章**：報告生成引擎（使用檢索結果）
- **第 9 章**：完整代理人整合（系統整合）
