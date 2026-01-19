# 第 3 章：向量嵌入

> 「嵌入是機器理解世界的眼睛——將萬物化為數學空間中的座標。」

## 本章學習目標

完成本章後，你將能夠：
- 理解 Word2Vec 與 GloVe 的訓練原理與使用場景
- 掌握 BERT、GPT 等動態嵌入模型的工作機制
- 分析嵌入向量的均勻分佈與空間覆蓋率
- 應用 PCA、t-SNE、UMAP 等技術最佳化嵌入向量

---

## 引言：從符號到向量的革命

在計算機的早期歷史中，「蘋果」這個詞在機器眼裡就是一串字符編碼：`\u860b\u679c`。機器不知道蘋果是一種水果，不知道它和「香蕉」有關聯，更不知道「Apple」在某些語境下指的是一家科技公司。

2013 年，Google 的研究團隊發表了 Word2Vec，開啟了詞嵌入的新紀元。突然間，機器可以知道：

```
向量("國王") - 向量("男人") + 向量("女人") ≈ 向量("女王")
```

這個簡單的向量運算揭示了一個深刻的事實：**語義可以被編碼為幾何關係**。

本章將帶你深入了解這個革命是如何發生的，以及如何在實際應用中選擇和最佳化嵌入向量。

---

## 3.1 靜態向量嵌入

靜態嵌入的特點是：每個詞彙有且只有一個固定的向量表示，無論它出現在什麼上下文中。

### 3.1.1 傳統詞向量模型：Word2Vec 與 GloVe

**Word2Vec：預測式方法**

Word2Vec 於 2013 年由 Mikolov 等人提出，有兩種架構：

```
1. CBOW (Continuous Bag of Words)
   給定上下文，預測中心詞

   輸入：[我, 喜歡, ___, 音樂, 很久了]
   預測：聽

2. Skip-gram
   給定中心詞，預測上下文

   輸入：聽
   預測：[我, 喜歡, 音樂, 很久了]
```

**Skip-gram 模型的數學原理**

```
目標函數：最大化語料庫的對數似然

L = Σ Σ log P(w_{t+j} | w_t)
    t  j

其中：
- w_t 是中心詞
- w_{t+j} 是上下文詞（窗口內）
- j ∈ [-c, c]，c 是窗口大小

條件概率使用 softmax：

P(w_o | w_i) = exp(v'_{w_o} · v_{w_i}) / Σ exp(v'_w · v_{w_i})
                                         w

其中：
- v_w 是詞 w 的「輸入向量」
- v'_w 是詞 w 的「輸出向量」
```

**實際訓練中的最佳化**

由於詞彙表可能有數萬甚至數十萬詞，計算完整的 softmax 代價太高。Word2Vec 使用以下技巧：

```
1. 負採樣 (Negative Sampling)

   不計算所有詞的概率，而是：
   - 對正例（真正的上下文詞）：最大化其概率
   - 對負例（隨機採樣的詞）：最小化其概率

   新目標函數：
   log σ(v'_{w_o} · v_{w_i}) + Σ E_{w_j ~ P_n(w)} [log σ(-v'_{w_j} · v_{w_i})]
                               k

   其中 k 是負樣本數量（通常 5-20）

2. 層次 Softmax (Hierarchical Softmax)

   使用霍夫曼樹組織詞彙
   計算複雜度從 O(V) 降到 O(log V)
```

**Word2Vec 的 Python 實現示例**

```python
from gensim.models import Word2Vec
import numpy as np

# 準備訓練資料（分詞後的句子列表）
sentences = [
    ["我", "喜歡", "機器", "學習"],
    ["深度", "學習", "是", "機器", "學習", "的", "分支"],
    ["自然", "語言", "處理", "使用", "深度", "學習"],
    # ... 更多句子
]

# 訓練 Word2Vec 模型
model = Word2Vec(
    sentences=sentences,
    vector_size=100,      # ‹1› 向量維度
    window=5,             # ‹2› 上下文窗口大小
    min_count=1,          # ‹3› 最小詞頻
    workers=4,            # ‹4› 訓練執行緒數
    sg=1,                 # ‹5› 1=Skip-gram, 0=CBOW
    negative=5,           # ‹6› 負採樣數量
    epochs=10             # ‹7› 訓練輪數
)

# 獲取詞向量
vector = model.wv["機器"]
print(f"「機器」的向量維度: {vector.shape}")  # (100,)

# 尋找相似詞
similar_words = model.wv.most_similar("學習", topn=5)
print("與「學習」最相似的詞:", similar_words)

# 向量運算
result = model.wv.most_similar(
    positive=["國王", "女人"],
    negative=["男人"],
    topn=1
)
print("國王 - 男人 + 女人 =", result)  # 期望: 女王
```

**GloVe：統計式方法**

GloVe (Global Vectors) 於 2014 年由 Stanford 提出，它結合了基於計數的方法和預測式方法的優點。

