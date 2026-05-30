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
    get_category_heatmap_data,
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
            )
        ]
    )


@callback(
    Output("category-heatmap", "figure"),
    Input("year-slider", "value"),
)
def update_heatmap(year_range):
    if year_range:
        start_year, end_year = int(year_range[0]), int(year_range[1])
    else:
        start_year, end_year = get_year_range()

    hm_filtered = get_category_heatmap_data((start_year, end_year))

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
            title=None,
            showgrid=False,
            tickangle=-45,
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            tickfont=dict(size=8),
            showticklabels=True,
            autorange=True,
        ),
        yaxis=dict(
            title=None,
            showgrid=False,
            autorange=True,
        ),
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