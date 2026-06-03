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
    PLANNER_THINKING_BUDGET,
    DISTANCE_CATEGORIES,
    get_planner_max_tokens,
)
from .prompts.plan_prompts import PLANNER_SYSTEM_INSTRUCTION, build_plan_prompt

MAX_RETRIES = 2
RETRY_BASE_DELAY = 2


def calculate_plan_weeks(race_date_str: str, distance: str) -> tuple[int, str]:
    """レース日から計画週数と開始日を計算する（AMC方式）

    最短週数（min_weeks）だけを下限として固定し、レースまで十分な期間があれば
    「作成週の月曜日」から計画を始める。レースが最短週数より近い場合のみ、
    最短週数を確保するため過去（作成週より前）に遡って開始する。
    上限（default_weeks）による切り捨ては行わない。

    Returns:
        (total_weeks, start_date_str)
    """
    race_dt = datetime.strptime(race_date_str, "%Y-%m-%d")
    today = datetime.today()
    min_weeks = DISTANCE_CATEGORIES[distance]["min_weeks"]

    # 月曜日基準で計算（曜日による端数をなくす）
    race_week_monday = race_dt - timedelta(days=race_dt.weekday())
    today_monday = today - timedelta(days=today.weekday())

    # 作成週〜レース週を含む inclusive な週数
    span = max(0, (race_week_monday - today_monday).days // 7) + 1

    if span >= min_weeks:
        # 十分な期間がある → 作成週の月曜日から開始
        total_weeks = span
        start_dt = today_monday
    else:
        # レースが最短週数より近い → 最短週数を確保するため過去に遡る
        total_weeks = min_weeks
        start_dt = race_week_monday - timedelta(weeks=min_weeks - 1)

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


_DAY_MAP = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}


def _extract_weekday(date_field: str) -> Optional[str]:
    """AIが返すdate文字列から曜日文字（月〜日）を取り出す。

    AIはスキーマ（"date": "月"）を無視して "2026-06-15(月)" や "6/15(月)" の
    ような完全日付を返すことがある。日付計算はコード側の start_dt を正とするため、
    文字列に含まれる曜日文字だけを抽出して返す（見つからなければ None）。
    """
    for ch in date_field:
        if ch in _DAY_MAP:
            return ch
    return None


def _plan_json_to_markdown(plan_data: dict, start_date: str = "", practice_races: str = "") -> str:
    """JSONトレーニング計画をMarkdown文字列に変換する"""
    lines = []

    start_dt = None
    if start_date:
        try:
            clean = start_date.replace("年", "-").replace("月", "-").replace("日", "")
            start_dt = datetime.strptime(clean, "%Y-%m-%d")
        except ValueError:
            pass

    intro = plan_data.get("introduction", "")
    if intro:
        lines.append(intro)
        lines.append("")

    basic = plan_data.get("basic_info", {})
    if basic:
        lines.append("## 基本情報")
        if basic.get("nickname"):
            lines.append(f"- 選手名：{basic['nickname']}")
        if basic.get("age"):
            lines.append(f"- 年齢：{basic['age']}歳")
        if basic.get("gender"):
            lines.append(f"- 性別：{basic['gender']}")
        lines.append(f"- 目標距離：{basic.get('target_event', '')}")
        lines.append(f"- 現在のベスト：{basic.get('current_best', '')}")
        lines.append(f"- 目標タイム：{basic.get('target_time', '')}")
        if basic.get("race_date"):
            lines.append(f"- 目標レース日：{basic['race_date']}")
        lines.append(f"- 計画期間：{basic.get('total_weeks', '')}週間")
        if basic.get("training_days"):
            lines.append(f"- 週練習日数：{basic['training_days']}日")
        if basic.get("has_track"):
            lines.append(f"- トラック：{basic['has_track']}")
        if basic.get("has_gym"):
            lines.append(f"- ウェイトジム：{basic['has_gym']}")
        if basic.get("concerns"):
            lines.append(f"- 要望・注意事項：{basic['concerns']}")
        if basic.get("form_focus"):
            lines.append(f"- フォーム改善テーマ：{basic['form_focus']}")
        if practice_races:
            lines.append(f"- 練習レース・記録会：{practice_races}")
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
                day_raw = day.get("date", "")
                # AIがdate欄に何を入れても曜日文字を抽出し、start_dt から日付を再計算する。
                # これによりAIが計画の開始日をずらせなくなる（日付の正はコード側）。
                weekday = _extract_weekday(day_raw)
                if start_dt and weekday is not None:
                    target_dt = start_dt + timedelta(weeks=(week_num - 1), days=_DAY_MAP[weekday])
                    date_label = f"{target_dt.month}/{target_dt.day}({weekday})"
                else:
                    date_label = day_raw
                menu = day.get("menu", "")
                detail = day.get("detail", "")
                intensity = day.get("intensity", "")
                rest = day.get("rest", "")
                advice = day.get("advice", "")
                lines.append(f"| {date_label} | {menu} | {detail} | {intensity} | {rest} | {advice} |")

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
                    max_output_tokens=get_planner_max_tokens(total_weeks),
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=PLANNER_THINKING_BUDGET,
                    ),
                ),
            )
            plan_data = _parse_plan_json(response.text)
            markdown = _plan_json_to_markdown(plan_data, start_date, user_data.get("practice_races", ""))
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
