# 第 11 章：团队协作与开发工作流程 - Agent 开发生命周期管理

## 本章内容概览

- 理解 Agent 开发的特殊挑战
- 设计 Git-based 开发工作流程
- 实现自动化 CI/CD 管线
- 建立 Pull Request 审查标准
- 管理多环境部署策略
- 处理紧急修复与回滚
- 完成一个企业级 DevOps 系统

---

## 11.1 场景：混乱的多团队开发

### 真实挑战

你是 TechCorp 的 DevOps 负责人，公司有 8 个团队同时开发 50+ 个 Agent 系统。但你发现严重的协作问题：

**协作混乱统计**：
```
调查范围：8 个开发团队、50 个 Agent 项目
调查周期：2024 年 Q3

发现的问题：
- 🔥 生产环境事故：每月 12 次
  └─ 原因：未经测试直接部署 (67%)
  └─ 原因：配置错误 (21%)
  └─ 原因：版本冲突 (12%)

- 🐛 代码冲突：每周 23 次
  └─ 多人同时修改同一文件
  └─ 合并时发现测试失败
  └─ 浪费时间：平均 2.3 小时/次

- 📦 部署延迟：平均 4.5 天
  └─ 等待人工审查
  └─ 环境配置不一致
  └─ 依赖问题排查

- 💰 损失成本：每月 NT$ 1,250,000
  └─ 生产事故修复
  └─ 冲突解决时间
  └─ 延迟上线的机会成本
```

**实际案例 - 灾难性部署**：

```
2024-09-15 14:30 - 团队 A 部署客服 Agent v2.3.0
├─ ❌ 未运行完整测试套件（"本地测试过了，应该没问题"）
├─ ❌ 直接推送到生产环境（绕过 staging）
├─ ❌ 未通知相关团队
└─ 💥 结果：

14:32 - 生产环境错误率飙升至 85%
14:35 - 客户投诉电话激增
14:45 - 紧急回滚（但已造成损失）
15:30 - 事后分析会议

影响：
- 服务中断 58 分钟
- 影响 12,000+ 客户
- 业务损失：NT$ 380,000
- 声誉损害：客户满意度下降 12%
```

**根本原因**：
- 🚫 **缺乏标准流程**：每个团队自己决定如何部署
- 🚫 **手动操作过多**：测试、构建、部署都靠人工
- 🚫 **审查不彻底**：没有强制的 Code Review
- 🚫 **环境不一致**：dev/staging/prod 配置混乱
- 🚫 **缺乏回滚计划**：出问题后手忙脚乱

---

## 11.2 Git-based 开发工作流程

### 11.2.1 分支策略：Git Flow 变体

```mermaid
gitGraph
    commit id: "Initial"
    branch develop
    checkout develop
    commit id: "Setup"

    branch feature/customer-agent
    checkout feature/customer-agent
    commit id: "Add customer lookup"
    commit id: "Add tests"
    checkout develop
    merge feature/customer-agent tag: "PR #123"

    branch feature/order-agent
    checkout feature/order-agent
    commit id: "Implement order API"
    commit id: "Add validation"

    checkout develop
    branch release/v2.1.0
    checkout release/v2.1.0
    commit id: "Update version"
    commit id: "Final testing"

    checkout main
    merge release/v2.1.0 tag: "v2.1.0"

    branch hotfix/security-patch
    checkout hotfix/security-patch
    commit id: "Fix CVE-2024-1234"
    checkout main
    merge hotfix/security-patch tag: "v2.1.1"
    checkout develop
    merge hotfix/security-patch
```

**分支类型与用途**：

| 分支类型 | 命名规范 | 生命周期 | 用途 |
|---------|---------|---------|------|
| **main** | `main` | 永久 | 生产环境代码，每个 commit 都是可部署版本 |
| **develop** | `develop` | 永久 | 开发主线，集成所有完成的功能 |
| **feature** | `feature/agent-name`<br/>`feature/issue-123` | 临时 | 新功能开发，完成后合并到 develop |
| **release** | `release/v2.1.0` | 临时 | 发布准备，bug 修复、版本号更新 |
| **hotfix** | `hotfix/critical-bug`<br/>`hotfix/cve-2024-1234` | 临时 | 紧急修复，直接从 main 分支 |

