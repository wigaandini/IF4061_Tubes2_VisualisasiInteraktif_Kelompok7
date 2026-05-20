import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="Food Price Volatility Dashboard",
)

server = app.server

SIDEBAR_STYLE = {
    "width": "240px",
    "minHeight": "100vh",
    "background": "#1F2A44",
    "position": "fixed",
    "top": 0,
    "left": 0,
    "zIndex": 100,
    "overflowY": "auto",
}

sidebar = html.Div(
    [
        html.Div(
            [
                html.H4(
                    "WFP Food Prices",
                    style={"color": "#F7F6F2", "fontWeight": "700", "marginBottom": "4px"},
                ),
                html.P(
                    "Global Volatility Dashboard",
                    style={"color": "#F5C49C", "fontSize": "13px", "marginBottom": "0"},
                ),
                html.P(
                    "2016 – 2026",
                    style={"color": "#4F5D75", "fontSize": "12px"},
                ),
            ],
            style={"padding": "24px 20px 16px"},
        ),
        html.Hr(style={"borderColor": "#2a3a5c", "margin": "0 20px"}),
        dbc.Nav(
            [
                dbc.NavLink(
                    [html.Span("📊", style={"marginRight": "10px"}), "Overview"],
                    href="/",
                    active="exact",
                    className="sidebar-link",
                ),
                # === Halaman tim lain (akan ditambahkan oleh masing-masing) ===
                # dbc.NavLink([html.Span("🌾"), " Commodity Explorer"], href="/commodity", active="exact", className="sidebar-link"),
                # dbc.NavLink([html.Span("🌍"), " Geographic Explorer"], href="/geography", active="exact", className="sidebar-link"),
                # dbc.NavLink([html.Span("🔬"), " Deep Dive"], href="/deep-dive", active="exact", className="sidebar-link"),
                # dbc.NavLink([html.Span("ℹ️"), " About"], href="/about", active="exact", className="sidebar-link"),
            ],
            vertical=True,
            pills=True,
            style={"padding": "16px 12px"},
        ),
        html.Div(
            [
                html.Hr(style={"borderColor": "#2a3a5c", "margin": "0 8px 12px"}),
                html.P(
                    "Kelompok 7 — IF4061",
                    style={"color": "#4F5D75", "fontSize": "11px", "textAlign": "center"},
                ),
                html.P(
                    "Institut Teknologi Bandung",
                    style={"color": "#4F5D75", "fontSize": "11px", "textAlign": "center", "marginTop": "-8px"},
                ),
            ],
            style={"position": "absolute", "bottom": "16px", "width": "100%"},
        ),
    ],
    style=SIDEBAR_STYLE,
    className="sidebar",
)

content = html.Div(
    dash.page_container,
    className="main-content",
)

app.layout = html.Div(
    [
        dcc.Location(id="url"),
        sidebar,
        content,
    ],
    className="app-container",
)

if __name__ == "__main__":
    app.run(debug=True, port=8050)
