from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from utils.data_loader import (
    load_category_heatmap,
    get_global_monthly_trend,
    get_year_range,
    compute_kpis,
    get_category_volatility_ranking,
)
from utils.components import (
    make_kpi_card,
    make_chart_card,
    PLOTLY_LAYOUT,
    COLORS,
)

EVENTS = [
    {"date": "2020-03", "label": "COVID-19"},
    {"date": "2022-02", "label": "Russia-Ukraine War"},
    {"date": "2023-06", "label": "El Niño Peak"},
]


def overview_layout():
    return html.Div(
        [
            dbc.Row(id="kpi-row", className="mb-4"),
            html.Div(
                [
                    html.Div(
                        [
                            html.H5(
                                "Tren Harga Pangan Global",
                                style={"margin": "0 0 4px 0", "fontSize": "16px", "fontWeight": "600"}
                            ),
                            html.P(
                                "Median harga bulanan (USD) seluruh komoditas pangan, dengan penanda event global",
                                style={"margin": "0 0 12px 0", "fontSize": "13px", "color": "var(--text-sub)"}
                            ),
                        ],
                        style={"marginBottom": "12px"}
                    ),
                    dcc.Graph(
                        id="global-trend-chart",
                        config={"displayModeBar": False, "responsive": True}
                    ),
                    html.Div(
                        [
                            html.P(
                                "Lonjakan harga terjadi bersamaan dengan guncangan global, seperti pandemi COVID-19 "
                                "dan konflik Rusia-Ukraina, meninggalkan jejak yang konsisten pada harga pangan dunia.",
                                style={
                                    "margin": "12px 0 0 0",
                                    "padding": "12px 16px",
                                    "borderLeft": "4px solid var(--highlight)",
                                    "backgroundColor": "rgba(217, 58, 47, 0.05)",
                                    "fontSize": "13px",
                                    "color": "var(--text-main)",
                                    "borderRadius": "4px",
                                }
                            ),
                        ]
                    ),
                ],
                style={
                    "backgroundColor": "var(--card-bg)",
                    "borderRadius": "8px",
                    "padding": "20px",
                    "boxShadow": "0 1px 3px rgba(31, 42, 68, 0.08)",
                    "marginBottom": "24px",
                }
            ),
            make_chart_card(
                "Intensitas Gejolak per Kategori Pangan",
                "Perubahan harga month-over-month (%) per kategori, semakin gelap, semakin bergejolak",
                html.Div(
                    [
                        dcc.Graph(id="category-heatmap", config={"displayModeBar": False}),
                        html.Div(id="heatmap-insight"),
                    ]
                ),
            ),
        ]
    )


@callback(
    Output("kpi-row", "children"),
    Input("year-slider", "value"),
)
def update_kpis(year_range):
    kpis = compute_kpis(year_range)
    lonjakan = f"+{kpis['lonjakan_pct']:.0f}%"
    return [
        dbc.Col(make_kpi_card(lonjakan, "Lonjakan Harga Tertinggi", COLORS["highlight"]), md=3),
        dbc.Col(make_kpi_card(kpis["top_volatile"], "Komoditas Paling Volatil", COLORS["spectrum_4"]), md=3),
        dbc.Col(make_kpi_card(kpis["top_country"], "Negara Paling Rentan", COLORS["spectrum_3"]), md=3),
        dbc.Col(make_kpi_card(kpis["top_category"], "Kategori Paling Bergejolak", COLORS["spectrum_2"]), md=3),
    ]


@callback(
    Output("global-trend-chart", "figure"),
    Input("year-slider", "value"),
)
def update_trend_with_zoom(year_range):
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
        **PLOTLY_LAYOUT,
        height=380,
        xaxis=dict(title=None, showgrid=False, dtick="M12", tickformat="%Y-%m"),
        yaxis=dict(title="Median Harga (USD)", showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        hovermode="x unified",
        dragmode=False,
    )
    return fig


