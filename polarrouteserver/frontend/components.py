import datetime

from dash import html
import dash_bootstrap_components as dbc
from dash_extensions.javascript import Namespace
import dash_leaflet as dl

__all__ = [
    "site_development_notice",
    "header",
    "footer",
    "marker",
    "amsr_layer",
    "request_status_toast",
]

ns = Namespace("polarRoute", "mapFunctions")


def marker(
    lat: float, lon: float, loc: str = "start", draggable: bool = True, id: str = None
):
    if loc == "start":
        iconUrl = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png"
    elif loc == "end":
        iconUrl = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png"
    else:
        raise ValueError(f"Valid values of loc are 'start' and 'end', got {loc}.")

    return dl.Marker(
        id={"type": "marker", "index": id if id else loc},
        position=[lat, lon],
        draggable=draggable,
        eventHandlers=dict(dragend=ns("dragend")),
        icon=dict(iconUrl=iconUrl, iconAnchor=[11, 40]),
    )


def amsr_layer(date: datetime.date):
    return dl.TileLayer(
        id="amsr",
        url="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/AMSRU2_Sea_Ice_Concentration_12km/default/"
        + date.strftime("%Y-%m-%d")
        + "/GoogleMapsCompatible_Level6/{z}/{y}/{x}",
        attribution='Imagery provided by services from the Global Imagery Browse Services (GIBS), operated by the NASA/GSFC/Earth Science Data and Information System (<a href="https://earthdata.nasa.gov">ESDIS</a>) with funding provided by NASA/HQ.',
        maxZoom=6,
    )


def request_status_toast(content, header, icon, is_open=True, duration=5000):
    return dbc.Toast(
        [html.P(content, className="mb-0")],
        id="request-status-toast",
        header=header,
        icon=icon,
        dismissable=True,
        is_open=is_open,
        duration=duration,
    )


site_development_notice = html.Div(
    className="site-development-notice",
    children=[
        html.Div(
            className="bsk-container-fluid",
            children=[
                html.Span(
                    className="bsk-label bsk-label-phase-alpha",
                    children="Alpha",
                ),
                "This is a new website – your ",
                html.A(
                    children="feedback",
                    href="https://www.bas.ac.uk/project/autonomous-marine-operations-planning/",
                    target="_blank",
                ),
                " will help us to improve it.",
            ],
        ),
        html.Hr(),
    ],
)

header = dbc.NavbarSimple(
    color="black",
    dark=True,
    class_name="bsk-navbar bsk-navbar-expand-lg bsk-navbar-dark bsk-bg-dark",
    links_left=True,
    children=[
        dbc.Row(
            justify="between",
            children=[
                dbc.Col(
                    width=3,
                    children=dbc.NavbarBrand(
                        "PolarRoute",
                        href="https://www.bas.ac.uk/project/autonomous-marine-operations-planning/",
                        class_name="bsk-navbar-brand",
                    ),
                ),
                dbc.Col(),
                dbc.Col(
                    width=6,
                    children=dbc.Stack(
                        direction="horizontal",
                        children=[
                            dbc.NavItem(
                                dbc.NavLink(
                                    "About",
                                    external_link=True,
                                    target="_blank",
                                    href="https://www.bas.ac.uk/project/autonomous-marine-operations-planning/",
                                    className="bsk-dropdown-item",
                                )
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    "Admin",
                                    external_link=True,
                                    target="_blank",
                                    href="/admin",
                                    className="bsk-dropdown-item",
                                )
                            ),
                            dbc.DropdownMenu(
                                nav=True,
                                in_navbar=True,
                                align_end=True,
                                label="Part of British Antarctic Survey",
                                toggle_style={
                                    "border": 0,
                                },
                                class_name="bsk-dropdown bsk-shadow",
                                children=[
                                    dbc.DropdownMenuItem(
                                        "BAS Home",
                                        href="https://www.bas.ac.uk/",
                                        class_name="bsk-dropdown-item",
                                    ),
                                    dbc.DropdownMenuItem(
                                        "Discover BAS Data",
                                        href="https://data.bas.ac.uk/",
                                        class_name="bsk-dropdown-item",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        ),
    ],
)

footer = html.Footer(
    className="site-footer",
    children=[
        html.Div(
            className="bsk-footer bsk-footer-default m-0",
            children=[
                html.Div(
                    className="bsk-container",
                    children=[
                        html.Div(
                            className="bsk-footer-governance",
                            style={"display": "inline-block"},
                            children=[
                                "The ",
                                html.A(
                                    "British Antarctic Survey",
                                    href="https://www.bas.ac.uk/",
                                ),
                                " (BAS) is part of ",
                                html.A(
                                    "UK Research and Innovation",
                                    href="https://www.ukri.org/",
                                ),
                                " (UKRI)",
                                html.Div(
                                    className="bsk-footer-ogl",
                                    children=[
                                        html.Div(
                                            className="bsk-ogl-symbol",
                                            children=[
                                                html.A(
                                                    href="http://www.nationalarchives.gov.uk/doc/open-government-licence",
                                                    children=[
                                                        html.Span(
                                                            className="bsk-ogl-symbol",
                                                            children=[
                                                                "Open Government Licence"
                                                            ],
                                                        )
                                                    ],
                                                ),
                                            ],
                                        ),
                                        "All content is available under the ",
                                        html.A(
                                            "Open Government Licence",
                                            href="http://www.nationalarchives.gov.uk/doc/open-government-licence",
                                        ),
                                        ", v3.0 except where otherwise stated",
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            className="bsk-footer-policy-links",
                            style={
                                "float": "right",
                                "clear": "right",
                                "display": "inline-block",
                            },
                            children=[
                                html.Ul(
                                    className="bsk-list-inline",
                                    children=[
                                        html.Li(
                                            [
                                                html.A(
                                                    "Cookies",
                                                    href="/cookies",
                                                )
                                            ],
                                            className="d-inline-block me-2",
                                        ),
                                        html.Li(
                                            [html.A("Copyright", href="/copyright")],
                                            className="d-inline-block me-2",
                                        ),
                                        html.Li(
                                            [html.A("Privacy", href="/privacy")],
                                            className="d-inline-block",
                                        ),
                                    ],
                                ),
                                f"{datetime.date.today().year} British Antarctic Survey",
                            ],
                        ),
                    ],
                ),
            ],
            style={"padding-bottom": "2rem"},
        )
    ],
)