### 11.2.2 开发工作流程

```python
# .github/workflows/developer-guide.md

## 开发新功能的标准流程

### 步骤 1：从 develop 创建 feature 分支
```bash
git checkout develop
git pull origin develop
git checkout -b feature/customer-sentiment-agent
```

### 步骤 2：开发与提交
```bash
# 遵循 Conventional Commits 规范
git add .
git commit -m "feat(customer): add sentiment analysis agent

- Implement emotion detection using Claude
- Add confidence scoring
- Include test cases with 95% coverage

Closes #456"
```

**Conventional Commits 格式**：
```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型（type）**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建工具、依赖更新

### 步骤 3：推送并创建 Pull Request
```bash
git push origin feature/customer-sentiment-agent
```

然后在 GitHub 创建 PR，填写模板：

```markdown
## 📝 变更描述
添加客户情绪分析 Agent，可自动识别客户消息的情绪倾向。

## 🎯 相关 Issue
Closes #456

## ✅ 变更类型
- [x] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 性能优化

## 🧪 测试
- [x] 单元测试通过（95% 覆盖率）
- [x] 集成测试通过
- [x] 手动测试完成

## 📸 截图/演示
<!-- 如果是 UI 变更，添加截图 -->

## 🔍 审查检查清单
- [x] 代码符合项目风格指南
- [x] 已添加/更新文档
- [x] 已添加/更新测试
- [x] 通过所有 CI 检查
- [x] 无安全漏洞
- [x] 已测试向后兼容性

## 🚀 部署注意事项
需要更新环境变量：
- `SENTIMENT_API_KEY`: Claude API 密钥
- `SENTIMENT_THRESHOLD`: 情绪阈值（默认 0.7）
```

### 步骤 4：Code Review
- 至少 2 名审查者批准
- 所有 CI 检查通过
- 无未解决的讨论

### 步骤 5：合并到 develop
```bash
# 使用 Squash Merge 保持历史清晰
gh pr merge --squash --delete-branch
```

### 步骤 6：发布流程
```bash
# 创建 release 分支
git checkout develop
git checkout -b release/v2.1.0

# 更新版本号
bump2version minor  # 2.0.5 -> 2.1.0

# 最后检查
npm run test:full
npm run build

# 合并到 main
git checkout main
git merge release/v2.1.0
git tag -a v2.1.0 -m "Release v2.1.0: Add sentiment analysis"
git push origin main --tags

# 同步回 develop
git checkout develop
git merge release/v2.1.0
git push origin develop
```

---

## 11.3 自动化 CI/CD 管线

### 11.3.1 完整 CI/CD 流程

```mermaid
graph LR
    A[Git Push] --> B[CI: 代码检查]
    B --> C[CI: 单元测试]
    C --> D[CI: 集成测试]
    D --> E[CI: 安全扫描]
    E --> F[CI: 构建镜像]
    F --> G{PR 合并?}

    G -->|是| H[CD: 部署到 Staging]
    G -->|否| Z[等待]

    H --> I[CD: 冒烟测试]
    I --> J{测试通过?}
    J -->|是| K[CD: 部署到 Production]
    J -->|否| L[回滚 Staging]

    K --> M[CD: 生产冒烟测试]
    M --> N{健康检查?}
    N -->|是| O[部署完成]
    N -->|否| P[自动回滚]

    style A fill:#e1f5ff
    style O fill:#d4edda
    style P fill:#f8d7da
    style L fill:#f8d7da
```

### 11.3.2 GitHub Actions 配置

