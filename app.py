import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="가족 자산 대시보드", layout="centered")

# --- 🎨 1. CSS (디자인 설정: 여기에 사진 모서리 곡선 추가) ---
st.markdown("""
<style>
    /* 📸 사진 모서리 둥글게 디자인 추가 */
    img {
        border-radius: 20px;
        margin-bottom: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    
    div[data-testid="metric-container"] { background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 8px 4px !important; border-radius: 12px; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); }
    @media (prefers-color-scheme: dark) {
        div[data-testid="metric-container"] { background-color: #262730 !important; border: 1px solid #414141 !important; }
        [data-testid="stMetricValue"] { color: #ffffff !important; }
        [data-testid="stMetricLabel"] { color: #aaaaaa !important; }
        .floating-nav { background-color: rgba(38, 39, 48, 0.95) !important; border: 1px solid #444 !important; }
        .floating-nav a { color: #ffffff !important; }
    }
    [data-testid="stMetricValue"] { font-size: 0.95rem !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; }
    .floating-nav {
        position: fixed; bottom: 15px; left: 50%; transform: translateX(-50%);
        background-color: rgba(255, 255, 255, 0.95); backdrop-filter: blur(8px); padding: 8px 18px; border-radius: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); display: flex; gap: 15px; z-index: 1000; border: 1px solid #eee;
    }
    .floating-nav a { text-decoration: none; color: #555; font-size: 0.8rem; font-weight: 600; }
    html { scroll-behavior: smooth; }
</style>
<div class="floating-nav">
    <a href="#summary">💰 요약</a> <a href="#charts">📊 구성</a> <a href="#table">📋 상세</a>
</div>
""", unsafe_allow_html=True)

# --- 🔑 2. Secrets 및 도구 (기존과 동일) ---
try:
    SHEET_ID = st.secrets["SHEET_ID"].strip()
    SHEET_GID = st.secrets["SHEET_GID"].strip()
except:
    st.error("❌ Secrets 설정 확인 필요")
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
        st.error(f"❌ 데이터 로드 실패: {e}")
        return pd.DataFrame()

df = load_data()

# --- 🚀 3. 화면 렌더링 (여기에 사진 위치!) ---
if not df.empty:
    st.markdown("<div id='summary'></div>", unsafe_allow_html=True)
    
    # ⭐ [family_photo.jpg]
    # 깃허브에 올린 파일명과 똑같이 써주세요. 
    # 가로로 긴(21:9) 사진을 올리시면 아주 예쁘게 나옵니다.
    try:
        st.image("family_photo.jpg", use_container_width=True)
    except:
        pass # 사진이 아직 업로드 전이면 그냥 넘어갑니다.

    st.title("👨‍👩‍👧 꼬뇽부부 2026")
    st.caption("화이팅! 잘하고 있다!")
    
    # (이하 요약/차트/상세표 코드는 동일합니다...)
    net_worth = df['금액'].sum()
    total_assets = df[df['금액'] > 0]['금액'].sum()
    total_debts = df[df['금액'] < 0]['금액'].sum()

    show_assets = st.toggle("👀 숨겨진 금액 확인하기", value=False)
    col1, col2, col3 = st.columns(3)
    
    if show_assets:
        col1.metric("💎 순자산", format_krw(net_worth))
        col2.metric("💰 총 자산", format_krw(total_assets))
        col3.metric("💸 총 부채", format_krw(total_debts))
    else:
        col1.metric("💎 순자산", "👆 클릭해서 확인!")
        col2.metric("💰 총 자산", "👆 클릭해서 확인!")
        col3.metric("💸 총 부채", "👆 클릭해서 확인!")
        
    st.divider()

    st.markdown("<div id='charts'></div>", unsafe_allow_html=True)
    st.subheader("📊 포트폴리오 구성")

    def draw_section(data, col):
        if data.empty or data['금액'].abs().sum() == 0: return st.info("데이터가 없습니다.")
        plot_df = data.copy()
        plot_df['금액'] = plot_df['금액'].abs()
        grouped = plot_df.groupby(['구성원', col], as_index=False)['금액'].sum()
        
        fig1 = px.pie(grouped, values='금액', names=col, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig1.update_layout(margin=dict(t=5, b=5, l=5, r=5), showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig1, use_container_width=True)
        
        grouped['멤버총합'] = grouped.groupby('구성원')['금액'].transform('sum')
        grouped['비중'] = grouped.apply(lambda x: round((x['금액']/x['멤버총합']*100), 1) if x['멤버총합'] > 0 else 0, axis=1)
        grouped['라벨'] = grouped[col] + " " + grouped['비중'].astype(str) + "%"
        
        fig2 = px.bar(grouped, y='구성원', x='금액', color=col, orientation='h', text='라벨', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_layout(barmode='stack', barnorm='percent', margin=dict(t=5, b=5, l=5, r=5), showlegend=False, xaxis=dict(showticklabels=False), yaxis_title=None, paper_bgcolor='rgba(0,0,0,0)')
        fig2.update_traces(textposition='inside')
        st.plotly_chart(fig2, use_container_width=True)

    tab1, tab2, tab3 = st.tabs(["💸 금융", "🏠 부동산/부채", "📦 기타"])
    with tab1: draw_section(df[~df['대분류'].isin(['부동산', '기타', '부채'])], '대분류')
    with tab2: draw_section(df[df['대분류'].isin(['부동산', '부채'])], '소분류')
    with tab3: draw_section(df[df['대분류'] == '기타'], '소분류')

    st.markdown("<div id='table'></div>", unsafe_allow_html=True)
    st.subheader("📋 구성원별 자산 상세")

    def style_total(row):
        return ['background-color: #1d4ed8; color: #ffffff; font-weight: bold'] * len(row) if row['구성원'] == '💡 합계' else [''] * len(row)

    m_list = ['전체'] + list(df['구성원'].unique())
    tabs = st.tabs([f"👤 {m}" for m in m_list])
    for i, tab in enumerate(tabs):
        with tab:
            target = df.copy() if m_list[i] == '전체' else df[df['구성원'] == m_list[i]].copy()
            res_df = pd.concat([pd.DataFrame([{'구성원': '💡 합계', '대분류': '-', '소분류': '총 순자산', '금액': target['금액'].sum()}]), target], ignore_index=True)
            st.dataframe(res_df.style.apply(style_total, axis=1).format({"금액": "{:,.0f}"}), use_container_width=True, hide_index=True)

    st.write("<br><br><br>", unsafe_allow_html=True)
