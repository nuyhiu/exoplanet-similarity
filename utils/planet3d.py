"""Plotly go.Surface로 3D 행성 구체를 그리는 모듈."""

import numpy as np
import plotly.graph_objects as go

# 지구용 컬러스케일: 짙은 바다(남색) -> 얕은 바다(청록) -> 육지(짙은 초록 -> 초록) -> 극지방(차분한 흰회색)
EARTH_COLORSCALE = [
    [0.00, "#041526"],
    [0.20, "#083150"],
    [0.40, "#0e4d75"],
    [0.53, "#166f97"],
    [0.55, "#16311c"],
    [0.68, "#1f4a27"],
    [0.80, "#2c6234"],
    [0.90, "#3a7a40"],
    [0.94, "#c6d2d8"],
    [1.00, "#eef2f4"],
]


def _earth_surface_value(theta, phi):
    """theta(극각 0~pi), phi(방위각 0~2pi)를 위도/경도로 변환한 뒤,
    실제 대륙의 대략적인 위치에 타원형 '블롭'을 배치해 대륙 모양을 흉내낸다."""
    lat = 90 - np.degrees(theta)  # +90(북극) ~ -90(남극)
    lon = ((np.degrees(phi) + 180) % 360) - 180  # -180 ~ 180

    def lon_diff(a, b):
        return (a - b + 180) % 360 - 180

    # (중심 위도, 중심 경도, 위도 반경, 경도 반경, 세기) - 실제 대륙의 대략적인 위치
    continents = [
        (48, -100, 24, 32, 1.00),   # 북아메리카
        (-16, -60, 26, 15, 0.92),   # 남아메리카
        (8, 20, 32, 24, 1.00),      # 아프리카
        (55, 80, 26, 60, 1.05),     # 유라시아
        (22, 78, 14, 16, 0.55),     # 인도 부근 (유라시아 남쪽 돌출부)
        (-24, 134, 15, 19, 0.85),   # 호주
        (73, -41, 11, 13, 0.55),    # 그린란드
        (62, 100, 16, 30, 0.45),    # 시베리아 동부 강조
    ]

    field = np.zeros_like(lat)
    for lat0, lon0, s_lat, s_lon, w in continents:
        d_lat = (lat - lat0) / s_lat
        d_lon = lon_diff(lon, lon0) / s_lon
        field += w * np.exp(-(d_lat ** 2 + d_lon ** 2))

    field = field / field.max()  # 0~1 정규화

    polar_mask = np.abs(lat) > 74  # 극지방 비중 축소(기존 66도 -> 74도)
    land_mask = (~polar_mask) & (field > 0.28)
    ocean_mask = (~polar_mask) & (~land_mask)

    value = np.zeros_like(field)
    # 대륙에서 멀수록(field->0) 짙은 심해색, 육지에 가까울수록(field->0.28) 밝은 연안색
    value[ocean_mask] = 0.02 + 0.51 * np.clip(field[ocean_mask] / 0.28, 0, 1)
    value[land_mask] = 0.55 + 0.35 * np.clip((field[land_mask] - 0.28) / 0.5, 0, 1)
    value[polar_mask] = 0.95 + 0.05 * (np.abs(lat[polar_mask]) - 74) / 16

    return np.clip(value, 0, 1)


def make_earth_figure(radius=1.0, title="지구 (Earth)", height=380):
    """바다(파랑)-육지(초록/갈색)-극지방(흰색)이 뚜렷하게 구분되는 스타일화된 지구 3D 구체."""
    theta = np.linspace(0, np.pi, 90)
    phi = np.linspace(0, 2 * np.pi, 90)
    theta, phi = np.meshgrid(theta, phi)

    display_radius = min(max((radius or 1.0) ** 0.5, 0.6), 1.8)
    x = display_radius * np.sin(theta) * np.cos(phi)
    y = display_radius * np.sin(theta) * np.sin(phi)
    z = display_radius * np.cos(theta)

    surfacecolor = _earth_surface_value(theta, phi)

    fig = go.Figure(
        data=[
            go.Surface(
                x=x, y=y, z=z,
                surfacecolor=surfacecolor,
                colorscale=EARTH_COLORSCALE,
                cmin=0, cmax=1,
                showscale=False,
                lighting=dict(ambient=0.55, diffuse=0.85, specular=0.25, roughness=0.7),
                lightposition=dict(x=150, y=200, z=150),
                hoverinfo="skip",
            )
        ]
    )
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            bgcolor="rgba(0,0,0,0)", aspectmode="cube",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40, b=0),
        title=dict(text=title, font=dict(color="#E8EAF6", size=18), x=0.5),
        height=height,
        showlegend=False,
    )
    return fig


def _color_for_temp(temp_c):
    """표면온도(섭씨)에 따라 파랑(극저온)~초록(온화)~주황/빨강(고온)~백열(초고온)로 이어지는 색을 계산."""
    if temp_c is None:
        return (110, 120, 135)  # 미확인 -> 회색
    stops = [
        (-270, (26, 42, 108)),
        (-150, (47, 90, 160)),
        (-50, (63, 155, 209)),
        (15, (74, 157, 92)),
        (60, (201, 168, 119)),
        (200, (201, 98, 47)),
        (600, (168, 50, 31)),
        (1500, (70, 20, 20)),
        (4500, (255, 235, 190)),
    ]
    t = max(min(temp_c, stops[-1][0]), stops[0][0])
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t0 <= t <= t1:
            frac = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(int(c0[i] + frac * (c1[i] - c0[i])) for i in range(3))
    return stops[-1][1]


