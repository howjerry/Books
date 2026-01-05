# 第 7 章：打造軟體工廠 (The Software Factory)

> 「好的軟體不是寫出來的，是持續改進出來的。」
> —— CloudMart 工程總監

---

## 本章學習目標

完成本章後，你將能夠：

- 解釋版本控制系統的核心概念
- 使用 Git 進行程式碼管理
- 設計 Git 分支策略
- 理解 DevOps 的文化和實踐
- 建立 CI/CD 自動化流程
- 使用 Azure DevOps 或 GitHub Actions

---

## 7.1 部署惡夢：手動發布的代價

2023 年某個週五下午 5 點，CloudMart 的工程師小王準備發布一個「簡單的」錯誤修復。

「只是改了一行程式碼，應該沒問題。」

他手動將程式碼上傳到生產伺服器，重啟服務。

5:05 — 網站正常
5:10 — 開始收到錯誤報告
5:15 — 購物車功能完全失效
5:30 — 緊急回滾，但發現沒有備份上一版本
6:30 — 終於從 Git 歷史中找回舊版本
7:00 — 服務恢復

損失：2 小時的營收，無數的客戶投訴，和小王一個週末的心理陰影。

```
┌─────────────────────────────────────────────────────────────────┐
│                    手動部署的問題                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  傳統流程：                                                      │
│                                                                 │
│  開發者 ──手動打包──► FTP 上傳 ──► 手動重啟服務                 │
│                           │                                     │
│                           ▼                                     │
│                      出了問題？                                  │
│                           │                                     │
│           ┌───────────────┴───────────────┐                     │
│           │                               │                     │
│           ▼                               ▼                     │
│       手動回滾                        找不到舊版本               │
│     （如果有備份）                    （常常發生）               │
│                                                                 │
│  問題清單：                                                      │
│  ✗ 沒有標準化流程                                               │
│  ✗ 沒有自動化測試                                               │
│  ✗ 沒有版本追蹤                                                 │
│  ✗ 無法快速回滾                                                 │
│  ✗ 依賴個人經驗                                                 │
│  ✗ 週五下午部署（大忌！）                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7.2 版本控制：時光機器

### 7.2.1 為什麼需要版本控制？

**版本控制系統（Version Control System, VCS）** 追蹤檔案的每一次變更，讓你可以：

- 回到任何歷史版本
- 看到誰在什麼時候改了什麼
- 多人同時工作而不互相覆蓋
- 建立分支進行實驗性開發

### 7.2.2 Git：分散式版本控制

**Git** 是目前最流行的分散式版本控制系統。

```
┌─────────────────────────────────────────────────────────────────┐
│                  Git 核心概念                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Repository（儲存庫）                                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  包含所有檔案和完整歷史記錄的資料夾                        │ │
│  │  每個開發者都有一份完整的副本（分散式）                    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Commit（提交）                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  一次變更的快照，包含：                                    │ │
│  │  • 變更的檔案內容                                          │ │
│  │  • 作者資訊                                                │ │
│  │  • 時間戳記                                                │ │
│  │  • 提交訊息                                                │ │
│  │  • 父提交的參照                                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Branch（分支）                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  獨立的開發線，不影響主線                                  │ │
│  │                                                           │ │
│  │       ○───○───○  feature/new-checkout                     │ │
│  │      /                                                    │ │
│  │  ○──○───○───○───○  main                                   │ │
│  │          \                                                │ │
│  │           ○───○  bugfix/cart-error                        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Merge（合併）                                                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  將一個分支的變更整合到另一個分支                          │ │
│  │                                                           │ │
│  │       ○───○───○──┐  feature/new-checkout                  │ │
│  │      /           \                                        │ │
│  │  ○──○───○───○───○───●  main (合併後)                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2.3 Git 基本操作

```bash
# 初始化新儲存庫
git init

# 複製遠端儲存庫
git clone https://github.com/cloudmart/webapp.git

# 查看狀態
git status

# 添加檔案到暫存區
git add src/cart.js              # 單一檔案
git add .                         # 所有變更

# 提交變更
git commit -m "修復購物車價格計算錯誤"

# 推送到遠端
git push origin main

# 從遠端拉取
git pull origin main

# 建立分支
git branch feature/new-payment

# 切換分支
git checkout feature/new-payment
# 或使用新語法
git switch feature/new-payment

# 建立並切換分支（合併操作）
git checkout -b feature/new-payment

# 合併分支
git checkout main
git merge feature/new-payment

# 查看提交歷史
git log --oneline --graph

# 回到特定版本
git checkout abc1234

# 撤銷未提交的變更
git restore src/cart.js
```

