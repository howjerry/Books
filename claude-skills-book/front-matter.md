# 前言

## 關於本書

當我在 2024 年首次接觸 Claude Code Skills 時，我立刻意識到這項技術將徹底改變軟體工程師的工作方式。不同於傳統的自動化工具需要大量的設定和維護，Skills 讓 AI 成為真正的協作夥伴——它能理解自然語言指令、適應變化的環境，並在遇到問題時自主找到解決方案。

這本書的誕生源於一個實際需求：我的團隊需要建立一套完整的網站監控測試系統。在傳統做法中，這需要數週的開發時間、大量的測試腳本維護，以及專門的測試工程師。但使用 Claude Skills 和 Stagehand，我們在幾天內就完成了原型，並且系統具有令人驚訝的穩定性和適應性。

這個經驗讓我深刻體會到：AI 自動化不是替代工程師，而是讓工程師能專注在真正重要的問題上。本書將帶領你走過這個旅程，從基礎概念到生產部署，每一步都基於實際專案經驗。

## 本書結構

本書分為三個部分，共 10 章：

**Part 1: 基礎篇**（第 1-3 章）建立基礎知識，讓你能夠創建並運行第一個 Skill。即使你沒有 AI 背景，也能快速上手。

**Part 2: 核心技術篇**（第 4-7 章）深入各個實務場景，從瀏覽器自動化到數據處理，從 API 測試到進階組合技巧。每章都包含完整的生產級代碼範例。

**Part 3: 生產部署篇**（第 8-10 章）聚焦在企業級應用，包括 CI/CD 整合、完整的 WebGuard 測試系統架構，以及企業部署的安全與監控考量。

全書以建立 **WebGuard 測試系統**為主軸。這是一個真實的、生產就緒的專案，會隨著章節逐步完善。你不僅學習 Skills 開發，更能理解如何將這些知識應用在實際專案中。

## 如何使用本書

### 給不同背景的讀者

**如果你是全端工程師**：本書的專案導向方法會讓你感到熟悉。你可以按順序閱讀，逐步建立完整系統。

**如果你是後端工程師**：第 5 章（數據處理）和第 6 章（API 測試）可能是最佳起點。瀏覽器自動化可以稍後學習。

**如果你是前端工程師**：第 4 章的 Stagehand 瀏覽器自動化會立即吸引你。你可以先專注在這部分，再回頭學習其他場景。

**如果你是 DevOps 工程師**：第 8-10 章的 CI/CD 整合和企業部署是核心內容，但建議先閱讀第 1-3 章了解基礎。

### 學習建議

1. **動手實作**：每章都包含完整的代碼範例。最好的學習方式是實際運行並修改這些代碼。

2. **循序漸進**：雖然各章可以獨立閱讀，但建議至少完成前三章再跳到特定主題。

3. **實驗精神**：Skills 的強大之處在於適應性。嘗試修改範例，看看 AI 如何應對不同情況。

4. **建立專案**：考慮同時進行一個自己的專案。將學到的技巧應用在實際問題上，能大幅加速學習。

### 代碼慣例

本書使用以下慣例：

- **粗體**：重要概念和術語首次出現時
- `等寬字體`：代碼、命令、檔案名稱
- 💡：提示和最佳實踐
- ⚠️：常見陷阱和注意事項
- 🔍：深入探討的技術細節

### 代碼範例

所有代碼範例都可以在本書的 GitHub 儲存庫中找到：
https://github.com/manning/claude-skills-in-action

每個範例都：
- ✓ 經過完整測試
- ✓ 包含詳細註解
- ✓ 可直接在生產環境使用
- ✓ 遵循產業最佳實踐

### 前置需求

本書假設你具備：

- **程式語言**：基本的 Python 或 JavaScript 知識
- **命令行**：熟悉終端機操作
- **版本控制**：了解 Git 基本指令
- **Web 概念**：理解 HTTP、API、HTML 基礎

不需要：
- ✗ AI 或機器學習背景
- ✗ 測試自動化經驗
- ✗ DevOps 專業知識

### 開發環境

推薦配置：
- **作業系統**：macOS、Linux、或 Windows with WSL2
- **Python**：3.10 或更新版本
- **Node.js**：18.0 或更新版本
- **記憶體**：最少 8GB RAM（建議 16GB）
- **儲存空間**：10GB 可用空間

