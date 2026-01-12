# PROMPT.md 模板庫

本目錄提供各種任務類型的 PROMPT.md 模板，供讀者直接使用或參考修改。

## 使用方式

1. 選擇適合任務類型的模板
2. 複製到你的專案根目錄
3. 根據具體任務修改模板內容
4. 啟動 Ralph Loop

```bash
cp templates/bug-fix.md ./PROMPT.md
# 編輯 PROMPT.md
vim PROMPT.md
# 啟動 Ralph Loop
./ralph.sh
```

## 模板清單

### 程式碼品質

| 模板 | 說明 | 適用場景 |
|------|------|----------|
| `bug-fix.md` | Bug 修復模板 | 已知錯誤的定位與修復 |
| `refactoring.md` | 重構模板 | 程式碼結構改善 |
| `lint-fix.md` | Linting 修復 | 修復 ESLint/Prettier 問題 |
| `type-error-fix.md` | 類型錯誤修復 | TypeScript 類型問題 |

### 程式碼遷移

| 模板 | 說明 | 適用場景 |
|------|------|----------|
| `migration-general.md` | 通用遷移模板 | 任意框架/庫遷移 |
| `jest-to-vitest.md` | Jest → Vitest | 測試框架遷移 |
| `commonjs-to-esm.md` | CJS → ESM | 模組系統遷移 |
| `class-to-hooks.md` | Class → Hooks | React 組件現代化 |

### 功能實作

| 模板 | 說明 | 適用場景 |
|------|------|----------|
| `feature-implement.md` | 功能實作 | 新功能開發 |
| `api-endpoint.md` | API 端點 | 新增 REST/GraphQL 端點 |
| `test-coverage.md` | 測試覆蓋 | 提升測試覆蓋率 |

### 文件生成

| 模板 | 說明 | 適用場景 |
|------|------|----------|
| `doc-generation.md` | 文件生成 | API 文件、README |
| `jsdoc-add.md` | JSDoc 註解 | 為函數新增文件註解 |

## 模板結構說明

每個模板都遵循統一結構：

```markdown
# 任務：[任務名稱]

## 情境
[背景資訊]

## 目標
[要達成的目標]

## 約束
[限制條件]

## 完成條件
[收斂條件 - 最重要]

## 工作流程
[建議步驟]

## 注意事項
[常見陷阱]
```

## 設計原則

### 1. 完成條件必須可機器驗證

```markdown
## 完成條件
✅ 好：npm test 返回 exit code 0
✅ 好：tsc --noEmit 無錯誤輸出
❌ 差：程式碼品質良好
❌ 差：使用者體驗改善
```

### 2. 約束條件要明確

```markdown
## 約束
✅ 好：不修改 src/core/ 目錄下的任何檔案
✅ 好：每個檔案變更不超過 50 行
❌ 差：保持程式碼風格一致
```

### 3. 工作流程要具體

```markdown
## 工作流程
✅ 好：
1. 執行 `npm test` 查看失敗的測試
2. 讀取失敗測試對應的原始碼
3. 修復問題
4. 重新執行測試驗證

❌ 差：
1. 分析問題
2. 修復問題
3. 驗證結果
```

## 貢獻指南

歡迎提交新的模板！請確保：

- [ ] 模板已在實際任務中驗證過
- [ ] 完成條件可機器驗證
- [ ] 包含足夠的使用說明
- [ ] 遵循模板結構規範
