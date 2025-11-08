# 第 2 章：賦予 Agent 執行能力 - 自動化報表生成系統

## 專案說明

這是《Claude Agent SDK 打造企業 Agent》第 2 章的完整可運行程式碼範例。

本專案展示如何建立一個能夠執行系統命令、讀寫檔案、生成圖表的 AI Agent，用於自動化業務報表生成。

## 功能特色

✅ **安全的 Bash 執行器**
- 命令白名單機制
- 危險模式黑名單
- 路徑限制與超時保護

✅ **檔案操作工具**
- 讀取 TXT, JSON, CSV
- 寫入 Markdown, JSON
- 目錄列表

✅ **Python 腳本執行**
- 圖表生成（matplotlib）
- 資料分析腳本

✅ **報表協調器**
- 自動規劃執行步驟
- 多工具協調
- 專業報表生成

## 快速開始

### 1. 安裝依賴

```bash
# 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
# 複製範例檔案
cp .env.example .env

# 編輯 .env 並填入你的 API 金鑰
# ANTHROPIC_API_KEY=your_api_key_here
```

### 3. 執行報表生成

```bash
python main.py
```

## 專案結構

```
chapter-02/
├── main.py                      # 主程式
├── report_coordinator.py        # 報表協調器 Agent
├── requirements.txt             # Python 依賴
├── .env.example                 # 環境變數範例
├── tools/                       # 工具模組
│   ├── bash_executor.py         # Bash 執行器
│   ├── file_operations.py       # 檔案操作
│   └── script_runner.py         # Python 腳本執行器
├── scripts/                     # Python 腳本
│   └── generate_chart.py        # 圖表生成腳本
├── sandbox/                     # 安全配置
│   └── allowed_commands.yaml    # 命令白名單
└── workspace/                   # 工作空間
    ├── data/                    # 原始資料
    │   └── users.csv
    ├── logs/                    # 日誌檔案
    │   ├── app.log
    │   └── api.log
    ├── reports/                 # 生成的報表（執行後產生）
    └── charts/                  # 生成的圖表（執行後產生）
```

## 測試資料

專案包含以下測試資料：

- **workspace/data/users.csv**: 用戶註冊統計（2025-11-01 ~ 2025-11-08）
- **workspace/logs/app.log**: 應用程式日誌（包含錯誤與警告）
- **workspace/logs/api.log**: API 呼叫記錄

## 安全機制

### 命令白名單
只允許執行以下命令：
- `grep`, `awk`, `sed`, `wc`, `cat`, `head`, `tail`, `sort`, `uniq`, `cut`
- `psql` (資料庫查詢)
- `python` (腳本執行)

### 危險模式黑名單
禁止以下模式：
- `rm -rf`, `sudo`, `chmod 777`
- `curl`, `wget` (網路請求)
- 訪問系統目錄（`/etc/`, `/var/`, `/usr/`）

### 路徑限制
所有檔案操作限制在 `workspace/` 目錄內。

## 自訂報表

你可以修改 `main.py` 中的 `request` 變數來自訂報表需求：

```python
request = """請產生 [你的需求]。

報表需包含：
1. [分析項目 1]
   - 資料來源：...

2. [分析項目 2]
   - 資料來源：...

最終報表儲存為：reports/[檔名].md
"""
```

## 擴展功能

### 添加新的圖表腳本

在 `scripts/` 目錄建立新的 Python 腳本，例如：

```python
# scripts/my_analysis.py
import sys

def analyze(input_file, output_file):
    # 你的分析邏輯
    pass

if __name__ == "__main__":
    analyze(sys.argv[1], sys.argv[2])
```

### 添加新的命令

編輯 `sandbox/allowed_commands.yaml`：

```yaml
allowed_commands:
  - grep
  - awk
  - your_new_command  # 添加這裡
```

## 故障排除

### 錯誤：「命令不在白名單中」
**解決方法**: 將命令添加到 `sandbox/allowed_commands.yaml`

### 錯誤：「路徑不安全」
**解決方法**: 確保所有檔案路徑相對於 `workspace/` 目錄

### 錯誤：「ModuleNotFoundError」
**解決方法**: 確認虛擬環境已啟動並已安裝所有依賴

## 效能指標

- **時間節省**: 97% (2.5 小時 → 4 分鐘)
- **API 成本**: 約 $0.11 / 次
- **程式碼量**: ~1,000 行

## 學習目標

完成本章後，你將掌握：

✅ 建構安全的 Bash 執行器
✅ 實作檔案讀寫工具
✅ 整合 Python 腳本執行能力
✅ 設計多工具協調的 Agent
✅ 安全防護機制的最佳實踐

## 相關章節

- 第 1 章：建構你的第一個 Claude Agent
- 第 3 章：情境工程 - 建立長期記憶的知識管理 Agent
- 第 8 章：生產環境的安全與監控

## 授權

本程式碼為教學用途，版權所有。

---

**最後更新**: 2025-11-08
