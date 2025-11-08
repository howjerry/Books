# 第 6 章
> 🔗 **技能整合**：API 測試與瀏覽器測試（**Chapter 4**）、數據處理（**Chapter 5**）共同構成完整的測試覆蓋。
：API 測試與整合驗證

現代 Web 應用程式架構通常採用前後端分離，後端透過 REST API、GraphQL 等方式提供服務。API 測試是確保系統穩定性的關鍵：一個前端 UI 的錯誤可能只影響視覺，但 API 的錯誤會導致數據錯誤、安全漏洞、服務中斷。本章將探討如何使用 Claude Code Skills 自動化 API 測試，涵蓋 REST/GraphQL 測試、認證處理、契約測試、性能驗證，並整合到 WebGuard 測試系統。

## 6.1 REST API 測試基礎

### 6.1.1 為什麼需要自動化 API 測試？

相較於 UI 測試，API 測試具有顯著優勢：

- **速度快**：無需啟動瀏覽器，直接 HTTP 請求，執行速度快 10-100 倍
- **穩定性高**：不受前端改版影響，API 契約通常更穩定
- **覆蓋率廣**：可測試所有業務邏輯，包括前端無法觸及的邊界情況
- **CI/CD 友善**：輕量級，適合在 CI 管道中高頻執行

**典型應用場景：**

- **冒煙測試（Smoke Tests）**：部署後快速驗證核心 API 可用
- **整合測試**：驗證多個微服務間的協作
- **契約測試**：確保 API 提供者與消費者的契約不被破壞
- **性能基準測試**：監控 API 響應時間、吞吐量

### 6.1.2 技術選型：Requests + httpx

Python 生態系統有兩大 HTTP 客戶端：

| 工具 | 優點 | 缺點 | 適用場景 |
|------|------|------|----------|
| **Requests** | 簡單易用、生態成熟、同步 API | 不支持 HTTP/2、async | 傳統同步測試 |
| **httpx** | 支持 async、HTTP/2、API 與 Requests 相似 | 相對較新 | 高並發、現代應用 |

我們將以 **Requests** 為主（成熟穩定），並示範 **httpx** 處理異步場景。