### 7.2.4 Git 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                 CloudMart Git 工作流程                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  GitFlow 策略：                                                  │
│                                                                 │
│  main ──────●────────────────●────────────────●──────────────   │
│             │                │                │                 │
│             │    release/    │                │                 │
│             │      1.2.0     │                │                 │
│             │    ┌───●───┐   │                │                 │
│  develop ───●────●───────●───●────●───●───●───●────●─────────   │
│             │    │           │    │   │   │   │    │            │
│             │    │           │    │   │   │   │    │            │
│  feature/   │    │           │    ○───○───○   │    │            │
│  checkout   ○────○───────────●                │    │            │
│                                               │    │            │
│  feature/                                     ○────●            │
│  search                                                         │
│                                                                 │
│  hotfix/                                                        │
│  urgent-fix         ────────────○────●                          │
│                                                                 │
│  ═══════════════════════════════════════════════════════════   │
│                                                                 │
│  分支說明：                                                      │
│                                                                 │
│  • main：生產環境程式碼，永遠是穩定的                            │
│  • develop：開發主線，整合所有功能                               │
│  • feature/*：新功能開發                                        │
│  • release/*：發布準備，最後的測試和修復                         │
│  • hotfix/*：緊急修復，直接從 main 分支                          │
│                                                                 │
│  ═══════════════════════════════════════════════════════════   │
│                                                                 │
│  命名規範：                                                      │
│                                                                 │
│  feature/add-payment-method                                     │
│  feature/JIRA-123-user-profile                                  │
│  bugfix/cart-calculation-error                                  │
│  hotfix/security-vulnerability                                  │
│  release/v1.2.0                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2.5 好的提交訊息

```
┌─────────────────────────────────────────────────────────────────┐
│                  提交訊息規範                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  格式：                                                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  <類型>(<範圍>): <簡短描述>                                 │ │
│  │                                                           │ │
│  │  <詳細說明>                                                │ │
│  │                                                           │ │
│  │  <關聯的 Issue>                                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  類型：                                                          │
│  • feat：新功能                                                 │
│  • fix：錯誤修復                                                │
│  • docs：文件變更                                               │
│  • style：格式調整（不影響程式碼邏輯）                           │
│  • refactor：重構（不新增功能或修復錯誤）                        │
│  • test：測試相關                                               │
│  • chore：維護工作（建置、依賴更新等）                           │
│                                                                 │
│  ═══════════════════════════════════════════════════════════   │
│                                                                 │
│  ✓ 好的提交訊息：                                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  fix(cart): 修正多商品時的價格計算錯誤                      │ │
│  │                                                           │ │
│  │  - 修正浮點數精度問題導致的四捨五入錯誤                     │ │
│  │  - 增加單元測試覆蓋邊界情況                                 │ │
│  │                                                           │ │
│  │  Fixes #234                                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ✗ 壞的提交訊息：                                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  fix bug                                                  │ │
│  │  更新                                                      │ │
│  │  asdfasdf                                                 │ │
│  │  WIP                                                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7.3 DevOps：開發與運維的融合

### 7.3.1 什麼是 DevOps？

**DevOps** 是一種文化和實踐，旨在打破開發（Development）和運維（Operations）之間的壁壘。

```
┌─────────────────────────────────────────────────────────────────┐
│                  傳統 vs. DevOps                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  傳統模式（筒倉式）                                              │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │  開發團隊                        運維團隊                  │ │
│  │  ┌─────────┐                    ┌─────────┐              │ │
│  │  │ 寫程式碼 │ ──「丟過牆」───► │ 部署維護 │              │ │
│  │  └─────────┘                    └─────────┘              │ │
│  │      │                              │                     │ │
│  │  「我的程式                    「你的程式碼               │ │
│  │   在我電腦                      有問題！」                │ │
│  │   上可以跑」                        │                     │ │
│  │      │                              │                     │ │
│  │      └──────── 互相指責 ────────────┘                     │ │
│  │                                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  DevOps 模式（協作式）                                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │            ┌─────────────────────────────┐               │ │
│  │            │      DevOps 團隊            │               │ │
│  │            │                             │               │ │
│  │            │  ┌─────┐  ┌─────┐  ┌─────┐ │               │ │
│  │            │  │ Dev │──│ QA  │──│ Ops │ │               │ │
│  │            │  └─────┘  └─────┘  └─────┘ │               │ │
│  │            │         共同責任            │               │ │
│  │            └─────────────────────────────┘               │ │
│  │                                                           │ │
│  │  「你建構它，你運行它」(You build it, you run it)         │ │
│  │                                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3.2 DevOps 的核心實踐

```
┌─────────────────────────────────────────────────────────────────┐
│                  DevOps 無限循環                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                         ┌─────────┐                             │
│              ┌──────────│  計畫   │◄─────────┐                  │
│              │          │  Plan   │          │                  │
│              │          └────┬────┘          │                  │
│              │               │               │                  │
│         ┌────┴────┐          │          ┌────┴────┐             │
│         │  監控   │          │          │  開發   │             │
│         │ Monitor │          │          │  Code   │             │
│         └────┬────┘          │          └────┬────┘             │
│              │               │               │                  │
│              │          ┌────▼────┐          │                  │
│              │          │   ∞    │          │                  │
│              │          │ DevOps │          │                  │
│              │          └────────┘          │                  │
│              │               │               │                  │
│         ┌────┴────┐          │          ┌────┴────┐             │
│         │  運行   │          │          │  建構   │             │
│         │ Operate │          │          │  Build  │             │
│         └────┬────┘          │          └────┬────┘             │
│              │               │               │                  │
│              │          ┌────┴────┐          │                  │
│              └──────────│  部署   │──────────┘                  │
│                         │ Deploy  │                             │
│                         └─────────┘                             │
│                                                                 │
│  ═══════════════════════════════════════════════════════════   │
│                                                                 │
│  關鍵指標（DORA Metrics）：                                      │
│                                                                 │
│  1. 部署頻率（Deployment Frequency）                            │
│     • 精英團隊：每天多次                                        │
│     • 一般團隊：每週或每月                                      │
│                                                                 │
│  2. 變更前置時間（Lead Time for Changes）                       │
│     • 從提交程式碼到部署生產的時間                              │
│     • 精英團隊：少於 1 天                                       │
│                                                                 │
│  3. 變更失敗率（Change Failure Rate）                           │
│     • 導致生產故障的部署百分比                                  │
│     • 精英團隊：0-15%                                          │
│                                                                 │
│  4. 平均復原時間（Mean Time to Restore）                        │
│     • 從故障到恢復服務的時間                                    │
│     • 精英團隊：少於 1 小時                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7.4 CI/CD：持續整合與持續部署

### 7.4.1 CI/CD 概念

```
┌─────────────────────────────────────────────────────────────────┐
│                      CI/CD 流程                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  持續整合（Continuous Integration, CI）                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │  開發者 A ──┐                                              │ │
│  │            ├──► 共用儲存庫 ──► 自動建構 ──► 自動測試      │ │
│  │  開發者 B ──┘         │              │            │        │ │
│  │                       │              │            │        │ │
│  │                       ▼              ▼            ▼        │ │
│  │                   頻繁整合      及早發現問題   快速回饋     │ │
│  │                   (每天多次)                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                               │                                 │
│                               ▼                                 │
│  持續交付（Continuous Delivery, CD）                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │  CI 成功 ──► 部署到測試環境 ──► 自動化測試 ──► 人工審核   │ │
│  │                                               ──► 部署    │ │
│  │                                                           │ │
│  │  程式碼隨時可以部署到生產環境（需要人工按鈕）              │ │
│  └───────────────────────────────────────────────────────────┘ │
│                               │                                 │
│                               ▼                                 │
│  持續部署（Continuous Deployment）                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │  CI 成功 ──► 自動部署到測試 ──► 自動部署到生產            │ │
│  │                                                           │ │
│  │  完全自動化，無需人工介入                                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.4.2 CloudMart CI/CD 流水線

```
┌─────────────────────────────────────────────────────────────────┐
│                CloudMart CI/CD 流水線                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐                                                    │
│  │ 開發者  │                                                    │
│  │ Push    │                                                    │
│  └────┬────┘                                                    │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    CI 階段                               │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │   │
│  │  │  程式碼  │  │  建構   │  │  單元   │  │  程式碼  │    │   │
│  │  │  檢出   │─►│  編譯   │─►│  測試   │─►│  掃描   │    │   │
│  │  │ Checkout│  │  Build  │  │  Test   │  │  Scan   │    │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │   │
│  └─────────────────────────────┬───────────────────────────┘   │
│                                │                                │
│                           成功？│                                │
│                    ┌───────────┴───────────┐                    │
│                   失敗                    成功                   │
│                    │                       │                    │
│                    ▼                       ▼                    │
│               通知開發者           ┌───────────────┐            │
│               修復問題             │   建構映像    │            │
│                                   │  Push to ACR  │            │
│                                   └───────┬───────┘            │
│                                           │                     │
│  ┌────────────────────────────────────────┼────────────────────┐│
│  │                    CD 階段             │                    ││
│  │                                        ▼                    ││
│  │  ┌─────────────────────────────────────────────────────┐   ││
│  │  │              部署到開發環境 (Dev)                    │   ││
│  │  │  • 自動部署                                          │   ││
│  │  │  • 自動冒煙測試                                      │   ││
│  │  └─────────────────────────┬───────────────────────────┘   ││
│  │                            │                                ││
│  │                            ▼                                ││
│  │  ┌─────────────────────────────────────────────────────┐   ││
│  │  │              部署到測試環境 (Staging)                │   ││
│  │  │  • 自動部署                                          │   ││
│  │  │  • 整合測試                                          │   ││
│  │  │  • 效能測試                                          │   ││
│  │  │  • 安全掃描                                          │   ││
│  │  └─────────────────────────┬───────────────────────────┘   ││
│  │                            │                                ││
│  │                       人工審核                              ││
│  │                            │                                ││
│  │                            ▼                                ││
│  │  ┌─────────────────────────────────────────────────────┐   ││
│  │  │              部署到生產環境 (Production)             │   ││
│  │  │  • 藍綠部署或金絲雀發布                              │   ││
│  │  │  • 健康檢查                                          │   ││
│  │  │  • 自動回滾機制                                      │   ││
│  │  └─────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.4.3 GitHub Actions 設定範例

```yaml
# .github/workflows/ci-cd.yml
# CloudMart CI/CD 流水線

name: CloudMart CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: cloudmart.azurecr.io
  IMAGE_NAME: order-service

jobs:
  # ========== CI 階段 ==========
  build-and-test:
    name: Build and Test
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run linter
        run: npm run lint

      - name: Run unit tests
        run: npm run test:unit -- --coverage

      - name: Upload coverage report
        uses: codecov/codecov-action@v3
        with:
          token: ${{ secrets.CODECOV_TOKEN }}

      - name: Run security scan
        run: npm audit --audit-level=high

      - name: Build application
        run: npm run build

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  # ========== 建構 Docker 映像 ==========
  build-image:
    name: Build Docker Image
    needs: build-and-test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Login to Azure Container Registry
        uses: azure/docker-login@v1
        with:
          login-server: ${{ env.REGISTRY }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}

  # ========== 部署到開發環境 ==========
  deploy-dev:
    name: Deploy to Development
    needs: build-image
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: development

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Login to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy to AKS (Dev)
        uses: azure/k8s-deploy@v4
        with:
          namespace: cloudmart-dev
          manifests: |
            k8s/deployment.yaml
            k8s/service.yaml
          images: |
            ${{ needs.build-image.outputs.image-tag }}

      - name: Run smoke tests
        run: |
          curl -f https://dev-api.cloudmart.com/health || exit 1

  # ========== 部署到測試環境 ==========
  deploy-staging:
    name: Deploy to Staging
    needs: [build-image, deploy-dev]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: staging

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Login to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy to AKS (Staging)
        uses: azure/k8s-deploy@v4
        with:
          namespace: cloudmart-staging
          manifests: |
            k8s/deployment.yaml
            k8s/service.yaml
          images: |
            ${{ needs.build-image.outputs.image-tag }}

      - name: Run integration tests
        run: npm run test:integration

      - name: Run performance tests
        run: npm run test:performance

  # ========== 部署到生產環境 ==========
  deploy-production:
    name: Deploy to Production
    needs: [build-image, deploy-staging]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Login to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy to AKS (Production) - Canary
        uses: azure/k8s-deploy@v4
        with:
          namespace: cloudmart-prod
          strategy: canary
          percentage: 20
          manifests: |
            k8s/deployment.yaml
            k8s/service.yaml
          images: |
            ${{ needs.build-image.outputs.image-tag }}

      - name: Monitor canary deployment
        run: |
          # 監控 5 分鐘，檢查錯誤率
          sleep 300
          ERROR_RATE=$(curl -s https://api.cloudmart.com/metrics/error-rate)
          if [ "$ERROR_RATE" -gt 1 ]; then
            echo "Error rate too high, rolling back"
            exit 1
          fi

      - name: Promote to 100%
        uses: azure/k8s-deploy@v4
        with:
          namespace: cloudmart-prod
          strategy: canary
          action: promote
          manifests: |
            k8s/deployment.yaml
```

---

## 7.5 基礎設施即程式碼（IaC）

### 7.5.1 為什麼需要 IaC？

```
┌─────────────────────────────────────────────────────────────────┐
│                  手動配置 vs. IaC                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  手動配置的問題：                                                │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  • 配置漂移：環境之間的差異隨時間累積                      │ │
│  │  • 無法追蹤：不知道誰在什麼時候改了什麼                    │ │
│  │  • 難以複製：建立新環境需要大量手動工作                    │ │
│  │  • 容易出錯：人為錯誤導致的故障                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  IaC 的優點：                                                    │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  • 版本控制：基礎設施的變更可以追蹤                        │ │
│  │  • 可重複性：可以精確地複製環境                            │ │
│  │  • 自動化：減少人為錯誤                                    │ │
│  │  • 文件化：程式碼本身就是文件                              │ │
│  │  • 審核：變更可以透過 PR 審核                              │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.5.2 Terraform 範例

```hcl
# main.tf
# CloudMart Azure 基礎設施

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "cloudmart-tfstate"
    storage_account_name = "cloudmarttfstate"
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

# 資源群組
resource "azurerm_resource_group" "main" {
  name     = "cloudmart-${var.environment}"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "CloudMart"
    ManagedBy   = "Terraform"
  }
}

# AKS 叢集
resource "azurerm_kubernetes_cluster" "main" {
  name                = "cloudmart-aks-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "cloudmart-${var.environment}"

  default_node_pool {
    name                = "default"
    node_count          = var.node_count
    vm_size             = var.node_size
    enable_auto_scaling = true
    min_count           = var.min_nodes
    max_count           = var.max_nodes
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
    network_policy = "calico"
  }

  tags = azurerm_resource_group.main.tags
}

# Container Registry
resource "azurerm_container_registry" "main" {
  name                = "cloudmart${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Premium"
  admin_enabled       = false

  tags = azurerm_resource_group.main.tags
}

# 輸出
output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}
```

---

## 7.6 章節總結

### 核心概念回顧

| 概念 | 說明 | 工具/服務 |
|------|------|----------|
| **版本控制** | 追蹤程式碼變更歷史 | Git, GitHub, Azure Repos |
| **分支策略** | 管理開發流程 | GitFlow, GitHub Flow |
| **CI** | 持續整合，自動建構測試 | GitHub Actions, Azure Pipelines |
| **CD** | 持續交付/部署 | GitHub Actions, Azure Pipelines |
| **IaC** | 基礎設施即程式碼 | Terraform, Bicep, ARM |

### AZ-900 考試重點

1. **Azure DevOps 服務**：Repos, Pipelines, Boards, Artifacts
2. **GitHub 與 Azure 整合**：GitHub Actions 部署到 Azure
3. **CI/CD 概念**：知道持續整合和持續交付的差異
4. **IaC 工具**：ARM Templates, Bicep

### 學習檢查清單

- [ ] 使用 Git 進行版本控制
- [ ] 設計適當的分支策略
- [ ] 建立 CI/CD 流水線
- [ ] 實作自動化測試
- [ ] 使用 IaC 管理基礎設施

---

**上一章：[第 6 章：事件驅動與自動化](./chapter-06.md)**

**下一章：[第 8 章：數位堡壘](./chapter-08.md)**
