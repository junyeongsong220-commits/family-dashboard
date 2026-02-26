import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 화면 설정
st.set_page_config(page_title="꼬뇽부부 자산 현황", layout="centered")

# (중략: 기존 CSS는 동일)

# --- 🔑 Secrets 로드 ---
try:
    SHEET_ID = st.secrets["SHEET_ID"]
    SHEET_GID = st.secrets["SHEET_GID"]
except:
    st.error("❌ Streamlit Secrets 설정에서 SHEET_ID와 SHEET_GID를 확인해주세요!")
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

# --- 2. 데이터 로드 (오직 구글 시트에서만!) ---
@st.cache_data(ttl=60)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
    try:
        df = pd.read_csv(url)
        # 금액 숫자로 변환
        df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        # 부채 처리
        df.loc[df['대분류'] == '부채', '금액'] = df.loc[df['대분류'] == '부채', '금액'].abs() * -1
        return df
    except Exception as e:
        st.error(f"⚠️ 구글 시트 로드 실패: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. 화면 렌더링 ---
if df.empty:
    st.warning("데이터가 비어있습니다. 구글 시트 공유 설정과 ID를 확인하세요.")
else:
    # (중략: 요약 지표 출력)
    net_worth = df['금액'].sum()
    total_assets = df[df['금액'] > 0]['금액'].sum()
    total_debts = df[df['금액'] < 0]['금액'].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("💎 순자산", format_krw(net_worth))
    col2.metric("💰 총 자산", format_krw(total_assets))
    col3.metric("💸 총 부채", format_krw(total_debts))

# --- 4. 차트 함수 (ZeroDivision 방지 완벽 보강) ---
def draw_section(data, col):
    if data.empty or data['금액'].abs().sum() == 0:
        return st.info("데이터가 없습니다.")
    
    plot_df = data.copy()
    plot_df['금액'] = plot_df['금액'].abs()
    grouped = plot_df.groupby(['구성원', col], as_index=False)['금액'].sum()
    
    # 도넛
    fig1 = px.pie(grouped, values='금액', names=col, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig1.update_layout(margin=dict(t=5, b=5, l=5, r=5), showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig1, use_container_width=True)
    
    # 100% 바 (안전한 계산)
    grouped['멤버총합'] = grouped.groupby('구성원')['금액'].transform('sum')
    grouped['비중'] = grouped.apply(lambda x: (x['금액']/x['멤버총합']*100).round(1) if x['멤버총합'] > 0 else 0, axis=1)
    grouped['라벨'] = grouped[col] + " " + grouped['비중'].astype(str) + "%"
    
    fig2 = px.bar(grouped, y='구성원', x='금액', color=col, orientation='h', text='라벨', color_discrete_sequence=px.colors.qualitative.Pastel)
    fig2.update_layout(barmode='stack', barnorm='percent', margin=dict(t=5, b=5, l=5, r=5), showlegend=False, xaxis=dict(showticklabels=False), yaxis_title=None, paper_bgcolor='rgba(0,0,0,0)')
    fig2.update_traces(textposition='inside')
    st.plotly_chart(fig2, use_container_width=True)

# (이후 탭 및 상세표 코드는 기존과 동일)
