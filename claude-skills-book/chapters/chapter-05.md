# 第 5 章
> 📚 **章節定位**：本章聚焦數據與文件處理自動化。結合 **Chapter 4** 的瀏覽器測試和本章的數據處理，你將具備端到端測試能力。
：數據與文件處理自動化

在現代軟件測試與自動化工作流中，數據處理是不可或缺的一環。測試數據可能來自 Excel 試算表、CSV 檔案、PDF 報告等多種格式，而測試結果也需要以結構化方式記錄和分析。本章將探討如何使用 Claude Code Skills 自動化處理各種數據與文件格式，從 Excel/CSV 的讀寫驗證，到 PDF 內容提取與驗證，再到數據驅動測試的實踐。

## 5.1 Excel/CSV 數據處理 Skills

### 5.1.1 為什麼需要自動化 Excel 處理？

Excel 在企業環境中無處不在：測試數據存儲於 Excel 表格、測試結果匯出為 Excel 報告、業務邏輯依賴 Excel 計算。手動處理這些檔案既耗時又容易出錯。透過 Claude Code Skills 整合 Python 的數據處理能力，我們可以：

- **批量讀取測試數據**：從 Excel 檔案讀取數百筆測試案例，自動執行測試
- **驗證數據格式**：確保上傳的 Excel 檔案符合預期結構（欄位名稱、數據類型、必填項）
- **生成測試報告**：將測試結果寫入 Excel，配合圖表和格式化，便於分享
- **數據清洗與轉換**：處理缺失值、格式轉換、數據標準化

### 5.1.2 技術選型：Pandas + openpyxl

Python 生態系統提供了強大的數據處理工具：

- **Pandas**：數據分析庫，提供 DataFrame 結構，支持 Excel/CSV 讀寫、數據清洗、統計分析
- **openpyxl**：讀寫 Excel 2010+ (.xlsx) 檔案，支持樣式、公式、圖表
- **xlrd/xlwt**：處理舊版 Excel (.xls)，但已逐漸被 openpyxl 取代

我們將使用 **Pandas + openpyxl** 組合，既能高效處理數據，又能控制 Excel 檔案的細節。

### 5.1.3 實作：ExcelProcessor 類別

以下是生產級的 Excel 處理器，涵蓋讀取、寫入、驗證三大功能：