```
核心思想：利用全局的詞-詞共現統計

1. 建立共現矩陣 X
   X_ij = 詞 i 和詞 j 在窗口內共同出現的次數

2. 定義目標函數
   J = Σ f(X_ij) (w_i · w̃_j + b_i + b̃_j - log X_ij)²
      i,j

   其中：
   - w_i, w̃_j 是詞向量
   - b_i, b̃_j 是偏置項
   - f(x) 是權重函數，降低高頻詞的影響

3. 權重函數
   f(x) = { (x/x_max)^α  if x < x_max
          { 1            otherwise

   通常 x_max = 100, α = 0.75
```

**GloVe vs Word2Vec 對比**

| 特性 | Word2Vec | GloVe |
|------|----------|-------|
| 方法類型 | 預測式（局部上下文） | 統計式（全局共現） |
| 訓練方式 | 在線學習，逐句處理 | 先建共現矩陣，再最佳化 |
| 記憶體需求 | 較低 | 較高（需存儲共現矩陣） |
| 訓練速度 | 中等 | 較快（一次遍歷） |
| 語義捕捉 | 局部語義關係 | 全局統計規律 |
| 適用場景 | 流式資料、動態更新 | 靜態語料庫 |

**使用預訓練的 GloVe 向量**

```python
import numpy as np

def load_glove_vectors(filepath: str, dimension: int = 300) -> dict:
    """
    載入 GloVe 預訓練向量

    ‹1› GloVe 檔案格式：每行是「詞 維度1 維度2 ... 維度N」
    """
    word_vectors = {}

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            values = line.split()
            word = values[0]
            vector = np.array(values[1:], dtype='float32')
            if len(vector) == dimension:
                word_vectors[word] = vector

    return word_vectors

# 載入預訓練向量
glove = load_glove_vectors('glove.6B.300d.txt', 300)

# 計算詞語相似度
def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

sim = cosine_similarity(glove['king'], glove['queen'])
print(f"king 和 queen 的相似度: {sim:.4f}")
```

### 3.1.2 靜態嵌入的局限性：語義多義性與上下文缺失

靜態嵌入有一個根本性的缺陷：**無法處理一詞多義**。

**多義詞問題示例**

```
「蘋果」的不同含義：

1. "我吃了一個蘋果"          → 水果
2. "蘋果發布了新手機"        → Apple 公司
3. "紐約被稱為大蘋果"        → 城市暱稱

在靜態嵌入中，這三個「蘋果」的向量完全相同！
```

```python
# 靜態嵌入無法區分多義詞
from gensim.models import Word2Vec

# 假設已訓練模型
apple_vector = model.wv["蘋果"]

# 無論在什麼語境，向量都相同
sentences = [
    "我吃了一個蘋果",
    "蘋果發布了新手機",
    "紐約被稱為大蘋果"
]

# 要區分含義，需要額外的消歧處理
```

**上下文缺失的影響**

```
否定語義問題：

"這部電影很好看"  →  向量 A
"這部電影不好看"  →  向量 B

靜態嵌入中，「好看」的向量是固定的
「不」的向量也是固定的
A 和 B 的差異取決於句子向量的組合方式
但無法精確捕捉「不」對「好看」的否定作用
```

**比較級和程度問題**

```
"稍微有點熱"  vs  "非常熱"  vs  "熱死了"

靜態嵌入難以精確表達程度差異
因為「熱」的向量在三個句子中相同
```

### 3.1.3 靜態向量嵌入在特定領域的應用

儘管有局限性，靜態嵌入在某些場景仍然有價值：

**1. 詞彙級任務**

```python
# 詞彙相似度計算
def find_similar_words(word: str, model, topn: int = 10):
    """尋找相似詞"""
    return model.wv.most_similar(word, topn=topn)

# 詞彙類比
def word_analogy(a: str, b: str, c: str, model):
    """a 之於 b，如同 c 之於 ?"""
    return model.wv.most_similar(positive=[b, c], negative=[a], topn=1)

# 例如：man:woman = king:?
result = word_analogy("man", "king", "woman", model)
# 期望結果：queen
```

**2. 資源受限環境**

```
靜態嵌入的優勢：

- 記憶體佔用小：只需載入詞向量矩陣
- 推理速度快：直接查表，無需模型計算
- 離線可用：不需要 GPU 或大量計算資源

適用場景：
- 行動裝置應用
- 邊緣計算設備
- 低成本部署
```

**3. 領域特定詞彙**

```python
# 在專業領域語料上訓練 Word2Vec

# 醫學領域
medical_sentences = [
    ["患者", "出現", "發熱", "症狀"],
    ["建議", "服用", "退燒藥"],
    ["高血壓", "需要", "長期", "用藥"],
    # ... 更多醫學文本
]

medical_model = Word2Vec(
    sentences=medical_sentences,
    vector_size=200,
    window=10,
    min_count=2,
    epochs=50
)

# 訓練後，模型能理解醫學術語的關係
similar_to_fever = medical_model.wv.most_similar("發熱")
# 可能返回：感染、炎症、體溫升高 等
```

