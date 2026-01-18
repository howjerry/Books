"""API 調用工具"""

from typing import Literal
from urllib.parse import urlparse

from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 嘗試導入 httpx，如果沒有則使用 urllib
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import urllib.request
    import json
    HAS_HTTPX = False


class APIRequestInput(BaseModel):
    """API 請求參數"""
    method: Literal["GET", "POST"] = Field(description="HTTP 方法")
    url: str = Field(description="API 端點 URL")
    params: dict | None = Field(default=None, description="查詢參數（GET 時使用）")
    body: dict | None = Field(default=None, description="請求體（POST 時使用）")


# 允許調用的 API 域名白名單
ALLOWED_DOMAINS = [
    "api.github.com",
    "api.coindesk.com",
    "api.openweathermap.org",
    "httpbin.org",  # 用於測試
    "jsonplaceholder.typicode.com",  # 用於測試
]


def _make_request_httpx(method: str, url: str, params: dict | None, body: dict | None) -> str:
    """使用 httpx 發送請求"""
    with httpx.Client(timeout=10.0) as client:
        if method == "GET":
            response = client.get(url, params=params)
        else:
            response = client.post(url, json=body)

        response.raise_for_status()
        return response.text[:2000]


def _make_request_urllib(method: str, url: str, params: dict | None, body: dict | None) -> str:
    """使用 urllib 發送請求（備用）"""
    import json

    if method == "GET" and params:
        from urllib.parse import urlencode
        url = f"{url}?{urlencode(params)}"

    req = urllib.request.Request(url)
    req.add_header("User-Agent", "TechAssist/1.0")

    if method == "POST" and body:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    else:
        data = None

    with urllib.request.urlopen(req, data=data, timeout=10) as response:
        return response.read().decode("utf-8")[:2000]


@tool(args_schema=APIRequestInput)
def call_api(
    method: str,
    url: str,
    params: dict | None = None,
    body: dict | None = None
) -> str:
    """調用外部 API。

    用於獲取即時資料、與外部服務互動。

    安全限制：
    - 只能調用預先授權的 API 端點
    - 請求超時限制為 10 秒
    - 回應大小限制為 2000 字元

    允許的 API 域名：
    - api.github.com
    - api.coindesk.com
    - api.openweathermap.org
    - httpbin.org (測試用)
    - jsonplaceholder.typicode.com (測試用)

    Returns:
        API 回應的文本內容或錯誤訊息
    """
    # 安全檢查：驗證域名
    try:
        parsed = urlparse(url)
        domain = parsed.netloc

        if domain not in ALLOWED_DOMAINS:
            return f"錯誤：不允許調用 '{domain}'。\n\n允許的域名：\n" + "\n".join(f"- {d}" for d in ALLOWED_DOMAINS)

    except Exception as e:
        return f"錯誤：無效的 URL - {e}"

    # 發送請求
    try:
        if HAS_HTTPX:
            result = _make_request_httpx(method, url, params, body)
        else:
            result = _make_request_urllib(method, url, params, body)

        return f"API 回應：\n{result}"

    except Exception as e:
        error_type = type(e).__name__

        if "Timeout" in error_type or "timeout" in str(e).lower():
            return "錯誤：API 請求超時（超過 10 秒）"
        elif "Connect" in error_type or "connection" in str(e).lower():
            return "錯誤：無法連接到 API 伺服器"
        elif "404" in str(e):
            return "錯誤：API 端點不存在 (404)"
        elif "401" in str(e) or "403" in str(e):
            return "錯誤：API 認證失敗，請檢查 API 金鑰"
        else:
            return f"錯誤：API 請求失敗 - {e}"
