from functools import lru_cache

from dash import html, dcc, callback, clientside_callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from utils.data_loader import load_monthly_index, get_year_range, get_country_detail
from utils.components import make_chart_card, PLOTLY_LAYOUT, COLORS, SPECTRUM
from processing.translations import COMMODITY_ID


COLORSCALE = [
    (0.0, "#f4c39b"),
    (0.33, "#ee8d59"),
    (0.66, "#e1694d"),
    (1.0, "#d8392e"),
]

LABEL_DARK = "#374357"

INIT_SCALE = 0.92
INIT_LON = 10
INIT_LAT = 12


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def _blend(c1, c2, w):
    return tuple(c1[i] * (1 - w) + c2[i] * w for i in range(3))


def _scale_color_rgb(t):
    t = max(0.0, min(1.0, t))
    for i in range(len(COLORSCALE) - 1):
        p0, h0 = COLORSCALE[i]
        p1, h1 = COLORSCALE[i + 1]
        if t <= p1:
            local = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return _blend(_hex_to_rgb(h0), _hex_to_rgb(h1), local)
    return _hex_to_rgb(COLORSCALE[-1][1])


def _iso_to_name(iso3):
    try:
        import pycountry
        country = pycountry.countries.get(alpha_3=iso3)
        return country.name if country else iso3
    except Exception:
        return iso3


@lru_cache(maxsize=1)
def _monthly_with_year():
    df = load_monthly_index().copy()
    df["year"] = pd.to_datetime(df["year_month"]).dt.year
    return df


@lru_cache(maxsize=32)
def _country_volatility_for_years(year_start, year_end):
    df = _monthly_with_year()
    df = df[(df["year"] >= year_start) & (df["year"] <= year_end)]

    cv = df.groupby("countryiso3").agg(
        n_months=("year_month", "nunique"),
        mean_index=("price_index", "mean"),
        std_index=("price_index", "std"),
        mean_mom_change=("mom_change_pct", "mean"),
        std_mom_change=("mom_change_pct", "std"),
        median_usdprice=("usdprice", "median"),
    ).reset_index()

    cv["cv_index"] = cv["std_index"] / cv["mean_index"]
    cv = cv.dropna(subset=["cv_index"]).reset_index(drop=True)
    return cv


@lru_cache(maxsize=128)
def _commodity_volatility_for_country(country_iso, year_start, year_end):
    df = _monthly_with_year()
    df = df[
        (df["countryiso3"] == country_iso)
        & (df["year"] >= year_start)
        & (df["year"] <= year_end)
    ]

    cv = df.groupby("commodity").agg(
        mean_index=("price_index", "mean"),
        std_index=("price_index", "std"),
        n_months=("year_month", "nunique"),
    ).reset_index()

    cv["cv_index"] = cv["std_index"] / cv["mean_index"]
    cv = cv.dropna(subset=["cv_index"]).sort_values("cv_index", ascending=False).reset_index(drop=True)
    return cv


def _resolve_years(year_range):
    if year_range and len(year_range) == 2:
        return int(year_range[0]), int(year_range[1])
    return get_year_range()


def _clicked_iso(clickData):
    if clickData and "points" in clickData and len(clickData["points"]) > 0:
        return clickData["points"][0].get("location")
    return None


def _empty_fig(message, height):
    fig = go.Figure()
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=height,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message,
                showarrow=False,
                font=dict(size=13, color=COLORS["text_sub"]),
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )
        ],
    )
    return fig


def _zoom_button(symbol, btn_id, font_size="18px"):
    return html.Button(
        symbol,
        id=btn_id,
        n_clicks=0,
        style={
            "width": "34px",
            "height": "34px",
            "backgroundColor": "rgba(31, 42, 68, 0.88)",
            "color": "white",
            "border": "none",
            "borderRadius": "8px",
            "cursor": "pointer",
            "fontSize": font_size,
            "fontWeight": "bold",
            "lineHeight": "1",
            "boxShadow": "0 2px 6px rgba(31, 42, 68, 0.25)",
        },
    )


def _detail_placeholder():
    return html.Div(
        [
            html.Div(
                "Belum ada negara dipilih",
                style={
                    "fontSize": "14px",
                    "fontWeight": "600",
                    "color": "var(--text-main)",
                    "marginBottom": "6px",
                },
            ),
            html.Div(
                "Klik salah satu negara pada globe untuk melihat detail "
                "volatilitas dan tren harganya.",
                style={
                    "fontSize": "13px",
                    "color": LABEL_DARK,
                    "lineHeight": "1.5",
                },
            ),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "center",
            "height": "100%",
            "minWidth": "0",
        },
    )


