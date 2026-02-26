import streamlit as st
import pandas as pd
import plotly.express as px
import pyupbit

# 1. 화면 기본 설정
st.set_page_config(page_title="가족 자산 대시보드", layout="centered")

# --- 🎨 디자인 및 다크모드 대응 CSS ---
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 8px 4px !important;
        border-radius: 12px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
    }
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
        background-color: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(8px); padding: 8px 18px; border-radius: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); display: flex; gap: 15px; z-index: 1000; border: 1px solid #eee;
    }
    .floating-nav a { text-decoration: none; color: #555; font-size: 0.8rem; font-weight: 600; }
    html { scroll-behavior: smooth; }
</style>
<div class="floating-nav">
    <a href="#summary">💰 요약</a> <a href="#charts">📊 구성</a> <a href="#table">📋 상세</a>
</div>
""", unsafe_allow_html=True)

# --- 🔑 24시간 가동을 위한 클라우드 비밀 금고(Secrets) 로드 ---
# 배포 후 스트림릿 설정 창에 입력할 변수명들입니다.
MY_ACCESS = st.secrets["MY_ACCESS"]
MY_SECRET = st.secrets["MY_SECRET"]
WIFE_ACCESS = st.secrets["WIFE_ACCESS"]
WIFE_SECRET = st.secrets["WIFE_SECRET"]
SHEET_ID = st.secrets["SHEET_ID"]
SHEET_GID = st.secrets["SHEET_GID"]

KEYS = {
    "준영": {"access": MY_ACCESS, "secret": MY_SECRET},
    "고은": {"access": WIFE_ACCESS, "secret": WIFE_SECRET}
}

def format_krw(amount):
    is_negative = amount < 0
    amount = abs(amount)
    if amount == 0: return "0 원"
    eok = int(amount // 100000000) 
    man = int((amount % 100000000) // 10000) 
    result = ""
    if eok > 0: result += f"{eok}억 "
    if man > 0: result += f"{man:,}만"
    final_str = result.strip() + " 원"
    return f"-{final_str}" if is_negative else final_str

# --- 2. 실시간 데이터 통합 로드 (구글 시트 + 업비트) ---
@st.cache_data(ttl=300) # 5분간 데이터를 캐시하여 구글 시트 과부하 방지
def load_data():
    # 1. 구글 시트 직접 조회 (클라우드 환경에선 collector.py가 없으므로 직접 읽음)
    sheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
    try:
        df_sheet = pd.read_csv(sheet_url)
        df_sheet['금액'] = pd.to_numeric(df_sheet['금액'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    except:
        df_sheet = pd.DataFrame(columns=["구성원", "대분류", "소분류", "금액"])

    # 2. 업비트 실시간 조회
    coin_list = []
    for name, key in KEYS.items():
        try:
            upbit = pyupbit.Upbit(key['access'], key['secret'])
            balances = upbit.get_balances()
            total = sum([float(b['balance']) * (pyupbit.get_current_price("KRW-"+b['currency']) if b['currency'] != "KRW" else 1) for b in balances])
            coin_list.append({"구성원": name, "대분류": "가상화폐", "소분류": "업비트(실시간)", "금액": total})
        except:
            coin_list.append({"구성원": name, "대분류": "가상화폐", "소분류": "업비트(오류)", "금액": 0})
    
    df_combined = pd.concat([df_sheet, pd.DataFrame(coin_list)], ignore_index=True)
    df_combined.loc[df_combined['대분류'] == '부채', '금액'] = df_combined.loc[df_combined['대분류'] == '부채', '금액'].abs() * -1
    return df_combined

df = load_data()

# --- 3. 화면 렌더링 (요약/차트/표 - 기존과 동일) ---
st.markdown("<div id='summary'></div>", unsafe_allow_html=True)
st.title("👨‍👩‍👧 가족 통합 자산 대시보드")
st.caption("새로고침 시 실시간 시세가 반영됩니다.")

total_assets = df[df['금액'] > 0]['금액'].sum()
total_debts = df[df['금액'] < 0]['금액'].sum()
net_worth = total_assets + total_debts

col1, col2, col3 = st.columns(3)
col1.metric("💎 순자산", format_krw(net_worth))
col2.metric("💰 총 자산", format_krw(total_assets))
col3.metric("💸 총 부채", format_krw(total_debts))
st.divider()

st.markdown("<div id='charts'></div>", unsafe_allow_html=True)
st.subheader("📊 포트폴리오 구성")

def draw_section(data, col):
    if data.empty: return st.info("데이터가 없습니다.")
    plot_df = data.copy()
    plot_df['금액'] = plot_df['금액'].abs()
    grouped = plot_df.groupby(['구성원', col], as_index=False)['금액'].sum()
    
    fig1 = px.pie(grouped, values='금액', names=col, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig1.update_layout(margin=dict(t=5, b=5, l=5, r=5), showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig1, use_container_width=True)
    
    grouped['비중'] = (grouped['금액'] / grouped.groupby('구성원')['금액'].transform('sum') * 100).round(1)
    grouped['라벨'] = grouped[col] + " " + grouped['비중'].astype(str) + "%"
    fig2 = px.bar(grouped, y='구성원', x='금액', color=col, orientation='h', text='라벨', color_discrete_sequence=px.colors.qualitative.Pastel)
    fig2.update_layout(barmode='stack', barnorm='percent', margin=dict(t=5, b=5, l=5, r=5), showlegend=False, xaxis=dict(showticklabels=False), yaxis_title=None, paper_bgcolor='rgba(0,0,0,0)')
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