```python
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ExcelProcessor:
    """
    Excel 處理器，提供讀寫、驗證、格式化功能

    適用於測試數據管理、結果報告生成等場景
    """

    def __init__(self, default_sheet: str = "Sheet1"):
        """
        初始化 Excel 處理器

        Args:
            default_sheet: 預設工作表名稱
        """
        self.default_sheet = default_sheet

    def read_test_data(
        self,
        file_path: str,
        sheet_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        讀取測試數據，轉換為字典列表

        Args:
            file_path: Excel 檔案路徑
            sheet_name: 工作表名稱，預設使用第一個工作表

        Returns:
            每筆資料為一個字典的列表

        Example:
            >>> processor = ExcelProcessor()
            >>> data = processor.read_test_data("test_cases.xlsx")
            >>> print(data[0])
            {'username': 'user1', 'password': 'pass123', 'expected': 'success'}
        """
        try:
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name or 0,
                engine='openpyxl'
            )

            # 移除完全空白的行
            df = df.dropna(how='all')

            # 轉換為字典列表
            records = df.to_dict('records')

            logger.info(
                f"成功讀取 {len(records)} 筆測試數據 "
                f"從 {file_path}"
            )

            return records

        except FileNotFoundError:
            logger.error(f"檔案不存在: {file_path}")
            raise
        except Exception as e:
            logger.error(f"讀取 Excel 失敗: {e}")
            raise

    def write_results(
        self,
        results: List[Dict[str, Any]],
        output_path: str,
        sheet_name: str = "Test Results",
        apply_formatting: bool = True
    ) -> None:
        """
        寫入測試結果到 Excel，支持自動格式化

        Args:
            results: 測試結果列表
            output_path: 輸出檔案路徑
            sheet_name: 工作表名稱
            apply_formatting: 是否套用格式化（標題行、條件格式）

        Example:
            >>> results = [
            ...     {'test_name': 'Login Test', 'status': 'PASSED', 'duration_ms': 1234},
            ...     {'test_name': 'Checkout Test', 'status': 'FAILED', 'duration_ms': 5678}
            ... ]
            >>> processor.write_results(results, "test_results.xlsx")
        """
        # 創建 DataFrame
        df = pd.DataFrame(results)

        # 確保輸出目錄存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 寫入 Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False
            )

            # 套用格式化
            if apply_formatting:
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]

                self._apply_header_formatting(worksheet)
                self._apply_status_formatting(worksheet, df)
                self._auto_adjust_column_width(worksheet, df)

        logger.info(f"測試結果已寫入: {output_path}")

    def validate_data(
        self,
        file_path: str,
        schema: Dict[str, Any],
        sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        驗證 Excel 數據格式是否符合預期

        Args:
            file_path: Excel 檔案路徑
            schema: 驗證規則
                - required_columns: 必要欄位列表
                - column_types: 欄位類型映射 {'column': dtype}
                - value_ranges: 值範圍驗證 {'column': {'min': 0, 'max': 100}}
            sheet_name: 工作表名稱

        Returns:
            驗證結果字典

        Example:
            >>> schema = {
            ...     'required_columns': ['username', 'password'],
            ...     'column_types': {'age': 'int64'},
            ...     'value_ranges': {'age': {'min': 0, 'max': 120}}
            ... }
            >>> result = processor.validate_data("users.xlsx", schema)
            >>> print(result['valid'])  # True/False
        """
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name or 0,
            engine='openpyxl'
        )

        errors = []
        warnings = []

        # 1. 檢查必要欄位
        required_columns = schema.get('required_columns', [])
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"缺少必要欄位: {col}")

        # 2. 檢查數據類型
        column_types = schema.get('column_types', {})
        for col, expected_dtype in column_types.items():
            if col in df.columns:
                actual_dtype = str(df[col].dtype)
                if actual_dtype != expected_dtype:
                    # 嘗試轉換
                    try:
                        df[col] = df[col].astype(expected_dtype)
                        warnings.append(
                            f"欄位 {col} 已自動轉換為 {expected_dtype}"
                        )
                    except (ValueError, TypeError):
                        errors.append(
                            f"欄位 {col} 類型錯誤: "
                            f"期望 {expected_dtype}, 實際 {actual_dtype}"
                        )

        # 3. 檢查值範圍
        value_ranges = schema.get('value_ranges', {})
        for col, range_spec in value_ranges.items():
            if col in df.columns:
                if 'min' in range_spec:
                    invalid_rows = df[df[col] < range_spec['min']]
                    if not invalid_rows.empty:
                        errors.append(
                            f"欄位 {col} 有 {len(invalid_rows)} 筆資料 "
                            f"小於最小值 {range_spec['min']}"
                        )

                if 'max' in range_spec:
                    invalid_rows = df[df[col] > range_spec['max']]
                    if not invalid_rows.empty:
                        errors.append(
                            f"欄位 {col} 有 {len(invalid_rows)} 筆資料 "
                            f"大於最大值 {range_spec['max']}"
                        )

        # 4. 檢查空值
        null_counts = df.isnull().sum()
        columns_with_nulls = null_counts[null_counts > 0]
        if not columns_with_nulls.empty:
            for col, count in columns_with_nulls.items():
                warnings.append(
                    f"欄位 {col} 有 {count} 筆空值"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns)
        }

    def _apply_header_formatting(self, worksheet):
        """套用標題列格式"""
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")

        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

    def _apply_status_formatting(self, worksheet, df):
        """根據狀態套用條件格式"""
        if 'status' not in df.columns:
            return

        status_col_idx = df.columns.get_loc('status') + 1  # openpyxl 從 1 開始

        for row_idx in range(2, len(df) + 2):  # 從第 2 行開始（第 1 行是標題）
            cell = worksheet.cell(row_idx, status_col_idx)
            status = cell.value

            if status == 'PASSED':
                cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                cell.font = Font(color="006100")
            elif status == 'FAILED':
                cell.fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                cell.font = Font(color="9C0006")
            elif status == 'SKIPPED':
                cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                cell.font = Font(color="9C6500")

    def _auto_adjust_column_width(self, worksheet, df):
        """自動調整欄寬"""
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass

            adjusted_width = min(max_length + 2, 50)  # 最大 50
            worksheet.column_dimensions[column_letter].width = adjusted_width
```