def _detail_message(text):
    return html.Div(
        text,
        style={
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "center",
            "height": "100%",
            "minWidth": "0",
            "color": LABEL_DARK,
            "fontSize": "13px",
            "lineHeight": "1.5",
        },
    )


def geography_layout():
    return html.Div(
        [
            dcc.Store(id="geo-zoom-dummy"),
            make_chart_card(
                "Persebaran Geografis Volatilitas Harga",
                "Koefisien variasi (CV) indeks harga pangan per negara pada rentang tahun terpilih. "
                "Semakin merah, semakin volatil. Seret untuk memutar globe dan gunakan tombol +/- untuk memperbesar.",
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                _zoom_button("+", "zoom-in-btn"),
                                                _zoom_button("\u2212", "zoom-out-btn"),
                                                _zoom_button("\u21BA", "geo-reset-btn", font_size="15px"),
                                            ],
                                            style={
                                                "position": "absolute",
                                                "top": "14px",
                                                "right": "14px",
                                                "zIndex": "5",
                                                "display": "flex",
                                                "flexDirection": "column",
                                                "gap": "6px",
                                            },
                                        ),
                                        dcc.Graph(
                                            id="country-volatility-map",
                                            config={
                                                "displayModeBar": False,
                                                "scrollZoom": False,
                                                "doubleClick": False,
                                            },
                                            style={"margin": "0"},
                                        ),
                                    ],
                                    style={
                                        "position": "relative",
                                        "zIndex": "0",
                                        "flex": "75 1 0",
                                        "minWidth": "340px",
                                        "borderRadius": "10px",
                                        "overflow": "hidden",
                                        "background": (
                                            "radial-gradient(circle at 46% 50%, "
                                            "rgba(168, 203, 229, 0.55) 0%, "
                                            "rgba(168, 203, 229, 0.16) 42%, "
                                            "rgba(247, 246, 242, 0) 64%)"
                                        ),
                                    },
                                ),
                                html.Div(
                                    id="country-detail-info",
                                    children=_detail_placeholder(),
                                    style={
                                        "display": "flex",
                                        "flexDirection": "column",
                                        "flex": "25 1 0",
                                        "minWidth": "260px",
                                        "padding": "20px 22px",
                                        "backgroundColor": "rgba(31, 42, 68, 0.03)",
                                        "borderRadius": "10px",
                                        "border": "1px solid rgba(31, 42, 68, 0.06)",
                                        "minHeight": "300px",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "flexWrap": "wrap",
                                "gap": "24px",
                                "alignItems": "stretch",
                            },
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            "Top 10 Komoditas Paling Volatil",
                                            style={
                                                "fontSize": "15px",
                                                "fontWeight": "600",
                                                "color": "var(--text-main)",
                                                "margin": "0 0 2px 0",
                                            },
                                        ),
                                        html.Div(
                                            id="country-top-commodities-sub",
                                            children="Berdasarkan koefisien variasi (CV) per komoditas.",
                                            style={
                                                "fontSize": "12px",
                                                "color": LABEL_DARK,
                                                "margin": "0 0 8px 0",
                                            },
                                        ),
                                        dcc.Graph(
                                            id="country-top-commodities",
                                            config={"displayModeBar": False, "responsive": True},
                                        ),
                                    ],
                                    style={"flex": "42 1 0", "minWidth": "300px"},
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            id="country-trend-title",
                                            children="Tren Harga Negara Terpilih",
                                            style={
                                                "fontSize": "15px",
                                                "fontWeight": "600",
                                                "color": "var(--text-main)",
                                                "margin": "0 0 2px 0",
                                            },
                                        ),
                                        html.Div(
                                            "Median harga bulanan (USD) seluruh komoditas, "
                                            "mengikuti rentang tahun pada header.",
                                            style={
                                                "fontSize": "12px",
                                                "color": LABEL_DARK,
                                                "margin": "0 0 8px 0",
                                            },
                                        ),
                                        dcc.Graph(
                                            id="country-trend-chart",
                                            config={"displayModeBar": False, "responsive": True},
                                        ),
                                    ],
                                    style={"flex": "58 1 0", "minWidth": "300px"},
                                ),
                            ],
                            style={
                                "display": "flex",
                                "flexWrap": "wrap",
                                "gap": "24px",
                                "marginTop": "28px",
                                "paddingTop": "20px",
                                "borderTop": "1px solid rgba(31, 42, 68, 0.08)",
                            },
                        ),
                    ]
                ),
            )
        ]
    )