---

## 3.2 動態向量嵌入

動態嵌入的革命性特點是：**同一個詞在不同上下文中有不同的向量表示**。

### 3.2.1 動態詞向量的生成：BERT 與 GPT 的嵌入機制

**Transformer 架構回顧**

BERT 和 GPT 都基於 Transformer 架構，其核心是自注意力機制（Self-Attention）。

```
自注意力機制的直覺：

輸入序列：[我, 喜歡, 蘋果, 手機]

對於「蘋果」這個詞：
- 注意到「手機」→ 理解這是 Apple 公司
- 如果上下文是「吃」「甜」→ 理解這是水果

自注意力公式：

Attention(Q, K, V) = softmax(QK^T / √d_k) V

其中：
- Q (Query): 查詢向量
- K (Key): 鍵向量
- V (Value): 值向量
- d_k: 鍵向量的維度

每個詞的輸出是所有詞的加權組合
權重由該詞與其他詞的相關性決定
```

**BERT 的嵌入生成**

BERT (Bidirectional Encoder Representations from Transformers) 使用雙向上下文。

```
BERT 的輸入表示：

Token Embeddings:    [CLS]   我    喜歡   蘋果   [SEP]
       +
Segment Embeddings:   A     A      A      A      A
       +
Position Embeddings:  0     1      2      3      4
       =
Input Embeddings:   (綜合表示，每個位置 768 維)

BERT 的處理流程：

輸入 → Token Embedding → N 層 Transformer → 上下文化的輸出

每一層的輸出都可以作為嵌入使用：
- 淺層（Layer 1-4）：捕捉語法特徵
- 中層（Layer 5-8）：捕捉語義特徵
- 深層（Layer 9-12）：捕捉任務特定特徵
```

**使用 BERT 生成嵌入**

```python
from transformers import BertTokenizer, BertModel
import torch

# 載入預訓練模型
tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
model = BertModel.from_pretrained('bert-base-chinese')
model.eval()

def get_bert_embeddings(text: str, layer: int = -1) -> torch.Tensor:
    """
    獲取 BERT 嵌入

    ‹1› layer: 使用哪一層的輸出，-1 表示最後一層
    """
    # 分詞
    inputs = tokenizer(
        text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512
    )

    # 前向傳播
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)

    # 獲取指定層的輸出
    if layer == -1:
        hidden_states = outputs.last_hidden_state
    else:
        hidden_states = outputs.hidden_states[layer]

    return hidden_states

# 測試多義詞
sentences = [
    "我今天吃了一個蘋果，很甜",
    "蘋果公司發布了新款 iPhone"
]

for sent in sentences:
    embeddings = get_bert_embeddings(sent)
    # 找到「蘋果」的位置並提取其嵌入
    tokens = tokenizer.tokenize(sent)
    if "蘋果" in sent:
        # 獲取「蘋果」的嵌入
        apple_idx = tokens.index("蘋") + 1  # +1 因為 [CLS]
        apple_embedding = embeddings[0, apple_idx, :]
        print(f"句子: {sent}")
        print(f"「蘋」的嵌入形狀: {apple_embedding.shape}")
```

**GPT 的嵌入生成**

GPT (Generative Pre-trained Transformer) 使用單向（從左到右）上下文。

```
GPT 與 BERT 的區別：

BERT (雙向)：
[我] ← → [喜歡] ← → [蘋果]
每個詞可以看到前後所有詞

GPT (單向)：
[我] → [喜歡] → [蘋果]
每個詞只能看到前面的詞

GPT 適合：文字生成任務
BERT 適合：文字理解任務

對於嵌入生成：
- BERT 通常更好（利用雙向上下文）
- GPT 也可用，特別是 GPT-3 之後的大模型
```

**OpenAI 的嵌入 API**

```python
import openai

client = openai.OpenAI()

def get_openai_embedding(text: str, model: str = "text-embedding-3-small"):
    """
    使用 OpenAI API 獲取嵌入

    可用模型：
    - text-embedding-3-small: 1536 維，速度快，成本低
    - text-embedding-3-large: 3072 維，精度高
    - text-embedding-ada-002: 1536 維，舊版模型
    """
    response = client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

# 比較多義詞的嵌入
sentences = [
    "我今天吃了一個蘋果",
    "蘋果公司的股價上漲了"
]

embeddings = [get_openai_embedding(s) for s in sentences]

# 計算相似度
import numpy as np
similarity = np.dot(embeddings[0], embeddings[1]) / (
    np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
)
print(f"兩個「蘋果」句子的相似度: {similarity:.4f}")
# 動態嵌入能夠區分不同含義，相似度會較低
```

### 3.2.2 動態嵌入的優勢：上下文敏感性與語義一致性

**上下文敏感性示例**

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-mpnet-base-v2')

# 多義詞在不同上下文中的嵌入
sentences = [
    "銀行的利率調整了",           # 金融機構
    "我坐在河銀行休息",           # 河岸（bank 的另一個含義）
    "這家銀行服務很好",           # 金融機構
    "血銀行急需 O 型血",          # 血庫
]