### 5.1.4 整合到 Claude Code Skill

現在將 ExcelProcessor 整合到 Skill 中，實現「讀取測試數據並執行測試」的自動化流程：

**SKILL.md:**

```markdown
---
name: run-data-driven-tests
description: Execute data-driven tests using test cases from Excel file
parameters:
  - name: excel_file
    description: Path to Excel file containing test cases
    type: string
    required: true
  - name: test_function
    description: Test function name to execute for each case
    type: string
    required: true
---

# Data-Driven Test Execution

This Skill reads test cases from an Excel file and executes the specified test function for each case.

## Expected Excel Format

| username | password | expected_result |
|----------|----------|-----------------|
| user1    | pass123  | success         |
| user2    | wrong    | failure         |

## Execution

The Skill will:
1. Read test cases from Excel
2. Validate data format
3. Execute test function for each case
4. Generate results Excel report
```

**skill.py:**

```python
import sys
import json
from pathlib import Path
from typing import Dict, Any
from excel_processor import ExcelProcessor


def run_data_driven_tests(excel_file: str, test_function: str) -> Dict[str, Any]:
    """
    執行數據驅動測試

    Args:
        excel_file: Excel 測試數據檔案路徑
        test_function: 測試函數名稱

    Returns:
        測試結果摘要
    """
    processor = ExcelProcessor()

    # 1. 讀取測試數據
    try:
        test_cases = processor.read_test_data(excel_file)
    except Exception as e:
        return {
            "success": False,
            "error": f"讀取測試數據失敗: {str(e)}"
        }

    # 2. 驗證數據格式
    schema = {
        'required_columns': ['username', 'password', 'expected_result']
    }

    validation = processor.validate_data(excel_file, schema)
    if not validation['valid']:
        return {
            "success": False,
            "error": "數據驗證失敗",
            "validation_errors": validation['errors']
        }

    # 3. 執行測試（動態導入測試函數）
    results = []
    test_module = __import__('tests.login_tests', fromlist=[test_function])
    test_func = getattr(test_module, test_function)

    for idx, test_case in enumerate(test_cases, 1):
        try:
            result = test_func(
                username=test_case['username'],
                password=test_case['password']
            )

            status = 'PASSED' if result == test_case['expected_result'] else 'FAILED'

            results.append({
                'case_id': idx,
                'username': test_case['username'],
                'expected': test_case['expected_result'],
                'actual': result,
                'status': status
            })
        except Exception as e:
            results.append({
                'case_id': idx,
                'username': test_case['username'],
                'status': 'ERROR',
                'error': str(e)
            })

    # 4. 寫入結果報告
    output_file = Path(excel_file).stem + "_results.xlsx"
    processor.write_results(results, output_file)

    # 5. 統計
    passed = sum(1 for r in results if r['status'] == 'PASSED')
    failed = sum(1 for r in results if r['status'] == 'FAILED')
    errors = sum(1 for r in results if r['status'] == 'ERROR')

    return {
        "success": True,
        "total_cases": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate": f"{passed / len(results) * 100:.2f}%",
        "report_file": output_file
    }


if __name__ == "__main__":
    params = json.loads(sys.argv[1])
    result = run_data_driven_tests(**params)
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

### 5.1.5 CSV 處理：輕量級替代方案

對於不需要複雜格式的場景，CSV 是更輕量的選擇。Pandas 同樣支持 CSV：

```python
# 讀取 CSV
df = pd.read_csv('test_data.csv', encoding='utf-8')

# 寫入 CSV
df.to_csv('results.csv', index=False, encoding='utf-8-sig')  # BOM for Excel 相容

