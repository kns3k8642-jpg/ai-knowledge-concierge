# ==============================================================================
# rag_engine.py - RAG（検索拡張生成）ロジックモジュール
# ==============================================================================
"""
このモジュールは、Gemini APIを使用した回答生成と、
ベクトルデータベースからの関連コンテキスト取得を担当します。
"""

import google.generativeai as genai
from vectorizer import query_collection
from config import AVAILABLE_MODELS, DEFAULT_MODEL, DEFAULT_TOP_K


# ==============================================================================
# 回答生成メイン関数
# ==============================================================================

def generate_answer(
    query: str,
    api_key: str,
    model_name: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K
) -> dict:
    """
    ユーザーの質問に対して、保存された知識から回答を生成する。
    
    Args:
        query: ユーザーの質問
        api_key: Gemini APIキー
        model_name: 使用するモデル名
        top_k: 検索する関連チャンク数
        
    Returns:
        dict: {"answer": 生成された回答, "sources": 参照したソース情報のリスト}
    """
    # 1. ベクトルデータベースから関連情報を検索
    relevant_chunks = query_collection(query, n_results=top_k)
    
    # 2. コンテキストの構築
    context_text = ""
    sources = []
    
    if relevant_chunks:
        context_parts = []
        for i, chunk in enumerate(relevant_chunks):
            context_parts.append(f"--- 資料 {i+1} ---\n{chunk['text']}")
            sources.append({
                "source": chunk.get("source", "不明なソース"),
                "text": chunk["text"],
                "score": chunk.get("score", 0.0)
            })
        context_text = "\n\n".join(context_parts)
    else:
        context_text = "関連する資料が見つかりませんでした。一般的な知識に基づいて回答するか、資料が不足している旨を伝えてください。"

    # 3. Gemini APIへのプロンプト構築
    prompt = f"""
あなたは誠実で優秀なAIアシスタント「AIナレッジ・コンシェルジュ」です。
提供された「参考資料」の内容のみに基づいて、ユーザーの質問に正確に答えてください。

【制約事項】
・資料に記載がない場合は「提供された資料にはその情報が含まれていません」とはっきり伝えてください。
・推測で答えないでください。
・回答は簡潔かつ丁寧な日本語で行ってください。
・専門用語は必要に応じて分かりやすく解説してください。

【参考資料】
{context_text}

【ユーザーの質問】
{query}

【回答】
"""

    # 4. モデルの実行
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        
        return {
            "answer": response.text,
            "sources": sources
        }
    except Exception as e:
        return {
            "answer": f"?? 回答生成中にエラーが発生しました: {str(e)}",
            "sources": sources
        }


# ==============================================================================
# API 接続・ユーティリティ
# ==============================================================================

def test_api_connection(api_key: str) -> tuple[bool, str]:
    """
    APIキーの有効性をテストする。
    
    Args:
        api_key: テストするAPIキー
        
    Returns:
        tuple[bool, str]: (成功したか, メッセージ)
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(DEFAULT_MODEL)
        # 低コストなリクエストでテスト
        model.generate_content("Hi", generation_config={"max_output_tokens": 5})
        return True, "?? 接続テスト成功: Gemini APIは有効です。"
    except Exception as e:
        return False, f"?? 接続テスト失敗: {str(e)}"