詳細的環境設置說明請參閱第 2 章。

## 線上資源

### 官方資源
- **Claude Code 官方文檔**：https://docs.anthropic.com/claude/docs
- **Skills GitHub**：https://github.com/anthropics/skills
- **Stagehand 文檔**：https://docs.stagehand.dev

### 本書資源
- **代碼儲存庫**：https://github.com/manning/claude-skills-in-action
- **作者論壇**：https://forums.manning.com/
- **勘誤表**：https://manning.com/books/claude-skills-in-action

### 社群資源
- **Discord 社群**：與其他讀者討論和分享經驗
- **每月網路研討會**：深入探討進階主題
- **範例專案庫**：社群貢獻的 Skills 範例

## 關於作者

[Author Name] 是一位資深軟體工程師，在測試自動化和 AI 系統整合領域有超過 10 年的經驗。他目前擔任 [Company] 的技術主管，領導團隊建立大規模的自動化測試基礎設施。

作為早期採用者，他從 Claude Code 發布之初就開始探索其可能性，並在多個生產專案中成功應用。他經常在技術會議上分享經驗，並為多個開源專案做出貢獻。

他相信 AI 工具應該增強而非取代人類的創造力，這個理念貫穿本書的每一頁。

## 致謝

撰寫一本技術書籍是一項團隊努力的成果。首先，我要感謝 Manning Publications 的整個團隊，特別是我的編輯 [Editor Name]，他的專業建議讓本書更加清晰和易讀。

感謝技術審稿團隊：[Reviewer Names]。他們細緻的審查和寶貴的反饋大幅提升了本書的品質。所有剩餘的錯誤都是我個人的責任。

特別感謝 Anthropic 團隊開發了 Claude 和 Skills 這樣出色的工具，以及 Browserbase 團隊創造的 Stagehand 框架。沒有他們的創新工作，這本書不可能存在。

感謝早期讀者社群，他們的回饋幫助塑造了本書的方向和內容。你們的提問和建議讓我更清楚如何解釋複雜概念。

感謝我的團隊同事，特別是 [Team Members]，與他們一起在實際專案中探索 Skills 的過程，成為本書許多範例的靈感來源。

最後，感謝我的家人在漫長的寫作過程中給予的支持和耐心。這本書獻給我的 [Family Members]，謝謝你們一直相信我。

## 關於技術審稿者

本書由以下專家審閱：

[List of technical reviewers with brief bios]

他們的專業知識涵蓋測試自動化、AI 系統、DevOps、和軟體架構等多個領域。他們的審查確保了本書的技術準確性和實用價值。

## 關於封面插圖

[Cover illustration description and acknowledgment]

---

## 序言（Foreword）

*By [Industry Leader Name], [Title] at [Company]*

The software industry is at an inflection point. For decades, we've automated repetitive tasks through scripts and tools, but true intelligent automation remained elusive. Claude Code Skills represents a fundamental shift in how we think about automation.

What makes Skills revolutionary isn't just the technology—it's the democratization of AI automation. You no longer need a PhD in machine learning or years of experience in test automation to build sophisticated, adaptive systems. As this book demonstrates, a software engineer with basic Python knowledge can create production-ready automation that rivals specialized systems built by teams of experts.

I've watched [Author] apply these techniques in real-world scenarios, and the results are impressive. The WebGuard system you'll build throughout this book isn't a toy example—it's the kind of infrastructure that powers critical business operations. The approaches taught here are battle-tested and production-proven.

What I appreciate most about this book is its pragmatic approach. Rather than focusing on theoretical possibilities, [Author] shows you exactly how to build, deploy, and maintain AI-powered automation in enterprise environments. The attention to security, monitoring, and scalability reflects real-world concerns that are often overlooked in technical literature.

As you work through this book, you're not just learning a new tool—you're gaining a new way of thinking about automation. The skills you develop here will remain relevant as the field evolves, because they're grounded in fundamental principles of system design and AI integration.

Whether you're building test automation, data pipelines, or development tools, the techniques in this book will transform how you approach these challenges. I'm excited to see what you'll build.

[Signature]

---

*Ready to begin your journey into AI-powered automation? Turn to Chapter 1 and let's get started!*