# 處理大型 CSV（分塊讀取）
chunk_size = 10000
for chunk in pd.read_csv('large_file.csv', chunksize=chunk_size):
    process_chunk(chunk)
```

**最佳實踐：**

- 小於 1MB 且無格式需求：使用 CSV
- 需要格式化、多工作表、公式：使用 Excel
- 超大數據（百萬行）：考慮資料庫或 Parquet 格式


## 5.2 PDF 文件處理與驗證

### 5.2.1 PDF 處理的應用場景

在測試自動化中，PDF 處理常見於：

- **報告驗證**：測試系統生成的 PDF 報告是否包含正確內容
- **文件下載測試**：驗證下載的 PDF 檔案完整性和內容
- **合規檢查**：確保 PDF 包含必要的法律聲明、條款
- **數據提取**：從 PDF 發票、報表中提取結構化數據進行驗證

### 5.2.2 技術選型：PyPDF2 vs pdfplumber vs pdfminer

Python 有多個 PDF 處理庫，各有優劣：

| 工具 | 優點 | 缺點 | 適用場景 |
|------|------|------|----------|
| **PyPDF2** | 輕量、易用、支持合併分割 | 文本提取不穩定 | 基本操作、合併 PDF |
| **pdfplumber** | 表格提取優秀、布局保留好 | 較重、依賴較多 | 提取表格數據 |
| **pdfminer.six** | 文本提取最準確、支持佈局分析 | API 複雜 | 精確文本提取 |
| **PyMuPDF (fitz)** | 速度快、功能全面 | C 依賴、安裝複雜 | 高性能需求 |

我們選用 **pdfminer.six**（文本提取）+ **PyPDF2**（基本操作）的組合。

### 5.2.3 實作：PDFValidator 類別

```python
import PyPDF2
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer, LAParams
from typing import Dict, Any, List, Optional
from pathlib import Path
import re
import logging

logger = logging.getLogger(__name__)