### 6.1.3 實作：APITester 基礎類別

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any, Optional, List
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class APITester:
    """
    REST API 測試器

    提供 HTTP 請求、響應驗證、重試、日誌等功能
    """

    def __init__(
        self,
        base_url: str,
        auth_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        初始化 API 測試器

        Args:
            base_url: API 基礎 URL（如 https://api.example.com）
            auth_token: 認證 Token（會自動加到 Authorization header）
            timeout: 請求超時時間（秒）
            max_retries: 最大重試次數（針對網絡錯誤）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

        # 設置重試策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,  # 指數退避：1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 設置認證
        if auth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {auth_token}'
            })

        # 測試歷史（可用於生成報告）
        self.test_history: List[Dict[str, Any]] = []

    def test_endpoint(
        self,
        method: str,
        endpoint: str,
        expected_status: int = 200,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        validate_schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        測試 API 端點

        Args:
            method: HTTP 方法（GET, POST, PUT, PATCH, DELETE）
            endpoint: API 端點路徑（如 /users/123）
            expected_status: 預期 HTTP 狀態碼
            json_data: 請求 body（JSON）
            params: URL 查詢參數
            headers: 額外 HTTP headers
            validate_schema: JSON Schema 驗證規則

        Returns:
            測試結果字典

        Example:
            >>> tester = APITester("https://api.example.com")
            >>> result = tester.test_endpoint(
            ...     "POST",
            ...     "/users",
            ...     json_data={"name": "Alice"},
            ...     expected_status=201
            ... )
            >>> assert result['success']
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        start_time = time.time()

        try:
            # 合併 headers
            merged_headers = self.session.headers.copy()
            if headers:
                merged_headers.update(headers)

            # 發送請求
            response = self.session.request(
                method=method.upper(),
                url=url,
                json=json_data,
                params=params,
                headers=merged_headers,
                timeout=self.timeout
            )

            elapsed_ms = (time.time() - start_time) * 1000

            # 解析響應
            try:
                response_body = response.json()
            except requests.exceptions.JSONDecodeError:
                response_body = response.text

            # 狀態碼驗證
            status_match = response.status_code == expected_status

            # JSON Schema 驗證（如果提供）
            schema_valid = True
            schema_errors = []
            if validate_schema and status_match:
                schema_valid, schema_errors = self._validate_json_schema(
                    response_body,
                    validate_schema
                )

            # 構建結果
            result = {
                "success": status_match and schema_valid,
                "method": method.upper(),
                "url": url,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "response_time_ms": round(elapsed_ms, 2),
                "response_body": response_body,
                "response_headers": dict(response.headers),
                "timestamp": datetime.now().isoformat()
            }

            if not status_match:
                result["error"] = (
                    f"狀態碼不符: 期望 {expected_status}, "
                    f"實際 {response.status_code}"
                )

            if not schema_valid:
                result["schema_errors"] = schema_errors

            # 記錄到測試歷史
            self.test_history.append(result)

            # 日誌
            log_level = logging.INFO if result['success'] else logging.WARNING
            logger.log(
                log_level,
                f"{method} {endpoint} -> {response.status_code} "
                f"({elapsed_ms:.0f}ms)"
            )

            return result

        except requests.exceptions.Timeout:
            error_result = {
                "success": False,
                "method": method.upper(),
                "url": url,
                "error": f"請求超時（>{self.timeout}s）",
                "timestamp": datetime.now().isoformat()
            }
            self.test_history.append(error_result)
            logger.error(f"{method} {endpoint} 超時")
            return error_result

        except requests.exceptions.RequestException as e:
            error_result = {
                "success": False,
                "method": method.upper(),
                "url": url,
                "error": f"請求失敗: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            self.test_history.append(error_result)
            logger.error(f"{method} {endpoint} 失敗: {e}")
            return error_result

    def _validate_json_schema(
        self,
        data: Any,
        schema: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        驗證 JSON 數據是否符合 Schema

        使用 jsonschema 庫進行驗證
        """
        try:
            from jsonschema import validate, ValidationError
        except ImportError:
            logger.warning("jsonschema 未安裝，跳過 schema 驗證")
            return True, []

        try:
            validate(instance=data, schema=schema)
            return True, []
        except ValidationError as e:
            return False, [str(e)]

    def batch_test(
        self,
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量執行測試案例

        Args:
            test_cases: 測試案例列表，每個案例包含 test_endpoint 的參數

        Returns:
            批量測試結果摘要

        Example:
            >>> test_cases = [
            ...     {"method": "GET", "endpoint": "/users/1", "expected_status": 200},
            ...     {"method": "GET", "endpoint": "/users/999", "expected_status": 404}
            ... ]
            >>> summary = tester.batch_test(test_cases)
            >>> print(summary['pass_rate'])
        """
        results = []

        for case in test_cases:
            result = self.test_endpoint(**case)
            results.append(result)

        passed = sum(1 for r in results if r['success'])
        failed = len(results) - passed

        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed / len(results) * 100:.2f}%" if results else "0%",
            "results": results
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        獲取性能指標（基於測試歷史）

        Returns:
            性能統計（平均響應時間、最慢端點等）
        """
        if not self.test_history:
            return {"error": "無測試歷史"}

        response_times = [
            r['response_time_ms']
            for r in self.test_history
            if 'response_time_ms' in r
        ]

        if not response_times:
            return {"error": "無有效響應時間數據"}

        return {
            "total_requests": len(self.test_history),
            "avg_response_time_ms": round(sum(response_times) / len(response_times), 2),
            "min_response_time_ms": round(min(response_times), 2),
            "max_response_time_ms": round(max(response_times), 2),
            "slowest_endpoint": max(
                self.test_history,
                key=lambda x: x.get('response_time_ms', 0)
            )['url']
        }
```

### 6.1.4 進階功能：認證處理

實際 API 測試中，認證是最常見的挑戰。以下擴展 APITester 支持多種認證方式：

```python
class AuthenticatedAPITester(APITester):
    """支持多種認證方式的 API 測試器"""

    def set_bearer_token(self, token: str):
        """設置 Bearer Token 認證"""
        self.session.headers.update({
            'Authorization': f'Bearer {token}'
        })

    def set_api_key(self, key: str, header_name: str = 'X-API-Key'):
        """設置 API Key 認證"""
        self.session.headers.update({
            header_name: key
        })

    def set_basic_auth(self, username: str, password: str):
        """設置 HTTP Basic Auth"""
        from requests.auth import HTTPBasicAuth
        self.session.auth = HTTPBasicAuth(username, password)

    def login_and_get_token(
        self,
        login_endpoint: str,
        username: str,
        password: str,
        token_path: str = 'access_token'
    ) -> Optional[str]:
        """
        執行登入並獲取 Token

        Args:
            login_endpoint: 登入 API 端點（如 /auth/login）
            username: 用戶名
            password: 密碼
            token_path: Token 在響應中的路徑（支持嵌套，如 data.token）

        Returns:
            Token 字串，失敗返回 None

        Example:
            >>> token = tester.login_and_get_token(
            ...     "/auth/login",
            ...     "admin",
            ...     "admin123",
            ...     token_path="data.access_token"
            ... )
            >>> if token:
            ...     tester.set_bearer_token(token)
        """
        result = self.test_endpoint(
            method="POST",
            endpoint=login_endpoint,
            json_data={"username": username, "password": password},
            expected_status=200
        )

        if not result['success']:
            logger.error("登入失敗")
            return None

        # 從響應中提取 Token（支持嵌套路徑）
        response_body = result['response_body']
        token_value = response_body

        for key in token_path.split('.'):
            if isinstance(token_value, dict) and key in token_value:
                token_value = token_value[key]
            else:
                logger.error(f"Token 路徑 {token_path} 無效")
                return None

        self.set_bearer_token(token_value)
        logger.info("成功獲取並設置 Token")
        return token_value

    def refresh_token(
        self,
        refresh_endpoint: str,
        refresh_token: str
    ) -> Optional[str]:
        """
        刷新 Token（適用於 JWT 等需要定期刷新的場景）

        Args:
            refresh_endpoint: 刷新 Token 的端點
            refresh_token: 刷新用的 Token

        Returns:
            新的 Access Token
        """
        result = self.test_endpoint(
            method="POST",
            endpoint=refresh_endpoint,
            json_data={"refresh_token": refresh_token},
            expected_status=200
        )

        if result['success']:
            new_token = result['response_body'].get('access_token')
            if new_token:
                self.set_bearer_token(new_token)
                return new_token

        return None
```


## 6.2 GraphQL API 測試

### 6.2.1 GraphQL vs REST

GraphQL 是一種查詢語言和 API 規範，相較於 REST：

- **單一端點**：通常只有一個 `/graphql` 端點，透過 query/mutation 區分操作
- **靈活查詢**：客戶端指定需要的欄位，避免 over-fetching
- **強類型 Schema**：提供 introspection，可自動生成文檔和測試

**測試挑戰：**

- 所有請求都是 POST，無法用 HTTP 方法區分操作類型
- 錯誤可能返回 200 狀態碼（錯誤在響應 body 的 `errors` 欄位）
- 需要驗證 Schema 相容性

### 6.2.2 實作：GraphQLTester

```python
import requests
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class GraphQLTester:
    """
    GraphQL API 測試器

    支持 query、mutation、subscription 測試
    """

    def __init__(
        self,
        endpoint: str,
        auth_token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        初始化 GraphQL 測試器

        Args:
            endpoint: GraphQL 端點 URL（通常是 /graphql）
            auth_token: 認證 Token
            timeout: 請求超時時間
        """
        self.endpoint = endpoint
        self.timeout = timeout
        self.session = requests.Session()

        if auth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {auth_token}'
            })

    def execute_query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        執行 GraphQL 查詢

        Args:
            query: GraphQL 查詢字串
            variables: 查詢變數
            operation_name: 操作名稱（多個 operation 時需要）

        Returns:
            執行結果

        Example:
            >>> tester = GraphQLTester("https://api.example.com/graphql")
            >>> result = tester.execute_query('''
            ...     query GetUser($id: ID!) {
            ...         user(id: $id) {
            ...             id
            ...             name
            ...             email
            ...         }
            ...     }
            ... ''', variables={"id": "123"})
            >>> print(result['data']['user']['name'])
        """
        payload = {
            "query": query,
            "variables": variables or {}
        }

        if operation_name:
            payload["operationName"] = operation_name

        try:
            response = self.session.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            body = response.json()

            # GraphQL 錯誤檢查
            if 'errors' in body:
                logger.warning(f"GraphQL 錯誤: {body['errors']}")
                return {
                    "success": False,
                    "errors": body['errors'],
                    "data": body.get('data')
                }

            return {
                "success": True,
                "data": body.get('data'),
                "extensions": body.get('extensions')
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"GraphQL 請求失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def test_query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        expected_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        測試 GraphQL 查詢並驗證響應

        Args:
            query: GraphQL 查詢
            variables: 查詢變數
            expected_fields: 預期響應中應包含的欄位（路徑，如 data.user.id）

        Returns:
            測試結果

        Example:
            >>> result = tester.test_query(
            ...     "query { users { id name } }",
            ...     expected_fields=["data.users"]
            ... )
            >>> assert result['success']
        """
        result = self.execute_query(query, variables)

        if not result['success']:
            return result

        # 驗證預期欄位
        if expected_fields:
            missing_fields = []

            for field_path in expected_fields:
                if not self._field_exists(result, field_path):
                    missing_fields.append(field_path)

            if missing_fields:
                return {
                    "success": False,
                    "error": f"缺少預期欄位: {missing_fields}",
                    "data": result['data']
                }

        return result

    def _field_exists(self, data: Dict, path: str) -> bool:
        """檢查嵌套欄位是否存在（如 data.user.id）"""
        keys = path.split('.')
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False

        return True

    def get_schema(self) -> Dict[str, Any]:
        """
        獲取 GraphQL Schema（使用 introspection）

        Returns:
            Schema 定義

        Example:
            >>> schema = tester.get_schema()
            >>> print(schema['data']['__schema']['types'])
        """
        introspection_query = """
        query IntrospectionQuery {
            __schema {
                queryType { name }
                mutationType { name }
                subscriptionType { name }
                types {
                    kind
                    name
                    description
                    fields {
                        name
                        type { name kind }
                    }
                }
            }
        }
        """

        return self.execute_query(introspection_query)
