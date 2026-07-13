"""Plotly go.Surface로 3D 행성 구체를 그리는 모듈."""

from functools import lru_cache
from io import BytesIO

import numpy as np
import plotly.graph_objects as go

# Solar System Scope의 지구 데이맵 텍스처 (구름 없는 실제 위성 이미지 합성본, CC BY 4.0, NASA 데이터 기반)
EARTH_TEXTURE_URL = "https://www.solarsystemscope.com/textures/download/2k_earth_daymap.jpg"

# 지구용 컬러스케일(실제 텍스처 로딩 실패 시 대체용): 밝은 파란 바다 -> 짙은 초록 육지 -> 차분한 흰회색 극지방
EARTH_COLORSCALE = [
    [0.00, "#0f4c81"],
    [0.20, "#1565a3"],
    [0.40, "#1f7fc0"],
    [0.53, "#3a9bd6"],
    [0.56, "#1c4523"],
    [0.68, "#25592c"],
    [0.80, "#2f6d37"],
    [0.90, "#3d8244"],
    [0.94, "#c6d2d8"],
    [1.00, "#eef2f4"],
]


def _smoothstep(x, edge0, edge1):
    t = np.clip((x - edge0) / (edge1 - edge0), 0, 1)
    return t * t * (3 - 2 * t)


def _earth_surface_value(theta, phi):
    """theta(극각 0~pi), phi(방위각 0~2pi)를 위도/경도로 변환한 뒤,
    실제 대륙의 대략적인 위치에 타원형 '블롭'을 배치해 대륙 모양을 흉내낸다(대체용)."""
    lat = 90 - np.degrees(theta)
    lon = ((np.degrees(phi) + 180) % 360) - 180

    def lon_diff(a, b):
        return (a - b + 180) % 360 - 180

    continents = [
        (45, -100, 22, 28, 1.00),
        (-15, -60, 26, 14, 0.95),
        (5, 20, 34, 20, 1.00),
        (50, 70, 24, 55, 1.00),
        (-24, 134, 14, 17, 0.85),
        (73, -41, 9, 11, 0.55),
    ]

    field = np.zeros_like(lat)
    for lat0, lon0, s_lat, s_lon, w in continents:
        d_lat = (lat - lat0) / s_lat
        d_lon = lon_diff(lon, lon0) / s_lon
        r2 = d_lat ** 2 + d_lon ** 2
        field = np.maximum(field, w * np.exp(-(r2 ** 1.3)))

    polar_mask = np.abs(lat) > 74
    land_frac = _smoothstep(field, 0.32, 0.5)
    ocean_value = 0.05 + 0.48 * _smoothstep(field, 0.0, 0.32)
    land_value = 0.56 + 0.34 * _smoothstep(field, 0.5, 1.0)
    value = ocean_value * (1 - land_frac) + land_value * land_frac
    value = np.where(polar_mask, 0.95 + 0.05 * (np.abs(lat) - 74) / 16, value)

    return np.clip(value, 0, 1)


_last_earth_load_error = None


def get_last_earth_load_error():
    """가장 최근 실제 텍스처 로딩 시도의 실패 사유(문자열) 반환. 성공했으면 None."""
    return _last_earth_load_error


@lru_cache(maxsize=1)
def _load_earth_palette(grid_lon=120, grid_lat=60):
    """실제 지구 텍스처 이미지를 불러와 (팔레트 인덱스 배열, RGB 팔레트) 로 변환.
    Pillow의 무거운 ADAPTIVE 색상 양자화(과거 서버 크래시 유발 의심) 대신,
    numpy로 직접 간단한 비트 축소 양자화를 수행해 가볍게 처리함.
    실패 시 None 반환 -> 호출부에서 스타일화된 지구로 자동 대체."""
    global _last_earth_load_error
    try:
        import requests
        from PIL import Image

        resp = requests.get(EARTH_TEXTURE_URL, timeout=8)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        img = img.resize((grid_lon, grid_lat), Image.NEAREST)  # 단순 리샘플링(무거운 필터 회피)
        arr = np.asarray(img, dtype=np.uint8)  # (grid_lat, grid_lon, 3)

        # 채널당 4비트(16단계)로 양자화 -> 색상 수를 보수적으로 제한(PIL ADAPTIVE 미사용)
        q = (arr.astype(np.int32) >> 4)
        key = q[..., 0] * 16 * 16 + q[..., 1] * 16 + q[..., 2]
        unique_keys, inverse = np.unique(key, return_inverse=True)

        r = (unique_keys // (16 * 16)) * 16 + 8
        g = ((unique_keys // 16) % 16) * 16 + 8
        b = (unique_keys % 16) * 16 + 8
        colors = list(zip(r.tolist(), g.tolist(), b.tolist()))

        idx = inverse.reshape(arr.shape[:2]).astype(float)
        _last_earth_load_error = None
        return idx, colors
    except Exception as e:
        _last_earth_load_error = f"{type(e).__name__}: {e}"
        return None


def make_earth_figure(radius=1.0, title="지구 (Earth)", height=380):
    """실제 위성 텍스처(구름 없는 데이맵)를 입힌 지구 3D 구체.
    로딩 실패 시 스타일화된 대륙 패턴으로 자동 대체."""
    loaded = _load_earth_palette()
    display_radius = min(max((radius or 1.0) ** 0.5, 0.6), 1.8)

    if loaded is not None:
        idx, colors = loaded
        grid_lat, grid_lon = idx.shape
        n_colors = len(colors)

        lat = np.linspace(0, np.pi, grid_lat)
        lon = np.linspace(0, 2 * np.pi, grid_lon)
        theta, phi = np.meshgrid(lat, lon, indexing="ij")

        x = display_radius * np.sin(theta) * np.cos(phi)
        y = display_radius * np.sin(theta) * np.sin(phi)
        z = display_radius * np.cos(theta)

        surfacecolor = idx / max(n_colors - 1, 1)
        colorscale = [[i / max(n_colors - 1, 1), f"rgb({r},{g},{b})"] for i, (r, g, b) in enumerate(colors)]
    else:
        theta = np.linspace(0, np.pi, 90)
        phi = np.linspace(0, 2 * np.pi, 90)
        theta, phi = np.meshgrid(theta, phi)
        x = display_radius * np.sin(theta) * np.cos(phi)
        y = display_radius * np.sin(theta) * np.sin(phi)
        z = display_radius * np.cos(theta)
        surfacecolor = _earth_surface_value(theta, phi)
        colorscale = EARTH_COLORSCALE

    fig = go.Figure(
        data=[
            go.Surface(
                x=x, y=y, z=z,
                surfacecolor=surfacecolor,
                colorscale=colorscale,
                cmin=0, cmax=1,
                showscale=False,
                lighting=dict(ambient=0.65, diffuse=0.85, specular=0.2, roughness=0.7),
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
