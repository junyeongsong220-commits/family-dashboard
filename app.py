import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="가족 자산 대시보드", layout="centered")

# --- 🎨 2. CSS (여백 및 컴팩트 디자인) ---
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    header { visibility: hidden; height: 0px; }
    
    img {
        border-radius: 20px;
        margin-bottom: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    .main-title {
        font-size: 1.4rem !important;
        font-weight: 800;
        margin-bottom: 2px;
        color: #31333F;
    }
    @media (prefers-color-scheme: dark) { .main-title { color: #ffffff; } }

    div[data-testid="metric-container"] { 
        background-color: #f8f9fa; 
        border: 1px solid #e9ecef; 
        padding: 8px 4px !important; 
        border-radius: 12px; 
    }
    
    @media (prefers-color-scheme: dark) {
        div[data-testid="metric-container"] { background-color: #262730 !important; border: 1px solid #414141 !important; }
    }

    [data-testid="stMetricValue"] { font-size: 0.95rem !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; }

    /* 하단 네비게이션 */
    .floating-nav {
        position: fixed; bottom: 15px; left: 50%; transform: translateX(-50%);
        background-color: rgba(255, 255, 255, 0.95); backdrop-filter: blur(8px); padding: 8px 18px; border-radius: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); display: flex; gap: 15px; z-index: 1000; border: 1px solid #eee;
    }
    .floating-nav a { text-decoration: none; color: #555; font-size: 0.8rem; font-weight: 600; }
</style>
<div class="floating-nav">
    <a href="#summary">💰 요약</a> <a href="#charts">📊 구성</a> <a href="#table">📋 상세</a>
</div>
""", unsafe_allow_html=True)

# --- 🔑 3. 데이터 로직 ---
try:
    SHEET_ID = st.secrets["SHEET_ID"].strip()
    SHEET_GID = st.secrets["SHEET_GID"].strip()
except:
    st.error("Secrets 설정을 확인해주세요!")
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
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

df = load_data()

# --- 🚀 4. 메인 화면 ---
if not df.empty:
    st.markdown("<div id='summary'></div>", unsafe_allow_html=True)
    try:
        st.image("family_photo.jpg", use_container_width=True)
    except:
        pass

    st.markdown('<p class="main-title">👨‍👩‍👧 Family Asset Monitor</p>', unsafe_allow_html=True)
    
    net_worth = df['금액'].sum()
    total_assets = df[df['금액'] > 0]['금액'].sum()
    total_debts = df[df['금액'] < 0]['금액'].sum()

    show_assets = st.toggle("👀 금액 보기", value=False)
    col1, col2, col3 = st.columns(3)
    if show_assets:
        col1.metric("💎 순자산", format_krw(net_worth))
        col2.metric("💰 총 자산", format_krw(total_assets))
        col3.metric("💸 총 부채", format_krw(total_debts))
    else:
        col1.metric("💎 순자산", "👆 클릭")
        col2.metric("💰 총 자산", "👆 클릭")
        col3.metric("💸 총 부채", "👆 클릭")
        
    st.divider()

    # --- 📊 5. 차트 섹션 (크기 및 레이블 수정) ---
    st.markdown("<div id='charts'></div>", unsafe_allow_html=True)
    st.subheader("📊 포트폴리오 구성")

    def draw_section(data, col):
        if data.empty or data['금액'].abs().sum() == 0:
            return st.info("데이터가 없습니다.")
        
        plot_df = data.copy()
        plot_df['금액'] = plot_df['금액'].abs()
        grouped = plot_df.groupby(['구성원', col], as_index=False)['금액'].sum()
        
        # 1. 도넛 차트 수정 (레이블+퍼센트 표시 및 높이 축소)
        fig1 = px.pie(grouped, values='금액', names=col, hole=0.5, 
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig1.update_traces(textinfo='label+percent', textposition='inside', textfont_size=10)
        fig1.update_layout(
            height=280, # 높이를 280으로 축소 (기본 약 450)
            margin=dict(t=20, b=20, l=10, r=10), 
            showlegend=False, 
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        # 2. 바 차트 수정 (높이 축소)
        grouped['멤버총합'] = grouped.groupby('구성원')['금액'].transform('sum')
        grouped['비중'] = grouped.apply(lambda x: round((x['금액']/x['멤버총합']*100), 1) if x['멤버총합'] > 0 else 0, axis=1)
        grouped['라벨'] = grouped[col] + " " + grouped['비중'].astype(str) + "%"
        
        fig2 = px.bar(grouped, y='구성원', x='금액', color=col, orientation='h', 
                     text='라벨', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_layout(
            height=180, # 높이를 180으로 축소
            barmode='stack', barnorm='percent', 
            margin=dict(t=10, b=10, l=10, r=10), 
            showlegend=False, 
            xaxis=dict(showticklabels=False), 
            yaxis_title=None, 
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig2.update_traces(textposition='inside', textfont_size=10)
        st.plotly_chart(fig2, use_container_width=True)

    tab1, tab2, tab3 = st.tabs(["💸 금융", "🏠 부동산", "📦 기타"])
    with tab1: draw_section(df[~df['대분류'].isin(['부동산', '기타', '부채'])], '대분류')
    with tab2: draw_section(df[df['대분류'].isin(['부동산', '부채'])], '소분류')
    with tab3: draw_section(df[df['대분류'] == '기타'], '소분류')

    # --- 📋 6. 상세 내역 ---
    st.markdown("<div id='table'></div>", unsafe_allow_html=True)
    st.subheader("📋 구성원별 상세")

    m_list = ['전체'] + list(df['구성원'].unique())
    tabs = st.tabs([f"👤 {m}" for m in m_list])
    for i, tab in enumerate(tabs):
        with tab:
            target = df.copy() if m_list[i] == '전체' else df[df['구성원'] == m_list[i]].copy()
            st.dataframe(target[['대분류', '소분류', '금액']].style.format({"금액": "{:,.0f}"}), 
                         use_container_width=True, hide_index=True)

    st.write("<br><br><br>", unsafe_allow_html=True)
