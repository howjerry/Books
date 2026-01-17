"""
chapter-02/embedding_visualizer.py

Embedding 視覺化工具

本模組展示如何將文字轉換為 Embedding 向量，並使用 UMAP 降維後視覺化，
讓你親眼看見語義相近的文字在向量空間中靠近。

使用方式：
    python embedding_visualizer.py

依賴安裝：
    pip install sentence-transformers matplotlib umap-learn scikit-learn
"""

from typing import List, Tuple, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import umap
from rich.console import Console
from rich.table import Table

console = Console()

# 設定中文字型（如果系統支援）
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class EmbeddingVisualizer:
    """
    Embedding 視覺化器

    將文字轉換為向量，並提供多種視覺化方法。

    Attributes:
        model: Sentence Transformer 模型
        model_name: 使用的模型名稱
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        初始化視覺化器

        Args:
            model_name: Sentence Transformer 模型名稱
                       多語言推薦：paraphrase-multilingual-MiniLM-L12-v2
                       英文推薦：all-MiniLM-L6-v2
        """
        console.print(f"[yellow]載入模型：{model_name}[/yellow]")
        self.model = SentenceTransformer(model_name)              # ‹1›
        self.model_name = model_name
        console.print(f"[green]✓ 模型載入完成[/green]")
        console.print(f"  向量維度：{self.model.get_sentence_embedding_dimension()}")

    def encode(self, texts: List[str]) -> np.ndarray:
        """
        將文字列表轉換為 Embedding 向量

        Args:
            texts: 要轉換的文字列表

        Returns:
            shape (len(texts), embedding_dim) 的向量矩陣
        """
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True
        )                                                         # ‹2›
        return embeddings

    def compute_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """
        計算兩段文字的餘弦相似度

        Args:
            text1: 第一段文字
            text2: 第二段文字

        Returns:
            餘弦相似度（-1 到 1，越接近 1 越相似）
        """
        emb1 = self.model.encode([text1])[0]
        emb2 = self.model.encode([text2])[0]

        # 餘弦相似度 = dot(a, b) / (||a|| * ||b||)
        similarity = np.dot(emb1, emb2) / (
            np.linalg.norm(emb1) * np.linalg.norm(emb2)
        )                                                         # ‹3›
        return float(similarity)

    def compute_similarity_matrix(
        self,
        texts: List[str]
    ) -> np.ndarray:
        """
        計算文字列表的相似度矩陣

        Args:
            texts: 文字列表

        Returns:
            shape (len(texts), len(texts)) 的相似度矩陣
        """
        embeddings = self.encode(texts)

        # 正規化向量
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms

        # 計算餘弦相似度矩陣
        similarity_matrix = np.dot(normalized, normalized.T)
        return similarity_matrix

    def reduce_dimensions(
        self,
        embeddings: np.ndarray,
        method: str = "umap",
        n_components: int = 2
    ) -> np.ndarray:
        """
        將高維向量降到 2D/3D 以便視覺化

        Args:
            embeddings: 高維 Embedding 向量
            method: 降維方法（"umap" 或 "tsne"）
            n_components: 目標維度（2 或 3）

        Returns:
            降維後的向量
        """
        if method == "umap":
            reducer = umap.UMAP(
                n_components=n_components,
                n_neighbors=min(15, len(embeddings) - 1),
                min_dist=0.1,
                metric='cosine',
                random_state=42
            )                                                     # ‹4›
        elif method == "tsne":
            reducer = TSNE(
                n_components=n_components,
                perplexity=min(30, len(embeddings) - 1),
                random_state=42
            )
        else:
            raise ValueError(f"不支援的降維方法：{method}")

        reduced = reducer.fit_transform(embeddings)
        return reduced

    def visualize_2d(
        self,
        texts: List[str],
        labels: List[str] = None,
        colors: List[str] = None,
        title: str = "Embedding 視覺化",
        method: str = "umap",
        save_path: str = None
    ) -> None:
        """
        2D 視覺化 Embedding

        Args:
            texts: 要視覺化的文字列表
            labels: 每個點的標籤（可選，預設使用文字前 20 字）
            colors: 每個點的顏色（可選）
            title: 圖表標題
            method: 降維方法
            save_path: 儲存路徑（可選）
        """
        # 計算 Embedding
        embeddings = self.encode(texts)

        # 降維
        reduced = self.reduce_dimensions(embeddings, method=method)

        # 準備標籤
        if labels is None:
            labels = [t[:20] + "..." if len(t) > 20 else t for t in texts]

        # 準備顏色
        if colors is None:
            colors = plt.cm.tab10(np.linspace(0, 1, len(texts)))

        # 繪圖
        fig, ax = plt.subplots(figsize=(12, 8))

        for i, (x, y) in enumerate(reduced):
            ax.scatter(x, y, c=[colors[i]], s=100, alpha=0.7)
            ax.annotate(
                labels[i],
                (x, y),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=9,
                alpha=0.8
            )

        ax.set_title(title, fontsize=14)
        ax.set_xlabel(f'{method.upper()} Dimension 1')
        ax.set_ylabel(f'{method.upper()} Dimension 2')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            console.print(f"[green]圖表已儲存至：{save_path}[/green]")

        plt.show()

    def visualize_similarity_heatmap(
        self,
        texts: List[str],
        labels: List[str] = None,
        title: str = "文字相似度熱力圖",
        save_path: str = None
    ) -> None:
        """
        繪製相似度熱力圖

        Args:
            texts: 文字列表
            labels: 標籤列表
            title: 圖表標題
            save_path: 儲存路徑
        """
        # 計算相似度矩陣
        similarity_matrix = self.compute_similarity_matrix(texts)

        # 準備標籤
        if labels is None:
            labels = [t[:15] + "..." if len(t) > 15 else t for t in texts]

        # 繪製熱力圖
        fig, ax = plt.subplots(figsize=(10, 8))

        im = ax.imshow(similarity_matrix, cmap='RdYlGn', vmin=0, vmax=1)

        # 設定軸標籤
        ax.set_xticks(np.arange(len(labels)))
        ax.set_yticks(np.arange(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_yticklabels(labels)

        # 添加數值標註
        for i in range(len(labels)):
            for j in range(len(labels)):
                text = ax.text(
                    j, i, f'{similarity_matrix[i, j]:.2f}',
                    ha='center', va='center',
                    color='white' if similarity_matrix[i, j] > 0.5 else 'black',
                    fontsize=8
                )

        ax.set_title(title, fontsize=14)
        fig.colorbar(im, ax=ax, label='餘弦相似度')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            console.print(f"[green]圖表已儲存至：{save_path}[/green]")

        plt.show()


def demonstrate_vocabulary_gap_solution():
    """演示 Embedding 如何解決詞彙鴻溝問題"""

    console.print("\n[bold blue]═══ Embedding 解決詞彙鴻溝問題演示 ═══[/bold blue]\n")

    visualizer = EmbeddingVisualizer()

    # 準備測試案例：每組包含語義相同但詞彙不同的文字
    test_cases = [
        # (使用者查詢, 知識庫文件, 類別)
        ("密碼忘記了", "如何重設密碼", "帳戶"),
        ("帳號進不去", "登入失敗處理", "帳戶"),
        ("要怎麼付錢", "付款方式說明", "付款"),
        ("可以用 Visa 嗎", "支援信用卡付款", "付款"),
        ("手機版閃退", "App 異常處理", "技術"),
        ("2FA 怎麼開", "啟用雙重驗證", "安全"),
    ]

    # 顯示相似度計算結果
    table = Table(title="詞彙鴻溝問題的語義相似度")
    table.add_column("使用者查詢", style="cyan")
    table.add_column("知識庫文件", style="white")
    table.add_column("餘弦相似度", style="magenta")
    table.add_column("判定", style="green")

    for query, doc, category in test_cases:
        similarity = visualizer.compute_similarity(query, doc)
        judgment = "✓ 匹配" if similarity > 0.5 else "✗ 不匹配"
        table.add_row(
            query,
            doc,
            f"{similarity:.4f}",
            judgment
        )

    console.print(table)

    # 視覺化
    all_texts = []
    labels = []
    colors = []

    color_map = {
        "帳戶": "#e74c3c",
        "付款": "#3498db",
        "技術": "#2ecc71",
        "安全": "#9b59b6",
    }

    for query, doc, category in test_cases:
        all_texts.extend([query, doc])
        labels.extend([f"Q: {query[:10]}", f"D: {doc[:10]}"])
        colors.extend([color_map[category], color_map[category]])

    console.print("\n[yellow]正在生成 Embedding 視覺化...[/yellow]")

    visualizer.visualize_2d(
        all_texts,
        labels=labels,
        colors=colors,
        title="Embedding 空間中的詞彙鴻溝解決方案\n(相同顏色 = 相同概念)",
        save_path="embedding_vocabulary_gap.png"
    )


def demonstrate_embedding_properties():
    """演示 Embedding 的基本性質"""

    console.print("\n[bold blue]═══ Embedding 基本性質演示 ═══[/bold blue]\n")

    visualizer = EmbeddingVisualizer()

    # 測試不同類別的文字
    texts = [
        # 帳戶類
        "如何重設密碼",
        "忘記密碼怎麼辦",
        "密碼找回流程",

        # 付款類
        "如何付款",
        "支付方式有哪些",
        "可以用信用卡嗎",

        # 技術類
        "API 使用教學",
        "如何呼叫介面",
        "開發者文件",

        # 完全不相關
        "今天天氣真好",
        "我喜歡吃蘋果",
    ]

    # 顯示相似度熱力圖
    visualizer.visualize_similarity_heatmap(
        texts,
        title="不同類別文字的相似度熱力圖",
        save_path="embedding_similarity_heatmap.png"
    )


def main():
    """主程式"""

    console.print("\n[bold blue]════════════════════════════════════════════════[/bold blue]")
    console.print("[bold blue]         Embedding 視覺化工具演示              [/bold blue]")
    console.print("[bold blue]════════════════════════════════════════════════[/bold blue]")

    # 1. 演示如何解決詞彙鴻溝
    demonstrate_vocabulary_gap_solution()

    # 2. 演示 Embedding 性質
    demonstrate_embedding_properties()

    console.print("\n[green]✓ 演示完成！[/green]")
    console.print("[dim]生成的圖表已儲存為 PNG 檔案[/dim]")


if __name__ == "__main__":
    main()
