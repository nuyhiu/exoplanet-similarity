"""Plotly go.Surface로 3D 행성 구체를 그리는 모듈."""

from functools import lru_cache
from io import BytesIO

import numpy as np
import plotly.graph_objects as go

EARTH_TEXTURE_URL = (
    "https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57735/"
    "land_ocean_ice_cloud_2048.jpg"
)

# 지구용 커스텀 컬러스케일(실제 텍스처 로딩 실패 시 대체용): 짙은 바다 -> 얕은 바다 -> 육지 -> 극지방
EARTH_COLORSCALE = [
    [0.00, "#0b3d61"],
    [0.20, "#134f7e"],
    [0.40, "#1f6fa8"],
    [0.54, "#3f9bd1"],
    [0.55, "#3f6b35"],
    [0.65, "#5c8a3a"],
    [0.75, "#8a7440"],
    [0.85, "#c9a877"],
    [0.90, "#e8e8e8"],
    [1.00, "#ffffff"],
]


def _earth_surface_value(theta, phi):
    """theta(극각 0~pi), phi(방위각 0~2pi)에 따라 대륙처럼 보이는 패턴을 생성(대체용)."""
    lat = 90 - np.degrees(theta)
    lon = np.degrees(phi)

    noise = (
        0.45 * np.sin(np.radians(3 * lat + 40)) * np.cos(np.radians(2.2 * lon + 15))
        + 0.30 * np.sin(np.radians(5 * lat - 1.5 * lon + 60))
        + 0.25 * np.cos(np.radians(6.5 * lon - 2 * lat + 10))
    )
    noise = (noise - noise.min()) / (noise.max() - noise.min())

    polar_mask = np.abs(lat) > 62
    land_mask = (~polar_mask) & (noise > 0.55)
    ocean_mask = (~polar_mask) & (~land_mask)

    value = np.zeros_like(noise)
    value[ocean_mask] = 0.54 * (noise[ocean_mask] / 0.55)
    value[land_mask] = 0.55 + 0.35 * ((noise[land_mask] - 0.55) / 0.45)
    value[polar_mask] = 0.92 + 0.08 * (np.abs(lat[polar_mask]) - 62) / 28

    return np.clip(value, 0, 1)


@lru_cache(maxsize=1)
def _load_earth_palette(grid_lon=144, grid_lat=72, palette_colors=64):
    """NASA 지구 텍스처 이미지를 불러와 (팔레트 인덱스 배열, RGB 팔레트) 로 변환.
    실패 시 None 반환 -> 호출부에서 노이즈 기반 지구로 자동 대체."""
    try:
        import requests
        from PIL import Image

        resp = requests.get(EARTH_TEXTURE_URL, timeout=8)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        img = img.resize((grid_lon, grid_lat))
        img_p = img.convert("P", palette=Image.ADAPTIVE, colors=palette_colors)
        idx = np.array(img_p, dtype=float)  # (grid_lat, grid_lon)
        pal = img_p.getpalette()[: palette_colors * 3]
        colors = [tuple(pal[i * 3: i * 3 + 3]) for i in range(palette_colors)]
        return idx, colors
    except Exception:
        return None


def make_earth_figure(radius=1.0, title="지구 (Earth)", height=380):
    """실제 NASA 위성사진 텍스처를 입힌 지구 3D 구체.
    인터넷 연결 문제 등으로 텍스처 로딩 실패 시, 노이즈 기반 대륙 패턴으로 자동 대체."""
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

        surfacecolor = idx / (n_colors - 1)
        colorscale = [[i / (n_colors - 1), f"rgb({r},{g},{b})"] for i, (r, g, b) in enumerate(colors)]
        cmin, cmax = 0, 1
    else:
        theta = np.linspace(0, np.pi, 80)
        phi = np.linspace(0, 2 * np.pi, 80)
        theta, phi = np.meshgrid(theta, phi)
        x = display_radius * np.sin(theta) * np.cos(phi)
        y = display_radius * np.sin(theta) * np.sin(phi)
        z = display_radius * np.cos(theta)
        surfacecolor = _earth_surface_value(theta, phi)
        colorscale = EARTH_COLORSCALE
        cmin, cmax = 0, 1

    fig = go.Figure(
        data=[
            go.Surface(
                x=x, y=y, z=z,
                surfacecolor=surfacecolor,
                colorscale=colorscale,
                cmin=cmin, cmax=cmax,
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