```yaml
# .github/workflows/ci-cd.yml
name: Agent CI/CD Pipeline

on:
  push:
    branches: [main, develop, 'feature/**', 'release/**']
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'

jobs:
  # ========================================
  # Job 1: 代码质量检查
  # ========================================
  code-quality:
    name: Code Quality Checks
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install black flake8 mypy pylint

      - name: Run Black (格式检查)
        run: black --check .

      - name: Run Flake8 (代码风格)
        run: flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

      - name: Run MyPy (类型检查)
        run: mypy src/ --strict

      - name: Run Pylint (代码质量)
        run: pylint src/ --fail-under=8.0

  # ========================================
  # Job 2: 单元测试
  # ========================================
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: code-quality

    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run pytest
        run: |
          pytest tests/unit/ \
            --cov=src \
            --cov-report=xml \
            --cov-report=term \
            --cov-fail-under=80 \
            -v

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-${{ matrix.python-version }}

  # ========================================
  # Job 3: 集成测试
  # ========================================
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY_TEST }}
        run: pytest tests/integration/ -v

  # ========================================
  # Job 4: 安全扫描
  # ========================================
  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    needs: code-quality

    steps:
      - uses: actions/checkout@v4

      - name: Run Bandit (安全漏洞扫描)
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-report.json

      - name: Run Safety (依赖漏洞扫描)
        run: |
          pip install safety
          safety check --json

      - name: Run Trivy (容器镜像扫描)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # ========================================
  # Job 5: 构建 Docker 镜像
  # ========================================
  build-image:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, security-scan]
    if: github.event_name == 'push'

    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix={{branch}}-

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ========================================
  # Job 6: 部署到 Staging
  # ========================================
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: build-image
    if: github.ref == 'refs/heads/develop'
    environment:
      name: staging
      url: https://staging.agents.company.com

    steps:
      - uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG_STAGING }}

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/agent-service \
            agent-container=${{ needs.build-image.outputs.image-tag }} \
            -n staging

          kubectl rollout status deployment/agent-service -n staging

      - name: Run smoke tests
        run: |
          npm install -g newman
          newman run tests/postman/smoke-tests.json \
            --env-var "base_url=https://staging.agents.company.com"

      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "✅ Deployed to Staging: ${{ github.sha }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Staging Deployment Successful*\n\nCommit: `${{ github.sha }}`\nBranch: `develop`\nURL: https://staging.agents.company.com"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_STAGING }}

  # ========================================
  # Job 7: 部署到 Production
  # ========================================
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: build-image
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://agents.company.com

    steps:
      - uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG_PRODUCTION }}

      - name: Blue-Green Deployment
        run: |
          # 部署新版本到 green 环境
          kubectl apply -f k8s/deployment-green.yaml

          # 等待 green 环境就绪
          kubectl wait --for=condition=available \
            deployment/agent-service-green \
            -n production \
            --timeout=300s

          # 运行健康检查
          ./scripts/health-check.sh production green

          # 切换流量到 green
          kubectl patch service agent-service \
            -n production \
            -p '{"spec":{"selector":{"version":"green"}}}'

          # 等待 30 秒观察
          sleep 30

          # 再次健康检查
          ./scripts/health-check.sh production green

          # 删除旧的 blue 环境
          kubectl delete deployment agent-service-blue -n production

      - name: Create GitHub Release
        if: startsWith(github.ref, 'refs/tags/')
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false

      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "🚀 Deployed to Production: ${{ github.sha }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Production Deployment Successful*\n\n:rocket: Version: `${{ github.ref }}`\n:white_check_mark: Health: OK\n:link: URL: https://agents.company.com"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_PRODUCTION }}
```

---

## 11.4 Pull Request 审查最佳实践

### 11.4.1 审查检查清单

