FROM python:3.11-slim

WORKDIR /app

# 安裝依賴
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# 執行應用
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
