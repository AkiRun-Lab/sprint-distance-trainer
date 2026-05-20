# SDT 技術仕様書

**バージョン：v1.4.0　最終更新：2026-05-21**

---

## 1. アプリ概要

| 項目 | 内容 |
|------|------|
| 名称 | SDT（Sprint & Distance Trainer） |
| バージョン | v1.4.0 |
| フレームワーク | Streamlit |
| 実行環境 | Python 3.9 以上 |
| AI バックエンド | Google Gemini（google-genai SDK） |
| デプロイ先 | Streamlit Cloud |
| リポジトリ | https://github.com/AkiRun-Lab/sprint-distance-trainer |

---

## 2. 対応距離とエネルギーシステム

| 距離 | 主エネルギー系 | フェーズ構成 | 最小週数 | デフォルト週数 |
|------|--------------|------------|--------|--------------|
| 100m | ATP-PC系（無酸素・神経系） | GPP → SPP → 競技期 | 8週 | 12週 |
| 200m | ATP-PC系 ＋ グリコーゲン分解系 | GPP → SPP → 競技期 | 8週 | 12週 |
| 400m | グリコーゲン分解系（無酸素系主体） | GPP → SPP → 競技期 | 10週 | 16週 |
| 800m | 有酸素系 ＋ 無酸素系（混合） | 有酸素基盤 → スピード持久力 → 競技期 | 10週 | 16週 |
| 1500m | 有酸素系主体 ＋ 無酸素系補完 | 有酸素基盤 → スピード持久力 → 競技期 | 12週 | 16週 |

---

## 3. AI モデル設定

### 3-1. スクリーナー（動画フィルタリング）

| パラメータ | 値 |
|-----------|-----|
| モデル | gemini-3.1-flash-lite |
| temperature | 0.2 |
| max_tokens | 256 |

役割：アップロードされた動画がランニング動画として適切かをチェックする。不適切な動画（関係のない映像・静止画等）を弾く。

### 3-2. アナライザー（フォーム診断）

| パラメータ | 値 |
|-----------|-----|
| モデル | gemini-3.5-flash |
| max_tokens | 16384 |
| thinking_budget | 16384 |

※ `temperature` / `top_p` / `top_k` は Gemini 3.5 Flash のデフォルト設定に最適化済みのため非推奨（指定しない）

診断項目：
- 全体的なランニングエコノミー
- 接地パターンと足部動作
- 姿勢・体幹安定性
- 腕振りと上半身の動き
- ストライドと歩幅のバランス
- 短距離特有（加速局面の前傾・接地時間・knee drive 等）

出力構成：
1. 全体評価
2. 主な改善点（優先順位付き）
3. 具体的なトレーニング提案（実施タイミング付き）

### 3-3. プランナー（計画生成）

| パラメータ | 値 |
|-----------|-----|
| モデル | gemini-3-flash-preview |
| temperature | 0.2 |
| top_p | 0.95 |
| max_tokens | 32768 |
| thinking_budget | 8192 |
| 出力形式 | application/json |

JSON スキーマ（主要フィールド）：
- `introduction`：コーチからの挨拶・評価
- `basic_info`：選手名・年齢・性別・目標距離・タイム・目標レース日・計画期間・週練習日数・施設環境・要望事項・フォーム改善テーマ
- `phase_overview`：フェーズ説明
- `weekly_schedules`：週次スケジュール（曜日・メニュー・詳細・強度・休憩・コーチングポイント）
- `precautions`：注意事項リスト
- `coach_message`：激励メッセージ

---

## 4. 動画処理フロー

```
[ユーザー] 動画アップロード
    ↓
[screener.py] 動画スクリーニング（Gemini flash-lite）
    → 不適切 → エラーメッセージ表示
    → 適切 ↓
[analyzer.py] フォーム診断（Gemini 3.5 Flash + Thinking）
    ↓
[app.py] 診断結果を session_state に保存
    ↓
[Files API] 動画を自動削除（cleanup_video）
    ↓
[app.py] ダウンロードボタン表示（sdt_form_diagnosis_YYYYMMDD.md）
```

- アップロード形式：MP4 / MOV / AVI / WEBM
- 最大サイズ：200MB
- ポーリング間隔：2秒
- アップロードタイムアウト：120秒

---

## 5. 計画生成フロー

```
[app.py] ユーザーデータ・フォーム診断結果を収集
    ↓
[plan_prompts.py] build_plan_prompt() でプロンプトを構築
    ↓
[threading.Thread] バックグラウンドで generate_plan() を実行
    ↓
[planner.py] Gemini API 呼び出し（リトライ最大2回）
    ↓
[planner.py] JSON → Markdown 変換（_plan_json_to_markdown）
    ↓
[app.py] 結果を session_state.training_plan に保存
    ↓
[app.py] ダウンロード内容を構築
         training_plan + フォーム診断結果（あれば末尾付記）
```

