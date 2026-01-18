"""文件搜尋工具"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class DocSearchInput(BaseModel):
    """文件搜尋參數"""
    query: str = Field(description="搜尋關鍵字")
    source: str = Field(
        default="all",
        description="文件來源：python, javascript, docker, kubernetes, all"
    )


# 模擬的文件資料庫
MOCK_DOCS = {
    "python": {
        "list comprehension": """列表推導式是 Python 中創建列表的簡潔方式。

基本語法：[expression for item in iterable if condition]

範例：
```python
# 建立 1-10 的平方數
squares = [x**2 for x in range(1, 11)]
```""",
        "async await": """Python 3.5+ 支援 async/await 語法進行異步編程。

關鍵概念：
- async def：定義異步函數
- await：等待異步操作完成
- asyncio.run()：運行異步主函數

範例：
```python
import asyncio

async def fetch_data():
    await asyncio.sleep(1)
    return "data"

asyncio.run(fetch_data())
```""",
        "decorator": """裝飾器是修改函數行為的語法糖。

基本語法：
```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before")
        result = func(*args, **kwargs)
        print("After")
        return result
    return wrapper

@my_decorator
def say_hello():
    print("Hello!")
```""",
    },
    "docker": {
        "dockerfile": """Dockerfile 用於定義 Docker 映像的建置步驟。

常用指令：
- FROM: 基礎映像
- RUN: 執行命令
- COPY: 複製檔案
- CMD: 容器啟動命令

範例：
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```""",
        "compose": """Docker Compose 用於定義和運行多容器應用。

範例 docker-compose.yml：
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
```""",
    },
    "kubernetes": {
        "pod": """Pod 是 Kubernetes 中最小的部署單位。

特點：
- 包含一個或多個容器
- 共享網路和存儲
- 通常由 Deployment 管理

範例：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
  - name: app
    image: nginx:latest
```""",
        "deployment": """Deployment 管理 Pod 的副本集和更新策略。

範例：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:v1
```""",
    },
}


@tool(args_schema=DocSearchInput)
def search_documentation(query: str, source: str = "all") -> str:
    """搜尋技術文件庫。

    用於查詢程式語言文件、框架 API、最佳實踐等。
    當使用者詢問特定技術的用法或細節時使用。

    Returns:
        搜尋結果的摘要，包含相關文件片段
    """
    results = []
    query_lower = query.lower()

    for src, docs in MOCK_DOCS.items():
        # 過濾來源
        if source != "all" and src != source:
            continue

        for keyword, content in docs.items():
            # 簡單的關鍵字匹配
            if query_lower in keyword.lower() or query_lower in content.lower():
                results.append(f"📚 [{src.upper()}] {keyword}\n{content}")

    if results:
        return "\n\n---\n\n".join(results[:3])  # 最多返回 3 個結果

    return f"未找到關於 '{query}' 的文件。建議：\n1. 檢查拼寫\n2. 使用更通用的關鍵字\n3. 指定特定的文件來源（python, docker, kubernetes）"