def _lighten(rgb, factor):
    """factor>0: 밝게, factor<0: 어둡게 (가스형 행성 줄무늬용)"""
    r, g, b = rgb
    if factor >= 0:
        r, g, b = (r + (255 - r) * factor, g + (255 - g) * factor, b + (255 - b) * factor)
    else:
        r, g, b = (r * (1 + factor), g * (1 + factor), b * (1 + factor))
    return tuple(int(max(0, min(255, v))) for v in (r, g, b))


def make_exoplanet_figure(row, title="Exoplanet", height=380):
    """외계행성 데이터(row: pandas Series)를 바탕으로 온도 기반 색상 + 가스형 밴드무늬 +
    대기층(반투명 껍질)을 자동으로 표현하는 3D 구체. 실제 사진이 없는 외계행성을 위한 데이터 기반 시각화."""
    def _get(key):
        v = row.get(key) if hasattr(row, "get") else None
        try:
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return None
        except TypeError:
            pass
        return v

    radius = _get("radius_earth") or 1.0
    temp_c = _get("temp_surface_c")
    density = _get("density_gcm3")
    pressure = _get("pressure_atm")

    base_rgb = _color_for_temp(float(temp_c) if temp_c is not None else None)
    is_gas_giant = density is not None and float(density) < 2.2

    display_radius = min(max(float(radius) ** 0.5, 0.6), 2.2)

    theta = np.linspace(0, np.pi, 80)
    phi = np.linspace(0, 2 * np.pi, 80)
    theta, phi = np.meshgrid(theta, phi)

    x = display_radius * np.sin(theta) * np.cos(phi)
    y = display_radius * np.sin(theta) * np.sin(phi)
    z = display_radius * np.cos(theta)

    if is_gas_giant:
        # 위도에 따른 줄무늬(목성/토성 느낌)
        lat = 90 - np.degrees(theta)
        band = 0.5 + 0.5 * np.sin(lat / 6.0) * np.cos(lat / 17.0 + 1.3)
        n_bands = 7
        shades = [_lighten(base_rgb, f) for f in np.linspace(-0.35, 0.35, n_bands)]
        colorscale = [[i / (n_bands - 1), f"rgb({r},{g},{b})"] for i, (r, g, b) in enumerate(shades)]
        surfacecolor = band
        cmin, cmax = 0, 1
    else:
        colorscale = [[0, f"rgb{base_rgb}"], [1, f"rgb{base_rgb}"]]
        surfacecolor = np.zeros_like(theta)
        cmin, cmax = 0, 1

    traces = [
        go.Surface(
            x=x, y=y, z=z,
            surfacecolor=surfacecolor,
            colorscale=colorscale,
            cmin=cmin, cmax=cmax,
            showscale=False,
            lighting=dict(ambient=0.55, diffuse=0.85, specular=0.35, roughness=0.6),
            lightposition=dict(x=150, y=200, z=150),
            hoverinfo="skip",
        )
    ]

    # 대기압이 어느 정도 있으면(0.05atm 이상) 반투명 대기층 추가
    if pressure is not None and float(pressure) > 0.05:
        p = float(pressure)
        opacity = min(0.35, 0.10 + 0.06 * np.log10(max(p, 0.05) + 1))
        shell_r = display_radius * 1.05
        xs = shell_r * np.sin(theta) * np.cos(phi)
        ys = shell_r * np.sin(theta) * np.sin(phi)
        zs = shell_r * np.cos(theta)
        traces.append(
            go.Surface(
                x=xs, y=ys, z=zs,
                surfacecolor=np.zeros_like(theta),
                colorscale=[[0, "rgb(200,225,255)"], [1, "rgb(200,225,255)"]],
                cmin=0, cmax=1,
                showscale=False,
                opacity=opacity,
                lighting=dict(ambient=0.9, diffuse=0.2, specular=0.1),
                hoverinfo="skip",
            )
        )

    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            bgcolor="rgba(0,0,0,0)", aspectmode="cube",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40, b=0),
        title=dict(text=title, font=dict(color="#E8EAF6", size=18), x=0.5),
        height=height,
        showlegend=False,
    )
    return fig


def make_planet_figure(color="#3D7EAA", title="Earth", radius=1.0, height=380, is_earth=False):
    radius = radius if (radius and radius > 0) else 1.0
    display_radius = min(max(radius ** 0.5, 0.6), 1.8)

    theta = np.linspace(0, np.pi, 80)
    phi = np.linspace(0, 2 * np.pi, 80)
    theta, phi = np.meshgrid(theta, phi)

    x = display_radius * np.sin(theta) * np.cos(phi)
    y = display_radius * np.sin(theta) * np.sin(phi)
    z = display_radius * np.cos(theta)

    if is_earth:
        surfacecolor = _earth_surface_value(theta, phi)
        colorscale = EARTH_COLORSCALE
        cmin, cmax = 0, 1
    else:
        surfacecolor = np.zeros_like(theta)
        colorscale = [[0, color], [1, color]]
        cmin, cmax = 0, 1

    fig = go.Figure(
        data=[
            go.Surface(
                x=x,
                y=y,
                z=z,
                surfacecolor=surfacecolor,
                colorscale=colorscale,
                cmin=cmin,
                cmax=cmax,
                showscale=False,
                lighting=dict(ambient=0.55, diffuse=0.85, specular=0.4, roughness=0.6),
                lightposition=dict(x=150, y=200, z=150),
                hoverinfo="skip",
            )
        ]
    )

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="rgba(0,0,0,0)",
            aspectmode="cube",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40, b=0),
        title=dict(text=title, font=dict(color="#E8EAF6", size=18), x=0.5),
        height=height,
        showlegend=False,
    )
    return fig

