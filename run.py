# run.py

import subprocess
import sys
import os

def main():
    """
    アプリケーションを安定して起動するためのメインスクリプト。
    """
    try:
        # このスクリプトがある場所を基準にプログラムを動かす
        # これにより、knowledge_filesなどの相対パスが正しく解決される
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # Streamlitを正しく起動するためのコマンドを構築
        # `python -m streamlit run ...` は、Pythonにパッケージの場所を教えるための標準的な方法
        command = [
            sys.executable,  # 現在の環境で使っているPythonの実行パスを取得
            "-m",
            "streamlit",
            "run",
            "app/main.py"
        ]

        # コマンドを実行
        print("アプリケーションを起動します...")
        subprocess.run(command, check=True)

    except FileNotFoundError:
        print("\nエラー: 'streamlit' コマンドが見つかりませんでした。")
        print("Streamlitが正しくインストールされているか確認してください。")
        print(f"（使用しようとしたPython: {sys.executable}）")
        input("\n何かキーを押して終了してください...")
    except Exception as e:
        print(f"\n起動中に予期せぬエラーが発生しました: {e}")
        input("\n何かキーを押して終了してください...")

if __name__ == "__main__":
    main()