# 第 6 章：長短時記憶管理 - 程式碼範例

> 本目錄包含《深度研究代理人實戰》第 6 章的完整可運行程式碼。

---

## 快速開始

### 1. 建立虛擬環境

```bash
cd code-examples/chapter-06
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 檔案，填入你的 API Key
```

### 4. 執行

```bash
# 記憶管理系統示範
python memory_manager.py --demo

# 壓縮器示範
python compressor.py --demo

# 嵌入器示範
python embedder.py --demo
```

---

## 檔案說明

| 檔案 | 行數 | 說明 |
|------|------|------|
| `memory_manager.py` | ~600 | 統一記憶管理系統 |
| `compressor.py` | ~200 | 情節壓縮器 |
| `embedder.py` | ~200 | 嵌入生成器 |
| `requirements.txt` | - | Python 依賴清單 |
| `.env.example` | - | 環境變數範例 |
| `README.md` | - | 本文件 |

---

## 核心概念

### 三層記憶架構

```
┌─────────────────────────────────────────────────────────┐
│              工作記憶（Working Memory）                  │
│  容量：~8K tokens | 生命週期：單次交互                    │
│  用途：當前問題、最近思考、臨時變數                       │
└─────────────────────────────────────────────────────────┘
                          ↓ 溢出
┌─────────────────────────────────────────────────────────┐
│              情節記憶（Episodic Memory）                 │
│  容量：~32K tokens | 生命週期：單次任務                   │
│  用途：研究步驟歷程、思考-行動-觀察記錄                    │
└─────────────────────────────────────────────────────────┘
                          ↓ 壓縮
┌─────────────────────────────────────────────────────────┐
│              語義記憶（Semantic Memory）                 │
│  容量：無限 | 生命週期：永久                              │
│  用途：持久化知識、向量檢索、知識圖譜                      │
└─────────────────────────────────────────────────────────┘
```

### 記憶優先級

| 優先級 | 標記 | 說明 |
|--------|------|------|
| CRITICAL | 🔴 | 關鍵資訊，不可驅逐 |
| HIGH | 🟠 | 高優先級 |
| MEDIUM | 🟡 | 中等優先級 |
| LOW | ⚪ | 低優先級 |

### 壓縮級別

| 級別 | 保留細節 | 目標長度 | 適用場景 |
|------|---------|---------|---------|
| LIGHT | 80% | ~100 字 | 1 小時內的記憶 |
| MEDIUM | 50% | ~50 字 | 1-4 小時的記憶 |
| HEAVY | 核心結論 | ~20 字 | 4+ 小時的記憶 |

---

## 使用範例

### 工作記憶

```python
from memory_manager import WorkingMemory, MemoryPriority

# 創建工作記憶（8K tokens 容量）
working = WorkingMemory(max_tokens=8000)

# 添加關鍵資訊
working.add(
    content="研究問題：分析 AI 晶片市場趨勢",
    importance=1.0,
    priority=MemoryPriority.CRITICAL
)

# 添加中間結果
working.add(
    content="NVIDIA 市場份額約 80%",
    importance=0.9,
    priority=MemoryPriority.HIGH
)

# 搜尋相關記憶
results = working.search("市場份額")

# 生成 prompt
prompt = working.to_prompt()
print(prompt)
```

### 情節記憶

```python
from memory_manager import EpisodicMemory

# 創建情節記憶
episodic = EpisodicMemory(max_tokens=32000)

# 記錄研究步驟
episodic.add_episode(
    thought="需要了解市場規模",
    action={"tool_name": "web_search", "query": "AI chip market"},
    observation="市場規模約 500 億美元",
    importance=0.8
)

# 獲取最近的情節
recent = episodic.get_recent(5)

# 獲取高重要性情節
important = episodic.get_by_importance(min_importance=0.7)
```

### 語義記憶

```python
from memory_manager import SemanticMemory
from embedder import SimpleEmbedder

# 創建語義記憶
semantic = SemanticMemory()

# 設置嵌入器
embedder = SimpleEmbedder()
semantic.set_embedder(embedder.embed)

# 添加知識
semantic.add_knowledge(
    content="NVIDIA 在 AI 晶片市場佔據 80% 份額",
    source_episodes=[1, 2]
)

# 語義搜尋
results = semantic.search("市場領導者", limit=5)
for chunk, similarity in results:
    print(f"[{similarity:.2f}] {chunk.content}")
```

### 統一記憶管理器

