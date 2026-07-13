import pandas as pd
import streamlit as st

from utils.planet3d import make_earth_figure, make_exoplanet_figure, make_planet_figure
from utils.similarity import EARTH, compute_overall_similarity

st.set_page_config(page_title="지구-외계행성 유사도 분석", page_icon="🪐", layout="wide")

# ----------------------------------------------------------------------------
# 다크 우주 테마 CSS (가독성이 확보된 우주 스타일)
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
    
    /* 화면의 기본 설명글 및 캡션 (밝은 청회색 고정) */
    .stApp div p, .stApp .stCaption, .stApp p {
        color: #C3CADB;
    }
    
    /* 토글(Expander) 내부 본문 텍스트 밝게 변경 */
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
    
    /* 행성 선택 드롭다운 리스트 가독성 패치 */
    div[data-baseweb="popover"] div {
        background-color: #0F163A !important;
    }
    div[data-baseweb="popover"] div div {
        color: #FFFFFF !important; 
    }
    div[data-baseweb="popover"] ul li:hover {
        background-color: #1E295D !important;
    }
    
    /* 메인 화면 링크형 투명 행성 이름 스타일 */
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
    
    /* 유사도 박스 및 신규 ESI 지수 스타일 */
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
    /* 새로 추가한 공식 ESI 지수 라벨 */
    .esi-value-label {
        font-size: 1.2rem;
        font-weight: 600;
        color: #93C5FD !important; /* 선명한 하늘색 톤 */
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
# 유사도 계산 및 표시 (ESI Index 지수 추가)
# ----------------------------------------------------------------------------
result = compute_overall_similarity(row)

st.markdown("<div class='similarity-box'>", unsafe_allow_html=True)
if result["overall"] is not None:
    # 1. 종합 유사도 퍼센티지
    st.markdown(f"<div class='similarity-percent'>{result['overall']*100:.1f}%</div>", unsafe_allow_html=True)
    
    # 2. [신규 추가] 인터넷 검색 규격에 맞는 소수점 형태 ESI 지수 (0.XX / 1.00)
    esi_val = result['esi'] if result['esi'] is not None else 0.0
    st.markdown(f"<div class='esi-value-label'>ESI Index: {esi_val:.2f} / 1.00</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='color:#AEB6E0; font-weight:500;'>지구와의 종합 유사도</div>", unsafe_allow_html=True)
    
    st.write("")
    sub1, sub2 = st.columns(2)
    sub1.metric("ESI", f"{result['esi']*100:.1f}%" if result["esi"] is not None else "N/A")
    sub2.metric("복합적 요소 고려한 유사도 (대기·항성·주기 등)", f"{result['extended']*100:.1f}%" if result["extended"] is not None else "N/A")
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
    ("자전축 기울기", "axial_tilt_deg", EARTH["axial_tilt_deg"], "°"),
    ("대기 - N2", "atmosphere_n2_pct", EARTH["atmosphere_n2_pct"], "%"),
    ("대기 - O2", "atmosphere_o2_pct", EARTH["atmosphere_o2_pct"], "%"),
    ("대기 - CO2", "atmosphere_co2_pct", EARTH["atmosphere_co2_pct"], "%"),
]

table_data = []
for label, key, earth_val, unit in factor_rows:
    val = row.get(key)
    has_val = pd.notna(val) and str(val).strip() != ""
    table_data.append(
        {
            "요소": label,
            "지구 값": f"{earth_val}{unit}",
            "이 행성 값": f"{val}{unit}" if has_val else "미확인"
        }
    )

st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

if isinstance(row.get("atmosphere_notes"), str) and row["atmosphere_notes"].strip():
    st.caption(f"💨 대기 관련 메모: {row['atmosphere_notes']}")

with st.expander("ℹ️ 유사도는 어떻게 계산되나요?"):
    st.markdown(
        """
- **ESI (Earth Similarity Index)**: 반지름, 밀도, (질량·반지름으로 추정한) 탈출속도, 표면온도를 이용한 고전적인 지구 유사도 지수입니다.
- **확장 유사도**: ESI에 포함되지 않는 항성 종류, 표면 기압, 표면 중력, 자전/공전 주기, 자전축 기울기, 대기 조성(N2/O2/CO2)을 가중 평균한 값입니다.
- **종합 유사도** = ESI × 0.6 + 확장 유사도 × 0.4 (둘 중 하나만 계산 가능하면 그 값을 그대로 사용합니다.)
- 값이 비어 있는(미확인) 요소는 계산에서 자동으로 제외되고, 나머지 요소들의 가중치로 재조정됩니다.
        """
    )