class PDFValidator:
    """
    PDF 驗證器，提供內容提取、驗證、元數據檢查功能

    適用於測試報告驗證、文件下載測試等場景
    """

    def __init__(self):
        """初始化 PDF 驗證器"""
        self.la_params = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            boxes_flow=0.5
        )

    def extract_text(self, pdf_path: str, page_numbers: Optional[List[int]] = None) -> str:
        """
        提取 PDF 文本內容

        Args:
            pdf_path: PDF 檔案路徑
            page_numbers: 要提取的頁碼列表（從 1 開始），None 表示全部

        Returns:
            提取的文本內容

        Example:
            >>> validator = PDFValidator()
            >>> text = validator.extract_text("report.pdf", page_numbers=[1, 2])
            >>> print(text[:100])
        """
        try:
            if page_numbers:
                # 提取特定頁面（pdfminer 頁碼從 1 開始）
                text = extract_text(
                    pdf_path,
                    page_numbers=set(page_numbers),
                    laparams=self.la_params
                )
            else:
                # 提取全部
                text = extract_text(pdf_path, laparams=self.la_params)

            logger.info(f"成功從 {pdf_path} 提取 {len(text)} 字元")
            return text

        except Exception as e:
            logger.error(f"PDF 文本提取失敗: {e}")
            raise

    def validate_content(
        self,
        pdf_path: str,
        expected_content: List[str],
        case_sensitive: bool = True,
        use_regex: bool = False
    ) -> Dict[str, Any]:
        """
        驗證 PDF 是否包含預期內容

        Args:
            pdf_path: PDF 檔案路徑
            expected_content: 預期內容列表
            case_sensitive: 是否區分大小寫
            use_regex: 是否使用正則表達式匹配

        Returns:
            驗證結果字典

        Example:
            >>> result = validator.validate_content(
            ...     "invoice.pdf",
            ...     ["Invoice #12345", "Total: \\$\\d+\\.\\d{2}"],
            ...     use_regex=True
            ... )
            >>> print(result['all_found'])  # True/False
        """
        text = self.extract_text(pdf_path)

        if not case_sensitive and not use_regex:
            text = text.lower()

        results = {
            "all_found": True,
            "missing": [],
            "found": [],
            "matches": {}
        }

        for content in expected_content:
            search_content = content if case_sensitive else content.lower()

            if use_regex:
                # 正則表達式匹配
                pattern = re.compile(search_content, re.IGNORECASE if not case_sensitive else 0)
                matches = pattern.findall(text)

                if matches:
                    results["found"].append(content)
                    results["matches"][content] = matches
                else:
                    results["missing"].append(content)
                    results["all_found"] = False
            else:
                # 普通字串匹配
                if search_content in text:
                    results["found"].append(content)
                else:
                    results["missing"].append(content)
                    results["all_found"] = False

        logger.info(
            f"內容驗證完成: {len(results['found'])}/{len(expected_content)} 找到"
        )

        return results

    def get_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        提取 PDF 元數據（作者、標題、創建日期等）

        Args:
            pdf_path: PDF 檔案路徑

        Returns:
            元數據字典

        Example:
            >>> metadata = validator.get_metadata("document.pdf")
            >>> print(metadata['title'])
        """
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata = reader.metadata

                return {
                    "title": metadata.get('/Title', ''),
                    "author": metadata.get('/Author', ''),
                    "subject": metadata.get('/Subject', ''),
                    "creator": metadata.get('/Creator', ''),
                    "producer": metadata.get('/Producer', ''),
                    "creation_date": metadata.get('/CreationDate', ''),
                    "modification_date": metadata.get('/ModDate', ''),
                    "page_count": len(reader.pages),
                    "is_encrypted": reader.is_encrypted
                }
        except Exception as e:
            logger.error(f"元數據提取失敗: {e}")
            raise

    def validate_structure(
        self,
        pdf_path: str,
        expected_pages: Optional[int] = None,
        max_file_size_mb: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        驗證 PDF 結構（頁數、檔案大小等）

        Args:
            pdf_path: PDF 檔案路徑
            expected_pages: 預期頁數
            max_file_size_mb: 最大檔案大小（MB）

        Returns:
            驗證結果

        Example:
            >>> result = validator.validate_structure(
            ...     "report.pdf",
            ...     expected_pages=10,
            ...     max_file_size_mb=5.0
            ... )
        """
        path = Path(pdf_path)

        if not path.exists():
            return {
                "valid": False,
                "errors": [f"檔案不存在: {pdf_path}"]
            }

        errors = []
        metadata = self.get_metadata(pdf_path)

        # 檢查頁數
        actual_pages = metadata['page_count']
        if expected_pages and actual_pages != expected_pages:
            errors.append(
                f"頁數不符: 期望 {expected_pages}, 實際 {actual_pages}"
            )

        # 檢查檔案大小
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if max_file_size_mb and file_size_mb > max_file_size_mb:
            errors.append(
                f"檔案過大: {file_size_mb:.2f} MB > {max_file_size_mb} MB"
            )

        # 檢查是否加密
        if metadata['is_encrypted']:
            errors.append("PDF 已加密，無法讀取")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "page_count": actual_pages,
            "file_size_mb": round(file_size_mb, 2),
            "metadata": metadata
        }

    def extract_tables(self, pdf_path: str, page_numbers: Optional[List[int]] = None) -> List[List[List[str]]]:
        """
        提取 PDF 中的表格（需要 pdfplumber）

        Args:
            pdf_path: PDF 檔案路徑
            page_numbers: 要提取的頁碼列表

        Returns:
            表格列表，每個表格是二維列表
        """
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("請安裝 pdfplumber: pip install pdfplumber")

        tables = []

        with pdfplumber.open(pdf_path) as pdf:
            pages_to_process = page_numbers if page_numbers else range(len(pdf.pages))

            for page_num in pages_to_process:
                page = pdf.pages[page_num]
                page_tables = page.extract_tables()

                if page_tables:
                    tables.extend(page_tables)

        logger.info(f"從 {pdf_path} 提取 {len(tables)} 個表格")
        return tables
