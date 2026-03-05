import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import time
import datetime
import pytz # 👈 시간 계산을 위해 추가

# 1. 페이지 설정
st.set_page_config(page_title="가족 자산 대시보드", layout="centered")

# --- 🎨 2. CSS (기존 스타일 유지) ---
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

# 💡 오류 수정 부분: 마지막 업데이트 시간을 G1 셀에서 정확하게 가져오는 함수
@st.cache_data(ttl=60)
def get_last_update_info():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
    try:
        # header=None으로 읽어야 1행의 G1(시간) 데이터를 열 이름으로 무시하지 않습니다.
        # nrows=1로 첫 줄만 빠르게 가져옵니다.
        df_time = pd.read_csv(url, header=None, nrows=1)
        
        # G1 셀은 0번 행의 6번 열입니다 (A=0, B=1, C=2, D=3, E=4, F=5, G=6)
        if df_time.shape[1] > 6:
            val = str(df_time.iloc[0, 6]).strip()
            # 값이 'nan'이 아니고 날짜 형식(최소 10자 이상)인 경우만 반환
            if val.lower() != 'nan' and len(val) >= 10:
                return val
        return None
    except:
        return None

@st.cache_data(ttl=60)
def load_history_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url, skiprows=2) 
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()
last_update_str = get_last_update_info() # 시간 데이터 가져오기

# --- 🚀 4. 메인 화면 ---

FAMILY_IMAGE_BASE64 = """4SGoRXhpZgAATU0AKgAAAAgADAEPAAIAAAAGAAAAngEQAAIAAAAKAAAApAESAAMAAAABAAEAAAEaAAUAAAABAAAArgEbAAUAAAABAAAAtgEoAAMAAAABAAIAAAExAAIAAAAFAAAAvgEyAAIAAAAUAAAAxAE8AAIAAAAKAAAA2AITAAMAAAABAAEAAIdpAAQAAAABAAAA4oglAAQAAAABAAAJygAACwJBcHBsZQBpUGhvbmUgMTQAAAAASAAAAAEAAABIAAAAATE4LjUAADIwMjU6MDg6MjMgMTc6MzI6MjcAaVBob25lIDE0AAAjgpoABQAAAAEAAAKMgp0ABQAAAAEAAAKUiCIAAwAAAAEAAgAAiCcAAwAAAAEAMgAAkAAABwAAAAQwMjMykAMAAgAAABQAAAKckAQAAgAAABQAAAKwkBAAAgAAAAcAAALEkBEAAgAAAAcAAALMkBIAAgAAAAcAAALUkQEABwAAAAQBAgMAkgEACgAAAAEAAALckgIABQAAAAEAAALkkgMACgAAAAEAAALskgQACgAAAAEAAAL0kgcAAwAAAAEABQAAkgkAAwAAAAEAEAAAkgoABQAAAAEAAAL8knwABwAABnEAAAMEkpEAAgAAAAQ2NDAAkpIAAgAAAAQ2NDAAoAAABwAAAAQwMTAwoAEAAwAAAAH"""