@callback(
    Output("category-heatmap", "figure"),
    Input("year-slider", "value"),
)
def update_heatmap(year_range):
    hm = load_category_heatmap()

    if year_range:
        start_year, end_year = int(year_range[0]), int(year_range[1])
    else:
        start_year, end_year = get_year_range()

    hm_filtered = hm.copy()
    hm_filtered["_year"] = pd.to_datetime(hm_filtered["year_month"]).dt.year
    hm_filtered = hm_filtered[(hm_filtered["_year"] >= start_year) & (hm_filtered["_year"] <= end_year)]

    pivot = hm_filtered.pivot_table(
        index="category", columns="year_month", values="mom_change_pct", aggfunc="mean", dropna=False
    )
    pivot = pivot.sort_index()

    x_labels = pivot.columns.tolist()
    x_positions = list(range(len(x_labels)))

    tickvals = []
    ticktext = []
    for i, label in enumerate(x_labels):
        try:
            date = pd.to_datetime(label)
            if date.month == 1:
                tickvals.append(i)
                ticktext.append(str(date.year))
        except (ValueError, TypeError):
            pass

    bulan_id = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober", 11: "November", 12: "Desember",
    }
    x_display = []
    for label in x_labels:
        try:
            d = pd.to_datetime(label)
            x_display.append(f"{bulan_id[d.month]} {d.year}")
        except (ValueError, TypeError):
            x_display.append(str(label))

    customdata = [list(x_display) for _ in range(len(pivot.index))]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=x_positions,
            y=[c.title() for c in pivot.index.tolist()],
            colorscale=[
                [0, "#F7F6F2"],
                [0.33, "#F4A261"],
                [0.66, "#E76F51"],
                [1, "#C8553D"],
            ],
            customdata=customdata,
            hovertemplate="<b>%{y}</b><br>Bulan: %{customdata}<br>MoM Change: %{z:.1f}%<extra></extra>",
            colorbar=dict(title="MoM %", titleside="right", thickness=12, len=0.9),
        )
    )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=420,
        uirevision=f"heatmap-{start_year}-{end_year}",
        dragmode="zoom",
        xaxis=dict(
            title=dict(text="Tahun", standoff=14),
            showgrid=False,
            tickangle=0,
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            tickfont=dict(size=10),
            showticklabels=True,
            autorange=True,
        ),
        yaxis=dict(
            title=dict(text="Kategori", standoff=18),
            showgrid=False,
            autorange=True,
            automargin=True,
            ticklabelstandoff=10,
        ),
    )

    current_margin = fig.layout.margin
    fig.update_layout(margin=dict(l=80, r=current_margin.r, t=current_margin.t, b=45))
    return fig

@callback(
    Output("heatmap-insight", "children"),
    Input("year-slider", "value"),
)
def update_heatmap_insight(year_range):
    if year_range:
        start_year, end_year = int(year_range[0]), int(year_range[1])
    else:
        start_year, end_year = get_year_range()

    ranking = get_category_volatility_ranking((start_year, end_year), top_n=3)

    if not ranking:
        return html.P(
            f"Tidak ada data kategori pada rentang periode {start_year} hingga {end_year}.",
            style={"margin": "0", "fontSize": "13px", "color": "var(--text-sub)"},
        )

    items = [
        html.Li(
            [
                html.Span(f"{cat.title()}", style={"fontWeight": "600"}),
                html.Span(f" ({val:.2f}%)", style={"color": "var(--highlight)", "fontWeight": "600"}),
            ],
            style={"marginBottom": "4px", "fontSize": "13px", "color": "var(--text-main)"},
        )
        for cat, val in ranking
    ]

    top_cat, top_val = ranking[0]

    return html.Div(
        [
            html.P(
                [
                    f"Pada rentang periode {start_year} hingga {end_year}, ",
                    html.Span(
                        top_cat.title(),
                        style={"color": "var(--highlight)", "fontWeight": "600"},
                    ),
                    " menjadi kategori pangan paling bergejolak."
                    " Tiga kategori dengan gejolak harga tertinggi (rata-rata absolut perubahan MoM) adalah:",
                ],
                style={"margin": "0 0 8px 0", "fontSize": "13px", "color": "var(--text-main)"},
            ),
            html.Ul(items, style={"margin": "0", "paddingLeft": "20px"}),
        ],
        style={
            "margin": "4px 0 0 0",
            "padding": "12px 16px",
            "borderLeft": "4px solid var(--highlight)",
            "backgroundColor": "rgba(217, 58, 47, 0.05)",
            "borderRadius": "4px",
        },
    )