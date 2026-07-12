

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