if not df.empty:
    try: 
        if FAMILY_IMAGE_BASE64 != """4SGoRXhpZgAATU0AKgAAAAgADAEPAAIAAAAGAAAAngEQAAIAAAAKAAAApAESAAMAAAABAAEAAAEaAAUAAAABAAAArgEbAAUAAAABAAAAtgEoAAMAAAABAAIAAAExAAIAAAAFAAAAvgEyAAIAAAAUAAAAxAE8AAIAAAAKAAAA2AITAAMAAAABAAEAAIdpAAQAAAABAAAA4oglAAQAAAABAAAJygAACwJBcHBsZQBpUGhvbmUgMTQAAAAASAAAAAEAAABIAAAAATE4LjUAADIwMjU6MDg6MjMgMTc6MzI6MjcAaVBob25lIDE0AAAjgpoABQAAAAEAAAKMgp0ABQAAAAEAAAKUiCIAAwAAAAEAAgAAiCcAAwAAAAEAMgAAkAAABwAAAAQwMjMykAMAAgAAABQAAAKckAQAAgAAABQAAAKwkBAAAgAAAAcAAALEkBEAAgAAAAcAAALMkBIAAgAAAAcAAALUkQEABwAAAAQBAgMAkgEACgAAAAEAAALckgIABQAAAAEAAALkkgMACgAAAAEAAALskgQACgAAAAEAAAL0kgcAAwAAAAEABQAAkgkAAwAAAAEAEAAAkgoABQAAAAEAAAL8knwABwAABnEAAAMEkpEAAgAAAAQ2NDAAkpIAAgAAAAQ2NDAAoAAABwAAAAQwMTAwoAEAAwAAAAH""":
            st.image(f"data:image/jpeg;base64,{FAMILY_IMAGE_BASE64}", use_container_width=True)
        else:
            st.image("family_photo.jpg", use_container_width=True)
    except Exception as e:
        st.error(f"🚨 이미지 에러 발생: {e}")

    # --- 🔄 제목 및 상태 표시 레이아웃 ---
    head_col1, head_col2, head_col3 = st.columns([0.55, 0.3, 0.15])
    
    with head_col1:
        st.markdown('<p class="main-title">🏠 Family Asset Monitor</p>', unsafe_allow_html=True)
    
    with head_col2:
        # 💡 "몇 분 전 업데이트" 계산 로직
        status_text = "확인 불가"
        delta_color = "off"
        
        if last_update_str:
            try:
                kst = pytz.timezone('Asia/Seoul')
                now_kst = datetime.datetime.now(kst)
                # 시트에서 가져온 시간을 날짜 객체로 변환
                last_update_dt = kst.localize(datetime.datetime.strptime(last_update_str, '%Y-%m-%d %H:%M:%S'))
                
                diff_min = int((now_kst - last_update_dt).total_seconds() // 60)
                
                if diff_min < 1: status_text = "방금 전"
                elif diff_min < 60: status_text = f"{diff_min}분 전"
                else: status_text = f"{diff_min // 60}시간 전"
                
                delta_color = "normal" if diff_min < 70 else "inverse" # 1시간 넘게 업데이트 안되면 색상 변경
            except:
                pass
        
        st.metric(label="업데이트 상태", value=status_text, delta="LIVE", delta_color=delta_color)

    with head_col3:
        if st.button("🔄"):
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
    
    if HISTORY_GID:
        history_df = load_history_data(HISTORY_GID)
        if not history_df.empty:
            current_month = datetime.datetime.now().month
            prev_month = current_month - 1
            target_col_name = f"{prev_month}월" if prev_month > 0 else "1월"
            target_row = history_df[history_df.apply(lambda row: row.astype(str).str.contains('순자산').any(), axis=1)]
            
            if not target_row.empty and target_col_name in history_df.columns:
                val_str = str(target_row[target_col_name].values[0])
                val_clean = val_str.replace(',', '').replace('₩', '').replace('원', '').strip()
                prev_net_worth = pd.to_numeric(val_clean, errors='coerce')
                if pd.isna(prev_net_worth): prev_net_worth = 0
            
            if prev_net_worth > 0:
                delta_val = net_worth - prev_net_worth

    main_tab1, main_tab2 = st.tabs(["📊 현재 자산 현황", "🚀 목표 및 AI 분석"])

    with main_tab1:
        st.markdown("<div id='summary'></div>", unsafe_allow_html=True)
        show_assets = st.toggle("👀 금액 상세 보기", value=False)
        col1, col2, col3 = st.columns(3)
        if show_assets:
            delta_text = f"{delta_val/10000:,.0f}만 (전월 대비)" if delta_val != 0 else None
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
                        당신은 우리 가족의 전속 프라이빗 뱅커(PB)입니다. 아래의 실시간 자산 데이터를 바탕으로 분석 리포트를 작성해 주세요.
                        [데이터] 총자산 {total_assets:,}원, 부채 {abs(total_debts):,}원, 순자산 {net_worth:,}원. 목표 {target_eok}억.
                        """
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(prompt)
                        st.success("분석이 완료되었습니다!")
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"API 호출 중 문제가 발생했습니다: {e}")
            
        st.write("<br><br><br>", unsafe_allow_html=True)