- 計画開始日：目標レース日から逆算した直近の月曜日
- リトライ：503 / 429 エラー時に指数バックオフで最大 2 回

---

## 6. ダウンロードファイル仕様

### 6-1. フォーム診断結果

| 項目 | 内容 |
|------|------|
| ファイル名 | `sdt_form_diagnosis_YYYYMMDD.md` |
| 内容 | Gemini が出力した Markdown 形式の診断テキスト |
| エンコーディング | UTF-8 BOM（スマートフォン対応） |
| ダウンロード箇所 | STEP 2（診断完了後 / 既存診断結果表示時） |

### 6-2. トレーニング計画

| 項目 | 内容 |
|------|------|
| ファイル名 | `sdt_plan_{距離}_{YYYYMMDD}.md` |
| 内容 | 計画 Markdown + フォーム診断結果（診断ありの場合のみ末尾付記） |
| エンコーディング | UTF-8 BOM（スマートフォン対応） |
| ダウンロード箇所 | STEP 3（計画生成後） |

計画ファイルへの診断結果付記フォーマット：
```
{計画本文}

---

## フォーム診断結果

{診断テキスト}
```

---

## 7. 使用回数制限

### 制限仕様

| 機能 | 1日あたりの上限 | 管理者 |
|------|--------------|-------|
| フォーム診断 | 3回 | 無制限 |
| トレーニング計画生成 | 3回 | 無制限 |

### Cookie による永続化

使用回数は以下の Cookie に保存されます。

| Cookie キー | 内容 | 有効期限 |
|------------|------|--------|
| `sdt_date` | 最終リセット日（YYYY-MM-DD） | 1日 |
| `sdt_diag_count` | フォーム診断の当日累計回数 | 1日 |
| `sdt_plan_count` | 計画生成の当日累計回数 | 1日 |

日付が変わると自動リセットされます。ブラウザのリロードではリセットされません。

### 初期化シーケンス

`streamlit-cookies-controller` はカスタムコンポーネントのため、初回レンダリングでは Cookie 値が未取得です。以下の3段階で初期化します。

1. Render 1：`_first_render_done = True` をセットしてスキップ
2. Render 2（null rerun）：`TypeError` を try-except で吸収してスキップ
3. Render 3（実値 rerun）：Cookie 値を読み込んで `counts_loaded = True`

書き込みは `cookie_write_pending` フラグ経由で次の描画サイクル先頭にまとめて実行します。

---

## 8. フォーム診断の計画への反映

フォーム診断がある場合、プロンプトに以下の指示を追加します。

- 「具体的なトレーニング提案」に含まれるすべての種目を週次スケジュールに組み込む
  - ドリル → ウォームアップ後（神経系が疲れていない状態）
  - 筋力トレーニング → 本練習後 or 別日
  - モビリティ・ストレッチ → クールダウン or 軽練習日
  - プライオメトリクス → 本練習前（ウォームアップ後の神経活性化）
- コーチングポイントフィールドに「（フォーム改善：〇〇）」と目的を明示する

---

## 9. ファイル構成

```
apps/sdt/
├── app.py                       # メイン Streamlit アプリ
├── requirements.txt             # 依存パッケージ
├── CHANGELOG.md                 # 更新履歴
├── README.md                    # セットアップ・概要
├── docs/
│   ├── user-manual.md           # ユーザーマニュアル
│   └── spec.md                  # 本仕様書
├── .streamlit/
│   ├── config.toml              # Streamlit 設定
│   ├── secrets.toml             # API キー（Git 管理外）
│   └── secrets.toml.example    # シークレットのテンプレート
└── src/
    ├── __init__.py
    ├── config.py                # 定数（モデル名・制限値・距離カテゴリ等）
    ├── screener.py              # 動画スクリーニング
    ├── analyzer.py              # フォーム診断（動画アップロード・解析）
    ├── planner.py               # 計画生成（JSON パース・Markdown 変換）
    ├── prompts/
    │   ├── __init__.py
    │   ├── form_prompts.py      # フォーム診断用プロンプト
    │   └── plan_prompts.py      # 計画生成用プロンプト
    └── ui/
        ├── __init__.py
        ├── components.py        # UI コンポーネント（ヘッダー・フッター等）
        └── styles.css           # カスタム CSS
```

---

## 10. 依存パッケージ

| パッケージ | バージョン要件 | 用途 |
|-----------|------------|------|
| streamlit | >=1.30.0 | Web フレームワーク |
| google-genai | >=1.0.0 | Gemini API クライアント |
| streamlit-cookies-controller | >=0.0.4 | Cookie 読み書き |

---

## 11. セキュリティ

- API キー・管理者パスワードは `.streamlit/secrets.toml` で管理し、コードにハードコードしない
- Cookie による使用制限はうっかり操作防止を目的とし、悪意ある回避（Cookie クリア）への対策は設けない
- 動画は Gemini Files API にアップロード後、診断完了時に即座に削除する
