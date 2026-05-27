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
                                "Lonjakan harga terjadi bersamaan dengan guncangan global — pandemi COVID-19 "
                                "dan konflik Rusia–Ukraina meninggalkan jejak yang konsisten pada harga pangan dunia.",
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
                "Perubahan harga month-over-month (%) per kategori — semakin gelap, semakin bergejolak",
                dcc.Graph(id="category-heatmap", config={"displayModeBar": False}),
            ),
            make_chart_card(
                "Persebaran Geografis Volatilitas Harga",
                "Koefisien variasi (CV) indeks harga pangan per negara — semakin merah, semakin volatil",
                html.Div(
                    [
                        dcc.Graph(id="country-volatility-map", config={"displayModeBar": False}, style={"margin": "0"}),
                        html.Div(id="country-detail-info", style={
                            "marginTop": "12px",
                            "padding": "16px",
                            "backgroundColor": "rgba(31, 42, 68, 0.03)",
                            "borderRadius": "6px",
                            "minHeight": "80px",
                        })
                    ]
                ),
            ),
        ]
    )


@callback(
    Output("category-heatmap", "figure"),
    Input("year-slider", "value"),
)
def update_heatmap(year_range):
    hm = load_category_heatmap()

    hm_filtered = hm.copy()
    hm_filtered["_year"] = pd.to_datetime(hm_filtered["year_month"]).dt.year
    
    hm_filtered = hm_filtered[
        (hm_filtered["_year"] >= 2016) & (hm_filtered["_year"] <= hm_filtered["_year"].max())
    ]

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
        except:
            pass

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=x_positions,
            y=[c.title() for c in pivot.index.tolist()],
            colorscale=[
                [0, "#F7F6F2"], [0.25, COLORS["spectrum_1"]],
                [0.5, COLORS["spectrum_2"]], [0.75, COLORS["spectrum_3"]],
                [1, COLORS["spectrum_4"]],
            ],
            customdata=x_labels,
            hovertemplate="<b>%{y}</b><br>Bulan: %{customdata}<br>MoM Change: %{z:.1f}%<extra></extra>",
            colorbar=dict(title="MoM %", titleside="right", thickness=12, len=0.9),
        )
    )
    
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=420,
        xaxis=dict(
            title=None,
            showgrid=False,
            tickangle=-45,
            tickmode='array',
            tickvals=tickvals,
            ticktext=ticktext,
            tickfont=dict(size=8),
            showticklabels=True,
            range=[-2, len(x_positions) - 1],
        ),
        yaxis=dict(title=None, showgrid=False),
    )
    
    current_margin = fig.layout.margin
    fig.update_layout(margin=dict(l=80, r=current_margin.r, t=current_margin.t, b=100))
    return fig


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
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11)
        ),
        hovermode="x unified",
        dragmode=False,
    )
    return fig


@callback(
    Output("country-volatility-map", "figure"),
    Input("year-slider", "value"),
)
def update_country_map(year_range):
    cv = load_country_volatility()
    
    try:
        import pycountry
        country_names = {}
        for idx, iso3 in enumerate(cv["countryiso3"]):
            try:
                country = pycountry.countries.get(alpha_3=iso3)
                country_names[idx] = country.name if country else iso3
            except:
                country_names[idx] = iso3
        cv["country_name"] = [country_names.get(i, iso) for i, iso in enumerate(cv["countryiso3"])]
    except:
        cv["country_name"] = cv["countryiso3"]
    
    fig = go.Figure(
        data=go.Choropleth(
            locations=cv["countryiso3"],
            z=cv["cv_index"],
            colorscale=[
                [0, "#f4c39b"],
                [0.33, "#ee8d59"],
                [0.66, "#e1694d"],
                [1, "#d8392e"],
            ],
            text=cv["country_name"],
            customdata=cv[["cv_index", "country_name", "countryiso3"]],
            hovertemplate="<b>%{customdata[1]}</b> (%{customdata[2]})<br>CV Index: %{customdata[0]:.3f}<extra></extra>",
            colorbar=dict(
                title="CV Index",
                thickness=12,
                len=0.9,
                tickformat=".3f"
            ),
            marker_line_width=0.5,
            marker_line_color="rgba(255, 255, 255, 0.5)",
        )
    )
    
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=650,
        geo=dict(
            projection_type="natural earth",
            showland=True,
            landcolor="#d8d3cb",
            showcoastlines=True,
            coastlinecolor="#D2DADC",
            showcountries=True,
            countrycolor="#D2DADC",
            countrywidth=0.5,
        ),
        hovermode="closest",
    )
    
    return fig


@callback(
    Output("country-detail-info", "children"),
    Input("country-volatility-map", "clickData"),
)
def display_country_info(clickData):
    if not clickData or "points" not in clickData or len(clickData["points"]) == 0:
        return html.Div(
            "Klik pada negara di peta untuk melihat detail informasi",
            style={"color": "var(--text-sub)", "fontSize": "13px", "fontStyle": "italic"}
        )
    
    point = clickData["points"][0]
    country_iso = point.get("location")
    
    if not country_iso:
        return "Informasi tidak tersedia"
    
    cv = load_country_volatility()
    country_data = cv[cv["countryiso3"] == country_iso]
    
    if country_data.empty:
        return "Data negara tidak ditemukan"
    
    row = country_data.iloc[0]
    
    try:
        import pycountry
        country = pycountry.countries.get(alpha_3=country_iso)
        country_name = country.name if country else country_iso
    except:
        country_name = country_iso
    
    return html.Div(
        [
            html.H6(
                f"{country_name} ({country_iso})",
                style={"margin": "0 0 12px 0", "fontSize": "16px", "fontWeight": "600", "color": "var(--text-main)"}
            ),
            html.Div(
                [
                    html.Div([
                        html.Span("Indeks Volatilitas (CV):", style={"fontWeight": "500"}),
                        html.Span(f"{row['cv_index']:.3f}", style={"marginLeft": "8px", "color": "var(--highlight)", "fontWeight": "600"})
                    ], style={"marginBottom": "8px", "fontSize": "13px"}),
                    html.Div([
                        html.Span("Jumlah Periode Data:", style={"fontWeight": "500"}),
                        html.Span(f"{int(row['n_months'])} bulan", style={"marginLeft": "8px"})
                    ], style={"marginBottom": "8px", "fontSize": "13px"}),
                    html.Div([
                        html.Span("Rata-rata Harga Indeks:", style={"fontWeight": "500"}),
                        html.Span(f"${row['mean_index']:.2f}", style={"marginLeft": "8px"})
                    ], style={"marginBottom": "8px", "fontSize": "13px"}),
                    html.Div([
                        html.Span("Standar Deviasi Indeks:", style={"fontWeight": "500"}),
                        html.Span(f"{row['std_index']:.2f}", style={"marginLeft": "8px"})
                    ], style={"marginBottom": "8px", "fontSize": "13px"}),
                    html.Div([
                        html.Span("Rata-rata Perubahan MoM:", style={"fontWeight": "500"}),
                        html.Span(f"{row['mean_mom_change']:.2f}%", style={"marginLeft": "8px"})
                    ], style={"marginBottom": "8px", "fontSize": "13px"}),
                    html.Div([
                        html.Span("Harga Median (USD):", style={"fontWeight": "500"}),
                        html.Span(f"${row['median_usdprice']:.4f}", style={"marginLeft": "8px"})
                    ], style={"marginBottom": "0px", "fontSize": "13px"}),
                ],
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"}
            )
        ]
    )