from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from utils.data_loader import load_country_volatility
from utils.components import make_chart_card, PLOTLY_LAYOUT, COLORS


def geography_layout():
    return html.Div(
        [
            dcc.Store(id="geo-zoom-level", data=1.0),
            make_chart_card(
                "Persebaran Geografis Volatilitas Harga",
                "Koefisien variasi (CV) indeks harga pangan per negara — semakin merah, semakin volatil",
                html.Div(
                    [
                        html.Div(
                            style={
                                "position": "absolute",
                                "top": "12px",
                                "left": "12px",
                                "zIndex": "1000",
                                "display": "flex",
                                "gap": "4px",
                            },
                            children=[
                                html.Button(
                                    "+",
                                    id="zoom-in-btn",
                                    style={
                                        "padding": "8px 12px",
                                        "backgroundColor": "#1F2A44",
                                        "color": "white",
                                        "border": "none",
                                        "borderRadius": "4px",
                                        "cursor": "pointer",
                                        "fontSize": "14px",
                                        "fontWeight": "bold",
                                    }
                                ),
                                html.Button(
                                    "-",
                                    id="zoom-out-btn",
                                    style={
                                        "padding": "8px 12px",
                                        "backgroundColor": "#1F2A44",
                                        "color": "white",
                                        "border": "none",
                                        "borderRadius": "4px",
                                        "cursor": "pointer",
                                        "fontSize": "14px",
                                        "fontWeight": "bold",
                                    }
                                ),
                            ]
                        ),
                        dcc.Graph(id="country-volatility-map", config={
                            "displayModeBar": False,
                            "scrollZoom": False,
                        }, style={"margin": "0"}),
                        html.Div(id="country-detail-info", style={
                            "marginTop": "12px",
                            "padding": "16px",
                            "backgroundColor": "rgba(31, 42, 68, 0.03)",
                            "borderRadius": "6px",
                            "minHeight": "80px",
                        })
                    ],
                    style={"position": "relative"}
                ),
            )
        ]
    )


@callback(
    Output("country-volatility-map", "figure"),
    Input("year-slider", "value"),
    Input("geo-zoom-level", "data"),
)
def update_country_map(year_range, zoom_level):
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
            customdata=cv[["cv_index", "country_name", "countryiso3"]].values,
            hovertemplate="<b>%{customdata[1]}</b> (%{customdata[2]})<br>CV Index: %{customdata[0]:.3f}<extra></extra>",
            colorbar=dict(title="CV Index", thickness=12, len=0.9, tickformat=".3f"),
            marker_line_width=0.5,
            marker_line_color="rgba(255, 255, 255, 0.5)",
        )
    )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=650,
        geo=dict(
            projection_type="orthographic",
            projection_scale=zoom_level,
            showland=True,
            landcolor="#d8d3cb",
            showcoastlines=True,
            coastlinecolor="#D2DADC",
            showcountries=True,
            countrycolor="#D2DADC",
            countrywidth=0.5,
            bgcolor="rgba(200, 220, 240, 0.3)",
        ),
        hovermode="closest",
    )

    return fig


@callback(
    Output("geo-zoom-level", "data"),
    Input("zoom-in-btn", "n_clicks"),
    Input("zoom-out-btn", "n_clicks"),
    State("geo-zoom-level", "data"),
)
def handle_zoom_buttons(zoom_in_clicks, zoom_out_clicks, current_zoom):
    current_zoom = current_zoom or 1.0
    
    # Determine which button was clicked
    if zoom_in_clicks and zoom_out_clicks:
        # Both have been clicked, check which one was clicked more recently
        diff = zoom_in_clicks - zoom_out_clicks
    elif zoom_in_clicks:
        diff = 1
    elif zoom_out_clicks:
        diff = -1
    else:
        diff = 0
    
    # Update zoom level (min 0.5, max 3.0)
    new_zoom = max(0.5, min(3.0, current_zoom + (diff * 0.3)))
    
    return new_zoom


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