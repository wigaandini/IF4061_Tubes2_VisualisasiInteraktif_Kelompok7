import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from utils.data_loader import (
    get_unique_commodities,
    get_commodity_monthly_trend,
)
from utils.components import (
    make_page_header,
    make_filter_group,
    make_chart_card,
    PLOTLY_LAYOUT,
    SPECTRUM,
)

dash.register_page(__name__, path="/commodity-trends", name="Commodity Trends", order=1)


def _default_commodities(options):
    if not options:
        return [None, None, None]
    picks = options[:3]
    while len(picks) < 3:
        picks.append(None)
    return picks


def layout():
    options = get_unique_commodities()
    default_1, default_2, default_3 = _default_commodities(options)

    return html.Div(
        [
            make_page_header(
                "Commodity Trends",
                "Bandingkan tren harga tahunan untuk hingga tiga komoditas sekaligus.",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        make_filter_group(
                            "Komoditas 1",
                            dcc.Dropdown(
                                id="commodity-dropdown-1",
                                options=[{"label": c, "value": c} for c in options],
                                value=default_1,
                                placeholder="Pilih komoditas",
                                clearable=True,
                            ),
                        ),
                        md=4,
                    ),
                    dbc.Col(
                        make_filter_group(
                            "Komoditas 2",
                            dcc.Dropdown(
                                id="commodity-dropdown-2",
                                options=[{"label": c, "value": c} for c in options],
                                value=default_2,
                                placeholder="Pilih komoditas",
                                clearable=True,
                            ),
                        ),
                        md=4,
                    ),
                    dbc.Col(
                        make_filter_group(
                            "Komoditas 3",
                            dcc.Dropdown(
                                id="commodity-dropdown-3",
                                options=[{"label": c, "value": c} for c in options],
                                value=default_3,
                                placeholder="Pilih komoditas",
                                clearable=True,
                            ),
                        ),
                        md=4,
                    ),
                ],
                className="mb-3",
            ),
            make_chart_card(
                "Tren Harga Komoditas",
                "Harga median per tahun (USD) untuk komoditas terpilih",
                dcc.Graph(id="commodity-trend-chart", config={"displayModeBar": False}),
            ),
        ]
    )


@callback(
    Output("commodity-trend-chart", "figure"),
    Input("commodity-dropdown-1", "value"),
    Input("commodity-dropdown-2", "value"),
    Input("commodity-dropdown-3", "value"),
)
def update_commodity_trend(commodity_1, commodity_2, commodity_3):
    selections = [commodity_1, commodity_2, commodity_3]
    selected = []
    for item in selections:
        if item and item not in selected:
            selected.append(item)

    fig = go.Figure()
    if not selected:
        fig.update_layout(
            **PLOTLY_LAYOUT,
            height=420,
            xaxis=dict(title="Year"),
            yaxis=dict(title="Harga (USD)"),
            annotations=[
                dict(
                    text="Pilih minimal satu komoditas untuk menampilkan grafik.",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=12),
                )
            ],
        )
        return fig

    monthly = get_commodity_monthly_trend(selected)
    monthly["_year"] = pd.to_datetime(monthly["year_month"]).dt.year
    yearly = (
        monthly.groupby(["commodity", "_year"])["usdprice"]
        .median()
        .reset_index()
        .sort_values("_year")
    )

    for idx, commodity in enumerate(selected):
        series = yearly[yearly["commodity"] == commodity]
        fig.add_trace(
            go.Scatter(
                x=series["_year"],
                y=series["usdprice"],
                mode="lines+markers",
                name=commodity,
                line=dict(color=SPECTRUM[idx % len(SPECTRUM)], width=2.5),
                marker=dict(size=6),
                hovertemplate="<b>%{x}</b><br>%{y:.2f} USD<extra>%{fullData.name}</extra>",
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=420,
        xaxis=dict(title="Year", dtick=1, showgrid=False),
        yaxis=dict(title="Harga (USD)", showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        hovermode="x unified",
    )
    return fig
