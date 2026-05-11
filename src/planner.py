"""
SDT - トレーニング計画生成クライアント
Gemini API を使ってJSONトレーニング計画を生成し、Markdownに変換する。
"""
import json
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from google import genai
from google.genai import types

from .config import (
    GEMINI_PLANNER_MODEL,
    PLANNER_TEMPERATURE,
    PLANNER_TOP_P,
    PLANNER_MAX_TOKENS,
    PLANNER_THINKING_BUDGET,
    DISTANCE_CATEGORIES,
)
from .prompts.plan_prompts import PLANNER_SYSTEM_INSTRUCTION, build_plan_prompt

MAX_RETRIES = 2
RETRY_BASE_DELAY = 2


def calculate_plan_weeks(race_date_str: str, distance: str) -> tuple[int, str]:
    """レース日から計画週数と開始日を計算する

    Returns:
        (total_weeks, start_date_str)
    """
    race_dt = datetime.strptime(race_date_str, "%Y-%m-%d")
    today = datetime.today()
    min_weeks = DISTANCE_CATEGORIES[distance]["min_weeks"]
    default_weeks = DISTANCE_CATEGORIES[distance]["default_weeks"]

    actual_weeks = max(0, (race_dt - today).days // 7)

    if actual_weeks < min_weeks:
        total_weeks = min_weeks
        start_dt = race_dt - timedelta(weeks=min_weeks)
    elif actual_weeks > default_weeks:
        total_weeks = default_weeks
        start_dt = race_dt - timedelta(weeks=default_weeks)
    else:
        total_weeks = actual_weeks
        start_dt = today

    # 直近の月曜日に合わせる
    start_dt = start_dt - timedelta(days=start_dt.weekday())
    return total_weeks, start_dt.strftime("%Y年%m月%d日")


def _repair_json(json_str: str) -> str:
    """Geminiが返す不正なJSONを修復する（AMCのロジックを踏襲）"""
    repaired = re.sub(
        r'("date"\s*:\s*"[^"]*")\s*,\s*"([^"]*?)"\s*,\s*"detail"',
        r'\1, "menu": "\2", "detail"',
        json_str,
    )
    return repaired


def _parse_plan_json(raw: str) -> dict:
    """APIレスポンスからJSONを抽出してパースする"""
    text = raw.strip()

    # コードブロック除去
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = _repair_json(text)
        return json.loads(repaired)


def _plan_json_to_markdown(plan_data: dict) -> str:
    """JSONトレーニング計画をMarkdown文字列に変換する"""
    lines = []

    intro = plan_data.get("introduction", "")
    if intro:
        lines.append(intro)
        lines.append("")

    basic = plan_data.get("basic_info", {})
    if basic:
        lines.append("## 基本情報")
        lines.append(f"- 目標距離：{basic.get('target_event', '')}")
        lines.append(f"- 現在のベスト：{basic.get('current_best', '')}")
        lines.append(f"- 目標タイム：{basic.get('target_time', '')}")
        lines.append(f"- 計画期間：{basic.get('total_weeks', '')}週間")
        if basic.get("form_focus"):
            lines.append(f"- フォーム改善テーマ：{basic['form_focus']}")
        lines.append("")

    phase_overview = plan_data.get("phase_overview", "")
    if phase_overview:
        lines.append("## フェーズ構成")
        lines.append(phase_overview)
        lines.append("")

    weekly_schedules = plan_data.get("weekly_schedules", [])
    for week_data in weekly_schedules:
        week_num = week_data.get("week", "")
        phase = week_data.get("phase", "")
        lines.append(f"## 第{week_num}週　{phase}")

        days = week_data.get("days", [])
        if days:
            lines.append("| 曜日 | 練習内容 | 詳細 | 強度 | 休憩 | ポイント |")
            lines.append("|------|---------|------|------|------|---------|")
            for day in days:
                date = day.get("date", "")
                menu = day.get("menu", "")
                detail = day.get("detail", "")
                intensity = day.get("intensity", "")
                rest = day.get("rest", "")
                advice = day.get("advice", "")
                lines.append(f"| {date} | {menu} | {detail} | {intensity} | {rest} | {advice} |")

        summary = week_data.get("weekly_summary", "")
        if summary:
            lines.append(f"\n{summary}")
        lines.append("")

    precautions = plan_data.get("precautions", [])
    if precautions:
        lines.append("## 注意事項")
        for p in precautions:
            lines.append(f"- {p}")
        lines.append("")

    coach_message = plan_data.get("coach_message", "")
    if coach_message:
        lines.append("## コーチより")
        lines.append(coach_message)

    return "\n".join(lines)


def generate_plan(
    api_key: str,
    user_data: dict,
    form_diagnosis: Optional[str],
    total_weeks: int,
    start_date: str,
    result_container: list,
    error_container: list,
) -> None:
    """トレーニング計画を生成してresult_containerに格納する（スレッド実行用）

    Args:
        result_container: 成功時に [markdown_text] を格納するリスト
        error_container:  失敗時に [error_message] を格納するリスト
    """
    client = genai.Client(api_key=api_key)
    prompt = build_plan_prompt(user_data, form_diagnosis, total_weeks, start_date)

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_PLANNER_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=PLANNER_SYSTEM_INSTRUCTION,
                    temperature=PLANNER_TEMPERATURE,
                    top_p=PLANNER_TOP_P,
                    max_output_tokens=PLANNER_MAX_TOKENS,
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=PLANNER_THINKING_BUDGET,
                    ),
                ),
            )
            plan_data = _parse_plan_json(response.text)
            markdown = _plan_json_to_markdown(plan_data)
            result_container.append(markdown)
            return

        except Exception as e:
            err = str(e)
            last_error = err
            if "503" in err or "Service Unavailable" in err:
                last_error = "503_SERVICE_UNAVAILABLE"
            elif "429" in err or "Resource Exhausted" in err:
                last_error = "429_RATE_LIMITED"

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt))

    error_container.append(last_error or "UNKNOWN_ERROR")
