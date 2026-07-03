"""
SDT - 動画スクリーニング
gemini-flash-lite で動画の品質チェックを行う。
アップロード済みの Files API ファイルオブジェクトを受け取り、診断可否を返す。
"""
import json

from google import genai
from google.genai import types

from .config import GEMINI_SCREENER_MODEL, SCREENER_MAX_TOKENS
from .prompts.form_prompts import SCREENER_SYSTEM_INSTRUCTION, SCREENER_USER_PROMPT


def screen_video(client: genai.Client, video_file) -> dict:
    """動画が診断に使用できるか高速チェックする

    Returns:
        {"ok": bool, "reason": str}
    """
    try:
        response = client.models.generate_content(
            model=GEMINI_SCREENER_MODEL,
            contents=[video_file, SCREENER_USER_PROMPT],
            config=types.GenerateContentConfig(
                system_instruction=SCREENER_SYSTEM_INSTRUCTION,
                max_output_tokens=SCREENER_MAX_TOKENS,
            ),
        )

        # 本文Noneでも fail-open（json.JSONDecodeError → 診断に進む）に落とす
        raw = (response.text or "").strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)

        if "ok" not in result:
            return {"ok": False, "reason": "スクリーニング結果の形式が不正でした。"}

        return {"ok": bool(result["ok"]), "reason": result.get("reason", "")}

    except json.JSONDecodeError:
        return {"ok": True, "reason": "スクリーニングをスキップして診断に進みます。"}

    except Exception as e:
        err = str(e)
        if "429" in err or "Resource Exhausted" in err:
            raise RuntimeError("429_RATE_LIMITED: APIのレート制限に達しました。しばらく待ってから再試行してください。")
        raise RuntimeError(f"スクリーニング中にエラーが発生しました: {err}")