```

### 5.2.4 整合到 Claude Code Skill：報告驗證

**SKILL.md:**

```markdown
---
name: validate-test-report
description: Validate generated PDF test report contains required content
parameters:
  - name: pdf_path
    description: Path to PDF test report
    type: string
    required: true
  - name: test_run_id
    description: Test run ID that should appear in report
    type: string
    required: true
---

# Test Report Validation

Validates that the generated PDF test report:
- Contains the correct test run ID
- Includes all required sections (Summary, Failures, Metrics)
- Has the expected number of pages
- File size is reasonable (<10MB)
```

**skill.py:**

```python
import sys
import json
from pdf_validator import PDFValidator


def validate_test_report(pdf_path: str, test_run_id: str) -> dict:
    """驗證測試報告 PDF"""
    validator = PDFValidator()

    # 1. 結構驗證
    structure = validator.validate_structure(
        pdf_path,
        expected_pages=None,  # 頁數可能變動
        max_file_size_mb=10.0
    )

    if not structure['valid']:
        return {
            "success": False,
            "errors": structure['errors']
        }

    # 2. 內容驗證（包含必要章節）
    required_content = [
        f"Test Run: {test_run_id}",
        "Executive Summary",
        "Test Results",
        "Failed Tests",
        r"Pass Rate: \d+\.\d+%"  # 正則：Pass Rate: 85.5%
    ]

    content_result = validator.validate_content(
        pdf_path,
        required_content,
        use_regex=True
    )

    if not content_result['all_found']:
        return {
            "success": False,
            "error": "報告內容不完整",
            "missing_sections": content_result['missing']
        }

    # 3. 提取統計數據（從文本中解析）
    text = validator.extract_text(pdf_path)

    import re
    pass_rate_match = re.search(r'Pass Rate: (\d+\.\d+)%', text)
    total_tests_match = re.search(r'Total Tests: (\d+)', text)

    return {
        "success": True,
        "report_metadata": structure['metadata'],
        "page_count": structure['page_count'],
        "file_size_mb": structure['file_size_mb'],
        "pass_rate": pass_rate_match.group(1) if pass_rate_match else None,
        "total_tests": int(total_tests_match.group(1)) if total_tests_match else None
    }


if __name__ == "__main__":
    params = json.loads(sys.argv[1])
    result = validate_test_report(**params)
    print(json.dumps(result, ensure_ascii=False, indent=2))
```


## 5.3 數據驅動測試實踐

### 5.3.1 什麼是數據驅動測試？

**數據驅動測試（Data-Driven Testing, DDT）** 是指測試邏輯與測試數據分離，同一測試函數使用不同數據集重複執行。優點：

- **減少代碼重複**：一個測試函數，數百個測試案例
- **提升覆蓋率**：輕鬆增加邊界值、異常值測試
- **便於維護**：業務人員可直接編輯 Excel 測試數據，無需改代碼

### 5.3.2 實作：Pytest + Excel DDT

使用 pytest 的參數化功能結合 Excel：

```python
import pytest
import pandas as pd
from excel_processor import ExcelProcessor


def load_test_data(excel_file: str, sheet_name: str = "TestCases"):
    """從 Excel 載入測試數據，轉為 pytest 參數"""
    processor = ExcelProcessor()
    data = processor.read_test_data(excel_file, sheet_name)

    # 轉換為 pytest.param 格式
    test_params = []
    for row in data:
        test_params.append(
            pytest.param(
                row['username'],
                row['password'],
                row['expected_result'],
                id=f"case_{row.get('case_id', len(test_params) + 1)}"
            )
        )

    return test_params


# 測試數據來自 Excel
test_cases = load_test_data("tests/data/login_tests.xlsx")


@pytest.mark.parametrize("username,password,expected", test_cases)
def test_login(username, password, expected):
    """數據驅動登入測試"""
    from app.auth import login

    result = login(username, password)

    if expected == "success":
        assert result.success is True
        assert result.user is not None
    elif expected == "invalid_password":
        assert result.success is False
        assert result.error == "Invalid password"
    elif expected == "user_not_found":
        assert result.success is False
        assert result.error == "User not found"
