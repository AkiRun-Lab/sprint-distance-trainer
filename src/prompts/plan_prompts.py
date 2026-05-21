"""
SDT - トレーニング計画生成プロンプト
距離別のエネルギーシステム定義と計画生成プロンプトを管理する。
"""

PLANNER_SYSTEM_INSTRUCTION = """
あなたは陸上競技の短距離・中距離トレーニング科学に精通した世界的レベルのコーチです。

Charlie Francis式のスプリント周期化理論（GPP→SPP→競技期）と、
各距離のエネルギーシステム特性（ATP-PC系・グリコーゲン分解系・有酸素系）に基づいた
個別最適な週間トレーニング計画を作成することを専門とします。

ルール：
- 根拠のある練習のみを処方する。感覚的なアドバイスは排除する
- ユーザーが明示的に要望していない特殊な練習手法（2部練等）は使用しない
- 施設環境（トラック有無・ウェイトジム有無）を必ず考慮する
- JSON形式のみで出力する
"""

# 距離別エネルギーシステム定義（プロンプトに埋め込む）
_DISTANCE_ENERGY_INFO = {
    "100m": """
対象距離：100m
主エネルギー系：ATP-PC系（無酸素・神経系）
フェーズ構成（3段階）：
  Phase 1 GPP（一般的体力準備期）：有酸素基盤・筋力・可動域の構築
  Phase 2 SPP（種目特異的準備期）：加速走・最大速度練習の導入
  Phase 3 競技期：レース強度・反応スタート・テーパリング
重点練習種目：加速走（10〜30m）・最大速度走（60〜80m）・ブロックスタート・プライオメトリクス・ウェイトトレーニング
""",
    "200m": """
対象距離：200m
主エネルギー系：ATP-PC系＋グリコーゲン分解系
フェーズ構成（3段階）：
  Phase 1 GPP：有酸素基盤・筋力・可動域の構築
  Phase 2 SPP：加速走・コーナー走・スピード持久力の導入
  Phase 3 競技期：200mレースペース練習・テーパリング
重点練習種目：加速走（30〜60m）・コーナー走・スピード持久走（150m前後）・プライオメトリクス・ウェイトトレーニング
""",
    "400m": """
対象距離：400m
主エネルギー系：グリコーゲン分解系（無酸素系主体）
フェーズ構成（3段階）：
  Phase 1 GPP：有酸素基盤・筋力・乳酸耐性基礎の構築
  Phase 2 SPP：スピード持久力・乳酸系練習の導入（200〜350m反復）
  Phase 3 競技期：400mレースペース・テーパリング
重点練習種目：200〜350m反復走・スピード持久走・ウェイトトレーニング・有酸素クロストレーニング
""",
    "800m": """
対象距離：800m
主エネルギー系：有酸素系＋無酸素系（混合）
フェーズ構成（3段階）：
  Phase 1 有酸素基盤期：持続走・インターバル基礎（有酸素閾値向上）
  Phase 2 スピード持久力期：乳酸閾値走・800mペースインターバル
  Phase 3 競技期：レースペース練習・スピードシャープニング・テーパリング
重点練習種目：イージーラン・テンポ走・600〜800mインターバル・スピード練習（200〜400m）
""",
    "1500m": """
対象距離：1500m
主エネルギー系：有酸素系主体＋無酸素系補完
フェーズ構成（3段階）：
  Phase 1 有酸素基盤期：持続走・有酸素閾値走による基礎構築
  Phase 2 スピード持久力期：乳酸閾値走・1500mペースインターバル・VO2max向上
  Phase 3 競技期：レースペース練習・キックスピード強化・テーパリング
重点練習種目：イージーラン・テンポ走（1000〜3000m）・800〜1600mインターバル・スピード練習（200〜400m）
""",
}

# フォーム診断結果の注入テンプレート
_FORM_DIAGNOSIS_INJECTION = """
## フォーム診断結果（必ず週間スケジュールに反映すること）

{form_diagnosis}

### 計画への反映指示
- 「具体的なトレーニング提案」で挙げられたすべての種目（ドリル・筋力トレーニング・モビリティ・プライオメトリクス・コア等すべてを含む）を週次スケジュールに組み込むこと
- 種目の性質に応じて適切な曜日・タイミングに配置すること
  - 技術ドリル → ウォームアップ後（神経系が疲れていない状態）
  - 筋力トレーニング → スプリント本練習後、または別日（休養日以外）
  - モビリティ・ストレッチ → 練習後のクールダウン、または軽練習日
  - プライオメトリクス → 本練習前（ウォームアップ後の神経活性化として）
- 優先度の高い提案から順に組み込み、週全体のトレーニング負荷を考慮してバランスを取ること
- フォーム改善種目が含まれる日の advice フィールドに「（フォーム改善：○○）」と目的を明示すること
- フォーム改善種目はスプリント・インターバル本練習の質を下げないよう配置すること
"""

