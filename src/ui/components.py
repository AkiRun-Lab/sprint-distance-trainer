"""
SDT - UIコンポーネント
"""
import os
import streamlit as st

from ..config import APP_NAME, APP_VERSION, AMAZON_FITNESS_LIST_URL


def render_gear_cta() -> None:
    """補強メニュー実践用の筋トレ・フィットネスグッズへ誘導するCTAカード"""
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
    <p class="gear-title">💪 補強メニューを、自宅で実践する</p>
    <p class="gear-sub">計画に含まれる筋力トレーニング・プライオ・コア・ドリルに必要な用品を、用途別にAmazonのおすすめリストにまとめました。
    殿筋・体幹・足首の安定づくりと弾性・パワーの強化に役立つグッズを揃えています。</p>
    <a class="akirun-gear-cta-btn" href="{AMAZON_FITNESS_LIST_URL}" target="_blank" rel="noopener noreferrer sponsored">筋トレ・補強グッズを見る ›</a>
    <p class="gear-note">ランナーの補強に必要なものを用途別に整理しています</p>
</div>
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
            <div class="value">{user_data['target_time']}</div>
        </div>
        <div class="summary-item">
            <div class="label">計画期間</div>
            <div class="value">{total_weeks}週間</div>
        </div>
        <div class="summary-item">
            <div class="label">現在のベスト</div>
            <div class="value">{user_data['current_best']}</div>
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
