import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from utils.data_loader import (
    load_commodity_volatility,
    load_country_volatility,
    load_category_heatmap,
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