embeddings = model.encode(sentences)

# 計算相似度矩陣
from sklearn.metrics.pairwise import cosine_similarity
sim_matrix = cosine_similarity(embeddings)

print("相似度矩陣：")
for i, s1 in enumerate(sentences):
    for j, s2 in enumerate(sentences):
        if j > i:
            print(f"'{s1[:10]}...' vs '{s2[:10]}...': {sim_matrix[i][j]:.3f}")
```

**語義一致性的保證**

動態嵌入能夠維持語義的一致性，即使用詞不同：

```python
# 語義等價的句子應該有相似的嵌入
semantic_pairs = [
    ("這部電影非常精彩", "這部電影很好看"),
    ("我需要幫助", "我需要協助"),
    ("天氣很熱", "溫度很高"),
]

for s1, s2 in semantic_pairs:
    e1, e2 = model.encode([s1, s2])
    sim = cosine_similarity([e1], [e2])[0][0]
    print(f"'{s1}' vs '{s2}': {sim:.3f}")

# 語義相反的句子應該有較低的相似度
opposite_pairs = [
    ("這部電影很好看", "這部電影很難看"),
    ("我喜歡這個", "我討厭這個"),
]

for s1, s2 in opposite_pairs:
    e1, e2 = model.encode([s1, s2])
    sim = cosine_similarity([e1], [e2])[0][0]
    print(f"'{s1}' vs '{s2}': {sim:.3f}")
```

### 3.2.3 動態向量嵌入的即時生成與最佳化

**批次處理最佳化**

```python
import torch
from transformers import AutoTokenizer, AutoModel
from typing import List
import numpy as np

class EfficientEmbedder:
    """
    高效的嵌入生成器

    ‹1› 支援批次處理
    ‹2› 支援 GPU 加速
    ‹3› 支援不同的池化策略
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = None,
        max_length: int = 512
    ):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

        # 自動選擇設備
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.model.to(self.device)
        self.model.eval()
        self.max_length = max_length

    def _mean_pooling(
        self,
        model_output: torch.Tensor,
        attention_mask: torch.Tensor
    ) -> torch.Tensor:
        """平均池化"""
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(
            token_embeddings.size()
        ).float()
        return torch.sum(
            token_embeddings * input_mask_expanded, 1
        ) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True,
        normalize: bool = True
    ) -> np.ndarray:
        """
        批次生成嵌入

        ‹1› normalize: 是否 L2 正規化
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            # 分詞
            encoded = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors='pt'
            )

            # 移動到指定設備
            encoded = {k: v.to(self.device) for k, v in encoded.items()}

            # 前向傳播
            with torch.no_grad():
                outputs = self.model(**encoded)

            # 池化
            embeddings = self._mean_pooling(
                outputs,
                encoded['attention_mask']
            )

            # 正規化
            if normalize:
                embeddings = torch.nn.functional.normalize(
                    embeddings, p=2, dim=1
                )

            all_embeddings.append(embeddings.cpu().numpy())

            if show_progress:
                progress = min((i + batch_size) / len(texts) * 100, 100)
                print(f"\r生成嵌入進度: {progress:.1f}%", end="")

        if show_progress:
            print()

        return np.vstack(all_embeddings)

# 使用示例
embedder = EfficientEmbedder()
texts = ["這是第一個句子", "這是第二個句子", ...] * 1000
embeddings = embedder.encode(texts, batch_size=64)
```

**快取策略**

```python
import hashlib
import json
from pathlib import Path
import numpy as np

class CachedEmbedder:
    """
    帶快取的嵌入生成器

    ‹1› 相同的文字只計算一次
    ‹2› 支援持久化到磁碟
    """

    def __init__(self, embedder: EfficientEmbedder, cache_dir: str = "./embedding_cache"):
        self.embedder = embedder
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache = {}

    def _get_cache_key(self, text: str) -> str:
        """生成快取鍵"""
        return hashlib.md5(text.encode()).hexdigest()

    def _load_from_disk(self, key: str) -> np.ndarray:
        """從磁碟載入"""
        cache_file = self.cache_dir / f"{key}.npy"
        if cache_file.exists():
            return np.load(cache_file)
        return None

    def _save_to_disk(self, key: str, embedding: np.ndarray):
        """保存到磁碟"""
        cache_file = self.cache_dir / f"{key}.npy"
        np.save(cache_file, embedding)

    def encode(self, texts: list, use_disk_cache: bool = True) -> np.ndarray:
        """
        生成嵌入，優先使用快取
        """
        results = [None] * len(texts)
        texts_to_encode = []
        indices_to_encode = []

        # 檢查快取
        for i, text in enumerate(texts):
            key = self._get_cache_key(text)

            # 記憶體快取
            if key in self.memory_cache:
                results[i] = self.memory_cache[key]
                continue

            # 磁碟快取
            if use_disk_cache:
                embedding = self._load_from_disk(key)
                if embedding is not None:
                    self.memory_cache[key] = embedding
                    results[i] = embedding
                    continue

            # 需要計算
            texts_to_encode.append(text)
            indices_to_encode.append(i)

        # 計算未快取的嵌入
        if texts_to_encode:
            new_embeddings = self.embedder.encode(texts_to_encode)

            for idx, text, embedding in zip(
                indices_to_encode,
                texts_to_encode,
                new_embeddings
            ):
                key = self._get_cache_key(text)
                self.memory_cache[key] = embedding
                if use_disk_cache:
                    self._save_to_disk(key, embedding)
                results[idx] = embedding

        return np.array(results)