@callback(
    Output("country-volatility-map", "figure"),
    Input("year-slider", "value"),
)
def update_country_map(year_range):
    year_start, year_end = _resolve_years(year_range)
    cv = _country_volatility_for_years(year_start, year_end).copy()
    cv["country_name"] = [_iso_to_name(iso) for iso in cv["countryiso3"]]

    if cv.empty:
        zmin, zmax = 0.0, 1.0
    else:
        zmin = float(cv["cv_index"].min())
        zmax = float(cv["cv_index"].max())

    fig = go.Figure(
        data=go.Choropleth(
            locations=cv["countryiso3"],
            z=cv["cv_index"],
            colorscale=[[p, h] for p, h in COLORSCALE],
            text=cv["country_name"],
            customdata=cv[["cv_index", "country_name", "countryiso3"]].values,
            hovertemplate="<b>%{customdata[1]}</b> (%{customdata[2]})<br>Indeks CV: %{customdata[0]:.3f}<extra></extra>",
            colorbar=dict(
                title=dict(text="Indeks CV", side="top"),
                thickness=12,
                len=0.55,
                x=0.97,
                xanchor="center",
                y=0.34,
                yanchor="middle",
                tickformat=".2f",
                tickfont=dict(size=10),
                ticks="outside",
                ticklen=3,
                outlinewidth=0,
            ),
            marker_line_width=0.4,
            marker_line_color="rgba(255, 255, 255, 0.85)",
            zmin=zmin,
            zmax=zmax,
        )
    )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=600,
        uirevision="geo-globe",
        geo=dict(
            projection_type="orthographic",
            projection_scale=INIT_SCALE,
            projection_rotation=dict(lon=INIT_LON, lat=INIT_LAT, roll=0),
            showland=True,
            landcolor="#e7e1d6",
            showocean=True,
            oceancolor="#aacbe5",
            showcoastlines=True,
            coastlinecolor="rgba(255, 255, 255, 0.9)",
            coastlinewidth=0.6,
            showcountries=True,
            countrycolor="rgba(255, 255, 255, 0.55)",
            countrywidth=0.4,
            showframe=True,
            framecolor="rgba(31, 42, 68, 0.22)",
            framewidth=1.0,
            lonaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.35)", gridwidth=0.4, dtick=30),
            lataxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.35)", gridwidth=0.4, dtick=30),
            bgcolor="rgba(0, 0, 0, 0)",
            domain=dict(x=[0.0, 0.9], y=[0.02, 0.98]),
        ),
        hovermode="closest",
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))

    return fig


clientside_callback(
    """
    function(zoomIn, zoomOut, reset) {
        var ctx = window.dash_clientside.callback_context;
        if (!ctx || !ctx.triggered || ctx.triggered.length === 0) {
            return window.dash_clientside.no_update;
        }
        var trigId = ctx.triggered[0].prop_id.split('.')[0];
        var gd = document.querySelector('#country-volatility-map .js-plotly-plot');
        if (!gd || !gd._fullLayout || !gd._fullLayout.geo) {
            return window.dash_clientside.no_update;
        }
        if (trigId === 'geo-reset-btn') {
            window.Plotly.relayout(gd, {
                'geo.projection.rotation.lon': 10,
                'geo.projection.rotation.lat': 12,
                'geo.projection.rotation.roll': 0,
                'geo.projection.scale': 0.92
            });
            return window.dash_clientside.no_update;
        }
        if (trigId !== 'zoom-in-btn' && trigId !== 'zoom-out-btn') {
            return window.dash_clientside.no_update;
        }
        var cur = 0.92;
        try {
            cur = gd._fullLayout.geo.projection.scale || 0.92;
        } catch (e) {
            cur = 0.92;
        }
        var factor = (trigId === 'zoom-in-btn') ? 1.3 : (1.0 / 1.3);
        var next = cur * factor;
        if (next < 0.5) { next = 0.5; }
        if (next > 5.0) { next = 5.0; }
        window.Plotly.relayout(gd, {'geo.projection.scale': next});
        return window.dash_clientside.no_update;
    }
    """,
    Output("geo-zoom-dummy", "data"),
    Input("zoom-in-btn", "n_clicks"),
    Input("zoom-out-btn", "n_clicks"),
    Input("geo-reset-btn", "n_clicks"),
)


