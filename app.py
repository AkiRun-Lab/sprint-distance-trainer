"""
SDT（Sprint & Distance Trainer）
短距離〜中距離ランナー向けトレーニング計画生成ツール
"""
import threading
from datetime import datetime, timedelta

import streamlit as st
from google import genai
from streamlit_cookies_controller import CookieController

from src.config import (
    APP_NAME,
    DISTANCE_OPTIONS,
    DISTANCE_CATEGORIES,
    SUPPORTED_VIDEO_TYPES,
    MAX_DIAGNOSES_PER_SESSION,
    MAX_PLAN_GENERATIONS_PER_SESSION,
)
from src.screener import screen_video
from src.analyzer import upload_video, analyze_form, cleanup_video
from src.planner import calculate_plan_weeks, generate_plan
from src.ui.components import load_css, render_header, render_step_indicator, render_plan_summary, render_result, render_gear_cta, render_footer

# =============================================
# ページ設定
# =============================================
st.set_page_config(page_title=APP_NAME, page_icon="⚡", layout="centered", initial_sidebar_state="collapsed")

# =============================================
# Cookie コントローラー
# =============================================
_cookie_controller = CookieController()


def _load_cookie_counts(controller: CookieController):
    """読み込み専用。書き込みは cookie_write_pending ブロックで行う。"""
    today = datetime.today().strftime("%Y-%m-%d")
    cookie_date = controller.get("sdt_date") or ""
    if cookie_date != today:
        return 0, 0
    diag = int(controller.get("sdt_diag_count") or "0")
    plan = int(controller.get("sdt_plan_count") or "0")
    return diag, plan


def _generate_plan_inline(api_key, user_data, form_diagnosis):
    """STEP 2 のボタン押下時にインラインで計画生成を実行し、プログレスバーを表示する。

    中間 st.rerun() なしで即座に while ループに入るため、
    ブラウザに STEP 2 の dim overlay が残るフリーズを防ぐ。
    """
    import time as _time

    plan_limit_reached = (
        st.session_state.plan_count >= MAX_PLAN_GENERATIONS_PER_SESSION
        and not st.session_state.is_admin
    )
    if plan_limit_reached:
        st.session_state.step = 3
        st.rerun()

    total_weeks, start_date = calculate_plan_weeks(user_data["race_date"], user_data["distance"])
    result_container = []
    error_container = []
    thread = threading.Thread(
        target=generate_plan,
        args=(api_key, user_data, form_diagnosis, total_weeks, start_date, result_container, error_container),
        daemon=True,
    )
    thread.start()

    ESTIMATED_SECONDS = 60
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    elapsed = 0
    while thread.is_alive():
        elapsed += 0.5
        progress = min(0.95, elapsed / ESTIMATED_SECONDS)
        progress_bar.progress(progress)
        status_text.text(f"Gemini がトレーニング計画を作成中です... （約{ESTIMATED_SECONDS}秒）")
        _time.sleep(0.5)

    thread.join()
    progress_bar.progress(1.0)
    status_text.empty()

    if result_container:
        st.session_state.training_plan = result_container[0]
        st.session_state.plan_count += 1
        st.session_state.cookie_write_pending = True
        st.session_state.step = 3
        st.rerun()
    else:
        err = error_container[0] if error_container else "UNKNOWN"
        if "503_SERVICE_UNAVAILABLE" in err:
            st.error("⚠️ サーバーが混雑しています。しばらく待ってから再試行してください。")
        elif "429_RATE_LIMITED" in err:
            st.error("⚠️ APIのリクエスト上限に達しました。しばらく待ってから再試行してください。")
        else:
            st.error(f"⚠️ 計画の生成に失敗しました: {err}")

