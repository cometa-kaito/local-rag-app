# app/config.py

import json
from pathlib import Path

# プロジェクトルートにあるconfig.jsonへのパスを解決
CONFIG_FILE_PATH = Path(__file__).parent.parent / "config.json"

def load_config() -> dict:
    """
    設定ファイル(config.json)を読み込む。
    ファイルが存在しない、または内容が不正な場合は空の辞書を返す。
    """
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    return config

# アプリケーション全体で使う設定値をグローバル変数としてロード
config = load_config()

# config.jsonにキーが存在しない場合のバックアップ（デフォルト値）を指定
LLM_MODEL = config.get("llm_model", "llama3")
EMBEDDING_MODEL = config.get("embedding_model", "llama3")