```


## 6.3 API 契約測試（Contract Testing）

### 6.3.1 什麼是契約測試？

在微服務架構中，服務間透過 API 通信。**契約測試**確保 API 提供者（Provider）與消費者（Consumer）對 API 契約的理解一致。

**與整合測試的區別：**

| 測試類型 | 測試內容 | 執行環境 | 速度 |
|----------|----------|----------|------|
| 整合測試 | 實際啟動所有服務，端到端測試 | 需要完整環境 | 慢 |
| 契約測試 | 驗證 API 契約（請求/響應格式） | 使用 Mock | 快 |

### 6.3.2 使用 Pact 進行契約測試

**Pact** 是業界標準的契約測試工具。工作流程：

1. **Consumer 測試**：消費者定義期望的 API 行為，生成 Pact 契約文件
2. **Provider 測試**：提供者讀取契約文件，驗證 API 是否滿足所有契約

**安裝：**

```bash
pip install pact-python
```

**Consumer 側範例（Python）：**

```python
import pytest
from pact import Consumer, Provider, Like, EachLike

# 定義 Pact
pact = Consumer('UserService-Frontend').has_pact_with(
    Provider('UserService-API'),
    pact_dir='./pacts'  # 契約文件輸出目錄
)


@pytest.fixture
def user_service():
    """啟動 Pact mock server"""
    pact.start_service()
    yield
    pact.stop_service()


