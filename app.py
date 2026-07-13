import pandas as pd
import streamlit as st

from utils.planet3d import make_earth_figure, make_exoplanet_figure, make_planet_figure
from utils.similarity import EARTH, compute_overall_similarity

st.set_page_config(page_title="지구-외계행성 유사도 분석", page_icon="🪐", layout="wide")

# ----------------------------------------------------------------------------
# [인터넷 참조 데이터] 행성별 공인 ESI 지수 매칭 딕셔너리
# ----------------------------------------------------------------------------
REFERENCED_ESI = {
    "KOI-4878.01": 0.98, "TRAPPIST-1e": 0.95, "티가든 b": 0.95, "글리제 581 g": 0.92,
    "루이텐 b": 0.91, "TRAPPIST-1d": 0.91, "케플러-438b": 0.88, "센타우루스자리 프록시마 b": 0.87,
    "로스 128 b": 0.86, "LHS 1723 b": 0.86, "케플러-296 e": 0.85, "글리제 667 Cc": 0.85,
    "케플러-442b": 0.84, "케플러-452b": 0.83, "케플러-62e": 0.83, "글리제 832 c": 0.81,
    "케플러-283c": 0.79, "HD 85512 b": 0.77, "볼프 1061c": 0.76, "글리제 667 Cf": 0.76,
    "케플러-440b": 0.75, "HD 40307 g": 0.74, "화성": 0.73, "수성": 0.73,
    "케플러-61b": 0.73, "글리제 581 d": 0.72, "케플러-22b": 0.71, "케플러-443b": 0.71,
    "글리제 422 b": 0.71, "TRAPPIST-1 f": 0.70, "글리제 3293 c": 0.70, "케플러-62f": 0.69,
    "티가든 c": 0.68, "케플러-298d": 0.68, "캅테인 b": 0.67, "케플러-186f": 0.64,
    "케플러-174d": 0.61, "케플러-296f": 0.60, "글리제 667 Ce": 0.60, "HD 69830 d": 0.60,
    "TRAPPIST-1 g": 0.59, "글리제 682 c": 0.59, "게자리 55 c": 0.56, "달": 0.56,
    "게자리 55 f": 0.53, "KOI-4427b": 0.52, "글리제 581b": 0.48, "금성": 0.44,
    "케플러-20f": 0.44, "글리제 1214 b": 0.42, "케플러-11b": 0.30, "케플러-20e": 0.29,
    "제단자리 뮤 e": 0.27, "글리제 581 c": 0.24, "케플러-20b": 0.24, "해왕성": 0.18,
    "글리제 581 e": 0.16, "목성": 0.12, "KOI-55c": 0.03
}

