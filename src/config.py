"""
SDT（Sprint & Distance Trainer）- 設定定数
"""
from datetime import datetime
from zoneinfo import ZoneInfo


def jst_now() -> datetime:
    """日本時間の現在時刻（naive）。Streamlit Cloud（UTC）での日付ズレ防止用。"""
    return datetime.now(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)


APP_NAME = "SDT | Sprint & Distance Trainer"
APP_VERSION = "1.13.3"

# 診断スコアの5項目（キー: Geminiに出力させる英語キー、値: 表示ラベル）
SCORE_ITEMS = {
    "foot_strike": "接地",
    "pelvis_core": "骨盤・体幹",
    "arm_swing": "腕振り",
    "hip_extension": "股関節伸展",
    "vertical_osc": "上下動",
}

# Amazonおすすめリスト⑦（ランナーの補強・筋トレ）の送客先URL。
# 公開情報（シークレットではない）。リスト未確定時はストアトップにフォールバック。
AMAZON_FITNESS_LIST_URL = "https://amzn.to/4o3iHCx"

# カテゴリ別Amazonアイデアリスト（2026-07-15発行・トラッキングID akirun-rfd-22）。
# generalは網羅型のリスト⑦（AMAZON_FITNESS_LIST_URL）を継続。
AMAZON_LIST_GLUTE_CORE = "https://amzn.to/4fxnEAV"  # 臀筋・体幹
AMAZON_LIST_MOBILITY = "https://amzn.to/4aS5UgW"    # 可動域ケア・ストレッチ
AMAZON_LIST_ELASTICITY = "https://amzn.to/3RdloWg"  # 接地バネ・プライオ
AMAZON_LIST_UPPER_BODY = "https://amzn.to/4pmRxr3"  # 腕振り・上半身補強

# 弱点連動CTA：診断結果の弱点カテゴリごとにCTA文言・送客先を切り替える。
# URLはカテゴリ別リストへ送客（2026-07-15差し替え済）。generalのみ網羅型リスト⑦。
WEAKNESS_CTA_VARIANTS = {
    "glute_core": {
        "title": "💪 殿筋・体幹を、自宅で強化する",
        "sub": "診断で挙がった殿筋・体幹の補強種目に使える用品をAmazonのおすすめリストにまとめました。ミニバンドや体幹トレーニング用品で、骨盤の安定と股関節伸展の土台をつくれます。",
        "url": AMAZON_LIST_GLUTE_CORE,
    },
    "mobility": {
        "title": "🧘 硬さをほぐして、可動域を広げる",
        "sub": "診断で挙がった股関節・足首の硬さには、フォームローラーやストレッチ用品が役立ちます。可動域を広げるためのグッズをAmazonのおすすめリストにまとめました。",
        "url": AMAZON_LIST_MOBILITY,
    },
    "elasticity": {
        "title": "⚡ 接地のバネを、鍛え直す",
        "sub": "診断で挙がった接地のバネ・弾性の不足には、縄跳びやプライオメトリクス用品が効果的です。地面反力を活かすための用品をAmazonのおすすめリストにまとめました。",
        "url": AMAZON_LIST_ELASTICITY,
    },
    "upper_body": {
        "title": "🏋️ 腕振りと上半身を、整える",
        "sub": "診断で挙がった腕振り・上半身の課題には、トレーニングチューブなどが役立ちます。肩まわりと上下半身の連動性を高める用品をAmazonのおすすめリストにまとめました。",
        "url": AMAZON_LIST_UPPER_BODY,
    },
    "general": {
        "title": "💪 補強メニューを、自宅で実践する",
        "sub": "上の診断で挙がった補強種目に必要な用品を、用途別にAmazonのおすすめリストにまとめました。殿筋・体幹・足首の安定づくりと弾性の強化に役立つグッズを揃えています。",
        "url": AMAZON_FITNESS_LIST_URL,
    },
}

# =============================================
# Gemini モデル設定
# =============================================

# 動画スクリーニング（軽量・高速）
GEMINI_SCREENER_MODEL = "gemini-3.1-flash-lite"

# フォーム診断（深層推論）
GEMINI_ANALYZER_MODEL = "gemini-3.5-flash"

# 503フォールバック用の代替診断モデル（Gemini 3系・thinking_level対応を確認済み 2026-07-10）。
# プライマリがRETRY_503_MAX_ATTEMPTS回連続503のとき、このモデルでFALLBACK_503_MAX_ATTEMPTS回まで試行する。
# モデルはリクエスト単位で選ばれるため、次の診断は常にプライマリから始まる（RFDと同基準）
GEMINI_ANALYZER_FALLBACK_MODEL = "gemini-3-flash-preview"

# トレーニング計画生成（構造化出力）
GEMINI_PLANNER_MODEL = "gemini-3.5-flash"

# =============================================
# Gemini API パラメータ
# 注: temperature / top_p / top_k は全 Gemini 3.x モデルで非推奨となり削除（公式: デフォルト設定が最適化済み）
# thinking は thinking_level（minimal/low/medium/high）を使用。深い推論用途のため high を指定
# =============================================

SCREENER_MAX_TOKENS = 256

# 注: thinkingトークンも max_output_tokens を消費するため、診断本文の必要量に
# 思考分（thinking_level="high"）の余裕を上乗せした床値にする（RFDと同基準）
ANALYZER_MAX_TOKENS = 24576
ANALYZER_THINKING_LEVEL = "high"

PLANNER_MAX_TOKENS = 32768  # フォールバック上限（get_planner_max_tokens未使用パス向け）
PLANNER_THINKING_LEVEL = "high"

# 解析リクエストのタイムアウト（秒）。SDKデフォルトは無期限のためハング対策として明示（RFDと同基準）
ANALYZE_TIMEOUT_SEC = 300
# スクリーニングのタイムアウト（秒）
SCREEN_TIMEOUT_SEC = 60
# 503（モデル高負荷）時の自動リトライ：最大試行回数と待機秒
RETRY_503_MAX_ATTEMPTS = 3
RETRY_503_WAIT_SEC = 10
# プライマリが503で尽きた際のフォールバックモデルの最大試行回数
FALLBACK_503_MAX_ATTEMPTS = 2

# 計画生成リクエストのタイムアウト（秒）。SDKデフォルトは無期限のためハング対策として明示。
# 計画生成はフォーム診断より長時間かかるため余裕をみて10分とする
PLAN_TIMEOUT_SEC = 600
# プライマリが503で尽きた際のフォールバックモデル（GEMINI_ANALYZER_FALLBACK_MODELを流用）の最大試行回数
PLAN_FALLBACK_MAX_ATTEMPTS = 2
# プログレスバーの目安時間（秒）。この時間で95%に達し、完了まで頭打ち
ANALYZE_EXPECTED_SEC = 120


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
