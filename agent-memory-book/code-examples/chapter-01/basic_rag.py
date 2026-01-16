"""
企業文件問答助手 v0.1
Chapter 1 - 基礎 RAG 系統完整實作

使用方式:
1. pip install -r requirements.txt
2. 創建 .env 文件並設定 OPENAI_API_KEY
3. 將文件放入 ./documents/ 目錄
4. python basic_rag.py
"""

import os
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


class DocumentProcessor:
    """
    文件處理器
    ‹1› 負責載入和分割文件
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        # ‹2› 遞歸分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )

    def load_documents(self, directory: str) -> List[Document]:
        """載入目錄下的所有文件"""
        documents = []
        dir_path = Path(directory)

        # PDF 文件
        for pdf_path in dir_path.glob("**/*.pdf"):
            try:
                loader = PyPDFLoader(str(pdf_path))
                documents.extend(loader.load())
                print(f"已載入: {pdf_path.name}")
            except Exception as e:
                print(f"載入 {pdf_path.name} 失敗: {e}")

        # 文本文件
        for txt_path in dir_path.glob("**/*.txt"):
            try:
                loader = TextLoader(str(txt_path), encoding="utf-8")
                documents.extend(loader.load())
                print(f"已載入: {txt_path.name}")
            except Exception as e:
                print(f"載入 {txt_path.name} 失敗: {e}")

        # Markdown 文件
        for md_path in dir_path.glob("**/*.md"):
            try:
                loader = TextLoader(str(md_path), encoding="utf-8")
                documents.extend(loader.load())
                print(f"已載入: {md_path.name}")
            except Exception as e:
                print(f"載入 {md_path.name} 失敗: {e}")

        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """分割文件"""
        chunks = self.text_splitter.split_documents(documents)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
        print(f"共分割成 {len(chunks)} 個文本塊")
        return chunks


class VectorStoreManager:
    """
    向量資料庫管理器
    ‹3› 負責向量化和儲存
    """

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "enterprise_docs"
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vector_store = None

    def create_index(self, documents: List[Document]) -> None:
        """建立向量索引"""
        print("正在建立向量索引...")
        self.vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
            collection_name=self.collection_name
        )
        print(f"索引建立完成，共 {len(documents)} 個向量")

    def load_index(self) -> None:
        """載入已存在的索引"""
        self.vector_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name=self.collection_name
        )
        print("已載入現有索引")

    def search(self, query: str, k: int = 5) -> List[Document]:
        """相似度搜尋"""
        if not self.vector_store:
            raise ValueError("請先建立或載入索引")
        return self.vector_store.similarity_search(query, k=k)


class RAGEngine:
    """
    RAG 引擎
    ‹4› 整合檢索和生成
    """

    def __init__(
        self,
        vector_store_manager: VectorStoreManager,
        model_name: str = "gpt-4o-mini"
    ):
        self.vector_manager = vector_store_manager
        self.llm = ChatOpenAI(model=model_name, temperature=0)

        # ‹5› RAG 提示模板
        self.prompt_template = ChatPromptTemplate.from_template("""
你是一個專業的企業知識助手。請根據以下提供的文件內容回答使用者的問題。

重要規則：
1. 只根據提供的文件內容回答，不要使用外部知識
2. 如果文件內容無法回答問題，請說「根據提供的資料，我無法找到這個問題的答案」
3. 回答時請引用相關的文件來源
4. 保持回答簡潔、專業

## 參考文件內容
{context}

## 使用者問題
{question}

## 回答
""")

    def _format_docs(self, docs: List[Document]) -> str:
        """格式化檢索結果"""
        formatted = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "未知來源")
            page = doc.metadata.get("page", "")
            page_info = f" (第 {page + 1} 頁)" if page != "" else ""
            formatted.append(f"""
---文件 {i}{page_info}---
來源: {source}
內容: {doc.page_content}
""")
        return "\n".join(formatted)

    def query(self, question: str, k: int = 5) -> Dict[str, Any]:
        """執行 RAG 查詢"""
        # 檢索
        retrieved_docs = self.vector_manager.search(question, k=k)
        context = self._format_docs(retrieved_docs)

        # 生成
        chain = self.prompt_template | self.llm | StrOutputParser()
        answer = chain.invoke({"context": context, "question": question})

        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "content": doc.page_content[:200] + "...",
                    "source": doc.metadata.get("source", "未知"),
                    "page": doc.metadata.get("page", None)
                }
                for doc in retrieved_docs
            ]
        }


def main():
    """主程式"""
    # 初始化
    doc_processor = DocumentProcessor(chunk_size=512, chunk_overlap=50)
    vector_manager = VectorStoreManager()

    documents_dir = "./documents"

    # 確保文件目錄存在
    Path(documents_dir).mkdir(exist_ok=True)

    # 檢查是否已有索引
    if Path("./chroma_db").exists():
        print("發現現有索引，直接載入...")
        vector_manager.load_index()
    else:
        # 載入文件
        documents = doc_processor.load_documents(documents_dir)
        if not documents:
            print(f"請將文件放入 {documents_dir} 目錄後重新執行")
            return

        chunks = doc_processor.split_documents(documents)
        vector_manager.create_index(chunks)

    # 初始化 RAG 引擎
    rag_engine = RAGEngine(vector_manager)

    # 互動式查詢
    print("\n=== 企業文件問答助手 v0.1 ===")
    print("輸入問題開始查詢，輸入 'quit' 退出\n")

    while True:
        question = input("你的問題: ").strip()

        if question.lower() == 'quit':
            print("再見！")
            break

        if not question:
            continue

        result = rag_engine.query(question)

        print(f"\n回答: {result['answer']}")
        print("\n參考來源:")
        for i, source in enumerate(result['sources'], 1):
            print(f"  {i}. {source['source']}")
        print()


if __name__ == "__main__":
    main()