```python
from memory_manager import UnifiedMemoryManager

# 創建統一管理器
memory = UnifiedMemoryManager(
    working_memory_tokens=8000,
    episodic_memory_tokens=32000
)

# 處理研究步驟
await memory.process_step(
    thought="分析市場數據",
    action={"tool_name": "analyze"},
    observation="發現三個主要趨勢...",
    importance=0.9
)

# 統一查詢
context = await memory.query(
    "市場趨勢",
    include_working=True,
    include_episodic=True,
    include_semantic=True
)

# 獲取統計
stats = memory.get_statistics()
print(f"工作記憶: {stats['working_memory']['utilization']*100:.1f}%")
print(f"情節記憶: {stats['episodic_memory']['utilization']*100:.1f}%")
```

---

## 執行範例

### 記憶管理系統示範

```
============================================================
🧠 記憶管理系統示範
============================================================

📍 1. 工作記憶示範
----------------------------------------
[工作記憶]
🔴 研究問題：分析 2024 年 AI 晶片市場
🟠 需要搜尋市場數據和主要廠商資訊
🟠 NVIDIA 市場份額約 80%

統計: {'item_count': 3, 'total_tokens': 156, 'utilization': 0.156}

📍 2. 情節記憶示範
----------------------------------------
[研究歷程]
[步驟 1]
思考：需要了解 AI 晶片市場的整體規模
行動：調用 web_search
觀察：市場規模約 500 億美元，年增長 30%

[步驟 2]
思考：已獲得市場規模，接下來分析主要競爭者
行動：調用 web_search
觀察：NVIDIA 80%，AMD 10%，Intel 5%

統計: {'episode_count': 2, 'compression_rate': 0.0, 'utilization': 0.012}

📍 3. 語義記憶示範
----------------------------------------
[知識庫]
• NVIDIA 在 AI 晶片市場佔據 80% 份額
• AMD 正在積極追趕，目前市場份額約 10%

統計: {'chunk_count': 2, 'total_sources': 3}
```

---

## 進階功能

### 漸進式壓縮

```python
from compressor import ProgressiveCompressor, CompressionLevel

compressor = ProgressiveCompressor()

# 根據記憶年齡自動選擇壓縮級別
result = await compressor.compress(
    content="原始內容...",
    age_hours=2.5  # 2.5 小時前的記憶 → MEDIUM 壓縮
)

print(f"壓縮比: {result.compression_ratio*100:.1f}%")
```

### 相似度計算

```python
from embedder import SimilarityCalculator

calc = SimilarityCalculator()

# 餘弦相似度
sim = calc.cosine_similarity(embedding1, embedding2)

# 找最相似的 K 個
top_k = calc.find_most_similar(
    query_embedding,
    candidate_embeddings,
    top_k=5
)
```

### 記憶垃圾回收

```python
from memory_manager import UnifiedMemoryManager

memory = UnifiedMemoryManager()

# 清理低優先級工作記憶
cleared = memory.working.clear(keep_critical=True)
print(f"清理了 {cleared} 個項目")
```

---

## 效能優化技巧

### 1. 批次嵌入

```python
# 單次 API 調用處理多個文本
embeddings = await embedder.batch_embed(texts, batch_size=100)
```

### 2. 嵌入快取

```python
embedder = EmbeddingGenerator(cache_enabled=True)
# 相同文本只會調用一次 API
```

### 3. 選擇性檢索

```python
# 只檢索需要的記憶層
context = await memory.query(
    query,
    include_working=True,    # 最近的上下文
    include_episodic=False,  # 跳過歷程
    include_semantic=True    # 相關知識
)
```

---

## 常見問題

### Q: 如何處理超長研究任務？

1. 設置更大的情節記憶容量
2. 降低壓縮觸發閾值
3. 使用更激進的壓縮策略

```python
episodic = EpisodicMemory(
    max_tokens=64000,              # 增加容量
    compression_threshold=0.6,     # 更早觸發壓縮
    window_size=5                  # 減少不壓縮的視窗
)
```

### Q: 如何提高語義檢索準確度？

1. 使用更大的嵌入模型
2. 調整相似度閾值
3. 增加知識片段數量

```python
semantic = SemanticMemory(
    embedding_dim=3072,            # 使用 text-embedding-3-large
    similarity_threshold=0.80      # 放寬去重閾值
)
```

### Q: 離線環境如何使用？

使用 SimpleEmbedder 替代 OpenAI 嵌入器：

```python
from embedder import SimpleEmbedder

embedder = SimpleEmbedder(dimensions=128)
semantic.set_embedder(embedder.embed)
```

---

## 延伸閱讀

- [第 5 章程式碼](../chapter-05/) - 工具調用與軌跡收集
- [第 7 章程式碼](../chapter-07/) - 搜尋與檢索引擎（待完成）
- [OpenAI Embeddings 文檔](https://platform.openai.com/docs/guides/embeddings)
- [向量資料庫比較](https://github.com/erikbern/ann-benchmarks)

---

**本章程式碼授權**：MIT License
