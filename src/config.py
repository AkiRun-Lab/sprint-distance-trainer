"""
SDT（Sprint & Distance Trainer）- 設定定数
"""
from datetime import datetime
from zoneinfo import ZoneInfo


def jst_now() -> datetime:
    """日本時間の現在時刻（naive）。Streamlit Cloud（UTC）での日付ズレ防止用。"""
    return datetime.now(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)


APP_NAME = "SDT | Sprint & Distance Trainer"
APP_VERSION = "1.10.2"

# Amazonおすすめリスト⑦（ランナーの補強・筋トレ）の送客先URL。
# 公開情報（シークレットではない）。リスト未確定時はストアトップにフォールバック。
AMAZON_FITNESS_LIST_URL = "https://amzn.to/4o3iHCx"

# =============================================
# Gemini モデル設定
# =============================================

# 動画スクリーニング（軽量・高速）
GEMINI_SCREENER_MODEL = "gemini-3.1-flash-lite"

# フォーム診断（深層推論）
GEMINI_ANALYZER_MODEL = "gemini-3.5-flash"

# トレーニング計画生成（構造化出力）
GEMINI_PLANNER_MODEL = "gemini-3.5-flash"

# =============================================
# Gemini API パラメータ
# 注: temperature / top_p / top_k は全 Gemini 3.x モデルで非推奨となり削除（公式: デフォルト設定が最適化済み）
# thinking は thinking_level（minimal/low/medium/high）を使用。深い推論用途のため high を指定
# =============================================

SCREENER_MAX_TOKENS = 256

ANALYZER_MAX_TOKENS = 16384
ANALYZER_THINKING_LEVEL = "high"

PLANNER_MAX_TOKENS = 32768  # フォールバック上限（get_planner_max_tokens未使用パス向け）
PLANNER_THINKING_LEVEL = "high"


def get_planner_max_tokens(total_weeks: int) -> int:
    """計画週数に応じた出力トークン上限を返す（AMC方式）。

    calculate_plan_weeks の上限撤廃により週数が大きくなり得るため、
    固定値だと遠いレースで JSON が途中で切れる。週数に比例させて確保する。
    SDTの週表は6列（曜日・内容・詳細・強度・休憩・ポイント）と密なため
    AMC（1200/週）よりやや多めの 1500/週 とし、モデル上限内に収める。
    """
    tokens = total_weeks * 1500 + 4096
    return max(PLANNER_MAX_TOKENS, min(tokens, 65536))

# =============================================
# 動画アップロード設定
# =============================================

SUPPORTED_VIDEO_TYPES = ["mp4", "mov", "avi", "webm"]
VIDEO_POLL_INTERVAL = 2      # ポーリング間隔（秒）
VIDEO_UPLOAD_TIMEOUT = 120   # タイムアウト（秒）
MAX_DIAGNOSES_PER_SESSION = 1

# =============================================
# 距離カテゴリ定義
# =============================================

DISTANCE_CATEGORIES = {
    "100m": {
        "label": "100m",
        "energy_system": "ATP-PC系（無酸素・神経系）",
        "phase_structure": "GPP → SPP → 競技期",
        "time_format": "秒（例：12.5）",
        "time_unit": "秒",
        "min_weeks": 8,
        "default_weeks": 12,
    },
    "200m": {
        "label": "200m",
        "energy_system": "ATP-PC系＋グリコーゲン分解系",
        "phase_structure": "GPP → SPP → 競技期",
        "time_format": "秒（例：25.0）",
        "time_unit": "秒",
        "min_weeks": 8,
        "default_weeks": 12,
    },
    "400m": {
        "label": "400m",
        "energy_system": "グリコーゲン分解系（無酸素系主体）",
        "phase_structure": "GPP → SPP → 競技期",
        "time_format": "秒（例：55.0）",
        "time_unit": "秒",
        "min_weeks": 10,
        "default_weeks": 16,
    },
    "800m": {
        "label": "800m",
        "energy_system": "有酸素系＋無酸素系（混合）",
        "phase_structure": "有酸素基盤 → スピード持久力 → 競技期",
        "time_format": "分:秒.0（例：2:10.5）",
        "time_unit": "分秒",
        "min_weeks": 10,
        "default_weeks": 16,
    },
    "1500m": {
        "label": "1500m",
        "energy_system": "有酸素系主体＋無酸素系補完",
        "phase_structure": "有酸素基盤 → スピード持久力 → 競技期",
        "time_format": "分:秒.0（例：4:30.5）",
        "time_unit": "分秒",
        "min_weeks": 12,
        "default_weeks": 16,
    },
}

DISTANCE_OPTIONS = list(DISTANCE_CATEGORIES.keys())

# =============================================
# セッション制限
# =============================================

MAX_PLAN_GENERATIONS_PER_SESSION = 1
