# Chapter 1 程式碼範例

本目錄包含第 1 章「從零開始打造智能化開發環境」的完整可運行程式碼。

## 目錄結構

```
chapter-01/
├── README.md                           # 本檔案
├── hooks/                             # Hook 腳本
│   ├── post-tool-use-tracker.sh      # 檔案編輯監聽 Hook
│   ├── skill-activation-prompt.sh    # 提示分析 Hook
│   ├── skill-activation-prompt.ts    # 提示分析邏輯
│   ├── check-skills.ts               # 檔案路徑匹配
│   ├── rule-engine.ts                # 規則引擎核心
│   ├── package.json                  # Node.js 依賴
│   └── tsconfig.json                 # TypeScript 配置
├── skills/                           # 技能範例
│   ├── skill-rules.json             # 規則配置
│   └── backend-dev-guidelines/      # 測試技能
│       └── SKILL.md
└── settings.json                     # Claude Code 配置
```

## 快速開始

### 1. 安裝依賴

```bash
cd hooks
npm install
```

### 2. 設定權限

```bash
chmod +x hooks/*.sh
```

### 3. 複製到你的專案

```bash
# 複製整個 .claude 目錄結構到你的專案
cp -r hooks ../your-project/.claude/hooks
cp -r skills ../your-project/.claude/skills
cp settings.json ../your-project/.claude/settings.json
```

### 4. 測試 Hook

```bash
# 測試 post-tool-use Hook
echo '{"tool":"Edit","args":{"file_path":"src/test.ts"}}' | ./hooks/post-tool-use-tracker.sh

# 測試 skill-activation Hook
echo '{"prompt":"create a new API controller","workingDirectory":"'$(pwd)'","recentFiles":[]}' | ./hooks/skill-activation-prompt.sh
```

## 檔案說明

### Hook 腳本

- **post-tool-use-tracker.sh**: 監聽 Claude 的檔案編輯操作，當檔案被編輯時觸發規則引擎
- **skill-activation-prompt.sh**: 分析使用者輸入的提示，根據關鍵字和意圖匹配相關技能
- **check-skills.ts**: 根據檔案路徑匹配相應的技能
- **skill-activation-prompt.ts**: 根據提示內容和最近編輯的檔案匹配技能

### 核心邏輯

- **rule-engine.ts**: 規則引擎，負責路徑模式匹配、關鍵字識別、優先級排序

### 配置檔案

- **settings.json**: Claude Code 的 Hook 配置
- **skill-rules.json**: 技能激活規則配置
- **package.json**: Node.js 依賴清單
- **tsconfig.json**: TypeScript 編譯配置

### 技能範例

- **backend-dev-guidelines/SKILL.md**: 後端開發指南技能範例

## 自訂配置

### 修改觸發規則

編輯 `skills/skill-rules.json`，根據你的專案調整：

```json
{
  "pathPatterns": [
    "src/api/**/*.ts",        // 調整為你的 API 路徑
    "backend/**/*.controller.ts"
  ],
  "promptTriggers": {
    "keywords": ["controller", "API", "route"],  // 添加你的關鍵字
    "intents": ["create.*controller"]            // 添加意圖模式
  }
}
```

### 添加新技能

1. 在 `skills/` 目錄下創建新技能資料夾
2. 添加 `SKILL.md` 檔案
3. 在 `skill-rules.json` 中添加規則

## 故障排除

### Hook 沒有執行

檢查權限：
```bash
ls -la hooks/*.sh
```

應該顯示 `-rwxr-xr-x`（可執行）

### 依賴缺失

確保已安裝所有依賴：
```bash
cd hooks
npm list
```

### JSON 格式錯誤

驗證配置檔案格式：
```bash
cat settings.json | jq .
cat skills/skill-rules.json | jq .
```

## 進階用法

### 查看活動日誌

```bash
tail -f hooks/activity.log
```

### 手動測試規則引擎

```bash
cd hooks
node -r ts-node/register check-skills.ts "src/api/controllers/user.controller.ts"
```

### 清理日誌

```bash
> hooks/activity.log
```

## 相關資源

- [Claude Code 官方文件](https://docs.claude.com)
- [原始專案：claude-code-infrastructure-showcase](https://github.com/diet103/claude-code-infrastructure-showcase)
- [Chapter 1 完整內容](../../manuscript/chapters/chapter-01.md)
