# SDT — Sprint & Distance Trainer

短距離・中距離ランナー向け AI トレーニング計画生成ツール。  
100m〜1500m に対応し、ランニングフォーム診断をオプションで統合できます。

## 対象ユーザー

- 100m / 200m / 400m / 800m / 1500m の競技タイム向上を目指す市民ランナー
- 科学的根拠に基づいた個別トレーニング計画を求める人

## 主な機能

| 機能 | 概要 |
|------|------|
| 基本情報入力 | 目標距離・タイム・レース日・環境条件を入力 |
| フォーム診断（任意） | ランニング動画を AI が解析し、改善点を提示 |
| トレーニング計画生成 | 週次スケジュールを Markdown 形式で出力・ダウンロード可 |

## セットアップ

### 必要条件

- **Python 3.10 以上**（コードが型注釈に PEP 604 の `X | None` 構文を使用。3.9 以下では `TypeError: unsupported operand type(s) for |` が出ます）。3.11 を推奨
- Gemini API キー

### インストール

```bash
# 仮想環境を作成（3.11 推奨）。macOS で 3.11 が無ければ brew install python@3.11
python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### シークレット設定

`.streamlit/secrets.toml` に以下を設定します（`.streamlit/secrets.toml.example` を参照）。

```toml
GEMINI_API_KEY = "your-api-key"
ADMIN_PASSWORD  = "your-admin-password"
```

### 起動

```bash
streamlit run app.py
```

## ファイル構成

```
apps/sdt/
├── app.py                  # メインアプリ
├── requirements.txt
├── CHANGELOG.md
├── README.md
├── docs/
│   ├── user-manual.md      # ユーザーマニュアル
│   └── spec.md             # 技術仕様書
└── src/
    ├── config.py           # 定数・設定
    ├── screener.py         # 動画スクリーニング
    ├── analyzer.py         # フォーム診断
    ├── planner.py          # 計画生成
    ├── prompts/
    │   ├── form_prompts.py # フォーム診断プロンプト
    │   └── plan_prompts.py # 計画生成プロンプト
    └── ui/
        ├── components.py   # UI コンポーネント
        └── styles.css      # スタイルシート
```

## 使用上の制限

- フォーム診断：1日1回まで（管理者は無制限）
- トレーニング計画生成：1日1回まで（管理者は無制限）
- 動画アップロード：200MB 以下、MP4 / MOV / AVI / WEBM 形式

## 技術スタック

- フレームワーク：Streamlit
- AI モデル：Google Gemini（google-genai SDK）
- 状態管理：Streamlit Session State + Cookie（streamlit-cookies-controller）

## ライセンス

AkiRun 内部プロダクト。外部公開・再配布不可。
