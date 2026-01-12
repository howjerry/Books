# 第 10 章：適用場景與成本經濟學 - 程式碼範例

> Token 成本監控與 ROI 計算工具

---

## 本目錄內容

本目錄包含第 10 章「適用場景與成本經濟學」的程式碼範例。

### 檔案清單

```
chapter-10/
├── README.md               # 本文件
├── tracker/
│   ├── main.go             # Token 追蹤器主程式
│   ├── tracker.go          # 追蹤邏輯實作
│   └── report.go           # 報告生成
├── calculator/
│   ├── main.go             # ROI 計算器
│   └── models.go           # 成本模型定義
├── examples/
│   └── migration-analysis/ # 遷移成本分析範例
├── go.mod
└── go.sum
```

---

## Token 追蹤器

### 功能

- 追蹤每次迭代的 Input/Output Token
- 計算累積成本
- 生成使用報告

### 使用方式

```bash
cd code-examples/chapter-10/tracker
go run . --session my-project
```

### 輸出範例

```
============================================
         Token 使用報告
============================================
Session: my-project
總迭代次數: 47
--------------------------------------------
Input Tokens:  892,340
Output Tokens: 156,780
--------------------------------------------
估計成本 (Claude Sonnet):
  Input:  $2.68
  Output: $2.35
  總計:   $5.03
============================================
```

---

## ROI 計算器

### 功能

- 比較傳統開發 vs Ralph Loop 成本
- 計算投資報酬率
- 適用性評估

### 使用方式

```bash
cd code-examples/chapter-10/calculator
go run . --task "Jest to Vitest migration" --files 500 --manual-hours 160
```

### 輸出範例

```
============================================
         ROI 分析報告
============================================
任務: Jest to Vitest migration
檔案數量: 500
--------------------------------------------
傳統方式:
  工時: 160 hours
  成本: $12,800 (假設 $80/hour)

Ralph Loop 方式:
  預估迭代: 150
  Token 成本: $12.50
  監督時間: 4 hours
  總成本: $332.50
--------------------------------------------
節省: $12,467.50 (97.4%)
ROI: 3,651%
============================================
```

---

## 成本模型

### Claude Sonnet 定價（2026 Q1）

| 項目 | 單價 |
|------|------|
| Input | $0.003 / 1K tokens |
| Output | $0.015 / 1K tokens |

### 每次迭代預估消耗

| 項目 | Tokens |
|------|--------|
| System Prompt | 5,000 |
| Tool Definitions | 3,000 |
| Code Context | 10,000 |
| Output | 2,000 |
| **總計** | **~20,000** |

---

## 適用性檢查清單

使用 Ralph Loop 前的評估：

- [ ] 任務是否可機器驗證？
- [ ] 是否有明確的收斂條件？
- [ ] 錯誤是否容易回滾？
- [ ] 是否有大量重複模式？
- [ ] 時間價值是否高於 Token 成本？
