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
import json
import re
import time

from google import genai
from google.genai import types

from .config import (
    GEMINI_ANALYZER_MODEL,
    ANALYZER_MAX_TOKENS,
    ANALYZER_THINKING_LEVEL,
    VIDEO_POLL_INTERVAL,
    VIDEO_UPLOAD_TIMEOUT,
    SCORE_ITEMS,
    WEAKNESS_CTA_VARIANTS,
)
from .prompts.form_prompts import ANALYZER_SYSTEM_INSTRUCTION, build_analyzer_prompt

# 弱点連動CTA：診断テキスト末尾のWEAKNESS_TAG行が取りうる値（config.pyの辞書キーと同一に保つ）
VALID_WEAKNESS_TAGS = set(WEAKNESS_CTA_VARIANTS.keys())

_WEAKNESS_TAG_RE = re.compile(r"^\s*WEAKNESS_TAG:\s*([a-zA-Z_]+)\s*$", re.MULTILINE | re.IGNORECASE)

# スコア化：診断テキスト中のSCORES_JSON行（config.pyのSCORE_ITEMSキーと同一に保つ）
_SCORES_JSON_RE = re.compile(r"^\s*SCORES_JSON:\s*(\{.*?\})\s*$", re.MULTILINE | re.IGNORECASE)

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


def extract_weakness_tag(text: str) -> tuple[str, str]:
    """診断テキスト末尾のWEAKNESS_TAG行を抽出し、本文から除去する。

    Args:
        text: analyze_form() が返す診断テキスト全文

    Returns:
        (タグ行を除去した本文, 弱点カテゴリ文字列)
        タグが見つからない、または不正なカテゴリの場合はカテゴリを "general" とする。
    """
    # 末尾側の行を優先するため、複数マッチがあれば最後のものを採用する
    matches = list(_WEAKNESS_TAG_RE.finditer(text))
    if not matches:
        return text, "general"
    match = matches[-1]

    tag = match.group(1).strip().lower()
    if tag not in VALID_WEAKNESS_TAGS:
        tag = "general"

    body = text[:match.start()] + text[match.end():]
    return body.rstrip(), tag


def extract_scores_json(text: str) -> tuple[str, dict | None]:
    """診断テキスト中のSCORES_JSON行を抽出し、本文から除去する。

    Args:
        text: analyze_form() が返す診断テキスト全文（またはextract_weakness_tag適用後の本文）

    Returns:
        (SCORES_JSON行を除去した本文, {SCORE_ITEMSキー: 1〜10の整数} または None)
        行が無い、JSONとして壊れている、必須キーの欠落・非数値がある場合は None。
        行らしきものが見つかった場合は、パース失敗時も本文からは除去する。
    """
    matches = list(_SCORES_JSON_RE.finditer(text))
    if not matches:
        return text, None
    match = matches[-1]

    body = (text[:match.start()] + text[match.end():]).rstrip()

    try:
        data = json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        return body, None

    if not isinstance(data, dict):
        return body, None

    scores: dict[str, int] = {}
    for key in SCORE_ITEMS:
        value = data.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return body, None
        scores[key] = max(1, min(10, round(value)))

    return body, scores


def cleanup_video(client: genai.Client, video_file) -> None:
    """Files API からアップロードした動画を削除する。失敗しても例外を伝播させない。"""
    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass
