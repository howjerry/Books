# 第 6 章：Re-Ranking——二階段檢索的威力

> **本章任務：** 實作一個 Cross-Encoder Re-Ranker，將檢索精準度提升 30%。

---

## 學習目標

完成本章後，你將能夠：

- [ ] 理解二階段檢索架構的設計原理
- [ ] 區分 Bi-Encoder（Embedding）與 Cross-Encoder（Re-Ranker）的差異
- [ ] 實作 Cross-Encoder Re-Ranker
- [ ] 量化評估 Re-Ranking 的成本效益
- [ ] 根據延遲與精準度需求調整候選數量

---

## 核心產出物

- `reranker.py` - Re-Ranking Pipeline 實作
- `two_stage_retrieval.py` - 二階段檢索系統
- `rerank_benchmark.py` - Re-Ranking 效能評估
- `latency_vs_precision.png` - 延遲與精準度權衡圖

---

## 章節內容

<!-- TODO: 撰寫完整章節內容 -->

### 6.1 為什麼需要二階段檢索？

### 6.2 Bi-Encoder vs Cross-Encoder

### 6.3 實作 Re-Ranking Pipeline

### 6.4 選擇 Re-Ranker 模型

### 6.5 調優候選數量（Top-N）

### 6.6 成本效益分析

### 6.7 整合到 AskBot

### 6.8 本章小結

---

## 下一步

Re-Ranking 專注於語義相關性，但有時候關鍵字精確匹配也很重要。第 7 章將介紹 Hybrid Search，融合兩種方法的優點。
