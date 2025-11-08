# Claude Code Skills 技術書 - 章節交叉引用指南

## 設計原則

1. **前向引用**：從基礎章節指向進階內容
2. **後向引用**：從進階章節回溯基礎概念
3. **平行引用**：相關主題間的橫向連接
4. **實作引用**：從理論到實作的連接

## 章節關係圖

```
Chapter 1 (概念) ─────────┬─────→ Chapter 2 (入門)
                          │
                          ├─────→ Chapter 3 (核心概念)
                          │
                          └─────→ Chapter 4-10 (實作)

Chapter 2 (入門) ─────────→ Chapter 3 (深入 Skills)
                          └─────→ Chapter 4 (Stagehand)

Chapter 3 (Skills 核心) ──┬─────→ Chapter 4 (瀏覽器自動化)
                          ├─────→ Chapter 5 (數據處理)
                          ├─────→ Chapter 6 (API 測試)
                          └─────→ Chapter 7 (進階模式)

Chapter 4 (Stagehand) ────┬─────→ Chapter 7 (編排)
                          ├─────→ Chapter 8 (CI/CD)
                          └─────→ Chapter 9 (系統架構)

Chapter 7 (進階模式) ─────┬─────→ Chapter 8 (測試整合)
                          └─────→ Chapter 9 (架構設計)

Chapter 8 (CI/CD) ────────→ Chapter 9 (完整系統)
                          └─────→ Chapter 10 (企業部署)

Chapter 9 (系統架構) ─────→ Chapter 10 (部署與安全)
```

## 關鍵交叉引用點

### Chapter 1 → 其他章節

| 位置 | 引用目標 | 引用文本 |
|------|---------|---------|
| 1.2.2 Skills 架構 | Chapter 3.1 | "SKILL.md 語法的完整規範，詳見 **Chapter 3.1**" |
| 1.3.2 WebGuard 演進 | Chapter 2.2 | "如何建立基礎架構，參見 **Chapter 2.2**" |
| 1.3.3 WebGuard 架構 | Chapter 9.1 | "完整系統架構詳解於 **Chapter 9.1**" |
| 1.4 Skills vs 傳統 | Chapter 4.1 | "Stagehand 實作範例見 **Chapter 4.1**" |

### Chapter 2 → 其他章節

| 位置 | 引用目標 | 引用文本 |
|------|---------|---------|
| 2.3 創建第一個 Skill | Chapter 3.2 | "深入了解 SKILL.md 語法，參見 **Chapter 3.2**" |
| 2.4 測試 Skill | Chapter 8.2 | "CI/CD 整合測試見 **Chapter 8.2**" |
| 2.5 常見問題 | Chapter 3.6 | "錯誤處理最佳實踐詳見 **Chapter 3.6**" |

### Chapter 3 → 其他章節

| 位置 | 引用目標 | 引用文本 |
|------|---------|---------|
| 3.1 SKILL.md 語法 | Chapter 4.3 | "瀏覽器測試 Skill 實作見 **Chapter 4.3**" |
| 3.3 參數驗證 | Chapter 5.3 | "數據驗證進階技巧見 **Chapter 5.3**" |
| 3.5 最佳實踐 | Chapter 7 | "Skills 編排與組合詳見 **Chapter 7**" |
| 3.6 錯誤處理 | Chapter 8.3 | "生產環境錯誤追蹤見 **Chapter 8.3**" |

### Chapter 4 → 其他章節

| 位置 | 引用目標 | 引用文本 |
|------|---------|---------|
| 4.2 Stagehand API | Chapter 7.2 | "結合多個 Skills 的編排見 **Chapter 7.2**" |
| 4.5 自愈機制 | Chapter 9.4 | "系統級容錯設計見 **Chapter 9.4**" |
| 4.6 WebGuard 模組 | Chapter 9.2 | "完整架構實作詳見 **Chapter 9.2**" |
| 4.8 性能調優 | Chapter 10.3 | "生產環境性能優化見 **Chapter 10.3**" |

### Chapter 5 → 其他章節

| 位置 | 引用目標 | 引用文本 |
|------|---------|---------|
| 5.2 Excel 處理 | Chapter 7.3 | "數據處理工作流編排見 **Chapter 7.3**" |
| 5.4 PDF 生成 | Chapter 9.5 | "報告系統架構見 **Chapter 9.5**" |