def test_get_user_contract(user_service):
    """定義 GET /users/:id 的契約"""
    expected_user = {
        'id': 1,
        'name': 'Alice',
        'email': 'alice@example.com',
        'created_at': Like('2024-01-01T00:00:00Z')  # 匹配類型，不關心具體值
    }

    # 定義期望的交互
    (pact
     .given('user with ID 1 exists')  # 提供者狀態
     .upon_receiving('a request for user 1')
     .with_request('GET', '/users/1')
     .will_respond_with(200, body=expected_user))

    # 進入 Pact context，mock server 會根據定義返回響應
    with pact:
        # 實際調用我們的客戶端代碼
        import requests
        response = requests.get(f'{pact.uri}/users/1')

        assert response.status_code == 200
        assert response.json()['name'] == 'Alice'

    # 測試結束後，Pact 會生成契約文件到 ./pacts/


def test_create_user_contract(user_service):
    """定義 POST /users 的契約"""
    new_user = {
        'name': 'Bob',
        'email': 'bob@example.com'
    }

    expected_response = {
        'id': Like(1),
        'name': 'Bob',
        'email': 'bob@example.com',
        'created_at': Like('2024-01-01T00:00:00Z')
    }

    (pact
     .given('user service is available')
     .upon_receiving('a request to create user')
     .with_request('POST', '/users', body=new_user)
     .will_respond_with(201, body=expected_response))

    with pact:
        import requests
        response = requests.post(f'{pact.uri}/users', json=new_user)

        assert response.status_code == 201
        assert response.json()['name'] == 'Bob'