@callback(
    Output("country-detail-info", "children"),
    Input("country-volatility-map", "clickData"),
    Input("year-slider", "value"),
)
def display_country_info(clickData, year_range):
    country_iso = _clicked_iso(clickData)
    if not country_iso:
        return _detail_placeholder()

    year_start, year_end = _resolve_years(year_range)
    cv = _country_volatility_for_years(year_start, year_end)
    country_data = cv[cv["countryiso3"] == country_iso]

    country_name = _iso_to_name(country_iso)

    if country_data.empty:
        return _detail_message(
            f"Tidak ada data untuk {country_name} ({country_iso}) "
            f"pada rentang tahun {year_start}-{year_end}."
        )

    row = country_data.iloc[0]

    cv_min = float(cv["cv_index"].min())
    cv_max = float(cv["cv_index"].max())
    t = 0.0 if cv_max == cv_min else (float(row["cv_index"]) - cv_min) / (cv_max - cv_min)
    base_rgb = _scale_color_rgb(t)
    border_hex = _rgb_to_hex(base_rgb)
    number_hex = _rgb_to_hex(_blend(base_rgb, (0, 0, 0), 0.45))
    bg_tint = "rgba(%d, %d, %d, 0.14)" % tuple(int(round(c)) for c in base_rgb)

    def stat(label, value):
        return html.Div(
            [
                html.Div(
                    label,
                    style={"fontSize": "11px", "color": LABEL_DARK, "marginBottom": "4px"},
                ),
                html.Div(
                    value,
                    style={
                        "fontSize": "20px",
                        "fontWeight": "600",
                        "color": "var(--text-main)",
                        "overflowWrap": "anywhere",
                    },
                ),
            ],
            style={
                "display": "flex",
                "flexDirection": "column",
                "justifyContent": "center",
                "minWidth": "0",
                "padding": "12px 14px",
                "backgroundColor": "var(--card-bg)",
                "borderRadius": "6px",
                "border": "1px solid rgba(31, 42, 68, 0.06)",
            },
        )

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        country_name,
                        style={
                            "fontSize": "18px",
                            "fontWeight": "700",
                            "color": "var(--text-main)",
                            "overflowWrap": "anywhere",
                        },
                    ),
                    html.Div(
                        f"{country_iso} \u00b7 {year_start}-{year_end}",
                        style={"fontSize": "12px", "color": LABEL_DARK, "fontWeight": "500", "marginTop": "2px"},
                    ),
                ],
                style={"marginBottom": "16px", "flex": "0 0 auto", "minWidth": "0"},
            ),
            html.Div(
                [
                    html.Span(
                        "Indeks Volatilitas (CV)",
                        style={"fontSize": "11px", "color": LABEL_DARK, "fontWeight": "500"},
                    ),
                    html.Div(
                        f"{row['cv_index']:.3f}",
                        style={
                            "fontSize": "30px",
                            "fontWeight": "700",
                            "color": number_hex,
                            "lineHeight": "1.1",
                            "overflowWrap": "anywhere",
                        },
                    ),
                ],
                style={
                    "padding": "14px 16px",
                    "backgroundColor": bg_tint,
                    "borderRadius": "8px",
                    "borderLeft": f"4px solid {border_hex}",
                    "marginBottom": "16px",
                    "flex": "0 0 auto",
                    "minWidth": "0",
                },
            ),
            html.Div(
                [
                    stat("Periode Data", f"{int(row['n_months'])} bulan"),
                    stat("Rata-rata Indeks", f"{row['mean_index']:.1f}"),
                    stat("Std. Deviasi Indeks", f"{row['std_index']:.1f}"),
                    stat("Rata-rata MoM", f"{row['mean_mom_change']:.2f}%"),
                    stat("Harga Median (USD)", f"${row['median_usdprice']:.4f}"),
                    stat("Std. MoM", f"{row['std_mom_change']:.2f}%"),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(110px, 1fr))",
                    "gridAutoRows": "1fr",
                    "gap": "10px",
                    "flex": "1 1 auto",
                    "minWidth": "0",
                },
            ),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "height": "100%",
            "minWidth": "0",
        },
    )