```

---

## 3.3 均勻分佈與空間覆蓋率

嵌入向量在高維空間中的分佈對檢索效果有重大影響。理想的嵌入應該均勻分佈，充分利用空間。

### 3.3.1 高維向量分佈分析

**各向異性問題**

研究發現，預訓練語言模型的嵌入空間存在「各向異性」(Anisotropy)：向量傾向於聚集在某些方向。

```python
import numpy as np
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

def analyze_embedding_distribution(embeddings: np.ndarray):
    """
    分析嵌入向量的分佈特性

    ‹1› 計算向量的平均相似度（應該接近 0）
    ‹2› 分析主成分方差分佈
    """
    # 計算平均餘弦相似度
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / norms

    # 隨機採樣計算
    n_samples = min(1000, len(embeddings))
    indices = np.random.choice(len(embeddings), n_samples, replace=False)
    sampled = normalized[indices]

    similarities = np.dot(sampled, sampled.T)
    np.fill_diagonal(similarities, 0)  # 排除自身
    avg_similarity = similarities.sum() / (n_samples * (n_samples - 1))

    print(f"平均餘弦相似度: {avg_similarity:.4f}")
    print(f"(理想值應接近 0，表示向量均勻分佈)")

    # PCA 分析
    pca = PCA()
    pca.fit(embeddings)

    # 方差解釋比例
    explained_variance = pca.explained_variance_ratio_

    print(f"\n前 10 個主成分解釋的方差比例:")
    for i in range(min(10, len(explained_variance))):
        print(f"  PC{i+1}: {explained_variance[i]:.4f}")

    print(f"\n前 10 個主成分累計解釋: {sum(explained_variance[:10]):.4f}")

    return {
        'avg_similarity': avg_similarity,
        'explained_variance': explained_variance
    }

# 分析嵌入分佈
stats = analyze_embedding_distribution(embeddings)
```

**視覺化高維分佈**

```python
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

def visualize_embeddings(
    embeddings: np.ndarray,
    labels: list = None,
    method: str = 'tsne',
    perplexity: int = 30
):
    """
    將高維嵌入降到 2D 視覺化

    ‹1› method: 'tsne' 或 'pca'
    """
    if method == 'tsne':
        reducer = TSNE(n_components=2, perplexity=perplexity, random_state=42)
    else:
        reducer = PCA(n_components=2)

    reduced = reducer.fit_transform(embeddings)

    plt.figure(figsize=(10, 8))

    if labels is not None:
        unique_labels = list(set(labels))
        colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_labels)))

        for label, color in zip(unique_labels, colors):
            mask = [l == label for l in labels]
            plt.scatter(
                reduced[mask, 0],
                reduced[mask, 1],
                c=[color],
                label=label,
                alpha=0.6
            )
        plt.legend()
    else:
        plt.scatter(reduced[:, 0], reduced[:, 1], alpha=0.6)

    plt.title(f'Embedding Visualization ({method.upper()})')
    plt.xlabel('Dimension 1')
    plt.ylabel('Dimension 2')
    plt.tight_layout()
    plt.savefig('embedding_visualization.png', dpi=150)
    plt.show()
```

### 3.3.2 嵌入向量的均勻性測量方法

**均勻性指標**

```python
def compute_uniformity(embeddings: np.ndarray, t: float = 2.0) -> float:
    """
    計算嵌入的均勻性分數

    基於論文 "Understanding Contrastive Representation Learning
    through Alignment and Uniformity on the Hypersphere"

    ‹1› 均勻性越低（負值越大）表示分佈越均勻
    """
    # 正規化到單位球面
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / norms

    # 計算兩兩距離的平方
    n = len(normalized)
    uniformity = 0

    # 批次計算以節省記憶體
    batch_size = 1000
    for i in range(0, n, batch_size):
        batch = normalized[i:i+batch_size]
        # 與所有向量計算距離
        sq_dist = 2 - 2 * np.dot(batch, normalized.T)
        sq_dist = np.clip(sq_dist, 0, None)  # 數值穩定性

        # 排除對角線（自身）
        if i < n:
            for j in range(min(batch_size, n - i)):
                if i + j < n:
                    sq_dist[j, i + j] = np.inf

        uniformity += np.exp(-t * sq_dist).sum()

    uniformity = np.log(uniformity / (n * (n - 1)))
    return uniformity

