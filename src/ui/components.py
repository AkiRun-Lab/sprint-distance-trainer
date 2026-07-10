"""
SDT - UIコンポーネント
"""
import html
import os
import streamlit as st
import plotly.graph_objects as go

from ..config import APP_NAME, APP_VERSION, AMAZON_FITNESS_LIST_URL, SCORE_ITEMS, WEAKNESS_CTA_VARIANTS


def render_gear_cta(weakness: str = "general") -> None:
    """補強メニュー実践用の筋トレ・フィットネスグッズへ誘導するCTAカード

    Args:
        weakness: 診断結果から抽出した弱点カテゴリ（analyzer.extract_weakness_tag() の戻り値）。
                   未知のカテゴリの場合は "general" の文言にフォールバックする。
    """
    variant = WEAKNESS_CTA_VARIANTS.get(weakness, WEAKNESS_CTA_VARIANTS["general"])
    st.markdown(
        f"""
<style>
.akirun-gear-cta {{
    background: linear-gradient(135deg, #F4C66B, #E0A23D);
    border-radius: 14px;
    padding: 22px 20px;
    margin: 18px 0 8px;
    text-align: center;
    box-shadow: 0 4px 14px rgba(0,0,0,0.18);
}}
.akirun-gear-cta .gear-title {{
    color: #1F3A6B;
    font-weight: 700;
    font-size: clamp(1.05rem, 4.2vw, 1.3rem);
    margin: 0 0 6px;
}}
.akirun-gear-cta .gear-sub {{
    color: #4a3b14;
    font-size: clamp(0.85rem, 3.2vw, 0.95rem);
    line-height: 1.6;
    margin: 0 auto 14px;
    max-width: 36em;
}}
.akirun-gear-cta-btn {{
    display: inline-block;
    background: #1F3A6B;
    color: #ffffff !important;
    font-weight: 700;
    font-size: clamp(0.95rem, 3.6vw, 1.1rem);
    text-decoration: none !important;
    padding: 13px 30px;
    border-radius: 9px;
    box-shadow: 0 3px 8px rgba(0,0,0,0.22);
    transition: transform .12s ease, filter .12s ease;
}}
.akirun-gear-cta-btn:hover, .akirun-gear-cta-btn:visited, .akirun-gear-cta-btn:focus {{
    color: #ffffff !important;
    text-decoration: none !important;
    filter: brightness(1.12);
    transform: translateY(-1px);
}}
.akirun-gear-cta .gear-note {{
    color: #5a4a1f;
    font-size: 0.78rem;
    margin: 12px 0 0;
}}
</style>
<div class="akirun-gear-cta">
    <p class="gear-title">{variant["title"]}</p>
    <p class="gear-sub">{variant["sub"]}</p>
    <a class="akirun-gear-cta-btn" href="{variant["url"]}" target="_blank" rel="noopener noreferrer sponsored">筋トレ・補強グッズを見る ›</a>
    <p class="gear-note">ランナーの補強に必要なものを用途別に整理しています</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_score_radar(scores: dict) -> None:
    """5項目スコアのレーダーチャート＋数値サマリーを表示（SDTテーマ＝dark基調に合わせた配色）"""
    keys = list(SCORE_ITEMS.keys())
    labels = [SCORE_ITEMS[k] for k in keys]
    values = [scores[k] for k in keys]
    # 多角形を閉じるため先頭を末尾に重複させる
    labels_closed = labels + [labels[0]]
    values_closed = values + [values[0]]

    col_chart, col_summary = st.columns([2, 1])

    with col_chart:
        fig = go.Figure(go.Scatterpolar(
            r=values_closed, theta=labels_closed, fill="toself",
            line=dict(color="#22D3EE", width=2),
            fillcolor="rgba(34, 211, 238, 0.25)",
            marker=dict(size=8, color="#22D3EE"),
            hovertemplate="%{theta}: %{r}点<extra></extra>",
        ))
        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(range=[0, 10], dtick=2, gridcolor="rgba(148,163,184,0.25)",
                                tickfont=dict(color="#64748B", size=10), linecolor="rgba(148,163,184,0.25)"),
                angularaxis=dict(tickfont=dict(color="#E2E8F0", size=13),
                                 gridcolor="rgba(148,163,184,0.25)", linecolor="rgba(148,163,184,0.35)"),
            ),
            paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
            margin=dict(l=50, r=50, t=30, b=30), height=340,
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with col_summary:
        overall = sum(values) / len(values)
        rows_html = "".join(
            f'<div style="display:flex; justify-content:space-between; padding:6px 0; '
            f'border-bottom:1px solid rgba(148,163,184,0.15);">'
            f'<span style="color:#94A3B8; font-size:0.85rem;">{SCORE_ITEMS[k]}</span>'
            f'<span style="color:#FFFFFF; font-weight:700; font-size:0.85rem;">{scores[k]}</span>'
            f'</div>'
            for k in keys
        )
        st.markdown(
            f"""
<div style="text-align:center; margin-bottom:0.8rem;">
    <span style="color:#FFFFFF; font-weight:700; font-size:2.2rem;">{overall:.1f}</span>
    <span style="color:#94A3B8; font-size:0.8rem;"> / 10</span>
    <div style="color:#94A3B8; font-size:0.8rem; margin-top:2px;">総合スコア</div>
    <div style="height:2px; margin:8px auto 0; width:60%; background:linear-gradient(90deg, transparent, #22D3EE, #3B82F6, transparent);"></div>
</div>
<div>{rows_html}</div>
            """,
            unsafe_allow_html=True,
        )


def load_css() -> None:
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_header() -> None:
    st.markdown(f"""
<div class="sdt-hero">
    <h1>⚡ {APP_NAME}</h1>
    <p class="tagline">100m〜1500m対応 | フォーム診断×AIで最適なトレーニング計画を生成</p>
    <p class="version">v{APP_VERSION} | Powered by Gemini | AkiRun</p>
</div>
""", unsafe_allow_html=True)


def render_step_indicator(current_step: int) -> None:
    steps = ["基本情報", "フォーム診断", "計画生成"]

    circles = []
    connectors = []
    for i, label in enumerate(steps, start=1):
        if i < current_step:
            circle_class = "step-circle done"
            label_class = "step-label done"
            circle_content = "✓"
        elif i == current_step:
            circle_class = "step-circle active"
            label_class = "step-label active"
            circle_content = str(i)
        else:
            circle_class = "step-circle"
            label_class = "step-label"
            circle_content = str(i)

        circles.append((circle_class, circle_content, label_class, label))
        if i < len(steps):
            conn_class = "step-connector done" if i < current_step else "step-connector"
            connectors.append(conn_class)

    html = '<div class="step-indicator">'
    for idx, (cc, content, lc, label) in enumerate(circles):
        html += f"""
<div class="step-item">
    <div class="{cc}">{content}</div>
    <span class="{lc}">{label}</span>
</div>"""
        if idx < len(connectors):
            html += f'<div class="{connectors[idx]}"></div>'
    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)


def render_plan_summary(user_data: dict, total_weeks: int, has_form: bool) -> None:
    form_label = "あり" if has_form else "なし"
    # 自由入力のタイム欄は「<」や「&」でHTMLが崩れるためエスケープする
    target_time = html.escape(str(user_data["target_time"]))
    current_best = html.escape(str(user_data["current_best"]))
    st.markdown(f"""
<div class="plan-summary">
    <h3>📋 生成する計画の概要</h3>
    <div class="summary-grid">
        <div class="summary-item">
            <div class="label">目標距離</div>
            <div class="value">{user_data['distance']}</div>
        </div>
        <div class="summary-item">
            <div class="label">目標タイム</div>
            <div class="value">{target_time}</div>
        </div>
        <div class="summary-item">
            <div class="label">計画期間</div>
            <div class="value">{total_weeks}週間</div>
        </div>
        <div class="summary-item">
            <div class="label">現在のベスト</div>
            <div class="value">{current_best}</div>
        </div>
        <div class="summary-item">
            <div class="label">週練習日数</div>
            <div class="value">{user_data['training_days']}日</div>
        </div>
        <div class="summary-item">
            <div class="label">フォーム診断</div>
            <div class="value">{form_label}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


def render_result(result_text: str) -> None:
    st.markdown("---")
    st.subheader("トレーニング計画")
    st.markdown(result_text)


def render_footer() -> None:
    st.markdown(f"""
<div class="sdt-footer">
    <p>開発者：あきら｜
    <a href="https://akirun.net/" target="_blank">AkiRun｜走りを科学でアップデート</a></p>
    <p>{APP_NAME} v{APP_VERSION} | © 2025 AkiRun</p>
</div>
""", unsafe_allow_html=True)
