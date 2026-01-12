# Context Engineering
## AI 時代的開發者生存指南

> 從消費者到生產者：掌握 LLM 的基礎原理，駕馭而非被動接受 AI 工具的演進

---

## 書籍資訊

**書名（中文）：** Context Engineering：AI 時代的開發者生存指南
**風格定位：** Manning "in Action" 系列
**目標字數：** 80,000 - 100,000 字（含程式碼範例）
**目標讀者：** 軟體工程師、技術主管、AI 應用開發者、技術創業者

---

## 本書特色

- **揭示真相**：所有 AI 編碼工具本質上都是「300 行程式碼在迴圈中運行 LLM tokens」
- **思維轉變**：將 Context Window 視為有限且一次性的記憶體陣列
- **實作導向**：從零建構自己的 coding agent
- **職涯保障**：理解基礎原理是從 AI 消費者轉變為生產者的關鍵

---

## 全書架構

### 第一部分：認知革命 — 理解 AI 編碼工具的本質

- **第 1 章：「300 行程式碼的真相」**
  - 揭示所有 AI 編碼工具的共同架構
  - 為何廠商比較是「追尾行為」
  - 案例：Geoffrey Huntley 的「coding agent 只是迴圈」宣言

- **第 2 章：「Context Window 是陣列，不是對話」**
  - malloc/free 問題：為何 Context 只增不減
  - 「廣告容量」vs「實際可用容量」：200K tokens 的真相
  - 實驗：觀察 Context 污染如何影響輸出品質

- **第 3 章：「不是所有 LLM 都是 Agentic」**
  - LLM 分類學：Oracle vs Agentic、High Safety vs Low Safety
  - Claude Sonnet：追逐工具呼叫的「機械松鼠」
  - 進階：將 Oracle 模型作為工具註冊給 Agentic 模型

### 第二部分：核心技能 — 從零建構 Coding Agent

- **第 4 章：「推論迴圈的解剖學」**
  - 輸入 → 推論 → 工具呼叫 → 結果分配 → 再推論
  - Harness Prompt 的結構與設計原則
  - 實作：用 Go 語言建構基本聊天介面

- **第 5 章：「五大核心工具」**
  - Read Tool：將檔案內容載入 Context
  - List Tool：目錄探索與檔案發現
  - Bash Tool：讓 LLM 執行系統命令
  - Edit Tool：將推論結果應用到檔案
  - Search Tool：ripgrep 與程式碼搜尋的秘密
  - 實作：完成一個能解決 FizzBuzz 的 coding agent

- **第 6 章：「MCP：工具的工具」**
  - Model Context Protocol 的本質：「帶有廣告牌的函數」
  - MCP 的 Context 成本：為何「less is more」
  - 案例分析：過度配置 MCP 工具導致的效能崩潰

### 第三部分：進階模式 — Ralph Wiggum Loop 與自主迭代

- **第 7 章：「Ralph Wiggum：五行程式碼的革命」**
  - Ralph 的起源：澳洲山羊農場的頓悟
  - 「確定性的失敗勝過非確定性的成功」哲學
  - 實作：建構你的第一個 Ralph Loop

- **第 8 章：「官方 Plugin vs 原始實現」**
  - Anthropic 官方 Plugin 的 Stop Hook 機制
  - 「消毒化」的代價：安全與效能的權衡
  - 案例：CURSED 程式語言的三個月開發歷程

- **第 9 章：「Prompt 工程的藝術」**
  - 設計收斂條件：讓迴圈知道何時停止
  - 「遊樂場」隱喻：建構、失敗、加標誌、重來
  - 實作：為不同任務類型設計 PROMPT.md 模板

### 第四部分：實戰應用 — 成為 AI 生產者

- **第 10 章：「適用場景與成本經濟學」**
  - 可機器驗證 vs 需要判斷：Ralph 的適用邊界
  - Token 成本計算：50 次迭代的經濟分析
  - 案例：$297 完成 $50,000 合約的真實故事

- **第 11 章：「企業級應用模式」**
  - 大規模重構：Jest 到 Vitest 遷移實戰
  - 「夜間工廠」：設定 Cron Job 讓 Ralph 在你睡覺時工作
  - 安全性考量：權限控制與審計追蹤

- **第 12 章：「未來展望：Subagents 與 KTLO 自動化」**
  - Subagents：解決 Context 溢出的新架構
  - 「Roomba 夢想」：成千上萬的 AI 機器人自動維護程式碼
  - 為 2027 年做準備：持續學習的路徑圖

---

## 專案結構

```
context-engineering/
├── README.md                           # 本文件
├── book-proposal-context-engineering.docx  # 原始出版企劃書
├── manuscript/
│   └── chapters/                       # 各章節內容
│       ├── chapter-01.md
│       ├── chapter-02.md
│       └── ...
├── code-examples/                      # 完整可運行的程式碼範例
│   ├── chapter-04/                     # 推論迴圈範例（Go）
│   ├── chapter-05/                     # 五大核心工具實作
│   ├── chapter-07/                     # Ralph Loop 實作
│   ├── chapter-10/                     # 成本監控範例
│   └── chapter-11/                     # 企業級應用範例
├── diagrams/                           # 技術圖表與架構圖
└── resources/
    └── prompt-templates/               # PROMPT.md 模板庫
```

---

## 當前進度

### 第一部分：認知革命 — 理解 AI 編碼工具的本質
- [ ] 第 1 章：300 行程式碼的真相
- [ ] 第 2 章：Context Window 是陣列，不是對話
- [ ] 第 3 章：不是所有 LLM 都是 Agentic

### 第二部分：核心技能 — 從零建構 Coding Agent
- [ ] 第 4 章：推論迴圈的解剖學
- [ ] 第 5 章：五大核心工具
- [ ] 第 6 章：MCP：工具的工具

### 第三部分：進階模式 — Ralph Wiggum Loop 與自主迭代
- [ ] 第 7 章：Ralph Wiggum：五行程式碼的革命
- [ ] 第 8 章：官方 Plugin vs 原始實現
- [ ] 第 9 章：Prompt 工程的藝術

### 第四部分：實戰應用 — 成為 AI 生產者
- [ ] 第 10 章：適用場景與成本經濟學
- [ ] 第 11 章：企業級應用模式
- [ ] 第 12 章：未來展望：Subagents 與 KTLO 自動化

**總計進度**：0/12 章

---

## 核心引言

> 「The tech industry's conveyor belt continues to move forward. 在 2026 年，理解這些基礎原理的開發者，將能駕馭而非被動接受 AI 工具的演進。」
> — Geoffrey Huntley

> 「你的同事會取代你的工作，不是 AI。」
> — Geoffrey Huntley

> 「Go forward and build.」
> — Geoffrey Huntley

---

## 技術棧

- **主要語言**：Go（coding agent 實作）、Python（輔助工具）
- **核心技術**：Claude API、Model Context Protocol (MCP)
- **工具整合**：ripgrep、Git
- **開發環境**：Claude Code CLI

---

## 附加資源

- **GitHub 程式碼庫**：所有實作範例的完整程式碼
- **PROMPT.md 模板庫**：針對不同任務類型的即用 prompt 模板

---

## 授權

本書內容為出版前的草稿，版權所有。未經授權，請勿複製或傳播。

---

**最後更新：2026-01-13**