```markdown
# Pull Request 审查指南

## 🎯 审查目标
- 确保代码质量
- 捕获潜在 bug
- 维护架构一致性
- 知识分享与学习

## ✅ 代码审查检查清单

### 1. 功能正确性
- [ ] 代码实现符合需求
- [ ] 边界条件处理完整
- [ ] 错误处理恰当
- [ ] 无明显逻辑错误

### 2. 测试覆盖
- [ ] 新代码有相应测试
- [ ] 测试覆盖率 ≥ 80%
- [ ] 测试用例有意义
- [ ] 包含边界条件测试

### 3. 代码质量
- [ ] 命名清晰且符合规范
- [ ] 代码结构清晰
- [ ] 无重复代码
- [ ] 注释恰当（解释"为什么"而非"是什么"）
- [ ] 无过长函数（< 50 行）
- [ ] 无过深嵌套（< 4 层）

### 4. 安全性
- [ ] 无 SQL 注入风险
- [ ] 无 XSS 风险
- [ ] 敏感数据已加密
- [ ] API 密钥未硬编码
- [ ] 输入验证完整

### 5. 性能
- [ ] 无 N+1 查询问题
- [ ] 数据库查询已优化
- [ ] 无内存泄漏
- [ ] 大数据处理有分页/流式

### 6. 向后兼容性
- [ ] API 变更有版本管理
- [ ] 数据库迁移可回滚
- [ ] 配置变更有文档
- [ ] 不破坏现有功能

### 7. 文档
- [ ] README 已更新
- [ ] API 文档已更新
- [ ] 复杂逻辑有注释
- [ ] 配置变更有说明

## 💬 审查反馈指南

### 反馈分类
- **Critical（必须修改）**: 阻止合并的问题
  - 例：安全漏洞、严重 bug、架构违反
- **Major（强烈建议）**: 应该修改的问题
  - 例：代码质量问题、测试不足
- **Minor（建议）**: 可选的改进
  - 例：命名优化、注释补充
- **Nitpick（吹毛求疵）**: 个人偏好
  - 例：空格、换行

### 反馈示例

#### ❌ 不好的反馈
```
这段代码写得不好。
```

#### ✅ 好的反馈
```
[Major] 这个函数过长（120 行），建议拆分：

1. 提取参数验证逻辑到 validate_input()
2. 提取数据库操作到 save_to_db()
3. 提取通知逻辑到 send_notification()

参考：Clean Code 第 3 章 - 函数应该只做一件事

建议重构：
```python
def process_order(order_data):
    validated_data = validate_input(order_data)
    order_id = save_to_db(validated_data)
    send_notification(order_id)
    return order_id
```
```

## 🚀 审查流程

### 时间要求
- **首次响应**: 24 小时内
- **完整审查**: 48 小时内
- **紧急 PR**: 4 小时内

### 审查者数量
- **功能 PR**: 至少 1 人
- **架构变更**: 至少 2 人
- **安全相关**: 至少 1 人 + 安全团队

### 自动检查
PR 必须通过所有自动检查才能合并：
- ✅ CI 测试全部通过
- ✅ 代码覆盖率 ≥ 80%
- ✅ 无安全漏洞
- ✅ 代码风格检查通过
```

### 11.4.2 自动化审查工具

```yaml
# .github/workflows/pr-checks.yml
name: PR Checks

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  pr-size-check:
    name: Check PR Size
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Check changed lines
        run: |
          CHANGED_LINES=$(git diff --stat origin/${{ github.base_ref }}...HEAD | tail -1 | awk '{print $4+$6}')
          echo "Changed lines: $CHANGED_LINES"

          if [ "$CHANGED_LINES" -gt 500 ]; then
            echo "::error::PR too large ($CHANGED_LINES lines). Please split into smaller PRs."
            exit 1
          fi

  pr-description-check:
    name: Check PR Description
    runs-on: ubuntu-latest
    steps:
      - name: Validate description
        uses: actions/github-script@v7
        with:
          script: |
            const pr = context.payload.pull_request;
            const body = pr.body || '';

            // 检查是否填写了必要内容
            const requiredSections = [
              '## 📝 变更描述',
              '## 🎯 相关 Issue',
              '## ✅ 变更类型',
              '## 🧪 测试'
            ];

            const missingSections = requiredSections.filter(
              section => !body.includes(section)
            );

            if (missingSections.length > 0) {
              core.setFailed(
                `PR description missing required sections:\n${missingSections.join('\n')}`
              );
            }

  complexity-check:
    name: Code Complexity Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install radon
        run: pip install radon

      - name: Check complexity
        run: |
          radon cc src/ -a -nb
          radon cc src/ -nc -nb > complexity.txt

          # 检查是否有复杂度过高的函数
          if grep -q "F " complexity.txt; then
            echo "::error::Found functions with F complexity rating"
            cat complexity.txt
            exit 1
          fi
```

