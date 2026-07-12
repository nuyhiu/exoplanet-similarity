"""Plotly go.Surface로 간단한 3D 행성 구체를 그리는 모듈."""

import numpy as np
import plotly.graph_objects as go


def make_planet_figure(color="#3D7EAA", title="Earth", radius=1.0, height=380):
    radius = radius if (radius and radius > 0) else 1.0
    # 반지름이 너무 크거나 작으면 화면에서 보기 좋게 스케일 압축
    display_radius = 0.6 + 0.4 * min(max(radius, 0.3), 3.0) / 3.0 * 3.0
    display_radius = min(max(radius ** 0.5, 0.6), 1.8)

    theta = np.linspace(0, np.pi, 60)
    phi = np.linspace(0, 2 * np.pi, 60)
    theta, phi = np.meshgrid(theta, phi)

    x = display_radius * np.sin(theta) * np.cos(phi)
    y = display_radius * np.sin(theta) * np.sin(phi)
    z = display_radius * np.cos(theta)

    colorscale = [[0, color], [1, color]]

    fig = go.Figure(
        data=[
            go.Surface(
                x=x,
                y=y,
                z=z,
                colorscale=colorscale,
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