```

**Provider 側驗證（在 API 服務端）：**

```python
from pact import Verifier

verifier = Verifier(
    provider='UserService-API',
    provider_base_url='http://localhost:8000'  # API 服務地址
)

# 驗證所有契約
verifier.verify_pacts(
    './pacts/userservice-frontend-userservice-api.json',
    provider_states_setup_url='http://localhost:8000/_pact/provider-states'
)
```


## 6.4 API Mock 與測試隔離

### 6.4.1 為什麼需要 Mock？

實際測試中，我們常需要隔離外部依賴：

- **第三方 API 不穩定**：支付網關、天氣 API 可能故障
- **成本考量**：某些 API 按調用次數收費
- **測試特殊情況**：如何測試「支付失敗」？需要 Mock

### 6.4.2 使用 responses 庫 Mock API

**responses** 是輕量級的 HTTP Mock 庫，攔截 `requests` 庫的請求：

```python
import responses
import requests


@responses.activate
def test_payment_api_success():
    """測試支付成功場景（Mock 支付網關）"""
    # Mock 支付 API
    responses.add(
        responses.POST,
        'https://payment-gateway.example.com/charge',
        json={'status': 'success', 'transaction_id': 'txn_12345'},
        status=200
    )

    # 執行業務邏輯（會調用支付 API）
    from app.payment import process_payment
    result = process_payment(amount=100, currency='USD')

    assert result['success'] is True
    assert result['transaction_id'] == 'txn_12345'


@responses.activate
def test_payment_api_failure():
    """測試支付失敗場景"""
    # Mock 支付 API 返回錯誤
    responses.add(
        responses.POST,
        'https://payment-gateway.example.com/charge',
        json={'error': 'insufficient_funds'},
        status=402
    )

    from app.payment import process_payment
    result = process_payment(amount=100, currency='USD')

    assert result['success'] is False
    assert result['error'] == 'insufficient_funds'


@responses.activate
def test_payment_api_timeout():
    """測試支付超時場景"""
    # Mock 超時
    from requests.exceptions import Timeout
    responses.add(
        responses.POST,
        'https://payment-gateway.example.com/charge',
        body=Timeout('Connection timeout')
    )

    from app.payment import process_payment
    result = process_payment(amount=100, currency='USD')

    assert result['success'] is False
    assert 'timeout' in result['error'].lower()
