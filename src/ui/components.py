"""
SDT - UIコンポーネント
"""
import os
import streamlit as st

from ..config import APP_NAME, APP_VERSION


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
