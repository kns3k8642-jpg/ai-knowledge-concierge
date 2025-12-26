# ==============================================================================
# app.py - AIナレッジ・コンシェルジュ メインアプリケーション
# ==============================================================================
"""
Streamlitベースのメインアプリケーション。
サイドバーでの設定管理と、メイン画面でのRAG Q&Aインターフェースを提供します。
"""

import streamlit as st
from config import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    get_api_key,
    get_api_key_status,
    is_api_key_valid,
)
from data_loader import (
    load_pdf,
    load_web,
    get_document_summary,
)
from vectorizer import (
    create_collection,
    get_collection_info,
    delete_collection,
    collection_exists,
)
from rag_engine import (
    generate_answer,
    test_api_connection,
)

# ==============================================================================
# ページ設定
# ==============================================================================
st.set_page_config(
    page_title="AIナレッジ・コンシェルジュ",
    page_icon="?",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# カスタムCSS
# ==============================================================================
st.markdown("""
<style>
/* メインコンテナのスタイル */
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 1rem;
}

/* サイドバーのセクションタイトル */
.sidebar-section {
    font-size: 1.1rem;
    font-weight: 600;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
    color: #4a5568;
}

/* ソースカード */
.source-card {
    background: #f7fafc;
    border-left: 4px solid #667eea;
    padding: 0.75rem;
    margin: 0.5rem 0;
    border-radius: 0 0.5rem 0.5rem 0;
}

/* スコアバッジ */
.score-badge {
    display: inline-block;
    background: #667eea;
    color: white;
    padding: 0.2rem 0.5rem;
    border-radius: 1rem;
    font-size: 0.75rem;
    margin-left: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# セッション状態の初期化
# ==============================================================================
def init_session_state() -> None:
    """セッション状態を初期化する。"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "documents_loaded" not in st.session_state:
        st.session_state.documents_loaded = False
    if "document_summary" not in st.session_state:
        st.session_state.document_summary = None
    if "manual_api_key" not in st.session_state:
        st.session_state.manual_api_key = ""

init_session_state()

# ==============================================================================
# サイドバー
# ==============================================================================
def render_sidebar() -> tuple[str, str]:
    """
    サイドバーをレンダリングする。
    Returns:
        tuple[str, str]: (有効なAPIキー, 選択されたモデル名)
    """
    with st.sidebar:
        st.markdown("## ?? 設定")
        
        # ----- APIキー管理 -----
        st.markdown('<p class="sidebar-section">? APIキー</p>', unsafe_allow_html=True)
        
        # 環境変数からのAPIキーチェック
        env_api_key = get_api_key()
        is_valid, status_msg = get_api_key_status()
        
        if is_valid:
            st.success(status_msg)
            active_api_key = env_api_key
        else:
            st.warning(status_msg)
            # 手動入力フォールバック
            manual_key = st.text_input(
                "APIキーを入力",
                type="password",
                value=st.session_state.manual_api_key,
                placeholder="AIzaSy...",
                help="Google AI StudioからAPIキーを取得してください",
            )
            if manual_key:
                st.session_state.manual_api_key = manual_key
            
            # 接続テスト
            if st.button("? 接続テスト", use_container_width=True):
                with st.spinner("テスト中..."):
                    success, msg = test_api_connection(manual_key)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
            active_api_key = manual_key if manual_key else ""

        st.divider()

        # ----- モデル選択 -----
        st.markdown('<p class="sidebar-section">? モデル選択</p>', unsafe_allow_html=True)
        selected_model = st.radio(
            "使用するモデル",
            options=list(AVAILABLE_MODELS.keys()),
            format_func=lambda x: AVAILABLE_MODELS[x],
            index=0,
            label_visibility="collapsed",
        )

        st.divider()

        # ----- ドキュメント管理 -----
        st.markdown('<p class="sidebar-section">? ソース管理</p>', unsafe_allow_html=True)
        
        # PDFアップロード
        uploaded_files = st.file_uploader(
            "PDFをアップロード",
            type=["pdf"],
            accept_multiple_files=True,
            help="複数のPDFファイルをアップロードできます",
        )
        
        # URL入力
        url_input = st.text_input(
            "WebサイトのURL",
            placeholder="https://example.com/article",
            help="Webページからテキストを抽出します",
        )

        # ロードボタン
        if st.button("? ドキュメントをロード", use_container_width=True, type="primary"):
            if not uploaded_files and not url_input:
                st.error("PDFまたはURLを入力してください")
            else:
                load_documents(uploaded_files, url_input)

        # 現在のドキュメント情報
        if st.session_state.documents_loaded:
            st.success("? ドキュメントロード済み")
            info = get_collection_info()
            if info:
                st.metric("チャンク数", info["count"])
            if st.session_state.document_summary:
                summary = st.session_state.document_summary
                st.caption(f"総文字数: {summary['total_chars']:,}文字")
        
        # クリアボタン
        if st.button("?? クリア", use_container_width=True):
            clear_documents()

        st.divider()

        # ----- ヘルプ -----
        with st.expander("?? 使い方"):
            st.markdown("""
            1. **APIキー設定**: `.env`ファイルまたはサイドバーで設定
            2. **ソース追加**: PDFアップロードまたはURL入力
            3. **質問**: メイン画面で質問を入力
            4. **回答確認**: 回答と根拠テキストを確認
            """)

    return active_api_key, selected_model

# ==============================================================================
# ドキュメント管理
# ==============================================================================
def load_documents(uploaded_files: list, url_input: str) -> None:
    """
    ドキュメントをロードしてベクトル化する。
    Args:
        uploaded_files: アップロードされたPDFファイルのリスト
        url_input: WebサイトのURL
    """
    all_chunks = []
    with st.spinner("ドキュメントを処理中..."):
        # PDFの処理
        for uploaded_file in uploaded_files:
            try:
                file_bytes = uploaded_file.read()
                chunks = load_pdf(file_bytes, uploaded_file.name)
                all_chunks.extend(chunks)
                st.sidebar.success(f"? {uploaded_file.name} を読み込みました")
            except Exception as e:
                st.sidebar.error(f"? {uploaded_file.name}: {str(e)}")
        
        # Webページの処理
        if url_input:
            try:
                chunks = load_web(url_input)
                all_chunks.extend(chunks)
                st.sidebar.success(f"? {url_input} を読み込みました")
            except Exception as e:
                st.sidebar.error(f"? URL読み込みエラー: {str(e)}")
        
        # ベクトル化
        if all_chunks:
            try:
                create_collection(all_chunks)
                st.session_state.documents_loaded = True
                st.session_state.document_summary = get_document_summary(all_chunks)
                st.sidebar.success(f"? {len(all_chunks)}チャンクをベクトル化しました")
            except Exception as e:
                st.sidebar.error(f"? ベクトル化エラー: {str(e)}")

def clear_documents() -> None:
    """ロード済みドキュメントをクリアする。"""
    delete_collection()
    st.session_state.documents_loaded = False
    st.session_state.document_summary = None
    st.session_state.messages = []
    st.rerun()

# ==============================================================================
# メイン画面
# ==============================================================================
def render_main(api_key: str, model_name: str) -> None:
    """
    メイン画面をレンダリングする。
    Args:
        api_key: 有効なAPIキー
        model_name: 選択されたモデル名
    """
    # ヘッダー
    st.markdown('<h1 class="main-header">? AIナレッジ・コンシェルジュ</h1>', unsafe_allow_html=True)
    st.markdown("**あなたの資料だけを情報源とする**、高精度なAIアシスタント")
    st.divider()

    # ドキュメントサマリー
    if st.session_state.documents_loaded and st.session_state.document_summary:
        summary = st.session_state.document_summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("? ソース数", len(summary["sources"]))
        with col2:
            st.metric("? チャンク数", summary["total_chunks"])
        with col3:
            st.metric("? 総文字数", f"{summary['total_chars']:,}")
        
        with st.expander("? ロード済みソース一覧"):
            for source in summary["sources"]:
                st.markdown(f"- {source}")
        st.divider()

    # チャット履歴の表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # アシスタントの回答には根拠表示
            if message["role"] == "assistant" and "sources" in message:
                render_sources(message["sources"])

    # チャット入力
    if not is_api_key_valid(api_key):
        st.warning("?? APIキーを設定してください（サイドバー参照）")
        return
    
    if not st.session_state.documents_loaded:
        st.info("? サイドバーからドキュメントをロードしてください")
        return

    if prompt := st.chat_input("質問を入力してください..."):
        # ユーザーメッセージを追加
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 回答生成
        with st.chat_message("assistant"):
            with st.spinner("回答を生成中..."):
                result = generate_answer(
                    query=prompt,
                    api_key=api_key,
                    model_name=model_name,
                )
                st.markdown(result["answer"])
                
                # 根拠テキストの表示
                if result["sources"]:
                    render_sources(result["sources"])
                
                # メッセージ履歴に追加
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result["sources"],
                })

def render_sources(sources: list[dict]) -> None:
    """
    参照した根拠テキストを表示する。
    Args:
        sources: ソース情報のリスト
    """
    if not sources:
        return
        
    with st.expander("? 根拠となったテキスト（Source Context）", expanded=False):
        for i, source in enumerate(sources, start=1):
            score = source.get("score", 0)
            score_color = "#22c55e" if score >= 0.7 else "#eab308" if score >= 0.5 else "#ef4444"
            st.markdown(f"""
            <div class="source-card">
                <strong>資料{i}</strong>
                <span style="background: {score_color}; color: white; padding: 0.2rem 0.5rem; border-radius: 1rem; font-size: 0.75rem; margin-left: 0.5rem;">
                    関連度: {score:.0%}
                </span>
                <br>
                <small style="color: #718096;">出典: {source.get("source", "不明")}</small>
                <p style="margin-top: 0.5rem; color: #2d3748;">{source.get("text", "")[:500]}...</p>
            </div>
            """, unsafe_allow_html=True)

# ==============================================================================
# エントリーポイント
# ==============================================================================
def main() -> None:
    """アプリケーションのエントリーポイント。"""
    api_key, model_name = render_sidebar()
    render_main(api_key, model_name)

if __name__ == "__main__":
    main()
