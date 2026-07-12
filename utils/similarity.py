"""
지구-외계행성 유사도 계산 모듈
- ESI (Earth Similarity Index): 반지름, 밀도, 탈출속도, 표면온도 기반 (Schulze-Makuch et al. 2011 공식 변형)
- Extended Score: 항성 종류, 기압, 중력, 자전/공전 주기, 자전축 기울기, 대기 조성 기반
결측치(빈 칸)는 자동으로 해당 항목만 제외하고, 나머지 가중치로 재정규화합니다.
"""

import numpy as np
import pandas as pd

EARTH = {
    "star_type": "G",
    "temp_surface_c": 15.0,
    "pressure_atm": 1.0,
    "mass_earth": 1.0,
    "gravity_earth": 1.0,
    "radius_earth": 1.0,
    "density_gcm3": 5.51,
    "orbital_period_days": 365.25,
    "rotation_period_hours": 24.0,
    "axial_tilt_deg": 23.4,
    "atmosphere_n2_pct": 78.0,
    "atmosphere_o2_pct": 21.0,
    "atmosphere_co2_pct": 0.04,
}

STAR_ORDER = ["O", "B", "A", "F", "G", "K", "M", "L", "T", "Y"]


def _has(row, key):
    return key in row and pd.notna(row[key]) and str(row[key]).strip() != ""


def normalized_similarity(x, x_earth):
    """일반적인 (1 - |x - earth| / (x + earth)) 형태의 유사도. x, x_earth는 양수여야 함."""
    x = float(x)
    if x + x_earth == 0:
        return None
    return 1 - abs(x - x_earth) / (x + x_earth)


def star_type_similarity(star_type):
    if star_type is None or (isinstance(star_type, float) and pd.isna(star_type)):
        return None
    st = str(star_type).strip().upper()
    if not st:
        return None
    st = st[0]
    if st not in STAR_ORDER:
        return None
    earth_idx = STAR_ORDER.index("G")
    idx = STAR_ORDER.index(st)
    max_dist = max(earth_idx, len(STAR_ORDER) - 1 - earth_idx)
    return 1 - abs(idx - earth_idx) / max_dist


def _esi_term(value, earth_value, weight, n_terms):
    sim = normalized_similarity(value, earth_value)
    if sim is None or sim < 0:
        sim = max(sim, 0) if sim is not None else None
    if sim is None:
        return None
    return sim ** (weight / n_terms)


def compute_esi(row):
    """고전 ESI 계산. 반지름/밀도(내부) + 탈출속도/표면온도(표면) 조합.
    반환: (esi_value 0~1 또는 None, 사용된 항목 리스트)
    """
    used = []

    # --- 내부 ESI: 반지름, 밀도 ---
    interior_terms = []
    if _has(row, "radius_earth"):
        t = _esi_term(row["radius_earth"], EARTH["radius_earth"], 0.57, 2)
        if t is not None:
            interior_terms.append(t)
            used.append("반지름")
    if _has(row, "density_gcm3"):
        t = _esi_term(row["density_gcm3"], EARTH["density_gcm3"], 1.07, 2)
        if t is not None:
            interior_terms.append(t)
            used.append("밀도")
    interior = float(np.prod(interior_terms)) if interior_terms else None

    # --- 표면 ESI: 탈출속도(질량/반지름 유도), 표면온도 ---
    surface_terms = []
    if _has(row, "mass_earth") and _has(row, "radius_earth") and float(row["radius_earth"]) > 0:
        v_esc = (float(row["mass_earth"]) / float(row["radius_earth"])) ** 0.5
        t = _esi_term(v_esc, 1.0, 0.70, 2)
        if t is not None:
            surface_terms.append(t)
            used.append("탈출속도(질량/반지름 기반)")
    if _has(row, "temp_surface_c"):
        t_k = float(row["temp_surface_c"]) + 273.15
        earth_k = EARTH["temp_surface_c"] + 273.15
        t = _esi_term(t_k, earth_k, 5.58, 2)
        if t is not None:
            surface_terms.append(t)
            used.append("표면온도")
    surface = float(np.prod(surface_terms)) if surface_terms else None

    if interior is not None and surface is not None:
        return (interior * surface) ** 0.5, used
    if interior is not None:
        return interior, used
    if surface is not None:
        return surface, used
    return None, used


def compute_extended_score(row):
    """ESI에 포함되지 않는 항목들(항성 종류, 기압, 중력, 자전/공전, 대기 조성)의 가중 평균 유사도."""
    scores, weights, used = [], [], []

    if _has(row, "star_type"):
        s = star_type_similarity(row["star_type"])
        if s is not None:
            scores.append(s); weights.append(1.0); used.append("항성 종류")

    if _has(row, "pressure_atm"):
        s = normalized_similarity(row["pressure_atm"], EARTH["pressure_atm"])
        if s is not None:
            scores.append(max(s, 0)); weights.append(1.0); used.append("표면 기압")

    if _has(row, "gravity_earth"):
        s = normalized_similarity(row["gravity_earth"], EARTH["gravity_earth"])
        if s is not None:
            scores.append(max(s, 0)); weights.append(1.0); used.append("표면 중력")

    if _has(row, "rotation_period_hours"):
        s = normalized_similarity(row["rotation_period_hours"], EARTH["rotation_period_hours"])
        if s is not None:
            scores.append(max(s, 0)); weights.append(0.7); used.append("자전 주기(하루 길이)")

    if _has(row, "orbital_period_days"):
        s = normalized_similarity(row["orbital_period_days"], EARTH["orbital_period_days"])
        if s is not None:
            scores.append(max(s, 0)); weights.append(0.5); used.append("공전 주기")

    if _has(row, "axial_tilt_deg"):
        diff = abs(float(row["axial_tilt_deg"]) - EARTH["axial_tilt_deg"])
        s = max(0.0, 1 - diff / 90.0)
        scores.append(s); weights.append(0.5); used.append("자전축 기울기(계절)")

    for gas, w in [("atmosphere_n2_pct", 0.8), ("atmosphere_o2_pct", 1.2), ("atmosphere_co2_pct", 0.8)]:
        if _has(row, gas):
            s = normalized_similarity(row[gas], EARTH[gas])
            if s is not None:
                scores.append(max(s, 0)); weights.append(w); used.append(gas.replace("atmosphere_", "").replace("_pct", "").upper() + " 비율")

    if not scores:
        return None, used
    scores = np.array(scores); weights = np.array(weights)
    return float(np.sum(scores * weights) / np.sum(weights)), used


def compute_overall_similarity(row, esi_weight=0.6):
    """최종 유사도 = esi_weight * ESI + (1-esi_weight) * 확장점수.
    둘 중 하나만 있으면 있는 값만 사용. 반환: dict"""
    esi, esi_used = compute_esi(row)
    ext, ext_used = compute_extended_score(row)

    if esi is not None and ext is not None:
        overall = esi_weight * esi + (1 - esi_weight) * ext
    elif esi is not None:
        overall = esi
    elif ext is not None:
        overall = ext
    else:
        overall = None

    return {
        "overall": overall,
        "esi": esi,
        "extended": ext,
        "esi_used_factors": esi_used,
        "extended_used_factors": ext_used,
    }