# 理想的均勻分佈，uniformity 約為 -2.0 到 -3.0
```

**對齊性指標**

```python
def compute_alignment(
    embeddings1: np.ndarray,
    embeddings2: np.ndarray,
    alpha: float = 2.0
) -> float:
    """
    計算嵌入對之間的對齊性

    ‹1› 對齊性用於測量正樣本對之間的距離
    ‹2› 對齊性越低表示正樣本越接近
    """
    assert len(embeddings1) == len(embeddings2)

    # 正規化
    e1 = embeddings1 / np.linalg.norm(embeddings1, axis=1, keepdims=True)
    e2 = embeddings2 / np.linalg.norm(embeddings2, axis=1, keepdims=True)

    # 計算對應向量之間的距離
    sq_dist = ((e1 - e2) ** 2).sum(axis=1)

    alignment = (sq_dist ** (alpha / 2)).mean()
    return alignment
```

### 3.3.3 空間覆蓋率對檢索性能的影響

**實驗：比較均勻與非均勻嵌入的檢索效果**

```python
import numpy as np
from sklearn.metrics import average_precision_score

def evaluate_retrieval_performance(
    embeddings: np.ndarray,
    queries: np.ndarray,
    ground_truth: list,
    k: int = 10
) -> dict:
    """
    評估檢索性能

    ‹1› ground_truth: 每個查詢的正確答案索引列表
    """
    # 正規化
    emb_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    query_norm = queries / np.linalg.norm(queries, axis=1, keepdims=True)

    # 計算相似度
    similarities = np.dot(query_norm, emb_norm.T)

    # 計算指標
    recalls = []
    precisions = []
    aps = []

    for i, (sim, gt) in enumerate(zip(similarities, ground_truth)):
        # Top-K 結果
        top_k = np.argsort(sim)[-k:][::-1]

        # Recall@K
        hits = len(set(top_k) & set(gt))
        recall = hits / min(k, len(gt))
        recalls.append(recall)

        # Precision@K
        precision = hits / k
        precisions.append(precision)

        # AP (Average Precision)
        y_true = np.zeros(len(embeddings))
        y_true[gt] = 1
        ap = average_precision_score(y_true, sim)
        aps.append(ap)

    return {
        'recall@k': np.mean(recalls),
        'precision@k': np.mean(precisions),
        'map': np.mean(aps)
    }
```

**提升均勻性的方法**

```python
def apply_whitening(embeddings: np.ndarray) -> np.ndarray:
    """
    應用白化變換以提升均勻性

    ‹1› 白化會將嵌入變換為零均值、單位方差
    ‹2› 能夠緩解各向異性問題
    """
    # 中心化
    mean = embeddings.mean(axis=0)
    centered = embeddings - mean

    # 計算協方差矩陣
    cov = np.cov(centered.T)

    # 特徵分解
    eigenvalues, eigenvectors = np.linalg.eigh(cov)

    # 白化變換
    # W = V * D^(-1/2)
    D_inv_sqrt = np.diag(1.0 / np.sqrt(eigenvalues + 1e-5))
    W = eigenvectors @ D_inv_sqrt

    whitened = centered @ W

    return whitened

# 測試白化效果
original_uniformity = compute_uniformity(embeddings)
whitened_embeddings = apply_whitening(embeddings)
whitened_uniformity = compute_uniformity(whitened_embeddings)

print(f"原始均勻性: {original_uniformity:.4f}")
print(f"白化後均勻性: {whitened_uniformity:.4f}")
```

---

## 3.4 嵌入向量最佳化

當原始嵌入不能滿足需求時，我們可以應用各種最佳化技術。

### 3.4.1 主成分分析與奇異值分解的降維應用

**PCA 降維**

```python
from sklearn.decomposition import PCA
import numpy as np

class PCAEmbeddingReducer:
    """
    使用 PCA 進行嵌入降維

    ‹1› 保留最重要的維度
    ‹2› 可以顯著減少儲存和計算成本
    """

    def __init__(self, n_components: int = 128, explained_variance_ratio: float = None):
        """
        ‹1› n_components: 目標維度
        ‹2› explained_variance_ratio: 或者指定保留的方差比例
        """
        if explained_variance_ratio:
            self.pca = PCA(n_components=explained_variance_ratio)
        else:
            self.pca = PCA(n_components=n_components)

        self.is_fitted = False

    def fit(self, embeddings: np.ndarray):
        """訓練 PCA"""
        self.pca.fit(embeddings)
        self.is_fitted = True

        print(f"原始維度: {embeddings.shape[1]}")
        print(f"降維後維度: {self.pca.n_components_}")
        print(f"保留方差比例: {sum(self.pca.explained_variance_ratio_):.4f}")

    def transform(self, embeddings: np.ndarray) -> np.ndarray:
        """應用降維"""
        if not self.is_fitted:
            raise ValueError("請先調用 fit() 方法")
        return self.pca.transform(embeddings)

    def fit_transform(self, embeddings: np.ndarray) -> np.ndarray:
        """訓練並降維"""
        self.fit(embeddings)
        return self.transform(embeddings)