# =============================================
# セッション状態の初期化
# =============================================
def _init_session_state():
    defaults = {
        "step": 1,
        "user_data": {},
        "form_diagnosis": None,
        "use_form_in_plan": False,
        "training_plan": None,
        "diagnosis_count": 0,
        "plan_count": 0,
        "is_admin": False,
        "counts_loaded": False,
        "cookie_write_pending": False,
        "_first_render_done": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session_state()

if not st.session_state.counts_loaded:
    if st.session_state._first_render_done:
        # Render 2+: コンポーネントがロード中 or 済み
        try:
            diag, plan = _load_cookie_counts(_cookie_controller)
            st.session_state.diagnosis_count = diag
            st.session_state.plan_count = plan
            st.session_state.counts_loaded = True
        except Exception:
            # null rerun による TypeError を捕捉、次の自動 rerun に委ねる
            pass
    else:
        # Render 1: コンポーネント未ロードのためスキップ
        st.session_state._first_render_done = True

# rerun直前にset()すると書き込みが失われるため、次の描画サイクル先頭でまとめて書く
if st.session_state.get("cookie_write_pending"):
    _cookie_opts = dict(
        same_site='none',
        secure=True,
        partitioned=True,
        expires=datetime.now() + timedelta(days=2),
    )
    _cookie_controller.set("sdt_date", datetime.today().strftime("%Y-%m-%d"), **_cookie_opts)
    _cookie_controller.set("sdt_diag_count", str(st.session_state.diagnosis_count), **_cookie_opts)
    _cookie_controller.set("sdt_plan_count", str(st.session_state.plan_count), **_cookie_opts)
    st.session_state.cookie_write_pending = False

# =============================================
# API クライアント初期化
# =============================================
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    st.error("⚠️ GEMINI_API_KEY が設定されていません。.streamlit/secrets.toml を確認してください。")
    st.stop()

client = genai.Client(api_key=api_key)

# =============================================
# サイドバー（管理者認証）
# =============================================
with st.sidebar:
    st.subheader("設定")
    if st.session_state.is_admin:
        st.success("管理者モード（回数制限なし）")
        if st.button("ログアウト"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        admin_pw = st.text_input("管理者パスワード", type="password", key="admin_pw_input")
        if st.button("ログイン"):
            if admin_pw == st.secrets.get("ADMIN_PASSWORD", ""):
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("パスワードが違います")

# =============================================
# ヘッダー
# =============================================
load_css()
render_header()
render_step_indicator(st.session_state.step)

# =============================================
# STEP 1: 基本情報入力
# =============================================
if st.session_state.step == 1:
    st.subheader("STEP 1　基本情報の入力")

    # 距離選択はフォーム外に置いて変更時に即時反映させる
    distance = st.selectbox(
        "目標距離",
        options=DISTANCE_OPTIONS,
        format_func=lambda x: DISTANCE_CATEGORIES[x]["label"],
        key="distance_select",
    )
    dist_info = DISTANCE_CATEGORIES[distance]

    with st.form("basic_info_form"):
        col1, col2 = st.columns(2)
        with col1:
            nickname = st.text_input("ニックネーム", placeholder="あきら")
            age = st.number_input("年齢", min_value=10, max_value=100, value=30)
        with col2:
            gender = st.selectbox("性別", ["男性", "女性", "その他"])
            training_days = st.selectbox("週練習日数", list(range(2, 8)), index=3)


        time_placeholder = dist_info["time_format"].split("（")[1].rstrip("）")
        col3, col4 = st.columns(2)
        with col3:
            current_best = st.text_input(
                "現在のベストタイム",
                placeholder=time_placeholder,
                key="current_best_input",
            )
        with col4:
            target_time = st.text_input(
                "目標タイム",
                placeholder=time_placeholder,
                key="target_time_input",
            )

        race_date = st.date_input(
            "目標レース日",
            value=datetime.today() + timedelta(weeks=dist_info["default_weeks"]),
            min_value=datetime.today() + timedelta(days=1),
        )

        st.markdown('練習レース・記録会 <span style="background-color: #1976D2; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 4px;">任意</span>', unsafe_allow_html=True)
        practice_races = st.text_area(
            "練習レース・記録会",
            placeholder="例: 6/1 春季記録会（400m）\n6/15 招待記録会（800m）",
            height=80,
            label_visibility="collapsed",
        )

        col5, col6 = st.columns(2)
        with col5:
            has_track = st.checkbox("トラック（競技場）が使える")
        with col6:
            has_gym = st.checkbox("ウェイトジムが使える")

        st.markdown('要望・注意事項 <span style="background-color: #1976D2; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 4px;">任意</span>', unsafe_allow_html=True)
        concerns = st.text_area(
            "要望・注意事項",
            placeholder="例1：左膝に違和感がある、朝練ができない\n例2：400m、800mにも取り組みたい",
            height=80,
            label_visibility="collapsed",
        )

        submitted = st.form_submit_button("次へ → フォーム診断", use_container_width=True)

    if submitted:
        errors = []
        if not nickname.strip():
            errors.append("ニックネームを入力してください")
        if not current_best.strip():
            errors.append("現在のベストタイムを入力してください")
        if not target_time.strip():
            errors.append("目標タイムを入力してください")

        if errors:
            for e in errors:
                st.error(f"❌ {e}")
        else:
            st.session_state.user_data = {
                "distance": st.session_state.get("distance_select", distance),
                "nickname": nickname.strip(),
                "age": age,
                "gender": gender,
                "training_days": training_days,
                "current_best": current_best.strip(),
                "target_time": target_time.strip(),
                "race_date": race_date.strftime("%Y-%m-%d"),
                "has_track": has_track,
                "has_gym": has_gym,
                "concerns": concerns.strip(),
                "practice_races": practice_races.strip(),
            }
            st.session_state.step = 2
            st.rerun()

# =============================================
# STEP 2: フォーム診断（オプション）
# =============================================
elif st.session_state.step == 2:
    st.subheader("STEP 2　フォーム診断（任意）")
    st.info(
        "走っている動画をアップロードすると、フォームの問題点を診断してトレーニング計画に組み込みます。\n"
        "スキップしてもトレーニング計画は作成できます。"
    )

    diagnosis_limit_reached = (
        st.session_state.diagnosis_count >= MAX_DIAGNOSES_PER_SESSION
        and not st.session_state.is_admin
    )

    if not diagnosis_limit_reached:
        uploaded_file = st.file_uploader(
            "動画をアップロード（MP4/MOV/AVI/WEBM、200MBまで）",
            type=SUPPORTED_VIDEO_TYPES,
        )
        if uploaded_file:
            st.video(uploaded_file)
        context_input = st.text_area(
            "距離・気になる点など（任意）",
            placeholder=(
                "例1：1000m×5インターバルの5本目後半です。ペースは3分30秒/kmです。\n"
                "例2：100m走のレース動画です。6コースの黄色いランシャツの選手のフォームを診断してください。"
            ),
            height=80,
        )

        col_diag, col_skip = st.columns(2)
        with col_diag:
            run_diagnosis = st.button(
                "フォームを診断する",
                disabled=(uploaded_file is None),
                use_container_width=True,
            )
        with col_skip:
            skip_diagnosis = st.button(
                "スキップして計画を作成する",
                use_container_width=True,
            )
    else:
        st.warning(f"1日あたりのフォーム診断は{MAX_DIAGNOSES_PER_SESSION}回までです。明日またお試しください。")
        skip_diagnosis = st.button("スキップして計画を作成する", use_container_width=True)
        run_diagnosis = False
        uploaded_file = None
        context_input = ""

    # フォーム診断の実行
    video_file = None
    if run_diagnosis and uploaded_file:
        video_bytes = uploaded_file.read()
        try:
            with st.status("動画をアップロード中...", expanded=True):
                video_file = upload_video(client, video_bytes, uploaded_file.name)
                st.write("アップロード完了")

            with st.status("動画をチェック中...", expanded=False):
                screen_result = screen_video(client, video_file)

            if not screen_result["ok"]:
                st.error(f"❌ {screen_result['reason']}")
            else:
                with st.status("フォームを解析中...", expanded=True):
                    st.write("Gemini が動画を解析しています（1〜2分かかる場合があります）")
                    diagnosis_result = analyze_form(client, video_file, context_input)

                st.session_state.form_diagnosis = diagnosis_result
                st.session_state.use_form_in_plan = True
                st.session_state.diagnosis_count += 1
                st.session_state.cookie_write_pending = True

        except RuntimeError as e:
            err = str(e)
            if "429_RATE_LIMITED" in err:
                st.error("⚠️ APIのレート制限に達しました。しばらく待ってから再試行してください。")
            elif "503_SERVICE_UNAVAILABLE" in err:
                st.error("⚠️ APIが一時的に利用できません。しばらく待ってから再試行してください。")
            else:
                st.error(f"⚠️ エラーが発生しました: {err}")
        finally:
            if video_file:
                cleanup_video(client, video_file)

    # 次のステップへ進むボタン（診断完了後）— cleanup完了後にまとめて表示
    if st.session_state.form_diagnosis:
        st.success("診断完了！")
        if st.button("計画を作成する →", use_container_width=True, type="primary"):
            _generate_plan_inline(api_key, st.session_state.user_data, st.session_state.form_diagnosis)

    # スキップ
    if skip_diagnosis:
        st.session_state.form_diagnosis = None
        st.session_state.use_form_in_plan = False
        _generate_plan_inline(api_key, st.session_state.user_data, None)

    # 戻るボタン
    if st.button("← 戻る"):
        st.session_state.step = 1
        st.rerun()

# =============================================
# STEP 3: トレーニング計画生成
# =============================================
elif st.session_state.step == 3:
    st.subheader("STEP 3　トレーニング計画の生成")

    user_data = st.session_state.user_data
    form_diagnosis = st.session_state.form_diagnosis

    total_weeks, start_date = calculate_plan_weeks(user_data["race_date"], user_data["distance"])

    render_plan_summary(user_data, total_weeks, form_diagnosis is not None)

    plan_limit_reached = (
        st.session_state.plan_count >= MAX_PLAN_GENERATIONS_PER_SESSION
        and not st.session_state.is_admin
    )

    # 既存の計画がある場合は表示
    if st.session_state.training_plan:
        render_result(st.session_state.training_plan)
        render_gear_cta()

        if st.session_state.get("form_diagnosis"):
            with st.expander("フォーム診断結果を確認する", expanded=False):
                st.markdown(st.session_state.form_diagnosis)

        col_dl, col_new = st.columns(2)
        with col_dl:
            today_str = datetime.now().strftime("%Y%m%d")
            _download_content = st.session_state.training_plan
            if st.session_state.form_diagnosis:
                _download_content += (
                    "\n\n---\n\n## フォーム診断結果\n\n"
                    + st.session_state.form_diagnosis
                )
            st.download_button(
                label="計画をダウンロード（Markdown）",
                data=_download_content.encode("utf-8-sig"),
                file_name=f"sdt_plan_{user_data['distance']}_{today_str}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_new:
            if st.button("最初からやり直す", use_container_width=True):
                for key in ["step", "user_data", "form_diagnosis", "use_form_in_plan", "training_plan"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    elif not plan_limit_reached:
        if st.button("トレーニング計画を生成する", type="primary", use_container_width=True):
            result_container = []
            error_container = []

            thread = threading.Thread(
                target=generate_plan,
                args=(api_key, user_data, form_diagnosis, total_weeks, start_date, result_container, error_container),
                daemon=True,
            )
            thread.start()

            ESTIMATED_SECONDS = 60
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            elapsed = 0

            import time as _time
            while thread.is_alive():
                elapsed += 0.5
                progress = min(0.95, elapsed / ESTIMATED_SECONDS)
                progress_bar.progress(progress)
                status_text.text(f"Gemini がトレーニング計画を作成中です... （約{ESTIMATED_SECONDS}秒）")
                _time.sleep(0.5)

            thread.join()
            progress_bar.progress(1.0)
            status_text.empty()

            if result_container:
                st.session_state.training_plan = result_container[0]
                st.session_state.plan_count += 1
                st.session_state.cookie_write_pending = True
                st.rerun()
            else:
                err = error_container[0] if error_container else "UNKNOWN"
                if "503_SERVICE_UNAVAILABLE" in err:
                    st.error("⚠️ サーバーが混雑しています。しばらく待ってから再試行してください。")
                elif "429_RATE_LIMITED" in err:
                    st.error("⚠️ APIのリクエスト上限に達しました。しばらく待ってから再試行してください。")
                else:
                    st.error(f"⚠️ 計画の生成に失敗しました: {err}")
    else:
        st.warning(f"1日あたりの計画生成は{MAX_PLAN_GENERATIONS_PER_SESSION}回までです。明日またお試しください。")

    # 戻るボタン
    if not st.session_state.training_plan:
        if st.button("← 戻る"):
            st.session_state.step = 2
            st.rerun()

# =============================================
# フッター
# =============================================
render_footer()
