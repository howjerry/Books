# Terminology Standards for Claude Skills Technical Book

## Capitalization Rules

### Proper Nouns (Always Capitalized)
- **Claude Code**: The platform
- **Skills**: When referring to the feature (e.g., "Claude Code Skills", "MCP Skills")
- **skill/skills**: Lowercase when used as common noun (e.g., "this skill performs", "register a skill")
- **WebGuard**: The book's main project
- **MCP**: Model Context Protocol
- **Stagehand**: The browser automation framework
- **Python**: The programming language
- **TypeScript**: The programming language
- **Docker**: The containerization platform
- **Kubernetes**: The orchestration platform
- **Playwright**: The testing framework
- **Selenium**: The testing framework
- **API**: Application Programming Interface (when standalone)
- **REST**: Representational State Transfer
- **CI/CD**: Continuous Integration/Continuous Deployment
- **Celery**: The task queue
- **Redis**: The cache system
- **PostgreSQL**: The database

### Lowercase in Technical Contexts
- **python**: In commands (e.g., `python script.py`, `python3.11`)
- **docker**: In filenames and directories (e.g., `docker/`, `Dockerfile`, `docker-compose.yml`)
- **kubernetes**: In YAML fields and configs (e.g., `kubernetes.io/ingress`)
- **typescript**: In code block language identifiers (e.g., ` ```typescript `)
- **api**: In variable/function names (e.g., `api_key`, `api_config`, `api_endpoint`)
- **skill**: In variable/function names (e.g., `skill_executor`, `register_skill`)

### Code Identifiers
- **Python**: Use `snake_case` for variables and functions
- **TypeScript/JavaScript**: Use `camelCase` for variables and functions
- **Classes**: Use `PascalCase` (e.g., `BrowserLoginTester`, `PerformanceAnalyzer`)
- **Constants**: Use `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)

## Consistency Rules

### File Paths and Directories
- Use forward slashes `/` consistently
- Use lowercase for directory names in paths (e.g., `src/skills/browser/`)
- Preserve original casing for actual filenames (e.g., `SKILL.md`, `README.md`)

### Commands and Code
- Preserve exact casing as required by the tool
- Command names are lowercase (e.g., `npm`, `pip`, `pytest`)
- Package names follow their official casing (e.g., `@browserbasehq/stagehand`)

### Chinese Technical Terms
- **測試**: Test/Testing
- **部署**: Deployment
- **監控**: Monitoring
- **驗證**: Validation
- **瀏覽器**: Browser
- **自動化**: Automation

## Cross-Reference Format
- Use format: "詳見 Chapter X.Y" or "參見 Chapter X"
- Chapter numbers use Arabic numerals: Chapter 1, Chapter 2, etc.
- Section numbers use decimal notation: 5.2.3

## Version Numbers
- Use semantic versioning format: MAJOR.MINOR.PATCH (e.g., 3.0.0, 1.2.5)
- Always include all three parts

## URLs and Links
- Use full HTTPS URLs when possible
- Preserve original casing in URLs
- Use angle brackets for standalone URLs in markdown: `<https://example.com>`

## Status: VERIFIED ✓
All chapters (1-10) have been reviewed and found to be consistent with these standards.
Last review: 2025-11-08
