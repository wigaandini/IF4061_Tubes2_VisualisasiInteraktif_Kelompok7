from dash import html
import dash_bootstrap_components as dbc

COLORS = {
    "bg": "#F7F6F2",
    "text_main": "#1F2A44",
    "text_sub": "#4F5D75",
    "highlight": "#D93A2F",
    "spectrum_1": "#F5C49C",
    "spectrum_2": "#EF8D5A",
    "spectrum_3": "#E26A4E",
    "spectrum_4": "#CB573F",
    "card_bg": "#FFFFFF",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color=COLORS["text_main"]),
    margin=dict(l=40, r=20, t=40, b=40),
    hoverlabel=dict(
        bgcolor=COLORS["text_main"],
        font_size=12,
        font_family="DM Sans, sans-serif",
        font_color="#fff",
    ),
)

SPECTRUM = ["#F5C49C", "#EF8D5A", "#E26A4E", "#CB573F", "#D93A2F"]

CATEGORY_COLORS = {
    "Serealia & Umbi": "#E69F00",
    "Daging, Ikan & Telur": "#56B4E9",
    "Sayuran & Buah": "#009E73",
    "Kacang-kacangan": "#D55E00",
    "Minyak & Lemak": "#0072B2",
    "Susu & Olahan Susu": "#CC79A7",
    "Pangan Lainnya": "#F0E442",
}


def make_kpi_card(value, label, accent_color=None):
    border_color = accent_color or COLORS["spectrum_2"]
    return html.Div(
        [
            html.Div(str(value), className="kpi-value"),
            html.Div(label, className="kpi-label"),
        ],
        className="kpi-card",
        style={"borderLeftColor": border_color},
    )


def make_chart_card(title, subtitle, chart_component, insight=None):
    children = [
        html.Div(title, className="chart-card-title"),
        html.Div(subtitle, className="chart-card-subtitle"),
        chart_component,
    ]
    if insight:
        children.append(html.Div(insight, className="insight-strip"))
    return html.Div(children, className="chart-card")


def make_page_header(title, subtitle):
    return html.Div(
        [
            html.H1(title, className="page-title"),
            html.P(subtitle, className="page-subtitle"),
        ]
    )


def make_filter_group(label, component):
    return html.Div(
        [
            html.Div(label, className="filter-label"),
            component,
        ],
        style={"marginBottom": "16px"},
    )


def make_info_note(text):
    return html.Div(
        [html.Span("ℹ ", style={"fontWeight": "700"}), text],
        style={
            "fontSize": "12px",
            "color": COLORS["text_sub"],
            "backgroundColor": "rgba(79, 93, 117, 0.06)",
            "borderRadius": "6px",
            "padding": "8px 12px",
            "marginBottom": "12px",
            "lineHeight": "1.5",
        },
    )