# 使用示例
reducer = PCAEmbeddingReducer(n_components=256)
reduced_embeddings = reducer.fit_transform(embeddings)

# 或者指定方差比例
reducer_90 = PCAEmbeddingReducer(explained_variance_ratio=0.90)
reduced_90 = reducer_90.fit_transform(embeddings)
```

**SVD 降維**

```python
from sklearn.decomposition import TruncatedSVD

class SVDEmbeddingReducer:
    """
    使用 SVD 進行嵌入降維

    ‹1› 比 PCA 更適合大規模稀疏矩陣
    ‹2› 不需要中心化資料
    """

    def __init__(self, n_components: int = 128):
        self.svd = TruncatedSVD(n_components=n_components)

    def fit_transform(self, embeddings: np.ndarray) -> np.ndarray:
        return self.svd.fit_transform(embeddings)

    def get_explained_variance(self) -> float:
        return sum(self.svd.explained_variance_ratio_)
```

### 3.4.2 t-SNE 與 UMAP 降維技術

**t-SNE：適合視覺化**

```python
from sklearn.manifold import TSNE
import numpy as np

def tsne_reduce(
    embeddings: np.ndarray,
    n_components: int = 2,
    perplexity: int = 30,
    n_iter: int = 1000
) -> np.ndarray:
    """
    使用 t-SNE 降維

    ‹1› 保留局部結構
    ‹2› 主要用於視覺化，不建議用於下游任務

    注意：t-SNE 是非確定性的，每次結果可能不同
    """
    tsne = TSNE(
        n_components=n_components,
        perplexity=perplexity,
        n_iter=n_iter,
        random_state=42,
        n_jobs=-1
    )
    return tsne.fit_transform(embeddings)

# t-SNE 參數建議
# perplexity: 通常設為 5-50，較大的資料集用較大的值
# n_iter: 至少 1000，複雜資料可能需要更多
```

**UMAP：更快且保留更多結構**

```python
import umap

def umap_reduce(
    embeddings: np.ndarray,
    n_components: int = 2,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    metric: str = 'cosine'
) -> np.ndarray:
    """
    使用 UMAP 降維

    ‹1› 比 t-SNE 更快
    ‹2› 同時保留局部和全局結構
    ‹3› 可以用於下游任務

    參數說明：
    - n_neighbors: 控制局部結構，較大值保留更多全局結構
    - min_dist: 控制點之間的最小距離，較小值產生更緊湊的聚類
    - metric: 距離度量
    """
    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=42
    )
    return reducer.fit_transform(embeddings)

# UMAP 參數建議
# n_neighbors: 5-50，視資料結構而定
# min_dist: 0.0-0.99，視覺化用較小值，保留結構用較大值
```

**t-SNE vs UMAP 對比**

| 特性 | t-SNE | UMAP |
|------|-------|------|
| 速度 | 慢 | 快（約快 10 倍） |
| 局部結構保留 | 優秀 | 優秀 |
| 全局結構保留 | 差 | 較好 |
| 可用於下游任務 | 不建議 | 可以 |
| 記憶體佔用 | 高 | 較低 |
| 確定性 | 否 | 是（設定 random_state） |

### 3.4.3 降維對嵌入語義保留與性能的權衡分析

**實驗框架**

```python
from typing import Dict, List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def evaluate_dimensionality_reduction(
    original_embeddings: np.ndarray,
    reduced_embeddings: np.ndarray,
    test_queries: np.ndarray,
    ground_truth: List[List[int]],
    k: int = 10
) -> Dict[str, float]:
    """
    評估降維對檢索性能的影響

    ‹1› 比較降維前後的檢索結果
    """
    def retrieve(embeddings, queries, k):
        """執行檢索"""
        results = []
        for query in queries:
            sims = cosine_similarity([query], embeddings)[0]
            top_k = np.argsort(sims)[-k:][::-1]
            results.append(set(top_k))
        return results

    # 原始空間的檢索結果
    original_results = retrieve(original_embeddings, test_queries, k)

    # 降維空間的檢索結果
    # 需要對查詢也進行降維（使用相同的變換）
    # 這裡假設 reduced_queries 已經準備好
    reduced_queries = test_queries  # 實際應用中需要變換

    # 計算指標
    metrics = {}

    # 1. 檢索一致性：降維前後返回相同結果的比例
    consistency_scores = []
    for orig, gt in zip(original_results, ground_truth):
        overlap = len(orig & set(gt)) / k
        consistency_scores.append(overlap)
    metrics['consistency'] = np.mean(consistency_scores)

    # 2. Recall@K
    recall_scores = []
    for result, gt in zip(original_results, ground_truth):
        recall = len(result & set(gt)) / min(len(gt), k)
        recall_scores.append(recall)
    metrics['recall@k'] = np.mean(recall_scores)

    return metrics

