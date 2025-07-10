# app/rag_core.py

import os
import shutil
import re
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import pandas as pd
import streamlit as st

# 自作モジュールから設定をインポート
from app.config import LLM_MODEL, EMBEDDING_MODEL

# ディレクトリ名を定義
KNOWLEDGE_DIR = "knowledge_files"
VECTOR_STORE_DIR = "vector_stores"


@st.cache_resource
def get_models():
    """
    OllamaのLLMと埋め込みモデルをロードする。
    `@st.cache_resource`デコレータにより、一度ロードしたらキャッシュされ、アプリの再実行時に再ロードしない。
    """
    llm = Ollama(model=LLM_MODEL)
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    return llm, embeddings

def load_document(file_path: str) -> list[Document]:
    """
    単一のファイルを拡張子に応じて読み込む。
    TXTファイルの場合は、箇条書きなどを正しく分割するための前処理を行う。
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    source_filename = os.path.basename(file_path)
    
    docs = []
    try:
        if file_extension == ".pdf":
            loader = PyPDFLoader(file_path)
            docs = loader.load()
        elif file_extension == ".docx":
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
        elif file_extension == ".xlsx":
            xls = pd.ExcelFile(file_path)
            docs = [Document(page_content=pd.read_excel(xls, s).to_string(), metadata={"source": source_filename, "sheet": s}) for s in xls.sheet_names]
        elif file_extension == ".txt":
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # 箇条書きや項目（「- 」「・ 」「数字. 」）の前に強制的に空行を2つ挿入し、段落として独立させる
            processed_content = re.sub(r'(\n|^)(-|・|\d+\.) ', r'\1\n\n\2 ', content)
            docs = [Document(page_content=processed_content, metadata={"source": source_filename})]
    except Exception as e:
        print(f"Error loading document {file_path}: {e}")
        return []

    # すべてのドキュメントにファイル名をメタデータとして付与
    for doc in docs:
        if 'source' not in doc.metadata:
            doc.metadata['source'] = source_filename
    return docs

def sync_knowledge_base():
    """
    `knowledge_files`フォルダと`vector_stores`フォルダの状態を同期させる。
    - `knowledge_files`に無くて`vector_stores`にあるものは削除。
    - `knowledge_files`にあって`vector_stores`に無いものは新規作成。
    """
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
    
    source_folders = {d for d in os.listdir(KNOWLEDGE_DIR) if os.path.isdir(os.path.join(KNOWLEDGE_DIR, d))}
    vector_store_folders = {d for d in os.listdir(VECTOR_STORE_DIR) if os.path.isdir(os.path.join(VECTOR_STORE_DIR, d))}

    # 不要になったベクトルストアを削除
    folders_to_delete = vector_store_folders - source_folders
    for folder in folders_to_delete:
        shutil.rmtree(os.path.join(VECTOR_STORE_DIR, folder))

    # 新しく追加されたフォルダを処理
    folders_to_process = source_folders - vector_store_folders
    if not folders_to_process and not folders_to_delete:
        return f"ナレッジは最新です。({len(source_folders)}件)"

    # 処理対象がある場合のみモデルをロード
    _, embeddings = get_models()
    for kb_name in folders_to_process:
        source_folder_path = os.path.join(KNOWLEDGE_DIR, kb_name)
        vector_store_path = os.path.join(VECTOR_STORE_DIR, kb_name)
        
        all_documents = []
        for filename in os.listdir(source_folder_path):
            file_path = os.path.join(source_folder_path, filename)
            all_documents.extend(load_document(file_path))
        
        if not all_documents: continue

        # テキストを適切なサイズに分割する設定
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "、", " "]
        )
        split_documents = text_splitter.split_documents(all_documents)
        
        # 分割したドキュメントをベクトル化し、ChromaDBに保存
        Chroma.from_documents(
            documents=split_documents, 
            embedding=embeddings,
            persist_directory=vector_store_path
        )
    
    return f"同期完了！ {len(folders_to_process)}件を新規作成し、{len(folders_to_delete)}件を削除しました。"