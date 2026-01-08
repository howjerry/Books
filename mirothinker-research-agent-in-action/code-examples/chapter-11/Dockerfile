# 深度研究代理人 - API 服務 Dockerfile
# ================================================
# 第 11 章：生產環境部署

# =================================
# 建構階段
# =================================
FROM python:3.11-slim as builder

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案
COPY requirements.txt .

# 建立虛擬環境並安裝依賴
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =================================
# 生產階段
# =================================
FROM python:3.11-slim

# 安裝運行時依賴
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 從建構階段複製虛擬環境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 複製應用程式碼
COPY . .

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_ENV=production

# 建立非 root 使用者
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# 切換到非 root 使用者
USER appuser

# 暴露端口
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 啟動命令
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