### Chapter 6 → 其他章節

| 位置 | 引用目標 | 引用文本 |
|------|---------|---------|
| 6.2 API 測試 | Chapter 8.4 | "API 測試 CI/CD 整合見 **Chapter 8.4**" |
| 6.3 認證處理 | Chapter 10.2 | "企業安全方案見 **Chapter 10.2**" |

### Chapter 7 → 其他章節

| 位置 | 引用目標 | 引用文本 |
|------|---------|---------|
| 7.2 Skills 編排 | Chapter 9.3 | "Celery 分散式任務見 **Chapter 9.3**" |
| 7.3 狀態管理 | Chapter 9.6 | "PostgreSQL 設計詳見 **Chapter 9.6**" |

### Chapter 8 → 其他章節

| 位置 | 引用目標 | 引用文本 |
|------|---------|---------|
| 8.2 GitHub Actions | Chapter 10.4 | "生產環境部署見 **Chapter 10.4**" |
| 8.3 測試報告 | Chapter 9.5 | "Allure 整合詳見 **Chapter 9.5**" |

### Chapter 9 → 其他章節

| 位置 | 引用目標 | 引用文本 |
|------|---------|---------|
| 9.1 四層架構 | Chapter 10.1 | "Kubernetes 部署見 **Chapter 10.1**" |
| 9.2 執行層 | Chapter 3-6 | "各類 Skills 實作見 **Chapters 3-6**" |

### Chapter 10 → 其他章節

| 位置 | 引用目標 | 引用文本 |
|------|---------|---------|
| 10.2 安全方案 | Chapter 3.6.7 | "Skills 安全設計見 **Chapter 3.6.7**" |
| 10.3 性能優化 | Chapter 4.8 | "Stagehand 優化技巧見 **Chapter 4.8**" |

## 附錄交叉引用

### 附錄 A (MCP Protocol)
- 引用自: Chapter 1.2.3, Chapter 3.4, Chapter 10.5
- 引用到: MCP 官方文檔

### 附錄 B (Docker/K8s 配置)
- 引用自: Chapter 9.7, Chapter 10.1
- 引用到: 配置範本 GitHub repo

### 附錄 C (測試工具對比)
- 引用自: Chapter 1.4, Chapter 4.1
- 引用到: 各工具官方文檔

### 附錄 D (最佳實踐清單)
- 引用自: Chapter 3.5, Chapter 7.4, Chapter 10.6
- 引用到: GitHub checklist template

## 引用格式規範

### 標準格式
```markdown
> 💡 **相關內容**：關於 [主題]，詳見 **Chapter X.Y**：[小標題]

> 📖 **進階閱讀**：想深入了解 [主題]？參閱 **Chapter X**

> ⚠️ **注意**：在實作前建議先閱讀 **Chapter X.Y** 的 [主題]
```

### 內聯引用
```markdown
...（關於這個主題的更多細節，參見 **Chapter X.Y**）...
```

### 回顧引用
```markdown
> 🔄 **回顧**：如需複習 [概念]，返回 **Chapter X.Y**
```

## 實施檢查清單

- [ ] Chapter 1: 添加 4+ 前向引用
- [ ] Chapter 2: 添加 3+ 前向引用
- [ ] Chapter 3: 添加 5+ 前向引用
- [ ] Chapter 4: 添加 4+ 前向引用
- [ ] Chapter 5: 添加 3+ 前向引用
- [ ] Chapter 6: 添加 3+ 前向引用
- [ ] Chapter 7: 添加 4+ 前向引用
- [ ] Chapter 8: 添加 3+ 前向引用
- [ ] Chapter 9: 添加 4+ 前向引用
- [ ] Chapter 10: 添加 3+ 後向引用
- [ ] 驗證所有引用的章節和小節確實存在
- [ ] 確保引用文本清晰描述目標內容

## 效果評估

添加交叉引用後應達成：
1. ✅ 讀者能輕鬆找到相關內容
2. ✅ 學習路徑清晰明確
3. ✅ 減少重複說明
4. ✅ 提升專業性和可讀性
