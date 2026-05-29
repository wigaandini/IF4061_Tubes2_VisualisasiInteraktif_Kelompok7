import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from utils.data_loader import (
    load_commodity_volatility,
    load_country_volatility,
    load_category_heatmap,
    load_monthly_index,
    get_global_monthly_trend,
    get_unique_categories,
    get_year_range,
)
from utils.components import (
    make_kpi_card,
    make_chart_card,
    make_page_header,
    make_filter_group,
    PLOTLY_LAYOUT,
    COLORS,
    SPECTRUM,
)

dash.register_page(__name__, path="/", name="Overview", order=0)

EVENTS = [
    {"date": "2020-03", "label": "COVID-19"},
    {"date": "2022-02", "label": "Russia-Ukraine War"},
    {"date": "2023-06", "label": "El Niño Peak"},
]


def layout():
    cv_comm = load_commodity_volatility()
    cv_country = load_country_volatility()
    min_year, max_year = get_year_range()

    n_commodities = cv_comm["commodity"].nunique()
    n_countries = cv_country["countryiso3"].nunique()
    top_volatile = cv_comm.nlargest(1, "cv_index")["commodity"].values[0]
    top_cv = cv_comm["cv_index"].max()

    return html.Div(
        [
            make_page_header(
                "Dinamika Pasar Pangan Global",
                "Memetakan volatilitas dan resiliensi harga pangan dunia selama satu dekade (2016–2026).",
            ),
            dbc.Row(
                [
                    dbc.Col(make_kpi_card(n_commodities, "Komoditas", COLORS["spectrum_2"]), md=3),
                    dbc.Col(make_kpi_card(n_countries, "Negara", COLORS["spectrum_3"]), md=3),
                    dbc.Col(make_kpi_card(f"{top_cv:.2f}", "CV Tertinggi", COLORS["spectrum_4"]), md=3),
                    dbc.Col(make_kpi_card(top_volatile, "Paling Volatil", COLORS["highlight"]), md=3),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        make_filter_group(
                            "Rentang Tahun",
                            dcc.RangeSlider(
                                id="year-slider",
                                min=min_year, max=max_year, step=1,
                                value=[min_year, max_year],
                                marks={y: str(y) for y in range(min_year, max_year + 1)},
                                tooltip={"placement": "bottom"},
                            ),
                        ),
                        md=12,
                    ),
                ],
                className="mb-3",
            ),
            make_chart_card(
                "Tren Harga Pangan Global",
                "Median harga bulanan (USD) seluruh komoditas pangan, dengan penanda event global",
                dcc.Graph(id="global-trend-chart", config={"displayModeBar": False}),
                insight="Lonjakan harga terjadi bersamaan dengan guncangan global — pandemi COVID-19 "
                        "dan konflik Rusia–Ukraina meninggalkan jejak yang konsisten pada harga pangan dunia.",
            ),
            make_chart_card(
                "Intensitas Gejolak per Kategori Pangan",
                "Perubahan harga month-over-month (%) per kategori — semakin gelap, semakin bergejolak",
                dcc.Graph(id="category-heatmap", config={"displayModeBar": False}),
            ),
            make_chart_card(
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    id="volatile-title",
                                    className="volatile-title",
                                ),

                                html.Div(
                                    "Diurutkan berdasarkan koefisien variasi (CV) dari indeks harga",
                                    className="volatile-subtitle",
                                ),
                            ]
                        ),

                        html.Div(
                            [
                                html.Small(
                                    "Top N",
                                    className="volatile-dropdown-label",
                                ),

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

                dcc.Graph(
                    id="top-volatile-chart",
                    config={"displayModeBar": False},
                ),
                insight="Rice, soybeans, dan peas secara bergantian mendominasi peringkat atas volatilitas sepanjang 2016-2026, tetapi ketiganya menunjukkan pola yang sama berupa peningkatan volatilitas yang saling terhubung. Hal ini mencerminkan pergeseran titik tekanan dalam sistem pangan global yang semakin berkaitan sejak 2016."
            )
        ]
    )


@callback(
    Output("global-trend-chart", "figure"),
    Input("year-slider", "value"),
)

