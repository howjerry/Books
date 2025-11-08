#!/usr/bin/env python
"""
圖表生成腳本

用法：
    python generate_chart.py <data_file> <output_file> <chart_type>

範例：
    python generate_chart.py workspace/data/sales.csv workspace/charts/sales.png bar
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def generate_chart(data_file: str, output_file: str, chart_type: str = "bar"):
    """
    生成圖表

    參數：
        data_file: CSV 資料檔案路徑
        output_file: 輸出圖片路徑
        chart_type: 圖表類型（bar, line, pie）
    """
    # 讀取資料
    df = pd.read_csv(data_file)

    # 建立圖表
    plt.figure(figsize=(10, 6))

    if chart_type == "bar":
        df.plot(kind='bar', x=df.columns[0], y=df.columns[1], ax=plt.gca())
    elif chart_type == "line":
        df.plot(kind='line', x=df.columns[0], y=df.columns[1], ax=plt.gca())
    elif chart_type == "pie":
        df.plot(kind='pie', y=df.columns[1], labels=df[df.columns[0]], ax=plt.gca())

    plt.title(f"{df.columns[1]} by {df.columns[0]}")
    plt.tight_layout()

    # 確保輸出目錄存在
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # 儲存圖表
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ 圖表已生成: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("錯誤：參數不足")
        print("用法：python generate_chart.py <data_file> <output_file> [chart_type]")
        sys.exit(1)

    data_file = sys.argv[1]
    output_file = sys.argv[2]
    chart_type = sys.argv[3] if len(sys.argv) > 3 else "bar"

    generate_chart(data_file, output_file, chart_type)