def find_optimal_dimensions(
    embeddings: np.ndarray,
    test_queries: np.ndarray,
    ground_truth: List[List[int]],
    dimension_candidates: List[int] = [64, 128, 256, 512]
) -> Dict[int, Dict[str, float]]:
    """
    找出最佳降維維度

    ‹1› 評估不同維度下的性能
    ‹2› 平衡精度和效率
    """
    from sklearn.decomposition import PCA

    results = {}

    for n_dim in dimension_candidates:
        if n_dim >= embeddings.shape[1]:
            continue

        # 降維
        pca = PCA(n_components=n_dim)
        reduced = pca.fit_transform(embeddings)
        reduced_queries = pca.transform(test_queries)

        # 評估
        metrics = evaluate_dimensionality_reduction(
            embeddings,
            reduced,
            reduced_queries,
            ground_truth
        )

        # 記錄壓縮比
        metrics['compression_ratio'] = embeddings.shape[1] / n_dim
        metrics['explained_variance'] = sum(pca.explained_variance_ratio_)

        results[n_dim] = metrics

        print(f"維度 {n_dim}:")
        print(f"  方差保留: {metrics['explained_variance']:.4f}")
        print(f"  Recall@10: {metrics['recall@k']:.4f}")
        print(f"  壓縮比: {metrics['compression_ratio']:.2f}x")

    return results
```

**降維的實踐建議**

```
降維決策流程：

1. 確定約束條件
   └── 記憶體限制？延遲要求？精度要求？

2. 評估原始嵌入的冗餘度
   └── 使用 PCA 分析方差分佈
   └── 如果前 50% 維度解釋 > 95% 方差，可以大幅降維

3. 選擇降維方法
   ├── 保留性能優先 → PCA
   ├── 視覺化目的 → t-SNE 或 UMAP
   └── 需要非線性降維 → UMAP

4. 確定目標維度
   └── 在驗證集上測試不同維度
   └── 找到性能下降 < 5% 的最小維度

5. 驗證
   └── 在測試集上確認效果
   └── 監控生產環境中的性能

常見維度選擇：

原始維度    建議降維後維度    說明
768         256              通常性能損失 < 3%
1024        384              常見的折衷選擇
1536        512              OpenAI 嵌入的常見降維
3072        768              保守的降維選擇
```

---

## 3.5 本章小結

在本章中，我們深入探討了向量嵌入的各個方面：

1. **靜態向量嵌入**
   - Word2Vec 使用預測式方法，通過上下文預測學習詞向量
   - GloVe 使用統計式方法，基於全局詞共現統計
   - 靜態嵌入的局限：無法處理多義詞和上下文依賴

2. **動態向量嵌入**
   - BERT 和 GPT 基於 Transformer 架構，生成上下文敏感的嵌入
   - 動態嵌入能夠根據上下文理解同一詞的不同含義
   - 需要更多計算資源，但語義理解能力更強

3. **嵌入空間分析**
   - 各向異性是預訓練模型的常見問題
   - 均勻性和對齊性是衡量嵌入品質的重要指標
   - 白化變換可以改善嵌入的均勻分佈

4. **嵌入最佳化**
   - PCA 和 SVD 用於線性降維，保留最重要的特徵
   - t-SNE 適合視覺化，UMAP 更適合保留結構
   - 降維需要在精度和效率之間取得平衡

理解嵌入是使用向量資料庫的基礎。在下一章中，我們將學習如何在這些向量上進行高效的相似性搜尋。

---

## 3.6 思考題

1. **概念理解**
   - 解釋為什麼 Word2Vec 的「國王 - 男人 + 女人 = 女王」類比能夠成立。這反映了詞向量空間的什麼特性？

2. **技術分析**
   - BERT 有 12 層（base）或 24 層（large），不同層捕捉不同層次的語言特徵。如果你要建構一個句子相似度檢索系統，你會選擇哪一層的輸出作為句子嵌入？為什麼？

3. **實作練習**
   - 使用 Python 實現以下功能：
     a) 載入預訓練的 Word2Vec 或 GloVe 向量
     b) 實現詞彙類比功能（a:b = c:?）
     c) 使用 BERT 對同一個多義詞生成不同上下文的嵌入
     d) 視覺化這些嵌入，觀察多義詞在不同上下文中的位置

4. **系統設計**
   - 你需要為一個多語言客服系統設計嵌入方案，支援中文、英文和日文。請討論：
     a) 應該使用什麼類型的嵌入模型？
     b) 如何處理不同語言之間的語義對齊？
     c) 如何在保持多語言能力的同時控制計算成本？

5. **批判性思考**
   - 「嵌入向量的維度越高，表達能力越強，檢索效果越好」——這個說法對嗎？請結合維度詛咒和計算成本進行分析。

---

> **下一章預告**：在第 4 章中，我們將學習向量相似性搜尋的基礎知識，包括暴力搜尋的實現與最佳化、不同距離度量的比較，以及如何評估搜尋性能。
