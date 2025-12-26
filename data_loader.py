# ==============================================================================
# data_loader.py - データ読み込みモジュール
# ==============================================================================
"""
このモジュールは、PDF・Webサイトからのテキスト抽出を担当します。
各関数は型ヒント付きで、独立してテスト可能な設計です。
"""

import re
from typing import Optional
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup

from config import CHUNK_SIZE, CHUNK_OVERLAP


# ==============================================================================
# PDF処理
# ==============================================================================

def load_pdf(file_bytes: bytes, filename: str = "uploaded.pdf") -> list[dict[str, str]]:
    """
    PDFファイルからテキストを抽出し、ページ単位のチャンクリストを返す。
    
    Args:
        file_bytes: PDFファイルのバイトデータ
        filename: ファイル名（ソース情報として使用）
        
    Returns:
        list[dict]: 各チャンクの辞書リスト
                   {"text": 抽出テキスト, "source": ソース情報, "page": ページ番号}
    """
    chunks: list[dict[str, str]] = []
    
    try:
        # PyMuPDFでPDFを開く（バイトデータから）
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            
            # 空白ページはスキップ
            if not text.strip():
                continue
            
            # テキストをチャンクに分割
            page_chunks = split_text_into_chunks(text)
            
            for chunk in page_chunks:
                chunks.append({
                    "text": chunk,
                    "source": f"{filename} - ページ {page_num}",
                    "page": str(page_num),
                })
        
        doc.close()
        
    except Exception as e:
        raise ValueError(f"PDF読み込みエラー: {str(e)}")
    
    return chunks


# ==============================================================================
# Web スクレイピング
# ==============================================================================

def load_web(url: str, timeout: int = 10) -> list[dict[str, str]]:
    """
    WebページからテキストをスクレイピングしてチャンクリストReturns:を返す。
    
    Args:
        url: 対象のURL
        timeout: リクエストタイムアウト秒数
        
    Returns:
        list[dict]: 各チャンクの辞書リスト
                   {"text": 抽出テキスト, "source": URL}
    """
    chunks: list[dict[str, str]] = []
    
    try:
        # HTTPリクエスト（User-Agentを設定してブロック回避）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        # BeautifulSoupで解析
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 不要なタグを除去（script, style, nav, footer等）
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        
        # 本文テキストを抽出
        # 優先度: article > main > body
        main_content = soup.find("article") or soup.find("main") or soup.find("body")
        
        if main_content:
            text = main_content.get_text(separator="
", strip=True)
        else:
            text = soup.get_text(separator="
", strip=True)
        
        # テキストをクリーンアップ
        text = clean_text(text)
        
        # チャンクに分割
        text_chunks = split_text_into_chunks(text)
        
        for chunk in text_chunks:
            chunks.append({
                "text": chunk,
                "source": url,
            })
            
    except requests.RequestException as e:
        raise ValueError(f"Web読み込みエラー: {str(e)}")
    
    return chunks


# ==============================================================================
# テキスト処理ユーティリティ
# ==============================================================================

def split_text_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """
    テキストを指定サイズのチャンクに分割する。
    文の途中で切れないよう、句読点で区切る。
    
    Args:
        text: 分割対象のテキスト
        chunk_size: 1チャンクの最大文字数
        overlap: チャンク間のオーバーラップ文字数
        
    Returns:
        list[str]: 分割されたチャンク의 리스트
    """
    if not text.strip():
        return []
    
    # 句読点または改行で文を分割
    sentences = re.split(r'(?<=[。．！？
])', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence)
        
        # チャンクサイズを超える場合は現在のチャンクを確定
        if current_length + sentence_length > chunk_size and current_chunk:
            chunks.append("".join(current_chunk))
            
            # オーバーラップを考慮して次のチャンクを開始
            overlap_text = "".join(current_chunk)[-overlap:] if overlap > 0 else ""
            current_chunk = [overlap_text] if overlap_text else []
            current_length = len(overlap_text)
        
        current_chunk.append(sentence)
        current_length += sentence_length
    
    # 残りのテキストを追加
    if current_chunk:
        chunks.append("".join(current_chunk))
    
    return chunks


def clean_text(text: str) -> str:
    """
    テキストから不要な空白や特殊文字を除去する。
    
    Args:
        text: クリーンアップ対象のテキスト
        
    Returns:
        str: クリーンアップ済みテキスト
    """
    # 連続する空白を1つに
    text = re.sub(r's+', ' ', text)
    # 連続する改行を1つに
    text = re.sub(r'
+', '
', text)
    # 前後の空白を除去
    text = text.strip()
    
    return text


def get_document_summary(chunks: list[dict[str, str]]) -> dict[str, any]:
    """
    ドキュメントのサマリー情報を生成する。
    
    Args:
        chunks: チャンクのリスト
        
    Returns:
        dict: サマリー情報
              {"total_chunks": チャンク数, "total_chars": 総文字数, "sources": ソース一覧}
    """
    sources = set()
    total_chars = 0
    
    for chunk in chunks:
        sources.add(chunk.get("source", "不明"))
        total_chars += len(chunk.get("text", ""))
    
    return {
        "total_chunks": len(chunks),
        "total_chars": total_chars,
        "sources": list(sources),
    }
