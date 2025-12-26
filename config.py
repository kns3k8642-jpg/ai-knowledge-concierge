# ==============================================================================
# config.py - 設定・APIキー管理モジュール
# ==============================================================================
"""
このモジュールは、アプリケーション全体の設定とAPIキー管理を担当します。
Streamlitのst.secretsを使用したセキュアなAPIキー読み込みを提供します。
"""

from typing import Optional
import streamlit as st


# ==============================================================================
# 定数定義
# ==============================================================================

# 利用可能なGeminiモデル
AVAILABLE_MODELS: dict[str, str] = {
    "gemini-1.5-flash": "Gemini 1.5 Flash（高速・軽量）",
    "gemini-1.5-pro": "Gemini 1.5 Pro（高精度）",
}

# デフォルトモデル
DEFAULT_MODEL: str = "gemini-1.5-flash"

# ChromaDB設定
CHROMA_PERSIST_DIR: str = ".chroma"
COLLECTION_NAME: str = "knowledge_base"

# 埋め込みモデル（sentence-transformers）
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

# ベクトル検索のトップK件数
DEFAULT_TOP_K: int = 5

# チャンクサイズ（テキスト分割用）
CHUNK_SIZE: int = 500
CHUNK_OVERLAP: int = 50


# ==============================================================================
# APIキー管理関数（st.secrets対応）
# ==============================================================================

def get_api_key() -> Optional[str]:
    """
    st.secretsからGoogle APIキーを取得する。
    
    Returns:
        Optional[str]: APIキー。未設定の場合はNone。
    """
    try:
        # st.secretsから読み込み（.streamlit/secrets.toml または Streamlit Cloud設定）
        return st.secrets.get("GOOGLE_API_KEY", None)
    except Exception:
        # secrets.tomlが存在しない場合
        return None


def is_api_key_valid(api_key: Optional[str]) -> bool:
    """
    APIキーが有効かどうかを簡易チェックする。
    
    Args:
        api_key: チェック対象のAPIキー
        
    Returns:
        bool: 有効な形式であればTrue
    """
    if api_key is None:
        return False
    # 最低限の長さチェック（Gemini APIキーは通常39文字）
    return len(api_key.strip()) >= 30


def get_api_key_status() -> tuple[bool, str]:
    """
    APIキーの状態を取得する。
    
    Returns:
        tuple[bool, str]: (有効かどうか, ステータスメッセージ)
    """
    api_key = get_api_key()
    
    if api_key is None:
        return False, "?? APIキー未設定（.streamlit/secrets.toml またはサイドバーで設定してください）"
    
    if not is_api_key_valid(api_key):
        return False, "?? APIキーの形式が不正です"
    
    # マスク表示用（最初と最後の4文字のみ表示）
    masked_key = f"{api_key[:4]}...{api_key[-4:]}"
    return True, f"? APIキー設定済み: {masked_key}"
