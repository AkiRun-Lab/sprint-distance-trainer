# 引き継ぎ書：SDT 診断モデル gemini-3.5-flash 移行

作成日：2026-05-21

---

## 背景・目的

RFDアプリで実施済みの作業と同じ移行。
メイン診断モデル（フォーム分析）を `gemini-3.1-pro-preview` → `gemini-3.5-flash` に切り替える。

**変更しないモデル：**
- `GEMINI_SCREENER_MODEL = "gemini-3.1-flash-lite"` → そのまま
- `GEMINI_PLANNER_MODEL = "gemini-3-flash-preview"` → そのまま

---

## Gemini 3.5 Flash の仕様変更（重要）

| 項目 | 旧仕様 | 新仕様 |
|------|--------|--------|
| `temperature` / `top_p` / `top_k` | 有効 | **非推奨・削除**（モデルのデフォルト設定に最適化済み） |
| `thinking_budget` | 整数（8192） | 整数のまま変更なし。**ただし上限が拡大されたため 16384 に増やす** |
| `thinking_level` | なし | ドキュメントに記載あるが **現行SDKには未実装**。文字列で渡すとPydanticエラーになる。使わない |

---

## 変更ファイルと具体的な変更内容

### 1. `src/config.py`

```python
# 変更前
GEMINI_ANALYZER_MODEL = "gemini-3.1-pro-preview"

ANALYZER_TEMPERATURE = 0.2    # → 削除
ANALYZER_TOP_P = 0.8          # → 削除
ANALYZER_TOP_K = 32           # → 削除
ANALYZER_MAX_TOKENS = 16384   # → そのまま
ANALYZER_THINKING_BUDGET = 8192  # → 16384 に変更

# 変更後
GEMINI_ANALYZER_MODEL = "gemini-3.5-flash"

ANALYZER_MAX_TOKENS = 16384
ANALYZER_THINKING_BUDGET = 16384
```

**触らないもの：**
- `SCREENER_TEMPERATURE` / `SCREENER_MAX_TOKENS` → そのまま
- `PLANNER_TEMPERATURE` / `PLANNER_TOP_P` / `PLANNER_MAX_TOKENS` / `PLANNER_THINKING_BUDGET` → そのまま

### 2. `src/analyzer.py`

importから削除：`ANALYZER_TEMPERATURE`, `ANALYZER_TOP_P`, `ANALYZER_TOP_K`

```python
# 変更前（config importの箇所）
from .config import (
    GEMINI_ANALYZER_MODEL,
    ANALYZER_TEMPERATURE,
    ANALYZER_TOP_P,
    ANALYZER_TOP_K,
    ANALYZER_MAX_TOKENS,
    ANALYZER_THINKING_BUDGET,
    ...
)

# 変更後
from .config import (
    GEMINI_ANALYZER_MODEL,
    ANALYZER_MAX_TOKENS,
    ANALYZER_THINKING_BUDGET,
    ...
)
```

`generate_content` の `config` から削除：

```python
# 変更前
config=types.GenerateContentConfig(
    system_instruction=ANALYZER_SYSTEM_INSTRUCTION,
    temperature=ANALYZER_TEMPERATURE,   # → 削除
    top_p=ANALYZER_TOP_P,               # → 削除
    top_k=ANALYZER_TOP_K,               # → 削除
    max_output_tokens=ANALYZER_MAX_TOKENS,
    thinking_config=types.ThinkingConfig(
        thinking_budget=ANALYZER_THINKING_BUDGET,
    ),
),

# 変更後
config=types.GenerateContentConfig(
    system_instruction=ANALYZER_SYSTEM_INSTRUCTION,
    max_output_tokens=ANALYZER_MAX_TOKENS,
    thinking_config=types.ThinkingConfig(
        thinking_budget=ANALYZER_THINKING_BUDGET,
    ),
),
```

docstringも更新：`gemini-pro-preview` → `gemini-3.5-flash`

### 3. `src/prompts/form_prompts.py`

コメントのみ更新：
```python
# フォーム診断（gemini-pro-preview）  →  # フォーム診断（gemini-3.5-flash）
```

### 4. `CHANGELOG.md`

v1.4.0 エントリを追加（現在の最新は v1.3.0）

### 5. `docs/spec.md`・`docs/user-manual.md`・`README.md`

`gemini-3.1-pro-preview` → `gemini-3.5-flash`、thinking_budget 8192 → 16384 に更新

---

## RFDとの違い（注意点）

| 項目 | RFD | SDT |
|------|-----|-----|
| 診断パラメータ定数 | 共有変数（`GEMINI_TEMPERATURE` 等）| **アプリ別に分離済み**（`ANALYZER_TEMPERATURE`、`SCREENER_TEMPERATURE`）|
| スクリーナーへの影響 | importエラーが発生した（要修正） | **発生しない**（すでに分離済み） |
| プランナー | なし | `planner.py`・`PLANNER_*` 定数が存在 → **変更しない** |

SDT は RFD より設計が整理されているため、修正箇所は少ない。

---

## 動作確認手順

```bash
cd /Users/yasuchin/akirun_project/apps/sdt
python3 -m streamlit run app.py
```

確認項目：
1. スクリーニング（flash-lite）が正常に動作すること
2. フォーム診断が `gemini-3.5-flash` で実行されること
3. プランナー（flash-preview）が正常に動作すること
4. エラーなく完了すること（特に `ThinkingConfig` の Pydantic エラーが出ないこと）

---

## コミット・プッシュ

```bash
git add -A
git commit -m "feat: 診断モデルを gemini-3.1-pro-preview から gemini-3.5-flash に移行 (v1.4.0)"
git push origin main
```