def update_trend(year_range):
    monthly = get_global_monthly_trend(year_range)

    fig = go.Figure()

    for event in EVENTS:
        if len(monthly) > 0 and event["date"] >= monthly["year_month"].min() and event["date"] <= monthly["year_month"].max():
            fig.add_vrect(
                x0=event["date"], x1=event["date"],
                line_width=2, line_dash="dot", line_color=COLORS["highlight"],
                annotation_text=event["label"],
                annotation_position="top left",
                annotation_font_size=10,
                annotation_font_color=COLORS["text_sub"],
            )

    fig.add_trace(
        go.Scatter(
            x=monthly["year_month"], y=monthly["median_price"],
            mode="lines", name="Median Harga",
            line=dict(color=COLORS["spectrum_4"], width=2.5),
            hovertemplate="<b>%{x}</b><br>Median: $%{y:.2f}<extra></extra>",
        )
    )

    if len(monthly) >= 6:
        monthly["smoothed"] = monthly["median_price"].rolling(6, center=True).mean()
        fig.add_trace(
            go.Scatter(
                x=monthly["year_month"], y=monthly["smoothed"],
                mode="lines", name="Rata-rata 6 bulan",
                line=dict(color=COLORS["text_sub"], width=1.5, dash="dash"),
                hovertemplate="<b>%{x}</b><br>Smoothed: $%{y:.2f}<extra></extra>",
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT, height=380,
        xaxis=dict(title=None, showgrid=False, dtick="M12", tickformat="%Y-%m"),
        yaxis=dict(title="Median Harga (USD)", showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        hovermode="x unified",
    )
    return fig

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
        grp = grp.replace([float("inf"), float("nan")], pd.NA).dropna(subset=["cv_index"])  # drop invalid
        top = grp.sort_values("cv_index", ascending=False).head(top_n).reset_index(drop=True)
    else:
        # fallback to precomputed if no monthly data in range
        df = load_commodity_volatility()
        top = df.sort_values("cv_index", ascending=False).head(top_n).reset_index(drop=True)

    # emphasize top 3 thru color
    top_colors = [SPECTRUM[4], SPECTRUM[3], SPECTRUM[2]]
    default_color = COLORS["text_sub"]
    colors = [top_colors[i] if i < 3 else default_color for i in range(len(top))]

    # reverse so largest appears on top for horizontal bar
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
        xaxis=dict(
            title="Indeks CV",
            showgrid=True,
            gridcolor="rgba(0,0,0,0.05)"
        ),
        yaxis=dict(
            title=None,
            automargin=True
        ),
        showlegend=False,
    )
    fig.update_layout(**layout)

    fig.update_yaxes(tickfont=dict(color=COLORS["text_main"], family="DM Sans, sans-serif", size=12), ticklabelstandoff=10)
    fig.update_xaxes(tickfont=dict(color=COLORS["text_main"], family="DM Sans, sans-serif", size=11))

    return fig


@callback(
    Output("category-heatmap", "figure"),
    Input("year-slider", "value"),
)
def update_heatmap(year_range):
    hm = load_category_heatmap()

    hm_filtered = hm.copy()
    hm_filtered["_year"] = pd.to_datetime(hm_filtered["year_month"]).dt.year
    hm_filtered = hm_filtered[
        (hm_filtered["_year"] >= year_range[0]) & (hm_filtered["_year"] <= year_range[1])
    ]

    pivot = hm_filtered.pivot_table(
        index="category", columns="year_month", values="mom_change_pct", aggfunc="mean"
    )
    pivot = pivot.sort_index()

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=[c.title() for c in pivot.index.tolist()],
            colorscale=[
                [0, "#F7F6F2"], [0.25, COLORS["spectrum_1"]],
                [0.5, COLORS["spectrum_2"]], [0.75, COLORS["spectrum_3"]],
                [1, COLORS["spectrum_4"]],
            ],
            hovertemplate="<b>%{y}</b><br>Bulan: %{x}<br>MoM Change: %{z:.1f}%<extra></extra>",
            colorbar=dict(title="MoM %", titleside="right", thickness=12, len=0.9),
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT, height=320,
        xaxis=dict(title=None, showgrid=False, dtick=6, tickangle=-45),
        yaxis=dict(title=None, showgrid=False),
    )
    return fig