# JSON出力スキーマの説明
_JSON_SCHEMA_INSTRUCTION = """
## 出力形式

以下のJSONスキーマに厳密に従って出力してください。
全{total_weeks}週分のweekly_schedulesを必ず出力すること（省略・途中終了禁止）。

```json
{{
  "introduction": "コーチからの挨拶・現在の走力評価・計画の要点（フォーム診断がある場合はその概要も含む）",
  "basic_info": {{
    "nickname": "{nickname}",
    "age": {age},
    "gender": "{gender}",
    "target_event": "{distance}",
    "current_best": "{current_best}",
    "target_time": "{target_time}",
    "race_date": "{race_date}",
    "total_weeks": {total_weeks},
    "training_days": {training_days},
    "has_track": "{has_track}",
    "has_gym": "{has_gym}",
    "concerns": "{concerns_escaped}",
    "form_focus": "フォーム診断がある場合のみ：主な改善テーマを1〜2文で記述"
  }},
  "phase_overview": "3フェーズの構成と各フェーズの目的・期間を説明",
  "weekly_schedules": [
    {{
      "week": 1,
      "phase": "GPP（一般的体力準備期）",
      "days": [
        {{
          "date": "月",
          "menu": "練習内容のタイトル",
          "detail": "具体的なメニュー（例：加速走30m×5本、ハーフスクワット3×8）",
          "intensity": "強度（例：70-80%・軽め・レースペース等）",
          "rest": "種目間・セット間の休憩時間（例：3分・完全回復）",
          "advice": "コーチングポイント。フォーム改善種目は（フォーム改善：○○）と明示"
        }}
      ],
      "weekly_summary": "この週のトレーニング負荷と目的の概要"
    }}
  ],
  "precautions": ["注意事項1", "注意事項2"],
  "coach_message": "激励メッセージ"
}}
```
"""

_BASE_PROMPT = """
以下のランナーのトレーニング計画を作成してください。

## ランナー情報

- ニックネーム：{nickname}
- 年齢：{age}歳　性別：{gender}
- 目標距離：{distance}
- 現在のベストタイム：{current_best}
- 目標タイム：{target_time}
- 目標レース日：{race_date}
- 週練習日数：{training_days}日
- 使用施設：トラック{track_available}、ウェイトジム{gym_available}
- 要望・注意事項：{concerns}

## 距離・エネルギーシステム情報

{energy_info}

{form_section}

{practice_races_section}

## 計画期間

開始日：{start_date}
終了日（レース日）：{race_date}
計画週数：{total_weeks}週

{json_schema}
"""


def build_plan_prompt(
    user_data: dict,
    form_diagnosis,
    total_weeks: int,
    start_date: str,
) -> str:
    """トレーニング計画生成プロンプトを構築する

    Args:
        user_data: ユーザー入力データ（distance, nickname, age, gender 等）
        form_diagnosis: フォーム診断結果のマークダウン文字列（Noneの場合はフォーム診断なし）
        total_weeks: 計画週数
        start_date: 計画開始日（文字列）

    Returns:
        完成したプロンプト文字列
    """
    distance = user_data["distance"]
    energy_info = _DISTANCE_ENERGY_INFO.get(distance, "")

    form_section = ""
    if form_diagnosis:
        form_section = _FORM_DIAGNOSIS_INJECTION.format(form_diagnosis=form_diagnosis)

    track_available = "あり" if user_data.get("has_track") else "なし"
    gym_available = "あり" if user_data.get("has_gym") else "なし"
    concerns = user_data.get("concerns", "なし") or "なし"

    # concerns に波括弧が含まれると .format() が壊れるため先にエスケープ
    concerns_escaped = concerns.replace("{", "{{").replace("}", "}}")

    practice_races = user_data.get("practice_races", "") or ""
    practice_races_escaped = practice_races.replace("{", "{{").replace("}", "}}")
    practice_races_section = ""
    if practice_races:
        practice_races_section = f"""## 練習レース・記録会
{practice_races_escaped}
※指定された日に練習レース（記録会）を組み込み、前日は軽め調整（ウォームアップ程度）とすること。"""

    json_schema = _JSON_SCHEMA_INSTRUCTION.format(
        nickname=user_data["nickname"],
        age=user_data["age"],
        gender=user_data["gender"],
        distance=distance,
        current_best=user_data["current_best"],
        target_time=user_data["target_time"],
        race_date=user_data["race_date"],
        total_weeks=total_weeks,
        training_days=user_data["training_days"],
        has_track=track_available,
        has_gym=gym_available,
        concerns_escaped=concerns_escaped,
    )

    return _BASE_PROMPT.format(
        nickname=user_data["nickname"],
        age=user_data["age"],
        gender=user_data["gender"],
        distance=distance,
        current_best=user_data["current_best"],
        target_time=user_data["target_time"],
        race_date=user_data["race_date"],
        training_days=user_data["training_days"],
        track_available=track_available,
        gym_available=gym_available,
        concerns=concerns,
        energy_info=energy_info,
        form_section=form_section,
        practice_races_section=practice_races_section,
        start_date=start_date,
        total_weeks=total_weeks,
        json_schema=json_schema,
    )
