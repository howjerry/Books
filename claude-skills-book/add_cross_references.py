#!/usr/bin/env python3
"""
自動添加章節交叉引用到 Claude Skills 技術書
"""

CROSS_REFERENCES = {
    "chapter-01.md": [
        {
            "search": "## 1.2 認識 Claude Code Skills",
            "insert_after": True,
            "content": "\n> 💡 **學習路徑**：閱讀完本節後，建議繼續 **Chapter 2** 實際建立開發環境，再於 **Chapter 3** 深入學習 SKILL.md 語法規範。\n"
        },
        {
            "search": "### 1.3.3 WebGuard 系統架構概覽",
            "insert_after": True,
            "content": "\n> 📖 **深入閱讀**：完整的 WebGuard 系統架構實作詳見 **Chapter 9.1-9.2**，包含四層架構的詳細設計與 PostgreSQL Schema。\n"
        },
        {
            "search": "### 1.4.1 場景：檢查用戶登入流程",
            "insert_after": True,
            "content": "\n> 🔗 **實作參考**：Stagehand 瀏覽器自動化的完整教學見 **Chapter 4**，登入測試 Skill 的詳細實作見 **Chapter 4.3**。\n"
        }
    ],
    "chapter-02.md": [
        {
            "search": "## 2.3 創建第一個 Skill",
            "insert_after": True,
            "content": "\n> 💡 **進階閱讀**：本節介紹基礎 Skill 結構。關於 SKILL.md 的完整語法規範、參數驗證、錯誤處理等進階主題，詳見 **Chapter 3**。\n"
        },
        {
            "search": "## 2.4 測試 Skill",
            "insert_after": True,
            "content": "\n> 🔗 **延伸學習**：生產環境的測試策略和 CI/CD 整合見 **Chapter 8**，完整的測試金字塔實作見 **Chapter 8.2-8.3**。\n"
        }
    ],
    "chapter-03.md": [
        {
            "search": "## 3.1 SKILL.md 完整語法規範",
            "insert_after": True,
            "content": "\n> 📖 **實作範例**：想看完整的 SKILL.md 實作？參考 **Chapter 4.3**（瀏覽器登入測試）、**Chapter 5.2**（Excel 數據處理）、**Chapter 6.2**（API 健康檢查）。\n"
        },
        {
            "search": "### 3.3 Skills 生命週期",
            "insert_after": True,
            "content": "\n> 🔄 **系統整合**：Skills 在完整系統中的執行流程，包含編排層、執行層的協作機制，詳見 **Chapter 9.2-9.3**。\n"
        },
        {
            "search": "### 3.6 生產級 Skills 開發",
            "insert_after": True,
            "content": "\n> 🎯 **進階主題**：Skills 的編排與組合模式見 **Chapter 7**，企業級安全方案見 **Chapter 10.2**，性能優化技巧見 **Chapter 4.8** 和 **Chapter 10.3**。\n"
        },
        {
            "search": "## 3.7 本章總結",
            "insert_before": True,
            "content": "\n> 🚀 **下一步**：掌握 Skills 核心概念後，接下來學習 **Chapter 4** 的 Stagehand 瀏覽器自動化，這是構建 WebGuard 系統的關鍵技術。\n\n"
        }
    ],
    "chapter-04.md": [
        {
            "search": "## 4.1 認識 Stagehand",
            "insert_after": True,
            "content": "\n> 💡 **前置知識**：本章假設你已了解 Skills 基本概念（**Chapter 3**）。如需複習 SKILL.md 語法，返回 **Chapter 3.1-3.2**。\n"
        },
        {
            "search": "## 4.6 WebGuard 瀏覽器測試模組",
            "insert_after": True,
            "content": "\n> 🔗 **系統整合**：本節的瀏覽器測試模組是 WebGuard 執行層的一部分。完整的四層架構見 **Chapter 9**，CI/CD 整合見 **Chapter 8**。\n"
        },
        {
            "search": "### 4.8.1 Stagehand 性能優化技巧",
            "insert_after": True,
            "content": "\n> ⚡ **企業級優化**：生產環境的性能調優、資源管理、成本控制等進階主題，詳見 **Chapter 10.3**。\n"
        },
        {
            "search": "## 4.7 本章總結",
            "insert_before": True,
            "content": "\n> 🎯 **學習路徑**：掌握瀏覽器自動化後，繼續 **Chapter 5**（數據處理）和 **Chapter 6**（API 測試），完整 WebGuard 技能棧。\n\n"
        }
    ],
    "chapter-05.md": [
        {
            "search": "# 第 5 章",
            "insert_after": True,
            "content": "\n> 📚 **章節定位**：本章聚焦數據與文件處理自動化。結合 **Chapter 4** 的瀏覽器測試和本章的數據處理，你將具備端到端測試能力。\n"
        }
    ],
    "chapter-06.md": [
        {
            "search": "# 第 6 章",
            "insert_after": True,
            "content": "\n> 🔗 **技能整合**：API 測試與瀏覽器測試（**Chapter 4**）、數據處理（**Chapter 5**）共同構成完整的測試覆蓋。\n"
        }
    ],
    "chapter-07.md": [
        {
            "search": "# 第 7 章",
            "insert_after": True,
            "content": "\n> 🎯 **進階階段**：本章探討 Skills 組合與編排。需具備 **Chapters 3-6** 的基礎，特別是 **Chapter 3** 的核心概念。\n"
        }
    ],
    "chapter-08.md": [
        {
            "search": "# 第 8 章",
            "insert_after": True,
            "content": "\n> 🔄 **系統整合**：CI/CD 是將前面章節的 Skills 整合到開發流程的關鍵。部署架構見 **Chapter 9-10**。\n"
        }
    ],
    "chapter-09.md": [
        {
            "search": "# 第 9 章",
            "insert_after": True,
            "content": "\n> 🏗️ **系統架構**：本章整合 **Chapters 1-8** 的所有內容，構建完整的 WebGuard 系統。建議按順序學習前面章節。\n"
        },
        {
            "search": "## 9.2 執行層設計",
            "insert_after": True,
            "content": "\n> 🔗 **Skills 實作**：執行層使用的 Skills 在 **Chapters 4-6** 有詳細說明：瀏覽器測試（Ch4）、數據處理（Ch5）、API 測試（Ch6）。\n"
        }
    ],
    "chapter-10.md": [
        {
            "search": "# 第 10 章",
            "insert_after": True,
            "content": "\n> 🚀 **最終章**：本章涵蓋企業級部署、安全與 MCP 生態。回顧安全設計見 **Chapter 3.6.7**，性能優化見 **Chapter 4.8**。\n"
        },
        {
            "search": "## 10.2 Kubernetes 生產環境部署",
            "insert_after": True,
            "content": "\n> 📦 **容器化基礎**：K8s 部署前需要容器化（**Chapter 9.7**）。配置範本詳見 **附錄 B**。\n"
        }
    ]
}

def add_references():
    """添加交叉引用到各章節"""
    import os

    chapters_dir = "/home/user/Books/claude-skills-book/chapters"

    for filename, references in CROSS_REFERENCES.items():
        filepath = os.path.join(chapters_dir, filename)

        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filename}")
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        modified = False

        for ref in references:
            search_text = ref["search"]
            insert_content = ref["content"]

            if search_text in content:
                if ref.get("insert_after", False):
                    # 在搜尋文本後插入
                    content = content.replace(
                        search_text,
                        search_text + insert_content
                    )
                elif ref.get("insert_before", False):
                    # 在搜尋文本前插入
                    content = content.replace(
                        search_text,
                        insert_content + search_text
                    )
                modified = True
                print(f"✓ Added reference in {filename}: {search_text[:50]}...")
            else:
                print(f"✗ Not found in {filename}: {search_text[:50]}...")

        if modified and content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Updated: {filename}\n")
        else:
            print(f"⏭️  No changes: {filename}\n")

if __name__ == "__main__":
    print("🔗 Adding cross-references to Claude Skills book...\n")
    add_references()
    print("\n✅ Cross-reference addition complete!")
