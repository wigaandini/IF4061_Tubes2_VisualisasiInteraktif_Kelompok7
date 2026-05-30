import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc

from utils.data_loader import get_year_range
from utils.components import COLORS
from tabs.tab_overview import overview_layout
from tabs.tab_commodity import commodity_layout
from tabs.tab_geography import geography_layout

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="Dinamika Pasar Pangan Global",
)

server = app.server

min_year, max_year = get_year_range()

header = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1("Dinamika Pasar Pangan Global", className="header-title"),
                        html.P(
                            "Volatilitas & Resiliensi Harga Pangan Dunia 2016–2026",
                            className="header-subtitle",
                        ),
                    ],
                    md=5,
                    className="d-flex flex-column justify-content-center",
                ),
                dbc.Col(
                    [
                        html.Div("RENTANG TAHUN", className="filter-label"),
                        dcc.RangeSlider(
                            id="year-slider",
                            min=min_year,
                            max=max_year,
                            step=1,
                            value=[min_year, max_year],
                            marks={y: str(y) for y in range(min_year, max_year + 1, 2)},
                            tooltip={"placement": "bottom"},
                        ),
                    ],
                    md=7,
                    className="d-flex flex-column justify-content-center",
                ),
            ],
            align="center",
        ),
    ],
    className="sticky-header",
)

tabs = dbc.Tabs(
    [
        dbc.Tab(overview_layout(), label="Gambaran Umum", tab_id="overview"),
        dbc.Tab(commodity_layout(), label="Komoditas", tab_id="commodity"),
        dbc.Tab(geography_layout(), label="Geografi", tab_id="geography"),
    ],
    id="main-tabs",
    active_tab="overview",
    className="dashboard-tabs",
)

footer = html.Div(
    [
        html.Span("Sumber: WFP Global Food Prices Database • CC BY-IGO"),
        html.Span(" · "),
        html.Span("Kelompok 7 — IF4061 Visualisasi Data • ITB 2026"),
    ],
    className="dashboard-footer",
)

app.layout = html.Div(
    [
        header,
        html.Div(tabs, className="main-content"),
        footer,
    ],
    className="app-container",
)

import tabs.tab_overview
import tabs.tab_commodity
import tabs.tab_geography

if __name__ == "__main__":
    app.run(debug=True, port=8050)