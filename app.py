import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import time
import datetime

# 1. 페이지 설정
st.set_page_config(page_title="가족 자산 대시보드", layout="centered")

# --- 🎨 2. CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem !important; padding-bottom: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    header { visibility: hidden; height: 0px; }
    img { border-radius: 20px; margin-bottom: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .main-title { font-size: 1.4rem !important; font-weight: 800; margin-bottom: 2px; color: #31333F; }
    @media (prefers-color-scheme: dark) { .main-title { color: #ffffff; } }
    div[data-testid="metric-container"] { background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 8px 4px !important; border-radius: 12px; }
    @media (prefers-color-scheme: dark) { div[data-testid="metric-container"] { background-color: #262730 !important; border: 1px solid #414141 !important; } }
    [data-testid="stMetricValue"] { font-size: 0.95rem !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; }
    .floating-nav { position: fixed; bottom: 15px; left: 50%; transform: translateX(-50%); background-color: rgba(255, 255, 255, 0.95); backdrop-filter: blur(8px); padding: 8px 18px; border-radius: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); display: flex; gap: 15px; z-index: 1000; border: 1px solid #eee; }
    .floating-nav a { text-decoration: none; color: #555; font-size: 0.8rem; font-weight: 600; }
    .goal-text { font-size: 1.2rem; font-weight: bold; color: #1f77b4; margin-bottom: 10px; }
    @media (prefers-color-scheme: dark) { .goal-text { color: #4facfe; } }
    .stButton > button { width: 100%; border-radius: 12px; border: 1px solid #ddd; height: 38px; }
</style>
<div class="floating-nav">
    <a href="#summary">💰 요약</a> <a href="#charts">📊 구성</a> <a href="#table">📋 상세</a>
</div>
""", unsafe_allow_html=True)

# --- 🔑 3. 데이터 및 API 설정 ---
try:
    SHEET_ID = st.secrets["SHEET_ID"].strip()
    SHEET_GID = st.secrets["SHEET_GID"].strip()
    # 🚨 주의: HISTORY_GID가 Secrets에 없으면 과거 데이터를 못 가져옵니다!
    HISTORY_GID = st.secrets.get("HISTORY_GID", "").strip() 
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
    
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
except:
    st.error("Secrets 설정을 확인해주세요! (SHEET_ID, SHEET_GID 등)")
    st.stop()

def format_krw(amount):
    is_negative = amount < 0
    amount = abs(amount)
    if amount == 0: return "0 원"
    eok = int(amount // 100000000)
    man = int((amount % 100000000) // 10000)
    res = f"{eok}억 " if eok > 0 else ""
    res += f"{man:,}만" if man > 0 else ""
    return f"{'-' if is_negative else ''}{res.strip()} 원"

@st.cache_data(ttl=60)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
    try:
        df = pd.read_csv(url)
        df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',', '').str.replace('₩', ''), errors='coerce').fillna(0)
        df.loc[df['대분류'] == '부채', '금액'] = df.loc[df['대분류'] == '부채', '금액'].abs() * -1
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_history_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        # 3행을 헤더로 사용하기 위해 위쪽 2줄 무시
        df = pd.read_csv(url, skiprows=2) 
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# --- 🚀 4. 메인 화면 ---

FAMILY_IMAGE_BASE64 = """4SGoRXhpZgAATU0AKgAAAAgADAEPAAIAAAAGAAAAngEQAAIAAAAKAAAApAESAAMAAAABAAEAAAEaAAUAAAABAAAArgEbAAUAAAABAAAAtgEoAAMAAAABAAIAAAExAAIAAAAFAAAAvgEyAAIAAAAUAAAAxAE8AAIAAAAKAAAA2AITAAMAAAABAAEAAIdpAAQAAAABAAAA4oglAAQAAAABAAAJygAACwJBcHBsZQBpUGhvbmUgMTQAAAAASAAAAAEAAABIAAAAATE4LjUAADIwMjU6MDg6MjMgMTc6MzI6MjcAaVBob25lIDE0AAAjgpoABQAAAAEAAAKMgp0ABQAAAAEAAAKUiCIAAwAAAAEAAgAAiCcAAwAAAAEAMgAAkAAABwAAAAQwMjMykAMAAgAAABQAAAKckAQAAgAAABQAAAKwkBAAAgAAAAcAAALEkBEAAgAAAAcAAALMkBIAAgAAAAcAAALUkQEABwAAAAQBAgMAkgEACgAAAAEAAALckgIABQAAAAEAAALkkgMACgAAAAEAAALskgQACgAAAAEAAAL0kgcAAwAAAAEABQAAkgkAAwAAAAEAEAAAkgoABQAAAAEAAAL8knwABwAABnEAAAMEkpEAAgAAAAQ2NDAAkpIAAgAAAAQ2NDAAoAAABwAAAAQwMTAwoAEAAwAAAAH"""

if not df.empty:
    try: 
        if FAMILY_IMAGE_BASE64 != """4SGoRXhpZgAATU0AKgAAAAgADAEPAAIAAAAGAAAAngEQAAIAAAAKAAAApAESAAMAAAABAAEAAAEaAAUAAAABAAAArgEbAAUAAAABAAAAtgEoAAMAAAABAAIAAAExAAIAAAAFAAAAvgEyAAIAAAAUAAAAxAE8AAIAAAAKAAAA2AITAAMAAAABAAEAAIdpAAQAAAABAAAA4oglAAQAAAABAAAJygAACwJBcHBsZQBpUGhvbmUgMTQAAAAASAAAAAEAAABIAAAAATE4LjUAADIwMjU6MDg6MjMgMTc6MzI6MjcAaVBob25lIDE0AAAjgpoABQAAAAEAAAKMgp0ABQAAAAEAAAKUiCIAAwAAAAEAAgAAiCcAAwAAAAEAMgAAkAAABwAAAAQwMjMykAMAAgAAABQAAAKckAQAAgAAABQAAAKwkBAAAgAAAAcAAALEkBEAAgAAAAcAAALMkBIAAgAAAAcAAALUkQEABwAAAAQBAgMAkgEACgAAAAEAAALckgIABQAAAAEAAALkkgMACgAAAAEAAALskgQACgAAAAEAAAL0kgcAAwAAAAEABQAAkgkAAwAAAAEAEAAAkgoABQAAAAEAAAL8knwABwAABnEAAAMEkpEAAgAAAAQ2NDAAkpIAAgAAAAQ2NDAAoAAABwAAAAQwMTAwoAEAAwAAAAH""":
            st.image(f"data:image/jpeg;base64,{FAMILY_IMAGE_BASE64}", use_container_width=True)
        else:
            # 텍스트가 없으면 원래 하던 대로 사진 파일을 찾습니다.
            st.image("family_photo.jpg", use_container_width=True)
    except Exception as e:
        st.error(f"🚨 이미지 에러 발생: {e}")

    # --- 🔄 제목 및 새로고침 버튼 레이아웃 ---
    head_col1, head_col2 = st.columns([0.85, 0.15])
    with head_col1:
        st.markdown('<p class="main-title">🏠 Family Asset Monitor</p>', unsafe_allow_html=True)
    with head_col2:
        if st.button("🔄Update now"):
            st.cache_data.clear()
            with st.spinner(""):
                time.sleep(0.5)
                st.rerun()
    
    net_worth = df['금액'].sum()
    total_assets = df[df['금액'] > 0]['금액'].sum()
    total_debts = df[df['금액'] < 0]['금액'].sum()

    # --- 📈 이번 달 실시간 성적표(Delta) 계산 ---
    prev_net_worth = 0
    delta_val = 0
    
    if HISTORY_GID: # Secrets에 HISTORY_GID가 제대로 입력되어 있어야만 작동!
        history_df = load_history_data(HISTORY_GID)
        
        if not history_df.empty:
            current_month = datetime.datetime.now().month
            prev_month = current_month - 1
            
            # 현재가 3월이면 "2월" 열을 찾음 (만약 1월이면 일단 1월을 참조하도록 방어)
            target_col_name = f"{prev_month}월" if prev_month > 0 else "1월"
            
            # '순자산'이라는 단어가 포함된 행(row)을 찾음
            target_row = history_df[history_df.apply(lambda row: row.astype(str).str.contains('순자산').any(), axis=1)]
            
            if not target_row.empty and target_col_name in history_df.columns:
                val_str = str(target_row[target_col_name].values[0])
                # 숫자 외의 문자(콤마, 원 등) 제거
                val_clean = val_str.replace(',', '').replace('₩', '').replace('원', '').strip()
                prev_net_worth = pd.to_numeric(val_clean, errors='coerce')
                
                if pd.isna(prev_net_worth): 
                    prev_net_worth = 0
            
            if prev_net_worth > 0:
                delta_val = net_worth - prev_net_worth
    # ---------------------------------------------

    main_tab1, main_tab2 = st.tabs(["📊 현재 자산 현황", "🚀 목표 및 AI 분석"])

    # ==========================================
    # 탭 1. 기존 대시보드 화면 
    # ==========================================
    with main_tab1:
        st.markdown("<div id='summary'></div>", unsafe_allow_html=True)
        show_assets = st.toggle("👀 금액 상세 보기", value=False)
        col1, col2, col3 = st.columns(3)
        if show_assets:
            # 💡 순자산 메트릭에 delta(변동폭) 적용!
            delta_text = f"{delta_val/10000:,.0f}만 (이번달 실시간)" if delta_val != 0 else None
            col1.metric("💎 순자산", format_krw(net_worth), delta=delta_text)
            
            col2.metric("💰 총 자산", format_krw(total_assets))
            col3.metric("💸 총 부채", format_krw(total_debts))
        else:
            col1.metric("💎 순자산", "👆 토글 켜기")
            col2.metric("💰 총 자산", "👆 토글 켜기")
            col3.metric("💸 총 부채", "👆 토글 켜기")
            
        st.divider()

        st.markdown("<div id='charts'></div>", unsafe_allow_html=True)
        st.subheader("📊 포트폴리오 구성")

        def draw_section(data, col):
            if data.empty or data['금액'].abs().sum() == 0: return st.info("데이터가 없습니다.")
            plot_df = data.copy()
            plot_df['금액'] = plot_df['금액'].abs()
            grouped = plot_df.groupby(['구성원', col], as_index=False)['금액'].sum()
            
            fig1 = px.pie(grouped, values='금액', names=col, hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig1.update_traces(textinfo='label+percent', textposition='inside', textfont_size=10)
            fig1.update_layout(height=280, margin=dict(t=20, b=20, l=10, r=10), showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig1, use_container_width=True)
            
            grouped['멤버총합'] = grouped.groupby('구성원')['금액'].transform('sum')
            grouped['비중'] = grouped.apply(lambda x: round((x['금액']/x['멤버총합']*100), 1) if x['멤버총합'] > 0 else 0, axis=1)
            grouped['라벨'] = grouped[col] + " " + grouped['비중'].astype(str) + "%"
            
            fig2 = px.bar(grouped, y='구성원', x='금액', color=col, orientation='h', text='라벨', color_discrete_sequence=px.colors.qualitative.Pastel)
            fig2.update_layout(height=180, barmode='stack', barnorm='percent', margin=dict(t=10, b=10, l=10, r=10), showlegend=False, xaxis=dict(showticklabels=False), yaxis_title=None, paper_bgcolor='rgba(0,0,0,0)')
            fig2.update_traces(textposition='inside', textfont_size=10)
            st.plotly_chart(fig2, use_container_width=True)

        tab_sub1, tab_sub2, tab_sub3 = st.tabs(["💸 금융", "🏠 부동산", "📦 기타"])
        with tab_sub1: draw_section(df[~df['대분류'].isin(['부동산', '기타', '부채'])], '대분류')
        with tab_sub2: draw_section(df[df['대분류'].isin(['부동산', '부채'])], '소분류')
        with tab_sub3: draw_section(df[df['대분류'] == '기타'], '소분류')

        st.markdown("<div id='table'></div>", unsafe_allow_html=True)
        st.subheader("📋 구성원별 상세")

        def style_total(row):
            if row['대분류'] == '💡 합계': return ['background-color: rgba(130, 130, 130, 0.2); font-weight: bold;'] * len(row)
            return [''] * len(row)

        m_list = ['전체'] + list(df['구성원'].unique())
        tabs_table = st.tabs([f"👤 {m}" for m in m_list])
        for i, t in enumerate(tabs_table):
            with t:
                target = df.copy() if m_list[i] == '전체' else df[df['구성원'] == m_list[i]].copy()
                total_row = pd.DataFrame([{'대분류': '💡 합계', '소분류': '총 순자산', '금액': target['금액'].sum()}])
                res_df = pd.concat([total_row, target[['대분류', '소분류', '금액']]], ignore_index=True)
                st.dataframe(res_df.style.apply(style_total, axis=1).format({"금액": "{:,.0f}"}), use_container_width=True, hide_index=True)
        st.write("<br><br><br>", unsafe_allow_html=True)

    # ==========================================
    # 탭 2. 새로운 목표 설정 및 찐! AI 피드백
    # ==========================================
    with main_tab2:
        st.subheader("🎯 우리의 재무 목표")
        
        target_eok = st.number_input("목표 순자산 (단위: 억원)", min_value=1, value=30, step=1)
        target_amount = target_eok * 100000000
        
        remaining = target_amount - net_worth
        progress_ratio = max(0.0, min(net_worth / target_amount, 1.0))
        
        st.markdown("<br>", unsafe_allow_html=True)
        if remaining > 0:
            st.markdown(f'<div class="goal-text">🔥 경제적 자유 {target_eok}억 까지!<br>앞으로 {format_krw(remaining)} 남았습니다.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="goal-text">🎉 축하합니다!<br>목표하신 경제적 자유 {target_eok}억을 돌파했습니다!</div>', unsafe_allow_html=True)
            
        st.progress(progress_ratio)
        st.caption(f"현재 달성률: {progress_ratio * 100:.1f}%")
        
        st.divider()
        st.subheader("🤖 AI 재무 비서 피드백")

        if not GEMINI_API_KEY:
            st.warning("스트림릿 Secrets에 `GEMINI_API_KEY`를 설정하면 AI의 분석을 받을 수 있습니다!")
        else:
            if st.button("✨ 제미나이에게 현재 자산 분석 맡기기"):
                with st.spinner("자산 포트폴리오를 꼼꼼히 분석하고 있습니다..."):
                    try:
                        asset_summary = df.groupby('대분류')['금액'].sum().to_dict()
                        prompt = f"""
                        당신은 우리 가족의 전속 프라이빗 뱅커(PB)입니다. 아래의 실시간 자산 데이터를 바탕으로, 모바일 화면에서 읽기 쉽도록 줄바꿈을 적극적으로 활용하여 구체적이고 전문적인 분석 리포트를 작성해 주세요.

                        [현재 가족 자산 현황]
                        - 총 자산: {total_assets:,}원
                        - 총 부채: {abs(total_debts):,}원
                        - 순자산: {net_worth:,}원
                        - 자산 구성(대분류별): {asset_summary}
                        - 현재 경제적 자유 목표: {target_eok}억원

                        [출력 형식 가이드라인]
                        반드시 아래의 3가지 섹션으로 나누고, 각 섹션마다 줄바꿈(엔터)을 2번씩 넣어 단락을 확실히 구분해 주세요.

                        1. 📊 현재 재무 상태 요약
                        (순자산과 부채 비율을 바탕으로 현재의 건전성을 2~3문장으로 평가)

                        2. 🔍 포트폴리오 정밀 분석
                        (자산 구성 데이터를 보고, 특정 자산에 치우쳐 있는지, 위험도나 유동성은 어떤지 구체적으로 분석)

                        3. 💡 목표 달성을 위한 액션 플랜
                        ({target_eok}억 목표 달성을 위해 지금 당장 가족이 실천해야 할 구체적인 조언 2가지)
                        
                        *주의: 친절하고 격려하는 톤을 유지하되, 마크다운(볼드체)과 이모지를 적절히 사용하여 가독성을 극대화하세요.*
                        """
                        
                        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        chosen_model = next((m for m in valid_models if 'flash' in m), valid_models[0])
                        
                        model = genai.GenerativeModel(chosen_model)
                        response = model.generate_content(prompt)
                        
                        st.success("분석이 완료되었습니다!")
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"API 호출 중 문제가 발생했습니다: {e}")
            
        st.write("<br><br><br>", unsafe_allow_html=True)


