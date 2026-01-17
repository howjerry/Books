# 第 3 章：RAG 的最小可行版本——5 行程式碼實現檢索增強生成

> **本章任務：** 整合檢索與生成，打造第一個能回答問題的 AI 助理。

---

## 學習目標

完成本章後，你將能夠：

- [ ] 實作一個端到端的 RAG 系統
- [ ] 理解 RAG 的核心架構（Retrieve → Augment → Generate）
- [ ] 設計有效的 Prompt 將檢索結果注入 LLM
- [ ] 實作來源追蹤，讓使用者能驗證答案可信度
- [ ] 理解 RAG 相比純 LLM 的優勢與適用場景

---

## 核心產出物

- `rag_v1.py` - RAG Pipeline 原型
- `prompt_templates.py` - 基礎 Prompt 範本
- `source_tracker.py` - 來源追蹤模組
- `askbot_demo.py` - AskBot 第一版演示

---

## 章節內容

<!-- TODO: 撰寫完整章節內容 -->

### 3.1 RAG 架構概覽

### 3.2 實作最簡單的 RAG Pipeline

### 3.3 Prompt Engineering 基礎

### 3.4 來源追蹤與可信度

### 3.5 RAG vs 純 LLM：何時使用哪個？

### 3.6 AskBot v1.0：我們的第一個成果

### 3.7 本章小結

---

## 下一步

基礎版 RAG 已經可以運作，但精準度可能不盡人意。在第二部分，我們將深入精準度工程，大幅提升搜尋品質。
