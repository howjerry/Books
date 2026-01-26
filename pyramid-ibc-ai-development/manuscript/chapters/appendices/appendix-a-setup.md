# 附錄 A：Claude Code 安裝與設定指南

## A.1 系統需求

### 作業系統
- macOS 12.0 或更新版本
- Ubuntu 20.04 或更新版本
- Windows 11（WSL2）

### 必要軟體
- Node.js 18.0 或更新版本
- npm 或 yarn
- Git

### 建議配置
- 記憶體：8GB 或以上
- 網路：穩定的網路連線

---

## A.2 安裝步驟

### 方法一：使用 npm（建議）

```bash
# 全域安裝 Claude Code
npm install -g @anthropic-ai/claude-code

# 驗證安裝
claude --version
```

### 方法二：使用 Homebrew（macOS）

```bash
# 新增 tap
brew tap anthropic/claude-code

# 安裝
brew install claude-code

# 驗證安裝
claude --version
```

### 方法三：手動安裝

```bash
# 下載最新版本
curl -L https://github.com/anthropics/claude-code/releases/latest/download/claude-code-linux.tar.gz -o claude-code.tar.gz

# 解壓縮
tar -xzf claude-code.tar.gz

# 移動到 PATH
sudo mv claude-code /usr/local/bin/claude

# 驗證安裝
claude --version
```

---

## A.3 初始設定

### 設定 API Key

```bash
# 設定環境變數
export ANTHROPIC_API_KEY="your-api-key-here"

# 或使用 claude config 指令
claude config set api_key "your-api-key-here"
```

> 💡 **取得 API Key**
>
> 1. 前往 https://console.anthropic.com
> 2. 登入或註冊帳號
> 3. 在 API Keys 頁面產生新的 key
> 4. 妥善保管，不要分享

### 永久設定環境變數

**macOS / Linux：**
```bash
# 編輯 shell 設定檔
echo 'export ANTHROPIC_API_KEY="your-api-key"' >> ~/.bashrc
# 或 ~/.zshrc（如果使用 zsh）

# 重新載入
source ~/.bashrc
```

**Windows（PowerShell）：**
```powershell
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "your-api-key", "User")
```

---

## A.4 設定檔說明

Claude Code 的設定檔位於 `~/.claude/config.json`：

```json
{
  "api_key": "your-api-key",
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 4096,
  "temperature": 0,
  "default_permissions": {
    "read": true,
    "write": "ask",
    "execute": "ask"
  },
  "editor": "code",
  "shell": "/bin/bash"
}
```

### 設定項目說明

| 設定項 | 說明 | 預設值 |
|--------|------|--------|
| `api_key` | Anthropic API Key | - |
| `model` | 使用的模型 | claude-sonnet-4-20250514 |
| `max_tokens` | 最大 token 數 | 4096 |
| `temperature` | 創意程度（0-1） | 0 |
| `default_permissions.read` | 讀取檔案權限 | true |
| `default_permissions.write` | 寫入檔案權限 | ask |
| `default_permissions.execute` | 執行指令權限 | ask |
| `editor` | 預設編輯器 | code |
| `shell` | 預設 shell | /bin/bash |

---

## A.5 常見問題排解

### 問題 1：API Key 無效

```
Error: Invalid API key
```

**解決方法：**
1. 確認 API key 正確無誤
2. 確認環境變數已設定：`echo $ANTHROPIC_API_KEY`
3. 確認 API key 沒有過期

### 問題 2：網路連線失敗

```
Error: Network error - Unable to connect to Anthropic API
```

**解決方法：**
1. 確認網路連線正常
2. 確認沒有防火牆阻擋
3. 如果使用代理，設定 `HTTPS_PROXY` 環境變數

### 問題 3：權限問題

```
Error: Permission denied when writing to file
```

**解決方法：**
1. 確認目標目錄有寫入權限
2. 使用 `claude config set default_permissions.write true` 允許寫入

---

## A.6 更新與卸載

### 更新到最新版本

```bash
# npm
npm update -g @anthropic-ai/claude-code

# Homebrew
brew upgrade claude-code
```

### 卸載

```bash
# npm
npm uninstall -g @anthropic-ai/claude-code

# Homebrew
brew uninstall claude-code

# 清理設定檔
rm -rf ~/.claude
```
