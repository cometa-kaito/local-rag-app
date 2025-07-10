# app/main.py

import streamlit as st
import os
import json
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from app.rag_core import load_document

# 自作モジュールから必要な関数や変数をインポート
from app.rag_core import VECTOR_STORE_DIR, KNOWLEDGE_DIR, get_models, sync_knowledge_base
from app.config import LLM_MODEL

# --- 定数設定 ---
CHAT_HISTORY_DIR = "chat_histories"
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

# --- アプリの基本設定 ---
st.set_page_config(page_title="ナレッジフォルダ検索AI", layout="wide")
st.title("ナレッジフォルダ検索AI")

# --- チャット履歴の保存・読み込み関数 ---
def save_chat_history(kb_name, history):
    """チャット履歴をナレッジベースごとにJSONファイルとして保存する"""
    if kb_name:
        history_file = os.path.join(CHAT_HISTORY_DIR, f"{kb_name}_history.json")
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

def load_chat_history(kb_name):
    """ナレッジベースに対応するチャット履歴をJSONファイルから読み込む"""
    if kb_name:
        history_file = os.path.join(CHAT_HISTORY_DIR, f"{kb_name}_history.json")
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    return []

# --- モデルのロード ---
llm, embeddings = get_models()

# --- プロンプトテンプレート ---
prompt = PromptTemplate(
    template="""あなたは誠実なアシスタントです。以下の「コンテキスト」情報だけを厳密に使って、ユーザーからの「質問」に日本語で回答してください。\n\n
    【重要ルール】\n- コンテキストに答えが明確に記述されていない場合、絶対に推測で回答せず、「提供された情報の中には、その質問に対する答えが見つかりませんでした。」とだけ回答してください。
    \n- 回答はコンテキスト内の情報源に完全に基づいている必要があります。\n\n
    【コンテキスト】\n{context}\n\n【質問】\n{input}\n\n【回答】""",
    input_variables=['context', 'input']
)

# --- サイドバーUI ---
with st.sidebar:
    st.title("ナレッジ管理")
    st.markdown("`knowledge_files` にフォルダを追加・削除後、下のボタンを押してください。")
    if st.button("ナレッジの同期", type="primary"):
        with st.spinner("ナレッジの状態を確認中..."):
            message = sync_knowledge_base()
            st.success(message)
    
    st.markdown("---")
    st.markdown(f"**使用中モデル:**\n`{LLM_MODEL}`")

# --- メイン画面UI ---
available_kbs = [d for d in os.listdir(VECTOR_STORE_DIR) if os.path.isdir(os.path.join(VECTOR_STORE_DIR, d))]
selected_kb = st.selectbox("検索対象のナレッジフォルダを選択", available_kbs, index=None, placeholder="ナレッジフォルダを選択してください")

# 選択されたナレッジベースが変更されたら、対応するチャット履歴を読み込む
if 'selected_kb' not in st.session_state or st.session_state.selected_kb != selected_kb:
    st.session_state.selected_kb = selected_kb
    st.session_state.chat_history = load_chat_history(selected_kb)
    st.rerun() # 画面を再読み込みしてチャット履歴を表示

# チャット履歴リセットボタン
if st.sidebar.button("チャット履歴をリセット"):
    if selected_kb:
        st.session_state.chat_history = []
        save_chat_history(selected_kb, []) # 保存ファイルも空にする
        st.rerun()

# --- チャット表示と処理 ---
if selected_kb:
    st.header(f"ナレッジフォルダ: `{selected_kb}`")
    
    # ハイブリッド検索のためのリトリーバー（検索部品）を準備
    source_folder_path = os.path.join(KNOWLEDGE_DIR, selected_kb)
    all_docs_for_bm25 = []
    if os.path.exists(source_folder_path):
        for filename in os.listdir(source_folder_path):
            file_path = os.path.join(source_folder_path, filename)
            all_docs_for_bm25.extend(load_document(file_path))

    if all_docs_for_bm25:
        # 1. キーワード検索 (BM25) の準備
        bm25_retriever = BM25Retriever.from_documents(all_docs_for_bm25)
        
        # 2. 意味検索 (Vector) の準備
        vector_store = Chroma(persist_directory=os.path.join(VECTOR_STORE_DIR, selected_kb), embedding_function=embeddings)
        vector_retriever = vector_store.as_retriever(search_kwargs={'k': 5})
        
        # 3. 2つの検索方法を組み合わせる
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[0.5, 0.5] # 検索の重み付け (50:50)
        )
        
        # RAGチェーンの作成
        rag_chain = create_retrieval_chain(ensemble_retriever, create_stuff_documents_chain(llm, prompt))

        # チャット履歴の表示
        for msg in st.session_state.get("chat_history", []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 新しい質問の受付と処理
        if question := st.chat_input(f"`{selected_kb}`のフォルダの内容について質問を入力"):
            # ユーザーの質問を履歴に追加して保存
            st.session_state.chat_history.append({"role": "user", "content": question})
            save_chat_history(selected_kb, st.session_state.chat_history)
            with st.chat_message("user"):
                st.markdown(question)

            # AIの回答を生成して表示
            with st.chat_message("assistant"):
                with st.spinner("AIが考えています..."):
                    
                    # 回答をストリーミング表示し、完了後に履歴を保存する関数
                    def stream_and_save():
                        full_answer = ""
                        context_docs = []
                        
                        # AIからの回答を断片的に受け取り、順次表示する
                        for chunk in rag_chain.stream({"input": question}):
                            if answer_piece := chunk.get("answer"):
                                full_answer += answer_piece
                                yield answer_piece
                            if context_chunk := chunk.get("context"):
                                context_docs = context_chunk
                        
                        # 免責事項を追加
                        disclaimer = "\n\n---\n*この回答はAIによって生成されました。内容の正確性を必ずご自身でご確認ください。*"
                        yield disclaimer
                        
                        # 完全な回答を履歴に保存
                        st.session_state.chat_history.append({"role": "assistant", "content": full_answer + disclaimer})
                        save_chat_history(selected_kb, st.session_state.chat_history)
                        
                        # 参照情報を表示
                        with st.expander("参照された可能性のある情報源"):
                            if not context_docs:
                                st.write("参照情報はありませんでした。")
                            for doc in context_docs:
                                st.info(f"**出典ファイル**: {doc.metadata.get('source', 'N/A')}\n\n{doc.page_content[:200]}...")
                    
                    # ストリーミング表示を実行
                    st.write_stream(stream_and_save)
    else:
        st.error("ナレッジフォルダ内に処理可能なドキュメントがありません。")

else:
    st.info("ナレッジフォルダを選択して、チャットを開始してください。")