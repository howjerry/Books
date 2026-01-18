"""TechAssist 工具模組"""

from .doc_search import search_documentation
from .calculator import calculator
from .api_client import call_api
from .code_runner import run_python_code

# 註冊所有可用工具
TECHASSIST_TOOLS = [
    search_documentation,
    calculator,
    call_api,
    run_python_code,
]

__all__ = [
    "search_documentation",
    "calculator",
    "call_api",
    "run_python_code",
    "TECHASSIST_TOOLS",
]
