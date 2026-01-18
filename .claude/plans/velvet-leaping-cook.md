# RAG in Action 完成計畫

## 專案概覽

**目標**：完成《RAG in Action: 打造精準的企業級 AI 搜尋系統》全書撰寫

**現況**：
- 13 章框架已建立（標題、學習目標、產出物清單）
- 前言已完成
- 所有章節內容尚未撰寫（只有 `<!-- TODO -->` 標記）
- 缺少 `code-examples/`、`diagrams/`、`CLAUDE.md`

**預期產出**：~136,000 字 + 完整可運行程式碼

---

## 執行計畫

### Phase 1：基礎建設（Ch1-3）

| 任務 | 說明 |
|------|------|
| **Ch1** 傳統資訊檢索 | 實作 BM25 引擎，演示詞彙鴻溝問題 |
| **Ch2** 語義搜尋 | Embedding 視覺化，部署 Qdrant |
| **Ch3** RAG MVP | 整合 Pipeline，完成 AskBot v1.0 |

**產出檔案**：
- `code-examples/chapter-01/search_engine_v1.py`
- `code-examples/chapter-02/semantic_search_engine.py`
- `code-examples/chapter-03/rag_v1.py`, `askbot_demo.py`

### Phase 2：精準度工程前半（Ch4-5）

| 任務 | 說明 |
|------|------|
| **Ch4** Chunking 策略 | 5 種策略實作與評估 |
| **Ch5** Embedding 選型 | 10 模型 Benchmark |

### Phase 3：精準度工程後半（Ch6-7）

| 任務 | 說明 |
|------|------|
| **Ch6** Re-Ranking | 二階段檢索，精準度提升 30% |
| **Ch7** Hybrid Search | BM25 + Vector，AskBot v2.0 |

### Phase 4：生產級系統（Ch8-10）

| 任務 | 說明 |
|------|------|
| **Ch8** Prompt Engineering | 5 種範本 + A/B 測試 |
| **Ch9** 監控系統 | Prometheus + Grafana |
| **Ch10** 部署架構 | K8s + 快取，AskBot v3.0 |

### Phase 5：持續優化（Ch11-13）

| 任務 | 說明 |
|------|------|
| **Ch11** 回饋收集 | 收集 API + UI |
| **Ch12** 評估框架 | 測試集 + A/B 測試 |
| **Ch13** 持續學習 | Airflow DAG，AskBot v4.0 |

---

## 每章撰寫規範

### 結構模板

```
1. 開場場景（500-800 字）
   - 企業真實問題
   - 角色代入：「你是...」

2. 學習目標（5-7 項）
   - checkbox 格式
   - 動詞開頭

3. 技術內容（6-10 小節）
   - 完整可執行程式碼
   - ‹1›, ‹2› 標記關鍵行
   - 每章至少 3 個 Mermaid 圖

4. 章節總結 + 下一章預告
```

### 字數目標

| 章節 | 目標字數 |
|------|----------|
| Ch1-Ch3 | 各 10,000 字 |
| Ch4, Ch8, Ch10 | 各 12,000 字 |
| 其他章節 | 各 10,000 字 |

---

## 待建立資源

### 1. CLAUDE.md（書籍撰寫指南）

位置：`/mnt/d/Books/rag-in-action/CLAUDE.md`

### 2. code-examples/ 目錄

```
code-examples/
├── chapter-01/
│   ├── search_engine_v1.py
│   └── vocabulary_gap_demo.py
├── chapter-02/
│   ├── embedding_visualizer.py
│   ├── semantic_search_engine.py
│   └── docker-compose.yml
├── chapter-03/
│   ├── rag_v1.py
│   ├── prompt_templates.py
│   └── askbot_demo.py
...（共 13 章）
└── askbot/          # 完整專案
```

### 3. diagrams/ 目錄

- 每章 3+ 個 Mermaid 圖表
- 包含架構圖、流程圖、對比圖

---

## 關鍵檔案

| 檔案 | 用途 |
|------|------|
| `manuscript/chapters/chapter-01.md` | 第一章（基礎）|
| `manuscript/chapters/chapter-03.md` | RAG MVP（核心）|
| `manuscript/chapters/chapter-07.md` | Hybrid Search（AskBot v2.0）|
| `manuscript/chapters/chapter-10.md` | 部署（AskBot v3.0）|
| `manuscript/chapters/chapter-13.md` | 持續學習（AskBot v4.0）|

---

## 驗證方式

1. **程式碼測試**：每章程式碼可獨立執行
2. **連貫性檢查**：AskBot 版本演進合理
3. **風格檢查**：符合 Manning "in Action" 規範
4. **字數檢查**：各章達到目標字數

---

## 執行順序

**一次完成全部 13 章**

1. 建立 `CLAUDE.md` 撰寫指南
2. 建立 `code-examples/` 目錄結構
3. 撰寫 Ch1-3（基礎建設篇）
4. 撰寫 Ch4-7（精準度工程篇）
5. 撰寫 Ch8-10（生產級系統篇）
6. 撰寫 Ch11-13（持續優化篇）
7. 全書品質檢查
