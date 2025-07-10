# ローカルRAGアプリケーション

OllamaとStreamlitを使用してローカルPCで動作する、チャット形式のRAG（検索拡張生成）アプリケーションです。

## 特徴
- 完全オフラインで動作
- フォルダ単位でのナレッジ管理
- ハイブリッド検索（意味検索＋キーワード検索）による情報検索

## 必要なもの
- Python 3.10以上
- Ollama

## セットアップ手順
1. このリポジトリをクローンまたはダウンロードします。
2. 必要なPythonライブラリをインストールします。
   ```bash
   pip install -r requirements.txt
3. 使用するAIモデルをOllamaでダウンロードします。
   ollama pull llama3
4. config.jsonファイルを開き、使用するモデル名を指定します。

## 実行方法
 - macOS: start_app.command をダブルクリックします。
 - Windows: start_app.bat をダブルクリックします。

## ナレッジの追加方法
1. knowledge_files フォルダ内に、プロジェクトごとのフォルダを作成します。
2. 作成したフォルダ内に、情報源となるファイル（.pdf, .docx, .txt, .xlsx）を入れます。
3. アプリケーションを起動し、サイドバーの「ナレッジの同期」ボタンを押します。

## 動作画面
![image](https://github.com/user-attachments/assets/f0a3ed45-1072-4e33-9a87-2afc7f94d05b)

## 詳しくは
Notionに追加していきます。
<https://deluxe-vessel-b94.notion.site/RAG-22c2a9d5a2dd80ad9deffe958647ecfa>