```


## 6.5 性能與負載測試

### 6.5.1 響應時間驗證

擴展 APITester 支持性能斷言：

```python
class PerformanceAPITester(APITester):
    """增強性能測試功能的 API 測試器"""

    def test_endpoint_performance(
        self,
        method: str,
        endpoint: str,
        max_response_time_ms: float,
        iterations: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        測試端點性能

        Args:
            method: HTTP 方法
            endpoint: API 端點
            max_response_time_ms: 最大允許響應時間（毫秒）
            iterations: 測試次數
            **kwargs: 傳遞給 test_endpoint 的其他參數

        Returns:
            性能測試結果

        Example:
            >>> result = tester.test_endpoint_performance(
            ...     "GET",
            ...     "/users",
            ...     max_response_time_ms=500,  # 要求 500ms 內響應
            ...     iterations=20
            ... )
            >>> assert result['success']
        """
        response_times = []
        failures = []

        for i in range(iterations):
            result = self.test_endpoint(method, endpoint, **kwargs)

            if 'response_time_ms' in result:
                response_times.append(result['response_time_ms'])

            if not result['success']:
                failures.append(i + 1)

        if not response_times:
            return {
                "success": False,
                "error": "無有效響應時間數據"
            }

        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)

        # 檢查是否所有請求都在限制內
        slow_requests = sum(1 for t in response_times if t > max_response_time_ms)

        success = slow_requests == 0 and len(failures) == 0

        return {
            "success": success,
            "iterations": iterations,
            "avg_response_time_ms": round(avg_time, 2),
            "min_response_time_ms": round(min_time, 2),
            "max_response_time_ms": round(max_time, 2),
            "slow_requests": slow_requests,
            "failed_requests": len(failures),
            "threshold_ms": max_response_time_ms,
            "verdict": "通過" if success else "失敗"
        }
```

### 6.5.2 使用 Locust 進行負載測試

對於大規模負載測試，使用 **Locust**（Python 負載測試框架）：

```python
# locustfile.py
from locust import HttpUser, task, between


class APIUser(HttpUser):
    """模擬 API 用戶"""
    wait_time = between(1, 3)  # 每個請求間隔 1-3 秒
    host = "https://api.example.com"

    def on_start(self):
        """用戶啟動時執行（如登入）"""
        response = self.client.post("/auth/login", json={
            "username": "test_user",
            "password": "test_pass"
        })
        self.token = response.json()['access_token']

    @task(3)  # 權重 3：這個任務執行頻率是下面的 3 倍
    def get_users(self):
        """獲取用戶列表"""
        self.client.get(
            "/users",
            headers={'Authorization': f'Bearer {self.token}'}
        )

    @task(1)
    def create_user(self):
        """創建用戶"""
        self.client.post(
            "/users",
            json={"name": "New User", "email": "new@example.com"},
            headers={'Authorization': f'Bearer {self.token}'}
        )
```

**執行負載測試：**

```bash
# 啟動 Locust Web UI
locust -f locustfile.py

# 或命令行模式：100 用戶，每秒增加 10 個，運行 5 分鐘
locust -f locustfile.py --headless -u 100 -r 10 -t 5m
```


## 6.6 整合到 Claude Code Skill

### 6.6.1 API 健康檢查 Skill

**SKILL.md:**

```markdown
---
name: api-health-check
description: Check API health by testing critical endpoints
parameters:
  - name: api_config
    description: Path to API configuration file (YAML)
    type: string
    required: true
---

# API Health Check Skill

Tests critical API endpoints to ensure service availability.

## Configuration Format (YAML)

```yaml
base_url: https://api.example.com
auth_token: ${ANTHROPIC_API_KEY}  # From environment variable

endpoints:
  - name: User API
    method: GET
    path: /users
    expected_status: 200
    max_response_time_ms: 500

  - name: Create User
    method: POST
    path: /users
    json_data:
      name: Test User
    expected_status: 201
```
```

**skill.py:**

```python
import sys
import json
import yaml
from pathlib import Path
from api_tester import APITester
import os


def api_health_check(api_config: str) -> dict:
    """執行 API 健康檢查"""

    # 讀取配置
    config_path = Path(api_config)
    if not config_path.exists():
        return {
            "success": False,
            "error": f"配置文件不存在: {api_config}"
        }

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # 替換環境變數
    auth_token = config.get('auth_token', '')
    if auth_token.startswith('${') and auth_token.endswith('}'):
        env_var = auth_token[2:-1]
        auth_token = os.getenv(env_var)

    # 初始化測試器
    tester = APITester(
        base_url=config['base_url'],
        auth_token=auth_token
    )

    # 執行測試
    results = []
    for endpoint in config.get('endpoints', []):
        result = tester.test_endpoint(
            method=endpoint['method'],
            endpoint=endpoint['path'],
            expected_status=endpoint.get('expected_status', 200),
            json_data=endpoint.get('json_data')
        )

        # 檢查性能
        max_time = endpoint.get('max_response_time_ms')
        if max_time and result.get('response_time_ms', 0) > max_time:
            result['success'] = False
            result['error'] = (
                f"響應時間超標: {result['response_time_ms']}ms > {max_time}ms"
            )

        results.append({
            'name': endpoint['name'],
            'success': result['success'],
            'status_code': result.get('status_code'),
            'response_time_ms': result.get('response_time_ms'),
            'error': result.get('error')
        })

    # 統計
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed

    return {
        "success": failed == 0,
        "total_checks": len(results),
        "passed": passed,
        "failed": failed,
        "results": results
    }


if __name__ == "__main__":
    params = json.loads(sys.argv[1])
    result = api_health_check(**params)
    print(json.dumps(result, ensure_ascii=False, indent=2))
```


## 6.7 與 WebGuard 系統整合

將 API 測試能力整合到 WebGuard 四層架構：

```python
# webguard/api/api_test_suite.py
from typing import List, Dict, Any
from api_tester import AuthenticatedAPITester
from webguard.core.test_base import TestBase
import logging

logger = logging.getLogger(__name__)


class APITestSuite(TestBase):
    """
    API 測試套件

    整合到 WebGuard 測試系統
    """

    def __init__(
        self,
        base_url: str,
        test_cases: List[Dict[str, Any]],
        auth_config: Optional[Dict[str, str]] = None
    ):
        """
        初始化 API 測試套件

        Args:
            base_url: API 基礎 URL
            test_cases: 測試案例列表
            auth_config: 認證配置 {"type": "bearer", "token": "..."}
        """
        super().__init__()
        self.base_url = base_url
        self.test_cases = test_cases
        self.tester = AuthenticatedAPITester(base_url)

        # 設置認證
        if auth_config:
            self._setup_auth(auth_config)

    def _setup_auth(self, config: Dict[str, str]):
        """設置認證"""
        auth_type = config.get('type')

        if auth_type == 'bearer':
            self.tester.set_bearer_token(config['token'])
        elif auth_type == 'api_key':
            self.tester.set_api_key(
                config['key'],
                config.get('header_name', 'X-API-Key')
            )
        elif auth_type == 'basic':
            self.tester.set_basic_auth(
                config['username'],
                config['password']
            )
        elif auth_type == 'login':
            # 自動登入獲取 Token
            self.tester.login_and_get_token(
                config['login_endpoint'],
                config['username'],
                config['password']
            )

    async def run(self) -> Dict[str, Any]:
        """執行 API 測試套件"""
        logger.info(f"開始執行 API 測試: {len(self.test_cases)} 個案例")

        # 批量執行測試
        summary = self.tester.batch_test(self.test_cases)

        # 性能指標
        metrics = self.tester.get_performance_metrics()

        return {
            "success": summary['failed'] == 0,
            "summary": summary,
            "performance": metrics,
            "test_history": self.tester.test_history
        }
```


## 6.8 最佳實踐與安全考量

### 6.8.1 API 測試最佳實踐

1. **測試金字塔原則**：API 測試應佔測試套件的 60-70%（比 UI 測試多）
2. **先測契約，再測實現**：確保 API 契約穩定
3. **獨立性**：每個測試獨立，不依賴其他測試的執行順序
4. **數據隔離**：使用測試專用數據庫或 Mock，避免污染生產數據
5. **冪等性**：GET/DELETE 測試應可重複執行

### 6.8.2 安全考量

**敏感數據保護：**

```python
# ❌ 錯誤：Token 寫死在代碼中
tester = APITester("https://api.example.com", auth_token="sk-1234567890abcdef")

# ✅ 正確：從環境變數讀取
import os
token = os.getenv('API_TOKEN')
tester = APITester("https://api.example.com", auth_token=token)
```

**防止 API 濫用：**

```python
# 限制測試頻率（避免觸發 Rate Limit）
import time

for test_case in test_cases:
    result = tester.test_endpoint(**test_case)
    time.sleep(0.5)  # 每個請求間隔 500ms
```

**HTTPS 驗證：**

```python
# 生產環境必須驗證 SSL 證書
session.verify = True

# 測試環境可暫時關閉（但要小心）
session.verify = False  # 僅用於測試環境
```


## 6.9 本章總結

本章深入探討了 API 測試自動化的完整體系：

**核心能力：**

- **REST API 測試**：使用 Requests 庫實現完整的 HTTP 測試，支持多種認證方式
- **GraphQL 測試**：處理 GraphQL 特有的查詢、Schema introspection
- **契約測試**：使用 Pact 確保微服務間 API 契約一致性
- **Mock 與隔離**：使用 responses 庫隔離外部依賴
- **性能測試**：響應時間驗證、Locust 負載測試

**整合視角：**

API 測試與前幾章能力形成完整測試矩陣：

- **瀏覽器測試（Chapter 4）**：測試用戶交互流程
- **數據處理（Chapter 5）**：處理測試數據與結果
- **API 測試（Chapter 6）**：快速驗證業務邏輯
- **三者結合**：完整的端到端測試系統（WebGuard）

**下一章預告：**

掌握單一 Skill 開發後，第 7 章將探討 **Skills 進階模式與編排**：如何組合多個 Skills 完成複雜工作流、順序執行與並行執行、錯誤恢復策略、動態參數傳遞。這將把我們的自動化能力提升到編排層（Orchestration Layer）。
