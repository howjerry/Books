# Code Examples - Claude Skills in Action

This directory contains all code examples from the book, organized by chapter.

## Structure

```
code-examples/
├── chapter-02/          # 開發環境設置與第一個 Skill
├── chapter-04/          # Stagehand 瀏覽器自動化實戰
├── chapter-05/          # 數據與文件處理自動化
├── chapter-06/          # API 測試與整合驗證
├── chapter-07/          # Skills 進階模式與組合技巧
├── chapter-08/          # 測試自動化與 CI/CD 整合
├── chapter-09/          # 完整測試系統架構（WebGuard）
└── chapter-10/          # 企業部署、安全與 MCP 生態
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Claude API key

### Setup
```bash
# Install Python dependencies
poetry install

# Install Node.js dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Run Examples

**Chapter 2: First Skill**
```bash
python chapter-02/web_health_check.py https://example.com
python chapter-02/test_health_check.py
```

**Chapter 4: Browser Automation**
```bash
node chapter-04/stagehand_basics.js
python chapter-04/login_test_skill.py
```

**Chapter 5: Data Processing**
```bash
python chapter-05/excel_processor.py
python chapter-05/pdf_validator.py
```

**Chapter 6: API Testing**
```bash
python chapter-06/rest_api_tester.py
python chapter-06/graphql_tester.py
```

**Chapter 7: Advanced Patterns**
```bash
python chapter-07/skill_composition.py
python chapter-07/parallel_execution.py
```

**Chapter 8: CI/CD Integration**
```bash
# GitHub Actions workflow is in chapter-08/
# See .github/workflows/webguard-tests.yml
```

**Chapter 9: Complete System**
```bash
cd chapter-09/webguard_complete
docker-compose up -d
python run_tests.py
```

**Chapter 10: Enterprise Deployment**
```bash
python chapter-10/security_config.py
python chapter-10/monitoring_setup.py
```

## Code Standards

All examples follow:
- PEP 8 (Python)
- ESLint + Prettier (JavaScript/TypeScript)
- Type hints where applicable
- Comprehensive error handling
- Detailed comments

## Testing

Each example includes tests:
```bash
# Run all tests
pytest

# Run specific chapter tests
pytest chapter-02/tests/
```

## License

MIT License - See LICENSE file

## Support

- GitHub Issues: https://github.com/manning/claude-skills-in-action/issues
- Author Forum: https://forums.manning.com/
- Discord Community: [Link]