@callback(
    Output("country-top-commodities", "figure"),
    Output("country-top-commodities-sub", "children"),
    Input("country-volatility-map", "clickData"),
    Input("year-slider", "value"),
)
def update_top_commodities(clickData, year_range):
    country_iso = _clicked_iso(clickData)
    sub_default = "Berdasarkan koefisien variasi (CV) per komoditas."

    if not country_iso:
        return _empty_fig("Klik negara pada globe untuk melihat komoditasnya", 320), sub_default

    year_start, year_end = _resolve_years(year_range)
    cv = _commodity_volatility_for_country(country_iso, year_start, year_end)
    country_name = _iso_to_name(country_iso)
    sub_text = f"{country_name} ({country_iso}) \u00b7 {year_start}-{year_end}"

    if cv.empty:
        return _empty_fig("Tidak ada data komoditas pada rentang ini", 320), sub_text

    top = cv.head(10).reset_index(drop=True)
    top_colors = [SPECTRUM[4], SPECTRUM[3], SPECTRUM[2]]
    colors = [top_colors[i] if i < 3 else COLORS["text_sub"] for i in range(len(top))]

    top_rev = top.iloc[::-1]
    colors_rev = colors[::-1]
    vals = top_rev["cv_index"].tolist()
    labels = [COMMODITY_ID.get(c, c) for c in top_rev["commodity"].tolist()]

    fig = go.Figure(
        data=go.Bar(
            x=top_rev["cv_index"],
            y=labels,
            orientation="h",
            marker=dict(color=colors_rev, line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Indeks CV: %{x:.3f}<extra></extra>",
            cliponaxis=False,
        )
    )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=320,
        xaxis=dict(title="Indeks CV", showgrid=True, gridcolor="rgba(0,0,0,0.05)", zeroline=False),
        yaxis=dict(
            title="Komoditas",
            automargin=True,
            tickfont=dict(size=11),
            ticks="outside",
            ticklen=12,
            tickcolor="rgba(0,0,0,0)",
        ),
        bargap=0.35,
    )
    fig.update_layout(margin=dict(l=10, r=40, t=10, b=40))

    return fig, sub_text


@callback(
    Output("country-trend-chart", "figure"),
    Output("country-trend-title", "children"),
    Input("country-volatility-map", "clickData"),
    Input("year-slider", "value"),
)
def update_country_trend(clickData, year_range):
    country_iso = _clicked_iso(clickData)

    if not country_iso:
        return _empty_fig("Klik negara pada globe untuk menampilkan tren harganya", 320), "Tren Harga Negara Terpilih"

    df = get_country_detail(country_iso).copy()
    df["_year"] = pd.to_datetime(df["year_month"]).dt.year
    if year_range:
        df = df[(df["_year"] >= int(year_range[0])) & (df["_year"] <= int(year_range[1]))]

    country_name = _iso_to_name(country_iso)
    title = f"Tren Harga di {country_name} ({country_iso})"

    if df.empty:
        return _empty_fig("Tidak ada data pada rentang tahun ini", 320), title

    monthly = (
        df.groupby("year_month")["usdprice"].median().reset_index(name="median_price")
    )
    monthly = monthly.sort_values("year_month")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=monthly["year_month"],
            y=monthly["median_price"],
            mode="lines",
            name="Median Harga",
            line=dict(color=COLORS["spectrum_4"], width=2.5),
            hovertemplate="<b>%{x|%Y-%m}</b><br>Median: $%{y:.2f}<extra></extra>",
        )
    )

    if len(monthly) >= 6:
        monthly["smoothed"] = monthly["median_price"].rolling(6, center=True).mean()
        fig.add_trace(
            go.Scatter(
                x=monthly["year_month"],
                y=monthly["smoothed"],
                mode="lines",
                name="Rata-rata 6 bulan",
                line=dict(color=COLORS["text_sub"], width=1.5, dash="dash"),
                hovertemplate="<b>%{x|%Y-%m}</b><br>Smoothed: $%{y:.2f}<extra></extra>",
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=320,
        xaxis=dict(title="Tahun", showgrid=False, dtick="M12", tickformat="%Y-%m"),
        yaxis=dict(title="Harga (USD)", showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        hovermode="x unified",
        dragmode=False,
    )

    return fig, title