"""
輸出格式定義 - 使用 Pydantic 定義標準格式
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator


class TestCase(BaseModel):
    """
    單一測試案例的標準格式
    """
    test_name: str = Field(..., description="測試函數名稱，例如：test_calculate_total")
    test_code: str = Field(..., description="完整的測試程式碼")
    target_function: str = Field(..., description="被測試的函數名稱")
    test_type: str = Field(..., description="測試類型：unit 或 integration")
    description: str = Field(..., description="測試說明")

    @validator('test_name')
    def validate_test_name(cls, v):
        """驗證測試名稱符合規範"""
        if not v.startswith('test_'):
            raise ValueError("測試名稱必須以 'test_' 開頭")
        if not v.islower() or not v.replace('_', '').isalnum():
            raise ValueError("測試名稱只能包含小寫字母、數字和底線")
        return v

    @validator('test_type')
    def validate_test_type(cls, v):
        """驗證測試類型"""
        if v not in ['unit', 'integration']:
            raise ValueError("測試類型必須是 'unit' 或 'integration'")
        return v


class TestGenerationOutput(BaseModel):
    """
    測試生成 Agent 的標準輸出格式
    """
    target_file: str = Field(..., description="被測試的原始檔案路徑")
    tests: List[TestCase] = Field(..., description="生成的測試列表")
    coverage_estimate: float = Field(..., ge=0, le=100, description="預估覆蓋率（0-100）")
    generation_metadata: Dict = Field(
        default_factory=dict,
        description="生成的元資料（模型、時間等）"
    )

    @validator('tests')
    def validate_tests_not_empty(cls, v):
        """至少要有一個測試"""
        if len(v) == 0:
            raise ValueError("必須至少生成一個測試")
        return v


class ValidationError(BaseModel):
    """驗證錯誤"""
    error_type: str  # 'format', 'execution', 'semantic'
    error_message: str
    error_location: Optional[str] = None
    suggested_fix: Optional[str] = None
