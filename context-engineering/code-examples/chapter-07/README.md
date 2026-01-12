# 第 7 章：Ralph Wiggum Loop - 程式碼範例

> 建構你的第一個 Ralph Loop

---

## 本目錄內容

本目錄包含第 7 章「Ralph Wiggum：五行程式碼的革命」的完整可運行程式碼範例。

### 檔案清單

```
chapter-07/
├── README.md               # 本文件
├── ralph.sh                # Ralph Loop Bash 腳本
├── PROMPT.md.example       # PROMPT.md 範例模板
├── start-ralph.sh          # 啟動腳本
├── stop-ralph.sh           # 停止腳本
├── monitor.sh              # 監控腳本
└── examples/
    ├── bug-fix/            # Bug 修復範例
    │   └── PROMPT.md
    ├── migration/          # 程式碼遷移範例
    │   └── PROMPT.md
    └── refactoring/        # 重構範例
        └── PROMPT.md
```

---

## 執行方式

### 前置需求

- Claude Code CLI
- Git
- Bash

### 基本使用

```bash
# 複製 PROMPT.md 範例
cp PROMPT.md.example PROMPT.md

# 編輯 PROMPT.md，定義你的任務
vim PROMPT.md

# 啟動 Ralph Loop
./ralph.sh
```

### ralph.sh 內容

```bash
#!/bin/bash
while true; do
    claude --prompt "$(cat PROMPT.md)" --dangerously-skip-permissions
    git add -A && git commit -m "checkpoint $(date +%Y%m%d-%H%M%S)"
done
```

---

## PROMPT.md 設計指南

有效的 PROMPT.md 應包含：

1. **任務描述**：清楚說明要完成什麼
2. **完成條件**：可機器驗證的收斂條件
3. **工作流程**：建議的執行步驟
4. **約束條件**：不應該做的事情

---

## 範例場景

### Bug 修復
見 `examples/bug-fix/PROMPT.md`

### 程式碼遷移
見 `examples/migration/PROMPT.md`

### 重構
見 `examples/refactoring/PROMPT.md`

---

## 監控與控制

### 監控進度

```bash
# 即時查看 commit 歷史
watch -n 5 'git log --oneline -20'

# 使用 monitor.sh
./monitor.sh
```

### 停止迴圈

```bash
# 使用 stop 腳本
./stop-ralph.sh

# 或手動中斷
Ctrl+C
```

---

## 注意事項

- 請在版本控制的專案中使用
- 建議先在測試分支上實驗
- 設定合理的執行時間上限
- 定期檢查 commit 歷史確認進度