---

## 11.5 多环境管理

### 11.5.1 环境配置策略

```
环境层级：
dev → staging → production

配置管理：
- 使用 Kubernetes ConfigMaps 和 Secrets
- 环境变量分离
- 敏感信息使用 Vault/AWS Secrets Manager
```

```yaml
# k8s/base/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-config
data:
  LOG_LEVEL: "info"
  MAX_RETRIES: "3"
  TIMEOUT: "30"

---
# k8s/overlays/staging/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-config
data:
  LOG_LEVEL: "debug"  # staging 使用 debug
  API_URL: "https://staging-api.company.com"

---
# k8s/overlays/production/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-config
data:
  LOG_LEVEL: "warn"  # production 只记录警告和错误
  API_URL: "https://api.company.com"
  ENABLE_CACHE: "true"
  CACHE_TTL: "3600"
```

---

## 11.6 紧急修复流程 (Hotfix)

### 11.6.1 Hotfix 工作流程

```mermaid
sequenceDiagram
    participant P as 生产环境
    participant O as On-call 工程师
    participant M as Main 分支
    participant H as Hotfix 分支
    participant D as Develop 分支

    P->>O: 🚨 报警：严重 bug
    O->>O: 1. 确认问题严重性
    O->>M: 2. 从 main 创建 hotfix 分支
    M->>H: git checkout -b hotfix/critical-bug

    O->>H: 3. 修复 bug
    O->>H: 4. 添加测试
    O->>H: 5. 本地验证

    H->>M: 6. 合并到 main
    M->>P: 7. 紧急部署

    P->>O: 8. 验证修复

    H->>D: 9. 同步到 develop

    Note over O: 10. 编写事后分析报告
```

### 11.6.2 Hotfix 自动化

```bash
# scripts/hotfix.sh
#!/bin/bash
set -e

# Hotfix 自动化脚本

echo "🚨 Hotfix 流程启动"

# 1. 检查当前状态
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ 工作目录不干净，请先提交或stash更改"
    exit 1
fi

# 2. 获取 hotfix 描述
read -p "Hotfix 简短描述（例如：fix-memory-leak）: " HOTFIX_NAME
BRANCH_NAME="hotfix/$HOTFIX_NAME"

# 3. 从 main 创建分支
echo "📌 从 main 创建 $BRANCH_NAME"
git checkout main
git pull origin main
git checkout -b "$BRANCH_NAME"

echo "✅ Hotfix 分支已创建"
echo "请在此分支上修复问题，然后运行: ./scripts/deploy-hotfix.sh"
```

