"""
格式驗證器 - 驗證 Agent 輸出是否符合預期格式
"""

from typing import Dict, List, Tuple, Optional
from pydantic import ValidationError as PydanticValidationError
import json

from .output_schema import TestGenerationOutput, ValidationError


class FormatValidator:
    """
    格式驗證器 - 驗證 Agent 輸出是否符合預期格式

    職責：
    1. 驗證 JSON 結構完整性
    2. 檢查必要欄位存在
    3. 驗證資料型別正確
    """

    def __init__(self):
        self.errors: List[ValidationError] = []

    def validate(self, agent_output: str) -> Tuple[bool, Optional[TestGenerationOutput]]:
        """
        驗證 Agent 的原始輸出

        Args:
            agent_output: Agent 返回的原始字串（應為 JSON）

        Returns:
            (驗證是否通過, 解析後的輸出物件或 None)
        """
        self.errors = []

        # 步驟 1: 驗證是否為有效的 JSON
        try:
            parsed_json = json.loads(agent_output)
        except json.JSONDecodeError as e:
            self.errors.append(ValidationError(
                error_type="format",
                error_message=f"無效的 JSON 格式: {str(e)}",
                suggested_fix="確保輸出是有效的 JSON 字串"
            ))
            return False, None

        # 步驟 2: 使用 Pydantic 驗證格式
        try:
            output = TestGenerationOutput(**parsed_json)
            return True, output
        except PydanticValidationError as e:
            # 將 Pydantic 的錯誤轉換為我們的格式
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error['loc'])
                self.errors.append(ValidationError(
                    error_type="format",
                    error_message=error['msg'],
                    error_location=field_path,
                    suggested_fix=self._suggest_fix(error)
                ))
            return False, None

    def _suggest_fix(self, pydantic_error: Dict) -> str:
        """根據錯誤類型提供修復建議"""
        error_type = pydantic_error['type']

        suggestions = {
            'value_error.missing': "請確保提供此必要欄位",
            'type_error.integer': "此欄位應為整數",
            'type_error.float': "此欄位應為浮點數",
            'value_error.list.min_items': "列表至少要有一個項目",
        }

        return suggestions.get(error_type, "請檢查欄位格式與型別")

    def get_error_report(self) -> str:
        """產生人類可讀的錯誤報告"""
        if not self.errors:
            return "✅ 格式驗證通過"

        report = ["❌ 格式驗證失敗\n"]
        for i, error in enumerate(self.errors, 1):
            report.append(f"{i}. {error.error_message}")
            if error.error_location:
                report.append(f"   位置: {error.error_location}")
            if error.suggested_fix:
                report.append(f"   建議: {error.suggested_fix}")
            report.append("")

        return "\n".join(report)
