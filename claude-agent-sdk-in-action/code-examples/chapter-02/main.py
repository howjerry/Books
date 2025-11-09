from report_coordinator import ReportCoordinator
from datetime import datetime


def main():
    print("=" * 60)
    print("📊 自動化報表生成系統")
    print("=" * 60)
    print()

    # 初始化協調器
    coordinator = ReportCoordinator()

    # 報表需求
    request = """請產生本週的業務報表（2025-11-01 到 2025-11-08）。

報表需包含：
1. 用戶註冊統計
   - 資料來源：data/users.csv
   - 需要生成趨勢圖表（圖表儲存在 charts/user_growth.png）

2. 系統錯誤分析
   - 資料來源：logs/app.log
   - 統計 ERROR 和 WARNING 的數量
   - 列出前 5 個最常見的錯誤

3. API 使用量
   - 資料來源：logs/api.log
   - 統計各 endpoint 的呼叫次數

最終報表儲存為：reports/weekly_report_2025-11-08.md
"""

    print("📝 報表需求：")
    print(request)
    print()
    print("🚀 開始生成報表...\n")

    # 生成報表
    result = coordinator.generate_report(request)

    # 顯示結果
    print("\n" + "=" * 60)
    if result["success"]:
        print("✅ 報表生成成功！")
        print(f"\n{result['message']}")

        print("\n📋 執行步驟：")
        for step in result["steps"]:
            print(f"  {step}")
    else:
        print("❌ 報表生成失敗")
        print(f"原因：{result['message']}")

    print("=" * 60)


if __name__ == "__main__":
    main()
