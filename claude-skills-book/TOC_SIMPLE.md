# Claude Code Skills 實戰指南 - 簡化目錄

> **技術書籍** | AI 自動化 | Python + TypeScript
> **預計閱讀時間**: 15-20 小時

---

## 前言 - Preface

快速了解本書的寫作動機、目標讀者、學習路徑與使用方式。

---

## Part 1: 基礎篇

### 第 1 章：AI 自動化入門與 Claude Skills 概述

- 1.1 自動化的演進：從腳本到智能
- 1.2 認識 Claude Code Skills
- 1.3 本書的主軸：WebGuard 測試系統
- 1.4 Skills vs. 傳統工具：實戰對比
- 1.5 實際應用案例
- 1.6 開始你的 Skills 之旅
- 1.7 下一章預告

### 第 2 章：開發環境設置與第一個 Skill

- 2.1 開發環境設置
- 2.2 創建 WebGuard 專案
- 2.3 創建第一個 Skill
- 2.4 與 Claude 整合
- 2.5 完善與調試
- 2.6 本章總結

---

## Part 2: 核心技術篇

### 第 3 章：Skills 核心概念與 SKILL.md 語法

- 3.1 SKILL.md 完整語法規範
- 3.2 三層漸進式揭露系統詳解
- 3.3 Skills 生命週期
- 3.4 參數定義與驗證
- 3.5 錯誤處理策略
- 3.6 Skills 開發最佳實踐

### 第 4 章：Stagehand 瀏覽器自動化實戰

- 4.1 認識 Stagehand
- 4.2 Stagehand 四大核心 API
- 4.3 實作登入測試 Skill
- 4.4 處理複雜 UI 互動
- 4.5 自愈機制與錯誤恢復
- 4.6 WebGuard 瀏覽器測試模組
- 4.7 本章總結
- 4.8 最佳實踐與性能調優

### 第 5 章：數據與文件處理自動化

- 5.1 Excel/CSV 數據處理 Skills
- 5.2 PDF 文件處理與驗證
- 5.3 數據驅動測試實踐
- 5.4 數據清洗與轉換
- 5.5 與 WebGuard 測試系統整合
- 5.6 最佳實踐與安全考量
- 5.7 本章總結

### 第 6 章：API 測試與整合驗證

- 6.1 REST API 測試基礎
- 6.2 GraphQL API 測試
- 6.3 API 契約測試（Contract Testing）
- 6.4 API Mock 與測試隔離
- 6.5 性能與負載測試
- 6.6 整合到 Claude Code Skill
- 6.7 與 WebGuard 系統整合
- 6.8 最佳實踐與安全考量
- 6.9 本章總結

### 第 7 章：Skills 進階模式與組合技巧

- 7.1 為什麼需要 Skill 編排？
- 7.2 Skill 編排器（SkillOrchestrator）
- 7.3 動態參數傳遞（Data Flow）
- 7.4 錯誤處理與重試策略
- 7.5 條件執行與分支邏輯
- 7.6 實戰案例：端到端測試工作流
- 7.7 最佳實踐與設計模式
- 7.8 本章總結

---

## Part 3: 生產部署篇

### 第 8 章：測試自動化與 CI/CD 整合

- 8.1 CI/CD 基礎：為什麼需要持續測試？
- 8.2 GitHub Actions 整合
- 8.3 GitLab CI/CD 整合
- 8.4 Jenkins 整合
- 8.5 測試報告與可視化
- 8.6 定時任務與健康監控
- 8.7 失敗通知與告警
- 8.8 最佳實踐
- 8.9 本章總結

### 第 9 章：完整測試系統架構（WebGuard）

- 9.1 WebGuard 系統概述
- 9.2 數據庫設計（PostgreSQL）
- 9.3 編排層實現
- 9.4 執行層實現
- 9.5 存儲層實現
- 9.6 報告層實現
- 9.7 API 網關（FastAPI）
- 9.8 部署架構（Docker Compose）
- 9.9 高可用性設計
- 9.10 本章總結

### 第 10 章：企業部署、安全與 MCP 生態

- 10.1 安全性最佳實踐
- 10.2 Kubernetes 生產環境部署
- 10.3 MCP（Model Context Protocol）整合
- 10.4 生產就緒清單
- 10.5 未來展望

---

## 附錄

### 附錄 A：MCP Protocol 參考

完整的 MCP 協議規範、Server 實作範例、安全性最佳實踐與故障排除指南。

### 附錄 C：測試工具對比表

詳細對比 Stagehand、Playwright、Selenium、Puppeteer、Cypress 等工具的技術特性、性能、成本與適用場景。

### 附錄 D：Skills 開發最佳實踐檢查清單

涵蓋設計、實作、測試、安全、性能、CI/CD、部署等各階段的完整檢查清單。

---

## 📚 章節統計

| 部分 | 章節數 | 主要內容 |
|------|--------|----------|
| **基礎篇** | 2 章 | Skills 概念、環境設置、第一個 Skill |
| **核心技術篇** | 5 章 | SKILL.md 語法、Stagehand、數據處理、API 測試、編排模式 |
| **生產部署篇** | 3 章 | CI/CD、完整系統架構、企業部署與安全 |
| **附錄** | 3 個 | MCP 協議、工具對比、最佳實踐清單 |

**總計**: 10 章 + 前言 + 3 個附錄

---

## 🎯 學習路徑建議

### 🚀 快速入門（2-3 天）
**閱讀**: 前言 + 第 1-4 章
**目標**: 理解 Skills 核心概念，完成第一個瀏覽器自動化測試

### 📚 完整掌握（1-2 週）
**閱讀**: 前言 + 第 1-8 章
**目標**: 掌握 Skills 開發完整流程，整合 CI/CD

### 🎓 生產部署（2-4 週）
**閱讀**: 全書 + 所有附錄
**目標**: 部署完整的 WebGuard 系統到生產環境

---

## 🔗 配套資源

- **代碼倉庫**: https://github.com/[username]/webguard-skills
- **Claude Skills 文檔**: https://docs.anthropic.com/claude/docs/skills
- **Stagehand 文檔**: https://docs.stagehand.dev
- **MCP 協議**: https://modelcontextprotocol.io

---

**版本**: 1.0 | **更新日期**: 2025-11-08 | **作者**: Claude
