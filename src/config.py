"""
SDT（Sprint & Distance Trainer）- 設定定数
"""

APP_NAME = "SDT | Sprint & Distance Trainer"
APP_VERSION = "1.8.4"

# =============================================
# Gemini モデル設定
# =============================================

# 動画スクリーニング（軽量・高速）
GEMINI_SCREENER_MODEL = "gemini-3.1-flash-lite"

# フォーム診断（深層推論）
GEMINI_ANALYZER_MODEL = "gemini-3.5-flash"

# トレーニング計画生成（構造化出力）
GEMINI_PLANNER_MODEL = "gemini-3-flash-preview"

# =============================================
# Gemini API パラメータ
# =============================================

SCREENER_TEMPERATURE = 0.2
SCREENER_MAX_TOKENS = 256

ANALYZER_MAX_TOKENS = 16384
ANALYZER_THINKING_BUDGET = 16384

PLANNER_TEMPERATURE = 0.2
PLANNER_TOP_P = 0.95
PLANNER_MAX_TOKENS = 32768
PLANNER_THINKING_BUDGET = 8192

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