```

**Excel 測試數據格式：**

| case_id | username | password | expected_result |
|---------|----------|----------|-----------------|
| 1 | admin | admin123 | success |
| 2 | admin | wrong | invalid_password |
| 3 | nonexist | any | user_not_found |
| 4 | user1 | pass1 | success |

### 5.3.3 高級技巧：動態生成測試數據

對於大規模測試（如壓力測試），可結合 Faker 生成數據：

```python
from faker import Faker
import pandas as pd

fake = Faker('zh_TW')

# 生成 1000 筆測試用戶
users = []
for i in range(1000):
    users.append({
        'user_id': i + 1,
        'name': fake.name(),
        'email': fake.email(),
        'phone': fake.phone_number(),
        'address': fake.address()
    })

# 寫入 Excel
df = pd.DataFrame(users)
df.to_excel('test_users_1000.xlsx', index=False)
```


## 5.4 數據清洗與轉換

### 5.4.1 常見數據問題

實際測試中，數據常有問題：

- **缺失值**：某些欄位為空
- **格式不一致**：日期格式混亂（2024-01-01 vs 01/01/2024）
- **數據類型錯誤**：數字存為文本
- **重複數據**：同一用戶多次出現

### 5.4.2 Pandas 數據清洗技巧

```python
import pandas as pd
import numpy as np

# 讀取數據
df = pd.read_excel('messy_data.xlsx')

# 1. 處理缺失值
df['email'].fillna('unknown@example.com', inplace=True)  # 填充預設值
df.dropna(subset=['username'], inplace=True)  # 刪除關鍵欄位為空的行

# 2. 數據類型轉換
df['age'] = pd.to_numeric(df['age'], errors='coerce')  # 無法轉換的變為 NaN
df['signup_date'] = pd.to_datetime(df['signup_date'], format='%Y-%m-%d', errors='coerce')

# 3. 去除重複
df.drop_duplicates(subset=['username'], keep='first', inplace=True)

# 4. 字串清理
df['phone'] = df['phone'].str.replace(r'\D', '', regex=True)  # 只保留數字

# 5. 數據標準化
df['name'] = df['name'].str.strip().str.title()  # 去空格，首字母大寫

# 6. 條件轉換
df['status'] = df['age'].apply(lambda x: 'adult' if x >= 18 else 'minor')

# 保存清洗後的數據
df.to_excel('cleaned_data.xlsx', index=False)
```


## 5.5 與 WebGuard 測試系統整合

將數據處理能力整合到 WebGuard 架構：

```python
# webguard/data/excel_test_suite.py
from typing import List, Dict, Any
from pathlib import Path
from excel_processor import ExcelProcessor
from webguard.core.test_base import TestBase
import logging

logger = logging.getLogger(__name__)


