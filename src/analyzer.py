"""
SDT - フォームアナライザー
動画のアップロード・ポーリング・Gemini Pro診断・クリーンアップを担当する。

使用パターン（app.py 側）:
    video_file = upload_video(client, video_bytes, filename)
    try:
        screen_result = screen_video(client, video_file)   # screener.py
        if screen_result["ok"]:
            result = analyze_form(client, video_file, context)
    finally:
        cleanup_video(client, video_file)
"""
import io
import time

from google import genai
from google.genai import types

from .config import (
    GEMINI_ANALYZER_MODEL,
    ANALYZER_MAX_TOKENS,
    ANALYZER_THINKING_LEVEL,
    VIDEO_POLL_INTERVAL,
    VIDEO_UPLOAD_TIMEOUT,
)
from .prompts.form_prompts import ANALYZER_SYSTEM_INSTRUCTION, build_analyzer_prompt

_MIME_MAP = {
    "mp4":  "video/mp4",
    "mov":  "video/quicktime",
    "avi":  "video/x-msvideo",
    "webm": "video/webm",
}


def _get_mime_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _MIME_MAP.get(ext, "video/mp4")


def upload_video(client: genai.Client, video_bytes: bytes, filename: str):
    """動画を Gemini Files API にアップロードし、処理完了まで待機する。

    Returns:
        処理完了した genai.File オブジェクト

    Raises:
        RuntimeError: アップロード失敗 / 処理タイムアウト / 処理エラー
    """
    mime_type = _get_mime_type(filename)

    try:
        video_file = client.files.upload(
            file=io.BytesIO(video_bytes),
            config=types.UploadFileConfig(
                mime_type=mime_type,
                display_name=filename,
            ),
        )
    except Exception as e:
        raise RuntimeError(f"動画のアップロードに失敗しました: {e}")

    elapsed = 0
    while video_file.state.name == "PROCESSING":
        if elapsed >= VIDEO_UPLOAD_TIMEOUT:
            raise RuntimeError(
                f"動画の処理がタイムアウトしました（{VIDEO_UPLOAD_TIMEOUT}秒）。"
                "短い動画か圧縮された動画をお試しください。"
            )
        time.sleep(VIDEO_POLL_INTERVAL)
        elapsed += VIDEO_POLL_INTERVAL
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError("動画の処理に失敗しました。別の動画ファイルをお試しください。")

    return video_file


def analyze_form(client: genai.Client, video_file, context: str) -> str:
    """gemini-3.5-flash でランニングフォームを診断する。

    Args:
        context: 距離・目標等のユーザーコンテキスト（空文字も可）

    Returns:
        マークダウン形式の診断テキスト
    """
    user_prompt = build_analyzer_prompt(context)

    try:
        response = client.models.generate_content(
            model=GEMINI_ANALYZER_MODEL,
            contents=[video_file, user_prompt],
            config=types.GenerateContentConfig(
                system_instruction=ANALYZER_SYSTEM_INSTRUCTION,
                max_output_tokens=ANALYZER_MAX_TOKENS,
                thinking_config=types.ThinkingConfig(
                    thinking_level=ANALYZER_THINKING_LEVEL,
                ),
            ),
        )

    except Exception as e:
        err = str(e)
        if "429" in err or "Resource Exhausted" in err:
            raise RuntimeError("429_RATE_LIMITED: APIのレート制限に達しました。しばらく待ってから再試行してください。")
        if "503" in err or "Service Unavailable" in err:
            raise RuntimeError("503_SERVICE_UNAVAILABLE: APIが一時的に利用できません。しばらく待ってから再試行してください。")
        raise RuntimeError(f"診断中にエラーが発生しました: {err}")

    # 空レスポンスガード：本文が無いまま返すと、結果非表示のまま診断枠だけ消費される
    text = response.text
    if not text or not text.strip():
        finish_reason = ""
        try:
            finish_reason = response.candidates[0].finish_reason.name
        except Exception:
            pass
        detail = f"（finish_reason: {finish_reason}）" if finish_reason else ""
        raise RuntimeError(
            f"AIが診断テキストを返しませんでした{detail}。"
            "診断回数は消費されていません。時間をおいて再試行してください。"
        )
    return text


def cleanup_video(client: genai.Client, video_file) -> None:
    """Files API からアップロードした動画を削除する。失敗しても例外を伝播させない。"""
    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass
