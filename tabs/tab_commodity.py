from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from utils.data_loader import (
    load_commodity_volatility,
    load_monthly_index,
    get_unique_commodities,
    get_commodity_monthly_trend,
)
from utils.components import (
    make_chart_card,
    PLOTLY_LAYOUT,
    COLORS,
    SPECTRUM,
)

COMMODITY_TREND_COLORS = ["#4F5D75", "#EF8D5A", "#CB573F"]


def commodity_layout():
    options = get_unique_commodities()
    default_picks = options[:3] if len(options) >= 3 else options
    while len(default_picks) < 3:
        default_picks.append(None)

    return html.Div(
        [
            make_chart_card(
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(id="volatile-title", className="volatile-title"),
                                html.Div(
                                    "Diurutkan berdasarkan koefisien variasi (CV) dari indeks harga",
                                    className="volatile-subtitle",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Small("Top N", className="volatile-dropdown-label"),
                                dcc.Dropdown(
                                    id="top-n-dropdown",
                                    options=[
                                        {"label": "5", "value": 5},
                                        {"label": "10", "value": 10},
                                        {"label": "20", "value": 20},
                                        {"label": "25", "value": 25},
                                    ],
                                    value=10,
                                    clearable=False,
                                    searchable=False,
                                    className="volatile-dropdown",
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ],
                            className="volatile-dropdown-group",
                        ),
                    ],
                    className="volatile-header",
                ),
                None,
                dcc.Graph(id="top-volatile-chart", config={"displayModeBar": False}),
                insight="Rice, soybeans, dan peas secara bergantian mendominasi peringkat atas volatilitas "
                        "sepanjang satu dekade terkahir, tetapi ketiganya menunjukkan pola yang sama berupa peningkatan "
                        "volatilitas yang saling terhubung.",
            ),
            make_chart_card(
                "Perbandingan Tren Komoditas",
                "Bandingkan tren harga tahunan untuk hingga tiga komoditas sekaligus",
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="commodity-dropdown-1",
                                        options=[{"label": c, "value": c} for c in options],
                                        value=default_picks[0],
                                        placeholder="Pilih komoditas",
                                        clearable=True,
                                    ),
                                    md=4,
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="commodity-dropdown-2",
                                        options=[{"label": c, "value": c} for c in options],
                                        value=default_picks[1],
                                        placeholder="Pilih komoditas",
                                        clearable=True,
                                    ),
                                    md=4,
                                ),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="commodity-dropdown-3",
                                        options=[{"label": c, "value": c} for c in options],
                                        value=default_picks[2],
                                        placeholder="Pilih komoditas",
                                        clearable=True,
                                    ),
                                    md=4,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dcc.Graph(id="commodity-trend-chart", config={"displayModeBar": False}),
                    ]
                ),
            ),
        ]
    )


@callback(
    Output("volatile-title", "children"),
    Input("top-n-dropdown", "value"),
)
def update_volatile_title(top_n):
    return f"Top {top_n} Komoditas Paling Volatil"


@callback(
    Output("top-volatile-chart", "figure"),
    Input("year-slider", "value"),
    Input("top-n-dropdown", "value"),
)
def update_top_volatile(year_range, top_n):
    try:
        top_n = int(top_n)
    except Exception:
        top_n = 10

    monthly = load_monthly_index()
    if year_range:
        monthly = monthly.copy()
        monthly["_year"] = pd.to_datetime(monthly["year_month"]).dt.year
        monthly = monthly[(monthly["_year"] >= year_range[0]) & (monthly["_year"] <= year_range[1])]

    if len(monthly) > 0:
        grp = monthly.groupby("commodity").agg(
            mean_index=("price_index", "mean"),
            std_index=("price_index", "std"),
            n_months=("price_index", "count"),
            median_usdprice=("usdprice", "median"),
        ).reset_index()
        grp["cv_index"] = grp["std_index"] / grp["mean_index"]
        grp = grp.replace([float("inf"), float("nan")], pd.NA).dropna(subset=["cv_index"])
        top = grp.sort_values("cv_index", ascending=False).head(top_n).reset_index(drop=True)
    else:
        df = load_commodity_volatility()
        top = df.sort_values("cv_index", ascending=False).head(top_n).reset_index(drop=True)

    top_colors = [SPECTRUM[4], SPECTRUM[3], SPECTRUM[2]]
    default_color = COLORS["text_sub"]
    colors = [top_colors[i] if i < 3 else default_color for i in range(len(top))]

    top_rev = top.iloc[::-1]
    colors_rev = colors[::-1]

    fig = go.Figure(
        data=go.Bar(
            x=top_rev["cv_index"],
            y=top_rev["commodity"],
            orientation="h",
            marker_color=colors_rev,
            hovertemplate="<b>%{y}</b><br>CV: %{x:.3f}<extra></extra>",
        )
    )

    layout = dict(**PLOTLY_LAYOUT)
    chart_height = max(420, top_n * 28)
    layout.update(
        height=chart_height,
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(title="Indeks CV", showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        yaxis=dict(
            title="Komoditas",
            automargin=True,
            tickfont=dict(size=11),
            ticks="outside",
            ticklen=12,
            tickcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
    )
    fig.update_layout(**layout)
    fig.update_yaxes(tickfont=dict(color=COLORS["text_main"], family="DM Sans, sans-serif", size=12), ticklabelstandoff=10)
    fig.update_xaxes(tickfont=dict(color=COLORS["text_main"], family="DM Sans, sans-serif", size=11))

    return fig


@callback(
    Output("commodity-trend-chart", "figure"),
    Input("year-slider", "value"),
    Input("commodity-dropdown-1", "value"),
    Input("commodity-dropdown-2", "value"),
    Input("commodity-dropdown-3", "value"),
)
def update_commodity_trend(year_range, commodity_1, commodity_2, commodity_3):
    selections = [commodity_1, commodity_2, commodity_3]
    selected = []
    for item in selections:
        if item and item not in selected:
            selected.append(item)

    fig = go.Figure()
    if not selected:
        fig.update_layout(
            **PLOTLY_LAYOUT, height=420,
            xaxis=dict(title="Tahun"), yaxis=dict(title="Harga (USD)"),
            annotations=[dict(
                text="Pilih minimal satu komoditas untuk menampilkan grafik.",
                x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font=dict(size=12),
            )],
        )
        return fig

    monthly = get_commodity_monthly_trend(selected)
    if year_range:
        monthly = monthly.copy()
        monthly["_year"] = pd.to_datetime(monthly["year_month"]).dt.year
        monthly = monthly[(monthly["_year"] >= year_range[0]) & (monthly["_year"] <= year_range[1])]
    monthly["_month"] = pd.to_datetime(monthly["year_month"])
    monthly_trend = (
        monthly.groupby(["commodity", "_month"])["usdprice"]
        .median().reset_index().sort_values("_month")
    )

    for idx, commodity in enumerate(selected):
        series = monthly_trend[monthly_trend["commodity"] == commodity]
        fig.add_trace(
            go.Scatter(
                x=series["_month"], y=series["usdprice"],
                mode="lines+markers", name=commodity,
                line=dict(color=COMMODITY_TREND_COLORS[idx % len(COMMODITY_TREND_COLORS)], width=2.5),
                marker=dict(size=6),
                hovertemplate="<b>%{x|%Y-%m}</b><br>Median: $%{y:.2f}<extra>%{fullData.name}</extra>",
            )
        )

    layout_kwargs = {
        **PLOTLY_LAYOUT,
        "margin": dict(b=40, l=40, r=20, t=40),
    }
    fig.update_layout(
        **layout_kwargs, height=420,
        xaxis=dict(title="Tahun", dtick="M12", tickformat="%Y-%m", showgrid=False),
        yaxis=dict(title="Harga (USD)", showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        hovermode="x unified",
    )
    return fig