class ExcelTestSuite(TestBase):
    """
    基於 Excel 的測試套件

    從 Excel 讀取測試案例，執行並回寫結果
    """

    def __init__(
        self,
        excel_path: str,
        sheet_name: str = "TestCases",
        result_sheet: str = "Results"
    ):
        super().__init__()
        self.excel_path = Path(excel_path)
        self.sheet_name = sheet_name
        self.result_sheet = result_sheet
        self.processor = ExcelProcessor()

    def load_test_cases(self) -> List[Dict[str, Any]]:
        """載入測試案例"""
        # 驗證數據格式
        schema = {
            'required_columns': ['test_name', 'test_type'],
            'column_types': {
                'timeout': 'int64',
                'retry': 'int64'
            }
        }

        validation = self.processor.validate_data(
            str(self.excel_path),
            schema,
            self.sheet_name
        )

        if not validation['valid']:
            raise ValueError(f"測試數據驗證失敗: {validation['errors']}")

        return self.processor.read_test_data(
            str(self.excel_path),
            self.sheet_name
        )

    async def run(self) -> Dict[str, Any]:
        """執行測試套件"""
        test_cases = self.load_test_cases()
        results = []

        for case in test_cases:
            test_name = case['test_name']
            test_type = case['test_type']

            logger.info(f"執行測試: {test_name} ({test_type})")

            try:
                # 根據類型選擇測試方法
                if test_type == 'browser':
                    result = await self._run_browser_test(case)
                elif test_type == 'api':
                    result = await self._run_api_test(case)
                else:
                    raise ValueError(f"未知測試類型: {test_type}")

                results.append({
                    'test_name': test_name,
                    'status': 'PASSED' if result['success'] else 'FAILED',
                    'duration_ms': result.get('duration_ms'),
                    'error': result.get('error')
                })

            except Exception as e:
                logger.error(f"測試執行失敗: {e}")
                results.append({
                    'test_name': test_name,
                    'status': 'ERROR',
                    'error': str(e)
                })

        # 寫入結果
        self._write_results(results)

        return {
            "success": True,
            "total": len(results),
            "passed": sum(1 for r in results if r['status'] == 'PASSED'),
            "failed": sum(1 for r in results if r['status'] == 'FAILED'),
            "errors": sum(1 for r in results if r['status'] == 'ERROR')
        }

    def _write_results(self, results: List[Dict[str, Any]]):
        """寫入測試結果到 Excel"""
        output_path = self.excel_path.parent / f"{self.excel_path.stem}_results.xlsx"
        self.processor.write_results(results, str(output_path), self.result_sheet)
        logger.info(f"測試結果已寫入: {output_path}")
```


## 5.6 最佳實踐與安全考量

### 5.6.1 數據處理最佳實踐

1. **始終驗證輸入數據**：不信任任何外部數據源
2. **優雅處理錯誤**：讀取失敗時提供清晰錯誤訊息
3. **分離數據與邏輯**：測試代碼與測試數據分開存放
4. **版本控制數據模板**：將 Excel 模板納入 Git，數據檔案則用 .gitignore 排除
5. **記錄數據血統**：記錄數據來源、轉換歷史

### 5.6.2 安全考量

**Excel 公式注入（Formula Injection）：**

如果 Excel 單元格內容來自不可信來源（如用戶輸入），惡意用戶可能注入公式：

```
=cmd|'/c calc.exe'!A1  # 執行計算機（Windows）
```

**防護措施：**

```python
def sanitize_cell_value(value: str) -> str:
    """清理單元格值，防止公式注入"""
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
        return f"'{value}"  # 加上單引號強制為文本
    return value

# 寫入時清理
safe_results = [
    {k: sanitize_cell_value(v) for k, v in row.items()}
    for row in results
]
processor.write_results(safe_results, output_path)
```

**PDF 安全：**

- 不執行 PDF 中的 JavaScript（使用 `strict=True` 參數）
- 限制檔案大小防止 DoS
- 掃描可疑內容（如嵌入的可執行檔）


## 5.7 本章總結

本章深入探討了數據與文件處理自動化，為構建完整的測試系統奠定基礎：

**核心技能：**

- **Excel/CSV 處理**：使用 Pandas + openpyxl 實現數據讀寫、驗證、格式化
- **PDF 驗證**：使用 pdfminer + PyPDF2 進行內容提取、結構驗證、元數據檢查
- **數據驅動測試**：將測試邏輯與數據分離，提升可維護性
- **數據清洗**：處理缺失值、格式不一致、重複數據等實際問題

**整合思維：**

這些數據處理能力並非孤立存在，而是與前幾章的 Skills 系統、Stagehand 瀏覽器自動化緊密整合：

- 從 Excel 讀取測試案例 → 用 Stagehand 執行瀏覽器測試 → 結果寫回 Excel
- PDF 報告驗證 Skill → 確保測試報告符合企業規範

**下一章預告：**

掌握數據處理後，我們將進入 **API 測試與整合驗證**（第 6 章），探討如何測試 REST/GraphQL API、處理認證、模擬第三方服務，並將 API 測試整合到 WebGuard 系統中。這將完善我們的測試能力矩陣：瀏覽器測試（Chapter 4）+ 數據處理（Chapter 5）+ API 測試（Chapter 6）= 全棧測試自動化。