```bash
# scripts/deploy-hotfix.sh
#!/bin/bash
set -e

echo "🚀 部署 Hotfix"

CURRENT_BRANCH=$(git branch --show-current)

if [[ ! $CURRENT_BRANCH =~ ^hotfix/ ]]; then
    echo "❌ 当前不在 hotfix 分支"
    exit 1
fi

# 1. 运行测试
echo "🧪 运行测试..."
pytest tests/ -v

# 2. 更新版本号（patch 版本）
echo "📦 更新版本号..."
bump2version patch

NEW_VERSION=$(grep "current_version" .bumpversion.cfg | cut -d= -f2 | tr -d ' ')

# 3. 提交
git add .
git commit -m "hotfix: $CURRENT_BRANCH - v$NEW_VERSION"

# 4. 合并到 main
echo "🔀 合并到 main..."
git checkout main
git merge --no-ff "$CURRENT_BRANCH"
git tag -a "v$NEW_VERSION" -m "Hotfix: v$NEW_VERSION"

# 5. 推送
echo "⬆️ 推送到远程..."
git push origin main
git push origin "v$NEW_VERSION"

# 6. 触发 CI/CD（自动部署到生产）
echo "⏳ 等待 CI/CD 部署..."
echo "监控地址：https://github.com/$GITHUB_REPOSITORY/actions"

# 7. 同步到 develop
echo "🔄 同步到 develop..."
git checkout develop
git pull origin develop
git merge --no-ff "$CURRENT_BRANCH"
git push origin develop

# 8. 清理
git branch -d "$CURRENT_BRANCH"

echo "✅ Hotfix 部署完成！"
echo "版本：v$NEW_VERSION"
echo "请监控生产环境，确保问题已解决"
```

---

## 11.7 实际效益

### 11.7.1 实施前后对比（TechCorp，6 个月数据）

| 指标 | 实施前 | 实施后 | 改善 |
|------|-------|--------|------|
| **生产事故** | 12 次/月 | 1.2 次/月 | **-90%** |
| **代码冲突** | 23 次/周 | 3 次/周 | **-87%** |
| **部署时间** | 4.5 天 | 45 分钟 | **-98%** |
| **测试覆盖率** | 52% | 91% | **+75%** |
| **回滚率** | 18% | 2% | **-89%** |
| **平均修复时间** | 4.2 小时 | 38 分钟 | **-85%** |

**成本节省**：
- 减少生产事故损失：NT$ 1,100,000/月
- 提升开发效率：节省 120 人时/月
- 减少延迟上线成本：NT$ 800,000/月
- **总节省**：NT$ 1,900,000/月

**ROI**：
- 初始投入：NT$ 1,200,000（工具、培训、流程建立）
- 月度运营成本：NT$ 180,000
- **回收期**：0.9 个月
- **年化 ROI**：1,267%

---

## 11.8 章节总结

### 你已经学会了什么

✅ **Git 工作流程**
   - Git Flow 分支策略
   - Conventional Commits 规范
   - PR 创建与合并流程

✅ **CI/CD 管线**
   - 代码质量检查
   - 自动化测试
   - 安全扫描
   - 多环境部署
   - Blue-Green 部署

✅ **Code Review**
   - 审查检查清单
   - 反馈最佳实践
   - 自动化审查工具

✅ **环境管理**
   - Dev/Staging/Production 分离
   - 配置管理
   - Secrets 管理

✅ **紧急修复**
   - Hotfix 流程
   - 自动化脚本
   - 事后分析

### 检查清单

建立 DevOps 体系前，请确认：

- [ ] **定义分支策略**（Git Flow 或其他）
- [ ] **建立 PR 模板**
- [ ] **配置 CI/CD 管线**
- [ ] **设置代码审查规则**
- [ ] **分离环境配置**
- [ ] **准备 Hotfix 流程**
- [ ] **建立监控告警**
- [ ] **培训团队成员**

---

## 11.9 下一章预告

**第 12 章：成本优化与资源管理 - 打造高效益的 Agent 系统**

你将学到：
- 多维度成本追踪（API、计算、存储、人力）
- Model Router 智能选择（Haiku/Sonnet/Opus）
- Prompt Caching 策略
- 预算预警与自动限流
- Token 使用优化
- ROI 计算框架

**实战项目**：建立完整的成本管理与优化系统，实现成本降低 50%+ 的目标。

准备好探索 Agent 成本优化的最佳实践了吗？让我们继续前进！

---

**章节完成时间**：约 90-120 分钟
**难度等级**：⭐⭐⭐⭐ (4/5 - 进阶)
**前置要求**：完成第 1-10 章，熟悉 Git 与 CI/CD