# ----------------------------------------------------------------------------
# 다크 우주 테마 CSS (가독성 확보 스타일)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(1px 1px at 20px 30px, #ffffff55, transparent),
            radial-gradient(1px 1px at 90px 120px, #ffffff44, transparent),
            radial-gradient(1.5px 1.5px at 160px 60px, #ffffff66, transparent),
            radial-gradient(1px 1px at 230px 180px, #ffffff33, transparent),
            radial-gradient(2px 2px at 300px 40px, #ffffff55, transparent),
            radial-gradient(1px 1px at 340px 220px, #ffffff33, transparent),
            linear-gradient(180deg, #05070f 0%, #0A0E27 50%, #0d1230 100%);
        background-repeat: repeat;
        background-size: 380px 260px, 380px 260px, 380px 260px, 380px 260px, 380px 260px, 380px 260px, cover;
    }
    h1, h2, h3, h4 { color: #E8EAF6 !important; }
    
    .stApp div p, .stApp .stCaption, .stApp p {
        color: #C3CADB;
    }
    
    .stExpander {
        background-color: rgba(14, 19, 46, 0.7) !important;
        border: 1px solid #3A4680 !important;
        border-radius: 8px;
    }
    .stExpander details summary p {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    .stExpander details div[data-testid="stExpanderDetails"] p,
    .stExpander details div[data-testid="stExpanderDetails"] li,
    .stExpander details div[data-testid="stExpanderDetails"] {
        color: #F1F5F9 !important;
    }
    
    div[data-baseweb="popover"] div {
        background-color: #0F163A !important;
    }
    div[data-baseweb="popover"] div div {
        color: #FFFFFF !important; 
    }
    div[data-baseweb="popover"] ul li:hover {
        background-color: #1E295D !important;
    }
    
    .planet-select-box div[data-baseweb="select"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    .planet-select-box div[data-baseweb="select"] > div {
        background-color: transparent !important;
        justify-content: center !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #EAF0FF !important;
        cursor: pointer;
    }
    .planet-select-box div[data-baseweb="select"] [data-testid="InputRoot"] ~ div {
        display: none !important;
    }
    
    .similarity-box {
        background: linear-gradient(135deg, #141A3C, #1B2350);
        border: 1px solid #3A4680;
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        margin-top: 0.5rem;
    }
    .similarity-percent {
        font-size: 3rem;
        font-weight: 800;
        color: #7FE6B8 !important;
        text-shadow: 0 0 15px rgba(127, 230, 184, 0.4);
        margin-bottom: 0px;
    }
    .esi-value-label {
        font-size: 1.2rem;
        font-weight: 600;
        color: #93C5FD !important; 
        margin-top: -5px;
        margin-bottom: 10px;
    }
    
    .factor-table td, .factor-table th { color: #D6DCF5 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    df = pd.read_csv("data/exoplanets_template.csv")
    return df


df = load_data()
planets_df = df[df["planet_name"] != "Earth"].reset_index(drop=True)

n = len(planets_df)

st.title("🪐 지구-외계행성 유사도 분석")
st.caption("ESI(지구 유사도 지수) + 대기·항성·자전공전 등 추가 요소를 종합해 지구와 얼마나 닮았는지 계산합니다.")

if n == 0:
    st.warning("data/exoplanets_template.csv 에 행성 데이터를 채워주세요.")
    st.stop()

# ----------------------------------------------------------------------------
# 행성 탐색 (좌우 화살표 + 이름 클릭 토글)
# ----------------------------------------------------------------------------
if "idx" not in st.session_state:
    st.session_state.idx = 0

nav_col1, nav_col2, nav_col3 = st.columns([1, 6, 1])

with nav_col1:
    st.write("") 
    if st.button("◀", use_container_width=True, disabled=(n == 0)):
        st.session_state.idx = (st.session_state.idx - 1) % n
        st.rerun()

with nav_col3:
    st.write("")
    if st.button("▶", use_container_width=True, disabled=(n == 0)):
        st.session_state.idx = (st.session_state.idx + 1) % n
        st.rerun()

with nav_col2:
    st.markdown('<div class="planet-select-box">', unsafe_allow_html=True)
    
    planet_options = list(planets_df["planet_name"])
    selected_planet = st.selectbox(
        "행성 선택",
        options=planet_options,
        index=st.session_state.idx,
        label_visibility="collapsed"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if planet_options.index(selected_planet) != st.session_state.idx:
        st.session_state.idx = planet_options.index(selected_planet)
        st.rerun()

# 현재 선택된 행성 데이터
row = planets_df.iloc[st.session_state.idx]

# 이미지 및 설명 표시
with nav_col2:
    if isinstance(row.get("image_url"), str) and row["image_url"].strip():
        st.image(row["image_url"], use_container_width=True)
    if isinstance(row.get("description"), str) and row["description"].strip():
        st.caption(row["description"])

st.divider()

# ----------------------------------------------------------------------------
# 좌: 지구 3D / 우: 선택한 행성 3D
# ----------------------------------------------------------------------------
col_left, col_right = st.columns(2)
with col_left:
    st.plotly_chart(make_earth_figure(radius=1.0, title="지구 (Earth)"), use_container_width=True)
with col_right:
    st.plotly_chart(
        make_exoplanet_figure(row, title=str(row["planet_name"])),
        use_container_width=True,
    )

# ----------------------------------------------------------------------------
# 유사도 계산 및 표시 (딕셔너리에서 데이터 찾아오기 적용)
# ----------------------------------------------------------------------------
result = compute_overall_similarity(row)
planet_name_str = str(row["planet_name"]).strip()

st.markdown("<div class='similarity-box'>", unsafe_allow_html=True)
if result["overall"] is not None:
    # 1. 계산된 종합 유사도 퍼센티지
    st.markdown(f"<div class='similarity-percent'>{result['overall']*100:.1f}%</div>", unsafe_allow_html=True)
    
    # 2. 제공해주신 데이터에서 행성 이름을 찾아서 참조 ESI 지수 출력 (없으면 N/A)
    # 뒤에 붙은 별표(*) 유무에 유연하게 대응하기 위해 무조건 텍스트 매칭 처리
    matched_esi = None
    for k, v in REFERENCED_ESI.items():
        if k in planet_name_str or planet_name_str in k:
            matched_esi = v
            break
            
    if matched_esi is not None:
        st.markdown(f"<div class='esi-value-label'>참조 ESI 지수: {matched_esi:.2f} / 1.00</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='esi-value-label'>참조 ESI 지수: 미확인</div>", unsafe_allow_html=True)
        
    st.markdown("<div style='color:#AEB6E0; font-weight:500;'>지구와의 종합 유사도</div>", unsafe_allow_html=True)
    
    st.write("")
    sub1, sub2 = st.columns(2)
    sub1.metric("ESI (물리적 유사도)", f"{result['esi']*100:.1f}%" if result["esi"] is not None else "N/A")
    sub2.metric("확장 유사도 (대기·항성·주기 등)", f"{result['extended']*100:.1f}%" if result["extended"] is not None else "N/A")
else:
    st.markdown("<div class='similarity-percent'>N/A</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#AEB6E0;'>계산 가능한 데이터가 부족합니다. CSV를 채워주세요.</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# ----------------------------------------------------------------------------
# 요소별 상세 비교 표
# ----------------------------------------------------------------------------
st.subheader("📊 요소별 상세 비교")

factor_rows = [
    ("항성 종류", "star_type", EARTH["star_type"], ""),
    ("표면 온도 (°C)", "temp_surface_c", EARTH["temp_surface_c"], "°C"),
    ("표면 기압 (지구=1)", "pressure_atm", EARTH["pressure_atm"], "atm"),
    ("질량 (지구=1)", "mass_earth", EARTH["mass_earth"], "M⊕"),
    ("표면 중력 (지구=1)", "gravity_earth", EARTH["gravity_earth"], "g"),
    ("반지름 (지구=1)", "radius_earth", EARTH["radius_earth"], "R⊕"),
    ("탈출속도", "escape_velocity_km_s", EARTH["escape_velocity_km_s"], "km/s"),
    ("평균 밀도", "density_gcm3", EARTH["density_gcm3"], "g/cm³"),
    ("공전 주기", "orbital_period_days", EARTH["orbital_period_days"], "일"),
    ("자전 주기 (하루 길이)", "rotation_period_hours", EARTH["rotation_period_hours"], "시간"),
    ("자전축 기울기", "axial_tilt_deg", EARTH
