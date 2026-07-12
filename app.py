대기·항성·자전공전 등 추가 요소를 종합해 지구와 얼마나 닮았는지 계산합니다.")

# ----------------------------------------------------------------------------
# 행성 탐색 (좌우 화살표)
# ----------------------------------------------------------------------------
nav_col1, nav_col2, nav_col3 = st.columns([1, 6, 1])
with nav_col1:
    if st.button("◀", use_container_width=True, disabled=(n == 0)):
        st.session_state.idx = (st.session_state.idx - 1) % n
with nav_col3:
    if st.button("▶", use_container_width=True, disabled=(n == 0)):
        st.session_state.idx = (st.session_state.idx + 1) % n

if n == 0:
    st.warning("data/exoplanets_template.csv 에 행성 데이터를 채워주세요.")
    st.stop()

row = planets_df.iloc[st.session_state.idx]

with nav_col2:
    st.markdown(f"<div class='planet-name'>{row['planet_name']}  ·  {st.session_state.idx + 1} / {n}</div>", unsafe_allow_html=True)
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
# 유사도 계산 및 표시
# ----------------------------------------------------------------------------
result = compute_overall_similarity(row)

st.markdown("<div class='similarity-box'>", unsafe_allow_html=True)
if result["overall"] is not None:
    st.markdown(f"<div class='similarity-percent'>{result['overall']*100:.1f}%</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#AEB6E0;'>지구와의 종합 유사도</div>", unsafe_allow_html=True)
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
            "이 행성 값": f"{val}{unit}" if has_val else "미확인",
            "계산 포함 여부": "✅ 포함" if has_val else "⛔ 제외",
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
